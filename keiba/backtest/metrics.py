"""バックテストメトリクス計算モジュール

ML予測と7ファクター予測の精度評価メトリクスを計算する
"""

from dataclasses import dataclass


@dataclass
class PredictionResult:
    """1頭の予測結果"""

    horse_number: int  # 馬番
    horse_name: str  # 馬名
    ml_probability: float | None  # ML予測確率（LightGBM未インストール時はNone）
    ml_rank: int | None  # ML予測順位
    factor_rank: int  # 7ファクター順位
    actual_rank: int  # 実際の着順


@dataclass
class RaceBacktestResult:
    """1レースのバックテスト結果"""

    race_id: str
    race_date: str
    race_name: str
    venue: str
    predictions: list[PredictionResult]


class MetricsCalculator:
    """バックテストメトリクス計算クラス"""

    @staticmethod
    def precision_at_k(
        results: list[RaceBacktestResult], k: int, use_ml: bool = True
    ) -> float:
        """Precision@k を計算

        予測上位k頭のうち、実際にk着以内に入った馬の割合を計算する。
        例: k=1の場合、予測1位が1着に入った割合
            k=3の場合、予測上位3頭のうち3着以内に入った馬の割合

        Args:
            results: バックテスト結果リスト
            k: 上位k位まで評価
            use_ml: True=ML予測、False=7ファクター

        Returns:
            Precision@k (0.0 - 1.0)
        """
        if not results:
            return 0.0

        total_hits = 0
        total_predictions = 0

        for race_result in results:
            predictions = race_result.predictions
            if not predictions:
                continue

            # 予測順位でソート
            if use_ml:
                # ML予測がNoneの馬はスキップ
                valid_predictions = [p for p in predictions if p.ml_rank is not None]
                if not valid_predictions:
                    continue
                sorted_predictions = sorted(valid_predictions, key=lambda p: p.ml_rank)
            else:
                sorted_predictions = sorted(predictions, key=lambda p: p.factor_rank)

            # 上位k頭を取得（予測数がkより少ない場合は全て）
            top_k = sorted_predictions[:k]

            # k着以内に入った馬をカウント（kに応じてヒット条件が変わる）
            for pred in top_k:
                total_predictions += 1
                if pred.actual_rank <= k:
                    total_hits += 1

        if total_predictions == 0:
            return 0.0

        return total_hits / total_predictions

    @staticmethod
    def hit_rate_by_rank(
        results: list[RaceBacktestResult], rank: int, use_ml: bool = True
    ) -> float:
        """指定順位の的中率を計算

        指定した予測順位の馬が3着以内に入った割合を計算する。

        Args:
            results: バックテスト結果リスト
            rank: 予測順位（1=1位指名、2=2位指名...）
            use_ml: True=ML予測、False=7ファクター

        Returns:
            的中率 (0.0 - 1.0) - 3着以内に入った割合
        """
        if not results:
            return 0.0

        total_races = 0
        hits = 0

        for race_result in results:
            predictions = race_result.predictions
            if not predictions:
                continue

            # 指定順位の馬を探す
            target_pred = next(
                (
                    p
                    for p in predictions
                    if (p.ml_rank if use_ml else p.factor_rank) == rank
                ),
                None,
            )
            if target_pred is None:
                continue

            total_races += 1
            if target_pred.actual_rank <= 3:
                hits += 1

        if total_races == 0:
            return 0.0

        return hits / total_races

    @staticmethod
    def calculate(results: list[RaceBacktestResult]) -> dict:
        """全メトリクスを計算

        ML予測と7ファクター予測の両方について、主要メトリクスを計算する。

        Args:
            results: バックテスト結果リスト

        Returns:
            {
                'ml': {
                    'precision_at_1': float,
                    'precision_at_3': float,
                    'hit_rate_rank_1': float,
                    'hit_rate_rank_2': float,
                    'hit_rate_rank_3': float,
                },
                'factor': {
                    'precision_at_1': float,
                    'precision_at_3': float,
                    'hit_rate_rank_1': float,
                    'hit_rate_rank_2': float,
                    'hit_rate_rank_3': float,
                }
            }
        """
        return {
            "ml": {
                "precision_at_1": MetricsCalculator.precision_at_k(
                    results, k=1, use_ml=True
                ),
                "precision_at_3": MetricsCalculator.precision_at_k(
                    results, k=3, use_ml=True
                ),
                "hit_rate_rank_1": MetricsCalculator.hit_rate_by_rank(
                    results, rank=1, use_ml=True
                ),
                "hit_rate_rank_2": MetricsCalculator.hit_rate_by_rank(
                    results, rank=2, use_ml=True
                ),
                "hit_rate_rank_3": MetricsCalculator.hit_rate_by_rank(
                    results, rank=3, use_ml=True
                ),
            },
            "factor": {
                "precision_at_1": MetricsCalculator.precision_at_k(
                    results, k=1, use_ml=False
                ),
                "precision_at_3": MetricsCalculator.precision_at_k(
                    results, k=3, use_ml=False
                ),
                "hit_rate_rank_1": MetricsCalculator.hit_rate_by_rank(
                    results, rank=1, use_ml=False
                ),
                "hit_rate_rank_2": MetricsCalculator.hit_rate_by_rank(
                    results, rank=2, use_ml=False
                ),
                "hit_rate_rank_3": MetricsCalculator.hit_rate_by_rank(
                    results, rank=3, use_ml=False
                ),
            },
        }
