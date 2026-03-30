"""Generate an infinitives list from the Académie française advanced search."""

from __future__ import annotations

import logging
import os
import re

import requests
from bs4 import BeautifulSoup

from verbe_af import constants as C
from verbe_af.client import DictionaryClient
from verbe_af.config import Config

logger = logging.getLogger(__name__)

# Strips Roman-numeral homonym index ("I. ", "III. " …) from entry labels.
_ROMAN_PREFIX_RE = re.compile(r"^[IVX]+\.\s+")

# One parsed search-result entry: (verb_id, display_text)
_Entry = tuple[str, str]


# ---------------------------------------------------------------------------
# Config-file loaders
# ---------------------------------------------------------------------------

def _load_exclude_set(path: str) -> set[str]:
    """Return canonical verb names to skip entirely.

    File format: ``verb:id`` — the id is treated as documentation only.
    Trailing ``*`` on the id field is stripped.  Lines starting with ``#``
    and blank lines are ignored.
    """
    result: set[str] = set()
    if not os.path.exists(path):
        logger.debug("Exclude file not found: %s", path)
        return result
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            verb = line.split(":")[0].strip()
            if verb:
                result.add(verb)
    logger.info("Loaded %d exclusions from %s.", len(result), path)
    return result


def _load_force_remap(path: str) -> dict[str, str]:
    """Return ``{verb: verb_id}`` overrides.

    File format: ``verb:id`` — entries here bypass the search result entirely
    and may reference non-9th-edition IDs (e.g. ``A8…``).  Trailing ``*`` on
    the id field is stripped.
    """
    result: dict[str, str] = {}
    if not os.path.exists(path):
        logger.debug("Force-remap file not found: %s", path)
        return result
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":", 1)
            if len(parts) == 2:
                verb = parts[0].strip()
                vid = parts[1].strip().rstrip("*")
                if verb and vid:
                    result[verb] = vid
    logger.info("Loaded %d force-remaps from %s.", len(result), path)
    return result


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_infinitives(cfg: Config, client: DictionaryClient) -> None:
    """POST for each letter a–z and write ``output/gen_infs/infinitives.txt``.

    Line format:
      * ``<verb>:<verb_id>``           — single entry (no homonyms)
      * ``<verb>_1:<id1>``             — first of N homonyms (IDs sorted asc)
      * ``<verb>_2:<id2>``             — second homonym, etc.

    Exclusion and remap rules are applied before suffixes are assigned:
      * ``exclude_infinitives.txt``    — verbs to omit entirely
      * ``infinitives_force_remap.txt`` — verb_id overrides (any edition)
    """
    output_path = os.path.join(C.DIR_GEN_INFS, "infinitives.txt")

    exclude = _load_exclude_set(C.FILE_EXCLUDE_INFINITIVES)
    remap = _load_force_remap(C.FILE_FORCE_REMAP_INFINITIVES)

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

            # Group all entries by canonical infinitive (Roman-numeral prefix
            # stripped) so homonyms ("I. partir", "II. partir") land in the
            # same bucket.
            grouped: dict[str, list[_Entry]] = {}

            for item in items:
                a_tag = item.find("a")
                if not a_tag or not a_tag.get("href"):
                    continue

                display = item.get_text(" ", strip=True)
                raw_name = display.split(",")[0].strip()
                raw_name = raw_name.replace("\u2019", "'")
                raw_name = raw_name.replace(" (s')", "").replace(" (se)", "")
                canonical = _ROMAN_PREFIX_RE.sub("", raw_name)

                # Skip verbs on the exclude list.
                if canonical in exclude:
                    logger.debug("Skipping excluded verb '%s'.", canonical)
                    continue

                verb_id = a_tag["href"].split("/")[-1]
                if not verb_id.startswith(C.VERB_ID_PREFIX):
                    logger.warning(
                        "Unexpected verb_id '%s' for '%s' — skipping.",
                        verb_id, canonical,
                    )
                    continue

                grouped.setdefault(canonical, []).append((verb_id, display))

            # Resolve groups → final (output_name, verb_id) pairs.
            pairs: list[tuple[str, str]] = []

            for verb in sorted(grouped):
                # Force-remap overrides everything: emit a single entry with
                # the specified ID (may be from any edition).
                if verb in remap:
                    forced_id = remap[verb]
                    original_ids = ", ".join(e[0] for e in grouped[verb])
                    logger.info(
                        "Force-remapping '%s' → %s (search returned: %s).",
                        verb, forced_id, original_ids,
                    )
                    pairs.append((verb, forced_id))
                    continue

                entries = grouped[verb]

                if len(entries) == 1:
                    pairs.append((verb, entries[0][0]))
                else:
                    # Multiple homonyms: assign _1, _2, … suffixes sorted by
                    # verb_id ascending so the order is deterministic.
                    sorted_entries = sorted(entries, key=lambda e: e[0])
                    suffix_list = ", ".join(
                        f"_{i}:{e[0]}" for i, e in enumerate(sorted_entries, 1)
                    )
                    logger.info(
                        "Homonym '%s': %d entries → %s",
                        verb, len(sorted_entries), suffix_list,
                    )
                    for i, (vid, _display) in enumerate(sorted_entries, 1):
                        pairs.append((f"{verb}_{i}", vid))

            logger.info("%d entries written for '%s'.", len(pairs), letter.upper())

            with open(output_path, "a", encoding="utf-8") as fh:
                for verb, vid in pairs:
                    fh.write(f"{verb}:{vid}\n")

        except Exception:
            logger.exception("Error generating infinitives for '%s'", letter.upper())
            continue

        except Exception:
            logger.exception("Error generating infinitives for '%s'", letter.upper())
            continue
