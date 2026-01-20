# ML予測機能 実装計画

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** LightGBMによる3着以内予測機能を既存のanalyzeコマンドに統合する

**Architecture:** 特徴量生成(FeatureBuilder) → 学習(Trainer) → 推論(Predictor)の3層構成。analyzeコマンド実行時に毎回学習・推論を行う。

**Tech Stack:** LightGBM, scikit-learn, SQLAlchemy, Click

---

## Task 1: 依存関係の追加

**Files:**
- Modify: `pyproject.toml:10-16`

**Step 1: pyproject.tomlに依存関係を追加**

`pyproject.toml`の`dependencies`に以下を追加:

```toml
dependencies = [
    "sqlalchemy>=2.0",
    "requests>=2.28",
    "beautifulsoup4>=4.11",
    "lxml>=4.9",
    "click>=8.0",
    "lightgbm>=4.0.0",
    "scikit-learn>=1.3.0",
]
```

**Step 2: 依存関係をインストール**

Run: `pip install -e ".[dev]"`
Expected: Successfully installed lightgbm and scikit-learn

**Step 3: インストール確認**

Run: `python -c "import lightgbm; import sklearn; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add lightgbm and scikit-learn dependencies"
```

---

## Task 2: mlパッケージの作成と__init__.py

**Files:**
- Create: `keiba/ml/__init__.py`

**Step 1: ディレクトリとファイルを作成**

```python
"""機械学習予測モジュール

LightGBMを使用した3着以内予測機能を提供する。
"""

from keiba.ml.feature_builder import FeatureBuilder
from keiba.ml.predictor import Predictor
from keiba.ml.trainer import Trainer

__all__ = [
    "FeatureBuilder",
    "Predictor",
    "Trainer",
]
```

注: この時点ではimportエラーになるが、後続タスクで解消される。

**Step 2: Commit**

```bash
git add keiba/ml/__init__.py
git commit -m "feat(ml): create ml package skeleton"
```

---

## Task 3: FeatureBuilder - テスト作成

**Files:**
- Create: `tests/ml/__init__.py`
- Create: `tests/ml/test_feature_builder.py`

**Step 1: テストディレクトリを作成**

`tests/ml/__init__.py`:
```python
"""ML module tests"""
```

**Step 2: FeatureBuilderのテストを作成**

`tests/ml/test_feature_builder.py`:
```python
"""FeatureBuilderのテスト"""

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

        # 欠損値は-1で埋められる
        assert features["odds"] == -1
        assert features["popularity"] == -1
        assert features["past_results_score"] == -1
        assert features["win_rate"] == -1

    def test_get_feature_names(self):
        """特徴量名リスト取得のテスト"""
        builder = FeatureBuilder()
        names = builder.get_feature_names()

        assert len(names) == 19
        assert "odds" in names
        assert "past_results_score" in names
        assert "win_rate" in names
```

**Step 3: テスト実行（失敗確認）**

Run: `pytest tests/ml/test_feature_builder.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'keiba.ml.feature_builder'"

**Step 4: Commit**

```bash
git add tests/ml/
git commit -m "test(ml): add FeatureBuilder tests"
```

---

## Task 4: FeatureBuilder - 実装

**Files:**
- Create: `keiba/ml/feature_builder.py`

**Step 1: FeatureBuilderを実装**

```python
"""特徴量生成モジュール"""

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

    MISSING_VALUE = -1

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
```

**Step 2: テスト実行（成功確認）**

Run: `pytest tests/ml/test_feature_builder.py -v`
Expected: PASS (all 4 tests)

**Step 3: Commit**

```bash
git add keiba/ml/feature_builder.py
git commit -m "feat(ml): implement FeatureBuilder for 19 features"
```

---

## Task 5: Trainer - テスト作成

**Files:**
- Create: `tests/ml/test_trainer.py`

**Step 1: Trainerのテストを作成**

```python
"""Trainerのテスト"""

import numpy as np
import pytest

from keiba.ml.trainer import Trainer


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
```

**Step 2: テスト実行（失敗確認）**

Run: `pytest tests/ml/test_trainer.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'keiba.ml.trainer'"

**Step 3: Commit**

```bash
git add tests/ml/test_trainer.py
git commit -m "test(ml): add Trainer tests"
```

---

## Task 6: Trainer - 実装

**Files:**
- Create: `keiba/ml/trainer.py`

**Step 1: Trainerを実装**

```python
"""モデル学習モジュール"""

import warnings
from typing import Any

import lightgbm as lgb
import numpy as np
from sklearn.model_selection import StratifiedKFold


class Trainer:
    """LightGBMモデルの学習を行うクラス"""

    MIN_SAMPLES = 100  # 最低限必要なサンプル数

    def __init__(self):
        """初期化"""
        self.model: lgb.LGBMClassifier | None = None
        self._params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.9,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
            "n_estimators": 100,
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
```

**Step 2: テスト実行（成功確認）**

Run: `pytest tests/ml/test_trainer.py -v`
Expected: PASS (all 5 tests)

**Step 3: Commit**

```bash
git add keiba/ml/trainer.py
git commit -m "feat(ml): implement Trainer with LightGBM and CV evaluation"
```

---

## Task 7: Predictor - テスト作成

**Files:**
- Create: `tests/ml/test_predictor.py`

**Step 1: Predictorのテストを作成**

```python
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
```

**Step 2: テスト実行（失敗確認）**

Run: `pytest tests/ml/test_predictor.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'keiba.ml.predictor'"

**Step 3: Commit**

```bash
git add tests/ml/test_predictor.py
git commit -m "test(ml): add Predictor tests"
```

---

## Task 8: Predictor - 実装

**Files:**
- Create: `keiba/ml/predictor.py`

**Step 1: Predictorを実装**

```python
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
```

**Step 2: テスト実行（成功確認）**

Run: `pytest tests/ml/test_predictor.py -v`
Expected: PASS (all 4 tests)

**Step 3: Commit**

```bash
git add keiba/ml/predictor.py
git commit -m "feat(ml): implement Predictor for probability and ranking output"
```

---

## Task 9: mlパッケージの__init__.py更新とテスト

**Files:**
- Modify: `keiba/ml/__init__.py`

**Step 1: インポートエラーがないか確認**

Run: `python -c "from keiba.ml import FeatureBuilder, Trainer, Predictor; print('OK')"`
Expected: `OK`

**Step 2: 全mlテストを実行**

Run: `pytest tests/ml/ -v`
Expected: PASS (all 13 tests)

**Step 3: Commit**

```bash
git add keiba/ml/__init__.py
git commit -m "feat(ml): complete ml package with all components"
```

---

## Task 10: CLI統合 - テスト作成

**Files:**
- Modify: `tests/test_cli.py`

**Step 1: 既存のtest_cli.pyにML予測テストを追加**

`tests/test_cli.py`の末尾に追加:

```python
class TestAnalyzeWithML:
    """analyzeコマンドのML予測テスト"""

    def test_analyze_with_prediction_shows_ml_header(self, runner, sample_db):
        """ML予測ヘッダーが表示されるテスト"""
        result = runner.invoke(
            main,
            ["analyze", "--db", sample_db, "--date", "2024-01-06", "--venue", "中山"],
        )
        # ML予測ヘッダーが含まれる
        assert "【ML予測】" in result.output or "学習データ" in result.output

    def test_analyze_with_no_predict_flag(self, runner, sample_db):
        """--no-predictフラグでML予測をスキップ"""
        result = runner.invoke(
            main,
            ["analyze", "--db", sample_db, "--date", "2024-01-06", "--venue", "中山", "--no-predict"],
        )
        # ML予測ヘッダーが含まれない
        assert "【ML予測】" not in result.output

    def test_analyze_shows_probability_column(self, runner, sample_db):
        """確率列が表示されるテスト"""
        result = runner.invoke(
            main,
            ["analyze", "--db", sample_db, "--date", "2024-01-06", "--venue", "中山"],
        )
        # 確率列のヘッダーが含まれる
        assert "3着内確率" in result.output or "確率" in result.output
```

注: sample_db fixtureは既存のものを使用。テストデータが不足している場合はスキップする処理を追加する必要があるかもしれない。

**Step 2: テスト実行（失敗確認）**

Run: `pytest tests/test_cli.py::TestAnalyzeWithML -v`
Expected: FAIL（ML予測機能がまだ未実装のため）

**Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test(cli): add ML prediction integration tests"
```

---

## Task 11: CLI統合 - _build_training_data関数

**Files:**
- Modify: `keiba/cli.py`

**Step 1: 学習データ構築用のヘルパー関数を追加**

`keiba/cli.py`の`_get_horse_past_results`関数の後に追加:

```python
def _build_training_data(session, target_date: date) -> tuple[list[dict], list[int]]:
    """ML学習用のデータを構築する

    Args:
        session: SQLAlchemyセッション
        target_date: 対象レース日（この日より前のデータを使用）

    Returns:
        (特徴量リスト, ラベルリスト)のタプル
    """
    from keiba.analyzers.factors import (
        CourseFitFactor,
        Last3FFactor,
        PastResultsFactor,
        PedigreeFactor,
        PopularityFactor,
        RunningStyleFactor,
        TimeIndexFactor,
    )
    from keiba.ml.feature_builder import FeatureBuilder

    # 対象日より前のレースを取得
    past_races = (
        session.query(Race)
        .filter(Race.date < target_date)
        .order_by(Race.date.desc())
        .all()
    )

    if not past_races:
        return [], []

    feature_builder = FeatureBuilder()
    factors = {
        "past_results": PastResultsFactor(),
        "course_fit": CourseFitFactor(),
        "time_index": TimeIndexFactor(),
        "last_3f": Last3FFactor(),
        "popularity": PopularityFactor(),
        "pedigree": PedigreeFactor(),
        "running_style": RunningStyleFactor(),
    }

    features_list = []
    labels = []

    for race in past_races:
        results = (
            session.query(RaceResult)
            .filter(RaceResult.race_id == race.id)
            .all()
        )

        field_size = len(results)

        for result in results:
            # 中止（finish_position=0）は除外
            if result.finish_position == 0:
                continue

            # 過去成績を取得
            horse_past = _get_horse_past_results(session, result.horse_id)

            # 馬情報を取得
            horse = session.get(Horse, result.horse_id)

            # ファクタースコアを計算
            factor_scores = {
                "past_results": factors["past_results"].calculate(
                    result.horse_id, horse_past
                ),
                "course_fit": factors["course_fit"].calculate(
                    result.horse_id, horse_past,
                    target_surface=race.surface, target_distance=race.distance
                ),
                "time_index": factors["time_index"].calculate(
                    result.horse_id, horse_past,
                    target_surface=race.surface, target_distance=race.distance
                ),
                "last_3f": factors["last_3f"].calculate(result.horse_id, horse_past),
                "popularity": factors["popularity"].calculate(
                    result.horse_id, [],
                    odds=result.odds, popularity=result.popularity
                ),
                "pedigree": factors["pedigree"].calculate(
                    result.horse_id, [],
                    sire=horse.sire if horse else None,
                    dam_sire=horse.dam_sire if horse else None,
                    target_surface=race.surface,
                    target_distance=race.distance,
                ),
                "running_style": factors["running_style"].calculate(
                    result.horse_id, horse_past,
                    passing_order=result.passing_order,
                    course=race.course,
                    distance=race.distance,
                ),
            }

            # 派生特徴量を計算
            past_stats = _calculate_past_stats(horse_past, race.date)

            # 生データ
            race_result_data = {
                "horse_id": result.horse_id,
                "odds": result.odds,
                "popularity": result.popularity,
                "weight": result.weight,
                "weight_diff": result.weight_diff,
                "age": result.age,
                "impost": result.impost,
                "horse_number": result.horse_number,
            }

            features = feature_builder.build_features(
                race_result=race_result_data,
                factor_scores=factor_scores,
                field_size=field_size,
                past_stats=past_stats,
            )

            features_list.append(features)

            # ラベル: 3着以内=1, 4着以下=0
            label = 1 if result.finish_position <= 3 else 0
            labels.append(label)

    return features_list, labels


def _calculate_past_stats(past_results: list[dict], current_date: date) -> dict:
    """派生特徴量を計算する

    Args:
        past_results: 過去成績リスト
        current_date: 現在のレース日

    Returns:
        派生特徴量の辞書
    """
    if not past_results:
        return {
            "win_rate": None,
            "top3_rate": None,
            "avg_finish_position": None,
            "days_since_last_race": None,
        }

    total = len(past_results)
    wins = sum(1 for r in past_results if r.get("finish_position") == 1)
    top3 = sum(1 for r in past_results if r.get("finish_position", 99) <= 3)
    positions = [r.get("finish_position", 0) for r in past_results if r.get("finish_position", 0) > 0]

    # 前走からの日数
    days_since = None
    if past_results and past_results[0].get("race_date"):
        last_date = past_results[0]["race_date"]
        if hasattr(last_date, "date"):
            last_date = last_date.date()
        days_since = (current_date - last_date).days

    return {
        "win_rate": wins / total if total > 0 else None,
        "top3_rate": top3 / total if total > 0 else None,
        "avg_finish_position": sum(positions) / len(positions) if positions else None,
        "days_since_last_race": days_since,
    }
```

**Step 2: Commit**

```bash
git add keiba/cli.py
git commit -m "feat(cli): add _build_training_data helper for ML"
```

---

## Task 12: CLI統合 - analyzeコマンドの修正

**Files:**
- Modify: `keiba/cli.py`

**Step 1: analyzeコマンドに--no-predictオプションを追加**

`keiba/cli.py`の`analyze`コマンドを修正:

```python
@main.command()
@click.option("--db", required=True, type=click.Path(), help="DBファイルパス")
@click.option("--date", required=True, type=str, help="レース日付（YYYY-MM-DD）")
@click.option("--venue", required=True, type=str, help="競馬場名（例: 中山）")
@click.option("--race", type=int, default=None, help="レース番号（省略時は全レース）")
@click.option("--no-predict", is_flag=True, default=False, help="ML予測をスキップ")
def analyze(db: str, date: str, venue: str, race: int | None, no_predict: bool):
    """指定した日付・競馬場のレースを分析してスコアを表示"""
    from datetime import datetime as dt

    import numpy as np
    from sqlalchemy import select

    from keiba.analyzers.factors import (
        CourseFitFactor,
        Last3FFactor,
        PastResultsFactor,
        PedigreeFactor,
        PopularityFactor,
        RunningStyleFactor,
        TimeIndexFactor,
    )
    from keiba.analyzers.score_calculator import ScoreCalculator
    from keiba.ml.feature_builder import FeatureBuilder
    from keiba.ml.predictor import Predictor
    from keiba.ml.trainer import Trainer

    # 日付をパース
    try:
        race_date = dt.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        click.echo(f"日付形式が不正です: {date}（YYYY-MM-DD形式で指定してください）")
        return

    click.echo(f"分析開始: {race_date} {venue}")
    click.echo(f"データベース: {db}")

    # DBに接続
    engine = get_engine(db)

    with get_session(engine) as session:
        # ML予測の準備（--no-predictでない場合）
        predictor = None
        training_count = 0

        if not no_predict:
            click.echo("")
            click.echo("ML予測モデルを学習中...")

            features_list, labels = _build_training_data(session, race_date)
            training_count = len(features_list)

            if training_count >= 100:
                feature_builder = FeatureBuilder()
                feature_names = feature_builder.get_feature_names()

                X = np.array([[f[name] for name in feature_names] for f in features_list])
                y = np.array(labels)

                trainer = Trainer()
                metrics = trainer.train_with_cv(X, y, n_splits=5)

                click.echo(f"学習完了: {training_count}サンプル")
                click.echo(f"  Precision@1: {metrics['precision_at_1']:.1%}" if metrics['precision_at_1'] else "  Precision@1: N/A")
                click.echo(f"  Precision@3: {metrics['precision_at_3']:.1%}" if metrics['precision_at_3'] else "  Precision@3: N/A")

                predictor = Predictor(trainer.model)
            else:
                click.echo(f"学習データ不足（{training_count}サンプル）: ML予測をスキップ")

        click.echo("")

        # 対象レースを取得
        stmt = select(Race).where(Race.date == race_date, Race.course == venue)
        if race is not None:
            stmt = stmt.where(Race.race_number == race)
        stmt = stmt.order_by(Race.race_number)

        races = session.execute(stmt).scalars().all()

        if not races:
            click.echo(f"レースが見つかりません: {race_date} {venue}")
            return

        # 各レースを分析
        for target_race in races:
            _analyze_race_with_ml(session, target_race, predictor, training_count)
```

**Step 2: _analyze_race_with_ml関数を追加**

既存の`_analyze_race`を拡張した新関数:

```python
def _analyze_race_with_ml(
    session, race: Race, predictor, training_count: int
) -> None:
    """レースを分析してスコアとML予測を表示する

    Args:
        session: SQLAlchemyセッション
        race: レースオブジェクト
        predictor: Predictorインスタンス（Noneの場合はML予測スキップ）
        training_count: 学習データ数
    """
    import numpy as np

    from keiba.analyzers.factors import (
        CourseFitFactor,
        Last3FFactor,
        PastResultsFactor,
        PedigreeFactor,
        PopularityFactor,
        RunningStyleFactor,
        TimeIndexFactor,
    )
    from keiba.analyzers.score_calculator import ScoreCalculator
    from keiba.ml.feature_builder import FeatureBuilder

    click.echo("=" * 80)
    click.echo(f"{race.date} {race.course} {race.race_number}R {race.name} {race.surface}{race.distance}m")

    if predictor:
        click.echo(f"【ML予測】学習データ: {training_count:,}件")

    click.echo("=" * 80)

    # レース結果を取得
    results = (
        session.query(RaceResult)
        .filter(RaceResult.race_id == race.id)
        .all()
    )

    if not results:
        click.echo("出走馬情報がありません")
        click.echo("")
        return

    # 各馬のスコアを計算
    calculator = ScoreCalculator()
    factors = {
        "past_results": PastResultsFactor(),
        "course_fit": CourseFitFactor(),
        "time_index": TimeIndexFactor(),
        "last_3f": Last3FFactor(),
        "popularity": PopularityFactor(),
        "pedigree": PedigreeFactor(),
        "running_style": RunningStyleFactor(),
    }
    feature_builder = FeatureBuilder()

    scores = []
    ml_features = []
    horse_ids = []

    for result in results:
        # 過去成績を取得
        past_results = _get_horse_past_results(session, result.horse_id)

        # 馬情報を取得
        horse = session.get(Horse, result.horse_id)

        # 各Factorスコアを計算
        factor_scores = {
            "past_results": factors["past_results"].calculate(
                result.horse_id, past_results
            ),
            "course_fit": factors["course_fit"].calculate(
                result.horse_id,
                past_results,
                target_surface=race.surface,
                target_distance=race.distance,
            ),
            "time_index": factors["time_index"].calculate(
                result.horse_id,
                past_results,
                target_surface=race.surface,
                target_distance=race.distance,
            ),
            "last_3f": factors["last_3f"].calculate(result.horse_id, past_results),
            "popularity": factors["popularity"].calculate(
                result.horse_id,
                [],
                odds=result.odds,
                popularity=result.popularity,
            ),
            "pedigree": factors["pedigree"].calculate(
                result.horse_id, [],
                sire=horse.sire if horse else None,
                dam_sire=horse.dam_sire if horse else None,
                target_surface=race.surface,
                target_distance=race.distance,
            ),
            "running_style": factors["running_style"].calculate(
                result.horse_id, past_results,
                passing_order=result.passing_order,
                course=race.course,
                distance=race.distance,
            ),
        }

        total_score = calculator.calculate_total(factor_scores)

        # ML用特徴量を構築
        if predictor:
            past_stats = _calculate_past_stats(past_results, race.date)
            race_result_data = {
                "horse_id": result.horse_id,
                "odds": result.odds,
                "popularity": result.popularity,
                "weight": result.weight,
                "weight_diff": result.weight_diff,
                "age": result.age,
                "impost": result.impost,
                "horse_number": result.horse_number,
            }
            features = feature_builder.build_features(
                race_result=race_result_data,
                factor_scores=factor_scores,
                field_size=len(results),
                past_stats=past_stats,
            )
            feature_names = feature_builder.get_feature_names()
            ml_features.append([features[name] for name in feature_names])
            horse_ids.append(result.horse_id)

        scores.append(
            {
                "horse_id": result.horse_id,
                "horse_number": result.horse_number,
                "horse_name": result.horse.name if result.horse else "不明",
                "total": total_score,
                "past_results": factor_scores["past_results"],
                "course_fit": factor_scores["course_fit"],
                "time_index": factor_scores["time_index"],
                "last_3f": factor_scores["last_3f"],
                "popularity": factor_scores["popularity"],
                "probability": None,  # 後で設定
                "ml_rank": None,  # 後で設定
            }
        )

    # ML予測を実行
    if predictor and ml_features:
        X = np.array(ml_features)
        predictions = predictor.predict_with_ranking(X, horse_ids)

        # 予測結果をscoresにマージ
        pred_map = {p["horse_id"]: p for p in predictions}
        for score in scores:
            pred = pred_map.get(score["horse_id"])
            if pred:
                score["probability"] = pred["probability"]
                score["ml_rank"] = pred["rank"]

    # ML予測ランキング順でソート（予測がある場合）、なければ総合スコア順
    if predictor:
        scores.sort(key=lambda x: x["ml_rank"] if x["ml_rank"] else 999)
    else:
        scores.sort(key=lambda x: x["total"] or 0, reverse=True)

    # 表形式で出力
    _print_score_table_with_ml(scores, predictor is not None)
    click.echo("")


def _print_score_table_with_ml(scores: list[dict], with_ml: bool) -> None:
    """スコアテーブルを表示する（ML予測付き）

    Args:
        scores: スコアリスト
        with_ml: ML予測を含むかどうか
    """
    if with_ml:
        # ML予測あり
        click.echo(
            f"{'予測':^4} | {'馬番':^4} | {'馬名':^12} | {'3着内確率':^8} | "
            f"{'総合':^6} | {'過去':^6} | {'適性':^6} | {'タイム':^6} | {'上がり':^6} | {'人気':^6}"
        )
        click.echo("-" * 100)

        for score in scores:
            rank = f"{score['ml_rank']}" if score["ml_rank"] else "-"
            prob = f"{score['probability']:.1%}" if score["probability"] is not None else "-"
            total = f"{score['total']:.1f}" if score["total"] is not None else "-"
            past = f"{score['past_results']:.1f}" if score["past_results"] is not None else "-"
            course = f"{score['course_fit']:.1f}" if score["course_fit"] is not None else "-"
            time_idx = f"{score['time_index']:.1f}" if score["time_index"] is not None else "-"
            last_3f = f"{score['last_3f']:.1f}" if score["last_3f"] is not None else "-"
            pop = f"{score['popularity']:.1f}" if score["popularity"] is not None else "-"

            horse_name = score["horse_name"][:12] if len(score["horse_name"]) > 12 else score["horse_name"]

            click.echo(
                f"{rank:^4} | {score['horse_number']:^4} | {horse_name:^12} | "
                f"{prob:^8} | {total:^6} | {past:^6} | {course:^6} | {time_idx:^6} | {last_3f:^6} | {pop:^6}"
            )

        # 確率50%以上の馬数
        high_prob_count = sum(1 for s in scores if s["probability"] and s["probability"] >= 0.5)
        if high_prob_count > 0:
            click.echo(f"\n※ 確率50%以上: {high_prob_count}頭")
    else:
        # 従来のスコアのみ表示
        _print_score_table(scores)
```

**Step 3: Commit**

```bash
git add keiba/cli.py
git commit -m "feat(cli): integrate ML prediction into analyze command"
```

---

## Task 13: 統合テスト

**Files:**
- Modify: `tests/test_cli.py` (if needed)

**Step 1: 全テストを実行**

Run: `pytest tests/ -v --cov=keiba --cov-report=term-missing`
Expected: PASS with 80%+ coverage

**Step 2: 手動テスト（実データがある場合）**

Run: `keiba analyze --db keiba.db --date 2024-01-06 --venue 中山`
Expected: ML予測付きの結果が表示される

**Step 3: --no-predictオプションのテスト**

Run: `keiba analyze --db keiba.db --date 2024-01-06 --venue 中山 --no-predict`
Expected: 従来のスコアのみ表示

**Step 4: Commit**

```bash
git add -A
git commit -m "test: verify ML prediction integration"
```

---

## Task 14: ドキュメント更新

**Files:**
- Modify: `README.md`

**Step 1: README.mdにML予測機能の説明を追加**

「使い方」セクションに追加:

```markdown
### レース分析（ML予測付き）

```bash
# ML予測付きでレース分析
keiba analyze --db keiba.db --date 2024-01-06 --venue 中山

# ML予測なしで分析（従来の動作）
keiba analyze --db keiba.db --date 2024-01-06 --venue 中山 --no-predict
```

ML予測機能は、過去のレース結果を学習データとしてLightGBMモデルを構築し、
各馬の「3着以内に入る確率」を予測します。

**必要条件:**
- 対象レース日より前に100レース以上のデータが必要
- データが不足している場合はML予測がスキップされます
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add ML prediction feature documentation"
```

---

## 完了確認

**全テスト実行:**
```bash
pytest tests/ -v --cov=keiba --cov-report=term-missing
```

**期待結果:**
- 全テストがPASS
- カバレッジ80%以上

**動作確認:**
```bash
keiba analyze --db keiba.db --date 2024-01-06 --venue 中山
```

**期待される出力:**
```
分析開始: 2024-01-06 中山
データベース: keiba.db

ML予測モデルを学習中...
学習完了: 2,345サンプル
  Precision@1: 32.5%
  Precision@3: 58.2%

================================================================================
2024-01-06 中山 11R 有馬記念 芝2500m
【ML予測】学習データ: 2,345件
================================================================================
予測 | 馬番 |     馬名     | 3着内確率 |  総合  |  過去  |  適性  | タイム | 上がり |  人気
----------------------------------------------------------------------------------------------------
  1  |   5  | イクイノックス |   78.2%  |  85.2  |  90.0  |  80.0  |  82.0  |  88.0  |  86.0
  2  |   3  | ドウデュース   |   65.4%  |  78.5  |  75.0  |  82.0  |  78.0  |  80.0  |  77.5
...

※ 確率50%以上: 3頭
```
