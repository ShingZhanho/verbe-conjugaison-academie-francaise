"""HTML panel — renders the cached HTML for a specific tense via QWebEngineView."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel

if TYPE_CHECKING:
    from audit.models import AuditUnit

# Maps JSON voice keys → HTML div id search candidates
_VOICE_TO_HTML_IDS: dict[str, list[str]] = {
    "voix_active_avoir": ["voix_active_avoir", "voix_active"],
    "voix_active_etre": ["voix_active_être", "voix_active"],
    "voix_active": ["voix_active"],
    "voix_passive": ["voix_passive"],
    "voix_prono": ["voix_prono"],
}

# Maps JSON mood keys → HTML div id suffix
_MOOD_TO_ID_SUFFIX: dict[str, str] = {
    "participe": "par",
    "indicatif": "ind",
    "subjonctif": "sub",
    "conditionnel": "con",
    "imperatif": "imp",
}

# Maps JSON tense key → French display name (lowercase for matching)
_TENSE_DISPLAY: dict[str, str] = {
    "present": "présent",
    "passe": "passé",
    "imparfait": "imparfait",
    "passe_simple": "passé simple",
    "futur_simple": "futur simple",
    "passe_compose": "passé composé",
    "plus_que_parfait": "plus-que-parfait",
    "passe_anterieur": "passé antérieur",
    "futur_anterieur": "futur antérieur",
    "participe": "participe",
}

_WRAPPER_CSS = """\
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    padding: 16px;
    background: #fafaf8;
    color: #333;
  }
  h3 { color: #555; margin: 0 0 4px 0; font-size: 13px; text-transform: uppercase; }
  h4 { color: #1a5276; margin: 8px 0 4px 0; font-size: 14px; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 8px; }
  tr.conj_line td { padding: 3px 8px; border-bottom: 1px solid #eee; }
  td.conj_pers-pron { color: #888; white-space: nowrap; }
  td.conj_refl-pron { color: #888; white-space: nowrap; }
  td.conj_auxil { color: #666; white-space: nowrap; }
  td.conj_verb { font-weight: 600; color: #1a5276; }
  span.or { color: #c0392b; font-style: italic; padding: 0 2px; }
  span.forme_rectif { color: #7d3c98; font-style: italic; }
  .no-data { color: #999; font-style: italic; padding: 20px; }
</style>
"""


class HtmlPanel(QWidget):
    """Right-side panel showing the source HTML for a tense."""

    def __init__(self, cache_dir: str | Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cache_dir = Path(cache_dir)
        self._web = QWebEngineView()
        self._header = QLabel("Source HTML")
        self._header.setStyleSheet("font-weight: bold; font-size: 13px; color: #555;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._header)
        layout.addWidget(self._web)

    def show_unit(self, unit: AuditUnit) -> None:
        """Load and display the HTML for the given audit unit."""
        html_path = self._cache_dir / f"{unit.verb}.html"
        if not html_path.exists():
            self._web.setHtml(
                _WRAPPER_CSS + '<div class="no-data">No cached HTML found.</div>'
            )
            self._header.setText(f"Source HTML — {unit.verb} (not found)")
            return

        raw_html = html_path.read_text(encoding="utf-8")
        tense_html = self._extract_tense_html(raw_html, unit)

        display_tense = _TENSE_DISPLAY.get(unit.tense, unit.tense)
        voice_label = unit.voice.replace("_", " ")
        mood_label = unit.mood.capitalize()

        self._header.setText(
            f"Source HTML — {unit.verb} › {voice_label} › {mood_label} › {display_tense}"
        )

        if tense_html:
            full = f"<!DOCTYPE html><html><head>{_WRAPPER_CSS}</head><body>"
            full += f"<h3>{voice_label} — {mood_label}</h3>"
            full += f"<h4>{display_tense.title()}</h4>"
            full += tense_html
            full += "</body></html>"
        else:
            full = (
                _WRAPPER_CSS
                + '<div class="no-data">Could not extract tense HTML from source.</div>'
            )
        self._web.setHtml(full)

    def _extract_tense_html(self, raw_html: str, unit: AuditUnit) -> str | None:
        """Extract the HTML table for a specific mood+tense within a voice."""
        from bs4 import BeautifulSoup, Tag

        soup = BeautifulSoup(raw_html, "lxml")

        # Find the voice div
        voice_tag = None
        for html_id in _VOICE_TO_HTML_IDS.get(unit.voice, []):
            voice_tag = soup.find("div", id=html_id)
            if voice_tag:
                break
        if voice_tag is None:
            return None

        # Find the mood div within the voice
        mood_suffix = _MOOD_TO_ID_SUFFIX.get(unit.mood)
        if mood_suffix is None:
            return None

        # The mood div has id like "active_ind", "prono_par" etc.
        mood_tag = None
        for div in voice_tag.find_all("div", class_="time"):
            div_id = div.get("id", "")
            if div_id.endswith(f"_{mood_suffix}"):
                mood_tag = div
                break

        if mood_tag is None:
            return None

        # For participle, return the entire mood section
        if unit.mood == "participe":
            return str(mood_tag.find("div", class_="grid"))

        # Find the specific tense by matching the h4.relation text
        target = _TENSE_DISPLAY.get(unit.tense, "").lower()
        for tense_div in mood_tag.find_all("div", class_="tense"):
            h4 = tense_div.find("h4", class_="relation")
            if h4 and h4.get_text(strip=True).lower() == target:
                return str(tense_div)

        return None
