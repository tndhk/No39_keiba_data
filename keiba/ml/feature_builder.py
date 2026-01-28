"""特徴量生成モジュール"""

import numpy as np
from typing import Any


class FeatureBuilder:
    """ML予測用の特徴量を生成するクラス

    19特徴量を生成:
    - 分析ファクター由来: 7つ
    - 生データ由来: 8つ
    - 派生特徴量: 4つ
    """

    FACTOR_NAMES = [
        "past_results",
        "course_fit",
        "time_index",
        "last_3f",
        "popularity",
        "pedigree",
        "running_style",
    ]

    RAW_DATA_NAMES = [
        "odds",
        "popularity",
        "weight",
        "weight_diff",
        "age",
        "impost",
        "horse_number",
        "field_size",
    ]

    DERIVED_NAMES = [
        "win_rate",
        "top3_rate",
        "avg_finish_position",
        "days_since_last_race",
    ]

    # LightGBMのネイティブ欠損値処理を活用するためnp.nanを使用
    MISSING_VALUE = np.nan

    def __init__(self):
        """初期化"""
        pass

    def build_features(
        self,
        race_result: dict[str, Any],
        factor_scores: dict[str, float | None],
        field_size: int,
        past_stats: dict[str, float | None],
    ) -> dict[str, float]:
        """レース結果から特徴量を生成する

        Args:
            race_result: レース結果データ（odds, popularity, weight等）
            factor_scores: 各分析ファクターのスコア
            field_size: 出走頭数
            past_stats: 派生特徴量（win_rate, top3_rate等）

        Returns:
            19特徴量の辞書
        """
        features = {}

        # 分析ファクター由来（7つ）
        for name in self.FACTOR_NAMES:
            score = factor_scores.get(name)
            features[f"{name}_score"] = (
                score if score is not None else self.MISSING_VALUE
            )

        # 生データ由来（8つ）
        for name in self.RAW_DATA_NAMES:
            if name == "field_size":
                features[name] = field_size
            elif name == "popularity":
                # popularityは生データ名とファクター名が重複するので区別
                value = race_result.get(name)
                features[name] = value if value is not None else self.MISSING_VALUE
            else:
                value = race_result.get(name)
                features[name] = value if value is not None else self.MISSING_VALUE

        # 派生特徴量（4つ）
        for name in self.DERIVED_NAMES:
            value = past_stats.get(name)
            features[name] = value if value is not None else self.MISSING_VALUE

        return features

    def get_feature_names(self) -> list[str]:
        """特徴量名のリストを取得する

        Returns:
            19特徴量の名前リスト
        """
        names = []

        # 分析ファクター由来
        for name in self.FACTOR_NAMES:
            names.append(f"{name}_score")

        # 生データ由来
        names.extend(self.RAW_DATA_NAMES)

        # 派生特徴量
        names.extend(self.DERIVED_NAMES)

        return names
