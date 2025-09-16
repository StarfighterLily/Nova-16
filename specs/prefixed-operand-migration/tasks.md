# Prefixed Operand Migration Tasks

## Phase 1: Planning & Design
- [ ] Review current opcode table in opcodes.py and identify redundant variants.
- [ ] Finalize mode byte encoding scheme (bits for operand modes).
- [ ] Define core opcode list (reduce from ~200 to ~50).

## Phase 2: Core Implementation
- [ ] Update opcodes.py: Remove variant opcodes, add core operations with mode support.
- [ ] Modify nova_assembler.py: Add mode encoding logic and syntax parsing.
- [ ] Revamp nova_cpu.py: Implement mode byte parsing in instruction decoder.
- [ ] Update nova_disassembler.py: Add mode byte decoding for disassembly.

## Phase 3: Integration & Testing
- [ ] Test assembler with sample programs (e.g., convert asm/simple_test.asm to new format).
- [ ] Debug integration: Use nova_debugger.py to verify mode parsing.
- [ ] Performance benchmarking: Ensure no >5% slowdown in execution.

## Phase 4: Tools & Documentation
- [ ] Update docs/: Add new instruction format guide.
- [ ] Modify graphics/sound tools if instruction changes affect them.
- [ ] Create migration script: Convert legacy .bin to new format.
- [ ] Write unit tests for decoder logic.

## Phase 5: Validation & Release
- [ ] Full test suite: Run all asm/ programs in both modes.
- [ ] User acceptance: Validate with complex programs (e.g., starfield.asm).
- [ ] Documentation review: Ensure docs/ covers new system.
- [ ] Release notes: Document changes and migration path.

## Risk Mitigation
- [ ] Backup current codebase before changes.
- [ ] Incremental commits: Test after each major update.

## Timeline Estimate
- Phase 1: 1-2 days
- Phase 2: 3-5 days
- Phase 3: 2-3 days
- Phase 4: 1-2 days
- Phase 5: 1 day

Total: ~1-2 weeks for full migration.