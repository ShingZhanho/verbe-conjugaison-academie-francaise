"""Cache and output file management."""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
from collections import defaultdict
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
# HTML cache queries
# ---------------------------------------------------------------------------

def html_cache_path(verb: str) -> str:
    """Return the canonical HTML cache path for *verb*."""
    return os.path.join(C.DIR_CACHE, f"{verb}.html")


def html_cache_exists(verb: str) -> bool:
    """Check whether an HTML cache file exists for *verb*."""
    return os.path.exists(html_cache_path(verb))


# ---------------------------------------------------------------------------
# Parsed-data store (SQLite key-value)
# ---------------------------------------------------------------------------

class ParsedStore:
    """Thread-safe SQLite key-value store for parsed verb JSON.

    Replaces the thousands of tiny ``output/parsed/<verb>.txt`` fragment
    files with a single ``output/parsed.db`` database using WAL mode for
    efficient concurrent writes.
    """

    def __init__(self, db_path: str = C.FILE_PARSED_DB) -> None:
        self._db_path = db_path
        self._local = threading.local()
        # Create schema on the main thread
        conn = self._conn()
        conn.execute(
            "CREATE TABLE IF NOT EXISTS parsed "
            "(verb TEXT PRIMARY KEY, data TEXT NOT NULL)"
        )
        conn.commit()

    # Each thread gets its own connection (SQLite requirement)
    def _conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return conn

    def has(self, verb: str) -> bool:
        """Return ``True`` if *verb* has already been parsed and stored."""
        row = self._conn().execute(
            "SELECT 1 FROM parsed WHERE verb = ?", (verb,)
        ).fetchone()
        return row is not None

    def put(self, verb: str, data: dict) -> None:
        """Store parsed *data* for *verb* (upsert)."""
        blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        blob = blob.replace("\u2019", "'")  # normalise typographic apostrophes
        conn = self._conn()
        conn.execute(
            "INSERT OR REPLACE INTO parsed (verb, data) VALUES (?, ?)",
            (verb, blob),
        )
        conn.commit()

    def all_entries(self) -> list[tuple[str, str]]:
        """Return all ``(verb, json_string)`` rows sorted by verb."""
        return self._conn().execute(
            "SELECT verb, data FROM parsed ORDER BY verb"
        ).fetchall()

    def count(self) -> int:
        """Return the number of stored entries."""
        row = self._conn().execute("SELECT COUNT(*) FROM parsed").fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        """Close the current thread's connection."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None

    def clear(self) -> None:
        """Delete all entries."""
        conn = self._conn()
        conn.execute("DELETE FROM parsed")
        conn.commit()


# ---------------------------------------------------------------------------
# Merge & output
# ---------------------------------------------------------------------------

def merge_store_to_json(store: ParsedStore) -> dict:
    """Write all entries from *store* into ``verbs.min.json`` and return
    the merged dict."""
    entries = store.all_entries()
    if not entries:
        logger.warning("No parsed entries in store.")
        return {}

    out_path = C.FILE_VERBS_MIN_JSON
    with open(out_path, "w", encoding="utf-8") as out:
        out.write("{")
        for i, (verb, blob) in enumerate(entries):
            # Each blob is already a full JSON object like {"verb": {...}}
            # Strip outer braces to get bare key:value fragment
            out.write(blob[1:-1])
            if i < len(entries) - 1:
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


# ---------------------------------------------------------------------------
# Homonym merging
# ---------------------------------------------------------------------------

_SUFFIX_RE = re.compile(r'_(\d+)$')

_META_KEYS = frozenset({
    "rectification_1990",
    "rectification_1990_variante",
    "h_aspire",
})


def _voice_data(entry: dict) -> dict:
    """Return only the voice keys from *entry* (strip metadata)."""
    return {k: v for k, v in entry.items() if k not in _META_KEYS}


def _is_subset(a: dict, b: dict) -> bool:
    """Return True if voice data *a* is a subset of *b*.

    *a* ⊆ *b* means every voice key in *a* also exists in *b* with
    identical content.
    """
    for key, val in a.items():
        if key not in b or b[key] != val:
            return False
    return True


def merge_homonyms(data: dict) -> dict:
    """Merge ``verb_1`` / ``verb_2`` homonyms where conjugation data is
    identical or one is a strict subset of the other.

    Rules applied within each homonym group:
      * Entries with identical voice data are collapsed into one.
      * If one entry's voices are a strict subset of another, the smaller
        is absorbed into the larger.
      * After collapsing, if only one distinct entry remains it is stored
        under the base name (no suffix).  Otherwise each distinct entry
        keeps a ``_N`` suffix (renumbered from 1).

    Returns a new dict with merged entries.
    """
    # Group suffixed entries by base name
    groups: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    passthrough: dict[str, dict] = {}

    for key, entry in data.items():
        m = _SUFFIX_RE.search(key)
        if m:
            base = key[:m.start()]
            groups[base].append((key, entry))
        else:
            passthrough[key] = entry

    # Process each homonym group
    merged_count = 0
    kept_count = 0
    for base, members in sorted(groups.items()):
        if len(members) == 1:
            # Single suffixed entry (partner missing) — keep suffix
            passthrough[members[0][0]] = members[0][1]
            kept_count += 1
            continue

        # Deduplicate: cluster identical / subset entries.
        # Each cluster is represented by its "best" (superset) member.
        clusters: list[tuple[str, dict, dict]] = []  # (key, entry, voices)
        for key, entry in members:
            vd = _voice_data(entry)
            absorbed = False
            for ci, (ck, ce, cv) in enumerate(clusters):
                if vd == cv or _is_subset(vd, cv):
                    # This entry is identical to or a subset of the cluster
                    absorbed = True
                    break
                if _is_subset(cv, vd):
                    # Cluster is a subset of this entry — replace
                    clusters[ci] = (key, entry, vd)
                    absorbed = True
                    break
            if not absorbed:
                clusters.append((key, entry, vd))

        if len(clusters) == 1:
            ck, ce, _ = clusters[0]
            passthrough[base] = ce
            merged_count += 1
            logger.info("Merged %d homonyms → '%s'", len(members), base)
        else:
            # Renumber from _1
            for i, (ck, ce, _) in enumerate(clusters, 1):
                suffixed = f"{base}_{i}"
                passthrough[suffixed] = ce
            kept_count += len(clusters)
            logger.debug(
                "Kept %d distinct homonyms for '%s'", len(clusters), base,
            )

    logger.info(
        "Homonym merge: %d groups merged, %d suffixed entries kept.",
        merged_count, kept_count,
    )
    return passthrough
