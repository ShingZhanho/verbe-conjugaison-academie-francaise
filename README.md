# verbe-conjugaison-académie-française

This repository hosts a list of French verbs with their conjugations, obtained from the Académie française's (AF) dictionary,
and also the Python scripts used to generate the conjugation tables.

The list of verb infinitives (`infinitives.txt`) is obtained from the AF dictionary, using the script options `-E:GEN-INFINITIVES`.
The list includes all 6,250 verbs that are available in the 9th edition of the dictionary.

## Format of the Release Artefacts

### Files `verbs.json` and `verbs.min.json`

The release artifacts include two JSON files:
- `verbs.json` - The full conjugation data of all verbs in the list, formatted for readability.
- `verbs.min.json` - A minified version of the conjugation data.

> [!note]
> All non-ASCII characters in the JSON file are NOT escaped.
> All JSON keys have their accents removed, and are in lowercase.

Each verb infinitive is a key in the JSON file.
Under each infinitive, at most three voices are provided:
1. `voix_active_avoir` - active voice with auxiliary verb "avoir"
2. `voix_active_etre` - active voice with auxiliary verb "être"
3. `voix_prono` - verb conjugated in reflexive form

Passive voice is not covered.

There is another extra key `h_aspire` at the same level as the voices, which indicates whether the verb
begins with an "h aspiré". This value is boolean.

Under each voice, at most five moods and all of their tenses are included:
1. `participe` - participle
    - `present` - present participle as a string (e.g., "abaissant")
    - `passe` - past participle with the following keys:
      - `sm` - masculine singular form (singulier masculin)
      - `sf` - feminine singular form (singulier féminin)
      - `pm` - masculine plural form (pluriel masculin)
      - `pf` - feminine plural form (pluriel féminin)
      - `compound_sm` - compound masculine singular with auxiliary (e.g., "ayant abaissé")
      - `compound_sf` - compound feminine singular with auxiliary
      - `compound_pm` - compound masculine plural with auxiliary
      - `compound_pf` - compound feminine plural with auxiliary
2. `indicatif` - indicative mood
    - `present`
    - `imparfait`
    - `passe_simple`
    - `futur_simple`
    - `passe_compose`
    - `plus_que_parfait`
    - `passe_anterieur`
    - `futur_anterieur`
3. `subjonctif` - subjunctive mood
    - `present`
    - `imparfait`
    - `passe`
    - `plus_que_parfait`
4. `conditionnel` - conditional mood
    - `present`
    - `passé`
5. `imperatif` - imperative mood
    - `present`
    - `passe`

If a verb is not conjugated in any tenses of a mood, that entire mood will not appear.

Under each tense, eight persons are provided (not applicable for participles):
1. `1s` - first person singular (je)
2. `2s` - second person singular (tu)
3. `3sm` - third person singular masculine (il)
4. `3sf` - third person singular feminine (elle)
5. `1p` - first person plural (nous)
6. `2p` - second person plural (vous)
7. `3pm` - third person plural masculine (ils)
8. `3pf` - third person plural feminine (elles)

Note that `3sf` has the same conjugation as `3sm`, and `3pf` has the same conjugation as `3pm`.

For participles:
- The `present` key contains a single string value
- The `passe` key contains a dictionary with keys: `sm`, `sf`, `pm`, `pf`, `compound_sm`, `compound_sf`, `compound_pm`, `compound_pf`

All verb conjugations are in masculine forms. For impersonal verbs, only the third person singular
and plural are conjugated, but the keys of other persons are still present, with values being `null`.

> [!note]
> **Support for French Orthography Reform (rectification orthographique du français en 1990)**
> 
> Some verbs have multiple accepted spellings due to the 1990 orthography reform.
> - If a verb infinitive has multiple forms (e.g., `connaître` vs `connaitre`), both appear as separate entries
> - Each entry includes metadata:
>   - `rectification_1990`: Boolean indicating if the verb has a reformed variant
>   - `rectification_1990_variante`: The alternate spelling (e.g., `connaître` ↔ `connaitre`)
> - Within conjugation forms, variants are separated by a semicolon (`;`)
>   - Example: `je vais; je vas` means both forms are accepted

### File `verbs.db`

An SQLite3 database file containing the conjugation data of all verbs in a normalized relational schema.

#### Database Schema

The database uses a normalized design with three main tables (all names in French with accents removed):

**`verbes` table** - Core verb metadata
- `id` (INTEGER PRIMARY KEY) - Unique verb identifier
- `infinitif` (TEXT UNIQUE NOT NULL) - The infinitive form of the verb
- `h_aspire` (BOOLEAN) - Whether the verb begins with an "h aspiré"
- `rectification_1990` (BOOLEAN) - Whether the verb has a 1990 reform variant
- `rectification_1990_variante` (TEXT) - The alternate spelling (e.g., `connaître` ↔ `connaitre`)

**`conjugaisons` table** - All person conjugations (normalized)
- `id` (INTEGER PRIMARY KEY) - Unique conjugation identifier
- `verbe_id` (INTEGER) - Foreign key to `verbes.id`
- `voix` (TEXT) - Voice: `voix_active_avoir`, `voix_active_etre`, or `voix_prono`
- `mode` (TEXT) - Mood: `indicatif`, `subjonctif`, `conditionnel`, or `imperatif`
- `temps` (TEXT) - Tense: `present`, `imparfait`, `passe_simple`, etc.
- `personne` (TEXT) - Person: `1s`, `2s`, `3sm`, `3sf`, `1p`, `2p`, `3pm`, or `3pf`
- `conjugaison` (TEXT) - The conjugated form
- **Unique constraint:** `(verbe_id, voix, mode, temps, personne)`

**`participes` table** - Participle forms
- `id` (INTEGER PRIMARY KEY) - Unique participle identifier
- `verbe_id` (INTEGER) - Foreign key to `verbes.id`
- `voix` (TEXT) - Voice: `voix_active_avoir`, `voix_active_etre`, or `voix_prono`
- `forme` (TEXT) - Form: `present`, `passe_sm`, `passe_sf`, `passe_pm`, `passe_pf`, `passe_compound_sm`, `passe_compound_sf`, `passe_compound_pm`, or `passe_compound_pf`
- `participe` (TEXT) - The participle form
- **Unique constraint:** `(verbe_id, voix, forme)`

#### Indexes
The database includes indexes on commonly queried fields for optimal performance:
- `idx_verbes_infinitif` - Fast lookup by infinitive
- `idx_verbes_variantes` - Fast lookup of reform variants
- `idx_conjugaisons_recherche` - Fast lookup by verb, voice, mood, tense, person
- `idx_conjugaisons_texte` - Fast search by conjugation text
- `idx_participes_recherche` - Fast lookup of participle forms

#### Example Queries

```sql
-- Get all present indicative forms of "être" across all voices
SELECT voix, personne, conjugaison
FROM conjugaisons c
JOIN verbes v ON c.verbe_id = v.id
WHERE v.infinitif = 'être' AND mode = 'indicatif' AND temps = 'present'
ORDER BY voix, personne;

-- Find all verbs with 1990 reform variants
SELECT infinitif, rectification_1990_variante
FROM verbes
WHERE rectification_1990 = 1 AND rectification_1990_variante IS NOT NULL;

-- Get all participles for a verb
SELECT voix, forme, participe
FROM participes p
JOIN verbes v ON p.verbe_id = v.id
WHERE v.infinitif = 'abaisser';

-- Find verbs where the conjugation contains a specific pattern
SELECT DISTINCT v.infinitif
FROM verbes v
JOIN conjugaisons c ON v.id = c.verbe_id
WHERE c.conjugaison LIKE '%aient%'
LIMIT 10;
```

## Running the Script

```shell
pip install -r requirements.txt    # Install dependencies
python crawler.py [options]        # Run the crawler script
```

### Command Line Options

#### Overwrite Options
- `-O:COOKIE-JSESSION-ID <JSESSION_ID>` - Overwrite the JSESSION_ID issued by the AF website when you visit the page.
The script attempts to obtain it automatically, but you may overwrite it manually if needed.
- `-O:USER-AGENT <USER_AGENT>` - Overwrite the user agent string used by the script.

#### Configuration Options
- `-C:IGNORE-CACHE` - Ignore the cached HTML files and always fetch the latest data from the AF website. False by default.
- `-C:MAX-RETRY <n>` - Set the maximum number of retries if HTTP requests fail. Default is 3.
- `-C:REQUESTS-DELAY <n>` - The delay between HTTP requests in ms. Default is 500 (half a second).
Set this to a higher value if the server blocks your IP for too many requests.
- `-C:VERBOSE` - Enable verbose output to see more details about the script's execution. False by default.

#### Extension Options
- `-E:GEN-SQLITE3` - Generate an SQLite3 database file of the conjugation data (`verbs.db`). False by default.
- `-E:GEN-INFINITIVES` - Generate a file of all verb infinitives (`./output/infinitives.txt`) from the AF dictionary. False by default.
(_Using this extension will only generate the infinitives list, not the conjugation data._)

> [!note]
> Running the script against the full list of verbs can take up to 8 hours.
> You are suggested to run the script with a subset of verbs that you need, and use the
> uploaded files in the [Releases](https://github.com/ShingZhanho/verbe-conjugaison-academie-francaise/releases)
> section for the full list of verbs.
