# Astrid Language Code Generator
# File: astrid/codegen/codegen.py
# Translates Astrid AST to Nova-16 assembly code with register allocation optimizations

from typing import List, Dict, Optional, Set, Tuple
from collections import Counter
from astrid.parser.parser import (
    Program, FunctionDef, VarDecl, Assignment, Return, If, While, DoWhile, For, FuncCall,
    Switch, Case,
    Expression, Number, StringLiteral, CharLiteral, Identifier, BinaryOp, UnaryOp, PostfixOp,
    Break, Continue, Cast,
    ArrayAccess, ArrayAssignment, StringIndexAccess, TernaryOp, PrefixOp,
    AddressOf, Deref, DerefAssignment, SizeofExpr,
    MemberAccess, MemberAssignment,
    CommaOp, Goto, Label, TypedefDecl,
    ImplBlock, MethodCall,
    AsmBlock,
)
from astrid.errors import CodeGenError
from astrid.codegen.optimizations import (
    ExpressionSimplifier,
    FunctionInliner,
    StrengthReducer,
    RegisterColoringPass,
    HotSpillAnalyzer,
    DynamicSpillAllocator,
    get_optimization_config,
)

class CodeGenerator:
    # Generates Nova-16 assembly code from Astrid AST with enhanced register allocation
    DATA_REGION_START = 0x0120
    # Fixed base address for global variables (scalars and arrays). Chosen
    # well above typical code segments (ORG 0x1000+) and far below the stack
    # (0xFF00) so global storage never collides with either.
    GLOBAL_REGION_START = 0x8000
    # Persistent storage for `static` local variables.  Static locals keep
    # their value across function calls (like a global) but have function-
    # level visibility.  Placed just below the global region so they never
    # collide with code (ORG 0x1000+), globals (0x8000+), or the stack.
    STATIC_LOCAL_REGION_END = 0x8000
    STATIC_LOCAL_REGION_START = 0x7F00  # 256 bytes for static locals
    # Read-only window for initialized `const` globals. A `const int table[] =
    # {..}` is never written (any write is already a compile error), so it does
    # not need writable RAM: it is emitted as part of the program image and
    # loaded with the code, exactly like the DEFSTR bytes of a string literal.
    # 0x5000 sits above the largest Astrid image measured so far (~0x4C71 of
    # code for starfield.ast) and below the static-local window, leaving
    # ~12 KB of tables. A program whose CODE grows past 0x5000 must pin its
    # tables with the explicit `@ addr` placement form, which always wins.
    CONST_REGION_START = 0x5000
    CONST_REGION_END = 0x7F00
    # Dedicated RAM region for spilled locals (hot-variable migration).
    # Each compiled function gets a disjoint window here so spilled locals
    # never collide with code (ORG 0x1000+), globals (0x8000+), the ITOS /
    # ITOB string buffers (0xA000 / 0xA100), the sprite SCB (0xF000-0xF0FF),
    # or the stack (grows down from 0xFF00). The previous scheme advanced a
    # 128-byte window per function upward from zero page (0x0080), which for
    # multi-function programs marched straight into the emitted code and
    # corrupted it at runtime (e.g. starfield's draw_stars overwriting its
    # own loop with spilled variables).
    SPILL_REGION_START = 0xC000
    SPILL_REGION_END = 0xF000
    LIVE_RANGE_SCHEDULER_MAX_LINES = 384
    LIVE_RANGE_SCHEDULER_MAX_WORK = 24576

    # Fixed RAM buffers for RUNTIME string concatenation results ("a" + "b").
    # Each is 256 bytes so a concatenated string can be copied and appended
    # with STRCPY/STRCAT without overflowing.  The addresses sit in the free
    # gap between the ITOB buffer (0xA100) and the spill region (0xC000), so
    # they never collide with globals (0x8000+), the stack (0xFF00), the
    # sprite SCB (0xF000) or per-function spill windows (0xC000+).  Buffers
    # are scratch storage: a concat expression's value is valid until the
    # next concat; deep nested right-hand concat expressions (a + (b + ...))
    # consume one buffer per nesting level, capped by this table.
    STRING_CONCAT_BUFFERS = (0xA200, 0xA300, 0xA400, 0xA500,
                                  0xA600, 0xA700)
    STRING_CONCAT_BUF_SIZE = 256

    # Named memory layouts. A layout pins every runtime storage region so data
    # placement is a deliberate choice rather than an accident of whichever
    # feature a program happens to use.
    #
    #   default   - the legacy single-image layout. Globals, the ITOS/ITOB
    #               string scratch cells and the concat buffers all live at
    #               0x8000-0xBFFF, which is ALSO the hardware bank window.
    #               That makes `set_bank(n)` unsafe: switching banks swaps the
    #               program's own globals out for the disk page and corrupts
    #               the runtime. It stays the default so every existing
    #               program and test is byte-for-byte unchanged.
    #   bank-safe - runtime storage moves OUT of 0x8000-0xBFFF, leaving the
    #               whole bank window free for OS use (NovaDOS NDF disks).
    #               Layout: code 0x1100-0x3FFF, globals 0x4000-0x7EFF, static
    #               locals 0x7F00-0x7FFF, string scratch 0xC000-0xC7FF, spills
    #               0xC800-0xEFFF, SCB 0xF000, stack 0xF100+ growing down.
    #               The code/globals split at 0x5000 is the tuning knob: the
    #               kernel's code grows faster than its globals, so code gets
    #               the larger half. Move the split and rebuild if either side
    #               runs out (a collision shows up as code overwriting globals).
    #               Because globals no longer live in the window, BANK can be
    #               switched at will and plain peek/poke window access is safe.
    MEMORY_LAYOUTS: Dict[str, Dict[str, object]] = {
        'default': {
            'code_org': 0x1100,
            'globals_start': 0x8000,
            # `const` tables (Tier-2 item 5): unplaced read-only globals are
            # emitted as initialized data in the CODE image (below the entry
            # stub at 0x1000, above the highest interrupt vector slot at
            # 0x011F) instead of the writable global region. Nothing else
            # lives in this window -- no runtime object is ever allocated
            # here -- so const tables are part of the loaded program image
            # and read-only by construction (any write is a compile error).
            'const_rom_start': 0x0120,
            'const_rom_end': 0x0F00,
            'static_locals_start': 0x7F00,
            'static_locals_end': 0x8000,
            'itos_buffer': 0xA000,
            'itob_buffer': 0xA100,
            'concat_buffers': (0xA200, 0xA300, 0xA400,
                               0xA500, 0xA600, 0xA700),
            'spill_start': 0xC000,
            'spill_end': 0xF000,
            'stack_floor': 0x8000,
        },
        'bank-safe': {
            'code_org': 0x1100,
            'code_limit': 0x4200,
            'globals_start': 0x4200,
            # Const-ROM window: identical to the 'default' layout. The
            # 0x0120-0x0EFF gap is free in every layout (vectors end at
            # 0x011F, the entry stub starts at 0x1000), so const tables keep
            # their addresses when a program switches layouts.
            'const_rom_start': 0x0120,
            'const_rom_end': 0x0F00,
            'static_locals_start': 0x7F00,
            'static_locals_end': 0x8000,
            'itos_buffer': 0xC000,
            'itob_buffer': 0xC100,
            'concat_buffers': (0xC200, 0xC300, 0xC400,
                               0xC500, 0xC600, 0xC700),
            'spill_start': 0xC800,
            'spill_end': 0xF000,
            'stack_floor': 0xF000,
            # The bank window is free: no runtime object may be placed here.
            'free_bank_window': (0x8000, 0xC000),
        },
    }

    # Static implementations for every builtin, keyed by assembly label.
    # Builtins are LAZILY LINKED: generate_builtins() only emits entries whose
    # label was recorded in self.used_builtins during code generation, so
    # programs that never call a builtin pay zero bytes for it. Each value is
    # a list of lines: instruction mnemonics are emitted indented; strings
    # starting with ';' are emitted verbatim as comments.
    BUILTIN_IMPLEMENTATIONS: Dict[str, List[str]] = {
        # --- Graphics ---
        'builtin_set_vmode': [
            'POP P0', 'POP P1', 'MOV VM, P1', 'PUSH P0', 'RET',
        ],
        'builtin_set_layer': [
            'POP P0', 'POP P1', 'MOV VL, P1', 'PUSH P0', 'RET',
        ],
        'builtin_set_pos': [
            'POP P0', 'POP P1', 'POP P2', 'MOV VX, P1', 'MOV VY, P2', 'PUSH P0', 'RET',
        ],
        'builtin_write_screen': [
            'POP P0', 'POP P1', 'SWRITE P1', 'PUSH P0', 'RET',
        ],
        'builtin_screen_fill': [
            'POP P0', 'POP P1', 'SFILL P1', 'PUSH P0', 'RET',
        ],
        'builtin_read_screen': [
            'SREAD P0', 'RET',
        ],
        # scroll_x/scroll_y accept an optional direction and amount:
        #   scroll_x(layer)            -> dir=0, amount=1
        #   scroll_x(layer, dir)       -> amount=1
        #   scroll_x(layer, dir, amount)
        # dir=0 rolls forward, any non-zero dir reverses. Because arguments
        # are stack-passed, each arity gets its own stub (see ARITY_BUILTINS).
        'builtin_scroll_x': [
            '; Args: layer (defaults dir=0, amount=1)',
            'POP P0', 'POP P1',
            'MOV VL, P1',
            'SROL 0, 1',
            'PUSH P0', 'RET',
        ],
        'builtin_scroll_x_2': [
            '; Args: layer, dir',
            'POP P0', 'POP P1', 'POP P2',
            'MOV VL, P1',
            'CMP P2, 0',
            'JZ builtin_scroll_x_2_fwd',
            'SROL 0, -1',
            'JMP builtin_scroll_x_2_end',
            'builtin_scroll_x_2_fwd:',
            'SROL 0, 1',
            'builtin_scroll_x_2_end:',
            'PUSH P0', 'RET',
        ],
        'builtin_scroll_x_3': [
            '; Args: layer, dir, amount',
            'POP P0', 'POP P1', 'POP P2', 'POP P3',
            'MOV VL, P1',
            'CMP P2, 0',
            'JZ builtin_scroll_x_3_fwd',
            'NEG P3',
            'builtin_scroll_x_3_fwd:',
            'SROL 0, P3',
            'PUSH P0', 'RET',
        ],
        'builtin_scroll_y': [
            '; Args: layer (defaults dir=0, amount=1)',
            'POP P0', 'POP P1',
            'MOV VL, P1',
            'SROL 1, 1',
            'PUSH P0', 'RET',
        ],
        'builtin_scroll_y_2': [
            '; Args: layer, dir',
            'POP P0', 'POP P1', 'POP P2',
            'MOV VL, P1',
            'CMP P2, 0',
            'JZ builtin_scroll_y_2_fwd',
            'SROL 1, -1',
            'JMP builtin_scroll_y_2_end',
            'builtin_scroll_y_2_fwd:',
            'SROL 1, 1',
            'builtin_scroll_y_2_end:',
            'PUSH P0', 'RET',
        ],
        'builtin_scroll_y_3': [
            '; Args: layer, dir, amount',
            'POP P0', 'POP P1', 'POP P2', 'POP P3',
            'MOV VL, P1',
            'CMP P2, 0',
            'JZ builtin_scroll_y_3_fwd',
            'NEG P3',
            'builtin_scroll_y_3_fwd:',
            'SROL 1, P3',
            'PUSH P0', 'RET',
        ],
        # roll_x/roll_y: same signature as scroll_x/scroll_y, but the
        # caller's active layer (VL) is saved and restored, so rolling one
        # layer never disturbs whatever layer is currently selected.
        'builtin_roll_x': [
            '; Args: layer (defaults dir=0, amount=1); preserves VL',
            'POP P0', 'POP P1',
            'MOV P5, VL',
            'MOV VL, P1',
            'SROL 0, 1',
            'MOV VL, P5',
            'PUSH P0', 'RET',
        ],
        'builtin_roll_x_2': [
            '; Args: layer, dir; preserves VL',
            'POP P0', 'POP P1', 'POP P2',
            'MOV P5, VL',
            'MOV VL, P1',
            'CMP P2, 0',
            'JZ builtin_roll_x_2_fwd',
            'SROL 0, -1',
            'JMP builtin_roll_x_2_end',
            'builtin_roll_x_2_fwd:',
            'SROL 0, 1',
            'builtin_roll_x_2_end:',
            'MOV VL, P5',
            'PUSH P0', 'RET',
        ],
        'builtin_roll_x_3': [
            '; Args: layer, dir, amount; preserves VL',
            'POP P0', 'POP P1', 'POP P2', 'POP P3',
            'MOV P5, VL',
            'MOV VL, P1',
            'CMP P2, 0',
            'JZ builtin_roll_x_3_fwd',
            'NEG P3',
            'builtin_roll_x_3_fwd:',
            'SROL 0, P3',
            'MOV VL, P5',
            'PUSH P0', 'RET',
        ],
        'builtin_roll_y': [
            '; Args: layer (defaults dir=0, amount=1); preserves VL',
            'POP P0', 'POP P1',
            'MOV P5, VL',
            'MOV VL, P1',
            'SROL 1, 1',
            'MOV VL, P5',
            'PUSH P0', 'RET',
        ],
        'builtin_roll_y_2': [
            '; Args: layer, dir; preserves VL',
            'POP P0', 'POP P1', 'POP P2',
            'MOV P5, VL',
            'MOV VL, P1',
            'CMP P2, 0',
            'JZ builtin_roll_y_2_fwd',
            'SROL 1, -1',
            'JMP builtin_roll_y_2_end',
            'builtin_roll_y_2_fwd:',
            'SROL 1, 1',
            'builtin_roll_y_2_end:',
            'MOV VL, P5',
            'PUSH P0', 'RET',
        ],
        'builtin_roll_y_3': [
            '; Args: layer, dir, amount; preserves VL',
            'POP P0', 'POP P1', 'POP P2', 'POP P3',
            'MOV P5, VL',
            'MOV VL, P1',
            'CMP P2, 0',
            'JZ builtin_roll_y_3_fwd',
            'NEG P3',
            'builtin_roll_y_3_fwd:',
            'SROL 1, P3',
            'MOV VL, P5',
            'PUSH P0', 'RET',
        ],
        'builtin_draw_rect': [
            '; Args: x2, y2, filled (start corner from VX/VY, color VC)',
            'POP P0', 'POP P1', 'POP P2', 'POP P3',
            'SRECT P1, P2, P3',
            'PUSH P0', 'RET',
        ],
        'builtin_set_color': [
            '; Args: color -> VC (drawing color for SRECT/SLINE/SCIRC/CHAR)',
            'POP P0', 'POP P1', 'MOV VC, P1', 'PUSH P0', 'RET',
        ],
        'builtin_vread': [
            '; Args: linear VRAM address. VREAD uses its operand as BOTH the',
            '; address input and the result destination, so the return address',
            '; must be stashed in P3 first (same pattern as builtin_random_range).',
            'POP P3', 'POP P1', 'VREAD P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_vwrite': [
            '; Args: value (writes VRAM at VX/VY)',
            'POP P0', 'POP P1', 'VWRITE P1', 'PUSH P0', 'RET',
        ],
        'builtin_screen_rotate': [
            '; Args: direction, amount',
            'POP P0', 'POP P1', 'POP P2', 'SROT P1, P2', 'PUSH P0', 'RET',
        ],
        'builtin_screen_shift': [
            '; Args: axis, amount',
            'POP P0', 'POP P1', 'POP P2', 'SSHFT P1, P2', 'PUSH P0', 'RET',
        ],
        'builtin_screen_flip': [
            '; Args: axis',
            'POP P0', 'POP P1', 'SFLIP P1', 'PUSH P0', 'RET',
        ],
        'builtin_draw_line': [
            '; Args: x2, y2 (uses VX/VY as start)',
            'POP P0', 'POP P1', 'POP P2', 'SLINE P1, P2', 'PUSH P0', 'RET',
        ],
        'builtin_draw_circle': [
            '; Args: radius, filled',
            'POP P0', 'POP P1', 'POP P2', 'SCIRC P1, P2', 'PUSH P0', 'RET',
        ],
        'builtin_screen_invert': [
            'POP P0', 'SINV', 'PUSH P0', 'RET',
        ],
        'builtin_screen_blit': [
            'POP P0', 'SBLIT', 'PUSH P0', 'RET',
        ],
        'builtin_sprite_blit': [
            '; sprite_blit(sprite_id): blit the sprite with the given ID (0-15).',
            '; The SCB (16 bytes per sprite at 0xF000 + id*16) must already be',
            '; programmed: data address (big-endian word = two poke() calls),',
            '; x, y, width, height, flags, transparency color.',
            'POP P0', 'POP P1', 'SPBLIT P1', 'PUSH P0', 'RET',
        ],
        'builtin_sprite_blitall': [
            '; sprite_blitall(): blit all active sprites (0-15) from their SCBs.',
            '; Clears sprite layers 5-8 first, then renders every active sprite.',
            'POP P0', 'SPBLITALL', 'PUSH P0', 'RET',
        ],
        'builtin_set_blend_mode': [
            'POP P0', 'POP P1', 'SBLEND P1', 'PUSH P0', 'RET',
        ],
        'builtin_set_blend_alpha': [
            'POP P0', 'POP P1', 'SALPHA P1', 'PUSH P0', 'RET',
        ],
        'builtin_draw_char': [
            '; Args: char (uses VX/VY position, VC color)',
            'POP P0', 'POP P1', 'CHAR P1', 'PUSH P0', 'RET',
        ],
        'builtin_set_pointers': [
            '; All pushes/pops are P (2 bytes) for 16-bit ABI consistency.',
            'POP P3', 'POP P1', 'POP P2', 'MOV P0, P1', 'MOV P1, P2', 'PUSH P3', 'RET',
        ],
        'builtin_write_text': [
            'POP P0', 'POP P1', 'POP P2', 'MOV VC, P2', 'TEXT P1', 'PUSH P0', 'RET',
        ],
        'builtin_set_font': [
            'POP P0', 'POP P1', 'PUSH P0', 'RET',
        ],
        'builtin_layer_swap': [
            'POP P0', 'POP P1', 'LSWAP P1', 'PUSH P0', 'RET',
        ],
        'builtin_layer_move': [
            'POP P0', 'POP P1', 'LMOVE P1', 'PUSH P0', 'RET',
        ],
        'builtin_layer_copy': [
            'POP P0', 'POP P1', 'LCOPY P1', 'PUSH P0', 'RET',
        ],
        # --- Sound ---
        # SPLAY/SSTOP are ZERO-operand opcodes (0x57/0x58): the assembler
        # silently discards any operands written after them, and the hardware
        # takes every parameter from the SA/SF/SV/SW special registers (SW
        # bits 0-2 waveform, 3-5 channel, 6 loop, 7 enable). So the builtin
        # stubs move their stack arguments into those registers first.
        'builtin_sound_play': [
            '; Args: freq (-> SF), volume (-> SV), SW control word (-> SW).',
            '; SA is intentionally untouched: set it before the call for',
            '; waveform-7 memory samples. SPLAY plays the channel encoded in',
            '; SW bits 3-5; bit 7 must be set or the play is ignored.',
            'POP P0', 'POP P1', 'POP P2', 'POP P3',
            '; Args pushed in reversed source order: stack top->bottom after POP P0 is',
            '; [arg0=freq, arg1=vol, arg2=sw]. So POP P1=freq, P2=vol, P3=sw.',
            'MOV SF, P1', 'MOV SV, P2', 'MOV SW, P3', 'SPLAY', 'PUSH P0', 'RET',
        ],
        'builtin_sound_stop': [
            '; Args: channel (0-7). SSTOP is zero-operand and reads the channel',
            '; from SW bits 3-5, so shift the channel into place before SSTOP.',
            'POP P0', 'POP P1',
            'MOV P2, P1', 'SHL P2, 3', 'MOV SW, P2', 'SSTOP', 'PUSH P0', 'RET',
        ],
        'builtin_sound_trigger': [
            'POP P0', 'POP P1', 'STRIG P1', 'PUSH P0', 'RET',
        ],
        'builtin_set_timer': [
            'POP P0', 'POP P1', 'POP P2', 'POP P3', 'POP P4',
            '; Args pushed in reversed source order: stack top->bottom after POP P0 is',
            '; [arg0=TT, arg1=TM, arg2=TS, arg3=TC]. So POP P1=TT, P2=TM, P3=TS, P4=TC.',
            'MOV TT, P1', 'MOV TM, P2', 'MOV TS, P3', 'MOV TC, P4', 'PUSH P0', 'RET',
        ],
        # --- Interrupts ---
        'builtin_sti': ['STI', 'RET'],
        'builtin_cli': ['CLI', 'RET'],
        'builtin_iret': ['IRET', 'RET'],
        'builtin_software_int': [
            'POP P0', 'POP P1', 'INT P1', 'PUSH P0', 'RET',
        ],
        # --- Keyboard ---
        'builtin_key_available': ['KEYSTAT P0', 'RET'],
        'builtin_key_read': ['KEYIN P0', 'RET'],
        'builtin_key_clear': ['KEYCLEAR', 'RET'],
        'builtin_key_count': ['KEYCOUNT P0', 'RET'],
        'builtin_key_ctrl': [
            'POP P0', 'POP P1', 'KEYCTRL P1', 'PUSH P0', 'RET',
        ],
        # --- Random ---
        'builtin_random': ['RND P0', 'RET'],
        'builtin_random_range': [
            '; Save return address in P3 (not P0, since RNDR will write its result to P0).',
            '; Stack: [ret_addr, color_max, color_min] (top = last pushed = color_min)',
            '; builtins with P0 as destination use P3 for the return address (see',
            '; builtin_set_pointers for the same pattern).',
            'POP P3', 'POP P1', 'POP P2', 'RNDR P0, P1, P2', 'PUSH P3', 'RET',
        ],
        # --- Math (unary, write result to P0) ---
        'builtin_abs': [
            'POP P3', 'POP P1', 'ABS P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_min': [
            'POP P3', 'POP P1', 'POP P2', 'MIN P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_max': [
            'POP P3', 'POP P1', 'POP P2', 'MAX P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_clz': [
            'POP P3', 'POP P1', 'CLZ P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_ctz': [
            'POP P3', 'POP P1', 'CTZ P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_popcnt': [
            'POP P3', 'POP P1', 'POPCNT P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_sqrt': [
            'POP P3', 'POP P1', 'SQRT P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_log': [
            'POP P3', 'POP P1', 'LOG P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_exp': [
            'POP P3', 'POP P1', 'EXP P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_sin': [
            'POP P3', 'POP P1', 'SIN P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_cos': [
            'POP P3', 'POP P1', 'COS P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_tan': [
            'POP P3', 'POP P1', 'TAN P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_atan': [
            'POP P3', 'POP P1', 'ATAN P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_asin': [
            'POP P3', 'POP P1', 'ASIN P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_acos': [
            'POP P3', 'POP P1', 'ACOS P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_deg': [
            'POP P3', 'POP P1', 'DEG P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_rad': [
            'POP P3', 'POP P1', 'RAD P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_floor': [
            'POP P3', 'POP P1', 'FLOOR P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_ceil': [
            'POP P3', 'POP P1', 'CEIL P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_round': [
            'POP P3', 'POP P1', 'ROUND P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_trunc': [
            'POP P3', 'POP P1', 'TRUNC P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_frac': [
            'POP P3', 'POP P1', 'FRAC P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_intgr': [
            'POP P3', 'POP P1', 'INTGR P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_int': [
            '; int(x): identity on 16-bit integers (values are already integral).',
            '; Do NOT use the INT opcode here -- that raises a software interrupt.',
            'POP P3', 'POP P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_powr': [
            'POP P3', 'POP P1', 'POP P2', 'POWR P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        # --- String ---
        'builtin_strcpy': [
            'POP P3', 'POP P1', 'POP P2', 'STRCPY P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_strcat': [
            'POP P3', 'POP P1', 'POP P2', 'STRCAT P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_strcmp': [
            'POP P3', 'POP P1', 'POP P2', 'POP P4', 'STRCMP P1, P2, P4', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_strlen': [
            '; STRLEN writes result to R0',
            'POP P3', 'POP P1', 'STRLEN P1', 'MOV P0, R0', 'PUSH P3', 'RET',
        ],
        'builtin_strupr': [
            'POP P3', 'POP P1', 'STRUPR P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_strlwr': [
            'POP P3', 'POP P1', 'STRLWR P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_strrev': [
            'POP P3', 'POP P1', 'STRREV P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_strfind': [
            '; STRFIND writes result to R0',
            'POP P3', 'POP P1', 'POP P2', 'STRFIND P1, P2', 'MOV P0, R0', 'PUSH P3', 'RET',
        ],
        'builtin_strfindi': [
            '; STRFINDI writes result to R0',
            'POP P3', 'POP P1', 'POP P2', 'STRFINDI P1, P2', 'MOV P0, R0', 'PUSH P3', 'RET',
        ],
        # --- Serial ---
        'builtin_ser_out': [
            'POP P3', 'POP P1', 'SEROUT P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_ser_in': ['SERIN P0', 'RET'],
        'builtin_ser_stat': ['SERSTAT P0', 'RET'],
        'builtin_ser_ctrl': [
            'POP P3', 'POP P1', 'SERCTRL P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        # --- Memory ---
        'builtin_memcpy': [
            'POP P3', 'POP P1', 'POP P2', 'POP P4', 'MEMCPY P1, P2, P4', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_memset': [    # memset(addr, value, length)
            'POP P3', 'POP P1', 'POP P2', 'POP P4', 'MEMSET P1, P2, P4', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_memmove': [
            'POP P3', 'POP P1', 'POP P2', 'POP P4', 'MEMMOVE P1, P2, P4', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_memcmp': [
            'POP P3', 'POP P1', 'POP P2', 'POP P4', 'POP P5', 'MEMCMP P1, P2, P4, P5', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_memtest': [
            'POP P3', 'POP P1', 'POP P2', 'POP P4', 'MEMTEST P1, P2, P4', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_memswap': [
            'POP P3', 'POP P1', 'POP P2', 'POP P4', 'MEMSWAP P1, P2, P4', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        # --- Low-level byte memory / banking (kernel primitives) ---
        'builtin_peek': [
            '; peek(addr) -> the byte stored at addr.',
            '; The data bus is word-granular and big-endian (the high byte of a',
            '; word lives at the LOWER address), so the byte AT addr is the HIGH',
            '; byte of the word loaded from addr. P-high-byte access (:P syntax',
            '; inverted: Px:) extracts it without any shift sequence.',
            'POP P3', 'POP P1',
            'MOV P2, [P1]',
            'MOV P0, P2:',
            'PUSH P3', 'RET',
        ],
        'builtin_poke': [
            '; poke(addr, val): store low byte of val at addr.',
            '; No byte-wide store exists on the bus, so this is a read-modify-',
            '; write of the containing word: keep the neighbor byte at addr+1',
            '; masked in place and splice val into the high byte. The 8-left-',
            '; shift also drops anything above bit 7 of val for free.',
            'POP P3', 'POP P1', 'POP P2',
            'MOV P4, [P1]',
            'MOV P5, 255',
            'AND P4, P5',
            'MOV P5, P2',
            '; val << 8: unrolled two-operand shifts (the bare "SHL Px" form',
            '; mis-encodes -- the ISA defines SHL as dst,count)',
            'SHL P5, 1', 'SHL P5, 1', 'SHL P5, 1', 'SHL P5, 1',
            'SHL P5, 1', 'SHL P5, 1', 'SHL P5, 1', 'SHL P5, 1',
            'OR P4, P5',
            'MOV [P1], P4',
            'PUSH P3', 'RET',
        ],
        'builtin_peek2': [
            '; peek2(addr) -> the 16-bit word stored at addr.',
            '; A single bus load grabs both bytes at once -- no read-modify-',
            '; write dance needed. Big-endian layout: high byte at addr, low',
            '; byte at addr+1, which is exactly how the CPU stores a word.',
            'POP P3', 'POP P1',
            'MOV P0, [P1]',
            'PUSH P3', 'RET',
        ],
        'builtin_poke2': [
            '; poke2(addr, val): store a full 16-bit word at addr.',
            '; One bus write deposits both bytes at once -- the high byte of',
            '; val lands at addr, the low byte at addr+1. No neighbor-byte',
            '; preservation needed since we own the entire word.',
            'POP P3', 'POP P1', 'POP P2',
            'MOV [P1], P2',
            'PUSH P3', 'RET',
        ],
        'builtin_byte': [
            '; byte(value, selector) -> high byte (selector=0) or low byte (selector=1).',
            '; Mirrors the Nova ISA\'s ":" byte-access syntax: P1: extracts the',
            '; high byte, :P1 extracts the low byte. The selector is a runtime',
            '; argument so we branch: selector 0 -> high, anything else -> low.',
            'POP P3', 'POP P1', 'POP P2',
            'CMP P2, 0',
            'JNZ .byte_low',
            'MOV P0, P1:',
            'JMP .byte_done',
            '.byte_low:',
            'MOV P0, :P1',
            '.byte_done:',
            'PUSH P3', 'RET',
        ],
        'builtin_set_bank': [
            '; set_bank(n): aim the 0x8000-0xBFFF window at page n.',
            '; Hardware clamps to 0-15 and invalidates the instruction cache;',
            '; banked writes never touch base RAM (see nova/memory/memory.py).',
            'POP P0', 'POP P1', 'MOV BANK, P1', 'PUSH P0', 'RET',
        ],
        'builtin_read_bank': [
            '; read_bank() -> currently visible page number (0-15).',
            '; Clear P0 first so the R->P move can never inherit stale',
            '; high-byte garbage from earlier expression evaluation.',
            'MOV P0, 0',
            'MOV R0, BANK',
            'MOV P0, R0',
            'RET',
        ],
        # --- CPU/system registers and stack access (systems tier) ---
        # Calling convention shared with all builtins: args sit at [ret, a1,
        # a2, ...] on entry (top first), P1/P2/P3/R0 are scratch, and the
        # 16-bit result lands in P0. P0-P7 are compiler expression scratch
        # (round-robin, P3 excluded), so set_reg/get_reg pairs only read back
        # reliably on P3 and on values nothing else touched in between. The
        # intended uses are hardware hand-off moments: ISR/asm register
        # interop, DIV-remainder inspection, and context switching.
        'builtin_get_reg': [
            '; get_reg(n) -> P[n] (16-bit). n 0-9 selects P0-P9; out of',
            '; range returns 0. The read happens BEFORE the return address',
            '; is consumed: P3 is never popped here, because the caller',
            '; planted value (or DIV remainder) in P3 must survive the',
            '; observation. RET consumes the return address instead.',
            'MOV P1, [SP+2]',
            'CMP P1, 0', 'JZ .p0',
            'CMP P1, 1', 'JZ .p1',
            'CMP P1, 2', 'JZ .p2',
            'CMP P1, 3', 'JZ .p3',
            'CMP P1, 4', 'JZ .p4',
            'CMP P1, 5', 'JZ .p5',
            'CMP P1, 6', 'JZ .p6',
            'CMP P1, 7', 'JZ .p7',
            'CMP P1, 8', 'JZ .p8',
            'CMP P1, 9', 'JZ .p9',
            'MOV P0, 0', 'JMP .gdone',
            '.p0:', 'MOV P0, P0', 'JMP .gdone',
            '.p1:', 'MOV P0, P1', 'JMP .gdone',
            '.p2:', 'MOV P0, P2', 'JMP .gdone',
            '.p3:', 'MOV P0, P3', 'JMP .gdone',
            '.p4:', 'MOV P0, P4', 'JMP .gdone',
            '.p5:', 'MOV P0, P5', 'JMP .gdone',
            '.p6:', 'MOV P0, P6', 'JMP .gdone',
            '.p7:', 'MOV P0, P7', 'JMP .gdone',
            '.p8:', 'MOV P0, P8', 'JMP .gdone',
            '.p9:', 'MOV P0, P9',
            '.gdone:', 'RET',
        ],
        'builtin_set_reg': [
            '; set_reg(n, v): writes v to P[n]. n 0-9; out of range is a',
            '; no-op that just returns the live P[n]. Reads n and v through',
            '; stack-relative windows so the return address is never popped',
            '; into P3 -- set_reg(3, x) must be able to plant a value in P3',
            '; without the stub first clobbering it. Returns the previously-',
            '; held P[n] value in P0 (the value observed at dispatch time).',
            'MOV P1, [SP+2]',
            'MOV P2, [SP+4]',
            'CMP P1, 0', 'JZ .s0',
            'CMP P1, 1', 'JZ .s1',
            'CMP P1, 2', 'JZ .s2',
            'CMP P1, 3', 'JZ .s3',
            'CMP P1, 4', 'JZ .s4',
            'CMP P1, 5', 'JZ .s5',
            'CMP P1, 6', 'JZ .s6',
            'CMP P1, 7', 'JZ .s7',
            'CMP P1, 8', 'JZ .s8',
            'CMP P1, 9', 'JZ .s9',
            'MOV P0, 0', 'JMP .sdone',
            '.s0:', 'MOV P0, P0', 'MOV P0, P2', 'JMP .sdone',
            '.s1:', 'MOV P0, P1', 'MOV P1, P2', 'JMP .sdone',
            '.s2:', 'MOV P0, P2', 'JMP .sdone',
            '.s3:', 'MOV P0, P3', 'MOV P3, P2', 'JMP .sdone',
            '.s4:', 'MOV P0, P4', 'MOV P4, P2', 'JMP .sdone',
            '.s5:', 'MOV P0, P5', 'MOV P5, P2', 'JMP .sdone',
            '.s6:', 'MOV P0, P6', 'MOV P6, P2', 'JMP .sdone',
            '.s7:', 'MOV P0, P7', 'MOV P7, P2', 'JMP .sdone',
            '.s8:', 'MOV P0, P8', 'MOV P8, P2', 'JMP .sdone',
            '.s9:', 'MOV P0, P9', 'MOV P9, P2',
            '.sdone:', 'RET',
        ],
        'builtin_get_rreg': [
            '; get_rreg(n) -> R[n] zero-extended to 16 bits (0-255).',
            '; n 0-9 selects R0-R9; out of range returns 0.',
            'POP P3', 'POP P1',
            'CMP P1, 0', 'JZ .r0',
            'CMP P1, 1', 'JZ .r1',
            'CMP P1, 2', 'JZ .r2',
            'CMP P1, 3', 'JZ .r3',
            'CMP P1, 4', 'JZ .r4',
            'CMP P1, 5', 'JZ .r5',
            'CMP P1, 6', 'JZ .r6',
            'CMP P1, 7', 'JZ .r7',
            'CMP P1, 8', 'JZ .r8',
            'CMP P1, 9', 'JZ .r9',
            'MOV P0, 0', 'JMP .rdone',
            '.r0:', 'MOV P0, 0', 'MOV P0, R0', 'JMP .rdone',
            '.r1:', 'MOV P0, 0', 'MOV P0, R1', 'JMP .rdone',
            '.r2:', 'MOV P0, 0', 'MOV P0, R2', 'JMP .rdone',
            '.r3:', 'MOV P0, 0', 'MOV P0, R3', 'JMP .rdone',
            '.r4:', 'MOV P0, 0', 'MOV P0, R4', 'JMP .rdone',
            '.r5:', 'MOV P0, 0', 'MOV P0, R5', 'JMP .rdone',
            '.r6:', 'MOV P0, 0', 'MOV P0, R6', 'JMP .rdone',
            '.r7:', 'MOV P0, 0', 'MOV P0, R7', 'JMP .rdone',
            '.r8:', 'MOV P0, 0', 'MOV P0, R8', 'JMP .rdone',
            '.r9:', 'MOV P0, 0', 'MOV P0, R9',
            '.rdone:', 'PUSH P3', 'RET',
        ],
        'builtin_set_rreg': [
            '; set_rreg(n, v): R[n] = low byte of v (16-bit arg truncates).',
            '; n 0-9; out of range is a no-op. The return address stays in',
            '; P3 because the dispatch targets are R registers only.',
            '; Returns the previously-held R[n] value in P0 (zero-extended).',
            'POP P3', 'POP P1', 'POP P2',
            'CMP P1, 0', 'JZ .t0',
            'CMP P1, 1', 'JZ .t1',
            'CMP P1, 2', 'JZ .t2',
            'CMP P1, 3', 'JZ .t3',
            'CMP P1, 4', 'JZ .t4',
            'CMP P1, 5', 'JZ .t5',
            'CMP P1, 6', 'JZ .t6',
            'CMP P1, 7', 'JZ .t7',
            'CMP P1, 8', 'JZ .t8',
            'CMP P1, 9', 'JZ .t9',
            'MOV P0, 0', 'JMP .tdone',
            '.t0:', 'MOV P0, 0', 'MOV P0, R0', 'MOV R0, P2', 'JMP .tdone',
            '.t1:', 'MOV P0, 0', 'MOV P0, R1', 'MOV R1, P2', 'JMP .tdone',
            '.t2:', 'MOV P0, 0', 'MOV P0, R2', 'MOV R2, P2', 'JMP .tdone',
            '.t3:', 'MOV P0, 0', 'MOV P0, R3', 'MOV R3, P2', 'JMP .tdone',
            '.t4:', 'MOV P0, 0', 'MOV P0, R4', 'MOV R4, P2', 'JMP .tdone',
            '.t5:', 'MOV P0, 0', 'MOV P0, R5', 'MOV R5, P2', 'JMP .tdone',
            '.t6:', 'MOV P0, 0', 'MOV P0, R6', 'MOV R6, P2', 'JMP .tdone',
            '.t7:', 'MOV P0, 0', 'MOV P0, R7', 'MOV R7, P2', 'JMP .tdone',
            '.t8:', 'MOV P0, 0', 'MOV P0, R8', 'MOV R8, P2', 'JMP .tdone',
            '.t9:', 'MOV P0, 0', 'MOV P0, R9', 'MOV R9, P2',
            '.tdone:', 'PUSH P3', 'RET',
        ],
        'builtin_get_sp': [
            '; get_sp() -> live stack pointer. Balanced POP/PUSH keeps the',
            '; observation non-destructive.',
            'POP P3',
            'MOV P0, SP',
            'PUSH P3', 'RET',
        ],
        'builtin_set_sp': [
            '; set_sp(v): switch the stack pointer to v and return with',
            '; SP exactly equal to v. The return address is consumed via a',
            '; register-indirect JMP instead of RET, because a RET would',
            '; pop from the NEW stack. This is the primitive behind',
            '; task/coroutine stack switching.',
            'POP P3',
            'POP P1',
            'MOV SP, P1',
            'JMP P3',
        ],
        'builtin_get_fp': [
            '; get_fp() -> live frame pointer.',
            'POP P3',
            'MOV P0, FP',
            'PUSH P3', 'RET',
        ],
        'builtin_set_fp': [
            '; set_fp(v): point the frame pointer at v and return. For',
            '; context switching only -- the CURRENT function must not',
            '; return through normal frames while FP is redirected (its',
            '; epilogue does MOV SP, FP / POP FP). Restore FP first.',
            'POP P3',
            'POP P1',
            'MOV FP, P1',
            'PUSH P3', 'RET',
        ],
        'builtin_get_flags': [
            '; get_flags() -> the 12-bit flag word (T,S,O,B,D,I,C,Z,P,H,A,E',
            '; in bits 0-11). PUSHF/POPF move the live word, so this observes',
            '; exactly what the CPU would see -- no recomputation.',
            'POP P3',
            'PUSHF',
            'POP P0',
            'PUSH P3', 'RET',
        ],
        'builtin_set_flags': [
            '; set_flags(f): wholesale-replace the flag word with the low 12',
            '; bits of f. Bit 11 (E, hacker flag) is never touched by the',
            '; CPU itself, making it a free user/system ownership tag.',
            'POP P3',
            'POP P1',
            'PUSH P1',
            'POPF',
            'PUSH P3', 'RET',
        ],
        # --- Stack manipulation and cooperative tasks (systems tier 2) ---
        'builtin_push': [
            '; push(v): deposit v as the new top-of-stack word (raw stack',
            '; access). Void: consumes its argument; on return [SP] == v.',
            'POP P3', 'POP P1',
            'PUSH P1',
            'PUSH P3', 'RET',
        ],
        'builtin_pop': [
            '; pop() -> removes and returns the top-of-stack word.',
            'POP P3',
            'POP P0',
            'PUSH P3', 'RET',
        ],
        'builtin_alloca': [
            '; alloca(bytes) -> address of `bytes` bytes of stack scratch.',
            '; The block lives until the CURRENT function returns: the',
            '; epilogue (MOV SP, FP / POP FP) reclaims it for free. Do not',
            '; call alloca inside an unbounded loop -- each call eats more',
            '; stack until the frame unwinds.',
            'POP P3', 'POP P1',
            'MOV P0, SP',
            'SUB SP, P1',
            'PUSH P3', 'RET',
        ],
        'builtin_stack_free': [
            '; stack_free() -> bytes of headroom between SP and the',
            '; low bound of the stack arena ({stack_floor}). Under the default',
            '; layout that bound is the 0x8000 global region; under bank-safe it',
            '; is the top of the scratch/spill region so a deep stack cannot',
            '; silently corrupt fixed runtime storage.',
            'POP P3',
            'MOV P0, SP',
            'SUB P0, {stack_floor}',
            'PUSH P3', 'RET',
        ],
        # Context layout (22 ints / 44 bytes, word index -> byte offset):
        #   0:  flags          +0     4-13:  R0-R9      +8..+26
        #   1:  FP             +2     14-21: P0-P7      +28..+44
        #   2:  SP-resume      +4
        #   3:  (unused)       +6
        # SP-resume points at a stack word holding the task's resume PC;
        # task_switch restores SP and RETs, which pops the PC. This keeps
        # the PC out of the register permutation entirely.
        'builtin_task_spawn': [
            '; task_spawn(ctx, stack_base, stack_words, entry): fabricate an',
            '; initial context for a fresh task. The resume PC (entry) is',
            '; parked at the top of the task stack region; R/P registers',
            '; start zeroed; FP starts at stack_base; flags are inherited',
            '; from the spawning task.',
            '; entry stack: [ret][ctx][stack_base][stack_words][entry]',
            'MOV P1, [SP+2]',
            'MOV P2, [SP+4]',
            'MOV P7, P3',
            'MOV P3, [SP+6]',
            'MOV P4, [SP+8]',
            'MOV P5, P3',
            'ADD P5, P3',
            'ADD P5, P2',
            'SUB P5, 2',
            'MOV [P5+0], P4',
            'MOV [P1+4], P5',
            'MOV P6, 0',
            'MOV [P1+6], P6',
            'MOV P6, P2',
            'MOV [P1+2], P6',
            'PUSHF',
            'POP P6',
            'MOV [P1+0], P6',
            'MOV P3, 0', 'MOV [P1+34], P3',
            'MOV P6, 0',
            'MOV [P1+28], P6', 'MOV [P1+30], P6', 'MOV [P1+32], P6',
            'MOV [P1+36], P6', 'MOV [P1+38], P6', 'MOV [P1+40], P6', 'MOV [P1+42], P6',
            'MOV R0, 0', 'MOV [P1+8], P6',
            'MOV R1, 0', 'MOV [P1+10], P6',
            'MOV R2, 0', 'MOV [P1+12], P6',
            'MOV R3, 0', 'MOV [P1+14], P6',
            'MOV R4, 0', 'MOV [P1+16], P6',
            'MOV R5, 0', 'MOV [P1+18], P6',
            'MOV R6, 0', 'MOV [P1+20], P6',
            'MOV R7, 0', 'MOV [P1+22], P6',
            'MOV R8, 0', 'MOV [P1+24], P6',
            'MOV R9, 0', 'MOV [P1+26], P6',
            'MOV P3, P7',
            'MOV P5, [SP+0]',
            'MOV [SP+8], P5',
            'ADD SP, 8',
            'RET',
        ],
        'builtin_task_switch': [
            '; task_switch(save_ctx, restore_ctx): symmetric coroutine',
            '; switch. Saves the CURRENT task into save_ctx (flags, FP, a',
            '; resume SP with the resume PC parked on its own stack, all R',
            '; and P0-P7 registers) and enters the task described by',
            '; restore_ctx via RET. On the next resume, execution continues',
            '; right after this call, exactly as if task_switch had just',
            '; returned. P0/P1 entering the stub hold the arg-eval scratch,',
            '; so the save records those slots as-seen (P0-P7 are compiler',
            '; scratch anyway; P3 -- the DIV remainder -- IS preserved).',
            '; entry stack: [ret][save_ctx][restore_ctx]',
            'MOV P1, [SP+2]',
            'MOV [P1+32], P2',
            'MOV [P1+34], P3',
            'MOV [P1+36], P4',
            'MOV [P1+38], P5',
            'MOV [P1+40], P6',
            'MOV [P1+42], P7',
            'MOV [P1+30], P1',
            'MOV [P1+28], P0',
            'MOV P2, [SP+4]',
            '; --- save phase: stage live registers through P5 ---',
            'MOV P5, R0',   'MOV [P1+8], P5',
            'MOV P5, R1',   'MOV [P1+10], P5',
            'MOV P5, R2',   'MOV [P1+12], P5',
            'MOV P5, R3',   'MOV [P1+14], P5',
            'MOV P5, R4',   'MOV [P1+16], P5',
            'MOV P5, R5',   'MOV [P1+18], P5',
            'MOV P5, R6',   'MOV [P1+20], P5',
            'MOV P5, R7',   'MOV [P1+22], P5',
            'MOV P5, R8',   'MOV [P1+24], P5',
            'MOV P5, R9',   'MOV [P1+26], P5',
            'MOV P5, FP',   'MOV [P1+2], P5',
            'PUSHF',
            'POP P5',
            'MOV [P1+0], P5',
            '; park the resume PC on THIS task stack and record the SP that',
            '; makes a plain RET land on it after the 2 args and the return',
            '; address are consumed (SP+6).',
            'MOV P5, [SP+0]',
            'MOV [SP+4], P5',
            'MOV P5, SP',
            'ADD P5, 4',
            'MOV [P1+4], P5',
            '; --- restore phase: P2 stays the base pointer throughout; P6',
            '; is the only scratch and is re-loaded from memory near the end',
            '; (memory->R loads are byte loads, so R values stage via P6).',
            'MOV P6, [P2+0]',
            'PUSH P6',
            'POPF',
            'MOV P6, [P2+8]',   'MOV R0, P6',
            'MOV P6, [P2+10]',  'MOV R1, P6',
            'MOV P6, [P2+12]',  'MOV R2, P6',
            'MOV P6, [P2+14]',  'MOV R3, P6',
            'MOV P6, [P2+16]',  'MOV R4, P6',
            'MOV P6, [P2+18]',  'MOV R5, P6',
            'MOV P6, [P2+20]',  'MOV R6, P6',
            'MOV P6, [P2+22]',  'MOV R7, P6',
            'MOV P6, [P2+24]',  'MOV R8, P6',
            'MOV P6, [P2+26]',  'MOV R9, P6',
            'MOV P0, [P2+28]',
            'MOV P1, [P2+30]',
            'MOV P3, [P2+34]',
            'MOV P4, [P2+36]',
            'MOV P6, [P2+38]', 'MOV P5, P6',
            'MOV P6, [P2+42]', 'MOV P7, P6',
            'MOV P6, [P2+40]',
            'MOV FP, [P2+2]',
            'MOV SP, [P2+4]',
            'MOV P2, [P2+32]',
            'RET',
        ],
        # --- Bit manipulation ---
        'builtin_btst': [
            'POP P3', 'POP P1', 'POP P2', 'BTST P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_bset': [
            'POP P3', 'POP P1', 'POP P2', 'BSET P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_bclr': [
            'POP P3', 'POP P1', 'POP P2', 'BCLR P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_bflip': [
            'POP P3', 'POP P1', 'POP P2', 'BFLIP P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        # --- Misc ---
        'builtin_swap': [
            'POP P3', 'POP P1', 'SWAP P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_xchng': [
            'POP P3', 'POP P1', 'POP P2', 'XCHNG P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_nop': ['NOP', 'RET'],
        'builtin_pushf': ['PUSHF', 'RET'],
        'builtin_popf': ['POPF', 'RET'],
        'builtin_pusha': ['PUSHA', 'RET'],
        'builtin_popa': [
            '; POPA restores EVERY register (R0-R9, P0-P9, VX/VY/VC), including',
            '; the ones this stub would normally use to keep its own return',
            '; address alive -- and it consumes the return address the CALL',
            '; pushed, along with anything else above it. Park the return',
            '; address in the documented ITOS scratch cell ({itos}) for the',
            '; duration of the call; no ITOS activity can occur in between.',
            'POP P3',
            'MOV [{itos}], P3',
            'POPA',
            'MOV P3, [{itos}]',
            'PUSH P3',
            'RET',
        ],
        'builtin_halt': ['HLT', 'RET'],
        # --- BCD ---
        'builtin_sed': ['SED', 'RET'],
        'builtin_cld': ['CLD', 'RET'],
        'builtin_cla': ['CLA', 'RET'],
        'builtin_bcd2bin': [
            'POP P3', 'POP P1', 'BCD2BIN P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_bin2bcd': [
            'POP P3', 'POP P1', 'BIN2BCD P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_bcdadd': [
            'POP P3', 'POP P1', 'POP P2', 'BCDADD P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_bcdsub': [
            'POP P3', 'POP P1', 'POP P2', 'BCDSUB P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_bcda': [
            'POP P3', 'POP P1', 'POP P2', 'BCDA P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_bcds': [
            'POP P3', 'POP P1', 'POP P2', 'BCDS P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_bcdcmp': [
            'POP P3', 'POP P1', 'POP P2', 'BCDCMP P1, P2', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        # --- Mouse ---
        'builtin_mouse_ctrl': [
            'POP P3', 'POP P1', 'MOUSECTRL P1', 'MOV P0, P1', 'PUSH P3', 'RET',
        ],
        'builtin_mouse_read': [
            'MOV P0, MB', 'RET',
        ],
        'builtin_mouse_pos': [
            '; Mouse position readout: axis 0=X, 1=Y',
            'POP P3',
            'POP P1',
            'MOV P0, MX',
            'CMP P1, 0',
            'JZ .mouse_pos_done',
            'MOV P0, MY',
            '.mouse_pos_done:',
            'PUSH P3',
            'RET',
        ],
        # --- Hardware state getters (read-only) ---
        # These mirror the mouse_read()/read_bank() convention: no arguments,
        # result written straight to P0 (the canonical 16-bit return register).
        'builtin_get_layer': [
            '; Returns the active graphics layer (VL register).',
            'MOV P0, VL', 'RET',
        ],
        'builtin_get_color': [
            '; Returns the current drawing color (VC register).',
            'MOV P0, VC', 'RET',
        ],
        'builtin_get_rtc': [
            '; RTC chunk readout: get_rtc(chunk) returns one 16-bit word of',
            '; the 32-bit seconds-since-epoch counter. chunk 0 = HIGH word',
            '; (C1), chunk 1 = LOW word (C0). C0/C1 are read-only, so the',
            '; call never disturbs its own result (same POP-P3/POP-P1 axis',
            '; pattern as builtin_mouse_pos).',
            'POP P3',
            'POP P1',
            'MOV P0, C1',
            'CMP P1, 0',
            'JZ .get_rtc_done',
            'MOV P0, C0',
            '.get_rtc_done:',
            'PUSH P3',
            'RET',
        ],
    }

    # Return types for builtin functions. Builtins are not registered in
    # self.functions (which only holds user-defined functions), so without
    # this table _cast_source_type cannot know that e.g. sin() returns a
    # float.  That gap caused mixed float/int expressions like
    # `sin(x * freq) * amplitude` to silently use integer MUL instead of
    # FMUL, producing wildly wrong results.
    BUILTIN_RETURN_TYPES: Dict[str, str] = {
        # --- Math: Q8.8 fixed-point trig/transcendental (float in/out) ---
        'sin': 'float', 'cos': 'float', 'atan': 'float',
        'asin': 'float', 'acos': 'float',
        'log': 'float', 'exp': 'float',
        # deg() takes plain degrees (int) and returns Q8.8 radians.
        'deg': 'float',
        # --- Math: integer-returning ---
        'tan': 'int',   # scaled by 1000, but integer domain
        'sqrt': 'int', 'rad': 'int',
        'floor': 'int', 'ceil': 'int', 'round': 'int',
        'trunc': 'int', 'intgr': 'int', 'frac': 'int',
        'abs': 'int', 'min': 'int', 'max': 'int',
        'clz': 'int', 'ctz': 'int', 'popcnt': 'int',
        'powr': 'int',
        # --- Graphics: void / status ---
        'set_mode': 'int', 'set_layer': 'int', 'set_pos': 'int',
        'write_screen': 'int', 'screen_fill': 'int', 'read_screen': 'int',
        'scroll_x': 'int', 'scroll_y': 'int',
        # Hardware state getters (VL/VC reads return integral ints; the RTC
        # chunks expose the RAW 16-bit words of a seconds counter, so they
        # are UNSIGNED -- a signed 'int' would ITOS a low word like 0x6417
        # (25623) as a negative number instead of its true magnitude).
        'get_layer': 'int', 'get_color': 'int', 'get_rtc': 'unsigned_int',
        # --- Keyboard / Mouse ---
        'key_available': 'int', 'key_read': 'int', 'key_clear': 'int',
        'key_count': 'int', 'key_ctrl': 'int', 'mouse_ctrl': 'int',
        'mouse_read': 'int', 'mouse_pos': 'int',
        # --- Random ---
        'random': 'int', 'random_range': 'int',
        # --- String (return type depends on the function) ---
        'strlen': 'int', 'strcmp': 'int', 'strfind': 'int', 'strfindi': 'int',
        # --- Serial ---
        'ser_out': 'int', 'ser_in': 'int', 'ser_stat': 'int', 'ser_ctrl': 'int',
        # --- Memory ---
        'memcpy': 'int', 'memset': 'int', 'memmove': 'int', 'memcmp': 'int',
        'memtest': 'int', 'memswap': 'int', 'peek': 'int', 'poke': 'int',
        'set_bank': 'int', 'read_bank': 'int',
        # --- Bit manipulation ---
        'btst': 'int', 'bset': 'int', 'bclr': 'int', 'bflip': 'int',
        # --- Misc ---
        'swap': 'int', 'xchng': 'int', 'nop': 'int',
        'pushf': 'int', 'popf': 'int', 'pusha': 'int', 'popa': 'int',
        'halt': 'int',
        # --- Interrupts ---
        'enable_interrupts': 'int', 'disable_interrupts': 'int',
        'software_int': 'int',
        # --- BCD ---
        'sed': 'int', 'cld': 'int', 'cla': 'int',
        'bcd2bin': 'int', 'bin2bcd': 'int',
        'bcdadd': 'int', 'bcdsub': 'int', 'bcda': 'int', 'bcds': 'int',
        'bcdcmp': 'int',
    }

    def __init__(self, enable_peephole: bool = True, debug_optimizations: bool = False,
                 enable_expr_simplify: bool = True, enable_live_range: bool = True,
                 enable_optimizations: bool = True,
                 enable_live_range_scheduling: Optional[bool] = None,
                 emit_all_builtins: bool = False,
                 memory_layout: str = 'default'):
        self.debug_optimizations = debug_optimizations
        self.opt_config = get_optimization_config()
        self.opt_config['debug_optimizations'] = debug_optimizations

        # Resolve the memory layout FIRST: every region constant below is read
        # from it, so a bad name must fail before anything is allocated.
        # 'default' reproduces the legacy addresses exactly; 'bank-safe' moves
        # runtime storage out of the 0x8000-0xBFFF bank window so programs can
        # switch banks (NovaDOS NDF disks). See MEMORY_LAYOUTS.
        self.memory_layout_name = memory_layout
        if memory_layout not in self.MEMORY_LAYOUTS:
            raise ValueError(
                f"Unknown memory layout '{memory_layout}'; expected one of "
                f"{sorted(self.MEMORY_LAYOUTS)}")
        layout = self.MEMORY_LAYOUTS[memory_layout]
        self.memory_layout = layout
        # Instance mirrors of the class constants: the constants stay as the
        # documented legacy defaults (tests introspect them), while generated
        # code reads these so the layout is actually selectable.
        self.code_org = int(layout['code_org'])
        self.global_region_start = int(layout['globals_start'])
        # Const-ROM window (Tier-2 item 5): unplaced `const` globals are
        # allocated sequentially here and emitted as initialized data with
        # the code image, so read-only tables are never mixed into the
        # writable global region.
        self.const_rom_start = int(layout['const_rom_start'])
        self.const_rom_end = int(layout['const_rom_end'])
        self.static_local_region_start = int(layout['static_locals_start'])
        self.static_local_region_end = int(layout['static_locals_end'])
        self.itos_buffer = int(layout['itos_buffer'])
        self.itob_buffer = int(layout['itob_buffer'])
        self.string_concat_buffers = tuple(layout['concat_buffers'])
        self.string_concat_buf_size = self.STRING_CONCAT_BUF_SIZE
        self.spill_region_start = int(layout['spill_start'])
        self.spill_region_end = int(layout['spill_end'])
        self.stack_floor = int(layout['stack_floor'])

        if enable_live_range_scheduling is not None:
            enable_live_range = enable_live_range_scheduling

        self.enable_optimizations = bool(enable_optimizations)
        if debug_optimizations:
            self.enable_optimizations = True

        self.enable_peephole = bool(enable_peephole)
        self.enable_expr_simplify = bool(enable_expr_simplify) and self.enable_optimizations
        self.enable_live_range = bool(enable_live_range) and self.enable_optimizations
        self.enable_live_range_scheduling = self.enable_live_range
        self.assembly = []
        self.enum_constants: Dict[str, int] = {}  # name -> value (from enum declarations)
        # Struct layouts: tag -> ordered field names. Every field is one
        # 16-bit word slot; field i lives at byte offset i*2.
        self.struct_defs: Dict[str, List[str]] = {}
        # Union layouts: tag -> ordered field names. All fields share byte
        # offset 0; the union size is the max field size (always 2 bytes
        # for int/struct fields).
        self.union_defs: Dict[str, List[str]] = {}
        # Type aliases: alias -> base_type (from typedef declarations).
        self.type_aliases: Dict[str, str] = {}
        self.global_vars = {}  # name -> {'address', 'type', 'size', 'is_array', 'count', 'init_values'}
        self.array_vars = {}   # per-function LOCAL arrays: name -> {'elem_type', 'count', 'elem_size', 'offset'}
        self.local_vars = {}
        self.var_types = {}  # name -> 'int' (16-bit, 2 bytes) or 'char' (8-bit)
        # const-enforcement tables. Global sets are filled by
        # _collect_storage_qualifiers; the per-function sets are rebuilt at
        # the top of every generate_function (methods included).
        self.const_globals = set()
        self.const_pointee_globals = set()
        # Next free address in the const-ROM window (0x0120+) and the
        # highest address any const global reached, used for the overflow
        # diagnostic in _allocate_globals.
        self._const_rom_next_addr = None
        self._const_rom_high_water = 0
        self._fn_const_names = set()
        self._fn_const_pointees = set()
        # Pointer-declared variables (`int *p`) and array parameters
        # (`void f(int arr[])`): both hold 16-bit addresses (2 bytes).
        self.pointer_vars: Set[str] = set()
        self.address_params: Set[str] = set()
        # Struct pointers (`struct Point *pp`): name -> struct tag, so
        # pp->field resolves the member offset through the pointee layout.
        self.pointer_struct_tags: Dict[str, str] = {}
        # Struct/union variables: name -> tag name. Used for struct assignment
        # detection (s1 = s2 copies all fields when both are the same tag).
        self.struct_tag_vars: Dict[str, str] = {}
        self.functions = {}
        # Storage-qualifier semantics carried from the parser into codegen:
        #   function_qualifiers[name] -> qualifier list on the FunctionDef
        #   global_qualifiers[name]   -> qualifier list on the global VarDecl
        #   volatile_vars             -> names that must stay memory-backed and
        #                                must never be folded/cached/CSE'd
        #   register_hint_vars        -> names that must not be spilled
        #   static_locals             -> persistent function-local storage keyed
        #                                by (function, name)
        #   extern_symbols            -> names imported from another object
        #                                (resolved by the linker/NOMF)
        #   object_mode               -> True when extern linkage forces
        #                                relocatable (.nobj) emission
        self.function_qualifiers: Dict[str, List[str]] = {}
        self.global_qualifiers: Dict[str, List[str]] = {}
        self.explicit_static_fn: Set[str] = set()
        self.explicit_extern_fn: Set[str] = set()
        self.extern_symbols: Set[str] = set()
        self.volatile_vars: Set[str] = set()
        self.register_hint_vars: Set[str] = set()
        self.static_locals: Dict[Tuple[str, str], Dict] = {}
        self._static_local_next_addr: int = self.static_local_region_start
        self.object_mode: bool = False
        self.strings = {}
        self.string_counter = 0
        self.label_counter = 0
        self.reg_counter = 0 
        self.current_function = None
        self.builtin_functions = self._init_builtins()
        # Next scratch buffer to allocate for a runtime string concat
        # ("a" + "b"). Reset per codegen run only (concat buffer scratch is
        # sequential at each call site, so a flat chain reuses one buffer
        # while nested right-hand concats advance through the table).
        self._concat_buf_index = 0
        # Labels of builtins actually referenced during code generation.
        # Only these get emitted into the output assembly (lazy linking).
        self.used_builtins: Set[str] = set()
        # When True, emit every builtin regardless of usage (--emit-all-builtins).
        self.emit_all_builtins = bool(emit_all_builtins)
        # Stack of (start_label, end_label) for break/continue support
        self.loop_stack = []
        
        # Access count tracking for hot variable optimization
        self.variable_access_counts: Dict[str, int] = Counter()
        # Spill allocations (var -> absolute memory address) determined by
        # the dynamic spill allocator. Populated during function generation.
        self.spill_allocations: Dict[str, int] = {}
        # Per-function zero-page spill base. The DynamicSpillAllocator assigns
        # addresses starting at a fixed base for EVERY function; since functions
        # call each other, two functions' spilled locals would collide at the
        # same zero-page address. Advance the base per function so each gets a
        # disjoint spill region.
        self._spill_window = self.spill_region_start
        # Spill window assigned to the function currently being generated
        # (None when the spill region is exhausted -> keep locals FP-relative).
        self._function_spill_base = None
        
        # Unified liveness tracking
        self.live_ranges: Dict[str, Tuple[int, int]] = {}  # name -> (start, end)
        self.live_at_point: Dict[int, Set[str]] = {}  # program_point -> set of live variables
        
        # Interference graph (tracks which variables cannot share registers)
        self.interference_graph: Dict[str, Set[str]] = {}  # variable -> set of interfering variables
        
        # Register allocation tracking
        self.register_usage: Dict[str, bool] = {
            'R0': False, 'R1': False, 'R2': False, 'R3': False, 'R4': False,
            'R5': False, 'R6': False, 'R7': False, 'R8': False, 'R9': False,
            'P0': False, 'P1': False, 'P2': False, 'P3': False, 'P4': False,
            'P5': False, 'P6': False, 'P7': False, 'SP': False, 'FP': False,
            'VX': False, 'VY': False, 'VM': False, 'VL': False, 'VC': False,
            'SA': False, 'SF': False, 'SV': False, 'SW': False,
            'TT': False, 'TM': False, 'TC': False, 'TS': False
        }
        
        # Preferred register order for allocation (P registers first for 16-bit, 
        # then R registers as fallback for 8-bit).
        # P3 is excluded (reserved for DIV remainder storage).
        self.allocation_order = [
            'P0', 'P1', 'P2', 'P4', 'P5', 'P6',
            'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9',
        ]
        
        # Variable register allocation (maps variable name to register)
        self.var_reg: Dict[str, str] = {}
        
        # Auto-free register set (registers freed after last use)
        self.auto_free_registers: Set[str] = set()
        
        # Register allocation statistics
        self.allocation_stats = {
            'total_allocations': 0,
            'total_deallocations': 0,
            'allocation_failures': 0,
            'max_simultaneous_allocated': 0
        }

    def _init_builtins(self) -> Dict[str, str]:
        # Initialize built-in function to assembly mappings
        return {
            # Graphics
            'set_mode': 'builtin_set_vmode', 'set_vmode': 'builtin_set_vmode',
            'set_layer': 'builtin_set_layer', 'set_pos': 'builtin_set_pos',
            'write_screen': 'builtin_write_screen', 'read_screen': 'builtin_read_screen',
            'get_layer': 'builtin_get_layer', 'get_color': 'builtin_get_color',
            'get_rtc': 'builtin_get_rtc',
            'screen_fill': 'builtin_screen_fill', 'sprite_blit': 'builtin_sprite_blit',
            'sprite_blitall': 'builtin_sprite_blitall',
            # scroll_x/scroll_y/roll_x/roll_y are dispatched to arity-specific
            # stubs at call sites (see ARITY_BUILTINS); these base labels cover
            # the 1-argument form scroll_x(layer).
            'scroll_x': 'builtin_scroll_x', 'scroll_y': 'builtin_scroll_y',
            'roll_x': 'builtin_roll_x', 'roll_y': 'builtin_roll_y',
            'draw_rect': 'builtin_draw_rect',
            'set_color': 'builtin_set_color',
            'vread': 'builtin_vread', 'vwrite': 'builtin_vwrite',
            'screen_rotate': 'builtin_screen_rotate', 'screen_shift': 'builtin_screen_shift',
            'screen_flip': 'builtin_screen_flip', 'draw_line': 'builtin_draw_line',
            'draw_circle': 'builtin_draw_circle', 'screen_invert': 'builtin_screen_invert',
            'screen_blit': 'builtin_screen_blit', 'set_blend_mode': 'builtin_set_blend_mode',
            'set_blend_alpha': 'builtin_set_blend_alpha',
            'draw_char': 'builtin_draw_char',
            'set_pointers': 'builtin_set_pointers', 'write_text': 'builtin_write_text',
            'set_font': 'builtin_set_font',
            'layer_swap': 'builtin_layer_swap', 'layer_move': 'builtin_layer_move',
            'layer_copy': 'builtin_layer_copy',
            # Sound
            'sound_play': 'builtin_sound_play',
            'sound_stop': 'builtin_sound_stop', 'sound_trigger': 'builtin_sound_trigger',
            'set_timer': 'builtin_set_timer',
            # Interrupts
            'sti': 'builtin_sti', 'cli': 'builtin_cli', 'iret': 'builtin_iret',
            'enable_interrupts': 'builtin_sti', 'disable_interrupts': 'builtin_cli',
            # software_int() raises a software interrupt via the INT opcode.
            # Distinct from int(), which is an identity conversion (see Math).
            'software_int': 'builtin_software_int',
            # Keyboard
            'key_available': 'builtin_key_available', 'key_read': 'builtin_key_read',
            'key_clear': 'builtin_key_clear', 'key_count': 'builtin_key_count',
            'key_ctrl': 'builtin_key_ctrl',
            # Mouse
            'mouse_read': 'builtin_mouse_read',
            'mouse_pos': 'builtin_mouse_pos',
            # Random
            'random': 'builtin_random',
            'random_range': 'builtin_random_range',
            # Math
            'abs': 'builtin_abs', 'min': 'builtin_min', 'max': 'builtin_max',
            'clz': 'builtin_clz', 'ctz': 'builtin_ctz', 'popcnt': 'builtin_popcnt',
            'sqrt': 'builtin_sqrt', 'log': 'builtin_log', 'exp': 'builtin_exp',
            'sin': 'builtin_sin', 'cos': 'builtin_cos', 'tan': 'builtin_tan',
            'atan': 'builtin_atan', 'asin': 'builtin_asin', 'acos': 'builtin_acos',
            'deg': 'builtin_deg', 'rad': 'builtin_rad',
            'floor': 'builtin_floor', 'ceil': 'builtin_ceil', 'round': 'builtin_round',
            'trunc': 'builtin_trunc', 'frac': 'builtin_frac', 'intgr': 'builtin_intgr',
            # int(x) is an identity conversion on 16-bit integer values
            # (distinct from intgr(), which truncates a fixed-point x/256).
            'int': 'builtin_int',
            'powr': 'builtin_powr',
            # String
            'strcpy': 'builtin_strcpy', 'strcat': 'builtin_strcat',
            'strcmp': 'builtin_strcmp', 'strlen': 'builtin_strlen',
            'strupr': 'builtin_strupr', 'strlwr': 'builtin_strlwr',
            'strrev': 'builtin_strrev', 'strfind': 'builtin_strfind',
            'strfindi': 'builtin_strfindi',
            # Serial
            'ser_out': 'builtin_ser_out', 'ser_in': 'builtin_ser_in',
            'ser_stat': 'builtin_ser_stat', 'ser_ctrl': 'builtin_ser_ctrl',
            # Memory
            'memcpy': 'builtin_memcpy', 'memset': 'builtin_memset',
            'memmove': 'builtin_memmove', 'memcmp': 'builtin_memcmp',
            'memtest': 'builtin_memtest', 'memswap': 'builtin_memswap',
            # Low-level byte memory access and bank-window control
            # (Star System kernel primitives: memory-as-file drivers and
            # the R: ramdisk both speak raw addresses and bank pages)
            'peek': 'builtin_peek', 'poke': 'builtin_poke',
            'peek2': 'builtin_peek2', 'poke2': 'builtin_poke2',
            'byte': 'builtin_byte',
            'set_bank': 'builtin_set_bank', 'read_bank': 'builtin_read_bank',
            # CPU/system register and stack access (systems tier 1). These are
            # volatile hardware views: the folding pass never touches them
            # (_fold_builtin_call is allowlist-based and they are not in it)
            # and FuncCall nodes are never entered into the CSE cache, so
            # every call re-reads live CPU state.
            'get_reg': 'builtin_get_reg', 'set_reg': 'builtin_set_reg',
            'get_rreg': 'builtin_get_rreg', 'set_rreg': 'builtin_set_rreg',
            'get_sp': 'builtin_get_sp', 'set_sp': 'builtin_set_sp',
            'get_fp': 'builtin_get_fp', 'set_fp': 'builtin_set_fp',
            'get_flags': 'builtin_get_flags', 'set_flags': 'builtin_set_flags',
            # Stack manipulation and cooperative task switching (systems
            # tier 2). push/pop are raw stack words; alloca grants frame-
            # lifetime scratch; task_spawn/task_switch implement symmetric
            # coroutines: a context is 22 ints (44 bytes) holding flags, FP,
            # a resume stack pointer, a resume PC parked on the task's own
            # stack, and all ten R plus eight P registers.
            'push': 'builtin_push', 'pop': 'builtin_pop',
            'alloca': 'builtin_alloca', 'stack_free': 'builtin_stack_free',
            'task_spawn': 'builtin_task_spawn',
            'task_switch': 'builtin_task_switch',
            # Bit manipulation
            'btst': 'builtin_btst', 'bset': 'builtin_bset',
            'bclr': 'builtin_bclr', 'bflip': 'builtin_bflip',
            # Misc
            'swap': 'builtin_swap', 'xchng': 'builtin_xchng',
            'nop': 'builtin_nop',
            'pushf': 'builtin_pushf', 'popf': 'builtin_popf',
            'pusha': 'builtin_pusha', 'popa': 'builtin_popa',
            'halt': 'builtin_halt',
            # BCD
            'sed': 'builtin_sed', 'cld': 'builtin_cld', 'cla': 'builtin_cla',
            'bcd2bin': 'builtin_bcd2bin', 'bin2bcd': 'builtin_bin2bcd',
            'bcdadd': 'builtin_bcdadd', 'bcdsub': 'builtin_bcdsub',
            'bcda': 'builtin_bcda', 'bcds': 'builtin_bcds',
            'bcdcmp': 'builtin_bcdcmp',
            # Mouse
            'mouse_ctrl': 'builtin_mouse_ctrl',
        }

    # Builtins whose implementation stub depends on the call-site argument
    # count (optional trailing arguments). Maps source name ->
    # {arg_count: implementation label}. An arity missing from the table
    # falls back to the base label from builtin_functions.
    ARITY_BUILTINS: Dict[str, Dict[int, str]] = {
        'scroll_x': {1: 'builtin_scroll_x', 2: 'builtin_scroll_x_2', 3: 'builtin_scroll_x_3'},
        'scroll_y': {1: 'builtin_scroll_y', 2: 'builtin_scroll_y_2', 3: 'builtin_scroll_y_3'},
        'roll_x': {1: 'builtin_roll_x', 2: 'builtin_roll_x_2', 3: 'builtin_roll_x_3'},
        'roll_y': {1: 'builtin_roll_y', 2: 'builtin_roll_y_2', 3: 'builtin_roll_y_3'},
    }

    def _resolve_builtin_label(self, name: str, arg_count: int) -> Optional[str]:
        """Pick the implementation label for a builtin call of this arity."""
        arity_table = self.ARITY_BUILTINS.get(name)
        if arity_table:
            return arity_table.get(arg_count) or self.builtin_functions.get(name)
        return self.builtin_functions.get(name)

    def _should_run_live_range_scheduler(self, assembly_lines: List[str]) -> Tuple[bool, str]:
        """Return whether the live-range scheduler is worth the compile-time cost."""
        line_count = len(assembly_lines)
        live_range_count = len(self.live_ranges)
        work_estimate = line_count * max(1, live_range_count)

        if line_count > self.LIVE_RANGE_SCHEDULER_MAX_LINES:
            return (
                False,
                f"line count {line_count} exceeds threshold {self.LIVE_RANGE_SCHEDULER_MAX_LINES}",
            )

        if work_estimate > self.LIVE_RANGE_SCHEDULER_MAX_WORK:
            return (
                False,
                f"work estimate {work_estimate} exceeds threshold {self.LIVE_RANGE_SCHEDULER_MAX_WORK} "
                f"({line_count} lines x {live_range_count} live ranges)",
            )

        return (
            True,
            f"within budget ({line_count} lines, {live_range_count} live ranges, work {work_estimate})",
        )

    def generate(self, ast: Program) -> List[str]:
        # Remember where the AST came from so codegen-phase diagnostics can
        # name the file and render source snippets.
        self.source_path = getattr(ast, 'source_path', None)
        self._diag_source_cache = None
        self.assembly.append("; Generated by the Astrid Compiler for Nova-16")
        # Adopt the parser's enum constant table so enum names resolve to
        # their integer values everywhere numbers are accepted.
        self.enum_constants = dict(getattr(ast, 'enum_constants', None) or {})
        # Adopt the parser's struct layout table so member accesses resolve
        # field offsets through their struct's definition.
        self.struct_defs = dict(getattr(ast, 'structs', None) or {})
        # Adopt the parser's union layout table. All union fields share byte
        # offset 0; member access resolves to the same base address.
        self.union_defs = dict(getattr(ast, 'union_defs', None) or {})
        # Adopt the parser's type alias table so typedef aliases resolve to
        # their base types during variable declaration code generation.
        self.type_aliases = dict(getattr(ast, 'type_aliases', None) or {})
        # Storage-qualifier intake before any optimization rewrite.  Runs
        # first so every later pass can consult the same linkage/memory
        # policy tables (extern/statics/volatile/register/inline).
        self._collect_storage_qualifiers(ast)
        # Run front-end expression simplifier (constant-folding, algebraic
        # simplifications, and CSE) to reduce register pressure and code size.
        if self.enable_optimizations and self.enable_expr_simplify:
            try:
                # Pre-scan for string/binary identifiers so the simplifier
                # can recognize '+' string concatenations and leave their
                # operand order (and CSE keys) untouched -- concatenation
                # is not commutative, and swapping `s + "lit"` into
                # `"lit" + s` silently reverses the runtime byte content.
                string_vars, string_funcs = self._collect_string_idents(ast)
                simplifier = ExpressionSimplifier(
                    debug=self.debug_optimizations,
                    string_vars=string_vars,
                    string_funcs=string_funcs,
                    # Volatile variables must not be constant-folded or CSE'd:
                    # each access must compile to a fresh memory load.
                    volatile_vars=frozenset(self.volatile_vars),
                )
                for func in ast.functions:
                    self._simplify_function_expressions(func, simplifier)
                if self.debug_optimizations:
                    print("[CODEGEN] Expression simplification applied to AST")
            except Exception:
                if self.debug_optimizations:
                    import traceback; traceback.print_exc()

        # Run function inlining pass (conservative) to eliminate small
        # call/return overhead and enable further optimizations. This must
        # run after expression simplification so constant-folding helps the
        # inliner decide eligibility.
        try:
            if self.enable_optimizations and self.opt_config.get('enable_function_inlining', True):
                inliner = FunctionInliner(
                    max_statements=self.opt_config.get('inlining_max_statements', 8),
                    min_call_sites=self.opt_config.get('inlining_min_call_sites', 2),
                    debug=self.debug_optimizations
                )
                # Analyze and inline; ast.functions is a list of FunctionDef
                try:
                    inlineable = inliner.analyze(ast.functions)
                    # Functions explicitly marked `inline` are force-inlined
                    # regardless of the conservative heuristic.
                    for func_def in ast.functions:
                        quals = list(getattr(func_def, 'qualifiers', []) or [])
                        if 'inline' in quals and func_def.name not in inlineable:
                            inlineable.add(func_def.name)
                    if inlineable and self.debug_optimizations:
                        print(f"[CODEGEN] Functions eligible for inlining: {inlineable}")
                except Exception:
                    # Some AST shapes may differ; fallback to conservative behavior
                    if self.debug_optimizations:
                        import traceback; traceback.print_exc()

                try:
                    ast.functions = inliner.inline_functions(ast.functions, inlineable if 'inlineable' in locals() else None)
                    if self.debug_optimizations:
                        print("[CODEGEN] Function inlining applied to AST")
                except Exception:
                    if self.debug_optimizations:
                        import traceback; traceback.print_exc()
        except Exception:
            if self.debug_optimizations:
                import traceback; traceback.print_exc()

        # Run strength reduction pass to convert multiplications by powers of 2
        # to left shifts for better performance. Applied after inlining so that
        # inlined multiply operations can be optimized.
        try:
            if self.enable_optimizations and self.opt_config.get('enable_strength_reduction', True):
                reducer = StrengthReducer(debug=self.debug_optimizations)
                for func in ast.functions:
                    func.body = reducer.reduce(func.body)
                if self.debug_optimizations:
                    print("[CODEGEN] Strength reduction applied to AST")
        except Exception:
            if self.debug_optimizations:
                import traceback; traceback.print_exc()

        # Allocate global variables (scalars and arrays) at fixed addresses
        # in the dedicated global region so code can reference them directly.
        self._allocate_globals(ast)

        # Pre-register ALL user functions before generating any bodies so
        # forward references (calls to functions defined later in the source,
        # or declared via C-style prototypes) resolve correctly.  Qualifier
        # tables are refreshed here as well (generate() may be called on an
        # AST whose qualifiers were attached after intake, e.g. by tests).
        for func_def in ast.functions:
            quals = list(getattr(func_def, 'qualifiers', []) or [])
            if quals:
                self.function_qualifiers.setdefault(func_def.name, quals)
            if 'extern' in quals:
                self.extern_symbols.add(func_def.name)
                self.explicit_extern_fn.add(func_def.name)
            if 'static' in quals:
                self.explicit_static_fn.add(func_def.name)
            self.functions[func_def.name] = self._function_signature(
                func_def, f'func_{func_def.name}')
        # Pre-register impl-block methods under namespaced keys
        # "TypeName::method" so `p.method()` call sites resolve. Method
        # labels are namespaced too (func_TypeName_method), allowing two
        # structs to share a method name without label collisions. A regular
        # function may not reuse a namespaced method label.
        used_labels = {v['label'] for v in self.functions.values()}
        for block in getattr(ast, 'impl_blocks', None) or []:
            for method in block.methods:
                key = f'{block.tag}::{method.name}'
                if key in self.functions:
                    raise CodeGenError(
                        f"Duplicate method '{method.name}' for type "
                        f"'{block.tag}'",
                        hint=(f"rename one of the methods, or remove the "
                              f"duplicate `impl {block.tag}` block"),
                        source_text=self._diag_source_text())
                method_label = f'func_{block.tag}_{method.name}'
                if method_label in used_labels:
                    raise CodeGenError(
                        f"Method label '{method_label}' collides with an "
                        f"existing function",
                        hint=('method names are emitted as '
                              '`func_TypeName_method`; rename the method or '
                              'the colliding function'))
                used_labels.add(method_label)
                self.functions[key] = self._function_signature(
                    method, method_label)
                method.impl_tag = block.tag

        # Emit object prologue (GLOBAL / EXTERN directives + main entry stub).
        self._emit_object_prologue(ast)

        # Generate all functions and data AFTER interrupt vector.
        for func_def in ast.functions:
            self.generate_function_with_diagnostics(func_def)

        # Generate impl-block method bodies (namespaced labels).
        for block in getattr(ast, 'impl_blocks', None) or []:
            for method in block.methods:
                self.generate_function_with_diagnostics(method)

        self.generate_strings()
        self.generate_builtins()
        self._emit_globals_data()

        assembly_output = "\n".join(self.assembly)
        assembly_lines = assembly_output.splitlines()

        if self.enable_optimizations and self.enable_live_range:
            schedule_decision, schedule_reason = self._should_run_live_range_scheduler(
                assembly_lines,
            )
            if schedule_decision:
                try:
                    from astrid.codegen.live_range_scheduler import LiveRangeScheduler

                    scheduler = LiveRangeScheduler(debug=self.debug_optimizations)
                    assembly_lines = scheduler.schedule(
                        assembly_lines, self.live_ranges,
                    )
                    if self.debug_optimizations:
                        print("[CODEGEN] Live-range scheduling applied")
                except Exception:
                    if self.debug_optimizations:
                        import traceback

                        traceback.print_exc()
            elif self.debug_optimizations:
                print(f"[CODEGEN] Skipping live-range scheduling: {schedule_reason}")

        if self.enable_optimizations and self.enable_peephole:
            from astrid.codegen.peephole import PeepholeOptimizer

            peephole_opt = PeepholeOptimizer(debug=self.debug_optimizations)
            assembly_output = peephole_opt.optimize("\n".join(assembly_lines))
            assembly_lines = assembly_output.splitlines()

            if self.debug_optimizations:
                print("[CODEGEN] Peephole optimization applied")
                print(
                    "[CODEGEN] Original: "
                    f"{len(self.assembly)} lines, Optimized: {len(assembly_lines)} lines"
                )

        return assembly_lines

    def _assembly_symbol(self, kind: str, name: str) -> str:
        """Map a source-level linkage name to its assembly label.

        Functions emit as ``func_<name>``; globals emit as ``gvar_<name>``.
        Extern references use the same label the defining unit exports, so
        the linker can resolve the relocation.
        """
        if kind == 'function':
            return f"func_{name}"
        return f"gvar_{name}"

    def _object_linkage_names(self, ast: Program) -> Dict[str, List[str]]:
        """Compute GLOBAL exports / EXTERN imports for this unit.

        Defined non-static functions and non-static, non-extern globals are
        exported (GLOBAL); referenced-but-undefined symbols are declared
        EXTERN.  Static functions/globals stay file-local (no export).  The
        names use the emitted assembly labels (``func_*`` / ``gvar_*``) so
        the new assembler's object mode converts symbol-relative operands
        into NOMF relocation records the linker resolves.
        """
        if not self.object_mode:
            return {"exports": [], "imports": []}

        exported_funcs = sorted(
            func_def.name for func_def in ast.functions
            if 'static' not in list(getattr(func_def, 'qualifiers', []) or []))
        exported_globals = sorted(
            name for name in self.global_vars
            if 'static' not in list(self.global_qualifiers.get(name, []))
            and name not in self.extern_symbols)
        imports = sorted(
            name for name in self.extern_symbols
            if name not in self.global_vars
            and name not in {f.name for f in ast.functions})
        exports = ([self._assembly_symbol('function', n) for n in exported_funcs]
                   + [self._assembly_symbol('global', n) for n in exported_globals])
        import_labels = [
            self._assembly_symbol(
                'function' if name in self.explicit_extern_fn else 'global', name)
            for name in imports]
        return {'exports': exports, 'imports': import_labels}

    def _emit_object_prologue(self, ast: Program) -> None:
        """Emit the object prologue: GLOBAL/EXTERN linkage directives and the
        absolute start stub (ORG 0x1000 + start label + CALL main + HLT).

        This is the ONLY place that writes the prologue.  The caller (generate)
        is responsible for emitting functions, strings, builtins, and globals
        AFTER this method returns.
        """
        # Emit GLOBAL / EXTERN directives for object mode.  In single-file
        # mode (_object_linkage_names returns empty), nothing is emitted.
        object_names = self._object_linkage_names(ast)
        for name in object_names['exports']:
            self.assembly.append(f"GLOBAL {name}")
        for name in object_names['imports']:
            self.assembly.append(f"EXTERN {name}")
        if object_names['exports'] or object_names['imports']:
            self.assembly.append("")

        # Main entry point MUST be first segment so emulator sets PC correctly.
        # Astrid stays a single-image compiler: every unit emits the legacy
        # absolute program (start stub + ORG'd code/data) byte-for-byte.
        self.assembly.append("ORG 0x1000")
        self.assembly.append("start:")
        self.assembly.append("    MOV SP, 0xFFFF ; Set stack pointer to high memory")
        self.assembly.append("    MOV FP, 0xFFFF ; Also init frame pointer")
        self.assembly.append("    CALL func_main")
        self.assembly.append("    HLT")
        self.assembly.append("")

        # Emit interrupt vectors at 0x0100 (before functions).
        # Collect all interrupt handlers: those declared with interrupt(N)
        # and the deprecated timer_interrupt name (vector 0).
        _vector_table = {}  # vector_number -> func_name
        for _func in ast.functions:
            _vec = getattr(_func, 'interrupt_vector', None)
            if _vec is not None:
                if _vec in _vector_table:
                    raise CodeGenError(
                        f"interrupt vector {_vec} assigned to both "
                        f"'{_vector_table[_vec]}' and '{_func.name}'")
                _vector_table[_vec] = _func.name
            elif _func.name == 'timer_interrupt' and not getattr(
                    _func, 'impl_tag', None):
                if 0 in _vector_table:
                    raise CodeGenError(
                        "interrupt vector 0 assigned to both "
                        f"'{_vector_table[0]}' and 'timer_interrupt'")
                _vector_table[0] = 'timer_interrupt'
        if _vector_table:
            if self.object_mode:
                _names = ', '.join(f"'{n}' (vector {v})"
                                   for v, n in sorted(_vector_table.items()))
                raise CodeGenError(
                    "interrupt handlers cannot be linked as a relocatable "
                    f"object: {_names}. Interrupt vectors require fixed ORG "
                    "0x0100 placement",
                    hint="drop 'extern' from this unit or compile it standalone")
            self.assembly.append("ORG 0x0100")
            # The interrupt vector table occupies 0x0100-0x011F: 8 slots of
            # 4 bytes each, so vector N's slot starts at address 0x0100 + 4*N.
            # Each DW below is 2 bytes, so pad with DS so every handler lands
            # in the correct slot (vector 0 at 0x0100, vector 2 at 0x0108,
            # etc.). Without this padding all entries pile up at 0x0100 and
            # only vector 0 ever dispatches correctly.
            _last_offset = 0
            for _vec_num, _func_name in sorted(_vector_table.items()):
                _target = 4 * _vec_num
                if _target > _last_offset:
                    self.assembly.append(f"    DS {_target - _last_offset}")
                _label = f"func_{_func_name}"
                self.assembly.append(f"    DW {_label}  ; vector {_vec_num}")
                _last_offset = _target + 2
            # Skip past the interrupt vector table (0x0100-0x011F, 8 vectors x 4 bytes).
            # WHY: code must resume ABOVE the 0x1000 start stub (15 bytes:
            # MOV SP / MOV FP / CALL main / HLT). The old ORG 0x0120 restarted
            # code below the stub, so any ISR program longer than ~3.8KB
            # overwrote the stub at 0x1000 and the emulator crashed at
            # PC 0x1001 with `Unknown opcode: F8` (NovaDOS kernel = 5033B).
            # 0x1100 leaves a 241-byte gap after the stub, keeps handlers in
            # low RAM, and stays far below globals (0x8000) and spills
            # (0xC000+). Non-ISR programs are unaffected (functions follow
            # the stub sequentially without an explicit ORG).
            self.assembly.append(f"ORG 0x{self.code_org:04X}")
            self.assembly.append("")

    # ------------------------------------------------------------------
    # Storage-qualifier intake and linkage policy
    # ------------------------------------------------------------------
    def _collect_storage_qualifiers(self, ast: Program) -> None:
        """Derive linkage/memory policy from parser-retained qualifiers.

        Nova-16 is single-image by default, so qualifiers must preserve the
        legacy single-file runtime while exposing real linker/NOMF semantics
        once an object boundary exists:

          extern global/function -> imported symbol (EXTERN + relocation);
                                    never allocated/emitted locally.
          static global/function -> file-local linkage; block-local statics
                                    become persistent global-backed storage.
          inline function        -> force-inline hint to FunctionInliner.
          register local/param   -> keep in registers; never spill.
          volatile var           -> memory-backed; reads/writes always touch
                                    memory and are never folded/cached.
          const                  -> read-only storage: direct assignments,
                                    ++/--, and writes through a const
                                    pointee are compile errors; unplaced
                                    const globals emit into the code
                                    region (ROM tables).

        The parser keeps every qualifier on VarDecl.qualifiers /
        FunctionDef.qualifiers; this intake centralizes them into codegen
        tables before optimization passes run.
        """
        self.function_qualifiers = {}
        self.global_qualifiers = {}
        self.explicit_static_fn = set()
        self.explicit_extern_fn = set()
        self.extern_symbols = set()
        self.volatile_vars = set()
        self.register_hint_vars = set()
        self.static_locals = {}
        # Rebuilt from scratch (generate() may run more than once on one
        # generator, e.g. from tools that re-compile the same AST).
        self.const_globals = set()
        self.const_pointee_globals = set()
        self._const_rom_next_addr = None
        self._const_rom_high_water = 0
        self.object_mode = False

        for decl in list(getattr(ast, 'globals', None) or []):
            quals = list(getattr(decl, 'qualifiers', []) or [])
            if not quals:
                continue
            self.global_qualifiers[decl.name] = quals
            if 'volatile' in quals:
                self.volatile_vars.add(decl.name)
            if 'register' in quals:
                self.register_hint_vars.add(decl.name)
            if 'const' in quals:
                if getattr(decl, 'pointer_depth', 0):
                    # `const T *p`: the pointee is read-only; p itself stays
                    # rebindable (C's pointer-to-const).
                    self.const_pointee_globals.add(decl.name)
                else:
                    self.const_globals.add(decl.name)
            if 'extern' in quals:
                self.extern_symbols.add(decl.name)
                # Single-file backward compatibility: do not force object mode
                # for extern variables.  They are still recorded in
                # extern_symbols for potential future linking, but a program
                # whose only "extern" references are variable declarations still
                # compiles and runs as a standalone image.
                self.object_mode = False

        for func_def in list(getattr(ast, 'functions', None) or []):
            quals = list(getattr(func_def, 'qualifiers', []) or [])
            if not quals:
                continue
            self.function_qualifiers[func_def.name] = quals
            if 'static' in quals:
                self.explicit_static_fn.add(func_def.name)
            if 'extern' in quals:
                self.explicit_extern_fn.add(func_def.name)
                self.extern_symbols.add(func_def.name)
                self.object_mode = True
            for param in list(getattr(func_def, 'params', None) or []):
                pquals = list(getattr(param, 'qualifiers', []) or [])
                if 'volatile' in pquals:
                    self.volatile_vars.add(param.name)
                if 'register' in pquals:
                    self.register_hint_vars.add(param.name)

        for block in list(getattr(ast, 'impl_blocks', None) or []):
            for method in list(getattr(block, 'methods', None) or []):
                quals = list(getattr(method, 'qualifiers', []) or [])
                if not quals:
                    continue
                key = f"{block.tag}::{method.name}"
                self.function_qualifiers[key] = quals

        # Volatile LOCALS: scan function bodies (including impl methods) for
        # VarDecl nodes carrying 'volatile'. Locals declared inside function
        # bodies are not part of ast.globals and never reach the param scan
        # above, so without this they would silently miss the volatile
        # contract and get register- or spill-allocated.
        for func_def in list(getattr(ast, 'functions', None) or []):
            self._collect_volatile_locals(func_def)
        for block in list(getattr(ast, 'impl_blocks', None) or []):
            for method in list(getattr(block, 'methods', None) or []):
                self._collect_volatile_locals(method)

    def _collect_volatile_locals(self, func_def) -> None:
        """Recursively register 'volatile' local VarDecls in a function body."""
        def walk(stmts):
            for node in stmts or []:
                if isinstance(node, list):
                    walk(node)
                elif isinstance(node, VarDecl):
                    if 'volatile' in list(getattr(node, 'qualifiers', []) or []):
                        self.volatile_vars.add(node.name)
                elif isinstance(node, If):
                    walk(node.then_body)
                    if node.else_body is not None:
                        walk(node.else_body)
                elif isinstance(node, (While, DoWhile)):
                    walk(node.body)
                elif isinstance(node, For):
                    if isinstance(node.init, list):
                        walk(node.init)
                    walk(node.body)
                elif isinstance(node, Switch):
                    for case in node.cases:
                        walk(case.body)
                    if node.default_body is not None:
                        walk(node.default_body)
                elif isinstance(node, Label):
                    if node.stmt is not None:
                        walk([node.stmt])
        walk(getattr(func_def, 'body', None))

    def _collect_string_idents(self, ast: Program) -> Tuple[Set[str], Set[str]]:
        """Pre-scan the AST for string/binary identifiers.

        The ExpressionSimplifier must never reorder the operands of a '+'
        whose result is a string value (concatenation is not commutative),
        so it needs to know which identifiers hold string/binary values and
        which functions return them.  Returns (string_var_names,
        string_func_names).

        The scan is deliberately conservative in both directions:
        * Scalar variables declared `string`/`binary` count; pointers
          (`string *p`) and arrays of strings (`string arr[4]`) do not --
          those identifiers decay to addresses, and address arithmetic with
          '+' stays safely commutative.
        * Names are collected program-wide (a local `int x` in one function
          may share its name with a `string x` elsewhere).  Over-approximating
          only disables an operand swap for an unrelated numeric expression,
          which is harmless; missing a real string identifier would be a
          correctness bug.
        """
        string_types = ('string', 'binary')
        string_vars: Set[str] = set()
        string_funcs: Set[str] = set()

        def visit(node) -> None:
            if node is None:
                return
            if isinstance(node, (list, tuple)):
                for child in node:
                    visit(child)
                return
            if isinstance(node, VarDecl):
                # Scalar string/binary variables only: pointers and arrays
                # hold addresses, and address '+' arithmetic is commutative.
                if (getattr(node, 'var_type', None) in string_types
                        and not getattr(node, 'pointer_depth', 0)
                        and getattr(node, 'array_size', None) is None):
                    string_vars.add(node.name)
                # Initializer expressions may themselves declare nothing,
                # but keep recursing for locals declared inside nested
                # control-flow bodies and for struct member initializers.
            elif isinstance(node, FunctionDef):
                if getattr(node, 'return_type', None) in string_types:
                    string_funcs.add(node.name)
            # Recurse into every child attribute so locals inside
            # if/while/for/switch bodies and impl-block methods are seen.
            for child in vars(node).values() if hasattr(node, '__dict__') else ():
                if isinstance(child, (list, tuple)):
                    for item in child:
                        visit(item)
                else:
                    visit(child)

        visit(ast)
        return string_vars, string_funcs

    def _simplify_function_expressions(self, func: FunctionDef, simplifier: ExpressionSimplifier):
        """Walk a function AST and simplify expression nodes in-place."""
        def simplify_node(node):
            if node is None:
                return None
            if isinstance(node, (Number, Identifier, StringLiteral, CharLiteral, BinaryOp, UnaryOp, PostfixOp, FuncCall, Cast)):
                return simplifier.simplify(node)
            # Newer expression/statement nodes: recurse manually since the
            # shared ExpressionSimplifier does not know their shape.
            if isinstance(node, ArrayAccess):
                node.index = simplify_node(node.index)
                if node.index2 is not None:
                    node.index2 = simplify_node(node.index2)
                return node
            if isinstance(node, StringIndexAccess):
                node.index = simplify_node(node.index)
                return node
            if isinstance(node, MemberAccess):
                # Simplify the base chain in place; field names are plain
                # identifiers with nothing to fold.
                node.base = simplify_node(node.base) or node.base
                return node
            if isinstance(node, MethodCall):
                # Simplify method-call arguments in place (the receiver chain
                # and method name are plain identifiers / field names).
                node.args = [simplify_node(a) for a in node.args]
                return node
            if isinstance(node, ArrayAssignment):
                node.target.index = simplify_node(node.target.index)
                if node.target.index2 is not None:
                    node.target.index2 = simplify_node(node.target.index2)
                node.value = simplify_node(node.value)
                return node
            if isinstance(node, MemberAssignment):
                node.value = simplify_node(node.value)
                return node
            if isinstance(node, TernaryOp):
                node.cond = simplify_node(node.cond)
                node.then_expr = simplify_node(node.then_expr)
                node.else_expr = simplify_node(node.else_expr)
                return node
            if isinstance(node, PrefixOp):
                node.operand = simplify_node(node.operand)
                return node
            if isinstance(node, VarDecl):
                if node.value is not None:
                    node.value = simplify_node(node.value)
                return node
            if isinstance(node, Assignment):
                node.value = simplify_node(node.value)
                return node
            if isinstance(node, Return):
                if node.value is not None:
                    node.value = simplify_node(node.value)
                return node
            if isinstance(node, If):
                node.cond = simplify_node(node.cond)
                node.then_body = [simplify_node(n) or n for n in node.then_body]
                if node.else_body:
                    node.else_body = [simplify_node(n) or n for n in node.else_body]
                return node
            if isinstance(node, While):
                node.cond = simplify_node(node.cond)
                node.body = [simplify_node(n) or n for n in node.body]
                return node
            if isinstance(node, DoWhile):
                node.cond = simplify_node(node.cond)
                node.body = [simplify_node(n) or n for n in node.body]
                return node
            if isinstance(node, For):
                if node.init is not None:
                    if isinstance(node.init, list):
                        node.init = [simplify_node(n) or n for n in node.init]
                    else:
                        node.init = simplify_node(node.init)
                if node.cond is not None:
                    node.cond = simplify_node(node.cond)
                if node.update is not None:
                    node.update = simplify_node(node.update)
                node.body = [simplify_node(n) or n for n in node.body]
                return node
            if isinstance(node, Switch):
                node.expr = simplify_node(node.expr)
                for case in node.cases:
                    case.value = simplify_node(case.value)
                    case.body = [simplify_node(n) or n for n in case.body]
                if node.default_body:
                    node.default_body = [simplify_node(n) or n for n in node.default_body]
                return node
            if isinstance(node, list):
                return [simplify_node(n) or n for n in node]
            return node

        func.body = [simplify_node(n) or n for n in func.body]

    def generate_strings(self):
        if not self.strings:
            return
        self.assembly.append(";")
        self.assembly.append("; Data Section")
        self.assembly.append(";")
        for value, label in self.strings.items():
            self.assembly.append(f"{label}: DEFSTR \"{value}\"")
        self.assembly.append("")

    def find_local_vars(self, statements: List) -> List[VarDecl]:
        # Recursively find all VarDecl nodes in a list of statements.
        decls = []
        for stmt in statements:
            if isinstance(stmt, VarDecl):
                decls.append(stmt)
            elif isinstance(stmt, list):
                decls.extend(self.find_local_vars(stmt))
            elif isinstance(stmt, If):
                decls.extend(self.find_local_vars(stmt.then_body))
                if stmt.else_body:
                    decls.extend(self.find_local_vars(stmt.else_body))
            elif isinstance(stmt, While):
                decls.extend(self.find_local_vars(stmt.body))
            elif isinstance(stmt, DoWhile):
                decls.extend(self.find_local_vars(stmt.body))
            elif isinstance(stmt, For):
                if isinstance(stmt.init, list):
                    decls.extend(stmt.init)
                decls.extend(self.find_local_vars(stmt.body))
            elif isinstance(stmt, Switch):
                for case in stmt.cases:
                    decls.extend(self.find_local_vars(case.body))
                if stmt.default_body:
                    decls.extend(self.find_local_vars(stmt.default_body))
        return decls

    def _var_size(self, name: str) -> int:
        # Return storage size in bytes for a variable.
        # 2 bytes for int/string/binary (16-bit values/addresses), 1 for char.
        # Pointers and array parameters always occupy 2 bytes (an address).
        if name in self.pointer_vars or name in self.address_params:
            return 2
        return 2 if self.var_types.get(name) in ('int', 'signed_int', 'unsigned_int', 'string', 'binary', 'float') else 1

    def _is_int_var(self, name: str) -> bool:
        return self.var_types.get(name) in ('int', 'signed_int', 'unsigned_int')

    def _get_local_offset(self, name: str) -> int:
        offset = self.local_vars[name]['offset']
        return offset

    def _emit_local_load(self, reg: str, name: str):
        offset = self._get_local_offset(name)
        var_size = self._var_size(name)
        # Record access for hot-variable optimization.
        self.variable_access_counts[name] += 1
        # Static locals live at a fixed absolute address (not on the stack).
        static_addr = self.local_vars.get(name, {}).get('static_addr')
        if static_addr is not None:
            self.emit(f"    MOV {reg}, [0x{static_addr:04X}]")
            return
        # If this local was migrated to a spill allocation, load from that
        # absolute address instead of the frame pointer slot. Do NOT do this
        # for `timer_interrupt` (uses SP-relative locals).
        if name in self.spill_allocations and not self._is_interrupt_handler:
            addr = self.spill_allocations[name]
            self.emit(f"    MOV {reg}, [0x{addr:04X}]")
            return
        if self._is_interrupt_handler:
            # Interrupt handler uses SP-relative locals (no ENTER/FP).
            # After "SUB SP, N", the first local (offset=-size) is at SP+0,
            # the second (offset=-2*size) is at SP+size, etc.
            # In general the byte offset from SP is: -(offset) - var_size.
            sp_offset = -offset - var_size
            self.emit(f"    MOV {reg}, [SP+{sp_offset}]")
        else:
            # Use [FP+offset] direct indexed addressing. This avoids
            # clobbering P2, which get_register() may have already
            # allocated as an expression temporary.
            self.emit(f"    MOV {reg}, [FP{offset:+d}]")

    def _emit_local_store(self, name: str, src_reg: str):
        offset = self._get_local_offset(name)
        var_size = self._var_size(name)
        # Record access frequency for hot-variable optimization.
        self.variable_access_counts[name] += 1
        # Static locals live at a fixed absolute address (not on the stack).
        static_addr = self.local_vars.get(name, {}).get('static_addr')
        if static_addr is not None:
            self.emit(f"    MOV [0x{static_addr:04X}], {src_reg}")
            return
        # If this local was migrated to a spill allocation, store to that
        # absolute address instead of the frame pointer slot. Do NOT do this
        # for `timer_interrupt` (uses SP-relative locals).
        if name in self.spill_allocations and not self._is_interrupt_handler:
            addr = self.spill_allocations[name]
            self.emit(f"    MOV [0x{addr:04X}], {src_reg}")
            return
        if self._is_interrupt_handler:
            # Interrupt handler uses SP-relative locals (no ENTER/FP) — see
            # _emit_local_load for the offset formula.
            sp_offset = -offset - var_size
            self.emit(f"    MOV [SP+{sp_offset}], {src_reg}")
        else:
            # Use [FP+offset] direct indexed addressing. This avoids
            # clobbering P2, which get_register() may have already
            # allocated as an expression temporary.
            self.emit(f"    MOV [FP{offset:+d}], {src_reg}")

    # ------------------------------------------------------------------
    # Globals, arrays, ternary, and prefix ++/-- support
    # ------------------------------------------------------------------

    def _elem_size(self, var_type: str) -> int:
        # Storage size in bytes for one element of the given type.
        # Struct fields are word slots, so a struct element is also 2 bytes.
        return 2 if var_type in ('int', 'signed_int', 'unsigned_int', 'string', 'binary', 'float', 'struct') else 1

    # ------------------------------------------------------------------
    # Struct layout and member access support
    # ------------------------------------------------------------------

    def _struct_fields(self, tag: str) -> List[str]:
        """Return the field names for a struct or union tag.

        The stored format is a list of (name, type) tuples so the codegen
        can also resolve per-field types; this helper extracts names for
        callers that only need the ordering / count.
        """
        fields = self.struct_defs.get(tag)
        if fields is None:
            fields = self.union_defs.get(tag)
        if fields is None:
            raise NameError(f"Undefined struct/union type '{tag}'")
        return [f[0] if isinstance(f, tuple) else f for f in fields]

    def _struct_field_type(self, tag: str, field: str) -> Optional[str]:
        """Return the declared type of a struct or union field ('int', 'char',
        'float', 'string', 'binary'), or None if not found."""
        fields = self.struct_defs.get(tag)
        if fields is None:
            fields = self.union_defs.get(tag)
        if fields is None:
            return None
        for entry in fields:
            if isinstance(entry, tuple):
                fname, ftype = entry
            else:
                # Backwards-compatible: bare name (treat as 'int').
                fname, ftype = entry, 'int'
            if fname == field:
                return ftype
        return None

    def _field_type_size_words(self, ftype: str,
                               _seen: Optional[frozenset] = None) -> int:
        """Storage footprint of one struct/union field type, in WORDS.

        Scalar slots are exactly one 16-bit word (chars are word-padded,
        mirroring how locals are laid out). A nested-aggregate field
        ('struct Tag' / 'union Tag') occupies as many words as the inner
        layout contains. Recursion is guarded against direct and indirect
        self-reference cycles (which the parser rejects at definition
        time, but the guard keeps a pathological .sym table or a hostile
        caller from hanging the compiler).
        """
        if not (ftype.startswith('struct ') or ftype.startswith('union ')):
            return 1
        member_kind, member_tag = ftype.split(' ', 1)
        seen = _seen or frozenset()
        if member_tag in seen:
            raise NameError(
                f"Circular {member_kind} '{member_tag}' in nested layout")
        if member_kind == 'struct':
            fields = self.struct_defs.get(member_tag)
        else:
            fields = self.union_defs.get(member_tag)
        if fields is None:
            raise NameError(
                f"Undefined {member_kind} type '{member_tag}' in nested layout")
        if member_kind == 'union':
            return max((self._field_type_size_words(
                            f[1] if isinstance(f, tuple) else 'int',
                            seen | {member_tag})
                        for f in fields), default=1)
        return sum((self._field_type_size_words(
                        f[1] if isinstance(f, tuple) else 'int',
                        seen | {member_tag})
                    for f in fields), 0)

    def _struct_size(self, tag: str) -> int:
        """Total byte size of one struct or union value.

        For structs, the sum of the member footprints: each scalar field is
        one word slot (2 bytes) and each nested-aggregate field occupies its
        inner layout's word count. For unions, all fields overlap at offset
        0, so the size is the largest member footprint.
        """
        if self._is_union_type(tag):
            fields = self.union_defs.get(tag, [])
            words = max((self._field_type_size_words(
                             f[1] if isinstance(f, tuple) else 'int')
                         for f in fields), default=1)
            return words * 2
        fields = self.struct_defs.get(tag)
        if fields is None:
            raise NameError(f"Undefined struct/union type '{tag}'")
        words = sum((self._field_type_size_words(
                         f[1] if isinstance(f, tuple) else 'int')
                     for f in fields), 0)
        return words * 2

    def _struct_field_offset(self, tag: str, field: str) -> int:
        """Byte offset of a field within the struct or union, or a clear error.

        For structs, the offset is the accumulated footprint of the preceding
        fields: each scalar takes one word slot (2 bytes) and each
        nested-aggregate field takes its inner layout's word count. For
        unions, all fields share byte offset 0.
        """
        if self._is_union_type(tag):
            return self._union_field_offset(tag, field)
        fields = self.struct_defs.get(tag)
        if fields is None:
            raise NameError(f"Undefined struct/union type '{tag}'")
        offset_words = 0
        for entry in fields:
            if isinstance(entry, tuple):
                fname, ftype = entry
            else:
                # Backwards-compatible: bare name (treat as 'int').
                fname, ftype = entry, 'int'
            if fname == field:
                return offset_words * 2
            offset_words += self._field_type_size_words(ftype)
        field_names = [f[0] if isinstance(f, tuple) else f for f in fields]
        raise NameError(
            f"Struct '{tag}' has no field '{field}' "
            f"(fields: {', '.join(field_names)})")

    def _resolve_type(self, name: str) -> str:
        """Resolve a type name through typedef aliases to its base type.

        If 'name' is a typedef alias, follow the chain until a base type
        ('int', 'char', 'struct Tag', etc.) is found. Non-alias names are
        returned unchanged.
        """
        seen = set()
        current = name
        while current in self.type_aliases and current not in seen:
            seen.add(current)
            current = self.type_aliases[current]
        return current

    def _is_union_type(self, tag: str) -> bool:
        """Return True if 'tag' names a union type."""
        return tag in self.union_defs

    def _union_field_offset(self, tag: str, field: str) -> int:
        """Byte offset of a field within a union (always 0)."""
        fields = self.union_defs.get(tag)
        if fields is None:
            raise NameError(f"Undefined union type '{tag}'")
        field_names = [f[0] if isinstance(f, tuple) else f for f in fields]
        if field not in field_names:
            raise NameError(
                f"Union '{tag}' has no field '{field}' "
                f"(fields: {', '.join(field_names)})")
        return 0  # All union fields share byte offset 0

    def _aggregate_field_offset(self, tag: str, field: str, is_union: bool = False) -> int:
        """Byte offset for a field in either a struct or union."""
        if is_union:
            return self._union_field_offset(tag, field)
        return self._struct_field_offset(tag, field)

    def _var_struct_tag(self, name: str) -> Optional[str]:
        """Struct tag for a declared struct variable/pointer/array, if any."""
        info = self.array_vars.get(name)
        if info and info.get('tag'):
            return info['tag']
        g = self.global_vars.get(name)
        if g and g.get('tag'):
            return g['tag']
        return self.pointer_struct_tags.get(name)

    def _struct_field_info(self, tag: str, field: str) -> Tuple[int, str]:
        """Byte offset and type key of a field within a struct or union.

        Returns ``(byte_offset, field_type_key)``.  Struct fields accumulate
        the real footprint of the preceding fields (a nested aggregate spans
        several words), while every union field shares byte offset 0.

        For nested aggregations the type key is the inner struct/union's
        **bare tag** (without the ``'struct '`` / ``'union '`` prefix) so the
        ``a.b.c`` chain walker can step into the inner layout with a key that
        matches ``struct_defs`` / ``union_defs``.  Scalar types (``'int'``,
        ``'char'``, ...) are returned unchanged.
        """
        is_union = self._is_union_type(tag)
        fields = (self.union_defs if is_union else self.struct_defs).get(tag)
        if fields is None:
            raise NameError(
                f"Undefined {'union' if is_union else 'struct'} type '{tag}'")
        offset_words = 0
        for entry in fields:
            if isinstance(entry, tuple):
                fname, ftype = entry
            else:
                fname, ftype = entry, 'int'
            if fname == field:
                # Aggregate type keys normalize to the bare tag.  This must be
                # the *declared* type (not a placeholder): the chain walker
                # uses it to resolve the next level's layout, so returning
                # 'int' for a `struct Pair p;` union member would break
                # `u.p.a` with "Undefined struct type 'int'".
                if ftype.startswith('struct ') or ftype.startswith('union '):
                    _, bare_tag = ftype.split(' ', 1)
                    return (0 if is_union else offset_words * 2), bare_tag
                return (0 if is_union else offset_words * 2), ftype
            if not is_union:
                offset_words += self._field_type_size_words(ftype)
        field_names = [f[0] if isinstance(f, tuple) else f for f in fields]
        raise NameError(
            f"{'Union' if is_union else 'Struct'} '{tag}' has no field "
            f"'{field}' (fields: {', '.join(field_names)})")

    def _member_base_info(self, expr: MemberAccess):
        """Resolve a ``MemberAccess`` chain -- flat *and* nested ``a.b.c`` --
        into ``(kind, data, offset_bytes, innermost_base), outer_tag``.

        ``kind`` is one of:

        * ``'array_const'`` -- scalar struct variable with a compile-time
          address (``r.inner.x``).
        * ``'array_indexed'`` -- array of structs indexed at run time
          (``pts[i].inner.x`` -- innermost base is an ``ArrayAccess``).
        * ``'pointer'`` -- struct pointer whose value must be loaded
          (``pp->inner.x``).

        ``data`` carries the addressing metadata for the *innermost* base
        (array-info dict for the two ``array_*`` kinds, ``(name, tag)`` for
        ``pointer``).  ``offset_bytes`` is the **total** accumulated byte
        offset across the entire chain.  ``innermost_base`` is the
        non-``MemberAccess`` base expression so the emitter can tell whether a
        run-time index is involved.  ``outer_tag`` is the struct/union tag of
        the outermost variable (preserved for caller compatibility).
        """
        # ---- 1. Collect the chain, outermost -> innermost. ----------
        chain = []
        node = expr
        while isinstance(node, MemberAccess):
            chain.append(node)
            node = node.base
        innermost_base = node
        chain.reverse()                       # outermost -> innermost

        # ---- 2. Resolve the innermost (non-MemberAccess) base. --------
        if isinstance(innermost_base, Identifier):
            name = innermost_base.name
            outer_tag = self._var_struct_tag(name)
            if outer_tag is None:
                if name in self.struct_defs:
                    hint = ''
                    g = self.global_vars.get(name)
                    if g is not None or name in self.local_vars:
                        hint = (" It IS declared elsewhere, but not visible "
                                "from this function's scope.")
                    raise NameError(
                        f"'{name}' is a struct TYPE, not a variable in this "
                        f"scope. Declare an instance and use it instead: "
                        f"struct {name} {name.lower()};  ...  "
                        f"{name.lower()}.{expr.field}"
                        f"{hint}")
                raise NameError(
                    f"'{name}' is not a struct variable or struct pointer")
            info = self.array_vars.get(name)
            if info is not None and info.get('tag'):
                kind, data = 'array_const', info
            else:
                g = self.global_vars.get(name)
                if (name in self.pointer_vars
                        or name in self.address_params
                        or (g is not None and g.get('is_pointer'))):
                    kind, data = 'pointer', (name, outer_tag)
                elif g is not None and g.get('tag'):
                    kind, data = 'array_const', {
                        'elem_type': 'struct', 'count': g['count'],
                        'elem_size': 2, 'stride': g.get('stride', 2),
                        'base_addr': g['address'], 'is_global': True,
                    }
                else:
                    raise NameError(
                        f"'{name}' is not a struct variable or struct pointer")

        elif isinstance(innermost_base, ArrayAccess):
            arr_name = innermost_base.name
            if innermost_base.index2 is not None:
                raise CodeGenError(
                    f"member access on 2-D arrays is not supported "
                    f"('{arr_name}[i][j].{expr.field}')")
            info = self.array_vars.get(arr_name)
            if info is None:
                g = self.global_vars.get(arr_name)
                if g and g.get('is_array'):
                    info = {
                        'elem_type': g['type'], 'count': g['count'],
                        'elem_size': self._elem_size(g['type']),
                        'stride': g.get('stride'),
                        'base_addr': g['address'], 'is_global': True,
                        **({'tag': g['tag']} if g.get('tag') else {}),
                    }
                else:
                    raise NameError(f"Undefined array '{arr_name}'")
            if not info.get('tag'):
                raise NameError(
                    f"'{arr_name}' is not an array of structs")
            kind, data, outer_tag = ('array_indexed', info, info['tag'])
        else:
            raise SyntaxError("Unsupported struct member base expression")

        # ---- 3. Walk the chain, accumulating byte offsets. ----------
        total_offset_bytes = 0
        tag = outer_tag
        for i, mae in enumerate(chain):
            foffset, ftype = self._struct_field_info(tag, mae.field)
            total_offset_bytes += foffset
            if i < len(chain) - 1:
                tag = ftype                 # step into the nested aggregate

        return (kind, data, total_offset_bytes, innermost_base), outer_tag

    def _emit_member_addr(self, expr: MemberAccess, addr_reg: str,
                          idx_reg: Optional[str] = None):
        """Emit code computing a member's byte address into addr_reg.

        For ArrayAccess bases the caller may pass a pre-evaluated index in
        idx_reg; for Identifier bases the address is fully constant.

        Nested chains (``r.inner.x``, ``pts[i].inner.x``, ``pp->inner.x``)
        are handled by _member_base_info, which returns the innermost base
        so this function can tell whether a run-time index is involved.
        """
        (kind, data, offset, innermost_base), _tag = self._member_base_info(expr)
        if kind == 'pointer':
            name, _tag2 = data
            self._emit_var_load(addr_reg, name)
            if offset:
                self.emit(f"    ADD {addr_reg}, {offset}")
        elif kind == 'array_indexed':
            info = data
            if idx_reg is None:
                idx_reg = self.generate_expression(innermost_base.index)
            self._emit_array_addr(info, idx_reg, addr_reg)
            if offset:
                self.emit(f"    ADD {addr_reg}, {offset}")
        else:
            # 'array_const': scalar struct local/global -- field j of an
            # N-field struct is element j of its underlying N-word array layout.
            info = data
            self._emit_array_const_addr(info, offset // 2, addr_reg)

    def _receiver_struct_tag(self, expr) -> Optional[str]:
        """Struct/union tag of a method-call receiver expression.

        Accepts an Identifier (scalar struct variable, struct pointer, or
        `self`) or an ArrayAccess (element of an array of structs). Returns
        None when the receiver is not a struct-typed value."""
        if isinstance(expr, Identifier):
            return self._var_struct_tag(expr.name)
        if isinstance(expr, ArrayAccess):
            info = self.array_vars.get(expr.name)
            if info is None:
                g = self.global_vars.get(expr.name)
                if g and g.get('is_array'):
                    info = {'elem_type': g['type'], 'count': g['count'],
                            'elem_size': self._elem_size(g['type']),
                            'stride': g.get('stride'),
                            'base_addr': g['address'], 'is_global': True,
                            **({'tag': g['tag']} if g.get('tag') else {})}
            if info is not None:
                return info.get('tag')
            return None
        return None

    def _emit_receiver_addr(self, expr, addr_reg: str,
                            idx_reg: Optional[str] = None):
        """Emit code computing the byte address of a method receiver.

        Supports the three receiver shapes used by method calls:
          p.m()      -- p is a scalar struct variable (local or global)
          pp->m()    -- pp is a struct pointer; its VALUE is the address
          pts[i].m() -- pts is an array of structs, element i
        Also covers `self.m()` inside methods (self is a struct pointer).
        """
        if isinstance(expr, Identifier):
            name = expr.name
            g = self.global_vars.get(name)
            is_ptr = (name in self.pointer_vars
                      or name in self.address_params
                      or (g is not None and g.get('is_pointer')))
            if is_ptr:
                # Struct pointer: load the pointer value (the struct address).
                self._emit_var_load(addr_reg, name)
                return
            info = self.array_vars.get(name)
            if info is not None and info.get('tag'):
                # Scalar struct local: laid out as an N-word array; element 0
                # is the struct base address.
                self._emit_array_const_addr(info, 0, addr_reg)
                return
            if g is not None and g.get('tag'):
                # Scalar struct global: absolute base address.
                gin = {'elem_type': 'struct', 'count': g['count'],
                       'elem_size': 2, 'stride': g.get('stride', 2),
                       'base_addr': g['address'], 'is_global': True}
                self._emit_array_const_addr(gin, 0, addr_reg)
                return
            raise NameError(
                f"'{name}' is not a struct variable or struct pointer")
        if isinstance(expr, ArrayAccess):
            arr_name = expr.name
            info = self.array_vars.get(arr_name)
            if info is None:
                g = self.global_vars.get(arr_name)
                if g and g.get('is_array'):
                    info = {'elem_type': g['type'], 'count': g['count'],
                            'elem_size': self._elem_size(g['type']),
                            'stride': g.get('stride'),
                            'base_addr': g['address'], 'is_global': True,
                            **({'tag': g['tag']} if g.get('tag') else {})}
                else:
                    raise NameError(f"Undefined array '{arr_name}'")
            if not info.get('tag'):
                raise NameError(
                    f"'{arr_name}' is not an array of structs")
            if idx_reg is None:
                idx_reg = self.generate_expression(expr.index)
            self._emit_array_addr(info, idx_reg, addr_reg)
            return
        raise SyntaxError("Unsupported method-call receiver expression")


    def _decl_is_true_array(self, decl):
        """Whether a declaration is a genuine array (vs a scalar with an
        initializer list). For structs, `struct Point p = {10, 20}` is a
        scalar struct whose initializer list fills fields; only `[...]`
        bracket syntax (or an explicit size) makes it an array."""
        if getattr(decl, 'struct_tag', None):
            return bool(getattr(decl, 'array_syntax', False)
                        or getattr(decl, 'array_size', None) is not None)
        return decl.is_array

    def _decl_2d_dims(self, decl: VarDecl):
        """(rows, cols) for a 2-D array declaration, or None for 1-D.

        Both dimensions must be positive compile-time constants; storage is
        flat (rows*cols elements) and subscripts desugar to i*cols + j."""
        if getattr(decl, 'array_size2', None) is None:
            return None
        rows = self._const_eval(decl.array_size) if decl.array_size is not None else None
        cols = self._const_eval(decl.array_size2)
        if rows is None or cols is None or rows <= 0 or cols <= 0:
            raise TypeError(
                f"Array '{decl.name}' 2-D dimensions must be positive "
                f"compile-time constants")
        return (rows, cols)

    def _resolve_array_count(self, decl: VarDecl) -> int:
        """Resolve an array's element count at compile time.

        An explicit size is authoritative (C semantics): a shorter
        initializer list zero-fills the remainder (the runtime zero-fill
        for locals is emitted by generate_var_decl), and a longer one is
        a compile error. Without an explicit size the initializer list
        determines the count. Struct arrays take flat WORD initializers,
        so the initializer budget is size * words-per-struct and a sizeless
        struct array derives its element count from the word count.
        2-D arrays (rows x cols) resolve to the flat element count
        rows*cols."""
        declared = None
        if decl.array_size is not None:
            if isinstance(decl.array_size, Number):
                declared = int(decl.array_size.value, 0)
            else:
                # Enum constants (or any constant expression) are valid sizes.
                declared = self._const_eval(decl.array_size)
                if declared is None:
                    raise TypeError(
                        f"Array '{decl.name}' size must be a compile-time constant")
        dims2d = self._decl_2d_dims(decl)
        if dims2d is not None:
            # 2-D storage is flat: the element count is rows * cols.
            if declared is None:
                raise TypeError(
                    f"Array '{decl.name}' needs both dimensions for a 2-D "
                    f"array (int {decl.name}[rows][cols])")
            declared = declared * dims2d[1]
        decl_tag = getattr(decl, 'struct_tag', None)
        words_per_struct = (self._struct_size(decl_tag) // 2) if decl_tag else 1
        init_count = len(decl.init_list) if decl.init_list is not None else None
        if declared is not None:
            if init_count is not None and init_count > declared * words_per_struct:
                raise TypeError(
                    f"Array '{decl.name}' declared with {declared} element(s) "
                    f"but has {init_count} initializer value(s)")
            count = declared
        elif init_count is not None:
            count = init_count
            if decl_tag:
                if init_count % words_per_struct:
                    raise TypeError(
                        f"Struct array '{decl.name}' needs a whole number of "
                        f"struct initializer values ({init_count} words for "
                        f"{words_per_struct}-word structs)")
                count = init_count // words_per_struct
        else:
            raise TypeError(
                f"Array '{decl.name}' size must be a compile-time constant")
        if count <= 0:
            raise ValueError(f"Array '{decl.name}' must have a positive size")
        if count > 0x8000:
            # Negative literal sizes arrive here masked to 16 bits
            # (e.g. a[-2] -> 65534); a frame can never exceed the 64KB
            # address space, so reject absurd element counts outright.
            raise ValueError(
                f"Array '{decl.name}' size {count} is out of range "
                f"(max 32768 elements)")
        return count

    def _contains_float(self, expr) -> bool:
        """True if `expr` references any floating-point literal (a Number
        containing a '.'), recursively."""
        if isinstance(expr, Number):
            return '.' in expr.value
        if isinstance(expr, UnaryOp):
            return self._contains_float(expr.right)
        if isinstance(expr, BinaryOp):
            return self._contains_float(expr.left) or self._contains_float(expr.right)
        return False

    def _const_eval_float(self, expr):
        """Evaluate a compile-time constant expression that contains a float
        literal in the floating-point (Python float) domain.

        Used for global `float g = <const>;` initializers.  Because mixed
        int/float arithmetic promotes to float, integer literals are treated
        as dimensionless float values (e.g. `1.5 + 2` -> 3.5), and the
        result is encoded as Q8.8.  Returns the masked 16-bit Q8.8 value or
        None when not a compile-time constant.
        """
        if isinstance(expr, Number):
            return float(expr.value)
        if isinstance(expr, CharLiteral):
            return float(expr.char_value)
        if isinstance(expr, Identifier):
            value = self.enum_constants.get(expr.name)
            return None if value is None else float(value)
        if isinstance(expr, UnaryOp) and expr.op == '-':
            inner = self._const_eval_float(expr.right)
            return None if inner is None else -inner
        if isinstance(expr, BinaryOp):
            left = self._const_eval_float(expr.left)
            right = self._const_eval_float(expr.right)
            if left is None or right is None:
                return None
            op = expr.op
            if op == '+':
                fv = left + right
            elif op == '-':
                fv = left - right
            elif op == '*':
                fv = left * right
            elif op == '/':
                if right == 0.0:
                    return None
                fv = left / right
            else:
                # %, &, |, ^, shifts are not defined on floats at const-fold.
                return None
            # Return the raw float value (in the *floating* domain); the
            # caller encodes the final result to Q8.8 exactly once.
            return fv
        return None

    def _const_eval(self, expr) -> Optional[int]:
        """Evaluate a compile-time constant expression (global initializers).

        Returns the 16-bit masked value, or None if the expression is not a
        compile-time constant.  Expressions containing a floating-point
        literal are evaluated in the float domain and encoded back to Q8.8.
        """
        try:
            # A float literal anywhere in the expression forces float-domain
            # evaluation (int operands promote), yielding a Q8.8 result.
            if self._contains_float(expr):
                fval = self._const_eval_float(expr)
                if fval is None:
                    return None
                return int(round(fval * self._FLOAT_SCALE)) & 0xFFFF
            if isinstance(expr, Number):
                return int(expr.value, 0) & 0xFFFF
            if isinstance(expr, CharLiteral):
                return expr.char_value & 0xFFFF
            if isinstance(expr, Identifier):
                # Enum constants are compile-time integers; any other
                # identifier is not a compile-time constant.
                value = self.enum_constants.get(expr.name)
                return None if value is None else value & 0xFFFF
            if isinstance(expr, UnaryOp) and expr.op == '-':
                inner = self._const_eval(expr.right)
                return None if inner is None else (-inner) & 0xFFFF
            if isinstance(expr, BinaryOp):
                left = self._const_eval(expr.left)
                right = self._const_eval(expr.right)
                if left is None or right is None:
                    return None
                op = expr.op

                def signed_lit(node, masked):
                    # A unary-minus operand arrives pre-masked (0xFFF9 for
                    # -7). Recover its signed value so '/', '%' and relational
                    # folds use the same interpretation as the
                    # ExpressionSimplifier (which folds -7 into an unmasked
                    # Number('-7')) and as C's signed literals. Positive and
                    # hex constants keep their masked/unsigned reading.
                    if masked and isinstance(node, UnaryOp) and node.op == '-' \
                            and (masked & 0x8000):
                        return masked - 0x10000
                    return masked

                if op == '/' and right != 0:
                    # int() truncates toward zero: C semantics (-7/2 == -3).
                    return int(signed_lit(expr.left, left) /
                               signed_lit(expr.right, right)) & 0xFFFF
                if op == '%' and right != 0:
                    # C remainder takes the dividend's sign (-7%2 == -1),
                    # not Python's divisor-signed %.
                    lv = signed_lit(expr.left, left)
                    rv = signed_lit(expr.right, right)
                    q = abs(lv) // abs(rv)
                    if (lv < 0) != (rv < 0):
                        q = -q
                    return (lv - q * rv) & 0xFFFF
                if op in ('<', '<=', '>', '>='):
                    # Relate in the signed domain when a unary-minus literal
                    # is an operand (-7 < 2 must fold to 1, not to the masked
                    # 65529 < 2). ==/!= stay masked: two's-complement
                    # equality is sign-agnostic for symmetric operands.
                    lv = signed_lit(expr.left, left)
                    rv = signed_lit(expr.right, right)
                    return int({'<': lv < rv, '<=': lv <= rv,
                                '>': lv > rv, '>=': lv >= rv}[op])
                if op == '+': return (left + right) & 0xFFFF
                if op == '-': return (left - right) & 0xFFFF
                if op == '*': return (left * right) & 0xFFFF
                # ('/' and '%' were handled above with C signed semantics.)
                if op == '&': return left & right
                if op == '|': return left | right
                if op == '^': return left ^ right
                if op == '<<': return (left << right) & 0xFFFF
                if op == '>>': return (left >> right) & 0xFFFF
            if isinstance(expr, Cast):
                # A cast of a constant is a compile-time constant. Pointer
                # casts and int casts keep the full 16-bit value (an address
                # is a plain number); char masks to the low byte.
                inner = self._const_eval(expr.expr)
                if inner is None:
                    return None
                if getattr(expr, 'pointer_depth', 0) > 0:
                    return inner & 0xFFFF
                target = {'signed_int': 'int', 'unsigned_int': 'int'}.get(
                    expr.target_type, expr.target_type)
                if target == 'char':
                    return inner & 0xFF
                return inner & 0xFFFF
            return None
        except (ValueError, ArithmeticError):
            return None

    def _alloc_const_rom(self, name: str, size: int) -> int:
        """Reserve ``size`` bytes in the const-ROM window for ``name``.

        The window (0x0120-0x0EFF by default) lies above the interrupt
        vector table (0x0100-0x011F) and below the entry stub at 0x1000, so
        no code, global, static local, string scratch cell, spill window or
        stack frame is ever allocated there: a `const` table is emitted as
        part of the loaded program image and is read-only by construction
        (any write to it is rejected at compile time by the const
        enforcement in `_check_const_target`).

        Raises CodeGenError when the table does not fit, naming the object
        that overflowed so the fix (place it with `@ addr`, shrink it, or
        make it non-const) is obvious.
        """
        if self._const_rom_next_addr is None:
            self._const_rom_next_addr = self.const_rom_start
        addr = self._const_rom_next_addr
        end = addr + size
        if end > self.const_rom_end:
            capacity = self.const_rom_end - self.const_rom_start
            raise CodeGenError(
                f"const data does not fit in the read-only window: "
                f"'{name}' needs {size} byte(s) at 0x{addr:04X} but the "
                f"window ends at 0x{self.const_rom_end:04X}",
                hint=(f"the const window holds {capacity} bytes "
                      f"(0x{self.const_rom_start:04X}-"
                      f"0x{self.const_rom_end - 1:04X}); place the table "
                      f"with '@ addr', shrink it, or drop 'const' so it "
                      f"uses the global region"),
                source_text=self._diag_source_text())
        self._const_rom_next_addr = end
        self._const_rom_high_water = max(self._const_rom_high_water, end)
        return addr

    def _allocate_globals(self, ast: Program):
        """Assign fixed storage addresses to all global variables/scalals.

        The default single-image path allocates every declared global --
        including extern globals -- in the legacy absolute 0x8000 region so
        single-file programs keep working with no linker present.  In object
        mode, however, extern globals are NOT allocated locally: the linker
        resolves them via EXTERN+relocation.  Static globals are allocated
        normally (they are file-local but still need storage).
        """
        next_addr = self.global_region_start
        # Function pre-registration happens after this pass (see generate()),
        # but global function-POINTER initializers need to know which names
        # are user functions so they can emit the `func_<name>` label instead
        # of failing the compile-time-constant check. Collect them up front.
        self._declared_func_names = frozenset(
            f.name for f in (getattr(ast, 'functions', None) or []))
        for decl in getattr(ast, 'globals', None) or []:
            # In object mode, extern globals are imported from another unit:
            # do not allocate local storage for them.
            if self.object_mode and decl.name in self.extern_symbols:
                continue
            # Absolute placement (`int scb[16] @ 0xF000;`): evaluate the
            # constant address. A placed global is pinned there and does NOT
            # consume a slot in the sequential 0x8000 region; it is emitted in
            # its own ORG segment by _emit_globals_data.
            placement = getattr(decl, 'placement_addr', None)
            placement_value = None
            if placement is not None:
                placement_value = self._const_eval(placement)
                if placement_value is None:
                    raise TypeError(
                        f"Global '{decl.name}' placement address must be a "
                        f"compile-time constant")
                if not (0 <= placement_value <= 0xFFFF):
                    raise TypeError(
                        f"Global '{decl.name}' placement address "
                        f"0x{placement_value:X} is out of the 16-bit range")
            # Unplaced `const` globals (Tier-2 item 5) are read-only tables:
            # allocate them in the const-ROM window of the code image instead
            # of the writable global region. An explicit `@ addr` placement
            # always wins (the programmer asked for that address).  Object
            # mode is excluded: a relocatable unit's data must stay in the
            # global region so the linker/NOMF can relocate it.
            is_const_rom = (placement_value is None
                            and decl.name in self.const_globals
                            and not self.object_mode)
            struct_tag = getattr(decl, 'struct_tag', None)
            # Pointers always occupy 2 bytes regardless of pointee type.
            elem_size = 2 if decl.pointer_depth else self._elem_size(decl.var_type)
            # A scalar struct variable (`struct Point p;`, including the
            # initializer-list form `struct Point p = {10, 20};`) is laid
            # out exactly like an array of its N word fields, so it
            # registers through the same is_array machinery below (bare-name
            # loads decay to the base address, &p works, member j == word j).
            struct_array_syntax = bool(struct_tag and (
                getattr(decl, 'array_syntax', False)
                or getattr(decl, 'array_size', None) is not None))
            is_struct_scalar = (bool(struct_tag) and not decl.pointer_depth
                                and not struct_array_syntax)
            # Arrays of structs step by the full struct byte size instead
            # of elem_size; recorded via the optional 'stride' key.
            stride = self._struct_size(struct_tag) \
                if (struct_tag and struct_array_syntax) else None
            init_values = []
            if decl.is_array or is_struct_scalar:
                if is_struct_scalar:
                    # A scalar struct occupies one word slot per field
                    # (including every word of nested aggregate fields),
                    # so the word count is the total struct size, not just
                    # the top-level field count.
                    count = self._struct_size(struct_tag) // 2
                    elem_size = 2
                    if getattr(decl, 'init_list', None):
                        if len(decl.init_list) > count:
                            raise TypeError(
                                f"Struct '{struct_tag}' has {count} fields "
                                f"but global '{decl.name}' lists "
                                f"{len(decl.init_list)} initializers")
                        for e in decl.init_list:
                            v = self._const_eval(e)
                            if v is None:
                                raise TypeError(
                                    f"Global struct '{decl.name}' initializers "
                                    f"must be compile-time constants")
                            init_values.append(v)
                elif stride is not None:
                    # Array of structs: initializer lists fill words
                    # sequentially across whole structs.
                    elem_size = 2
                    fields_per_struct = stride // 2
                    if decl.array_size is not None:
                        if isinstance(decl.array_size, Number):
                            count = int(decl.array_size.value, 0)
                        else:
                            cval = self._const_eval(decl.array_size)
                            if cval is None:
                                raise TypeError(
                                    f"Array '{decl.name}' size must be a "
                                    f"compile-time constant")
                            count = cval
                    else:
                        n_words = len(decl.init_list or [])
                        if n_words % fields_per_struct:
                            raise TypeError(
                                f"Global struct array '{decl.name}' needs an "
                                f"explicit size or a whole-number-of-structs "
                                f"initializer list")
                        count = n_words // fields_per_struct
                    if decl.init_list and len(decl.init_list) > count * fields_per_struct:
                        raise TypeError(
                            f"Global struct array '{decl.name}' declared with "
                            f"{count} element(s) but has {len(decl.init_list)} "
                            f"initializer value(s)")
                    for e in (decl.init_list or []):
                        v = self._const_eval(e)
                        if v is None:
                            raise TypeError(
                                f"Global array '{decl.name}' initializers must be "
                                f"compile-time constants")
                        init_values.append(v)
                else:
                    count = self._resolve_array_count(decl)
                    if decl.init_list:
                        for e in decl.init_list:
                            v = self._const_eval(e)
                            if v is None:
                                # A function-pointer array's initializer is a
                                # function ADDRESS, which is an assembly label
                                # resolved in the assembler's second pass, not
                                # a numeric constant. Accept `&func` for user
                                # functions and builtins (the builtin's
                                # implementation is linked on demand here).
                                v = self._fnptr_array_init(e, decl.name)
                            if v is None:
                                raise TypeError(
                                    f"Global array '{decl.name}' initializers must be "
                                    f"compile-time constants")
                            init_values.append(v)
                total_size = count * (stride or elem_size)
                if is_const_rom:
                    # Read-only table: reserve it in the const-ROM window of
                    # the program image (see _alloc_const_rom) so it never
                    # consumes writable global storage.
                    _arr_addr = self._alloc_const_rom(decl.name, total_size)
                else:
                    _arr_addr = (placement_value if placement_value is not None
                                 else next_addr)
                ginfo = {
                    'address': _arr_addr, 'type': decl.var_type,
                    'size': total_size, 'is_array': True,
                    'elem_size': elem_size,
                    'count': count, 'init_values': init_values,
                    # Struct entries hold WORD values regardless of the
                    # element stride (each field is one DW slot).
                    'init_elem_bytes': 2 if struct_tag else elem_size,
                    **({'stride': stride} if stride else {}),
                    **({'tag': struct_tag} if struct_tag else {}),
                    **({'placement': True} if placement_value is not None else {}),
                    **({'const_rom': True} if is_const_rom else {}),
                }
                dims2d = self._decl_2d_dims(decl)
                if dims2d is not None:
                    # 2-D layout bookkeeping (a[i][j] -> a[i*cols + j]).
                    ginfo['rows'], ginfo['cols'] = dims2d
                self.global_vars[decl.name] = ginfo
                # Scalar struct/union globals are laid out like N-word arrays
                # (is_array=True) so bare-name loads decay to the base address,
                # but they still participate in whole-struct assignment and
                # by-value return destinations -- register the tag.
                if is_struct_scalar and struct_tag:
                    self.struct_tag_vars[decl.name] = struct_tag
                if placement_value is None and not is_const_rom:
                    next_addr += total_size
            else:
                init_value = None
                if decl.value is not None:
                    if (decl.var_type in ('string', 'binary')
                            and isinstance(decl.value, StringLiteral)):
                        # Global string/binary scalars hold a POINTER to the
                        # literal's DEFSTR bytes.  The initializer is the
                        # label, which the assembler resolves to the string's
                        # address when the DW is emitted (matches how local
                        # string vars get their pointer from get_string_label).
                        # The RAW form is used (get_string_label keys by it,
                        # shared with local literals of the same text).
                        init_value = self.get_string_label(decl.value.value)
                    elif (getattr(decl, 'is_fn_ptr', False)
                          and isinstance(decl.value, AddressOf)
                          and isinstance(decl.value.operand, Identifier)):
                        # Function-pointer global initialized with &func: the
                        # DW initializer is the function's assembly label, which
                        # the assembler resolves in its second pass. Only user
                        # functions qualify (builtins are lazily linked and may
                        # not exist when the DW is emitted).
                        fname = decl.value.operand.name
                        if any(f.name == fname for f in ast.functions):
                            init_value = f'func_{fname}'
                    if init_value is None:
                        init_value = self._const_eval(decl.value)
                    if init_value is None:
                        raise TypeError(
                            f"Global variable '{decl.name}' initializer must be "
                            f"a compile-time constant")
                if is_const_rom:
                    # Read-only scalar constant: same const-ROM window as
                    # const tables.
                    _scalar_addr = self._alloc_const_rom(decl.name, elem_size)
                else:
                    _scalar_addr = (placement_value
                                    if placement_value is not None
                                    else next_addr)
                self.global_vars[decl.name] = {
                    'address': _scalar_addr,
                    'type': decl.var_type,
                    'size': elem_size, 'is_array': False,
                    'elem_size': elem_size,
                    # Global pointers hold addresses (16-bit values).
                    'is_pointer': bool(decl.pointer_depth),
                    'count': 1,
                    'init_values': [init_value] if init_value is not None else [],
                    # Function-pointer globals: generate_call resolves an
                    # indirect call through this slot.
                    'fn_ptr': bool(getattr(decl, 'is_fn_ptr', False)),
                    # Struct pointers remember their layout so pp->field
                    # resolves member offsets through the pointee type.
                    **({'tag': struct_tag} if struct_tag else {}),
                    **({'placement': True} if placement_value is not None else {}),
                    **({'const_rom': True} if is_const_rom else {}),
                }
                # Track scalar struct/union variables for struct assignment
                if struct_tag and not self.global_vars[decl.name].get('is_array'):
                    self.struct_tag_vars[decl.name] = struct_tag
                if placement_value is None and not is_const_rom:
                    next_addr += elem_size

    def _emit_globals_data(self):
        """Emit the global-variable data segments.

        Three destinations: unplaced `const` globals go to the read-only
        window of the program image (const-ROM, see `_alloc_const_rom`),
        placed globals (`@ addr`) go to their own ORG segment, and
        everything else stays contiguous in the writable global region.
        """
        if not self.global_vars:
            return
        const_rom = [(name, info) for name, info in self.global_vars.items()
                     if info.get('const_rom')]
        placed = [(name, info) for name, info in self.global_vars.items()
                  if info.get('placement')]
        unplaced = [(name, info) for name, info in self.global_vars.items()
                    if not info.get('placement') and not info.get('const_rom')]
        if const_rom:
            self.assembly.append("")
            self.assembly.append("; Const data -- read-only program image")
            for name, info in const_rom:
                self.assembly.append("")
                self.assembly.append(f"ORG 0x{info['address']:04X}")
                self.assembly.append(f"; const global '{name}'")
                self._emit_global_entry(name, info)
            self.assembly.append("")
        if unplaced:
            self.assembly.append("")
            self.assembly.append(f"ORG 0x{self.global_region_start:04X}")
            self.assembly.append("; Global Variables")
            for name, info in unplaced:
                self._emit_global_entry(name, info)
            self.assembly.append("")
        for name, info in placed:
            self.assembly.append("")
            self.assembly.append(f"ORG 0x{info['address']:04X}")
            self.assembly.append(f"; Placed global '{name}'")
            self._emit_global_entry(name, info)
            self.assembly.append("")

    def _emit_global_entry(self, name: str, info: Dict) -> None:
        """Emit one global's label + data (used by _emit_globals_data)."""
        self.assembly.append(f"gvar_{name}:")
        elem_size = info.get('elem_size', self._elem_size(info['type']))
        directive = "DW" if elem_size == 2 else "DB"
        init = info.get('init_values') or []
        if info['is_array']:
            if init:
                self.assembly.append(f"    {directive} {', '.join(str(v) for v in init)}")
            # Bytes consumed by the initialized prefix. Struct entries
            # hold word values even when the element stride is larger
            # (arrays of structs fill words sequentially).
            init_bytes = len(init) * info.get('init_elem_bytes', elem_size)
            remaining = info['size'] - init_bytes
            if remaining > 0:
                self.assembly.append(f"    DS {remaining}")
        else:
            if init:
                self.assembly.append(f"    {directive} {init[0]}")
            else:
                self.assembly.append(f"    DS {info['size']}")

    def _get_array_info(self, name: str) -> Dict:
        """Return layout info for an array (local or global).

        Pointer variables also produce access info: p[i] means *(p + i)
        with the index scaled by the pointee size (C subscript semantics),
        so arrays and pointers share the same indexing code paths."""
        if name in self.array_vars:
            return self.array_vars[name]
        g = self.global_vars.get(name)
        if g and g.get('is_array'):
            return {'elem_type': g['type'], 'count': g['count'],
                    'elem_size': self._elem_size(g['type']),
                    **({'stride': g['stride']} if g.get('stride') else {}),
                    **({'tag': g['tag']} if g.get('tag') else {}),
                    # 2-D layout bookkeeping (a[i][j] -> a[i*cols + j]).
                    **({'rows': g['rows'], 'cols': g['cols']}
                       if 'cols' in g else {}),
                    'base_addr': g['address'], 'is_global': True}
        if name in self.pointer_vars or name in self.address_params:
            return {'is_pointer': True, 'name': name,
                    'elem_size': 1 if self.var_types.get(name) == 'char' else 2,
                    'count': 0}
        if g and g.get('is_pointer'):
            return {'is_pointer': True, 'name': name,
                    'elem_size': 1 if g['type'] == 'char' else 2,
                    'count': 0}
        raise NameError(f"Undefined array '{name}'")

    def _pointer_step(self, name: str) -> Optional[int]:
        """Byte step for pointer arithmetic on `name`, or None when the
        name is not pointer-like.

        Declared pointers and array parameters step by their pointee size;
        arrays decay to pointers (arr + i scales by elem_size), matching C."""
        if name in self.pointer_vars or name in self.address_params:
            return 1 if self.var_types.get(name) == 'char' else 2
        if name in self.array_vars:
            return self.array_vars[name]['elem_size']
        g = self.global_vars.get(name)
        if g:
            if g.get('is_pointer'):
                return 1 if g['type'] == 'char' else 2
            if g.get('is_array'):
                return self._elem_size(g['type'])
        return None

    def _array_stride(self, info: Dict) -> int:
        """Bytes between consecutive array elements.

        Plain arrays (and scalar struct variables, which are laid out as
        word arrays) step by elem_size; arrays of structs step by the
        whole struct size via the optional 'stride' key."""
        return info.get('stride') or info['elem_size']

    def _linearize_2d_inplace(self, access: ArrayAccess) -> ArrayAccess:
        """Desugar a 2-D subscript in place: a[i][j] -> a[i*COLS + j].

        A 2-D array is stored flat (rows*cols elements, row-major), so the
        second subscript is folded into a linear element index that the
        ordinary 1-D addressing machinery (load/store, compound assignment,
        ISR variants, address-of) already handles. Mutating the shared node
        in place preserves the parser's object-identity link between an
        assignment target and its compound-assignment RHS (`a[i][j] += v`
        shares one node), so compound detection keeps working after the
        rewrite."""
        if access.index2 is None:
            return access
        info = self._get_array_info(access.name)
        cols = info.get('cols')
        if cols is None:
            raise CodeGenError(
                f"'{access.name}[...][...]' requires a 2-D array "
                f"(declare it as {access.name}[rows][cols])")
        access.index = BinaryOp(
            BinaryOp(access.index, '*', Number(str(cols))),
            '+', access.index2)
        access.index2 = None
        return access

    def _emit_array_addr(self, info: Dict, idx_reg: str, addr_reg: str):
        """Emit code computing an element address into addr_reg.

        On entry idx_reg holds the element index; it is scaled in place to
        a byte offset (x stride) and combined with the array base
        (FP-relative for locals, absolute for globals, SP-relative inside
        timer_interrupt which has no frame pointer)."""
        stride = self._array_stride(info)
        if stride == 1:
            pass
        elif stride == 2:
            # Scale word index to byte offset: idx * 2
            self.emit(f"    ADD {idx_reg}, {idx_reg}")
        else:
            # Arrays of structs: scale by the full struct size. The
            # multiplier is an immediate constant operand (MUL reg, imm),
            # so NO scratch register is allocated from the round-robin
            # pool -- an allocated temp could alias a live outer value
            # (e.g. a compound-assignment accumulator still in its
            # register while this expression evaluates).
            self.emit(f"    MUL {idx_reg}, {stride}")
        if info.get('is_pointer'):
            # Pointer subscripting: the variable holds the base address;
            # element i lives at base + i*elem_size (already scaled above).
            self._emit_var_load(addr_reg, info['name'])
            self.emit(f"    ADD {addr_reg}, {idx_reg}")
            return
        if info.get('is_param'):
            # Array parameter: the slot at FP+offset CONTAINS the caller's
            # array base address; element i lives at base + i*elem_size.
            self.emit(f"    MOV {addr_reg}, [FP{info['offset']:+d}]")
            self.emit(f"    ADD {addr_reg}, {idx_reg}")
        elif info.get('is_global'):
            self.emit(f"    MOV {addr_reg}, 0x{info['base_addr']:04X}")
            self.emit(f"    ADD {addr_reg}, {idx_reg}")
        elif self._is_interrupt_handler:
            # Interrupt handler locals are SP-relative: the array's lowest
            # byte sits at SP + (-(offset) - total_size).
            base_sp = -info['offset'] - info['count'] * self._array_stride(info)
            self.emit(f"    MOV {addr_reg}, SP")
            self.emit(f"    ADD {addr_reg}, {base_sp}")
            self.emit(f"    ADD {addr_reg}, {idx_reg}")
        else:
            off = -info['offset']  # byte distance below FP (positive)
            self.emit(f"    MOV {addr_reg}, FP")
            self.emit(f"    SUB {addr_reg}, {off}")
            self.emit(f"    ADD {addr_reg}, {idx_reg}")

    def _emit_array_const_addr(self, info: Dict, index: int, addr_reg: str,
                               slot_step: bool = False):
        """Emit code computing an element address for a compile-time index.

        slot_step=True steps by the element slot size (elem_size) instead of
        the array stride -- used when walking a flat initializer list across
        the words of an array of structs."""
        if slot_step:
            byte_off = index * info['elem_size']
        else:
            byte_off = index * self._array_stride(info)
        if info.get('is_pointer'):
            # Pointer subscripting with a compile-time index.
            self._emit_var_load(addr_reg, info['name'])
            if byte_off:
                self.emit(f"    ADD {addr_reg}, {byte_off}")
            return
        if info.get('is_struct_param'):
            # By-value aggregate parameter: the words live INLINE at
            # FP+offset (the caller's PUSH sequence is the copy), so the
            # element address is FP + offset + byte offset.  This differs
            # from 'is_param' below, where the slot holds an *address*.
            self.emit(f"    MOV {addr_reg}, FP")
            self.emit(f"    ADD {addr_reg}, {info['offset'] + byte_off}")
            return
        if info.get('is_param'):
            self.emit(f"    MOV {addr_reg}, [FP{info['offset']:+d}]")
            self.emit(f"    ADD {addr_reg}, {byte_off}")
        elif info.get('is_global'):
            self.emit(f"    MOV {addr_reg}, 0x{info['base_addr'] + byte_off:04X}")
        elif self._is_interrupt_handler:
            base_sp = (-info['offset'] - info['count'] * self._array_stride(info)
                       + byte_off)
            self.emit(f"    MOV {addr_reg}, SP")
            self.emit(f"    ADD {addr_reg}, {base_sp}")
        else:
            delta = info['offset'] + byte_off  # signed delta from FP
            self.emit(f"    MOV {addr_reg}, FP")
            if delta >= 0:
                self.emit(f"    ADD {addr_reg}, {delta}")
            else:
                self.emit(f"    SUB {addr_reg}, {-delta}")

    def _emit_var_load(self, reg: str, name: str):
        """Load a scalar variable (local or global) into reg.

        Arrays decay to their base address (C pointer-decay semantics), so
        char buffers can be passed to strcpy/strlen/etc. by name."""
        if name in self.address_params and name in self.local_vars:
            # Array parameter: loading the name yields its address. The
            # parameter slot CONTAINS the caller's array base address, so
            # load through the slot (C decay semantics).
            offset = self.local_vars[name]['offset']
            if self._is_interrupt_handler:
                sp_offset = -offset - 2
                self.emit(f"    MOV {reg}, [SP+{sp_offset}]")
            else:
                self.emit(f"    MOV {reg}, [FP{offset:+d}]")
            return
        if name in self.array_vars:
            info = self.array_vars[name]
            if info.get('is_struct_param'):
                # By-value aggregate parameter decays to the address of its
                # inline copy at FP+offset (positive, above FP).
                self.emit(f"    MOV {reg}, FP")
                self.emit(f"    ADD {reg}, {info['offset']}")
                return
            if self._is_interrupt_handler:
                # SP-relative decay: use the array stride (struct arrays
                # step by the whole struct size, not elem_size) so the
                # decayed base matches _emit_array_addr's layout.
                base_sp = (-info['offset']
                           - info['count'] * self._array_stride(info))
                self.emit(f"    MOV {reg}, SP")
                self.emit(f"    ADD {reg}, {base_sp}")
            else:
                self.emit(f"    MOV {reg}, FP")
                self.emit(f"    SUB {reg}, {-info['offset']}")
            return
        if name in self.local_vars:
            # Locals and parameters shadow globals of the same name (C scoping
            # semantics). A function `void f(int x)` that declares a global
            # `x` must read the FP-relative param slot, NOT the global. This
            # mirrors _emit_var_store, which already resolves locals first.
            self._emit_local_load(reg, name)
            return
        g = self.global_vars.get(name)
        if g:
            if g.get('is_array'):
                self.emit(f"    MOV {reg}, 0x{g['address']:04X}")
            else:
                self.emit(f"    MOV {reg}, [0x{g['address']:04X}]")
            return
        raise NameError(f"Undefined variable '{name}'")

    def _emit_var_store(self, name: str, src_reg: str):
        """Store src_reg into a scalar variable (local or global)."""
        if name in self.local_vars:
            self._emit_local_store(name, src_reg)
            return
        g = self.global_vars.get(name)
        if g and not g.get('is_array'):
            self.emit(f"    MOV [0x{g['address']:04X}], {src_reg}")
            return
        raise NameError(f"Undefined variable '{name}'")

    def _function_signature(self, func_def: FunctionDef, label: str) -> Dict:
        """Descriptor stored in ``self.functions`` for a function or method.

        ``param_kinds`` lets a call site size each argument slot correctly:
        a by-value aggregate parameter consumes several argument words while
        every scalar parameter consumes exactly one.  When the function
        returns a struct/union by value, a hidden sret pointer is prepended
        as the first argument slot (the caller pushes the destination
        address last, so it lands at FP+4).
        """
        kinds = [self._param_kind(p) for p in func_def.params]
        ret_tag = getattr(func_def, 'return_struct_tag', None) or None
        if ret_tag:
            # Hidden destination pointer: one word, first in the frame.
            kinds = [{'sret': True, 'words': 1}] + kinds
        return {
            'label': label,
            'params': len(func_def.params),
            'return_type': func_def.return_type,
            'return_struct_tag': ret_tag,
            'param_kinds': kinds,
        }

    def _param_byval_struct_tag(self, param) -> Optional[str]:
        """Struct/union tag when ``param`` is a by-value aggregate parameter.

        ``struct Tag p`` / ``union Tag p`` (no pointer, not an array) names an
        inline aggregate copy: the caller pushes the struct's words and the
        callee owns a private instance.  Pointer (``struct Tag *p``) and array
        (``struct Tag p[]``) forms pass an address instead and return None.
        """
        tag = getattr(param, 'struct_tag', None)
        if not tag or param.pointer_depth:
            return None
        if getattr(param, 'is_array_param', False):
            return None
        return tag

    def _param_kind(self, param) -> Dict:
        """Argument-slot descriptor for one parameter (see _function_signature)."""
        tag = self._param_byval_struct_tag(param)
        if tag:
            return {'byval_struct': tag,
                    'words': self._struct_size(tag) // 2}
        return {}

    def _function_label(self, func_def: FunctionDef) -> str:
        """Assembly label for a function or impl-block method.

        Top-level functions use func_name; impl methods are namespaced to
        the owning type (func_TypeName_method) so two structs may define
        the same method name without label collisions."""
        tag = getattr(func_def, 'impl_tag', None)
        if tag:
            return f'func_{tag}_{func_def.name}'
        return f'func_{func_def.name}'

    def _diag_source_text(self) -> Optional[str]:
        """Lazily load the source file for diagnostic snippets.

        Only called on the error path; returns ``None`` when no source
        file is known (stdin compiles) so diagnostics degrade gracefully
        to position-less messages.
        """
        cached = getattr(self, '_diag_source_cache', None)
        if cached is not None:
            return cached or None
        text = None
        path = getattr(self, 'source_path', None)
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as fh:
                    text = fh.read()
            except OSError:
                text = None
        self._diag_source_cache = text if text is not None else ''
        return text

    def generate_function_with_diagnostics(self, func_def: "FunctionDef"):
        """Generate one function, annotating failures with its identity.

        Codegen raises raw exceptions deep inside expression emission; a
        bare "Register exhaustion" without context is nearly undebuggable.
        This wraps the failure with the function (or ``Tag::method``)
        name and its source position so the user knows where to look.
        ``CodeGenError`` subclasses already carry full diagnostics and
        pass through untouched.
        """
        try:
            self.generate_function(func_def)
        except CodeGenError:
            raise
        except Exception as exc:
            if getattr(func_def, 'impl_tag', None):
                qualname = f"{func_def.impl_tag}::{func_def.name}"
            else:
                qualname = func_def.name
            exc_text = str(exc).lower()
            hint = None
            if 'register' in exc_text and ('exhaust' in exc_text
                                           or 'no available' in exc_text):
                hint = ('the expression is too register-hungry -- split it '
                        'into several statements or simplify deeply nested '
                        'expressions')
            raise CodeGenError(
                f"error while generating function '{qualname}': {exc}",
                filename=getattr(self, 'source_path', None),
                line=getattr(func_def, 'line', None),
                column=getattr(func_def, 'column', None),
                hint=hint,
                source_text=self._diag_source_text()) from exc

    def generate_function(self, func_def: FunctionDef):
        label = self._function_label(func_def)
        # Keep the signature descriptor in sync with pre-registration so a
        # caller generated later still sees param_kinds (argument slot sizes).
        self.functions[func_def.name] = self._function_signature(
            func_def, label)
        # Only a top-level function named timer_interrupt is an ISR. A method
        # inside an `impl` block is never an interrupt handler, even if it
        # happens to be called timer_interrupt.
        # Determine if this function is an interrupt handler via the
        # interrupt(N) attribute (preferred) or the deprecated
        # timer_interrupt name convention (vector 0, for backward compat).
        _explicit_vector = getattr(func_def, 'interrupt_vector', None)
        _is_timer_name = (func_def.name == 'timer_interrupt'
                          and not getattr(func_def, 'impl_tag', None))
        is_interrupt_handler = (_explicit_vector is not None) or _is_timer_name
        # The vector this handler occupies (0-7). None if not an ISR.
        interrupt_vector = (_explicit_vector if _explicit_vector is not None
                            else (0 if _is_timer_name else None))
        # Naked functions skip the register save/restore prologue/epilogue.
        is_naked = ('naked' in (getattr(func_def, 'qualifiers', None) or []))
        # Store for use in generate_asm_block operand resolution.
        self._is_interrupt_handler = is_interrupt_handler
        self._is_naked = is_naked

        # Clear spill allocations for this function (per-function scope)
        self.spill_allocations = {}
        # Reserve this function's spill window from the dedicated spill
        # region so spilled locals never collide with code, globals, the
        # stack, or another function's window. When the region is exhausted,
        # keep locals FP-relative (no migration) rather than corrupt memory.
        if self._spill_window + self.opt_config.get('zero_page_size', 128) <= self.spill_region_end:
            self._function_spill_base = self._spill_window
            self._spill_window += self.opt_config.get('zero_page_size', 128)
        else:
            self._function_spill_base = None
        
        # Apply register-coloring metadata pass to local variables. This is a
        # lightweight, conservative optimization pass that records likely color
        # assignments without breaking the current expression-temporary allocator.
        if self.local_vars:
            # Reset to safe local variable scope for this function.
            pass
        
        self.current_function = func_def.name
        self.local_vars = {}
        self.var_types = {}
        self.array_vars = {}  # per-function local array scope
        self.pointer_vars = set()   # per-function pointer-declared locals/params
        self.address_params = set()  # per-function array/pointer parameters
        # By-value aggregate return: hidden sret pointer lives at FP+4.
        self._current_sret_tag = getattr(func_def, 'return_struct_tag', None)
        self._pending_sret_dest = None
        
        self.assembly.append(f"; Function: {func_def.name}")
        self.assembly.append(f"{label}:")
        
        all_local_decls = self.find_local_vars(func_def.body)

        # const intake for THIS scope: params plus every local decl (the
        # sets are rebuilt per function; impl methods run through
        # generate_function as well). Locals/params shadow globals
        # entirely (C scoping), so ownership is decided per-name by
        # _const_scope at each write site.
        self._fn_const_names = {
            d.name for d in all_local_decls
            if 'const' in (getattr(d, 'qualifiers', None) or [])
            and not getattr(d, 'pointer_depth', 0)}
        self._fn_const_pointees = {
            d.name for d in all_local_decls
            if 'const' in (getattr(d, 'qualifiers', None) or [])
            and getattr(d, 'pointer_depth', 0)}
        for param in func_def.params:
            if 'const' not in (getattr(param, 'qualifiers', None) or []):
                continue
            if (getattr(param, 'pointer_depth', 0)
                    or getattr(param, 'is_array_param', False)):
                # `const int *p` / `const int p[]`: the elements are
                # read-only; the pointer parameter itself stays rebindable.
                self._fn_const_pointees.add(param.name)
            else:
                # By-value `const int x`: the slot itself is read-only.
                self._fn_const_names.add(param.name)
        
        # Compute stack frame size: each int/string/binary var/param takes 2 bytes, char takes 1
        # Params: int/string/binary params use 2 bytes each, char params use 1 byte
        param_size = 0
        for param in func_def.params:
            self.var_types[param.name] = param.var_type
            byval_tag = self._param_byval_struct_tag(param)
            if byval_tag:
                # By-value struct/union parameter: the caller pushed the whole
                # aggregate, so the slot spans the struct's full word count
                # rather than a single address word.
                words = self._struct_size(byval_tag) // 2
                param_size += words * 2
                # Track the tag so `p = q` (whole-aggregate assignment) is
                # recognised when either side is a by-value parameter.
                self.struct_tag_vars[param.name] = byval_tag
                # Register layout info so `p.field` / `p.nested.field` resolve
                # FP-relative into the caller's argument area.  The offset is
                # POSITIVE (above FP, unlike locals) and is filled in once the
                # running param offset is known below.
                self.array_vars[param.name] = {
                    'elem_type': 'struct', 'count': words,
                    'elem_size': 2, 'stride': 2,
                    'offset': None, 'is_struct_param': True,
                    'tag': byval_tag,
                }
            elif param.pointer_depth or getattr(param, 'is_array_param', False):
                # Pointers and array parameters hold a 16-bit address.
                param_size += 2
                self.pointer_vars.add(param.name)
                if getattr(param, 'struct_tag', None):
                    # `struct Point *p` parameters remember their pointee
                    # layout so p->field resolves member offsets (mirrors
                    # how local/global struct pointer declarators register
                    # their tag in the locals loop below).
                    self.pointer_struct_tags[param.name] = param.struct_tag
                if getattr(param, 'is_array_param', False):
                    self.address_params.add(param.name)
                    # Register layout info so arr[i] indexing works on the
                    # parameter (offset filled in once known below).  A
                    # `struct Tag arr[]` parameter also carries the element
                    # tag so `return arr[i]` can resolve as a by-value
                    # aggregate of that tag.
                    info = {
                        'elem_type': param.var_type, 'count': 0,
                        'elem_size': self._elem_size(param.var_type),
                        'offset': None, 'is_param': True,
                    }
                    ptag = getattr(param, 'struct_tag', None)
                    if ptag:
                        info['tag'] = ptag
                        info['elem_type'] = 'struct'
                        info['elem_size'] = 2
                        info['stride'] = self._struct_size(ptag)
                    self.array_vars[param.name] = info
            else:
                param_size += 2 if param.var_type in ('int', 'signed_int', 'unsigned_int', 'string', 'binary', 'float') else 1
        
        local_size = 0
        for decl in all_local_decls:
            self.var_types[decl.name] = decl.var_type
            decl_tag = getattr(decl, 'struct_tag', None)
            if decl_tag and not self._decl_is_true_array(decl):
                # Track struct/union variables for struct assignment detection.
                # Arrays of structs are excluded: assigning an array to a pointer
                # must decay to a base address, not copy element-by-element.
                self.struct_tag_vars[decl.name] = decl_tag
            if self._decl_is_true_array(decl):
                # Arrays occupy count * elem_size contiguous bytes in the
                # frame; arrays of structs step by the full struct size.
                stride = self._struct_size(decl_tag) if decl_tag \
                    else self._elem_size(decl.var_type)
                local_size += self._resolve_array_count(decl) * stride
            elif decl.pointer_depth:
                local_size += 2
                self.pointer_vars.add(decl.name)
                if decl_tag:
                    # Struct pointers remember their layout for ->field.
                    self.pointer_struct_tags[decl.name] = decl_tag
            elif decl_tag:
                # Scalar struct local: one word slot per field.
                local_size += self._struct_size(decl_tag)
            else:
                local_size += 2 if decl.var_type in ('int', 'signed_int', 'unsigned_int', 'string', 'binary', 'float') else 1
        
        if is_interrupt_handler:
            # Interrupt handlers must NOT use ENTER/LEAVE because the CPU
            # already pushed PC and flags on the stack. Use direct SP
            # manipulation instead so IRET can find the saved context.
            # The CPU's interrupt entry saves ONLY PC + flags -- general
            # registers are NOT preserved. Interrupted code keeps live
            # values in P/R registers across the interrupt (e.g. a while(1)
            # loop condition re-reads its register after the handler
            # returns), so the handler must save/restore them itself --
            # UNLESS it is declared 'naked', in which case the programmer
            # takes full responsibility for register preservation.
            # Registers are pushed BEFORE allocating locals so that
            # SP-relative ([SP+n]) local addressing stays valid in the
            # handler body; _emit_isr_register_restore mirrors this order.
            if not is_naked:
                self._emit_isr_register_save()
            if local_size > 0:
                self.assembly.append(f"    SUB SP, {local_size} ; Allocate locals")
        else:
            self.assembly.append(f"    ENTER {local_size}")

        # Param offsets: after ENTER pushes FP (2 bytes) and CALL pushes ret addr (2 bytes),
        # params are at positive offsets from FP starting at +4.
        # A by-value aggregate return prepends a hidden sret pointer at FP+4
        # so the callee can write the result into the caller's destination.
        param_offset = 4
        if self._current_sret_tag:
            self.local_vars['__sret'] = {'offset': param_offset}
            self.pointer_vars.add('__sret')
            param_offset += 2
        for param in func_def.params:
            param_entry = {'offset': param_offset}
            if getattr(param, 'is_fn_ptr', False):
                # Function-pointer parameter: the slot holds an entry address.
                param_entry['fn_ptr'] = True
            self.local_vars[param.name] = param_entry
            if param.name in self.array_vars and self.array_vars[param.name].get('is_param'):
                self.array_vars[param.name]['offset'] = param_offset
            byval_tag = self._param_byval_struct_tag(param)
            if byval_tag:
                # By-value aggregate: the slot spans the whole struct, and
                # member addressing starts at FP+param_offset (positive).
                self.array_vars[param.name]['offset'] = param_offset
                param_offset += self._struct_size(byval_tag)
            else:
                param_offset += 2 if (param.var_type in ('int', 'signed_int', 'unsigned_int', 'string', 'binary', 'float')
                                      or param.pointer_depth
                                      or getattr(param, 'is_array_param', False)) else 1

        # Local offsets: start at -2 going down (2 bytes per slot for simplicity;
        # char vars also get 2 bytes to keep word access alignment simple)
        local_offset = 0
        for decl in all_local_decls:
            decl_tag = getattr(decl, 'struct_tag', None)
            # `static` locals get persistent storage in the static-local
            # region (below the global region), NOT on the stack.  They keep
            # their value across calls but have function-level visibility.
            decl_quals = list(getattr(decl, 'qualifiers', []) or [])
            if 'static' in decl_quals:
                slot_size = 2 if decl.pointer_depth else (
                    self._struct_size(decl_tag) if decl_tag else
                    (2 if decl.var_type in ('int', 'signed_int', 'unsigned_int',
                                            'string', 'binary', 'float') else 1))
                static_addr = self._static_local_next_addr
                self._static_local_next_addr += slot_size
                info = {'address': static_addr, 'size': slot_size,
                        'type': decl.var_type, 'is_static': True}
                if decl_tag:
                    info['struct_tag'] = decl_tag
                self.static_locals[(self.current_function, decl.name)] = info
                static_entry = {
                    'offset': -local_offset,  # unused for static locals
                    'static_addr': static_addr,
                }
                if getattr(decl, 'is_fn_ptr', False):
                    static_entry['fn_ptr'] = True
                self.local_vars[decl.name] = static_entry
                # Static locals are NOT counted in local_size (no stack slot).
                continue
            if self._decl_is_true_array(decl):
                count = self._resolve_array_count(decl)
                stride = self._struct_size(decl_tag) if decl_tag \
                    else self._elem_size(decl.var_type)
                local_offset += count * stride
                info = {
                    'elem_type': decl.var_type, 'count': count,
                    'elem_size': 2 if decl_tag else self._elem_size(decl.var_type),
                    'offset': -local_offset,
                }
                dims2d = self._decl_2d_dims(decl)
                if dims2d is not None:
                    # 2-D layout bookkeeping: _linearize_2d_inplace folds
                    # a[i][j] into a[i*cols + j] using the cols stride.
                    info['rows'], info['cols'] = dims2d
                if decl_tag:
                    info['tag'] = decl_tag
                    info['stride'] = stride
                self.local_vars[decl.name] = {'offset': -local_offset}
                self.array_vars[decl.name] = info
            elif decl.pointer_depth:
                local_offset += 2
                local_entry = {'offset': -local_offset}
                if getattr(decl, 'is_fn_ptr', False):
                    # Function-pointer local: indirect calls read the slot.
                    local_entry['fn_ptr'] = True
                self.local_vars[decl.name] = local_entry
            elif decl_tag:
                # Scalar struct/union local: register as an N-word array so
                # all array addressing paths (member loads, &p, decay) apply.
                # The element count mirrors the ACTUAL frame allocation
                # (_struct_size): a N-field struct is N words, a union is a
                # single overlapping word. Using field_count*2 for unions
                # would misaddress the slot (frames allocate only 1 word),
                # letting nested call stack activity clobber it.
                struct_bytes = self._struct_size(decl_tag)
                local_offset += struct_bytes
                n_words = struct_bytes // 2
                self.local_vars[decl.name] = {'offset': -local_offset}
                self.array_vars[decl.name] = {
                    'elem_type': 'struct', 'count': n_words,
                    'elem_size': 2, 'offset': -local_offset,
                    'tag': decl_tag,
                }
            else:
                local_offset += 2 if (decl.var_type in ('int', 'signed_int', 'unsigned_int', 'string', 'binary', 'float')
                                      or decl.pointer_depth) else 1
                self.local_vars[decl.name] = {'offset': -local_offset}

        # Store locals_size for iret() cleanup
        self._timer_interrupt_locals_size = local_size if is_interrupt_handler else 0
        self._emitted_return = False

        # Run a lightweight register-coloring pass to record assignment hints.
        # IMPORTANT: Only process actual local variables (VarDecl), not parameters.
        # Parameters have their own stack offsets and should never be spilled to zero-page.
        if self.local_vars:
            # Separate parameters from local variables
            param_names = {p.name for p in func_def.params}
            # `register` variables must not be spilled: they stay in registers.
            # `volatile` variables must NOT be register-allocated either: every
            # access is a fresh memory touch, so they are excluded from both the
            # register-coloring candidate set and the spill-candidate set (they
            # stay FP-relative -- the built-in fallback when no allocation is
            # made). This is what makes `volatile` finally mean something.
            register_names = self.register_hint_vars
            actual_local_names = [name for name in self.local_vars
                                  if name not in param_names and name not in self.array_vars
                                  and name not in register_names
                                  and name not in self.volatile_vars]
            
            if actual_local_names:
                candidate_graph: Dict[str, Set[str]] = {name: set() for name in actual_local_names}
                for i, name in enumerate(actual_local_names):
                    for other in actual_local_names[i + 1:]:
                        candidate_graph[name].add(other)
                        candidate_graph[other].add(name)
                available_regs = ['P0', 'P1', 'P2', 'P4', 'P5', 'P6', 'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']
                color_map = RegisterColoringPass(candidate_graph, available_regs, debug=self.debug_optimizations).color_graph()
                if color_map:
                    self.var_reg.update(color_map)
                    if self.debug_optimizations:
                        print(f"[CODEGEN] Register colors assigned in {func_def.name}: {color_map}")

                hot = HotSpillAnalyzer(
                    spill_slots={name: idx for idx, name in enumerate(actual_local_names)},
                    access_counts={name: self.variable_access_counts.get(name, 0) for name in actual_local_names},
                    debug=self.debug_optimizations,
                )
                hot_spills = hot.identify_hot_spills(threshold_percentile=75.0)
                if hot_spills and self.debug_optimizations:
                    print(f"[CODEGEN] Hot spills for {func_def.name}: {hot_spills}")

                # Use DynamicSpillAllocator to assign concrete spill addresses
                # (fallback to a larger spill region) for hot/spilled locals.
                try:
                    allocs = {}
                    if self._function_spill_base is not None:
                        allocator = DynamicSpillAllocator(
                            spill_slots={name: idx for idx, name in enumerate(actual_local_names)},
                            access_counts={name: self.variable_access_counts.get(name, 0) for name in actual_local_names},
                            debug=self.debug_optimizations,
                            zero_page_base=self._function_spill_base,
                            zero_page_size=self.opt_config.get('zero_page_size', 128),
                        )
                        allocs = allocator.allocate()
                    for var, addr in allocs.items():
                        self.spill_allocations[var] = addr
                    if allocs and self.debug_optimizations:
                        print(f"[CODEGEN] Spill allocations for {func_def.name}: {allocs}")
                except Exception:
                    if self.debug_optimizations:
                        import traceback; traceback.print_exc()

        self.generate_block(func_def.body)

        # Only emit implicit return if the function didn't already return (e.g. via iret)
        if func_def.return_type == 'void' and not self._emitted_return:
            if is_interrupt_handler:
                # ISR without an explicit iret() call: restore the saved
                # context and return from the interrupt. A normal RET here
                # would pop the pushed flags word as a return address and
                # corrupt the interrupted program state.
                self.assembly.append("; Implicit ISR return")
                if self._timer_interrupt_locals_size > 0:
                    self.assembly.append(
                        f"    ADD SP, {self._timer_interrupt_locals_size} ; Deallocate locals before IRET")
                if not is_naked:
                    self._emit_isr_register_restore()
                self.assembly.append("    IRET")
            else:
                self.assembly.append("; Implicit return for void function")
                self.assembly.append("    MOV SP, FP")
                self.assembly.append("    POP FP")
                self.assembly.append("    RET")

        self.assembly.append("")
        self.current_function = None

    # Registers preserved across interrupt-handler invocations. The CPU's
    # interrupt entry pushes only PC + flags; every other register is
    # effectively caller-save, so an ISR that clobbers P/R registers would
    # corrupt the interrupted code's live register state. P8 (SP) is
    # excluded on purpose: handlers keep the stack balanced, so SP is
    # restored implicitly by the SUB SP / ADD SP prologue-epilogue pair.
    ISR_SAVED_P_REGS = ['P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'P7', 'P9']
    ISR_SAVED_R_REGS = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']

    def _emit_isr_register_save(self):
        """Push all caller-saved registers at interrupt-handler entry.

        Must be emitted BEFORE any SUB SP local allocation so that
        SP-relative local addressing inside the handler is unaffected."""
        self.assembly.append("    ; Save general registers (interrupt entry only saves PC+flags)")
        for reg in self.ISR_SAVED_P_REGS:
            self.assembly.append(f"    PUSH {reg}")
        for reg in self.ISR_SAVED_R_REGS:
            self.assembly.append(f"    PUSH {reg}")

    def _emit_isr_register_restore(self):
        """Pop the registers saved by _emit_isr_register_save, in reverse."""
        for reg in reversed(self.ISR_SAVED_R_REGS):
            self.emit(f"    POP {reg}")
        for reg in reversed(self.ISR_SAVED_P_REGS):
            self.emit(f"    POP {reg}")

    def generate_block(self, body: List):
        for statement in body:
            if isinstance(statement, list):
                self.generate_block(statement)
            elif isinstance(statement, VarDecl):
                self.generate_var_decl(statement)
            elif isinstance(statement, Assignment):
                self.generate_assignment(statement)
            elif isinstance(statement, ArrayAssignment):
                self.generate_array_assignment(statement)
            elif isinstance(statement, MemberAssignment):
                self.generate_member_assignment(statement)
            elif isinstance(statement, DerefAssignment):
                self.generate_deref_assignment(statement)
            elif isinstance(statement, Return):
                self.generate_return(statement)
            elif isinstance(statement, If):
                self.generate_if(statement)
            elif isinstance(statement, While):
                self.generate_while(statement)
            elif isinstance(statement, DoWhile):
                self.generate_do_while(statement)
            elif isinstance(statement, Switch):
                self.generate_switch(statement)
            elif isinstance(statement, For):
                self.generate_for(statement)
            elif isinstance(statement, Break):
                self.generate_break()
            elif isinstance(statement, Continue):
                self.generate_continue()
            elif isinstance(statement, Goto):
                self.generate_goto(statement)
            elif isinstance(statement, Label):
                self.generate_user_label(statement)
            elif isinstance(statement, AsmBlock):
                self.generate_asm_block(statement)
            elif isinstance(statement, FuncCall):
                if statement.name == 'iret' and getattr(self, '_is_interrupt_handler', False):
                    # Special handling for iret: don't emit normal epilogue.
                    # Works for any interrupt handler (interrupt(N) attribute
                    # or deprecated timer_interrupt name).
                    if getattr(self, '_timer_interrupt_locals_size', 0) > 0:
                        self.emit(f"    ADD SP, {self._timer_interrupt_locals_size} ; Deallocate locals before IRET")
                    # Restore the general registers saved by the ISR prologue
                    # (interrupt entry only preserves PC + flags).
                    # Naked functions skip this (no save was done).
                    if not getattr(self, '_is_naked', False):
                        self._emit_isr_register_restore()
                    self.emit("    IRET")
                    self._emitted_return = True
                    return  # Exit function after IRET
                else:
                    self.generate_call(statement)
            elif isinstance(statement, Expression):
                self.generate_expression(statement)
            else:
                raise RuntimeError(f"Unknown statement type: {type(statement)}")

    def generate_var_decl(self, var_decl: VarDecl):
        if getattr(var_decl, 'placement_addr', None) is not None:
            raise CodeGenError(
                f"absolute placement '@' is only valid on global variables "
                f"('{var_decl.name}' is local)")
        if var_decl.is_array:
            # Local arrays: emit runtime stores for initializer-list elements.
            # (Global array initializers are emitted as DW/DB data instead.)
            info = self._get_array_info(var_decl.name)
            self.emit_comment(f"array {var_decl.name}[{info['count']}]")
            if var_decl.init_list and not info.get('is_global'):
                # C semantics: with a partial initializer the remaining
                # elements are zero-filled (an automatic array with NO
                # initializer stays indeterminate, also matching C).
                # Struct arrays take flat word initializers: total slots
                # is count * words-per-struct (stride / elem_size).
                total_slots = (info['count']
                               * (self._array_stride(info) // info['elem_size']))
                for i in range(total_slots):
                    init_expr = (var_decl.init_list[i]
                                 if i < len(var_decl.init_list) else Number('0'))
                    reg = self.generate_expression(init_expr)
                    addr_reg = self.get_register()
                    # Initializer lists fill the flat word slots of struct
                    # arrays (each value occupies one elem_size slot), so
                    # step by elem_size, not the struct stride.
                    self._emit_array_const_addr(info, i, addr_reg,
                                                slot_step=True)
                    self._emit_mem_store(addr_reg, reg, info['elem_size'])
                    self.free_register()
            return
        if var_decl.value:
            self.emit_comment(f"var {var_decl.name} = ...")
            # struct Point p = make(1, 2); -- call writes through sret into p.
            if (isinstance(var_decl.value, (FuncCall, MethodCall))
                    and var_decl.name in self.struct_tag_vars):
                lhs_tag = self.struct_tag_vars[var_decl.name]
                call = var_decl.value
                if isinstance(call, FuncCall) and isinstance(call.callee, str):
                    entry = self.functions.get(call.name)
                    ret_tag = entry.get('return_struct_tag') if entry else None
                    if ret_tag and ret_tag == lhs_tag:
                        self._pending_sret_dest = var_decl.name
                        try:
                            reg = self.generate_call(call)
                            self.free_register()
                        finally:
                            self._pending_sret_dest = None
                        return
                if isinstance(call, MethodCall):
                    member = call.base
                    rtag = self._receiver_struct_tag(member.base)
                    info = self.functions.get(f'{rtag}::{member.field}') if rtag else None
                    ret_tag = info.get('return_struct_tag') if info else None
                    if ret_tag and ret_tag == lhs_tag:
                        self._pending_sret_dest = var_decl.name
                        try:
                            reg = self.generate_method_call(call)
                            self.free_register()
                        finally:
                            self._pending_sret_dest = None
                        return
            reg = self.generate_expression(var_decl.value)
            # Implicit int -> float promotion when initializing a float var
            # with an integer expression (e.g. `float f = 5;`).
            if self._cast_source_type(Identifier(var_decl.name)) == 'float':
                self._ensure_float(reg, var_decl.value)
            self._emit_var_store(var_decl.name, reg)
            self.free_register()

    # ------------------------------------------------------------------
    # const enforcement (Tier-2 item 5)
    # ------------------------------------------------------------------
    def _const_scope(self, name):
        """(const_names, const_pointees) for the scope owning ``name``.

        Locals and params shadow globals entirely (C scoping): a local
        ``int x`` hides a global ``const int x`` and vice versa, so the
        owning table is selected by local_vars membership.
        """
        if name in self.local_vars:
            return self._fn_const_names, self._fn_const_pointees
        return self.const_globals, self.const_pointee_globals

    def _is_const_name(self, name: str) -> bool:
        names, _ = self._const_scope(name)
        return name in names

    def _is_const_pointee(self, name: str) -> bool:
        _, pointees = self._const_scope(name)
        return name in pointees

    def _member_root_name(self, node):
        """Base variable name under a member/deref chain, or None.

        Resolves ``a.b.c``, ``arr[i].f``, ``p->f`` (arrow keeps the
        Identifier base) and ``(*p).f`` down to the declared variable so
        const rules apply to the object being written.  Computed-address
        forms (``*(q+1)``) return None: their constness is not tracked
        statically -- the same blind spot C has without whole-program
        analysis of cast-away pointers.
        """
        while True:
            if isinstance(node, Identifier):
                return node.name
            if isinstance(node, ArrayAccess):
                return node.name
            if isinstance(node, MemberAccess):
                node = node.base
            elif isinstance(node, Deref):
                node = node.operand
            else:
                return None

    def _reject_const_write(self, name, node, pointee=False):
        if pointee:
            message = f"cannot modify const data through pointer '{name}'"
            hint = ("the pointer's target type is declared const; write "
                    "through a non-const pointer instead")
        else:
            message = f"cannot assign to const variable '{name}'"
            hint = ("remove 'const' from the declaration, or write through "
                    "a non-const pointer")
        raise CodeGenError(
            message, filename=self.source_path,
            line=getattr(node, 'line', None),
            column=getattr(node, 'column', None),
            hint=hint, source_text=self._diag_source_text())

    def _check_const_target(self, name, node):
        """Raise when a direct write to ``name`` violates const.

        Covers both a const object itself (``const T x``) and a write
        THROUGH a const pointee (``const T *p`` -> ``*p`` / ``p[i]``).
        """
        if self._is_const_name(name):
            self._reject_const_write(name, node)
        elif self._is_const_pointee(name):
            self._reject_const_write(name, node, pointee=True)

    def _check_const_base(self, base, node):
        """Const check for an assignment/increment base expression."""
        root = self._member_root_name(base)
        if root is not None:
            self._check_const_target(root, node)

    def generate_assignment(self, assignment: Assignment):
        # A write site: reject `const x = ...` reassignment before any code
        # is emitted (declarations/initializers never reach this path).
        self._check_const_target(assignment.name, assignment)
        self.emit_comment(f"Assignment to {assignment.name}")
        # Struct/union assignment: s1 = s2 copies all fields from s2 to s1.
        # Detected when the RHS is a simple Identifier naming a struct/union
        # variable and the LHS is also a struct/union variable of the same tag.
        if (isinstance(assignment.value, Identifier)
                and assignment.name in self.struct_tag_vars
                and assignment.value.name in self.struct_tag_vars):
            lhs_tag = self.struct_tag_vars[assignment.name]
            rhs_tag = self.struct_tag_vars[assignment.value.name]
            if lhs_tag == rhs_tag:
                self._generate_struct_assignment(assignment.name, assignment.value.name, lhs_tag)
                return
        # By-value aggregate return used as RHS of a struct assignment:
        #   struct Point p; p = make(1, 2);
        # The call writes directly into p through the hidden sret pointer.
        if (isinstance(assignment.value, FuncCall)
                and assignment.name in self.struct_tag_vars):
            lhs_tag = self.struct_tag_vars[assignment.name]
            call = assignment.value
            entry = self.functions.get(call.name) if isinstance(call.callee, str) else None
            ret_tag = entry.get('return_struct_tag') if entry else None
            if ret_tag and ret_tag == lhs_tag:
                self._pending_sret_dest = assignment.name
                try:
                    # generate_call performs the call (and the sret write);
                    # discard the returned destination address.
                    reg = self.generate_call(call)
                    self.free_register()
                finally:
                    self._pending_sret_dest = None
                return
            if ret_tag and ret_tag != lhs_tag:
                raise TypeError(
                    f"cannot assign return of '{ret_tag}' to '{lhs_tag}' "
                    f"variable '{assignment.name}'")
        # Method returning a struct assigned to a struct variable:
        #   p = q.make();
        if (isinstance(assignment.value, MethodCall)
                and assignment.name in self.struct_tag_vars):
            lhs_tag = self.struct_tag_vars[assignment.name]
            call = assignment.value
            # Resolve method signature the same way generate_method_call does.
            member = call.base
            tag = self._receiver_struct_tag(member.base)
            info = self.functions.get(f'{tag}::{member.field}') if tag else None
            ret_tag = info.get('return_struct_tag') if info else None
            if ret_tag and ret_tag == lhs_tag:
                self._pending_sret_dest = assignment.name
                try:
                    reg = self.generate_method_call(call)
                    self.free_register()
                finally:
                    self._pending_sret_dest = None
                return
            if ret_tag and ret_tag != lhs_tag:
                raise TypeError(
                    f"cannot assign return of '{ret_tag}' to '{lhs_tag}' "
                    f"variable '{assignment.name}'")
        # Check for compound assignment pattern: x = x <op> rhs
        # The parser decomposes x += y into Assignment('x', BinaryOp(Identifier('x'), '+', y)).
        # NOTE: the ExpressionSimplifier may canonicalize commutative ops
        # constant-first (x + 2 becomes 2 + x), so mirror such forms back
        # to variable-first before matching.
        value = assignment.value
        if isinstance(value, BinaryOp):
            lhs_is_var = isinstance(value.left, Identifier) and value.left.name == assignment.name
            rhs_is_var = isinstance(value.right, Identifier) and value.right.name == assignment.name
            if rhs_is_var and not lhs_is_var and value.op in ('+', '*', '&', '|', '^'):
                value = BinaryOp(value.right, value.op, value.left)
        if (isinstance(value, BinaryOp) and
            isinstance(value.left, Identifier) and
            value.left.name == assignment.name):
            op = value.op
            var_reg = self.get_register()
            self._emit_var_load(var_reg, assignment.name)
            if op in ['<<', '>>']:
                # Shift operations: constant amounts unroll; variable amounts
                # (any int expression) use a counted runtime loop.
                if isinstance(value.right, Number):
                    self._emit_shift(var_reg, int(value.right.value, 0),
                                     op == '>>', prefix="shift")
                else:
                    can_push = not self._is_interrupt_handler
                    if can_push:
                        self.emit(f"    PUSH {var_reg}")
                        count_reg = self.generate_expression(value.right)
                        count_reg = self._pop_preserving(var_reg, count_reg)
                    else:
                        # ISR: no stack protection; the SP-relative target
                        # load allocates nothing, so re-home the count and
                        # shift in place without evaluating anything else.
                        count_reg = self.generate_expression(value.right)
                        saved = self.get_register(exclude={count_reg})
                        self.emit(f"    MOV {saved}, {count_reg}")
                        count_reg = saved
                    self._emit_shift(var_reg, count_reg, op == '>>',
                                     prefix="shift")
                    self.free_register()
            else:
                can_push = not self._is_interrupt_handler
                if can_push:
                    # Preserve the accumulator across RHS evaluation.
                    # Expression temporaries are round-robin reused, and a
                    # user-function call result can overwrite var_reg before
                    # the compound operation is emitted.
                    self.emit(f"    PUSH {var_reg}")
                rhs_reg = self.generate_expression(value.right)
                if can_push:
                    rhs_reg = self._pop_preserving(var_reg, rhs_reg)
                else:
                    # ISR: reuse the target's current value after RHS
                    # evaluation.  This avoids holding the accumulator live
                    # in round-robin temporaries.  As with no-push paths
                    # elsewhere, RHS expressions in ISRs must not modify the
                    # assignment target itself.
                    rhs_home = self.get_register(exclude={rhs_reg, var_reg})
                    self.emit(f"    MOV {rhs_home}, {rhs_reg}")
                    rhs_reg = rhs_home
                    self._emit_var_load(var_reg, assignment.name)
                # Float compound assignment (f += x, f *= x, ...): the target
                # already holds Q8.8; promote the RHS if needed and use
                # FMUL/FDIV for * and / (add/sub are ordinary fixed-point).
                is_float = self._cast_source_type(Identifier(assignment.name)) == 'float'
                if is_float and op in ('+', '-', '*', '/'):
                    self.emit_comment("Float (Q8.8) compound assignment")
                    self._ensure_float(rhs_reg, value.right)
                # Pointer compound arithmetic (p += n / p -= n): scale n by
                # the pointee size before adding (C semantics).
                if op in ('+', '-'):
                    step = self._pointer_step(assignment.name)
                    if step and step > 1:
                        scale_reg = self.get_register(exclude={var_reg, rhs_reg})
                        self.emit(f"    MOV {scale_reg}, {step}")
                        self.emit(f"    MUL {rhs_reg}, {scale_reg}")
                if op == '+': self.emit(f"    ADD {var_reg}, {rhs_reg}")
                elif op == '-': self.emit(f"    SUB {var_reg}, {rhs_reg}")
                elif op == '*':
                    self.emit(f"    {'FMUL' if is_float else 'MUL'} {var_reg}, {rhs_reg}")
                elif op in ('/', '%'):
                    self._emit_divmod(op, var_reg, rhs_reg,
                                      value.left, value.right, is_float)
                elif op == '&': self.emit(f"    AND {var_reg}, {rhs_reg}")
                elif op == '|': self.emit(f"    OR {var_reg}, {rhs_reg}")
                elif op == '^': self.emit(f"    XOR {var_reg}, {rhs_reg}")
                else: raise SyntaxError(f"Unknown compound operator '{op}'")
                self.free_register()
            self._emit_var_store(assignment.name, var_reg)
            self.free_register()
        else:
            reg = self.generate_expression(assignment.value)
            # Implicit int -> float promotion when assigning to a float var.
            if self._cast_source_type(Identifier(assignment.name)) == 'float':
                self._ensure_float(reg, assignment.value)
            self._emit_var_store(assignment.name, reg)
            self.free_register()

    def _generate_struct_assignment(self, lhs_name: str, rhs_name: str, tag: str):
        """Generate a word-by-word copy for struct/union assignment: lhs = rhs.

        Each scalar field occupies one 16-bit word slot; a nested-aggregate
        field occupies as many consecutive words as its inner layout needs.
        The copy therefore walks every word of the *total* footprint (see
        ``_struct_size``) rather than only the top-level field names, so the
        second and later words of a nested child are not dropped.

        For unions all fields share byte offset 0, so ``_struct_size`` yields
        a single word and the copy degenerates to one word transfer.
        """
        # Copy every word of the struct/union footprint, not just the
        # top-level field names.  A nested aggregate field spans multiple
        # consecutive word slots (e.g. a 2-field nested struct occupies 2
        # words), so iterating top-level fields alone would copy only the
        # first word of each nested child and silently drop the rest.
        total_words = self._struct_size(tag) // 2
        self.emit_comment(f"Struct/union assignment: {lhs_name} = {rhs_name} ({tag})")
        for word_idx in range(total_words):
            offset = word_idx * 2
            # For unions all fields share offset 0, so a single word copy
            # suffices (total_words == 1 for unions by _struct_size).
            src_reg = self.get_register()
            self._emit_member_field_load(src_reg, rhs_name, offset)
            self._emit_member_field_store(lhs_name, offset, src_reg)

    def _emit_member_field_load(self, reg: str, var_name: str, offset: int):
        """Load a struct/union field (at byte offset from the variable's
        base address) into reg."""
        if var_name in self.local_vars:
            # Local variable: FP-relative addressing
            fp_off = self._get_local_offset(var_name)
            field_fp_off = fp_off + offset
            self.emit(f"    MOV {reg}, [FP{field_fp_off:+d}]")
        elif var_name in self.global_vars:
            # Global variable: absolute addressing
            base_addr = self.global_vars[var_name].get('address', self.global_region_start)
            self.emit(f"    MOV {reg}, [0x{base_addr + offset:04X}]")
        else:
            raise NameError(f"Unknown variable '{var_name}' in struct field load")

    def _emit_member_field_store(self, var_name: str, offset: int, src_reg: str):
        """Store a register value to a struct/union field (at byte offset
        from the variable's base address)."""
        if var_name in self.local_vars:
            fp_off = self._get_local_offset(var_name)
            field_fp_off = fp_off + offset
            self.emit(f"    MOV [FP{field_fp_off:+d}], {src_reg}")
        elif var_name in self.global_vars:
            base_addr = self.global_vars[var_name].get('address', self.global_region_start)
            self.emit(f"    MOV [0x{base_addr + offset:04X}], {src_reg}")
        else:
            raise NameError(f"Unknown variable '{var_name}' in struct field store")

    def _member_targets_equal(self, a: MemberAccess, b: MemberAccess) -> bool:
        """Structural equality of two member targets (for compound-assignment
        detection). Index expressions inside array bases may differ
        syntactically after simplification; they address the same storage,
        so only the access chain shape is compared."""
        while isinstance(a, MemberAccess) and isinstance(b, MemberAccess):
            if a.field != b.field or a.arrow != b.arrow:
                return False
            a, b = a.base, b.base
        if isinstance(a, Identifier) and isinstance(b, Identifier):
            return a.name == b.name
        if isinstance(a, ArrayAccess) and isinstance(b, ArrayAccess):
            return a.name == b.name
        return False

    def generate_member_access(self, expr: MemberAccess) -> str:
        """Read a struct member (p.x, pts[i].y, pp->z) into a register."""
        addr_reg = self.get_register()
        self.emit_comment(f"Member read ({expr.field})")
        self._emit_member_addr(expr, addr_reg)
        result_reg = self.get_register()
        self._emit_mem_load(result_reg, addr_reg, 2)
        return result_reg

    def generate_member_assignment(self, stmt: MemberAssignment) -> str:
        """Generate p.field = value (simple or compound).

        The member address is computed first and preserved across RHS
        evaluation via the stack (expression temporaries are round-robin
        reused and a deep RHS could clobber the address register)."""
        target = stmt.target
        # `const struct S s; s.f = ...` (and writes through a pointer to
        # const) are compile errors; resolve the chain to its base variable.
        self._check_const_base(target.base, stmt)

        # Detect compound assignment: p.x += v decomposes to
        # MemberAssignment(p.x, BinaryOp(p.x, '+', v)).
        compound_op = None
        rhs = stmt.value
        if (isinstance(stmt.value, BinaryOp)
                and isinstance(stmt.value.left, MemberAccess)
                and self._member_targets_equal(stmt.value.left, target)):
            compound_op = stmt.value.op
            rhs = stmt.value.right

        can_push = not self._is_interrupt_handler
        self.emit_comment(f"Member assignment to ...{target.field}")

        # Phase 1: compute the member's byte address.
        idx_reg = None
        if isinstance(target.base, ArrayAccess):
            idx_reg = self.generate_expression(target.base.index)
        addr_reg = self.get_register(exclude={idx_reg} if idx_reg else None)
        self._emit_member_addr(target, addr_reg, idx_reg=idx_reg)

        if compound_op:
            acc_reg = self.get_register(exclude={addr_reg})
            self._emit_mem_load(acc_reg, addr_reg, 2)
            if can_push:
                # Save both the accumulator and the address across RHS eval.
                self.emit(f"    PUSH {acc_reg}")
                self.emit(f"    PUSH {addr_reg}")
            rhs_reg = self.generate_expression(rhs)
            if can_push:
                # Stack top is addr, then acc. Restore the address directly,
                # then pop the accumulator (relocating rhs if aliased).
                self.emit(f"    POP {addr_reg}")
                rhs_reg = self._pop_preserving(acc_reg, rhs_reg)
            if compound_op in ('<<', '>>'):
                if isinstance(rhs, Number):
                    self._emit_shift(acc_reg, int(rhs.value, 0),
                                     compound_op == '>>', prefix="shift")
                else:
                    # Variable shift count: rhs was evaluated across the
                    # PUSH/POP protection of acc (stack top addr, then acc);
                    # rhs_reg now holds the runtime count.
                    self._emit_shift(acc_reg, rhs_reg, compound_op == '>>',
                                     prefix="shift")
            elif compound_op == '+': self.emit(f"    ADD {acc_reg}, {rhs_reg}")
            elif compound_op == '-': self.emit(f"    SUB {acc_reg}, {rhs_reg}")
            elif compound_op == '*': self.emit(f"    MUL {acc_reg}, {rhs_reg}")
            elif compound_op in ('/', '%'):
                self._emit_divmod(compound_op, acc_reg, rhs_reg,
                                  target, rhs)
            elif compound_op == '&': self.emit(f"    AND {acc_reg}, {rhs_reg}")
            elif compound_op == '|': self.emit(f"    OR {acc_reg}, {rhs_reg}")
            elif compound_op == '^': self.emit(f"    XOR {acc_reg}, {rhs_reg}")
            else: raise SyntaxError(f"Unknown compound operator '{compound_op}'")
            val_reg = acc_reg
        else:
            if can_push:
                self.emit(f"    PUSH {addr_reg}")
            val_reg = self.generate_expression(rhs)
            if can_push:
                val_reg = self._pop_preserving(addr_reg, val_reg)

        self._emit_mem_store(addr_reg, val_reg, 2)
        return val_reg

    def _pop_preserving(self, target_reg: str, protected_reg: Optional[str]) -> Optional[str]:
        """POP the top of stack into target_reg safely.

        Expression temporaries are handed out round-robin, so a register
        obtained earlier can be re-issued under the same name while its value
        is still live. If protected_reg names the same register as target_reg,
        its value is relocated to a fresh temporary before the POP clobbers
        it. Returns the register now holding the protected value."""
        if protected_reg is not None and protected_reg == target_reg:
            tmp_reg = self.get_register(exclude={target_reg})
            self.emit(f"    MOV {tmp_reg}, {protected_reg}")
            self.emit(f"    POP {target_reg}")
            return tmp_reg
        self.emit(f"    POP {target_reg}")
        return protected_reg

    def generate_array_assignment(self, stmt: ArrayAssignment):
        """Generate arr[index] = value (simple or compound)."""
        # 2-D subscripts desugar to the flat form first (no-op for 1-D).
        # The rewrite mutates the shared node in place, preserving the
        # compound-assignment identity check below.
        stmt.target = self._linearize_2d_inplace(stmt.target)
        target = stmt.target
        # Writes to `const arr[...]` or through `const T *p` are rejected
        # before any code is emitted (covers the string/binary branch too).
        self._check_const_target(target.name, stmt)
        # String/binary scalar variables: s[i] = c writes one byte through
        # (pointer stored in s) + i.
        if self._is_string_or_binary_scalar(target.name):
            self.emit_comment(f"String index assignment to {target.name}[...]")
            compound_op = None
            rhs = stmt.value
            if (isinstance(stmt.value, BinaryOp)
                    and isinstance(stmt.value.left, ArrayAccess)
                    and stmt.value.left.name == target.name
                    and stmt.value.left.index is target.index):
                compound_op = stmt.value.op
                rhs = stmt.value.right
            base_reg = self.get_register()
            self._emit_var_load(base_reg, target.name)
            idx_reg = self.generate_expression(target.index)
            self.emit(f"    ADD {base_reg}, {idx_reg}")
            self.free_register()  # idx_reg
            # Protect the byte address across RHS evaluation (round-robin
            # temporaries would otherwise clobber it).
            self.emit(f"    PUSH {base_reg}")
            if compound_op is not None:
                acc_reg = self.get_register(exclude={base_reg})
                self._emit_mem_load(acc_reg, base_reg, 1)
                rhs_reg = self.generate_expression(rhs)
                rhs_reg = self._pop_preserving(base_reg, rhs_reg)
                if compound_op == '+': self.emit(f"    ADD {acc_reg}, {rhs_reg}")
                elif compound_op == '-': self.emit(f"    SUB {acc_reg}, {rhs_reg}")
                elif compound_op == '*': self.emit(f"    MUL {acc_reg}, {rhs_reg}")
                elif compound_op == '/': self.emit(f"    DIV {acc_reg}, {rhs_reg}")
                elif compound_op == '%': self.emit(f"    MOD {acc_reg}, {rhs_reg}")
                elif compound_op == '&': self.emit(f"    AND {acc_reg}, {rhs_reg}")
                elif compound_op == '|': self.emit(f"    OR {acc_reg}, {rhs_reg}")
                elif compound_op == '^': self.emit(f"    XOR {acc_reg}, {rhs_reg}")
                elif compound_op in ('<<', '>>'):
                    if isinstance(rhs, Number):
                        self._emit_shift(acc_reg, int(rhs.value, 0),
                                         compound_op == '>>', prefix="shift")
                    else:
                        self.emit(f"    PUSH {acc_reg}")
                        rhs_reg = self.generate_expression(rhs)
                        rhs_reg = self._pop_preserving(acc_reg, rhs_reg)
                        self._emit_shift(acc_reg, rhs_reg,
                                         compound_op == '>>', prefix="shift")
                        self.free_register()
                else:
                    raise SyntaxError(f"Unknown compound operator '{compound_op}'")
                self._emit_mem_store(base_reg, acc_reg, 1)
            else:
                val_reg = self.generate_expression(rhs)
                val_reg = self._pop_preserving(base_reg, val_reg)
                self._emit_mem_store(base_reg, val_reg, 1)
            return val_reg if not compound_op else None
        info = self._get_array_info(target.name)
        can_push = not self._is_interrupt_handler

        # Detect compound assignment: the parser decomposes arr[i] += v into
        # ArrayAssignment(arr[i], BinaryOp(arr[i], '+', v)) sharing the same
        # index node object between both occurrences of arr[i].
        compound_op = None
        rhs = stmt.value
        if (isinstance(stmt.value, BinaryOp)
                and isinstance(stmt.value.left, ArrayAccess)
                and stmt.value.left.name == target.name
                and stmt.value.left.index is target.index):
            compound_op = stmt.value.op
            rhs = stmt.value.right

        self.emit_comment(f"Array assignment to {target.name}[...]")

        if not can_push:
            # ISR: no PUSH protection possible (see helper).
            return self._generate_isr_array_assignment(
                target, info, compound_op, rhs)

        idx_reg = self.generate_expression(target.index)
        # Preserve the index across RHS evaluation: expression temporaries
        # are round-robin reused and a deep RHS could clobber idx_reg.
        self.emit(f"    PUSH {idx_reg}")

        store_reg = None
        if compound_op:
            addr_reg = self.get_register()
            self._emit_array_addr(info, idx_reg, addr_reg)
            acc_reg = self.get_register()
            self._emit_mem_load(acc_reg, addr_reg, info['elem_size'])
            if compound_op in ('<<', '>>'):
                if isinstance(rhs, Number):
                    self._emit_shift(acc_reg, int(rhs.value, 0),
                                     compound_op == '>>', prefix="shift")
                else:
                    # Variable shift count: stash the loaded element on the
                    # stack (the index sits below it) while the count is
                    # evaluated, then restore and apply the counted loop.
                    self.emit(f"    PUSH {acc_reg}")
                    rhs_reg = self.generate_expression(rhs)
                    rhs_reg = self._pop_preserving(acc_reg, rhs_reg)
                    self._emit_shift(acc_reg, rhs_reg, compound_op == '>>',
                                     prefix="shift")
                    self.free_register()
            else:
                # Stash the loaded element across RHS evaluation, restore it,
                # THEN apply the operation (applying before the POP would let
                # the stale stacked value overwrite the computed result).
                self.emit(f"    PUSH {acc_reg}")
                rhs_reg = self.generate_expression(rhs)
                rhs_reg = self._pop_preserving(acc_reg, rhs_reg)
                if compound_op == '+': self.emit(f"    ADD {acc_reg}, {rhs_reg}")
                elif compound_op == '-': self.emit(f"    SUB {acc_reg}, {rhs_reg}")
                elif compound_op == '*': self.emit(f"    MUL {acc_reg}, {rhs_reg}")
                elif compound_op in ('/', '%'):
                    self._emit_divmod(compound_op, acc_reg, rhs_reg,
                                      target, rhs)
                elif compound_op == '&': self.emit(f"    AND {acc_reg}, {rhs_reg}")
                elif compound_op == '|': self.emit(f"    OR {acc_reg}, {rhs_reg}")
                elif compound_op == '^': self.emit(f"    XOR {acc_reg}, {rhs_reg}")
                else: raise SyntaxError(f"Unknown compound operator '{compound_op}'")
            store_reg = acc_reg
        else:
            val_reg = self.generate_expression(rhs)
            store_reg = val_reg

        # The index was stashed across RHS evaluation; restore it without
        # destroying the computed value (register names can alias).
        store_reg = self._pop_preserving(idx_reg, store_reg)
        addr_reg = self.get_register(exclude={idx_reg, store_reg})
        self._emit_array_addr(info, idx_reg, addr_reg)
        self._emit_mem_store(addr_reg, store_reg, info['elem_size'])
        return store_reg

    def _generate_isr_array_assignment(self, target, info, compound_op, rhs):
        """ISR variant of generate_array_assignment.

        The stack is reserved for the handler's SP-relative frame, so the
        index cannot be PUSH-protected across RHS evaluation the way the
        normal path does. Round-robin temporaries wrap after seven
        allocations, so an RHS evaluating several array reads would
        otherwise clobber the target's index register before the final
        store recomputes the address from it. Evaluate the RHS FIRST:
        the index and address temporaries are then allocated last and
        stay live only across the load/store pair."""
        rhs_reg = None
        rhs_const_shift = None
        if compound_op not in ('<<', '>>'):
            # Every non-shift RHS is evaluated up front.
            rhs_reg = self.generate_expression(rhs)
            # Re-home the RHS result into a register allocated AFTER the
            # whole RHS evaluation. The round-robin revisits a register
            # every 7 allocations, and the RHS result's register may be
            # revisited as early as the very next allocation (deep RHS).
            # A fresh allocation here can never alias the result register
            # within one wrap period (or it resets the revisit clock if
            # it does), giving the index evaluation below a full safe
            # distance before the final store needs the value.
            result_reg = self.get_register()
            self.emit(f"    MOV {result_reg}, {rhs_reg}")
            rhs_reg = result_reg
        else:
            # Shift amounts may be a compile-time constant (unrolled) or any
            # runtime integer expression (counted loop).
            rhs_const_shift = (int(rhs.value, 0)
                               if isinstance(rhs, Number) else None)
            if rhs_const_shift is None:
                rhs_reg = self.generate_expression(rhs)
                result_reg = self.get_register()
                self.emit(f"    MOV {result_reg}, {rhs_reg}")
                rhs_reg = result_reg

        idx_reg = self.generate_expression(target.index)
        excluded = {idx_reg} | ({rhs_reg} if rhs_reg else set())
        addr_reg = self.get_register(exclude=excluded)
        self._emit_array_addr(info, idx_reg, addr_reg)
        if compound_op:
            acc_reg = self.get_register(exclude=excluded | {addr_reg})
            self._emit_mem_load(acc_reg, addr_reg, info['elem_size'])
            if compound_op in ('<<', '>>'):
                if rhs_const_shift is not None:
                    self._emit_shift(acc_reg, rhs_const_shift,
                                     compound_op == '>>', prefix="shift")
                elif rhs_reg is not None:
                    self._emit_shift(acc_reg, rhs_reg, compound_op == '>>',
                                     prefix="shift")
            elif compound_op == '+': self.emit(f"    ADD {acc_reg}, {rhs_reg}")
            elif compound_op == '-': self.emit(f"    SUB {acc_reg}, {rhs_reg}")
            elif compound_op == '*': self.emit(f"    MUL {acc_reg}, {rhs_reg}")
            elif compound_op in ('/', '%'):
                # No PUSH in ISR context: _emit_divmod stays in registers.
                self._emit_divmod(compound_op, acc_reg, rhs_reg,
                                  target, rhs)
            elif compound_op == '&': self.emit(f"    AND {acc_reg}, {rhs_reg}")
            elif compound_op == '|': self.emit(f"    OR {acc_reg}, {rhs_reg}")
            elif compound_op == '^': self.emit(f"    XOR {acc_reg}, {rhs_reg}")
            else: raise SyntaxError(f"Unknown compound operator '{compound_op}'")
            store_reg = acc_reg
        else:
            store_reg = rhs_reg
        self._emit_mem_store(addr_reg, store_reg, info['elem_size'])
        return store_reg

    def generate_address_of(self, expr: AddressOf) -> str:
        """&var / &arr[i] / &func: compute an address into a register.

        Pointers are plain 16-bit addresses on Nova-16, so & simply yields
        the variable's storage location or function entry point as an integer value."""
        operand = expr.operand
        if isinstance(operand, Identifier):
            name = operand.name
            reg = self.get_register()
            # Check if it's a local variable first (locals shadow globals and functions)
            if name in self.local_vars:
                # Params/locals shadow globals (C scoping) -- &x on a param
                # whose name collides with a global must yield the frame slot.
                # Respect spill allocations so &x matches where loads/stores
                # of x actually live (zero-page migration).
                if name in self.spill_allocations and not self._is_interrupt_handler:
                    self.emit(f"    MOV {reg}, 0x{self.spill_allocations[name]:04X}")
                    return reg
                offset = self._get_local_offset(name)
                if self._is_interrupt_handler:
                    sp_offset = -offset - self._var_size(name)
                    self.emit(f"    MOV {reg}, SP")
                    self.emit(f"    ADD {reg}, {sp_offset}")
                else:
                    self.emit(f"    MOV {reg}, FP")
                    if offset >= 0:
                        self.emit(f"    ADD {reg}, {offset}")
                    else:
                        self.emit(f"    SUB {reg}, {-offset}")
                return reg
            # Check if it's a global variable
            g = self.global_vars.get(name)
            if g:
                self.emit(f"    MOV {reg}, 0x{g['address']:04X}")
                return reg
            # Check if it's a function name (user-defined or builtin)
            if name in self.functions:
                func_label = self.functions[name]['label']
                self.emit(f"    MOV {reg}, {func_label}")
                return reg
            # Check if it's a builtin function
            if name in self.builtin_functions:
                builtin_label = self.builtin_functions[name]
                # Lazily-linked builtins only exist if marked used: taking a
                # builtin's address is itself a use, so record it now.
                self.used_builtins.add(builtin_label)
                self.emit(f"    MOV {reg}, {builtin_label}")
                return reg
            raise NameError(f"Cannot take address of undefined variable or function '{name}'")
        if isinstance(operand, ArrayAccess):
            # 2-D subscripts desugar to the flat form first (no-op 1-D).
            operand = self._linearize_2d_inplace(operand)
            info = self._get_array_info(operand.name)
            idx_reg = self.generate_expression(operand.index)
            addr_reg = self.get_register(exclude={idx_reg})
            self._emit_array_addr(info, idx_reg, addr_reg)
            return addr_reg
        if isinstance(operand, MemberAccess):
            # &p.field / &pts[i].field: address of one member slot.
            idx_reg = None
            if isinstance(operand.base, ArrayAccess):
                idx_reg = self.generate_expression(operand.base.index)
            addr_reg = self.get_register(exclude={idx_reg} if idx_reg else None)
            self._emit_member_addr(operand, addr_reg, idx_reg=idx_reg)
            return addr_reg
        raise SyntaxError("'&' operand must be a variable, function, or array element")

    def generate_deref_assignment(self, stmt: DerefAssignment) -> str:
        """*ptr = value (simple or compound). Returns register holding value."""
        target = stmt.target
        can_push = not self._is_interrupt_handler
        # `*p = ...` writes the pointee: reject when p is `const T *`
        # (or when the root is a const object, e.g. `*arr` on const arr).
        self._check_const_base(target.operand, stmt)

        # Detect compound assignment: *p += v decomposes to
        # DerefAssignment(*p, BinaryOp(*p, '+', v)) sharing the same operand.
        compound_op = None
        rhs = stmt.value
        if (isinstance(stmt.value, BinaryOp)
                and isinstance(stmt.value.left, Deref)
                and stmt.value.left.operand is stmt.target.operand):
            compound_op = stmt.value.op
            rhs = stmt.value.right

        self.emit_comment("Pointer assignment (*ptr = ...)")
        ptr_reg = self.generate_expression(target.operand)
        if can_push:
            # Preserve the pointer across RHS evaluation (round-robin temps).
            self.emit(f"    PUSH {ptr_reg}")

        if compound_op:
            acc_reg = self.get_register()
            self.emit(f"    MOV {acc_reg}, [{ptr_reg}]")
            if can_push:
                self.emit(f"    PUSH {acc_reg}")
            rhs_reg = self.generate_expression(rhs)
            if can_push:
                rhs_reg = self._pop_preserving(acc_reg, rhs_reg)
            if compound_op == '<<':
                if isinstance(rhs, Number):
                    self._emit_shift(acc_reg, int(rhs.value, 0), False,
                                     prefix="shift")
                else:
                    self._emit_shift(acc_reg, rhs_reg, False, prefix="shift")
            elif compound_op == '>>':
                if isinstance(rhs, Number):
                    self._emit_shift(acc_reg, int(rhs.value, 0), True,
                                     prefix="shift")
                else:
                    self._emit_shift(acc_reg, rhs_reg, True, prefix="shift")
            elif compound_op == '+': self.emit(f"    ADD {acc_reg}, {rhs_reg}")
            elif compound_op == '-': self.emit(f"    SUB {acc_reg}, {rhs_reg}")
            elif compound_op == '*': self.emit(f"    MUL {acc_reg}, {rhs_reg}")
            elif compound_op in ('/', '%'):
                # Type comes from the Deref node: a signed pointee selects
                # the signed sequence, an untyped/unknown one stays raw.
                self._emit_divmod(compound_op, acc_reg, rhs_reg,
                                  stmt.value.left, rhs)
            elif compound_op == '&': self.emit(f"    AND {acc_reg}, {rhs_reg}")
            elif compound_op == '|': self.emit(f"    OR {acc_reg}, {rhs_reg}")
            elif compound_op == '^': self.emit(f"    XOR {acc_reg}, {rhs_reg}")
            else: raise SyntaxError(f"Unknown compound operator '{compound_op}'")
            val_reg = acc_reg
        else:
            val_reg = self.generate_expression(rhs)

        if can_push:
            # Restore the pointer into ptr_reg WITHOUT clobbering the
            # computed value (register names can alias under round-robin).
            val_reg = self._pop_preserving(ptr_reg, val_reg)
        self._emit_mem_store(ptr_reg, val_reg, self._pointee_size(target.operand))
        return val_reg

    def _emit_mem_store(self, addr_reg: str, val_reg: str, elem_size: int):
        """Store val_reg through addr_reg with the correct width.

        MOV [mem], Psrc performs a 16-bit big-endian word write whose high
        byte clobbers the adjacent cell -- fatal for packed char arrays.
        Routing the value through an R register forces an 8-bit write."""
        if elem_size == 1:
            self.emit(f"    MOV R0, {val_reg}")
            self.emit(f"    MOV [{addr_reg}], R0")
        else:
            self.emit(f"    MOV [{addr_reg}], {val_reg}")

    def _emit_mem_load(self, dst_reg: str, addr_reg: str, elem_size: int):
        """Load dst_reg through addr_reg with the correct width.

        MOV Pdst, [mem] reads a 16-bit word; for single-byte elements an
        R-register read fetches exactly one byte (no neighbor contamination)."""
        if elem_size == 1:
            self.emit(f"    MOV R0, [{addr_reg}]")
            self.emit(f"    MOV {dst_reg}, R0")
        else:
            self.emit(f"    MOV {dst_reg}, [{addr_reg}]")

    def _emit_shift(self, reg: str, shift, is_right: bool,
                    prefix: str = "shift"):
        """Shift a register left/right by a constant OR a runtime count.

        ``shift`` is either a Python int (the count is a compile-time
        literal, so the shift unrolls into count single-step instructions --
        branch-free and fast) or a register name holding the count at
        runtime, in which case a counted loop is emitted:

            CMP count, 0
            JZ  done
        loop:
            SHL/SHR reg, 1
            DEC  count
            JNZ  loop
        done:

        The count register is consumed (decremented to zero), matching C's
        by-value expression semantics for shift amounts.  The loop shares no
        temporaries across iterations, so a variable shift amount is fully
        general where the previous compiler version required a constant
        (``TypeError: Shift amount must be a constant integer``).
        """
        mnemonic = "SHR" if is_right else "SHL"
        if isinstance(shift, int):
            self.emit_comment(f"Unrolled shift {mnemonic} by {shift}")
            for _ in range(shift):
                self.emit(f"    {mnemonic} {reg}, 1")
            return
        end_label = self.generate_label(f"{prefix}_end")
        loop_label = self.generate_label(f"{prefix}_loop")
        self.emit_comment(f"Runtime shift {mnemonic} by register {shift}")
        self.emit(f"    CMP {shift}, 0")
        self.emit(f"    JZ {end_label}")
        self.emit_label(loop_label)
        self.emit(f"    {mnemonic} {reg}, 1")
        self.emit(f"    DEC {shift}")
        self.emit(f"    JNZ {loop_label}")
        self.emit_label(end_label)

    def _pointee_size(self, ptr_expr) -> int:
        """Element size a pointer expression points at (2 unless char*)."""
        if isinstance(ptr_expr, Identifier):
            return 1 if self.var_types.get(ptr_expr.name) == 'char' else 2
        return 2

    def _sizeof_bytes(self, expr: SizeofExpr) -> int:
        """Resolve sizeof(...) to a compile-time byte count.

        sizeof(arrayVariable) yields the TOTAL storage size in bytes
        (count * elem_size), matching C; sizeof(struct Tag) / sizeof(structVar)
        yield the whole struct layout size; everything else sizes its base
        type (1 for char, 2 otherwise)."""
        target = expr.target
        if isinstance(target, tuple) and len(target) == 2 and target[0] == 'struct':
            return self._struct_size(target[1])
        if isinstance(target, str):
            type_name = target
            return 1 if type_name == 'char' else 2
        if isinstance(target, Identifier):
            name = target.name
            if name in self.array_vars:
                info = self.array_vars[name]
                return info['count'] * self._array_stride(info)
            g = self.global_vars.get(name)
            if g and g.get('is_array'):
                stride = g.get('stride') or g.get('elem_size',
                                                  self._elem_size(g['type']))
                return g['count'] * stride
            type_name = self.var_types.get(name) or (g['type'] if g else 'int')
            return 1 if type_name == 'char' else 2
        type_name = self._cast_source_type(target) or 'int'
        return 1 if type_name == 'char' else 2

    def generate_array_access(self, expr: ArrayAccess) -> str:
        """Read arr[index]: compute the element address, then load through it."""
        # 2-D subscripts desugar to the flat form first (no-op for 1-D).
        expr = self._linearize_2d_inplace(expr)
        # String/binary SCALAR variables hold a char* pointer, so s[i] is a
        # byte read through (pointer stored in s) + i.  _get_array_info would
        # reject them, so handle them before the real-array path.
        if self._is_string_or_binary_scalar(expr.name):
            base_reg = self.get_register()
            self._emit_var_load(base_reg, expr.name)
            idx_reg = self.generate_expression(expr.index)
            self.emit(f"    ADD {base_reg}, {idx_reg}")
            self.free_register()  # idx_reg
            result_reg = self.get_register(exclude={base_reg})
            self._emit_mem_load(result_reg, base_reg, 1)
            self.free_register()  # base_reg
            return result_reg
        info = self._get_array_info(expr.name)
        idx_reg = self.generate_expression(expr.index)
        addr_reg = self.get_register()
        self._emit_array_addr(info, idx_reg, addr_reg)
        result_reg = self.get_register()
        self._emit_mem_load(result_reg, addr_reg, info['elem_size'])
        return result_reg

    def generate_ternary(self, expr: TernaryOp) -> str:
        """cond ? a : b - evaluates only the selected branch.

        Each branch pushes its result onto the stack and control converges at
        end_label with exactly one value pushed, which is then popped into a
        fresh result register. This avoids holding a result register across
        branch evaluation (round-robin temps would alias it)."""
        self.emit_comment("Ternary conditional")
        else_label = self.generate_label("tern_else")
        end_label = self.generate_label("tern_end")
        cond_reg = self.generate_expression(expr.cond)
        self.emit(f"    CMP {cond_reg}, 0")
        self.free_register()
        self.emit(f"    JZ {else_label}")
        then_reg = self.generate_expression(expr.then_expr)
        self.emit(f"    PUSH {then_reg}")
        self.emit(f"    JMP {end_label}")
        self.emit_label(else_label)
        else_reg = self.generate_expression(expr.else_expr)
        self.emit(f"    PUSH {else_reg}")
        self.emit_label(end_label)
        result_reg = self.get_register()
        self.emit(f"    POP {result_reg}")
        return result_reg

    def generate_prefix(self, expr: PrefixOp) -> str:
        """++i / --i / ++(*p) - returns the NEW value (C semantics).

        Pointer operands advance by the pointee size; dereference operands
        increment/decrement the pointee VALUE by 1."""
        # `++`/`--` perform a write: same const rules as '='.
        self._check_const_base(expr.operand, expr)
        if isinstance(expr.operand, Deref):
            self.emit_comment(f"Prefix {expr.op} on *ptr")
            ptr_reg = self.generate_expression(expr.operand.operand)
            size = self._pointee_size(expr.operand.operand)
            reg = self.get_register(exclude={ptr_reg})
            self._emit_mem_load(reg, ptr_reg, size)
            if expr.op == '++':
                self.emit(f"    INC {reg}")
            elif expr.op == '--':
                self.emit(f"    DEC {reg}")
            else:
                raise SyntaxError(f"Unknown prefix operator '{expr.op}'")
            self._emit_mem_store(ptr_reg, reg, size)
            return reg
        if isinstance(expr.operand, MemberAccess):
            # ++p.x / --p.y: increment/decrement the member VALUE in place.
            self.emit_comment(f"Prefix {expr.op} on member ({expr.operand.field})")
            addr_reg = self.get_register()
            self._emit_member_addr(expr.operand, addr_reg)
            reg = self.get_register(exclude={addr_reg})
            self._emit_mem_load(reg, addr_reg, 2)
            if expr.op == '++':
                self.emit(f"    INC {reg}")
            elif expr.op == '--':
                self.emit(f"    DEC {reg}")
            else:
                raise SyntaxError(f"Unknown prefix operator '{expr.op}'")
            self._emit_mem_store(addr_reg, reg, 2)
            return reg
        if not isinstance(expr.operand, Identifier):
            raise SyntaxError("Prefix ++/-- can only be applied to variables")
        self.emit_comment(f"Prefix {expr.op} on {expr.operand.name}")
        reg = self.get_register()
        self._emit_var_load(reg, expr.operand.name)
        step = self._pointer_step(expr.operand.name)
        # Float variables increment/decrement by 1.0 (256 in Q8.8),
        # not by 1/256 (the INC/DEC unit in Q8.8 space).
        is_float = self._cast_source_type(expr.operand) == 'float'
        float_step = 256  # 1.0 in Q8.8 fixed-point
        if expr.op == '++':
            if step and step > 1:
                self.emit(f"    ADD {reg}, {step}")
            elif is_float:
                self.emit(f"    ADD {reg}, {float_step}")
            else:
                self.emit(f"    INC {reg}")
        elif expr.op == '--':
            if step and step > 1:
                self.emit(f"    SUB {reg}, {step}")
            elif is_float:
                self.emit(f"    SUB {reg}, {float_step}")
            else:
                self.emit(f"    DEC {reg}")
        else:
            raise SyntaxError(f"Unknown prefix operator '{expr.op}'")
        self._emit_var_store(expr.operand.name, reg)
        return reg

    def generate_return(self, return_stmt: Return):
        self.emit_comment("Function return")
        if return_stmt.value:
            ret_tag = self._current_sret_tag
            if ret_tag:
                # By-value aggregate return: copy the returned value through
                # the hidden sret pointer the caller pushed as the first arg.
                # P0 still receives the destination address so a discarded
                # call result (or a chained pass) can locate the written block.
                self._emit_sret_return(return_stmt.value, ret_tag)
            else:
                reg = self.generate_expression(return_stmt.value)
                # Astrid 'int' is 16-bit, but R0 is an 8-bit register. Returning
                # only via R0 truncates values > 255 (e.g. 1234 -> 210). Place the
                # full 16-bit result in P0 (the canonical 16-bit return register)
                # and the low byte in R0 for byte-level callers / compatibility.
                self.emit(f"    MOV P0, {reg}")
                self.emit(f"    MOV R0, {reg}")
                self.free_register()
        self.emit("    MOV SP, FP")
        self.emit("    POP FP")
        self.emit("    RET")
        self._emitted_return = True

    def _emit_sret_return(self, value_expr, tag: str):
        """Copy a by-value aggregate return into the caller's sret destination.

        The callee loads the hidden destination pointer from FP+4, walks every
        word of the returned aggregate (variable, nested member, array element,
        or by-value parameter), stores each word through the destination, and
        leaves the destination address in P0 for the caller.
        """
        words = self._struct_size(tag) // 2
        # Resolve source address of the returned aggregate.
        src_reg = self.get_register()
        src_tag = self._aggregate_expr_tag(value_expr)
        if src_tag is None:
            raise TypeError(
                f"cannot return this expression by value as struct/union "
                f"'{tag}'; return a named aggregate (variable, member, or "
                f"array element)")
        if src_tag != tag:
            raise TypeError(
                f"return value has type '{src_tag}' but function returns "
                f"'{tag}'")
        self._emit_aggregate_value_addr(value_expr, src_reg, tag)
        # Load the hidden sret destination pointer (FP+4).
        dst_reg = self.get_register(exclude={src_reg})
        self.emit(f"    MOV {dst_reg}, [FP+4] ; sret destination")
        # Word-by-word copy: src -> dest.
        tmp = self.get_register(exclude={src_reg, dst_reg})
        for k in range(words):
            off = k * 2
            src_op = f"[{src_reg}]" if off == 0 else f"[{src_reg}+{off}]"
            dst_op = f"[{dst_reg}]" if off == 0 else f"[{dst_reg}+{off}]"
            self.emit(f"    MOV {tmp}, {src_op}")
            self.emit(f"    MOV {dst_op}, {tmp}")
        # Leave destination address in P0 (and low byte in R0) so the caller
        # can locate the written block if it needs to (e.g. discarded call,
        # or chaining into another by-value parameter push).
        self.emit(f"    MOV P0, {dst_reg}")
        self.emit(f"    MOV R0, {dst_reg}")
        self.free_register()  # tmp
        self.free_register()  # dst
        self.free_register()  # src


    def generate_if(self, if_stmt: If):
        self.emit_comment("If statement")
        end_label = self.generate_label("if_end")
        else_label = self.generate_label("if_else")
        reg = self.generate_expression(if_stmt.cond)
        self.emit(f"    CMP {reg}, 0")
        self.free_register()
        self.emit(f"    JZ {else_label if if_stmt.else_body else end_label}")
        # Reset _emitted_return before generating branches so a conditional
        # return inside an if-then body doesn't permanently suppress the
        # function-level epilogue for the fall-through path (when there is
        # no else branch, the condition-false path runs after the if).
        self._emitted_return = False
        self.generate_block(if_stmt.then_body)
        then_returns = self._emitted_return
        if if_stmt.else_body:
            # The end label is only reachable via an explicit skip over the
            # else branch; when the then-branch already returned there is
            # nothing to skip, so neither the JMP nor the label is needed.
            if not then_returns:
                self.emit(f"    JMP {end_label}")
            self.emit_label(else_label)
            self._emitted_return = False
            self.generate_block(if_stmt.else_body)
            else_returns = self._emitted_return
            # The if-statement unconditionally returns only when BOTH
            # branches do; otherwise the fall-through path needs an epilogue.
            self._emitted_return = then_returns and else_returns
            if not then_returns:
                self.emit_label(end_label)
        else:
            self.emit_label(end_label)
            # Without an else branch the fall-through (condition-false) path
            # never returns, so the if-statement as a whole does not
            # unconditionally return.
            self._emitted_return = False

    def generate_while(self, while_stmt: While):
        self.emit_comment("While loop")
        start_label = self.generate_label("while_start")
        end_label = self.generate_label("while_end")
        # For while loops, continue jumps to the start (condition check)
        self.loop_stack.append((start_label, end_label))
        self.emit_label(start_label)
        reg = self.generate_expression(while_stmt.cond)
        self.emit(f"    CMP {reg}, 0")
        self.free_register()
        self.emit(f"    JZ {end_label}")
        self.generate_block(while_stmt.body)
        self.emit(f"    JMP {start_label}")
        self.emit_label(end_label)
        self.loop_stack.pop()

    def _detect_wrap_prone_var(self, for_stmt: For) -> Optional[str]:
        """Detect if a for-loop has a pattern prone to 16-bit unsigned wrap-around.

        Recognizes patterns where a loop variable is compared in the condition
        and modified by a compound-update in the update expression, such that
        the variable could overflow/underflow the 16-bit range before the
        condition becomes false.

        Recognized condition patterns (var is the loop variable):
        - var < bound   (incrementing var, bound near 0xFFFF)
        - var <= bound
        - var > bound   (decrementing var, bound near 0x0000)
        - var >= bound

        Recognized update patterns:
        - var += expr  (compound: var = var + expr)
        - var -= expr  (compound: var = var - expr)
        - var++        (postfix increment)
        - var--        (postfix decrement)

        The wrap check is suppressed for 'timer_interrupt' because that function
        uses SP-relative locals (no ENTER/FP) and PUSH/POP would shift the SP
        base, corrupting SP-relative addresses for all local variables.

        Args:
            for_stmt: The For AST node.

        Returns:
            The loop variable name if a wrap-prone pattern is detected, else None.
        """
        if not for_stmt.cond or not for_stmt.update:
            return None
        if not isinstance(for_stmt.cond, BinaryOp):
            return None
        if for_stmt.cond.op not in ['<', '<=', '>', '>=', '==', '!=']:
            return None

        # Collect candidate loop-variable names from both sides of the condition.
        # The variable may appear on either side depending on how the AST was
        # constructed (e.g. "p < finish" or "finish > p").
        candidates = []
        if isinstance(for_stmt.cond.left, Identifier):
            candidates.append(for_stmt.cond.left.name)
        if isinstance(for_stmt.cond.right, Identifier):
            candidates.append(for_stmt.cond.right.name)

        if not candidates:
            return None

        update = for_stmt.update
        for var_name in candidates:
            # Case 1: Compound assignment — var = var <op> expr
            # Parser decomposes "var += expr" into Assignment('var', BinaryOp(Identifier('var'), '+', expr))
            if isinstance(update, Assignment):
                if update.name == var_name:
                    value = update.value
                    if isinstance(value, BinaryOp) and isinstance(value.left, Identifier) \
                            and value.left.name == var_name:
                        return var_name

            # Case 2: Postfix operator — var++ or var--
            elif isinstance(update, PostfixOp):
                if isinstance(update.left, Identifier) and update.left.name == var_name:
                    return var_name

        return None

    def generate_for(self, for_stmt: For):
        self.emit_comment("For loop")
        start_label = self.generate_label("for_start")
        end_label = self.generate_label("for_end")
        # For for loops, continue jumps to the update expression
        # We use a separate continue_label that points to the update section
        continue_label = self.generate_label("for_continue")
        self.loop_stack.append((continue_label, end_label))

        # Emit initialization (may be a VarDecl list for "for(int x=...)",
        # or an Assignment/Expression for "for(x=...)")
        if for_stmt.init:
            self.generate_block([for_stmt.init])

        # Condition check: evaluate cond to 0/1, exit if false (zero)
        self.emit_label(start_label)
        if for_stmt.cond:
            reg = self.generate_expression(for_stmt.cond)
            self.emit(f"    CMP {reg}, 0")
            self.free_register()
            self.emit(f"    JZ {end_label}")

        # Loop body
        self.generate_block(for_stmt.body)

        # Continue target: update expression
        self.emit_label(continue_label)

        # Wrap-aware for-loop emission:
        # When a 16-bit loop variable is incremented (e.g., p += 32) and
        # the loop bound is 0xFFFF (or any value near 0xFFFF), the variable
        # can wrap from 0xFFF0 to 0x0010.  The unsigned comparison
        # (p < 0xFFFF) remains true after the wrap, causing an infinite loop.
        #
        # To detect this, we save the variable's value before the update, then
        # compare it with the new value after the update.  If new < old
        # (unsigned borrow / carry), the variable wrapped → exit loop.
        #
        # This check is suppressed in 'timer_interrupt' because that function
        # uses SP-relative locals (no ENTER/FP) and PUSH/POP would shift the
        # SP base, corrupting SP-relative addresses for all local variables.
        loop_var = self._detect_wrap_prone_var(for_stmt)
        need_wrap_check = (
            loop_var is not None
            and not self._is_interrupt_handler
        )

        if need_wrap_check:
            # Save current value of loop variable on the stack before update.
            # PUSH/POP are safe here because FP-relative addressing is unaffected
            # by SP changes (only SP-relative access in timer_interrupt is affected,
            # which we've already excluded above).
            self.emit_comment(f"Wrap-check: save {loop_var} before update")
            old_reg = self.get_register()
            self._emit_local_load(old_reg, loop_var)
            self.emit(f"    PUSH {old_reg}")
            self.free_register()

        # Emit update expression (e.g., p += step).
        #
        # Support a bare step idiom: when the update clause is a plain
        # expression of the form `var op expr` (e.g. `i + 8`) rather than an
        # explicit `i += 8` assignment, treat it as `var = var op expr` so the
        # computed value is stored back into the loop variable. Previously the
        # bare expression was only evaluated into a scratch register and its
        # result discarded, silently freezing the loop variable -- game.ast's
        # `for (int i = 0; i < 256; i + 8)` never advanced i, so the level
        # boundary drew just a single 'X ... X' line before looping forever.
        #
        # NOTE: the ExpressionSimplifier may canonicalize commutative ops
        # constant-first (`i + 8` becomes `8 + i`), so the loop variable may
        # appear on either side of the BinaryOp. generate_assignment already
        # mirrors such const-first compound forms back to variable-first.
        if for_stmt.update:
            update = for_stmt.update
            if isinstance(update, BinaryOp):
                if isinstance(update.left, Identifier):
                    update = Assignment(update.left.name, update)
                elif (isinstance(update.right, Identifier)
                        and not isinstance(update.left, Identifier)
                        and update.op in ('+', '*', '&', '|', '^')):
                    update = Assignment(update.right.name, update)
            self.generate_block([update])

        if need_wrap_check:
            # Restore pre-update value and compare with new value to detect
            # unsigned wrap-around.
            # CMP new, old computes new - old.  If new < old (unsigned),
            # the carry/borrow flag is set, indicating the variable wrapped
            # from a high value back to a low value.
            self.emit_comment(f"Wrap-check: compare {loop_var} new vs old")
            old_reg = self.get_register()
            self.emit(f"    POP {old_reg}")
            new_reg = self.get_register()
            self._emit_local_load(new_reg, loop_var)
            self.emit(f"    CMP {new_reg}, {old_reg}")
            self.free_register()
            # JC = jump if carry (borrow) → new < old → wrapped → exit
            self.emit(f"    JC {end_label}")

        # Jump back to condition check
        self.emit(f"    JMP {start_label}")
        self.emit_label(end_label)
        self.loop_stack.pop()

    def generate_do_while(self, stmt: DoWhile):
        """Generate code for do-while loop: do { body } while (cond);"""
        self.emit_comment("Do-While loop")
        start_label = self.generate_label("dowhile_start")
        cond_label = self.generate_label("dowhile_cond")
        end_label = self.generate_label("dowhile_end")
        # For do-while, `continue` jumps to the condition check (C semantics),
        # NOT back to the top of the body.
        self.loop_stack.append((cond_label, end_label))
        self.emit_label(start_label)
        self.generate_block(stmt.body)
        self.emit_label(cond_label)
        reg = self.generate_expression(stmt.cond)
        self.emit(f"    CMP {reg}, 0")
        self.free_register()
        self.emit(f"    JNZ {start_label}")  # Loop back if condition is true
        self.emit_label(end_label)
        self.loop_stack.pop()

    def generate_switch(self, stmt: Switch):
        """Generate code for switch/case statement.

        Compiles to a series of comparisons (CMP/JZ) against each case value.
        Supports break and C-style fall-through between cases (no break).
        """
        self.emit_comment("Switch statement")
        end_label = self.generate_label("switch_end")
        # Push loop context so break inside switch exits to end_label.
        # No continue target (None) because continue is not valid in switch.
        self.loop_stack.append((None, end_label))

        reg = self.generate_expression(stmt.expr)

        # Pre-generate labels for each case body
        case_labels = [self.generate_label("case") for _ in stmt.cases]

        # Emit comparisons for each case value
        for i, case in enumerate(stmt.cases):
            case_val_reg = self.generate_expression(case.value)
            self.emit(f"    CMP {reg}, {case_val_reg}")
            self.free_register()  # free case_val_reg
            self.emit(f"    JZ {case_labels[i]}")

        # Free the switch expression register after all comparisons
        self.free_register()

        # If no case matched, go to default or end
        if stmt.default_body:
            self.generate_block(stmt.default_body)
            self.emit(f"    JMP {end_label}")
        else:
            self.emit(f"    JMP {end_label}")

        # Emit case bodies (fall-through is natural between consecutive cases)
        for i, case in enumerate(stmt.cases):
            self.emit_label(case_labels[i])
            self.generate_block(case.body)

        self.emit_label(end_label)
        self.loop_stack.pop()

    def generate_break(self):
        # Generate assembly for a break statement - jump to loop end
        if not self.loop_stack:
            raise RuntimeError("break statement outside of loop")
        _, end_label = self.loop_stack[-1]
        self.emit_comment("break")
        self.emit(f"    JMP {end_label}")

    def generate_continue(self):
        # Generate assembly for a continue statement - jump to loop continue target
        if not self.loop_stack:
            raise RuntimeError("continue statement outside of loop")
        continue_label, _ = self.loop_stack[-1]
        if continue_label is None:
            raise RuntimeError("continue statement is not valid inside a switch")
        self.emit_comment("continue")
        self.emit(f"    JMP {continue_label}")

    def generate_goto(self, stmt: Goto):
        """Generate goto label; -- unconditional jump to a labeled statement.

        Labels are function-scoped; the label name is emitted as-is with
        a 'label_' prefix to avoid collisions with user-defined symbols.
        """
        label_codegen_name = self._user_label_codegen_name(stmt.label)
        self.emit_comment(f"goto {stmt.label}")
        self.emit(f"    JMP {label_codegen_name}")

    def generate_user_label(self, stmt: Label):
        """Generate label: statement -- a goto target.

        Emits the label, then generates the attached statement (if any).
        The label name is prefixed to avoid collisions with other symbols.
        """
        label_codegen_name = self._user_label_codegen_name(stmt.name)
        self.emit_comment(f"label {stmt.name}:")
        self.emit_label(label_codegen_name)
        if stmt.stmt is not None:
            # Generate the statement attached to this label
            stmts = stmt.stmt if isinstance(stmt.stmt, list) else [stmt.stmt]
            self.generate_block(stmts)

    def _resolve_asm_operand(self, name: str) -> str:
        """Resolve an Astrid variable name to its codegen identity for use
        as an inline-asm operand.

        Returns a register name (e.g. 'P2') when the variable currently
        lives in a compiler-allocated register, or a memory reference
        like '[0x8020]' / '[FP-4]' / '[SP+2]' when it is spilled or
        global.  Falls back to the bare name (let the assembler try to
        resolve it as a label) when the name is unknown -- this keeps
        hand-written asm that references raw labels working.

        Reuses the exact same address-mode logic as _emit_local_load so
        the asm operand always matches where the variable actually lives.
        """
        # --- locals (including params) --------------------------------
        if name in self.local_vars:
            info = self.local_vars[name]
            offset = info['offset']
            var_size = self._var_size(name)
            # Static locals: fixed absolute address.
            static_addr = info.get('static_addr')
            if static_addr is not None:
                return f"[0x{static_addr:04X}]"
            # Spilled locals: absolute spill address (not FP-relative).
            if name in self.spill_allocations:
                return f"[0x{self.spill_allocations[name]:04X}]"
            # ISR (SP-relative) locals.
            if self._is_interrupt_handler:
                sp_offset = -offset - var_size
                return f"[SP+{sp_offset}]"
            # Normal FP-relative local.
            return f"[FP{offset:+d}]"
        # --- globals --------------------------------------------------
        g = self.global_vars.get(name)
        if g:
            return f"[0x{g['address']:04X}]"
        # --- register-allocated variable (var_reg) --------------------
        # var_reg maps name -> register for variables the allocator has
        # placed in a hardware register.
        reg = self.var_reg.get(name)
        if reg:
            return reg
        # --- unknown: pass through as bare token ----------------------
        return name

    def _substitute_asm_operands(self, line: str) -> str:
        """Replace {varname} tokens in an inline-asm instruction with the
        variable's codegen identity (register or memory reference).

        Handles nested braces and unknown names gracefully: unknown
        {name} tokens are left intact so the assembler can try label
        resolution.
        """
        import re
        def repl(m):
            name = m.group(1)
            return self._resolve_asm_operand(name)
        return re.sub(r'\{([A-Za-z_][A-Za-z0-9_]*)\}', repl, line)

    def generate_asm_block(self, stmt: AsmBlock):
        """Emit an inline assembly block verbatim.

        Each element of stmt.lines is one raw assembly instruction. We
        emit each line indented by four spaces (matching the rest of
        the function body) with no further analysis, transformation,
        or register allocation. The programmer is fully responsible
        for correctness -- including the calling convention, flag
        state, and any registers the asm touches.

        Because the optimizer cannot reason about the effects of raw
        asm, asm blocks act as compiler barriers: they are never
        constant-folded, never CSE'd, and the live-range scheduler
        treats them as clobbering all registers conservatively. This
        is documented in the language reference.

        Astrid variables may be referenced inline using ``{varname}``
        syntax; each occurrence is replaced with the variable's codegen
        identity (a register like ``P2`` or a memory reference like
        ``[0x8020]`` / ``[FP-4]``) so the asm can see the exact location
        the compiler is using for that variable."""
        self.emit_comment("asm {")
        for line in stmt.lines:
            line = self._substitute_asm_operands(line)
            # Emit each raw instruction indented, verbatim.
            # We do NOT analyze operands, allocate registers, or
            # validate the instruction -- that is the programmer's job.
            self.emit(f"    {line}")
        self.emit_comment("}")

    def _user_label_codegen_name(self, name: str) -> str:
        """Return the assembly-safe label name for a user label.

        Prefixes with 'label_' and includes the current function name to
        keep labels function-scoped.
        """
        func_prefix = self.current_function or 'global'
        return f"label_{func_prefix}_{name}"

    def generate_expression(self, expr: Expression) -> str:
        if isinstance(expr, AsmBlock):
            # Inline asm used as an expression: emit the block and return
            # P0 as the result register (the asm is expected to leave its
            # result in P0 per the Astrid ABI).
            self.generate_asm_block(expr)
            return "P0"
        if isinstance(expr, Number):
            reg = self.get_register()
            if '.' in expr.value:
                # Float literal -> Q8.8 fixed-point integer (16-bit).
                literal = self._float_to_q8(expr.value)
                self.emit_comment(f"Float literal {expr.value} -> Q8.8 {literal}")
            else:
                # Normalize the literal to a plain decimal integer: the
                # Nova-16 assembler understands decimal and 0x hex, but not
                # 0b/0o forms.
                try:
                    literal = int(expr.value, 0)
                except (ValueError, TypeError):
                    literal = expr.value
            self.emit(f"    MOV {reg}, {literal}")
            return reg
        elif isinstance(expr, StringLiteral):
            reg = self.get_register()
            label = self.get_string_label(expr.value)
            self.emit(f"    MOV {reg}, {label}")
            return reg
        elif isinstance(expr, CharLiteral):
            reg = self.get_register()
            self.emit(f"    MOV {reg}, {expr.char_value}")
            return reg
        elif isinstance(expr, StringIndexAccess):
            # C-style string literal indexing: "abc"[i].  A compile-time
            # index folds to the character constant (validated in range, so
            # an off-by-one is caught at build time); a runtime index emits a
            # single-byte load through the DEFSTR address.
            index_val = self._const_eval(expr.index)
            if index_val is not None:
                index_val &= 0xFFFF
                text = expr.value  # unescaped logical characters
                if not (0 <= index_val < len(text)):
                    raise IndexError(
                        f"String index {index_val} out of bounds for \"{expr.raw}\" (len {len(text)})")
                result_reg = self.get_register()
                self.emit(f"    MOV {result_reg}, {ord(text[index_val])}")
                return result_reg
            # Runtime index: byte load from (label + index). Temporal
            # registers are always P0-P7 (never R0), so the R0 scratch used
            # inside _emit_mem_load cannot clobber the live address.
            base_reg = self.get_register()
            self.emit(f"    MOV {base_reg}, {self.get_string_label(expr.raw)}")
            idx_reg = self.generate_expression(expr.index)
            self.emit(f"    ADD {base_reg}, {idx_reg}")
            self.free_register()  # idx_reg
            result_reg = self.get_register(exclude={base_reg})
            self._emit_mem_load(result_reg, base_reg, 1)
            self.free_register()  # base_reg
            return result_reg
        elif isinstance(expr, Cast):
            return self.generate_cast(expr)
        elif isinstance(expr, Identifier):
            reg = self.get_register()
            if expr.name in self.enum_constants:
                # Enum constants are compile-time integers.
                self.emit(f"    MOV {reg}, {self.enum_constants[expr.name]}")
                return reg
            self._emit_var_load(reg, expr.name)
            return reg
        elif isinstance(expr, BinaryOp):
            # String concatenation via '+': when BOTH sides are string- or
            # binary-typed values, 'a' + 'b' means concatenate their bytes
            # (C's string operators don't exist, so Astrid borrows the '+'
            # spelling from languages like Java/JS).  A '+' with a numeric
            # or pointer operand on either side still means pointer/address
            # arithmetic (char *p + 1, &arr[i] + n), so this check leaves
            # those alone.
            if (expr.op == '+'
                    and self._is_string_expr(expr.left)
                    and self._is_string_expr(expr.right)):
                return self._generate_string_concat(expr)
            # Constant folding: evaluate simple binary ops with two numeric
            # literal operands at compile time (brought over from NoBASIC's
            # ExpressionSimplifier). This avoids emitting MOV/ADD/SUB/etc.
            # instructions for expressions like `2 + 3` or `10 * 5`.
            if isinstance(expr.left, Number) and isinstance(expr.right, Number):
                try:
                    op = expr.op
                    if '.' in expr.left.value or '.' in expr.right.value:
                        # Float-literal constant folding: fold in the
                        # floating-point domain, then encode the Q8.8 result.
                        # Handles + - * / (result is Q8.8) and comparisons
                        # (result is 0/1). Operators not defined on floats
                        # (% & | ^ shifts) fall through to runtime emission.
                        lfv = float(expr.left.value)
                        rfv = float(expr.right.value)
                        if op == '+':
                            folded = int(round((lfv + rfv) * 256)) & 0xFFFF
                        elif op == '-':
                            folded = int(round((lfv - rfv) * 256)) & 0xFFFF
                        elif op == '*':
                            folded = int(round((lfv * rfv) * 256)) & 0xFFFF
                        elif op == '/':
                            if rfv == 0.0:
                                raise ArithmeticError("Division by zero")
                            folded = int(round((lfv / rfv) * 256)) & 0xFFFF
                        elif op == '==': folded = 1 if lfv == rfv else 0
                        elif op == '!=': folded = 1 if lfv != rfv else 0
                        elif op == '<': folded = 1 if lfv < rfv else 0
                        elif op == '>': folded = 1 if lfv > rfv else 0
                        elif op == '<=': folded = 1 if lfv <= rfv else 0
                        elif op == '>=': folded = 1 if lfv >= rfv else 0
                        else: folded = None
                        if folded is not None:
                            self.emit_comment(
                                f"Constant folded (float): {expr.left.value} "
                                f"{op} {expr.right.value} -> Q8.8 {folded}")
                            reg = self.get_register()
                            self.emit(f"    MOV {reg}, {folded}")
                            return reg
                    left_val = int(expr.left.value, 0)
                    right_val = int(expr.right.value, 0)
                    if op == '+': folded = left_val + right_val
                    elif op == '-': folded = left_val - right_val
                    elif op == '*': folded = left_val * right_val
                    elif op == '/':
                        if right_val == 0:
                            folded = None
                            raise ArithmeticError("Division by zero")
                        # int() truncates toward zero: C's rule (-7/2 == -3),
                        # matching the ExpressionSimplifier's '/' fold.
                        folded = int(left_val / right_val)
                    elif op == '%':
                        if right_val == 0:
                            folded = None
                        else:
                            # C remainder (sign of the dividend, -7%2 == -1),
                            # not Python's divisor-signed %: derived from the
                            # truncated quotient so both folds agree.
                            _q = abs(left_val) // abs(right_val)
                            if (left_val < 0) != (right_val < 0):
                                _q = -_q
                            folded = left_val - _q * right_val
                    elif op == '&': folded = left_val & right_val
                    elif op == '|': folded = left_val | right_val
                    elif op == '^': folded = left_val ^ right_val
                    elif op == '<<': folded = left_val << right_val
                    elif op == '>>': folded = left_val >> right_val
                    elif op == '==': folded = 1 if left_val == right_val else 0
                    elif op == '!=': folded = 1 if left_val != right_val else 0
                    elif op == '<': folded = 1 if left_val < right_val else 0
                    elif op == '>': folded = 1 if left_val > right_val else 0
                    elif op == '<=': folded = 1 if left_val <= right_val else 0
                    elif op == '>=': folded = 1 if left_val >= right_val else 0
                    elif op == '&&': folded = 1 if (left_val != 0 and right_val != 0) else 0
                    elif op == '||': folded = 1 if (left_val != 0 or right_val != 0) else 0
                    else: folded = None
                    if folded is not None:
                        self.emit_comment(f"Constant folded: {left_val} {op} {right_val} = {folded}")
                        reg = self.get_register()
                        self.emit(f"    MOV {reg}, {folded}")
                        return reg
                except (ArithmeticError, ValueError):
                    pass

            if (expr.op == '&' and isinstance(expr.right, Number) and expr.right.value in ('0xFF', '255')):
                if (isinstance(expr.left, BinaryOp) and expr.left.op == '>>' and 
                    isinstance(expr.left.right, Number) and expr.left.right.value == '8'):
                    self.emit_comment("Optimized high-byte access: (val >> 8) & 0xFF")
                    val_reg = self.generate_expression(expr.left.left)
                    result_reg = self.get_register()
                    if val_reg.startswith('P'):
                        self.emit(f"    MOV {result_reg}, {val_reg}:")
                    else:
                        self.emit(f"    MOV {result_reg}, {val_reg}")
                    self.free_register()
                    return result_reg
                else:
                    self.emit_comment("Optimized low-byte access: val & 0xFF")
                    val_reg = self.generate_expression(expr.left)
                    result_reg = self.get_register()
                    if val_reg.startswith('P'):
                        self.emit(f"    MOV {result_reg}, :{val_reg}")
                    else:
                        self.emit(f"    MOV {result_reg}, {val_reg}")
                    self.free_register()
                    return result_reg
            
            if expr.op == '>>' or expr.op == '<<':
                can_push = not self._is_interrupt_handler
                is_right = (expr.op == '>>')
                if isinstance(expr.right, Number):
                    left_reg = self.generate_expression(expr.left)
                    self._emit_shift(left_reg, int(expr.right.value, 0),
                                     is_right, prefix="shift")
                    return left_reg
                # Variable shift count (C allows any int expression): protect
                # the left operand across RHS evaluation (round-robin temps).
                if can_push:
                    left_reg = self.generate_expression(expr.left)
                    self.emit(f"    PUSH {left_reg}")
                    count_reg = self.generate_expression(expr.right)
                    count_reg = self._pop_preserving(left_reg, count_reg)
                else:
                    # ISR: no stack protection possible. Evaluate the count
                    # FIRST and re-home it into a fresh register (allocated
                    # after the whole RHS, so the LHS evaluation below cannot
                    # revisit it within one wrap period).
                    count_reg = self.generate_expression(expr.right)
                    saved = self.get_register(exclude={count_reg})
                    self.emit(f"    MOV {saved}, {count_reg}")
                    count_reg = saved
                    left_reg = self.generate_expression(expr.left)
                self._emit_shift(left_reg, count_reg, is_right, prefix="shift")
                self.free_register()
                return left_reg

            left_reg = self.generate_expression(expr.left)
            # Preserve the left operand across right-hand evaluation:
            # expression temporaries are round-robin reused, and a deep RHS
            # (each array element read alone consumes two temporaries) would
            # otherwise clobber left_reg before the operation is emitted.
            can_push_left = not self._is_interrupt_handler
            if can_push_left:
                self.emit(f"    PUSH {left_reg}")
            right_reg = self.generate_expression(expr.right)
            if can_push_left:
                right_reg = self._pop_preserving(left_reg, right_reg)
            op = expr.op
            # ---- Float (Q8.8) promotion ----
            # If either operand is float-typed, the operation happens in
            # fixed-point: promote any integer side with ITOF so both share
            # the Q8.8 representation.  * and / then use FMUL/FDIV; + and -
            # are ordinary ADD/SUB (Q8.8 adds directly). Comparisons promote
            # too so both operands use an equal representation.
            if (self._cast_source_type(expr.left) == 'float' or
                    self._cast_source_type(expr.right) == 'float'):
                if op in ('+', '-', '*', '/'):
                    self.emit_comment("Float (Q8.8) operation - promote operands")
                    self._ensure_float(left_reg, expr.left)
                    self._ensure_float(right_reg, expr.right)
                    float_op = True
                elif op in ['==', '!=', '>', '<', '>=', '<=']:
                    self.emit_comment("Float (Q8.8) comparison - promote operands")
                    self._ensure_float(left_reg, expr.left)
                    self._ensure_float(right_reg, expr.right)
                    float_op = False  # comparisons yield an int 0/1
                else:
                    float_op = False
            else:
                float_op = False
            # Pointer arithmetic (C semantics): ptr ± n advances by
            # n * pointee_size bytes. Declared pointers, array parameters,
            # and decayed arrays all participate. The mirrored form
            # (n + ptr) produced by constant-first canonicalization of the
            # ExpressionSimplifier scales identically.
            if op in ('+', '-'):
                # Which side holds the pointer determines which operand
                # gets scaled: always scale the INTEGER offset.
                ptr_side_left = isinstance(expr.left, Identifier)
                if ptr_side_left:
                    step = self._pointer_step(expr.left.name)
                elif op == '+' and isinstance(expr.right, Identifier):
                    step = self._pointer_step(expr.right.name)
                else:
                    step = None
                if step and step > 1:
                    # Pointer on the left -> the RIGHT operand is the
                    # integer offset; mirrored form scales the LEFT one.
                    offset_reg = right_reg if ptr_side_left else left_reg
                    scale_reg = self.get_register(exclude={left_reg, right_reg})
                    self.emit(f"    MOV {scale_reg}, {step}")
                    self.emit(f"    MUL {offset_reg}, {scale_reg}")
            if op == '+': self.emit(f"    ADD {left_reg}, {right_reg}")
            elif op == '-': self.emit(f"    SUB {left_reg}, {right_reg}")
            elif op == '*':
                self.emit(f"    {'FMUL' if float_op else 'MUL'} {left_reg}, {right_reg}")
            elif op in ('/', '%'):
                # Signed operands (signed_int, negative literal) get the
                # sign-corrected sequence; plain/unsigned ints keep raw
                # hardware DIV/MOD -- see _use_signed_division.
                self._emit_divmod(op, left_reg, right_reg,
                                  expr.left, expr.right, float_op)
            elif op in ['==', '!=', '>', '<', '>=', '<=']:
                true_label = self.generate_label("cmp_true")
                end_label = self.generate_label("cmp_end")
                if op in ('==', '!='):
                    # Equality is the same under both interpretations.
                    self.emit(f"    CMP {left_reg}, {right_reg}")
                    self.emit(f"    {'JZ' if op == '==' else 'JNZ'} {true_label}")
                elif self._use_signed_comparison(expr.left, expr.right):
                    # Signed (two's-complement) comparison via the CPU's
                    # overflow⊕sign jumps: CMP left, right then JLT/JGE/JGT/JLE
                    # maps exactly to C's signed relational operators.  Used
                    # when a float (Q8.8) or a negative-valued constant is
                    # involved; plain byte/pointer comparisons stay unsigned.
                    self.emit_comment("Signed comparison (two's complement)")
                    self.emit(f"    CMP {left_reg}, {right_reg}")
                    cmp_jump = {'<': 'JLT', '>=': 'JGE',
                                '>': 'JGT', '<=': 'JLE'}[op]
                    self.emit(f"    {cmp_jump} {true_label}")
                elif op == '<':
                    # Unsigned: after CMP a,b (a-b) the borrow/carry flag is
                    # set iff a < b.
                    self.emit(f"    CMP {left_reg}, {right_reg}")
                    self.emit(f"    JC {true_label}")
                elif op == '>=':
                    self.emit(f"    CMP {left_reg}, {right_reg}")
                    self.emit(f"    JNC {true_label}")
                elif op == '>':
                    # Swap operands so a single carry test suffices.
                    self.emit(f"    CMP {right_reg}, {left_reg}")
                    self.emit(f"    JC {true_label}")
                elif op == '<=':
                    self.emit(f"    CMP {right_reg}, {left_reg}")
                    self.emit(f"    JNC {true_label}")
                self.emit(f"    MOV {left_reg}, 0")
                self.emit(f"    JMP {end_label}")
                self.emit_label(true_label)
                self.emit(f"    MOV {left_reg}, 1")
                self.emit_label(end_label)

            elif op == '&&':
                # Short-circuit AND: if left is 0, result is 0 (skip right)
                false_label = self.generate_label("sc_false")
                end_label = self.generate_label("sc_end")
                self.emit(f"    CMP {left_reg}, 0")
                self.emit(f"    JZ {false_label}")
                right_reg = self.generate_expression(expr.right)
                self.emit(f"    CMP {right_reg}, 0")
                self.emit(f"    JZ {false_label}")
                self.emit(f"    MOV {left_reg}, 1")
                self.emit(f"    JMP {end_label}")
                self.emit_label(false_label)
                self.emit(f"    MOV {left_reg}, 0")
                self.emit_label(end_label)
                self.free_register()
                return left_reg
            elif op == '||':
                # Short-circuit OR: if left is non-zero, result is 1 (skip right)
                true_label = self.generate_label("sc_true")
                end_label = self.generate_label("sc_end")
                self.emit(f"    CMP {left_reg}, 0")
                self.emit(f"    JNZ {true_label}")
                right_reg = self.generate_expression(expr.right)
                self.emit(f"    CMP {right_reg}, 0")
                self.emit(f"    JNZ {true_label}")
                self.emit(f"    MOV {left_reg}, 0")
                self.emit(f"    JMP {end_label}")
                self.emit_label(true_label)
                self.emit(f"    MOV {left_reg}, 1")
                self.emit_label(end_label)
                self.free_register()
                return left_reg
            elif op == '&': self.emit(f"    AND {left_reg}, {right_reg}")
            elif op == '|': self.emit(f"    OR {left_reg}, {right_reg}")
            elif op == '^': self.emit(f"    XOR {left_reg}, {right_reg}")
            else: raise SyntaxError(f"Unknown binary operator '{op}'")
            self.free_register()
            return left_reg
        elif isinstance(expr, UnaryOp):
            reg = self.generate_expression(expr.right)
            op = expr.op
            if op == '-':
                self.emit(f"    NEG {reg}")
            elif op == '~':
                # Bitwise NOT: 16-bit complement. Matches the CPU's NOT opcode.
                self.emit(f"    NOT {reg}")
            elif op == '!':
                # Logical NOT: must produce exactly 0 or 1, NOT bitwise
                # complement.  The CPU's NOT instruction gives ~value
                # (e.g. !5 -> 0xFFFA) which is a different magnitude and
                # has different truthiness than the C-style 0/1 result.
                not_true = self.generate_label("not_true")
                not_end = self.generate_label("not_end")
                self.emit(f"    CMP {reg}, 0")
                self.emit(f"    JZ {not_true}")
                # reg != 0 -> logical false (0)
                self.emit(f"    MOV {reg}, 0")
                self.emit(f"    JMP {not_end}")
                self.emit_label(not_true)
                # reg == 0 -> logical true (1)
                self.emit(f"    MOV {reg}, 1")
                self.emit_label(not_end)
            else:
                raise SyntaxError(f"Unknown unary operator '{op}'")
            return reg
        elif isinstance(expr, ArrayAccess):
            return self.generate_array_access(expr)
        elif isinstance(expr, Assignment):
            # Assignment used as an expression (chained assignment like
            # `a = b = c`, or assignments inside conditions/arguments):
            # store the RHS and yield the assigned value.
            reg = self.generate_expression(expr.value)
            self._emit_var_store(expr.name, reg)
            return reg
        elif isinstance(expr, ArrayAssignment):
            return self.generate_array_assignment(expr)
        elif isinstance(expr, MemberAssignment):
            return self.generate_member_assignment(expr)
        elif isinstance(expr, MemberAccess):
            return self.generate_member_access(expr)
        elif isinstance(expr, DerefAssignment):
            return self.generate_deref_assignment(expr)
        elif isinstance(expr, AddressOf):
            return self.generate_address_of(expr)
        elif isinstance(expr, Deref):
            # Load through a pointer: evaluate the address expression (the
            # generic BinaryOp path already scales ptr ± n by the pointee
            # size for both constant and variable offsets), then read
            # through it.
            ptr_reg = self.generate_expression(expr.operand)
            self._emit_mem_load(ptr_reg, ptr_reg, self._pointee_size(expr.operand))
            return ptr_reg
        elif isinstance(expr, SizeofExpr):
            reg = self.get_register()
            self.emit(f"    MOV {reg}, {self._sizeof_bytes(expr)}")
            return reg
        elif isinstance(expr, TernaryOp):
            return self.generate_ternary(expr)
        elif isinstance(expr, CommaOp):
            # Comma operator: evaluate left (discard result), then evaluate
            # right and return its value. Matches C semantics.
            self.generate_expression(expr.left)
            return self.generate_expression(expr.right)
        elif isinstance(expr, PrefixOp):
            return self.generate_prefix(expr)
        elif isinstance(expr, PostfixOp):
            # `const x++` / `const p[0]++` are writes: same rules as '='.
            self._check_const_base(expr.left, expr)
            if isinstance(expr.left, Identifier):
                reg = self.get_register()
                self._emit_var_load(reg, expr.left.name)
                result_reg = self.get_register(exclude={reg})
                self.emit(f"    MOV {result_reg}, {reg}")
                # Pointer postfix ++/-- advance by the pointee size (C).
                step = self._pointer_step(expr.left.name)
                # Float variables increment/decrement by 1.0 (256 in Q8.8),
                # not by 1/256 (the INC/DEC unit in Q8.8 space).
                is_float = self._cast_source_type(expr.left) == 'float'
                float_step = 256  # 1.0 in Q8.8 fixed-point
                if expr.op == '++':
                    if step and step > 1:
                        self.emit(f"    ADD {reg}, {step}")
                    elif is_float:
                        self.emit(f"    ADD {reg}, {float_step}")
                    else:
                        self.emit(f"    INC {reg}")
                elif expr.op == '--':
                    if step and step > 1:
                        self.emit(f"    SUB {reg}, {step}")
                    elif is_float:
                        self.emit(f"    SUB {reg}, {float_step}")
                    else:
                        self.emit(f"    DEC {reg}")
                else:
                    raise SyntaxError(f"Unknown postfix operator '{expr.op}'")
                self._emit_var_store(expr.left.name, reg)
                self.free_register()
                return result_reg
            if isinstance(expr.left, Deref):
                # (*p)++ / (*p)-- : returns the OLD pointee value.
                ptr_reg = self.generate_expression(expr.left.operand)
                size = self._pointee_size(expr.left.operand)
                old_reg = self.get_register(exclude={ptr_reg})
                self._emit_mem_load(old_reg, ptr_reg, size)
                result_reg = self.get_register(exclude={ptr_reg, old_reg})
                self.emit(f"    MOV {result_reg}, {old_reg}")
                if expr.op == '++':
                    self.emit(f"    INC {old_reg}")
                elif expr.op == '--':
                    self.emit(f"    DEC {old_reg}")
                else:
                    raise SyntaxError(f"Unknown postfix operator '{expr.op}'")
                self._emit_mem_store(ptr_reg, old_reg, size)
                return result_reg
            if isinstance(expr.left, MemberAccess):
                # p.x++ / p.x-- : returns the OLD member value (C semantics).
                target = expr.left
                self.emit_comment(f"Postfix {expr.op} on member ({target.field})")
                addr_reg = self.get_register()
                self._emit_member_addr(target, addr_reg)
                old_reg = self.get_register(exclude={addr_reg})
                self._emit_mem_load(old_reg, addr_reg, 2)
                result_reg = self.get_register(exclude={addr_reg, old_reg})
                self.emit(f"    MOV {result_reg}, {old_reg}")
                if expr.op == '++':
                    self.emit(f"    INC {old_reg}")
                elif expr.op == '--':
                    self.emit(f"    DEC {old_reg}")
                else:
                    raise SyntaxError(f"Unknown postfix operator '{expr.op}'")
                self._emit_mem_store(addr_reg, old_reg, 2)
                return result_reg
            if isinstance(expr.left, ArrayAccess):
                # arr[i]++ / arr[i]-- : returns the OLD value (C semantics).
                # 2-D subscripts desugar to the flat form first (no-op 1-D).
                target = self._linearize_2d_inplace(expr.left)
                info = self._get_array_info(target.name)
                can_push = not self._is_interrupt_handler
                idx_reg = self.generate_expression(target.index)
                if can_push:
                    self.emit(f"    PUSH {idx_reg}")
                addr_reg = self.get_register()
                self._emit_array_addr(info, idx_reg, addr_reg)
                old_reg = self.get_register()
                self._emit_mem_load(old_reg, addr_reg, info['elem_size'])
                result_reg = self.get_register()
                self.emit(f"    MOV {result_reg}, {old_reg}")
                if expr.op == '++':
                    self.emit(f"    INC {old_reg}")
                elif expr.op == '--':
                    self.emit(f"    DEC {old_reg}")
                else:
                    raise SyntaxError(f"Unknown postfix operator '{expr.op}'")
                self._emit_mem_store(addr_reg, old_reg, info['elem_size'])
                return result_reg
            raise SyntaxError("Postfix operators can only be applied to variables, pointers, or array elements")
        elif isinstance(expr, FuncCall):
            return self.generate_call(expr)
        elif isinstance(expr, MethodCall):
            return self.generate_method_call(expr)
        else:
            raise RuntimeError(f"Unknown expression type: {type(expr)}")

    def emit_unsigned_to_string(self, dest_reg: str, value_reg: str,
                                base_addr: int = None):
        """Emit a software unsigned-to-string conversion using only Nova-16 ops.

        This avoids inventing a new hardware instruction while keeping the
        correct 16-bit unsigned magnitude semantics for values like 655300.
        The result is stored as a NUL-terminated ASCII string at the layout's
        ITOS scratch cell (0xA000 by default, 0xC000 under bank-safe) and the
        buffer address is returned in dest_reg. ``base_addr`` overrides that
        cell so a caller can reserve a leading byte (the signed converter
        prefixes '-' with it).
        """
        base = self.itos_buffer if base_addr is None else base_addr
        tmp = self.get_register(exclude={value_reg, dest_reg})
        scratch = self.get_register(exclude={value_reg, dest_reg, tmp})
        quotient = self.get_register(exclude={value_reg, dest_reg, tmp, scratch})
        digit = self.get_register(exclude={value_reg, dest_reg, tmp, scratch, quotient})
        
        zero_label = self.generate_label("utoa_zero")
        loop_label = self.generate_label("utoa_loop")
        done_label = self.generate_label("utoa_done")
        reverse_label = self.generate_label("utoa_rev")
        finish_label = self.generate_label("utoa_finish")

        # Check for zero
        self.emit(f"    CMP {value_reg}, 0")
        self.emit(f"    JZ {zero_label}")
        
        # Generate digits in reverse order at the ITOB scratch cell
        # (layout-dependent: 0xA100 by default, 0xC100 under bank-safe).
        self.emit(f"    MOV {tmp}, {value_reg}")
        self.emit(f"    MOV {scratch}, 0x{self.itob_buffer:04X}")
        self.emit_label(loop_label)
        self.emit(f"    CMP {tmp}, 0")
        self.emit(f"    JZ {done_label}")
        self.emit(f"    MOV {quotient}, {tmp}")
        self.emit(f"    MOV {digit}, 10")
        self.emit(f"    DIV {quotient}, {digit}")
        self.emit(f"    MOV {digit}, P3")
        self.emit(f"    ADD {digit}, 48")
        # MOV [mem], Psrc writes a 16-bit big-endian word whose high byte
        # (0x00 for ASCII digits) lands at the target address and pushes the
        # digit one byte further -- corrupting the next slot.  Route the byte
        # through R0 (same convention as _emit_mem_store) for an 8-bit write.
        self.emit(f"    MOV R0, {digit}")
        self.emit(f"    MOV [{scratch}], R0")
        self.emit(f"    MOV {tmp}, {quotient}")
        self.emit(f"    INC {scratch}")
        self.emit(f"    JMP {loop_label}")

        self.emit_label(done_label)
        # Now reverse the digits from the ITOB cell into the ITOS cell...
        # scratch points to ONE PAST the last digit, so DEC back to the last
        self.emit(f"    DEC {scratch}")
        # Copy backward: read from scratch (going down), write to target (going up)
        self.emit(f"    MOV {tmp}, 0x{base:04X}")
        self.emit_label(reverse_label)
        # Unsigned loop: continue while scratch >= the ITOB cell (unsigned).
        # Once scratch drops below it (borrow), JC will jump.
        self.emit(f"    CMP {scratch}, 0x{self.itob_buffer:04X}")
        self.emit(f"    JC {finish_label}")  # Unsigned: jump if carry (borrow), i.e., scratch < ITOB
        # Byte reads/writes only: the source buffer holds packed ASCII bytes,
        # so a word read (high byte) or word store (high byte 0x00) would
        # contaminate the neighbouring cell.
        self.emit(f"    MOV R0, [{scratch}]")
        self.emit(f"    MOV [{tmp}], R0")
        self.emit(f"    INC {tmp}")
        self.emit(f"    DEC {scratch}")
        self.emit(f"    JMP {reverse_label}")
        
        self.emit_label(finish_label)
        self.emit(f"    MOV [{tmp}], 0")
        self.emit(f"    MOV {dest_reg}, 0x{base:04X}")
        self.emit(f"    JMP {finish_label}_end")
        
        self.emit_label(zero_label)
        self.emit(f"    MOV [0x{base:04X}], 48")
        self.emit(f"    MOV [0x{base + 1:04X}], 0")
        self.emit(f"    MOV {dest_reg}, 0x{base:04X}")
        
        self.emit_label(f"{finish_label}_end")

    def emit_signed_to_string(self, dest_reg: str, value_reg: str):
        """Signed decimal conversion with NO hardware ITOS dependency.

        WHY: the CPU's ITOS instruction ALWAYS writes its scratch digits to the
        fixed 0xA000 cell (core/exec_handlers.py::_itos), regardless of the
        operand, and 0xA000 lives inside the 0x8000-0xBFFF bank window. A banked
        program (NovaDOS NDF disk I/O) would therefore scribble decimal digits
        over a disk page. This routine produces the same text using only the
        active layout's itos_buffer/itob_buffer cells (0xC000/0xC100 under
        bank-safe), so the bank window is never written.

        Negative values get '-' at the ITOS cell followed by the magnitude one
        byte higher (base override), keeping every byte in the layout block.
        """
        negative_label = self.generate_label("stoa_neg")
        end_label = self.generate_label("stoa_end")
        magnitude = self.get_register(exclude={value_reg})

        self.emit_comment("Signed decimal conversion (layout-local scratch)")
        self.emit(f"    CMP {value_reg}, 0")
        self.emit(f"    JS {negative_label}")
        # Non-negative: plain unsigned conversion into the ITOS cell.
        self.emit_unsigned_to_string(dest_reg, value_reg)
        self.emit(f"    JMP {end_label}")

        self.emit_label(negative_label)
        # magnitude = 0 - value (two's complement). value_reg is dead from here,
        # so R0 is free for the strict 8-bit byte store below.
        self.emit(f"    MOV {magnitude}, 0")
        self.emit(f"    SUB {magnitude}, {value_reg}")
        self.emit(f"    MOV R0, 45")
        self.emit(f"    MOV [0x{self.itos_buffer:04X}], R0")
        self.emit(f"    MOV [0x{self.itos_buffer + 1:04X}], 0")
        self.emit_unsigned_to_string(dest_reg, magnitude,
                                     base_addr=self.itos_buffer + 1)
        # Re-point the result at the leading '-', not at the first digit.
        self.emit(f"    MOV {dest_reg}, 0x{self.itos_buffer:04X}")

        self.emit_label(end_label)

    def emit_hex_string(self, dest_reg: str, value_reg: str):
        """Emit a software unsigned-to-hex-string conversion using only Nova-16 ops.

        Converts a 16-bit value to a 4-character hex string (e.g. 0xDEAD -> "DEAD").
        The result is stored as a NUL-terminated ASCII string at 0xA000 and the
        buffer address is returned in dest_reg.

        Implementation notes:
          * R0 is deliberately AVOIDED as a scratch register: this routine runs
            in the middle of expression evaluation where R0 may still be live
            (it is the compiler's return-value/scratch register), so all work
            uses separately-allocated P-register temporaries.
          * Extraction order: shift THEN mask (SHR Pn, imm; AND Pn, 0x0F), so
            each nibble of the 16-bit value lands in the low 4 bits in turn.
          * ASCII selection uses the sign flag from CMP nibble, 10: a negative
            result means nibble < 10 (digit '0'-'9', add 48); otherwise the
            nibble is 10-15 (uppercase 'A'-'F', add 55).
        """
        tmp = self.get_register(exclude={value_reg, dest_reg})
        scratch = self.get_register(exclude={value_reg, dest_reg, tmp})
        nibble = self.get_register(exclude={value_reg, dest_reg, tmp, scratch})

        # Generate 4 hex digits (most significant nibble first)
        self.emit(f"    MOV {scratch}, 0x{self.itos_buffer:04X}")
        self.emit(f"    MOV {tmp}, {value_reg}")

        # Process each nibble from bits 12-15 down to 0-3
        for shift in (12, 8, 4, 0):
            self.emit(f"    MOV {nibble}, {tmp}")
            if shift > 0:
                self.emit(f"    SHR {nibble}, {shift}")
            self.emit(f"    AND {nibble}, 0x0F")
            # Convert nibble to ASCII: 0-9 -> '0'-'9', 10-15 -> 'A'-'F'
            self.emit(f"    CMP {nibble}, 10")
            self.emit(f"    JS .hex_digit_{shift}")
            self.emit(f"    ADD {nibble}, 55")  # 'A' = 65, 65 - 10 = 55
            self.emit(f"    JMP .hex_done_{shift}")
            self.emit_label(f".hex_digit_{shift}")
            self.emit(f"    ADD {nibble}, 48")  # '0' = 48
            self.emit_label(f".hex_done_{shift}")
            # MOV [mem], Psrc writes a 16-bit big-endian word whose high byte
            # (0x00 for ASCII chars) lands at the target address -- it would
            # shove each hex char one byte forward and corrupt the slot.  Route
            # the byte through R0 (same convention as _emit_mem_store and
            # emit_unsigned_to_string) for a strict 8-bit write.
            self.emit(f"    MOV R0, {nibble}")
            self.emit(f"    MOV [{scratch}], R0")
            self.emit(f"    INC {scratch}")

        # NUL terminate
        self.emit(f"    MOV [{scratch}], 0")
        self.emit(f"    MOV {dest_reg}, 0x{self.itos_buffer:04X}")

    def generate_cast(self, cast: Cast) -> str:
        """Generate code for type cast expressions using Nova-16 conversion instructions.

        Supported casts:
          (string)expr   -> ITOS:  converts int expr to decimal string at 0xA000,
                                    returns buffer address
          (stringh)expr  -> converts int expr to hex string at 0xA000,
                                    returns buffer address
          (binary)expr   -> ITOB:  converts int expr to binary string at 0xA100,
                                    returns buffer address
          (int)expr      -> STOI/BTOI: converts string/binary addr to int
          (char)expr     -> truncates to 8 bits (low byte)
        """
        target = cast.target_type
        # 'signed_int' / 'unsigned_int' share int's representation and codegen
        # path; the distinction is kept in type metadata, not in the emitted
        # register layout.
        if target in ('signed_int', 'unsigned_int'):
            target = 'int'
        # Address cast: (int *)0xF000, (char *)addr. A pointer is a plain
        # 16-bit address, so the cast is an identity conversion -- the value
        # is the FULL address (never masked to the pointee width). This is
        # what makes `*(int *)0xF000` load a word from 0xF000, matching the
        # peek2/poke2 behaviour without a new codegen path.
        if getattr(cast, 'pointer_depth', 0) > 0:
            return self.generate_expression(cast.expr)
        inner = cast.expr

        # Identity cast optimization: casting to the type the expression
        # already produces is a no-op (just a register copy). Without this,
        # `(string)s` where s is a string variable would ITOS the string
        # *address* — producing the decimal digits of the pointer — instead
        # of simply passing the existing string through.
        source_type = self._cast_source_type(inner)
        # Preserve the explicit integer signedness until the conversion
        # instruction is selected. For example, an unsigned 16-bit value must
        # use UITOS instead of the signed ITOS path.
        if source_type == target and target in ('string', 'binary', 'int', 'char', 'float'):
            reg = self.get_register()
            inner_reg = self.generate_expression(inner)
            if inner_reg != reg:
                self.emit(f"    MOV {reg}, {inner_reg}")
            self.free_register()
            return reg

        # Compile-time optimization: casting a literal is a compile-time op.
        if isinstance(inner, Number):
            is_float_const = '.' in inner.value
            if is_float_const:
                fval = float(inner.value)
                num_val = self._float_to_q8(inner.value)  # Q8.8 encoding
            else:
                fval = None
                num_val = int(inner.value, 0) & 0xFFFF
            if target == 'char':
                reg = self.get_register()
                if is_float_const:
                    # (char)1.5 -> integer part (FTOI), then low byte.
                    self.emit(f"    MOV {reg}, {int(fval) & 0xFF}")
                else:
                    self.emit(f"    MOV {reg}, {num_val & 0xFF}")
                return reg
            elif target == 'int':
                reg = self.get_register()
                if is_float_const:
                    # (int)1.5 -> FTOI: truncate toward zero.
                    self.emit(f"    MOV {reg}, {int(fval) & 0xFFFF}")
                else:
                    self.emit(f"    MOV {reg}, {num_val}")
                return reg
            elif target == 'float':
                reg = self.get_register()
                if is_float_const:
                    self.emit(f"    MOV {reg}, {num_val}")
                else:
                    # (float)5 -> encode the integer as Q8.8 (5 << 8).
                    self.emit(f"    MOV {reg}, {num_val * self._FLOAT_SCALE & 0xFFFF}")
                return reg
            # string/binary literal casts fall through to runtime

        self.emit_comment(f"Type cast: ({target}) expr")
        inner_reg = self.generate_expression(inner)
        result_reg = self.get_register()

        if target == 'string':
            # A char source is a GLYPH, not a count: (string)'l' must yield
            # the 1-character string "l", NOT the decimal digits of its code
            # ("108").  Store the byte as a 1-byte NUL-terminated string in
            # the ITOS scratch buffer (0xA000) and return its address.  This
            # mirrors the write_text char handling and keeps (int)char as the
            # way to render the numeric value as digits.
            if source_type == 'char':
                self.emit_comment("Char-to-string: 1-byte glyph string")
                self.emit(f"    MOV R0, {inner_reg}")
                self.emit(f"    MOV [0x{self.itos_buffer:04X}], R0")
                self.emit(f"    MOV [0x{self.itos_buffer + 1:04X}], 0")
                self.emit(f"    MOV {result_reg}, 0x{self.itos_buffer:04X}")
            # Use the built-in ITOS path for signed values. Unsigned values need
            # a software decimal conversion because the Nova-16 ISA does not have
            # a UITOS instruction.
            elif source_type == 'unsigned_int':
                self.emit_unsigned_to_string(result_reg, inner_reg)
            elif self.memory_layout_name == 'bank-safe':
                # ITOS scribbles its digits at the fixed 0xA000 cell inside the
                # bank window; a banked program would overwrite a disk page.
                self.emit_signed_to_string(result_reg, inner_reg)
            else:
                self.emit(f"    ITOS {result_reg}, {inner_reg}")
        elif target == 'stringh':
            # (stringh)expr converts an integer to a 4-character hex string
            # (e.g. 0xDEAD -> "DEAD"). Uses the same 0xA000 scratch buffer
            # as ITOS but produces uppercase hex digits.
            self.emit_comment("Hex string conversion")
            self.emit_hex_string(result_reg, inner_reg)
        elif target == 'binary':
            # ITOB writes the binary string to the fixed buffer 0xA100 and
            # writes that buffer address into the destination operand.
            # First load the fixed buffer address into a temp register.
            self.emit(f"    MOV {result_reg}, 0x{self.itob_buffer:04X}")
            self.emit(f"    ITOB {result_reg}, {inner_reg}")
        elif target == 'int':
            # STOI parses a decimal string; BTOI parses a binary string.
            # A float source needs FTOI (Q8.8 -> integer).  Numeric sources
            # (int/char) already hold their value, so a plain MOV is right.
            if source_type == 'binary':
                self.emit(f"    BTOI {result_reg}, {inner_reg}")
            elif source_type == 'string':
                self.emit(f"    STOI {result_reg}, {inner_reg}")
            elif source_type == 'float':
                # (int)floatExpr: FTOI truncates the fixed-point value.
                self.emit(f"    MOV {result_reg}, {inner_reg}")
                self.emit(f"    FTOI {result_reg}")
            else:
                # Numeric (int/char): value already in inner_reg; just copy.
                self.emit(f"    MOV {result_reg}, {inner_reg}")
        elif target == 'char':
            # Truncate to 8 bits (low byte).  A float source is first
            # converted to integer (FTOI) so (char)1.5 -> 1, not 0x80.
            if source_type == 'float':
                self.emit(f"    MOV {result_reg}, {inner_reg}")
                self.emit(f"    FTOI {result_reg}")
            elif inner_reg.startswith('P'):
                self.emit(f"    MOV {result_reg}, :{inner_reg}")
            else:
                self.emit(f"    MOV {result_reg}, {inner_reg}")
        elif target == 'float':
            # (float)expr -> ITOF. String/binary sources parse to an int
            # first, then promote; other numeric sources promote directly.
            if source_type == 'string':
                self.emit(f"    STOI {result_reg}, {inner_reg}")
                self.emit(f"    ITOF {result_reg}")
            elif source_type == 'binary':
                self.emit(f"    BTOI {result_reg}, {inner_reg}")
                self.emit(f"    ITOF {result_reg}")
            else:
                self.emit(f"    MOV {result_reg}, {inner_reg}")
                self.emit(f"    ITOF {result_reg}")
        else:
            raise TypeError(f"Unknown cast target type '{target}'")

        self.free_register()  # inner_reg no longer needed
        return result_reg

    def _is_string_or_binary_expr(self, expr: Expression) -> bool:
        """Determine if an expression produces a string or binary typed value."""
        if isinstance(expr, Identifier):
            # LOCAL declarations first (C shadowing semantics), then GLOBAL
            # declarations as fallback: var_types only holds locals+params
            # for the function currently being generated, so a file-scope
            # `string sword;` was invisible here and write_text(sword)
            # ITOS-converted the variable's POINTER into decimal digits.
            if expr.name in self.var_types:
                return self.var_types[expr.name] in ('string', 'binary')
            g = self.global_vars.get(expr.name)
            if g:
                return g['type'] in ('string', 'binary')
        if isinstance(expr, StringLiteral):
            return True
        if isinstance(expr, Cast):
            return expr.target_type in ('string', 'stringh', 'binary')
        if isinstance(expr, FuncCall):
            func = self.functions.get(expr.name)
            return bool(func and func.get('return_type') in ('string', 'binary'))
        if isinstance(expr, BinaryOp) and self._is_string_concat(expr):
            # "a" + "b" produces a string value (a scratch-buffer address).
            return True
        return False

    def _is_string_expr(self, expr: Expression) -> bool:
        """True when `expr` produces a string/binary VALUE (not an address
        into one).  String literals, (string)/(stringh)/(binary) casts, string/binary
        scalar variables, and string-returning user functions qualify;
        char* / int* pointer variables and single-character string-index
        expressions ("abc"[i], which yield a byte) do not."""
        if isinstance(expr, StringLiteral):
            return True
        if isinstance(expr, Identifier):
            if expr.name in self.var_types:
                return self.var_types[expr.name] in ('string', 'binary')
            g = self.global_vars.get(expr.name)
            return bool(g and not g.get('is_array') and not g.get('is_pointer')
                        and g['type'] in ('string', 'binary'))
        if isinstance(expr, Cast):
            return expr.target_type in ('string', 'stringh', 'binary')
        if isinstance(expr, FuncCall):
            func = self.functions.get(expr.name)
            return bool(func and func.get('return_type') in ('string', 'binary'))
        if isinstance(expr, BinaryOp) and self._is_string_concat(expr):
            return True
        return False

    def _is_string_concat(self, expr: Expression) -> bool:
        return (isinstance(expr, BinaryOp) and expr.op == '+'
                and self._is_string_expr(expr.left)
                and self._is_string_expr(expr.right))

    def _is_string_or_binary_scalar(self, name: str) -> bool:
        """True when `name` is a SCALAR string/binary variable (local or
        global).  Such variables store a char* pointer, so `name[i]` means a
        byte read/write through that pointer -- distinct from declared char
        arrays (which index their own inline storage) and from arrays of
        strings (which the array machinery already lays out as word slots)."""
        if name in self.var_types:
            return self.var_types[name] in ('string', 'binary')
        g = self.global_vars.get(name)
        return bool(g and not g.get('is_array') and not g.get('is_pointer')
                    and g['type'] in ('string', 'binary'))

    def _alloc_concat_buffer(self) -> int:
        """Reserve the next scratch buffer for a runtime string concatenation.

        Each emitted '+' operator consumes exactly one fresh buffer (never a
        re-use), so neither operand's bytes can be clobbered by a nested
        concat during evaluation -- the left operand's ADDRESS is safe on the
        stack because its bytes live in a DEFSTR or a buffer that will never
        be touched again within this concat tree."""
        if self._concat_buf_index >= len(self.string_concat_buffers):
            raise SyntaxError(
                "String concatenation nesting exceeds the scratch buffer "
                "capacity ({}) -- split the expression or use strcat/strcpy"
                .format(len(self.string_concat_buffers)))
        addr = self.string_concat_buffers[self._concat_buf_index]
        self._concat_buf_index += 1
        return addr

    def _generate_string_concat(self, expr: BinaryOp) -> str:
        """Generate a runtime string concatenation `expr`.

        Strategy: materialize the LEFT operand, save its address on the stack
        while the RIGHT is evaluated (it may itself be a nested concat), then
        STRCPY left + STRCAT right into a freshly allocated scratch buffer and
        return that buffer's address in a register.

        The left operand is evaluated FIRST (C left-to-right order), then
        pushed; a fresh buffer per operator guarantees the right side can't
        corrupt the left's storage."""
        if not isinstance(expr, BinaryOp) or expr.op != '+':
            raise SyntaxError(
                "internal: _generate_string_concat requires a '+' BinaryOp")
        self.emit_comment("String concatenation")
        left_reg = self._string_operand(expr.left)
        self.emit(f"    PUSH {left_reg}")
        right_reg = self._string_operand(expr.right)
        # _pop_preserving pops the stack TOP into its FIRST argument
        # (left_reg, the saved left address) while protecting the second
        # argument (right_reg), relocating it if the names alias.  The return
        # value is the (possibly relocated) protected-register handle.
        right_reg = self._pop_preserving(left_reg, right_reg)
        buf_addr = self._alloc_concat_buffer()
        result_reg = self.get_register(exclude={left_reg, right_reg})
        self.emit(f"    MOV {result_reg}, 0x{buf_addr:04X}")
        self.emit(f"    STRCPY {result_reg}, {left_reg}")
        self.emit(f"    STRCAT {result_reg}, {right_reg}")
        self.free_register()  # left_reg
        self.free_register()  # right_reg
        return result_reg

    def _string_operand(self, expr: Expression) -> str:
        """Evaluate a concat operand and return a register holding its address."""
        if self._is_string_concat(expr):
            return self._generate_string_concat(expr)
        return self.generate_expression(expr)

    # ------------------------------------------------------------------
    # Floating-point (Q8.8 fixed-point) helpers
    # ------------------------------------------------------------------
    #
    # The Nova-16 CPU has no native IEEE-754 floating point; its "float"
    # support is Q8.8 fixed-point: a 16-bit value whose high byte holds the
    # signed integer part and low byte holds 1/256ths.  Astrid's `float`
    # maps directly onto this representation (2 bytes, stored like an int),
    # calling ITOF/FTOI for conversions and FMUL/FDIV for multiply/divide.
    # Addition and subtraction need no scaling (fixed-point adds directly).
    _FLOAT_SCALE = 256

    def _is_float_literal(self, expr: Expression) -> bool:
        """True if `expr` is a floating-point literal (contains a '.')."""
        return isinstance(expr, Number) and '.' in expr.value

    def _float_to_q8(self, literal: str) -> int:
        """Encode a decimal float literal to its Q8.8 fixed-point integer.

        E.g. "1.5" -> 384 (0x0180), "-1.5" -> 0xFE80. The result is masked
        to 16 bits so it can be emitted as a plain immediate (or DW word).
        """
        try:
            value = float(literal)
        except ValueError:
            value = 0.0
        return int(round(value * self._FLOAT_SCALE)) & 0xFFFF

    def _ensure_float(self, reg: str, expr: Expression):
        """Emit an in-place ITOF so `reg` holds `expr` as Q8.8.

        `expr`'s value is already in `reg` as a raw integer. If the
        expression is not already float-typed, promote it to fixed-point.
        Used when a float arithmetic operand must be Q8.8 while a sibling
        operand is an integer (implicit int -> float promotion on mixed
        float expressions, matching C semantics).
        """
        if self._cast_source_type(expr) != 'float':
            self.emit_comment("Promote int operand to float (Q8.8)")
            self.emit(f"    ITOF {reg}")

    def _cast_source_type(self, expr: Expression) -> Optional[str]:
        """Determine the type of an expression's value for cast resolution.

        Returns 'string', 'binary', 'int', 'signed_int', 'unsigned_int',
        'char', or None if unknown. 'signed_int' and 'unsigned_int' mark
        values declared with explicit C qualifiers so comparison logic can
        choose the correct signed/unsigned branch instead of collapsing both
        to plain int.
        Used by generate_cast to pick STOI/BTOI vs simple MOV for (int) casts,
        and by identity-cast elimination when casting to the same type.
        """
        if isinstance(expr, MemberAccess):
            # Struct field read (p.x, pts[i].y): resolve the declared
            # field type through the struct layout so signed members
            # propagate their signedness into comparison decisions.
            try:
                _, tag = self._member_base_info(expr)
                return self._struct_field_type(tag, expr.field)
            except (NameError, SyntaxError):
                return None
        if isinstance(expr, Identifier):
            # Locals first (shadowing semantics); globals provide the
            # fallback so casts on file-scope string/binary variables pick
            # STOI/BTOI instead of a plain MOV of the pointer.
            if expr.name in self.var_types:
                return self.var_types.get(expr.name)
            g = self.global_vars.get(expr.name)
            # Scalar globals only: array identifiers decay to an address, so
            # (int)someGlobalCharArray must stay a plain MOV of the pointer.
            if g and not g.get('is_array'):
                return g['type']
            return None
        if isinstance(expr, Cast):
            # An address cast yields an address (int-like), not a typed
            # scalar: (char *)x must NOT be treated as a char value.
            if getattr(expr, 'pointer_depth', 0) > 0:
                return None
            # (stringh)x yields a string value (hex representation)
            if expr.target_type == 'stringh':
                return 'string'
            return expr.target_type  # (string)x yields a string value
        if isinstance(expr, StringLiteral):
            return 'string'
        if isinstance(expr, StringIndexAccess):
            # "abc"[i] / "abc"[CONST] yields a single character byte.
            return 'char'
        if isinstance(expr, CharLiteral):
            return 'char'
        if isinstance(expr, Number):
            # A decimal point marks a floating-point literal (Q8.8).
            return 'float' if '.' in expr.value else 'int'
        if isinstance(expr, FuncCall):
            func = self.functions.get(expr.name)
            if func:
                return func.get('return_type')
            # Builtin functions aren't in self.functions; look up their
            # return type from the dedicated table.
            return self.BUILTIN_RETURN_TYPES.get(expr.name)
        if isinstance(expr, PostfixOp):
            if isinstance(expr.left, Identifier):
                return self.var_types.get(expr.left.name)
        if isinstance(expr, ArrayAccess):
            # s[i] on a string/binary scalar is a single-byte character read.
            if self._is_string_or_binary_scalar(expr.name):
                return 'char'
            try:
                info = self._get_array_info(expr.name)
            except NameError:
                return None
            if 'elem_type' in info:
                return info['elem_type']
            # Pointer subscript (p[i] where p is a pointer variable): the
            # element type is the pointee type, looked up from the pointer's
            # declared base type (var_types for locals/params, global_vars for
            # file-scope pointers). This keeps char*/int*/float*/etc. indexing
            # typing-consistent with the rest of the cast machinery.
            if info.get('is_pointer'):
                pt = self.var_types.get(expr.name)
                if pt is None:
                    g = self.global_vars.get(expr.name)
                    if g and not g.get('is_array') and not g.get('is_pointer'):
                        pt = g['type']
                    elif g and g.get('is_pointer'):
                        pt = g['type']
                return pt  # None if the pointer's type can't be resolved
            return None
        if isinstance(expr, BinaryOp):
            # A '+' of two string/binary values yields a string; otherwise
            # an arithmetic/comparison expression is float if either operand
            # is float (implicit promotion), else integer-valued.
            if self._is_string_concat(expr):
                return 'string'
            if (self._cast_source_type(expr.left) == 'float' or
                    self._cast_source_type(expr.right) == 'float'):
                return 'float'
            ltype = self._cast_source_type(expr.left)
            rtype = self._cast_source_type(expr.right)
            if ltype == 'unsigned_int' or rtype == 'unsigned_int':
                return 'unsigned_int'
            if ltype == 'signed_int' or rtype == 'signed_int':
                return 'signed_int'
            return 'int'
        if isinstance(expr, UnaryOp):
            # -x / !x / ~x preserve the operand's numeric category.
            rtype = self._cast_source_type(expr.right)
            if rtype == 'float':
                return 'float'
            if rtype == 'unsigned_int':
                return 'unsigned_int'
            if rtype == 'signed_int':
                return 'signed_int'
            return 'int'
        return None

    def _use_signed_comparison(self, left: Expression,
                               right: Expression) -> bool:
        """Whether a relational <, <=, >, >= should use signed jumps.

        Nova-16 offers both unsigned (JC/JNC borrow-based) and signed
        (JLT/JGE/JGT/JLE, overflow XOR sign) comparison families.  Astrid
        mirrors C's default-signed semantics wherever the operands' types
        or values make the intent unambiguous:

        * ``char`` / ``binary`` / ``string`` values are byte-oriented and
          compare unsigned (their high bit legitimately encodes 128-255).
        * Q8.8 ``float`` uses a signed fixed-point representation, so any
          float comparison is signed.
        * A value declared with the ``signed`` qualifier ('signed_int',
          e.g. a struct health field) always compares signed: it can
          legitimately hold negative values such as -1 after damage.
        * A compile-time constant whose top bit is set (negative literal
          such as -1 or -0x8000, or a hex constant 0x8000+ written
          directly) flips the comparison to signed -- the C interpretation
          of such a constant is a negative number.

        Everything else keeps the historical unsigned behavior: pointer
        values, addresses, and program counters live at 0x8000+ and must
        not be treated as negatives.
        """
        ltype = self._cast_source_type(left)
        rtype = self._cast_source_type(right)
        if ltype in ('char', 'binary', 'string') or \
                rtype in ('char', 'binary', 'string'):
            return False
        if ltype == 'float' or rtype == 'float':
            return True
        if ltype == 'unsigned_int' or rtype == 'unsigned_int':
            return False
        if ltype == 'signed_int' or rtype == 'signed_int':
            return True
        lval = self._const_eval(left)
        rval = self._const_eval(right)
        if lval is not None and (lval & 0x8000):
            return True
        if rval is not None and (rval & 0x8000):
            return True
        # A direct comparison with literal zero is C's most common sign
        # check (`x < 0`, `x >= 0`, `0 < x`): treat it as signed.  The
        # char/binary/string exclusions above already keep byte values
        # unsigned, and no existing Nova-16 program compares addresses
        # against 0 (null pointers use ==/!=).
        if lval == 0 or rval == 0:
            return True
        return False

    def _use_signed_division(self, left: Expression,
                             right: Expression) -> bool:
        """Whether integer '/' or '%' on these operands needs C signed semantics.

        Shares ``_use_signed_comparison``'s operand policy so division and
        relational ops agree: an explicit ``signed_int`` operand or a
        top-bit constant (negative literal) selects the sign-corrected
        sequence; ``unsigned_int``/``char`` and plain ``int`` (historically
        unsigned on this machine -- addresses live at 0x8000+) keep the raw
        hardware DIV/MOD.  For values < 0x8000 both interpretations produce
        the same bits, so the default path stays byte-identical for
        existing programs.
        """
        # Float '%' has no Q8.8 meaning and keeps its legacy raw path;
        # float '/' never reaches this helper (FDIV is chosen at the call
        # site before signedness is consulted).
        if self._cast_source_type(left) == 'float' or \
                self._cast_source_type(right) == 'float':
            return False
        return self._use_signed_comparison(left, right)

    def _emit_divmod(self, op: str, dst: str, src: str, left,
                     right, is_float: bool = False):
        """Emit DIV/FDIV/MOD -- or the signed sequence -- for ``dst {op} src``.

        ``left``/``right`` are the original operand expressions: their
        types and constant values decide signed vs unsigned per
        _use_signed_division.  ``is_float`` routes '/' to FDIV; float '%'
        falls through to raw MOD.  Shared by the binary-operator path and
        every compound-assignment site so all of them pick the same rule.
        Clobbers dst and src (both are temporaries at every call site).
        """
        if op == '/' and is_float:
            self.emit(f"    FDIV {dst}, {src}")
        elif not is_float and self._use_signed_division(left, right):
            if op == '/':
                self._emit_signed_div(dst, src)
            else:
                self._emit_signed_mod(dst, src)
        else:
            self.emit(f"    {'DIV' if op == '/' else 'MOD'} {dst}, {src}")

    def _emit_signed_div(self, dst: str, src: str):
        """``dst /= src`` with C truncation-toward-zero semantics.

        Hardware DIV is unsigned, so negate negative operands into their
        magnitudes first, divide, then negate the quotient iff exactly one
        operand was negative: -7/2 == -3, never 0x7FFD.  Clobbers dst and
        src; uses no stack (ISR-safe, mirrors NoBASIC's _emit_signed_div).
        """
        dst_pos = self.generate_label("sdiv_pos")
        src_pos = self.generate_label("sdiv_np")
        both_pos = self.generate_label("sdiv_pp")
        done = self.generate_label("sdiv_done")
        self.emit(f"    CMP {dst}, 0")
        self.emit(f"    JGE {dst_pos}")
        self.emit(f"    NEG {dst}")                   # dst < 0 -> |dst|
        self.emit(f"    CMP {src}, 0")
        self.emit(f"    JGE {src_pos}")               # |dst| / src
        self.emit(f"    NEG {src}")                   # |dst| / |src|
        self.emit(f"    DIV {dst}, {src}")            # both neg -> positive
        self.emit(f"    JMP {done}")
        self.emit_label(src_pos)
        self.emit(f"    DIV {dst}, {src}")
        self.emit(f"    NEG {dst}")                   # one neg -> negative
        self.emit(f"    JMP {done}")
        self.emit_label(dst_pos)                      # dst >= 0
        self.emit(f"    CMP {src}, 0")
        self.emit(f"    JGE {both_pos}")
        self.emit(f"    NEG {src}")
        self.emit(f"    DIV {dst}, {src}")
        self.emit(f"    NEG {dst}")                   # one neg -> negative
        self.emit(f"    JMP {done}")
        self.emit_label(both_pos)
        self.emit(f"    DIV {dst}, {src}")
        self.emit_label(done)

    def _emit_signed_mod(self, dst: str, src: str):
        """``dst %= src`` with C sign-of-dividend remainder semantics.

        Make src positive first (MOD's result then follows dst's
        magnitude), and negate the remainder when dst was negative so
        -7%2 == -1.  Clobbers dst and src; no stack (ISR-safe, mirrors
        NoBASIC's _emit_signed_mod).
        """
        src_pos = self.generate_label("smod_pos")
        dst_pos = self.generate_label("smod_pos2")
        done = self.generate_label("smod_done")
        self.emit(f"    CMP {src}, 0")
        self.emit(f"    JGE {src_pos}")
        self.emit(f"    NEG {src}")
        self.emit_label(src_pos)
        self.emit(f"    CMP {dst}, 0")
        self.emit(f"    JGE {dst_pos}")
        self.emit(f"    NEG {dst}")
        self.emit(f"    MOD {dst}, {src}")
        self.emit(f"    NEG {dst}")
        self.emit(f"    JMP {done}")
        self.emit_label(dst_pos)
        self.emit(f"    MOD {dst}, {src}")
        self.emit_label(done)

    def _aggregate_expr_tag(self, expr) -> Optional[str]:
        """Struct/union tag of an aggregate-valued expression, if known.

        Handles the forms that can denote a whole struct value: a variable
        (``rect``), a chained member (``box.outer``), and an element of an
        array of structs (``arr[2]``).  Returns None when the expression is
        not an aggregate at all (a scalar, an unknown name, or a call).
        """
        if isinstance(expr, Identifier):
            return self._var_struct_tag(expr.name)
        if isinstance(expr, MemberAccess):
            # Walk to the innermost non-member base to find the starting tag,
            # then step through each field's declared type.
            chain = []
            node = expr
            while isinstance(node, MemberAccess):
                chain.append(node)
                node = node.base
            tag = self._aggregate_expr_tag(node)
            if tag is None:
                return None
            chain.reverse()
            for mae in chain:
                tag = self._struct_field_info(tag, mae.field)[1]
            return tag
        if isinstance(expr, ArrayAccess):
            info = self.array_vars.get(expr.name)
            if info is not None and info.get('tag'):
                return info['tag']
            g = self.global_vars.get(expr.name)
            if g is not None and g.get('tag'):
                return g['tag']
        return None

    def _emit_aggregate_value_addr(self, arg, reg: str, tag: str):
        """Compute the base address of a by-value aggregate argument.

        Validates that the argument really is an aggregate of the declared
        tag, so a scalar or mismatched struct is a compile error instead of
        silently passing one word where the callee reads several.
        """
        arg_tag = self._aggregate_expr_tag(arg)
        if arg_tag is None:
            raise TypeError(
                f"cannot pass this expression by value as struct/union "
                f"'{tag}'; store it in a variable first")
        if arg_tag != tag:
            raise TypeError(
                f"by-value argument has type '{arg_tag}' but parameter "
                f"expects '{tag}'")
        if isinstance(arg, Identifier):
            self._emit_var_load(reg, arg.name)
            return
        if isinstance(arg, MemberAccess):
            self._emit_member_addr(arg, reg)
            return
        if isinstance(arg, ArrayAccess):
            info = self.array_vars.get(arg.name)
            if info is None:
                g = self.global_vars.get(arg.name)
                info = {
                    'elem_type': g['type'], 'count': g['count'],
                    'elem_size': self._elem_size(g['type']),
                    'stride': g.get('stride'),
                    'base_addr': g['address'], 'is_global': True,
                }
            idx_reg = self.generate_expression(arg.index)
            if idx_reg != reg:
                self._emit_array_addr(info, idx_reg, reg)
                self.free_register()
            return
        raise TypeError(
            f"unsupported by-value aggregate argument for struct/union '{tag}'")

    def _emit_push_struct_arg(self, arg, tag: str) -> int:
        """Push a by-value aggregate argument; returns the word count pushed.

        The caller's PUSH sequence IS the copy the callee reads, so the words
        go out in reverse layout order: the last word is pushed first (landing
        at the highest address) and word 0 last (landing at the lowest
        argument address) -- exactly where the callee's FP+param_offset points.
        """
        words = self._struct_size(tag) // 2
        base_reg = self.get_register()
        self._emit_aggregate_value_addr(arg, base_reg, tag)
        for k in range(words - 1, -1, -1):
            off = k * 2
            operand = f"[{base_reg}]" if off == 0 else f"[{base_reg}+{off}]"
            self.emit(f"    PUSH {operand}")
        self.free_register()
        return words

    def _emit_push_sret_dest(self, tag: Optional[str]) -> int:
        """Push the hidden destination pointer for a by-value aggregate return.

        When the call is the RHS of a struct assignment (``p = make(...)``),
        ``_pending_sret_dest`` names the LHS variable and we push its address
        so the callee writes straight into it.  Otherwise a temporary is
        allocated in the caller's frame (or a scratch buffer is used) and its
        address is pushed; the call result then lives there for the rest of
        the expression (P0 holds the same address after RET).

        Returns 1 (one word pushed).
        """
        dest_reg = self.get_register()
        dest_name = getattr(self, '_pending_sret_dest', None)
        if dest_name:
            # Assignment destination: push &dest so the callee fills it.
            self.emit_comment(f"sret dest := &{dest_name}")
            # Reuse address-of logic for locals/globals/by-value params.
            fake = AddressOf(Identifier(dest_name))
            # generate_address_of allocates its own register; copy into dest_reg
            # and free the temporary so register pressure stays bounded.
            addr = self.generate_address_of(fake)
            if addr != dest_reg:
                self.emit(f"    MOV {dest_reg}, {addr}")
                self.free_register()  # free addr
        else:
            # Standalone / nested call: allocate a scratch slot large enough
            # for the returned aggregate and pass its address.  The scratch
            # lives in a fixed high-memory buffer so nested returns of the
            # same size share storage (last-writer-wins, matching C temporary
            # lifetime for discarded results).
            words = self._struct_size(tag) // 2 if tag else 1
            scratch = self._sret_scratch_addr(words)
            self.emit_comment(f"sret scratch @ 0x{scratch:04X} ({words} words)")
            self.emit(f"    MOV {dest_reg}, 0x{scratch:04X}")
        self.emit(f"    PUSH {dest_reg} ; sret destination")
        self.free_register()
        return 1

    def _sret_scratch_addr(self, words: int) -> int:
        """Fixed scratch buffer for discarded / temporary aggregate returns.

        Placed just below the ITOS conversion buffer so it does not collide
        with code, globals, or the descending stack.  Nested returns of the
        same (or smaller) size reuse the buffer; larger returns extend it.
        """
        # itos_buffer is typically 0xA000; park sret temps at 0x9F00 so a
        # 128-word (256-byte) aggregate still fits below ITOS.
        base = getattr(self, 'itos_buffer', 0xA000) - 0x100
        return base

    def generate_call(self, call: FuncCall) -> str:
        self.emit_comment(f"Call to {call.name}")

        # --- float() conversion call ---
        # float(x) is a type-conversion call, routed through the cast
        # machinery so a float variable/expression (Q8.8) is handled with
        # ITOF/FTOI instead of being treated as an undefined function.
        # (int/char/string/binary conversion calls already lower to their
        # builtin stubs further down, so only `float` is special-cased here.)
        if call.name == 'float' and len(call.args) == 1:
            return self.generate_cast(Cast('float', call.args[0]))

        # --- write_text with a non-string first argument ---
        # The TEXT instruction expects a memory address (null-terminated string).
        # When the first argument is an integer/expression rather than a string
        # (or string-typed value), we use the ITOS CPU instruction to convert
        # the integer into a decimal ASCII string at the fixed buffer 0xA000,
        # then pass that buffer address instead of the raw numeric value.
        # If the first argument is already a string expression — a StringLiteral,
        # a cast to string ((string)key), or a string/binary variable — simply
        # pass it through without an extra ITOS to avoid double conversion.
        if (call.name == 'write_text' and len(call.args) >= 1
                and not isinstance(call.args[0], StringLiteral)
                and not self._is_string_or_binary_expr(call.args[0])):
            self.emit_comment("Integer-to-string conversion for write_text")
            # Evaluate the integer expression into a temporary register.
            val_reg = self.generate_expression(call.args[0])
            # ITOS dest, src: converts src (integer) to a decimal ASCII string
            # at the fixed buffer 0xA000, and writes the buffer address into dest.
            str_reg = self.get_register()
            # A char-typed argument (e.g. the result of s[i] on a string
            # variable, or an explicit (char) cast) is a single glyph code,
            # NOT a count to be rendered as decimal digits.  ITOS would turn
            # 'l' (0x6C) into the string "108"; instead, store the byte as a
            # 1-byte NUL-terminated string at the ITOS scratch buffer (0xA000)
            # so TEXT draws the actual character the user requested.  This is
            # safe because the char path never uses ITOS, leaving 0xA000 free.
            if self._cast_source_type(call.args[0]) == 'char':
                self.emit_comment("Char argument: store as single-byte string")
                self.emit(f"    MOV R0, {val_reg}")
                self.emit(f"    MOV [0x{self.itos_buffer:04X}], R0")
                self.emit(f"    MOV [0x{self.itos_buffer + 1:04X}], 0")
                self.emit(f"    MOV {str_reg}, 0x{self.itos_buffer:04X}")
            elif self.memory_layout_name == 'bank-safe':
                # See generate_cast: no hardware ITOS under bank-safe (its
                # scratch cell sits in the bank window).
                self.emit_signed_to_string(str_reg, val_reg)
            else:
                self.emit(f"    ITOS {str_reg}, {val_reg}")
            self.free_register()  # release val_reg (no longer needed)
            
            # Push arguments in reversed source order so the stack top
            # matches the source argument order expected by builtin_write_text
            # (which pops return_addr, then string_ptr into P1, then color into P2).
            if len(call.args) > 1:
                color_reg = self.generate_expression(call.args[1])
                self.emit(f"    PUSH {color_reg}")
                self.free_register()
            else:
                # Default color (white on blue, 0x1F) if not specified.
                self.emit(f"    PUSH 0x1F")
            
            self.emit(f"    PUSH {str_reg}")
            self.free_register()
            
            label = self.builtin_functions.get(call.name)
            if label:
                # Record usage so generate_builtins emits this implementation.
                self.used_builtins.add(label)
            self.emit(f"    CALL {label}")
            self.emit(f"    ; Args consumed by callee")
            
            result_reg = self.get_register()
            self.emit(f"    MOV {result_reg}, R0")
            return result_reg
        
        # --- Normal call path: push all args in reversed order so the
        # stack top matches the source argument order expected by the
        # callee (user functions and builtins alike). Both direct and
        # indirect calls share this argument prologue; for indirect calls
        # the callee address is evaluated LAST, after every argument
        # temporary has been pushed and freed, so round-robin register
        # allocation cannot clobber the target register.
        indirect_call = False
        # Argument-slot sizes come from the callee's signature.  A by-value
        # struct/union parameter consumes several argument words, and the
        # caller-cleanup must pop exactly the number of words it pushed.
        # When the callee returns a struct/union by value, param_kinds[0]
        # is the hidden sret pointer; source args map to the remaining
        # slots and the sret destination is pushed last (so it lands at
        # FP+4 for the callee).
        param_kinds = []
        entry = None
        ret_struct_tag = None
        if isinstance(call.callee, str):
            entry = self.functions.get(call.name)
            if entry:
                param_kinds = list(entry.get('param_kinds') or [])
                ret_struct_tag = entry.get('return_struct_tag')
        has_sret = bool(param_kinds and param_kinds[0].get('sret'))
        # Source-argument kinds: strip the leading sret slot if present.
        src_kinds = param_kinds[1:] if has_sret else param_kinds
        total_arg_words = 0
        for idx in range(len(call.args) - 1, -1, -1):
            arg = call.args[idx]
            kind = src_kinds[idx] if idx < len(src_kinds) else {}
            byval_tag = kind.get('byval_struct')
            if byval_tag:
                total_arg_words += self._emit_push_struct_arg(arg, byval_tag)
            else:
                arg_reg = self.generate_expression(arg)
                self.emit(f"    PUSH {arg_reg}")
                self.free_register()
                total_arg_words += 1
        # Hidden sret destination: push the address of the caller's result
        # storage last so it sits at the lowest argument address (FP+4).
        if has_sret:
            total_arg_words += self._emit_push_sret_dest(ret_struct_tag)
        
        if isinstance(call.callee, str):
            if call.name in self.functions:
                label = self.functions[call.name]['label']
            else:
                # Arity-aware builtin resolution: optional-argument builtins
                # (scroll_x/scroll_y/roll_x/roll_y) select a dedicated stub per
                # argument count so the stack layout always matches the callee.
                label = self._resolve_builtin_label(call.name, len(call.args))
            if not label:
                # Not a user function and not a builtin: the callee name may
                # be a function-pointer VARIABLE whose value is a function
                # entry address (taken with &func, or loaded from anywhere).
                if not self._is_fnptr_var(call.name):
                    raise NameError(f"Undefined function '{call.name}'")
                self.emit_comment(f"Indirect call via '{call.name}'")
                indirect_call = True
                target_reg = self.get_register()
                self._emit_var_load(target_reg, call.name)
                self.emit(f"    CALL {target_reg}")
                self.free_register()
                if total_arg_words:
                    # Indirect callees follow the user-function (cdecl-style)
                    # convention: the callee leaves pushed args on the stack
                    # and the caller deallocates them (one word per argument
                    # word -- by-value aggregates span several; sret adds one).
                    self.emit(f"    ADD SP, {total_arg_words * 2} ; Caller cleans up args")
                result_reg = self.get_register()
                self.emit(f"    MOV {result_reg}, P0")
                return result_reg
            # Record builtin usage so generate_builtins only emits what is called.
            if label in self.BUILTIN_IMPLEMENTATIONS:
                self.used_builtins.add(label)
            
            self.emit(f"    CALL {label}")
            if call.name in self.functions and total_arg_words:
                # User-function callees end with MOV SP, FP / POP FP / RET,
                # which restores SP to the frame base and LEAVES the
                # caller-pushed arguments on the stack. Deallocate them here
                # (cdecl-style, one word per argument -- every PUSH above is a
                # full 16-bit word regardless of the parameter's declared type).
                # Without this, loops that call functions with arguments leak
                # stack bytes every iteration until SP walks down through low
                # memory, wraps, and corrupts the running program.  A by-value
                # aggregate argument occupies one word per struct word; an
                # sret destination pointer adds one more.
                self.emit(f"    ADD SP, {total_arg_words * 2} ; Caller cleans up args")
            elif call.args:
                # Builtin stubs pop their own arguments off the stack.
                self.emit(f"    ; Args consumed by callee")
        else:
            # --- Indirect call: the callee is an expression evaluating to a
            # function entry address -- fp(x), (*fp)(x), (&f)(x), or an array
            # element of function pointers (handlers[0](x)). A bare identifier
            # that names a known user function degenerates to a direct call.
            callee = call.callee
            # `(*fp)(x)` -- in C a function designator decays straight back
            # to the pointer, so a dereference of a function-pointer slot
            # yields the slot VALUE, not a memory load at that address.
            # Only unwrap when the operand really is an fn-ptr slot; a
            # pointer-to-function-pointer keeps the load (real C semantics).
            if isinstance(callee, Deref) and self._is_fnptr_expr(callee.operand):
                callee = callee.operand
            if isinstance(callee, Identifier) and callee.name in self.functions:
                self.emit_comment(f"Direct call via '{callee.name}'")
                self.emit(f"    CALL {self.functions[callee.name]['label']}")
            else:
                self.emit_comment("Indirect call via function pointer")
                indirect_call = True
                target_reg = self.generate_expression(callee)
                self.emit(f"    CALL {target_reg}")
                self.free_register()
            if total_arg_words:
                # Indirect callees follow the user-function convention: the
                # caller owns the pushed argument words.
                self.emit(f"    ADD SP, {total_arg_words * 2} ; Caller cleans up args")

        result_reg = self.get_register()
        # User-defined functions return their 16-bit int result in P0
        # (see generate_return), and a subset of builtins also write P0
        # directly (RND P0, RNDR P0, KEYSTAT P0, KEYIN P0, SREAD P0,
        # SERIN P0, SERSTAT P0, KEYCOUNT P0, the VL/VC/rtc state getters,
        # and all math/string/memory/bit/BCD builtins that write their
        # result to P0).
        # Void builtins (set_vmode, etc.) leave both untouched; their
        # return value is discarded so the source register is irrelevant.
        p0_returning_builtins = {
            'random', 'random_range', 'key_available', 'key_read',
            'read_screen', 'key_count', 'ser_in', 'ser_stat', 'vread',
            'get_layer', 'get_color', 'get_rtc',
            'abs', 'min', 'max', 'clz', 'ctz', 'popcnt',
            'sqrt', 'log', 'exp', 'sin', 'cos', 'tan',
            'atan', 'asin', 'acos', 'deg', 'rad',
            'floor', 'ceil', 'round', 'trunc', 'frac', 'intgr', 'int', 'powr',
            'strcpy', 'strcat', 'strcmp', 'strlen',
            'strupr', 'strlwr', 'strrev', 'strfind', 'strfindi',
            'ser_out', 'ser_ctrl',
            'memcpy', 'memset', 'memmove', 'memcmp', 'memtest', 'memswap',
            'peek', 'peek2', 'read_bank',
            'byte',
            # Systems tier (get_reg/set_reg/get_rreg/set_rreg/get_sp/
            # set_sp/get_fp/set_fp/get_flags/set_flags) return in P0 like
            # their peek/peek2/read_bank siblings -- the stubs write P0
            # directly (see BUILTIN_IMPLEMENTATIONS).
            'get_reg', 'set_reg', 'get_rreg', 'set_rreg',
            'get_sp', 'set_sp', 'get_fp', 'set_fp',
            'get_flags', 'set_flags',
            # Stack/tasks tier: pop/alloca/stack_free/task_switch return in
            # P0 (task_switch's "value" is undefined -- it RETs into another
            # task; the resume path just re-reads P0 harmlessly). push and
            # task_spawn are void and stay in the R0-reading default set.
            'pop', 'alloca', 'stack_free', 'task_switch',
            'btst', 'bset', 'bclr', 'bflip',
            'swap', 'xchng',
            'bcd2bin', 'bin2bcd', 'bcdadd', 'bcdsub',
            'bcda', 'bcds', 'bcdcmp',
            'mouse_ctrl', 'mouse_read', 'mouse_pos',
        }
        if (indirect_call or call.name in self.functions
                or call.name in p0_returning_builtins):
            self.emit(f"    MOV {result_reg}, P0")
        else:
            self.emit(f"    MOV {result_reg}, R0")
        return result_reg

    def _is_fnptr_expr(self, expr) -> bool:
        """Whether `expr` denotes a function-pointer SLOT (a variable whose
        stored 16-bit value is a function entry address), as opposed to a
        plain pointer that must be dereferenced to reach such a slot.

        Used to give `(*fp)(x)` the C meaning (the designator decays back to
        the pointer, so no memory load happens) while leaving
        `(*pp)(x)` -- a pointer to a function pointer -- as a real load.
        """
        if isinstance(expr, Identifier):
            return self._is_fnptr_var(expr.name)
        if isinstance(expr, ArrayAccess):
            return self._is_fnptr_var(expr.name)
        return False

    def _fnptr_array_init(self, expr, arr_name: str):
        """Resolve one global function-pointer-array initializer element.

        `&func` is a symbol reference, not an integer, so it cannot go through
        _const_eval; it is emitted as the function's assembly label and
        resolved by the assembler. User functions map to `func_<name>`;
        builtins resolve through the lazily-linked builtin table (referencing
        one here records its use so both the label and its implementation are
        emitted). Returns None when the element is neither -- the caller then
        reports the usual "compile-time constants" error.
        """
        if not (isinstance(expr, AddressOf)
                and isinstance(expr.operand, Identifier)):
            return None
        fname = expr.operand.name
        # Function pre-registration runs AFTER global allocation (see
        # generate()), so self.functions is still empty here. Prefer the
        # AST-derived name set stashed by _allocate_globals, and fall back to
        # self.functions for any caller that allocates globals later.
        if fname in getattr(self, '_declared_func_names', ()) \
                or fname in self.functions:
            return f'func_{fname}'
        label = self._resolve_builtin_label(fname, None)
        if label and label in self.BUILTIN_IMPLEMENTATIONS:
            self.used_builtins.add(label)
            return label
        return None

    def _is_fnptr_var(self, name: str) -> bool:
        """Whether `name` is a declared function-pointer variable (a local,
        parameter, static, or global whose slot holds a function entry
        address). Used by generate_call to resolve indirect calls."""
        d = self.local_vars.get(name)
        if d is not None and d.get('fn_ptr'):
            return True
        g = self.global_vars.get(name)
        return bool(g and g.get('fn_ptr'))

    def generate_method_call(self, call: MethodCall) -> str:
        """Generate an instance-method call: p.method(...), pp->method(...).

        The receiver is resolved at compile time to its struct/union tag,
        and the method is looked up under the namespaced key
        "TypeName::method". The receiver ADDRESS is pushed as the first
        argument (the callee's `self` parameter), followed by the explicit
        arguments (pushed in reverse source order, matching generate_call's
        cdecl-style convention where caller cleans up). User-defined methods
        return their 16-bit result in P0, like top-level user functions.
        """
        member = call.base  # MemberAccess(receiver_expr, method_name, arrow)
        receiver_expr = member.base
        method_name = member.field

        tag = self._receiver_struct_tag(receiver_expr)
        if tag is None:
            raise NameError(
                f"Method call '{method_name}' requires a struct/union "
                f"receiver (variable, pointer, or array element)")
        key = f'{tag}::{method_name}'
        info = self.functions.get(key)
        if info is None:
            available = sorted(
                k.split('::', 1)[1]
                for k in self.functions if k.startswith(f'{tag}::'))
            hint = (f" (available: {', '.join(available) or 'none'})"
                    if available else "")
            raise NameError(
                f"Type '{tag}' has no method '{method_name}'{hint}")

        self.emit_comment(f"Method call {tag}::{method_name}")

        # Push the explicit arguments in reverse source order so the stack
        # top ends up as the LAST argument (the callee reads params at
        # ascending FP offsets, so the first parameter -- `self` -- must be
        # pushed last, right before the CALL).  Argument-slot sizes come from
        # the method signature.  When the method returns a struct/union by
        # value, param_kinds[0] is the hidden sret pointer, param_kinds[1]
        # is `self`, and explicit argument `i` maps to param_kinds[i + 2].
        all_kinds = list(info.get('param_kinds') or [])
        has_sret = bool(all_kinds and all_kinds[0].get('sret'))
        # Skip sret (if any) and the implicit self slot to get explicit-arg kinds.
        skip = 2 if has_sret else 1
        param_kinds = all_kinds[skip:]
        ret_struct_tag = info.get('return_struct_tag')
        total_arg_words = 0
        for idx in range(len(call.args) - 1, -1, -1):
            arg = call.args[idx]
            kind = param_kinds[idx] if idx < len(param_kinds) else {}
            byval_tag = kind.get('byval_struct')
            if byval_tag:
                total_arg_words += self._emit_push_struct_arg(arg, byval_tag)
            else:
                arg_reg = self.generate_expression(arg)
                self.emit(f"    PUSH {arg_reg}")
                self.free_register()
                total_arg_words += 1

        # Evaluate and push the receiver address (the implicit `self` arg).
        recv_reg = self.get_register()
        self._emit_receiver_addr(receiver_expr, recv_reg)
        self.emit(f"    PUSH {recv_reg} ; Receiver := self")
        self.free_register()
        total_arg_words += 1

        # Hidden sret destination last so it lands at FP+4.
        if has_sret:
            total_arg_words += self._emit_push_sret_dest(ret_struct_tag)

        self.emit(f"    CALL {info['label']}")
        # User-function callees restore SP to the frame base, leaving the
        # caller-pushed arguments on the stack; deallocate all of them
        # (receiver + explicit argument words [+ sret]), cdecl-style.
        self.emit(f"    ADD SP, {total_arg_words * 2} ; Caller cleans up args + receiver")

        result_reg = self.get_register()
        self.emit(f"    MOV {result_reg}, P0")
        return result_reg

    def generate_builtins(self):
        """Emit builtin implementations referenced by the program.

        Builtins are LAZILY LINKED: only labels recorded in self.used_builtins
        (populated by generate_call) are emitted, so programs that never call
        a builtin pay zero bytes for it. Set emit_all_builtins=True
        (--emit-all-builtins CLI flag) to restore the legacy behavior of
        emitting the full builtin library.
        """
        if self.emit_all_builtins:
            selected = list(self.BUILTIN_IMPLEMENTATIONS.items())
        else:
            selected = [(label, body)
                        for label, body in self.BUILTIN_IMPLEMENTATIONS.items()
                        if label in self.used_builtins]
        if not selected:
            return
        self.assembly.append("; Built-in Function Implementations")
        # Region placeholders in builtin bodies are filled from the active
        # memory layout, so a stub that parks a return address in the ITOS
        # scratch cell (POPA) or measures stack headroom (stack_free) follows
        # the same addresses as the generated code around it.
        substitutions = {
            'itos': f"0x{self.itos_buffer:04X}",
            'itob': f"0x{self.itob_buffer:04X}",
            'stack_floor': f"0x{self.stack_floor:04X}",
        }
        for label, body in selected:
            self.emit_label(label)
            for raw_line in body:
                line = raw_line.format(**substitutions) if '{' in raw_line else raw_line
                if line.startswith(';'):
                    # Comment lines are emitted verbatim (no extra indent).
                    self.assembly.append(line)
                elif line.endswith(':'):
                    # Internal branch labels inside multi-path stubs
                    # (e.g. direction selection in scroll/roll builtins).
                    self.emit_label(line[:-1])
                else:
                    self.emit(line)
        self.assembly.append("")

    def get_string_label(self, value: str) -> str:
        if value not in self.strings:
            label = self.generate_label("str")
            self.strings[value] = label
            return label
        return self.strings[value]

    def emit(self, line: str):
        self.assembly.append(f"    {line}")

    def emit_comment(self, comment: str):
        self.assembly.append(f"; {comment}")

    def emit_label(self, label: str):
        self.assembly.append(f"{label}:")

    def generate_label(self, prefix: str) -> str:
        label = f"{prefix}_{self.label_counter}"
        self.label_counter += 1
        return label

    def get_register(self, exclude: set = None, preferred: str = None) -> str:
        # Use P0-P7 as 16-bit expression temporaries. P8 is SP and P9 is FP,
        # so they must never be used for general temporaries or arithmetic
        # results (e.g. MOV P9, 3 would clobber the frame pointer).
        # P3 is reserved for DIV remainder storage (the CPU's DIV instruction
        # unconditionally writes the remainder to P3), so we exclude P3.
        # Preferred register can be specified (e.g., 'P0', 'P1', etc.)
        # P3 is always excluded (reserved for DIV remainder). Use string matching.
        # 
        # Round-robin through P0-P7 (skipping P3 and user-excluded registers).
        # This preserves the original behavior where expression temporaries are
        # reused freely between statements without true liveness-based allocation.
        # The register_usage/var_reg/auto_free infrastructure is retained for
        # future graph-coloring allocation passes but does NOT gate allocation here.
        excluded = {'P3'} | (exclude or set())
        
        # Try preferred register first
        if preferred and preferred not in excluded:
            return preferred
        
        # Round-robin through P registers only (preserves original behavior)
        for _ in range(20):
            idx = self.reg_counter % 8
            self.reg_counter += 1
            reg = f"P{idx}"
            if reg not in excluded:
                return reg
        
        # Fallback (should never happen)
        return "P0"

    def free_register(self):
        # Expression temporaries are reused round-robin; no-op to preserve
        # original behavior where registers are safe to reuse after an
        # expression completes. Advanced liveness-based deallocation is
        # available via deallocate_register()/_clear_temp_registers() for
        # future integration, but is NOT used at expression boundaries here
        # to avoid freeing registers still referenced by outer expressions.
        pass

    def record_live_range(self, name: str, program_point: int):
        # Record that a variable/temporary is live at a program point.
        if name not in self.live_ranges:
            self.live_ranges[name] = (program_point, program_point)
        else:
            start, end = self.live_ranges[name]
            self.live_ranges[name] = (min(start, program_point), max(end, program_point))
        
        if program_point not in self.live_at_point:
            self.live_at_point[program_point] = set()
        self.live_at_point[program_point].add(name)

    def allocate_register(self, preferred_reg: str = None) -> str:
        # Allocate an unused register, preferring the specified register if available.
        self.allocation_stats['total_allocations'] += 1
        
        # Try preferred register first
        if preferred_reg and not self.register_usage.get(preferred_reg, True):
            self.register_usage[preferred_reg] = True
            self.auto_free_registers.add(preferred_reg)
            self.allocation_stats['max_simultaneous_allocated'] = max(
                self.allocation_stats['max_simultaneous_allocated'],
                sum(1 for used in self.register_usage.values() if used)
            )
            return preferred_reg
        
        # Try allocation order
        for reg in self.allocation_order:
            if not self.register_usage[reg]:
                self.register_usage[reg] = True
                self.auto_free_registers.add(reg)
                self.allocation_stats['max_simultaneous_allocated'] = max(
                    self.allocation_stats['max_simultaneous_allocated'],
                    sum(1 for used in self.register_usage.values() if used)
                )
                return reg
        
        # No free registers
        self.allocation_stats['allocation_failures'] += 1
        raise RuntimeError("Register exhaustion: No available registers")

    def deallocate_register(self, reg: str):
        # Deallocate a register, marking it as available.
        if reg in self.register_usage:
            self.register_usage[reg] = False
            self.auto_free_registers.discard(reg)
            self.allocation_stats['total_deallocations'] += 1

    def _clear_temp_registers(self):
        # Clear all temporary registers that aren't variable registers.
        var_regs = set(self.var_reg.values())
        for reg in list(self.auto_free_registers):
            if reg not in var_regs:
                self.deallocate_register(reg)

    def smart_deallocate_regs(self):
        # Intelligently deallocate temporary registers that are likely dead.
        var_regs = set(self.var_reg.values())
        for reg in list(self.auto_free_registers):
            if reg not in var_regs:
                self.deallocate_register(reg)
        
        self.allocation_stats['total_deallocations'] += 1
