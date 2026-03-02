"""Crawl orchestration — processes verbs through search → download → parse → transform."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup

from verbe_af import constants as C
from verbe_af.cache import cache_exists, cache_path, write_parsed_fragment
from verbe_af.client import DictionaryClient
from verbe_af.config import Config
from verbe_af.exceptions import ParsingError
from verbe_af.parser import parse_conjugation_table
from verbe_af.transformer import create_reformed_entry, transform_verb

logger = logging.getLogger(__name__)


class VerbCrawler:
    """Thread-safe verb crawler that coordinates the full pipeline."""

    def __init__(self, cfg: Config, client: DictionaryClient) -> None:
        self._cfg = cfg
        self._client = client
        self._lock = threading.Lock()
        self._processed = 0

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self, verbs: list[tuple[str, str | None]]) -> tuple[int, list[str]]:
        """Process all *verbs* and return ``(success_count, failed_verbs)``."""
        total = len(verbs)
        self._processed = 0

        args_list = [
            (verb, vid, i + 1, total)
            for i, (verb, vid) in enumerate(verbs)
        ]

        success = 0
        failed: list[str] = []

        if self._cfg.max_threads == 1:
            for a in args_list:
                ok = self._process_one(*a)
                if ok:
                    success += 1
                else:
                    failed.append(a[0])
        else:
            with ThreadPoolExecutor(max_workers=self._cfg.max_threads) as pool:
                futures = {
                    pool.submit(self._process_one, *a): a[0]
                    for a in args_list
                }
                for fut in as_completed(futures):
                    verb_name = futures[fut]
                    try:
                        if fut.result():
                            success += 1
                        else:
                            failed.append(verb_name)
                    except Exception:
                        logger.exception("Exception processing '%s'", verb_name)
                        failed.append(verb_name)

        return success, failed

    # ------------------------------------------------------------------
    # Single-verb pipeline
    # ------------------------------------------------------------------

    def _process_one(
        self,
        verb: str,
        verb_id: str | None,
        counter: int,
        total: int,
    ) -> bool:
        width = len(str(total))
        with self._lock:
            self._processed += 1
            seq = self._processed

        # Already parsed?
        if not self._cfg.ignore_cache and cache_exists(verb, "parsed"):
            logger.debug("(%*d/%d) '%s' already parsed — skipping.", width, seq, total, verb)
            return True

        # Resolve verb ID if needed
        if verb_id is None:
            logger.info("(%*d/%d) Searching: %s", width, seq, total, verb)
            verb_id = self._client.search_entry(verb)
            if verb_id is None:
                logger.warning("No entry found for '%s'.", verb)
                return False
        else:
            logger.info("(%*d/%d) Processing: %s (ID %s)", width, seq, total, verb, verb_id)

        # Download
        if not self._cfg.ignore_cache and cache_exists(verb, "html"):
            logger.info("Using cached HTML for '%s'.", verb)
        else:
            logger.info("Downloading conjugation for '%s' …", verb)
            if not self._client.download_conjugation(verb, verb_id):
                return False

        # Parse + transform + write
        return self._parse_and_write(verb, verb_id)

    def _parse_and_write(self, verb: str, verb_id: str) -> bool:
        """Read cached HTML, parse, transform, and write parsed fragments."""
        html_path = cache_path(verb, "html")
        try:
            with open(html_path, encoding="utf-8") as fh:
                raw = fh.read()
        except OSError as exc:
            logger.warning("Cannot read cache for '%s': %s", verb, exc)
            return False

        soup = BeautifulSoup(raw, "lxml")

        # Locate root div
        root = soup.find("div", id=verb_id)
        if root is None:
            # Fallback: any A9… div (handles homonym ID mismatches)
            root = soup.find("div", id=lambda x: x and x.startswith(C.VERB_ID_PREFIX))
            if root is not None:
                logger.info("'%s': expected div#%s, found div#%s (fallback).", verb, verb_id, root["id"])
            else:
                logger.warning("No conjugation div found for '%s'.", verb)
                return False

        # Shrink full-page caches on the fly
        stripped = raw.lstrip()
        if stripped.startswith("<!DOCTYPE") or stripped.startswith("<html"):
            logger.info("Shrinking full-page cache for '%s'.", verb)
            with open(html_path, "w", encoding="utf-8") as fh:
                fh.write(str(root))

        # Parse
        parsed = parse_conjugation_table(root, verb)
        if parsed is None:
            logger.warning("No conjugation data for '%s'.", verb)
            return False

        # Transform
        verb_data = parsed[verb]
        transformed = transform_verb(verb, verb_data)

        # Write main entry
        write_parsed_fragment(verb, transformed)

        # Write reformed-spelling entry if applicable
        entry = create_reformed_entry(verb, transformed)
        if entry:
            reformed_name, reformed_data = entry
            write_parsed_fragment(reformed_name, reformed_data)

        return True
