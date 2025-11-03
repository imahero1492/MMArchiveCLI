#!/usr/bin/env python3
"""
Extract Missing Sounds

Searches SND archives for missing sound files and extracts them to target directory.
"""

import os
import sys
from pathlib import Path

# Add src directory to path for MMArchive imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.RSLod_complete import rs_load_mm_archive
except ImportError:
    print("Error: MMArchiveCLI src modules not found. Ensure src/ directory exists.")
    sys.exit(1)

def load_missing_files(missing_txt_path: str) -> set:
    """Load list of missing files from text file."""
    try:
        with open(missing_txt_path, 'r', encoding='utf-8') as f:
            # Read lines and normalize to uppercase without .wav extension
            missing = set()
            for line in f:
                filename = line.strip()
                if filename:
                    # Remove .wav extension if present
                    if filename.upper().endswith('.WAV'):
                        filename = filename[:-4]
                    missing.add(filename.upper())
            return missing
    except FileNotFoundError:
        print(f"Error: {missing_txt_path} not found")
        sys.exit(1)

def extract_missing_sounds(snd_root: str, missing_txt: str, target_dir: str):
    """
    Extract missing sound files from SND archives.
    
    Args:
        snd_root: Root directory containing .snd files (E:/Games/Heroes/01.deduped)
        missing_txt: Path to missing.txt file
        target_dir: Target directory for extracted files (J:/Heroes/missing-sound)
    """
    snd_path = Path(snd_root)
    target_path = Path(target_dir)
    
    if not snd_path.exists():
        print(f"Error: SND directory {snd_root} does not exist")
        return
    
    # Load missing files list
    missing_files = load_missing_files(missing_txt)
    print(f"Looking for {len(missing_files)} missing sound files\n")
    
    # Create target directory
    target_path.mkdir(parents=True, exist_ok=True)
    
    found_files = {}
    not_found = set(missing_files)
    
    # Find all .snd files recursively
    snd_files = sorted(list(snd_path.rglob("*.snd")))
    print(f"Searching {len(snd_files)} .snd archives...\n")
    
    for snd_file in snd_files:
        if not not_found:
            break  # All files found
        
        try:
            # Open SND file using MMArchive
            snd = rs_load_mm_archive(str(snd_file))
            
            if snd.files.count == 0:
                continue
            
            # Check each file in archive
            for i in range(snd.files.count):
                if not not_found:
                    break
                
                filename = snd.files.get_name(i).rstrip('\x00')
                
                # Normalize filename for comparison
                clean_name = filename.replace('\x00', '')
                
                # Handle various formats: "FILEwav", "FILE.wav", "FILE"
                name_upper = clean_name.upper()
                if name_upper.endswith('.WAV'):
                    name_no_ext = name_upper[:-4]
                elif name_upper.endswith('WAV'):
                    name_no_ext = name_upper[:-3]
                else:
                    name_no_ext = name_upper
                
                # Check if this is a missing file
                if name_no_ext in not_found:
                    # Extract file data
                    file_data = snd.extract_array(i)
                    
                    # Normalize output filename
                    output_name = name_no_ext + '.wav'
                    target_file = target_path / output_name
                    
                    with open(target_file, 'wb') as f:
                        f.write(file_data)
                    
                    found_files[name_no_ext] = str(snd_file)
                    not_found.remove(name_no_ext)
                    print(f"✓ Found {output_name} in {snd_file.name}")
        
        except Exception as e:
            print(f"Error processing {snd_file}: {e}")
            continue
    
    # Report results
    print(f"\n{'='*60}")
    print(f"Extraction complete:")
    print(f"  Found and extracted: {len(found_files)}")
    print(f"  Not found: {len(not_found)}")
    
    if not_found:
        print(f"\n{'='*60}")
        print(f"The following {len(not_found)} files were NOT FOUND:\n")
        for filename in sorted(not_found):
            print(f"  {filename}.wav")

def main():
    if len(sys.argv) < 4:
        print("Usage: python extract_missing_sounds.py <snd_root> <missing_txt> <target_dir>")
        print("Example: python extract_missing_sounds.py 'E:/Games/Heroes/01.deduped' 'missing.txt' 'J:/Heroes/missing-sound'")
        sys.exit(1)
    
    snd_root = sys.argv[1]
    missing_txt = sys.argv[2]
    target_dir = sys.argv[3]
    
    extract_missing_sounds(snd_root, missing_txt, target_dir)

if __name__ == "__main__":
    main()
