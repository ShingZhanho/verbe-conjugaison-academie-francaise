"""
Methods for parsing conjugation data from downloaded HTML files.
Created at: 2025-06-03 14:52:21 HKT
Created by: Jacob Shing
"""

from bs4 import BeautifulSoup
import log

def parse_conjugation_table(root_tag, verb: str, verb_nature: str) -> dict:
    """
    Parses the conjugation table from the HTML element.
    Args:
        root_tag: The HTML element of div#verb-id containing the conjugation data.
        verb (str): The verb being conjugated.
        verb_nature (str): The nature of the verb returned from dictionary search.
    Returns:
        dict: A dictionary containing the parsed conjugation data.
    """
    result = { verb: {} }

    # Look for div.voix_active_être / div.voix_active_avoir / div.voix_active
    # If only div.voix_active is present, try to determine the auxiliary from the table content
    # Also look for div.voix_pron for reflexive verbs
    if (voix_active_avoir := root_tag.find("div", class_="voix_active_avoir")) is None \
        or (voix_active_etre := root_tag.find("div", class_="voix_active_être")) is None:
        voix_active = root_tag.find("div", class_="voix_active")
        if (guessed_aux := __guess_auxiliary(voix_active)) == 1:  # Avoir
            voix_active_avoir = voix_active
        elif guessed_aux == 2:  # Être
            voix_active_etre = voix_active
        
    return result

def __guess_auxiliary(voix_active_tag) -> int:
    """
    (Internal) Guesses the auxiliary verb based on the content of the voix_active_tag.
    Args:
        voix_active_tag: The HTML element containing the conjugation data.
    Returns:
        int: 1 for avoir, 2 for être, or 0 if unable to determine.
    """
    if voix_active_tag is None:
        return 0  # Unable to determine auxiliary

    # find the table of indicative passé composé
    conjugation_divs = voix_active_tag.select('div#active_ind div.tense')
    for div in conjugation_divs:
        passe_compose_header = div.find("h4", string="Passé composé")
        if passe_compose_header is not None:  # Found the passé composé table
            table = div.find("table")
            first_row_auxiliary = table.find("td", class_="conj_auxil").text.strip().lower()
            if first_row_auxiliary in ["ai", "as", "a", "avons", "avez", "ont"]:
                return 1
            elif first_row_auxiliary in ["suis", "es", "est", "sommes", "êtes", "sont"]:
                return 2

    log.warning(f"Unable to determine the auxiliary verb for the verb. The active voice will not be parsed.")
    return 0
