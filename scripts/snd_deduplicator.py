#!/usr/bin/env python3
"""
SND File Deduplicator

Recursively searches for .snd files, extracts their contents with deduplication
based on xxhash, and organizes them in a new directory structure.
"""

import os
import sys
from pathlib import Path
import xxhash
from typing import Set

# Add src directory to path for MMArchive imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.RSLod_complete import rs_load_mm_archive
except ImportError:
    print("Error: MMArchiveCLI src modules not found. Ensure src/ directory exists.")
    sys.exit(1)

def extract_snd_files_deduplicated(source_root: str, target_root: str):
    """
    Extract SND files with deduplication based on xxhash.
    
    Args:
        source_root: Root directory to search for .snd files (E:/Games/Heroes/01.deduped)
        target_root: Root directory for extracted files (J:/Heroes/sound)
    """
    source_path = Path(source_root)
    target_path = Path(target_root)
    
    if not source_path.exists():
        print(f"Error: Source directory {source_root} does not exist")
        return
    
    seen_hashes: Set[str] = set()
    processed_files = 0
    skipped_files = 0
    extracted_files = 0
    
    print(f"Searching for .snd files in {source_root}")
    
    # Find all .snd files recursively
    snd_files = sorted(list(source_path.rglob("*.snd")))
    print(f"Found {len(snd_files)} .snd files")
    
    for snd_file in snd_files:
        try:
            print(f"Processing {snd_file}")
            
            # Open SND file using MMArchive
            snd = rs_load_mm_archive(str(snd_file))
            
            if snd.files.count == 0:
                print(f"  Archive appears empty (0 files)")
                continue
            
            # Check if any files match our criteria before creating directories
            matching_files = []
            for i in range(snd.files.count):
                filename = snd.files.get_name(i).rstrip('\x00')
                filename_upper = filename.upper()
                name_no_ext = os.path.splitext(filename)[0].upper()
                

                
                if any(suffix in filename_upper for suffix in ['ATTK', 'DFND', 'KILL', 'MOVE', 'SHOT', 'WNCE', 'SUMM']):
                    matching_files.append((i, filename))
            
            if not matching_files:
                print(f"  No matching files found (checked {snd.files.count} files)")
                continue
            

            
            # Create target directory structure only if we have matching files
            rel_path = snd_file.relative_to(source_path)
            target_dir = target_path / rel_path.parent / f"{snd_file.stem}_snd"
            target_dir.mkdir(parents=True, exist_ok=True)
            
            for i, filename in matching_files:
                processed_files += 1
                
                # Extract file data to memory
                file_data = snd.extract_array(i)
                
                # Calculate xxhash
                hash_obj = xxhash.xxh64()
                hash_obj.update(file_data)
                file_hash = hash_obj.hexdigest()
                
                if file_hash in seen_hashes:
                    skipped_files += 1
                    continue
                
                seen_hashes.add(file_hash)
                
                # Write unique file to disk
                clean_filename = filename.replace('\x00', '')
                if clean_filename.upper().endswith('WAV'):
                    clean_filename = clean_filename[:-3] + '.wav'
                elif not clean_filename.lower().endswith('.wav'):
                    clean_filename += '.wav'
                target_file = target_dir / clean_filename
                with open(target_file, 'wb') as f:
                    f.write(file_data)
                
                extracted_files += 1
                
                if extracted_files % 100 == 0:
                    print(f"  Extracted {extracted_files} unique files, skipped {skipped_files} duplicates")
            
        except Exception as e:
            print(f"Error processing {snd_file}: {e}")
            continue
    
    print(f"\nCompleted:")
    print(f"  Total files processed: {processed_files}")
    print(f"  Unique files extracted: {extracted_files}")
    print(f"  Duplicate files skipped: {skipped_files}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python snd_deduplicator.py <source_root> <target_root>")
        print("Example: python snd_deduplicator.py 'E:/Games/Heroes/01.deduped' 'J:/Heroes/sound'")
        sys.exit(1)
    
    source_root = sys.argv[1]
    target_root = sys.argv[2]
    
    extract_snd_files_deduplicated(source_root, target_root)