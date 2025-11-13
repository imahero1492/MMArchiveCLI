#!/usr/bin/env python3
"""
Check Efreeti Sounds

Checks if Efreeti sounds are properly configured and copied.
"""

import sys
from pathlib import Path

try:
    import json5
except ImportError:
    print("Error: json5 library required. Install with: pip install json5")
    sys.exit(1)

def check_efreeti(creatures_json: str, original_sound_dir: str, renamed_sound_dir: str):
    """Check Efreeti sound configuration and files."""
    
    # Load creatures.json
    try:
        with open(creatures_json, 'r', encoding='utf-8') as f:
            creatures_data = json5.load(f)
    except FileNotFoundError:
        print(f"Error: {creatures_json} not found")
        return
    
    # Find Efreeti entries
    print("Searching for Efreeti in creatures.json...\n")
    
    for key, data in creatures_data.items():
        if not isinstance(data, dict):
            continue
        
        name = data.get('name', '')
        if 'efreet' in name.lower() or 'efreet' in key.lower():
            print(f"Found: {key}")
            print(f"  Name: {name}")
            print(f"  Faction: {data.get('faction', 'N/A')}")
            
            if 'sounds' in data:
                print(f"  Sounds:")
                for action, filename in data['sounds'].items():
                    print(f"    {action}: {filename}")
                    
                    # Check if file exists in original location
                    original_path = Path(original_sound_dir)
                    found_original = None
                    for wav_file in original_path.rglob("*.wav"):
                        if wav_file.stem.upper() == filename.upper():
                            found_original = wav_file
                            break
                    
                    if found_original:
                        print(f"      ✓ Found in original: {found_original}")
                    else:
                        print(f"      ✗ NOT found in original")
                    
                    # Check if file exists in renamed location
                    renamed_path = Path(renamed_sound_dir)
                    faction_name = data.get('faction', '').split('.')[-1]
                    action_names = {
                        'Attack': 'AttackSound',
                        'Defend': 'DefendSound',
                        'Death': 'DeathSound',
                        'Move': 'MoveSound',
                        'Shoot': 'ShootSound',
                        'Hurt': 'HurtSound',
                        'Summon': 'SummonSound'
                    }
                    action_name = action_names.get(action, f"{action}Sound")
                    expected_renamed = renamed_path / faction_name / f"Heroes3 - {name} - {action_name}.wav"
                    
                    if expected_renamed.exists():
                        print(f"      ✓ Found in renamed: {expected_renamed}")
                    else:
                        print(f"      ✗ NOT found in renamed: {expected_renamed}")
            else:
                print(f"  No sounds configured")
            
            print()

def main():
    if len(sys.argv) < 4:
        print("Usage: python check_efreeti.py <creatures_json> <original_sound_dir> <renamed_sound_dir>")
        print("Example: python check_efreeti.py creatures.json 'J:/Heroes/sound' 'J:/Heroes/renamed-sound'")
        sys.exit(1)
    
    creatures_json = sys.argv[1]
    original_sound_dir = sys.argv[2]
    renamed_sound_dir = sys.argv[3]
    
    check_efreeti(creatures_json, original_sound_dir, renamed_sound_dir)

if __name__ == "__main__":
    main()
