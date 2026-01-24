"""Base scraper module for netkeiba data collection."""

import time

import requests
from bs4 import BeautifulSoup


class BaseScraper:
    """Base class for web scrapers.

    Provides common functionality for HTTP requests and HTML parsing.

    Attributes:
        DEFAULT_USER_AGENT: Default User-Agent string for HTTP requests.
        delay: Delay in seconds between consecutive requests.

    Example:
        >>> class MyScraper(BaseScraper):
        ...     def parse(self, soup: BeautifulSoup) -> dict:
        ...         return {"title": soup.find("title").text}
        >>> scraper = MyScraper(delay=1.0)
        >>> html = scraper.fetch("https://example.com")
        >>> soup = scraper.get_soup(html)
        >>> result = scraper.parse(soup)
    """

    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, delay: float = 1.0) -> None:
        """Initialize BaseScraper.

        Args:
            delay: Delay in seconds between consecutive HTTP requests.
                   Default is 1.0 second.
        """
        self.delay = delay
        self._last_request_time: float | None = None

    def fetch(self, url: str) -> str:
        """Fetch HTML content from the specified URL.

        Applies delay between consecutive requests to avoid overloading
        the target server.

        Args:
            url: The URL to fetch.

        Returns:
            The HTML content as a string.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        self._apply_delay()

        headers = {"User-Agent": self.DEFAULT_USER_AGENT}
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # netkeiba.com uses EUC-JP encoding
        if "netkeiba.com" in url:
            response.encoding = "EUC-JP"

        self._last_request_time = time.time()

        return response.text

    def _apply_delay(self) -> None:
        """Apply delay if needed based on last request time."""
        if self._last_request_time is None:
            return

        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def get_soup(self, html: str) -> BeautifulSoup:
        """Parse HTML string into a BeautifulSoup object.

        Args:
            html: The HTML content to parse.

        Returns:
            A BeautifulSoup object representing the parsed HTML.
        """
        return BeautifulSoup(html, "lxml")

    def parse(self, soup: BeautifulSoup) -> dict:
        """Parse the BeautifulSoup object and extract data.

        This method must be implemented by subclasses.

        Args:
            soup: The BeautifulSoup object to parse.

        Returns:
            A dictionary containing the extracted data.

        Raises:
            NotImplementedError: If not implemented by subclass.
        """
        raise NotImplementedError
