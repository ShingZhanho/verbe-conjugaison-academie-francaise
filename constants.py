"""
Constants for the verb conjugation crawler.
Created on: 2025-11-11
"""

# Cache status constants
CACHE_NOT_FOUND = "NOT_FOUND_SKIPPED"
CACHE_PARSE_FAILED = "PARSE_FAILED"

# Directory paths
DIR_OUTPUT = "./output"
DIR_CACHE = "./output/cache"
DIR_PARSED = "./output/parsed"
DIR_GEN_INFS = "./output/gen_infs"

# File paths
FILE_INFINITIVES = "./infinitives.txt"
FILE_VERBS_JSON = "./output/verbs.json"
FILE_VERBS_MIN_JSON = "./output/verbs.min.json"
FILE_VERBS_DB = "./output/verbs.db"
FILE_LOG = "./output/log.txt"

# File extensions
EXT_HTML = ".html"
EXT_TXT = ".txt"
EXT_JSON = ".json"

# HTTP timeouts (seconds)
HTTP_TIMEOUT = 30

# Pronoun lists
PRONOUNS_FULL = ["je", "tu", "il", "nous", "vous", "ils"]
PRONOUNS_IMPERATIVE = ["tu", "nous", "vous"]

# Voice mappings
VOICE_MAPPING = {
    "voix_active_avoir": "ACTIVE_AVOIR",
    "voix_active_etre": "ACTIVE_ETRE",
    "voix_prono": "PRONOMINAL"
}

# Tense name mappings
TENSE_NAME_MAP = {
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
