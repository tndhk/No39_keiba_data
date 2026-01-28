"""model_resolver のユニットテスト"""

from unittest.mock import patch

from keiba.cli.utils.model_resolver import resolve_model_path


class TestResolveModelPath:
    """resolve_model_path 関数のテスト"""

    def test_resolve_model_path_explicit(self):
        """モデルパス明示指定時はそのまま返す"""
        result = resolve_model_path("data/models/my_model.joblib")
        assert result == "data/models/my_model.joblib"

    @patch("keiba.cli.utils.model_resolver.find_latest_model")
    def test_resolve_model_path_auto_detect(self, mock_find):
        """None時は自動検索で最新モデルを返す"""
        mock_find.return_value = "/abs/path/to/model.joblib"

        result = resolve_model_path(None)

        assert result == "/abs/path/to/model.joblib"
        mock_find.assert_called_once_with("data/models")

    @patch("keiba.cli.utils.model_resolver.find_latest_model")
    def test_resolve_model_path_custom_dir(self, mock_find):
        """カスタムディレクトリ指定時はそのディレクトリで検索する"""
        mock_find.return_value = "/custom/dir/model.joblib"

        result = resolve_model_path(None, models_dir="/custom/dir")

        assert result == "/custom/dir/model.joblib"
        mock_find.assert_called_once_with("/custom/dir")

    @patch("keiba.cli.utils.model_resolver.find_latest_model")
    def test_resolve_model_path_no_model_found(self, mock_find):
        """モデル未検出時はNoneを返す"""
        mock_find.return_value = None

        result = resolve_model_path(None)

        assert result is None
        mock_find.assert_called_once_with("data/models")

    def test_resolve_model_path_explicit_ignores_auto_detect(self):
        """明示指定時はfind_latest_modelが呼ばれない"""
        with patch("keiba.cli.utils.model_resolver.find_latest_model") as mock_find:
            result = resolve_model_path("explicit/path.joblib")

            assert result == "explicit/path.joblib"
            mock_find.assert_not_called()
