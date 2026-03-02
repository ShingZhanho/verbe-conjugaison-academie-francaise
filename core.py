"""
Core components for the crawler.
Created at: 2025-06-02 13:59:27 HKT
Updated on: 2025-11-11
Created by: Jacob Shing
"""

import re
from bs4 import BeautifulSoup
import conjugation_parser as conj
import global_vars as gl
import constants as const
from http_client import DictionaryHTTPClient
import json
import log
from typing import Optional
import data_transformer


# Create a global HTTP client instance
_http_client = DictionaryHTTPClient()


def obtain_jsession_id() -> Optional[str]:
    """
    Makes a GET request to the root URL and obtain the JSESSION_ID from the cookies.
    Returns:
        str: The JSESSION_ID cookie value.
    """
    return _http_client.obtain_jsession_id()


def search_entry(verb: str, prev_entry_id: Optional[str] = None) -> Optional[str]:
    """
    Searches for the entry of a verb in the dictionary.
    Args:
        verb (str): The verb to search for.
        prev_entry_id (str, optional): The previous entry ID to continue from. Defaults to None.
    Returns:
        str | None: The entry ID, or None if not found.
    """
    return _http_client.search_entry(verb, prev_entry_id)


def download_conjugation(verb: str, verb_id: str, prev_id: Optional[str] = None) -> bool:
    """
    Downloads the conjugation webpage for a given verb.
    Args:
        verb (str): The infinitive form of the verb.
        verb_id (str): The ID of the verb entry in the dictionary.
        prev_id (str, optional): The previous entry ID to continue from. Defaults to None.
    Returns:
        bool: True if the download was successful, False otherwise.
    """
    return _http_client.download_conjugation(verb, verb_id, prev_id)

def parse_conjugation_page(verb: str, verb_id: str) -> bool:
    """
    Parses the conjugation webpage for a given verb and extracts the conjugation data.
    Args:
        verb (str): The infinitive form of the verb.
        verb_id (str): The ID of the verb entry in the dictionary.
    Returns:
        bool: True if the parsing was successful, False otherwise.
    """
    try:  # read file and parse html
        cache_path = f"{const.DIR_CACHE}/{verb}.html"
        with open(cache_path, "r", encoding="utf-8") as f:
            raw_html = f.read()
        conj_page_soup = BeautifulSoup(raw_html, "lxml")
        conj_page_root = conj_page_soup.find("div", id=verb_id)
        if conj_page_root is None:
            # Fallback: try to find any div whose ID starts with "A9" (handles homonym ID mismatches)
            conj_page_root = conj_page_soup.find("div", id=lambda x: x and x.startswith("A9"))
            if conj_page_root is not None:
                log.info(f"Verb '{verb}': expected div#{verb_id}, found div#{conj_page_root['id']} instead. Using fallback.")
            else:
                log.warning(f"Conjugation page for verb '{verb}' does not contain any conjugation div.")
                return False
        
        # If the cached file contains a full HTML page, shrink it to div-only
        stripped = raw_html.lstrip()
        if stripped.startswith("<!DOCTYPE") or stripped.startswith("<html"):
            log.info(f"Shrinking cached HTML for verb '{verb}' (removing non-essential tags)...")
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(str(conj_page_root))
    except Exception as e:
        log.warning(f"An error occurred while reading the conjugation page for verb '{verb}': {e}.")
        return False
    
    parsed = conj.parse_conjugation_table(conj_page_root, verb)

    if parsed is None:
        log.warning(f"No conjugation data found for verb '{verb}'.")
        return False

    # Transform the parsed data to new format
    verb_data = parsed[verb]  # Extract verb data from {verb: {...}} structure
    transformed = data_transformer.transform_verb_data(verb, verb_data)
    
    # Write the main entry
    transformed_with_key = {verb: transformed}
    min_json = json.dumps(transformed_with_key, ensure_ascii=False, separators=(',', ':'), indent=None)
    min_json = min_json.replace("  ", " ").replace("'", "'")  # Replace double spaces and apostrophes
    with open(f"{const.DIR_PARSED}/{verb}.txt", "w", encoding="utf-8") as out:
        out.write(min_json[1:-1])  # Remove the outer braces
    
    # Create reformed spelling entry if applicable
    reformed_entry = data_transformer.create_reformed_verb_entry(verb, transformed)
    if reformed_entry:
        reformed_name, reformed_data = reformed_entry
        reformed_with_key = {reformed_name: reformed_data}
        min_json = json.dumps(reformed_with_key, ensure_ascii=False, separators=(',', ':'), indent=None)
        min_json = min_json.replace("  ", " ").replace("'", "'")
        with open(f"{const.DIR_PARSED}/{reformed_name}.txt", "w", encoding="utf-8") as out:
            out.write(min_json[1:-1])
    
    return True

def try_update_jsession_id(response, fatal_on_missing = False) -> None:
    """
    Checks if the response contains a new JSESSION_ID and updates the global variable if it does.
    Args:
        response (requests.Response): The response object to check for a new JSESSION_ID.
        fatal_on_missing (bool): If True, log a fatal error if JSESSION_ID is not found. Defaults to False.
    """
    set_cookie = response.headers.get("Set-Cookie")
    if set_cookie:
        match = re.search(r"JSESSIONID=([^;]+)", set_cookie)
        if match:
            new_jsession_id = match.group(1)
            if new_jsession_id != gl.COOKIE_JSESSION_ID:
                log.info(f"Updating JSESSION_ID to {new_jsession_id}.")
                gl.COOKIE_JSESSION_ID = new_jsession_id
        else:
            if fatal_on_missing:
                log.fatal("JSESSION_ID not found in Set-Cookie header")
            else:
                log.warning("JSESSION_ID not found in Set-Cookie header.")
    else:
        if fatal_on_missing:
            log.fatal("Set-Cookie header not found in response.")
        else:
            log.warning("Set-Cookie header not found in response.")
