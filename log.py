"""
Simple functions to write logs to stdout.
Created on: 2025-06-02 13:41:57 HKT
Created by: Jacob Shing
"""
import time

def _write_log(message: str, tag: str = "INFO", ansi_seq: str = "\033[0m") -> None:
    """
    (Internal) Writes a log message to stdout with a specific tag.
    """
    print(f"{ansi_seq}{time.strftime('%Y-%m-%d %H:%M:%S')} [{tag}] {message}")

def info(message: str) -> None:
    """
    Writes an info log message to stdout.
    """
    _write_log(message)

def warning(message: str) -> None:
    """
    Writes a warning log message to stdout.
    """
    _write_log(message, tag="WARNING", ansi_seq="\033[1;33m")

def error(message: str) -> None:
    """
    Writes an error log message to stdout.
    """
    _write_log(message, tag="ERROR", ansi_seq="\033[1;31m")

def fatal(message: str, exit_code: int = 1) -> None:
    """
    Writes a fatal error log message to stdout and exits the program.
    """
    _write_log(message, tag="FATAL", ansi_seq="\033[1;31m")
    exit(exit_code)
