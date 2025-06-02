"""
Created on: 2025-06-02 12:57:45 HKT
Created by: Jacob Shing
"""

import core
from global_vars import USER_AGENT, COOKIE_JSESSION_ID
import log
import sys

# Handle command line options
def parse_cmd_args(args: list):
    """
    Parses command line arguments. Modifies the necessary global variables.
    Does not return anything. args should not include the script name.
    """
    counter = 0
    while counter < len(args):
        if args[counter] == "-OUSER-AGENT":
            counter += 1
            if counter >= len(args):
                log.fatal("Missing value for overwrite option -OUSER-AGENT.")
            global USER_AGENT
            USER_AGENT = args[counter]
        elif args[counter] == "-OCOOKIE-JSESSION-ID":
            counter += 1
            if counter >= len(args):
                log.fatal("Missing value for overwrite option -OCOOKIE-JSESSION-ID.")
            global COOKIE_JSESSION_ID
            COOKIE_JSESSION_ID = args[counter]
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
    global COOKIE_JSESSION_ID
    if COOKIE_JSESSION_ID is None:
        log.info("JSESSION_ID is not set. Obtaining it from the website...")
        COOKIE_JSESSION_ID = core.obtain_jsession_id()
    log.info(f"JSESSION_ID is set to {COOKIE_JSESSION_ID}.")

if __name__ == "__main__":
    main()