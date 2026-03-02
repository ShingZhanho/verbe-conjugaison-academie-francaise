"""Command-line interface and main entry point."""

from __future__ import annotations

import argparse
import logging
import sys

from verbe_af import __version__, constants as C
from verbe_af.cache import (
    ensure_directories,
    count_lines,
    merge_parsed_files,
    read_infinitives,
    write_formatted_json,
)
from verbe_af.client import DictionaryClient
from verbe_af.config import Config
from verbe_af.crawler import VerbCrawler
from verbe_af.exceptions import CrawlerError, ConfigError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verbe_af",
        description="Scrape French verb conjugations from the Académie française dictionary.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  python -m verbe_af --verbose
  python -m verbe_af --ignore-cache --max-retry 5
  python -m verbe_af --gen-sqlite3
  python -m verbe_af --gen-infinitives""",
    )

    over = parser.add_argument_group("overwrite options")
    over.add_argument("--user-agent", metavar="AGENT", help="override the User-Agent header")
    over.add_argument("--jsession-id", metavar="ID", help="override the JSESSIONID cookie")

    cfg = parser.add_argument_group("configuration")
    cfg.add_argument("--ignore-cache", action="store_true", help="re-fetch and re-parse everything")
    cfg.add_argument("--max-retry", type=int, default=5, metavar="N", help="HTTP retry limit (default: 5)")
    cfg.add_argument("--requests-delay", type=int, default=500, metavar="MS",
                     help="delay between requests in ms (default: 500)")
    cfg.add_argument("--max-threads", type=int, default=4, metavar="N",
                     help="worker threads (default: 4)")
    cfg.add_argument("-v", "--verbose", action="store_true", help="enable verbose output")
    cfg.add_argument("--log-file", metavar="PATH", default=None,
                     help="write log output to this file in addition to the terminal")

    ext = parser.add_argument_group("extensions")
    ext.add_argument("--gen-sqlite3", action="store_true", help="generate SQLite database")
    ext.add_argument("--gen-infinitives", action="store_true",
                     help="generate infinitives list (skip conjugation crawl)")

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _build_config(ns: argparse.Namespace) -> Config:
    """Convert parsed arguments into a :class:`Config` instance."""
    if ns.requests_delay < 0:
        raise ConfigError("--requests-delay must be non-negative")
    if ns.max_threads < 1:
        raise ConfigError("--max-threads must be at least 1")

    cfg = Config(
        ignore_cache=ns.ignore_cache,
        max_retry=ns.max_retry,
        request_delay_ms=ns.requests_delay,
        max_threads=ns.max_threads,
        verbose=ns.verbose,
        gen_sqlite3=ns.gen_sqlite3,
        gen_infinitives=ns.gen_infinitives,
    )
    if ns.user_agent:
        cfg.user_agent = ns.user_agent
    if ns.jsession_id:
        cfg.jsession_id = ns.jsession_id
    cfg.log_file = ns.log_file
    return cfg


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(verbose: bool, log_file: str | None = None) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)

    # Console handler (coloured, stderr)
    class _ColouredFormatter(logging.Formatter):
        _COLOURS = {
            logging.WARNING: "\033[1;33m",
            logging.ERROR: "\033[1;31m",
            logging.CRITICAL: "\033[1;31m",
        }
        _RESET = "\033[0m"

        def format(self, record: logging.LogRecord) -> str:
            colour = self._COLOURS.get(record.levelno, self._RESET)
            copy = logging.makeLogRecord(record.__dict__)
            copy.msg = f"{colour}{record.msg}{self._RESET}"
            return super().format(copy)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(_ColouredFormatter(fmt, datefmt=datefmt))
    root.addHandler(console)

    # Optional file handler (plain text, no ANSI codes)
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        root.addHandler(fh)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = _build_parser()
    ns = parser.parse_args(argv)

    try:
        cfg = _build_config(ns)
    except ConfigError as exc:
        parser.error(str(exc))

    _setup_logging(cfg.verbose, cfg.log_file)
    logger.info("verbe_af %s — starting (args: %s)", __version__, " ".join(sys.argv[1:]))

    client = DictionaryClient(cfg)

    # Ensure JSESSIONID
    if cfg.jsession_id is None:
        logger.info("Obtaining JSESSIONID …")
        cfg.jsession_id = client.obtain_jsession_id()
    logger.info("JSESSIONID = %s", cfg.jsession_id)

    # Prepare directories
    dirs = [C.DIR_OUTPUT, C.DIR_CACHE, C.DIR_PARSED]
    if cfg.gen_infinitives:
        dirs.append(C.DIR_GEN_INFS)
    ensure_directories(dirs)

    # Extension: generate infinitives only
    if cfg.gen_infinitives:
        logger.warning("Running gen-infinitives extension (conjugation crawl skipped).")
        from verbe_af.extensions.gen_infinitives import generate_infinitives
        generate_infinitives(cfg, client)
        return

    # Main crawl
    total = count_lines(C.FILE_INFINITIVES)
    verbs = read_infinitives(C.FILE_INFINITIVES)
    logger.info("Processing %d verbs with %d thread(s) …", total, cfg.max_threads)

    crawler = VerbCrawler(cfg, client)
    success, failed = crawler.run(verbs)
    logger.info("Done: %d succeeded, %d failed.", success, len(failed))

    if failed and cfg.verbose:
        logger.info("Failed verbs: %s%s",
                     ", ".join(failed[:10]),
                     " …" if len(failed) > 10 else "")

    # Merge output
    logger.info("Merging parsed entries → %s", C.FILE_VERBS_MIN_JSON)
    try:
        merged = merge_parsed_files()
    except CrawlerError:
        logger.exception("Failed to merge parsed files.")
        sys.exit(1)

    logger.info("Writing formatted JSON → %s", C.FILE_VERBS_JSON)
    write_formatted_json(merged, C.FILE_VERBS_JSON)

    # Extension: SQLite
    if cfg.gen_sqlite3:
        logger.info("Generating SQLite database …")
        from verbe_af.extensions.db import generate_sqlite_db
        generate_sqlite_db(cfg, merged)
