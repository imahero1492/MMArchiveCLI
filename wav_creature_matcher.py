#!/usr/bin/env python3
"""
WAV Creature Matcher

Finds WAV files, removes action suffixes from filenames, and matches
the remaining stem to creature names using fuzzy matching.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
import sys

try:
    from fuzzywuzzy import fuzz, process
except ImportError:
    print("Error: fuzzywuzzy library required. Install with: pip install fuzzywuzzy")
    sys.exit(1)

def load_creatures_json(json_path: str) -> Dict[str, str]:
    """
    Load creatures.json and extract name mappings.
    
    Returns:
        Dict mapping creature keys to names
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            creatures_data = json.load(f)
        
        # Extract name field from each creature
        name_mapping = {}
        for key, creature_info in creatures_data.items():
            if isinstance(creature_info, dict) and 'name' in creature_info:
                name_mapping[key] = creature_info['name']
        
        return name_mapping
    except FileNotFoundError:
        print(f"Error: creatures.json not found at {json_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {json_path}: {e}")
        sys.exit(1)

def remove_action_suffixes(filename_stem: str) -> str:
    """
    Remove action suffixes from filename stem.
    
    Args:
        filename_stem: Filename without extension
        
    Returns:
        Cleaned filename stem
    """
    suffixes = ['ATTK', 'DFND', 'KILL', 'MOVE', 'SHOT', 'WNCE', 'SUMM']
    
    stem_upper = filename_stem.upper()
    for suffix in suffixes:
        if stem_upper.endswith(suffix):
            return filename_stem[:-len(suffix)]
    
    return filename_stem

def find_best_creature_match(cleaned_stem: str, creature_names: Dict[str, str], threshold: int = 60) -> Tuple[str, str, int]:
    """
    Find the best matching creature name using fuzzy matching.
    
    Args:
        cleaned_stem: Cleaned filename stem
        creature_names: Dict of creature key -> name mappings
        threshold: Minimum match score (0-100)
        
    Returns:
        Tuple of (creature_key, creature_name, match_score)
    """
    if not cleaned_stem:
        return "", "", 0
    
    # Create list of all creature names for fuzzy matching
    names_list = list(creature_names.values())
    
    # Try multiple fuzzy matching methods for better results
    methods = [
        fuzz.ratio,
        fuzz.partial_ratio,
        fuzz.token_sort_ratio,
        fuzz.token_set_ratio
    ]
    
    best_match = None
    best_score = 0
    
    for method in methods:
        match = process.extractOne(cleaned_stem, names_list, scorer=method)
        if match and match[1] > best_score:
            best_match = match
            best_score = match[1]
    
    if best_match and best_match[1] >= threshold:
        matched_name = best_match[0]
        match_score = best_match[1]
        
        # Find the creature key for this name
        creature_key = next((key for key, name in creature_names.items() if name == matched_name), "")
        
        return creature_key, matched_name, match_score
    
    return "", "", 0

def process_wav_files(sound_dir: str, creatures_json_path: str, output_file: str = None):
    """
    Process WAV files and match them to creatures.
    
    Args:
        sound_dir: Directory containing WAV files
        creatures_json_path: Path to creatures.json file
        output_file: Optional output file for results
    """
    sound_path = Path(sound_dir)
    
    if not sound_path.exists():
        print(f"Error: Sound directory {sound_dir} does not exist")
        return
    
    # Load creature names
    creature_names = load_creatures_json(creatures_json_path)
    print(f"Loaded {len(creature_names)} creatures from JSON")
    
    # Find all WAV files recursively
    wav_files = list(sound_path.rglob("*.wav"))
    print(f"Found {len(wav_files)} WAV files")
    
    results = []
    matched_count = 0
    
    for wav_file in wav_files:
        filename_stem = wav_file.stem
        
        # Remove action suffixes
        cleaned_stem = remove_action_suffixes(filename_stem)
        
        # Skip if nothing left after cleaning
        if not cleaned_stem:
            continue
        
        # Find best creature match
        creature_key, creature_name, match_score = find_best_creature_match(cleaned_stem, creature_names)
        
        result = {
            'file_path': str(wav_file),
            'original_stem': filename_stem,
            'cleaned_stem': cleaned_stem,
            'creature_key': creature_key,
            'creature_name': creature_name,
            'match_score': match_score
        }
        
        results.append(result)
        
        if creature_key:
            matched_count += 1
        else:
            print(f"✗ {filename_stem} -> {cleaned_stem} -> No match found")
    
    print(f"\nMatching complete:")
    print(f"  Total files processed: {len(results)}")
    print(f"  Successfully matched: {matched_count}")
    print(f"  No matches found: {len(results) - matched_count}")
    
    # Save results if output file specified
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Results saved to {output_file}")

def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: python wav_creature_matcher.py <sound_dir> <creatures_json> [output_file]")
        print("Example: python wav_creature_matcher.py 'J:/Heroes/sound' 'creatures.json' 'matches.json'")
        sys.exit(1)
    
    sound_dir = sys.argv[1]
    creatures_json = sys.argv[2]
    output_file = sys.argv[3] if len(sys.argv) > 3 else None
    
    process_wav_files(sound_dir, creatures_json, output_file)

if __name__ == "__main__":
    main()