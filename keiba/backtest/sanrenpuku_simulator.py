"""三連複馬券バックテストシミュレータ

三連複馬券の購入戦略をシミュレートし、回収率を計算する
"""

from dataclasses import dataclass

from sqlalchemy import select

from keiba.backtest.base_simulator import BaseSimulator
from keiba.models.race import Race
from keiba.models.race_result import RaceResult
from keiba.repositories.race_result_repository import SQLAlchemyRaceResultRepository
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


class SanrenpukuSimulator(BaseSimulator[SanrenpukuRaceResult, SanrenpukuSummary]):
    """三連複馬券シミュレータ

    予測モデルの出力を使用して、三連複馬券の購入戦略をシミュレートする。
    予測Top3の1点買いを行い、3頭全てが3着以内に入れば的中。
    """

    def simulate_race(self, race_id: str, model_path: str | None = None) -> SanrenpukuRaceResult:
        """1レースの三連複シミュレーションを実行

        Args:
            race_id: レースID
            model_path: MLモデルファイルパス（Noneの場合はファクタースコアのみ使用）

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
            repository = SQLAlchemyRaceResultRepository(session)
            prediction_service = PredictionService(repository=repository, model_path=model_path)
            predictions = prediction_service.predict_from_shutuba(shutuba_data)

            # 4. 予測結果のrank順（=total_score降順）でTop-3馬番を取得
            sorted_predictions = sorted(predictions, key=lambda p: p.rank)
            top_3_horse_numbers = [p.horse_number for p in sorted_predictions[:3]]

        # 5. 三連複は順不同なので、昇順ソート
        predicted_trio = tuple(sorted(top_3_horse_numbers))

        # 6. 三連複払戻データを取得
        sanrenpuku_data = self._scraper.fetch_sanrenpuku_payout(race_id)

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

    def _build_summary(
        self,
        period_from: str,
        period_to: str,
        race_results: list[SanrenpukuRaceResult],
    ) -> SanrenpukuSummary:
        """期間サマリーを構築

        Args:
            period_from: 期間開始日
            period_to: 期間終了日
            race_results: レース別結果のリスト

        Returns:
            SanrenpukuSummary: 期間サマリー
        """
        total_races = len(race_results)
        total_hits = sum(1 for r in race_results if r.hit)
        total_investment = sum(r.investment for r in race_results)
        total_payout = sum(r.payout for r in race_results)

        hit_rate = total_hits / total_races if total_races > 0 else 0.0
        return_rate = total_payout / total_investment if total_investment > 0 else 0.0

        return SanrenpukuSummary(
            period_from=period_from,
            period_to=period_to,
            total_races=total_races,
            total_hits=total_hits,
            hit_rate=hit_rate,
            total_investment=total_investment,
            total_payout=total_payout,
            return_rate=return_rate,
            race_results=tuple(race_results),
        )
