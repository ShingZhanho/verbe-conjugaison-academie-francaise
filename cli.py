"""
Command-line interface for the verb conjugation crawler.
Created on: 2025-11-11
"""

import argparse
import global_vars as gl


def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments using argparse.
    
    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog='crawler.py',
        description='Scrape French verb conjugations from the Académie française dictionary',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python crawler.py --verbose
  python crawler.py --ignore-cache --max-retry 5
  python crawler.py --gen-sqlite3 --gen-infinitives
        """
    )
    
    # Overwrite options group
    overwrite_group = parser.add_argument_group('overwrite options')
    overwrite_group.add_argument(
        '--user-agent',
        dest='user_agent',
        metavar='AGENT',
        help='overwrite the user agent string'
    )
    overwrite_group.add_argument(
        '--jsession-id',
        dest='jsession_id',
        metavar='ID',
        help='overwrite the JSESSION_ID cookie value'
    )
    
    # Configuration options group
    config_group = parser.add_argument_group('configuration options')
    config_group.add_argument(
        '--ignore-cache',
        dest='ignore_cache',
        action='store_true',
        help='ignore cached HTML files and always fetch latest data'
    )
    config_group.add_argument(
        '--max-retry',
        dest='max_retry',
        type=int,
        metavar='N',
        default=gl.CONFIG_MAX_RETRY,
        help=f'maximum number of retries for HTTP requests (default: {gl.CONFIG_MAX_RETRY})'
    )
    config_group.add_argument(
        '--requests-delay',
        dest='requests_delay',
        type=int,
        metavar='MS',
        default=gl.CONFIG_REQUESTS_DELAY,
        help=f'delay between HTTP requests in milliseconds (default: {gl.CONFIG_REQUESTS_DELAY})'
    )
    config_group.add_argument(
        '--max-threads',
        dest='max_threads',
        type=int,
        metavar='N',
        default=gl.CONFIG_MAX_THREADS,
        help=f'maximum number of concurrent threads for parsing (default: {gl.CONFIG_MAX_THREADS})'
    )
    config_group.add_argument(
        '-v', '--verbose',
        dest='verbose',
        action='store_true',
        help='enable verbose output'
    )
    
    # Extension options group
    extension_group = parser.add_argument_group('extension options')
    extension_group.add_argument(
        '--gen-sqlite3',
        dest='gen_sqlite3',
        action='store_true',
        help='generate an SQLite3 database file (verbs.db)'
    )
    extension_group.add_argument(
        '--gen-infinitives',
        dest='gen_infinitives',
        action='store_true',
        help='generate infinitives list from AF dictionary (skips conjugation data)'
    )
    
    return parser.parse_args()


def apply_arguments(args: argparse.Namespace) -> None:
    """
    Apply parsed arguments to global variables.
    
    Args:
        args: Parsed command-line arguments
    """
    # Overwrite options
    if args.user_agent:
        gl.USER_AGENT = args.user_agent
    
    if args.jsession_id:
        gl.COOKIE_JSESSION_ID = args.jsession_id
    
    # Configuration options
    gl.CONFIG_IGNORE_CACHE = args.ignore_cache
    gl.CONFIG_MAX_RETRY = args.max_retry
    
    if args.requests_delay < 0:
        raise ValueError("Requests delay must be a non-negative integer")
    gl.CONFIG_REQUESTS_DELAY = args.requests_delay
    
    if args.max_threads < 1:
        raise ValueError("Max threads must be at least 1")
    gl.CONFIG_MAX_THREADS = args.max_threads
    
    gl.CONFIG_VERBOSE = args.verbose
    
    # Extension options
    gl.EXTENSION_GEN_SQLITE3 = args.gen_sqlite3
    gl.EXTENSION_GEN_INFINITIVES = args.gen_infinitives
