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
        _global_last_request_time: Class-level timestamp shared across all instances.

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

    # グローバルレートリミッタ: 全インスタンス間で共有
    _global_last_request_time: float | None = None

    def __init__(self, delay: float = 1.0) -> None:
        """Initialize BaseScraper.

        Args:
            delay: Delay in seconds between consecutive HTTP requests.
                   Default is 1.0 second.
        """
        self.delay = delay
        self._last_request_time: float | None = None
        self.session = requests.Session()
        self._retry_count = 0  # リトライカウンタ

    def fetch(self, url: str) -> str:
        """Fetch HTML content from the specified URL with retry logic.

        Applies delay between consecutive requests to avoid overloading
        the target server. Retries on 403, 429, and 503 errors with
        exponential backoff (5s, 10s, 30s). Max 3 retries.

        Args:
            url: The URL to fetch.

        Returns:
            The HTML content as a string.

        Raises:
            requests.HTTPError: If the HTTP request fails after retries.
        """
        max_retries = 3
        backoff_delays = [5, 10, 30]  # 指数バックオフの待機時間
        retryable_errors = ["403", "429", "503"]  # リトライ対象のエラー

        for attempt in range(max_retries + 1):
            self._apply_delay()

            headers = {
                "User-Agent": self.DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Referer": "https://db.netkeiba.com/",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            try:
                response = self.session.get(url, headers=headers, timeout=10)

                # netkeiba.com uses EUC-JP encoding
                if "netkeiba.com" in url:
                    response.encoding = "EUC-JP"

                response.raise_for_status()

                # 成功したらリトライカウンタをリセット
                self._retry_count = 0
                return response.text
            except requests.HTTPError as e:
                # リトライ対象のエラーかチェック
                is_retryable = any(code in str(e) for code in retryable_errors)

                if is_retryable and attempt < max_retries:
                    # バックオフ待機
                    backoff_time = backoff_delays[attempt]
                    time.sleep(backoff_time)
                    self._retry_count += 1
                else:
                    # リトライ不可またはリトライ上限に達した場合は例外を投げる
                    raise
            finally:
                # グローバルタイマーとインスタンスタイマーの両方を更新
                current_time = time.time()
                self._last_request_time = current_time
                BaseScraper._global_last_request_time = current_time

        # ここには到達しないはずだが、念のため
        raise requests.HTTPError("Max retries exceeded")

    def fetch_json(self, url: str, params: dict | None = None) -> dict:
        """Fetch JSON content from the specified URL.

        Applies delay between consecutive requests to avoid overloading
        the target server.

        Args:
            url: The URL to fetch JSON from.
            params: Optional query parameters to include in the request.

        Returns:
            The parsed JSON response as a dictionary.

        Raises:
            requests.HTTPError: If the HTTP request fails.
        """
        self._apply_delay()

        headers = {
            "User-Agent": self.DEFAULT_USER_AGENT,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Referer": "https://db.netkeiba.com/",
            "X-Requested-With": "XMLHttpRequest",
        }
        try:
            response = self.session.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        finally:
            # グローバルタイマーとインスタンスタイマーの両方を更新
            current_time = time.time()
            self._last_request_time = current_time
            BaseScraper._global_last_request_time = current_time

    def _apply_delay(self) -> None:
        """Apply delay if needed based on global last request time.

        Uses class-level _global_last_request_time to enforce rate limiting
        across all BaseScraper instances.
        """
        if BaseScraper._global_last_request_time is None:
            return

        elapsed = time.time() - BaseScraper._global_last_request_time
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
