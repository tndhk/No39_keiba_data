"""scrape-horses コマンドのテスト"""

from datetime import date
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

from keiba.cli import main
from keiba.models import Horse
from keiba.models.entry import RaceEntry, ShutubaData


class TestScrapeHorsesCommand:
    """scrape-horses コマンドの基本テスト"""

    def test_scrape_horses_command_exists(self):
        """scrape-horses コマンドが登録されていること"""
        assert "scrape-horses" in main.commands

    def test_scrape_horses_help(self):
        """scrape-horses --help が正常に動作すること"""
        runner = CliRunner()
        result = runner.invoke(main, ["scrape-horses", "--help"])
        assert result.exit_code == 0
        assert "--db" in result.output
        assert "--limit" in result.output
        assert "--date" in result.output
        assert "--venue" in result.output


class TestScrapeHorsesDateMode:
    """--date モードのテスト"""

    @patch("keiba.cli.commands.scrape.HorseDetailScraper")
    @patch("keiba.cli.commands.scrape.ShutubaScraper")
    @patch("keiba.cli.commands.scrape.RaceListScraper")
    @patch("keiba.cli.commands.scrape.get_session")
    @patch("keiba.cli.commands.scrape.get_engine")
    @patch("keiba.cli.commands.scrape.init_db")
    def test_date_mode_collects_entry_horse_ids(
        self,
        mock_init_db,
        mock_get_engine,
        mock_get_session,
        mock_race_list_scraper,
        mock_shutuba_scraper,
        mock_horse_detail_scraper,
    ):
        """--date 指定時に出走予定馬の horse_id を収集すること"""
        # Mock setup
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # RaceListScraper mock
        mock_list_scraper = MagicMock()
        mock_list_scraper.fetch_race_urls.return_value = [
            "https://db.netkeiba.com/race/202606010101/",
            "https://db.netkeiba.com/race/202606010102/",
        ]
        mock_race_list_scraper.return_value = mock_list_scraper

        # ShutubaScraper mock
        mock_shutuba = MagicMock()
        entry1 = RaceEntry(
            horse_id="2021101234",
            horse_name="テストホース1",
            horse_number=1,
            bracket_number=1,
            jockey_id="00001",
            jockey_name="騎手1",
            impost=58.0,
        )
        entry2 = RaceEntry(
            horse_id="2021101235",
            horse_name="テストホース2",
            horse_number=2,
            bracket_number=2,
            jockey_id="00002",
            jockey_name="騎手2",
            impost=58.0,
        )
        mock_shutuba_data = MagicMock(entries=(entry1, entry2))
        mock_shutuba.fetch_shutuba.return_value = mock_shutuba_data
        mock_shutuba_scraper.return_value = mock_shutuba

        # Horse query mock (両方とも DB に存在するが sire は NULL)
        horse1 = Horse(id="2021101234", name="テストホース1", sex="牡", birth_year=2021)
        horse2 = Horse(id="2021101235", name="テストホース2", sex="牡", birth_year=2021)
        mock_session.get.side_effect = lambda model, id: {
            "2021101234": horse1,
            "2021101235": horse2,
        }.get(id)

        # HorseDetailScraper mock
        mock_detail_scraper = MagicMock()
        mock_detail_scraper.fetch_horse_detail.return_value = {
            "name": "テストホース",
            "sex": "牡",
            "birth_year": 2021,
            "sire": "父馬",
            "dam": "母馬",
            "dam_sire": "母父",
        }
        mock_horse_detail_scraper.return_value = mock_detail_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "scrape-horses",
                    "--db",
                    "test.db",
                    "--date",
                    "2026-06-01",
                ],
            )

        # RaceListScraper が呼ばれたこと
        mock_list_scraper.fetch_race_urls.assert_called_once_with(
            2026, 6, 1, jra_only=True
        )

        # ShutubaScraper が2レース分呼ばれたこと
        assert mock_shutuba.fetch_shutuba.call_count == 2

        # HorseDetailScraper が2頭分呼ばれたこと
        assert mock_detail_scraper.fetch_horse_detail.call_count == 2

    @patch("keiba.cli.commands.scrape.HorseDetailScraper")
    @patch("keiba.cli.commands.scrape.ShutubaScraper")
    @patch("keiba.cli.commands.scrape.RaceListScraper")
    @patch("keiba.cli.commands.scrape.get_session")
    @patch("keiba.cli.commands.scrape.get_engine")
    @patch("keiba.cli.commands.scrape.init_db")
    def test_date_and_venue_mode_filters_by_venue(
        self,
        mock_init_db,
        mock_get_engine,
        mock_get_session,
        mock_race_list_scraper,
        mock_shutuba_scraper,
        mock_horse_detail_scraper,
    ):
        """--date と --venue 指定時に会場でフィルタリングすること"""
        # Mock setup
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # RaceListScraper mock (中山と東京が混在)
        mock_list_scraper = MagicMock()
        mock_list_scraper.fetch_race_urls.return_value = [
            "https://db.netkeiba.com/race/202606010101/",  # 中山（06）
            "https://db.netkeiba.com/race/202605010101/",  # 東京（05）
        ]
        mock_race_list_scraper.return_value = mock_list_scraper

        # ShutubaScraper mock
        mock_shutuba = MagicMock()
        entry = RaceEntry(
            horse_id="2021101234",
            horse_name="テストホース",
            horse_number=1,
            bracket_number=1,
            jockey_id="00001",
            jockey_name="騎手1",
            impost=58.0,
        )
        mock_shutuba_data = MagicMock(entries=(entry,))
        mock_shutuba.fetch_shutuba.return_value = mock_shutuba_data
        mock_shutuba_scraper.return_value = mock_shutuba

        # Horse query mock
        horse = Horse(id="2021101234", name="テストホース", sex="牡", birth_year=2021)
        mock_session.get.return_value = horse

        # HorseDetailScraper mock
        mock_detail_scraper = MagicMock()
        mock_detail_scraper.fetch_horse_detail.return_value = {
            "name": "テストホース",
            "sire": "父馬",
        }
        mock_horse_detail_scraper.return_value = mock_detail_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "scrape-horses",
                    "--db",
                    "test.db",
                    "--date",
                    "2026-06-01",
                    "--venue",
                    "中山",
                ],
            )

        # ShutubaScraper は中山（06）のレースのみ処理（1レースのみ）
        assert mock_shutuba.fetch_shutuba.call_count == 1
        mock_shutuba.fetch_shutuba.assert_called_with("202606010101")


class TestScrapeHorsesSkipsExisting:
    """既に sire が取得済みの馬をスキップするテスト"""

    @patch("keiba.cli.commands.scrape.HorseDetailScraper")
    @patch("keiba.cli.commands.scrape.ShutubaScraper")
    @patch("keiba.cli.commands.scrape.RaceListScraper")
    @patch("keiba.cli.commands.scrape.get_session")
    @patch("keiba.cli.commands.scrape.get_engine")
    @patch("keiba.cli.commands.scrape.init_db")
    def test_skips_horses_with_sire_already_fetched(
        self,
        mock_init_db,
        mock_get_engine,
        mock_get_session,
        mock_race_list_scraper,
        mock_shutuba_scraper,
        mock_horse_detail_scraper,
    ):
        """sire が既に取得済みの馬はスキップすること"""
        # Mock setup
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # RaceListScraper mock
        mock_list_scraper = MagicMock()
        mock_list_scraper.fetch_race_urls.return_value = [
            "https://db.netkeiba.com/race/202606010101/",
        ]
        mock_race_list_scraper.return_value = mock_list_scraper

        # ShutubaScraper mock
        mock_shutuba = MagicMock()
        entry1 = RaceEntry(
            horse_id="2021101234",
            horse_name="取得済み",
            horse_number=1,
            bracket_number=1,
            jockey_id="00001",
            jockey_name="騎手1",
            impost=58.0,
        )
        entry2 = RaceEntry(
            horse_id="2021101235",
            horse_name="未取得",
            horse_number=2,
            bracket_number=2,
            jockey_id="00002",
            jockey_name="騎手2",
            impost=58.0,
        )
        mock_shutuba_data = MagicMock(entries=(entry1, entry2))
        mock_shutuba.fetch_shutuba.return_value = mock_shutuba_data
        mock_shutuba_scraper.return_value = mock_shutuba

        # Horse query mock (1頭は sire あり、もう1頭は sire なし)
        horse1 = Horse(
            id="2021101234",
            name="取得済み",
            sex="牡",
            birth_year=2021,
            sire="既存父馬",  # sire あり
        )
        horse2 = Horse(
            id="2021101235", name="未取得", sex="牡", birth_year=2021, sire=None  # sire なし
        )
        mock_session.get.side_effect = lambda model, id: {
            "2021101234": horse1,
            "2021101235": horse2,
        }.get(id)

        # HorseDetailScraper mock
        mock_detail_scraper = MagicMock()
        mock_detail_scraper.fetch_horse_detail.return_value = {
            "name": "テストホース",
            "sire": "父馬",
        }
        mock_horse_detail_scraper.return_value = mock_detail_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "scrape-horses",
                    "--db",
                    "test.db",
                    "--date",
                    "2026-06-01",
                ],
            )

        # HorseDetailScraper は未取得の1頭のみ呼ばれること
        assert mock_detail_scraper.fetch_horse_detail.call_count == 1
        mock_detail_scraper.fetch_horse_detail.assert_called_with("2021101235")


class TestScrapeHorsesMissingHorseRecords:
    """DB未登録馬のハンドリングテスト"""

    @patch("keiba.cli.commands.scrape.HorseDetailScraper")
    @patch("keiba.cli.commands.scrape.ShutubaScraper")
    @patch("keiba.cli.commands.scrape.RaceListScraper")
    @patch("keiba.cli.commands.scrape.get_session")
    @patch("keiba.cli.commands.scrape.get_engine")
    @patch("keiba.cli.commands.scrape.init_db")
    def test_creates_missing_horse_records(
        self,
        mock_init_db,
        mock_get_engine,
        mock_get_session,
        mock_race_list_scraper,
        mock_shutuba_scraper,
        mock_horse_detail_scraper,
    ):
        """DB未登録の馬のレコードを作成すること"""
        # Mock setup
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # RaceListScraper mock
        mock_list_scraper = MagicMock()
        mock_list_scraper.fetch_race_urls.return_value = [
            "https://db.netkeiba.com/race/202606010101/",
        ]
        mock_race_list_scraper.return_value = mock_list_scraper

        # ShutubaScraper mock
        mock_shutuba = MagicMock()
        entry = RaceEntry(
            horse_id="2021101234",
            horse_name="新規馬",
            horse_number=1,
            bracket_number=1,
            jockey_id="00001",
            jockey_name="騎手1",
            impost=58.0,
        )
        mock_shutuba_data = MagicMock(entries=(entry,))
        mock_shutuba.fetch_shutuba.return_value = mock_shutuba_data
        mock_shutuba_scraper.return_value = mock_shutuba

        # Horse query mock (DB に存在しない)
        mock_session.get.return_value = None

        # HorseDetailScraper mock
        mock_detail_scraper = MagicMock()
        mock_detail_scraper.fetch_horse_detail.return_value = {
            "name": "新規馬",
            "sex": "牡",
            "birth_year": 2021,
            "sire": "父馬",
        }
        mock_horse_detail_scraper.return_value = mock_detail_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "scrape-horses",
                    "--db",
                    "test.db",
                    "--date",
                    "2026-06-01",
                ],
            )

        # session.add が呼ばれて新規馬が作成されたこと
        assert mock_session.add.called
        # HorseDetailScraper が呼ばれたこと
        assert mock_detail_scraper.fetch_horse_detail.call_count == 1


class TestScrapeHorsesLegacyLimitMode:
    """既存の --limit モードが変更されていないことのテスト"""

    @patch("keiba.cli.commands.scrape.HorseDetailScraper")
    @patch("keiba.cli.commands.scrape.get_session")
    @patch("keiba.cli.commands.scrape.get_engine")
    @patch("keiba.cli.commands.scrape.init_db")
    def test_legacy_limit_mode_works(
        self,
        mock_init_db,
        mock_get_engine,
        mock_get_session,
        mock_horse_detail_scraper,
    ):
        """--date を指定しない場合、従来の --limit モードで動作すること"""
        # Mock setup
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Query mock (sire が NULL の馬を返す)
        horse = Horse(id="2021101234", name="テストホース", sex="不明", birth_year=0)
        mock_query = MagicMock()
        mock_query.filter.return_value.limit.return_value.all.return_value = [horse]
        mock_session.query.return_value = mock_query

        # HorseDetailScraper mock
        mock_detail_scraper = MagicMock()
        mock_detail_scraper.fetch_horse_detail.return_value = {
            "name": "テストホース",
            "sire": "父馬",
        }
        mock_horse_detail_scraper.return_value = mock_detail_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "scrape-horses",
                    "--db",
                    "test.db",
                    "--limit",
                    "5",
                ],
            )

        # Query で limit が呼ばれたこと
        mock_query.filter.return_value.limit.assert_called_with(5)
        # HorseDetailScraper が呼ばれたこと
        assert mock_detail_scraper.fetch_horse_detail.call_count == 1


# =============================================================================
# Task 2d: CLI出力改善のテスト
# =============================================================================


class TestScrapeHorsesVerboseOutput:
    """--verbose モードの出力テスト"""

    @patch("keiba.cli.commands.scrape.HorseDetailScraper")
    @patch("keiba.cli.commands.scrape.get_session")
    @patch("keiba.cli.commands.scrape.get_engine")
    @patch("keiba.cli.commands.scrape.init_db")
    def test_verbose_mode_shows_parsed_fields(
        self,
        mock_init_db,
        mock_get_engine,
        mock_get_session,
        mock_horse_detail_scraper,
    ):
        """--verbose でパース結果（取得できたフィールド）が表示される"""
        # Mock setup
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Query mock (sire が NULL の馬を返す)
        horse = Horse(id="2021101234", name="テストホース", sex="不明", birth_year=0)
        mock_query = MagicMock()
        mock_query.filter.return_value.limit.return_value.all.return_value = [horse]
        mock_session.query.return_value = mock_query

        # HorseDetailScraper mock
        mock_detail_scraper = MagicMock()
        mock_detail_scraper.fetch_horse_detail.return_value = {
            "name": "テストホース",
            "sire": "父馬",
            "dam": "母馬",
        }
        mock_horse_detail_scraper.return_value = mock_detail_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "scrape-horses",
                    "--db",
                    "test.db",
                    "--limit",
                    "1",
                    "--verbose",
                ],
            )

        # --verbose モードで取得したフィールドが表示される
        assert result.exit_code == 0
        assert "sire" in result.output or "父" in result.output
        assert "dam" in result.output or "母" in result.output


class TestScrapeHorsesWarnings:
    """警告出力のテスト"""

    @patch("keiba.cli.commands.scrape.HorseDetailScraper")
    @patch("keiba.cli.commands.scrape.get_session")
    @patch("keiba.cli.commands.scrape.get_engine")
    @patch("keiba.cli.commands.scrape.init_db")
    def test_warning_when_zero_fields_updated(
        self,
        mock_init_db,
        mock_get_engine,
        mock_get_session,
        mock_horse_detail_scraper,
    ):
        """更新フィールドが0の場合に警告が出る"""
        # Mock setup
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Query mock
        horse = Horse(id="2021101234", name="テストホース", sex="不明", birth_year=0)
        mock_query = MagicMock()
        mock_query.filter.return_value.limit.return_value.all.return_value = [horse]
        mock_session.query.return_value = mock_query

        # HorseDetailScraper mock (空データを返す)
        mock_detail_scraper = MagicMock()
        mock_detail_scraper.fetch_horse_detail.return_value = {}
        mock_horse_detail_scraper.return_value = mock_detail_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "scrape-horses",
                    "--db",
                    "test.db",
                    "--limit",
                    "1",
                ],
            )

        # 0フィールド更新時に警告が表示される
        assert result.exit_code == 0
        assert "警告" in result.output or "warning" in result.output.lower()


class TestScrapeHorsesSummaryOutput:
    """サマリー出力のテスト"""

    @patch("keiba.cli.commands.scrape.HorseDetailScraper")
    @patch("keiba.cli.commands.scrape.get_session")
    @patch("keiba.cli.commands.scrape.get_engine")
    @patch("keiba.cli.commands.scrape.init_db")
    def test_summary_shows_actual_update_count(
        self,
        mock_init_db,
        mock_get_engine,
        mock_get_session,
        mock_horse_detail_scraper,
    ):
        """サマリーに実際の更新馬数が表示される"""
        # Mock setup
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Query mock (2頭返す)
        horse1 = Horse(id="2021101234", name="馬1", sex="不明", birth_year=0)
        horse2 = Horse(id="2021101235", name="馬2", sex="不明", birth_year=0)
        mock_query = MagicMock()
        mock_query.filter.return_value.limit.return_value.all.return_value = [
            horse1,
            horse2,
        ]
        mock_session.query.return_value = mock_query

        # HorseDetailScraper mock (1頭目は成功、2頭目は空データ)
        mock_detail_scraper = MagicMock()
        mock_detail_scraper.fetch_horse_detail.side_effect = [
            {"name": "馬1", "sire": "父馬1"},  # 2フィールド更新
            {},  # 0フィールド更新
        ]
        mock_horse_detail_scraper.return_value = mock_detail_scraper

        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                main,
                [
                    "scrape-horses",
                    "--db",
                    "test.db",
                    "--limit",
                    "2",
                ],
            )

        # サマリーに「実際に更新した馬数」が表示される
        # 処理数: 2、実際の更新: 1（1頭のみ実際に更新された）
        assert result.exit_code == 0
        assert "処理数: 2" in result.output or "処理数:2" in result.output
        # 実際の更新数は1頭のみ
        assert "実際の更新: 1" in result.output or "更新成功: 1" in result.output
