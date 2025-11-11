"""
Main crawler script for extracting French verb conjugations.
Created on: 2025-06-02 12:57:45 HKT
Updated on: 2025-11-11
Created by: Jacob Shing
"""

import cli
import core
import extensions.db as ext_db
import extensions.gen_infinitives as ext_gen_infs
import global_vars as gl
import json
import log
import os
import sys

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
        "./output",
        "./output/cache",
        "./output/parsed",
    ]
    out_dirs.append("./output/gen_infs") if gl.EXTENSION_GEN_INFINITIVES else None
    [os.makedirs(dir, exist_ok=True) for dir in out_dirs if not os.path.exists(dir)]

    if gl.EXTENSION_GEN_INFINITIVES:
        ext_gen_infs.gen_infs_main()
        return

    total_verbs = 0
    verbs_counter = 0
    with open("./infinitives.txt", "rb") as f:
        total_verbs = sum(1 for _ in f)
    
    # iterate over the verb infinitives from infinitives.txt
    with open("./infinitives.txt", "r", encoding="utf-8") as f:
        prev_id = None

        for infinitive in f:
            infinitive = infinitive.strip()
            verbs_counter += 1

            log.verbose(f"({verbs_counter:>{len(str(total_verbs))}}/{total_verbs}) Checking infinitive cache: {infinitive}", gl.CONFIG_VERBOSE)
            # == CHECK IF ALREADY PARSED ==
            if not gl.CONFIG_IGNORE_CACHE and os.path.exists(f"./output/parsed/{infinitive}.txt"):
                log.verbose(f"Verb '{infinitive}' already parsed. Skipping.", gl.CONFIG_VERBOSE)
                continue

            # == SEARCH IF THE VERB EXISTS IN THE DICTIONARY ==
            if not gl.CONFIG_IGNORE_CACHE and os.path.exists(f"./output/cache/{infinitive}.txt"):
                log.verbose(f"Using cached result for infinitive '{infinitive}'.", gl.CONFIG_VERBOSE)
                with open(f"./output/cache/{infinitive}.txt", "r", encoding="utf-8") as out:
                    content = out.read().strip()
                if content == "NOT_FOUND_SKIPPED" or content == "PARSE_FAILED":
                    continue
                else:
                    verb_id, verb_nature = content.split("\n")
                    log.info(f"Cached verb ID: {verb_id}, Nature: {verb_nature}.")
            else:
                log.info(f"({verbs_counter:>{len(str(total_verbs))}}/{total_verbs}) Processing: {infinitive}")
                search = core.search_entry(infinitive, prev_id)
                if search is None:
                    log.warning(f"Failed to find entry for infinitive '{infinitive}'. Skipping this verb.")
                    with open(f"./output/cache/{infinitive}.txt", "w", encoding="utf-8") as out:
                        out.write(f"NOT_FOUND_SKIPPED")
                    continue
                verb_id, verb_nature = search
                log.info(f"Found verb ID: {verb_id}, Nature: {verb_nature} for infinitive '{infinitive}'.")
                with open(f"./output/cache/{infinitive}.txt", "w", encoding="utf-8") as out:
                    out.write(f"{verb_id}\n{verb_nature}")

            # == DOWNLOAD THE CONJUGATION WEBPAGE ==
            if not gl.CONFIG_IGNORE_CACHE and os.path.exists(f"./output/cache/{infinitive}.html"):
                log.info(f"Using cached conjugation webpage for infinitive '{infinitive}'. Skipping download.")
            else:
                prev_id = verb_id
                log.info(f"Downloading conjugation webpage for verb {infinitive} ({verb_id})...")
                core.download_conjugation(infinitive, verb_id, prev_id)

            # == PROCESS THE HTML FILE AND GENERATE PARTIAL JSON ==
            parse_success = core.parse_conjugation_page(infinitive, verb_id, verb_nature)
            if not parse_success:
                log.error(f"Failed to parse conjugation page for verb '{infinitive}'. Manual entry may be required.")
                with open(f"./output/cache/{infinitive}.txt", "w", encoding="utf-8") as out:
                    out.write(f"PARSE_FAILED")

    log.info(f"All verbs ({verbs_counter}) processed.")
    
    # == MERGE ALL PARTIAL JSON FILES ==
    with open("./output/verbs.min.json", "w", encoding="utf-8") as out:
        parsed = sorted([f for f in os.listdir("./output/parsed") if ".txt" in f])
        log.info(f"Merging all parsed ({len(parsed)}) entries...")
        out.write("{")
        for i, file in enumerate(parsed):
            with open(f"./output/parsed/{file}", "r", encoding="utf-8") as f:
                content = f.read().strip()
                out.write(content)
                if i < len(parsed) - 1:
                    out.write(",")
        out.write("}")
    with open("./output/verbs.min.json", "r", encoding="utf-8") as min_file:
        log.info("Writing to ./output/verbs.min.json")
        min_data = json.load(min_file)
    with open("./output/verbs.json", "w", encoding="utf-8") as out:
        log.info("Writing to ./output/verbs.json")
        json.dump(min_data, out, ensure_ascii=False, indent=4)

    # == GENERATE SQLITE3 DATABASE IF REQUIRED ==
    if gl.EXTENSION_GEN_SQLITE3:
        log.info("Generating SQLite3 database...")
        ext_db.generate_sqlite_db(min_data)

if __name__ == "__main__":
    main()