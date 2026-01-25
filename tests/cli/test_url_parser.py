"""URL解析関数のテスト

対象関数:
- extract_race_id_from_url: レースURLからIDを抽出
- extract_race_id_from_shutuba_url: 出馬表URLからIDを抽出
"""

import pytest

from keiba.cli import extract_race_id_from_url, extract_race_id_from_shutuba_url


class TestExtractRaceIdFromUrl:
    """extract_race_id_from_url関数のテスト"""

    # 正常系テスト
    def test_basic_race_url(self):
        """基本的なレースURLからIDを抽出できる"""
        url = "https://race.netkeiba.com/race/202401010101.html"
        result = extract_race_id_from_url(url)
        assert result == "202401010101"

    def test_race_url_with_trailing_slash(self):
        """末尾スラッシュ付きURLからIDを抽出できる"""
        url = "https://race.netkeiba.com/race/202401010101/"
        result = extract_race_id_from_url(url)
        assert result == "202401010101"

    def test_race_url_without_html_extension(self):
        """HTMLなしURLからIDを抽出できる"""
        url = "https://race.netkeiba.com/race/202401010101"
        result = extract_race_id_from_url(url)
        assert result == "202401010101"

    def test_race_url_with_query_params(self):
        """クエリパラメータ付きURLからIDを抽出できる"""
        url = "https://race.netkeiba.com/race/202401010101.html?foo=bar"
        result = extract_race_id_from_url(url)
        assert result == "202401010101"

    def test_db_netkeiba_race_url(self):
        """db.netkeibaのレースURLからIDを抽出できる"""
        url = "https://db.netkeiba.com/race/202401010101/"
        result = extract_race_id_from_url(url)
        assert result == "202401010101"

    def test_different_race_ids(self):
        """様々なレースIDを抽出できる"""
        test_cases = [
            ("https://race.netkeiba.com/race/202606010802.html", "202606010802"),
            ("https://race.netkeiba.com/race/202501050112.html", "202501050112"),
            ("https://db.netkeiba.com/race/199001010101/", "199001010101"),
        ]
        for url, expected_id in test_cases:
            assert extract_race_id_from_url(url) == expected_id

    # 異常系テスト
    def test_invalid_url_no_race_path(self):
        """レースパスがないURLでValueError"""
        url = "https://race.netkeiba.com/horse/2019104308"
        with pytest.raises(ValueError, match="Invalid race URL"):
            extract_race_id_from_url(url)

    def test_invalid_url_empty_string(self):
        """空文字列でValueError"""
        with pytest.raises(ValueError, match="Invalid race URL"):
            extract_race_id_from_url("")

    def test_invalid_url_no_race_id(self):
        """レースIDがないURLでValueError"""
        url = "https://race.netkeiba.com/race/"
        with pytest.raises(ValueError, match="Invalid race URL"):
            extract_race_id_from_url(url)

    def test_invalid_url_shutuba_format(self):
        """出馬表形式URLでValueError（race_id=形式）"""
        url = "https://race.netkeiba.com/race/shutuba.html?race_id=202401010101"
        with pytest.raises(ValueError, match="Invalid race URL"):
            extract_race_id_from_url(url)

    def test_invalid_url_non_numeric_id(self):
        """数字以外のIDでValueError"""
        url = "https://race.netkeiba.com/race/abcdefg.html"
        with pytest.raises(ValueError, match="Invalid race URL"):
            extract_race_id_from_url(url)


class TestExtractRaceIdFromShutubaUrl:
    """extract_race_id_from_shutuba_url関数のテスト"""

    # 正常系テスト
    def test_basic_shutuba_url(self):
        """基本的な出馬表URLからIDを抽出できる"""
        url = "https://race.netkeiba.com/race/shutuba.html?race_id=202606010802"
        result = extract_race_id_from_shutuba_url(url)
        assert result == "202606010802"

    def test_shutuba_url_with_multiple_params(self):
        """複数パラメータ付きURLからIDを抽出できる"""
        url = "https://race.netkeiba.com/race/shutuba.html?race_id=202606010802&rf=race_list"
        result = extract_race_id_from_shutuba_url(url)
        assert result == "202606010802"

    def test_shutuba_url_race_id_not_first_param(self):
        """race_idが最初のパラメータでない場合もIDを抽出できる"""
        url = "https://race.netkeiba.com/race/shutuba.html?rf=race_list&race_id=202606010802"
        result = extract_race_id_from_shutuba_url(url)
        assert result == "202606010802"

    def test_different_shutuba_race_ids(self):
        """様々なレースIDを抽出できる"""
        test_cases = [
            (
                "https://race.netkeiba.com/race/shutuba.html?race_id=202401010101",
                "202401010101",
            ),
            (
                "https://race.netkeiba.com/race/shutuba.html?race_id=202501050112",
                "202501050112",
            ),
            (
                "https://race.netkeiba.com/race/shutuba.html?race_id=199001010101",
                "199001010101",
            ),
        ]
        for url, expected_id in test_cases:
            assert extract_race_id_from_shutuba_url(url) == expected_id

    def test_shutuba_old_format_url(self):
        """旧形式出馬表URLからIDを抽出できる"""
        url = "https://race.netkeiba.com/race/shutuba_past.html?race_id=202606010802"
        result = extract_race_id_from_shutuba_url(url)
        assert result == "202606010802"

    # 異常系テスト
    def test_invalid_url_no_race_id_param(self):
        """race_idパラメータがないURLでValueError"""
        url = "https://race.netkeiba.com/race/shutuba.html?foo=bar"
        with pytest.raises(ValueError, match="Invalid shutuba URL"):
            extract_race_id_from_shutuba_url(url)

    def test_invalid_url_empty_string(self):
        """空文字列でValueError"""
        with pytest.raises(ValueError, match="Invalid shutuba URL"):
            extract_race_id_from_shutuba_url("")

    def test_invalid_url_no_query_string(self):
        """クエリ文字列がないURLでValueError"""
        url = "https://race.netkeiba.com/race/shutuba.html"
        with pytest.raises(ValueError, match="Invalid shutuba URL"):
            extract_race_id_from_shutuba_url(url)

    def test_invalid_url_empty_race_id(self):
        """race_idが空のURLでValueError"""
        url = "https://race.netkeiba.com/race/shutuba.html?race_id="
        with pytest.raises(ValueError, match="Invalid shutuba URL"):
            extract_race_id_from_shutuba_url(url)

    def test_invalid_url_non_numeric_race_id(self):
        """race_idが数字以外のURLでValueError"""
        url = "https://race.netkeiba.com/race/shutuba.html?race_id=abcdefg"
        with pytest.raises(ValueError, match="Invalid shutuba URL"):
            extract_race_id_from_shutuba_url(url)

    def test_invalid_url_direct_race_format(self):
        """直接レースID形式URLでValueError"""
        url = "https://race.netkeiba.com/race/202401010101.html"
        with pytest.raises(ValueError, match="Invalid shutuba URL"):
            extract_race_id_from_shutuba_url(url)


class TestUrlParserEdgeCases:
    """エッジケースのテスト"""

    def test_extract_race_id_preserves_leading_zeros(self):
        """先頭ゼロが保持される"""
        url = "https://race.netkeiba.com/race/000101010101.html"
        result = extract_race_id_from_url(url)
        assert result == "000101010101"

    def test_extract_shutuba_preserves_leading_zeros(self):
        """出馬表URLで先頭ゼロが保持される"""
        url = "https://race.netkeiba.com/race/shutuba.html?race_id=000101010101"
        result = extract_race_id_from_shutuba_url(url)
        assert result == "000101010101"

    def test_extract_race_id_http_protocol(self):
        """HTTPプロトコルのURLからIDを抽出できる"""
        url = "http://race.netkeiba.com/race/202401010101.html"
        result = extract_race_id_from_url(url)
        assert result == "202401010101"

    def test_extract_shutuba_http_protocol(self):
        """HTTPプロトコルの出馬表URLからIDを抽出できる"""
        url = "http://race.netkeiba.com/race/shutuba.html?race_id=202606010802"
        result = extract_race_id_from_shutuba_url(url)
        assert result == "202606010802"
