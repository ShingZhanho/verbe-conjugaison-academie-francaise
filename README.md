# verbe-conjugaison-académie-française

This repository hosts a list of French verbs with their conjugations, obtained from the Académie Française's (AF) dictionary,
and also the Python scripts used to generate the conjugation tables.

The list of verb infinitives (`infinitives.txt`) is based on the file `verbs.json` from the repository
[Einenlum/french-verbs-list](https://github.com/Einenlum/french-verbs-list).
The list of verbs are checked against the AF dictionary and only those that are present in the 9th edition of the dictionary
are used to generate the conjugation tables.

> [!note]
> It is unknown whether the verbs provided by the list are complete as the file was last updated 7 years ago (as of Jun 2025).
> Should you find a verb that is not present in the list, you may add it to the file `infinitives.txt` (preferably remove
> all other verbs) then run the script `crawler.py` to generate the conjugation data.

## Format of the Release `verbes-francais.json`

> [!note]
> All non-ASCII characters in the JSON file are NOT escaped.
> You should use the appropriate accented characters when accessing the data file.

Each verb infinitive is a key in the JSON file.
Under each infinitive, at most three voices are provided:
1. `voix_active_avoir` - active voice with auxiliary verb "avoir"
2. `voix_active_être` - active voice with auxiliary verb "être"
3. `voix_prono` - verb conjugated in reflexive form

Passive voice is not covered.

Under each voice, at most four moods and all of their tenses are included:
1. `indicatif` - indicative mood
    - `présent`
    - `imparfait`
    - `passé_simple`
    - `futur_simple`
    - `passé_composé`
    - `plus_que_parfait`
    - `passé_antérieur`
    - `futur_antérieur`
2. `subjonctif` - subjunctive mood
    - `présent`
    - `imparfait`
    - `passé`
    - `plus_que_parfait`
3. `conditionnel` - conditional mood
    - `présent`
    - `passé`
4. `impératif` - imperative mood
    - `présent`
    - `passé`

Note that participles are not included in the release file. You may modify the script `conjugation_parser.py` to parse the
HTML files and extract the participles if you need them.

If a verb is not conjugated in any tenses of a mood, that entire mood will not appear.

Under each tense, six persons are provided:
1. `je` - first person singular
2. `tu` - second person singular
3. `il` - third person singular (masculine)
4. `nous` - first person plural
5. `vous` - second person plural
6. `ils` - third person plural (masculine)

All verb conjugations are in masculine forms. For impersonal verbs, only the third person singular
and plural are conjugated, but the keys of other persons are still present, with values being `null`.

> [!note]
> **Support for French Orthography Reform (retification orthographique du français)**
> Some verbs may have more than one conjugation form due to the orthography reforms.
> The two forms accepted by the AF dictionary are both included in the same key,
> separated by a comma (`,`).

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
- `-C:IGNORE-CACHE` - Ignore the cached HTML files and always fetch the latest data from the AF website.

- `-C:MAX-RETRY <n>` - Set the maximum number of retries if HTTP requests fail. Default is 3.

- `-C:REQUESTS-DELAY <n>` - The delay between HTTP requests in ms. Default is 500 (half a second).
Set this to a higher value if the server blocks your IP for too many requests.

- `-C:VERBOSE` - Enable verbose output to see more details about the script's execution.

> [!note]
> Running the script against the full list of verbs can take up to 8 hours.
> You are suggested to run the script with a subset of verbs that you need, and use the
> uploaded files in the [Releases](https://github.com/ShingZhanho/verbe-conjugaison-academie-francaise/releases)
> section for the full list of verbs.