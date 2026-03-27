"""Entry point for the audit GUI: ``python -m audit``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from audit.app import MainWindow


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manual audit GUI for parsed French conjugation data.",
    )
    parser.add_argument(
        "--json",
        default="output/verbs.json",
        help="Path to verbs.json (default: output/verbs.json)",
    )
    parser.add_argument(
        "--cache",
        default="output/cache",
        help="Path to the HTML cache directory (default: output/cache)",
    )
    parser.add_argument(
        "--progress",
        default="audit/progress.jsonl",
        help="Path to the audit progress file (default: audit/progress.jsonl)",
    )
    parser.add_argument(
        "--auditor",
        default="",
        help="Auditor name recorded in the progress file.",
    )
    args = parser.parse_args()

    json_path = Path(args.json)
    cache_dir = Path(args.cache)

    if not json_path.exists():
        print(f"Error: {json_path} not found. Run the pipeline first.", file=sys.stderr)
        sys.exit(1)
    if not cache_dir.is_dir():
        print(f"Error: {cache_dir} not found.", file=sys.stderr)
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("Conjugation Audit")

    window = MainWindow(
        json_path=json_path,
        cache_dir=cache_dir,
        progress_path=args.progress,
        auditor=args.auditor,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
