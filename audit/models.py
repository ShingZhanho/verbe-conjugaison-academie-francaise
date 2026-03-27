"""Audit data models: loader, audit state, and audit unit definitions."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# ── Audit unit: one tense within one voice of one verb ────────────────────

VOICE_ORDER = [
    "voix_active_avoir",
    "voix_active_etre",
    "voix_active",
    "voix_passive",
    "voix_prono",
]

MOOD_ORDER = ["participe", "indicatif", "subjonctif", "conditionnel", "imperatif"]

TENSE_ORDER = [
    "present",
    "passe",
    "imparfait",
    "passe_simple",
    "futur_simple",
    "passe_compose",
    "plus_que_parfait",
    "passe_anterieur",
    "futur_anterieur",
]


@dataclass(frozen=True)
class AuditUnit:
    """A single reviewable unit: one tense inside one voice of one verb."""

    verb: str
    voice: str
    mood: str
    tense: str

    @property
    def key(self) -> str:
        return f"{self.verb}|{self.voice}|{self.mood}|{self.tense}"


# ── Data loader ───────────────────────────────────────────────────────────


def load_verbs(json_path: str | Path) -> dict:
    """Load the full verbs.json and return the dict."""
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def enumerate_units(data: dict) -> list[AuditUnit]:
    """Enumerate every auditable tense unit across all verbs, in deterministic order."""
    units: list[AuditUnit] = []
    for verb in sorted(data.keys()):
        vdata = data[verb]
        for voice in VOICE_ORDER:
            if voice not in vdata:
                continue
            voice_data = vdata[voice]
            for mood in MOOD_ORDER:
                if mood not in voice_data:
                    continue
                mood_data = voice_data[mood]
                if mood == "participe":
                    # Participle is a single unit (not subdivided by tense keys
                    # in the same way), but it has present/passe sub-keys.
                    units.append(AuditUnit(verb, voice, mood, "participe"))
                else:
                    for tense in TENSE_ORDER:
                        if tense in mood_data:
                            units.append(AuditUnit(verb, voice, mood, tense))
    return units


# ── Audit state persistence (JSONL) ──────────────────────────────────────

STATUS_OK = "ok"
STATUS_FLAGGED = "flagged"
STATUS_SKIPPED = "skipped"


@dataclass
class FlagEntry:
    """One flagged form within a tense."""

    person: str
    note: str = ""

    def to_dict(self) -> dict:
        d: dict = {"person": self.person}
        if self.note:
            d["note"] = self.note
        return d

    @staticmethod
    def from_dict(d: dict) -> FlagEntry:
        return FlagEntry(person=d["person"], note=d.get("note", ""))


@dataclass
class AuditRecord:
    """The stored result of auditing one unit."""

    verb: str
    voice: str
    mood: str
    tense: str
    status: str  # ok | flagged | skipped
    auditor: str = ""
    timestamp: str = ""
    flags: list[FlagEntry] = field(default_factory=list)
    note: str = ""

    @property
    def key(self) -> str:
        return f"{self.verb}|{self.voice}|{self.mood}|{self.tense}"

    def to_dict(self) -> dict:
        d = {
            "verb": self.verb,
            "voice": self.voice,
            "mood": self.mood,
            "tense": self.tense,
            "status": self.status,
            "auditor": self.auditor,
            "ts": self.timestamp,
            "flags": [f.to_dict() for f in self.flags],
        }
        if self.note:
            d["note"] = self.note
        return d

    @staticmethod
    def from_dict(d: dict) -> AuditRecord:
        return AuditRecord(
            verb=d["verb"],
            voice=d["voice"],
            mood=d["mood"],
            tense=d["tense"],
            status=d["status"],
            auditor=d.get("auditor", ""),
            timestamp=d.get("ts", ""),
            flags=[FlagEntry.from_dict(f) for f in d.get("flags", [])],
            note=d.get("note", ""),
        )


class AuditState:
    """Manages audit progress backed by a JSONL file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._records: dict[str, AuditRecord] = {}
        if self._path.exists():
            self._load()

    # ── public API ────────────────────────────────────────────────────

    @property
    def records(self) -> dict[str, AuditRecord]:
        return self._records

    def get(self, unit: AuditUnit) -> AuditRecord | None:
        return self._records.get(unit.key)

    def is_audited(self, unit: AuditUnit) -> bool:
        return unit.key in self._records

    def save_record(self, unit: AuditUnit, status: str, auditor: str,
                    flags: list[FlagEntry] | None = None,
                    note: str = "") -> None:
        record = AuditRecord(
            verb=unit.verb,
            voice=unit.voice,
            mood=unit.mood,
            tense=unit.tense,
            status=status,
            auditor=auditor,
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            flags=flags or [],
            note=note,
        )
        self._records[unit.key] = record
        self._save_all()

    def count_audited(self) -> int:
        return len(self._records)

    def count_flagged(self) -> int:
        return sum(1 for r in self._records.values() if r.status == STATUS_FLAGGED)

    def count_ok(self) -> int:
        return sum(1 for r in self._records.values() if r.status == STATUS_OK)

    def count_skipped(self) -> int:
        return sum(1 for r in self._records.values() if r.status == STATUS_SKIPPED)

    # ── persistence ───────────────────────────────────────────────────

    def _load(self) -> None:
        with open(self._path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = AuditRecord.from_dict(json.loads(line))
                self._records[record.key] = record

    def _save_all(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            for record in self._records.values():
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
