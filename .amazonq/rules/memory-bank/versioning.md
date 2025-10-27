# Version Management Guidelines

## CLI Version Updates

### When to Update Version
- **ALWAYS** update `CLI_VERSION` in `MMArchiveCLI.py` when making any code changes
- Increment patch version (e.g., 1.3.1 → 1.3.2) for bug fixes
- Increment minor version (e.g., 1.3.x → 1.4.0) for new features
- Increment major version (e.g., 1.x.x → 2.0.0) for breaking changes

### Version Format
- Use semantic versioning with `-py` suffix: `MAJOR.MINOR.PATCH-py`
- Current version location: Line ~12 in `MMArchiveCLI.py`
- Example: `CLI_VERSION = '1.3.1-py'`

### Mandatory Process
1. Make code changes
2. **IMMEDIATELY** update `CLI_VERSION` 
3. Test changes
4. Commit both code and version changes together

### Version History Context
- Started at 1.3.0-py (initial Python port)
- 1.3.1-py: Fixed add_to_archive BytesIO stream handling bug

**CRITICAL**: Never commit code changes without updating the version number.