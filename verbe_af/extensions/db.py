"""Generate a normalised SQLite database from the merged JSON conjugation data."""

from __future__ import annotations

import logging
import os
import sqlite3

from verbe_af import constants as C
from verbe_af.config import Config

logger = logging.getLogger(__name__)

# Moods that contain tense→person conjugation rows
_MOODS = ("indicatif", "subjonctif", "conditionnel", "imperatif")


def generate_sqlite_db(cfg: Config, loaded_json: dict) -> None:
    """Create ``output/verbs.db`` from *loaded_json*.

    The schema mirrors the JSON structure with three normalised tables:
    ``verbes``, ``conjugaisons``, and ``participes``.
    """
    db_path = C.FILE_VERBS_DB
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.info("Removed existing database: %s", db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    _create_schema(cur)

    verb_n = conj_n = part_n = 0

    for infinitive, verb_data in loaded_json.items():
        cur.execute(
            """INSERT INTO verbes (infinitif, h_aspire, rectification_1990, rectification_1990_variante)
               VALUES (?, ?, ?, ?)""",
            (
                infinitive,
                verb_data.get("h_aspire", False),
                verb_data.get("rectification_1990", False),
                verb_data.get("rectification_1990_variante"),
            ),
        )
        vid = cur.lastrowid
        verb_n += 1

        for voice_key in C.VOICE_KEYS:
            voice = verb_data.get(voice_key)
            if not voice:
                continue

            # Participles
            part = voice.get("participe")
            if part:
                pres = part.get("present")
                if pres:
                    if isinstance(pres, dict):
                        # Passive voice — gendered present participle
                        for form, val in pres.items():
                            cur.execute(
                                "INSERT INTO participes (verbe_id, voix, forme, participe) VALUES (?,?,?,?)",
                                (vid, voice_key, f"present_{form}", val),
                            )
                            part_n += 1
                    else:
                        cur.execute(
                            "INSERT INTO participes (verbe_id, voix, forme, participe) VALUES (?,?,?,?)",
                            (vid, voice_key, "present", pres),
                        )
                        part_n += 1
                for form, val in part.get("passe", {}).items():
                    cur.execute(
                        "INSERT INTO participes (verbe_id, voix, forme, participe) VALUES (?,?,?,?)",
                        (vid, voice_key, f"passe_{form}", val),
                    )
                    part_n += 1

            # Moods / tenses
            for mood in _MOODS:
                mood_data = voice.get(mood)
                if not mood_data:
                    continue
                for tense, tense_data in mood_data.items():
                    if not isinstance(tense_data, dict):
                        continue
                    for person, conjugation in tense_data.items():
                        if conjugation:
                            cur.execute(
                                """INSERT INTO conjugaisons
                                   (verbe_id, voix, mode, temps, personne, conjugaison)
                                   VALUES (?,?,?,?,?,?)""",
                                (vid, voice_key, mood, tense, person, conjugation),
                            )
                            conj_n += 1

        if verb_n % 1000 == 0:
            logger.info("Processed %d verbs …", verb_n)

    conn.commit()
    cur.close()
    conn.close()

    size_mb = os.path.getsize(db_path) / (1024 * 1024)
    logger.info("Database complete: %d verbs, %d conjugations, %d participles (%.2f MB) → %s",
                verb_n, conj_n, part_n, size_mb, db_path)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def _create_schema(cur: sqlite3.Cursor) -> None:
    cur.execute("""
        CREATE TABLE verbes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            infinitif TEXT UNIQUE NOT NULL,
            h_aspire BOOLEAN DEFAULT 0,
            rectification_1990 BOOLEAN DEFAULT 0,
            rectification_1990_variante TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE conjugaisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verbe_id INTEGER NOT NULL,
            voix TEXT NOT NULL,
            mode TEXT NOT NULL,
            temps TEXT NOT NULL,
            personne TEXT NOT NULL,
            conjugaison TEXT NOT NULL,
            FOREIGN KEY (verbe_id) REFERENCES verbes(id) ON DELETE CASCADE,
            UNIQUE(verbe_id, voix, mode, temps, personne)
        )
    """)
    cur.execute("""
        CREATE TABLE participes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verbe_id INTEGER NOT NULL,
            voix TEXT NOT NULL,
            forme TEXT NOT NULL,
            participe TEXT NOT NULL,
            FOREIGN KEY (verbe_id) REFERENCES verbes(id) ON DELETE CASCADE,
            UNIQUE(verbe_id, voix, forme)
        )
    """)

    cur.execute("CREATE INDEX idx_verbes_infinitif ON verbes(infinitif)")
    cur.execute("CREATE INDEX idx_verbes_variantes ON verbes(rectification_1990_variante)")
    cur.execute("CREATE INDEX idx_conjugaisons_recherche ON conjugaisons(verbe_id, voix, mode, temps, personne)")
    cur.execute("CREATE INDEX idx_conjugaisons_texte ON conjugaisons(conjugaison)")
    cur.execute("CREATE INDEX idx_participes_recherche ON participes(verbe_id, voix, forme)")
