"""Data transformation — converts raw parsed dicts into the output format.

Responsibilities:
- Map pronoun keys (je → 1s, tu → 2s …)
- Preserve explicitly parsed participle gender/number slots
- Expand compound participles
- Detect and create 1990 spelling-reform variant entries
"""

from __future__ import annotations

import copy
import logging
import re

from verbe_af import constants as C

logger = logging.getLogger(__name__)


# ===================================================================
# Public API
# ===================================================================

def transform_verb(verb: str, verb_data: dict) -> dict:
    """Transform one verb's parsed data into the output format."""
    result: dict = {}

    # 1990 reform metadata
    result["rectification_1990"] = _has_reform_variant(verb)
    result["rectification_1990_variante"] = (
        _reform_spelling(verb) if result["rectification_1990"] else None
    )

    for key, value in verb_data.items():
        if key.startswith("_"):
            continue
        if key in ("h_aspire", "bloque_elision_liaison"):
            result[key] = value
            continue

        # key is a voice key (voix_active_avoir, voix_passive, …)
        result[key] = _transform_voice(value)

    if verb_data.get("_circumflex_alternatives"):
        match = re.search(r"^.*?[îû]", verb)
        if match:
            lexical_prefix = match.group()
            plain_prefix = lexical_prefix.replace("î", "i").replace("û", "u")
            pattern = re.compile(r"(?<!\w)" + re.escape(lexical_prefix))

            def add_alternatives(value):
                if isinstance(value, dict):
                    return {key: add_alternatives(item) for key, item in value.items()}
                if not isinstance(value, str):
                    return value
                forms = [item.strip() for item in value.split(";")]
                # Replace only the lexical prefix, never auxiliary or grammatical
                # circumflexes (e.g. connûmes, abîmâmes, eût).
                for form in list(forms):
                    alternative = pattern.sub(plain_prefix, form)
                    if alternative not in forms:
                        forms.append(alternative)
                return ";".join(forms)

            for key in C.VOICE_KEYS:
                if key in result:
                    result[key] = add_alternatives(result[key])
    return result


def create_reformed_entry(verb: str, transformed: dict) -> tuple[str, dict] | None:
    """If *verb* has a 1990 reform variant, return ``(reformed_name, data)``
    with the variant forms placed first.  Otherwise return ``None``.
    """
    if not _has_reform_variant(verb):
        return None
    reformed = _reform_spelling(verb)
    if reformed is None:
        return None

    data = copy.deepcopy(transformed)
    data["rectification_1990"] = True
    data["rectification_1990_variante"] = verb  # points back to original

    def prefer_reform(value):
        if isinstance(value, dict):
            return {key: prefer_reform(item) for key, item in value.items()}
        if isinstance(value, str) and ";" in value:
            return ";".join(reversed([part.strip() for part in value.split(";")]))
        return value

    for key in C.VOICE_KEYS:
        if key in data:
            data[key] = prefer_reform(data[key])

    logger.info("Created reformed entry: %s → %s", reformed, verb)
    return reformed, data


# ===================================================================
# Internal — voice / mood / tense transforms
# ===================================================================

def _transform_voice(voice_data: dict) -> dict:
    out: dict = {}
    for mood_key, mood_data in voice_data.items():
        if mood_key == "participe":
            out["participe"] = _transform_participle(mood_data)
        else:
            out[mood_key] = {
                tense_key: _transform_tense(tense_data)
                for tense_key, tense_data in mood_data.items()
            }
    return out


def _transform_participle(data: dict) -> dict:
    passe = data.get("passe", {})
    forms = dict(passe.get("simple", {}))
    forms.update({f"compound_{key}": value
                  for key, value in passe.get("compound", {}).items()})
    return {"present": data.get("present"), "passe": forms}


def _transform_tense(tense_data: dict) -> dict:
    temp: dict[str, str] = {}
    for person, conj in tense_data.items():
        if conj is None:
            continue
        value = conj.replace(",", ";")
        for out_key in C.PERSON_EXPAND_MAP.get(person, (person,)):
            temp[out_key] = value

    ordered = {k: temp[k] for k in C.PERSON_ORDER if k in temp}
    return _merge_identical(ordered)


def _merge_identical(tense: dict[str, str]) -> dict[str, str]:
    """Merge person keys that share the same conjugation value.

    ``{"1sm": "combine", "1sf": "combine"}`` → ``{"1sm;1sf": "combine"}``

    Keys are joined with ``;`` and their relative order from
    :data:`C.PERSON_ORDER` is preserved.
    """
    from collections import OrderedDict

    # Group keys by value, preserving insertion order
    groups: OrderedDict[str, list[str]] = OrderedDict()
    for key, val in tense.items():
        groups.setdefault(val, []).append(key)

    merged: dict[str, str] = {}
    for val, keys in groups.items():
        merged[";".join(keys)] = val
    return merged


# ===================================================================
# 1990 reform helpers
# ===================================================================

def _has_reform_variant(verb: str) -> bool:
    return "î" in verb or "û" in verb


def _reform_spelling(verb: str) -> str | None:
    if _has_reform_variant(verb):
        return verb.replace("î", "i").replace("û", "u")
    return None
