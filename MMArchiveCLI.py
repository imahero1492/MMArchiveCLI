#!/usr/bin/env python3
"""
MMArchive Command Line Interface
Python port of MMArchiveCLI.dpr
"""

import sys
import os
import json
from pathlib import Path
from src.RSLod_complete import *
from src.RSDef import TRSDefWrapper

CLI_VERSION = '1.3.9-py'

_def_config_cache = None

def _load_def_config():
    """Load defConfig.json once"""
    global _def_config_cache
    if _def_config_cache is None:
        try:
            json_path = Path(__file__).parent / 'defConfig.json'
            with open(json_path, 'r') as f:
                data = json.load(f)
                # Convert crop bounds arrays to tuples
                data['cropBounds'] = {k: tuple(v) for k, v in data['cropBounds'].items()}
                # Convert lists to sets for faster lookup
                data['hotaShadowP2P3'] = set(data['hotaShadowP2P3'])
                data['hotaPalette255To5'] = set(data['hotaPalette255To5'])
                data['keepSelectionPalette'] = set(data['keepSelectionPalette'])
                _def_config_cache = data
        except:
            _def_config_cache = {}
    return _def_config_cache




class Config:
    """Configuration flags"""
    def __init__(self):
        self.extract_with_shadow = True
        self.extract_in_24_bits = False
        self.ignore_unzip_errors = True
        self.crop_frames = True
        self.no_crop_types = set()
        self.individual_crop = False
        self.prefer_hota_names = False
        self.hdl_structure = False
        self.shadow_in_main = False


def get_group_name(group_index, type_of_def, creature_name=''):
    """Get human-readable group name based on DEF type and index"""
    config = _load_def_config()
    type_map = {
        0x42: config.get('creatureGroupNames', {}),
        0x44: config.get('mapObjectGroupNames', {}),
        0x49: config.get('heroGroupNames', {})
    }
    
    if type_of_def in type_map:
        names = type_map[type_of_def]
        group_name = names.get(str(group_index))
        if group_name:
            
            # Special handling for creature groups 17-19
            if type_of_def == 0x42 and group_index in [17, 18, 19]:
                direction = ['Up', 'Straight', 'Down'][group_index - 17]
                if creature_name in config.get('creaturesWithAttack2', []):
                    return f'Attack {direction} 2'
                elif creature_name in config.get('creaturesWithCast', []):
                    return f'Cast {direction}'
            
            return group_name
    return f'Group {group_index}'


def most_repeated_frame(frames):
    """Find the index of the most repeated frame"""
    frame_counts = {}
    for i, frame in enumerate(frames):
        frame_name = frame if isinstance(frame, str) else str(frame)
        if frame_name in frame_counts:
            frame_counts[frame_name].append(i)
        else:
            frame_counts[frame_name] = [i]
    
    max_count = 0
    most_repeated = 0
    for frame_name, indices in frame_counts.items():
        if len(indices) > max_count:
            max_count = len(indices)
            most_repeated = indices[0]
    
    return most_repeated


_objects_cache = None

def _load_objects():
    """Load objectsByID.json once"""
    global _objects_cache
    if _objects_cache is None:
        try:
            json_path = Path(__file__).parent / 'objectsByID.json'
            with open(json_path, 'r') as f:
                data = json.load(f)
                _objects_cache = data if isinstance(data, dict) else {}
        except:
            _objects_cache = {}
    return _objects_cache


def isAdvMapCreature(def_name):
    """Check if DEF is adventure map creature"""
    objects = _load_objects()
    obj = objects.get(def_name.lower())
    return isinstance(obj, dict) and obj.get('sub_type') == 'creature'


def uses_hota_shadow_p2p3(def_name, archive_path='', prefer_hota=False):
    """Check if object uses HotA palette 2/3 for shadow"""
    if 'HotA' not in archive_path and not prefer_hota:
        return False
    config = _load_def_config()
    return def_name.lower() in config.get('hotaShadowP2P3', set())


def needs_palette_255_fix(def_name, archive_path='', prefer_hota=False):
    """Check if palette 255 should be replaced with palette 5"""
    if 'HotA' not in archive_path and not prefer_hota:
        return False
    config = _load_def_config()
    return def_name.lower() in config.get('hotaPalette255To5', set())


def keeps_selection_palette(def_name):
    """Check if selection palette should be kept (not made transparent)"""
    config = _load_def_config()
    return def_name.lower() in config.get('keepSelectionPalette', set())


def get_name(def_name, archive_path='', prefer_hota=False):
    """Get name from objectsByID.json with HotA support"""
    objects = _load_objects()
    obj = objects.get(def_name.lower())
    if not isinstance(obj, dict):
        return ''
    
    # Prefer HotA name if flag is set
    if prefer_hota:
        if 'nameHotA' in obj:
            return obj['nameHotA']
        elif 'name' in obj:
            return obj['name']
    else:
        # Prefer standard name, fallback to HotA name
        if 'name' in obj:
            return obj['name']
        elif 'nameHotA' in obj:
            return obj['nameHotA']
    
    return ''


def get_frame_durations(frames, def_type, group_id, def_name=''):
    """Calculate frame durations based on DEF type and group"""
    durations = []
    pNum = most_repeated_frame(frames)
    
    for num in range(len(frames)):
        if def_type == '9' and group_id == 4 and num == 5:
            durations.append(1000)
        elif def_type == '9' and group_id == 1:
            durations.append(1000/8)
        elif def_type == '2' and group_id == 2 and num == 7:
            durations.append(3000)
        elif def_type == '3' and isAdvMapCreature(def_name) and num == pNum:
            durations.append(1000)
        elif def_type == '3':
            durations.append(1000/6)
        else:
            durations.append(100)
    
    return durations


def show_help():
    """Display help message"""
    print('MMArchive Command Line Interface')
    print('Usage:')
    print('  MMArchiveCLI.py <operation> <archive> [options]')
    print()
    print('Operations:')
    print('  list <archive>                    - List files in archive')
    print('  extract <archive> [-o output_dir] [-f *.ext] - Extract files')
    print('  add <archive> <file>              - Add file to archive (replaces if exists)')
    print('  extractdef <archive|def_file> [-o output_dir] - Extract DEF files for DefTool')
    print('  extractwebp <archive|def_file> [-o output_dir] - Extract DEF files as animated WebP')
    print('  testdef <archive|def_file>                    - Test DEF files without extracting')
    print('  version                           - Show version information')
    print('  help                              - Show this help')
    print()
    print('Options:')
    print('  -o <dir>         Output directory')
    print('  -f <*.ext>       File filter (e.g., *.bmp, *.def)')
    print('  --no-shadow      Extract DEF without external shadow')
    print('  --24bits         Extract DEF in 24 bits')
    print('  --strict-errors  Fail on unpacking errors (default: ignore)')
    print('  --no-crop [2,4]  Disable cropping (default: crop enabled), optionally for specific DEF types')
    print('  --individual-crop Use group-based cropping instead of predefined bounds')
    print('  --hota           Prefer HotA names from objectsByID.json')
    print('  --hdl-structure  Read from HDL and BMP files instead of DEF (extractwebp only)')
    print('  --shadow-in-main Process main frames as if they contain shadows (extractwebp only)')
    print()
    print('Examples:')
    print('  MMArchiveCLI.py list data.lod')
    print('  MMArchiveCLI.py extract data.lod -o extracted -f *.bmp')
    print('  MMArchiveCLI.py add data.lod newfile.txt')
    print('  MMArchiveCLI.py extractdef sprites.lod -o deftool')
    print('  MMArchiveCLI.py extractdef sprite.def -o deftool')
    print('  MMArchiveCLI.py extractwebp sprites.lod -o webp_output')
    print('  MMArchiveCLI.py version')


def parse_args():
    """Parse command line arguments"""
    if len(sys.argv) < 2:
        return 'help', None, None, None, None, None
    
    cmd = sys.argv[1].lower()
    
    if cmd == 'help':
        return 'help', None, None, None, None, None
    
    if cmd == 'version':
        return 'version', None, None, None, None, None
    
    if cmd in ['list', 'extract', 'add', 'extractdef', 'extractwebp', 'testdef']:
        if len(sys.argv) < 3:
            return 'help', None, None, None, None, None
        
        archive = sys.argv[2]
        output = None
        target = None
        file_filter = None
        config = Config()
        
        if cmd == 'add' and len(sys.argv) >= 4:
            target = sys.argv[3]
        
        i = 3 if cmd != 'add' else 4
        while i < len(sys.argv):
            if sys.argv[i] == '-o' and i + 1 < len(sys.argv):
                output = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == '-f' and i + 1 < len(sys.argv):
                file_filter = sys.argv[i + 1].lower()
                i += 2
            elif sys.argv[i] == '--no-shadow':
                config.extract_with_shadow = False
                i += 1
            elif sys.argv[i] == '--24bits':
                config.extract_in_24_bits = True
                i += 1
            elif sys.argv[i] == '--strict-errors':
                config.ignore_unzip_errors = False
                i += 1
            elif sys.argv[i] == '--no-crop':
                if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('-'):
                    # Parse def types
                    types_str = sys.argv[i + 1]
                    config.no_crop_types = set(types_str.split(','))
                    i += 2
                else:
                    # Disable cropping for all types
                    config.crop_frames = False
                    i += 1
            elif sys.argv[i] == '--individual-crop':
                config.individual_crop = True
                i += 1
            elif sys.argv[i] == '--hota':
                config.prefer_hota_names = True
                i += 1
            elif sys.argv[i] == '--hdl-structure':
                config.hdl_structure = True
                i += 1
            elif sys.argv[i] == '--shadow-in-main':
                config.shadow_in_main = True
                i += 1
            else:
                i += 1
        
        if output is None and cmd in ['extract', 'extractdef', 'extractwebp']:
            base = Path(archive).stem.replace('.', '_')
            suffix = '_deftool' if cmd == 'extractdef' else '_webp' if cmd == 'extractwebp' else ''
            output = str(Path(archive).parent / f"{base}{suffix}")
        
        if cmd == 'testdef':
            return cmd, archive, None, None, None, config
        return cmd, archive, output, target, file_filter, config
    
    return 'help', None, None, None, None, None


def list_archive(archive_path, config):
    """List files in archive"""
    try:
        print(f'Loading archive: {archive_path}')
        archive = rs_load_mm_archive(archive_path)
        archive.files.ignore_unzip_errors = config.ignore_unzip_errors
        
        print(f'Archive type: {type(archive).__name__}')
        print(f'Files in archive: {archive.count}')
        if hasattr(archive, 'version'):
            print(f'Archive version: {archive.version}')
        
        print('Name')
        print('----')
        for i in range(archive.count):
            print(archive.get_file_name(i))
    except ERSLodException as e:
        print(f'Error: {e}')
        return 1
    except Exception as e:
        print(f'Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        return 1
    return 0


def extract_archive(archive_path, output_path, file_filter, config):
    """Extract files from archive"""
    try:
        archive = rs_load_mm_archive(archive_path)
        archive.files.ignore_unzip_errors = config.ignore_unzip_errors
        
        filtered_count = sum(1 for i in range(archive.count)
                           if not file_filter or Path(archive.get_file_name(i)).suffix.lower() in file_filter)
        
        print(f'Extracting {filtered_count} files to: {output_path}')
        
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        for i in range(archive.count):
            name = archive.get_file_name(i).rstrip('\x00')  # Remove null terminators
            if file_filter and Path(name).suffix.lower() not in file_filter:
                continue
            
            try:
                extracted = archive.extract(i, output_path, True)
                if extracted:
                    print(f'Extracted: {Path(extracted).name}')
                else:
                    print(f'Skipped: {name}')
            except Exception as e:
                print(f'Error extracting {name}: {e}')
        
        print('Extraction complete.')
    except ERSLodException as e:
        print(f'Error: {e}')
        return 1
    return 0


def add_to_archive(archive_path, target_path, config):
    """Add file to archive"""
    try:
        if not Path(archive_path).exists():
            print(f'Archive not found: {archive_path}')
            return 1
        
        if not Path(target_path).exists():
            print(f'File not found: {target_path}')
            return 1
        
        archive = rs_load_mm_archive(archive_path)
        archive.files.ignore_unzip_errors = config.ignore_unzip_errors
        
        with open(target_path, 'rb') as f:
            file_data = f.read()
            file_name = Path(target_path).name
        
        from io import BytesIO
        data_stream = BytesIO(file_data)
        archive.add(file_name, data_stream)
        print(f'Added: {file_name}')
        
        # Force save to write buffers immediately
        archive.files.save()
        print('Archive saved.')
    except ERSLodException as e:
        print(f'Error: {e}')
        return 1
    return 0


def test_def_files(archive_path, config):
    """Test DEF files in memory without extracting"""
    try:
        if Path(archive_path).suffix.lower() == '.def':
            print(f'Testing DEF file: {archive_path}')
            try:
                with open(archive_path, 'rb') as f:
                    def_data = f.read()
                
                def_wrapper = TRSDefWrapper(def_data)
                print(f'✓ DEF file valid: {def_wrapper.pictures_count} pictures, {len(def_wrapper.groups)} groups')
            except Exception as e:
                print(f'✗ DEF file error: {e}')
                return 1
        else:
            archive = rs_load_mm_archive(archive_path)
            archive.files.ignore_unzip_errors = config.ignore_unzip_errors
            
            print(f'Testing DEF files in archive: {archive.count} total files')
            
            def_count = 0
            error_count = 0
            
            for i in range(archive.count):
                name = archive.get_file_name(i).rstrip('\x00')
                if Path(name).suffix.lower() != '.def':
                    continue
                
                def_count += 1
                try:
                    def_data = archive.extract_array(i)
                    def_wrapper = TRSDefWrapper(bytes(def_data))
                    # Only print errors, not successful tests
                except Exception as e:
                    print(f'✗ {name}: {e}')
                    error_count += 1
            
            print(f'\nTesting complete: {def_count} DEF files tested, {error_count} errors')
            return 1 if error_count > 0 else 0
    except ERSLodException as e:
        print(f'Error: {e}')
        return 1
    return 0


def parse_hdl(hdl_path):
    """Parse HDL file and return def_type and groups info"""
    with open(hdl_path, 'r') as f:
        content = f.read()
    
    # Get type
    type_line = [l for l in content.split('\n') if l.startswith('Type=')]
    def_type = type_line[0].split('=')[1] if type_line else '3'
    
    groups = []
    group_idx = 0
    while f'Group{group_idx}=' in content:
        line = [l for l in content.split('\n') if l.startswith(f'Group{group_idx}=')][0]
        frames = [f.strip() for f in line.split('=')[1].split('|') if f.strip()]
        
        shadow_line = [l for l in content.split('\n') if l.startswith(f'Shadow{group_idx}=')]
        shadows = []
        if shadow_line:
            shadows = [f.strip() for f in shadow_line[0].split('=')[1].split('|') if f.strip()]
        
        groups.append({'group_id': group_idx, 'frames': frames, 'shadows': shadows})
        group_idx += 1
    
    return def_type, groups


def process_webp_group(def_name, def_type, group_id, group_count, frames_data, archive_path, output_dir, config):
    """Process a group of frames and save as WebP"""
    from PIL import Image
    
    # Get object name for filename prefix
    obj_name = get_name(def_name, archive_path, config.prefer_hota_names)
    filename_prefix = obj_name if obj_name else def_name
    
    # Get group name
    if group_count == 1:
        webp_name = f'{filename_prefix}.webp'
    else:
        type_map = {'2': 0x42, '3': 0x43, '4': 0x44, '9': 0x49}
        type_of_def = type_map.get(def_type, 0x43)
        creature_name = obj_name if obj_name else ''
        group_name = get_group_name(group_id, type_of_def, creature_name)
        if group_name.startswith('Group '):
            webp_name = f'{filename_prefix}_{group_id}.webp'
        else:
            webp_name = f'{filename_prefix} {group_name}.webp'
    
    frames = [f['image'] for f in frames_data]
    frame_names = [f['name'] for f in frames_data]
    
    # Crop frames if enabled
    if config.crop_frames and def_type not in config.no_crop_types:
        if config.individual_crop:
            min_x, min_y, max_x, max_y = float('inf'), float('inf'), 0, 0
            for frame in frames:
                bbox = frame.getbbox()
                if bbox:
                    min_x = min(min_x, bbox[0])
                    min_y = min(min_y, bbox[1])
                    max_x = max(max_x, bbox[2])
                    max_y = max(max_y, bbox[3])
            if min_x < float('inf'):
                frames = [frame.crop((min_x, min_y, max_x, max_y)) for frame in frames]
        else:
            crop_key = def_type
            if def_type == '4':
                name_result = get_name(def_name, archive_path, config.prefer_hota_names)
                if 'Airship' in str(name_result):
                    crop_key = '4Airship'
                elif 'Boat' in str(name_result):
                    crop_key = '4Boat'
            
            config = _load_def_config()
            crop_bounds = config.get('cropBounds', {})
            if crop_key in crop_bounds:
                bounds = crop_bounds[crop_key]
                frames = [frame.crop(bounds) for frame in frames]
            else:
                min_x, min_y, max_x, max_y = float('inf'), float('inf'), 0, 0
                for frame in frames:
                    bbox = frame.getbbox()
                    if bbox:
                        min_x = min(min_x, bbox[0])
                        min_y = min(min_y, bbox[1])
                        max_x = max(max_x, bbox[2])
                        max_y = max(max_y, bbox[3])
                if min_x < float('inf'):
                    frames = [frame.crop((min_x, min_y, max_x, max_y)) for frame in frames]
    
    # Calculate durations
    durations = get_frame_durations(frame_names, def_type, group_id, def_name)
    
    # Save as animated WebP
    webp_path = output_dir / webp_name
    frames[0].save(
        webp_path,
        format='WebP',
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        lossless=True,
        quality=100
    )
    print(f'Created WebP: {webp_name} ({len(frames)} frames)')


def extract_webp(archive_path, output_path, config):
    """Extract DEF files as animated WebP"""
    try:
        from PIL import Image
    except ImportError:
        print('Error: Pillow is required for WebP extraction')
        return 1
    
    try:
        if config.hdl_structure:
            # HDL structure mode
            hdl_dir = Path(archive_path)
            if not hdl_dir.is_dir():
                print('Error: --hdl-structure requires a directory path')
                return 1
            
            print(f'Scanning {hdl_dir} for HDL files...')
            hdl_files = list(hdl_dir.glob('*.hdl'))
            
            if not hdl_files:
                print('No HDL files found')
                return 1
            
            print(f'Found {len(hdl_files)} HDL files')
            Path(output_path).mkdir(parents=True, exist_ok=True)
            
            for hdl_path in hdl_files:
                def_name = hdl_path.stem
                output_dir = Path(output_path) / def_name
                output_dir.mkdir(parents=True, exist_ok=True)
                
                def_type, groups = parse_hdl(hdl_path)
                
                for group in groups:
                    if not group['frames']:
                        continue
                    
                    frames_data = []
                    for frame_idx, frame_path in enumerate(group['frames']):
                        img_path = hdl_dir / frame_path
                        shadow_path = hdl_dir / group['shadows'][frame_idx] if frame_idx < len(group['shadows']) and not config.shadow_in_main else None
                        
                        img = Image.open(img_path)
                        shadow = Image.open(shadow_path) if shadow_path and shadow_path.exists() and not config.shadow_in_main else None
                        
                        # Get palette from image
                        palette = img.getpalette()
                        if palette:
                            transparent = tuple(palette[0:3])
                            edge = tuple(palette[3:6])
                            body_two = tuple(palette[6:9])
                            edge_two = tuple(palette[9:12])
                            body = tuple(palette[12:15])
                            selection = tuple(palette[15:18])
                            body_sel = tuple(palette[18:21])
                            edge_sel = tuple(palette[21:24])
                        else:
                            transparent = (255, 255, 0)
                            edge = body = body_two = edge_two = selection = body_sel = edge_sel = (0, 0, 0)
                        
                        # Convert to RGBA
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        if shadow and shadow.mode == 'P':
                            shadow = shadow.convert('RGBA')
                        
                        # Process main image
                        img_data = img.load()
                        w, h = img.size
                        for y in range(h):
                            for x in range(w):
                                pixel = img_data[x, y][:3]
                                if pixel == transparent:
                                    img_data[x, y] = (0, 0, 0, 0)
                        
                        # Process shadow
                        if config.shadow_in_main:
                            # Process main image as if it contains shadows
                            keep_sel = keeps_selection_palette(def_name)
                            for y in range(h):
                                for x in range(w):
                                    pixel = img_data[x, y][:3]
                                    if pixel == transparent or (pixel == selection and not keep_sel):
                                        img_data[x, y] = (0, 0, 0, 0)
                                    elif pixel == edge or pixel == edge_sel or (pixel == edge_two and uses_hota_shadow_p2p3(def_name, '', config.prefer_hota_names)):
                                        img_data[x, y] = (0, 0, 0, 127)
                                    elif pixel == body or pixel == body_sel or (pixel == body_two and uses_hota_shadow_p2p3(def_name, '', config.prefer_hota_names)):
                                        img_data[x, y] = (0, 0, 0, 191)
                        elif shadow:
                            shadow_data = shadow.load()
                            keep_sel = keeps_selection_palette(def_name)
                            for y in range(h):
                                for x in range(w):
                                    pixel = shadow_data[x, y][:3]
                                    if pixel == transparent or (pixel == selection and not keep_sel):
                                        shadow_data[x, y] = (0, 0, 0, 0)
                                    elif pixel == edge or pixel == edge_sel or (pixel == edge_two and uses_hota_shadow_p2p3(def_name, '', config.prefer_hota_names)):
                                        shadow_data[x, y] = (0, 0, 0, 127)
                                    elif pixel == body or pixel == body_sel or (pixel == body_two and uses_hota_shadow_p2p3(def_name, '', config.prefer_hota_names)):
                                        shadow_data[x, y] = (0, 0, 0, 191)
                                    else:
                                        shadow_data[x, y] = (0, 0, 0, 0)
                            
                            img = Image.alpha_composite(shadow, img)
                        
                        frames_data.append({'image': img, 'name': frame_path})
                    
                    if frames_data:
                        process_webp_group(def_name, def_type, group['group_id'], len(groups), frames_data, '', output_dir, config)
            return 0
        
        if Path(archive_path).suffix.lower() == '.def':
            print(f'Extracting DEF file as WebP to: {output_path}')
            
            with open(archive_path, 'rb') as f:
                def_data = f.read()
            
            def_wrapper = TRSDefWrapper(def_data)
            def_name = Path(archive_path).stem
            def_dir = Path(output_path) / def_name
            def_dir.mkdir(parents=True, exist_ok=True)
            
            # Map TypeOfDef to string for duration logic
            type_map = {0x42: '2', 0x43: '3', 0x44: '4', 0x49: '9'}
            def_type = type_map.get(def_wrapper.header.TypeOfDef, 'unknown')
            
            # Check if palette replacement is needed
            replace_palette = needs_palette_255_fix(def_name, archive_path, config.prefer_hota_names)
            
            for group_idx, group in enumerate(def_wrapper.groups):
                if group.ItemsCount == 0:
                    continue
                
                # Get object name for filename prefix
                obj_name = get_name(def_name, archive_path, config.prefer_hota_names)
                filename_prefix = obj_name if obj_name else def_name
                
                # Get group name
                if len(def_wrapper.groups) == 1:
                    webp_name = f'{filename_prefix}.webp'
                else:
                    creature_name = obj_name if obj_name else ''
                    group_name = get_group_name(group.GroupNum, def_wrapper.header.TypeOfDef, creature_name)
                    if group_name.startswith('Group '):
                        webp_name = f'{filename_prefix}_{group.GroupNum}.webp'
                    else:
                        webp_name = f'{filename_prefix} {group_name}.webp'
                
                # Extract frames
                frames_data = []
                for pic_idx in range(group.ItemsCount):
                    try:
                        img, shadow = def_wrapper.extract_bmp(group_idx, pic_idx, bmp_spec=not config.shadow_in_main)
                        
                        # Process both images
                        palette = def_wrapper.def_palette
                        if palette and len(palette) > 7:
                            # Get shadow colors from palette
                            transparent = palette[0]
                            edge = palette[1]
                            body_two = palette[2]
                            edge_two = palette[3]
                            body = palette[4]
                            selection = palette[5]
                            body_sel = palette[6]
                            edge_sel = palette[7]
                            
                            # Process main image
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            
                            img_data = img.load()
                            w, h = img.size
                            for y in range(h):
                                for x in range(w):
                                    pixel = img_data[x, y][:3]
                                    if pixel == transparent:
                                        img_data[x, y] = (0, 0, 0, 0)
                            
                            # Process shadow image
                            if shadow and shadow.mode == 'P':
                                shadow = shadow.convert('RGBA')
                                shadow_data = shadow.load()
                            else:
                                shadow_data = None
                            
                            if config.shadow_in_main:
                                # Process main image as if it contains shadows
                                keep_sel = keeps_selection_palette(def_name)
                                for y in range(h):
                                    for x in range(w):
                                        pixel = img_data[x, y][:3]
                                        if pixel == transparent or (pixel == selection and not keep_sel):
                                            img_data[x, y] = (0, 0, 0, 0)
                                        elif pixel == edge or pixel == edge_sel or (pixel == edge_two and uses_hota_shadow_p2p3(def_name, archive_path, config.prefer_hota_names)):
                                            img_data[x, y] = (0, 0, 0, 127)
                                        elif pixel == body or pixel == body_sel or (pixel == body_two and uses_hota_shadow_p2p3(def_name, archive_path, config.prefer_hota_names)):
                                            img_data[x, y] = (0, 0, 0, 191)
                            elif shadow_data:
                                for y in range(h):
                                    for x in range(w):
                                        pixel = shadow_data[x, y][:3]
                                        keep_sel = keeps_selection_palette(def_name)
                                        if pixel == transparent or (pixel == selection and not keep_sel):
                                            shadow_data[x, y] = (0, 0, 0, 0)
                                        elif pixel == edge or pixel == edge_sel or (pixel == edge_two and uses_hota_shadow_p2p3(def_name, archive_path, config.prefer_hota_names)):
                                            shadow_data[x, y] = (0, 0, 0, 127)
                                        elif pixel == body or pixel == body_sel or (pixel == body_two and uses_hota_shadow_p2p3(def_name, archive_path, config.prefer_hota_names)):
                                            shadow_data[x, y] = (0, 0, 0, 191)
                                        else:
                                            shadow_data[x, y] = (0, 0, 0, 0)
                                
                                img = Image.alpha_composite(shadow, img)
                        else:
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                        
                        # Apply palette replacement if needed
                        if replace_palette:
                            palette = def_wrapper.def_palette
                            if palette and len(palette) > 255:
                                color_255 = palette[255]
                                color_5 = palette[5]
                                img_data = img.load()
                                for y in range(img.size[1]):
                                    for x in range(img.size[0]):
                                        if img_data[x, y][:3] == color_255:
                                            img_data[x, y] = color_5 + (img_data[x, y][3],)
                        
                        frames_data.append({'image': img, 'name': def_wrapper.get_pic_name(group_idx, pic_idx)})
                    except Exception as e:
                        print(f'Error extracting frame {pic_idx} from group {group_idx}: {e}')
                
                if frames_data:
                    process_webp_group(def_name, def_type, group.GroupNum, len(def_wrapper.groups), frames_data, archive_path, def_dir, config)
        
        else:
            archive = rs_load_mm_archive(archive_path)
            archive.files.ignore_unzip_errors = config.ignore_unzip_errors
            
            print(f'Extracting DEF files as WebP to: {output_path}')
            lod_name = Path(archive_path).stem
            lod_dir = Path(output_path) / lod_name
            lod_dir.mkdir(parents=True, exist_ok=True)
            
            def_count = 0
            for i in range(archive.count):
                name = archive.get_file_name(i).rstrip('\x00')
                if Path(name).suffix.lower() != '.def':
                    continue
                
                def_count += 1
                try:
                    def_data = archive.extract_array(i)
                    def_wrapper = TRSDefWrapper(bytes(def_data))
                    def_name = Path(name).stem
                    def_dir = lod_dir / def_name
                    def_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Map TypeOfDef to string for duration logic
                    type_map = {0x42: '2', 0x44: '4', 0x49: '9'}
                    def_type = type_map.get(def_wrapper.header.TypeOfDef, 'unknown')
                    
                    # Check if palette replacement is needed
                    replace_palette = needs_palette_255_fix(def_name, archive_path, config.prefer_hota_names)
                    
                    for group_idx, group in enumerate(def_wrapper.groups):
                        if group.ItemsCount == 0:
                            continue
                        
                        # Get object name for filename prefix
                        obj_name = get_name(def_name, archive_path, config.prefer_hota_names)
                        filename_prefix = obj_name if obj_name else def_name
                        
                        # Get group name
                        if len(def_wrapper.groups) == 1:
                            webp_name = f'{filename_prefix}.webp'
                        else:
                            creature_name = obj_name if obj_name else ''
                            group_name = get_group_name(group.GroupNum, def_wrapper.header.TypeOfDef, creature_name)
                            if group_name.startswith('Group '):
                                webp_name = f'{filename_prefix}_{group.GroupNum}.webp'
                            else:
                                webp_name = f'{filename_prefix} {group_name}.webp'
                        
                        # Extract frames
                        frames_data = []
                        for pic_idx in range(group.ItemsCount):
                            try:
                                img, shadow = def_wrapper.extract_bmp(group_idx, pic_idx, bmp_spec=not config.shadow_in_main)
                                
                                # Process both images
                                palette = def_wrapper.def_palette
                                if palette and len(palette) > 7:
                                    # Get shadow colors from palette
                                    transparent = palette[0]
                                    edge = palette[1]
                                    body_two = palette[2]
                                    edge_two = palette[3]
                                    body = palette[4]
                                    selection = palette[5]
                                    body_sel = palette[6]
                                    edge_sel = palette[7]
                                    
                                    # Process main image
                                    if img.mode == 'P':
                                        img = img.convert('RGBA')
                                    
                                    img_data = img.load()
                                    w, h = img.size
                                    for y in range(h):
                                        for x in range(w):
                                            pixel = img_data[x, y][:3]
                                            if pixel == transparent:
                                                img_data[x, y] = (0, 0, 0, 0)
                                    
                                    # Process shadow image
                                    if shadow and shadow.mode == 'P':
                                        shadow = shadow.convert('RGBA')
                                        shadow_data = shadow.load()
                                    else:
                                        shadow_data = None
                                    
                                    if config.shadow_in_main:
                                        # Process main image as if it contains shadows
                                        keep_sel = keeps_selection_palette(def_name)
                                        for y in range(h):
                                            for x in range(w):
                                                pixel = img_data[x, y][:3]
                                                if pixel == transparent or (pixel == selection and not keep_sel):
                                                    img_data[x, y] = (0, 0, 0, 0)
                                                elif pixel == edge or pixel == edge_sel or (pixel == edge_two and uses_hota_shadow_p2p3(def_name, archive_path, config.prefer_hota_names)):
                                                    img_data[x, y] = (0, 0, 0, 127)
                                                elif pixel == body or pixel == body_sel or (pixel == body_two and uses_hota_shadow_p2p3(def_name, archive_path, config.prefer_hota_names)):
                                                    img_data[x, y] = (0, 0, 0, 191)
                                    elif shadow_data:
                                        for y in range(h):
                                            for x in range(w):
                                                pixel = shadow_data[x, y][:3]
                                                keep_sel = keeps_selection_palette(def_name)
                                                if pixel == transparent or (pixel == selection and not keep_sel):
                                                    shadow_data[x, y] = (0, 0, 0, 0)
                                                elif pixel == edge or pixel == edge_sel or (pixel == edge_two and uses_hota_shadow_p2p3(def_name, archive_path, config.prefer_hota_names)):
                                                    shadow_data[x, y] = (0, 0, 0, 127)
                                                elif pixel == body or pixel == body_sel or (pixel == body_two and uses_hota_shadow_p2p3(def_name, archive_path, config.prefer_hota_names)):
                                                    shadow_data[x, y] = (0, 0, 0, 191)
                                                else:
                                                    shadow_data[x, y] = (0, 0, 0, 0)
                                        
                                        img = Image.alpha_composite(shadow, img)
                                else:
                                    if img.mode == 'P':
                                        img = img.convert('RGBA')
                                
                                # Apply palette replacement if needed
                                if replace_palette:
                                    palette = def_wrapper.def_palette
                                    if palette and len(palette) > 255:
                                        color_255 = palette[255]
                                        color_5 = palette[5]
                                        img_data = img.load()
                                        for y in range(img.size[1]):
                                            for x in range(img.size[0]):
                                                if img_data[x, y][:3] == color_255:
                                                    img_data[x, y] = color_5 + (img_data[x, y][3],)
                                
                                frames_data.append({'image': img, 'name': def_wrapper.get_pic_name(group_idx, pic_idx)})
                            except Exception as e:
                                print(f'Error extracting frame {pic_idx} from group {group_idx} in {name}: {e}')
                        
                        if frames_data:
                            process_webp_group(def_name, def_type, group.GroupNum, len(def_wrapper.groups), frames_data, archive_path, def_dir, config)
                
                except Exception as e:
                    print(f'Error processing {name}: {e}')
            
            if def_count == 0:
                print('No DEF files found in archive')
            else:
                print(f'WebP extraction complete: {def_count} DEF files processed')
    
    except ERSLodException as e:
        print(f'Error: {e}')
        return 1
    return 0


def extract_def_tool(archive_path, output_path, config):
    """Extract DEF files for DefTool"""
    try:
        if Path(archive_path).suffix.lower() == '.def':
            print(f'Extracting DEF file for DefTool to: {output_path}')
            Path(output_path).mkdir(parents=True, exist_ok=True)
            
            try:
                with open(archive_path, 'rb') as f:
                    def_data = f.read()
                
                def_wrapper = TRSDefWrapper(def_data)
                output_file = Path(output_path) / Path(archive_path).with_suffix('.hdl').name
                def_wrapper.extract_def_tool_list(str(output_file), config.extract_with_shadow, config.extract_in_24_bits)
                print(f'Extracted DEF: {Path(archive_path).name}')
            except Exception as e:
                print(f'Error extracting DEF file: {e}')
                return 1
        else:
            archive = rs_load_mm_archive(archive_path)
            archive.files.ignore_unzip_errors = config.ignore_unzip_errors
            
            print(f'Archive loaded: {archive.count} files found')
            if archive.count == 0:
                print('Warning: No files found in archive')
                return 0
            
            print(f'Extracting DEF files for DefTool to: {output_path}')
            Path(output_path).mkdir(parents=True, exist_ok=True)
            
            def_count = 0
            for i in range(archive.count):
                name = archive.get_file_name(i)
                name = name.rstrip('\x00')  # Remove null terminators
                print(f'Found file: {name}')
                if Path(name).suffix.lower() != '.def':
                    continue
                
                def_count += 1
                try:
                    extract_dir = Path(output_path) / Path(name).stem
                    extract_dir.mkdir(parents=True, exist_ok=True)
                    
                    def_data = archive.extract_array(i)
                    def_wrapper = TRSDefWrapper(bytes(def_data))
                    output_file = extract_dir / Path(name).with_suffix('.hdl').name
                    def_wrapper.extract_def_tool_list(str(output_file), config.extract_with_shadow, config.extract_in_24_bits)
                    print(f'Extracted DEF: {name}')
                except Exception as e:
                    print(f'Error extracting {name}: {e}')
            
            if def_count == 0:
                print('No DEF files found in archive')
            print('DEF extraction complete.')
    except ERSLodException as e:
        print(f'Error: {e}')
        return 1
    return 0


def main():
    """Main entry point"""
    cmd, archive, output, target, file_filter, config = parse_args()
    
    if cmd == 'help':
        show_help()
        return 0
    
    if cmd == 'version':
        print(f'MMArchive CLI Version {CLI_VERSION}')
        print('Based on MMArchive by GrayFace')
        return 0
    
    if not Path(archive).exists():
        print(f'Archive not found: {archive}')
        return 1
    
    if cmd == 'list':
        return list_archive(archive, config)
    elif cmd == 'extract':
        return extract_archive(archive, output, file_filter, config)
    elif cmd == 'add':
        return add_to_archive(archive, target, config)
    elif cmd == 'extractdef':
        return extract_def_tool(archive, output, config)
    elif cmd == 'extractwebp':
        return extract_webp(archive, output, config)
    elif cmd == 'testdef':
        return test_def_files(archive, config)
    
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        print(f'Unexpected error: {e}')
        sys.exit(1)
