"""Tests for RaceDetailScraper.fetch_payouts() method."""

from pathlib import Path
from unittest.mock import patch, Mock

import pytest
from bs4 import BeautifulSoup

from keiba.scrapers.race_detail import RaceDetailScraper


class TestFetchPayouts:
    """fetch_payouts() メソッドのテスト"""

    def test_returns_list_of_dicts(self):
        """fetch_payouts() は list[dict] を返す"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>5</td>
        <td class="txt_r">150</td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_payouts("202401010101")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], dict)

    def test_parses_single_fukusho(self):
        """単一の複勝払戻金を正しく解析する"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>5</td>
        <td class="txt_r">150</td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_payouts("202401010101")

        assert len(result) == 1
        assert result[0]["horse_number"] == 5
        assert result[0]["payout"] == 150

    def test_parses_multiple_fukusho_with_br_separator(self):
        """<br />区切りの複数複勝払戻金を正しく解析する"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>11<br />3<br />13</td>
        <td class="txt_r">120<br />280<br />1,980</td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_payouts("202401010101")

        assert len(result) == 3
        assert result[0] == {"horse_number": 11, "payout": 120}
        assert result[1] == {"horse_number": 3, "payout": 280}
        assert result[2] == {"horse_number": 13, "payout": 1980}

    def test_parses_payout_with_comma(self):
        """カンマ区切りの払戻金を正しく解析する（例: 1,980 -> 1980）"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>7</td>
        <td class="txt_r">12,345</td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_payouts("202401010101")

        assert result[0]["payout"] == 12345

    def test_returns_empty_list_when_no_payout_table(self):
        """払戻金テーブルがない場合は空リストを返す"""
        html = """
        <html>
        <body>
        <div>No payout table here</div>
        </body>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_payouts("202401010101")

        assert result == []

    def test_returns_empty_list_when_no_fukusho_row(self):
        """複勝行がない場合は空リストを返す"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="tan">単勝</th>
        <td>5</td>
        <td class="txt_r">350</td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_payouts("202401010101")

        assert result == []

    def test_dict_contains_required_keys(self):
        """各dictには 'horse_number' と 'payout' キーが含まれる"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>8</td>
        <td class="txt_r">200</td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_payouts("202401010101")

        assert "horse_number" in result[0]
        assert "payout" in result[0]

    def test_horse_number_is_int(self):
        """horse_number は int 型"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>12</td>
        <td class="txt_r">300</td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_payouts("202401010101")

        assert isinstance(result[0]["horse_number"], int)

    def test_payout_is_int(self):
        """payout は int 型"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>4</td>
        <td class="txt_r">550</td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_payouts("202401010101")

        assert isinstance(result[0]["payout"], int)


class TestParseFukushoPayouts:
    """_parse_fukusho_payouts() 内部メソッドのテスト"""

    def test_parse_from_soup_directly(self):
        """BeautifulSoup オブジェクトから直接複勝を解析できる"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>1<br />2<br />3</td>
        <td class="txt_r">100<br />200<br />300</td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_fukusho_payouts(soup)

        assert len(result) == 3
        assert result[0] == {"horse_number": 1, "payout": 100}
        assert result[1] == {"horse_number": 2, "payout": 200}
        assert result[2] == {"horse_number": 3, "payout": 300}

    def test_handles_whitespace_in_values(self):
        """値の前後の空白を除去する"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>  5  </td>
        <td class="txt_r">  150  </td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_fukusho_payouts(soup)

        assert result[0]["horse_number"] == 5
        assert result[0]["payout"] == 150

    def test_handles_mismatched_counts(self):
        """馬番と払戻金の数が一致しない場合は空リストを返す"""
        html = """
        <html>
        <dl class="pay_block">
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>1<br />2</td>
        <td class="txt_r">100<br />200<br />300</td>
        </tr>
        </table>
        </dl>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_fukusho_payouts(soup)

        # 不整合なデータは無視して空リストを返す
        assert result == []


class TestParseFukushoPayoutsRaceNetkeiba:
    """_parse_fukusho_payouts_race_netkeiba() 内部メソッドのテスト

    race.netkeiba.com の HTML 構造:
    <tr class="Fukusho">
      <th>複勝</th>
      <td class="Result">
        <div><span>5</span></div>
        <div><span>6</span></div>
        <div><span>3</span></div>
      </td>
      <td class="Payout">
        <span>280円<br />210円<br />330円</span>
      </td>
    </tr>
    """

    def test_parses_single_fukusho(self):
        """単一の複勝払戻金を正しく解析する"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fukusho">
          <th>複勝</th>
          <td class="Result">
            <div><span>5</span></div>
          </td>
          <td class="Payout">
            <span>280円</span>
          </td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_fukusho_payouts_race_netkeiba(soup)

        assert len(result) == 1
        assert result[0]["horse_number"] == 5
        assert result[0]["payout"] == 280

    def test_parses_multiple_fukusho(self):
        """複数の複勝払戻金を正しく解析する"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fukusho">
          <th>複勝</th>
          <td class="Result">
            <div><span>5</span></div>
            <div><span>6</span></div>
            <div><span>3</span></div>
          </td>
          <td class="Payout">
            <span>280円<br />210円<br />330円</span>
          </td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_fukusho_payouts_race_netkeiba(soup)

        assert len(result) == 3
        assert result[0] == {"horse_number": 5, "payout": 280}
        assert result[1] == {"horse_number": 6, "payout": 210}
        assert result[2] == {"horse_number": 3, "payout": 330}

    def test_parses_payout_with_comma(self):
        """カンマ区切りの払戻金を正しく解析する（例: 1,980円 -> 1980）"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fukusho">
          <th>複勝</th>
          <td class="Result">
            <div><span>7</span></div>
          </td>
          <td class="Payout">
            <span>1,980円</span>
          </td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_fukusho_payouts_race_netkeiba(soup)

        assert result[0]["payout"] == 1980

    def test_returns_empty_list_when_no_fukusho_row(self):
        """複勝行がない場合は空リストを返す"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Tansho">
          <th>単勝</th>
          <td class="Result"><div><span>5</span></div></td>
          <td class="Payout"><span>350円</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_fukusho_payouts_race_netkeiba(soup)

        assert result == []

    def test_returns_empty_list_when_no_table(self):
        """テーブルがない場合は空リストを返す"""
        html = """
        <html>
        <body>
        <div>No payout table here</div>
        </body>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_fukusho_payouts_race_netkeiba(soup)

        assert result == []

    def test_handles_mismatched_counts(self):
        """馬番と払戻金の数が一致しない場合は空リストを返す"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fukusho">
          <th>複勝</th>
          <td class="Result">
            <div><span>5</span></div>
            <div><span>6</span></div>
          </td>
          <td class="Payout">
            <span>280円<br />210円<br />330円</span>
          </td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_fukusho_payouts_race_netkeiba(soup)

        assert result == []


class TestFetchPayoutsFromRaceNetkeiba:
    """_fetch_payouts_from_race_netkeiba() メソッドのテスト"""

    def test_fetches_from_race_netkeiba_url(self):
        """race.netkeiba.com の正しいURLにアクセスする"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fukusho">
          <th>複勝</th>
          <td class="Result"><div><span>5</span></div></td>
          <td class="Payout"><span>280円</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html) as mock_fetch:
            scraper._fetch_payouts_from_race_netkeiba("202401010101")

            mock_fetch.assert_called_once_with(
                "https://race.netkeiba.com/race/result.html?race_id=202401010101"
            )

    def test_returns_parsed_payouts(self):
        """払戻金を正しく解析して返す"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fukusho">
          <th>複勝</th>
          <td class="Result">
            <div><span>5</span></div>
            <div><span>6</span></div>
          </td>
          <td class="Payout">
            <span>280円<br />210円</span>
          </td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper._fetch_payouts_from_race_netkeiba("202401010101")

        assert len(result) == 2
        assert result[0] == {"horse_number": 5, "payout": 280}
        assert result[1] == {"horse_number": 6, "payout": 210}


class TestFetchPayoutsFallback:
    """fetch_payouts() のフォールバック機構テスト"""

    def test_returns_db_netkeiba_result_when_available(self):
        """db.netkeiba.com から取得できる場合はその結果を返す"""
        db_html = """
        <html>
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>5</td>
        <td class="txt_r">150</td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=db_html):
            result = scraper.fetch_payouts("202401010101")

        assert len(result) == 1
        assert result[0] == {"horse_number": 5, "payout": 150}

    def test_falls_back_to_race_netkeiba_when_db_empty(self):
        """db.netkeiba.com から取得できない場合は race.netkeiba.com にフォールバック"""
        db_html = """
        <html>
        <body>
        <div>No payout table here</div>
        </body>
        </html>
        """
        race_html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fukusho">
          <th>複勝</th>
          <td class="Result">
            <div><span>7</span></div>
            <div><span>3</span></div>
          </td>
          <td class="Payout">
            <span>320円<br />180円</span>
          </td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)

        def mock_fetch(url):
            if "db.netkeiba.com" in url:
                return db_html
            elif "race.netkeiba.com" in url:
                return race_html
            raise ValueError(f"Unexpected URL: {url}")

        with patch.object(scraper, 'fetch', side_effect=mock_fetch):
            result = scraper.fetch_payouts("202401010101")

        assert len(result) == 2
        assert result[0] == {"horse_number": 7, "payout": 320}
        assert result[1] == {"horse_number": 3, "payout": 180}

    def test_returns_empty_when_both_sources_fail(self):
        """両方のソースから取得できない場合は空リストを返す"""
        empty_html = """
        <html>
        <body>
        <div>No payout data</div>
        </body>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=empty_html):
            result = scraper.fetch_payouts("202401010101")

        assert result == []

    def test_does_not_call_race_netkeiba_when_db_succeeds(self):
        """db.netkeiba.com から取得できた場合は race.netkeiba.com にアクセスしない"""
        db_html = """
        <html>
        <table class="pay_table_01">
        <tr>
        <th class="fuku">複勝</th>
        <td>5</td>
        <td class="txt_r">150</td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=db_html) as mock_fetch:
            scraper.fetch_payouts("202401010101")

            # db.netkeiba.com のみ呼ばれる
            assert mock_fetch.call_count == 1
            assert "db.netkeiba.com" in mock_fetch.call_args[0][0]


class TestParseUmarenPayoutRaceNetkeiba:
    """_parse_umaren_payout_race_netkeiba() 内部メソッドのテスト

    race.netkeiba.com の HTML 構造:
    <tr class="Umaren">
      <th>馬連</th>
      <td class="Result">
        <ul>
          <li><span>5</span></li>
          <li><span>6</span></li>
        </ul>
      </td>
      <td class="Payout"><span>2,470</span></td>
    </tr>
    """

    def test_parses_umaren_correctly(self):
        """馬番2頭と払戻金が正しくパースされる"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Umaren">
          <th>馬連</th>
          <td class="Result">
            <ul>
              <li><span>5</span></li>
              <li><span>6</span></li>
            </ul>
          </td>
          <td class="Payout"><span>2,470</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_umaren_payout_race_netkeiba(soup)

        assert result is not None
        assert result["horse_numbers"] == [5, 6]
        assert result["payout"] == 2470

    def test_parses_payout_with_comma(self):
        """カンマ区切りの払戻金を正しく解析する（例: 12,345 -> 12345）"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Umaren">
          <th>馬連</th>
          <td class="Result">
            <ul>
              <li><span>1</span></li>
              <li><span>8</span></li>
            </ul>
          </td>
          <td class="Payout"><span>12,345</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_umaren_payout_race_netkeiba(soup)

        assert result is not None
        assert result["payout"] == 12345

    def test_returns_none_when_no_umaren_row(self):
        """Umaren行がない場合はNoneを返す"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Tansho">
          <th>単勝</th>
          <td class="Result"><div><span>5</span></div></td>
          <td class="Payout"><span>350</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_umaren_payout_race_netkeiba(soup)

        assert result is None

    def test_returns_none_when_no_table(self):
        """テーブルがない場合はNoneを返す"""
        html = """
        <html>
        <body>
        <div>No payout table here</div>
        </body>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_umaren_payout_race_netkeiba(soup)

        assert result is None

    def test_return_type_structure(self):
        """戻り値の型確認: {"horse_numbers": list[int], "payout": int}"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Umaren">
          <th>馬連</th>
          <td class="Result">
            <ul>
              <li><span>3</span></li>
              <li><span>7</span></li>
            </ul>
          </td>
          <td class="Payout"><span>1,500</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_umaren_payout_race_netkeiba(soup)

        assert result is not None
        assert isinstance(result, dict)
        assert "horse_numbers" in result
        assert "payout" in result
        assert isinstance(result["horse_numbers"], list)
        assert all(isinstance(n, int) for n in result["horse_numbers"])
        assert isinstance(result["payout"], int)

    def test_parses_payout_with_yen_suffix(self):
        """「円」サフィックス付きの払戻金を正しく解析する（例: 2,470円 -> 2470）"""
        html = '''
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Umaren">
          <th>馬連</th>
          <td class="Result">
            <ul>
              <li><span>5</span></li>
              <li><span>6</span></li>
            </ul>
          </td>
          <td class="Payout"><span>2,470円</span></td>
        </tr>
        </table>
        </html>
        '''
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_umaren_payout_race_netkeiba(soup)

        assert result is not None
        assert result["horse_numbers"] == [5, 6]
        assert result["payout"] == 2470


class TestFetchUmarenPayout:
    """fetch_umaren_payout() メソッドのテスト"""

    def test_fetches_umaren_correctly(self):
        """馬番2頭と払戻金が正しくパースされる"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Umaren">
          <th>馬連</th>
          <td class="Result">
            <ul>
              <li><span>5</span></li>
              <li><span>6</span></li>
            </ul>
          </td>
          <td class="Payout"><span>2,470</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_umaren_payout("202401010101")

        assert result is not None
        assert result["horse_numbers"] == [5, 6]
        assert result["payout"] == 2470

    def test_parses_payout_with_comma(self):
        """カンマ区切りの払戻金を正しく解析する（例: 2,470 -> 2470）"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Umaren">
          <th>馬連</th>
          <td class="Result">
            <ul>
              <li><span>2</span></li>
              <li><span>9</span></li>
            </ul>
          </td>
          <td class="Payout"><span>15,890</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_umaren_payout("202401010101")

        assert result is not None
        assert result["payout"] == 15890

    def test_returns_none_when_no_umaren_row(self):
        """Umaren行がない場合はNoneを返す"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Tansho">
          <th>単勝</th>
          <td class="Result"><div><span>5</span></div></td>
          <td class="Payout"><span>350</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_umaren_payout("202401010101")

        assert result is None

    def test_returns_none_when_no_table(self):
        """テーブルがない場合はNoneを返す"""
        html = """
        <html>
        <body>
        <div>No payout table here</div>
        </body>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_umaren_payout("202401010101")

        assert result is None

    def test_return_type_structure(self):
        """戻り値の型確認: {"horse_numbers": list[int], "payout": int}"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Umaren">
          <th>馬連</th>
          <td class="Result">
            <ul>
              <li><span>4</span></li>
              <li><span>11</span></li>
            </ul>
          </td>
          <td class="Payout"><span>3,200</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_umaren_payout("202401010101")

        assert result is not None
        assert isinstance(result, dict)
        assert "horse_numbers" in result
        assert "payout" in result
        assert isinstance(result["horse_numbers"], list)
        assert len(result["horse_numbers"]) == 2
        assert all(isinstance(n, int) for n in result["horse_numbers"])
        assert isinstance(result["payout"], int)


class TestParseSanrenpukuPayoutRaceNetkeiba:
    """_parse_sanrenpuku_payout_race_netkeiba() 内部メソッドのテスト

    race.netkeiba.com の HTML 構造:
    <tr class="Fuku3">
      <th>3連複</th>
      <td class="Result">
        <ul>
          <li><span>3</span></li>
          <li><span>5</span></li>
          <li><span>6</span></li>
        </ul>
      </td>
      <td class="Payout"><span>11,060</span></td>
    </tr>
    """

    def test_parses_sanrenpuku_correctly(self):
        """馬番3頭と払戻金が正しくパースされる"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fuku3">
          <th>3連複</th>
          <td class="Result">
            <ul>
              <li><span>3</span></li>
              <li><span>5</span></li>
              <li><span>6</span></li>
            </ul>
          </td>
          <td class="Payout"><span>11,060</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_sanrenpuku_payout_race_netkeiba(soup)

        assert result is not None
        assert result["horse_numbers"] == [3, 5, 6]
        assert result["payout"] == 11060

    def test_parses_payout_with_comma(self):
        """カンマ区切りの払戻金を正しく解析する（例: 11,060 -> 11060）"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fuku3">
          <th>3連複</th>
          <td class="Result">
            <ul>
              <li><span>1</span></li>
              <li><span>2</span></li>
              <li><span>3</span></li>
            </ul>
          </td>
          <td class="Payout"><span>123,456</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_sanrenpuku_payout_race_netkeiba(soup)

        assert result is not None
        assert result["payout"] == 123456

    def test_returns_none_when_no_fuku3_row(self):
        """Fuku3行がない場合はNoneを返す"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fukusho">
          <th>複勝</th>
          <td class="Result"><div><span>5</span></div></td>
          <td class="Payout"><span>280円</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_sanrenpuku_payout_race_netkeiba(soup)

        assert result is None

    def test_returns_none_when_no_table(self):
        """テーブルがない場合はNoneを返す"""
        html = """
        <html>
        <body>
        <div>No payout table here</div>
        </body>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_sanrenpuku_payout_race_netkeiba(soup)

        assert result is None

    def test_return_type(self):
        """戻り値の型確認: {"horse_numbers": list[int], "payout": int}"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fuku3">
          <th>3連複</th>
          <td class="Result">
            <ul>
              <li><span>7</span></li>
              <li><span>8</span></li>
              <li><span>9</span></li>
            </ul>
          </td>
          <td class="Payout"><span>5,000</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_sanrenpuku_payout_race_netkeiba(soup)

        assert isinstance(result, dict)
        assert "horse_numbers" in result
        assert "payout" in result
        assert isinstance(result["horse_numbers"], list)
        assert all(isinstance(n, int) for n in result["horse_numbers"])
        assert isinstance(result["payout"], int)

    def test_parses_payout_with_yen_suffix(self):
        """「円」サフィックス付きの払戻金を正しく解析する（例: 11,060円 -> 11060）"""
        html = '''
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fuku3">
          <th>3連複</th>
          <td class="Result">
            <ul>
              <li><span>3</span></li>
              <li><span>5</span></li>
              <li><span>6</span></li>
            </ul>
          </td>
          <td class="Payout"><span>11,060円</span></td>
        </tr>
        </table>
        </html>
        '''
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_sanrenpuku_payout_race_netkeiba(soup)

        assert result is not None
        assert result["horse_numbers"] == [3, 5, 6]
        assert result["payout"] == 11060


class TestParseTanshoPayoutRaceNetkeiba:
    """_parse_tansho_payout_race_netkeiba() 内部メソッドのテスト

    race.netkeiba.com の HTML 構造:
    <tr class="Tansho">
      <th>単勝</th>
      <td class="Result"><div><span>5</span></div></td>
      <td class="Payout"><span>350円</span></td>
    </tr>
    """

    def test_parses_single_tansho(self):
        """単勝払戻金を正しく解析する"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Tansho">
          <th>単勝</th>
          <td class="Result">
            <div><span>5</span></div>
          </td>
          <td class="Payout">
            <span>350円</span>
          </td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_tansho_payout_race_netkeiba(soup)

        assert result is not None
        assert result["horse_number"] == 5
        assert result["payout"] == 350

    def test_parses_payout_with_comma(self):
        """カンマ区切りの払戻金を正しく解析する（例: 1,980円 -> 1980）"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Tansho">
          <th>単勝</th>
          <td class="Result">
            <div><span>7</span></div>
          </td>
          <td class="Payout">
            <span>1,980円</span>
          </td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_tansho_payout_race_netkeiba(soup)

        assert result is not None
        assert result["payout"] == 1980

    def test_parses_payout_without_yen_suffix(self):
        """「円」サフィックスなしの払戻金を正しく解析する（例: 350 -> 350）"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Tansho">
          <th>単勝</th>
          <td class="Result">
            <div><span>3</span></div>
          </td>
          <td class="Payout">
            <span>350</span>
          </td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_tansho_payout_race_netkeiba(soup)

        assert result is not None
        assert result["payout"] == 350

    def test_returns_none_when_no_tansho_row(self):
        """Tansho行がない場合はNoneを返す"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fukusho">
          <th>複勝</th>
          <td class="Result"><div><span>5</span></div></td>
          <td class="Payout"><span>280円</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_tansho_payout_race_netkeiba(soup)

        assert result is None

    def test_returns_none_when_no_table(self):
        """テーブルがない場合はNoneを返す"""
        html = """
        <html>
        <body>
        <div>No payout table here</div>
        </body>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_tansho_payout_race_netkeiba(soup)

        assert result is None

    def test_return_type_structure(self):
        """戻り値の型確認: {"horse_number": int, "payout": int}"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Tansho">
          <th>単勝</th>
          <td class="Result">
            <div><span>12</span></div>
          </td>
          <td class="Payout">
            <span>2,500円</span>
          </td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_tansho_payout_race_netkeiba(soup)

        assert result is not None
        assert isinstance(result, dict)
        assert "horse_number" in result
        assert "payout" in result
        assert isinstance(result["horse_number"], int)
        assert isinstance(result["payout"], int)

    def test_parses_large_payout(self):
        """高配当を正しく解析する（例: 123,456円 -> 123456）"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Tansho">
          <th>単勝</th>
          <td class="Result">
            <div><span>16</span></div>
          </td>
          <td class="Payout">
            <span>123,456円</span>
          </td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        soup = scraper.get_soup(html)
        result = scraper._parse_tansho_payout_race_netkeiba(soup)

        assert result is not None
        assert result["horse_number"] == 16
        assert result["payout"] == 123456


class TestFetchTanshoPayout:
    """fetch_tansho_payout() メソッドのテスト"""

    def test_fetches_tansho_payout(self):
        """単勝払戻金を正しく取得する"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Tansho">
          <th>単勝</th>
          <td class="Result">
            <div><span>5</span></div>
          </td>
          <td class="Payout">
            <span>350円</span>
          </td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_tansho_payout("202401010101")

        assert result is not None
        assert result["horse_number"] == 5
        assert result["payout"] == 350

    def test_parses_payout_with_comma(self):
        """カンマ区切りの払戻金を正しく解析する"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Tansho">
          <th>単勝</th>
          <td class="Result">
            <div><span>8</span></div>
          </td>
          <td class="Payout">
            <span>15,890円</span>
          </td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_tansho_payout("202401010101")

        assert result is not None
        assert result["payout"] == 15890

    def test_returns_none_when_no_tansho_row(self):
        """Tansho行がない場合はNoneを返す"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fukusho">
          <th>複勝</th>
          <td class="Result"><div><span>5</span></div></td>
          <td class="Payout"><span>280円</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_tansho_payout("202401010101")

        assert result is None

    def test_returns_none_when_no_table(self):
        """テーブルがない場合はNoneを返す"""
        html = """
        <html>
        <body>
        <div>No payout table here</div>
        </body>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_tansho_payout("202401010101")

        assert result is None

    def test_return_type_structure(self):
        """戻り値の型確認: {"horse_number": int, "payout": int}"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Tansho">
          <th>単勝</th>
          <td class="Result">
            <div><span>4</span></div>
          </td>
          <td class="Payout">
            <span>3,200円</span>
          </td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_tansho_payout("202401010101")

        assert result is not None
        assert isinstance(result, dict)
        assert "horse_number" in result
        assert "payout" in result
        assert isinstance(result["horse_number"], int)
        assert isinstance(result["payout"], int)

    def test_fetches_from_correct_url(self):
        """race.netkeiba.com の正しいURLにアクセスする"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Tansho">
          <th>単勝</th>
          <td class="Result"><div><span>5</span></div></td>
          <td class="Payout"><span>350円</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html) as mock_fetch:
            scraper.fetch_tansho_payout("202401010101")

            mock_fetch.assert_called_once_with(
                "https://race.netkeiba.com/race/result.html?race_id=202401010101"
            )


class TestFetchSanrenpukuPayout:
    """fetch_sanrenpuku_payout() メソッドのテスト"""

    def test_fetches_sanrenpuku_payout(self):
        """3連複払戻金を正しく取得する"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fuku3">
          <th>3連複</th>
          <td class="Result">
            <ul>
              <li><span>3</span></li>
              <li><span>5</span></li>
              <li><span>6</span></li>
            </ul>
          </td>
          <td class="Payout"><span>11,060</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_sanrenpuku_payout("202401010101")

        assert result is not None
        assert result["horse_numbers"] == [3, 5, 6]
        assert result["payout"] == 11060

    def test_parses_payout_with_comma(self):
        """カンマ区切りの払戻金を正しく解析する"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fuku3">
          <th>3連複</th>
          <td class="Result">
            <ul>
              <li><span>1</span></li>
              <li><span>2</span></li>
              <li><span>3</span></li>
            </ul>
          </td>
          <td class="Payout"><span>999,999</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_sanrenpuku_payout("202401010101")

        assert result is not None
        assert result["payout"] == 999999

    def test_returns_none_when_no_fuku3_row(self):
        """Fuku3行がない場合はNoneを返す"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fukusho">
          <th>複勝</th>
          <td class="Result"><div><span>5</span></div></td>
          <td class="Payout"><span>280円</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_sanrenpuku_payout("202401010101")

        assert result is None

    def test_returns_none_when_no_table(self):
        """テーブルがない場合はNoneを返す"""
        html = """
        <html>
        <body>
        <div>No payout table here</div>
        </body>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_sanrenpuku_payout("202401010101")

        assert result is None

    def test_return_type(self):
        """戻り値の型確認: {"horse_numbers": list[int], "payout": int}"""
        html = """
        <html>
        <table class="Payout_Detail_Table">
        <tr class="Fuku3">
          <th>3連複</th>
          <td class="Result">
            <ul>
              <li><span>10</span></li>
              <li><span>11</span></li>
              <li><span>12</span></li>
            </ul>
          </td>
          <td class="Payout"><span>8,500</span></td>
        </tr>
        </table>
        </html>
        """
        scraper = RaceDetailScraper(delay=0)
        with patch.object(scraper, 'fetch', return_value=html):
            result = scraper.fetch_sanrenpuku_payout("202401010101")

        assert isinstance(result, dict)
        assert "horse_numbers" in result
        assert "payout" in result
        assert isinstance(result["horse_numbers"], list)
        assert all(isinstance(n, int) for n in result["horse_numbers"])
        assert isinstance(result["payout"], int)