"""FeatureBuilderのテスト"""

import numpy as np
import pytest

from keiba.ml.feature_builder import FeatureBuilder


class TestFeatureBuilder:
    """FeatureBuilderのテストクラス"""

    def test_init(self):
        """初期化テスト"""
        builder = FeatureBuilder()
        assert builder is not None

    def test_build_features_from_race_result(self):
        """レース結果から特徴量を生成するテスト"""
        builder = FeatureBuilder()

        # モックデータ
        race_result = {
            "horse_id": "2019104308",
            "odds": 5.5,
            "popularity": 2,
            "weight": 480,
            "weight_diff": 4,
            "age": 4,
            "impost": 57.0,
            "horse_number": 5,
        }
        factor_scores = {
            "past_results": 75.0,
            "course_fit": 80.0,
            "time_index": 70.0,
            "last_3f": 85.0,
            "popularity": 90.0,
            "pedigree": 65.0,
            "running_style": 70.0,
        }
        field_size = 16
        past_stats = {
            "win_rate": 0.25,
            "top3_rate": 0.5,
            "avg_finish_position": 3.2,
            "days_since_last_race": 28,
        }

        features = builder.build_features(
            race_result=race_result,
            factor_scores=factor_scores,
            field_size=field_size,
            past_stats=past_stats,
        )

        # 19特徴量が生成されることを確認
        assert len(features) == 19
        assert features["odds"] == 5.5
        assert features["popularity"] == 2
        assert features["past_results_score"] == 75.0
        assert features["win_rate"] == 0.25

    def test_build_features_with_missing_values(self):
        """欠損値がある場合のテスト"""
        builder = FeatureBuilder()

        race_result = {
            "horse_id": "2019104308",
            "odds": None,  # 欠損
            "popularity": None,  # 欠損
            "weight": 480,
            "weight_diff": None,  # 欠損
            "age": 4,
            "impost": 57.0,
            "horse_number": 5,
        }
        factor_scores = {
            "past_results": None,  # 欠損
            "course_fit": 80.0,
            "time_index": 70.0,
            "last_3f": None,  # 欠損
            "popularity": 90.0,
            "pedigree": None,  # 欠損
            "running_style": 70.0,
        }
        field_size = 16
        past_stats = {
            "win_rate": None,  # 欠損
            "top3_rate": None,  # 欠損
            "avg_finish_position": None,  # 欠損
            "days_since_last_race": None,  # 欠損
        }

        features = builder.build_features(
            race_result=race_result,
            factor_scores=factor_scores,
            field_size=field_size,
            past_stats=past_stats,
        )

        # 欠損値はnp.nanで埋められる
        assert np.isnan(features["odds"])
        assert np.isnan(features["popularity"])
        assert np.isnan(features["past_results_score"])
        assert np.isnan(features["win_rate"])

    def test_get_feature_names(self):
        """特徴量名リスト取得のテスト"""
        builder = FeatureBuilder()
        names = builder.get_feature_names()

        assert len(names) == 19
        assert "odds" in names
        assert "past_results_score" in names
        assert "win_rate" in names

    def test_missing_values_use_nan(self):
        """欠損値がnp.nanで表現されること"""
        builder = FeatureBuilder()

        race_result = {
            "horse_id": "2019104308",
            "odds": None,
            "popularity": None,
            "weight": 480,
            "weight_diff": None,
            "age": 4,
            "impost": 57.0,
            "horse_number": 5,
        }
        factor_scores = {
            "past_results": None,
            "course_fit": 80.0,
            "time_index": 70.0,
            "last_3f": None,
            "popularity": 90.0,
            "pedigree": None,
            "running_style": 70.0,
        }
        field_size = 16
        past_stats = {
            "win_rate": None,
            "top3_rate": None,
            "avg_finish_position": None,
            "days_since_last_race": None,
        }

        features = builder.build_features(
            race_result=race_result,
            factor_scores=factor_scores,
            field_size=field_size,
            past_stats=past_stats,
        )

        # 欠損値はnp.nanで表現されるべき
        assert np.isnan(features["odds"])
        assert np.isnan(features["popularity"])
        assert np.isnan(features["past_results_score"])
        assert np.isnan(features["win_rate"])
