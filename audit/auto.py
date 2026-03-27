"""Automatic auditor — bulk-approves structurally sound units, skips complex ones."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from audit.models import (
    STATUS_OK,
    AuditState,
    AuditUnit,
    enumerate_units,
    load_verbs,
)

logger = logging.getLogger(__name__)

# Expected merged person keys for standard (non-imperative) tenses.
# After merge, identical forms share keys like "1sm;1sf".
# We check that every base person has at least one key covering it.
_STANDARD_PERSONS = {"1sm", "1sf", "2sm", "2sf", "3sm", "3sf",
                     "1pm", "1pf", "2pm", "2pf", "3pm", "3pf"}
_IMPERATIVE_PERSONS = {"2sm", "2sf", "1pm", "1pf", "2pm", "2pf"}


def _persons_covered(form_data: dict) -> set[str]:
    """Return the set of atomic person keys covered by (possibly merged) keys."""
    covered = set()
    for key in form_data:
        for part in key.split(";"):
            covered.add(part)
    return covered


def _has_semicolons_in_values(form_data: dict) -> bool:
    """Check if any form value contains ';' (alternatives or reform variants)."""
    return any(";" in v for v in form_data.values() if isinstance(v, str))


class _VerbCache:
    """Pre-computed per-verb metadata to avoid repeated filesystem checks."""

    def __init__(self, verbs_data: dict, cache_dir: Path) -> None:
        self._has_html: set[str] = set()
        self._is_reform: set[str] = set()
        cached_files = set(os.listdir(cache_dir))

        for verb, vdata in verbs_data.items():
            if f"{verb}.html" in cached_files:
                self._has_html.add(verb)
            else:
                # Try variant fallback
                variant = vdata.get("rectification_1990_variante")
                if variant and f"{variant}.html" in cached_files:
                    self._has_html.add(verb)

            # A generated reform entry has no î/û but points to one that does
            variant = vdata.get("rectification_1990_variante")
            if variant and "î" not in verb and "û" not in verb and ("î" in variant or "û" in variant):
                self._is_reform.add(verb)

    def has_html(self, verb: str) -> bool:
        return verb in self._has_html

    def is_reform_variant(self, verb: str) -> bool:
        return verb in self._is_reform


def _get_unit_data(unit: AuditUnit, verbs_data: dict) -> dict | None:
    """Extract the form data for a specific audit unit."""
    vdata = verbs_data.get(unit.verb, {})
    voice_data = vdata.get(unit.voice, {})
    if not isinstance(voice_data, dict):
        return None
    mood_data = voice_data.get(unit.mood, {})
    if not isinstance(mood_data, dict):
        return None

    if unit.mood == "participe":
        return mood_data  # entire participe dict

    return mood_data.get(unit.tense, {})


SkipReason = str  # short reason why unit was skipped


def classify_unit(
    unit: AuditUnit,
    verbs_data: dict,
    vcache: _VerbCache,
    state: AuditState,
) -> tuple[bool, SkipReason]:
    """Decide whether a unit can be auto-approved.

    Returns ``(True, "")`` if auto-OK, or ``(False, reason)`` if it should be
    left for human review.
    """
    # Already audited — don't overwrite human decisions
    if state.is_audited(unit):
        return False, "already audited"

    # Reform variant entries have no own HTML and need human review
    if vcache.is_reform_variant(unit.verb):
        return False, "reform variant entry"

    # Must have cached HTML
    if not vcache.has_html(unit.verb):
        return False, "no cached HTML"

    form_data = _get_unit_data(unit, verbs_data)
    if form_data is None:
        return False, "no data in JSON"

    # Participe: gender agreement is complex — always needs human
    if unit.mood == "participe":
        return False, "participe (complex gender)"

    # Empty tense data (defective verb) — human should confirm
    if not form_data:
        return False, "empty tense (defective verb)"

    # Values with semicolons indicate alternatives/reform variants
    if _has_semicolons_in_values(form_data):
        return False, "alternative forms present"

    # Check all values are non-empty strings
    for key, val in form_data.items():
        if not isinstance(val, str) or not val.strip():
            return False, f"empty form value for {key}"

    # Person coverage check
    covered = _persons_covered(form_data)

    if unit.mood == "imperatif":
        if not _IMPERATIVE_PERSONS.issubset(covered):
            return False, "missing imperative persons"
    else:
        if not _STANDARD_PERSONS.issubset(covered):
            return False, "missing person keys"

    return True, ""


# ---------------------------------------------------------------------------
# Main auto-audit runner
# ---------------------------------------------------------------------------

def run_auto_audit(
    json_path: str | Path,
    cache_dir: str | Path,
    progress_path: str | Path,
    auditor: str = "auto",
) -> None:
    """Run automatic audit, approving simple units and skipping complex ones."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    json_path = Path(json_path)
    cache_dir = Path(cache_dir)

    logger.info("Loading %s …", json_path)
    verbs_data = load_verbs(json_path)

    units = enumerate_units(verbs_data)
    state = AuditState(progress_path)
    vcache = _VerbCache(verbs_data, cache_dir)

    logger.info("Total audit units: %d", len(units))
    logger.info("Already audited: %d", state.count_audited())

    auto_ok = 0
    skipped = 0
    already = 0
    skip_reasons: dict[str, int] = {}

    for unit in units:
        ok, reason = classify_unit(unit, verbs_data, vcache, state)
        if ok:
            state.add_record(unit, STATUS_OK, auditor=auditor)
            auto_ok += 1
        else:
            if reason == "already audited":
                already += 1
            else:
                skipped += 1
                skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

    state.flush()

    logger.info("Auto-audit complete.")
    logger.info("  Auto-OK:  %d", auto_ok)
    logger.info("  Skipped:  %d (left for human review)", skipped)
    logger.info("  Already audited: %d (untouched)", already)

    if skip_reasons:
        logger.info("Skip reasons:")
        for reason, count in sorted(skip_reasons.items(), key=lambda x: -x[1]):
            logger.info("  %-35s %d", reason, count)

    logger.info("Progress: %d / %d audited (%.1f%%)",
                state.count_audited(), len(units),
                100 * state.count_audited() / len(units) if units else 0)
    logger.info("Remaining for human review: %d",
                len(units) - state.count_audited())
