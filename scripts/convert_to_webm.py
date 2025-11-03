#!/usr/bin/env python3
"""
Convert to WebM

Converts WAV files to WebM format using ffmpeg.
"""

import subprocess
import sys
from pathlib import Path

def convert_to_webm(source_dir: str, output_dir: str):
    """Convert all WAV files to WebM format."""
    
    source_path = Path(source_dir)
    output_path = Path(output_dir)
    
    if not source_path.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        return
    
    # Find all WAV files recursively
    wav_files = list(source_path.rglob("*.wav"))
    print(f"Found {len(wav_files)} WAV files\n")
    
    converted = 0
    failed = 0
    
    for wav_file in wav_files:
        # Preserve directory structure
        rel_path = wav_file.relative_to(source_path)
        target_file = output_path / rel_path.with_suffix('.webm')
        
        # Create target directory
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert using ffmpeg
        try:
            subprocess.run(
                ['ffmpeg', '-i', str(wav_file), '-y', str(target_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            converted += 1
            if converted % 10 == 0:
                print(f"Converted {converted}/{len(wav_files)} files...")
        except subprocess.CalledProcessError:
            print(f"✗ Failed: {wav_file.name}")
            failed += 1
        except FileNotFoundError:
            print("Error: ffmpeg not found. Please install ffmpeg and add to PATH")
            return
    
    print(f"\n{'='*60}")
    print(f"Conversion complete:")
    print(f"  Converted: {converted}")
    print(f"  Failed: {failed}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python convert_to_webm.py <source_dir> <output_dir>")
        print("Example: python convert_to_webm.py 'J:/Heroes/renamed-sound' 'J:/Heroes/webm-sounds'")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    output_dir = sys.argv[2]
    
    convert_to_webm(source_dir, output_dir)

if __name__ == "__main__":
    main()
