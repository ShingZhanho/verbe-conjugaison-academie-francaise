"""Runtime configuration — replaces mutable global variables with an injectable dataclass."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default HTTP header values (immutable, not user-configurable)
# ---------------------------------------------------------------------------
_DEFAULT_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-GB,en;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15"
)

_MISC_COOKIES = "acceptCookies=1; accessibilitySettings=wordNavigationLink=false&openDyslexic=false"


@dataclass
class Config:
    """Central, injectable configuration for a crawler run."""

    # --- HTTP ---------------------------------------------------------------
    user_agent: str = _DEFAULT_USER_AGENT
    jsession_id: str | None = None
    http_timeout_s: int = 30
    max_retry: int = 5
    request_delay_ms: int = 500

    # --- Concurrency --------------------------------------------------------
    max_threads: int = 4

    # --- Behaviour ----------------------------------------------------------
    ignore_cache: bool = False
    verbose: bool = False
    log_file: str | None = None

    # --- Extensions ---------------------------------------------------------
    gen_sqlite3: bool = False
    gen_infinitives: bool = False

    # --- Derived (set once at startup) --------------------------------------
    # These are populated by cli.main() before the crawl starts.
    base_url: str = "https://dictionnaire-academie.fr/"

    # --- Internal (not user-facing) -----------------------------------------
    default_headers: dict[str, str] = field(default_factory=lambda: dict(_DEFAULT_HEADERS))
    misc_cookies: str = _MISC_COOKIES

    # --- Convenience --------------------------------------------------------
    @property
    def url_search(self) -> str:
        return f"{self.base_url}search"

    @property
    def url_conjugation(self) -> str:
        return f"{self.base_url}conjuguer/"

    @property
    def url_advsearch(self) -> str:
        return f"{self.base_url}advsearch/"
