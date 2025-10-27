# Development Guidelines

## Code Quality Standards

### Documentation Patterns
- **Comprehensive Module Headers**: Every module includes detailed copyright information, author contact, and purpose description
- **Docstring Format**: Use triple-quoted strings with clear descriptions for classes and methods
- **Inline Comments**: Provide explanatory comments for complex algorithms and binary operations
- **Type Annotations**: Extensive use of typing module for function parameters and return values

### Naming Conventions
- **Class Names**: Use PascalCase with descriptive prefixes (e.g., `TRSDefWrapper`, `TRSXForm`, `TRSMMFiles`)
- **Method Names**: Use snake_case for methods and functions (e.g., `get_pic_header`, `extract_bmp`, `rebuild_pal`)
- **Constants**: Use UPPER_CASE for module-level constants (e.g., `HEROES_ID`, `VID_SIZE_SIG_OLD`)
- **Private Methods**: Prefix with underscore for internal methods (e.g., `_parse_header`, `_extract_buffer`)

### Error Handling
- **Custom Exceptions**: Define specific exception classes inheriting from base exceptions (e.g., `ERSDefException`, `ERSLodException`)
- **Resource Strings**: Use constants for error messages (e.g., `S_RS_INVALID_DEF`, `S_RS_LOD_CORRUPT`)
- **Graceful Degradation**: Handle missing dependencies with try/except blocks and informative error messages

## Structural Conventions

### Class Organization
- **Dataclasses**: Use `@dataclass` decorator for simple data containers (e.g., `TRSDefHeader`, `TMMLodFile`)
- **Property Methods**: Implement properties for computed values and data access (e.g., `@property def pictures_count`)
- **Method Grouping**: Organize methods logically with public interface methods first, then private helpers

### File I/O Patterns
- **Context Management**: Use proper file handling with try/finally blocks for resource cleanup
- **Stream Abstraction**: Accept `BinaryIO` parameters for flexible input/output handling
- **Buffer Management**: Implement efficient memory management for large binary data processing

### Binary Data Handling
- **Struct Module**: Use `struct.pack/unpack` for binary data serialization with explicit endianness (`<` for little-endian)
- **Byte Operations**: Handle raw bytes and bytearray objects for binary file manipulation
- **Offset Calculations**: Use clear arithmetic for file offset and size calculations

## Semantic Patterns

### Factory Methods and Builders
- **Wrapper Classes**: Create wrapper classes for complex file format handling (e.g., `TRSDefWrapper` for DEF files)
- **Builder Pattern**: Use incremental construction for complex objects (e.g., `TRSDefMaker` for creating DEF files)
- **Options Objects**: Use configuration objects for customizable behavior (e.g., `TRSMMFilesOptions`)

### Polymorphic Method Design
- **Overloaded Methods**: Support multiple parameter signatures for flexibility (e.g., `extract_bmp(*args)` accepting different argument patterns)
- **Optional Parameters**: Use default values and None checks for optional functionality
- **Special Constants**: Define sentinel objects for special behavior modes (e.g., `RSFullBmp = object()`)

### Image Processing Integration
- **PIL Integration**: Seamless integration with Pillow library for image operations
- **Format Conversion**: Support multiple image formats with automatic conversion
- **Palette Management**: Handle indexed color images with custom palette operations

## Internal API Usage Patterns

### File Format Processing
```python
# Standard pattern for binary file parsing
def _parse_header(self):
    if len(self.data) < expected_size:
        raise CustomException(error_message)
    
    values = struct.unpack('<format_string', self.data[offset:offset+size])
    self.header = DataClass(*values)
```

### Resource Management
```python
# Pattern for stream handling
def begin_operation(self) -> BinaryIO:
    # Setup and return stream
    
def end_operation(self, stream: BinaryIO):
    # Cleanup resources
    
# Usage with try/finally
stream = self.begin_operation()
try:
    # Perform operations
finally:
    self.end_operation(stream)
```

### Error Handling with Fallbacks
```python
try:
    from PIL import Image
except ImportError:
    Image = None

def method_requiring_pil(self):
    if Image is None:
        raise ImportError("PIL/Pillow required")
```

## Frequently Used Code Idioms

### Binary Data Validation
```python
if offset + size > len(self.data):
    raise ERSException(S_INVALID_FORMAT)
```

### Conditional Resource Initialization
```python
if self._cached_data is None:
    self._initialize_cached_data()
```

### Flexible Parameter Handling
```python
def method(self, *args, **kwargs):
    if len(args) == 1:
        # Handle single parameter case
    else:
        # Handle multiple parameter case
```

### Buffer Operations with Bounds Checking
```python
for i in range(min(length, available_space)):
    if offset + i < len(buffer):
        buffer[offset + i] = value
```

## Popular Annotations and Decorators

### Type Hints
- `Optional[Type]` for nullable values
- `List[Type]` for homogeneous collections  
- `Union[Type1, Type2]` for multiple possible types
- `BinaryIO` for file-like objects
- `Callable` for function parameters

### Dataclass Usage
```python
@dataclass
class DataStructure:
    field1: int
    field2: bytes
    field3: Optional[str] = None
```

### Property Definitions
```python
@property
def computed_value(self) -> int:
    return self._calculate_value()
```

This codebase demonstrates sophisticated binary file processing with clean separation of concerns, robust error handling, and flexible API design patterns suitable for game asset manipulation tools.