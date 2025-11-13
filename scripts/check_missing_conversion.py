#!/usr/bin/env python3
"""
Check Missing Conversion

Checks which WAV files exist in source but not in WebM output.
"""

import sys
from pathlib import Path

def check_missing(source_dir: str, output_dir: str):
    """Check which files weren't converted."""
    
    source_path = Path(source_dir)
    output_path = Path(output_dir)
    
    if not source_path.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        return
    
    if not output_path.exists():
        print(f"Error: Output directory {output_dir} does not exist")
        return
    
    # Get all WAV files
    wav_files = {f.relative_to(source_path): f for f in source_path.rglob("*.wav")}
    
    # Get all WebM files
    webm_files = {f.relative_to(output_path).with_suffix('.wav'): f for f in output_path.rglob("*.webm")}
    
    # Find missing
    missing = []
    for rel_path, wav_file in wav_files.items():
        if rel_path not in webm_files:
            missing.append((rel_path, wav_file))
    
    print(f"Total WAV files: {len(wav_files)}")
    print(f"Total WebM files: {len(webm_files)}")
    print(f"Missing conversions: {len(missing)}\n")
    
    if missing:
        print("Missing files:")
        for rel_path, full_path in missing:
            print(f"  {rel_path}")
            print(f"    Full path: {full_path}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python check_missing_conversion.py <source_dir> <output_dir>")
        print("Example: python check_missing_conversion.py 'J:/Heroes/renamed-sound' 'J:/Heroes/webm-sounds'")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    check_missing(source_dir, output_dir)

if __name__ == "__main__":
    main()
