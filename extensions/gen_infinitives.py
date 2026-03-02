"""
An extension for generating infinitives from AF dictionary.
Created on: 2025-06-05 10:19:06 HKT
Created by: Jacob Shing
"""

from bs4 import BeautifulSoup
import global_vars as gl
import log
import os
import requests
import constants as const


def gen_infs_main():
    """
    Generate the infinitives.txt file from the AF dictionary.
    Each line is in the format: <verb>:<verb_id>
    The verb_id is extracted from the entry's href (e.g. ../article/A9A0009 -> A9A0009).
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

    gen_infs_output = f"{const.DIR_GEN_INFS}/infinitives.txt"

    # Clear the output file if it already exists
    if os.path.exists(gen_infs_output):
        os.remove(gen_infs_output)

    for alphabet in range(ord('a'), ord('z') + 1):
        alphabet_char = chr(alphabet)
        data = gl.EXT_GEN_INFS_HEADER_DATA.replace("{% ALPHABET %}", alphabet_char)

        try:
            log.info(f"POST {gl.EXT_GEN_INFS_URL} for alphabet '{alphabet_char.upper()}'")
            response = requests.post(gl.EXT_GEN_INFS_URL, headers=headers, data=data.replace(" ", "%20"))
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            list_items = soup.select('div#colGaucheResultat ul.listColGauche li')
            if not list_items:
                log.warning(f"No infinitives found for alphabet '{alphabet_char.upper()}'")
                continue
            log.info(f"Found {len(list_items)} entries for alphabet '{alphabet_char.upper()}'")

            # Extract verb:verb_id pairs, deduplicating by verb name
            seen = {}  # verb -> verb_id (keep first occurrence)
            for item in list_items:
                a_tag = item.find('a')
                if not a_tag or not a_tag.get('href'):
                    continue

                # Extract verb name from text (before the comma)
                raw_entry_data = item.text
                entry_data = raw_entry_data.split(',')[0].strip()
                entry_data = entry_data.replace("\u2019", "'")
                entry_data = entry_data.replace(" (s')", "").replace(" (se)", "")

                # Extract verb_id from href (last segment)
                href = a_tag['href']
                verb_id = href.split('/')[-1]

                if not verb_id.startswith('A9'):
                    log.warning(f"Unexpected verb_id format '{verb_id}' for entry '{entry_data}'. Skipping.")
                    continue

                if entry_data not in seen:
                    seen[entry_data] = verb_id

            inf_list = sorted(seen.items(), key=lambda x: x[0])
            log.info(f"Found {len(inf_list)} unique infinitives for alphabet '{alphabet_char.upper()}'")

            with open(gen_infs_output, "a", encoding="utf-8") as f:
                for verb, verb_id in inf_list:
                    f.write(f"{verb}:{verb_id}\n")
        except Exception as e:
            log.error(f"An error occurred while generating infinitives for alphabet '{alphabet_char.upper()}': {e}")
            continue
