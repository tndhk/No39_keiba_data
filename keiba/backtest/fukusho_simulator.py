"""複勝馬券バックテストシミュレータ

複勝馬券の購入戦略をシミュレートし、回収率を計算する
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from keiba.models.race import Race
from keiba.models.race_result import RaceResult
from keiba.scrapers.race_detail import RaceDetailScraper


@dataclass(frozen=True)
class FukushoRaceResult:
    """1レースの複勝シミュレーション結果

    Attributes:
        race_id: レースID
        race_name: レース名
        venue: 開催場所
        race_date: 開催日
        top_n_predictions: 予測top-n馬番
        fukusho_horses: 複勝対象馬番（3着以内）
        hits: 的中した馬番
        payouts: 的中した払戻額
        investment: 投資額（100 * top_n）
        payout_total: 払戻総額
    """

    race_id: str
    race_name: str
    venue: str
    race_date: str
    top_n_predictions: tuple[int, ...]
    fukusho_horses: tuple[int, ...]
    hits: tuple[int, ...]
    payouts: tuple[int, ...]
    investment: int
    payout_total: int


@dataclass(frozen=True)
class FukushoSummary:
    """期間シミュレーションのサマリー

    Attributes:
        period_from: 期間開始日
        period_to: 期間終了日
        total_races: 総レース数
        total_bets: 総ベット数
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
    total_bets: int
    total_hits: int
    hit_rate: float
    total_investment: int
    total_payout: int
    return_rate: float
    race_results: tuple[FukushoRaceResult, ...]


class FukushoSimulator:
    """複勝馬券シミュレータ

    予測モデルの出力を使用して、複勝馬券の購入戦略をシミュレートする。
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

    def simulate_race(self, race_id: str, top_n: int = 3) -> FukushoRaceResult:
        """1レースの複勝シミュレーションを実行

        Args:
            race_id: レースID
            top_n: 購入する上位馬の数

        Returns:
            FukushoRaceResult: シミュレーション結果

        Raises:
            ValueError: レースが見つからない場合
        """
        # 1. レース情報を取得
        with self._get_session() as session:
            race = session.get(Race, race_id)
            if race is None:
                raise ValueError(f"Race not found: {race_id}")

            race_name = race.name
            venue = race.course
            race_date = race.date.strftime("%Y-%m-%d")

        # 2. 払戻データを取得
        scraper = RaceDetailScraper()
        payout_data = scraper.fetch_payouts(race_id)

        # 複勝対象馬番と払戻額をマップ
        fukusho_map = {p["horse_number"]: p["payout"] for p in payout_data}
        fukusho_horses = tuple(fukusho_map.keys())

        # 3. 予測を実行（バックテストなのでDBからRaceResultを取得して人気順で予測）
        with self._get_session() as session:
            results = session.execute(
                select(RaceResult).where(RaceResult.race_id == race_id)
            ).scalars().all()

            # 人気順にソートし、予測順位を付与
            sorted_results = sorted(results, key=lambda r: r.popularity or 999)
            top_n_predictions = tuple(r.horse_number for r in sorted_results[:top_n])

        # 4. 的中判定
        hits = []
        payouts_list = []
        for horse_num in top_n_predictions:
            if horse_num in fukusho_map:
                hits.append(horse_num)
                payouts_list.append(fukusho_map[horse_num])

        investment = 100 * top_n
        payout_total = sum(payouts_list)

        return FukushoRaceResult(
            race_id=race_id,
            race_name=race_name,
            venue=venue,
            race_date=race_date,
            top_n_predictions=top_n_predictions,
            fukusho_horses=fukusho_horses,
            hits=tuple(hits),
            payouts=tuple(payouts_list),
            investment=investment,
            payout_total=payout_total,
        )

    def simulate_period(
        self,
        from_date: str,
        to_date: str,
        venues: list[str] | None = None,
        top_n: int = 3,
    ) -> FukushoSummary:
        """期間シミュレーションを実行

        Args:
            from_date: 開始日 (YYYY-MM-DD形式)
            to_date: 終了日 (YYYY-MM-DD形式)
            venues: 対象会場リスト（Noneの場合は全会場）
            top_n: 購入する上位馬の数

        Returns:
            FukushoSummary: 期間サマリー
        """
        race_results = []

        with self._get_session() as session:
            races = self._get_races_in_period(session, from_date, to_date, venues)

        for race in races:
            try:
                result = self.simulate_race(race.id, top_n)
                race_results.append(result)
            except Exception:
                # レース取得エラーはスキップ
                continue

        # サマリー計算
        total_races = len(race_results)
        total_bets = total_races * top_n
        total_hits = sum(len(r.hits) for r in race_results)
        total_investment = sum(r.investment for r in race_results)
        total_payout = sum(r.payout_total for r in race_results)

        hit_rate = total_hits / total_bets if total_bets > 0 else 0.0
        return_rate = total_payout / total_investment if total_investment > 0 else 0.0

        return FukushoSummary(
            period_from=from_date,
            period_to=to_date,
            total_races=total_races,
            total_bets=total_bets,
            total_hits=total_hits,
            hit_rate=hit_rate,
            total_investment=total_investment,
            total_payout=total_payout,
            return_rate=return_rate,
            race_results=tuple(race_results),
        )
