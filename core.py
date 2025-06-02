"""
Core components for the crawler.
Created at: 2025-06-02 13:59:27 HKT
Created by: Jacob Shing
"""

import log

def obtain_jsession_id() -> str:
    """
    Makes a GET request to the root URL and obtain the JSESSION_ID from the cookies.
    Returns:
        str: The JSESSION_ID cookie value.
    """
    return "NOT_IMPLEMENTED"  # TODO: Implement the actual request to obtain JSESSION_ID