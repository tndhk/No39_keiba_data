"""馬連馬券バックテストシミュレータ

馬連馬券の購入戦略をシミュレートし、回収率を計算する
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
class UmarenRaceResult:
    """1レースの馬連シミュレーション結果

    Attributes:
        race_id: レースID
        race_name: レース名
        venue: 開催場所
        race_date: 開催日
        bet_combinations: 購入組み合わせ（3点: Top1-2, Top1-3, Top2-3）
        actual_pair: 実際の1-2着の組み合わせ（払戻データがない場合はNone）
        hit: 的中したかどうか
        payout: 払戻額（外れの場合は0）
        investment: 投資額（300円固定: 3点 x 100円）
    """

    race_id: str
    race_name: str
    venue: str
    race_date: str
    bet_combinations: tuple[tuple[int, int], ...]
    actual_pair: tuple[int, int] | None
    hit: bool
    payout: int
    investment: int


@dataclass(frozen=True)
class UmarenSummary:
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
    race_results: tuple[UmarenRaceResult, ...]


class UmarenSimulator(BaseSimulator[UmarenRaceResult, UmarenSummary]):
    """馬連馬券シミュレータ

    予測モデルの出力を使用して、馬連馬券の購入戦略をシミュレートする。
    予測Top3から3組の馬連を購入（1-2, 1-3, 2-3）し、的中すれば払戻を得る。
    """

    def _generate_bet_combinations(
        self, top_3_predictions: tuple[int, ...]
    ) -> tuple[tuple[int, int], ...]:
        """予測Top3から馬連購入組み合わせを生成

        Args:
            top_3_predictions: 予測Top3馬番（順位順）

        Returns:
            tuple[tuple[int, int], ...]: 馬連組み合わせ（3点）
                各組み合わせは(小さい番号, 大きい番号)の順
        """
        if len(top_3_predictions) < 3:
            return ()

        h1, h2, h3 = top_3_predictions[0], top_3_predictions[1], top_3_predictions[2]

        # 馬連は順不同なので、小さい番号を先に
        combo_1_2 = (min(h1, h2), max(h1, h2))
        combo_1_3 = (min(h1, h3), max(h1, h3))
        combo_2_3 = (min(h2, h3), max(h2, h3))

        return (combo_1_2, combo_1_3, combo_2_3)

    def simulate_race(self, race_id: str, model_path: str | None = None) -> UmarenRaceResult:
        """1レースの馬連シミュレーションを実行

        Args:
            race_id: レースID
            model_path: MLモデルファイルパス（Noneの場合はファクタースコアのみ使用）

        Returns:
            UmarenRaceResult: シミュレーション結果

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
            top_3_predictions = tuple(
                p.horse_number for p in sorted_predictions[:3]
            )

        # 5. 馬連組み合わせを生成
        bet_combinations = self._generate_bet_combinations(top_3_predictions)

        # 6. 馬連払戻データを取得
        scraper = RaceDetailScraper()
        umaren_data = scraper.fetch_umaren_payout(race_id)

        # 7. 的中判定
        actual_pair = None
        hit = False
        payout = 0

        if umaren_data is not None:
            # 馬連データは{horse_numbers: [int, int], payout: int}形式
            horse_numbers = umaren_data["horse_numbers"]
            # 小さい番号を先にしてタプル化
            actual_pair = (min(horse_numbers), max(horse_numbers))

            # 購入組み合わせに的中があるかチェック
            if actual_pair in bet_combinations:
                hit = True
                payout = umaren_data["payout"]

        investment = 300  # 3点 x 100円

        return UmarenRaceResult(
            race_id=race_id,
            race_name=race_name,
            venue=venue,
            race_date=race_date,
            bet_combinations=bet_combinations,
            actual_pair=actual_pair,
            hit=hit,
            payout=payout,
            investment=investment,
        )

    def _build_summary(
        self, period_from: str, period_to: str, race_results: list[UmarenRaceResult]
    ) -> UmarenSummary:
        """期間サマリーを構築

        Args:
            period_from: 期間開始日
            period_to: 期間終了日
            race_results: レース別結果のリスト

        Returns:
            UmarenSummary: 期間サマリー
        """
        total_races = len(race_results)
        total_hits = sum(1 for r in race_results if r.hit)
        total_investment = sum(r.investment for r in race_results)
        total_payout = sum(r.payout for r in race_results)

        hit_rate = total_hits / total_races if total_races > 0 else 0.0
        return_rate = total_payout / total_investment if total_investment > 0 else 0.0

        return UmarenSummary(
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
