#!/usr/bin/env python3
"""
Verify Sound Files

Checks if all sound files referenced in creatures.json exist in the sound directory.
"""

import json
import sys
from pathlib import Path

try:
    import json5
except ImportError:
    print("Error: json5 library required. Install with: pip install json5")
    sys.exit(1)

def verify_sound_files(creatures_json_path: str, sound_dir: str):
    """Verify all sound files exist."""
    
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
    
    # Build case-insensitive lookup of all wav files
    all_wav_files = {}
    for wav_file in sound_path.rglob("*.wav"):
        all_wav_files[wav_file.stem.upper()] = str(wav_file)
    
    print(f"Found {len(all_wav_files)} WAV files in {sound_dir}\n")
    
    missing = []
    found_count = 0
    
    for creature_key, creature_info in creatures_data.items():
        if isinstance(creature_info, dict) and 'sounds' in creature_info:
            name = creature_info.get('name', creature_key)
            
            for action, filename in creature_info['sounds'].items():
                # Check case-insensitive
                if filename.upper() not in all_wav_files:
                    missing.append((creature_key, name, action, filename))
                else:
                    found_count += 1
    
    print(f"Verified {found_count} sound files exist\n")
    print(f"Total creatures with sounds: {sum(1 for c in creatures_data.values() if isinstance(c, dict) and 'sounds' in c)}")
    print(f"Total sound references: {found_count + len(missing)}")
    
    if missing:
        print(f"\n{len(missing)} sound files are MISSING:\n")
        for key, name, action, filename in sorted(missing):
            print(f"{filename}.wav")
    else:
        print("All sound files found!")

def main():
    if len(sys.argv) < 3:
        print("Usage: python verify_sound_files.py <creatures_json> <sound_dir>")
        print("Example: python verify_sound_files.py creatures.json 'J:/Heroes/sound'")
        sys.exit(1)
    
    creatures_json = sys.argv[1]
    sound_dir = sys.argv[2]
    verify_sound_files(creatures_json, sound_dir)

if __name__ == "__main__":
    main()
