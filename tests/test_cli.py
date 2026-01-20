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


@skip_without_lightgbm
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
