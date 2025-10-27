# MMArchive Command Line Interface

A Python implementation of MMArchive for working with Heroes of Might and Magic game archives.

## Overview

MMArchiveCLI is a command-line tool that provides complete functionality for reading, extracting, and manipulating LOD (Library of Data) files and DEF (Definition) files used by the Heroes of Might and Magic series.

## Features

- **Archive Operations**: List, extract, and add files to LOD archives
- **DEF Processing**: Extract DEF sprite files for DefTool compatibility
- **WebP Export**: Convert DEF animations to WebP format with transparency and shadows
- **HDL Structure Support**: Process HDL files with separate BMP frames
- **Multiple Formats**: Supports Heroes, MM6, MM7, MM8 archive formats
- **Batch Operations**: Process multiple files with filters
- **Error Handling**: Configurable error tolerance for corrupted archives
- **HotA Support**: Special handling for HotA mod assets
- **Smart Cropping**: Predefined and dynamic frame cropping
- **Object Name Resolution**: Human-readable filenames from objectsByID.json

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Syntax
```bash
python MMArchiveCLI.py <operation> <archive> [options]
```

### Operations

#### List Files
```bash
python MMArchiveCLI.py list <archive>
```
Lists all files in the specified archive.

#### Extract Files
```bash
python MMArchiveCLI.py extract <archive> [-o output_dir] [-f filter]
```
Extracts files from archive to specified directory.

#### Add Files
```bash
python MMArchiveCLI.py add <archive> <file>
```
Adds a file to the specified archive.

#### Extract DEF Files
```bash
python MMArchiveCLI.py extractdef <archive|def_file> [-o output_dir]
```
Extracts DEF files for DefTool compatibility.

#### Extract DEF Files as WebP
```bash
python MMArchiveCLI.py extractwebp <archive|def_file|directory> [-o output_dir]
```
Extracts DEF files as animated WebP files with proper transparency and shadows.

#### Test DEF Files
```bash
python MMArchiveCLI.py testdef <archive|def_file>
```
Tests DEF files without extracting them.

#### Version Information
```bash
python MMArchiveCLI.py version
```
Shows version information.

#### Help
```bash
python MMArchiveCLI.py help
```
Displays help information.

### Options

#### General Options
- `-o <dir>`: Output directory
- `-f <*.ext>`: File filter (e.g., `*.bmp`, `*.def`)
- `--strict-errors`: Fail on unpacking errors (default: ignore)

#### DEF Extraction Options (extractdef)
- `--no-shadow`: Extract DEF without external shadow
- `--24bits`: Extract DEF in 24 bits

#### WebP Export Options (extractwebp)
- `--no-crop [2,4]`: Disable cropping (default: crop enabled), optionally for specific DEF types
- `--individual-crop`: Use group-based cropping instead of predefined bounds
- `--hota`: Prefer HotA names from objectsByID.json
- `--hdl-structure`: Read from HDL and BMP files instead of DEF (requires directory path)
- `--shadow-in-main`: Process main frames as if they contain shadows (ignores shadow files)

## Examples

### List Archive Contents
```bash
python MMArchiveCLI.py list data.lod
```

### Extract All Files
```bash
python MMArchiveCLI.py extract sprites.lod -o extracted_sprites
```

### Extract Specific File Types
```bash
python MMArchiveCLI.py extract bitmaps.lod -o images -f *.bmp
python MMArchiveCLI.py extract data.lod -o definitions -f *.def
```

### Add File to Archive
```bash
python MMArchiveCLI.py add custom.lod newsprite.def
```

### Extract DEF Files for DefTool
```bash
# From LOD archive with default settings
python MMArchiveCLI.py extractdef sprites.lod -o deftool_output

# Single DEF file without shadow, in 24-bit mode
python MMArchiveCLI.py extractdef creature.def -o deftool_output --no-shadow --24bits

# With strict error handling
python MMArchiveCLI.py extractdef sprites.lod -o output --strict-errors
```

### Extract DEF Files as Animated WebP
```bash
# Extract with default predefined crop bounds
python MMArchiveCLI.py extractwebp sprites.lod -o webp_output

# Extract single DEF file
python MMArchiveCLI.py extractwebp creature.def -o webp_output

# Extract without any cropping
python MMArchiveCLI.py extractwebp creature.def -o webp_output --no-crop

# Extract with cropping disabled only for DEF types 2 and 4
python MMArchiveCLI.py extractwebp sprites.lod -o webp_output --no-crop 2,4

# Extract using group-based cropping instead of predefined bounds
python MMArchiveCLI.py extractwebp sprites.lod -o webp_output --individual-crop

# Extract with HotA mode enabled (uses HotA names and applies fixes)
python MMArchiveCLI.py extractwebp HotA_sprites.lod -o webp_output --hota

# Extract from HDL structure (directory with HDL and BMP files)
python MMArchiveCLI.py extractwebp hdl_directory -o webp_output --hdl-structure

# Process main frames as containing shadows (ignore shadow files)
python MMArchiveCLI.py extractwebp sprites.lod -o webp_output --shadow-in-main
```

### Test DEF Files
```bash
# Test all DEF files in archive
python MMArchiveCLI.py testdef sprites.lod

# Test single DEF file
python MMArchiveCLI.py testdef creature.def
```

## Configuration Files

The tool uses two JSON configuration files:

### defConfig.json
Contains DEF-specific configuration:
- **cropBounds**: Predefined crop bounds for DEF types (4, 4Airship, 4Boat, 9)
- **hotaShadowP2P3**: Objects using HotA palette 2/3 for shadow
- **hotaPalette255To5**: Objects needing palette 255→5 replacement
- **keepSelectionPalette**: Objects that keep selection palette
- **creaturesWithAttack2**: Creatures with secondary attack animation
- **creaturesWithCast**: Creatures with cast animation
- **creatureGroupNames**: Group names for creature DEF (type 0x42)
- **mapObjectGroupNames**: Group names for map object DEF (type 0x44)
- **heroGroupNames**: Group names for hero DEF (type 0x49)

### objectsByID.json
Maps DEF IDs to human-readable names with HotA support.

## WebP Export Features

### Cropping System
The WebP extraction uses a hierarchical cropping system:

1. **Default Behavior**: Uses predefined crop bounds from defConfig.json:
   - Type 4: (15, 3, 77, 64) - Standard map objects
   - Type 4 Airship: (0, 0, 85, 127) - Flying units with "Airship" in name
   - Type 4 Boat: (4, 0, 92, 64) - Water units with "Boat" in name
   - Type 9: (23, 29, 108, 149) - Heroes

2. **Individual Cropping** (`--individual-crop`): Calculates crop bounds per animation group based on actual frame content

3. **No Cropping** (`--no-crop`): Disables all cropping, preserving original frame dimensions

4. **Selective No Cropping** (`--no-crop 2,4`): Disables cropping only for specified DEF types

### Shadow Processing
- **Standard Mode**: Processes separate shadow frames with palette-based transparency
  - Palette 0 (transparent) → fully transparent
  - Palette 1, 7 (edge) → semi-transparent black (alpha 127)
  - Palette 4, 6 (body) → semi-transparent black (alpha 191)
  - Palette 5 (selection) → transparent (unless in keepSelectionPalette)
  - HotA P2P3 fix: Uses palette 2/3 for shadow on specific objects

- **Shadow-in-Main Mode** (`--shadow-in-main`): Processes main frames as containing shadows
  - Ignores separate shadow files
  - Applies shadow palette logic to main image

### HDL Structure Mode
- Reads HDL files with frame and shadow paths
- Loads BMP files from directory
- Supports all standard WebP features (cropping, HotA fixes, etc.)
- Parses DEF type from HDL file for proper group naming and durations

### Special Case: AVWccoat (Couatl Adventure Map)
The AVWccoat DEF file from HotA.lod (as of 1.7.3) has shadows embedded in the main frames and requires special processing:

1. Extract the DEF file from HotA.lod with `extract`
2. Extract the DEF with `extractdef` to create HDL and BMP files
3. Remove the bmp files from the main folder (ignore Shadow folder)
4. Replace the extracted BMP files with the individual PCX/BMP files from HotA.lod
5. Open the HDL file in a text editor and verify the Group lines list the correct BMP filenames
6. Use `extractwebp` with `--hdl-structure` and `--shadow-in-main` flags

Example:
```bash
# Extract DEF from archive
python MMArchiveCLI.py extract HotA.lod -o temp -f AVWccoat.def

# Extract DEF to HDL structure
python MMArchiveCLI.py extractdef temp/AVWccoat.def -o hdl_output

# Remove the extracted BMP files from main folder (Shadow folder should be ignored)
del hdl_output/AVWccoat/*.bmp

# Extract pcx from archive to bmp files
python MMArchiveCLI.py extract HotA.lod -o temp -f AVWctl*.pcx

# Copy bmp files to HDL directory
copy temp/AVWctl*.bmp hdl_output/AVWccoat/

# Edit hdl_output/AVWccoat/AVWccoat.hdl to verify bmp files match (probably need find/replace all)

# Extract as WebP with shadow-in-main mode
python MMArchiveCLI.py extractwebp hdl_output/AVWccoat -o webp_output --hdl-structure --shadow-in-main
```

## Supported File Formats

### Archive Types
- **LOD**: Heroes of Might and Magic archive format
- **SND**: Sound archives
- **VID**: Video archives
- **LWD**: Transparent bitmap archives

### Content Types
- **DEF**: Sprite definition files
- **BMP**: Bitmap images
- **PCX**: PCX images
- **WAV**: Sound files
- **SMK**: Video files
- **HDL**: DefTool list files

## Error Handling

The tool provides robust error handling:
- Invalid archive detection
- Corrupted file recovery (default: ignore and continue)
- Missing file warnings
- Decompression error tolerance (configurable with `--strict-errors`)

By default, the tool ignores unpacking errors and continues processing. Use `--strict-errors` to fail on any error.

## HotA Support

The tool includes special support for Heroes of Might and Magic III: Horn of the Abyss (HotA) mod:

### Object Name Integration
- Reads `objectsByID.json` to get human-readable names for DEF files
- WebP files are named using object names instead of DEF IDs (e.g., "Angel Moving.webp" instead of "cavgel Moving.webp")
- Supports both standard and HotA-specific names
- Automatically detects special unit types (Airship, Boat) for proper cropping

### HotA Mode (`--hota` flag)
When enabled:
- **Name Preference**: Prefers HotA names over standard names from objectsByID.json
- **Shadow Fixes**: Applies P2P3 shadow palette fixes for specific HotA objects (from defConfig.json)
- **Background Fixes**: Applies palette 255→5 replacement for specific HotA objects (from defConfig.json)

### Automatic HotA Detection
The tool automatically detects HotA archives by checking for "HotA" in the archive path and applies appropriate fixes without requiring the `--hota` flag.

### Special Animation Detection
- Distinguishes between "Attack 2" and "Cast" animations for creature combat (Type 0x42 DEF)
- Uses creature names from objectsByID.json to determine correct animation labels
- Supports HotA-specific creatures and animations
- Group names 17-19 are dynamically renamed based on creature type

## Version Information

- **Based on**: MMArchive by GrayFace
- **Language**: Python 3.x
- **Dependencies**: Pillow >= 9.0.0
- **Configuration**: defConfig.json (required), objectsByID.json (optional)

## Technical Details

### Archive Structure Support
- Heroes format archives (LOD, SND, VID)
- MM6/MM7/MM8 format archives
- Compressed and uncompressed files
- Multiple palette support for sprites
- HotA mod archives with special shadow and palette handling
- HDL structure with separate BMP files

### Name Resolution
- Reads objectsByID.json for human-readable names
- Supports both standard Heroes III and HotA naming
- Fallback to DEF filename if name not found
- Group names from defConfig.json for proper animation labeling

### Frame Duration Calculation
- Type-specific durations (heroes, creatures, map objects)
- Special handling for standing animations
- Configurable per group and frame index

### Performance Features
- Lazy loading for large archives
- Streaming decompression
- Memory-efficient processing
- Batch operation optimization
- Configuration caching

## Troubleshooting

### Common Issues

**"Archive not found"**
- Verify file path is correct
- Check file permissions

**"Error: File invalid or corrupt"**
- Archive may be damaged
- Try with default settings (errors ignored) or use `--strict-errors` to see specific errors

**"PIL/Pillow required"**
- Install Pillow: `pip install Pillow>=9.0.0`

**Import errors**
- Ensure all source files are present in `src/` directory
- Check Python path configuration

**"No HDL files found"**
- Ensure `--hdl-structure` is used with a directory path
- Check that directory contains .hdl files

**Shadow not appearing correctly in WebP**
- Some HotA DEF files have shadows embedded in main frames
- Use `--shadow-in-main` flag for these files
- See "Special Case: HotA DEF Files with Embedded Shadows" section

### Debug Mode
Use `--strict-errors` flag to see detailed error messages for debugging problematic archives.

## Development

### Project Structure
```
MMArchiveCLI/
├── src/                    # Core library modules
├── MMArchiveCLI.py        # Command-line interface
├── defConfig.json         # DEF configuration
├── objectsByID.json       # Object name mappings
├── requirements.txt       # Dependencies
└── README.md              # Documentation
```

### Contributing
When modifying the code:
1. Update version number in `CLI_VERSION`
2. Update this README if functionality changes
3. Update defConfig.json if adding new constants
4. Test with sample archives
5. Update flag documentation if options are added
