# verbe-conjugaison-académie-française

A comprehensive dataset of **6,358 French verbs** with complete conjugation data extracted from the [Académie française's official dictionary](https://dictionnaire-academie.fr/). This repository includes both the parsed conjugation data and the Python scripts used to generate it.

## Dataset Overview

- **6,358 verbs** from the 9th edition of the Académie française dictionary
- **Complete conjugation tables** across all moods, tenses, and persons
- **Gender-aware conjugations** — separate masculine/feminine forms for all persons when they differ (passive voice, être auxiliaries, pronominal compounds)
- **Three output formats**: JSON (formatted), JSON (minified), and SQLite3 database
- **Multi-threaded parser** for efficient data generation
- **1990 orthography reform support** with variant tracking

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/ShingZhanho/verbe-conjugaison-academie-francaise.git
cd verbe-conjugaison-academie-francaise

# Install dependencies
pip install -r requirements.txt
```

### Usage

```bash
# Generate JSON files (uses 4 threads by default)
python -m verbe_af

# Generate JSON + SQLite database
python -m verbe_af --gen-sqlite3

# Generate with 8 threads for faster processing
python -m verbe_af --max-threads 8

# Reparse local HTML after parser changes, without network requests
python -m verbe_af --reparse-cache --gen-sqlite3

# Force fresh data (ignore cache)
python -m verbe_af --ignore-cache

# Generate infinitives list only
python -m verbe_af --gen-infinitives

# Verbose output for debugging
python -m verbe_af --verbose

# Write log to file (in addition to terminal)
python -m verbe_af --log-file crawl.log
```

## Output Files

### JSON Files (`verbs.json` and `verbs.min.json`)

Two JSON files are generated:
- **`verbs.json`** - Human-readable formatted conjugation data
- **`verbs.min.json`** - Minified version for production use

#### JSON Structure

```json
{
  "aller": {
    "h_aspire": false,
    "bloque_elision_liaison": false,
    "rectification_1990": false,
    "rectification_1990_variante": null,
    "voix_active_etre": {
      "participe": {
        "present": "allant",
        "passe": {
          "sm": "allé",
          "sf": "allée",
          "pm": "allés",
          "pf": "allées",
          "compound_sm": "étant allé",
          "compound_sf": "étant allée",
          "compound_pm": "étant allés",
          "compound_pf": "étant allées"
        }
      },
      "indicatif": {
        "present": {
          "1sm;1sf": "vais",
          "2sm;2sf": "vas",
          "3sm;3sf": "va",
          "1pm;1pf": "allons",
          "2pm;2pf": "allez",
          "3pm;3pf": "vont"
        },
        "passe_compose": {
          "1sm": "suis allé",
          "1sf": "suis allée",
          "2sm": "es allé",
          "2sf": "es allée",
          "3sm": "est allé",
          "3sf": "est allée",
          "1pm": "sommes allés",
          "1pf": "sommes allées",
          "2pm": "êtes allés",
          "2pf": "êtes allées",
          "3pm": "sont allés",
          "3pf": "sont allées"
        }
      }
    }
  }
}
```

#### Key Features

**Voices** (voix):
- `voix_active_avoir` - Active voice with auxiliary "avoir"
- `voix_active_etre` - Active voice with auxiliary "être"
- `voix_active` - Active voice (defective verbs with unknown auxiliary)
- `voix_passive` - Passive voice
- `voix_prono` - Reflexive/pronominal form

**Moods** (modes):
- `participe` - Participle (present and past)
- `indicatif` - Indicative (8 tenses)
- `subjonctif` - Subjunctive (4 tenses)
- `conditionnel` - Conditional (2 tenses)
- `imperatif` - Imperative (2 tenses)

**Persons** (personnes) — full `{1,2,3} × {s,p} × {m,f,n}` grid:
- `1sm` / `1sf` — je (first person singular masculine / feminine)
- `2sm` / `2sf` — tu (second person singular masculine / feminine)
- `3sm` — il (third person singular masculine)
- `3sf` — elle (third person singular feminine)
- `3sn` — on (third person singular neutral — used by reciprocal verbs like *s'entraider*)
- `1pm` / `1pf` — nous (first person plural masculine / feminine)
- `2pm` / `2pf` — vous (second person plural masculine / feminine)
- `3pm` — ils (third person plural masculine)
- `3pf` — elles (third person plural feminine)

**Key merging** — when multiple person keys share the same conjugation value within a tense, they are merged into a single semicolon-separated key:
- Simple tenses (no participle agreement): `"1sm;1sf"`, `"2sm;2sf"`, `"3sm;3sf"`, `"1pm;1pf"`, `"2pm;2pf"`, `"3pm;3pf"` — 6 keys
- Compound tenses with être (participle agrees in gender): all 12 keys separate
- Passive voice simple tenses: keys merge across persons with the same auxiliary and participle form (e.g. `"1sm;2sm"` when both use *étais combiné*)

### SQLite3 Database (`verbs.db`)

A normalized relational database (~361 MB) with ~1.6M conjugation rows optimized for queries. The `personne` column uses the same merged key format as the JSON output (e.g. `"1sm;1sf"`).

#### Database Schema

**`verbes` table** - Core verb metadata
```sql
CREATE TABLE verbes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    infinitif TEXT UNIQUE NOT NULL,
    h_aspire BOOLEAN DEFAULT 0,
    rectification_1990 BOOLEAN DEFAULT 0,
    rectification_1990_variante TEXT,
    bloque_elision_liaison BOOLEAN NOT NULL DEFAULT 0
);
```

**`conjugaisons` table** - Person conjugations
```sql
CREATE TABLE conjugaisons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verbe_id INTEGER NOT NULL,
    voix TEXT NOT NULL,
    mode TEXT NOT NULL,
    temps TEXT NOT NULL,
    personne TEXT NOT NULL,
    conjugaison TEXT NOT NULL,
    FOREIGN KEY (verbe_id) REFERENCES verbes(id) ON DELETE CASCADE,
    UNIQUE(verbe_id, voix, mode, temps, personne)
);
```

**`participes` table** - Participle forms
```sql
CREATE TABLE participes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verbe_id INTEGER NOT NULL,
    voix TEXT NOT NULL,
    forme TEXT NOT NULL,
    participe TEXT NOT NULL,
    FOREIGN KEY (verbe_id) REFERENCES verbes(id) ON DELETE CASCADE,
    UNIQUE(verbe_id, voix, forme)
);
```

#### Optimized Indexes

```sql
CREATE INDEX idx_verbes_infinitif ON verbes(infinitif);
CREATE INDEX idx_verbes_variantes ON verbes(rectification_1990_variante);
CREATE INDEX idx_conjugaisons_recherche ON conjugaisons(verbe_id, voix, mode, temps, personne);
CREATE INDEX idx_conjugaisons_texte ON conjugaisons(conjugaison);
CREATE INDEX idx_participes_recherche ON participes(verbe_id, voix, forme);
```

#### Example Queries

```sql
-- Get all present indicative conjugations for "être"
SELECT personne, conjugaison
FROM conjugaisons c
JOIN verbes v ON c.verbe_id = v.id
WHERE v.infinitif = 'être' 
  AND voix = 'voix_active_avoir'
  AND mode = 'indicatif' 
  AND temps = 'present'
ORDER BY personne;

-- Find verbs with 1990 orthography reform variants
SELECT infinitif, rectification_1990_variante
FROM verbes
WHERE rectification_1990 = 1;

-- Search for all conjugations containing "aient"
SELECT v.infinitif, c.voix, c.mode, c.temps, c.personne, c.conjugaison
FROM conjugaisons c
JOIN verbes v ON c.verbe_id = v.id
WHERE c.conjugaison LIKE '%aient%'
LIMIT 20;

-- Get all participle forms for "aller"
SELECT voix, forme, participe
FROM participes p
JOIN verbes v ON p.verbe_id = v.id
WHERE v.infinitif = 'aller';

-- Count conjugations by mood
SELECT mode, COUNT(*) as total
FROM conjugaisons
GROUP BY mode
ORDER BY total DESC;
```

## Command Line Options

### Basic Options

| Option | Description | Default |
|--------|-------------|---------|
| `--verbose`, `-v` | Enable detailed logging | `False` |
| `--ignore-cache` | Force fresh data fetch (ignore cached HTML and parsed store) | `False` |
| `--reparse-cache` | Rebuild the parsed store from local HTML without network access; abort artifact generation if any input cache is missing | `False` |
| `--gen-sqlite3` | Generate SQLite database file | `False` |
| `--gen-infinitives` | Generate infinitives list only | `False` |
| `--log-file PATH` | Write log to file (in addition to terminal) | — |

### Performance Options

| Option | Description | Default |
|--------|-------------|---------|
| `--max-threads N` | Number of concurrent parsing threads | `4` |
| `--max-retry N` | Maximum HTTP request retries | `5` |
| `--requests-delay MS` | Delay between requests (milliseconds) | `500` |

### Advanced Options

| Option | Description |
|--------|-------------|
| `--user-agent AGENT` | Custom user agent string |
| `--jsession-id ID` | Override JSESSION_ID cookie |

### Examples

```bash
# Fast generation with 8 threads
python -m verbe_af --max-threads 8 --gen-sqlite3

# Conservative mode (slower, but safer for rate limiting)
python -m verbe_af --max-threads 2 --requests-delay 1000

# Debug mode with verbose output
python -m verbe_af --verbose --max-threads 1

# Generate fresh database ignoring cache
python -m verbe_af --ignore-cache --gen-sqlite3 --max-threads 8
```

## Data Accuracy

### Gender Agreement
The parser correctly extracts gender-specific conjugations from the Académie française dictionary for **all persons**:
- **All persons** receive distinct masculine/feminine forms when the verb includes a gender-agreeing past participle (passive voice, être auxiliary compound tenses, pronominal compound tenses)
- Example: "je suis allé" (1sm) vs "je suis allée" (1sf)
- Example: "il est allé" (3sm) vs "elle est allée" (3sf)
- Example: "ils sont allés" (3pm) vs "elles sont allées" (3pf)
- When masculine and feminine forms are identical (simple tenses, avoir auxiliary), person keys are merged: `"1sm;1sf": "vais"`
- **Reciprocal verbs** using the pronoun **on** are assigned the neutral key `3sn` (e.g., *s'entraider*: `"3sn": "s'entraide"`)

### 1990 Orthography Reform
Verbs with reformed spellings are tracked:
- **Both variants** appear as separate entries (e.g., "connaître" and "connaitre")
- **Metadata fields**: `rectification_1990` (boolean) and `rectification_1990_variante` (string)

### Source corrections and parsing fixes (2026-10-29)

The manual audit of the v0.4.0 release covered all 6,358 entries, 1,682,575
conjugation rows and 117,705 participle rows. It found 127 affected entries
across seven parsing/transformation issues. The fixes preserve source mood–tense
coverage. The subsequent source corrections and schema addition are included below:

- Materialize lexical î/û alternatives only when the source explicitly permits
  them. Include participles and compound/reflexive forms, retaining grammatical
  circumflexes such as *connûmes*, *abîmâmes/abimâmes* and *eût*.
- Preserve reform alternatives in prefixed imperatives and repeat the complete
  auxiliary prefix for every participle alternative.
- Split partial plural participle lists into `pm`/`pf`. Restore singulars only for
  seven confirmed incomplete source rows: active être past compound for *croître*
  and *recroître*; passive present/past and pronominal past compound for *devoir*;
  passive present/past for *redevoir*. The correction requires an exact match of
  the known plural pair and does not replace explicit source singulars. Spelling
  aliases *croitre/recroitre* receive the same correction. Traditional singular
  pairs are *crû/crue*, *recrû/recrue*, *dû/due*, *redû/redue*.
  The [OQLF spelling rule](https://vitrinelinguistique.oqlf.gouv.qc.ca/23701/lorthographe/accents-trema-et-cedille/accent-circonflexe/laccent-circonflexe-dans-les-formes-verbales)
  and [Larousse's redevoir table](https://www.larousse.fr/conjugaison/francais/redevoir/7567)
  independently confirm the masculine-singular accent pattern. These corrections
  do not introduce additional spelling-reform alternatives.
- Preserve an explicitly invariant simple past participle even when no compound
  participle row exists (*entre-nuire*, *entrenuire*).
- Rewrite orthographic-variant references after homonym merging/renumbering.
- Export `bloque_elision_liaison` in JSON and the `verbes` table. True means the
  source explicitly blocks elision and liaison, including for *ululer* and
  *yoyoter*. False means no such lexical block is marked; actual liaison still
  depends on grammatical context. `h_aspire` is true only for an h-initial verb
  with that marker. This is an additive SQLite schema change; consumers should
  name selected columns rather than rely on the width/order of `SELECT *`.
- Separate alternatives and merged person keys with `;` without adjacent spaces.
  Spaces within each French form remain intact.

One intentional source correction excludes both `sur-aller` and `suraller` from
infinitive generation, input loading and merged output. The Academy's
[aller table](https://www.dictionnaire-academie.fr/conjuguer/A9A1226) incorrectly
contains `allons ou sur-aller` in the active and pronominal present. The parser
removes only that exact erroneous alternative under *aller*, preserving
`allons` and `nous en allons`. Cached HTML remains unchanged. Legitimate
`entre-`/`entr’` compounds and their spelling variants are retained.

#### Consumer compatibility with v0.4.0

This update includes a breaking correction to passive present participles for
*devoir* and *redevoir*: JSON `voix_passive.participe.present` changes from a
string to a gender-keyed object, matching other agreeing passive participles.
In SQLite, their generic `forme = 'present'` rows are replaced by
`present_sm`, `present_sf`, `present_pm` and `present_pf` rows. Consumers must
handle those gendered forms instead of expecting the former generic value.

The boolean `bloque_elision_liaison` is added to every JSON entry and appended
to the SQLite `verbes` schema. Existing column names and their order remain;
fixed-width `SELECT *` unpacking and JSON decoders that reject additional fields
need adjustment. Consumers should select named columns and accept the new field.
Use this flag to detect lexical blocking for *ululer/yoyoter*; their `h_aspire`
value remains false, as in v0.4.0. Existing verb IDs and finite mood–tense/person
coverage are preserved in the verified rebuild. Alternative values now use `;`
without spaces; merged person keys retain that existing delimiter convention.

After changing parser logic, use `--reparse-cache` to avoid stale parsed entries.
It rebuilds `parsed.db`, reads HTML without modifying it, performs no network
requests, and refuses to generate artifacts if any requested input is missing
or fails to parse. It cannot be combined with `--ignore-cache` or
`--gen-infinitives`. For an intentionally cache-only input subset, prepare that
subset explicitly and retain a separate list of omitted input names/IDs; do not
silently describe a partial source crawl as complete.

The first verified local rebuild on 2026-10-29 reparsed 6,416 cached inputs and
produced 6,358 entries, 1,682,575 conjugation rows and 117,709 participle rows.
Compared with the audited v0.4.0 release, exactly 128 entries changed semantically
(the 127 affected entries plus *aller*); all other entries, verb IDs, finite
mood–tense/person coverage and primary cached-source hashes were preserved.
All spelling-variant references resolve. SQLite integrity and foreign-key checks
passed, and every generated JSON form agrees with the database. The database
SHA-256 is `eb95a82debc8018f29bc9201808806bc4e055e81731aec0af2ebeb6d90432c98`.
This is a local rebuilt artifact, not a replacement of the published v0.4.0 asset.

The subsequent verified rebuild on 2026-10-29 includes the singular corrections,
`bloque_elision_liaison` and separator normalization. All 6,416 cached inputs
succeeded; it produced 6,358 entries, 1,682,575 conjugation rows and 117,727
participle rows. Against the first rebuild, exactly 18 singular slots were added
and 29 participle values lost spaces after semicolons. Every entry gained the
blocking flag; only *ululer/yoyoter* changed `h_aspire` to false. Full artifact
comparison found no other changes. All JSON rows match SQLite; verb IDs,
finite forms and their coverage, variant references, integrity and foreign keys
passed verification. All 6,358 audited primary HTML hashes remain unchanged.
Eight focused regression checks passed. The installed local database SHA-256 is
`43ec6028c12e82b7db71823493da8baff09273f07505b4eaaf5577828599306b`.
The published release artifact remains the audited original.

Four input names had no HTML cache and no previous parsed-store entry:
`becter_1`, `hululer_2`, `roidir_1`, `saouler_2`. They were explicitly omitted
from this offline input subset. Comparison confirmed that no release database
entry was lost. This does not claim completeness against uncached source-site
homonyms.

Run the focused regression checks with:

```bash
python -m unittest discover -s tests -v
```

## 🔧 Technical Details

### Requirements
- **Python**: 3.13+ (tested, lower versions may work)
- **Dependencies**: BeautifulSoup4 (lxml), requests
- **Platform**: Cross-platform (Windows, macOS, Linux)

### Architecture

The codebase is organised as a Python package (`verbe_af/`) with clean separation of concerns:

| Module | Responsibility |
|--------|---------------|
| `verbe_af/cli.py` | argparse CLI and main dispatch |
| `verbe_af/config.py` | Injectable `Config` dataclass (replaces mutable globals) |
| `verbe_af/client.py` | `DictionaryClient` — `requests.Session`-based HTTP |
| `verbe_af/parser.py` | Conjugation HTML → structured dict |
| `verbe_af/transformer.py` | Normalise parsed data, 1990 reform handling |
| `verbe_af/cache.py` | HTML cache helpers, `ParsedStore` (SQLite KV), JSON merge |
| `verbe_af/crawler.py` | `VerbCrawler` — threaded orchestration |
| `verbe_af/constants.py` | Immutable constants, `VoiceType` enum, person key maps |
| `verbe_af/exceptions.py` | `CrawlerError` hierarchy |
| `verbe_af/extensions/` | Optional generators (infinitives, SQLite) |
| `audit/` | PySide6 GUI for manual data verification |

### Audit GUI

A PySide6-based manual verification tool for comparing parsed JSON data against source HTML:

```bash
pip install -r audit/requirements.txt
python -m audit --auditor yourname
```

**Features**: split-pane layout (JSON vs source HTML), per-tense review units, per-form flag buttons, status/voice filters, CSV export of flagged items, JSONL progress file (Git-collaborative), keyboard shortcuts (`Alt+O`/`Alt+F`/`Alt+S`/`Alt+N`/`Alt+P`).

## Related Resources

- [Académie française Dictionary](https://dictionnaire-academie.fr/)
- [French Orthography Reform (1990)](https://www.academie-francaise.fr/questions-de-langue#5_strong-em-les-rectifications-de-lorthographe-em-strong)
