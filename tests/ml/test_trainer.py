"""Trainerのテスト"""

import numpy as np
import pytest

# LightGBMが使用可能か確認
try:
    import lightgbm  # noqa: F401

    LIGHTGBM_AVAILABLE = True
except (ImportError, OSError):
    LIGHTGBM_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not LIGHTGBM_AVAILABLE,
    reason="LightGBM is not available (missing libomp or other dependency)",
)

if LIGHTGBM_AVAILABLE:
    from keiba.ml.trainer import Trainer
else:
    Trainer = None


class TestTrainer:
    """Trainerのテストクラス"""

    def test_init(self):
        """初期化テスト"""
        trainer = Trainer()
        assert trainer is not None
        assert trainer.model is None

    def test_train_with_valid_data(self):
        """正常データでの学習テスト"""
        trainer = Trainer()

        # ダミーの学習データ（100サンプル、19特徴量）
        np.random.seed(42)
        X = np.random.rand(100, 19)
        y = np.random.randint(0, 2, 100)  # 0 or 1

        trainer.train(X, y)

        assert trainer.model is not None

    def test_train_with_insufficient_data(self):
        """データ不足時の警告テスト"""
        trainer = Trainer()

        # 少なすぎるデータ（10サンプル）
        X = np.random.rand(10, 19)
        y = np.random.randint(0, 2, 10)

        # 警告を出すが学習は実行する
        trainer.train(X, y)
        assert trainer.model is not None

    def test_evaluate_returns_metrics(self):
        """評価指標が返されるテスト"""
        trainer = Trainer()

        np.random.seed(42)
        X = np.random.rand(200, 19)
        # 不均衡データ（3着以内は約25%）
        y = (np.random.rand(200) < 0.25).astype(int)

        metrics = trainer.train_with_cv(X, y, n_splits=3)

        assert "precision_at_1" in metrics
        assert "precision_at_3" in metrics
        assert "auc_roc" in metrics
        assert "log_loss" in metrics
        assert all(0 <= v <= 1 for v in metrics.values() if v is not None)

    def test_get_feature_importance(self):
        """特徴量重要度取得のテスト"""
        trainer = Trainer()

        X = np.random.rand(100, 19)
        y = np.random.randint(0, 2, 100)

        trainer.train(X, y)
        importance = trainer.get_feature_importance()

        assert len(importance) == 19
        assert all(v >= 0 for v in importance)
