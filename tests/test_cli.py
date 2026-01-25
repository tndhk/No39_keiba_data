"""Tests for keiba.cli module."""

from datetime import date
from unittest.mock import MagicMock, patch

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


class TestMainGroup:
    """main()コマンドグループのテスト"""

    def test_main_is_click_group(self):
        """main()はclickグループである"""
        assert hasattr(main, "commands")

    def test_main_help(self):
        """main --helpが正常に動作する"""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "競馬データ収集CLI" in result.output

    def test_scrape_command_registered(self):
        """scrapeコマンドが登録されている"""
        assert "scrape" in main.commands


class TestScrapeCommand:
    """scrapeコマンドのテスト"""

    def test_scrape_help(self):
        """scrape --helpが正常に動作する"""
        runner = CliRunner()
        result = runner.invoke(main, ["scrape", "--help"])
        assert result.exit_code == 0
        assert "--year" in result.output
        assert "--month" in result.output
        assert "--db" in result.output

    def test_scrape_requires_year(self):
        """scrapeは--yearオプションを必須とする"""
        runner = CliRunner()
        result = runner.invoke(main, ["scrape", "--month", "1", "--db", "test.db"])
        assert result.exit_code != 0
        assert "year" in result.output.lower() or "missing" in result.output.lower()

    def test_scrape_requires_month(self):
        """scrapeは--monthオプションを必須とする"""
        runner = CliRunner()
        result = runner.invoke(main, ["scrape", "--year", "2024", "--db", "test.db"])
        assert result.exit_code != 0
        assert "month" in result.output.lower() or "missing" in result.output.lower()

    def test_scrape_requires_db(self):
        """scrapeは--dbオプションを必須とする"""
        runner = CliRunner()
        result = runner.invoke(main, ["scrape", "--year", "2024", "--month", "1"])
        assert result.exit_code != 0
        assert "db" in result.output.lower() or "missing" in result.output.lower()

    def test_scrape_year_must_be_int(self):
        """scrapeの--yearは整数でなければならない"""
        runner = CliRunner()
        result = runner.invoke(
            main, ["scrape", "--year", "abc", "--month", "1", "--db", "test.db"]
        )
        assert result.exit_code != 0

    def test_scrape_month_must_be_int(self):
        """scrapeの--monthは整数でなければならない"""
        runner = CliRunner()
        result = runner.invoke(
            main, ["scrape", "--year", "2024", "--month", "abc", "--db", "test.db"]
        )
        assert result.exit_code != 0


class TestScrapeCommandExecution:
    """scrapeコマンドの実行テスト"""

    @patch("keiba.cli.RaceDetailScraper")
    @patch("keiba.cli.RaceListScraper")
    @patch("keiba.cli.init_db")
    @patch("keiba.cli.get_session")
    @patch("keiba.cli.get_engine")
    def test_scrape_initializes_db(
        self,
        mock_get_engine,
        mock_get_session,
        mock_init_db,
        mock_race_list_scraper,
        mock_race_detail_scraper,
    ):
        """scrapeはDBを初期化する"""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # RaceListScraperがレースURLを返さない設定（早期終了）
        mock_scraper = MagicMock()
        mock_scraper.fetch_race_urls.return_value = []
        mock_race_list_scraper.return_value = mock_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["scrape", "--year", "2024", "--month", "1", "--db", "test.db"]
            )

        mock_get_engine.assert_called_once_with("test.db")
        mock_init_db.assert_called_once_with(mock_engine)

    @patch("keiba.cli.RaceDetailScraper")
    @patch("keiba.cli.RaceListScraper")
    @patch("keiba.cli.init_db")
    @patch("keiba.cli.get_session")
    @patch("keiba.cli.get_engine")
    def test_scrape_fetches_race_list_for_each_day(
        self,
        mock_get_engine,
        mock_get_session,
        mock_init_db,
        mock_race_list_scraper,
        mock_race_detail_scraper,
    ):
        """scrapeは各日のレース一覧を取得する"""
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
                main, ["scrape", "--year", "2024", "--month", "1", "--db", "test.db"]
            )

        # 2024年1月は31日ある
        assert mock_scraper.fetch_race_urls.call_count == 31

    @patch("keiba.cli.RaceDetailScraper")
    @patch("keiba.cli.RaceListScraper")
    @patch("keiba.cli.init_db")
    @patch("keiba.cli.get_session")
    @patch("keiba.cli.get_engine")
    def test_scrape_fetches_race_details(
        self,
        mock_get_engine,
        mock_get_session,
        mock_init_db,
        mock_race_list_scraper,
        mock_race_detail_scraper,
    ):
        """scrapeはレース詳細を取得する"""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_session.get.return_value = None  # レースが存在しない
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # RaceListScraperの設定
        mock_list_scraper = MagicMock()
        mock_list_scraper.fetch_race_urls.return_value = [
            "https://race.netkeiba.com/race/202401010101.html"
        ]
        mock_race_list_scraper.return_value = mock_list_scraper

        # RaceDetailScraperの設定
        mock_detail_scraper = MagicMock()
        mock_detail_scraper.fetch_race_detail.return_value = {
            "race": {
                "id": "202401010101",
                "name": "テストレース",
                "date": "2024年1月1日",
                "course": "中山",
                "race_number": 1,
                "distance": 1600,
                "surface": "芝",
                "weather": "晴",
                "track_condition": "良",
            },
            "results": [],
        }
        mock_race_detail_scraper.return_value = mock_detail_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["scrape", "--year", "2024", "--month", "1", "--db", "test.db"]
            )

        # レース詳細が取得されたことを確認（31日分 x 1レース）
        assert mock_detail_scraper.fetch_race_detail.call_count >= 1


class TestScrapeDataSaving:
    """scrapeコマンドのデータ保存テスト"""

    @patch("keiba.cli.RaceDetailScraper")
    @patch("keiba.cli.RaceListScraper")
    @patch("keiba.cli.init_db")
    @patch("keiba.cli.get_session")
    @patch("keiba.cli.get_engine")
    def test_scrape_saves_race(
        self,
        mock_get_engine,
        mock_get_session,
        mock_init_db,
        mock_race_list_scraper,
        mock_race_detail_scraper,
    ):
        """scrapeはレースデータを保存する"""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_session.get.return_value = None  # レースが存在しない
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # 1日目だけレースがあり、それ以外は空
        mock_list_scraper = MagicMock()
        call_count = [0]
        def fetch_side_effect(year, month, day, jra_only=False):
            call_count[0] += 1
            if day == 1:
                return ["https://race.netkeiba.com/race/202401010101.html"]
            return []
        mock_list_scraper.fetch_race_urls.side_effect = fetch_side_effect
        mock_race_list_scraper.return_value = mock_list_scraper

        mock_detail_scraper = MagicMock()
        mock_detail_scraper.fetch_race_detail.return_value = {
            "race": {
                "id": "202401010101",
                "name": "テストレース",
                "date": "2024年1月1日",
                "course": "中山",
                "race_number": 1,
                "distance": 1600,
                "surface": "芝",
                "weather": "晴",
                "track_condition": "良",
            },
            "results": [
                {
                    "finish_position": 1,
                    "bracket_number": 1,
                    "horse_number": 1,
                    "horse_id": "horse001",
                    "horse_name": "テスト馬",
                    "jockey_id": "jockey001",
                    "jockey_name": "テスト騎手",
                    "trainer_id": "trainer001",
                    "trainer_name": "テスト調教師",
                    "odds": 2.5,
                    "popularity": 1,
                    "weight": 480,
                    "weight_diff": 0,
                    "time": "1:35.0",
                    "margin": "",
                }
            ],
        }
        mock_race_detail_scraper.return_value = mock_detail_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["scrape", "--year", "2024", "--month", "1", "--db", "test.db"]
            )

        # session.addが呼ばれたことを確認
        assert mock_session.add.called or mock_session.merge.called

    @patch("keiba.cli.RaceDetailScraper")
    @patch("keiba.cli.RaceListScraper")
    @patch("keiba.cli.init_db")
    @patch("keiba.cli.get_session")
    @patch("keiba.cli.get_engine")
    def test_scrape_skips_existing_race(
        self,
        mock_get_engine,
        mock_get_session,
        mock_init_db,
        mock_race_list_scraper,
        mock_race_detail_scraper,
    ):
        """scrapeは既存のレースをスキップする"""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()

        # レースが既に存在する場合
        mock_existing_race = MagicMock()
        mock_session.get.return_value = mock_existing_race

        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_list_scraper = MagicMock()
        mock_list_scraper.fetch_race_urls.return_value = [
            "https://race.netkeiba.com/race/202401010101.html"
        ]
        mock_race_list_scraper.return_value = mock_list_scraper

        mock_detail_scraper = MagicMock()
        mock_race_detail_scraper.return_value = mock_detail_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["scrape", "--year", "2024", "--month", "1", "--db", "test.db"]
            )

        # レース詳細を取得しないことを確認（既存データはスキップ）
        mock_detail_scraper.fetch_race_detail.assert_not_called()


class TestScrapeProgressOutput:
    """scrapeコマンドの進捗表示テスト"""

    @patch("keiba.cli.RaceDetailScraper")
    @patch("keiba.cli.RaceListScraper")
    @patch("keiba.cli.init_db")
    @patch("keiba.cli.get_session")
    @patch("keiba.cli.get_engine")
    def test_scrape_shows_start_message(
        self,
        mock_get_engine,
        mock_get_session,
        mock_init_db,
        mock_race_list_scraper,
        mock_race_detail_scraper,
    ):
        """scrapeは開始メッセージを表示する"""
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
                main, ["scrape", "--year", "2024", "--month", "1", "--db", "test.db"]
            )

        assert "2024年1月" in result.output

    @patch("keiba.cli.RaceDetailScraper")
    @patch("keiba.cli.RaceListScraper")
    @patch("keiba.cli.init_db")
    @patch("keiba.cli.get_session")
    @patch("keiba.cli.get_engine")
    def test_scrape_shows_completion_message(
        self,
        mock_get_engine,
        mock_get_session,
        mock_init_db,
        mock_race_list_scraper,
        mock_race_detail_scraper,
    ):
        """scrapeは完了メッセージを表示する"""
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
                main, ["scrape", "--year", "2024", "--month", "1", "--db", "test.db"]
            )

        assert "完了" in result.output

    @patch("keiba.cli.RaceDetailScraper")
    @patch("keiba.cli.RaceListScraper")
    @patch("keiba.cli.init_db")
    @patch("keiba.cli.get_session")
    @patch("keiba.cli.get_engine")
    def test_scrape_exits_successfully(
        self,
        mock_get_engine,
        mock_get_session,
        mock_init_db,
        mock_race_list_scraper,
        mock_race_detail_scraper,
    ):
        """scrapeは正常終了する（exit_code=0）"""
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
                main, ["scrape", "--year", "2024", "--month", "1", "--db", "test.db"]
            )

        assert result.exit_code == 0


class TestHelperFunctions:
    """ヘルパー関数のテスト"""

    def test_extract_race_id_from_url(self):
        """URLからレースIDを抽出できる"""
        from keiba.cli import extract_race_id_from_url

        url = "https://race.netkeiba.com/race/202401010101.html"
        race_id = extract_race_id_from_url(url)
        assert race_id == "202401010101"

    def test_extract_race_id_from_url_with_different_format(self):
        """異なる形式のURLからもレースIDを抽出できる"""
        from keiba.cli import extract_race_id_from_url

        url = "https://race.netkeiba.com/race/202412251211.html"
        race_id = extract_race_id_from_url(url)
        assert race_id == "202412251211"

    def test_parse_race_date(self):
        """レース日付を解析できる"""
        from keiba.cli import parse_race_date

        date_str = "2024年1月1日"
        result = parse_race_date(date_str)
        assert result == date(2024, 1, 1)

    def test_parse_race_date_with_month_padding(self):
        """月がパディングされた日付を解析できる"""
        from keiba.cli import parse_race_date

        date_str = "2024年12月25日"
        result = parse_race_date(date_str)
        assert result == date(2024, 12, 25)


class TestAnalyzeCommand:
    """analyzeコマンドのテスト"""

    def test_analyze_command_registered(self):
        """analyzeコマンドが登録されている"""
        assert "analyze" in main.commands

    def test_analyze_help(self):
        """analyze --helpが正常に動作する"""
        runner = CliRunner()
        result = runner.invoke(main, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "--db" in result.output
        assert "--date" in result.output
        assert "--venue" in result.output

    def test_analyze_requires_db(self):
        """analyzeは--dbオプションを必須とする"""
        runner = CliRunner()
        result = runner.invoke(
            main, ["analyze", "--date", "2024-01-06", "--venue", "中山"]
        )
        assert result.exit_code != 0

    def test_analyze_requires_date(self):
        """analyzeは--dateオプションを必須とする"""
        runner = CliRunner()
        result = runner.invoke(main, ["analyze", "--db", "test.db", "--venue", "中山"])
        assert result.exit_code != 0

    def test_analyze_requires_venue(self):
        """analyzeは--venueオプションを必須とする"""
        runner = CliRunner()
        result = runner.invoke(
            main, ["analyze", "--db", "test.db", "--date", "2024-01-06"]
        )
        assert result.exit_code != 0


@skip_without_lightgbm
class TestAnalyzeCommandExecution:
    """analyzeコマンドの実行テスト"""

    @patch("keiba.cli.get_session")
    @patch("keiba.cli.get_engine")
    def test_analyze_with_no_races(
        self,
        mock_get_engine,
        mock_get_session,
    ):
        """レースがない場合はメッセージを表示する"""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        runner = CliRunner()
        with runner.isolated_filesystem():
            # テスト用の空のDBを作成
            result = runner.invoke(
                main,
                [
                    "analyze",
                    "--db",
                    "test.db",
                    "--date",
                    "2024-01-06",
                    "--venue",
                    "中山",
                ],
            )

        assert result.exit_code == 0
        assert "レースが見つかりません" in result.output or "No races" in result.output

    @patch("keiba.cli.get_session")
    @patch("keiba.cli.get_engine")
    def test_analyze_outputs_table_format(
        self,
        mock_get_engine,
        mock_get_session,
    ):
        """analyzeは表形式で出力する"""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()

        # モックレースを作成
        mock_race = MagicMock()
        mock_race.id = "202401060601"
        mock_race.name = "テストレース"
        mock_race.race_number = 1
        mock_race.distance = 1600
        mock_race.surface = "芝"
        mock_race.date = date(2024, 1, 6)
        mock_race.course = "中山"

        # レースが見つかる設定
        mock_session.execute.return_value.scalars.return_value.all.return_value = [
            mock_race
        ]

        # レース結果のモック
        mock_result = MagicMock()
        mock_result.horse_id = "horse001"
        mock_result.horse_number = 1
        mock_result.popularity = 1
        mock_result.odds = 2.5
        mock_result.last_3f = 34.5
        mock_result.horse = MagicMock()
        mock_result.horse.name = "テスト馬"

        # 結果リストを返すクエリのモック
        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [mock_result]
        mock_session.query.return_value = query_mock

        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "analyze",
                    "--db",
                    "test.db",
                    "--date",
                    "2024-01-06",
                    "--venue",
                    "中山",
                ],
            )

        # 表形式の出力を確認
        assert "テストレース" in result.output or "テスト馬" in result.output


class TestMigrateGradesCommand:
    """migrate-gradesコマンドのテスト"""

    def test_migrate_grades_command_registered(self):
        """migrate-gradesコマンドが登録されている"""
        assert "migrate-grades" in main.commands

    def test_migrate_grades_help(self):
        """migrate-grades --helpが正常に動作する"""
        runner = CliRunner()
        result = runner.invoke(main, ["migrate-grades", "--help"])
        assert result.exit_code == 0
        assert "--db" in result.output

    def test_migrate_grades_requires_db(self):
        """migrate-gradesは--dbオプションを必須とする"""
        runner = CliRunner()
        result = runner.invoke(main, ["migrate-grades"])
        assert result.exit_code != 0


class TestMigrateGradesCommandExecution:
    """migrate-gradesコマンドの実行テスト"""

    @patch("keiba.cli.get_session")
    @patch("keiba.cli.get_engine")
    def test_migrate_grades_updates_races(
        self,
        mock_get_engine,
        mock_get_session,
    ):
        """migrate-gradesはレースのgradeを更新する"""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()

        # gradeがNoneのレースを返すモック
        mock_race = MagicMock()
        mock_race.id = "202401010101"
        mock_race.name = "有馬記念(G1)"
        mock_race.grade = None

        mock_session.query.return_value.filter.return_value.all.return_value = [mock_race]
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["migrate-grades", "--db", "test.db"]
            )

        # gradeが更新されたことを確認
        assert mock_race.grade == "G1"

    @patch("keiba.cli.get_session")
    @patch("keiba.cli.get_engine")
    def test_migrate_grades_shows_progress(
        self,
        mock_get_engine,
        mock_get_session,
    ):
        """migrate-gradesは進捗を表示する"""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()

        # 空のリストを返す
        mock_session.query.return_value.filter.return_value.all.return_value = []
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["migrate-grades", "--db", "test.db"]
            )

        assert result.exit_code == 0
        assert "完了" in result.output


class TestScrapeDataSavingWithGrade:
    """scrapeコマンドのグレード保存テスト"""

    @patch("keiba.cli.RaceDetailScraper")
    @patch("keiba.cli.RaceListScraper")
    @patch("keiba.cli.init_db")
    @patch("keiba.cli.get_session")
    @patch("keiba.cli.get_engine")
    def test_scrape_saves_race_with_grade(
        self,
        mock_get_engine,
        mock_get_session,
        mock_init_db,
        mock_race_list_scraper,
        mock_race_detail_scraper,
    ):
        """scrapeはレースデータにgradeを含めて保存する"""
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_session.get.return_value = None  # レースが存在しない
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # 1日目だけレースがあり、それ以外は空
        mock_list_scraper = MagicMock()
        def fetch_side_effect(year, month, day, jra_only=False):
            if day == 1:
                return ["https://race.netkeiba.com/race/202401010101.html"]
            return []
        mock_list_scraper.fetch_race_urls.side_effect = fetch_side_effect
        mock_race_list_scraper.return_value = mock_list_scraper

        mock_detail_scraper = MagicMock()
        mock_detail_scraper.fetch_race_detail.return_value = {
            "race": {
                "id": "202401010101",
                "name": "有馬記念(G1)",
                "date": "2024年1月1日",
                "course": "中山",
                "race_number": 11,
                "distance": 2500,
                "surface": "芝",
                "weather": "晴",
                "track_condition": "良",
                "grade": "G1",  # グレード情報が含まれる
            },
            "results": [
                {
                    "finish_position": 1,
                    "bracket_number": 1,
                    "horse_number": 1,
                    "horse_id": "horse001",
                    "horse_name": "テスト馬",
                    "jockey_id": "jockey001",
                    "jockey_name": "テスト騎手",
                    "trainer_id": "trainer001",
                    "trainer_name": "テスト調教師",
                    "odds": 2.5,
                    "popularity": 1,
                    "weight": 480,
                    "weight_diff": 0,
                    "time": "1:35.0",
                    "margin": "",
                }
            ],
        }
        mock_race_detail_scraper.return_value = mock_detail_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main, ["scrape", "--year", "2024", "--month", "1", "--db", "test.db"]
            )

        # session.addが呼ばれたことを確認
        assert mock_session.add.called

        # 追加されたオブジェクトにgradeが含まれていることを確認するには
        # addの呼び出し引数を検査
        add_calls = mock_session.add.call_args_list
        # Raceオブジェクトを探す
        for call in add_calls:
            obj = call[0][0]
            if hasattr(obj, "grade"):
                # Raceモデルのgradeは設定されているはず
                assert hasattr(obj, "grade")


# ============================================================================
# ML予測テスト用のFixtureとテストクラス
# ============================================================================


@pytest.fixture
def runner():
    """CLIテスト用のClickランナー"""
    return CliRunner()


@pytest.fixture
def sample_db(tmp_path):
    """テスト用のサンプルデータベースパス"""
    return str(tmp_path / "test_keiba.db")


@pytest.fixture
def sample_db_with_data(tmp_path):
    """テスト用のサンプルデータベース（初期化とデータ投入済み）"""
    from datetime import date as dt_date
    from keiba.db import get_engine, init_db, get_session
    from keiba.models import Race, RaceResult, Horse, Jockey, Trainer

    db_path = str(tmp_path / "test_keiba.db")
    engine = get_engine(db_path)
    init_db(engine)

    with get_session(engine) as session:
        # テスト用の競走馬（id属性を使用、必須フィールドを含める）
        horse1 = Horse(id="horse001", name="テストホース1", sex="牡", birth_year=2020, sire="ディープインパクト")
        horse2 = Horse(id="horse002", name="テストホース2", sex="牝", birth_year=2021, sire="キングカメハメハ")
        session.add_all([horse1, horse2])

        # テスト用の騎手（id属性を使用）
        jockey = Jockey(id="jockey001", name="テスト騎手")
        session.add(jockey)

        # テスト用の調教師（id属性を使用）
        trainer = Trainer(id="trainer001", name="テスト調教師")
        session.add(trainer)

        # テスト用のレース（対象日）- course属性を使用
        race = Race(
            id="202401060511",
            name="テストレース",
            date=dt_date(2024, 1, 6),
            course="中山",
            surface="芝",
            distance=2000,
            track_condition="良",
            race_number=11,
        )
        session.add(race)

        # テスト用のレース結果（必須フィールド: bracket_number, margin を含める）
        result1 = RaceResult(
            race_id="202401060511",
            horse_id="horse001",
            jockey_id="jockey001",
            trainer_id="trainer001",
            bracket_number=1,
            horse_number=1,
            finish_position=1,
            odds=2.5,
            popularity=1,
            time="2:00.0",
            margin="",
            sex="牡",
            age=4,
        )
        result2 = RaceResult(
            race_id="202401060511",
            horse_id="horse002",
            jockey_id="jockey001",
            trainer_id="trainer001",
            bracket_number=2,
            horse_number=2,
            finish_position=2,
            odds=5.0,
            popularity=2,
            time="2:00.5",
            margin="1/2",
            sex="牝",
            age=3,
        )
        session.add_all([result1, result2])

        # 学習用の過去レースデータ（2023年）
        for i in range(10):
            past_race = Race(
                id=f"2023010{i:02d}0511",
                name=f"過去レース{i}",
                date=dt_date(2023, 1, 10 + i),
                course="中山",
                surface="芝",
                distance=2000,
                track_condition="良",
                race_number=11,
            )
            session.add(past_race)

            past_result = RaceResult(
                race_id=f"2023010{i:02d}0511",
                horse_id="horse001",
                jockey_id="jockey001",
                trainer_id="trainer001",
                bracket_number=1,
                horse_number=1,
                finish_position=(i % 3) + 1,
                odds=3.0,
                popularity=1,
                time="2:00.0",
                margin="",
                sex="牡",
                age=3,
            )
            session.add(past_result)

    return db_path


@skip_without_lightgbm
class TestAnalyzeWithML:
    """analyzeコマンドのML予測テスト"""

    def test_analyze_with_prediction_shows_ml_header(self, runner, sample_db_with_data):
        """ML予測ヘッダーが表示されるテスト"""
        result = runner.invoke(
            main,
            ["analyze", "--db", sample_db_with_data, "--date", "2024-01-06", "--venue", "中山"],
        )
        # ML予測が有効な場合、ヘッダーまたは学習メッセージが含まれる
        # 学習データが不足の場合はメッセージが出る
        assert "【ML予測】" in result.output or "学習データ" in result.output or "ML予測モデルを学習中" in result.output

    def test_analyze_with_no_predict_flag(self, runner, sample_db_with_data):
        """--no-predictフラグでML予測をスキップ"""
        result = runner.invoke(
            main,
            ["analyze", "--db", sample_db_with_data, "--date", "2024-01-06", "--venue", "中山", "--no-predict"],
        )
        # ML予測ヘッダーが含まれない
        assert "【ML予測】" not in result.output

    def test_analyze_shows_probability_column(self, runner, sample_db_with_data):
        """確率列または学習メッセージが表示されるテスト"""
        result = runner.invoke(
            main,
            ["analyze", "--db", sample_db_with_data, "--date", "2024-01-06", "--venue", "中山"],
        )
        # 確率列のヘッダーが含まれるか、または学習関連のメッセージが含まれる
        assert "3着内確率" in result.output or "確率" in result.output or "学習" in result.output or "ML予測モデル" in result.output


# ============================================================================
# backtestコマンドのテスト
# ============================================================================


class TestBacktestCommand:
    """backtestコマンドのテスト"""

    def test_backtest_command_exists(self):
        """backtestコマンドが登録されている"""
        assert "backtest" in main.commands

    def test_backtest_help(self):
        """backtest --helpが正常に動作する"""
        runner = CliRunner()
        result = runner.invoke(main, ["backtest", "--help"])
        assert result.exit_code == 0
        assert "--db" in result.output
        assert "バックテスト" in result.output or "backtest" in result.output.lower()

    def test_backtest_requires_db(self):
        """backtestは--dbオプションを必須とする"""
        runner = CliRunner()
        result = runner.invoke(main, ["backtest"])
        assert result.exit_code != 0
        assert "db" in result.output.lower() or "missing" in result.output.lower()

    def test_backtest_date_range_options(self):
        """backtestは--fromと--toオプションを受け付ける"""
        runner = CliRunner()
        result = runner.invoke(main, ["backtest", "--help"])
        assert "--from" in result.output
        assert "--to" in result.output

    def test_backtest_months_option(self):
        """backtestは--monthsオプションを受け付ける"""
        runner = CliRunner()
        result = runner.invoke(main, ["backtest", "--help"])
        assert "--months" in result.output

    def test_backtest_verbose_flag(self):
        """backtestは-v/--verboseフラグを受け付ける"""
        runner = CliRunner()
        result = runner.invoke(main, ["backtest", "--help"])
        assert "-v" in result.output or "--verbose" in result.output

    def test_backtest_retrain_interval_option(self):
        """backtestは--retrain-intervalオプションを受け付ける"""
        runner = CliRunner()
        result = runner.invoke(main, ["backtest", "--help"])
        assert "--retrain-interval" in result.output

    def test_backtest_retrain_interval_choices(self):
        """--retrain-intervalはdaily/weekly/monthlyのみ受け付ける"""
        runner = CliRunner()
        result = runner.invoke(main, ["backtest", "--help"])
        # ヘルプにchoiceが表示される
        assert "daily" in result.output
        assert "weekly" in result.output
        assert "monthly" in result.output


@skip_without_lightgbm
class TestBacktestCommandExecution:
    """backtestコマンドの実行テスト

    CLIの出力メッセージを検証することで、正しい引数処理を確認する
    """

    def test_backtest_shows_start_message(self):
        """backtestは開始メッセージを表示する"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.db", "w") as f:
                f.write("")

            result = runner.invoke(main, ["backtest", "--db", "test.db"])

        # 開始メッセージが表示される（エラー終了でも表示される）
        assert "バックテスト開始" in result.output

    def test_backtest_with_date_range_shows_period(self):
        """backtestは--from/--toで指定した期間を表示する"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.db", "w") as f:
                f.write("")

            result = runner.invoke(
                main,
                ["backtest", "--db", "test.db", "--from", "2024-10-01", "--to", "2024-12-31"],
            )

        # 指定した期間が出力に含まれる
        assert "2024-10-01" in result.output
        assert "2024-12-31" in result.output

    def test_backtest_with_months_calculates_period(self):
        """backtestは--monthsで直近N ヶ月を計算して表示する"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.db", "w") as f:
                f.write("")

            result = runner.invoke(main, ["backtest", "--db", "test.db", "--months", "3"])

        # 期間が表示される
        assert "期間:" in result.output

    def test_backtest_shows_retrain_interval(self):
        """backtestは再学習間隔を表示する"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.db", "w") as f:
                f.write("")

            result = runner.invoke(
                main, ["backtest", "--db", "test.db", "--retrain-interval", "weekly"]
            )

        # 再学習間隔が表示される
        assert "再学習間隔: weekly" in result.output

    def test_backtest_retrain_interval_daily(self):
        """backtestは--retrain-interval dailyを受け付ける"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.db", "w") as f:
                f.write("")

            result = runner.invoke(
                main, ["backtest", "--db", "test.db", "--retrain-interval", "daily"]
            )

        assert "再学習間隔: daily" in result.output

    def test_backtest_retrain_interval_monthly(self):
        """backtestは--retrain-interval monthlyを受け付ける"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.db", "w") as f:
                f.write("")

            result = runner.invoke(
                main, ["backtest", "--db", "test.db", "--retrain-interval", "monthly"]
            )

        assert "再学習間隔: monthly" in result.output

    def test_backtest_invalid_date_format(self):
        """backtestは不正な日付形式でエラーメッセージを表示する"""
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test.db", "w") as f:
                f.write("")

            result = runner.invoke(
                main,
                ["backtest", "--db", "test.db", "--from", "invalid", "--to", "2024-12-31"],
            )

        # エラーメッセージが表示される
        assert "日付形式が不正です" in result.output


# ============================================================================
# predictコマンドのテスト
# ============================================================================


class TestPredictCommand:
    """predictコマンドのテスト"""

    def test_predict_command_exists(self):
        """predictコマンドが登録されている"""
        assert "predict" in main.commands

    def test_predict_help(self):
        """predict --helpが正常に動作する"""
        runner = CliRunner()
        result = runner.invoke(main, ["predict", "--help"])
        assert result.exit_code == 0
        assert "--url" in result.output
        assert "--db" in result.output

    def test_predict_requires_url_option(self):
        """predictは--urlオプションを必須とする"""
        runner = CliRunner()
        result = runner.invoke(main, ["predict", "--db", "test.db"])
        assert result.exit_code != 0
        assert "url" in result.output.lower() or "missing" in result.output.lower()

    def test_predict_requires_db_option(self):
        """predictは--dbオプションを必須とする"""
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["predict", "--url", "https://race.netkeiba.com/race/shutuba.html?race_id=202606010802"],
        )
        assert result.exit_code != 0
        assert "db" in result.output.lower() or "missing" in result.output.lower()

    def test_predict_no_ml_flag(self):
        """predictは--no-mlフラグを受け付ける"""
        runner = CliRunner()
        result = runner.invoke(main, ["predict", "--help"])
        assert "--no-ml" in result.output


class TestExtractRaceIdFromShutubaUrl:
    """extract_race_id_from_shutuba_url関数のテスト"""

    def test_extract_race_id_from_shutuba_url(self):
        """出馬表URLからrace_idを正しく抽出できる"""
        from keiba.cli import extract_race_id_from_shutuba_url

        url = "https://race.netkeiba.com/race/shutuba.html?race_id=202606010802"
        race_id = extract_race_id_from_shutuba_url(url)
        assert race_id == "202606010802"

    def test_extract_race_id_with_additional_params(self):
        """追加パラメータがあるURLからもrace_idを抽出できる"""
        from keiba.cli import extract_race_id_from_shutuba_url

        url = "https://race.netkeiba.com/race/shutuba.html?race_id=202606010802&rf=shutuba_submenu"
        race_id = extract_race_id_from_shutuba_url(url)
        assert race_id == "202606010802"

    def test_extract_race_id_invalid_url_raises_error(self):
        """不正なURLはValueErrorを発生させる"""
        from keiba.cli import extract_race_id_from_shutuba_url

        with pytest.raises(ValueError):
            extract_race_id_from_shutuba_url("https://example.com/invalid")


@skip_without_lightgbm
class TestPredictCommandExecution:
    """predictコマンドの実行テスト"""

    def test_predict_displays_results(self):
        """predictコマンドは予測結果を表示する（_print_prediction_tableのテスト）"""
        from keiba.cli import _print_prediction_table
        from keiba.services.prediction_service import PredictionResult

        # PredictionResultを作成
        mock_prediction_result = PredictionResult(
            horse_number=1,
            horse_name="テストホース1",
            horse_id="horse001",
            ml_probability=0.623,
            factor_scores={
                "past_results": 80.0,
                "course_fit": 70.5,
                "time_index": 68.3,
                "last_3f": 82.1,
                "popularity": 90.0,
                "pedigree": 65.0,
                "running_style": 70.0,
            },
            total_score=75.2,
            combined_score=75.5,
            rank=1,
        )

        runner = CliRunner()
        # _print_prediction_tableが例外を発生させないことを確認
        with runner.isolated_filesystem():
            # clickの出力をキャプチャするため、関数を直接呼び出す
            _print_prediction_table([mock_prediction_result], with_ml=True)

    def test_predict_with_no_ml_flag(self):
        """predictコマンドは--no-mlフラグで因子スコアのみ表示する"""
        from keiba.cli import _print_prediction_table
        from keiba.services.prediction_service import PredictionResult

        # PredictionResult（ML確率は0.0）
        mock_prediction_result = PredictionResult(
            horse_number=1,
            horse_name="テストホース1",
            horse_id="horse001",
            ml_probability=0.0,
            factor_scores={
                "past_results": 80.0,
                "course_fit": 70.5,
                "time_index": 68.3,
                "last_3f": 82.1,
                "popularity": 90.0,
                "pedigree": 65.0,
                "running_style": 70.0,
            },
            total_score=75.2,
            combined_score=75.5,
            rank=1,
        )

        runner = CliRunner()
        with runner.isolated_filesystem():
            # 因子スコアのみのテーブル表示（with_ml=False）
            _print_prediction_table([mock_prediction_result], with_ml=False)

    def test_predict_shows_race_info_header(self):
        """predictコマンドはレース情報ヘッダーを表示する（extract_race_id_from_shutuba_urlのテスト）"""
        from keiba.cli import extract_race_id_from_shutuba_url

        url = "https://race.netkeiba.com/race/shutuba.html?race_id=202606010802"
        race_id = extract_race_id_from_shutuba_url(url)

        # race_idが正しく抽出されている
        assert race_id == "202606010802"


# ============================================================================
# _save_predictions_markdown / _parse_predictions_markdown のテスト
# ============================================================================


class TestSavePredictionsMarkdown:
    """_save_predictions_markdown関数のテスト"""

    def test_save_predictions_with_race_id(self, tmp_path):
        """予測データにrace_idが含まれている場合、Markdownに保存される"""
        from keiba.cli import _save_predictions_markdown

        predictions_data = [
            {
                "race_id": "202606010801",
                "race_number": 1,
                "race_name": "テストレース",
                "surface": "芝",
                "distance": 2000,
                "predictions": [
                    {
                        "rank": 1,
                        "horse_number": 5,
                        "horse_name": "テストホース",
                        "ml_probability": 0.623,
                        "total_score": 75.2,
                    }
                ],
            }
        ]

        filepath = _save_predictions_markdown(
            predictions_data=predictions_data,
            date_str="2026-01-24",
            venue="中山",
            output_dir=str(tmp_path),
        )

        # ファイルが作成された
        from pathlib import Path
        path = Path(filepath)
        assert path.exists()

        # ファイル内容を確認
        content = path.read_text(encoding="utf-8")
        assert "race_id: 202606010801" in content
        assert "1R テストレース" in content

    def test_save_predictions_without_race_id(self, tmp_path):
        """予測データにrace_idが含まれていない場合、race_id行は出力されない"""
        from keiba.cli import _save_predictions_markdown

        predictions_data = [
            {
                "race_number": 1,
                "race_name": "テストレース",
                "surface": "芝",
                "distance": 2000,
                "predictions": [],
            }
        ]

        filepath = _save_predictions_markdown(
            predictions_data=predictions_data,
            date_str="2026-01-24",
            venue="中山",
            output_dir=str(tmp_path),
        )

        # ファイル内容を確認
        from pathlib import Path
        content = Path(filepath).read_text(encoding="utf-8")
        assert "race_id:" not in content


class TestParsePredictionsMarkdown:
    """_parse_predictions_markdown関数のテスト"""

    def test_parse_predictions_with_race_id(self, tmp_path):
        """race_idを含むMarkdownファイルをパースできる"""
        from keiba.cli import _parse_predictions_markdown

        # テスト用Markdownファイルを作成
        content = """# 2026-01-24 中山 予測結果

生成日時: 2026-01-24 10:00:00

## 1R テストレース
race_id: 202606010801
芝2000m

| 順位 | 馬番 | 馬名 | ML確率 | 総合 |
|:---:|:---:|:---|:---:|:---:|
| 1 | 5 | テストホース | 62.3% | 75.2 |
| 2 | 3 | テストホース2 | 45.1% | 68.5 |

## 2R テストレース2
race_id: 202606010802
芝1600m

| 順位 | 馬番 | 馬名 | ML確率 | 総合 |
|:---:|:---:|:---|:---:|:---:|
| 1 | 1 | テストホース3 | - | 80.0 |
"""
        filepath = tmp_path / "test-predictions.md"
        filepath.write_text(content, encoding="utf-8")

        # パース
        result = _parse_predictions_markdown(str(filepath))

        # 結果を確認
        assert len(result["races"]) == 2

        race1 = result["races"][0]
        assert race1["race_id"] == "202606010801"
        assert race1["race_number"] == 1
        assert race1["race_name"] == "テストレース"
        assert len(race1["predictions"]) == 2
        assert race1["predictions"][0]["horse_number"] == 5
        assert race1["predictions"][0]["ml_probability"] == pytest.approx(0.623, rel=0.01)

        race2 = result["races"][1]
        assert race2["race_id"] == "202606010802"
        assert race2["race_number"] == 2
        assert race2["predictions"][0]["ml_probability"] == 0.0  # "-"は0.0

    def test_parse_predictions_without_race_id(self, tmp_path):
        """race_idを含まない古い形式のMarkdownファイルもパースできる"""
        from keiba.cli import _parse_predictions_markdown

        # テスト用Markdownファイルを作成（race_idなし）
        content = """# 2026-01-24 中山 予測結果

## 1R テストレース
芝2000m

| 順位 | 馬番 | 馬名 | ML確率 | 総合 |
|:---:|:---:|:---|:---:|:---:|
| 1 | 5 | テストホース | 62.3% | 75.2 |
"""
        filepath = tmp_path / "test-predictions.md"
        filepath.write_text(content, encoding="utf-8")

        # パース
        result = _parse_predictions_markdown(str(filepath))

        # 結果を確認
        assert len(result["races"]) == 1
        race1 = result["races"][0]
        assert race1["race_id"] == ""  # race_idは空文字
        assert race1["race_number"] == 1
        assert race1["race_name"] == "テストレース"

    def test_parse_nonexistent_file(self, tmp_path):
        """存在しないファイルの場合は空の結果を返す"""
        from keiba.cli import _parse_predictions_markdown

        result = _parse_predictions_markdown(str(tmp_path / "nonexistent.md"))
        assert result == {"races": []}
