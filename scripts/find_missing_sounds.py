#!/usr/bin/env python3
"""
Find Missing Sounds

Reports creatures in creatures.json that are missing sound mappings.
"""

import json
import sys

try:
    import json5
except ImportError:
    print("Error: json5 library required. Install with: pip install json5")
    sys.exit(1)

def find_missing_sounds(creatures_json_path: str):
    """Find creatures without sound mappings."""
    
    try:
        with open(creatures_json_path, 'r', encoding='utf-8') as f:
            creatures_data = json5.load(f)
    except FileNotFoundError:
        print(f"Error: creatures.json not found at {creatures_json_path}")
        return
    
    missing = []
    
    for creature_key, creature_info in creatures_data.items():
        if isinstance(creature_info, dict):
            if 'sounds' not in creature_info or not creature_info['sounds']:
                name = creature_info.get('name', creature_key)
                missing.append((creature_key, name))
    
    print(f"Found {len(missing)} creatures without sounds:\n")
    
    for key, name in sorted(missing, key=lambda x: x[1]):
        print(f"{key}: {name}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python find_missing_sounds.py <creatures_json>")
        print("Example: python find_missing_sounds.py creatures.json")
        sys.exit(1)
    
    creatures_json = sys.argv[1]
    find_missing_sounds(creatures_json)

if __name__ == "__main__":
    main()
