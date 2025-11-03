#!/usr/bin/env python3
"""
Organize Sounds

Organizes sound files by faction and renames them with creature names.
"""

import json
import sys
import shutil
from pathlib import Path

try:
    import json5
except ImportError:
    print("Error: json5 library required. Install with: pip install json5")
    sys.exit(1)

def organize_sounds(creatures_json_path: str, sound_dir: str, output_dir: str):
    """Organize and rename sound files by faction."""
    
    try:
        with open(creatures_json_path, 'r', encoding='utf-8') as f:
            creatures_data = json5.load(f)
    except FileNotFoundError:
        print(f"Error: creatures.json not found at {creatures_json_path}")
        return
    
    sound_path = Path(sound_dir)
    if not sound_path.exists():
        print(f"Error: Sound directory {sound_dir} does not exist")
        return
    
    output_path = Path(output_dir)
    
    # Build case-insensitive lookup of all wav files
    all_wav_files = {}
    for wav_file in sound_path.rglob("*.wav"):
        all_wav_files[wav_file.stem.upper()] = wav_file
    
    print(f"Found {len(all_wav_files)} WAV files\n")
    
    # Action name mapping
    action_names = {
        'Attack': 'AttackSound',
        'Defend': 'DefendSound',
        'Death': 'DeathSound',
        'Move': 'MoveSound',
        'Shoot': 'ShootSound',
        'Hurt': 'HurtSound',
        'Summon': 'SummonSound'
    }
    
    copied_count = 0
    missing_count = 0
    
    for creature_key, creature_info in creatures_data.items():
        if not isinstance(creature_info, dict) or 'sounds' not in creature_info:
            continue
        
        name = creature_info.get('name', creature_key)
        faction = creature_info.get('faction', 'unknown')
        
        # Extract faction name (remove "sod." or "hota." prefix)
        faction_name = faction.split('.')[-1] if '.' in faction else faction
        
        # Create faction directory
        faction_dir = output_path / faction_name
        faction_dir.mkdir(parents=True, exist_ok=True)
        
        for action, filename in creature_info['sounds'].items():
            # Find source file (case-insensitive)
            source_file = all_wav_files.get(filename.upper())
            
            if not source_file:
                print(f"✗ Missing: {filename}.wav for {name} ({action})")
                missing_count += 1
                continue
            
            # Build target filename
            action_name = action_names.get(action, f"{action}Sound")
            target_filename = f"Heroes3 - {name} - {action_name}.wav"
            target_file = faction_dir / target_filename
            
            # Copy file
            shutil.copy2(source_file, target_file)
            copied_count += 1
    
    print(f"\n{'='*60}")
    print(f"Organization complete:")
    print(f"  Files copied: {copied_count}")
    print(f"  Files missing: {missing_count}")

def main():
    if len(sys.argv) < 4:
        print("Usage: python organize_sounds.py <creatures_json> <sound_dir> <output_dir>")
        print("Example: python organize_sounds.py creatures.json 'J:/Heroes/sound' 'J:/Heroes/renamed-sound'")
        sys.exit(1)
    
    creatures_json = sys.argv[1]
    sound_dir = sys.argv[2]
    output_dir = sys.argv[3]
    
    organize_sounds(creatures_json, sound_dir, output_dir)

if __name__ == "__main__":
    main()
