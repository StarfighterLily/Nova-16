# Phase 4: Tools & Documentation Tasks

## Overview
Update supporting tools and docs. The endpoint is a complete migration toolkit and updated documentation.

## Detailed Steps
1. **Update docs/**
   - Add new instruction format guide to `docs/`.
   - Document mode byte encoding and examples.
   - Update CPU spec and opcode references.
   - Output: Comprehensive docs for new system.

2. **Modify Graphics/Sound Tools**
   - Check if tools like `nova_graphics_monitor.py` are affected by instruction changes.
   - Update any binary parsing if needed.
   - Test with new binaries.
   - Output: Compatible tools.

3. **Create Migration Script**
   - Write a script to convert legacy .bin to new format.
   - Handle opcode mapping and mode insertion.
   - Test on sample binaries.
   - Output: Migration tool (e.g., `migrate_bin.py`).

4. **Write Unit Tests**
   - Add tests for decoder logic in nova_cpu.py.
   - Cover mode parsing, operand fetching, and edge cases.
   - Integrate with existing test framework.
   - Output: Test suite with >90% coverage.

## Risk Mitigation
- Backup original docs/ before updates.
- Test migration script on copies of binaries.

## Timeline
1-2 days.

## Endpoint Verification
- Docs/ fully updated.
- Tools work with new binaries.
- Migration script converts legacy files.
- Unit tests pass.