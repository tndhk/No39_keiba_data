"""Tests for keiba.scrapers module."""

import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup

from keiba.scrapers.base import BaseScraper
from keiba.scrapers.race_list import RaceListScraper


class TestBaseScraperInit:
    """BaseScraper初期化のテスト"""

    def test_default_delay(self):
        """デフォルトのdelay値は1.0秒"""
        scraper = BaseScraper()
        assert scraper.delay == 1.0

    def test_custom_delay(self):
        """カスタムdelay値を設定できる"""
        scraper = BaseScraper(delay=2.5)
        assert scraper.delay == 2.5

    def test_last_request_time_initially_none(self):
        """初期状態では_last_request_timeはNone"""
        scraper = BaseScraper()
        assert scraper._last_request_time is None

    def test_has_default_user_agent(self):
        """DEFAULT_USER_AGENTクラス属性が存在する"""
        assert hasattr(BaseScraper, "DEFAULT_USER_AGENT")
        assert "Mozilla" in BaseScraper.DEFAULT_USER_AGENT


class TestBaseScraperFetch:
    """BaseScraper.fetch()のテスト"""

    @patch("keiba.scrapers.base.requests.get")
    def test_fetch_returns_html_text(self, mock_get):
        """fetch()はHTMLテキストを返す"""
        mock_response = Mock()
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=0)
        html = scraper.fetch("https://example.com")

        assert html == "<html><body>Test</body></html>"

    @patch("keiba.scrapers.base.requests.get")
    def test_fetch_uses_user_agent(self, mock_get):
        """fetch()はUser-Agentヘッダーを設定する"""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=0)
        scraper.fetch("https://example.com")

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert "headers" in call_kwargs
        assert "User-Agent" in call_kwargs["headers"]
        assert call_kwargs["headers"]["User-Agent"] == BaseScraper.DEFAULT_USER_AGENT

    @patch("keiba.scrapers.base.requests.get")
    def test_fetch_updates_last_request_time(self, mock_get):
        """fetch()は_last_request_timeを更新する"""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=0)
        assert scraper._last_request_time is None

        scraper.fetch("https://example.com")

        assert scraper._last_request_time is not None
        assert isinstance(scraper._last_request_time, float)

    @patch("keiba.scrapers.base.requests.get")
    @patch("keiba.scrapers.base.time.sleep")
    def test_fetch_applies_delay_on_second_request(self, mock_sleep, mock_get):
        """2回目のリクエストではdelayが適用される"""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=1.0)

        # 1回目のリクエスト - sleepなし
        scraper.fetch("https://example.com/page1")
        assert mock_sleep.call_count == 0

        # _last_request_timeを直前に設定してdelayが必要な状況を作る
        scraper._last_request_time = time.time()

        # 2回目のリクエスト - sleepあり
        scraper.fetch("https://example.com/page2")
        assert mock_sleep.call_count == 1

    @patch("keiba.scrapers.base.requests.get")
    @patch("keiba.scrapers.base.time.sleep")
    def test_fetch_no_delay_if_enough_time_passed(self, mock_sleep, mock_get):
        """十分な時間が経過していればdelayは適用されない"""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=1.0)
        # 2秒前にリクエストしたことにする
        scraper._last_request_time = time.time() - 2.0

        scraper.fetch("https://example.com")

        # 十分な時間が経過しているのでsleepは呼ばれない
        mock_sleep.assert_not_called()

    @patch("keiba.scrapers.base.requests.get")
    def test_fetch_calls_raise_for_status(self, mock_get):
        """fetch()はraise_for_status()を呼び出す"""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        scraper = BaseScraper(delay=0)
        scraper.fetch("https://example.com")

        mock_response.raise_for_status.assert_called_once()


class TestBaseScraperGetSoup:
    """BaseScraper.get_soup()のテスト"""

    def test_get_soup_returns_beautifulsoup(self):
        """get_soup()はBeautifulSoupオブジェクトを返す"""
        scraper = BaseScraper()
        html = "<html><body><p>Test</p></body></html>"

        soup = scraper.get_soup(html)

        assert isinstance(soup, BeautifulSoup)

    def test_get_soup_parses_html_correctly(self):
        """get_soup()はHTMLを正しくパースする"""
        scraper = BaseScraper()
        html = "<html><body><p class='test'>Hello World</p></body></html>"

        soup = scraper.get_soup(html)

        p_tag = soup.find("p", class_="test")
        assert p_tag is not None
        assert p_tag.text == "Hello World"

    def test_get_soup_uses_lxml_parser(self):
        """get_soup()はlxmlパーサーを使用する"""
        scraper = BaseScraper()
        # lxmlは不正なHTMLも適切に処理する
        html = "<p>Unclosed paragraph"

        soup = scraper.get_soup(html)

        # lxmlパーサーは適切にパースできる
        assert soup.find("p") is not None


class TestBaseScraperParse:
    """BaseScraper.parse()のテスト"""

    def test_parse_raises_not_implemented(self):
        """parse()はNotImplementedErrorを発生させる"""
        scraper = BaseScraper()
        soup = BeautifulSoup("<html></html>", "lxml")

        with pytest.raises(NotImplementedError):
            scraper.parse(soup)


class TestBaseScraperSubclass:
    """BaseScraperのサブクラス化テスト"""

    def test_subclass_can_implement_parse(self):
        """サブクラスでparse()を実装できる"""

        class MyScraper(BaseScraper):
            def parse(self, soup: BeautifulSoup) -> dict:
                title = soup.find("title")
                return {"title": title.text if title else None}

        scraper = MyScraper()
        html = "<html><head><title>Test Page</title></head></html>"
        soup = scraper.get_soup(html)
        result = scraper.parse(soup)

        assert result == {"title": "Test Page"}


# =============================================================================
# RaceListScraper Tests
# =============================================================================


@pytest.fixture
def race_list_html():
    """テスト用HTMLフィクスチャを読み込む"""
    fixture_path = Path(__file__).parent / "fixtures" / "race_list.html"
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def race_list_scraper():
    """RaceListScraperインスタンスを返す"""
    return RaceListScraper(delay=0)


class TestRaceListScraperInit:
    """RaceListScraper初期化のテスト"""

    def test_inherits_from_base_scraper(self):
        """RaceListScraperはBaseScraperを継承している"""
        scraper = RaceListScraper()
        assert isinstance(scraper, BaseScraper)

    def test_default_delay(self):
        """デフォルトのdelay値を継承する"""
        scraper = RaceListScraper()
        assert scraper.delay == 1.0

    def test_custom_delay(self):
        """カスタムdelay値を設定できる"""
        scraper = RaceListScraper(delay=2.0)
        assert scraper.delay == 2.0

    def test_base_url_attribute(self):
        """BASE_URL属性が正しく設定されている"""
        assert RaceListScraper.BASE_URL == "https://race.netkeiba.com"


class TestRaceListScraperParse:
    """RaceListScraper.parse()のテスト"""

    def test_parse_returns_list(self, race_list_scraper, race_list_html):
        """parse()はリストを返す"""
        soup = race_list_scraper.get_soup(race_list_html)
        result = race_list_scraper.parse(soup)
        assert isinstance(result, list)

    def test_parse_extracts_all_race_urls(self, race_list_scraper, race_list_html):
        """parse()は全てのレースURLを抽出する"""
        soup = race_list_scraper.get_soup(race_list_html)
        result = race_list_scraper.parse(soup)
        # フィクスチャには5つのレースリンクがある
        assert len(result) == 5

    def test_parse_returns_full_urls(self, race_list_scraper, race_list_html):
        """parse()は完全なURLを返す"""
        soup = race_list_scraper.get_soup(race_list_html)
        result = race_list_scraper.parse(soup)
        for url in result:
            assert url.startswith("https://race.netkeiba.com/race/")
            assert url.endswith(".html")

    def test_parse_extracts_correct_race_ids(self, race_list_scraper, race_list_html):
        """parse()は正しいレースIDを含むURLを抽出する"""
        soup = race_list_scraper.get_soup(race_list_html)
        result = race_list_scraper.parse(soup)
        expected_race_ids = [
            "202401010101",
            "202401010102",
            "202401010103",
            "202401010201",
            "202401010202",
        ]
        for race_id in expected_race_ids:
            expected_url = f"https://race.netkeiba.com/race/{race_id}.html"
            assert expected_url in result

    def test_parse_excludes_non_race_links(self, race_list_scraper, race_list_html):
        """parse()はレース以外のリンクを除外する"""
        soup = race_list_scraper.get_soup(race_list_html)
        result = race_list_scraper.parse(soup)
        # 馬情報や騎手情報のリンクは含まれない
        for url in result:
            assert "/horse/" not in url
            assert "/jockey/" not in url

    def test_parse_with_empty_html(self, race_list_scraper):
        """空のHTMLでは空のリストを返す"""
        soup = race_list_scraper.get_soup("<html><body></body></html>")
        result = race_list_scraper.parse(soup)
        assert result == []

    def test_parse_with_no_race_links(self, race_list_scraper):
        """レースリンクがない場合は空のリストを返す"""
        html = """
        <html><body>
        <div class="RaceList">
            <a href="/horse/123.html">馬情報</a>
        </div>
        </body></html>
        """
        soup = race_list_scraper.get_soup(html)
        result = race_list_scraper.parse(soup)
        assert result == []


class TestRaceListScraperBuildUrl:
    """RaceListScraper._build_url()のテスト"""

    def test_build_url_formats_date_correctly(self, race_list_scraper):
        """_build_url()は日付を正しくフォーマットする"""
        url = race_list_scraper._build_url(year=2024, month=1, day=1)
        assert url == "https://race.netkeiba.com/top/race_list.html?kaisai_date=20240101"

    def test_build_url_pads_month_and_day(self, race_list_scraper):
        """_build_url()は月と日をゼロパディングする"""
        url = race_list_scraper._build_url(year=2024, month=12, day=25)
        assert url == "https://race.netkeiba.com/top/race_list.html?kaisai_date=20241225"

    def test_build_url_with_single_digit_month(self, race_list_scraper):
        """1桁の月でもゼロパディングする"""
        url = race_list_scraper._build_url(year=2024, month=5, day=15)
        assert "kaisai_date=20240515" in url

    def test_build_url_with_single_digit_day(self, race_list_scraper):
        """1桁の日でもゼロパディングする"""
        url = race_list_scraper._build_url(year=2024, month=10, day=3)
        assert "kaisai_date=20241003" in url


class TestRaceListScraperFetchRaceUrls:
    """RaceListScraper.fetch_race_urls()のテスト"""

    @patch.object(RaceListScraper, "fetch")
    def test_fetch_race_urls_calls_fetch_with_correct_url(
        self, mock_fetch, race_list_scraper, race_list_html
    ):
        """fetch_race_urls()は正しいURLでfetch()を呼び出す"""
        mock_fetch.return_value = race_list_html

        race_list_scraper.fetch_race_urls(year=2024, month=1, day=1)

        mock_fetch.assert_called_once_with(
            "https://race.netkeiba.com/top/race_list.html?kaisai_date=20240101"
        )

    @patch.object(RaceListScraper, "fetch")
    def test_fetch_race_urls_returns_list_of_urls(
        self, mock_fetch, race_list_scraper, race_list_html
    ):
        """fetch_race_urls()はURLのリストを返す"""
        mock_fetch.return_value = race_list_html

        result = race_list_scraper.fetch_race_urls(year=2024, month=1, day=1)

        assert isinstance(result, list)
        assert len(result) == 5
        assert all(url.startswith("https://") for url in result)

    @patch.object(RaceListScraper, "fetch")
    def test_fetch_race_urls_integration(
        self, mock_fetch, race_list_scraper, race_list_html
    ):
        """fetch_race_urls()の統合テスト"""
        mock_fetch.return_value = race_list_html

        result = race_list_scraper.fetch_race_urls(year=2024, month=1, day=1)

        expected_urls = [
            "https://race.netkeiba.com/race/202401010101.html",
            "https://race.netkeiba.com/race/202401010102.html",
            "https://race.netkeiba.com/race/202401010103.html",
            "https://race.netkeiba.com/race/202401010201.html",
            "https://race.netkeiba.com/race/202401010202.html",
        ]
        assert result == expected_urls
