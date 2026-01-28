"""モデルパス解決ユーティリティ"""

from keiba.ml.model_utils import find_latest_model


def resolve_model_path(model: str | None, models_dir: str = "data/models") -> str | None:
    """モデルパスを解決する

    Args:
        model: 指定されたモデルパス（Noneの場合は自動検索）
        models_dir: モデルディレクトリ（デフォルト: "data/models"）

    Returns:
        解決されたモデルパス（見つからない場合はNone）
    """
    if model is not None:
        return model
    return find_latest_model(models_dir)
