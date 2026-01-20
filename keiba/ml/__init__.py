"""機械学習予測モジュール

LightGBMを使用した3着以内予測機能を提供する。
"""

from keiba.ml.feature_builder import FeatureBuilder


def __getattr__(name: str):
    """遅延インポート（LightGBM依存モジュール用）"""
    if name == "Predictor":
        from keiba.ml.predictor import Predictor

        return Predictor
    if name == "Trainer":
        from keiba.ml.trainer import Trainer

        return Trainer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "FeatureBuilder",
    "Predictor",
    "Trainer",
]
