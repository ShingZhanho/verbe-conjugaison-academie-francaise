"""
Created on: 2025-06-02 12:57:45 HKT
Created by: Jacob Shing
"""

import core
import global_vars as gl
import log
import os
import sys

# Handle command line options
def parse_cmd_args(args: list):
    """
    Parses command line arguments. Modifies the necessary global variables.
    Does not return anything. args should not include the script name.
    """
    counter = 0
    while counter < len(args):
        if args[counter] == "-O:USER-AGENT":
            counter += 1
            if counter >= len(args):
                log.fatal("Missing value for overwrite option -O:USER-AGENT.")
            gl.USER_AGENT = args[counter]
        elif args[counter] == "-O:COOKIE-JSESSION-ID":
            counter += 1
            if counter >= len(args):
                log.fatal("Missing value for overwrite option -O:COOKIE-JSESSION-ID.")
            gl.COOKIE_JSESSION_ID = args[counter]
        elif args[counter] == "-C:IGNORE-CACHE":
            gl.CONFIG_IGNORE_CACHE = True
        elif args[counter] == "-C:MAX-RETRY":
            counter += 1
            if counter >= len(args) or not args[counter].isdigit():
                log.fatal("Missing or invalid value for configuration option -C:MAX-RETRY.")
            gl.CONFIG_MAX_RETRY = int(args[counter])
        elif args[counter] == "-C:REQUESTS-DELAY":
            counter += 1
            if counter >= len(args) or not args[counter].isdigit():
                log.fatal("Missing or invalid value for configuration option -C:REQUESTS-DELAY.")
            if int(args[counter]) < 0:
                log.fatal("Configuration option -C:REQUESTS-DELAY must be a non-negative integer.")
            gl.CONFIG_REQUESTS_DELAY = int(args[counter])
        elif args[counter] == "-C:VERBOSE":
            gl.CONFIG_VERBOSE = True
            log.verbose("Verbose mode enabled.", gl.CONFIG_VERBOSE)
        else:
            log.warning(f"Unknown command line option {args[counter]}. Ignored.")
        counter += 1

def main():
    """
    Entry point.
    """
    log.info("\n\t=== VERBE-CONJUGAISION-ACADÉMIE-FRANÇAISE CRAWLER ===\n\t\tProgram invoked with arguments: " + " ".join(sys.argv[1:]))
    log.info("Parsing command line arguments...")
    parse_cmd_args(sys.argv[1:])

    # Check if JSESSION_ID is set
    log.info("Checking JSESSION_ID...")
    if gl.COOKIE_JSESSION_ID is None:
        log.info("JSESSION_ID is not set. Obtaining it from the website...")
        gl.COOKIE_JSESSION_ID = core.obtain_jsession_id()
    log.info(f"JSESSION_ID is set to {gl.COOKIE_JSESSION_ID}.")

    # Prepare output directories
    log.info("Preparing output directories...")
    if not os.path.exists("./output"):
        os.makedirs("./output")
    if not os.path.exists("./output/cache"):
        os.makedirs("./output/cache")

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
            log.info(f"({verbs_counter:>{len(str(total_verbs))}}/{total_verbs}) Processing infinitive: {infinitive}")

            # == SEARCH IF THE VERB EXISTS IN THE DICTIONARY ==
            if not gl.CONFIG_IGNORE_CACHE and os.path.exists(f"./output/cache/{infinitive}.txt"):
                log.info(f"Using cached result for infinitive '{infinitive}'. Skipping.")
                continue
            else:
                search = core.search_entry(infinitive, prev_id)
                if search is None:
                    log.warning(f"Failed to find entry for infinitive '{infinitive}'. Skipping this verb.")
                    with open(f"./output/cache/{infinitive}.txt", "w", encoding="utf-8") as out:
                        out.write(f"NOT_FOUND_SKIPPED")
                    continue
                verb_id, verb_nature = search
                log.info(f"Found verb ID: {verb_id}, Nature: {verb_nature} for infinitive '{infinitive}'.")

            # == DOWNLOAD THE CONJUGATION WEBPAGE ==
            if not gl.CONFIG_IGNORE_CACHE and os.path.exists(f"./output/cache/{infinitive}.html"):
                log.info(f"Using cached conjugation webpage for infinitive '{infinitive}'. Skipping download.")
            else:
                prev_id = verb_id
                log.info(f"Downloading conjugation webpage for verb {infinitive} ({verb_id})...")
                core.download_conjugation(infinitive, verb_id, prev_id)

if __name__ == "__main__":
    main()