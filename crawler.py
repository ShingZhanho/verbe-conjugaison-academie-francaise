"""
Created on: 2025-06-02 12:57:45 HKT
Created by: Jacob Shing
"""

import log
import sys

# Global variables
HEADER_ACCEPT = "application/json, text/javascript, */*; q=0.01"
HEADER_CONTENT_TYPE = "application/x-www-form-urlencoded; charset=UTF-8"
HEADER_SEC_FETCH_SITE = "same-origin"
HEADER_SEC_FETCH_MODE = "cors"
HEADER_SEC_FETCH_DEST = "empty"
COOKIE_JSESSION_ID = None # Obtained from the website during runtime
URL_ROOT = "https://dictionnaire-academie.fr/"
URL_SEARCH = f"{URL_ROOT}/search"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15"

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

if __name__ == "__main__":
    main()