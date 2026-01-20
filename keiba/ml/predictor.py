"""推論モジュール"""

from typing import Any

import lightgbm as lgb
import numpy as np


class Predictor:
    """学習済みモデルで予測を行うクラス"""

    def __init__(self, model: lgb.LGBMClassifier):
        """初期化

        Args:
            model: 学習済みのLightGBMモデル
        """
        self.model = model

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """3着以内確率を予測する

        Args:
            X: 特徴量行列 (n_samples, n_features)

        Returns:
            各サンプルの3着以内確率
        """
        return self.model.predict_proba(X)[:, 1]

    def predict_with_ranking(
        self, X: np.ndarray, horse_ids: list[str]
    ) -> list[dict[str, Any]]:
        """確率とランキングを返す

        Args:
            X: 特徴量行列
            horse_ids: 馬IDのリスト

        Returns:
            ランキング順にソートされた結果リスト
            各要素: {"rank": int, "horse_id": str, "probability": float}
        """
        probas = self.predict_proba(X)

        results = []
        for i, (horse_id, proba) in enumerate(zip(horse_ids, probas)):
            results.append({
                "horse_id": horse_id,
                "probability": float(proba),
            })

        # 確率降順でソート
        results.sort(key=lambda x: x["probability"], reverse=True)

        # ランキングを付与
        for rank, result in enumerate(results, 1):
            result["rank"] = rank

        return results
