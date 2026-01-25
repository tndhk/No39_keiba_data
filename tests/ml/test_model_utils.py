"""Tests for model_utils module."""

import pytest
from pathlib import Path


class TestFindLatestModel:
    """Tests for find_latest_model function."""

    def test_find_latest_model_returns_newest(self, tmp_path: Path) -> None:
        """複数モデルがある場合、最新（mtime）を返す"""
        from keiba.ml.model_utils import find_latest_model
        import time

        # Create multiple model files with different mtimes
        old_model = tmp_path / "model_old.joblib"
        old_model.write_text("old")

        # Ensure different mtime
        time.sleep(0.01)

        new_model = tmp_path / "model_new.joblib"
        new_model.write_text("new")

        result = find_latest_model(str(tmp_path))

        assert result == str(new_model)

    def test_find_latest_model_returns_none_if_no_models(
        self, tmp_path: Path
    ) -> None:
        """.joblibファイルがない場合Noneを返す"""
        from keiba.ml.model_utils import find_latest_model

        # Create a non-joblib file
        other_file = tmp_path / "readme.txt"
        other_file.write_text("not a model")

        result = find_latest_model(str(tmp_path))

        assert result is None

    def test_find_latest_model_returns_none_if_dir_missing(
        self, tmp_path: Path
    ) -> None:
        """ディレクトリが存在しない場合Noneを返す"""
        from keiba.ml.model_utils import find_latest_model

        non_existent_dir = tmp_path / "does_not_exist"

        result = find_latest_model(str(non_existent_dir))

        assert result is None
