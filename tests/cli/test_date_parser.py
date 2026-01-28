"""Tests for parse_race_date function."""

from datetime import date

import pytest

from keiba.cli import parse_race_date


class TestParseRaceDateNormal:
    """正常系テスト: 有効な日付文字列を変換"""

    def test_standard_date(self):
        """標準的な日付文字列を変換できる"""
        result = parse_race_date("2024年1月1日")
        assert result == date(2024, 1, 1)

    def test_double_digit_month_and_day(self):
        """2桁の月と日を変換できる"""
        result = parse_race_date("2024年12月31日")
        assert result == date(2024, 12, 31)

    def test_single_digit_month_double_digit_day(self):
        """1桁の月と2桁の日を変換できる"""
        result = parse_race_date("2025年5月15日")
        assert result == date(2025, 5, 15)

    def test_double_digit_month_single_digit_day(self):
        """2桁の月と1桁の日を変換できる"""
        result = parse_race_date("2025年10月5日")
        assert result == date(2025, 10, 5)

    def test_leap_year_date(self):
        """うるう年の2月29日を変換できる"""
        result = parse_race_date("2024年2月29日")
        assert result == date(2024, 2, 29)


class TestParseRaceDateEdgeCases:
    """エッジケーステスト: 境界値や特殊ケース"""

    def test_year_start(self):
        """年の初日を変換できる"""
        result = parse_race_date("2024年1月1日")
        assert result == date(2024, 1, 1)

    def test_year_end(self):
        """年の最終日を変換できる"""
        result = parse_race_date("2024年12月31日")
        assert result == date(2024, 12, 31)

    def test_month_start(self):
        """月の初日を変換できる"""
        result = parse_race_date("2024年6月1日")
        assert result == date(2024, 6, 1)

    def test_with_leading_zero_month(self):
        """先頭ゼロ付きの月を変換できる"""
        result = parse_race_date("2024年01月15日")
        assert result == date(2024, 1, 15)

    def test_with_leading_zero_day(self):
        """先頭ゼロ付きの日を変換できる"""
        result = parse_race_date("2024年3月05日")
        assert result == date(2024, 3, 5)

    def test_with_leading_zeros_both(self):
        """先頭ゼロ付きの月と日を変換できる"""
        result = parse_race_date("2024年01月01日")
        assert result == date(2024, 1, 1)

    def test_far_future_year(self):
        """未来の年を変換できる"""
        result = parse_race_date("2030年7月20日")
        assert result == date(2030, 7, 20)

    def test_past_year(self):
        """過去の年を変換できる"""
        result = parse_race_date("2000年8月8日")
        assert result == date(2000, 8, 8)


class TestParseRaceDateInvalid:
    """異常系テスト: 無効な文字列でValueError"""

    def test_empty_string(self):
        """空文字列でValueErrorが発生する"""
        with pytest.raises(ValueError, match="Invalid date string"):
            parse_race_date("")

    def test_none_like_string(self):
        """None文字列でValueErrorが発生する"""
        with pytest.raises(ValueError, match="Invalid date string"):
            parse_race_date("None")

    def test_wrong_format_slash(self):
        """スラッシュ区切りの日付でValueErrorが発生する"""
        with pytest.raises(ValueError, match="Invalid date string"):
            parse_race_date("2024/1/1")

    def test_iso_format_hyphen(self):
        """ハイフン区切りのISO形式日付を変換できる"""
        result = parse_race_date("2024-01-01")
        assert result == date(2024, 1, 1)

    def test_wrong_format_no_kanji(self):
        """漢字なしの日付でValueErrorが発生する"""
        with pytest.raises(ValueError, match="Invalid date string"):
            parse_race_date("20240101")

    def test_partial_date_year_only(self):
        """年のみでValueErrorが発生する"""
        with pytest.raises(ValueError, match="Invalid date string"):
            parse_race_date("2024年")

    def test_partial_date_year_month(self):
        """年月のみでValueErrorが発生する"""
        with pytest.raises(ValueError, match="Invalid date string"):
            parse_race_date("2024年1月")

    def test_missing_year(self):
        """年がない日付でValueErrorが発生する"""
        with pytest.raises(ValueError, match="Invalid date string"):
            parse_race_date("1月1日")

    def test_random_text(self):
        """ランダムなテキストでValueErrorが発生する"""
        with pytest.raises(ValueError, match="Invalid date string"):
            parse_race_date("hello world")

    def test_date_with_extra_text_before(self):
        """日付の前に余分なテキストがあるとValueErrorが発生する"""
        with pytest.raises(ValueError, match="Invalid date string"):
            parse_race_date("開催日: 2024年1月1日")

    def test_invalid_month(self):
        """無効な月（13月）でValueErrorが発生する"""
        # 正規表現はマッチするが、dateコンストラクタでエラー
        with pytest.raises(ValueError):
            parse_race_date("2024年13月1日")

    def test_invalid_day(self):
        """無効な日（32日）でValueErrorが発生する"""
        # 正規表現はマッチするが、dateコンストラクタでエラー
        with pytest.raises(ValueError):
            parse_race_date("2024年1月32日")

    def test_invalid_leap_year(self):
        """うるう年でない年の2月29日でValueErrorが発生する"""
        # 正規表現はマッチするが、dateコンストラクタでエラー
        with pytest.raises(ValueError):
            parse_race_date("2023年2月29日")

    def test_month_zero(self):
        """月が0でValueErrorが発生する"""
        with pytest.raises(ValueError):
            parse_race_date("2024年0月1日")

    def test_day_zero(self):
        """日が0でValueErrorが発生する"""
        with pytest.raises(ValueError):
            parse_race_date("2024年1月0日")
