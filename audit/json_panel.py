"""JSON panel — displays parsed conjugation data with per-form flag buttons."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from audit.models import AuditUnit

# Display labels for person keys
_PERSON_LABELS: dict[str, str] = {
    "1sm": "je (m)",
    "1sf": "je (f)",
    "2sm": "tu (m)",
    "2sf": "tu (f)",
    "3sm": "il",
    "3sf": "elle",
    "1pm": "nous (m)",
    "1pf": "nous (f)",
    "2pm": "vous (m)",
    "2pf": "vous (f)",
    "3pm": "ils",
    "3pf": "elles",
}

# Participle key labels
_PARTICIPLE_LABELS: dict[str, str] = {
    "present": "Présent",
    "sm": "Passé (m.s.)",
    "sf": "Passé (f.s.)",
    "pm": "Passé (m.p.)",
    "pf": "Passé (f.p.)",
    "compound_sm": "Composé (m.s.)",
    "compound_sf": "Composé (f.s.)",
    "compound_pm": "Composé (m.p.)",
    "compound_pf": "Composé (f.p.)",
    "present_sm": "Présent (m.s.)",
    "present_sf": "Présent (f.s.)",
    "present_pm": "Présent (m.p.)",
    "present_pf": "Présent (f.p.)",
}


def _is_dark_mode() -> bool:
    pal = QApplication.instance().palette()
    return pal.color(QPalette.ColorRole.Window).lightnessF() < 0.5


class FlagButton(QPushButton):
    """Toggle button for flagging a single form."""

    flag_toggled = Signal(str, bool)  # person_key, is_flagged

    def __init__(self, person_key: str, parent: QWidget | None = None) -> None:
        super().__init__("Flag", parent)
        self._person_key = person_key
        self._flagged = False
        self._dark = _is_dark_mode()
        self.setCheckable(True)
        self.setFixedWidth(50)
        self.setStyleSheet(self._style())
        self.clicked.connect(self._on_click)

    def _on_click(self) -> None:
        self._flagged = self.isChecked()
        self.setText("✗" if self._flagged else "Flag")
        self.setStyleSheet(self._style())
        self.flag_toggled.emit(self._person_key, self._flagged)

    def set_flagged(self, flagged: bool) -> None:
        self._flagged = flagged
        self.setChecked(flagged)
        self.setText("✗" if flagged else "Flag")
        self.setStyleSheet(self._style())

    @property
    def is_flagged(self) -> bool:
        return self._flagged

    @property
    def person_key(self) -> str:
        return self._person_key

    def _style(self) -> str:
        if self._flagged:
            return (
                "QPushButton { background: #e74c3c; color: white; border: none; "
                "border-radius: 3px; padding: 2px 6px; font-weight: bold; }"
            )
        if self._dark:
            return (
                "QPushButton { background: #444; color: #aaa; border: 1px solid #666; "
                "border-radius: 3px; padding: 2px 6px; }"
                "QPushButton:hover { background: #553333; color: #e74c3c; border-color: #e74c3c; }"
            )
        return (
            "QPushButton { background: #ecf0f1; color: #666; border: 1px solid #ccc; "
            "border-radius: 3px; padding: 2px 6px; }"
            "QPushButton:hover { background: #fadbd8; color: #c0392b; border-color: #e74c3c; }"
        )


def _person_label(key: str) -> str:
    """Build a human-readable label for a (possibly merged) person key."""
    parts = key.split(";")
    labels = [_PERSON_LABELS.get(p, p) for p in parts]
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for lab in labels:
        if lab not in seen:
            seen.add(lab)
            unique.append(lab)
    return ", ".join(unique)


class JsonPanel(QWidget):
    """Left-side panel showing parsed JSON data with flag buttons."""

    flags_changed = Signal()  # emitted when any flag is toggled

    def __init__(self, data: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._data = data
        self._flag_buttons: list[FlagButton] = []
        self._dark = _is_dark_mode()

        header_color = "#ccc" if self._dark else "#555"
        self._header = QLabel("Parsed Data")
        self._header.setStyleSheet(
            f"font-weight: bold; font-size: 13px; color: {header_color};"
        )

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 8, 8, 8)
        self._scroll.setWidget(self._content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._header)
        layout.addWidget(self._scroll)

    def show_unit(self, unit: AuditUnit) -> None:
        """Display the parsed data for the given unit."""
        self._clear_content()
        self._flag_buttons.clear()

        voice_label = unit.voice.replace("_", " ")
        mood_label = unit.mood.capitalize()
        tense_label = unit.tense.replace("_", " ").title()
        self._header.setText(
            f"Parsed JSON — {unit.verb} › {voice_label} › {mood_label} › {tense_label}"
        )

        verb_data = self._data.get(unit.verb, {})
        voice_data = verb_data.get(unit.voice, {})
        mood_data = voice_data.get(unit.mood, {})

        if unit.mood == "participe":
            self._render_participle(mood_data)
        else:
            tense_data = mood_data.get(unit.tense, {})
            self._render_tense(tense_data)

        self._content_layout.addStretch()

    def get_flagged_persons(self) -> list[str]:
        """Return a list of person keys that are currently flagged."""
        return [b.person_key for b in self._flag_buttons if b.is_flagged]

    def set_flags(self, flagged_persons: list[str]) -> None:
        """Restore flag state from a list of person keys."""
        flagged_set = set(flagged_persons)
        for btn in self._flag_buttons:
            btn.set_flagged(btn.person_key in flagged_set)

    def _render_tense(self, tense_data: dict) -> None:
        """Render a regular tense (person → conjugation)."""
        if not tense_data:
            lbl = QLabel("(no data)")
            lbl.setStyleSheet("color: #999; font-style: italic; padding: 12px;")
            self._content_layout.addWidget(lbl)
            return

        for person_key, conjugation in tense_data.items():
            self._add_form_row(person_key, _person_label(person_key), conjugation)

    def _render_participle(self, participle_data: dict) -> None:
        """Render the participle section."""
        if not participle_data:
            lbl = QLabel("(no data)")
            lbl.setStyleSheet("color: #999; font-style: italic; padding: 12px;")
            self._content_layout.addWidget(lbl)
            return

        present = participle_data.get("present")
        if present is not None:
            if isinstance(present, dict):
                for sub_key, val in present.items():
                    full_key = f"present_{sub_key}"
                    label = _PARTICIPLE_LABELS.get(full_key, f"Présent ({sub_key})")
                    self._add_form_row(full_key, label, str(val))
            else:
                self._add_form_row("present", "Présent", str(present))

        passe = participle_data.get("passe")
        if isinstance(passe, dict):
            for sub_key, val in passe.items():
                label = _PARTICIPLE_LABELS.get(sub_key, sub_key)
                self._add_form_row(f"passe.{sub_key}", label, str(val))

    def _add_form_row(self, key: str, label: str, value: str) -> None:
        """Add a single form row: [label] [value] [flag button]."""
        row = QHBoxLayout()
        row.setSpacing(8)

        lbl_color = "#aaa" if self._dark else "#888"
        lbl = QLabel(label)
        lbl.setFixedWidth(160)
        lbl.setStyleSheet(
            f"color: {lbl_color}; font-size: 13px; padding: 4px 0;"
        )

        val_color = "#5dade2" if self._dark else "#1a5276"
        val = QLabel(value)
        val.setStyleSheet(
            f"font-weight: 600; color: {val_color}; font-size: 14px; padding: 4px 0;"
        )
        val.setWordWrap(True)

        btn = FlagButton(key)
        btn.flag_toggled.connect(lambda *_: self.flags_changed.emit())
        self._flag_buttons.append(btn)

        row.addWidget(lbl)
        row.addWidget(val, stretch=1)
        row.addWidget(btn)

        self._content_layout.addLayout(row)

    def _clear_content(self) -> None:
        """Remove all widgets from the content layout."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())
