"""Predictorのテスト"""

import numpy as np
import pytest

from keiba.ml.predictor import Predictor
from keiba.ml.trainer import Trainer


class TestPredictor:
    """Predictorのテストクラス"""

    @pytest.fixture
    def trained_model(self):
        """学習済みモデルを提供するfixture"""
        trainer = Trainer()
        np.random.seed(42)
        X = np.random.rand(100, 19)
        y = np.random.randint(0, 2, 100)
        trainer.train(X, y)
        return trainer.model

    def test_init(self, trained_model):
        """初期化テスト"""
        predictor = Predictor(trained_model)
        assert predictor is not None

    def test_predict_proba(self, trained_model):
        """確率予測のテスト"""
        predictor = Predictor(trained_model)

        # 予測対象（5頭）
        X = np.random.rand(5, 19)
        probas = predictor.predict_proba(X)

        assert len(probas) == 5
        assert all(0 <= p <= 1 for p in probas)

    def test_predict_with_ranking(self, trained_model):
        """確率とランキングを返すテスト"""
        predictor = Predictor(trained_model)

        X = np.random.rand(5, 19)
        horse_ids = ["horse_1", "horse_2", "horse_3", "horse_4", "horse_5"]

        results = predictor.predict_with_ranking(X, horse_ids)

        assert len(results) == 5
        # ランキング順にソートされている
        assert results[0]["rank"] == 1
        assert results[4]["rank"] == 5
        # 確率が降順
        assert results[0]["probability"] >= results[1]["probability"]
        # horse_idが含まれる
        assert all("horse_id" in r for r in results)

    def test_predict_with_ranking_includes_all_fields(self, trained_model):
        """結果に必要なフィールドが含まれるテスト"""
        predictor = Predictor(trained_model)

        X = np.random.rand(3, 19)
        horse_ids = ["h1", "h2", "h3"]

        results = predictor.predict_with_ranking(X, horse_ids)

        for r in results:
            assert "rank" in r
            assert "horse_id" in r
            assert "probability" in r
