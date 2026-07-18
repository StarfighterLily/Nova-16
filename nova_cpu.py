import numpy as np
from nova.memory import Memory as mem
import nova_gfx as gpu
import nova_mouse as mouse
import nova_sound as sound
import nova_uart as uart
from core.exec import build_instruction_table
import time
import cProfile
import pstats
from datetime import datetime, timezone
from functools import wraps
from core.flags import Flags
from core.regfile import RegisterFile, REGISTER_CODE_MAP
from core.fetch import decode_operands, calculate_memory_address, release_operands, Operand

class CPU:
    # Frozen set of register types served by RegisterFile dispatch
    _REGFILE_TYPES = frozenset({'R', 'P', 'P_high', 'P_low', 'SP', 'FP', 'V', 'VL',
                                'TT', 'TM', 'TC', 'TS', 'C0', 'C1', 'MX', 'MY', 'MB',
                                'SA', 'SF', 'SV', 'SW', 'BANK'})

    RTC_EPOCH_UNIX = int(datetime(2018, 7, 17, tzinfo=timezone.utc).timestamp())

    def __init__(self, memory, gfx, keyboard=None, sound_system=None,
                 uart_device=None, mouse_device=None, stack_size=65535,
                 bus=None, interrupt_controller=None, timer_device=None):
        self.memory = memory
        self.gfx = gfx
        self.keyboard_device = keyboard
        self.bus = bus
        self.intr_ctrl = interrupt_controller
        self.timer_device = timer_device
        
        if sound_system is None:
            self.sound = sound.NovaSound()
        else:
            self.sound = sound_system

        self.regfile = RegisterFile()
        self.Rregisters = self.regfile.R
        self.Pregisters = self.regfile.P

        self.pc = 0x0000
        self.flags_obj = Flags()
        self._cached_flags: int = 0
        self._last_operation_was_cmp = False
        self.stack_size = stack_size
        self.stack = []
        
        self.interrupts = [0] * 8
        self.hw_breakpoints = [0] * 4
        self.hw_breakpoint_enabled = [False] * 4

        import random
        self.rng_seed = random.randint(0, 0xFFFF)
        self.rtc_time_source = time.time
        
        self.uart = uart_device if uart_device is not None else uart.NovaUART()
        self.serial = uart.SerialRegisterView(self.uart)
        self.uart.set_interrupt_callback(self._refresh_pending_interrupt_sources)
        self.mouse = mouse_device if mouse_device is not None else mouse.NovaMouse(self.gfx)
        self.mouse.attach(gfx=self.gfx, cpu_ref=self)
        self.mouse.set_interrupt_callback(self._refresh_pending_interrupt_sources)

        self.keyboard = [0] * 4
        self.key_buffer = []
        self.key_buffer_size = 64

        self.halted = False
        self.cycles = 0
        
        self._register_lookup = self._build_register_lookup_table()
        
        self.interrupt_check_counter = 0
        self.interrupt_check_frequency = 1024
        self.last_interrupt_state = 0
        self.has_pending_interrupt_sources = False
        self.has_hw_breakpoints = False
        self._last_pc = 0xFFFF
        self._sequential_fetch_threshold = 2

        self.instruction_table = build_instruction_table()
        self._noop_opcode_set = set()
        for opcode, inst in self.instruction_table.items():
            if inst.num_operands == 0:
                self._noop_opcode_set.add(opcode)

        self.opcode_to_name = {}
        for opcode, instruction in self.instruction_table.items():
            self.opcode_to_name[opcode] = instruction.name

        self._register_externals()

        self.profiling_enabled = False
        self.profile_data = {
            'total_cycles': 0,
            'instructions_executed': 0,
            'opcode_counts': {},
            'method_times': {},
            'memory_accesses': 0,
            'start_time': None,
            'instruction_start_times': {},
            'cycle_start_time': None
        }

    def enable_profiling(self):
        self.profiling_enabled = True
        self.profile_data['start_time'] = time.time()

    def disable_profiling(self):
        self.profiling_enabled = False

    def reset_profile_data(self):
        self.profile_data = {
            'total_cycles': 0,
            'instructions_executed': 0,
            'opcode_counts': {},
            'method_times': {},
            'memory_accesses': 0,
            'start_time': self.profile_data.get('start_time'),
            'instruction_start_times': {},
            'cycle_start_time': None
        }

    def get_profile_report(self):
        if not self.profiling_enabled:
            return "Profiling not enabled"
        end_time = time.time()
        total_time = end_time - (self.profile_data['start_time'] or end_time)
        report = []
        report.append("=== CPU Profiling Report ===")
        report.append(f"Total execution time: {total_time:.4f} seconds")
        report.append(f"Instructions executed: {self.profile_data['instructions_executed']}")
        report.append(f"Memory accesses: {self.profile_data['memory_accesses']}")
        report.append(f"Operand parses: {self.profile_data.get('operand_parses', 0)}")
        report.append(f"Operand value gets: {self.profile_data.get('operand_values', 0)}")
        report.append(f"Average IPS: {self.profile_data['instructions_executed'] / total_time:.2f}")
        if self.profile_data['opcode_counts']:
            report.append("\nTop 10 instructions by frequency:")
            sorted_opcodes = sorted(self.profile_data['opcode_counts'].items(),
                                  key=lambda x: x[1], reverse=True)[:10]
            for opcode, count in sorted_opcodes:
                pct = (count / self.profile_data['instructions_executed']) * 100
                name = self.opcode_to_name.get(opcode, f"0x{opcode:02X}")
                report.append(f"  {name}: {count} ({pct:.1f}%)")
        if self.profile_data['method_times']:
            report.append("\nMethod timing (total time spent):")
            sorted_methods = sorted(self.profile_data['method_times'].items(),
                                  key=lambda x: x[1], reverse=True)
            for method, mt in sorted_methods:
                pct = (mt / total_time) * 100 if total_time > 0 else 0
                report.append(f"  {method}: {mt:.6f}s ({pct:.1f}%)")
        return "\n".join(report)

    def profile_method(self, method_name):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if self.profiling_enabled:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    end_time = time.time()
                    elapsed = end_time - start_time
                    if method_name not in self.profile_data['method_times']:
                        self.profile_data['method_times'][method_name] = 0
                    self.profile_data['method_times'][method_name] += elapsed
                    return result
                else:
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    # ---- FLAGS ACCESS ----

    @property
    def flags(self):
        return self.flags_obj

    @flags.setter
    def flags(self, value):
        if isinstance(value, (list, tuple)):
            self.flags_obj.set_state(value)
        elif isinstance(value, Flags):
            self.flags_obj = value

    # ---- FLAG PROPERTIES ----

    @property
    def trap_flag(self):
        return self.flags_obj.trap_flag
    @trap_flag.setter
    def trap_flag(self, value):
        self.flags_obj.trap_flag = value

    @property
    def sign_flag(self):
        return self.flags_obj.sign_flag
    @sign_flag.setter
    def sign_flag(self, value):
        self.flags_obj.sign_flag = value

    @property
    def overflow_flag(self):
        return self.flags_obj.overflow_flag
    @overflow_flag.setter
    def overflow_flag(self, value):
        self.flags_obj.overflow_flag = value

    @property
    def break_flag(self):
        return self.flags_obj.break_flag
    @break_flag.setter
    def break_flag(self, value):
        self.flags_obj.break_flag = value

    @property
    def decimal_flag(self):
        return self.flags_obj.decimal_flag
    @decimal_flag.setter
    def decimal_flag(self, value):
        self.flags_obj.decimal_flag = value

    @property
    def interrupt_flag(self):
        return self.flags_obj.interrupt_flag
    @interrupt_flag.setter
    def interrupt_flag(self, value):
        self.flags_obj.interrupt_flag = value

    @property
    def carry_flag(self):
        return self.flags_obj.carry_flag
    @carry_flag.setter
    def carry_flag(self, value):
        self.flags_obj.carry_flag = value

    @property
    def zero_flag(self):
        return self.flags_obj.zero_flag
    @zero_flag.setter
    def zero_flag(self, value):
        self.flags_obj.zero_flag = value

    @property
    def parity_flag(self):
        return self.flags_obj.parity_flag
    @parity_flag.setter
    def parity_flag(self, value):
        self.flags_obj.parity_flag = value

    @property
    def direction_flag(self):
        return self.flags_obj.direction_flag
    @direction_flag.setter
    def direction_flag(self, value):
        self.flags_obj.direction_flag = value

    @property
    def bcd_carry_flag(self):
        return self.flags_obj.bcd_carry_flag
    @bcd_carry_flag.setter
    def bcd_carry_flag(self, value):
        self.flags_obj.bcd_carry_flag = value

    @property
    def hacker_flag(self):
        return self.flags_obj.hacker_flag
    @hacker_flag.setter
    def hacker_flag(self, value):
        self.flags_obj.hacker_flag = value

    @property
    def decimal_mode(self):
        return self.flags_obj.decimal_mode
    @decimal_mode.setter
    def decimal_mode(self, value):
        self.flags_obj.decimal_mode = value

    @property
    def aux_carry(self):
        return self.flags_obj.aux_carry
    @aux_carry.setter
    def aux_carry(self, value):
        self.flags_obj.aux_carry = value

    # ---- REGISTER PROPERTIES ----

    @property
    def r0(self):
        return int(self.Rregisters[0])
    @r0.setter
    def r0(self, value):
        self.Rregisters[0] = int(value) & 0xFF

    @property
    def r1(self):
        return int(self.Rregisters[1])
    @r1.setter
    def r1(self, value):
        self.Rregisters[1] = int(value) & 0xFF

    @property
    def r2(self):
        return int(self.Rregisters[2])
    @r2.setter
    def r2(self, value):
        self.Rregisters[2] = int(value) & 0xFF

    @property
    def r3(self):
        return int(self.Rregisters[3])
    @r3.setter
    def r3(self, value):
        self.Rregisters[3] = int(value) & 0xFF

    @property
    def r4(self):
        return int(self.Rregisters[4])
    @r4.setter
    def r4(self, value):
        self.Rregisters[4] = int(value) & 0xFF

    @property
    def r5(self):
        return int(self.Rregisters[5])
    @r5.setter
    def r5(self, value):
        self.Rregisters[5] = int(value) & 0xFF

    @property
    def r6(self):
        return int(self.Rregisters[6])
    @r6.setter
    def r6(self, value):
        self.Rregisters[6] = int(value) & 0xFF

    @property
    def r7(self):
        return int(self.Rregisters[7])
    @r7.setter
    def r7(self, value):
        self.Rregisters[7] = int(value) & 0xFF

    @property
    def r8(self):
        return int(self.Rregisters[8])
    @r8.setter
    def r8(self, value):
        self.Rregisters[8] = int(value) & 0xFF

    @property
    def r9(self):
        return int(self.Rregisters[9])
    @r9.setter
    def r9(self, value):
        self.Rregisters[9] = int(value) & 0xFF

    @property
    def p0(self):
        return int(self.Pregisters[0])
    @p0.setter
    def p0(self, value):
        self.Pregisters[0] = int(value) & 0xFFFF

    @property
    def p1(self):
        return int(self.Pregisters[1])
    @p1.setter
    def p1(self, value):
        self.Pregisters[1] = int(value) & 0xFFFF

    @property
    def p2(self):
        return int(self.Pregisters[2])
    @p2.setter
    def p2(self, value):
        self.Pregisters[2] = int(value) & 0xFFFF

    @property
    def p3(self):
        return int(self.Pregisters[3])
    @p3.setter
    def p3(self, value):
        self.Pregisters[3] = int(value) & 0xFFFF

    @property
    def p4(self):
        return int(self.Pregisters[4])
    @p4.setter
    def p4(self, value):
        self.Pregisters[4] = int(value) & 0xFFFF

    @property
    def p5(self):
        return int(self.Pregisters[5])
    @p5.setter
    def p5(self, value):
        self.Pregisters[5] = int(value) & 0xFFFF

    @property
    def p6(self):
        return int(self.Pregisters[6])
    @p6.setter
    def p6(self, value):
        self.Pregisters[6] = int(value) & 0xFFFF

    @property
    def p7(self):
        return int(self.Pregisters[7])
    @p7.setter
    def p7(self, value):
        self.Pregisters[7] = int(value) & 0xFFFF

    @property
    def p8(self):
        return int(self.Pregisters[8])
    @p8.setter
    def p8(self, value):
        self.Pregisters[8] = int(value) & 0xFFFF

    @property
    def p9(self):
        return int(self.Pregisters[9])
    @p9.setter
    def p9(self, value):
        self.Pregisters[9] = int(value) & 0xFFFF

    @property
    def sp(self):
        return int(self.Pregisters[8])
    @sp.setter
    def sp(self, value):
        self.Pregisters[8] = int(value) & 0xFFFF

    @property
    def fp(self):
        return int(self.Pregisters[9])
    @fp.setter
    def fp(self, value):
        self.Pregisters[9] = int(value) & 0xFFFF

    # ---- SOUND REGISTER PROPERTIES ----

    @property
    def sa(self):
        if self.sound:
            return int(self.sound.get_register('SA'))
        return 0
    @sa.setter
    def sa(self, value):
        if self.sound:
            self.sound.update_registers(sa=int(value) & 0xFFFF)

    @property
    def sf(self):
        if self.sound:
            return int(self.sound.get_register('SF'))
        return 0
    @sf.setter
    def sf(self, value):
        if self.sound:
            self.sound.update_registers(sf=int(value) & 0xFF)

    @property
    def sv(self):
        if self.sound:
            return int(self.sound.get_register('SV'))
        return 0
    @sv.setter
    def sv(self, value):
        if self.sound:
            self.sound.update_registers(sv=int(value) & 0xFF)

    @property
    def sw(self):
        if self.sound:
            return int(self.sound.get_register('SW'))
        return 0
    @sw.setter
    def sw(self, value):
        if self.sound:
            self.sound.update_registers(sw=int(value) & 0xFF)

    @property
    def mx(self):
        return int(self.mouse.x)
    @mx.setter
    def mx(self, value):
        self.mouse.move_to(value, self.mouse.y)

    @property
    def my(self):
        return int(self.mouse.y)
    @my.setter
    def my(self, value):
        self.mouse.move_to(self.mouse.x, value)

    @property
    def mb(self):
        return int(self.mouse.buttons) & 0xFF
    @mb.setter
    def mb(self, value):
        self.mouse.set_buttons(value)

    @property
    def rtc_seconds(self):
        elapsed = int(self.rtc_time_source()) - self.RTC_EPOCH_UNIX
        return max(0, elapsed) & 0xFFFFFFFF

    @property
    def c0(self):
        return self.rtc_seconds & 0xFFFF
    @c0.setter
    def c0(self, value):
        return

    @property
    def c1(self):
        return (self.rtc_seconds >> 16) & 0xFFFF
    @c1.setter
    def c1(self, value):
        return

    # ---- BULK OPERATIONS ----

    def reset_all_flags(self):
        self.flags_obj.reset_all()

    def reset_all_registers(self):
        self.Rregisters[:] = [0] * len(self.Rregisters)
        self.Pregisters[:] = [0] * len(self.Pregisters)
        self.Pregisters[8] = 0xFFFF
        self.Pregisters[9] = 0xFFFF

    def get_flag_state(self):
        return self.flags_obj.get_state()

    def set_flag_state(self, flag_array):
        self.flags_obj.set_state(flag_array)

    def get_register_state(self):
        return {
            'r_registers': self.Rregisters.copy(),
            'p_registers': self.Pregisters.copy()
        }

    def set_register_state(self, reg_dict):
        if 'r_registers' in reg_dict:
            self.Rregisters[:] = reg_dict['r_registers']
        if 'p_registers' in reg_dict:
            self.Pregisters[:] = reg_dict['p_registers']

    def reinit(self):
        self.Rregisters[:] = [0] * len(self.Rregisters)
        self.Pregisters[:] = [0] * len(self.Pregisters)
        self.Pregisters[8] = 0xFFFF
        self.Pregisters[9] = 0xFFFF
        self.pc = 0x0000
        self.flags_obj.reset_all()
        self.stack = []
        self.interrupts[:] = [0] * len(self.interrupts)
        self.interrupt_check_counter = 0
        self.last_interrupt_state = 0
        self.has_pending_interrupt_sources = False
        self.uart.reset()
        self.keyboard[:] = [0] * len(self.keyboard)
        self.key_buffer = []
        if self.keyboard_device is not None:
            self.keyboard_device.clear_buffer()
        self.halted = False
        self.has_hw_breakpoints = False
        self.memory.reset()
        self.gfx.vram[:] = 0
        self.gfx.screen[:] = 0
        self.gfx.flags[:] = 0
        self.gfx.Vregisters[:] = [0, 0, 0, 0]
        self.gfx.vmode = 0
        if self.sound:
            self.sound.sstop()
            self.sound.update_registers(sa=0, sf=0, sv=0, sw=0)
        self.mouse.reset()
        if self.timer_device:
            self.timer_device.reset()
        self._register_lookup = self._build_register_lookup_table()
        self._noop_opcode_set = set()
        for opcode, inst in self.instruction_table.items():
            if inst.num_operands == 0:
                self._noop_opcode_set.add(opcode)
        if self.keyboard_device is not None:
            self.keyboard_device.cpu = self
        self.mouse.attach(gfx=self.gfx, cpu_ref=self)
        self.mouse.set_interrupt_callback(self._refresh_pending_interrupt_sources)

    def _refresh_pending_interrupt_sources(self):
        self.has_pending_interrupt_sources = bool(
            (self.interrupts[2] == 1 and (self.keyboard[1] & 0x80) != 0) or
            (self.interrupts[1] == 1 and self.uart.pending_interrupt) or
            (self.interrupts[3] == 1 and self.mouse.pending_interrupt) or
            self.interrupts[4] == 1
        )

    def _has_enabled_async_interrupt_sources(self):
        v = (self.interrupts[1] or self.interrupts[2] or
             self.interrupts[3] or self.interrupts[4])
        self._cached_async_sources = bool(v)
        return self._cached_async_sources

    def _refresh_hw_breakpoint_state(self):
        self.has_hw_breakpoints = bool(
            self.hw_breakpoint_enabled[0] or self.hw_breakpoint_enabled[1] or
            self.hw_breakpoint_enabled[2] or self.hw_breakpoint_enabled[3]
        )

    # ---- REGISTER DISPATCH ----

    def _register_externals(self):
        rf = self.regfile
        snd = self.sound
        gfx = self.gfx
        mouse = self.mouse
        tdev = self.timer_device
        mem = self.memory

        rf.register_external('BANK',
            getter=lambda idx: int(mem.current_bank),
            setter=lambda idx, v: mem.set_bank(int(v) & 0xFF))

        if snd:
            rf.register_external('SA',
                getter=lambda idx: int(snd.get_register('SA')),
                setter=lambda idx, v: snd.update_registers(sa=int(v) & 0xFFFF))
            rf.register_external('SF',
                getter=lambda idx: int(snd.get_register('SF')),
                setter=lambda idx, v: snd.update_registers(sf=int(v) & 0xFF))
            rf.register_external('SV',
                getter=lambda idx: int(snd.get_register('SV')),
                setter=lambda idx, v: snd.update_registers(sv=int(v) & 0xFF))
            rf.register_external('SW',
                getter=lambda idx: int(snd.get_register('SW')),
                setter=lambda idx, v: snd.update_registers(sw=int(v) & 0xFF))
        else:
            rf.register_external('SA', getter=lambda idx: 0)
            rf.register_external('SF', getter=lambda idx: 0)
            rf.register_external('SV', getter=lambda idx: 0)
            rf.register_external('SW', getter=lambda idx: 0)

        rf.register_external('V',
            getter=lambda idx: gfx.Vregisters[idx],
            setter=lambda idx, v: gfx.Vregisters.__setitem__(idx, int(v) & 0xFF))
        rf.register_external('VL',
            getter=lambda idx: int(gfx.VL),
            setter=lambda idx, v: setattr(gfx, 'VL', int(v) & 0xFF))

        rf.register_external('MX',
            getter=lambda idx: int(mouse.x),
            setter=lambda idx, v: mouse.move_to(v, mouse.y))
        rf.register_external('MY',
            getter=lambda idx: int(mouse.y),
            setter=lambda idx, v: mouse.move_to(mouse.x, v))
        rf.register_external('MB',
            getter=lambda idx: int(mouse.buttons) & 0xFF,
            setter=lambda idx, v: mouse.set_buttons(v))

        rf.register_external('C0', getter=lambda idx: int(self.c0))
        rf.register_external('C1', getter=lambda idx: int(self.c1))

        if tdev:
            rf.register_external('TT',
                getter=lambda idx: tdev.get_register(0),
                setter=lambda idx, v: tdev.set_register(0, v))
            rf.register_external('TM',
                getter=lambda idx: tdev.get_register(1),
                setter=lambda idx, v: tdev.set_register(1, v))
            rf.register_external('TC',
                getter=lambda idx: tdev.get_register(2),
                setter=lambda idx, v: tdev.set_register(2, v))
            rf.register_external('TS',
                getter=lambda idx: tdev.get_register(3),
                setter=lambda idx, v: tdev.set_register(3, v))
        else:
            rf.register_external('TT', getter=lambda idx: 0, setter=lambda idx, v: None)
            rf.register_external('TM', getter=lambda idx: 0, setter=lambda idx, v: None)
            rf.register_external('TC', getter=lambda idx: 0, setter=lambda idx, v: None)
            rf.register_external('TS', getter=lambda idx: 0, setter=lambda idx, v: None)

    def _get_operand_value(self, type, idx):
        """Optimized type dispatch — common types 'R'/'P' checked first."""
        if type == 'R':
            return int(self.regfile.get('R', idx))
        if type == 'P':
            return int(self.regfile.get('P', idx))
        if type == 'SP':
            return int(self.regfile.get('P', 8))
        if type == 'FP':
            return int(self.regfile.get('P', 9))
        if type in self._REGFILE_TYPES:
            return int(self.regfile.get(type, idx))
        if type == 'SA:':
            return int((self.sound.get_register('SA') >> 8) & 0xFF) if self.sound else 0
        if type == ':SA':
            return int(self.sound.get_register('SA') & 0xFF) if self.sound else 0
        if type == 'Rind': return self.memory.read_byte_fast(self.Rregisters[idx])
        if type == 'Pind': return self.memory.read_byte_fast(self.Pregisters[idx])
        if type == 'SPind': return self.memory.read_byte_fast(self.sp)
        if type == 'FPind': return self.memory.read_byte_fast(self.fp)
        if type == 'Vind': return self.memory.read_byte_fast(self.gfx.Vregisters[idx])
        if type == 'Ridx': return self.memory.read_byte_fast(self.Rregisters[idx])
        if type == 'Pidx': return self.memory.read_byte_fast(self.Pregisters[idx])
        if type == 'Vidx': return self.memory.read_byte_fast(self.gfx.Vregisters[idx])
        return 0

    def _set_operand_value(self, type, idx, value):
        if type == 'R':
            self.regfile.set('R', idx, value)
            return
        if type == 'P':
            self.regfile.set('P', idx, value)
            return
        if type == 'SP':
            self.regfile.set('P', 8, int(value) & 0xFFFF)
            return
        if type == 'FP':
            self.regfile.set('P', 9, int(value) & 0xFFFF)
            return
        if type in self._REGFILE_TYPES:
            try:
                self.regfile.set(type, idx, value)
            except Exception:
                pass
            return
        if type == 'SA:':
            if self.sound:
                current = self.sound.get_register('SA')
                new_sa = (current & 0x00FF) | ((int(value) & 0xFF) << 8)
                self.sound.update_registers(sa=new_sa)
            return
        if type == ':SA':
            if self.sound:
                current = self.sound.get_register('SA')
                new_sa = (current & 0xFF00) | (int(value) & 0xFF)
                self.sound.update_registers(sa=new_sa)
            return
        if type == 'Rind':
            self.write_byte(self.Rregisters[idx], int(value) & 0xFF)
            return
        if type == 'Pind':
            self.write_byte(self.Pregisters[idx], int(value) & 0xFF)
            return
        if type == 'SPind':
            self.write_byte(self.sp, int(value) & 0xFF)
            return
        if type == 'FPind':
            self.write_byte(self.fp, int(value) & 0xFF)
            return
        if type == 'Vind':
            self.write_byte(self.gfx.Vregisters[idx], int(value) & 0xFF)
            return
        if type == 'Ridx':
            self.write_byte(self.Rregisters[idx], int(value) & 0xFF)
            return
        if type == 'Pidx':
            self.write_byte(self.Pregisters[idx], int(value) & 0xFF)
            return
        if type == 'Vidx':
            self.write_byte(self.gfx.Vregisters[idx], int(value) & 0xFF)
            return

    def _set_flags_8bit(self, result, original_result=None):
        if original_result is None:
            original_result = result
        self.flags_obj.set_from_8bit(
            result & 0xFF,
            original_result=original_result,
            is_cmp=getattr(self, '_last_operation_was_cmp', False),
            last_operation_was_cmp=getattr(self, '_last_operation_was_cmp', False)
        )
        if getattr(self, '_last_operation_was_cmp', False):
            self._last_operation_was_cmp = False

    def _set_flags_16bit(self, result, original_result=None):
        if original_result is None:
            original_result = result
        self.flags_obj.set_from_16bit(
            result & 0xFFFF,
            original_result=original_result,
            is_cmp=getattr(self, '_last_operation_was_cmp', False),
            last_operation_was_cmp=getattr(self, '_last_operation_was_cmp', False)
        )
        if getattr(self, '_last_operation_was_cmp', False):
            self._last_operation_was_cmp = False

    def _set_overflow_flag_8bit(self, op1, op2, result, is_subtraction=False):
        self.flags_obj.set_overflow_8bit(op1, op2, result, is_subtraction)

    def _set_overflow_flag_16bit(self, op1, op2, result, is_subtraction=False):
        self.flags_obj.set_overflow_16bit(op1, op2, result, is_subtraction)

    # ---- BCD OPERATIONS ----

    def _is_valid_bcd(self, value):
        return ((value & 0x0F) <= 9) and (((value & 0xF0) >> 4) <= 9)

    def _bcd_to_binary(self, bcd_value):
        if not self._is_valid_bcd(bcd_value):
            return bcd_value
        low_nibble = bcd_value & 0x0F
        high_nibble = (bcd_value & 0xF0) >> 4
        return high_nibble * 10 + low_nibble

    def _binary_to_bcd(self, binary_value):
        if binary_value > 99:
            binary_value = binary_value % 100
        tens = binary_value // 10
        ones = binary_value % 10
        return (tens << 4) | ones

    def _bcd_add(self, val1, val2):
        bin1 = self._bcd_to_binary(val1)
        bin2 = self._bcd_to_binary(val2)
        result = bin1 + bin2 + (1 if self.bcd_carry_flag else 0)
        bcd_carry = result > 99
        if bcd_carry:
            result = result % 100
        bcd_result = self._binary_to_bcd(result)
        return bcd_result, bcd_carry

    def _bcd_sub(self, val1, val2):
        bin1 = self._bcd_to_binary(val1)
        bin2 = self._bcd_to_binary(val2)
        result = bin1 - bin2 - (1 if self.bcd_carry_flag else 0)
        bcd_borrow = result < 0
        if bcd_borrow:
            result = result + 100
        bcd_result = self._binary_to_bcd(result)
        return bcd_result, bcd_borrow

    def _set_flags_8bit_bcd(self, result, bcd_carry=False):
        self.flags_obj.set_from_bcd(result & 0xFF, bcd_carry)

    def bcd_add(self, val1, val2):
        result, carry = self._bcd_add(val1, val2)
        self._set_flags_8bit_bcd(result, carry)
        return result

    def bcd_subtract(self, val1, val2):
        result, borrow = self._bcd_sub(val1, val2)
        self._set_flags_8bit_bcd(result, borrow)
        return result

    def bcd_compare(self, val1, val2):
        result, borrow = self._bcd_sub(val1, val2)
        self._set_flags_8bit_bcd(result, borrow)
        return result

    def bcd_to_binary(self, bcd_value):
        return self._bcd_to_binary(bcd_value)

    def binary_to_bcd(self, binary_value):
        return self._binary_to_bcd(binary_value)

    # ---- INLINE FLAG CHECKS ----

    def _check_interrupts_enabled(self) -> bool:
        return self.flags_obj.check_I()

    def _check_carry_flag(self) -> bool:
        return self.flags_obj.check_C()

    def _check_zero_flag(self) -> bool:
        return self.flags_obj.check_Z()

    def _clear_hot_flags(self):
        self.flags_obj._bits &= ~((1 << self.flags_obj.I) |
                                  (1 << self.flags_obj.Z) |
                                  (1 << self.flags_obj.C))

    # ---- KEYBOARD ----

    def add_key_to_buffer(self, key_code):
        if self.keyboard_device is not None:
            self.keyboard_device.add_key(key_code)
            self.keyboard[0] = self.keyboard_device.data_register
            self.keyboard[1] = self.keyboard_device.status_register
            self.keyboard[3] = self.keyboard_device.buffer_count
            if self.intr_ctrl is None and self.interrupts[2] == 1:
                self.keyboard[1] |= 0x80
                self.has_pending_interrupt_sources = True
            return
        if len(self.key_buffer) < self.key_buffer_size:
            self.key_buffer.append(key_code & 0xFF)
            self.keyboard[3] = len(self.key_buffer)
            self.keyboard[0] = key_code & 0xFF
            self.keyboard[1] |= 0x01
            if len(self.key_buffer) >= self.key_buffer_size:
                self.keyboard[1] |= 0x02
            if self.interrupts[2] == 1:
                self.keyboard[1] |= 0x80
                self.has_pending_interrupt_sources = True

    def read_key_from_buffer(self):
        if self.keyboard_device is not None:
            key = self.keyboard_device.read_key()
            self.keyboard[0] = self.keyboard_device.data_register
            self.keyboard[1] = self.keyboard_device.status_register
            self.keyboard[3] = self.keyboard_device.buffer_count
            return key
        if self.key_buffer:
            key_code = self.key_buffer.pop(0)
            self.keyboard[3] = len(self.key_buffer)
            if self.key_buffer:
                self.keyboard[0] = self.key_buffer[0]
            else:
                self.keyboard[0] = 0
                self.keyboard[1] = self.keyboard[1] & 0xFE
            if len(self.key_buffer) < self.key_buffer_size:
                self.keyboard[1] = self.keyboard[1] & 0xFD
            return key_code
        else:
            self.keyboard[0] = 0
            self.keyboard[3] = 0
            self.keyboard[1] = self.keyboard[1] & 0xFE
            self.keyboard[1] = self.keyboard[1] & 0xFD
            return 0

    def clear_keyboard_buffer(self):
        if self.keyboard_device is not None:
            self.keyboard_device.clear_buffer()
        self.key_buffer = []
        self.keyboard[0] = 0
        self.keyboard[1] = 0
        self.keyboard[3] = 0

    def interrupt(self, interrupt_vector):
        if 0 <= interrupt_vector < 8:
            self._trigger_interrupt(interrupt_vector)

    def _trigger_interrupt(self, interrupt_vector):
        if self._check_interrupts_enabled():
            sp = int(self.Pregisters[8])
            if sp < 0x0124:
                raise RuntimeError(f"Stack overflow: SP=0x{sp:04X}")
            vector_address = 0x0100 + (interrupt_vector * 4)
            handler_address = self.memory.read_word(vector_address)
            flags_val = self.flags_obj.pack()
            self.Pregisters[8] = (int(self.Pregisters[8]) - 2) & 0xFFFF
            self.memory.write_word(self.Pregisters[8], flags_val)
            self.Pregisters[8] = (int(self.Pregisters[8]) - 2) & 0xFFFF
            self.memory.write_word(self.Pregisters[8], self.pc)
            self.flags_obj[5] = 0
            self.pc = handler_address

    def _check_pending_interrupts(self):
        if not self.has_pending_interrupt_sources:
            return False
        self.interrupt_check_counter += 1
        if self.interrupt_check_counter < self.interrupt_check_frequency:
            return False
        self.interrupt_check_counter = 0
        if not self._check_interrupts_enabled():
            return False
        current_state = (
            (self.interrupts[1] << 7) |
            (self.interrupts[2] << 6) |
            (self.interrupts[3] << 5) |
            (self.interrupts[4] << 4) |
            ((self.keyboard[1] & 0x80) >> 3) |
            ((0x80 if self.uart.pending_interrupt else 0) >> 4) |
            ((0x80 if self.mouse.pending_interrupt else 0) >> 5)
        )
        if current_state == self.last_interrupt_state and current_state == 0:
            self.has_pending_interrupt_sources = False
            return False
        self.last_interrupt_state = current_state
        if self.interrupts[2] == 1 and (self.keyboard[1] & 0x80):
            self.keyboard[1] &= 0x7F
            self._refresh_pending_interrupt_sources()
            self._trigger_interrupt(2)
            return True
        if self.interrupts[1] == 1 and self.uart.pending_interrupt:
            self.uart.clear_interrupt()
            self._refresh_pending_interrupt_sources()
            self._trigger_interrupt(1)
            return True
        if self.interrupts[3] == 1 and self.mouse.pending_interrupt:
            self.mouse.clear_interrupt()
            self._refresh_pending_interrupt_sources()
            self._trigger_interrupt(3)
            return True
        if self.interrupts[4] == 1:
            pass
        self._refresh_pending_interrupt_sources()
        return False

    def _check_hw_breakpoints(self):
        if not self.has_hw_breakpoints and self.flags_obj[0] != 1:
            return
        any_enabled = False
        for i in range(4):
            if self.hw_breakpoint_enabled[i]:
                any_enabled = True
                if self.pc == self.hw_breakpoints[i]:
                    self.flags_obj[3] = 1
                    self._trigger_interrupt(7)
                    return
        if not any_enabled:
            self.has_hw_breakpoints = False
        if self.flags_obj[0] == 1:
            self.flags_obj[3] = 1
            self._trigger_interrupt(7)

    def _build_register_lookup_table(self):
        lookup = {}
        lookup[0xC2] = (0, 'BANK')
        lookup[0xC3] = (0, 'C0')
        lookup[0xC4] = (0, 'C1')
        lookup[0xC5] = (0, 'MX')
        lookup[0xC6] = (0, 'MY')
        lookup[0xC7] = (0, 'MB')
        lookup[0xDD] = (0, 'SA')
        lookup[0xDE] = (0, 'SF')
        lookup[0xDF] = (0, 'SV')
        lookup[0xE0] = (0, 'SW')
        for i in range(10):
            lookup[0xC9 + i] = (i, 'P_high')
            lookup[0xD3 + i] = (i, 'P_low')
        lookup[0xE1] = (2, 'V')
        lookup[0xE2] = (0, 'VL')
        lookup[0xC8] = (3, 'V')
        lookup[0xE3] = (0, 'TT')
        lookup[0xE4] = (1, 'TM')
        lookup[0xE5] = (2, 'TC')
        lookup[0xE6] = (3, 'TS')
        for i in range(10):
            lookup[0xE7 + i] = (i, 'R')
        for i in range(10):
            lookup[0xF1 + i] = (i, 'P')
        lookup[0xFB] = (8, 'P')
        lookup[0xFC] = (9, 'P')
        lookup[0xFD] = (0, 'V')
        lookup[0xFE] = (1, 'V')
        return lookup

    def reg_index(self, reg_code):
        try:
            return self._register_lookup[reg_code]
        except KeyError:
            if reg_code == 0x00:
                return 0, 'R'
            raise Exception(f"Unknown register code: {reg_code:02X}")

    def fetch(self, bytes=1):
        if bytes == 1:
            data = self.memory.read(self.pc, 1)
            self.pc = (self.pc + 1) & 0xFFFF
            return data[0]
        elif bytes == 2:
            data = self.memory.read(self.pc, 2)
            self.pc = (self.pc + 2) & 0xFFFF
            return (int(data[0]) << 8) | int(data[1])
        else:
            data = self.memory.read(self.pc, bytes)
            self.pc = (self.pc + bytes) & 0xFFFF
            return [int(b) for b in data]

    def fetch_byte(self):
        if self.profiling_enabled:
            self.profile_data['memory_accesses'] += 1
        value = self.memory.read_byte_fast(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        return int(value)

    def fetch_word(self):
        high = self.fetch_byte()
        low = self.fetch_byte()
        return (int(high) << 8) | int(low)

    def fetch_bytes(self, count):
        result = [self.memory.read_byte_fast((self.pc + i) & 0xFFFF) for i in range(count)]
        self.pc = (self.pc + count) & 0xFFFF
        return result

    def write_memory(self, address, value, bytes=1):
        self.memory.write(address, value, bytes)

    def write_byte(self, address, value):
        self.memory.write_byte_fast(address, value)

    def write_word(self, address, value):
        self.memory.write_word_fast(address, value)

    def invalidate_prefetch(self):
        pass

    # ---- PREFIXED OPERAND METHODS ----

    def fetch_operand_by_mode(self, mode_bits):
        if mode_bits == 0:
            reg_code = self.fetch_byte()
            idx, typ = self.reg_index(reg_code)
            return self._get_operand_value(typ, idx)
        elif mode_bits == 1:
            return self.fetch_byte()
        elif mode_bits == 2:
            return self.fetch_word()
        elif mode_bits == 3:
            indexed = (self._current_mode_byte & (1 << 6)) != 0
            direct = (self._current_mode_byte & (1 << 7)) != 0
            if direct and not indexed:
                addr = self.fetch_word()
                return self.memory.read_word(addr)
            elif not direct and not indexed:
                reg_code = self.fetch_byte()
                idx, typ = self.reg_index(reg_code)
                if typ == 'P':
                    addr = self.Pregisters[idx]
                elif typ == 'R':
                    addr = self.Rregisters[idx]
                else:
                    raise Exception(f"Invalid register type {typ} for indirect addressing")
                return self.memory.read_word(addr & 0xFFFF)
            elif not direct and indexed:
                reg_code = self.fetch_byte()
                index = self.fetch_byte()
                idx, typ = self.reg_index(reg_code)
                if typ == 'P':
                    base_addr = self.Pregisters[idx]
                elif typ == 'R':
                    base_addr = self.Rregisters[idx]
                else:
                    raise Exception(f"Invalid register type {typ} for indexed addressing")
                if idx in [8, 9]:
                    signed_offset = index if index < 128 else index - 256
                    addr = (base_addr + signed_offset) & 0xFFFF
                else:
                    addr = (base_addr + index) & 0xFFFF
                return self.memory.read_word(addr)
            elif direct and indexed:
                addr = self.fetch_word()
                index = self.fetch_byte()
                final_addr = (addr + index) & 0xFFFF
                return self.memory.read_word(final_addr)
        else:
            raise Exception(f"Invalid mode bits: {mode_bits}")

    def parse_operands(self, num_operands):
        if self.profiling_enabled:
            self.profile_data['operand_parses'] = self.profile_data.get('operand_parses', 0) + 1
        operands = []
        for i in range(num_operands):
            mode_bits = (self._current_mode_byte >> (i * 2)) & 0x3
            operand = {'mode': mode_bits}
            if mode_bits == 0:
                reg_code = self.fetch_byte()
                idx, typ = self.reg_index(reg_code)
                operand['type'] = 'register'
                operand['reg_type'] = typ
                operand['reg_idx'] = idx
            elif mode_bits == 1:
                operand['type'] = 'immediate'
                operand['value'] = self.fetch_byte()
                operand['size'] = 8
            elif mode_bits == 2:
                operand['type'] = 'immediate'
                operand['value'] = self.fetch_word()
                operand['size'] = 16
            elif mode_bits == 3:
                indexed = (self._current_mode_byte & (1 << 6)) != 0
                direct = (self._current_mode_byte & (1 << 7)) != 0
                operand['type'] = 'memory'
                operand['indexed'] = indexed
                operand['direct'] = direct
                if direct and not indexed:
                    operand['address'] = self.fetch_word()
                elif not direct and not indexed:
                    reg_code = self.fetch_byte()
                    idx, typ = self.reg_index(reg_code)
                    if typ not in ['P', 'R']:
                        raise Exception(f"Invalid register type {typ} for indirect addressing")
                    operand['indirect'] = True
                    operand['reg_type'] = typ
                    operand['reg_idx'] = idx
                elif not direct and indexed:
                    reg_code = self.fetch_byte()
                    index = self.fetch_byte()
                    idx, typ = self.reg_index(reg_code)
                    if typ not in ['P', 'R']:
                        raise Exception(f"Invalid register type {typ} for indexed addressing")
                    operand['indexed'] = True
                    operand['reg_type'] = typ
                    operand['reg_idx'] = idx
                    operand['index'] = index
                elif direct and indexed:
                    addr = self.fetch_word()
                    index = self.fetch_byte()
                    operand['address'] = (addr + index) & 0xFFFF
                    operand['index'] = index
            operands.append(operand)
        return operands

    def get_operand_value(self, operand, dest_operand=None):
        if self.profiling_enabled:
            self.profile_data['operand_values'] = self.profile_data.get('operand_values', 0) + 1
        if operand['type'] == 'register':
            return self._get_operand_value(operand['reg_type'], operand['reg_idx'])
        elif operand['type'] == 'immediate':
            return operand['value']
        elif operand['type'] == 'memory':
            if 'address' in operand:
                address = operand['address']
            elif 'indirect' in operand:
                address = self.Pregisters[operand['reg_idx']] if operand['reg_type'] == 'P' else self.Rregisters[operand['reg_idx']]
            elif 'indexed' in operand:
                base = self.Pregisters[operand['reg_idx']] if operand['reg_type'] == 'P' else self.Rregisters[operand['reg_idx']]
                address = (base + operand['index']) & 0xFFFF
            else:
                raise Exception("Invalid memory operand")
            if dest_operand and dest_operand['type'] == 'register':
                if dest_operand['reg_type'] == 'R':
                    return self.memory.read_byte(address)
                else:
                    return self.memory.read_word(address)
            else:
                return self.memory.read_word(address)
        else:
            raise Exception(f"Unknown operand type: {operand['type']}")

    def set_operand_value(self, operand, value, source_operand=None):
        if operand['type'] == 'register':
            self._set_operand_value(operand['reg_type'], operand['reg_idx'], value)
        elif operand['type'] == 'memory':
            if 'address' in operand:
                address = operand['address']
            elif 'indirect' in operand:
                address = self.Pregisters[operand['reg_idx']] if operand['reg_type'] == 'P' else self.Rregisters[operand['reg_idx']]
            elif 'indexed' in operand:
                base = self.Pregisters[operand['reg_idx']] if operand['reg_type'] == 'P' else self.Rregisters[operand['reg_idx']]
                address = (base + operand['index']) & 0xFFFF
            else:
                raise Exception("Invalid memory operand")
            if source_operand and source_operand['type'] == 'immediate':
                if source_operand.get('size') == 8:
                    self.write_byte(address, value)
                else:
                    self.write_memory(address, value, bytes=2)
            elif source_operand and source_operand['type'] == 'register':
                if source_operand['reg_type'] == 'R':
                    self.write_byte(address, value)
                else:
                    self.write_memory(address, value, bytes=2)
            else:
                self.write_memory(address, value, bytes=2)
        else:
            raise Exception(f"Cannot set value for operand type: {operand['type']}")

    def get_register_value(self, reg_num):
        if 0 <= reg_num <= 9:
            return self.Rregisters[reg_num]
        elif 10 <= reg_num <= 19:
            return self.Pregisters[reg_num - 10]
        elif reg_num == 20:
            return self.gfx.Vregisters[0]
        elif reg_num == 21:
            return self.gfx.Vregisters[1]
        elif reg_num == 22:
            return self.gfx.Vregisters[3]
        else:
            raise Exception(f"Invalid register number: {reg_num}")

    def set_register_value(self, reg_num, value):
        if 0 <= reg_num <= 9:
            self.Rregisters[reg_num] = value & 0xFF
        elif 10 <= reg_num <= 19:
            self.Pregisters[reg_num - 10] = value & 0xFFFF
        elif reg_num == 20:
            self.gfx.Vregisters[0] = value & 0xFF
        elif reg_num == 21:
            self.gfx.Vregisters[1] = value & 0xFF
        elif reg_num == 22:
            self.gfx.Vregisters[3] = value & 0xFF
        else:
            raise Exception(f"Invalid register number: {reg_num}")

    def get_operand_address(self, mode_bits):
        if mode_bits == 0:
            raise Exception("Cannot get address for register direct mode")
        elif mode_bits == 1:
            raise Exception("Cannot get address for immediate 8-bit mode")
        elif mode_bits == 2:
            raise Exception("Cannot get address for immediate 16-bit mode")
        elif mode_bits == 3:
            indexed = (self._current_mode_byte & (1 << 6)) != 0
            direct = (self._current_mode_byte & (1 << 7)) != 0
            if direct and not indexed:
                return self.fetch_word()
            elif not direct and not indexed:
                reg_code = self.fetch_byte()
                idx, typ = self.reg_index(reg_code)
                if typ == 'P':
                    return self.Pregisters[idx] & 0xFFFF
                elif typ == 'R':
                    return self.Rregisters[idx] & 0xFFFF
                else:
                    raise Exception(f"Invalid register type {typ} for indirect addressing")
            elif not direct and indexed:
                reg_code = self.fetch_byte()
                index = self.fetch_byte()
                idx, typ = self.reg_index(reg_code)
                if typ == 'P':
                    base_addr = self.Pregisters[idx]
                elif typ == 'R':
                    base_addr = self.Rregisters[idx]
                else:
                    raise Exception(f"Invalid register type {typ} for indexed addressing")
                if idx in [8, 9]:
                    signed_offset = index if index < 128 else index - 256
                    return (base_addr + signed_offset) & 0xFFFF
                else:
                    return (base_addr + index) & 0xFFFF
            elif direct and indexed:
                addr = self.fetch_word()
                index = self.fetch_byte()
                return (addr + index) & 0xFFFF
        else:
            raise Exception(f"Invalid mode bits: {mode_bits}")

    def step(self):
        if self.halted:
            return
        self.cycles += 1
        if self.timer_device is not None:
            self.timer_device._on_tick(self.cycles)
        if self.uart.host_bridge is not None and (self.cycles & 0x3F) == 0:
            self.uart.poll_host_bridge()
        pc = self.pc
        opcode = self.memory.fetch_opcode(pc)
        self.pc = (pc + 1) & 0xFFFF
        self._execute_instruction(opcode)
        if self.intr_ctrl is not None:
            self.intr_ctrl.check()
        if self.has_pending_interrupt_sources:
            self._check_pending_interrupts()
        elif self._has_enabled_async_interrupt_sources():
            self._refresh_pending_interrupt_sources()
            if self.has_pending_interrupt_sources:
                self._check_pending_interrupts()

    def _execute_instruction(self, opcode):
        """Execute a single instruction — optimized dispatch.
        
        Uses _noop_opcode_set to skip the per-instruction num_operands check
        while keeping instruction_table as the single source of truth.
        """
        if self.profiling_enabled:
            self.profile_data['instructions_executed'] += 1
            self.profile_data['opcode_counts'][opcode] = self.profile_data['opcode_counts'].get(opcode, 0) + 1

        instruction = self.instruction_table.get(opcode)
        if instruction is None:
            raise Exception(f"Unknown opcode: {opcode:02X}")

        if opcode in self._noop_opcode_set:
            self._current_mode_byte = 0
            self.operands = []
            instruction.execute(self)
            if self.has_hw_breakpoints or self.flags_obj.trap_flag:
                self._check_hw_breakpoints()
            return

        mode_byte = self.memory.read_byte_fast(self.pc)
        self._current_mode_byte = mode_byte
        self.pc = (self.pc + 1) & 0xFFFF

        if instruction.handler is not None:
            self.operands, byte_length = decode_operands(
                self.memory, self.pc, mode_byte, instruction.num_operands,
                self.regfile.decode_register_code
            )
            self.pc = (self.pc + byte_length) & 0xFFFF
        else:
            self.operands = []

        instruction.execute(self)
        if self.has_hw_breakpoints or self.flags_obj.trap_flag:
            self._check_hw_breakpoints()
        if instruction.handler is not None:
            release_operands(self.operands)

    def execute(self, opcode):
        self._execute_instruction(opcode)


if __name__ == "__main__":
    print("Nova-16")