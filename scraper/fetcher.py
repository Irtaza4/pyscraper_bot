import random
import time
import httpx
from typing import Optional, Dict, Any

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
]

class HTTPFetcher:
    """HTTP fetcher with User-Agent rotation, timeouts, and rate limiting."""

    def __init__(self, timeout: float = 15.0, delay_between_requests: float = 1.0, max_retries: int = 2):
        self.timeout = timeout
        self.delay_between_requests = delay_between_requests
        self.max_retries = max_retries
        self._last_request_time = 0.0

    def get_random_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    def _apply_rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.delay_between_requests:
            time.sleep(self.delay_between_requests - elapsed)
        self._last_request_time = time.time()

    def fetch(self, url: str) -> Optional[str]:
        """Synchronously fetch HTML content of a URL."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        self._apply_rate_limit()

        for attempt in range(self.max_retries + 1):
            try:
                headers = self.get_random_headers()
                with httpx.Client(timeout=self.timeout, follow_redirects=True, verify=False) as client:
                    response = client.get(url, headers=headers)
                    if response.status_code == 200:
                        return response.text
            except Exception as e:
                if attempt == self.max_retries:
                    pass
                time.sleep(1)
        return None

    async def fetch_async(self, url: str) -> Optional[str]:
        """Asynchronously fetch HTML content of a URL."""
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        for attempt in range(self.max_retries + 1):
            try:
                headers = self.get_random_headers()
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True, verify=False) as client:
                    response = await client.get(url, headers=headers)
                    if response.status_code == 200:
                        return response.text
            except Exception:
                pass
        return None
