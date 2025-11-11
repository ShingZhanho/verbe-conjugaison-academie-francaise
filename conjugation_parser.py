"""
Methods for parsing conjugation data from downloaded HTML files.
Created at: 2025-06-03 14:52:21 HKT
Created by: Jacob Shing
"""

import log

def parse_conjugation_table(root_tag, verb: str, verb_nature: str) -> dict | None:
    """
    Parses the conjugation table from the HTML element.
    Args:
        root_tag: The HTML element of div#verb-id containing the conjugation data.
        verb (str): The verb being conjugated.
        verb_nature (str): The nature of the verb returned from dictionary search.
    Returns:
        dict: A dictionary containing the parsed conjugation data. None if no conjugation data is found.
    """
    result = { verb: {} }

    voix_active_avoir = root_tag.find("div", id="voix_active_avoir")
    voix_active_etre = root_tag.find("div", id="voix_active_être")
    # Look for div.voix_active_être / div.voix_active_avoir / div.voix_active
    # If only div.voix_active is present, try to determine the auxiliary from the table content
    if voix_active_avoir is None and voix_active_etre is None:
        voix_active = root_tag.find("div", id="voix_active")
        if (guessed_aux := __guess_auxiliary(voix_active)) == 1:  # Avoir
            voix_active_avoir = voix_active
        elif guessed_aux == 2:  # Être
            voix_active_etre = voix_active

    # Look for div.voix_pron for reflexive verbs
    voix_pron = root_tag.find("div", id="voix_prono")

    if voix_active_avoir is None and voix_active_etre is None and voix_pron is None:
        log.warning(f"No conjugation data found for verb '{verb}'. Skipping parsing.")
        return None

    # Parse each voice
    if voix_active_avoir is not None:
        log.info(f"Parsing active voice with auxiliary 'avoir'...")
        result[verb]["voix_active_avoir"] = __parse_conjugation_div(voix_active_avoir, 1)
    if voix_active_etre is not None:
        log.info(f"Parsing active voice with auxiliary 'être'...")
        result[verb]["voix_active_etre"] = __parse_conjugation_div(voix_active_etre, 1)
    if voix_pron is not None:
        log.info(f"Parsing reflexive voice...")
        result[verb]["voix_prono"] = __parse_conjugation_div(voix_pron, 2)

    # Check for "h aspiré"
    log.info(f"Checking for 'h aspiré'...")
    if verb[0] != 'h':
        result[verb]["h_aspire"] = False
    else:
        result[verb]["h_aspire"] = "H aspiré" in root_tag.text
        
    return result if len(result[verb]) > 0 else None

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
    indicatif_div       = div_tag.find("div", id=f"{'active' if type == 1 else 'prono'}_ind")
    subjonctif_div      = div_tag.find("div", id=f"{'active' if type == 1 else 'prono'}_sub")
    conditionnel_div    = div_tag.find("div", id=f"{'active' if type == 1 else 'prono'}_con")
    imperatif_div       = div_tag.find("div", id=f"{'active' if type == 1 else 'prono'}_imp")

    if indicatif_div is not None:
        log.info(f"    Parsing indicative mood...")
        result["indicatif"] = __parse_mood_div(indicatif_div)
    else:
        log.warning(f"    The verb does not seem to contain an indicative mood.")
    if subjonctif_div is not None:
        log.info(f"    Parsing subjunctive mood...")
        result["subjonctif"] = __parse_mood_div(subjonctif_div)
    else:
        log.warning(f"    The verb does not seem to contain a subjunctive mood.")
    if conditionnel_div is not None:
        log.info(f"    Parsing conditional mood...")
        result["conditionnel"] = __parse_mood_div(conditionnel_div)
    else:
        log.warning(f"    The verb does not seem to contain a conditional mood.")
    if imperatif_div is not None:
        log.info(f"    Parsing imperative mood...")
        result["imperatif"] = __parse_mood_div(imperatif_div, True)
    else:
        log.warning(f"    The verb does not seem to contain an imperative mood.")

    return result

def __parse_mood_div(div_tag, is_imperatif: bool = False) -> dict:
    """
    (Internal) Parses a mood div tag and extracts the conjugation data for all tenses within that mood.
    Args:
        div_tag: The HTML element containing the mood div (`div#active_`).
        is_imperatif (bool): Whether the mood is imperative. Defaults to False.
    Returns:
        dict: A dictionary containing the conjugation data for all tenses within that mood.
    """
    result = {}

    # Find all tenses tables within the mood
    tense_divs = div_tag.find_all("div", class_="tense")
    tense_name_key_map = {
        "présent": "present",
        "passé": "passe",
        "imparfait": "imparfait",
        "passé composé": "passe_compose",
        "plus-que-parfait": "plus_que_parfait",
        "futur simple": "futur_simple",
        "futur antérieur": "futur_anterieur",
        "passé simple": "passe_simple",
        "passé antérieur": "passe_anterieur",
    }
    for tense_div in tense_divs:
        tense_name = tense_div.find("h4", class_="relation").text.strip().lower()
        tense_name_key = tense_name_key_map.get(tense_name, None)
        if tense_name_key is None:
            log.warning(f"    Unknown tense '{tense_name}' found in mood div. Skipping.")
            continue
        tense_table_rows = tense_div.find_all("tr", class_="conj_line")
        if is_imperatif:
            result[tense_name_key] = __parse_imperative_table(tense_table_rows)
        else:
            result[tense_name_key] = __parse_tense_table(tense_table_rows)

    return result

def __parse_tense_table(table_rows_tags) -> dict:
    """
    (Internal) Parses a tense table for all pronouns and their conjugations.
    Args:
        table_rows_tags: The HTML elements containing the rows of the tense table.
    Returns:
        dict: A dictionary containing the conjugation data for all pronouns in the tense.
    """
    result: dict[str, str | None] = {
        "je": None, "tu": None, "il": None, "nous": None, "vous": None, "ils": None,
    }

    def __map_pronoun_to_key(pronoun: str):
        pronoun = pronoun.strip().lower()
        if "j" in pronoun:
            return "je"
        elif "t" in pronoun:
            return "tu"
        elif "ils" in pronoun or "elles" in pronoun:  # Keep only masculine form
            return "ils"
        elif "il" in pronoun or "elle" in pronoun or "on" in pronoun:    # Keep only masculine form
            return "il"
        elif "nous" in pronoun:
            return "nous"
        elif "vous" in pronoun:
            return "vous"
        return None

    for row in table_rows_tags:
        if (conj_pp := row.find("span", class_="conj_pp")) is None:
            log.warning(f"    Row does not contain a pronoun. Skipping.")
            continue
        pronoun_key = __map_pronoun_to_key(conj_pp.text)
        if pronoun_key is None:
            log.warning(f"    Unknown pronoun found in tense table. Skipping.")
            continue
        reflexive_pronoun_tag = row.find("td", class_="conj_refl-pron")
        reflexive_pronoun = reflexive_pronoun_tag.text.strip() if reflexive_pronoun_tag else ""
        reflexive_pronoun = reflexive_pronoun.replace("’", "'")  # Normalize apostrophes
        if reflexive_pronoun != "" and "'" not in reflexive_pronoun:
            reflexive_pronoun += " "

        auxiliary_verb_tag = row.find("td", class_="conj_auxil")
        auxiliary_verb = (auxiliary_verb_tag.text + " ") if auxiliary_verb_tag else ""

        conjugated_verb_tag = str(list(row.find("td", class_="conj_verb").stripped_strings)[0])
        conjugated_verb = conjugated_verb_tag.strip() if conjugated_verb_tag else ""
        # Split on comma first to get first form, then remove spaces within that form only
        conjugated_verb = conjugated_verb.split(",")[0].replace(" ", "")

        rectified_conjugated_verb_tag = row.find("span", class_="forme_rectif")  # may have alternative (1990 orthographic reform)
        rectified_conjugated_verb = rectified_conjugated_verb_tag.text.strip() if rectified_conjugated_verb_tag else ""
        rectified_conjugated_verb = rectified_conjugated_verb.split(",")[0].replace(" ", "")  # keep only the masculine form

        result[pronoun_key] = f"{reflexive_pronoun}{auxiliary_verb}{conjugated_verb}"
        if rectified_conjugated_verb:
            result[pronoun_key] =  f"{result[pronoun_key]},{reflexive_pronoun}{auxiliary_verb}{rectified_conjugated_verb}"

    return result

def __parse_imperative_table(table_rows_tags) -> dict:
    """
    (Internal) Parses the imperative tense table for all pronouns and their conjugations.
    Args:
        table_rows_tags: The HTML elements containing the rows of the imperative tense table.
    Returns:
        dict: A dictionary containing the conjugation data for all pronouns in the imperative tense.
    """
    result: dict[str, str | None] = {
        "tu": None, "nous": None, "vous": None,
    }
    for index, row in enumerate(table_rows_tags):
        # For pronominal imperative passé, the structure is different
        # The "conj_refl-pron" actually contains the auxiliary verb with reflexive pronoun
        reflexive_pronoun_tag = row.find("td", class_="conj_refl-pron")
        
        auxiliary_verb_tag = row.find("td", class_="conj_auxil")
        
        # If reflexive_pronoun_tag exists but no auxiliary_verb_tag,
        # it means the reflexive_pronoun_tag contains both (e.g., "sois-toi")
        if reflexive_pronoun_tag and not auxiliary_verb_tag:
            full_text = reflexive_pronoun_tag.text.strip()
            # This is the combined auxiliary + reflexive pronoun
            auxiliary_verb = full_text + " "
        elif auxiliary_verb_tag:
            auxiliary_verb = (auxiliary_verb_tag.text + " ") if auxiliary_verb_tag else ""
        else:
            auxiliary_verb = ""

        conjugated_verb_tag = str(list(row.find("td", class_="conj_verb").stripped_strings)[0])
        conjugated_verb = conjugated_verb_tag.strip() if conjugated_verb_tag else ""
        conjugated_verb = conjugated_verb.replace(" ", "").split(",")[0]  # keep only the masculine form

        key = "tu" if index == 0 else "nous" if index == 1 else "vous"
        result[key] = f"{auxiliary_verb}{conjugated_verb}"
    return result