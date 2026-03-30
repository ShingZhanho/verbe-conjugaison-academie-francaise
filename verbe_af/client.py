"""HTTP client for the Académie française dictionary."""

from __future__ import annotations

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

from verbe_af import constants as C
from verbe_af.cache import html_cache_path
from verbe_af.config import Config
from verbe_af.exceptions import NetworkError

logger = logging.getLogger(__name__)


class DictionaryClient:
    """Manages all HTTP interactions with the Académie française dictionary.

    Uses a persistent :class:`requests.Session` for connection reuse and
    cookie management.
    """

    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._session = requests.Session()

        # Base headers applied to every request
        self._session.headers.update(cfg.default_headers)
        self._session.headers["User-Agent"] = cfg.user_agent

    # ------------------------------------------------------------------
    # Session bootstrap
    # ------------------------------------------------------------------

    def obtain_jsession_id(self) -> str:
        """GET the dictionary root page and extract ``JSESSIONID`` from the
        ``Set-Cookie`` header.

        Updates ``cfg.jsession_id`` and returns the value.

        Raises:
            NetworkError: when the request fails or no cookie is returned.
        """
        headers = {
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
        }
        try:
            logger.info("GET %s", self._cfg.base_url)
            resp = self._session.get(
                self._cfg.base_url,
                headers=headers,
                timeout=self._cfg.http_timeout_s,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise NetworkError(
                f"Failed to obtain JSESSIONID: {exc}", url=self._cfg.base_url
            ) from exc

        set_cookie = resp.headers.get("Set-Cookie", "")
        match = re.search(r"JSESSIONID=([^;]+)", set_cookie)
        if not match:
            raise NetworkError("JSESSIONID not found in Set-Cookie header")

        self._cfg.jsession_id = match.group(1)
        logger.info("JSESSIONID obtained: %s", self._cfg.jsession_id)
        return self._cfg.jsession_id

    # ------------------------------------------------------------------
    # Verb search (POST)
    # ------------------------------------------------------------------

    def search_entry(self, verb: str, prev_entry_id: str | None = None) -> str | None:
        """Search for *verb* in the dictionary and return its entry ID.

        Returns ``None`` (without raising) when no matching entry is found.

        Raises:
            NetworkError: after all retries are exhausted.
        """
        headers = {
            "Content-Type": self._cfg.default_headers["Content-Type"],
            "Cookie": self._cookie_string(prev_entry_id),
        }
        if prev_entry_id:
            headers["Referer"] = f"{self._cfg.base_url}article/{prev_entry_id}"

        data = f"term={verb}&options=1"

        for attempt in range(1, self._cfg.max_retry + 1):
            if attempt > 1:
                time.sleep(self._cfg.request_delay_ms / 1000)
            try:
                logger.info(
                    "POST %s --data %r  (attempt %d/%d)",
                    self._cfg.url_search, data, attempt, self._cfg.max_retry,
                )
                resp = self._session.post(
                    self._cfg.url_search,
                    headers=headers,
                    data=data,
                    timeout=self._cfg.http_timeout_s,
                )
                resp.raise_for_status()
                return self._extract_entry_id(resp.json(), verb)

            except requests.RequestException as exc:
                remaining = self._cfg.max_retry - attempt
                logger.warning(
                    "Request failed for '%s': %s  (%d attempt(s) left)",
                    verb, exc, remaining,
                )
                if attempt == self._cfg.max_retry:
                    return None
            except Exception as exc:  # noqa: BLE001
                logger.warning("Unexpected error searching '%s': %s", verb, exc)
                return None

        return None  # unreachable, but keeps mypy happy

    # ------------------------------------------------------------------
    # Conjugation page download (GET)
    # ------------------------------------------------------------------

    def download_conjugation(
        self,
        verb: str,
        verb_id: str,
        prev_id: str | None = None,
    ) -> bool:
        """Download the conjugation page for *verb* and save the
        ``div#<verb_id>`` fragment to the HTML cache.

        Returns ``True`` on success.
        """
        headers = {
            "Cookie": self._cookie_string(prev_id),
        }
        if prev_id:
            headers["Referer"] = f"{self._cfg.base_url}article/{prev_id}"

        url = f"{self._cfg.url_conjugation}{verb_id}"
        try:
            logger.info("GET %s", url)
            resp = self._session.get(
                url, headers=headers, timeout=self._cfg.http_timeout_s
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("Failed to download conjugation for '%s': %s", verb, exc)
            return False

        soup = BeautifulSoup(resp.text, "lxml")
        verb_div = soup.find("div", id=verb_id)
        if verb_div is None:
            logger.warning("div#%s not found in downloaded page for '%s'", verb_id, verb)
            return False

        out = html_cache_path(verb)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(str(verb_div))
        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cookie_string(self, last_entry_id: str | None = None) -> str:
        cookie = f"JSESSIONID={self._cfg.jsession_id}; {self._cfg.misc_cookies}"
        if last_entry_id:
            cookie += f"; lastEntry={last_entry_id}"
        return cookie

    @staticmethod
    def _extract_entry_id(response_json: dict, verb: str) -> str | None:
        """Pick the best verb entry whose label matches *verb* exactly.

        When multiple homonym entries share the same label (e.g. "I. partir"
        the archaic defective form vs. "II. partir" the common verb), prefer
        the non-defective entry so that the richer, modern conjugation page
        is chosen.
        """
        matches = []
        for entry in response_json.get("result", []):
            nature = entry.get("nature", "")
            if "v." not in nature:
                continue
            label = (
                entry.get("label", "")
                .replace("\u2019", "'")
                .replace(" (s')", "")
                .replace(" (se)", "")
            )
            if label == verb:
                matches.append(entry)

        if not matches:
            logger.warning("No exact match for '%s' in search results", verb)
            return None

        if len(matches) == 1:
            return matches[0]["url"].split("/")[-1]

        # Multiple homonyms: prefer entries not marked as defective.
        non_defective = [
            e for e in matches
            if "défectif" not in e.get("nature", "").lower()
        ]
        chosen = (non_defective or matches)[0]
        logger.info(
            "Multiple entries for '%s': chose %s (nature: %s)",
            verb, chosen["url"].split("/")[-1], chosen.get("nature", ""),
        )
        return chosen["url"].split("/")[-1]
