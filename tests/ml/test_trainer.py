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

    def test_trainer_accuracy_with_reduced_params(self):
        """軽量パラメータでも精度が許容範囲内であることを確認（AUC >= 0.55）"""
        trainer = Trainer(lightweight=True)

        # 学習データを生成（特徴量と結果に相関を持たせる）
        np.random.seed(42)
        n_samples = 500
        X = np.random.rand(n_samples, 19)
        # 最初の3特徴量の合計が大きいほど1になりやすい
        prob = 1 / (1 + np.exp(-(X[:, 0] + X[:, 1] + X[:, 2] - 1.5)))
        y = (np.random.rand(n_samples) < prob).astype(int)

        metrics = trainer.train_with_cv(X, y, n_splits=3)

        assert metrics["auc_roc"] is not None
        assert metrics["auc_roc"] >= 0.55, (
            f"AUC should be >= 0.55 with lightweight params, got {metrics['auc_roc']:.4f}"
        )

    def test_trainer_training_time_reduced(self):
        """学習時間が短縮されていることを確認（軽量モードは基準時間の50%以下）"""
        import time

        np.random.seed(42)
        n_samples = 1000
        X = np.random.rand(n_samples, 19)
        y = np.random.randint(0, 2, n_samples)

        # 通常モードでの学習時間を計測
        trainer_normal = Trainer(lightweight=False)
        start = time.perf_counter()
        trainer_normal.train(X, y)
        normal_time = time.perf_counter() - start

        # 軽量モードでの学習時間を計測
        trainer_light = Trainer(lightweight=True)
        start = time.perf_counter()
        trainer_light.train(X, y)
        light_time = time.perf_counter() - start

        # 軽量モードは通常モードの50%以下の時間であること
        assert light_time < normal_time * 0.5, (
            f"Lightweight training should be < 50% of normal time. "
            f"Normal: {normal_time:.4f}s, Lightweight: {light_time:.4f}s "
            f"(ratio: {light_time/normal_time:.2%})"
        )

    def test_trainer_lightweight_flag_default(self):
        """デフォルトはlightweight=Falseであること"""
        trainer = Trainer()
        assert trainer._lightweight is False

    def test_trainer_lightweight_params(self):
        """軽量モードで正しいパラメータが設定されること"""
        trainer = Trainer(lightweight=True)
        assert trainer._params["num_leaves"] == 15
        assert trainer._params["learning_rate"] == 0.1
        assert trainer._params["n_estimators"] == 50

    def test_trainer_normal_params(self):
        """通常モードで従来のパラメータが維持されること"""
        trainer = Trainer(lightweight=False)
        assert trainer._params["num_leaves"] == 31
        assert trainer._params["learning_rate"] == 0.05
        assert trainer._params["n_estimators"] == 100

    def test_save_model_creates_file(self, tmp_path):
        """学習後にsave_modelでファイルが作成されること"""
        trainer = Trainer()

        # ダミーの学習データ
        np.random.seed(42)
        X = np.random.rand(100, 19)
        y = np.random.randint(0, 2, 100)

        trainer.train(X, y)

        # モデルを保存
        model_path = tmp_path / "models" / "test_model.joblib"
        trainer.save_model(str(model_path))

        # ファイルが作成されていること
        assert model_path.exists()
        assert model_path.stat().st_size > 0

    def test_save_model_without_training_raises_error(self):
        """未学習時にsave_modelを呼ぶとValueErrorが発生すること"""
        trainer = Trainer()

        with pytest.raises(ValueError, match="モデルが学習されていません"):
            trainer.save_model("/tmp/test_model.joblib")
