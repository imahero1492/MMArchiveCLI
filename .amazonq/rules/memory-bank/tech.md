# Technology Stack

## Programming Languages
- **Python**: Primary development language for all modules and utilities
- **Version**: Compatible with Python 3.x (modern Python standards)

## Dependencies and Libraries

### Core Dependencies
- **Pillow (>=9.0.0)**: Essential image processing library for graphics conversion and manipulation
  - Handles format conversions (PCX, BMP, WebP, etc.)
  - Provides image processing capabilities for game assets
  - Enables batch processing of graphics files

### Standard Library Usage
The project leverages Python's standard library for:
- File I/O operations for reading LOD and DEF files
- Binary data processing for game file formats
- Path manipulation and file system operations
- Data structure handling for asset management

## Development Environment

### File Types and Formats
The project processes various game-specific file formats:
- **LOD files**: Library of Data archive format
- **DEF files**: Definition/animation files
- **PCX files**: Graphics format used in Heroes games
- **BMP files**: Standard bitmap format for conversion
- **WebP files**: Modern web-optimized image format

### Build and Execution
- **No build system required**: Pure Python implementation
- **Direct execution**: Modules can be run directly or imported
- **Package structure**: Organized as importable Python package

## Development Commands

### Installation
```bash
pip install -r requirements.txt
```

### Usage
```bash
# Command-line interface
python MMArchiveCLI.py <operation> <archive> [options]

# Example operations
python MMArchiveCLI.py list data.lod
python MMArchiveCLI.py extract sprites.lod -o output
python MMArchiveCLI.py extractwebp creature.def -o webp_output
```

### Library Usage
```python
# Import core modules for programmatic use
from src import RSLod, RSDef, RSGraphics

# Use integrated functionality
from src import RSLod_complete, RSDefLod
```

### Asset Processing
The toolkit handles binary file processing with focus on:
- Memory-efficient file reading
- Format-specific parsing algorithms
- Graphics conversion pipelines
- Batch processing capabilities

## Technical Considerations
- **Binary file handling**: Specialized for game asset formats
- **Memory management**: Efficient processing of large asset archives
- **Cross-platform compatibility**: Pure Python ensures portability
- **Modular architecture**: Enables selective feature usage