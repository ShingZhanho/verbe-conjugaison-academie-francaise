"""
Main crawler script for extracting French verb conjugations.
Created on: 2025-06-02 12:57:45 HKT
Updated on: 2025-11-11
Created by: Jacob Shing
"""

import cli
import constants as const
import core
import extensions.db as ext_db
import extensions.gen_infinitives as ext_gen_infs
import file_utils
import global_vars as gl
import log
import sys


def process_verb(infinitive: str, verb_counter: int, total_verbs: int, prev_id: str = None) -> tuple[bool, str]:
    """
    Process a single verb: search, download, and parse.
    
    Args:
        infinitive: The verb infinitive
        verb_counter: Current verb number
        total_verbs: Total number of verbs
        prev_id: Previous entry ID
        
    Returns:
        Tuple of (success, new_prev_id)
    """
    width = len(str(total_verbs))
    log.verbose(f"({verb_counter:>{width}}/{total_verbs}) Checking infinitive cache: {infinitive}", gl.CONFIG_VERBOSE)
    
    # Check if already parsed
    if not gl.CONFIG_IGNORE_CACHE and file_utils.cache_exists(infinitive, "parsed"):
        log.verbose(f"Verb '{infinitive}' already parsed. Skipping.", gl.CONFIG_VERBOSE)
        return True, prev_id
    
    # Check cached search result
    if not gl.CONFIG_IGNORE_CACHE and file_utils.cache_exists(infinitive, "txt"):
        log.verbose(f"Using cached result for infinitive '{infinitive}'.", gl.CONFIG_VERBOSE)
        content = file_utils.read_cache_file(infinitive)
        
        if content in (const.CACHE_NOT_FOUND, const.CACHE_PARSE_FAILED):
            return False, prev_id
        
        verb_id, verb_nature = content.split("\n")
        log.info(f"Cached verb ID: {verb_id}, Nature: {verb_nature}.")
    else:
        # Search for the verb
        log.info(f"({verb_counter:>{width}}/{total_verbs}) Processing: {infinitive}")
        search_result = core.search_entry(infinitive, prev_id)
        
        if search_result is None:
            log.warning(f"Failed to find entry for infinitive '{infinitive}'. Skipping this verb.")
            file_utils.write_cache_file(infinitive, const.CACHE_NOT_FOUND)
            return False, prev_id
        
        verb_id, verb_nature = search_result
        log.info(f"Found verb ID: {verb_id}, Nature: {verb_nature} for infinitive '{infinitive}'.")
        file_utils.write_cache_file(infinitive, f"{verb_id}\n{verb_nature}")
    
    # Download conjugation webpage
    if not gl.CONFIG_IGNORE_CACHE and file_utils.cache_exists(infinitive, "html"):
        log.info(f"Using cached conjugation webpage for infinitive '{infinitive}'. Skipping download.")
    else:
        prev_id = verb_id
        log.info(f"Downloading conjugation webpage for verb {infinitive} ({verb_id})...")
        if not core.download_conjugation(infinitive, verb_id, prev_id):
            file_utils.write_cache_file(infinitive, const.CACHE_PARSE_FAILED)
            return False, prev_id
    
    # Parse the HTML file
    parse_success = core.parse_conjugation_page(infinitive, verb_id, verb_nature)
    if not parse_success:
        log.error(f"Failed to parse conjugation page for verb '{infinitive}'. Manual entry may be required.")
        file_utils.write_cache_file(infinitive, const.CACHE_PARSE_FAILED)
        return False, prev_id
    
    return True, verb_id

def main():
    """
    Entry point.
    """
    log.info("\n\t=== VERBE-CONJUGAISION-ACADÉMIE-FRANÇAISE CRAWLER ===\n\t\tProgram invoked with arguments: " + " ".join(sys.argv[1:]))
    
    # Parse command-line arguments
    log.info("Parsing command line arguments...")
    try:
        args = cli.parse_arguments()
        cli.apply_arguments(args)
    except ValueError as e:
        log.fatal(str(e))
    
    if gl.CONFIG_VERBOSE:
        log.verbose("Verbose mode enabled.", gl.CONFIG_VERBOSE)
    
    if gl.EXTENSION_GEN_INFINITIVES:
        log.warning("Using extension GEN-INFINITIVES. This will only generate the infinitives.txt file.")

    # Check if JSESSION_ID is set
    log.info("Checking JSESSION_ID...")
    if gl.COOKIE_JSESSION_ID is None:
        log.info("JSESSION_ID is not set. Obtaining it from the website...")
        gl.COOKIE_JSESSION_ID = core.obtain_jsession_id()
    log.info(f"JSESSION_ID is set to {gl.COOKIE_JSESSION_ID}.")

    # Prepare output directories
    log.info("Preparing output directories...")
    out_dirs = [
        const.DIR_OUTPUT,
        const.DIR_CACHE,
        const.DIR_PARSED,
    ]
    if gl.EXTENSION_GEN_INFINITIVES:
        out_dirs.append(const.DIR_GEN_INFS)
    file_utils.ensure_directories(out_dirs)

    if gl.EXTENSION_GEN_INFINITIVES:
        ext_gen_infs.gen_infs_main()
        return

    # Count and process verbs
    total_verbs = file_utils.count_lines(const.FILE_INFINITIVES)
    infinitives = file_utils.read_infinitives_file(const.FILE_INFINITIVES)
    
    verbs_counter = 0
    prev_id = None
    
    for infinitive in infinitives:
        verbs_counter += 1
        success, prev_id = process_verb(infinitive, verbs_counter, total_verbs, prev_id)

    log.info(f"All verbs ({verbs_counter}) processed.")
    
    # Merge all partial JSON files
    log.info("Merging all parsed entries...")
    min_data = file_utils.merge_parsed_files(const.FILE_VERBS_MIN_JSON)
    log.info(f"Writing to {const.FILE_VERBS_MIN_JSON}")
    
    log.info(f"Writing to {const.FILE_VERBS_JSON}")
    file_utils.write_formatted_json(min_data, const.FILE_VERBS_JSON)

    # == GENERATE SQLITE3 DATABASE IF REQUIRED ==
    if gl.EXTENSION_GEN_SQLITE3:
        log.info("Generating SQLite3 database...")
        ext_db.generate_sqlite_db(min_data)

if __name__ == "__main__":
    main()