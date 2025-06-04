"""
An extension for generating an SQLite database for verb conjugations.
Created on: 2025-06-04 10:56:40
Created by: Jacob Shing
"""

import global_vars as gl
import log
import os
import sqlite3

def generate_sqlite_db(loaded_json):
    if os.path.exists("./output/verbs.db"):
        os.remove("./output/verbs.db")

    conn = sqlite3.connect("./output/verbs.db")
    cursor = conn.cursor()

    # == CREATE TABLES ==
    # Each voice has its own table (ACTIVE_AVOIR, ACTIVE_ETRE, PRONOMINAL)
    # Each table has one row per verb
    # Columns: verb (PRIMARY KEY), ind_present, ind_passe_compose, ..., sub_present, etc.
    column_defs = """verb VARCHAR(255) PRIMARY KEY NOT NULL,
    ind_present VARCHAR(255),
    ind_passe_simple VARCHAR(255),
    ind_futur_simple VARCHAR(255),
    ind_passe_compose VARCHAR(255),
    ind_plus_que_parfait VARCHAR(255),
    ind_passe_anterieur VARCHAR(255),
    ind_futur_anterieur VARCHAR(255),
    ind_imparfait VARCHAR(255),
    sub_present VARCHAR(255),
    sub_passe VARCHAR(255),
    sub_imparfait VARCHAR(255),
    sub_plus_que_parfait VARCHAR(255),
    con_present VARCHAR(255),
    con_passe VARCHAR(255),
    imp_present VARCHAR(255),
    imp_passe VARCHAR(255)"""
    for voice in ["ACTIVE_AVOIR", "ACTIVE_ETRE", "PRONOMINAL"]:
        cursor.execute(f"CREATE TABLE {voice} ({column_defs})")

    # == LOAD DATA INTO TABLES ==
    voice_name_table_map = {
        "voix_active_avoir": "ACTIVE_AVOIR",
        "voix_active_être": "ACTIVE_ETRE",
        "voix_prono": "PRONOMINAL"
    }
    for verb in loaded_json:
        verb_dict = loaded_json[verb]
        for voice in voice_name_table_map:
            voice_moods = verb_dict.get(voice, {})
            if len(voice_moods) == 0:
                continue
            conjugation_data = {
                "verb": verb,
                "ind_present": None,
                "ind_passe_simple": None,
                "ind_futur_simple": None,
                "ind_passe_compose": None,
                "ind_plus_que_parfait": None,
                "ind_passe_anterieur": None,
                "ind_futur_anterieur": None,
                "ind_imparfait": None,
                "sub_present": None,
                "sub_passe": None,
                "sub_imparfait": None,
                "sub_plus_que_parfait": None,
                "con_present": None,
                "con_passe": None,
                "imp_present": None,
                "imp_passe": None
            }
            # Indicative mood
            if (ind_data := voice_moods.get("indicatif", None)) is not None:
                conjugation_data["ind_present"] = ind_data.get("présent", None)
                conjugation_data["ind_passe_simple"] = ind_data.get("passé_simple", None)
                conjugation_data["ind_futur_simple"] = ind_data.get("futur_simple", None)
                conjugation_data["ind_passe_compose"] = ind_data.get("passé_composé", None)
                conjugation_data["ind_plus_que_parfait"] = ind_data.get("plus_que_parfait", None)
                conjugation_data["ind_passe_anterieur"] = ind_data.get("passé_antérieur", None)
                conjugation_data["ind_futur_anterieur"] = ind_data.get("futur_antérieur", None)
                conjugation_data["ind_imparfait"] = ind_data.get("imparfait", None)
            # Subjunctive mood
            if (sub_data := voice_moods.get("subjonctif", None)) is not None:
                conjugation_data["sub_present"] = sub_data.get("présent", None)
                conjugation_data["sub_passe"] = sub_data.get("passé", None)
                conjugation_data["sub_imparfait"] = sub_data.get("imparfait", None)
                conjugation_data["sub_plus_que_parfait"] = sub_data.get("plus_que_parfait", None)
            # Conditional mood
            if (con_data := voice_moods.get("conditionnel", None)) is not None:
                conjugation_data["con_present"] = con_data.get("présent", None)
                conjugation_data["con_passe"] = con_data.get("passé", None)
            # Imperative mood
            if (imp_data := voice_moods.get("impératif", None)) is not None:
                conjugation_data["imp_present"] = imp_data.get("présent", None)
                conjugation_data["imp_passe"] = imp_data.get("passé", None)
            
            for key in conjugation_data:
                if key == "verb":
                    # Escape single quotes and surround with single quotes
                    conjugation_data[key] = f"'{conjugation_data[key].replace("'", "''")}'"
                    continue
                if conjugation_data[key] is None:
                    conjugation_data[key] = "NULL"
                else:
                    # Flatten the dictionary for each pronoun
                    pronoun_dict = conjugation_data.get(key, {})
                    if key[:3] == "imp":
                        # imperative mood tenses have only three pronouns
                        pronouns = ["tu", "nous", "vous"]
                    else:
                        # all other tenses have six pronouns
                        pronouns = ["je", "tu", "il", "nous", "vous", "ils"]
                    conjs = []
                    for pronoun in pronouns:
                        if pronoun in pronoun_dict:
                            conj = pronoun_dict.get(pronoun, "")
                            conjs.append("" if conj is None else conj)
                        else:
                            conjs.append("")
                    cell_str = ";".join(conjs)
                    # Escape single quotes and surround with single quotes
                    conjugation_data[key] = f"'{cell_str.replace("'", "''")}'"

            # Insert data into the corresponding table
            table_name = voice_name_table_map[voice]
            sql_command = f"""INSERT INTO {table_name} VALUES(
                {conjugation_data['verb']},
                {conjugation_data['ind_present']},
                {conjugation_data['ind_passe_simple']},
                {conjugation_data['ind_futur_simple']},
                {conjugation_data['ind_passe_compose']},
                {conjugation_data['ind_plus_que_parfait']},
                {conjugation_data['ind_passe_anterieur']},
                {conjugation_data['ind_futur_anterieur']},
                {conjugation_data['ind_imparfait']},
                {conjugation_data['sub_present']},
                {conjugation_data['sub_passe']},
                {conjugation_data['sub_imparfait']},
                {conjugation_data['sub_plus_que_parfait']},
                {conjugation_data['con_present']},
                {conjugation_data['con_passe']},
                {conjugation_data['imp_present']},
                {conjugation_data['imp_passe']}
            )"""
            log.verbose(f"Executing SQL command: {sql_command}", gl.CONFIG_VERBOSE)
            cursor.execute(sql_command)

    # Close connection
    cursor.close()
    conn.commit()
    conn.close()