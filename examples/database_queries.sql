-- Example SQL queries for the French verb conjugation database
-- Database: verbs.db
-- 
-- This file contains example queries demonstrating how to use the normalized
-- database schema to extract various conjugation information.
--
-- NOTE: All table and column names are in French with accents removed:
--   - verbes (table) with infinitif (column)
--   - conjugaisons (table) with verbe_id, voix, mode, temps, personne, conjugaison
--   - participes (table) with verbe_id, voix, forme, participe

-- ============================================================================
-- BASIC QUERIES
-- ============================================================================

-- 1. Get all conjugations for a specific verb
SELECT 
    v.infinitif,
    c.voix,
    c.mode,
    c.temps,
    c.personnenene,
    c.conjugaison
FROM conjugaisons c
JOIN verbes v ON c.verbe_id = v.id
WHERE v.infinitif = 'être'
ORDER BY c.voix, c.mode, c.temps, 
    CASE c.personnenene 
        WHEN '1s' THEN 1 WHEN '2s' THEN 2 WHEN '3sm' THEN 3 WHEN '3sf' THEN 4
        WHEN '1p' THEN 5 WHEN '2p' THEN 6 WHEN '3pm' THEN 7 WHEN '3pf' THEN 8
    END;

-- 2. Get present indicative conjugation for a verb
SELECT 
    personne,
    conjugaison
FROM conjugaisons c
JOIN verbes v ON c.verbe_id = v.id
WHERE v.infinitif = 'aller' 
    AND mode = 'indicatif' 
    AND temps = 'present'
    AND voix = 'voix_active_etre'
ORDER BY 
    CASE personne 
        WHEN '1s' THEN 1 WHEN '2s' THEN 2 WHEN '3sm' THEN 3 WHEN '3sf' THEN 4
        WHEN '1p' THEN 5 WHEN '2p' THEN 6 WHEN '3pm' THEN 7 WHEN '3pf' THEN 8
    END;

-- 3. Get all participles for a verb
SELECT 
    voix,
    forme,
    participe
FROM participes p
JOIN verbes v ON p.verbe_id = v.id
WHERE v.infinitif = 'abaisser'
ORDER BY voix, forme;

-- ============================================================================
-- VERBS WITH H ASPIRÉ
-- ============================================================================

-- 4. Find all verbs that begin with h aspiré
SELECT infinitive
FROM verbs
WHERE h_aspire = 1
ORDER BY infinitive;

-- ============================================================================
-- 1990 SPELLING REFORM QUERIES
-- ============================================================================

-- 5. Find all verbs with 1990 reform variants
SELECT 
    infinitif,
    rectification_1990_variante
FROM verbs
WHERE rectification_1990 = 1 
    AND rectification_1990_variante IS NOT NULL
ORDER BY infinitive;

-- 6. Get both spellings of a reformed verb (e.g., connaître/connaitre)
SELECT 
    infinitif,
    rectification_1990_variante as alternate_spelling
FROM verbs
WHERE infinitif IN ('connaître', 'connaitre')
ORDER BY infinitive;

-- 7. Count how many verb pairs have reform variants
SELECT COUNT(*) / 2 as reformed_verb_pairs
FROM verbs
WHERE rectification_1990 = 1 
    AND rectification_1990_variante IS NOT NULL;

-- ============================================================================
-- AUXILIARY VERB QUERIES
-- ============================================================================

-- 8. Find verbs that use "être" as auxiliary
SELECT DISTINCT infinitive
FROM verbes v
JOIN conjugaisons c ON v.id = c.verbe_id
WHERE c.voix = 'voix_active_etre'
ORDER BY infinitive
LIMIT 20;

-- 9. Find verbs that have both "avoir" and "être" auxiliary forms
SELECT DISTINCT v.infinitif
FROM verbes v
WHERE EXISTS (
    SELECT 1 FROM conjugaisons c1 
    WHERE c1.verbe_id = v.id AND c1.voix = 'voix_active_avoir'
)
AND EXISTS (
    SELECT 1 FROM conjugaisons c2 
    WHERE c2.verbe_id = v.id AND c2.voix = 'voix_active_etre'
)
ORDER BY v.infinitif
LIMIT 20;

-- ============================================================================
-- PRONOMINAL/REFLEXIVE VERBS
-- ============================================================================

-- 10. Find all pronominal verbs
SELECT DISTINCT v.infinitif
FROM verbes v
JOIN conjugaisons c ON v.id = c.verbe_id
WHERE c.voix = 'voix_prono'
ORDER BY v.infinitif
LIMIT 20;

-- 11. Compare active vs pronominal forms
SELECT 
    'active' as form,
    person,
    conjugation
FROM conjugaisons c
JOIN verbes v ON c.verbe_id = v.id
WHERE v.infinitif = 'abaisser'
    AND voice = 'voix_active_avoir'
    AND mood = 'indicatif'
    AND tense = 'present'
UNION ALL
SELECT 
    'pronominal' as form,
    person,
    conjugation
FROM conjugaisons c
JOIN verbes v ON c.verbe_id = v.id
WHERE v.infinitif = 'abaisser'
    AND voice = 'voix_prono'
    AND mood = 'indicatif'
    AND tense = 'present'
ORDER BY person, form;

-- ============================================================================
-- CONJUGATION PATTERN SEARCHES
-- ============================================================================

-- 12. Find verbs ending in -er
SELECT infinitive
FROM verbs
WHERE infinitif LIKE '%er'
ORDER BY infinitive
LIMIT 20;

-- 13. Find verbs where 1st person singular present ends in -ais
SELECT DISTINCT v.infinitif
FROM verbes v
JOIN conjugaisons c ON v.id = c.verbe_id
WHERE c.personnene = '1s'
    AND c.mode = 'indicatif'
    AND c.temps = 'present'
    AND c.conjugaison LIKE '%ais'
ORDER BY v.infinitif
LIMIT 20;

-- 14. Find irregular verbs in present tense (e.g., stem changes)
-- Example: verbs where 1s and 1p have different stems
SELECT DISTINCT v.infinitif,
    c1.conjugaison as first_singular,
    c2.conjugaison as first_plural
FROM verbes v
JOIN conjugaisons c1 ON v.id = c1.verbe_id AND c1.personne = '1s'
JOIN conjugaisons c2 ON v.id = c2.verbe_id AND c2.personne = '1p'
WHERE c1.mode = 'indicatif' 
    AND c1.temps = 'present'
    AND c2.mode = 'indicatif' 
    AND c2.temps = 'present'
    AND c1.voix = c2.voix
    AND v.infinitif LIKE '%er'
    AND SUBSTR(c1.conjugaison, 1, LENGTH(c1.conjugaison)-2) != 
        SUBSTR(c2.conjugaison, 1, LENGTH(c2.conjugaison)-3)
ORDER BY v.infinitif
LIMIT 20;

-- ============================================================================
-- STATISTICAL QUERIES
-- ============================================================================

-- 15. Count total verbs in database
SELECT COUNT(*) as total_verbs FROM verbs;

-- 16. Count conjugations per mood
SELECT 
    mood,
    COUNT(*) as conjugation_count
FROM conjugations
GROUP BY mood
ORDER BY conjugation_count DESC;

-- 17. Count verbs by auxiliary type
SELECT 
    CASE 
        WHEN voice = 'voix_active_avoir' THEN 'avoir'
        WHEN voice = 'voix_active_etre' THEN 'être'
        WHEN voice = 'voix_prono' THEN 'pronominal'
    END as auxiliary_type,
    COUNT(DISTINCT verb_id) as verb_count
FROM conjugations
GROUP BY voice
ORDER BY verb_count DESC;

-- 18. Find most common conjugation patterns
SELECT 
    conjugation,
    COUNT(*) as frequency
FROM conjugations
WHERE mood = 'indicatif' 
    AND tense = 'present' 
    AND person = '1s'
GROUP BY conjugation
ORDER BY frequency DESC
LIMIT 20;

-- ============================================================================
-- ADVANCED QUERIES
-- ============================================================================

-- 19. Find verbs with identical conjugations across different persons
SELECT DISTINCT v.infinitif
FROM verbes v
JOIN conjugaisons c1 ON v.id = c1.verbe_id AND c1.personne = '1s'
JOIN conjugaisons c2 ON v.id = c2.verbe_id AND c2.personne = '3sm'
WHERE c1.mode = 'indicatif'
    AND c1.temps = 'present'
    AND c2.mode = 'indicatif'
    AND c2.temps = 'present'
    AND c1.voix = c2.voix
    AND c1.conjugaison = c2.conjugaison
ORDER BY v.infinitif
LIMIT 20;

-- 20. Find verbs that exist only in impersonal form (only 3sm conjugated)
SELECT DISTINCT v.infinitif
FROM verbes v
WHERE EXISTS (
    SELECT 1 FROM conjugaisons c
    WHERE c.verbe_id = v.id 
        AND c.personnene = '3sm'
        AND c.mode = 'indicatif'
        AND c.temps = 'present'
)
AND NOT EXISTS (
    SELECT 1 FROM conjugaisons c
    WHERE c.verbe_id = v.id 
        AND c.personnene = '1s'
        AND c.mode = 'indicatif'
        AND c.temps = 'present'
)
ORDER BY v.infinitif
LIMIT 20;

-- 21. Get conjugation comparison across tenses
SELECT 
    tense,
    conjugation
FROM conjugaisons c
JOIN verbes v ON c.verbe_id = v.id
WHERE v.infinitif = 'faire'
    AND voice = 'voix_active_avoir'
    AND mood = 'indicatif'
    AND person = '1s'
ORDER BY 
    CASE tense
        WHEN 'present' THEN 1
        WHEN 'imparfait' THEN 2
        WHEN 'passe_simple' THEN 3
        WHEN 'futur_simple' THEN 4
        WHEN 'passe_compose' THEN 5
        WHEN 'plus_que_parfait' THEN 6
        WHEN 'passe_anterieur' THEN 7
        WHEN 'futur_anterieur' THEN 8
    END;

-- 22. Full conjugation table for a verb (present indicative)
SELECT 
    CASE person
        WHEN '1s' THEN 'je'
        WHEN '2s' THEN 'tu'
        WHEN '3sm' THEN 'il'
        WHEN '3sf' THEN 'elle'
        WHEN '1p' THEN 'nous'
        WHEN '2p' THEN 'vous'
        WHEN '3pm' THEN 'ils'
        WHEN '3pf' THEN 'elles'
    END as pronoun,
    conjugation
FROM conjugaisons c
JOIN verbes v ON c.verbe_id = v.id
WHERE v.infinitif = 'parler'
    AND voice = 'voix_active_avoir'
    AND mood = 'indicatif'
    AND tense = 'present'
ORDER BY 
    CASE person 
        WHEN '1s' THEN 1 WHEN '2s' THEN 2 WHEN '3sm' THEN 3 WHEN '3sf' THEN 4
        WHEN '1p' THEN 5 WHEN '2p' THEN 6 WHEN '3pm' THEN 7 WHEN '3pf' THEN 8
    END;
