"""venue_filter ユーティリティのテスト"""

import pytest

from keiba.cli.utils.venue_filter import get_race_ids_for_venue


def test_get_race_ids_for_venue_filters_correctly():
    """指定競馬場のレースIDが正しくフィルタリングされること"""
    race_urls = [
        "https://db.netkeiba.com/race/202406010101/",  # 中山（06）
        "https://db.netkeiba.com/race/202405010201/",  # 東京（05）
        "https://db.netkeiba.com/race/202406020101/",  # 中山（06）
        "https://db.netkeiba.com/race/202409010101/",  # 阪神（09）
    ]

    # 中山（コード "06"）でフィルタ
    result = get_race_ids_for_venue(race_urls, "06")

    assert len(result) == 2
    assert "202406010101" in result
    assert "202406020101" in result
    assert "202405010201" not in result
    assert "202409010101" not in result


def test_get_race_ids_for_venue_empty_result():
    """該当する競馬場がない場合、空リストを返すこと"""
    race_urls = [
        "https://db.netkeiba.com/race/202406010101/",  # 中山（06）
        "https://db.netkeiba.com/race/202405010201/",  # 東京（05）
    ]

    # 札幌（コード "01"）でフィルタ → 該当なし
    result = get_race_ids_for_venue(race_urls, "01")

    assert len(result) == 0
    assert result == []


def test_get_race_ids_for_venue_handles_trailing_slash():
    """末尾のスラッシュありなしの両方に対応すること"""
    race_urls_with_slash = [
        "https://db.netkeiba.com/race/202406010101/",
    ]
    race_urls_without_slash = [
        "https://db.netkeiba.com/race/202406010101",
    ]

    result_with = get_race_ids_for_venue(race_urls_with_slash, "06")
    result_without = get_race_ids_for_venue(race_urls_without_slash, "06")

    assert result_with == ["202406010101"]
    assert result_without == ["202406010101"]


def test_get_race_ids_for_venue_ignores_invalid_urls():
    """無効なURLはスキップされること"""
    race_urls = [
        "https://db.netkeiba.com/race/202406010101/",  # 有効
        "https://invalid.url/",  # 無効
        "not_a_url",  # 無効
        "https://db.netkeiba.com/race/202405010201/",  # 有効
    ]

    result = get_race_ids_for_venue(race_urls, "06")

    assert len(result) == 1
    assert "202406010101" in result
