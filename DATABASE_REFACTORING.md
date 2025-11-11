# Database Schema Refactoring Summary

## Overview
The SQLite database has been completely redesigned from a denormalized wide-table structure to a properly normalized relational schema. This provides better queryability, flexibility, and maintainability.

## Schema Changes

### Old Design (Deprecated)
```
ACTIVE_AVOIR, ACTIVE_ETRE, PRONOMINAL tables
- One row per verb
- Wide table with ~18 columns (ind_present, ind_passe_simple, etc.)
- Conjugations flattened as semicolon-separated strings
- No participles stored
- No reform metadata
```

### New Design (Current)
```
verbs table
- Core metadata (infinitive, h_aspire, reform info)
- 6,288 rows (including reform variants)

conjugations table  
- Normalized person conjugations (one row per person/tense)
- 978,010 rows
- Fully queryable by any dimension

participles table
- All participle forms including compounds
- 74,748 rows
```

## Key Improvements

### 1. Proper Normalization
- **Before**: Each tense stored as semicolon-separated string `"abaisse;abaisses;abaisse;abaissons;abaissez;abaissent"`
- **After**: Each person stored as individual row with structured columns

### 2. Complete Data Coverage
- **Added**: All participle forms (present, past with all genders/numbers)
- **Added**: Compound participles (`ayant abaissé`, `s'étant abaissé`, etc.)
- **Added**: 1990 spelling reform metadata and cross-references
- **Added**: Separate keys for elle/elles (3sf/3pf)

### 3. Flexible Querying
- **Before**: Must parse semicolon-separated strings to extract individual persons
- **After**: Direct SQL queries on any conjugation dimension

### 4. Person Key Format
- **Old**: `je`, `tu`, `il`, `nous`, `vous`, `ils` (hardcoded positions)
- **New**: `1s`, `2s`, `3sm`, `3sf`, `1p`, `2p`, `3pm`, `3pf` (explicit keys)

### 5. Reform Support
- **Before**: Variants in same string separated by commas
- **After**: Separate verb entries with bidirectional cross-references

## Performance Optimizations

### Indexes Created
```sql
idx_verbs_infinitive           -- Fast lookup by infinitive
idx_verbs_variants             -- Fast lookup of reform variants  
idx_conjugations_lookup        -- Fast lookup by (verb, voice, mood, tense, person)
idx_conjugations_search        -- Fast search by conjugation text
idx_participles_lookup         -- Fast lookup of participles
```

### Database Size
- **Total size**: 209 MB
- **Verbs**: 6,288 (including 122 reform variants = 61 pairs)
- **Conjugations**: 978,010 records
- **Participles**: 74,748 records

## Example Query Comparisons

### Get 1st person singular present indicative

**Old approach:**
```sql
SELECT verb, ind_present FROM ACTIVE_AVOIR WHERE verb = 'parler';
-- Result: "parler", "parle;parles;parle;parlons;parlez;parlent"
-- Must parse string at position 0 to get "parle"
```

**New approach:**
```sql
SELECT conjugation 
FROM conjugations c
JOIN verbs v ON c.verb_id = v.id
WHERE v.infinitive = 'parler' 
  AND voice = 'voix_active_avoir'
  AND mood = 'indicatif' 
  AND tense = 'present'
  AND person = '1s';
-- Result: "parle" (direct access)
```

### Find all verbs where 1s ends in -ais

**Old approach:**
```sql
-- Not possible without string parsing in application code
```

**New approach:**
```sql
SELECT DISTINCT v.infinitive
FROM verbs v
JOIN conjugations c ON v.id = c.verb_id
WHERE c.person = '1s'
  AND c.mood = 'indicatif'
  AND c.tense = 'present'
  AND c.conjugation LIKE '%ais'
ORDER BY v.infinitive;
```

### Get participles

**Old approach:**
```sql
-- Not stored in database at all
```

**New approach:**
```sql
SELECT form, participle
FROM participles p
JOIN verbs v ON p.verb_id = v.id
WHERE v.infinitive = 'abaisser'
  AND v.voice = 'voix_active_avoir';
-- Returns all 9 forms (present + 8 past forms)
```

## Migration Notes

### For Existing Users

If you have code using the old schema:

**Python example (old):**
```python
cursor.execute("SELECT ind_present FROM ACTIVE_AVOIR WHERE verb = ?", (verb,))
result = cursor.fetchone()[0]
persons = result.split(';')  # ['parle', 'parles', 'parle', ...]
je_form = persons[0]
```

**Python example (new):**
```python
cursor.execute("""
    SELECT conjugation 
    FROM conjugations c
    JOIN verbs v ON c.verb_id = v.id
    WHERE v.infinitive = ? 
      AND voice = 'voix_active_avoir'
      AND mood = 'indicatif' 
      AND tense = 'present'
      AND person = '1s'
""", (verb,))
je_form = cursor.fetchone()[0]
```

Or use the helper class:
```python
from examples.database_example import FrenchVerbDB

db = FrenchVerbDB()
je_form = db.get_conjugation(verb, 'voix_active_avoir', 'indicatif', 'present', '1s')
```

## Resources

- **SQL Examples**: `examples/database_queries.sql` (22 example queries)
- **Python Helper**: `examples/database_example.py` (FrenchVerbDB class)
- **Schema Documentation**: See `README.md` for full schema details

## Benefits Summary

✅ **Normalized** - Proper relational design, no data duplication  
✅ **Complete** - Includes participles, compounds, reform metadata  
✅ **Queryable** - Search by any dimension without string parsing  
✅ **Flexible** - Easy to extend with new persons or tenses  
✅ **Performant** - Strategic indexes for common queries  
✅ **Documented** - 22 SQL examples + Python helper class  
✅ **Compatible** - Supports all 6,288 verbs including reform variants

## Generation

To regenerate the database with the new schema:

```bash
python3 crawler.py -E:GEN-SQLITE3
```

The database will be created at `./output/verbs.db`.
