"""
HTTP client for making requests to the Académie française dictionary.
Created on: 2025-11-11
"""

import global_vars as gl
import log
import requests
import time
from typing import Optional, Dict


class DictionaryHTTPClient:
    """HTTP client for interacting with the Académie française dictionary."""
    
    def __init__(self):
        """Initialize the HTTP client."""
        self.jsession_id = gl.COOKIE_JSESSION_ID
    
    def _get_headers(self, referer: Optional[str] = None, content_type: Optional[str] = None) -> Dict[str, str]:
        """
        Build HTTP headers for requests.
        
        Args:
            referer: Optional referer URL
            content_type: Optional content type
            
        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            "Accept": gl.HEADER_ACCEPT,
            "Accept-Encoding": gl.HEADER_ACCEPT_ENCODING,
            "Accept-Language": gl.HEADER_ACCEPT_LANGUAGE,
            "User-Agent": gl.USER_AGENT,
            "Sec-Fetch-Site": gl.HEADER_SEC_FETCH_SITE,
            "Sec-Fetch-Mode": gl.HEADER_SEC_FETCH_MODE,
            "Sec-Fetch-Dest": gl.HEADER_SEC_FETCH_DEST,
        }
        
        if content_type:
            headers["Content-Type"] = content_type
        
        if referer:
            headers["Referer"] = referer
        
        return headers
    
    def _get_cookies(self, last_entry_id: Optional[str] = None) -> str:
        """
        Build cookie string for requests.
        
        Args:
            last_entry_id: Optional last entry ID
            
        Returns:
            Cookie string
        """
        cookies = f"JSESSIONID={self.jsession_id}; {gl.HEADER_MISC_COOKIES}"
        if last_entry_id:
            cookies += f"; lastEntry={last_entry_id}"
        return cookies
    
    def obtain_jsession_id(self) -> Optional[str]:
        """
        Obtain JSESSION_ID from the root URL.
        
        Returns:
            JSESSION_ID value or None if failed
        """
        headers = self._get_headers()
        headers["Sec-Fetch-Site"] = "none"
        headers["Sec-Fetch-Mode"] = "navigate"
        headers["Sec-Fetch-Dest"] = "document"
        
        try:
            log.info(f"GET {gl.URL_ROOT}")
            response = requests.get(gl.URL_ROOT, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Extract JSESSION_ID from Set-Cookie header
            set_cookie = response.headers.get("Set-Cookie")
            if set_cookie:
                import re
                match = re.search(r"JSESSIONID=([^;]+)", set_cookie)
                if match:
                    self.jsession_id = match.group(1)
                    gl.COOKIE_JSESSION_ID = self.jsession_id
                    return self.jsession_id
            
            log.warning("JSESSION_ID not found in response")
            return None
            
        except requests.RequestException as e:
            log.fatal(f"An error occurred while obtaining JSESSION_ID: {e}")
            return None
    
    def search_entry(self, verb: str, prev_entry_id: Optional[str] = None) -> Optional[tuple[str, str]]:
        """
        Search for a verb entry in the dictionary.
        
        Args:
            verb: The verb to search for
            prev_entry_id: Optional previous entry ID
            
        Returns:
            Tuple of (entry_id, verb_nature) or None if not found
        """
        headers = self._get_headers(
            referer=f"{gl.URL_ROOT}article/{prev_entry_id}" if prev_entry_id else None,
            content_type=gl.HEADER_CONTENT_TYPE
        )
        headers["Cookie"] = self._get_cookies(prev_entry_id)
        
        data = f"term={verb}&options=1"
        
        for attempt in range(1, gl.CONFIG_MAX_RETRY + 1):
            if attempt > 1:
                time.sleep(gl.CONFIG_REQUESTS_DELAY / 1000)
            
            try:
                log.info(f"POST {gl.URL_SEARCH} --data \"{data}\" (attempt {attempt}/{gl.CONFIG_MAX_RETRY})")
                response = requests.post(gl.URL_SEARCH, headers=headers, data=data, timeout=30)
                response.raise_for_status()
                
                response_json = response.json()
                log.verbose(f"Response JSON: {response_json}", gl.CONFIG_VERBOSE)
                
                results_arr = response_json.get("result", [])
                if not results_arr:
                    log.warning(f"No results found for verb '{verb}'.")
                    return None
                
                for entry in results_arr:
                    entry_url = entry.get("url")
                    entry_label = entry.get("label", "").replace(" (s')", "").replace(" (se)", "")
                    entry_nature = entry.get("nature", "")
                    
                    if "v." not in entry_nature:
                        continue
                    
                    if entry_label == verb:
                        entry_id = entry_url.split("/")[-1]
                        return entry_id, entry_nature
                
                log.warning(f"Failed to find an exact match for verb '{verb}'.")
                return None
                
            except requests.RequestException as e:
                log.warning(f"Request failed for verb '{verb}': {e}. {gl.CONFIG_MAX_RETRY - attempt} attempts left.")
                if attempt == gl.CONFIG_MAX_RETRY:
                    return None
                continue
            except Exception as e:
                log.warning(f"An error occurred while searching for verb '{verb}': {e}.")
                return None
        
        return None
    
    def download_conjugation(self, verb: str, verb_id: str, prev_id: Optional[str] = None) -> bool:
        """
        Download the conjugation webpage for a verb.
        
        Args:
            verb: The infinitive form of the verb
            verb_id: The ID of the verb entry
            prev_id: Optional previous entry ID
            
        Returns:
            True if successful, False otherwise
        """
        headers = self._get_headers(
            referer=f"{gl.URL_ROOT}article/{prev_id}" if prev_id else None,
            content_type=gl.HEADER_CONTENT_TYPE
        )
        headers["Cookie"] = self._get_cookies(prev_id)
        
        try:
            url = f"{gl.URL_CONJUGATION_TABLE}{verb_id}"
            log.info(f"GET {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            with open(f"./output/cache/{verb}.html", "w", encoding="utf-8") as out:
                out.write(response.text)
            
            return True
            
        except requests.RequestException as e:
            log.warning(f"Failed to download conjugation webpage for verb '{verb}': {e}")
            return False
        except Exception as e:
            log.warning(f"An error occurred while downloading conjugation webpage for verb '{verb}': {e}")
            return False
