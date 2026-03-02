"""HTML conjugation-table parser.

Extracts structured conjugation data from the ``div#<verb_id>`` root element
downloaded from the Académie française dictionary.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from verbe_af import constants as C
from verbe_af.constants import VoiceType

if TYPE_CHECKING:
    from bs4 import Tag

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pronoun look-up (module-level, created once)
# ---------------------------------------------------------------------------

def _map_pronoun(pronoun: str) -> str | tuple[str, str] | None:
    """Map a raw pronoun string to a dict key (or a masc/fem tuple for 3rd person)."""
    p = pronoun.strip().lower()
    if "j" in p:
        return "je"
    if "t" in p:
        return "tu"
    # Order matters: test "ils"/"elles" before "il"/"elle"
    if "ils" in p or "elles" in p:
        return ("ils", "elles")
    if "il" in p or "elle" in p or "on" in p:
        return ("il", "elle")
    if "nous" in p:
        return "nous"
    if "vous" in p:
        return "vous"
    return None


# ===================================================================
# Public API
# ===================================================================

def parse_conjugation_table(root_tag: Tag, verb: str) -> dict | None:
    """Parse a ``div#<verb_id>`` element into a structured conjugation dict.

    Returns ``{verb: {voice_key: {...}, ..., "h_aspire": bool}}``
    or ``None`` when no parseable voice is found.
    """
    voices = _detect_voices(root_tag)
    if not voices:
        logger.warning("No conjugation data found for '%s'. Skipping.", verb)
        return None

    data: dict = {}
    for voice_key, voice_tag, voice_type in voices:
        logger.info("Parsing %s …", voice_key)
        data[voice_key] = _parse_voice(voice_tag, voice_type)

    # h aspiré detection
    data["h_aspire"] = verb[0] == "h" and "H aspiré" in root_tag.text

    return {verb: data} if data else None


# ===================================================================
# Voice detection
# ===================================================================

_VOICE_SPECS: list[tuple[str, str, VoiceType]] = [
    # (output key,          HTML div id,            voice type)
    ("voix_active_avoir",   "voix_active_avoir",    VoiceType.ACTIVE),
    ("voix_active_etre",    "voix_active_être",     VoiceType.ACTIVE),
    ("voix_passive",        "voix_passive",         VoiceType.PASSIVE),
    ("voix_prono",          "voix_prono",           VoiceType.PRONOMINAL),
]


def _detect_voices(root: Tag) -> list[tuple[str, Tag, VoiceType]]:
    """Return a list of ``(output_key, tag, voice_type)`` for every voice present."""
    found: list[tuple[str, Tag, VoiceType]] = []

    # Explicit avoir / être / passive / prono
    for key, div_id, vtype in _VOICE_SPECS:
        tag = root.find("div", id=div_id)
        if tag is not None:
            found.append((key, tag, vtype))

    # If neither avoir nor être was found, try the generic "voix_active"
    has_explicit_active = any(k.startswith("voix_active") for k, _, _ in found)
    if not has_explicit_active:
        generic = root.find("div", id="voix_active")
        if generic is not None:
            guessed = _guess_auxiliary(generic)
            if guessed == 1:
                found.append(("voix_active_avoir", generic, VoiceType.ACTIVE))
            elif guessed == 2:
                found.append(("voix_active_etre", generic, VoiceType.ACTIVE))
            elif generic.find("div", id=lambda x: x and x.startswith("active_")):
                # Defective verb — auxiliary unknown but moods exist
                found.append(("voix_active", generic, VoiceType.ACTIVE))

    return found


def _guess_auxiliary(voix_tag: Tag | None) -> int:
    """Return ``1`` (avoir), ``2`` (être), or ``0`` (unknown)."""
    if voix_tag is None:
        return 0
    for div in voix_tag.select("div#active_ind div.tense"):
        h4 = div.find("h4", string="Passé composé")
        if h4 is None:
            continue
        table = div.find("table")
        if table is None:
            continue
        auxil_td = table.find("td", class_="conj_auxil")
        if auxil_td is None:
            continue
        form = auxil_td.text.strip().lower()
        if form in C.AVOIR_FORMS:
            return 1
        if form in C.ETRE_FORMS:
            return 2

    logger.warning("Cannot determine auxiliary — active voice will not be parsed.")
    return 0


# ===================================================================
# Voice → moods
# ===================================================================

# (mood_suffix, mood_output_key, log_label, is_imperative)
_MOOD_SPECS = [
    ("par", "participe",    "participle",   False),
    ("ind", "indicatif",    "indicative",   False),
    ("sub", "subjonctif",   "subjunctive",  False),
    ("con", "conditionnel", "conditional",  False),
    ("imp", "imperatif",    "imperative",   True),
]


def _parse_voice(voice_tag: Tag, voice_type: VoiceType) -> dict:
    prefix = C.MOOD_PREFIX[voice_type]
    result: dict = {}

    for suffix, key, label, is_imp in _MOOD_SPECS:
        div = voice_tag.find("div", id=f"{prefix}_{suffix}")
        if div is None:
            logger.warning("    Missing %s mood.", label)
            continue
        logger.info("    Parsing %s …", label)
        if key == "participe":
            result[key] = _parse_participle(div, voice_type)
        elif is_imp:
            result[key] = _parse_mood(div, imperative=True)
        else:
            result[key] = _parse_mood(div)

    return result


# ===================================================================
# Participle parsing
# ===================================================================

def _parse_participle(div: Tag, voice_type: VoiceType) -> dict:
    result: dict = {}
    for tense_div in div.find_all("div", class_="tense"):
        h4 = tense_div.find("h4", class_="relation")
        if h4 is None:
            continue
        name = h4.get_text(strip=True).lower()
        rows = tense_div.find_all("tr", class_="conj_line")

        if name == "présent":
            result["present"] = _first_verb_text(rows)

        elif name == "passé":
            result["passe"] = (
                _parse_passive_passe(rows) if voice_type == VoiceType.PASSIVE
                else _parse_active_passe(rows)
            )

    return result


def _first_verb_text(rows: list[Tag]) -> str | None:
    for row in rows:
        td = row.find("td", class_="conj_verb")
        if td:
            text = td.get_text(strip=True)
            if text:
                return text
    return None


def _parse_active_passe(rows: list[Tag]) -> dict:
    """Active / pronominal past participle — up to 2 rows (simple + compound)."""
    data: dict = {}
    if rows:
        td = rows[0].find("td", class_="conj_verb")
        if td:
            forms = [f.strip() for f in td.get_text(strip=True).split(",")]
            if len(forms) >= 4:
                data["singulier_m"] = forms[0]
                data["singulier_f"] = forms[1]
                data["pluriel_m"] = forms[2]
                data["pluriel_f"] = forms[3]
    if len(rows) > 1:
        td = rows[1].find("td", class_="conj_verb")
        if td:
            text = td.get_text(strip=True)
            if text:
                data["compose"] = text
    return data


def _parse_passive_passe(rows: list[Tag]) -> dict:
    """Passive past participle — single compound row only."""
    data: dict = {}
    if not rows:
        return data
    td = rows[0].find("td", class_="conj_verb")
    if td is None:
        return data
    text = td.get_text(strip=True)
    forms = [f.strip() for f in text.split(",")]
    if len(forms) >= 4:
        first_parts = forms[0].split()
        data["singulier_m"] = first_parts[-1]
        data["singulier_f"] = forms[1]
        data["pluriel_m"] = forms[2]
        data["pluriel_f"] = forms[3]
        data["compose"] = text
    return data


# ===================================================================
# Mood → tenses
# ===================================================================

def _parse_mood(div: Tag, *, imperative: bool = False) -> dict:
    result: dict = {}
    for tense_div in div.find_all("div", class_="tense"):
        h4 = tense_div.find("h4", class_="relation")
        if h4 is None:
            continue
        tense_name = h4.text.strip().lower()
        tense_key = C.TENSE_NAME_MAP.get(tense_name)
        if tense_key is None:
            logger.warning("    Unknown tense '%s'. Skipping.", tense_name)
            continue
        rows = tense_div.find_all("tr", class_="conj_line")
        result[tense_key] = (
            _parse_imperative_rows(rows) if imperative
            else _parse_tense_rows(rows)
        )
    return result


# ===================================================================
# Tense row parsing
# ===================================================================

def _parse_tense_rows(rows: list[Tag]) -> dict:
    result: dict[str, str | None] = {
        "je": None, "tu": None, "il": None,
        "nous": None, "vous": None, "ils": None,
    }

    for row in rows:
        pp_span = row.find("span", class_="conj_pp")
        if pp_span is None:
            logger.warning("    Row without pronoun — skipping.")
            continue
        key = _map_pronoun(pp_span.text)
        if key is None:
            logger.warning("    Unknown pronoun — skipping.")
            continue

        refl = _reflexive_text(row)
        aux = _auxiliary_text(row)
        verb_el = row.find("td", class_="conj_verb")
        if verb_el is None:
            continue

        main_text = str(list(verb_el.stripped_strings)[0]).strip()
        forms = [f.strip().replace("\u00a0", "") for f in main_text.split(",")]
        masc = forms[0] if forms else ""
        fem = forms[1] if len(forms) > 1 else masc

        # 1990 reform variant
        rectif_span = row.find("span", class_="forme_rectif")
        if rectif_span:
            rf = rectif_span.text.strip()
            rf_forms = [f.strip().replace("\u00a0", "") for f in rf.split(",")]
            rf_masc = rf_forms[0] if rf_forms else ""
            rf_fem = rf_forms[1] if len(rf_forms) > 1 else rf_masc
        else:
            rf_masc = rf_fem = ""

        masc_conj = f"{refl}{aux}{masc}"
        if rf_masc:
            masc_conj += f",{refl}{aux}{rf_masc}"

        if isinstance(key, tuple):
            result[key[0]] = masc_conj
            if fem != masc:
                fem_conj = f"{refl}{aux}{fem}"
                if rf_fem and rf_fem != fem:
                    fem_conj += f",{refl}{aux}{rf_fem}"
                result[key[1]] = fem_conj
            else:
                result[key[1]] = masc_conj
        else:
            result[key] = masc_conj

    return result


def _parse_imperative_rows(rows: list[Tag]) -> dict:
    result: dict[str, str | None] = {"tu": None, "nous": None, "vous": None}
    keys = ("tu", "nous", "vous")
    for idx, row in enumerate(rows):
        refl_tag = row.find("td", class_="conj_refl-pron")
        aux_tag = row.find("td", class_="conj_auxil")

        if refl_tag and not aux_tag:
            aux = refl_tag.text.strip() + " "
        elif aux_tag:
            aux = aux_tag.text + " "
        else:
            aux = ""

        verb_td = row.find("td", class_="conj_verb")
        if verb_td is None:
            continue
        verb = str(list(verb_td.stripped_strings)[0]).strip()
        verb = verb.split(",")[0].replace("\u00a0", "")

        result[keys[idx]] = f"{aux}{verb}"
    return result


# ===================================================================
# Tiny helpers
# ===================================================================

def _reflexive_text(row: Tag) -> str:
    tag = row.find("td", class_="conj_refl-pron")
    if tag is None:
        return ""
    text = tag.text.strip().replace("\u2019", "'")
    if text and "'" not in text:
        text += " "
    return text


def _auxiliary_text(row: Tag) -> str:
    tag = row.find("td", class_="conj_auxil")
    return (tag.text + " ") if tag else ""
