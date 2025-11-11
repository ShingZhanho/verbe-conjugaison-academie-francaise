"""
Data transformation module for converting parsed conjugation data to the new format.
This module handles:
- Person key mapping (je→1s, tu→2s, etc.)
- Participle key transformation (singulier_m→sm, etc.)
- 1990 spelling reform variants
- Compound participle expansion

Created on: 2025-11-11
"""

import log

# Person pronoun mapping
PERSON_MAPPING = {
    'je': '1s',
    'tu': '2s',
    'il': '3sm',
    'nous': '1p',
    'vous': '2p',
    'ils': '3pm'
}

def transform_verb_data(verb_name: str, verb_data: dict) -> dict:
    """
    Transform verb data from old format to new format.
    
    Args:
        verb_name: The infinitive form of the verb
        verb_data: The parsed verb data in old format
        
    Returns:
        Transformed verb data in new format
    """
    result = {}
    
    # Add 1990 reform metadata
    result['rectification_1990'] = has_infinitive_variant(verb_name)
    result['rectification_1990_variante'] = get_infinitive_variant(verb_name) if result['rectification_1990'] else None
    
    # Transform each voice
    for voice_key, voice_data in verb_data.items():
        if voice_key == 'h_aspire':
            result['h_aspire'] = voice_data
            continue
            
        result[voice_key] = {}
        
        # Transform participle
        if 'participe' in voice_data:
            result[voice_key]['participe'] = transform_participle(voice_data['participe'])
        
        # Transform other moods
        for mood_key, mood_data in voice_data.items():
            if mood_key == 'participe':
                continue
                
            result[voice_key][mood_key] = {}
            
            for tense_key, tense_data in mood_data.items():
                result[voice_key][mood_key][tense_key] = transform_tense(
                    tense_data, 
                    verb_name,
                    mood_key,
                    tense_key
                )
    
    return result


def transform_participle(participe_data: dict) -> dict:
    """
    Transform participle data to new format.
    
    Args:
        participe_data: Participle data with 'present' and 'passe' keys
        
    Returns:
        Transformed participle data with sm, sf, pm, pf, compound_* keys
    """
    result = {
        'present': participe_data.get('present', None),
        'passe': {}
    }
    
    passe = participe_data.get('passe', {})
    if not passe:
        return result
    
    # Transform simple past participles
    if 'singulier_m' in passe:
        # Variable participle
        result['passe']['sm'] = passe['singulier_m']
        result['passe']['sf'] = passe['singulier_f']
        result['passe']['pm'] = passe['pluriel_m']
        result['passe']['pf'] = passe['pluriel_f']
    elif 'compose' in passe:
        # Invariable participle - extract from compose
        compose_text = passe['compose']
        parts = compose_text.split()
        invariable_pp = parts[-1] if parts else compose_text
        
        result['passe']['sm'] = invariable_pp
        result['passe']['sf'] = invariable_pp
        result['passe']['pm'] = invariable_pp
        result['passe']['pf'] = invariable_pp
    
    # Transform compound participles
    if 'compose' in passe:
        compose_text = passe['compose']
        if ',' in compose_text:
            # Has gender/number variations in compound
            parts = [p.strip() for p in compose_text.split(',')]
            if len(parts) >= 4:
                aux_and_sm = parts[0].split()
                aux = ' '.join(aux_and_sm[:-1])
                result['passe']['compound_sm'] = parts[0]
                result['passe']['compound_sf'] = f"{aux} {parts[1]}"
                result['passe']['compound_pm'] = f"{aux} {parts[2]}"
                result['passe']['compound_pf'] = f"{aux} {parts[3]}"
            else:
                # Fallback - duplicate if not enough parts
                result['passe']['compound_sm'] = compose_text
                result['passe']['compound_sf'] = compose_text
                result['passe']['compound_pm'] = compose_text
                result['passe']['compound_pf'] = compose_text
        else:
            # Invariable compound participle
            result['passe']['compound_sm'] = compose_text
            result['passe']['compound_sf'] = compose_text
            result['passe']['compound_pm'] = compose_text
            result['passe']['compound_pf'] = compose_text
    
    return result


def transform_tense(tense_data: dict, verb_name: str, mood: str, tense: str) -> dict:
    """
    Transform a tense conjugation from old format to new format.
    
    Args:
        tense_data: Dictionary with je/tu/il/nous/vous/ils keys
        verb_name: The infinitive form (for 1990 reform detection)
        mood: The mood name (e.g., 'indicatif', 'subjonctif')
        tense: The tense name (e.g., 'present', 'futur_simple')
        
    Returns:
        Transformed tense data with 1s/2s/3sm/3sf/1p/2p/3pm/3pf keys
    """
    result = {}
    
    for person_key, conjugation in tense_data.items():
        # Skip None values (some verbs don't have all persons)
        if conjugation is None:
            continue
            
        # Map to new key
        new_key = PERSON_MAPPING.get(person_key, person_key)
        
        # Convert comma to semicolon (Académie uses comma for variants)
        transformed_conjugation = conjugation.replace(',', ';')
        
        result[new_key] = transformed_conjugation
    
    # Add elle and elles forms (same as il and ils)
    if '3sm' in result:
        result['3sf'] = result['3sm']
    if '3pm' in result:
        result['3pf'] = result['3pm']
    
    return result


def has_infinitive_variant(verb_name: str) -> bool:
    """
    Check if a verb infinitive has a 1990 reform variant.
    
    Args:
        verb_name: The infinitive form of the verb
        
    Returns:
        True if the verb has î or û (which can be reformed)
    """
    return 'î' in verb_name or 'û' in verb_name


def get_infinitive_variant(verb_name: str) -> str | None:
    """
    Get the 1990 reform variant of a verb infinitive.
    
    Args:
        verb_name: The infinitive form of the verb
        
    Returns:
        The reformed spelling (î→i, û→u) or None if no variant
    """
    if has_infinitive_variant(verb_name):
        return verb_name.replace('î', 'i').replace('û', 'u')
    return None


def create_reformed_verb_entry(verb_name: str, verb_data: dict) -> tuple[str, dict] | None:
    """
    Create a duplicate entry for the reformed spelling of a verb.
    
    Args:
        verb_name: The original infinitive form
        verb_data: The transformed verb data
        
    Returns:
        Tuple of (reformed_infinitive, reformed_verb_data) or None if no variant
    """
    if not has_infinitive_variant(verb_name):
        return None
    
    reformed_name = get_infinitive_variant(verb_name)
    if not reformed_name:
        return None
    
    # Create a copy of the verb data
    import copy
    reformed_data = copy.deepcopy(verb_data)
    
    # Update the reform metadata
    reformed_data['rectification_1990'] = True
    reformed_data['rectification_1990_variante'] = verb_name  # Points back to original
    
    # Swap the order of variants in conjugations (reformed form first)
    for voice_key, voice_data in reformed_data.items():
        if voice_key in ['h_aspire', 'rectification_1990', 'rectification_1990_variante']:
            continue
            
        for mood_key, mood_data in voice_data.items():
            if mood_key == 'participe':
                continue
                
            for tense_key, tense_data in mood_data.items():
                for person_key, conjugation in tense_data.items():
                    # If there are variants separated by semicolon, swap them
                    if ';' in conjugation:
                        parts = conjugation.split(';')
                        # Swap order: reformed first for reformed entry
                        tense_data[person_key] = ';'.join(reversed(parts))
    
    log.info(f"Created reformed spelling entry: {reformed_name} → {verb_name}")
    return (reformed_name, reformed_data)
