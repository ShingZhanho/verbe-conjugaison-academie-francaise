"""
An extension for generating an SQLite database for verb conjugations.

This module creates a normalized relational database from the JSON conjugation data.
The schema supports efficient querying by person, tense, mood, voice, and includes
full support for participles and 1990 spelling reform metadata.

Schema:
    - verbs: Core verb metadata (infinitive, h_aspire, reform info)
    - conjugations: All person conjugations (normalized, one row per person/tense)
    - participles: Participle forms (present, past with all genders/numbers)

Created on: 2025-06-04 10:56:40
Updated on: 2025-11-11
Created by: Jacob Shing
"""

import global_vars as gl
import log
import os
import sqlite3
import constants as const

def generate_sqlite_db(loaded_json):
    """
    Generate a normalized SQLite database from the JSON conjugation data.
    
    Args:
        loaded_json: Dictionary of verb data loaded from verbs.json
    """
    db_path = f"{const.DIR_OUTPUT}/verbs.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        log.info(f"Removed existing database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # == CREATE NORMALIZED SCHEMA ==
    log.info("Creating database schema...")
    
    # Core verb metadata table
    cursor.execute("""
        CREATE TABLE verbs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            infinitive TEXT UNIQUE NOT NULL,
            h_aspire BOOLEAN DEFAULT 0,
            rectification_1990 BOOLEAN DEFAULT 0,
            rectification_1990_variante TEXT
        )
    """)
    
    # Conjugations table (normalized by person)
    cursor.execute("""
        CREATE TABLE conjugations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verb_id INTEGER NOT NULL,
            voice TEXT NOT NULL,
            mood TEXT NOT NULL,
            tense TEXT NOT NULL,
            person TEXT NOT NULL,
            conjugation TEXT NOT NULL,
            FOREIGN KEY (verb_id) REFERENCES verbs(id) ON DELETE CASCADE,
            UNIQUE(verb_id, voice, mood, tense, person)
        )
    """)
    
    # Participles table
    cursor.execute("""
        CREATE TABLE participles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verb_id INTEGER NOT NULL,
            voice TEXT NOT NULL,
            form TEXT NOT NULL,
            participle TEXT NOT NULL,
            FOREIGN KEY (verb_id) REFERENCES verbs(id) ON DELETE CASCADE,
            UNIQUE(verb_id, voice, form)
        )
    """)
    
    # Create indexes for common queries
    log.info("Creating indexes...")
    cursor.execute("CREATE INDEX idx_verbs_infinitive ON verbs(infinitive)")
    cursor.execute("CREATE INDEX idx_verbs_variants ON verbs(rectification_1990_variante)")
    cursor.execute("CREATE INDEX idx_conjugations_lookup ON conjugations(verb_id, voice, mood, tense, person)")
    cursor.execute("CREATE INDEX idx_conjugations_search ON conjugations(conjugation)")
    cursor.execute("CREATE INDEX idx_participles_lookup ON participles(verb_id, voice, form)")

    # == LOAD DATA INTO TABLES ==
    log.info(f"Loading data for {len(loaded_json)} verbs...")
    verb_count = 0
    conjugation_count = 0
    participle_count = 0
    
    for infinitive, verb_data in loaded_json.items():
        # Insert verb metadata
        cursor.execute("""
            INSERT INTO verbs (infinitive, h_aspire, rectification_1990, rectification_1990_variante)
            VALUES (?, ?, ?, ?)
        """, (
            infinitive,
            verb_data.get('h_aspire', False),
            verb_data.get('rectification_1990', False),
            verb_data.get('rectification_1990_variante')
        ))
        verb_id = cursor.lastrowid
        verb_count += 1
        
        # Process each voice
        for voice_key in ['voix_active_avoir', 'voix_active_etre', 'voix_prono']:
            voice_data = verb_data.get(voice_key)
            if not voice_data:
                continue
            
            # Process participles
            participe_data = voice_data.get('participe')
            if participe_data:
                # Present participle
                if participe_data.get('present'):
                    cursor.execute("""
                        INSERT INTO participles (verb_id, voice, form, participle)
                        VALUES (?, ?, ?, ?)
                    """, (verb_id, voice_key, 'present', participe_data['present']))
                    participle_count += 1
                
                # Past participles
                passe_data = participe_data.get('passe', {})
                for form_key, participle_value in passe_data.items():
                    cursor.execute("""
                        INSERT INTO participles (verb_id, voice, form, participle)
                        VALUES (?, ?, ?, ?)
                    """, (verb_id, voice_key, f'passe_{form_key}', participle_value))
                    participle_count += 1
            
            # Process moods and tenses
            for mood in ['indicatif', 'subjonctif', 'conditionnel', 'imperatif']:
                mood_data = voice_data.get(mood)
                if not mood_data:
                    continue
                
                for tense, tense_data in mood_data.items():
                    if not isinstance(tense_data, dict):
                        continue
                    
                    # Insert each person conjugation
                    for person, conjugation in tense_data.items():
                        if conjugation:  # Skip None/empty values
                            cursor.execute("""
                                INSERT INTO conjugations (verb_id, voice, mood, tense, person, conjugation)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (verb_id, voice_key, mood, tense, person, conjugation))
                            conjugation_count += 1
        
        # Log progress every 1000 verbs
        if verb_count % 1000 == 0:
            log.info(f"Processed {verb_count} verbs...")

    # Commit and close
    conn.commit()
    cursor.close()
    conn.close()
    
    log.info(f"Database generation complete!")
    log.info(f"  Verbs: {verb_count}")
    log.info(f"  Conjugations: {conjugation_count}")
    log.info(f"  Participles: {participle_count}")
    log.info(f"  Database size: {os.path.getsize(db_path) / 1024 / 1024:.2f} MB")
    log.info(f"  Saved to: {db_path}")