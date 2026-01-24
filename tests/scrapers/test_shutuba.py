"""Tests for keiba.scrapers.shutuba module."""

from pathlib import Path
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup

from keiba.scrapers.base import BaseScraper


@pytest.fixture
def shutuba_html():
    """テスト用HTMLフィクスチャを読み込む"""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "shutuba.html"
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def shutuba_scraper():
    """ShutubaScraper インスタンスを返す"""
    from keiba.scrapers.shutuba import ShutubaScraper
    return ShutubaScraper(delay=0)


class TestShutubaScraperInit:
    """ShutubaScraper 初期化のテスト"""

    def test_inherits_from_base_scraper(self, shutuba_scraper):
        """ShutubaScraper は BaseScraper を継承している"""
        assert isinstance(shutuba_scraper, BaseScraper)

    def test_default_delay(self):
        """デフォルトの delay 値を継承する"""
        from keiba.scrapers.shutuba import ShutubaScraper
        scraper = ShutubaScraper()
        assert scraper.delay == 1.0

    def test_custom_delay(self):
        """カスタム delay 値を設定できる"""
        from keiba.scrapers.shutuba import ShutubaScraper
        scraper = ShutubaScraper(delay=2.0)
        assert scraper.delay == 2.0

    def test_base_url_attribute(self, shutuba_scraper):
        """BASE_URL 属性が正しく設定されている"""
        from keiba.scrapers.shutuba import ShutubaScraper
        assert ShutubaScraper.BASE_URL == "https://race.netkeiba.com"


class TestShutubaScraperParseEntriesExtractsHorseInfo:
    """test_parse_entries_extracts_horse_info: 馬ID、馬名、馬番、枠番の抽出"""

    def test_extracts_horse_id(self, shutuba_scraper, shutuba_html):
        """馬IDを正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        entries = shutuba_scraper._parse_entries(soup)

        assert len(entries) == 5
        assert entries[0].horse_id == "2023104001"
        assert entries[1].horse_id == "2023104002"
        assert entries[2].horse_id == "2023104003"

    def test_extracts_horse_name(self, shutuba_scraper, shutuba_html):
        """馬名を正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        entries = shutuba_scraper._parse_entries(soup)

        assert entries[0].horse_name == "テストホース1"
        assert entries[1].horse_name == "テストホース2"
        assert entries[2].horse_name == "テストホース3"

    def test_extracts_horse_number(self, shutuba_scraper, shutuba_html):
        """馬番を正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        entries = shutuba_scraper._parse_entries(soup)

        assert entries[0].horse_number == 1
        assert entries[1].horse_number == 2
        assert entries[2].horse_number == 3

    def test_extracts_bracket_number(self, shutuba_scraper, shutuba_html):
        """枠番を正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        entries = shutuba_scraper._parse_entries(soup)

        assert entries[0].bracket_number == 1
        assert entries[1].bracket_number == 2
        assert entries[2].bracket_number == 3


class TestShutubaScraperParseEntriesExtractsJockeyInfo:
    """test_parse_entries_extracts_jockey_info: 騎手ID、騎手名の抽出"""

    def test_extracts_jockey_id(self, shutuba_scraper, shutuba_html):
        """騎手IDを正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        entries = shutuba_scraper._parse_entries(soup)

        assert entries[0].jockey_id == "01167"
        assert entries[1].jockey_id == "01180"
        assert entries[3].jockey_id == "a0257"  # 英数字IDも対応

    def test_extracts_jockey_name(self, shutuba_scraper, shutuba_html):
        """騎手名を正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        entries = shutuba_scraper._parse_entries(soup)

        assert entries[0].jockey_name == "武豊"
        assert entries[1].jockey_name == "ルメール"
        assert entries[2].jockey_name == "横山和生"


class TestShutubaScraperParseEntriesExtractsImpost:
    """test_parse_entries_extracts_impost: 斤量の抽出"""

    def test_extracts_impost(self, shutuba_scraper, shutuba_html):
        """斤量を正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        entries = shutuba_scraper._parse_entries(soup)

        assert entries[0].impost == 56.0
        assert entries[1].impost == 54.0
        assert entries[4].impost == 57.0


class TestShutubaScraperParseEntriesExtractsSexAge:
    """性別と年齢の抽出"""

    def test_extracts_sex(self, shutuba_scraper, shutuba_html):
        """性別を正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        entries = shutuba_scraper._parse_entries(soup)

        assert entries[0].sex == "牡"
        assert entries[1].sex == "牝"
        assert entries[3].sex == "セ"  # セン馬

    def test_extracts_age(self, shutuba_scraper, shutuba_html):
        """年齢を正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        entries = shutuba_scraper._parse_entries(soup)

        assert entries[0].age == 3
        assert entries[1].age == 3


class TestShutubaScraperFetchShutuba:
    """test_fetch_shutuba_returns_shutuba_data: ShutubaData の返却確認"""

    @patch.object(BaseScraper, "fetch")
    def test_returns_shutuba_data(self, mock_fetch, shutuba_scraper, shutuba_html):
        """fetch_shutuba は ShutubaData を返す"""
        from keiba.scrapers.shutuba import ShutubaData
        mock_fetch.return_value = shutuba_html

        result = shutuba_scraper.fetch_shutuba(race_id="202606010802")

        assert isinstance(result, ShutubaData)

    @patch.object(BaseScraper, "fetch")
    def test_contains_entries(self, mock_fetch, shutuba_scraper, shutuba_html):
        """ShutubaData は entries を含む"""
        mock_fetch.return_value = shutuba_html

        result = shutuba_scraper.fetch_shutuba(race_id="202606010802")

        assert hasattr(result, "entries")
        assert len(result.entries) == 5

    @patch.object(BaseScraper, "fetch")
    def test_contains_race_info(self, mock_fetch, shutuba_scraper, shutuba_html):
        """ShutubaData は race_info を含む"""
        mock_fetch.return_value = shutuba_html

        result = shutuba_scraper.fetch_shutuba(race_id="202606010802")

        assert hasattr(result, "race_id")
        assert result.race_id == "202606010802"


class TestShutubaScraperExtractRaceInfo:
    """test_extract_race_info: レースID、レース名、開催情報の抽出"""

    def test_extracts_race_name(self, shutuba_scraper, shutuba_html):
        """レース名を正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        race_info = shutuba_scraper._parse_race_info(soup)

        assert race_info["race_name"] == "第65回京成杯(G3)"

    def test_extracts_race_number(self, shutuba_scraper, shutuba_html):
        """レース番号を正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        race_info = shutuba_scraper._parse_race_info(soup)

        assert race_info["race_number"] == 11

    def test_extracts_course(self, shutuba_scraper, shutuba_html):
        """開催場所を正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        race_info = shutuba_scraper._parse_race_info(soup)

        assert race_info["course"] == "中山"

    def test_extracts_distance(self, shutuba_scraper, shutuba_html):
        """距離を正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        race_info = shutuba_scraper._parse_race_info(soup)

        assert race_info["distance"] == 2000

    def test_extracts_surface(self, shutuba_scraper, shutuba_html):
        """馬場を正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        race_info = shutuba_scraper._parse_race_info(soup)

        assert race_info["surface"] == "芝"

    def test_extracts_date(self, shutuba_scraper, shutuba_html):
        """日付を正しく抽出する"""
        soup = shutuba_scraper.get_soup(shutuba_html)
        race_info = shutuba_scraper._parse_race_info(soup)

        assert race_info["date"] == "2026年1月8日"


class TestShutubaScraperBuildUrl:
    """ShutubaScraper._build_url() のテスト"""

    def test_build_url_formats_race_id_correctly(self, shutuba_scraper):
        """_build_url() はレースIDを正しくフォーマットする"""
        url = shutuba_scraper._build_url(race_id="202606010802")
        assert url == "https://race.netkeiba.com/race/shutuba.html?race_id=202606010802"


class TestShutubaScraperEmptyHtml:
    """空のHTMLに対するテスト"""

    def test_parse_entries_returns_empty_list_for_empty_html(self, shutuba_scraper):
        """空のHTMLでは空のリストを返す"""
        soup = shutuba_scraper.get_soup("<html><body></body></html>")
        entries = shutuba_scraper._parse_entries(soup)
        assert entries == []

    def test_parse_race_info_returns_empty_dict_for_empty_html(self, shutuba_scraper):
        """空のHTMLでは空の辞書を返す（必須キーのみ）"""
        soup = shutuba_scraper.get_soup("<html><body></body></html>")
        race_info = shutuba_scraper._parse_race_info(soup)
        # 空HTMLでもデフォルト値が設定される
        assert isinstance(race_info, dict)
