"""Tests for predict-day command in keiba.cli module."""

import os
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from click.testing import CliRunner

from keiba.cli import main


# LightGBMが使用可能か確認
try:
    import lightgbm  # noqa: F401

    LIGHTGBM_AVAILABLE = True
except (ImportError, OSError):
    LIGHTGBM_AVAILABLE = False

skip_without_lightgbm = pytest.mark.skipif(
    not LIGHTGBM_AVAILABLE,
    reason="LightGBM is not available (missing libomp or other dependency)",
)


class TestVenueCodeMap:
    """VENUE_CODE_MAP定数のテスト"""

    def test_venue_code_map_exists(self):
        """VENUE_CODE_MAPが定義されている"""
        from keiba.constants import VENUE_CODE_MAP

        assert isinstance(VENUE_CODE_MAP, dict)

    def test_venue_code_map_has_all_jra_venues(self):
        """VENUE_CODE_MAPに全JRA競馬場が含まれる"""
        from keiba.constants import VENUE_CODE_MAP

        expected_venues = [
            "札幌",
            "函館",
            "福島",
            "新潟",
            "東京",
            "中山",
            "中京",
            "京都",
            "阪神",
            "小倉",
        ]
        for venue in expected_venues:
            assert venue in VENUE_CODE_MAP

    def test_venue_code_map_values_are_two_digit_strings(self):
        """競馬場コードは2桁の文字列"""
        from keiba.constants import VENUE_CODE_MAP

        for venue, code in VENUE_CODE_MAP.items():
            assert isinstance(code, str)
            assert len(code) == 2
            assert code.isdigit()

    def test_nakayama_code_is_06(self):
        """中山の競馬場コードは06"""
        from keiba.constants import VENUE_CODE_MAP

        assert VENUE_CODE_MAP["中山"] == "06"

    def test_tokyo_code_is_05(self):
        """東京の競馬場コードは05"""
        from keiba.constants import VENUE_CODE_MAP

        assert VENUE_CODE_MAP["東京"] == "05"


class TestGetRaceIdsForVenue:
    """_get_race_ids_for_venue関数のテスト"""

    def test_filters_race_ids_by_venue_code(self):
        """指定競馬場のレースIDのみフィルタリングする"""
        from keiba.cli.commands.predict import _get_race_ids_for_venue

        race_urls = [
            "https://db.netkeiba.com/race/202606010801/",  # 中山 (06)
            "https://db.netkeiba.com/race/202606010802/",  # 中山 (06)
            "https://db.netkeiba.com/race/202605010801/",  # 東京 (05)
            "https://db.netkeiba.com/race/202609010801/",  # 阪神 (09)
        ]

        result = _get_race_ids_for_venue(race_urls, "06")

        assert len(result) == 2
        assert "202606010801" in result
        assert "202606010802" in result

    def test_returns_empty_list_when_no_match(self):
        """該当競馬場のレースがない場合は空リストを返す"""
        from keiba.cli.commands.predict import _get_race_ids_for_venue

        race_urls = [
            "https://db.netkeiba.com/race/202605010801/",  # 東京 (05)
            "https://db.netkeiba.com/race/202609010801/",  # 阪神 (09)
        ]

        result = _get_race_ids_for_venue(race_urls, "06")

        assert result == []

    def test_handles_empty_input(self):
        """空リスト入力時は空リストを返す"""
        from keiba.cli.commands.predict import _get_race_ids_for_venue

        result = _get_race_ids_for_venue([], "06")

        assert result == []

    def test_extracts_race_id_from_url(self):
        """URLからレースIDを正しく抽出する"""
        from keiba.cli.commands.predict import _get_race_ids_for_venue

        race_urls = [
            "https://db.netkeiba.com/race/202606010812/",  # trailing slash
        ]

        result = _get_race_ids_for_venue(race_urls, "06")

        assert result == ["202606010812"]


class TestSavePredictionsMarkdown:
    """_save_predictions_markdown関数のテスト"""

    def test_creates_markdown_file(self, tmp_path):
        """Markdownファイルが作成される"""
        from keiba.cli.formatters.markdown import save_predictions_markdown

        predictions_data = [
            {
                "race_number": 1,
                "race_name": "テストレース",
                "predictions": [
                    {
                        "rank": 1,
                        "horse_number": 5,
                        "horse_name": "テストホース",
                        "ml_probability": 0.65,
                        "total_score": 75.5,
                    }
                ],
            }
        ]

        output_dir = tmp_path / "predictions"
        output_dir.mkdir(parents=True)

        filepath = save_predictions_markdown(
            predictions_data,
            date_str="2026-01-24",
            venue="中山",
            output_dir=str(output_dir),
        )

        # ファイルが存在することを確認
        assert Path(filepath).exists()
        assert filepath.endswith("2026-01-24-nakayama.md")

    def test_markdown_contains_race_info(self, tmp_path):
        """Markdownファイルにレース情報が含まれる"""
        from keiba.cli.formatters.markdown import save_predictions_markdown

        predictions_data = [
            {
                "race_number": 12,
                "race_name": "第65回京成杯(G3)",
                "surface": "芝",
                "distance": 2000,
                "predictions": [
                    {
                        "rank": 1,
                        "horse_number": 5,
                        "horse_name": "テストホース",
                        "ml_probability": 0.65,
                        "total_score": 75.5,
                    }
                ],
            }
        ]

        output_dir = tmp_path / "predictions"
        output_dir.mkdir(parents=True)

        filepath = save_predictions_markdown(
            predictions_data,
            date_str="2026-01-24",
            venue="中山",
            output_dir=str(output_dir),
        )

        content = Path(filepath).read_text()
        assert "第65回京成杯" in content
        assert "12R" in content


class TestPredictDayCommand:
    """predict-dayコマンドのテスト"""

    def test_predict_day_command_registered(self):
        """predict-dayコマンドが登録されている"""
        assert "predict-day" in main.commands

    def test_predict_day_help(self):
        """predict-day --helpが正常に動作する"""
        runner = CliRunner()
        result = runner.invoke(main, ["predict-day", "--help"])
        assert result.exit_code == 0
        assert "--date" in result.output
        assert "--venue" in result.output
        assert "--db" in result.output
        assert "--no-ml" in result.output

    def test_predict_day_requires_db(self):
        """predict-dayは--dbオプションを必須とする"""
        runner = CliRunner()
        result = runner.invoke(
            main, ["predict-day", "--date", "2026-01-24", "--venue", "中山"]
        )
        assert result.exit_code != 0
        assert "db" in result.output.lower() or "missing" in result.output.lower()

    def test_predict_day_requires_venue(self):
        """predict-dayは--venueオプションを必須とする"""
        runner = CliRunner()
        result = runner.invoke(
            main, ["predict-day", "--date", "2026-01-24", "--db", "test.db"]
        )
        assert result.exit_code != 0
        assert "venue" in result.output.lower() or "missing" in result.output.lower()

    def test_predict_day_date_defaults_to_today(self):
        """--dateを省略すると今日の日付が使用される"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            # コマンド実行（DBがないのでエラー終了するが、日付のデフォルト確認）
            result = runner.invoke(
                main, ["predict-day", "--venue", "中山", "--db", "test.db"]
            )
            # 日付形式エラーではなく、DB関連のエラーになること
            assert "日付形式が不正" not in result.output

    def test_predict_day_invalid_venue_shows_error(self):
        """無効な競馬場名はエラーになる"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "predict-day",
                    "--date",
                    "2026-01-24",
                    "--venue",
                    "無効な競馬場",
                    "--db",
                    "test.db",
                ],
            )
            assert result.exit_code != 0
            assert "競馬場" in result.output or "無効" in result.output

    def test_predict_day_invalid_date_format(self):
        """無効な日付形式はエラーになる"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "predict-day",
                    "--date",
                    "2026/01/24",  # Invalid format
                    "--venue",
                    "中山",
                    "--db",
                    "test.db",
                ],
            )
            assert result.exit_code != 0
            assert "日付形式" in result.output


class TestPredictDayExecution:
    """predict-dayコマンドの実行テスト"""

    @patch("keiba.cli.commands.predict.ShutubaScraper")
    @patch("keiba.cli.commands.predict.RaceListScraper")
    @patch("keiba.cli.commands.predict.get_session")
    @patch("keiba.cli.commands.predict.get_engine")
    def test_predict_day_fetches_race_list(
        self,
        mock_get_engine,
        mock_get_session,
        mock_race_list_scraper,
        mock_shutuba_scraper,
    ):
        """predict-dayはRaceListScraperでレース一覧を取得する"""
        # Setup mocks
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_scraper = MagicMock()
        mock_scraper.fetch_race_urls.return_value = []
        mock_race_list_scraper.return_value = mock_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "predict-day",
                    "--date",
                    "2026-01-24",
                    "--venue",
                    "中山",
                    "--db",
                    "test.db",
                ],
            )

        # RaceListScraperが呼ばれたことを確認
        mock_scraper.fetch_race_urls.assert_called_once_with(2026, 1, 24, jra_only=True)

    @patch("keiba.cli.commands.predict.PredictionService")
    @patch("keiba.cli.commands.predict.ShutubaScraper")
    @patch("keiba.cli.commands.predict.RaceListScraper")
    @patch("keiba.cli.commands.predict.get_session")
    @patch("keiba.cli.commands.predict.get_engine")
    def test_predict_day_filters_by_venue(
        self,
        mock_get_engine,
        mock_get_session,
        mock_race_list_scraper,
        mock_shutuba_scraper,
        mock_prediction_service,
    ):
        """predict-dayは指定競馬場のレースのみ処理する"""
        # Setup mocks
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Mock race list with mixed venues
        mock_list_scraper = MagicMock()
        mock_list_scraper.fetch_race_urls.return_value = [
            "https://db.netkeiba.com/race/202606010801/",  # 中山
            "https://db.netkeiba.com/race/202606010802/",  # 中山
            "https://db.netkeiba.com/race/202605010801/",  # 東京
        ]
        mock_race_list_scraper.return_value = mock_list_scraper

        # Mock shutuba scraper - create a proper mock for each fetch_shutuba call
        mock_shutuba = MagicMock()
        mock_shutuba_data = MagicMock(
            race_id="202606010801",
            race_name="テストレース",
            race_number=1,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月24日",
            entries=(),
        )
        mock_shutuba.fetch_shutuba.return_value = mock_shutuba_data
        mock_shutuba_scraper.return_value = mock_shutuba

        # Mock prediction service
        mock_service = MagicMock()
        mock_service.predict_from_shutuba.return_value = []
        mock_prediction_service.return_value = mock_service

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "predict-day",
                    "--date",
                    "2026-01-24",
                    "--venue",
                    "中山",
                    "--db",
                    "test.db",
                ],
            )

        # 中山（06）のレースのみ処理されることを確認（2レース）
        assert mock_shutuba.fetch_shutuba.call_count == 2

    @patch("keiba.cli.commands.predict.save_predictions_markdown")
    @patch("keiba.cli.commands.predict.PredictionService")
    @patch("keiba.cli.commands.predict.ShutubaScraper")
    @patch("keiba.cli.commands.predict.RaceListScraper")
    @patch("keiba.cli.commands.predict.get_session")
    @patch("keiba.cli.commands.predict.get_engine")
    def test_predict_day_saves_markdown(
        self,
        mock_get_engine,
        mock_get_session,
        mock_race_list_scraper,
        mock_shutuba_scraper,
        mock_prediction_service,
        mock_save_markdown,
    ):
        """predict-dayは結果をMarkdownファイルに保存する"""
        # Setup mocks
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_list_scraper = MagicMock()
        mock_list_scraper.fetch_race_urls.return_value = [
            "https://db.netkeiba.com/race/202606010801/",
        ]
        mock_race_list_scraper.return_value = mock_list_scraper

        mock_shutuba = MagicMock()
        mock_shutuba.fetch_shutuba.return_value = MagicMock(
            race_id="202606010801",
            race_name="テストレース",
            race_number=1,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月24日",
            entries=(),
        )
        mock_shutuba_scraper.return_value = mock_shutuba

        mock_service = MagicMock()
        mock_service.predict_from_shutuba.return_value = []
        mock_prediction_service.return_value = mock_service

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "predict-day",
                    "--date",
                    "2026-01-24",
                    "--venue",
                    "中山",
                    "--db",
                    "test.db",
                ],
            )

        # Markdownファイル保存が呼ばれたことを確認
        mock_save_markdown.assert_called_once()
        call_args = mock_save_markdown.call_args
        assert call_args.kwargs["date_str"] == "2026-01-24"
        assert call_args.kwargs["venue"] == "中山"

    @patch("keiba.cli.commands.predict.save_predictions_markdown")
    @patch("keiba.cli.commands.predict.PredictionService")
    @patch("keiba.cli.commands.predict.ShutubaScraper")
    @patch("keiba.cli.commands.predict.RaceListScraper")
    @patch("keiba.cli.commands.predict.get_session")
    @patch("keiba.cli.commands.predict.get_engine")
    def test_predict_day_shows_summary(
        self,
        mock_get_engine,
        mock_get_session,
        mock_race_list_scraper,
        mock_shutuba_scraper,
        mock_prediction_service,
        mock_save_markdown,
    ):
        """predict-dayはコンソールにサマリーを表示する"""
        # Setup mocks
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_list_scraper = MagicMock()
        mock_list_scraper.fetch_race_urls.return_value = [
            "https://db.netkeiba.com/race/202606010801/",
        ]
        mock_race_list_scraper.return_value = mock_list_scraper

        mock_shutuba = MagicMock()
        mock_shutuba.fetch_shutuba.return_value = MagicMock(
            race_id="202606010801",
            race_name="テストレース",
            race_number=1,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月24日",
            entries=(),
        )
        mock_shutuba_scraper.return_value = mock_shutuba

        # Mock prediction with high probability horse
        mock_service = MagicMock()
        mock_prediction = MagicMock()
        mock_prediction.rank = 1
        mock_prediction.horse_number = 5
        mock_prediction.horse_name = "テストホース"
        mock_prediction.ml_probability = 0.65
        mock_prediction.total_score = 75.5
        mock_service.predict_from_shutuba.return_value = [mock_prediction]
        mock_prediction_service.return_value = mock_service

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "predict-day",
                    "--date",
                    "2026-01-24",
                    "--venue",
                    "中山",
                    "--db",
                    "test.db",
                ],
            )

        # サマリーがコンソールに出力されることを確認
        assert "テストレース" in result.output or "注目馬" in result.output


class TestPredictDayNoMl:
    """predict-day --no-mlオプションのテスト"""

    @patch("keiba.cli.commands.predict.save_predictions_markdown")
    @patch("keiba.cli.commands.predict.PredictionService")
    @patch("keiba.cli.commands.predict.ShutubaScraper")
    @patch("keiba.cli.commands.predict.RaceListScraper")
    @patch("keiba.cli.commands.predict.get_session")
    @patch("keiba.cli.commands.predict.get_engine")
    def test_predict_day_with_no_ml_skips_ml_prediction(
        self,
        mock_get_engine,
        mock_get_session,
        mock_race_list_scraper,
        mock_shutuba_scraper,
        mock_prediction_service,
        mock_save_markdown,
    ):
        """--no-mlオプションでML予測をスキップする"""
        # Setup mocks
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_list_scraper = MagicMock()
        mock_list_scraper.fetch_race_urls.return_value = [
            "https://db.netkeiba.com/race/202606010801/",
        ]
        mock_race_list_scraper.return_value = mock_list_scraper

        mock_shutuba = MagicMock()
        mock_shutuba.fetch_shutuba.return_value = MagicMock(
            race_id="202606010801",
            race_name="テストレース",
            race_number=1,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月24日",
            entries=(),
        )
        mock_shutuba_scraper.return_value = mock_shutuba

        mock_service = MagicMock()
        mock_service.predict_from_shutuba.return_value = []
        mock_prediction_service.return_value = mock_service

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "predict-day",
                    "--date",
                    "2026-01-24",
                    "--venue",
                    "中山",
                    "--db",
                    "test.db",
                    "--no-ml",
                ],
            )

        # PredictionServiceがmodel_path=Noneで初期化されることを確認
        call_kwargs = mock_prediction_service.call_args.kwargs
        assert call_kwargs.get("model_path") is None


class TestPredictDayModelAutoDetection:
    """predict-dayコマンドのモデル自動検出テスト"""

    @patch("keiba.cli.commands.predict.find_latest_model")
    @patch("keiba.cli.commands.predict.save_predictions_markdown")
    @patch("keiba.cli.commands.predict.PredictionService")
    @patch("keiba.cli.commands.predict.ShutubaScraper")
    @patch("keiba.cli.commands.predict.RaceListScraper")
    @patch("keiba.cli.commands.predict.get_session")
    @patch("keiba.cli.commands.predict.get_engine")
    def test_predict_day_uses_model_if_exists(
        self,
        mock_get_engine,
        mock_get_session,
        mock_race_list_scraper,
        mock_shutuba_scraper,
        mock_prediction_service,
        mock_save_markdown,
        mock_find_latest_model,
    ):
        """モデルファイルがある場合はそのパスを使用する"""
        # Setup mocks
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_list_scraper = MagicMock()
        mock_list_scraper.fetch_race_urls.return_value = [
            "https://db.netkeiba.com/race/202606010801/",
        ]
        mock_race_list_scraper.return_value = mock_list_scraper

        mock_shutuba = MagicMock()
        mock_shutuba.fetch_shutuba.return_value = MagicMock(
            race_id="202606010801",
            race_name="テストレース",
            race_number=1,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月24日",
            entries=(),
        )
        mock_shutuba_scraper.return_value = mock_shutuba

        mock_service = MagicMock()
        mock_service.predict_from_shutuba.return_value = []
        mock_prediction_service.return_value = mock_service

        # モデルパスが見つかるように設定
        mock_find_latest_model.return_value = "/path/to/data/models/model.joblib"

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "predict-day",
                    "--date",
                    "2026-01-24",
                    "--venue",
                    "中山",
                    "--db",
                    "data/test.db",
                ],
            )

        # PredictionServiceがモデルパスを持って初期化されることを確認
        call_kwargs = mock_prediction_service.call_args.kwargs
        assert call_kwargs.get("model_path") == "/path/to/data/models/model.joblib"

    @patch("keiba.cli.commands.predict.find_latest_model")
    @patch("keiba.cli.commands.predict.save_predictions_markdown")
    @patch("keiba.cli.commands.predict.PredictionService")
    @patch("keiba.cli.commands.predict.ShutubaScraper")
    @patch("keiba.cli.commands.predict.RaceListScraper")
    @patch("keiba.cli.commands.predict.get_session")
    @patch("keiba.cli.commands.predict.get_engine")
    def test_predict_day_works_without_model(
        self,
        mock_get_engine,
        mock_get_session,
        mock_race_list_scraper,
        mock_shutuba_scraper,
        mock_prediction_service,
        mock_save_markdown,
        mock_find_latest_model,
    ):
        """モデルファイルがない場合でもエラーなく動作する"""
        # Setup mocks
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_list_scraper = MagicMock()
        mock_list_scraper.fetch_race_urls.return_value = [
            "https://db.netkeiba.com/race/202606010801/",
        ]
        mock_race_list_scraper.return_value = mock_list_scraper

        mock_shutuba = MagicMock()
        mock_shutuba.fetch_shutuba.return_value = MagicMock(
            race_id="202606010801",
            race_name="テストレース",
            race_number=1,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月24日",
            entries=(),
        )
        mock_shutuba_scraper.return_value = mock_shutuba

        mock_service = MagicMock()
        mock_service.predict_from_shutuba.return_value = []
        mock_prediction_service.return_value = mock_service

        # モデルパスが見つからないように設定
        mock_find_latest_model.return_value = None

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "predict-day",
                    "--date",
                    "2026-01-24",
                    "--venue",
                    "中山",
                    "--db",
                    "data/test.db",
                ],
            )

        # エラーなく完了すること
        assert result.exit_code == 0
        # PredictionServiceがmodel_path=Noneで初期化されることを確認
        call_kwargs = mock_prediction_service.call_args.kwargs
        assert call_kwargs.get("model_path") is None


class TestPredictCommandModelAutoDetection:
    """predictコマンドのモデル自動検出テスト"""

    @patch("keiba.cli.commands.predict.find_latest_model")
    @patch("keiba.cli.commands.predict.PredictionService")
    @patch("keiba.cli.commands.predict.ShutubaScraper")
    @patch("keiba.cli.commands.predict.get_session")
    @patch("keiba.cli.commands.predict.get_engine")
    def test_predict_uses_model_if_exists(
        self,
        mock_get_engine,
        mock_get_session,
        mock_shutuba_scraper,
        mock_prediction_service,
        mock_find_latest_model,
    ):
        """predictコマンドでモデルファイルがある場合はそのパスを使用する"""
        # Setup mocks
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_shutuba = MagicMock()
        mock_shutuba_data = MagicMock(
            race_id="202606010801",
            race_name="テストレース",
            race_number=1,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月24日",
            entries=(),
        )
        mock_shutuba.fetch_shutuba.return_value = mock_shutuba_data
        mock_shutuba_scraper.return_value = mock_shutuba

        mock_service = MagicMock()
        mock_service.predict_from_shutuba.return_value = []
        mock_prediction_service.return_value = mock_service

        # モデルパスが見つかるように設定
        mock_find_latest_model.return_value = "/path/to/data/models/model.joblib"

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "predict",
                    "--url",
                    "https://race.netkeiba.com/race/shutuba.html?race_id=202606010801",
                    "--db",
                    "data/test.db",
                ],
            )

        # PredictionServiceがモデルパスを持って初期化されることを確認
        call_kwargs = mock_prediction_service.call_args.kwargs
        assert call_kwargs.get("model_path") == "/path/to/data/models/model.joblib"

    @patch("keiba.cli.commands.predict.find_latest_model")
    @patch("keiba.cli.commands.predict.PredictionService")
    @patch("keiba.cli.commands.predict.ShutubaScraper")
    @patch("keiba.cli.commands.predict.get_session")
    @patch("keiba.cli.commands.predict.get_engine")
    def test_predict_works_without_model(
        self,
        mock_get_engine,
        mock_get_session,
        mock_shutuba_scraper,
        mock_prediction_service,
        mock_find_latest_model,
    ):
        """predictコマンドでモデルファイルがない場合でもエラーなく動作する"""
        # Setup mocks
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_shutuba = MagicMock()
        mock_shutuba_data = MagicMock(
            race_id="202606010801",
            race_name="テストレース",
            race_number=1,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月24日",
            entries=(),
        )
        mock_shutuba.fetch_shutuba.return_value = mock_shutuba_data
        mock_shutuba_scraper.return_value = mock_shutuba

        mock_service = MagicMock()
        mock_service.predict_from_shutuba.return_value = []
        mock_prediction_service.return_value = mock_service

        # モデルパスが見つからないように設定
        mock_find_latest_model.return_value = None

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "predict",
                    "--url",
                    "https://race.netkeiba.com/race/shutuba.html?race_id=202606010801",
                    "--db",
                    "data/test.db",
                ],
            )

        # エラーなく完了すること
        assert result.exit_code == 0
        # PredictionServiceがmodel_path=Noneで初期化されることを確認
        call_kwargs = mock_prediction_service.call_args.kwargs
        assert call_kwargs.get("model_path") is None

    @patch("keiba.cli.commands.predict.find_latest_model")
    @patch("keiba.cli.commands.predict.PredictionService")
    @patch("keiba.cli.commands.predict.ShutubaScraper")
    @patch("keiba.cli.commands.predict.get_session")
    @patch("keiba.cli.commands.predict.get_engine")
    def test_predict_no_ml_flag_skips_model(
        self,
        mock_get_engine,
        mock_get_session,
        mock_shutuba_scraper,
        mock_prediction_service,
        mock_find_latest_model,
    ):
        """predictコマンドの--no-mlフラグでモデル検索をスキップする"""
        # Setup mocks
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_shutuba = MagicMock()
        mock_shutuba_data = MagicMock(
            race_id="202606010801",
            race_name="テストレース",
            race_number=1,
            course="中山",
            distance=2000,
            surface="芝",
            date="2026年1月24日",
            entries=(),
        )
        mock_shutuba.fetch_shutuba.return_value = mock_shutuba_data
        mock_shutuba_scraper.return_value = mock_shutuba

        mock_service = MagicMock()
        mock_service.predict_from_shutuba.return_value = []
        mock_prediction_service.return_value = mock_service

        # モデルパスがあっても
        mock_find_latest_model.return_value = "/path/to/data/models/model.joblib"

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "predict",
                    "--url",
                    "https://race.netkeiba.com/race/shutuba.html?race_id=202606010801",
                    "--db",
                    "data/test.db",
                    "--no-ml",
                ],
            )

        # --no-mlの場合はfind_latest_modelは呼ばれない
        mock_find_latest_model.assert_not_called()
        # PredictionServiceがmodel_path=Noneで初期化されることを確認
        call_kwargs = mock_prediction_service.call_args.kwargs
        assert call_kwargs.get("model_path") is None
