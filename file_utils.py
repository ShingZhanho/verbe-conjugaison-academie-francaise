"""
File and directory utilities for the crawler.
Created on: 2025-11-11
"""

import constants as const
import json
import os
from typing import List, Optional


def ensure_directories(directories: List[str]) -> None:
    """
    Ensure that all specified directories exist.
    
    Args:
        directories: List of directory paths to create
    """
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def read_infinitives_file(filepath: str) -> List[tuple[str, Optional[str]]]:
    """
    Read infinitives from a file.
    Supports two formats:
      - '<verb>:<verb_id>' (new format with pre-resolved verb ID)
      - '<verb>' (legacy format, verb ID will be resolved via search)
    
    Args:
        filepath: Path to the infinitives file
        
    Returns:
        List of (verb, verb_id_or_None) tuples
    """
    result = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if ':' in line:
                verb, verb_id = line.split(':', 1)
                result.append((verb.strip(), verb_id.strip()))
            else:
                result.append((line, None))
    return result


def count_lines(filepath: str) -> int:
    """
    Count the number of lines in a file.
    
    Args:
        filepath: Path to the file
        
    Returns:
        Number of lines
    """
    with open(filepath, "rb") as f:
        return sum(1 for _ in f)





def cache_exists(verb: str, cache_type: str = "html") -> bool:
    """
    Check if a cache file exists for a verb.
    
    Args:
        verb: The verb infinitive
        cache_type: Type of cache ('html', 'parsed')
        
    Returns:
        True if cache exists
    """
    if cache_type == "html":
        return os.path.exists(f"{const.DIR_CACHE}/{verb}{const.EXT_HTML}")
    elif cache_type == "parsed":
        return os.path.exists(f"{const.DIR_PARSED}/{verb}{const.EXT_TXT}")
    return False


def merge_parsed_files(output_file: str) -> dict:
    """
    Merge all parsed conjugation files into a single JSON file.
    
    Args:
        output_file: Path to the output JSON file
        
    Returns:
        Merged dictionary
    """
    parsed_files = sorted([f for f in os.listdir(const.DIR_PARSED) if f.endswith(const.EXT_TXT)])
    
    with open(output_file, "w", encoding="utf-8") as out:
        out.write("{")
        for i, file in enumerate(parsed_files):
            with open(f"{const.DIR_PARSED}/{file}", "r", encoding="utf-8") as f:
                content = f.read().strip()
                out.write(content)
                if i < len(parsed_files) - 1:
                    out.write(",")
        out.write("}")
    
    # Read back and return
    with open(output_file, "r", encoding="utf-8") as f:
        return json.load(f)


def write_formatted_json(data: dict, output_file: str) -> None:
    """
    Write formatted JSON to file.
    
    Args:
        data: Dictionary to write
        output_file: Path to the output file
    """
    with open(output_file, "w", encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=4)
