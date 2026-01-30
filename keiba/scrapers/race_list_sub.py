"""Race list sub scraper for future race dates.

This module provides functionality to scrape race IDs from
race.netkeiba.com/top/race_list_sub.html, which supports future dates
unlike db.netkeiba.com/race/list/ (past data only).
"""

import re

from keiba.constants import JRA_COURSE_CODES
from keiba.scrapers.base import BaseScraper


class RaceListSubScraper(BaseScraper):
    """Scraper for race.netkeiba.com race list (supports future dates).

    Extracts race IDs from race_list_sub.html for a specific date.

    Example:
        >>> scraper = RaceListSubScraper()
        >>> race_ids = scraper.fetch_race_ids(year=2026, month=2, day=1)
        >>> print(race_ids[0])
        202605010201
    """

    BASE_URL = "https://race.netkeiba.com/top/race_list_sub.html"

    def parse(self, html: str) -> list[str]:
        """Parse HTML and extract race IDs.

        Args:
            html: HTML content from race_list_sub.html

        Returns:
            List of race IDs (12-digit strings)
        """
        # race_id=YYYYPPNNRRXX パターンを抽出
        pattern = r'race_id=(\d{12})'
        matches = re.findall(pattern, html)

        # 重複を除外してユニークなリストを返す
        return list(dict.fromkeys(matches))

    def fetch_race_ids(
        self, year: int, month: int, day: int, jra_only: bool = False
    ) -> list[str]:
        """Fetch race IDs for a specific date.

        Args:
            year: Year (e.g., 2026)
            month: Month (1-12)
            day: Day (1-31)
            jra_only: If True, return only JRA (central) races

        Returns:
            List of race IDs
        """
        url = self._build_url(year, month, day)
        html = self.fetch(url)
        race_ids = self.parse(html)

        if jra_only:
            race_ids = self._filter_jra_only(race_ids)

        return race_ids

    def _build_url(self, year: int, month: int, day: int) -> str:
        """Build URL for race_list_sub.html.

        Args:
            year: Year (e.g., 2026)
            month: Month (1-12)
            day: Day (1-31)

        Returns:
            Full URL with kaisai_date parameter
        """
        date_str = f"{year:04d}{month:02d}{day:02d}"
        return f"{self.BASE_URL}?kaisai_date={date_str}"

    def _filter_jra_only(self, race_ids: list[str]) -> list[str]:
        """Filter race IDs to JRA races only.

        Args:
            race_ids: List of race IDs

        Returns:
            Filtered list containing only JRA races
        """
        jra_codes = set(JRA_COURSE_CODES.keys())
        return [
            race_id
            for race_id in race_ids
            if len(race_id) >= 6 and race_id[4:6] in jra_codes
        ]
