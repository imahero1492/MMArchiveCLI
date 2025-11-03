#!/usr/bin/env python3
"""
WAV Creature Matcher

Loads sound mappings from creatures/*.json files, then fuzzy matches
remaining files for creatures without sound data (factory/cove).
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

try:
    import json5
except ImportError:
    print("Error: json5 library required. Install with: pip install json5")
    sys.exit(1)

def load_faction_sounds(creatures_dir: str) -> Dict[str, Dict[str, str]]:
    """
    Load sound mappings from creatures/*.json files.
    
    Returns:
        Dict mapping creature keys to their sound mappings
    """
    creatures_path = Path(creatures_dir)
    if not creatures_path.exists():
        return {}
    
    sound_mappings = {}
    
    # Load from creatures/*.json (sod factions)
    for json_file in creatures_path.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                faction_data = json5.load(f)
            
            for creature_key, creature_info in faction_data.items():
                if isinstance(creature_info, dict) and 'sound' in creature_info:
                    # Convert sound keys to our format and remove .wav extension
                    sounds = {}
                    for action, filename in creature_info['sound'].items():
                        # Map their keys to our keys
                        action_map = {
                            'attack': 'Attack',
                            'defend': 'Defend',
                            'killed': 'Death',
                            'move': 'Move',
                            'wince': 'Hurt',
                            'shoot': 'Shoot',
                            'summon': 'Summon'
                        }
                        if action in action_map:
                            # Remove .wav extension
                            sounds[action_map[action]] = filename.replace('.wav', '')
                    
                    if sounds:
                        # Prepend "sod." to match creatures.json format
                        full_key = f"sod.{creature_key}"
                        sound_mappings[full_key] = sounds
        except Exception as e:
            print(f"Warning: Error loading {json_file}: {e}")
    
    # Load from creatures/hota/*/*.json (hota factions)
    hota_path = creatures_path / 'hota'
    if hota_path.exists():
        for json_file in hota_path.rglob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    faction_data = json5.load(f)
                
                for creature_key, creature_info in faction_data.items():
                    if isinstance(creature_info, dict) and 'sound' in creature_info:
                        # Convert sound keys to our format
                        sounds = {}
                        for action, filepath in creature_info['sound'].items():
                            # Map their keys to our keys
                            action_map = {
                                'attack': 'Attack',
                                'defend': 'Defend',
                                'killed': 'Death',
                                'move': 'Move',
                                'wince': 'Hurt',
                                'shoot': 'Shoot',
                                'summon': 'Summon'
                            }
                            if action in action_map:
                                # Extract filename from path (last part after /)
                                filename = filepath.split('/')[-1].replace('.wav', '')
                                sounds[action_map[action]] = filename
                        
                        if sounds:
                            # Prepend "hota." to match creatures.json format
                            full_key = f"hota.{creature_key}"
                            sound_mappings[full_key] = sounds
            except Exception as e:
                print(f"Warning: Error loading {json_file}: {e}")
    
    return sound_mappings

def load_creatures_json(json_path: str) -> Dict[str, str]:
    """
    Load creatures.json and extract name mappings.
    
    Returns:
        Dict mapping creature keys to names
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            creatures_data = json5.load(f)
        
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
    
    # First, check for exact prefix matches (highest priority)
    for key, name in creature_names.items():
        if name.lower().startswith(cleaned_stem.lower()):
            # Found a creature whose name starts with the file prefix - use it!
            return key, name, 100
    
    # Create list of all creature names for fuzzy matching
    names_list = list(creature_names.values())
    
    # Try multiple fuzzy matching methods
    methods = [
        fuzz.ratio,
        fuzz.partial_ratio,
        fuzz.token_sort_ratio,
        fuzz.token_set_ratio
    ]
    
    best_match = None
    best_score = 0
    
    for method in methods:
        match = process.extractOne(cleaned_stem.lower(), [name.lower() for name in names_list], scorer=method)
        if match and match[1] > best_score:
            # Find original name that matches the lowercase result
            original_name = next((name for name in names_list if name.lower() == match[0]), match[0])
            best_match = (original_name, match[1])
            best_score = match[1]
    
    if best_match and best_match[1] >= threshold:
        matched_name = best_match[0]
        match_score = best_match[1]
        
        # Find the creature key for this name
        creature_key = next((key for key, name in creature_names.items() if name == matched_name), "")
        
        return creature_key, matched_name, match_score
    
    return "", "", 0

def process_wav_files(sound_dir: str, creatures_json_path: str, creatures_dir: str, output_file: str = None):
    """
    Process WAV files and match them to creatures.
    
    Args:
        sound_dir: Directory containing WAV files
        creatures_json_path: Path to creatures.json file
        creatures_dir: Directory containing faction JSON files
        output_file: Optional output file for results
    """
    sound_path = Path(sound_dir)
    
    if not sound_path.exists():
        print(f"Error: Sound directory {sound_dir} does not exist")
        return
    
    # Load full creatures data
    try:
        with open(creatures_json_path, 'r', encoding='utf-8') as f:
            creatures_data = json5.load(f)
    except FileNotFoundError:
        print(f"Error: creatures.json not found at {creatures_json_path}")
        return
    
    # Load sound mappings from faction files
    faction_sounds = load_faction_sounds(creatures_dir)
    print(f"Loaded sound mappings for {len(faction_sounds)} creatures from faction files")
    
    # Track files from faction mappings (normalize to uppercase for case-insensitive matching)
    faction_files = set()
    for sounds in faction_sounds.values():
        for filename in sounds.values():
            faction_files.add(filename.upper())
    
    # Apply faction sound mappings to creatures_data
    for creature_key, sounds in faction_sounds.items():
        if creature_key in creatures_data:
            if 'sounds' not in creatures_data[creature_key]:
                creatures_data[creature_key]['sounds'] = {}
            creatures_data[creature_key]['sounds'].update(sounds)
    
    # Extract name mappings for matching
    creature_names = {}
    for key, creature_info in creatures_data.items():
        if isinstance(creature_info, dict) and 'name' in creature_info:
            creature_names[key] = creature_info['name']
    
    print(f"Loaded {len(creature_names)} creatures from JSON")
    
    # Find all WAV files recursively
    wav_files = list(sound_path.rglob("*.wav"))
    print(f"Found {len(wav_files)} WAV files")
    
    # Action suffix to sound key mapping
    action_mapping = {
        'ATTK': 'Attack',
        'DFND': 'Defend', 
        'KILL': 'Death',
        'MOVE': 'Move',
        'SHOT': 'Shoot',
        'WNCE': 'Hurt',
        'SUMM': 'Summon'
    }
    
    # Track all files with action suffixes
    file_tracking = {}
    
    # Track unmatched files
    for wav_file in wav_files:
        filename_stem = wav_file.stem
        
        # Determine which action this file represents
        action_type = None
        cleaned_stem = filename_stem
        
        for suffix, action in action_mapping.items():
            if filename_stem.upper().endswith(suffix):
                action_type = action
                cleaned_stem = filename_stem[:-len(suffix)]
                break
        
        # Skip if no action suffix found
        if not action_type or not cleaned_stem:
            continue
        
        # Check if this file is in faction files (case-insensitive)
        if filename_stem.upper() in faction_files:
            file_tracking[filename_stem] = True
        else:
            file_tracking[filename_stem] = False
    
    # Report all unassigned files in JSON format
    unassigned = [filename for filename, assigned in file_tracking.items() if not assigned]
    
    faction_count = len(faction_files)
    unmatched_count = len(unassigned)
    print(f"\nMatched {faction_count} files from faction JSON files")
    print(f"{unmatched_count} files need manual assignment:\n")
    
    if unassigned:
        
        # Group by base name (without suffix)
        from collections import defaultdict
        grouped = defaultdict(dict)
        
        for filename in sorted(unassigned):
            # Find action suffix and clean stem
            cleaned_stem = filename
            action = None
            
            for suffix in action_mapping.keys():
                if filename.upper().endswith(suffix):
                    cleaned_stem = filename[:-len(suffix)]
                    action = action_mapping[suffix]
                    break
            
            if action:
                grouped[cleaned_stem.upper()][action] = filename
        
        # Print in JSON format
        for base, sounds in sorted(grouped.items()):
            print('        "sounds": {')
            items = list(sounds.items())
            for i, (action, filename) in enumerate(items):
                comma = ',' if i < len(items) - 1 else ''
                print(f'            "{action}": "{filename}"{comma}')
            print('        }\n')
    
    # Save updated creatures.json (use standard json for output)
    with open(creatures_json_path, 'w', encoding='utf-8') as f:
        json.dump(creatures_data, f, indent=4, ensure_ascii=False)
    print(f"\nUpdated {creatures_json_path} with sound mappings")

def main():
    """Main entry point"""
    if len(sys.argv) < 4:
        print("Usage: python wav_creature_matcher.py <sound_dir> <creatures_json> <creatures_dir> [output_file]")
        print("Example: python wav_creature_matcher.py 'J:/Heroes/sound' 'creatures.json' 'creatures'")
        sys.exit(1)
    
    sound_dir = sys.argv[1]
    creatures_json = sys.argv[2]
    creatures_dir = sys.argv[3]
    output_file = sys.argv[4] if len(sys.argv) > 4 else None
    
    process_wav_files(sound_dir, creatures_json, creatures_dir, output_file)

if __name__ == "__main__":
    main()