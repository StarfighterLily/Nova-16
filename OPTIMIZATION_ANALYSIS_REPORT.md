
# Nova-16 System Optimization Analysis Report

## Executive Summary

This report analyzes the Nova-16 emulator system for optimization opportunities in three key areas:
1. **Performance Optimizations** - CPU hot-path, memory access, graphics rendering
2. **Batching Opportunities** - Coalescing operations to reduce overhead
3. **Caching Strategies** - Eliminating redundant computations and memory accesses

The analysis reveals a mature system with substantial optimizations already implemented through a phased reimplantation strategy (Phases 1-6). However, several opportunities remain for further performance gains.

---

## 1. CPU Core Optimizations (nova_cpu.py)

### Current Optimizations

**✅ Pre-computed Register Lookup Table**
- `_register_lookup` table provides O(1) opcode-to-register resolution
- Eliminates if/elif chains during operand decoding

**✅ Parity Table Pre-computation**
- `_parity_table` provides O(1) parity flag calculation
- Avoids bit-counting loops during every flag update

**✅ Interrupt Check Batching**
- `interrupt_check_frequency = 8` reduces interrupt polling overhead
- `has_pending_interrupt_sources` fast-gate avoids unnecessary scans
- `last_interrupt_state` cache detects state changes

**✅ Profiling Infrastructure**
- Built-in cycle counting and instruction profiling
- Memory access counting via `profile_data['memory_accesses']`

**✅ No-Operand Instruction Fast Path**
- `NO_OPERAND_OPCODES` set identifies instructions that skip operand parsing
- Significant cycle savings for common control-flow instructions (HLT, RET, NOP, CLI, STI, PUSHF, POPF, PUSHA, POPA)

### Remaining Optimization Opportunities

**⚠️ Instruction Fetch Overhead**
- `fetch_opcode()` uses simple dict cache (64 entries)
- Sequential instruction fetch is **already optimized** via PC-delta tracking bypass
- LRU eviction now handles non-sequential hot addresses efficiently

**⚠️ Operand Value Resolution**
- `_resolve_operands()` in `core/exec.py` creates per-instruction dispatch lookups
- **Issue**: Redundant register file lookup for frequently-accessed operands
- **Recommendation**: Consider operand value caching for hot loops

**⚠️ Flag Setting Indirection**
- Multiple flag-setting methods: `_set_flags_8bit`, `_set_flags_16bit`, `_set_flags_8bit_bcd`, `_set_flags_16bit_bcd`
- Each has condition checks for CMP operations
- **Recommendation**: Consolidate into unified `set_from_operation()` method (already exists in `Flags` class)

---

## 2. Memory System Optimizations (nova/memory/memory.py)

### Current Optimizations

**✅ Single Hot-Region View**
- `_hot = self.memory[0:self.HOT_END]` is a numpy view (zero-copy)
- Covers zero page (0x0000-0x00FF) and interrupt vectors (0x0100-0x011F)
- Eliminates separate cache arrays and synchronization logic

**✅ Fast-Path Memory Access**
- `read_byte_fast()`, `write_byte_fast()`, `read_word_fast()`, `write_word_fast()`
- Skip bounds checking for trusted internal calls

**✅ LRU Instruction Cache**
- Implemented using `OrderedDict` for O(1) LRU eviction
- Sequential fetch bypass avoids cache overhead for linear code
- LRU keeps frequently-jumped-to addresses cached (loops, interrupt vectors)

**✅ Binary Load Vectorized**
- `np.frombuffer()` and array assignment for bulk loads
- Avoids per-byte Python loop overhead

**✅ ORG Segment Loading**
- `load_with_org_info()` supports multi-segment programs
- Uses numpy vectorized operations

### Remaining Optimization Opportunities

**⚠️ SCB Event Publishing Overhead**
- Each write to 0xF000-0xF0FF publishes individual bus events
- Address range 0xF000-0xF100 has 256 addresses, 16 sprites
- **Recommendation**: Batch SCB writes or use dirty range tracking

**⚠️ Memory Read/Write API Redundancy**
- Multiple methods: `read()`, `read_byte()`, `read_bytes_direct()`, `read_word()`, and fast variants
- **Recommendation**: Consolidate to fewer entry points, use fast variants internally

**⚠️ Missing Bulk Memory Operations in Fast Path**
- No `memcpy`-style vectorized bulk copy in fast path
- **Recommendation**: Add `copy_bytes_fast(dst, src, count)` for large transfers

---

## 3. Graphics System Optimizations (nova/graphics/)

### Current Optimizations

**✅ Layer Compositor Dirty Tracking**
- Per-layer `dirty` flags in `Compositor`
- `_pixel_counts` tracking avoids `np.any()` scans on 256x256 buffers
- Only re-composite changed layers

**✅ Blitter Batching**
- `graphics_batch_counter` and `graphics_batch_frequency = 4`
- Coalesces VRAM-to-screen transfers

**✅ Blend Fast Path**
- `blend_enabled` cached boolean avoids per-pixel blend mode checks
- Normal blend mode (0) + full alpha (255) takes direct assignment path

**✅ Numpy Array Operations**
- All graphics operations use numpy vectorized operations
- `np.rot90()`, `np.flip()`, `np.roll()` leverage optimized C implementations

**✅ Sprite Engine Event Subscription**
- Subscribes to `memory.scb_written` for automatic layer marking
- Eliminates explicit sprite update calls

### Remaining Optimization Opportunities

**⚠️ Per-Pixel Operations Not Fully Vectorized**
- `_set_pixel_fast()` and `_set_pixel_to_layer()` have if/elif chains for layer selection
- Called per-pixel in some paths (e.g., `draw_line`, `draw_rectangle`)

**⚠️ Pixel Count Tracking Overhead**
- `update_pixel_count()` called for every pixel change
- **Recommendation**: Batch pixel count updates after bulk operations

**⚠️ Sprite Blitting Pixel Loop**
- Transparency-enabled sprite blitting uses Python loop:
```python
for dy in range(dst_y_start, dst_y_end):
    for dx in range(dst_x_start, dst_x_end):
        ...
```
- **Recommendation**: Use numpy boolean indexing for vectorized transparency

**⚠️ VRAM Transfer Immediate Execution**
- `vram_to_screen()` calls `_copy_vram_to_screen()` immediately if batch threshold not met
- **Issue**: May trigger unnecessary composites
- **Recommendation**: Defer composite until actual screen read needed

**⚠️ Mouse Cursor Masking**
- Uses `np.any(mask)` check in `_composite_mouse_cursor()`
- **Recommendation**: Cache mouse cursor raster or use precomputed mask

---

## 4. Sound System Optimizations (nova_sound.py)

### Current Optimizations

**✅ Pre-generated Waveform Tables**
- `_generate_waveform_tables()` creates 1024-sample lookup tables
- Avoids runtime `np.sin()` calculations

**✅ Cache-Friendly Interpolation**
- Linear interpolation between table samples in `_generate_waveform_sample()`

**✅ Register-Based Sound Control**
- Sound registers (SA, SF, SV, SW) decoupled from CPU
- Can be accessed without CPU involvement

### Remaining Optimization Opportunities

**⚠️ Memory-Based Sample Loading**
- `_load_sample_from_memory()` has Python loop:
```python
for i in range(min(samples_needed, 1024)):
    addr = (self.SA + i) & 0xFFFF
    sample_byte = self.memory.read_byte(addr)
```
- **Recommendation**: Use vectorized read for bulk sample loading

**⚠️ Pink Noise Generation**
- Uses iterative loop for 1/f filtering
- **Recommendation**: Pre-compute pink noise table or use numpy filtering

**⚠️ Per-Sample Array Allocation**
- Each `_generate_waveform_sample()` creates new numpy array
- **Recommendation**: Reuse pre-allocated buffer or pool

**⚠️ Stereo Duplication**
- Manual stacking for stereo output:
```python
stereo_data = np.column_stack((sample_data, sample_data))
```
- **Recommendation**: Could be done during playback with mono buffer

---

## 5. Assembler Optimizations (nova_assembler.py)

### Current Optimizations

**✅ 2-Pass Assembly**
- Separates symbol resolution from code generation
- Supports forward references

**✅ Include Expansion**
- Recursive include resolution with circular include detection

**✅ Macro Preprocessing**
- Two-pass macro collection and expansion
- Parameter substitution with word-boundary matching

**✅ Instruction Set Caching**
- `InstructionSet` caches opcode/register mappings at construction

### Remaining Optimization Opportunities

**⚠️ Repeated Regex Compilation**
- Patterns compiled per-instance in `Parser`, `OperandClassifier`, `CodeGenerator`
- **Recommendation**: Make patterns class-level constants or use `re.compile` module cache

**⚠️ String Literal Parsing**
- `_parse_string_literal()` has character-by-character loop
- **Recommendation**: Use `ord()` on list comprehension or bytes conversion

**⚠️ Error Accumulation Overhead**
- `self.errors.append()` for each error during assembly
- **Recommendation**: Consider fail-fast mode for development

**⚠️ Symbol Table as Dict**
- Linear search in symbol table for EQU resolution
- **Recommendation**: Consider ordered symbol handling for deterministic output

---

## 6. Event Bus Optimizations (nova/bus/eventbus.py)

### Current Optimizations

**✅ Simple Synchronous Dispatch**
- No async overhead, direct callback invocation
- Efficient for in-thread communication

**✅ One-Shot Subscriptions**
- `subscribe_once()` for single-use handlers without removal overhead

### Remaining Optimization Opportunities

**⚠️ Callback List Re-allocation**
- `defaultdict(list)` grows dynamically
- **Recommendation**: Pre-size subscriber lists for known event types

**⚠️ No Event Prioritization**
- All subscribers called in registration order
- **Recommendation**: Consider priority ordering for critical events (timer, interrupt)

**⚠️ Missing Event Buffering**
- For high-frequency events (e.g., per-cycle `cpu.tick`), immediate dispatch overhead
- **Recommendation**: Consider event coalescing or deferred dispatch

---

## 7. Register File Optimizations (core/regfile.py)

### Current Optimizations

**✅ O(1) Dispatch Tables**
- `_get_dispatchers` and `_set_dispatchers` dict-based dispatch
- Replaces if/elif chains

**✅ External Register Decoupling**
- Getter/setter callbacks keep register file independent of peripherals
- No direct references to sound, mouse, timer modules

### Remaining Optimization Opportunities

**⚠️ List-Based P Registers**
- Uses `list` instead of `array('H')` for backward compatibility
- **Issue**: Bounds checking on every set
- **Recommendation**: Could benefit from `numpy` or `array` with view compatibility

**⚠️ Reset All Inefficient**
- `reset_all()` switches from list to array, breaking type consistency
- **Recommendation**: Keep consistent data structure type

---

## 8. Flags Optimizations (core/flags.py)

### Current Optimizations

**✅ Bitfield Operations**
- Single `_bits: int` field with bitwise operations
- O(1) flag read/write via `__getitem__`/`__setitem__`

**✅ Module-Level Parity Table**
- `PARITY_TABLE` shared across all instances

**✅ Unified Flag Setting**
- `set_from_operation()` handles arithmetic, subtraction, and comparison in one method

### Remaining Optimization Opportunities

**⚠️ Property Overhead**
- Individual flag properties (trap_flag, sign_flag, etc.) each call `_bits & (1 << bit)`
- **Recommendation**: Could inline commonly-checked flags (I, Z, C)

---

## 9. Timer Peripheral Optimizations (nova/peripherals/timer.py)

### Current Optimizations

**✅ Event-Driven Ticking**
- Subscribes to `cpu.tick` instead of polling
- No CPU overhead when idle

**✅ Divisor-Based Threshold**
- `_cycle_count` and `_divisor` avoid per-cycle counter updates

**✅ Interrupt Controller Integration**
- Direct sync to `intr_ctrl.set_enable()`

### Remaining Optimization Opportunities

**⚠️ Register Read per Tock**
- `_on_tick()` reads `_divisor` and `_cycle_count` every cycle
- **Recommendation**: Could inline local variable caching

---

## 10. Security Considerations

### Current Security Posture

**✅ Memory Bounds Checking**
- `read_byte()`, `write_byte()` validate addresses
- Prevents out-of-bounds access

**✅ Stack Overflow Protection**
- Interrupt handler checks SP < 0x0124 before push
- IRET/RETN check for sufficient stack data

### Security Recommendations

**⚠️ No Memory Protection Keys**
- No segmentation or memory protection
- 64KB flat address space vulnerable to corruption

**⚠️ No Execution Limits**
- Programs can run indefinitely without timeout
- **Recommendation**: Add cycle limit in headless mode

**⚠️ No Input Sanitization for Networking**
- UART TCP bridge may receive arbitrary data
- **Recommendation**: Add length/buffer size limits

---

## 11. Priority Optimization Targets

| Priority | Component | Opportunity | Effort | Impact |
|----------|-----------|-------------|--------|--------|
| 🔴 P0 | Graphics Sprites | Vectorize transparency blitting | Medium | High |
| 🔴 P0 | Sound | Vectorize sample loading from memory | Low | Medium |
| 🟡 P1 | Graphics Sprites | Cache mouse cursor raster | Low | Medium |
| 🟢 P2 | Memory | LRU cache implemented (was P1) | Done | Medium |
| 🟢 P2 | Assembler | Compile regex patterns once | Low | Low |
| 🟢 P2 | CPU | Skip iCache for sequential fetch (already implemented) | Done | Low |
| 🟢 P2 | Flags | Inline common flag property checks | Low | Low |

---

## 12. Architectural Strengths

The Nova-16 system demonstrates excellent software engineering principles:

1. **Modular Phase-Based Refactoring** - Clear separation of concerns across `core/`, `nova/`, and module level
2. **Event Bus Decoupling** - Eliminates circular dependencies between CPU, memory, peripherals
3. **Numpy Vectorization** - Graphics and memory operations leverage optimized C routines
4. **Object Pooling** - Operand objects reused to reduce GC pressure
5. **Fast/Safe API Split** - Internal operations use fast paths, external use bounds-checked versions

---

## 13. Recommendations Summary

### Immediate Actions (P0)
1. Vectorize sprite transparency blitting using numpy boolean indexing
2. Add vectorized memory read for sound sample loading
3. Consider LRU or NRU for instruction cache instead of FIFO

### Medium-Term Actions (P1)
1. Cache mouse cursor raster operations
2. Consolidate register list/array types in `RegisterFile`
3. Add bulk memory copy operations in fast path
4. Consider inline caching for frequently-accessed operands

### Long-Term Actions (P2)
1. Add JIT compilation path for hot instruction loops
2. Implement memory protection segmentation
3. Add cycle budgeting for untrusted code execution
4. Profile-guided optimization for instruction handler dispatch

---

## Appendix: Code References

| File | Key Optimizations |
|------|-------------------|
| `nova_cpu.py` | Lines 94-108 (register lookup), 877-912 (interrupt batching), 1793-1855 (instruction step) |
| `nova/memory/memory.py` | Lines 54-66 (hot view), 79-86 (fast read), 220-240 (iCache), 128-176 (bulk load) |
| `nova/graphics/blitter.py` | Lines 38-42 (batching state), 171-185 (batch exec), 64-67 (blend cache) |
| `nova/graphics/compositor.py` | Lines 41-42 (pixel counts), 109-114 (visible check) |
| `nova/graphics/sprites.py` | Lines 127-147 (transparency loop), 152-168 (all sprites blit) |
| `nova_sound.py` | Lines 99-101 (waveform tables), 220-247 (sample loading) |
| `core/regfile.py` | Lines 120-133 (dispatch tables), 160-180 (get/set with dispatch) |
| `core/flags.py` | Lines 15-34 (parity table), 326-426 (unified flag setting) |
| `core/exec.py` | Lines 110-120 (handler dispatch), 379-429 (instruction table builder) |
| `core/fetch.py` | Lines 127-142 (operand pool), 147-215 (decode with pool) |

---

*Report generated: 2026-07-05*
*Analysis based on Nova-16 Phase 6 reimplantation architecture*