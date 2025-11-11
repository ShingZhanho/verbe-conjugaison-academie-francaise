#!/usr/bin/env python3
"""
Example Python script demonstrating how to use the French verb conjugation database.

This script shows various ways to query the normalized SQLite database to retrieve
verb conjugations, participles, and metadata.
"""

import sqlite3
from typing import List, Tuple, Dict, Optional


class FrenchVerbDB:
    """Helper class for querying the French verb conjugation database."""
    
    def __init__(self, db_path: str = "./output/verbs.db"):
        """Initialize database connection."""
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self.cursor = self.conn.cursor()
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def get_verb_metadata(self, infinitive: str) -> Optional[Dict]:
        """Get metadata for a verb (h_aspire, reform info)."""
        self.cursor.execute("""
            SELECT id, infinitif, h_aspire, rectification_1990, rectification_1990_variante
            FROM verbes
            WHERE infinitif = ?
        """, (infinitive,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def get_conjugation(self, infinitive: str, voice: str, mood: str, 
                       tense: str, person: str) -> Optional[str]:
        """Get a specific conjugation form."""
        self.cursor.execute("""
            SELECT c.conjugaison
            FROM conjugaisons c
            JOIN verbes v ON c.verbe_id = v.id
            WHERE v.infinitif = ? 
                AND c.voix = ? 
                AND c.mode = ? 
                AND c.temps = ?
                AND c.personne = ?
        """, (infinitive, voice, mood, tense, person))
        row = self.cursor.fetchone()
        return row['conjugaison'] if row else None
    
    def get_tense_conjugations(self, infinitive: str, voice: str, 
                               mood: str, tense: str) -> Dict[str, str]:
        """Get all person conjugations for a specific tense."""
        self.cursor.execute("""
            SELECT c.personne, c.conjugaison
            FROM conjugaisons c
            JOIN verbes v ON c.verbe_id = v.id
            WHERE v.infinitif = ? 
                AND c.voix = ? 
                AND c.mode = ? 
                AND c.temps = ?
            ORDER BY 
                CASE c.personne 
                    WHEN '1s' THEN 1 WHEN '2s' THEN 2 WHEN '3sm' THEN 3 WHEN '3sf' THEN 4
                    WHEN '1p' THEN 5 WHEN '2p' THEN 6 WHEN '3pm' THEN 7 WHEN '3pf' THEN 8
                END
        """, (infinitive, voice, mood, tense))
        return {row['personne']: row['conjugaison'] for row in self.cursor.fetchall()}
    
    def get_participles(self, infinitive: str, voice: str) -> Dict[str, str]:
        """Get all participle forms for a verb."""
        self.cursor.execute("""
            SELECT forme, participe
            FROM participes p
            JOIN verbes v ON p.verbe_id = v.id
            WHERE v.infinitif = ? AND p.voix = ?
            ORDER BY forme
        """, (infinitive, voice))
        return {row['forme']: row['participe'] for row in self.cursor.fetchall()}
    
    def find_verbs_with_pattern(self, pattern: str, mood: str = 'indicatif',
                                tense: str = 'present', person: str = '1s',
                                limit: int = 10) -> List[Tuple[str, str]]:
        """Find verbs where conjugation matches a pattern (SQL LIKE syntax)."""
        self.cursor.execute("""
            SELECT DISTINCT v.infinitif, c.conjugaison
            FROM verbes v
            JOIN conjugaisons c ON v.id = c.verbe_id
            WHERE c.conjugaison LIKE ?
                AND c.mode = ?
                AND c.temps = ?
                AND c.personne = ?
            ORDER BY v.infinitif
            LIMIT ?
        """, (pattern, mood, tense, person, limit))
        return [(row['infinitif'], row['conjugaison']) for row in self.cursor.fetchall()]
    
    def get_reform_variants(self) -> List[Tuple[str, str]]:
        """Get all pairs of 1990 reform spelling variants."""
        self.cursor.execute("""
            SELECT infinitif, rectification_1990_variante
            FROM verbes
            WHERE rectification_1990 = 1 
                AND rectification_1990_variante IS NOT NULL
                AND infinitif < rectification_1990_variante  -- Avoid duplicates
            ORDER BY infinitif
        """)
        return [(row['infinitif'], row['rectification_1990_variante']) 
                for row in self.cursor.fetchall()]
    
    def get_verbs_by_auxiliary(self, auxiliary: str) -> List[str]:
        """Get verbs using a specific auxiliary (avoir/etre/pronominal)."""
        voice_map = {
            'avoir': 'voix_active_avoir',
            'etre': 'voix_active_etre',
            'être': 'voix_active_etre',
            'pronominal': 'voix_prono'
        }
        voice = voice_map.get(auxiliary.lower())
        if not voice:
            raise ValueError(f"Invalid auxiliary: {auxiliary}")
        
        self.cursor.execute("""
            SELECT DISTINCT v.infinitif
            FROM verbes v
            JOIN conjugaisons c ON v.id = c.verbe_id
            WHERE c.voix = ?
            ORDER BY v.infinitif
        """, (voice,))
        return [row['infinitif'] for row in self.cursor.fetchall()]


def print_conjugation_table(db: FrenchVerbDB, infinitive: str, 
                            voice: str = 'voix_active_avoir',
                            mood: str = 'indicatif', tense: str = 'present'):
    """Print a formatted conjugation table."""
    person_labels = {
        '1s': 'je', '2s': 'tu', '3sm': 'il', '3sf': 'elle',
        '1p': 'nous', '2p': 'vous', '3pm': 'ils', '3pf': 'elles'
    }
    
    conjugations = db.get_tense_conjugations(infinitive, voice, mood, tense)
    
    print(f"\n{infinitive.upper()} - {mood} {tense}")
    print("=" * 50)
    for person, conj in conjugations.items():
        label = person_labels.get(person, person)
        print(f"{label:8} {conj}")


def main():
    """Run example queries."""
    db = FrenchVerbDB()
    
    # Example 1: Get verb metadata
    print("=" * 70)
    print("EXAMPLE 1: Verb Metadata")
    print("=" * 70)
    metadata = db.get_verb_metadata('être')
    print(f"Verb: {metadata['infinitif']}")
    print(f"H aspiré: {metadata['h_aspire']}")
    print(f"1990 Reform: {metadata['rectification_1990']}")
    print(f"Variant: {metadata['rectification_1990_variante']}")
    
    # Example 2: Get specific conjugation
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Specific Conjugation")
    print("=" * 70)
    conj = db.get_conjugation('aller', 'voix_active_etre', 'indicatif', 'present', '1s')
    print(f"je vais: {conj}")
    
    # Example 3: Print conjugation table
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Conjugation Table")
    print("=" * 70)
    print_conjugation_table(db, 'parler', 'voix_active_avoir', 'indicatif', 'present')
    
    # Example 4: Get participles
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Participles")
    print("=" * 70)
    participles = db.get_participles('abaisser', 'voix_active_avoir')
    print(f"Participles for 'abaisser':")
    for form, participle in participles.items():
        print(f"  {form:20} {participle}")
    
    # Example 5: Find verbs ending in -ais
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Pattern Search (1s forms ending in -ais)")
    print("=" * 70)
    verbs = db.find_verbs_with_pattern('%ais', 'indicatif', 'present', '1s', 10)
    for infinitive, conjugation in verbs:
        print(f"  {infinitive:20} -> {conjugation}")
    
    # Example 6: Get reform variants
    print("\n" + "=" * 70)
    print("EXAMPLE 6: 1990 Spelling Reform Variants (first 10)")
    print("=" * 70)
    variants = db.get_reform_variants()[:10]
    for v1, v2 in variants:
        print(f"  {v1:20} <-> {v2}")
    
    # Example 7: Compare active vs pronominal
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Active vs Pronominal Comparison")
    print("=" * 70)
    print("Active voice (avoir):")
    active = db.get_tense_conjugations('abaisser', 'voix_active_avoir', 'indicatif', 'present')
    for person, conj in list(active.items())[:3]:
        print(f"  {person}: {conj}")
    
    print("\nPronominal voice:")
    prono = db.get_tense_conjugations('abaisser', 'voix_prono', 'indicatif', 'present')
    for person, conj in list(prono.items())[:3]:
        print(f"  {person}: {conj}")
    
    # Example 8: Verbs using être auxiliary
    print("\n" + "=" * 70)
    print("EXAMPLE 8: Verbs using 'être' auxiliary (first 15)")
    print("=" * 70)
    etre_verbs = db.get_verbs_by_auxiliary('être')[:15]
    for i, verb in enumerate(etre_verbs, 1):
        print(f"  {i:2}. {verb}")
    
    db.close()
    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
