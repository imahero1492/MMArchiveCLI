#!/usr/bin/env python3
"""
Add Loadpr01.bmp to empty.lod
"""

import sys
import os
from pathlib import Path

script_dir = Path(__file__).parent

class MMArchiveConfig:
    ignore_unzip_errors = True

def add_to_archive(archivepath, filepath, config):
    """Add file to archive using MMArchiveCLI logic"""
    sys.path.insert(0, str(script_dir / 'src'))
    from src.RSLod_complete import rs_load_mm_archive
    from io import BytesIO
    
    if not Path(archivepath).exists():
        print(f'Archive not found: {archivepath}')
        return 1
    
    if not Path(filepath).exists():
        print(f'File not found: {filepath}')
        return 1
    
    archive = rs_load_mm_archive(archivepath)
    archive.files.ignore_unzip_errors = config.ignore_unzip_errors
    
    with open(filepath, 'rb') as f:
        file_data = f.read()
        file_name = Path(filepath).name
    
    data_stream = BytesIO(file_data)
    archive.add(file_name, data_stream)
    print(f'Added: {file_name}')
    
    archive.files.save()
    print('Archive saved.')
    return 0

def LOD_ADD(folder, filename, archive):
    archivepath = script_dir / "Data" / archive
    filepath = script_dir / "Data" / folder / filename
    add_to_archive(str(archivepath), str(filepath), MMArchiveConfig())

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python add_loadpr01.py <lod_file> <bmp_file>")
        print("Example: python add_loadpr01.py empty.lod Loadpr01.bmp")
        sys.exit(1)
    
    sys.exit(add_to_archive(sys.argv[1], sys.argv[2], MMArchiveConfig()))
