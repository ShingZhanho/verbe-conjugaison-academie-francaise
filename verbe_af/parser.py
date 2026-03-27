"""HTML conjugation-table parser.

Extracts structured conjugation data from the ``div#<verb_id>`` root element
downloaded from the Académie française dictionary.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from bs4 import NavigableString

from verbe_af import constants as C
from verbe_af.constants import VoiceType

if TYPE_CHECKING:
    from bs4 import Tag

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pronoun look-up (module-level, created once)
# ---------------------------------------------------------------------------

def _map_pronoun(pronoun: str) -> str | tuple[str, str] | None:
    """Map a raw pronoun string to a dict key (or a masc/fem tuple for 3rd person).

    Third-person pronouns are returned as a ``(masc, fem)`` tuple **only**
    when both genders appear in the text (e.g. ``"il, elle "``).  When only
    one gender is present (e.g. impersonal ``"il "`` in *falloir*), a plain
    string is returned so that only the matching key is populated.
    """
    p = pronoun.strip().lower()
    if "j" in p:
        return "je"
    if "t" in p:
        return "tu"
    # Order matters: test plural before singular
    if "ils" in p and "elles" in p:
        return ("ils", "elles")
    if "ils" in p:
        return "ils"
    if "elles" in p:
        return "elles"
    if "il" in p and "elle" in p:
        return ("il", "elle")
    if "il" in p or "on" in p:
        return "il"
    if "elle" in p:
        return "elle"
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
            if voice_type == VoiceType.PASSIVE:
                result["present"] = _parse_passive_present_participle(rows)
            else:
                result["present"] = _first_verb_text(rows)

        elif name == "passé":
            result["passe"] = (
                _parse_passive_passe(rows) if voice_type == VoiceType.PASSIVE
                else _parse_active_passe(rows)
            )

    return result


def _parse_passive_present_participle(rows: list[Tag]) -> dict:
    """Parse passive present participle into gendered forms ``{sm, sf, pm, pf}``."""
    for row in rows:
        td = row.find("td", class_="conj_verb")
        if td is None:
            continue
        main_text = _td_main_text(td)
        if not main_text:
            continue
        forms = [f.strip() for f in main_text.split(",")]
        if len(forms) >= 4:
            first_parts = forms[0].split()
            # Prefix is everything before the last word (e.g. "étant")
            prefix = " ".join(first_parts[:-1])
            reform_spans = td.find_all("span", class_="forme_rectif")
            reforms = [s.get_text(strip=True) for s in reform_spans]
            sm = forms[0]
            if len(reforms) >= 1:
                sm += f" ou {reforms[0]}"
            sf = f"{prefix} {forms[1]}" if prefix else forms[1]
            pm = f"{prefix} {forms[2]}" if prefix else forms[2]
            if len(reforms) >= 2:
                pm += f" ou {reforms[1]}"
            pf = f"{prefix} {forms[3]}" if prefix else forms[3]
            return {"sm": sm, "sf": sf, "pm": pm, "pf": pf}
        # Fewer than 4 forms — return as-is
        return _td_full_text(td)
    return None


def _first_verb_text(rows: list[Tag]) -> str | None:
    """Get the text of the first verb cell, properly handling ``<span>`` elements."""
    for row in rows:
        td = row.find("td", class_="conj_verb")
        if td:
            text = _td_full_text(td)
            if text:
                return text
    return None


# ---------------------------------------------------------------------------
# Verb-cell text helpers
# ---------------------------------------------------------------------------

def _td_full_text(td: Tag) -> str:
    """Get the full text from a ``conj_verb`` cell, preserving spaces."""
    return re.sub(r"\s+", " ", td.get_text()).strip()


def _td_main_text(td: Tag) -> str:
    """Get text excluding ``<span class="or">`` and ``<span class="forme_rectif">``."""
    parts: list[str] = []
    for child in td.children:
        if isinstance(child, NavigableString):
            parts.append(str(child))
        elif child.name == "span" and (
            "or" in child.get("class", []) or "forme_rectif" in child.get("class", [])
        ):
            continue
        else:
            parts.append(child.get_text())
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def _parse_active_passe(rows: list[Tag]) -> dict:
    """Active / pronominal past participle — up to 2 rows (simple + compound)."""
    data: dict = {}
    if rows:
        td = rows[0].find("td", class_="conj_verb")
        if td:
            text = _td_main_text(td)
            forms = [f.strip() for f in text.split(",")]
            if len(forms) >= 4:
                data["singulier_m"] = forms[0]
                data["singulier_f"] = forms[1]
                data["pluriel_m"] = forms[2]
                data["pluriel_f"] = forms[3]
    if len(rows) > 1:
        td = rows[1].find("td", class_="conj_verb")
        if td:
            text = _td_main_text(td)
            if text:
                data["compose"] = text
                # Collect reform variant for the compound form
                reform_spans = td.find_all("span", class_="forme_rectif")
                if reform_spans:
                    data["compose_reform"] = " ".join(
                        s.get_text(strip=True) for s in reform_spans
                    )
    return data


def _parse_passive_passe(rows: list[Tag]) -> dict:
    """Passive past participle — compound form only (no simple forms)."""
    data: dict = {}
    if not rows:
        return data
    td = rows[0].find("td", class_="conj_verb")
    if td is None:
        return data
    text = _td_main_text(td)
    forms = [f.strip() for f in text.split(",")]
    if len(forms) >= 4:
        data["compose"] = text
        reform_spans = td.find_all("span", class_="forme_rectif")
        if reform_spans:
            data["compose_reforms"] = [s.get_text(strip=True) for s in reform_spans]
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

        has_or = verb_el.find("span", class_="or") is not None
        rectif_span = verb_el.find("span", class_="forme_rectif")

        # --- Extract main and alternative forms ---
        if has_or and not rectif_span:
            # Non-reform alternative: "form1 ou form2[, fem2]"
            full_text = _td_full_text(verb_el)
            or_parts = re.split(r"\s+ou\s+", full_text, maxsplit=1)
            main_text = or_parts[0].strip()
            alt_text = or_parts[1].strip() if len(or_parts) > 1 else ""
        else:
            main_text = _td_main_text(verb_el)
            alt_text = ""

        forms = [f.strip().replace("\u00a0", "") for f in main_text.split(",")]
        masc = forms[0] if forms else ""
        fem = forms[1] if len(forms) > 1 else masc

        # Parse alternative / 1990 reform variant
        if rectif_span:
            rf = rectif_span.text.strip()
            rf_forms = [f.strip().replace("\u00a0", "") for f in rf.split(",")]
            rf_masc = rf_forms[0] if rf_forms else ""
            if len(rf_forms) > 1:
                rf_fem = rf_forms[1]
            elif fem != masc:
                rf_fem = ""   # masculine-only reform
            else:
                rf_fem = rf_masc
        elif alt_text:
            alt_forms = [f.strip().replace("\u00a0", "") for f in alt_text.split(",")]
            rf_masc = alt_forms[0] if alt_forms else ""
            if len(alt_forms) > 1:
                rf_fem = alt_forms[1]
            elif fem != masc:
                rf_fem = ""   # masculine-only alternative
            else:
                rf_fem = rf_masc
        else:
            rf_masc = rf_fem = ""

        masc_conj = f"{refl}{aux}{masc}"
        if rf_masc:
            masc_conj += f",{refl}{aux}{rf_masc}"

        # Build feminine conjugation when the verb form differs by gender
        if fem != masc:
            fem_conj = f"{refl}{aux}{fem}"
            if rf_fem:
                fem_conj += f",{refl}{aux}{rf_fem}"
        else:
            fem_conj = masc_conj

        if isinstance(key, tuple):
            # 3rd person — separate il/elle or ils/elles keys
            result[key[0]] = masc_conj
            result[key[1]] = fem_conj
        else:
            # 1st / 2nd person
            if fem != masc:
                # Gender matters — store under gendered keys
                result[key] = None          # clear ungendered slot
                result[key + "_m"] = masc_conj
                result[key + "_f"] = fem_conj
            else:
                result[key] = masc_conj

    return result


def _parse_imperative_rows(rows: list[Tag]) -> dict:
    result: dict[str, str | None] = {"tu": None, "nous": None, "vous": None}
    # Positional order for non-pronominal present imperative (no suffix/prefix)
    _POSITION_PERSONS = ["tu", "nous", "vous"]
    position = 0

    for row in rows:
        verb_td = row.find("td", class_="conj_verb")
        if verb_td is None:
            continue

        refl_tag = row.find("td", class_="conj_refl-pron")
        aux_tag = row.find("td", class_="conj_auxil")

        # --- Build the reflexive / auxiliary prefix ---
        if refl_tag and not aux_tag:
            prefix = refl_tag.text.strip() + " "
        elif aux_tag:
            prefix = aux_tag.text.strip() + " "
        else:
            prefix = ""

        # --- Detect person from the row content ---
        person = _detect_imperative_person(row, prefix)
        if person is None:
            # Fallback: positional assignment (rows are always tu/nous/vous)
            if position < len(_POSITION_PERSONS):
                person = _POSITION_PERSONS[position]
            else:
                position += 1
                continue
        position += 1

        # --- Extract verb text ---
        full_text = _td_full_text(verb_td)
        main_text = _td_main_text(verb_td)
        has_or = verb_td.find("span", class_="or") is not None
        rectif_span = verb_td.find("span", class_="forme_rectif")

        # Determine the pronoun suffix for this person
        suffix_map = {
            "tu": "-toi", "nous": "-nous", "vous": "-vous",
        }
        pronoun_suffix = suffix_map[person]

        if prefix:
            # Passé tense — prefix is the reflexive pronoun (e.g. "sois-toi ")
            # The verb cell contains the participle (may be gendered: "assis, assise")
            verb_forms = [f.strip().replace("\u00a0", "") for f in main_text.split(",")]
            masc = verb_forms[0] if verb_forms else ""
            fem = verb_forms[1] if len(verb_forms) > 1 else masc
            masc_conj = f"{prefix}{masc}"
            if fem != masc:
                fem_conj = f"{prefix}{fem}"
                result[person] = None
                result[person + "_m"] = masc_conj
                result[person + "_f"] = fem_conj
            else:
                result[person] = masc_conj
        else:
            # Présent tense — the verb form includes the pronoun suffix
            if has_or:
                # Alternative forms: "assieds ou assois-toi"
                # The suffix may only appear on the last form
                alt_forms = _extract_imperative_alternatives(verb_td, pronoun_suffix)
                if rectif_span and not has_or:
                    # Shouldn't reach here, but safety check
                    result[person] = alt_forms
                else:
                    result[person] = alt_forms
            else:
                result[person] = full_text

    return result


def _detect_imperative_person(row: Tag, prefix: str) -> str | None:
    """Detect which person (tu/nous/vous) an imperative row corresponds to."""
    # For pronominal passé: detect from the reflexive pronoun prefix
    if prefix:
        p = prefix.lower()
        if "toi" in p:
            return "tu"
        if "nous" in p:
            return "nous"
        if "vous" in p:
            return "vous"
        # Non-pronominal: detect from auxiliary (aie/sois→tu, ayons/soyons→nous,
        # ayez/soyez→vous).  Strip "été" for passive compound auxiliaries.
        first_word = p.split()[0] if p.split() else ""
        if first_word in ("aie", "aies", "sois"):
            return "tu"
        if first_word in ("ayons", "soyons"):
            return "nous"
        if first_word in ("ayez", "soyez"):
            return "vous"
        return None

    # For présent: detect from the verb form suffix (pronominal)
    verb_td = row.find("td", class_="conj_verb")
    if verb_td is None:
        return None
    text = _td_full_text(verb_td).lower()
    # Check suffixes — order matters (check longer suffixes first)
    if text.endswith("-nous-en") or text.endswith("-nous"):
        return "nous"
    if text.endswith("-vous-en") or text.endswith("-vous"):
        return "vous"
    # Apostrophe variants for "s'en aller" type
    if text.endswith("-t\u2019en") or text.endswith("-t'en") or text.endswith("-toi"):
        return "tu"
    return None


def _extract_imperative_alternatives(td: Tag, pronoun_suffix: str) -> str:
    """Extract all alternative forms from an imperative verb cell.

    When forms are separated by ``<span class="or">``, the pronoun suffix
    (e.g. ``-toi``) often appears only on the last form.  This function
    appends the suffix to any form that lacks it.

    Reform variants (``<span class="forme_rectif">``) are joined with ``,``
    (the transformer later converts to ``;``).
    """
    full = _td_full_text(td)
    # Split on " ou " to get alternatives
    parts = re.split(r"\s+ou\s+", full)
    if len(parts) == 1:
        return full

    # Find the pronoun suffix from the last part
    last = parts[-1]
    actual_suffix = ""
    for sfx in ("-nous-en", "-vous-en", "-t\u2019en", "-t'en", "-toi", "-nous", "-vous"):
        if last.endswith(sfx):
            actual_suffix = sfx
            break

    if not actual_suffix:
        # Non-pronominal: no pronoun suffix, just join the bare alternatives
        stripped = [p.strip() for p in parts]
        return ",".join(stripped)

    # Append suffix to forms that don't already have it
    fixed: list[str] = []
    for part in parts:
        part = part.strip()
        if not part.endswith(actual_suffix):
            part += actual_suffix
        fixed.append(part)

    return ",".join(fixed)


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
    if tag is None:
        return ""
    text = re.sub(r"\s+", " ", tag.text).strip()
    return (text + " ") if text else ""
