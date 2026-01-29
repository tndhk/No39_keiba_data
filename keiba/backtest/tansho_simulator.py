"""単勝馬券バックテストシミュレータ

単勝馬券の購入戦略をシミュレートし、回収率を計算する
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
class TanshoRaceResult:
    """1レースの単勝シミュレーション結果

    Attributes:
        race_id: レースID
        race_name: レース名
        venue: 開催場所
        race_date: 開催日
        top_n_predictions: 予測top-n馬番
        winning_horse: 1着馬の馬番（払戻データがない場合はNone）
        hit: 的中したかどうか
        payout: 払戻額（外れの場合は0）
        investment: 投資額（100 * top_n）
    """

    race_id: str
    race_name: str
    venue: str
    race_date: str
    top_n_predictions: tuple[int, ...]
    winning_horse: int | None
    hit: bool
    payout: int
    investment: int


@dataclass(frozen=True)
class TanshoSummary:
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
    race_results: tuple[TanshoRaceResult, ...]


class TanshoSimulator(BaseSimulator[TanshoRaceResult, TanshoSummary]):
    """単勝馬券シミュレータ

    予測モデルの出力を使用して、単勝馬券の購入戦略をシミュレートする。
    予測Top-Nの各馬に100円ずつ賭け、いずれかが1着になれば的中。
    """

    def simulate_race(self, race_id: str, top_n: int = 3, model_path: str | None = None) -> TanshoRaceResult:
        """1レースの単勝シミュレーションを実行

        Args:
            race_id: レースID
            top_n: 購入する上位馬の数
            model_path: MLモデルファイルパス（Noneの場合はファクタースコアのみ使用）

        Returns:
            TanshoRaceResult: シミュレーション結果

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

            # 4. 予測結果のrank順（=total_score降順）でTop-N馬番を取得
            sorted_predictions = sorted(predictions, key=lambda p: p.rank)
            top_n_predictions = tuple(
                p.horse_number for p in sorted_predictions[:top_n]
            )

        # 5. 単勝払戻データを取得
        tansho_data = self._scraper.fetch_tansho_payout(race_id)

        # 6. 的中判定
        winning_horse = None
        hit = False
        payout = 0

        if tansho_data is not None:
            winning_horse = tansho_data["horse_number"]
            if winning_horse in top_n_predictions:
                hit = True
                payout = tansho_data["payout"]

        investment = 100 * top_n

        return TanshoRaceResult(
            race_id=race_id,
            race_name=race_name,
            venue=venue,
            race_date=race_date,
            top_n_predictions=top_n_predictions,
            winning_horse=winning_horse,
            hit=hit,
            payout=payout,
            investment=investment,
        )

    def _build_summary(
        self, period_from: str, period_to: str, race_results: list[TanshoRaceResult]
    ) -> TanshoSummary:
        """期間サマリーを構築

        Args:
            period_from: 期間開始日
            period_to: 期間終了日
            race_results: レース別結果のリスト

        Returns:
            TanshoSummary: 期間サマリー
        """
        total_races = len(race_results)
        total_bets = sum(len(r.top_n_predictions) for r in race_results)
        total_hits = sum(1 for r in race_results if r.hit)
        total_investment = sum(r.investment for r in race_results)
        total_payout = sum(r.payout for r in race_results)

        hit_rate = total_hits / total_races if total_races > 0 else 0.0
        return_rate = total_payout / total_investment if total_investment > 0 else 0.0

        return TanshoSummary(
            period_from=period_from,
            period_to=period_to,
            total_races=total_races,
            total_bets=total_bets,
            total_hits=total_hits,
            hit_rate=hit_rate,
            total_investment=total_investment,
            total_payout=total_payout,
            return_rate=return_rate,
            race_results=tuple(race_results),
        )
