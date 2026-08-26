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
    ArrayAccess, ArrayAssignment, TernaryOp, PrefixOp,
    AddressOf, Deref, DerefAssignment, SizeofExpr,
    MemberAccess, MemberAssignment,
)
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
            'SINV', 'RET',
        ],
        'builtin_screen_blit': [
            'SBLIT', 'RET',
        ],
        'builtin_set_blend_mode': [
            'POP P0', 'POP P1', 'SBLEND P1', 'PUSH P0', 'RET',
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
        'builtin_sound_play': [
            'POP P0', 'POP P1', 'POP P2', 'POP P3', 'SPLAY P3, P2, P1', 'PUSH P0', 'RET',
        ],
        'builtin_sound_stop': [
            'POP P0', 'POP P1', 'SPLAY P1, 0, 0', 'PUSH P0', 'RET',
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
        'builtin_memset': [
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
        'builtin_popa': ['POPA', 'RET'],
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
    }

    def __init__(self, enable_peephole: bool = True, debug_optimizations: bool = False,
                 enable_expr_simplify: bool = True, enable_live_range: bool = True,
                 enable_optimizations: bool = True,
                 enable_live_range_scheduling: Optional[bool] = None,
                 emit_all_builtins: bool = False):
        self.debug_optimizations = debug_optimizations
        self.opt_config = get_optimization_config()
        self.opt_config['debug_optimizations'] = debug_optimizations

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
        self.global_vars = {}  # name -> {'address', 'type', 'size', 'is_array', 'count', 'init_values'}
        self.array_vars = {}   # per-function LOCAL arrays: name -> {'elem_type', 'count', 'elem_size', 'offset'}
        self.local_vars = {}
        self.var_types = {}  # name -> 'int' (16-bit, 2 bytes) or 'char' (8-bit)
        # Pointer-declared variables (`int *p`) and array parameters
        # (`void f(int arr[])`): both hold 16-bit addresses (2 bytes).
        self.pointer_vars: Set[str] = set()
        self.address_params: Set[str] = set()
        # Struct pointers (`struct Point *pp`): name -> struct tag, so
        # pp->field resolves the member offset through the pointee layout.
        self.pointer_struct_tags: Dict[str, str] = {}
        self.functions = {}
        self.strings = {}
        self.string_counter = 0
        self.label_counter = 0
        self.reg_counter = 0 
        self.current_function = None
        self.builtin_functions = self._init_builtins()
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
        self._spill_window = self.SPILL_REGION_START
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
            'screen_fill': 'builtin_screen_fill',
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
        self.assembly.append("; Generated by the Astrid Compiler for Nova-16")
        # Adopt the parser's enum constant table so enum names resolve to
        # their integer values everywhere numbers are accepted.
        self.enum_constants = dict(getattr(ast, 'enum_constants', None) or {})
        # Adopt the parser's struct layout table so member accesses resolve
        # field offsets through their struct's definition.
        self.struct_defs = dict(getattr(ast, 'structs', None) or {})
        # Run front-end expression simplifier (constant-folding, algebraic
        # simplifications, and CSE) to reduce register pressure and code size.
        if self.enable_optimizations and self.enable_expr_simplify:
            try:
                simplifier = ExpressionSimplifier(debug=self.debug_optimizations)
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
        # or declared via C-style prototypes) resolve correctly.
        for func_def in ast.functions:
            self.functions[func_def.name] = {
                'label': f'func_{func_def.name}',
                'params': len(func_def.params),
                'return_type': func_def.return_type
            }

        # Main entry point MUST be first segment so emulator sets PC correctly
        self.assembly.append("ORG 0x1000")
        self.assembly.append("start:")
        self.assembly.append("    MOV SP, 0xFFFF ; Set stack pointer to high memory")
        self.assembly.append("    MOV FP, 0xFFFF ; Also init frame pointer")
        self.assembly.append("    CALL func_main")
        self.assembly.append("    HLT")
        self.assembly.append("")

        # Emit interrupt vector FIRST at 0x0100 (before functions)
        if any(func.name == 'timer_interrupt' for func in ast.functions):
            self.assembly.append("ORG 0x0100")
            self.assembly.append("    DW func_timer_interrupt")
            # Skip past the interrupt vector table (0x0100-0x011F, 8 vectors x 4 bytes)
            self.assembly.append("ORG 0x0120")
            self.assembly.append("")

        # Generate all functions and data AFTER interrupt vector
        for func_def in ast.functions:
            self.generate_function(func_def)

        self.generate_strings()
        self.generate_builtins()
        self._emit_globals_data()

        assembly_output = "\n".join(self.assembly)
        assembly_lines = assembly_output.splitlines()

        if self.enable_optimizations and self.enable_live_range:
            should_schedule, schedule_reason = self._should_run_live_range_scheduler(assembly_lines)
            if should_schedule:
                try:
                    from astrid.codegen.live_range_scheduler import LiveRangeScheduler
                    scheduler = LiveRangeScheduler(debug=self.debug_optimizations)
                    assembly_lines = scheduler.schedule(assembly_lines, self.live_ranges)
                    if self.debug_optimizations:
                        print("[CODEGEN] Live-range scheduling applied")
                except Exception:
                    if self.debug_optimizations:
                        import traceback; traceback.print_exc()
            elif self.debug_optimizations:
                print(f"[CODEGEN] Skipping live-range scheduling: {schedule_reason}")

        if self.enable_optimizations and self.enable_peephole:
            from astrid.codegen.peephole import PeepholeOptimizer
            peephole_opt = PeepholeOptimizer(debug=self.debug_optimizations)
            assembly_output = peephole_opt.optimize("\n".join(assembly_lines))
            assembly_lines = assembly_output.splitlines()

            if self.debug_optimizations:
                print("[CODEGEN] Peephole optimization applied")
                print(f"[CODEGEN] Original: {len(self.assembly)} lines, Optimized: {len(assembly_lines)} lines")

        return assembly_lines

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
                return node
            if isinstance(node, MemberAccess):
                # Simplify the base chain in place; field names are plain
                # identifiers with nothing to fold.
                node.base = simplify_node(node.base) or node.base
                return node
            if isinstance(node, ArrayAssignment):
                node.target.index = simplify_node(node.target.index)
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
        return 2 if self.var_types.get(name) in ('int', 'string', 'binary') else 1

    def _is_int_var(self, name: str) -> bool:
        return self.var_types.get(name) == 'int'

    def _get_local_offset(self, name: str) -> int:
        offset = self.local_vars[name]['offset']
        return offset

    def _emit_local_load(self, reg: str, name: str):
        offset = self._get_local_offset(name)
        var_size = self._var_size(name)
        # Record access for hot-variable optimization.
        self.variable_access_counts[name] += 1
        # If this local was migrated to a spill allocation, load from that
        # absolute address instead of the frame pointer slot. Do NOT do this
        # for `timer_interrupt` (uses SP-relative locals).
        if name in self.spill_allocations and self.current_function != 'timer_interrupt':
            addr = self.spill_allocations[name]
            self.emit(f"    MOV {reg}, [0x{addr:04X}]")
            return
        if self.current_function == 'timer_interrupt':
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
        # If this local was migrated to a spill allocation, store to that
        # absolute address instead of the frame pointer slot. Do NOT do this
        # for `timer_interrupt` (uses SP-relative locals).
        if name in self.spill_allocations and self.current_function != 'timer_interrupt':
            addr = self.spill_allocations[name]
            self.emit(f"    MOV [0x{addr:04X}], {src_reg}")
            return
        if self.current_function == 'timer_interrupt':
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
        return 2 if var_type in ('int', 'string', 'binary', 'struct') else 1

    # ------------------------------------------------------------------
    # Struct layout and member access support
    # ------------------------------------------------------------------

    def _struct_fields(self, tag: str) -> List[str]:
        fields = self.struct_defs.get(tag)
        if fields is None:
            raise NameError(f"Undefined struct type '{tag}'")
        return fields

    def _struct_size(self, tag: str) -> int:
        """Total byte size of one struct value (each field is a word slot)."""
        return len(self._struct_fields(tag)) * 2

    def _struct_field_offset(self, tag: str, field: str) -> int:
        """Byte offset of a field within the struct, or a clear error."""
        fields = self._struct_fields(tag)
        if field not in fields:
            raise NameError(
                f"Struct '{tag}' has no field '{field}' "
                f"(fields: {', '.join(fields)})")
        return fields.index(field) * 2

    def _var_struct_tag(self, name: str) -> Optional[str]:
        """Struct tag for a declared struct variable/pointer/array, if any."""
        info = self.array_vars.get(name)
        if info and info.get('tag'):
            return info['tag']
        g = self.global_vars.get(name)
        if g and g.get('tag'):
            return g['tag']
        return self.pointer_struct_tags.get(name)

    def _member_base_info(self, expr: MemberAccess):
        """Resolve a MemberAccess base into (kind, data, field_offset).

        kind 'array'   -- data is an array-info dict; the member address is
                          the array element address plus the field offset.
                          Covers scalar struct variables (an N-field struct
                          is laid out exactly like an N-word array) AND
                          arrays of structs via ArrayAccess bases.
        kind 'pointer' -- data is (name, tag); the variable's VALUE is the
                          struct base address (`pp->field`).
        """
        base = expr.base
        while isinstance(base, MemberAccess):
            raise SyntaxError(
                "Nested struct members (a.b.c) are not supported")
        if isinstance(base, Identifier):
            name = base.name
            tag = self._var_struct_tag(name)
            if tag is None:
                if name in self.struct_defs:
                    # The name IS a struct type -- the user likely declared
                    # (or tried to use) an instance in the wrong scope.
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
            offset = self._struct_field_offset(tag, expr.field)
            info = self.array_vars.get(name)
            if info is not None and info.get('tag'):
                # Scalar struct local: an N-word array under the hood.
                return ('array', info, offset), tag
            g = self.global_vars.get(name)
            if name in self.pointer_vars or name in self.address_params or \
                    (g is not None and g.get('is_pointer')):
                # Struct pointer: pp->field loads the pointer then adds.
                # NOTE: must be tested before the scalar-global branch --
                # global struct pointers also carry the struct tag.
                return ('pointer', (name, tag), offset), tag
            if g is not None and g.get('tag'):
                # Scalar struct global: registered as an is_array word block.
                return ('array', {
                    'elem_type': 'struct', 'count': g['count'],
                    'elem_size': 2, 'stride': g.get('stride', 2),
                    'base_addr': g['address'], 'is_global': True,
                }, offset), tag
            raise NameError(
                f"'{name}' is not a struct variable or struct pointer")
        if isinstance(base, ArrayAccess):
            arr_name = base.name
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
            offset = self._struct_field_offset(info['tag'], expr.field)
            return ('array', info, offset), info['tag']
        raise SyntaxError("Unsupported struct member base expression")

    def _emit_member_addr(self, expr: MemberAccess, addr_reg: str,
                          idx_reg: Optional[str] = None):
        """Emit code computing a member's byte address into addr_reg.

        For ArrayAccess bases the caller may pass a pre-evaluated index in
        idx_reg; for Identifier bases the address is fully constant."""
        (kind, data, offset), tag = self._member_base_info(expr)
        if kind == 'pointer':
            name, _tag2 = data
            self._emit_var_load(addr_reg, name)
            if offset:
                self.emit(f"    ADD {addr_reg}, {offset}")
        elif isinstance(expr.base, ArrayAccess):
            info = data
            if idx_reg is None:
                idx_reg = self.generate_expression(expr.base.index)
            self._emit_array_addr(info, idx_reg, addr_reg)
            if offset:
                self.emit(f"    ADD {addr_reg}, {offset}")
        else:
            # Constant scalar-struct base: field j of an N-field struct is
            # element j of its underlying N-word array layout.
            info = data
            self._emit_array_const_addr(info, offset // 2, addr_reg)


    def _decl_is_true_array(self, decl):
        """Whether a declaration is a genuine array (vs a scalar with an
        initializer list). For structs, `struct Point p = {10, 20}` is a
        scalar struct whose initializer list fills fields; only `[...]`
        bracket syntax (or an explicit size) makes it an array."""
        if getattr(decl, 'struct_tag', None):
            return bool(getattr(decl, 'array_syntax', False)
                        or getattr(decl, 'array_size', None) is not None)
        return decl.is_array

    def _resolve_array_count(self, decl: VarDecl) -> int:
        """Resolve an array's element count at compile time."""
        if decl.init_list is not None:
            return len(decl.init_list)
        if isinstance(decl.array_size, Number):
            count = int(decl.array_size.value, 0)
        else:
            # Enum constants (or any constant expression) are valid sizes.
            count = self._const_eval(decl.array_size)
            if count is None:
                raise TypeError(
                    f"Array '{decl.name}' size must be a compile-time constant")
        if count <= 0:
            raise ValueError(f"Array '{decl.name}' must have a positive size")
        return count

    def _const_eval(self, expr) -> Optional[int]:
        """Evaluate a compile-time constant expression (global initializers).

        Returns the 16-bit masked value, or None if the expression is not a
        compile-time constant."""
        try:
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
                if op == '+': return (left + right) & 0xFFFF
                if op == '-': return (left - right) & 0xFFFF
                if op == '*': return (left * right) & 0xFFFF
                if op == '/' and right != 0: return int(left / right) & 0xFFFF
                if op == '%' and right != 0: return (left % right) & 0xFFFF
                if op == '&': return left & right
                if op == '|': return left | right
                if op == '^': return left ^ right
                if op == '<<': return (left << right) & 0xFFFF
                if op == '>>': return (left >> right) & 0xFFFF
            return None
        except (ValueError, ArithmeticError):
            return None

    def _allocate_globals(self, ast: Program):
        """Assign fixed storage addresses to all global variables/scalars."""
        next_addr = self.GLOBAL_REGION_START
        for decl in getattr(ast, 'globals', None) or []:
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
                    # N fields == N word slots; init lists fill words.
                    count = len(self._struct_fields(struct_tag))
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
                                raise TypeError(
                                    f"Global array '{decl.name}' initializers must be "
                                    f"compile-time constants")
                            init_values.append(v)
                total_size = count * (stride or elem_size)
                self.global_vars[decl.name] = {
                    'address': next_addr, 'type': decl.var_type,
                    'size': total_size, 'is_array': True,
                    'elem_size': elem_size,
                    'count': count, 'init_values': init_values,
                    # Struct entries hold WORD values regardless of the
                    # element stride (each field is one DW slot).
                    'init_elem_bytes': 2 if struct_tag else elem_size,
                    **({'stride': stride} if stride else {}),
                    **({'tag': struct_tag} if struct_tag else {}),
                }
                next_addr += total_size
            else:
                init_value = None
                if decl.value is not None:
                    init_value = self._const_eval(decl.value)
                    if init_value is None:
                        raise TypeError(
                            f"Global variable '{decl.name}' initializer must be "
                            f"a compile-time constant")
                self.global_vars[decl.name] = {
                    'address': next_addr, 'type': decl.var_type,
                    'size': elem_size, 'is_array': False,
                    'elem_size': elem_size,
                    # Global pointers hold addresses (16-bit values).
                    'is_pointer': bool(decl.pointer_depth),
                    'count': 1,
                    'init_values': [init_value] if init_value is not None else [],
                    # Struct pointers remember their layout so pp->field
                    # resolves member offsets through the pointee type.
                    **({'tag': struct_tag} if struct_tag else {}),
                }
                next_addr += elem_size

    def _emit_globals_data(self):
        """Emit the global-variable data segment at GLOBAL_REGION_START."""
        if not self.global_vars:
            return
        self.assembly.append("")
        self.assembly.append(f"ORG 0x{self.GLOBAL_REGION_START:04X}")
        self.assembly.append("; Global Variables")
        for name, info in self.global_vars.items():
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
        self.assembly.append("")

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
        elif self.current_function == 'timer_interrupt':
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
        if info.get('is_param'):
            self.emit(f"    MOV {addr_reg}, [FP{info['offset']:+d}]")
            self.emit(f"    ADD {addr_reg}, {byte_off}")
        elif info.get('is_global'):
            self.emit(f"    MOV {addr_reg}, 0x{info['base_addr'] + byte_off:04X}")
        elif self.current_function == 'timer_interrupt':
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
            if self.current_function == 'timer_interrupt':
                sp_offset = -offset - 2
                self.emit(f"    MOV {reg}, [SP+{sp_offset}]")
            else:
                self.emit(f"    MOV {reg}, [FP{offset:+d}]")
            return
        if name in self.array_vars:
            info = self.array_vars[name]
            if self.current_function == 'timer_interrupt':
                base_sp = -info['offset'] - info['count'] * info['elem_size']
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

    def generate_function(self, func_def: FunctionDef):
        self.functions[func_def.name] = {
            'label': f'func_{func_def.name}',
            'params': len(func_def.params),
            'return_type': func_def.return_type
        }

        # Clear spill allocations for this function (per-function scope)
        self.spill_allocations = {}
        # Reserve this function's spill window from the dedicated spill
        # region so spilled locals never collide with code, globals, the
        # stack, or another function's window. When the region is exhausted,
        # keep locals FP-relative (no migration) rather than corrupt memory.
        if self._spill_window + self.opt_config.get('zero_page_size', 128) <= self.SPILL_REGION_END:
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
        
        self.assembly.append(f"; Function: {func_def.name}")
        self.assembly.append(f"func_{func_def.name}:")
        
        all_local_decls = self.find_local_vars(func_def.body)
        
        # Compute stack frame size: each int/string/binary var/param takes 2 bytes, char takes 1
        # Params: int/string/binary params use 2 bytes each, char params use 1 byte
        param_size = 0
        for param in func_def.params:
            self.var_types[param.name] = param.var_type
            if param.pointer_depth or getattr(param, 'is_array_param', False):
                # Pointers and array parameters hold a 16-bit address.
                param_size += 2
                self.pointer_vars.add(param.name)
                if getattr(param, 'is_array_param', False):
                    self.address_params.add(param.name)
                    # Register layout info so arr[i] indexing works on the
                    # parameter (offset filled in once known below).
                    self.array_vars[param.name] = {
                        'elem_type': param.var_type, 'count': 0,
                        'elem_size': self._elem_size(param.var_type),
                        'offset': None, 'is_param': True,
                    }
            else:
                param_size += 2 if param.var_type in ('int', 'string', 'binary') else 1
        
        local_size = 0
        for decl in all_local_decls:
            self.var_types[decl.name] = decl.var_type
            decl_tag = getattr(decl, 'struct_tag', None)
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
                local_size += 2 if decl.var_type in ('int', 'string', 'binary') else 1
        
        if func_def.name == 'timer_interrupt':
            # Interrupt handlers must NOT use ENTER/LEAVE because the CPU
            # already pushed PC and flags on the stack. Use direct SP
            # manipulation instead so IRET can find the saved context.
            # The CPU's interrupt entry saves ONLY PC + flags -- general
            # registers are NOT preserved. Interrupted code keeps live
            # values in P/R registers across the interrupt (e.g. a while(1)
            # loop condition re-reads its register after the handler
            # returns), so the handler must save/restore them itself.
            # Registers are pushed BEFORE allocating locals so that
            # SP-relative ([SP+n]) local addressing stays valid in the
            # handler body; _emit_isr_register_restore mirrors this order.
            self._emit_isr_register_save()
            if local_size > 0:
                self.assembly.append(f"    SUB SP, {local_size} ; Allocate locals")
        else:
            self.assembly.append(f"    ENTER {local_size}")

        # Param offsets: after ENTER pushes FP (2 bytes) and CALL pushes ret addr (2 bytes),
        # params are at positive offsets from FP starting at +4.
        param_offset = 4
        for param in func_def.params:
            self.local_vars[param.name] = {'offset': param_offset}
            if param.name in self.array_vars and self.array_vars[param.name].get('is_param'):
                self.array_vars[param.name]['offset'] = param_offset
            param_offset += 2 if (param.var_type in ('int', 'string', 'binary')
                                  or param.pointer_depth
                                  or getattr(param, 'is_array_param', False)) else 1

        # Local offsets: start at -2 going down (2 bytes per slot for simplicity;
        # char vars also get 2 bytes to keep word access alignment simple)
        local_offset = 0
        for decl in all_local_decls:
            decl_tag = getattr(decl, 'struct_tag', None)
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
                if decl_tag:
                    info['tag'] = decl_tag
                    info['stride'] = stride
                self.local_vars[decl.name] = {'offset': -local_offset}
                self.array_vars[decl.name] = info
            elif decl.pointer_depth:
                local_offset += 2
                self.local_vars[decl.name] = {'offset': -local_offset}
            elif decl_tag:
                # Scalar struct local: register as an N-word array so all
                # array addressing paths (member loads, &p, decay) apply.
                n_fields = len(self._struct_fields(decl_tag))
                local_offset += n_fields * 2
                self.local_vars[decl.name] = {'offset': -local_offset}
                self.array_vars[decl.name] = {
                    'elem_type': 'struct', 'count': n_fields,
                    'elem_size': 2, 'offset': -local_offset,
                    'tag': decl_tag,
                }
            else:
                local_offset += 2 if (decl.var_type in ('int', 'string', 'binary')
                                      or decl.pointer_depth) else 1
                self.local_vars[decl.name] = {'offset': -local_offset}

        # Store locals_size for iret() cleanup
        self._timer_interrupt_locals_size = local_size if func_def.name == 'timer_interrupt' else 0
        self._emitted_return = False

        # Run a lightweight register-coloring pass to record assignment hints.
        # IMPORTANT: Only process actual local variables (VarDecl), not parameters.
        # Parameters have their own stack offsets and should never be spilled to zero-page.
        if self.local_vars:
            # Separate parameters from local variables
            param_names = {p.name for p in func_def.params}
            actual_local_names = [name for name in self.local_vars
                                  if name not in param_names and name not in self.array_vars]
            
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
            if func_def.name == 'timer_interrupt':
                # ISR without an explicit iret() call: restore the saved
                # context and return from the interrupt. A normal RET here
                # would pop the pushed flags word as a return address and
                # corrupt the interrupted program state.
                self.assembly.append("; Implicit ISR return")
                if self._timer_interrupt_locals_size > 0:
                    self.assembly.append(
                        f"    ADD SP, {self._timer_interrupt_locals_size} ; Deallocate locals before IRET")
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
            elif isinstance(statement, FuncCall):
                if statement.name == 'iret' and self.current_function == 'timer_interrupt':
                    # Special handling for iret: don't emit normal epilogue
                    if hasattr(self, '_timer_interrupt_locals_size') and self._timer_interrupt_locals_size > 0:
                        self.emit(f"    ADD SP, {self._timer_interrupt_locals_size} ; Deallocate locals before IRET")
                    # Restore the general registers saved by the ISR prologue
                    # (interrupt entry only preserves PC + flags).
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
        if var_decl.is_array:
            # Local arrays: emit runtime stores for initializer-list elements.
            # (Global array initializers are emitted as DW/DB data instead.)
            info = self._get_array_info(var_decl.name)
            self.emit_comment(f"array {var_decl.name}[{info['count']}]")
            if var_decl.init_list and not info.get('is_global'):
                for i, init_expr in enumerate(var_decl.init_list):
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
            reg = self.generate_expression(var_decl.value)
            self._emit_var_store(var_decl.name, reg)
            self.free_register()

    def generate_assignment(self, assignment: Assignment):
        self.emit_comment(f"Assignment to {assignment.name}")
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
                # Shift operations: amount must be a constant (parser requires this)
                if not isinstance(value.right, Number):
                    raise TypeError("Shift amount must be a constant integer for this compiler version.")
                shift_amount = int(value.right.value, 0)
                op_mnemonic = "SHR" if op == '>>' else "SHL"
                self.emit_comment(f"Compound shift {op_mnemonic} by {shift_amount}")
                for _ in range(shift_amount):
                    self.emit(f"    {op_mnemonic} {var_reg}, 1")
            else:
                rhs_reg = self.generate_expression(value.right)
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
                elif op == '*': self.emit(f"    MUL {var_reg}, {rhs_reg}")
                elif op == '/': self.emit(f"    DIV {var_reg}, {rhs_reg}")
                elif op == '%': self.emit(f"    MOD {var_reg}, {rhs_reg}")
                elif op == '&': self.emit(f"    AND {var_reg}, {rhs_reg}")
                elif op == '|': self.emit(f"    OR {var_reg}, {rhs_reg}")
                elif op == '^': self.emit(f"    XOR {var_reg}, {rhs_reg}")
                else: raise SyntaxError(f"Unknown compound operator '{op}'")
                self.free_register()
            self._emit_var_store(assignment.name, var_reg)
            self.free_register()
        else:
            reg = self.generate_expression(assignment.value)
            self._emit_var_store(assignment.name, reg)
            self.free_register()

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

        # Detect compound assignment: p.x += v decomposes to
        # MemberAssignment(p.x, BinaryOp(p.x, '+', v)).
        compound_op = None
        rhs = stmt.value
        if (isinstance(stmt.value, BinaryOp)
                and isinstance(stmt.value.left, MemberAccess)
                and self._member_targets_equal(stmt.value.left, target)):
            compound_op = stmt.value.op
            rhs = stmt.value.right

        can_push = self.current_function != 'timer_interrupt'
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
                if not isinstance(rhs, Number):
                    raise TypeError(
                        "Shift amount must be a constant integer for this "
                        "compiler version.")
                shift_amount = int(rhs.value, 0)
                op_mnemonic = "SHR" if compound_op == '>>' else "SHL"
                for _ in range(shift_amount):
                    self.emit(f"    {op_mnemonic} {acc_reg}, 1")
            elif compound_op == '+': self.emit(f"    ADD {acc_reg}, {rhs_reg}")
            elif compound_op == '-': self.emit(f"    SUB {acc_reg}, {rhs_reg}")
            elif compound_op == '*': self.emit(f"    MUL {acc_reg}, {rhs_reg}")
            elif compound_op == '/': self.emit(f"    DIV {acc_reg}, {rhs_reg}")
            elif compound_op == '%': self.emit(f"    MOD {acc_reg}, {rhs_reg}")
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
        target = stmt.target
        info = self._get_array_info(target.name)
        can_push = self.current_function != 'timer_interrupt'

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
        idx_reg = self.generate_expression(target.index)
        if can_push:
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
                # Shift amounts are compile-time constants: no codegen runs
                # between the load and the shifts, so acc cannot be clobbered.
                if not isinstance(rhs, Number):
                    raise TypeError("Shift amount must be a constant integer for this compiler version.")
                shift_amount = int(rhs.value, 0)
                op_mnemonic = "SHR" if compound_op == '>>' else "SHL"
                for _ in range(shift_amount):
                    self.emit(f"    {op_mnemonic} {acc_reg}, 1")
            else:
                # Stash the loaded element across RHS evaluation, restore it,
                # THEN apply the operation (applying before the POP would let
                # the stale stacked value overwrite the computed result).
                if can_push:
                    self.emit(f"    PUSH {acc_reg}")
                rhs_reg = self.generate_expression(rhs)
                if can_push:
                    rhs_reg = self._pop_preserving(acc_reg, rhs_reg)
                if compound_op == '+': self.emit(f"    ADD {acc_reg}, {rhs_reg}")
                elif compound_op == '-': self.emit(f"    SUB {acc_reg}, {rhs_reg}")
                elif compound_op == '*': self.emit(f"    MUL {acc_reg}, {rhs_reg}")
                elif compound_op == '/': self.emit(f"    DIV {acc_reg}, {rhs_reg}")
                elif compound_op == '%': self.emit(f"    MOD {acc_reg}, {rhs_reg}")
                elif compound_op == '&': self.emit(f"    AND {acc_reg}, {rhs_reg}")
                elif compound_op == '|': self.emit(f"    OR {acc_reg}, {rhs_reg}")
                elif compound_op == '^': self.emit(f"    XOR {acc_reg}, {rhs_reg}")
                else: raise SyntaxError(f"Unknown compound operator '{compound_op}'")
            store_reg = acc_reg
        else:
            val_reg = self.generate_expression(rhs)
            store_reg = val_reg

        if can_push:
            # The index was stashed across RHS evaluation; restore it without
            # destroying the computed value (register names can alias).
            store_reg = self._pop_preserving(idx_reg, store_reg)
        addr_reg = self.get_register(exclude={idx_reg, store_reg})
        self._emit_array_addr(info, idx_reg, addr_reg)
        self._emit_mem_store(addr_reg, store_reg, info['elem_size'])
        return store_reg

    def generate_address_of(self, expr: AddressOf) -> str:
        """&var / &arr[i]: compute an address into a register.

        Pointers are plain 16-bit addresses on Nova-16, so & simply yields
        the variable's storage location as an integer value."""
        operand = expr.operand
        if isinstance(operand, Identifier):
            name = operand.name
            reg = self.get_register()
            if name in self.local_vars:
                # Params/locals shadow globals (C scoping) -- &x on a param
                # whose name collides with a global must yield the frame slot.
                # Respect spill allocations so &x matches where loads/stores
                # of x actually live (zero-page migration).
                if name in self.spill_allocations and self.current_function != 'timer_interrupt':
                    self.emit(f"    MOV {reg}, 0x{self.spill_allocations[name]:04X}")
                    return reg
                offset = self._get_local_offset(name)
                if self.current_function == 'timer_interrupt':
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
            g = self.global_vars.get(name)
            if g:
                self.emit(f"    MOV {reg}, 0x{g['address']:04X}")
                return reg
            raise NameError(f"Cannot take address of undefined variable '{name}'")
        if isinstance(operand, ArrayAccess):
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
        raise SyntaxError("'&' operand must be a variable or array element")

    def generate_deref_assignment(self, stmt: DerefAssignment) -> str:
        """*ptr = value (simple or compound). Returns register holding value."""
        target = stmt.target
        can_push = self.current_function != 'timer_interrupt'

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
            if compound_op == '+': self.emit(f"    ADD {acc_reg}, {rhs_reg}")
            elif compound_op == '-': self.emit(f"    SUB {acc_reg}, {rhs_reg}")
            elif compound_op == '*': self.emit(f"    MUL {acc_reg}, {rhs_reg}")
            elif compound_op == '/': self.emit(f"    DIV {acc_reg}, {rhs_reg}")
            elif compound_op == '%': self.emit(f"    MOD {acc_reg}, {rhs_reg}")
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
        if expr.op == '++':
            if step and step > 1:
                self.emit(f"    ADD {reg}, {step}")
            else:
                self.emit(f"    INC {reg}")
        elif expr.op == '--':
            if step and step > 1:
                self.emit(f"    SUB {reg}, {step}")
            else:
                self.emit(f"    DEC {reg}")
        else:
            raise SyntaxError(f"Unknown prefix operator '{expr.op}'")
        self._emit_var_store(expr.operand.name, reg)
        return reg

    def generate_return(self, return_stmt: Return):
        self.emit_comment("Function return")
        if return_stmt.value:
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


    def generate_if(self, if_stmt: If):
        self.emit_comment("If statement")
        end_label = self.generate_label("if_end")
        else_label = self.generate_label("if_else")
        reg = self.generate_expression(if_stmt.cond)
        self.emit(f"    CMP {reg}, 0")
        self.free_register()
        self.emit(f"    JZ {else_label if if_stmt.else_body else end_label}")
        self.generate_block(if_stmt.then_body)
        if if_stmt.else_body:
            self.emit(f"    JMP {end_label}")
            self.emit_label(else_label)
            self.generate_block(if_stmt.else_body)
        self.emit_label(end_label)

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
            and self.current_function != 'timer_interrupt'
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

    def generate_expression(self, expr: Expression) -> str:
        if isinstance(expr, Number):
            reg = self.get_register()
            # Normalize the literal to a plain decimal integer: the Nova-16
            # assembler understands decimal and 0x hex, but not 0b/0o forms.
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
            # Constant folding: evaluate simple binary ops with two numeric
            # literal operands at compile time (brought over from NoBASIC's
            # ExpressionSimplifier). This avoids emitting MOV/ADD/SUB/etc.
            # instructions for expressions like `2 + 3` or `10 * 5`.
            if isinstance(expr.left, Number) and isinstance(expr.right, Number):
                try:
                    left_val = int(expr.left.value, 0)
                    right_val = int(expr.right.value, 0)
                    op = expr.op
                    if op == '+': folded = left_val + right_val
                    elif op == '-': folded = left_val - right_val
                    elif op == '*': folded = left_val * right_val
                    elif op == '/':
                        if right_val == 0:
                            folded = None
                            raise ArithmeticError("Division by zero")
                        folded = int(left_val / right_val)
                    elif op == '%': folded = left_val % right_val if right_val != 0 else None
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
                if not isinstance(expr.right, Number):
                    raise TypeError("Shift amount must be a constant integer for this compiler version.")
                left_reg = self.generate_expression(expr.left)
                shift_amount = int(expr.right.value, 0)
                op_mnemonic = "SHR" if expr.op == '>>' else "SHL"
                self.emit_comment(f"Unrolled shift {op_mnemonic} by {shift_amount}")
                for _ in range(shift_amount):
                    self.emit(f"    {op_mnemonic} {left_reg}, 1")
                return left_reg

            left_reg = self.generate_expression(expr.left)
            # Preserve the left operand across right-hand evaluation:
            # expression temporaries are round-robin reused, and a deep RHS
            # (each array element read alone consumes two temporaries) would
            # otherwise clobber left_reg before the operation is emitted.
            can_push_left = self.current_function != 'timer_interrupt'
            if can_push_left:
                self.emit(f"    PUSH {left_reg}")
            right_reg = self.generate_expression(expr.right)
            if can_push_left:
                right_reg = self._pop_preserving(left_reg, right_reg)
            op = expr.op
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
            elif op == '*': self.emit(f"    MUL {left_reg}, {right_reg}")
            elif op == '/': self.emit(f"    DIV {left_reg}, {right_reg}")
            elif op == '%': self.emit(f"    MOD {left_reg}, {right_reg}")
            elif op in ['==', '!=', '>', '<', '>=', '<=']:
                # Use unsigned comparisons (JC/JNC) based on carry flag for
                # <, >, <=, >=.  After CMP a,b (a-b), carry = 1 (borrow) iff
                # a < b (unsigned).  For > and <= we swap operands so a single
                # conditional jump suffices.
                true_label = self.generate_label("cmp_true")
                end_label = self.generate_label("cmp_end")
                if op == '==':
                    self.emit(f"    CMP {left_reg}, {right_reg}")
                    self.emit(f"    JZ {true_label}")
                elif op == '!=':
                    self.emit(f"    CMP {left_reg}, {right_reg}")
                    self.emit(f"    JNZ {true_label}")
                elif op == '<':
                    self.emit(f"    CMP {left_reg}, {right_reg}")
                    self.emit(f"    JC {true_label}")     # borrow → left < right (unsigned)
                elif op == '>=':
                    self.emit(f"    CMP {left_reg}, {right_reg}")
                    self.emit(f"    JNC {true_label}")   # no borrow → left >= right (unsigned)
                elif op == '>':
                    self.emit(f"    CMP {right_reg}, {left_reg}")
                    self.emit(f"    JC {true_label}")     # borrow of (right-left) → right < left → left > right (unsigned)
                elif op == '<=':
                    self.emit(f"    CMP {right_reg}, {left_reg}")
                    self.emit(f"    JNC {true_label}")   # no borrow → right >= left → left <= right (unsigned)
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
        elif isinstance(expr, PrefixOp):
            return self.generate_prefix(expr)
        elif isinstance(expr, PostfixOp):
            if isinstance(expr.left, Identifier):
                reg = self.get_register()
                self._emit_var_load(reg, expr.left.name)
                result_reg = self.get_register(exclude={reg})
                self.emit(f"    MOV {result_reg}, {reg}")
                # Pointer postfix ++/-- advance by the pointee size (C).
                step = self._pointer_step(expr.left.name)
                if expr.op == '++':
                    if step and step > 1: self.emit(f"    ADD {reg}, {step}")
                    else: self.emit(f"    INC {reg}")
                elif expr.op == '--':
                    if step and step > 1: self.emit(f"    SUB {reg}, {step}")
                    else: self.emit(f"    DEC {reg}")
                else: raise SyntaxError(f"Unknown postfix operator '{expr.op}'")
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
                target = expr.left
                info = self._get_array_info(target.name)
                can_push = self.current_function != 'timer_interrupt'
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
        else:
            raise RuntimeError(f"Unknown expression type: {type(expr)}")

    def generate_cast(self, cast: Cast) -> str:
        """Generate code for type cast expressions using Nova-16 conversion instructions.
        
        Supported casts:
          (string)expr   -> ITOS:  converts int expr to decimal string at 0xA000, 
                                    returns buffer address
          (binary)expr   -> ITOB:  converts int expr to binary string at 0xA100,
                                    returns buffer address
          (int)expr      -> STOI/BTOI: converts string/binary addr to int
          (char)expr     -> truncates to 8 bits (low byte)
        """
        target = cast.target_type
        inner = cast.expr

        # Identity cast optimization: casting to the type the expression
        # already produces is a no-op (just a register copy). Without this,
        # `(string)s` where s is a string variable would ITOS the string
        # *address* — producing the decimal digits of the pointer — instead
        # of simply passing the existing string through.
        source_type = self._cast_source_type(inner)
        if source_type == target and target in ('string', 'binary', 'int'):
            reg = self.get_register()
            inner_reg = self.generate_expression(inner)
            if inner_reg != reg:
                self.emit(f"    MOV {reg}, {inner_reg}")
            self.free_register()
            return reg

        # Compile-time optimization: casting a literal is a compile-time op.
        if isinstance(inner, Number):
            num_val = int(inner.value, 0) & 0xFFFF
            if target == 'char':
                reg = self.get_register()
                self.emit(f"    MOV {reg}, {num_val & 0xFF}")
                return reg
            elif target == 'string':
                # (string)CONST -> convert at runtime is actually still needed
                # for decimal string generation, but ITOS works fine at runtime.
                pass  # fall through to runtime
            elif target == 'binary':
                pass  # fall through to runtime
            elif target == 'int':
                reg = self.get_register()
                self.emit(f"    MOV {reg}, {num_val}")
                return reg

        self.emit_comment(f"Type cast: ({target}) expr")
        inner_reg = self.generate_expression(inner)
        result_reg = self.get_register()

        if target == 'string':
            # ITOS writes the decimal string to the fixed buffer 0xA000 and
            # writes that buffer address into the destination operand.
            self.emit(f"    ITOS {result_reg}, {inner_reg}")
        elif target == 'binary':
            # ITOB writes the binary string to the fixed buffer 0xA100 and
            # writes that buffer address into the destination operand.
            # First load the fixed buffer address into a temp register.
            self.emit(f"    MOV {result_reg}, 0xA100")
            self.emit(f"    ITOB {result_reg}, {inner_reg}")
        elif target == 'int':
            # STOI parses a decimal string; BTOI parses a binary string.
            # Numeric sources (int/char) already hold their value in a
            # register, so a plain MOV is correct — no memory dereference.
            if source_type == 'binary':
                self.emit(f"    BTOI {result_reg}, {inner_reg}")
            elif source_type == 'string':
                self.emit(f"    STOI {result_reg}, {inner_reg}")
            else:
                # Numeric (int/char): value already in inner_reg; just copy.
                self.emit(f"    MOV {result_reg}, {inner_reg}")
        elif target == 'char':
            # Truncate to 8 bits: use the low byte of the register.

            if inner_reg.startswith('P'):
                self.emit(f"    MOV {result_reg}, :{inner_reg}")
            else:
                self.emit(f"    MOV {result_reg}, {inner_reg}")
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
            return expr.target_type in ('string', 'binary')
        if isinstance(expr, FuncCall):
            func = self.functions.get(expr.name)
            return bool(func and func.get('return_type') in ('string', 'binary'))
        return False

    def _cast_source_type(self, expr: Expression) -> Optional[str]:
        """Determine the type of an expression's value for cast resolution.

        Returns 'string', 'binary', 'int', 'char', or None if unknown.
        Used by generate_cast to pick STOI/BTOI vs simple MOV for (int) casts,
        and by identity-cast elimination when casting to the same type.
        """
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
            return expr.target_type  # (string)x yields a string value
        if isinstance(expr, StringLiteral):
            return 'string'
        if isinstance(expr, CharLiteral):
            return 'char'
        if isinstance(expr, Number):
            return 'int'
        if isinstance(expr, FuncCall):
            func = self.functions.get(expr.name)
            return func.get('return_type') if func else None
        if isinstance(expr, PostfixOp):
            if isinstance(expr.left, Identifier):
                return self.var_types.get(expr.left.name)
        if isinstance(expr, ArrayAccess):
            try:
                return self._get_array_info(expr.name)['elem_type']
            except NameError:
                return None
        return None

    def generate_call(self, call: FuncCall) -> str:
        self.emit_comment(f"Call to {call.name}")
        
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
        
        # --- Normal call path: push all args in reversed order ---
        for arg in reversed(call.args):
            arg_reg = self.generate_expression(arg)
            self.emit(f"    PUSH {arg_reg}")
            self.free_register()
        
        if call.name in self.functions:
            label = self.functions[call.name]['label']
        else:
            # Arity-aware builtin resolution: optional-argument builtins
            # (scroll_x/scroll_y/roll_x/roll_y) select a dedicated stub per
            # argument count so the stack layout always matches the callee.
            label = self._resolve_builtin_label(call.name, len(call.args))
        if not label:
            raise NameError(f"Undefined function '{call.name}'")
        # Record builtin usage so generate_builtins only emits what is called.
        if label in self.BUILTIN_IMPLEMENTATIONS:
            self.used_builtins.add(label)
        
        self.emit(f"    CALL {label}")
        if call.name in self.functions and call.args:
            # User-function callees end with MOV SP, FP / POP FP / RET,
            # which restores SP to the frame base and LEAVES the
            # caller-pushed arguments on the stack. Deallocate them here
            # (cdecl-style, one word per argument -- every PUSH above is a
            # full 16-bit word regardless of the parameter's declared type).
            # Without this, loops that call functions with arguments leak
            # stack bytes every iteration until SP walks down through low
            # memory, wraps, and corrupts the running program.
            self.emit(f"    ADD SP, {len(call.args) * 2} ; Caller cleans up args")
        elif call.args:
            # Builtin stubs pop their own arguments off the stack.
            self.emit(f"    ; Args consumed by callee")

        result_reg = self.get_register()
        # User-defined functions return their 16-bit int result in P0
        # (see generate_return), and a subset of builtins also write P0
        # directly (RND P0, RNDR P0, KEYSTAT P0, KEYIN P0, SREAD P0,
        # SERIN P0, SERSTAT P0, KEYCOUNT P0, and all math/string/memory/
        # bit/BCD builtins that write their result to P0).
        # Void builtins (set_vmode, etc.) leave both untouched; their
        # return value is discarded so the source register is irrelevant.
        p0_returning_builtins = {
            'random', 'random_range', 'key_available', 'key_read',
            'read_screen', 'key_count', 'ser_in', 'ser_stat', 'vread',
            'abs', 'min', 'max', 'clz', 'ctz', 'popcnt',
            'sqrt', 'log', 'exp', 'sin', 'cos', 'tan',
            'atan', 'asin', 'acos', 'deg', 'rad',
            'floor', 'ceil', 'round', 'trunc', 'frac', 'intgr', 'int', 'powr',
            'strcpy', 'strcat', 'strcmp', 'strlen',
            'strupr', 'strlwr', 'strrev', 'strfind', 'strfindi',
            'ser_out', 'ser_ctrl',
            'memcpy', 'memset', 'memmove', 'memcmp', 'memtest', 'memswap',
            'btst', 'bset', 'bclr', 'bflip',
            'swap', 'xchng',
            'bcd2bin', 'bin2bcd', 'bcdadd', 'bcdsub',
            'bcda', 'bcds', 'bcdcmp',
            'mouse_ctrl',
        }
        if call.name in self.functions or call.name in p0_returning_builtins:
            self.emit(f"    MOV {result_reg}, P0")
        else:
            self.emit(f"    MOV {result_reg}, R0")
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
        for label, body in selected:
            self.emit_label(label)
            for line in body:
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
