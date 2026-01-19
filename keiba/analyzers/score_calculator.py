"""ScoreCalculator - 重み付きスコア計算"""

from keiba.config.weights import FACTOR_WEIGHTS


class ScoreCalculator:
    """Factor結果の重み付き合計スコアを計算する"""

    def __init__(self, weights: dict[str, float] | None = None):
        """ScoreCalculatorを初期化する

        Args:
            weights: Factor重み設定（Noneの場合はデフォルト値を使用）
        """
        self._weights = weights or FACTOR_WEIGHTS

    def get_weights(self) -> dict[str, float]:
        """重み設定を取得する"""
        return self._weights.copy()

    def calculate_total(self, factor_scores: dict[str, float | None]) -> float | None:
        """重み付き合計スコアを計算する

        Args:
            factor_scores: 各Factorのスコア（Noneは無視される）

        Returns:
            重み付き合計スコア（0-100）、全てNoneの場合はNone
        """
        total_score = 0.0
        total_weight = 0.0

        for factor_name, score in factor_scores.items():
            if score is not None and factor_name in self._weights:
                weight = self._weights[factor_name]
                total_score += score * weight
                total_weight += weight

        if total_weight == 0:
            return None

        # 正規化（有効なFactorの重みで割る）
        return round(total_score / total_weight, 1)
