"""Race ID resolver with fallback logic.

This module provides a unified function to fetch race IDs for a specific date,
with automatic fallback from RaceListSubScraper (supports future dates) to
RaceListScraper (past data only).
"""

import re

from keiba.scrapers.race_list import RaceListScraper
from keiba.scrapers.race_list_sub import RaceListSubScraper


def fetch_race_ids_for_date(
    year: int, month: int, day: int, jra_only: bool = False
) -> list[str]:
    """Fetch race IDs for a specific date with fallback logic.

    Tries RaceListSubScraper first (supports future dates), then falls back
    to RaceListScraper (past data only) if the first attempt returns empty
    or raises an exception.

    Args:
        year: Year (e.g., 2026)
        month: Month (1-12)
        day: Day (1-31)
        jra_only: If True, return only JRA (central) races

    Returns:
        List of race IDs (12-digit strings)

    Example:
        >>> race_ids = fetch_race_ids_for_date(year=2026, month=2, day=1)
        >>> print(race_ids[0])
        202605010201
    """
    # Try RaceListSubScraper first (supports future dates)
    try:
        scraper = RaceListSubScraper()
        race_ids = scraper.fetch_race_ids(
            year=year, month=month, day=day, jra_only=jra_only
        )
        if race_ids:
            return race_ids
    except Exception:
        # Fall through to RaceListScraper
        pass

    # Fallback to RaceListScraper (past data only)
    scraper = RaceListScraper()
    race_urls = scraper.fetch_race_urls(
        year=year, month=month, day=day, jra_only=jra_only
    )

    # Extract race IDs from URLs
    return _extract_race_ids_from_urls(race_urls)


def _extract_race_ids_from_urls(urls: list[str]) -> list[str]:
    """Extract race IDs from race URLs.

    Args:
        urls: List of race URLs (e.g., "https://db.netkeiba.com/race/202605010201/")

    Returns:
        List of race IDs extracted from URLs
    """
    race_ids = []
    pattern = re.compile(r'/race/(\d{12})/?')

    for url in urls:
        match = pattern.search(url)
        if match:
            race_ids.append(match.group(1))

    return race_ids
