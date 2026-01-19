"""Tests for keiba.scrapers module."""

import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup

from keiba.scrapers.base import BaseScraper
from keiba.scrapers.horse_detail import HorseDetailScraper
from keiba.scrapers.race_list import RaceListScraper
from keiba.scrapers.race_detail import RaceDetailScraper


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
        assert RaceListScraper.BASE_URL == "https://db.netkeiba.com"


class TestRaceListScraperIsJraRace:
    """RaceListScraper.is_jra_race()のテスト"""

    def test_jra_race_sapporo(self):
        """札幌競馬場（01）はJRA"""
        url = "https://db.netkeiba.com/race/202401010101/"
        assert RaceListScraper.is_jra_race(url) is True

    def test_jra_race_hakodate(self):
        """函館競馬場（02）はJRA"""
        url = "https://db.netkeiba.com/race/202402010101/"
        assert RaceListScraper.is_jra_race(url) is True

    def test_jra_race_fukushima(self):
        """福島競馬場（03）はJRA"""
        url = "https://db.netkeiba.com/race/202403010101/"
        assert RaceListScraper.is_jra_race(url) is True

    def test_jra_race_niigata(self):
        """新潟競馬場（04）はJRA"""
        url = "https://db.netkeiba.com/race/202404010101/"
        assert RaceListScraper.is_jra_race(url) is True

    def test_jra_race_tokyo(self):
        """東京競馬場（05）はJRA"""
        url = "https://db.netkeiba.com/race/202405010101/"
        assert RaceListScraper.is_jra_race(url) is True

    def test_jra_race_nakayama(self):
        """中山競馬場（06）はJRA"""
        url = "https://db.netkeiba.com/race/202406010101/"
        assert RaceListScraper.is_jra_race(url) is True

    def test_jra_race_chukyo(self):
        """中京競馬場（07）はJRA"""
        url = "https://db.netkeiba.com/race/202407010101/"
        assert RaceListScraper.is_jra_race(url) is True

    def test_jra_race_kyoto(self):
        """京都競馬場（08）はJRA"""
        url = "https://db.netkeiba.com/race/202408010101/"
        assert RaceListScraper.is_jra_race(url) is True

    def test_jra_race_hanshin(self):
        """阪神競馬場（09）はJRA"""
        url = "https://db.netkeiba.com/race/202409010101/"
        assert RaceListScraper.is_jra_race(url) is True

    def test_jra_race_kokura(self):
        """小倉競馬場（10）はJRA"""
        url = "https://db.netkeiba.com/race/202410010101/"
        assert RaceListScraper.is_jra_race(url) is True

    def test_nar_race_kawasaki(self):
        """川崎競馬場（45）はNAR"""
        url = "https://db.netkeiba.com/race/202445010101/"
        assert RaceListScraper.is_jra_race(url) is False

    def test_nar_race_ooi(self):
        """大井競馬場（42）はNAR"""
        url = "https://db.netkeiba.com/race/202442010101/"
        assert RaceListScraper.is_jra_race(url) is False

    def test_nar_race_funabashi(self):
        """船橋競馬場（43）はNAR"""
        url = "https://db.netkeiba.com/race/202443010101/"
        assert RaceListScraper.is_jra_race(url) is False

    def test_nar_race_monbetsu(self):
        """門別競馬場（30）はNAR"""
        url = "https://db.netkeiba.com/race/202430010101/"
        assert RaceListScraper.is_jra_race(url) is False

    def test_invalid_url_format(self):
        """不正なURLフォーマット"""
        url = "https://db.netkeiba.com/horse/2019104251/"
        assert RaceListScraper.is_jra_race(url) is False

    def test_invalid_race_id_too_short(self):
        """短すぎるレースID"""
        url = "https://db.netkeiba.com/race/2024010101/"
        assert RaceListScraper.is_jra_race(url) is False


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
        # フィクスチャには7つのレースリンクがある（JRA5 + NAR2）
        assert len(result) == 7

    def test_parse_returns_full_urls(self, race_list_scraper, race_list_html):
        """parse()は完全なURLを返す"""
        soup = race_list_scraper.get_soup(race_list_html)
        result = race_list_scraper.parse(soup)
        for url in result:
            assert url.startswith("https://db.netkeiba.com/race/")
            assert url.endswith("/")

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
            "202445010101",
            "202445010102",
        ]
        for race_id in expected_race_ids:
            expected_url = f"https://db.netkeiba.com/race/{race_id}/"
            assert expected_url in result

    def test_parse_jra_only_filters_nar_races(self, race_list_scraper, race_list_html):
        """parse(jra_only=True)は地方競馬を除外する"""
        soup = race_list_scraper.get_soup(race_list_html)
        result = race_list_scraper.parse(soup, jra_only=True)
        # JRAレースのみ5件
        assert len(result) == 5
        # 川崎競馬場（45）のレースは含まれない
        for url in result:
            assert "/race/202445" not in url

    def test_parse_jra_only_false_includes_all(self, race_list_scraper, race_list_html):
        """parse(jra_only=False)は全レースを返す"""
        soup = race_list_scraper.get_soup(race_list_html)
        result = race_list_scraper.parse(soup, jra_only=False)
        assert len(result) == 7

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
        assert url == "https://db.netkeiba.com/race/list/20240101/"

    def test_build_url_pads_month_and_day(self, race_list_scraper):
        """_build_url()は月と日をゼロパディングする"""
        url = race_list_scraper._build_url(year=2024, month=12, day=25)
        assert url == "https://db.netkeiba.com/race/list/20241225/"

    def test_build_url_with_single_digit_month(self, race_list_scraper):
        """1桁の月でもゼロパディングする"""
        url = race_list_scraper._build_url(year=2024, month=5, day=15)
        assert "/race/list/20240515/" in url

    def test_build_url_with_single_digit_day(self, race_list_scraper):
        """1桁の日でもゼロパディングする"""
        url = race_list_scraper._build_url(year=2024, month=10, day=3)
        assert "/race/list/20241003/" in url


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
            "https://db.netkeiba.com/race/list/20240101/"
        )

    @patch.object(RaceListScraper, "fetch")
    def test_fetch_race_urls_returns_list_of_urls(
        self, mock_fetch, race_list_scraper, race_list_html
    ):
        """fetch_race_urls()はURLのリストを返す"""
        mock_fetch.return_value = race_list_html

        result = race_list_scraper.fetch_race_urls(year=2024, month=1, day=1)

        assert isinstance(result, list)
        assert len(result) == 7  # JRA5 + NAR2
        assert all(url.startswith("https://") for url in result)

    @patch.object(RaceListScraper, "fetch")
    def test_fetch_race_urls_integration(
        self, mock_fetch, race_list_scraper, race_list_html
    ):
        """fetch_race_urls()の統合テスト"""
        mock_fetch.return_value = race_list_html

        result = race_list_scraper.fetch_race_urls(year=2024, month=1, day=1)

        expected_urls = [
            "https://db.netkeiba.com/race/202401010101/",
            "https://db.netkeiba.com/race/202401010102/",
            "https://db.netkeiba.com/race/202401010103/",
            "https://db.netkeiba.com/race/202401010201/",
            "https://db.netkeiba.com/race/202401010202/",
            "https://db.netkeiba.com/race/202445010101/",
            "https://db.netkeiba.com/race/202445010102/",
        ]
        assert result == expected_urls

    @patch.object(RaceListScraper, "fetch")
    def test_fetch_race_urls_jra_only(
        self, mock_fetch, race_list_scraper, race_list_html
    ):
        """fetch_race_urls(jra_only=True)はJRAレースのみを返す"""
        mock_fetch.return_value = race_list_html

        result = race_list_scraper.fetch_race_urls(
            year=2024, month=1, day=1, jra_only=True
        )

        assert len(result) == 5
        expected_urls = [
            "https://db.netkeiba.com/race/202401010101/",
            "https://db.netkeiba.com/race/202401010102/",
            "https://db.netkeiba.com/race/202401010103/",
            "https://db.netkeiba.com/race/202401010201/",
            "https://db.netkeiba.com/race/202401010202/",
        ]
        assert result == expected_urls


# =============================================================================
# RaceDetailScraper Tests
# =============================================================================


@pytest.fixture
def race_detail_html():
    """テスト用HTMLフィクスチャを読み込む"""
    fixture_path = Path(__file__).parent / "fixtures" / "race_detail.html"
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def race_detail_scraper():
    """RaceDetailScraperインスタンスを返す"""
    return RaceDetailScraper(delay=0)


class TestRaceDetailScraperInit:
    """RaceDetailScraper初期化のテスト"""

    def test_inherits_from_base_scraper(self):
        """RaceDetailScraperはBaseScraperを継承している"""
        scraper = RaceDetailScraper()
        assert isinstance(scraper, BaseScraper)

    def test_default_delay(self):
        """デフォルトのdelay値を継承する"""
        scraper = RaceDetailScraper()
        assert scraper.delay == 1.0

    def test_custom_delay(self):
        """カスタムdelay値を設定できる"""
        scraper = RaceDetailScraper(delay=2.0)
        assert scraper.delay == 2.0

    def test_base_url_attribute(self):
        """BASE_URL属性が正しく設定されている"""
        assert RaceDetailScraper.BASE_URL == "https://db.netkeiba.com"


class TestRaceDetailScraperParse:
    """RaceDetailScraper.parse()のテスト"""

    def test_parse_returns_dict(self, race_detail_scraper, race_detail_html):
        """parse()は辞書を返す"""
        soup = race_detail_scraper.get_soup(race_detail_html)
        result = race_detail_scraper.parse(soup, race_id="202401010101")
        assert isinstance(result, dict)

    def test_parse_returns_race_and_results_keys(
        self, race_detail_scraper, race_detail_html
    ):
        """parse()はraceとresultsキーを含む辞書を返す"""
        soup = race_detail_scraper.get_soup(race_detail_html)
        result = race_detail_scraper.parse(soup, race_id="202401010101")
        assert "race" in result
        assert "results" in result

    def test_parse_race_info(self, race_detail_scraper, race_detail_html):
        """parse()はレース情報を正しく抽出する"""
        soup = race_detail_scraper.get_soup(race_detail_html)
        result = race_detail_scraper.parse(soup, race_id="202401010101")
        race = result["race"]

        assert race["id"] == "202401010101"
        assert race["name"] == "有馬記念(G1)"
        assert race["date"] == "2024年12月22日"
        assert race["course"] == "中山"
        assert race["race_number"] == 11
        assert race["distance"] == 1600
        assert race["surface"] == "芝"
        assert race["weather"] == "晴"
        assert race["track_condition"] == "良"

    def test_parse_results_list(self, race_detail_scraper, race_detail_html):
        """parse()は結果リストを正しく抽出する"""
        soup = race_detail_scraper.get_soup(race_detail_html)
        result = race_detail_scraper.parse(soup, race_id="202401010101")
        results = result["results"]

        assert isinstance(results, list)
        assert len(results) == 5  # 5頭分のデータ

    def test_parse_first_place_horse(self, race_detail_scraper, race_detail_html):
        """parse()は1着馬の情報を正しく抽出する"""
        soup = race_detail_scraper.get_soup(race_detail_html)
        result = race_detail_scraper.parse(soup, race_id="202401010101")
        first_horse = result["results"][0]

        assert first_horse["finish_position"] == 1
        assert first_horse["bracket_number"] == 3
        assert first_horse["horse_number"] == 5
        assert first_horse["horse_id"] == "2019104251"
        assert first_horse["horse_name"] == "ドウデュース"
        assert first_horse["jockey_id"] == "01167"
        assert first_horse["jockey_name"] == "武豊"
        assert first_horse["trainer_id"] == "01088"
        assert first_horse["trainer_name"] == "友道康夫"
        assert first_horse["odds"] == 3.5
        assert first_horse["popularity"] == 2
        assert first_horse["weight"] == 512
        assert first_horse["weight_diff"] == 4
        assert first_horse["time"] == "2:31.2"
        assert first_horse["margin"] == ""

    def test_parse_second_place_horse(self, race_detail_scraper, race_detail_html):
        """parse()は2着馬の情報を正しく抽出する"""
        soup = race_detail_scraper.get_soup(race_detail_html)
        result = race_detail_scraper.parse(soup, race_id="202401010101")
        second_horse = result["results"][1]

        assert second_horse["finish_position"] == 2
        assert second_horse["bracket_number"] == 1
        assert second_horse["horse_number"] == 2
        assert second_horse["horse_id"] == "2020104567"
        assert second_horse["horse_name"] == "シャフリヤール"
        assert second_horse["jockey_id"] == "01178"
        assert second_horse["jockey_name"] == "クリスチャン・デムーロ"
        assert second_horse["trainer_id"] == "01095"
        assert second_horse["trainer_name"] == "藤原英昭"
        assert second_horse["odds"] == 8.2
        assert second_horse["popularity"] == 4
        assert second_horse["weight"] == 486
        assert second_horse["weight_diff"] == -2
        assert second_horse["time"] == "2:31.4"
        assert second_horse["margin"] == "1 1/4"

    def test_parse_third_place_horse_zero_weight_diff(
        self, race_detail_scraper, race_detail_html
    ):
        """parse()は体重差0の場合も正しく抽出する"""
        soup = race_detail_scraper.get_soup(race_detail_html)
        result = race_detail_scraper.parse(soup, race_id="202401010101")
        third_horse = result["results"][2]

        assert third_horse["finish_position"] == 3
        assert third_horse["horse_name"] == "タイトルホルダー"
        assert third_horse["weight"] == 492
        assert third_horse["weight_diff"] == 0

    def test_parse_disqualified_horse(self, race_detail_scraper, race_detail_html):
        """parse()は競走中止馬の情報を正しく抽出する"""
        soup = race_detail_scraper.get_soup(race_detail_html)
        result = race_detail_scraper.parse(soup, race_id="202401010101")
        # 中止馬は5番目（インデックス4）
        dq_horse = result["results"][4]

        assert dq_horse["finish_position"] is None  # 中止は順位なし
        assert dq_horse["horse_name"] == "テスト馬"
        assert dq_horse["time"] == ""  # タイムなし


class TestRaceDetailScraperBuildUrl:
    """RaceDetailScraper._build_url()のテスト"""

    def test_build_url_formats_race_id_correctly(self, race_detail_scraper):
        """_build_url()はレースIDを正しくフォーマットする"""
        url = race_detail_scraper._build_url(race_id="202401010101")
        assert url == "https://db.netkeiba.com/race/202401010101/"


class TestRaceDetailScraperFetchRaceDetail:
    """RaceDetailScraper.fetch_race_detail()のテスト"""

    @patch.object(RaceDetailScraper, "fetch")
    def test_fetch_race_detail_calls_fetch_with_correct_url(
        self, mock_fetch, race_detail_scraper, race_detail_html
    ):
        """fetch_race_detail()は正しいURLでfetch()を呼び出す"""
        mock_fetch.return_value = race_detail_html

        race_detail_scraper.fetch_race_detail(race_id="202401010101")

        mock_fetch.assert_called_once_with(
            "https://db.netkeiba.com/race/202401010101/"
        )

    @patch.object(RaceDetailScraper, "fetch")
    def test_fetch_race_detail_returns_dict(
        self, mock_fetch, race_detail_scraper, race_detail_html
    ):
        """fetch_race_detail()は辞書を返す"""
        mock_fetch.return_value = race_detail_html

        result = race_detail_scraper.fetch_race_detail(race_id="202401010101")

        assert isinstance(result, dict)
        assert "race" in result
        assert "results" in result

    @patch.object(RaceDetailScraper, "fetch")
    def test_fetch_race_detail_integration(
        self, mock_fetch, race_detail_scraper, race_detail_html
    ):
        """fetch_race_detail()の統合テスト"""
        mock_fetch.return_value = race_detail_html

        result = race_detail_scraper.fetch_race_detail(race_id="202401010101")

        # レース情報の確認
        assert result["race"]["name"] == "有馬記念(G1)"
        assert result["race"]["course"] == "中山"

        # 結果の確認
        assert len(result["results"]) == 5
        assert result["results"][0]["horse_name"] == "ドウデュース"


# =============================================================================
# HorseDetailScraper Tests
# =============================================================================


@pytest.fixture
def horse_detail_html():
    """テスト用HTMLフィクスチャを読み込む"""
    fixture_path = Path(__file__).parent / "fixtures" / "horse_detail.html"
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def horse_detail_scraper():
    """HorseDetailScraperインスタンスを返す"""
    return HorseDetailScraper(delay=0)


class TestHorseDetailScraperInit:
    """HorseDetailScraper初期化のテスト"""

    def test_inherits_from_base_scraper(self):
        """HorseDetailScraperはBaseScraperを継承している"""
        scraper = HorseDetailScraper()
        assert isinstance(scraper, BaseScraper)

    def test_default_delay(self):
        """デフォルトのdelay値を継承する"""
        scraper = HorseDetailScraper()
        assert scraper.delay == 1.0

    def test_custom_delay(self):
        """カスタムdelay値を設定できる"""
        scraper = HorseDetailScraper(delay=2.0)
        assert scraper.delay == 2.0

    def test_base_url_attribute(self):
        """BASE_URL属性が正しく設定されている"""
        assert HorseDetailScraper.BASE_URL == "https://db.netkeiba.com"


class TestHorseDetailScraperParse:
    """HorseDetailScraper.parse()のテスト"""

    def test_parse_returns_dict(self, horse_detail_scraper, horse_detail_html):
        """parse()は辞書を返す"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert isinstance(result, dict)

    def test_parse_extracts_horse_id(self, horse_detail_scraper, horse_detail_html):
        """parse()は馬IDを正しく設定する"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert result["id"] == "2019104251"

    def test_parse_extracts_name(self, horse_detail_scraper, horse_detail_html):
        """parse()は馬名を正しく抽出する"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert result["name"] == "ドウデュース"

    def test_parse_extracts_sex(self, horse_detail_scraper, horse_detail_html):
        """parse()は性別を正しく抽出する"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert result["sex"] == "牡"

    def test_parse_extracts_birth_year(self, horse_detail_scraper, horse_detail_html):
        """parse()は生年を正しく抽出する"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert result["birth_year"] == 2019

    def test_parse_extracts_trainer_id(self, horse_detail_scraper, horse_detail_html):
        """parse()は調教師IDを正しく抽出する"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert result["trainer_id"] == "01088"

    def test_parse_extracts_owner_id(self, horse_detail_scraper, horse_detail_html):
        """parse()は馬主IDを正しく抽出する"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert result["owner_id"] == "001234"

    def test_parse_extracts_breeder_id(self, horse_detail_scraper, horse_detail_html):
        """parse()は生産者IDを正しく抽出する"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert result["breeder_id"] == "005678"

    def test_parse_extracts_birthplace(self, horse_detail_scraper, horse_detail_html):
        """parse()は産地を正しく抽出する"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert result["birthplace"] == "安平町"

    def test_parse_extracts_coat_color(self, horse_detail_scraper, horse_detail_html):
        """parse()は毛色を正しく抽出する"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert result["coat_color"] == "鹿毛"

    def test_parse_extracts_sire(self, horse_detail_scraper, horse_detail_html):
        """parse()は父を正しく抽出する"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert result["sire"] == "ハーツクライ"

    def test_parse_extracts_dam(self, horse_detail_scraper, horse_detail_html):
        """parse()は母を正しく抽出する"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert result["dam"] == "ダストアンドダイヤモンズ"

    def test_parse_extracts_total_races(self, horse_detail_scraper, horse_detail_html):
        """parse()は通算出走数を正しく抽出する"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert result["total_races"] == 5

    def test_parse_extracts_total_wins(self, horse_detail_scraper, horse_detail_html):
        """parse()は通算勝利数を正しく抽出する"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert result["total_wins"] == 3

    def test_parse_extracts_total_earnings(self, horse_detail_scraper, horse_detail_html):
        """parse()は獲得賞金を正しく抽出する"""
        soup = horse_detail_scraper.get_soup(horse_detail_html)
        result = horse_detail_scraper.parse(soup, horse_id="2019104251")
        assert result["total_earnings"] == 15234


class TestHorseDetailScraperBuildUrl:
    """HorseDetailScraper._build_url()のテスト"""

    def test_build_url_formats_horse_id_correctly(self, horse_detail_scraper):
        """_build_url()は馬IDを正しくフォーマットする"""
        url = horse_detail_scraper._build_url(horse_id="2019104251")
        assert url == "https://db.netkeiba.com/horse/2019104251/"


class TestHorseDetailScraperFetchHorseDetail:
    """HorseDetailScraper.fetch_horse_detail()のテスト"""

    @patch.object(HorseDetailScraper, "fetch")
    def test_fetch_horse_detail_calls_fetch_with_correct_url(
        self, mock_fetch, horse_detail_scraper, horse_detail_html
    ):
        """fetch_horse_detail()は正しいURLでfetch()を呼び出す"""
        mock_fetch.return_value = horse_detail_html

        horse_detail_scraper.fetch_horse_detail(horse_id="2019104251")

        mock_fetch.assert_called_once_with(
            "https://db.netkeiba.com/horse/2019104251/"
        )

    @patch.object(HorseDetailScraper, "fetch")
    def test_fetch_horse_detail_returns_dict(
        self, mock_fetch, horse_detail_scraper, horse_detail_html
    ):
        """fetch_horse_detail()は辞書を返す"""
        mock_fetch.return_value = horse_detail_html

        result = horse_detail_scraper.fetch_horse_detail(horse_id="2019104251")

        assert isinstance(result, dict)
        assert "id" in result
        assert "name" in result

    @patch.object(HorseDetailScraper, "fetch")
    def test_fetch_horse_detail_integration(
        self, mock_fetch, horse_detail_scraper, horse_detail_html
    ):
        """fetch_horse_detail()の統合テスト"""
        mock_fetch.return_value = horse_detail_html

        result = horse_detail_scraper.fetch_horse_detail(horse_id="2019104251")

        # 基本情報の確認
        assert result["name"] == "ドウデュース"
        assert result["sex"] == "牡"
        assert result["birth_year"] == 2019

        # 血統情報の確認
        assert result["sire"] == "ハーツクライ"
        assert result["dam"] == "ダストアンドダイヤモンズ"

        # 成績情報の確認
        assert result["total_races"] == 5
        assert result["total_wins"] == 3
        assert result["total_earnings"] == 15234
