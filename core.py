"""
Core components for the crawler.
Created at: 2025-06-02 13:59:27 HKT
Created by: Jacob Shing
"""

import global_vars as gl
import log
import re
import requests

def obtain_jsession_id() -> str|None:
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

    result = None

    try:
        log.info(f"GET {gl.URL_ROOT}")
        response = requests.get(gl.URL_ROOT, headers=headers)
        if (response.status_code != 200):
            log.fatal(f"Failed to obtain JSESSION_ID. Status code: {response.status_code}")
        response.raise_for_status()  # Raise an error for bad responses
        set_cookie = response.headers.get("Set-Cookie") # match for "JSESSIONID=(...); ..."
        if set_cookie:
            match = re.search(r"JSESSIONID=([^;]+)", set_cookie)
            if match:
                result = match.group(1)
            else:
                log.fatal("JSESSION_ID not found in Set-Cookie header.")
        else:
            log.fatal("Set-Cookie header not found in response.")
    except requests.RequestException as e:
        log.fatal(f"An error occurred while obtaining JSESSION_ID: {e}")

    return result
