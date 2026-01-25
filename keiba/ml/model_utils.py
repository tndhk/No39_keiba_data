"""Model utility functions."""

from pathlib import Path


def find_latest_model(model_dir: str) -> str | None:
    """最新の.joblibファイルを検索.

    Args:
        model_dir: モデルファイルが格納されているディレクトリパス

    Returns:
        最新の.joblibファイルの絶対パス。ファイルが見つからない場合はNone。
    """
    model_path = Path(model_dir).resolve()

    # ディレクトリの存在確認
    if not model_path.exists() or not model_path.is_dir():
        return None

    try:
        joblib_files = list(model_path.glob("*.joblib"))
        if not joblib_files:
            return None
        return str(max(joblib_files, key=lambda p: p.stat().st_mtime))
    except (OSError, ValueError):
        return None
