"""Generate an infinitives list from the Académie française advanced search."""

from __future__ import annotations

import logging
import os

import requests
from bs4 import BeautifulSoup

from verbe_af import constants as C
from verbe_af.client import DictionaryClient
from verbe_af.config import Config

logger = logging.getLogger(__name__)


def generate_infinitives(cfg: Config, client: DictionaryClient) -> None:
    """POST for each letter a–z and write ``output/gen_infs/infinitives.txt``.

    Each line is ``<verb>:<verb_id>``.
    """
    output_path = os.path.join(C.DIR_GEN_INFS, "infinitives.txt")

    if os.path.exists(output_path):
        os.remove(output_path)

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": cfg.default_headers["Accept-Encoding"],
        "Accept-Language": cfg.default_headers["Accept-Language"],
        "Content-Type": cfg.default_headers["Content-Type"],
        "Cookie": f"{cfg.misc_cookies}; JSESSIONID={cfg.jsession_id}",
        "User-Agent": cfg.user_agent,
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
    }

    for code in range(ord("a"), ord("z") + 1):
        letter = chr(code)
        body = C.GEN_INFS_BODY_TEMPLATE.format(letter=letter).replace(" ", "%20")

        try:
            logger.info("POST %s for letter '%s'", cfg.url_advsearch, letter.upper())
            resp = requests.post(
                cfg.url_advsearch,
                headers=headers,
                data=body,
                timeout=cfg.http_timeout_s,
            )
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select("div#colGaucheResultat ul.listColGauche li")
            if not items:
                logger.warning("No infinitives found for '%s'", letter.upper())
                continue
            logger.info("Found %d entries for '%s'", len(items), letter.upper())

            # Deduplicate by verb name (keep first occurrence)
            seen: dict[str, str] = {}
            for item in items:
                a_tag = item.find("a")
                if not a_tag or not a_tag.get("href"):
                    continue

                entry = item.text.split(",")[0].strip()
                entry = entry.replace("\u2019", "'")
                entry = entry.replace(" (s')", "").replace(" (se)", "")

                verb_id = a_tag["href"].split("/")[-1]
                if not verb_id.startswith(C.VERB_ID_PREFIX):
                    logger.warning("Unexpected verb_id '%s' for '%s' — skipping.", verb_id, entry)
                    continue

                if entry not in seen:
                    seen[entry] = verb_id

            pairs = sorted(seen.items())
            logger.info("%d unique infinitives for '%s'", len(pairs), letter.upper())

            with open(output_path, "a", encoding="utf-8") as fh:
                for verb, vid in pairs:
                    fh.write(f"{verb}:{vid}\n")

        except Exception:
            logger.exception("Error generating infinitives for '%s'", letter.upper())
            continue
