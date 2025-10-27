# Project Structure

## Directory Organization

```
MMArchiveCLI/
├── src/                    # Core source code modules
│   ├── __init__.py        # Package initialization
│   ├── RSDef.py           # DEF file format handler
│   ├── RSDefLod.py        # Combined DEF/LOD operations
│   ├── RSGraphics.py      # Graphics processing utilities
│   ├── RSLod.py           # Core LOD file handler
│   ├── RSLod_complete.py  # Complete LOD processing implementation
│   ├── RSLod_graphics.py  # LOD graphics-specific operations
│   ├── RSLod_integrated.py # Integrated LOD functionality
│   ├── RSLod_part2.py     # Extended LOD operations (part 2)
│   ├── RSLod_part3.py     # Extended LOD operations (part 3)
│   └── RSLod_part4.py     # Extended LOD operations (part 4)
├── MMArchiveCLI.py        # Main command-line interface
├── defConfig.json         # DEF configuration settings
├── objectsByID.json       # Object name mappings
├── requirements.txt       # Python dependencies
├── README.md              # Project documentation
├── requirements.txt        # Python dependencies
└── .gitignore             # Git ignore patterns
```

## Core Components and Relationships

### Command-Line Interface
- **MMArchiveCLI.py**: Main entry point providing command-line interface for all operations
- **defConfig.json**: Configuration file containing DEF-specific settings, crop bounds, and HotA fixes
- **objectsByID.json**: Object name mappings for human-readable filenames

### Primary Modules
- **RSLod.py**: Foundation module for LOD file operations, provides base functionality for reading and extracting LOD archives
- **RSDef.py**: Handles DEF animation files, manages frame extraction and sprite processing
- **RSGraphics.py**: Graphics utilities for format conversion and image processing operations

### Extended Functionality
- **RSDefLod.py**: Bridges DEF and LOD operations, enabling combined asset processing workflows
- **RSLod_complete.py**: Comprehensive LOD implementation with full feature set
- **RSLod_graphics.py**: Specialized graphics operations within LOD context
- **RSLod_integrated.py**: Unified interface combining multiple LOD processing approaches

### Modular Extensions
- **RSLod_part2.py - RSLod_part4.py**: Incremental feature additions and specialized operations, likely representing iterative development or feature-specific implementations

## Architectural Patterns

### Modular Design
The project follows a modular architecture where each component handles specific aspects of game asset processing. This allows for:
- Independent development and testing of features
- Flexible combination of functionality
- Easy maintenance and updates

### Incremental Development
The numbered part files (part2-4) suggest an iterative development approach, where functionality is built up progressively while maintaining backward compatibility.

### Separation of Concerns
- File format handling (LOD/DEF) is separated from graphics processing
- Core operations are distinct from extended/specialized features
- Integration modules provide unified interfaces without coupling base components