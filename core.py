"""
Core components for the crawler.
Created at: 2025-06-02 13:59:27 HKT
Created by: Jacob Shing
"""

import global_vars as gl
import log
import re
import requests
import time

def obtain_jsession_id() -> str | None:
    """
    Makes a GET request to the root URL and obtain the JSESSION_ID from the cookies.
    Returns:
        str: The JSESSION_ID cookie value.
    """
    headers = {
        "Accept": gl.HEADER_ACCEPT,
        "Accept-Encoding": gl.HEADER_ACCEPT_ENCODING,
        "Accept-Language": gl.HEADER_ACCEPT_LANGUAGE,
        "User-Agent": gl.USER_AGENT,
        "Content-Type": gl.HEADER_CONTENT_TYPE,
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document",
    }

    try:
        log.info(f"GET {gl.URL_ROOT}")
        response = requests.get(gl.URL_ROOT, headers=headers)
        if (response.status_code != 200):
            log.fatal(f"Failed to obtain JSESSION_ID. Status code: {response.status_code}")
        response.raise_for_status()  # Raise an error for bad responses
        try_update_jsession_id(response)
    except requests.RequestException as e:
        log.fatal(f"An error occurred while obtaining JSESSION_ID: {e}")

    return gl.COOKIE_JSESSION_ID

def search_entry(verb: str, prev_entry_id: str | None = None) -> tuple[str, str] | None:
    """
    Searches for the entry of a verb in the dictionary.
    Args:
        verb (str): The verb to search for.
        prev_entry_id (str, optional): The previous entry ID to continue from. Defaults to None.
    Returns:
        tuple[str, str] | None: A tuple containing the entry ID and the verb's nature, or None if not found.
    """
    cookies_str = f"JSESSIONID={gl.COOKIE_JSESSION_ID}; {gl.HEADER_MISC_COOKIES}"
    if prev_entry_id:
        cookies_str += f"; lastEntry={prev_entry_id}"
    headers = {
        "Accept": gl.HEADER_ACCEPT,
        "Accept-Encoding": gl.HEADER_ACCEPT_ENCODING,
        "Accept-Language": gl.HEADER_ACCEPT_LANGUAGE,
        "User-Agent": gl.USER_AGENT,
        "Content-Type": gl.HEADER_CONTENT_TYPE,
        "Cookie": cookies_str,
        "Sec-Fetch-Site": gl.HEADER_SEC_FETCH_SITE,
        "Sec-Fetch-Mode": gl.HEADER_SEC_FETCH_MODE,
        "Sec-Fetch-Dest": gl.HEADER_SEC_FETCH_DEST,
    }
    if prev_entry_id:
        headers["Referer"] = f"{gl.URL_ROOT}article/{prev_entry_id}"
    data = f"term={verb}&options=1"

    attempts = 0
    response_json = None

    while attempts < gl.CONFIG_MAX_RETRY:
        if attempts > 0:
            time.sleep(gl.CONFIG_REQUESTS_DELAY / 1000)
        attempts += 1
        try:
            log.info(f"POST {gl.URL_SEARCH} --data \"{data}\"")
            response = requests.post(gl.URL_SEARCH, headers=headers, data=data)
            if response.status_code != 200:
                log.warning(f"Failed to search for verb '{verb}'. Status code: {response.status_code}. {gl.CONFIG_MAX_RETRY - attempts} attempts left.")
                continue
            response.raise_for_status()  # Raise an error for bad responses
            response_json = response.json()
        except Exception as e:
            log.warning(f"An error occurred while searching for verb '{verb}': {e}. {gl.CONFIG_MAX_RETRY - attempts} attempts left.")
            continue
        
        # Decode the response JSON
        log.verbose(f"Response JSON: {response_json}", gl.CONFIG_VERBOSE)
        results_arr = response_json.get("result", [])
        if len(results_arr) == 0:
            log.warning(f"No results found for verb '{verb}'.")
            return None
        for entry in results_arr:
            entry_url = entry.get("url")
            entry_label = entry.get("label")
            entry_nature = entry.get("nature")
            if entry_label != verb: # look for the exact match
                continue
            entry_id = entry_url.split("/")[-1]  # Extract the entry ID from the URL
            return entry_id, entry_nature
        # If we reach here, it means we didn't find the exact match
        log.warning(f"Failed to find an exact match for verb '{verb}'.")
        return None

    return None

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
