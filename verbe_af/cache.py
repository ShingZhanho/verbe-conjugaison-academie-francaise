"""Cache and output file management."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from verbe_af import constants as C
from verbe_af.exceptions import CacheError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Directory helpers
# ---------------------------------------------------------------------------

def ensure_directories(directories: list[str]) -> None:
    """Create each directory in *directories* if it does not already exist."""
    for d in directories:
        os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------------------
# Infinitives file
# ---------------------------------------------------------------------------

def read_infinitives(filepath: str) -> list[tuple[str, str | None]]:
    """Read an infinitives file.

    Supports two line formats:
      * ``<verb>:<verb_id>``  — new format with pre-resolved IDs
      * ``<verb>``            — legacy format (ID resolved at runtime)

    Returns a list of ``(verb, verb_id_or_None)`` tuples.
    """
    result: list[tuple[str, str | None]] = []
    with open(filepath, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                verb, verb_id = line.split(":", 1)
                result.append((verb.strip(), verb_id.strip()))
            else:
                result.append((line, None))
    return result


def count_lines(filepath: str) -> int:
    """Return the number of non-empty lines in *filepath*."""
    with open(filepath, "rb") as fh:
        return sum(1 for _ in fh)


# ---------------------------------------------------------------------------
# Cache queries
# ---------------------------------------------------------------------------

def cache_path(verb: str, kind: str = "html") -> str:
    """Return the canonical cache path for *verb*.

    *kind* is ``"html"`` (raw cache) or ``"parsed"`` (transformed JSON fragment).
    """
    if kind == "html":
        return os.path.join(C.DIR_CACHE, f"{verb}.html")
    if kind == "parsed":
        return os.path.join(C.DIR_PARSED, f"{verb}.txt")
    raise ValueError(f"Unknown cache kind: {kind!r}")


def cache_exists(verb: str, kind: str = "html") -> bool:
    """Check whether a cache file exists for *verb*."""
    return os.path.exists(cache_path(verb, kind))


# ---------------------------------------------------------------------------
# Parsed-fragment I/O
# ---------------------------------------------------------------------------

def write_parsed_fragment(verb: str, data: dict) -> None:
    """Serialise *data* as a minified JSON fragment for *verb*.

    The fragment is written without outer braces so that fragments can be
    concatenated into a single JSON object later.
    """
    wrapped = {verb: data}
    blob = json.dumps(wrapped, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("\u2019", "'")  # normalise typographic apostrophes
    # Strip outer braces → bare key:value
    Path(cache_path(verb, "parsed")).write_text(blob[1:-1], encoding="utf-8")


# ---------------------------------------------------------------------------
# Merge & output
# ---------------------------------------------------------------------------

def merge_parsed_files() -> dict:
    """Merge all ``output/parsed/*.txt`` fragments into *verbs.min.json*.

    Returns the merged dict.
    """
    parsed_dir = C.DIR_PARSED
    fragments = sorted(f for f in os.listdir(parsed_dir) if f.endswith(".txt"))
    if not fragments:
        logger.warning("No parsed fragments found in %s", parsed_dir)
        return {}

    out_path = C.FILE_VERBS_MIN_JSON
    with open(out_path, "w", encoding="utf-8") as out:
        out.write("{")
        for i, name in enumerate(fragments):
            fpath = os.path.join(parsed_dir, name)
            content = Path(fpath).read_text(encoding="utf-8").strip()
            out.write(content)
            if i < len(fragments) - 1:
                out.write(",")
        out.write("}")

    with open(out_path, encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError as exc:
            raise CacheError(f"Merged JSON is malformed: {exc}", path=out_path) from exc


def write_formatted_json(data: dict, filepath: str) -> None:
    """Write *data* as indented JSON to *filepath*."""
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=4)
