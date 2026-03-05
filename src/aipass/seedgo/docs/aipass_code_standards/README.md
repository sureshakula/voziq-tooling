# CODE_STANDARDS
**Status:** Active - CLI Service Provider Pattern Implemented
**Date:** 2025-11-13 (Updated)
**Last Major Update:** CLI Error Handler Migration Complete

## Purpose

Universal code standards for all AIPass branches. This defines how branches should be structured, how code should be organized, and the patterns all branches follow.

## Structure

Each file in this directory covers a specific aspect of code standards:
- **architecture.md** - Branch structure and layers ✅
- **naming.md** - File and function naming conventions ✅
- **json_structure.md** - Data/state management patterns (three-JSON, logs, registries) ✅
- **cli.md** - CLI design (interactive vs arguments) + Service Provider Pattern ✅
- **error_handling.md** - Error handling service via CLI ✅
- **imports.md** - Import patterns and standards ✅
- **handlers.md** - Handler-specific rules ✅
- **modules.md** - Module-specific rules ✅
- **documentation.md** - Code documentation requirements ✅
- **testing.md** - Testing expectations ✅

## Recent Updates

### CLI Service Provider Pattern (2025-11-13)

**What Changed:**
- CLI branch now provides centralized formatting and error handling services
- Follows Prax pattern: import once, use throughout
- Rich library integration for beautiful console output
- Error handling migrated from Cortex to CLI (eliminated ~10,300 lines duplicate code)

**Service Components:**
1. **Console Service** - Rich Console instance (`from cli.apps.modules import console`)
2. **Display Functions** - header, success, error, warning, section
3. **Operation Templates** - operation_start, operation_complete
4. **Error Handling** - OperationResult, decorators, automatic logging

**Benefits:**
- Consistency across all branches
- Single source of truth for formatting
- Automatic logging integration
- Rich formatting (colors, panels, tables, progress bars)
- Centralized maintenance

**Current Status:**
- CLI service implemented and tested (test_cli_errors.py passing)
- Seed pilot integration complete
- CLI branch self-adoption: 31% (needs error_handler.py and formatters.py migration)
- External adoption: 0 branches (ready for rollout)

**Next Steps:**
- Complete CLI branch self-adoption (100%)
- Choose external pilot branch for adoption
- Create migration guide for remaining branches

## Process

1. ✅ Build skeleton structure (placeholder files)
2. ✅ Fill in detailed content for each section
3. ✅ Implement service provider patterns (CLI + Prax)
4. ⏳ Complete CLI branch self-adoption
5. ⏳ Roll out to external branches
6. ⏳ Create programmatic validation (standards checkers)

## Philosophy

**Understanding WHY > Following HOW**

These standards explain the reasoning behind decisions, not just the rules. When branches read these, they should understand:
- WHY we structure code this way
- WHAT problem each pattern solves
- WHEN to apply (and when not to apply) patterns
- The CONSEQUENCES of not following standards

This enables branches to make good decisions based on understanding, not blindly follow instructions.

## Notes

- These are NOT migration instructions (disposable)
- These ARE permanent reference standards
- Branches read these to understand how to structure themselves
- Standards evolve as system evolves
- Content comes from conversations → extracted and organized into sections
