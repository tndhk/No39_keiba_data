"""三連複馬券バックテストシミュレータ

三連複馬券の購入戦略をシミュレートし、回収率を計算する
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from keiba.backtest.fukusho_simulator import _BacktestRaceResultRepository
from keiba.models.entry import RaceEntry, ShutubaData
from keiba.models.race import Race
from keiba.models.race_result import RaceResult
from keiba.scrapers.race_detail import RaceDetailScraper
from keiba.services.prediction_service import PredictionService


@dataclass(frozen=True)
class SanrenpukuRaceResult:
    """1レースの三連複シミュレーション結果

    Attributes:
        race_id: レースID
        race_name: レース名
        venue: 開催場所
        race_date: 開催日
        predicted_trio: 予測Top3馬番（昇順ソート）
        actual_trio: 実際の3着以内の馬番（昇順ソート、払戻データがない場合はNone）
        hit: 的中したかどうか
        payout: 払戻額（外れの場合は0）
        investment: 投資額（100円固定: 1点買い）
    """

    race_id: str
    race_name: str
    venue: str
    race_date: str
    predicted_trio: tuple[int, int, int]
    actual_trio: tuple[int, int, int] | None
    hit: bool
    payout: int
    investment: int


@dataclass(frozen=True)
class SanrenpukuSummary:
    """期間シミュレーションのサマリー

    Attributes:
        period_from: 期間開始日
        period_to: 期間終了日
        total_races: 総レース数
        total_hits: 総的中数
        hit_rate: 的中率
        total_investment: 総投資額
        total_payout: 総払戻額
        return_rate: 回収率
        race_results: レース別結果
    """

    period_from: str
    period_to: str
    total_races: int
    total_hits: int
    hit_rate: float
    total_investment: int
    total_payout: int
    return_rate: float
    race_results: tuple[SanrenpukuRaceResult, ...]


class SanrenpukuSimulator:
    """三連複馬券シミュレータ

    予測モデルの出力を使用して、三連複馬券の購入戦略をシミュレートする。
    予測Top3の1点買いを行い、3頭全てが3着以内に入れば的中。
    """

    def __init__(self, db_path: str) -> None:
        """シミュレータを初期化

        Args:
            db_path: データベースファイルのパス
        """
        self._db_path = db_path

    def _get_session(self) -> Session:
        """DBセッションを取得

        Returns:
            Session: SQLAlchemyセッション
        """
        engine = create_engine(f"sqlite:///{self._db_path}")
        return Session(engine)

    def _get_races_in_period(
        self, session: Session, from_date: str, to_date: str, venues: list[str] | None
    ) -> list[Race]:
        """期間内のレースを取得

        Args:
            session: DBセッション
            from_date: 開始日 (YYYY-MM-DD形式)
            to_date: 終了日 (YYYY-MM-DD形式)
            venues: 対象会場リスト（Noneの場合は全会場）

        Returns:
            list[Race]: 対象レースのリスト
        """
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()

        stmt = select(Race).where(Race.date >= from_dt, Race.date <= to_dt)
        if venues:
            stmt = stmt.where(Race.course.in_(venues))
        stmt = stmt.order_by(Race.date, Race.race_number)

        return list(session.execute(stmt).scalars().all())

    def simulate_race(self, race_id: str) -> SanrenpukuRaceResult:
        """1レースの三連複シミュレーションを実行

        Args:
            race_id: レースID

        Returns:
            SanrenpukuRaceResult: シミュレーション結果

        Raises:
            ValueError: レースが見つからない場合
        """
        # 1. レース情報とRaceResultを取得
        with self._get_session() as session:
            race = session.get(Race, race_id)
            if race is None:
                raise ValueError(f"Race not found: {race_id}")

            race_name = race.name
            venue = race.course
            race_date = race.date.strftime("%Y-%m-%d")

            # RaceResultを取得
            results = session.execute(
                select(RaceResult).where(RaceResult.race_id == race_id)
            ).scalars().all()

            # 2. ShutubaDataを構築
            shutuba_data = self._build_shutuba_from_race_results(race, results)

            # 3. PredictionServiceで予測を実行
            repository = _BacktestRaceResultRepository(session)
            prediction_service = PredictionService(repository=repository)
            predictions = prediction_service.predict_from_shutuba(shutuba_data)

            # 4. 予測結果のrank順（=total_score降順）でTop-3馬番を取得
            sorted_predictions = sorted(predictions, key=lambda p: p.rank)
            top_3_horse_numbers = [p.horse_number for p in sorted_predictions[:3]]

        # 5. 三連複は順不同なので、昇順ソート
        predicted_trio = tuple(sorted(top_3_horse_numbers))

        # 6. 三連複払戻データを取得
        scraper = RaceDetailScraper()
        sanrenpuku_data = scraper.fetch_sanrenpuku_payout(race_id)

        # 7. 的中判定
        actual_trio = None
        hit = False
        payout = 0

        if sanrenpuku_data is not None:
            # 三連複データは{horse_numbers: [int, int, int], payout: int}形式
            horse_numbers = sanrenpuku_data["horse_numbers"]
            # 昇順ソートしてタプル化
            actual_trio = tuple(sorted(horse_numbers))

            # 予測トリオと実際のトリオが完全一致すれば的中
            if predicted_trio == actual_trio:
                hit = True
                payout = sanrenpuku_data["payout"]

        investment = 100  # 1点買い x 100円

        return SanrenpukuRaceResult(
            race_id=race_id,
            race_name=race_name,
            venue=venue,
            race_date=race_date,
            predicted_trio=predicted_trio,
            actual_trio=actual_trio,
            hit=hit,
            payout=payout,
            investment=investment,
        )

    def simulate_period(
        self,
        from_date: str,
        to_date: str,
        venues: list[str] | None = None,
    ) -> SanrenpukuSummary:
        """期間シミュレーションを実行

        Args:
            from_date: 開始日 (YYYY-MM-DD形式)
            to_date: 終了日 (YYYY-MM-DD形式)
            venues: 対象会場リスト（Noneの場合は全会場）

        Returns:
            SanrenpukuSummary: 期間サマリー
        """
        race_results = []

        with self._get_session() as session:
            races = self._get_races_in_period(session, from_date, to_date, venues)

        for race in races:
            try:
                result = self.simulate_race(race.id)
                race_results.append(result)
            except Exception:
                # レース取得エラーはスキップ
                continue

        # サマリー計算
        total_races = len(race_results)
        total_hits = sum(1 for r in race_results if r.hit)
        total_investment = sum(r.investment for r in race_results)
        total_payout = sum(r.payout for r in race_results)

        hit_rate = total_hits / total_races if total_races > 0 else 0.0
        return_rate = total_payout / total_investment if total_investment > 0 else 0.0

        return SanrenpukuSummary(
            period_from=from_date,
            period_to=to_date,
            total_races=total_races,
            total_hits=total_hits,
            hit_rate=hit_rate,
            total_investment=total_investment,
            total_payout=total_payout,
            return_rate=return_rate,
            race_results=tuple(race_results),
        )

    def _build_shutuba_from_race_results(
        self, race: Race, results: list[RaceResult]
    ) -> ShutubaData:
        """RaceResultのリストからShutubaDataを構築する

        Args:
            race: Raceオブジェクト
            results: RaceResultのリスト

        Returns:
            ShutubaData: 出馬表データ
        """
        entries = []
        for result in results:
            # horseリレーションシップから馬名を取得
            horse_name = result.horse.name if result.horse else ""
            # jockeyリレーションシップから騎手名を取得
            jockey_name = result.jockey.name if result.jockey else ""

            entry = RaceEntry(
                horse_id=result.horse_id,
                horse_name=horse_name,
                horse_number=result.horse_number,
                bracket_number=result.bracket_number,
                jockey_id=result.jockey_id,
                jockey_name=jockey_name,
                impost=result.impost if result.impost is not None else 0.0,
                sex=result.sex,
                age=result.age,
            )
            entries.append(entry)

        return ShutubaData(
            race_id=race.id,
            race_name=race.name,
            race_number=race.race_number,
            course=race.course,
            distance=race.distance,
            surface=race.surface,
            date=race.date.strftime("%Y-%m-%d"),
            entries=tuple(entries),
        )
