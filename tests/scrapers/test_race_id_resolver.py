"""Tests for keiba.scrapers.race_id_resolver module."""

from unittest.mock import patch

import pytest


class TestFetchRaceIdsForDate:
    """fetch_race_ids_for_date() のテスト"""

    @patch('keiba.scrapers.race_id_resolver.RaceListSubScraper')
    def test_returns_race_ids_from_race_list_sub(self, mock_sub_scraper_class):
        """RaceListSubScraper が正常にrace_idを返す場合"""
        from keiba.scrapers.race_id_resolver import fetch_race_ids_for_date

        # RaceListSubScraper のモック設定
        mock_instance = mock_sub_scraper_class.return_value
        mock_instance.fetch_race_ids.return_value = ["202605010201", "202605010202", "202605010203"]

        result = fetch_race_ids_for_date(year=2026, month=2, day=1)

        assert result == ["202605010201", "202605010202", "202605010203"]
        mock_instance.fetch_race_ids.assert_called_once_with(
            year=2026, month=2, day=1, jra_only=False
        )

    @patch('keiba.scrapers.race_id_resolver.RaceListScraper')
    @patch('keiba.scrapers.race_id_resolver.RaceListSubScraper')
    def test_fallback_to_race_list_when_empty(self, mock_sub_scraper_class, mock_list_scraper_class):
        """RaceListSubScraper が空リストを返した場合、RaceListScraper にフォールバック"""
        from keiba.scrapers.race_id_resolver import fetch_race_ids_for_date

        # RaceListSubScraper が空リストを返す
        mock_sub_instance = mock_sub_scraper_class.return_value
        mock_sub_instance.fetch_race_ids.return_value = []

        # RaceListScraper はURLを返す
        mock_list_instance = mock_list_scraper_class.return_value
        mock_list_instance.fetch_race_urls.return_value = [
            "https://db.netkeiba.com/race/202605010201/",
            "https://db.netkeiba.com/race/202605010202/",
        ]

        result = fetch_race_ids_for_date(year=2026, month=2, day=1)

        assert result == ["202605010201", "202605010202"]
        mock_list_instance.fetch_race_urls.assert_called_once_with(
            year=2026, month=2, day=1, jra_only=False
        )

    @patch('keiba.scrapers.race_id_resolver.RaceListScraper')
    @patch('keiba.scrapers.race_id_resolver.RaceListSubScraper')
    def test_fallback_to_race_list_when_exception(self, mock_sub_scraper_class, mock_list_scraper_class):
        """RaceListSubScraper が例外を投げた場合、RaceListScraper にフォールバック"""
        from keiba.scrapers.race_id_resolver import fetch_race_ids_for_date

        # RaceListSubScraper が例外を投げる
        mock_sub_instance = mock_sub_scraper_class.return_value
        mock_sub_instance.fetch_race_ids.side_effect = Exception("Network error")

        # RaceListScraper はURLを返す
        mock_list_instance = mock_list_scraper_class.return_value
        mock_list_instance.fetch_race_urls.return_value = [
            "https://db.netkeiba.com/race/202605010201/",
        ]

        result = fetch_race_ids_for_date(year=2026, month=2, day=1)

        assert result == ["202605010201"]
        mock_list_instance.fetch_race_urls.assert_called_once()

    @patch('keiba.scrapers.race_id_resolver.RaceListSubScraper')
    def test_jra_only_parameter_propagation(self, mock_sub_scraper_class):
        """jra_only パラメータが正しく伝播される"""
        from keiba.scrapers.race_id_resolver import fetch_race_ids_for_date

        mock_instance = mock_sub_scraper_class.return_value
        mock_instance.fetch_race_ids.return_value = ["202605010201"]

        fetch_race_ids_for_date(year=2026, month=2, day=1, jra_only=True)

        mock_instance.fetch_race_ids.assert_called_once_with(
            year=2026, month=2, day=1, jra_only=True
        )

    @patch('keiba.scrapers.race_id_resolver.RaceListScraper')
    @patch('keiba.scrapers.race_id_resolver.RaceListSubScraper')
    def test_returns_empty_list_when_both_empty(self, mock_sub_scraper_class, mock_list_scraper_class):
        """両方とも空の場合は空リストを返す"""
        from keiba.scrapers.race_id_resolver import fetch_race_ids_for_date

        # 両方とも空
        mock_sub_instance = mock_sub_scraper_class.return_value
        mock_sub_instance.fetch_race_ids.return_value = []

        mock_list_instance = mock_list_scraper_class.return_value
        mock_list_instance.fetch_race_urls.return_value = []

        result = fetch_race_ids_for_date(year=2026, month=2, day=1)

        assert result == []

    @patch('keiba.scrapers.race_id_resolver.RaceListScraper')
    @patch('keiba.scrapers.race_id_resolver.RaceListSubScraper')
    def test_extracts_race_id_from_url(self, mock_sub_scraper_class, mock_list_scraper_class):
        """URLからrace_idを正しく抽出する"""
        from keiba.scrapers.race_id_resolver import fetch_race_ids_for_date

        mock_sub_instance = mock_sub_scraper_class.return_value
        mock_sub_instance.fetch_race_ids.return_value = []

        mock_list_instance = mock_list_scraper_class.return_value
        mock_list_instance.fetch_race_urls.return_value = [
            "https://db.netkeiba.com/race/202605010201/",
            "https://db.netkeiba.com/race/202608020412/",
            "https://db.netkeiba.com/race/202610010101/",
        ]

        result = fetch_race_ids_for_date(year=2026, month=2, day=1)

        assert result == ["202605010201", "202608020412", "202610010101"]
