# verbe-conjugaison-académie-française

A comprehensive dataset of **6,288 French verbs** with complete conjugation data extracted from the [Académie française's official dictionary](https://dictionnaire-academie.fr/). This repository includes both the parsed conjugation data and the Python scripts used to generate it.

## 📊 Dataset Overview

- **6,288 verbs** from the 9th edition of the Académie française dictionary
- **Complete conjugation tables** across all moods, tenses, and persons
- **Gender-aware conjugations** - Separate forms for masculine/feminine when they differ
- **Three output formats**: JSON (formatted), JSON (minified), and SQLite3 database
- **Multi-threaded parser** for efficient data generation
- **1990 orthography reform support** with variant tracking

## 🚀 Quick Start

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
python crawler.py

# Generate JSON + SQLite database
python crawler.py --gen-sqlite3

# Generate with 8 threads for faster processing
python crawler.py --max-threads 8

# Force fresh data (ignore cache)
python crawler.py --ignore-cache

# Generate infinitives list only
python crawler.py --gen-infinitives

# Verbose output for debugging
python crawler.py --verbose
```

## 📦 Output Files

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
          "1s": "vais",
          "2s": "vas",
          "3sm": "va",
          "3sf": "va",
          "1p": "allons",
          "2p": "allez",
          "3pm": "vont",
          "3pf": "vont"
        },
        "passe_compose": {
          "1s": "suis allé",
          "2s": "es allé",
          "3sm": "est allé",
          "3sf": "est allée",
          "1p": "sommes allés",
          "2p": "êtes allés",
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
- `voix_prono` - Reflexive/pronominal form

**Moods** (modes):
- `participe` - Participle (present and past)
- `indicatif` - Indicative (8 tenses)
- `subjonctif` - Subjunctive (4 tenses)
- `conditionnel` - Conditional (2 tenses)
- `imperatif` - Imperative (2 tenses)

**Persons** (personnes):
- `1s` - je (first person singular)
- `2s` - tu (second person singular)
- `3sm` - il (third person singular masculine)
- `3sf` - elle (third person singular feminine)
- `1p` - nous (first person plural)
- `2p` - vous (second person plural)
- `3pm` - ils (third person plural masculine)
- `3pf` - elles (third person plural feminine)

> [!IMPORTANT]
> **Gender Agreement**: This dataset correctly captures gender differences in conjugations. For example, with verbs using "être" as auxiliary, `3sf` and `3pf` will differ from `3sm` and `3pm` when the past participle agrees in gender (e.g., "il est allé" vs "elle est allée").

### SQLite3 Database (`verbs.db`)

A normalized relational database with ~209 MB of conjugation data optimized for queries.

#### Database Schema

**`verbes` table** - Core verb metadata (6,288 rows)
```sql
CREATE TABLE verbes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    infinitif TEXT UNIQUE NOT NULL,
    h_aspire BOOLEAN NOT NULL,
    rectification_1990 BOOLEAN NOT NULL,
    rectification_1990_variante TEXT
);
```

**`conjugaisons` table** - Person conjugations (978,010 rows)
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

**`participes` table** - Participle forms (74,748 rows)
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

## 🛠️ Command Line Options

### Basic Options

| Option | Description | Default |
|--------|-------------|---------|
| `--verbose`, `-v` | Enable detailed logging | `False` |
| `--ignore-cache` | Force fresh data fetch (ignore cached HTML) | `False` |
| `--gen-sqlite3` | Generate SQLite database file | `False` |
| `--gen-infinitives` | Generate infinitives list only | `False` |

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
python crawler.py --max-threads 8 --gen-sqlite3

# Conservative mode (slower, but safer for rate limiting)
python crawler.py --max-threads 2 --requests-delay 1000

# Debug mode with verbose output
python crawler.py --verbose --max-threads 1

# Generate fresh database ignoring cache
python crawler.py --ignore-cache --gen-sqlite3 --max-threads 8
```

## 📋 Data Accuracy

### Gender Agreement
The parser correctly extracts gender-specific conjugations from the Académie française dictionary:
- **Masculine/Feminine differences** are preserved when they exist
- Example: "il est allé" (3sm) vs "elle est allée" (3sf)
- Example: "ils sont allés" (3pm) vs "elles sont allées" (3pf)

### 1990 Orthography Reform
Verbs with reformed spellings are tracked:
- **Both variants** appear as separate entries (e.g., "connaître" and "connaitre")
- **Metadata fields**: `rectification_1990` (boolean) and `rectification_1990_variante` (string)
- **Alternative forms** within conjugations are separated by semicolons (e.g., "je vais; je vas")

## 🔧 Technical Details

### Requirements
- **Python**: 3.13+ (tested on 3.13.3)
- **Dependencies**: BeautifulSoup4 (lxml), requests
- **Platform**: Cross-platform (Windows, macOS, Linux)

### Architecture
- **Parser**: `conjugation_parser.py` - Extracts conjugations from HTML tables
- **Crawler**: `crawler.py` - Multi-threaded orchestration with progress tracking
- **Database**: `extensions/db.py` - SQLite3 generation with normalized schema
- **CLI**: `cli.py` - Modern argparse-based command-line interface

### Caching
HTML pages are cached in `./output/cache/` to avoid redundant HTTP requests:
- Cache is used by default unless `--ignore-cache` is specified
- Each verb has two cached files: `.html` (raw) and `.txt` (parsed)
- Cache significantly speeds up subsequent runs

## 🔗 Related Resources

- [Académie française Dictionary](https://dictionnaire-academie.fr/)
- [French Orthography Reform (1990)](https://www.academie-francaise.fr/questions-de-langue#5_strong-em-les-rectifications-de-lorthographe-em-strong)

---

**Last Updated**: November 2025  
**Dataset Version**: 6,288 verbs from the 9th edition
