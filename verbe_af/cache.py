"""Cache and output file management."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
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
