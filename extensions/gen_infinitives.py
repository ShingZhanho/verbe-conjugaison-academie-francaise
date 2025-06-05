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

def gen_infs_main():
    """
    Generates the infinitives.txt file from the AF dictionary.
    """
    # Try entry ID in format A9<leter><<number> e.g. A9B1234 means the word starts with B and has ID 1234.
    counters = {chr(letter): 0 for letter in range(ord('A'), ord('Z') + 1)}
    # Try to load cached counters
    if os.path.exists("./output/gen_infs/counters.json"):
        with open("./output/gen_infs/counters.json", "r", encoding="utf-8") as f:
            counters = json.load(f)

    headers = {
        "Accept": gl.HEADER_ACCEPT,
        "Accept-Encoding": gl.HEADER_ACCEPT_ENCODING,
        "Accept-Language": gl.HEADER_ACCEPT_LANGUAGE,
        "User-Agent": gl.USER_AGENT,
        "Content-Type": gl.HEADER_CONTENT_TYPE,
        "Cookie": f"JSESSIONID={gl.COOKIE_JSESSION_ID}; {gl.HEADER_MISC_COOKIES}",
        "Sec-Fetch-Site": gl.HEADER_SEC_FETCH_SITE,
        "Sec-Fetch-Mode": gl.HEADER_SEC_FETCH_MODE,
        "Sec-Fetch-Dest": gl.HEADER_SEC_FETCH_DEST,
    }

    prev_entry_id = None
    for letter in counters.keys():
        log.info(f"Querying infinitives beginning with `{letter}`...")
        if counters[letter] == -1:  # -1 means all entries for this letter have been processed
            log.info(f"All entries for letter `{letter}` have been processed.")
            continue
        verb_count = 0
        while counters[letter] != -1:
            counters[letter] += 1
            if not prev_entry_id:
                headers["Cookie"] += f"; lastEntry={prev_entry_id}"
                headers["Referer"] = f"{gl.URL_ROOT}article/{letter}"
            prev_entry_id = f"A9{letter}{counters[letter]:04d}"

            try:
                log.verbose(f"GET {gl.URL_ROOT}article/{prev_entry_id}", gl.CONFIG_VERBOSE)
                response = requests.get(f"{gl.URL_ROOT}article/{prev_entry_id}", headers=headers)
                if response.status_code != 200 and response.status_code != 404:
                    log.warning(f"Failed to get entry for ID {prev_entry_id}. Status code: {response.status_code}.")
                    continue
                elif response.status_code == 404:
                    # No more entries for this letter
                    log.info(f"Finished querying infinitives for letter `{letter}`, found {verb_count} verbs.")
                    counters[letter] = -1
            except Exception as e:
                log.warning(f"An error occurred while getting entry for ID {prev_entry_id}: {e}.")
                continue

            if counters[letter] % 100 == 0:
                # Cache counters every 100 entries
                with open("./output/gen_infs/counters.json", "w", encoding="utf-8") as f:
                    json.dump(counters, f, ensure_ascii=False, indent=4)
                log.verbose(f"Cached counters after processing {counters[letter]} entries for letter `{letter}`.", gl.CONFIG_VERBOSE)
            
            # Parse the response
            soup = BeautifulSoup(response.text, "lxml")
            word_content = soup.find("div", id=prev_entry_id)
            if word_content is None:
                log.warning(f"Failed to find content for entry ID {prev_entry_id}.")
                continue
            word_category_span = word_content.find("span", class_="s_cat")
            if word_category_span is None:
                continue
            word_category = word_category_span.text.strip().lower()
            if "verbe" not in word_category or "adverbe" in word_category:
                continue  # Skip non-verb entries
            verb_infinitive = soup.find("div", class_="s_Entree_haut").find("h1").text.strip().lower()
            verb_infinitive = verb_infinitive.replace(" (s’)", "").replace(" (s')", "")
            with open("./output/gen_infs/infinitives.txt", "a", encoding="utf-8") as f:
                f.write(f"{verb_infinitive}\n")
            log.verbose(f"Found verb infinitive: {verb_infinitive} (ID: {prev_entry_id})", gl.CONFIG_VERBOSE)
            verb_count += 1

            # Cache counters when any verb is found
            with open("./output/gen_infs/counters.json", "w", encoding="utf-8") as f:
                json.dump(counters, f, ensure_ascii=False, indent=4)
            log.verbose(f"Cached counters after processing {counters[letter]} entries for letter `{letter}`.", gl.CONFIG_VERBOSE)

            if verb_count % 10 == 0:
                log.info(f"Found {verb_count} verbs for letter `{letter}` so far.")
                