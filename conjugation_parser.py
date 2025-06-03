"""
Methods for parsing conjugation data from downloaded HTML files.
Created at: 2025-06-03 14:52:21 HKT
Created by: Jacob Shing
"""

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
    if (voix_active_avoir := root_tag.find("div", class_="voix_active_avoir")) is None \
        or (voix_active_etre := root_tag.find("div", class_="voix_active_être")) is None:
        voix_active = root_tag.find("div", class_="voix_active")
        if (guessed_aux := __guess_auxiliary(voix_active)) == 1:  # Avoir
            voix_active_avoir = voix_active
        elif guessed_aux == 2:  # Être
            voix_active_etre = voix_active

    # Look for div.voix_pron for reflexive verbs
    voix_pron = root_tag.find("div", class_="voix_pron")

    # Parse each voice
    if voix_active_avoir is not None:
        log.info(f"Parsing active voice with auxiliary 'avoir'...")
        result[verb]["voix_active_avoir"] = __parse_conjugation_div(voix_active_avoir, 1)
    if voix_active_etre is not None:
        log.info(f"Parsing active voice with auxiliary 'être'...")
        result[verb]["voix_active_être"] = __parse_conjugation_div(voix_active_etre, 1)
    if voix_pron is not None:
        log.info(f"Parsing reflexive voice...")
        result[verb]["voix_pron"] = __parse_conjugation_div(voix_pron, 2)
        
    return result

def __guess_auxiliary(voix_active_tag) -> int:
    """
    (Internal) Guesses the auxiliary verb based on the content of the voix_active_tag.
    Args:
        voix_active_tag: The HTML element containing the conjugation data.
    Returns:
        int: `1` for avoir, `2` for être, or `0` if unable to determine.
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

def __parse_conjugation_div(div_tag, type: int) -> dict:
    """
    (Internal) Parses a conjugation div tag and extracts the conjugation data for each tense.
    Args:
        div_tag: The HTML element containing the div (`div.voix_active_être`, `div.voix_active_avoir`, etc.).
        type (int): The type of voice (`1` for active (avoir/être), `2` for reflexive (pron)).
    Returns:
        dict: A dictionary containing the conjugation data for each tense.
    """
    result = {}

    # Find all moods within the div
    indicatif_div       = div_tag.find("div", id=f"{'active' if type == 1 else 'pron'}_ind")
    subjonctif_div      = div_tag.find("div", id=f"{'active' if type == 1 else 'pron'}_sub")
    conditionnel_div    = div_tag.find("div", id=f"{'active' if type == 1 else 'pron'}_con")
    imperatif_div       = div_tag.find("div", id=f"{'active' if type == 1 else 'pron'}_imp")

    if indicatif_div is not None:
        log.info(f"Parsing indicative mood...")
        result["indicatif"] = __parse_mood_div(indicatif_div)
    else:
        log.warning(f"The verb does not seem to contain an indicative mood. This might be an error.")
    if subjonctif_div is not None:
        log.info(f"Parsing subjunctive mood...")
        result["subjonctif"] = __parse_mood_div(subjonctif_div)
    else:
        log.warning(f"The verb does not seem to contain a subjunctive mood. This might be an error.")
    if conditionnel_div is not None:
        log.info(f"Parsing conditional mood...")
        result["conditionnel"] = __parse_mood_div(conditionnel_div)
    else:
        log.warning(f"The verb does not seem to contain a conditional mood. This might be an error.")
    if imperatif_div is not None:
        log.info(f"Parsing imperative mood...")
        result["impératif"] = __parse_mood_div(imperatif_div)
    else:
        log.warning(f"The verb does not seem to contain an imperative mood. This might be an error.")

    return result

def __parse_mood_div(div_tag) -> dict:
    """
    (Internal) Parses a mood div tag and extracts the conjugation data for all tenses within that mood.
    Args:
        div_tag: The HTML element containing the mood div (`div#active_`).
    Returns:
        dict: A dictionary containing the conjugation data for all tenses within that mood.
    """
    result = {}

    # Find all tenses tables within the mood
    tense_divs = div_tag.find_all("div", class_="tense")
    tense_name_key_map = {
        "présent": "présent",
        "passé": "passé",
        "imparfait": "imparfait",
        "passé composé": "passé_composé",
        "plus-que-parfait": "plus_que_parfait",
        "futur simple": "futur_simple",
        "futur antérieur": "futur_antérieur",
        "passé simple": "passé_simple",
        "passé antérieur": "passé_antérieur",
    }

    return result