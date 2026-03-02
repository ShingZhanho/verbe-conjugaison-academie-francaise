"""Immutable constants — directory paths, linguistic mappings, and enums."""

from __future__ import annotations

import os
from enum import IntEnum

# ---------------------------------------------------------------------------
# Directory / file paths (relative to the working directory)
# ---------------------------------------------------------------------------
DIR_OUTPUT = "./output"
DIR_CACHE = os.path.join(DIR_OUTPUT, "cache")
DIR_PARSED = os.path.join(DIR_OUTPUT, "parsed")
DIR_GEN_INFS = os.path.join(DIR_OUTPUT, "gen_infs")

FILE_INFINITIVES = "./infinitives.txt"
FILE_VERBS_JSON = os.path.join(DIR_OUTPUT, "verbs.json")
FILE_VERBS_MIN_JSON = os.path.join(DIR_OUTPUT, "verbs.min.json")
FILE_VERBS_DB = os.path.join(DIR_OUTPUT, "verbs.db")

# ---------------------------------------------------------------------------
# HTML structure constants
# ---------------------------------------------------------------------------
VERB_ID_PREFIX = "A9"  # All 9th-edition verb div IDs start with this


# ---------------------------------------------------------------------------
# Voice types used by the parser
# ---------------------------------------------------------------------------
class VoiceType(IntEnum):
    """Numeric voice-type tags passed to the parser."""
    ACTIVE = 1
    PRONOMINAL = 2
    PASSIVE = 3


# Map voice type → mood-div ID prefix in the HTML
MOOD_PREFIX: dict[VoiceType, str] = {
    VoiceType.ACTIVE: "active",
    VoiceType.PRONOMINAL: "prono",
    VoiceType.PASSIVE: "passive",
}


# ---------------------------------------------------------------------------
# Linguistic mappings
# ---------------------------------------------------------------------------

# French tense display name → normalised key
TENSE_NAME_MAP: dict[str, str] = {
    "présent": "present",
    "passé": "passe",
    "imparfait": "imparfait",
    "passé composé": "passe_compose",
    "plus-que-parfait": "plus_que_parfait",
    "futur simple": "futur_simple",
    "futur antérieur": "futur_anterieur",
    "passé simple": "passe_simple",
    "passé antérieur": "passe_anterieur",
}

# Person pronoun → compact output key
PERSON_KEY_MAP: dict[str, str] = {
    "je": "1s",
    "tu": "2s",
    "il": "3sm",
    "elle": "3sf",
    "nous": "1p",
    "vous": "2p",
    "ils": "3pm",
    "elles": "3pf",
}

# Ordered list of person keys for deterministic output
PERSON_ORDER: list[str] = ["1s", "2s", "3sm", "3sf", "1p", "2p", "3pm", "3pf"]

# Auxiliary verb look-up tables
AVOIR_FORMS = frozenset(["ai", "as", "a", "avons", "avez", "ont"])
ETRE_FORMS = frozenset(["suis", "es", "est", "sommes", "êtes", "sont"])

# Voice key strings used in the output JSON
VOICE_KEYS = (
    "voix_active_avoir",
    "voix_active_etre",
    "voix_active",       # defective verbs (unknown auxiliary)
    "voix_passive",
    "voix_prono",
)

# Extension: gen-infinitives POST body template
GEN_INFS_BODY_TEMPLATE = (
    "txt_fullsearch=&chk_allform=1&lst_section=&checked_domain="
    "&txt_entry={letter}.*&chk_noaccent=1"
    "&checked_grammcat=27%2C28%2C29%2C30%2C31%2C32%2C33%2C"
    "&chk_grpcat=on"
    "&chk_gramcat=v.&chk_gramcat=v.+tr.&chk_gramcat=v.+intr."
    "&chk_gramcat=v.+pron.&chk_gramcat=v.+r%C3%A9cipr.&chk_gramcat=v.+impers."
    "&checked_lang=&lst_datation=&lst_editions=9&btRechercher="
)
