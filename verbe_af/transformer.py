"""Data transformation — converts raw parsed dicts into the output format.

Responsibilities:
- Map pronoun keys (je → 1s, tu → 2s …)
- Transform participle keys (singulier_m → sm …)
- Expand compound participles
- Detect and create 1990 spelling-reform variant entries
"""

from __future__ import annotations

import copy
import logging

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
        if key == "h_aspire":
            result["h_aspire"] = value
            continue

        # key is a voice key (voix_active_avoir, voix_passive, …)
        result[key] = _transform_voice(value)

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

    # Swap semicolon-separated variants so reformed form comes first
    for voice_key, voice_data in data.items():
        if voice_key in ("h_aspire", "rectification_1990", "rectification_1990_variante"):
            continue
        for mood_key, mood_data in voice_data.items():
            if mood_key == "participe":
                continue
            for tense_key, tense_data in mood_data.items():
                for person_key, conj in tense_data.items():
                    if ";" in conj:
                        parts = conj.split(";")
                        tense_data[person_key] = ";".join(reversed(parts))

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
    present = data.get("present")
    result: dict = {
        "present": present,
        "passe": {},
    }
    passe = data.get("passe", {})
    if not passe:
        return result

    # Simple forms (only for active/pronominal, not passive compound-only)
    if "singulier_m" in passe:
        result["passe"]["sm"] = passe["singulier_m"]
        result["passe"]["sf"] = passe["singulier_f"]
        result["passe"]["pm"] = passe["pluriel_m"]
        result["passe"]["pf"] = passe["pluriel_f"]
    elif "compose" in passe and "," not in passe["compose"]:
        # Invariable participle — extract last word from compound
        word = passe["compose"].split()[-1]
        result["passe"]["sm"] = word
        result["passe"]["sf"] = word
        result["passe"]["pm"] = word
        result["passe"]["pf"] = word

    # Compound forms
    if "compose" in passe:
        compose = passe["compose"]
        reforms = passe.get("compose_reforms", [])

        if "," in compose:
            parts = [p.strip() for p in compose.split(",")]
            if len(parts) >= 4:
                aux_parts = parts[0].split()
                aux = " ".join(aux_parts[:-1])
                sm_val = parts[0]
                sf_val = f"{aux} {parts[1]}"
                pm_val = f"{aux} {parts[2]}"
                pf_val = f"{aux} {parts[3]}"

                # Apply reform variants (reforms pair with masculine forms)
                if reforms:
                    if len(reforms) >= 1:
                        sm_val += f"; {aux} {reforms[0]}"
                    if len(reforms) >= 2:
                        pm_val += f"; {aux} {reforms[1]}"

                result["passe"]["compound_sm"] = sm_val
                result["passe"]["compound_sf"] = sf_val
                result["passe"]["compound_pm"] = pm_val
                result["passe"]["compound_pf"] = pf_val
            else:
                for k in ("compound_sm", "compound_sf", "compound_pm", "compound_pf"):
                    result["passe"][k] = compose
        else:
            # Single reform for non-comma compound
            reform_text = passe.get("compose_reform", "")
            base = compose
            if reform_text:
                base += f"; {reform_text}"
            for k in ("compound_sm", "compound_sf", "compound_pm", "compound_pf"):
                result["passe"][k] = base

    return result


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
