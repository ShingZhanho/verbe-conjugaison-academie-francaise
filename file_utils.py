"""
File and directory utilities for the crawler.
Created on: 2025-11-11
"""

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


def read_infinitives_file(filepath: str) -> List[str]:
    """
    Read infinitives from a file.
    
    Args:
        filepath: Path to the infinitives file
        
    Returns:
        List of verb infinitives
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


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


def read_cache_file(verb: str) -> Optional[str]:
    """
    Read cached search result for a verb.
    
    Args:
        verb: The verb infinitive
        
    Returns:
        Cache content or None if not found
    """
    cache_path = f"./output/cache/{verb}.txt"
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


def write_cache_file(verb: str, content: str) -> None:
    """
    Write search result to cache.
    
    Args:
        verb: The verb infinitive
        content: Content to cache
    """
    with open(f"./output/cache/{verb}.txt", "w", encoding="utf-8") as f:
        f.write(content)


def cache_exists(verb: str, cache_type: str = "txt") -> bool:
    """
    Check if a cache file exists for a verb.
    
    Args:
        verb: The verb infinitive
        cache_type: Type of cache ('txt', 'html', 'parsed')
        
    Returns:
        True if cache exists
    """
    if cache_type == "txt":
        return os.path.exists(f"./output/cache/{verb}.txt")
    elif cache_type == "html":
        return os.path.exists(f"./output/cache/{verb}.html")
    elif cache_type == "parsed":
        return os.path.exists(f"./output/parsed/{verb}.txt")
    return False


def merge_parsed_files(output_file: str) -> dict:
    """
    Merge all parsed conjugation files into a single JSON file.
    
    Args:
        output_file: Path to the output JSON file
        
    Returns:
        Merged dictionary
    """
    parsed_files = sorted([f for f in os.listdir("./output/parsed") if f.endswith(".txt")])
    
    with open(output_file, "w", encoding="utf-8") as out:
        out.write("{")
        for i, file in enumerate(parsed_files):
            with open(f"./output/parsed/{file}", "r", encoding="utf-8") as f:
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
