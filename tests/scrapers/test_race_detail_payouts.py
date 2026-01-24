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
