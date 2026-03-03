# verbe-conjugaison-académie-française

A comprehensive dataset of **6,298 French verbs** with complete conjugation data extracted from the [Académie française's official dictionary](https://dictionnaire-academie.fr/). This repository includes both the parsed conjugation data and the Python scripts used to generate it.

## Dataset Overview

- **6,298 verbs** from the 9th edition of the Académie française dictionary
- **Complete conjugation tables** across all moods, tenses, and persons
- **Gender-aware conjugations** — separate masculine/feminine forms for all persons when they differ (passive voice, être auxiliaries, pronominal compounds)
- **Compact merged keys** — identical conjugation forms within a tense share a single key (e.g. `"1sm;1sf"` instead of two separate entries)
- **Three output formats**: JSON (formatted), JSON (minified), and SQLite3 database
- **SSD-friendly caching** — parsed data stored in a single SQLite WAL-mode database instead of thousands of fragment files
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

**Persons** (personnes) — full `{1,2,3} × {s,p} × {m,f}` grid:
- `1sm` / `1sf` — je (first person singular masculine / feminine)
- `2sm` / `2sf` — tu (second person singular masculine / feminine)
- `3sm` — il (third person singular masculine)
- `3sf` — elle (third person singular feminine)
- `1pm` / `1pf` — nous (first person plural masculine / feminine)
- `2pm` / `2pf` — vous (second person plural masculine / feminine)
- `3pm` — ils (third person plural masculine)
- `3pf` — elles (third person plural feminine)

**Key merging** — when multiple person keys share the same conjugation value within a tense, they are merged into a single semicolon-separated key:
- Simple tenses (no participle agreement): `"1sm;1sf"`, `"2sm;2sf"`, `"3sm;3sf"`, `"1pm;1pf"`, `"2pm;2pf"`, `"3pm;3pf"` — 6 keys
- Compound tenses with être (participle agrees in gender): all 12 keys separate
- Passive voice simple tenses: keys merge across persons with the same auxiliary and participle form (e.g. `"1sm;2sm"` when both use *étais combiné*)

> [!NOTE]
> Gender agreement is correctly applied for **all persons** (not just 3rd person) whenever the conjugation includes a past participle that agrees in gender — this includes passive voice, active voice with être auxiliary, and pronominal compound tenses. Impersonal verbs like *falloir* only have third-person masculine entries.

### SQLite3 Database (`verbs.db`)

A normalized relational database (~361 MB) with ~1.6M conjugation rows optimized for queries. The `personne` column uses the same merged key format as the JSON output (e.g. `"1sm;1sf"`).

#### Database Schema

**`verbes` table** - Core verb metadata
```sql
CREATE TABLE verbes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    infinitif TEXT UNIQUE NOT NULL,
    h_aspire BOOLEAN NOT NULL,
    rectification_1990 BOOLEAN NOT NULL,
    rectification_1990_variante TEXT
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
The parser correctly extracts gender-specific conjugations from the Académie française dictionary for **all six persons**:
- **All persons** receive distinct masculine/feminine forms when the verb includes a gender-agreeing past participle (passive voice, être auxiliary compound tenses, pronominal compound tenses)
- Example: "je suis allé" (1sm) vs "je suis allée" (1sf)
- Example: "il est allé" (3sm) vs "elle est allée" (3sf)
- Example: "ils sont allés" (3pm) vs "elles sont allées" (3pf)
- When masculine and feminine forms are identical (simple tenses, avoir auxiliary), person keys are merged: `"1sm;1sf": "vais"`

### 1990 Orthography Reform
Verbs with reformed spellings are tracked:
- **Both variants** appear as separate entries (e.g., "connaître" and "connaitre")
- **Metadata fields**: `rectification_1990` (boolean) and `rectification_1990_variante` (string)
- **Alternative forms** within conjugations are separated by semicolons (e.g., "je vais; je vas")

## 🔧 Technical Details

### Requirements
- **Python**: 3.13+ (tested on 3.14.2, lower versions may work)
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

### Caching
Two layers of caching minimise network and CPU work:

**HTML cache** (`./output/cache/*.html`):
- One file per verb containing the raw conjugation div fragment
- Full-page HTML caches are automatically shrunk to div-only on first parse
- Skipped when `--ignore-cache` is specified

**Parsed store** (`./output/parsed.db`):
- Single SQLite WAL-mode database replacing thousands of fragment files
- Stores each verb's fully-parsed and transformed JSON keyed by infinitive
- Thread-safe via per-thread connections (`threading.local()`)
- Dramatically reduces SSD write amplification compared to individual files
- Cleared automatically when `--ignore-cache` is specified

## Related Resources

- [Académie française Dictionary](https://dictionnaire-academie.fr/)
- [French Orthography Reform (1990)](https://www.academie-francaise.fr/questions-de-langue#5_strong-em-les-rectifications-de-lorthographe-em-strong)
