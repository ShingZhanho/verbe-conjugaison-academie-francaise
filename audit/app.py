"""Main window — ties together all panels, navigation, and audit controls."""

from __future__ import annotations

import csv
import io
import random
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QPalette, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from audit.html_panel import HtmlPanel
from audit.json_panel import JsonPanel
from audit.models import (
    STATUS_FLAGGED,
    STATUS_OK,
    STATUS_SKIPPED,
    AuditState,
    AuditUnit,
    FlagEntry,
    enumerate_units,
    load_verbs,
)

_FILTER_ALL = "All"
_FILTER_UNAUDITED = "Unaudited"
_FILTER_FLAGGED = "Flagged"
_FILTER_OK = "OK"
_FILTER_SKIPPED = "Skipped"

_VOICE_ALL = "All voices"
_VOICE_LABELS: dict[str, str] = {
    "voix_active_avoir": "Active (avoir)",
    "voix_active_etre": "Active (être)",
    "voix_active": "Active",
    "voix_passive": "Passive",
    "voix_prono": "Pronominale",
}


class MainWindow(QMainWindow):
    def __init__(
        self,
        json_path: str | Path,
        cache_dir: str | Path,
        progress_path: str | Path,
        auditor: str = "",
    ) -> None:
        super().__init__()
        self.setWindowTitle("Conjugation Audit")
        self.resize(1400, 800)

        # ── data ──────────────────────────────────────────────────────
        self._data = load_verbs(json_path)
        self._all_units = enumerate_units(self._data)
        random.shuffle(self._all_units)
        self._state = AuditState(progress_path)
        self._auditor = auditor or "anonymous"
        self._cache_dir = Path(cache_dir)

        # Filtered view
        self._filtered_units: list[AuditUnit] = list(self._all_units)
        self._current_index = 0

        # Dark mode detection
        pal = QApplication.instance().palette()
        self._dark = pal.color(QPalette.ColorRole.Window).lightnessF() < 0.5

        # ── panels ────────────────────────────────────────────────────
        self._json_panel = JsonPanel(self._data)
        self._html_panel = HtmlPanel(self._cache_dir)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._json_panel)
        splitter.addWidget(self._html_panel)
        splitter.setSizes([600, 600])

        # ── top bar: search + filter + progress ───────────────────────
        self._search = QLineEdit()
        self._search.setPlaceholderText("Jump to verb…")
        self._search.setMaximumWidth(220)
        self._search.returnPressed.connect(self._on_search)

        self._filter_combo = QComboBox()
        self._filter_combo.addItems([
            _FILTER_ALL, _FILTER_UNAUDITED, _FILTER_FLAGGED,
            _FILTER_OK, _FILTER_SKIPPED,
        ])
        self._filter_combo.setMaximumWidth(140)
        self._filter_combo.currentTextChanged.connect(self._on_filter_changed)

        self._voice_combo = QComboBox()
        self._voice_combo.addItem(_VOICE_ALL)
        for key, label in _VOICE_LABELS.items():
            self._voice_combo.addItem(label, key)
        self._voice_combo.setMaximumWidth(160)
        self._voice_combo.currentIndexChanged.connect(self._on_filter_changed)

        self._btn_export = QPushButton("Export flagged")
        self._btn_export.setMaximumWidth(120)
        self._btn_export.clicked.connect(self._export_flagged)

        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(True)
        self._progress_label = QLabel()

        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Search:"))
        top_bar.addWidget(self._search)
        top_bar.addSpacing(12)
        top_bar.addWidget(QLabel("Status:"))
        top_bar.addWidget(self._filter_combo)
        top_bar.addSpacing(12)
        top_bar.addWidget(QLabel("Voice:"))
        top_bar.addWidget(self._voice_combo)
        top_bar.addSpacing(12)
        top_bar.addWidget(self._btn_export)
        top_bar.addSpacing(12)
        top_bar.addWidget(self._progress_bar, stretch=1)
        top_bar.addWidget(self._progress_label)

        # ── bottom bar: navigation + audit actions ────────────────────
        self._lbl_position = QLabel()
        pos_color = "#ddd" if self._dark else "inherit"
        self._lbl_position.setStyleSheet(
            f"font-weight: bold; min-width: 120px; color: {pos_color};"
        )

        btn_prev = QPushButton("◀ Previous")
        btn_prev.clicked.connect(self._go_prev)
        btn_next = QPushButton("Next ▶")
        btn_next.clicked.connect(self._go_next)

        self._btn_ok = QPushButton("✓ Mark OK")
        self._btn_ok.setStyleSheet(
            "QPushButton { background: #27ae60; color: white; padding: 6px 16px; "
            "border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #229954; }"
        )
        self._btn_ok.clicked.connect(self._mark_ok)

        self._btn_flag = QPushButton("✗ Flag Issues")
        self._btn_flag.setStyleSheet(
            "QPushButton { background: #e74c3c; color: white; padding: 6px 16px; "
            "border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #c0392b; }"
        )
        self._btn_flag.clicked.connect(self._mark_flagged)

        self._btn_skip = QPushButton("Skip")
        self._btn_skip.setStyleSheet(
            "QPushButton { background: #95a5a6; color: white; padding: 6px 16px; "
            "border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background: #7f8c8d; }"
        )
        self._btn_skip.clicked.connect(self._mark_skipped)

        self._note_input = QLineEdit()
        self._note_input.setPlaceholderText("Describe the issue…")
        self._note_input.setMinimumWidth(260)

        bottom_bar = QHBoxLayout()
        bottom_bar.addWidget(btn_prev)
        bottom_bar.addWidget(self._lbl_position)
        bottom_bar.addWidget(btn_next)
        bottom_bar.addSpacing(12)
        bottom_bar.addWidget(QLabel("Note:"))
        bottom_bar.addWidget(self._note_input, stretch=1)
        bottom_bar.addSpacing(12)
        bottom_bar.addWidget(self._btn_ok)
        bottom_bar.addWidget(self._btn_flag)
        bottom_bar.addWidget(self._btn_skip)

        # ── assemble ──────────────────────────────────────────────────
        central = QWidget()
        main_layout = QVBoxLayout(central)
        main_layout.addLayout(top_bar)
        main_layout.addWidget(splitter, stretch=1)
        main_layout.addLayout(bottom_bar)
        self.setCentralWidget(central)

        # ── keyboard shortcuts (Alt+ to avoid conflict with search) ───
        QShortcut(QKeySequence("Alt+N"), self, self._go_next)
        QShortcut(QKeySequence("Alt+P"), self, self._go_prev)
        QShortcut(QKeySequence("Alt+O"), self, self._mark_ok)
        QShortcut(QKeySequence("Alt+F"), self, self._mark_flagged)
        QShortcut(QKeySequence("Alt+S"), self, self._mark_skipped)
        QShortcut(QKeySequence("Alt+Right"), self, self._go_next)
        QShortcut(QKeySequence("Alt+Left"), self, self._go_prev)

        # ── initial display ───────────────────────────────────────────
        self._advance_to_first_unaudited()
        self._show_current()

    # ── navigation ────────────────────────────────────────────────────

    def _go_next(self) -> None:
        if self._current_index < len(self._filtered_units) - 1:
            self._current_index += 1
            self._show_current()

    def _go_prev(self) -> None:
        if self._current_index > 0:
            self._current_index -= 1
            self._show_current()

    def _advance_to_first_unaudited(self) -> None:
        """Set the index to the first unaudited unit in the filtered list."""
        for i, unit in enumerate(self._filtered_units):
            if not self._state.is_audited(unit):
                self._current_index = i
                return
        self._current_index = 0

    def _show_current(self) -> None:
        if not self._filtered_units:
            self._lbl_position.setText("No units to display")
            self._update_progress()
            return

        unit = self._filtered_units[self._current_index]

        # Update both panels
        self._json_panel.show_unit(unit)
        self._html_panel.show_unit(unit)

        # Restore flag state if previously audited
        record = self._state.get(unit)
        if record and record.flags:
            self._json_panel.set_flags([f.person for f in record.flags])

        # Restore note
        self._note_input.setText(record.note if record else "")

        # Position label
        self._lbl_position.setText(
            f"{self._current_index + 1} / {len(self._filtered_units)}"
        )

        # Highlight action buttons based on existing audit state
        self._update_button_states(record)
        self._update_progress()

    def _update_button_states(self, record) -> None:
        """Dim the previously-chosen action button."""
        for btn in (self._btn_ok, self._btn_flag, self._btn_skip):
            btn.setEnabled(True)
        if record:
            if record.status == STATUS_OK:
                self._btn_ok.setText("✓ Marked OK")
            elif record.status == STATUS_FLAGGED:
                self._btn_flag.setText("✗ Flagged")
            elif record.status == STATUS_SKIPPED:
                self._btn_skip.setText("Skipped")
        else:
            self._btn_ok.setText("✓ Mark OK")
            self._btn_flag.setText("✗ Flag Issues")
            self._btn_skip.setText("Skip")

    # ── audit actions ─────────────────────────────────────────────────

    def _mark_ok(self) -> None:
        unit = self._filtered_units[self._current_index]
        self._state.save_record(unit, STATUS_OK, self._auditor,
                                note=self._note_input.text().strip())
        self._auto_advance()

    def _mark_flagged(self) -> None:
        unit = self._filtered_units[self._current_index]
        flagged = self._json_panel.get_flagged_persons()
        flags = [FlagEntry(person=p) for p in flagged]
        self._state.save_record(unit, STATUS_FLAGGED, self._auditor, flags,
                                note=self._note_input.text().strip())
        self._auto_advance()

    def _mark_skipped(self) -> None:
        unit = self._filtered_units[self._current_index]
        self._state.save_record(unit, STATUS_SKIPPED, self._auditor,
                                note=self._note_input.text().strip())
        self._auto_advance()

    def _auto_advance(self) -> None:
        """After auditing, advance to the next unaudited unit."""
        start = self._current_index + 1
        for i in range(start, len(self._filtered_units)):
            if not self._state.is_audited(self._filtered_units[i]):
                self._current_index = i
                self._show_current()
                return
        # If nothing after current, wrap around
        for i in range(0, start):
            if not self._state.is_audited(self._filtered_units[i]):
                self._current_index = i
                self._show_current()
                return
        # All audited — stay
        self._show_current()

    # ── search ────────────────────────────────────────────────────────

    def _on_search(self) -> None:
        query = self._search.text().strip().lower()
        if not query:
            return
        for i, unit in enumerate(self._filtered_units):
            if unit.verb.lower().startswith(query):
                self._current_index = i
                self._show_current()
                return
        QMessageBox.information(self, "Not found", f"No verb starting with '{query}'.")

    # ── filter ────────────────────────────────────────────────────────

    def _on_filter_changed(self, *_args) -> None:
        status_text = self._filter_combo.currentText()
        voice_key = self._voice_combo.currentData()  # None for "All voices"

        units = self._all_units

        # Status filter
        if status_text == _FILTER_UNAUDITED:
            units = [u for u in units if not self._state.is_audited(u)]
        elif status_text == _FILTER_FLAGGED:
            units = [
                u for u in units
                if self._state.get(u) and self._state.get(u).status == STATUS_FLAGGED
            ]
        elif status_text == _FILTER_OK:
            units = [
                u for u in units
                if self._state.get(u) and self._state.get(u).status == STATUS_OK
            ]
        elif status_text == _FILTER_SKIPPED:
            units = [
                u for u in units
                if self._state.get(u) and self._state.get(u).status == STATUS_SKIPPED
            ]

        # Voice filter
        if voice_key:
            units = [u for u in units if u.voice == voice_key]

        self._filtered_units = units
        self._current_index = 0
        self._show_current()

    # ── progress ──────────────────────────────────────────────────────

    def _update_progress(self) -> None:
        total = len(self._all_units)
        audited = self._state.count_audited()
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(audited)

        ok = self._state.count_ok()
        flagged = self._state.count_flagged()
        skipped = self._state.count_skipped()
        pct = (audited / total * 100) if total else 0
        self._progress_label.setText(
            f"{audited}/{total} ({pct:.1f}%) — "
            f"OK: {ok}  Flagged: {flagged}  Skipped: {skipped}"
        )

    # ── export ────────────────────────────────────────────────────────

    def _export_flagged(self) -> None:
        """Export all flagged records to a CSV file."""
        flagged = [
            r for r in self._state.records.values()
            if r.status == STATUS_FLAGGED
        ]
        if not flagged:
            QMessageBox.information(self, "Export", "No flagged items to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export flagged items", "audit/flagged_report.csv",
            "CSV files (*.csv);;All files (*)",
        )
        if not path:
            return

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["verb", "voice", "mood", "tense", "flagged_persons", "note", "auditor", "timestamp"])
            for r in sorted(flagged, key=lambda r: (r.verb, r.voice, r.mood, r.tense)):
                persons = "; ".join(fl.person for fl in r.flags)
                writer.writerow([r.verb, r.voice, r.mood, r.tense, persons, r.note, r.auditor, r.timestamp])

        QMessageBox.information(
            self, "Export", f"Exported {len(flagged)} flagged items to:\n{path}"
        )
