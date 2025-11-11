"""
An extension for generating infinitives from AF dictionary.
Created on: 2025-06-05 10:19:06 HKT
Created by: Jacob Shing
"""

from bs4 import BeautifulSoup
import global_vars as gl
import json
import log
import os
import requests
import constants as const

def gen_infs_main():
    """
    Generates the infinitives.txt file from the AF dictionary.
    """
    headers = {
        "Accept": gl.EXT_GEN_INFS_HEADER_ACCEPT,
        "Accept-Encoding": gl.HEADER_ACCEPT_ENCODING,
        "Accept-Language": gl.HEADER_ACCEPT_LANGUAGE,
        "Content-Type": gl.HEADER_CONTENT_TYPE,
        "Cookie": f"{gl.HEADER_MISC_COOKIES}; JSESSIONID={gl.COOKIE_JSESSION_ID}",
        "User-Agent": gl.USER_AGENT,
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Dest": "document"
    }
    
    for alphabet in range(ord('a'), ord('z') + 1):
        alphabet_char = chr(alphabet)
        data = gl.EXT_GEN_INFS_HEADER_DATA.replace("{% ALPHABET %}", alphabet_char)
        
        try:
            log.info(f"GET {gl.EXT_GEN_INFS_URL} for alphabet '{alphabet_char.upper()}'")
            response = requests.post(gl.EXT_GEN_INFS_URL, headers=headers, data=data.replace(" ", "%20"))
            response.raise_for_status()  # Raise an error for bad responses
            
            soup = BeautifulSoup(response.text, 'html.parser')
            list_items = soup.select('div#colGaucheResultat ul.listColGauche li')
            if not list_items:
                log.warning(f"No infinitives found for alphabet '{alphabet_char.upper()}'")
                continue
            log.info(f"Found {len(list_items)} infinitives for alphabet '{alphabet_char.upper()}'")

            inf_list = []
            for item in list_items:
                raw_entry_data = item.text
                entry_data = raw_entry_data.split(',')[0].strip().replace(" (s’)", "").replace(" (se)", "").replace(" (s')", "")
                inf_list.append(entry_data)
            inf_list = sorted(set(inf_list))  # Remove duplicates and sort
            log.info(f"Found {len(inf_list)} unique infinitives for alphabet '{alphabet_char.upper()}'")

            gen_infs_output = f"{const.DIR_GEN_INFS}/infinitives.txt"
            with open(gen_infs_output, "a", encoding="utf-8") as f:
                for inf in inf_list:
                    f.write(f"{inf}\n")
        except Exception as e:
            log.error(f"An error occurred while generating infinitives for alphabet '{alphabet_char.upper()}': {e}")
            continue
                