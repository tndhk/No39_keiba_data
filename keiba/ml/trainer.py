"""モデル学習モジュール"""

import warnings
from typing import Any

import lightgbm as lgb
import numpy as np
from sklearn.model_selection import StratifiedKFold


class Trainer:
    """LightGBMモデルの学習を行うクラス"""

    MIN_SAMPLES = 100  # 最低限必要なサンプル数

    # 通常モード用パラメータ
    _NORMAL_PARAMS = {
        "num_leaves": 31,
        "learning_rate": 0.05,
        "n_estimators": 100,
    }

    # 軽量モード用パラメータ（バックテスト向け）
    _LIGHTWEIGHT_PARAMS = {
        "num_leaves": 15,
        "learning_rate": 0.1,
        "n_estimators": 50,
    }

    def __init__(self, lightweight: bool = False):
        """初期化

        Args:
            lightweight: Trueの場合、バックテスト用の軽量パラメータを使用
        """
        self.model: lgb.LGBMClassifier | None = None
        self._lightweight = lightweight

        # モードに応じたパラメータを選択
        mode_params = self._LIGHTWEIGHT_PARAMS if lightweight else self._NORMAL_PARAMS

        self._params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "boosting_type": "gbdt",
            "feature_fraction": 0.9,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
            **mode_params,
        }

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """モデルを学習する

        Args:
            X: 特徴量行列 (n_samples, n_features)
            y: ラベル (n_samples,) - 1: 3着以内, 0: 4着以下
        """
        if len(X) < self.MIN_SAMPLES:
            warnings.warn(
                f"学習データが少なすぎます（{len(X)}サンプル）。"
                f"最低{self.MIN_SAMPLES}サンプル推奨。"
            )

        self.model = lgb.LGBMClassifier(**self._params)
        self.model.fit(X, y)

    def train_with_cv(
        self, X: np.ndarray, y: np.ndarray, n_splits: int = 5
    ) -> dict[str, float]:
        """クロスバリデーション付きで学習し、評価指標を返す

        Args:
            X: 特徴量行列
            y: ラベル
            n_splits: CVの分割数

        Returns:
            評価指標の辞書
        """
        if len(X) < self.MIN_SAMPLES:
            warnings.warn(
                f"学習データが少なすぎます（{len(X)}サンプル）。"
                f"最低{self.MIN_SAMPLES}サンプル推奨。"
            )

        kfold = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

        precision_at_1_scores = []
        precision_at_3_scores = []
        auc_scores = []
        logloss_scores = []

        for train_idx, val_idx in kfold.split(X, y):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]

            model = lgb.LGBMClassifier(**self._params)
            model.fit(X_train, y_train)

            y_proba = model.predict_proba(X_val)[:, 1]

            # Precision@K計算
            p_at_1 = self._precision_at_k(y_val, y_proba, k=1)
            p_at_3 = self._precision_at_k(y_val, y_proba, k=3)
            precision_at_1_scores.append(p_at_1)
            precision_at_3_scores.append(p_at_3)

            # AUC-ROC
            from sklearn.metrics import log_loss, roc_auc_score

            try:
                auc = roc_auc_score(y_val, y_proba)
                auc_scores.append(auc)
            except ValueError:
                pass

            # Log Loss
            ll = log_loss(y_val, y_proba)
            logloss_scores.append(ll)

        # 全データで最終モデルを学習
        self.train(X, y)

        return {
            "precision_at_1": np.mean(precision_at_1_scores) if precision_at_1_scores else None,
            "precision_at_3": np.mean(precision_at_3_scores) if precision_at_3_scores else None,
            "auc_roc": np.mean(auc_scores) if auc_scores else None,
            "log_loss": np.mean(logloss_scores) if logloss_scores else None,
        }

    def _precision_at_k(
        self, y_true: np.ndarray, y_proba: np.ndarray, k: int
    ) -> float:
        """Precision@Kを計算する

        Args:
            y_true: 正解ラベル
            y_proba: 予測確率
            k: 上位K件

        Returns:
            Precision@K
        """
        if len(y_true) < k:
            k = len(y_true)

        top_k_indices = np.argsort(y_proba)[::-1][:k]
        top_k_labels = y_true[top_k_indices]

        return np.sum(top_k_labels) / k

    def get_feature_importance(self) -> np.ndarray:
        """特徴量重要度を取得する

        Returns:
            特徴量重要度の配列
        """
        if self.model is None:
            raise ValueError("モデルが学習されていません")

        return self.model.feature_importances_
