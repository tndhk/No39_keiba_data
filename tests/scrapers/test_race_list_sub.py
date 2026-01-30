"""Tests for keiba.scrapers.race_list_sub module."""

from pathlib import Path
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup

from keiba.scrapers.base import BaseScraper


@pytest.fixture
def race_list_sub_html():
    """テスト用HTMLフィクスチャを読み込む"""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "race_list_sub.html"
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def race_list_sub_scraper():
    """RaceListSubScraper インスタンスを返す"""
    from keiba.scrapers.race_list_sub import RaceListSubScraper
    return RaceListSubScraper(delay=0)


class TestRaceListSubScraperInit:
    """RaceListSubScraper 初期化のテスト"""

    def test_inherits_from_base_scraper(self, race_list_sub_scraper):
        """RaceListSubScraper は BaseScraper を継承している"""
        assert isinstance(race_list_sub_scraper, BaseScraper)

    def test_default_delay(self):
        """デフォルトの delay 値を継承する"""
        from keiba.scrapers.race_list_sub import RaceListSubScraper
        scraper = RaceListSubScraper()
        assert scraper.delay == 1.0

    def test_custom_delay(self):
        """カスタム delay 値を設定できる"""
        from keiba.scrapers.race_list_sub import RaceListSubScraper
        scraper = RaceListSubScraper(delay=2.0)
        assert scraper.delay == 2.0


class TestRaceListSubScraperParse:
    """RaceListSubScraper.parse() のテスト"""

    def test_parse_extracts_race_ids(self, race_list_sub_scraper, race_list_sub_html):
        """HTMLからrace_idを抽出できる"""
        race_ids = race_list_sub_scraper.parse(race_list_sub_html)

        assert isinstance(race_ids, list)
        assert len(race_ids) == 36
        assert "202605010201" in race_ids
        assert "202605010212" in race_ids

    def test_parse_returns_unique_race_ids(self, race_list_sub_scraper, race_list_sub_html):
        """重複するrace_idは除外される"""
        race_ids = race_list_sub_scraper.parse(race_list_sub_html)

        assert len(race_ids) == len(set(race_ids))

    def test_parse_empty_html_returns_empty_list(self, race_list_sub_scraper):
        """race_idが存在しないHTMLでは空リストを返す"""
        html = "<html><body>No races</body></html>"
        race_ids = race_list_sub_scraper.parse(html)

        assert race_ids == []


class TestRaceListSubScraperFetchRaceIds:
    """RaceListSubScraper.fetch_race_ids() のテスト"""

    @patch('keiba.scrapers.race_list_sub.RaceListSubScraper.fetch')
    def test_fetch_race_ids_returns_all_race_ids(self, mock_fetch, race_list_sub_scraper, race_list_sub_html):
        """fetch_race_ids() はすべてのrace_idを返す"""
        mock_fetch.return_value = race_list_sub_html

        race_ids = race_list_sub_scraper.fetch_race_ids(year=2026, month=2, day=1)

        assert len(race_ids) == 36
        assert "202605010201" in race_ids
        mock_fetch.assert_called_once()

    @patch('keiba.scrapers.race_list_sub.RaceListSubScraper.fetch')
    def test_fetch_race_ids_with_jra_only_filters_correctly(self, mock_fetch, race_list_sub_scraper, race_list_sub_html):
        """jra_only=True でJRA競馬場のみをフィルタする"""
        mock_fetch.return_value = race_list_sub_html

        race_ids = race_list_sub_scraper.fetch_race_ids(year=2026, month=2, day=1, jra_only=True)

        # すべてのrace_idがJRAコード（01-10）である
        for race_id in race_ids:
            course_code = race_id[4:6]
            assert course_code in ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]

    @patch('keiba.scrapers.race_list_sub.RaceListSubScraper.fetch')
    def test_fetch_race_ids_constructs_correct_url(self, mock_fetch, race_list_sub_scraper, race_list_sub_html):
        """正しいURLを構築してfetch()を呼び出す"""
        mock_fetch.return_value = race_list_sub_html

        race_list_sub_scraper.fetch_race_ids(year=2026, month=2, day=1)

        expected_url = "https://race.netkeiba.com/top/race_list_sub.html?kaisai_date=20260201"
        mock_fetch.assert_called_once_with(expected_url)
