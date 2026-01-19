"""Race list scraper module for netkeiba.

This module provides functionality to scrape race URLs from netkeiba's
race list page for a specific date.
"""

import re

from bs4 import BeautifulSoup

from keiba.constants import JRA_COURSE_CODES
from keiba.scrapers.base import BaseScraper


class RaceListScraper(BaseScraper):
    """Scraper for netkeiba race list pages.

    Extracts race URLs from the race list page for a specific date.

    Attributes:
        BASE_URL: Base URL for netkeiba race pages.

    Example:
        >>> scraper = RaceListScraper()
        >>> urls = scraper.fetch_race_urls(year=2024, month=1, day=1)
        >>> print(urls[0])
        https://race.netkeiba.com/race/202401010101.html
    """

    BASE_URL = "https://db.netkeiba.com"

    # Pattern to match race URLs: /race/YYYYMMDDXXXX/
    RACE_URL_PATTERN = re.compile(r"^/race/\d+/$")

    @staticmethod
    def is_jra_race(race_url: str) -> bool:
        """Check if the race URL is for JRA (central horse racing).

        Args:
            race_url: Race URL (e.g., https://db.netkeiba.com/race/202405020811/)

        Returns:
            True if JRA race, False if NAR (regional) race.
        """
        match = re.search(r"/race/(\d{12})/?", race_url)
        if not match:
            return False

        race_id = match.group(1)
        course_code = race_id[4:6]
        return course_code in JRA_COURSE_CODES

    def parse(self, soup: BeautifulSoup, jra_only: bool = False) -> list[str]:
        """Parse the race list page and extract race URLs.

        Args:
            soup: BeautifulSoup object of the race list page.
            jra_only: If True, return only JRA races.

        Returns:
            List of full race URLs.
        """
        race_urls: list[str] = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            if self.RACE_URL_PATTERN.match(href):
                full_url = f"{self.BASE_URL}{href}"
                if jra_only and not self.is_jra_race(full_url):
                    continue
                race_urls.append(full_url)

        return race_urls

    def _build_url(self, year: int, month: int, day: int) -> str:
        """Build the race list URL for a specific date.

        Args:
            year: Year (e.g., 2024).
            month: Month (1-12).
            day: Day (1-31).

        Returns:
            Full URL for the race list page.
        """
        date_str = f"{year:04d}{month:02d}{day:02d}"
        return f"{self.BASE_URL}/race/list/{date_str}/"

    def fetch_race_urls(
        self, year: int, month: int, day: int, jra_only: bool = False
    ) -> list[str]:
        """Fetch race URLs for a specific date.

        Args:
            year: Year (e.g., 2024).
            month: Month (1-12).
            day: Day (1-31).
            jra_only: If True, return only JRA races.

        Returns:
            List of race URLs for the specified date.
        """
        url = self._build_url(year, month, day)
        html = self.fetch(url)
        soup = self.get_soup(html)
        return self.parse(soup, jra_only=jra_only)
