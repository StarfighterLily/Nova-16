#!/usr/bin/env python3
"""
NoBASIC Interpreter VM

Interprets NoBASIC source directly from AST while using Nova-16 runtime components
(CPU, memory, graphics, keyboard, and sound) as the hardware backend.
"""

from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pygame


# Add NoBASIC compiler path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "compiler"))

from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer
from compiler.utils.error import CompilerError
from compiler.parser.ast import (
    Program,
    Statement,
    Expression,
    AssignmentStmt,
    ExpressionStmt,
    IfStmt,
    ForStmt,
    WhileStmt,
    RepeatStmt,
    GotoStmt,
    LabelStmt,
    StructDeclarationStmt,
    VarDeclarationStmt,
    FunctionDefStmt,
    ReturnStmt,
    ClrDrawStmt,
    PxlOnStmt,
    PxlOffStmt,
    LineStmt,
    CircleStmt,
    TextStmt,
    SetLayerStmt,
    SpriteOnStmt,
    SpriteOffStmt,
    PlayToneStmt,
    PlayWaveStmt,
    StopSoundStmt,
    SetChannelStmt,
    GetKeyStmt,
    SerOutStmt,
    SerInStmt,
    SerStatStmt,
    SerCtrlStmt,
    InputStmt,
    DispStmt,
    PauseStmt,
    FunctionCallStmt,
    AsmBlockStmt,
    LiteralExpr,
    VariableExpr,
    ListAccessExpr,
    MatrixAccessExpr,
    MemberAccessExpr,
    BinaryExpr,
    UnaryExpr,
    FunctionCallExpr,
    GroupingExpr,
)


# Add Nova-16 emulator imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import nova_cpu as cpu
from nova.memory import Memory as ram
import nova_gfx as gpu
import nova_sound as sound
import nova_keyboard as keyboard


class VMRuntimeError(RuntimeError):
    """Raised for runtime VM errors."""


class GotoSignal(Exception):
    """Internal control-flow signal for GOTO."""

    def __init__(self, label: str):
        super().__init__(label)
        self.label = label


class ReturnSignal(Exception):
    """Internal control-flow signal for RETURN."""

    def __init__(self, value: Any):
        super().__init__("RETURN")
        self.value = value


@dataclass
class NoBASICVMConfig:
    """Runtime configuration for the VM."""

    enable_sound: bool = True
    max_steps: int = 1_000_000
    verbose: bool = False
    skip_semantic: bool = False
    strict_asm: bool = False


class SilentSound:
    """No-op sound backend used when VM sound is disabled."""

    max_channels = 0
    sample_rate = 0

    def set_memory_reference(self, memory: Any) -> None:
        return

    def update_registers(self, **kwargs: Any) -> None:
        return

    def get_register(self, register_name: str) -> int:
        return 0

    def splay(self, channel: Optional[int] = None) -> bool:
        return False

    def sstop(self, channel: Optional[int] = None) -> bool:
        return True

    def cleanup(self) -> None:
        return


class NoBASICVM:
    """NoBASIC AST interpreter backed by Nova-16 components."""

    def __init__(self, config: Optional[NoBASICVMConfig] = None):
        self.config = config or NoBASICVMConfig()

        self.lexer = Lexer()
        self.parser = Parser()
        self.analyzer = SemanticAnalyzer()

        self.proc, self.mem, self.gfx, self.kbd, self.snd = self._initialize_system(
            self.config.enable_sound
        )

        self.program: Optional[Program] = None
        self.labels: Dict[str, int] = {}
        self.functions: Dict[str, FunctionDefStmt] = {}
        self.struct_defs: Dict[str, List[str]] = {}
        self.frames: List[Dict[str, Any]] = [dict()]
        self.current_channel: int = 0
        self.steps: int = 0
        self._asm_warning_emitted = False

        self._set_var("ans", 0)

    @staticmethod
    def _initialize_system(enable_sound: bool = True):
        """Initialize Nova-16 system components."""
        mem = ram.Memory()
        gfx = gpu.GFX()
        kbd = keyboard.NovaKeyboard()
        snd = sound.NovaSound() if enable_sound else SilentSound()

        proc = cpu.CPU(mem, gfx, kbd, snd)
        kbd.cpu = proc
        mem.gfx_system = gfx

        if snd:
            snd.set_memory_reference(mem)

        return proc, mem, gfx, kbd, snd

    def load_source(self, source: str, filename: str = "<stdin>") -> Program:
        """Lex/parse/analyze source and prepare runtime tables."""
        tokens = self.lexer.tokenize(source, filename)
        program = self.parser.parse(tokens, filename)

        if not self.config.skip_semantic:
            self.analyzer.analyze(program, filename)

        self.program = program
        self._index_program(program)
        return program

    def load_file(self, source_file: str) -> Program:
        """Load NoBASIC source from file and prepare for execution."""
        with open(source_file, "r", encoding="utf-8") as handle:
            source = handle.read()
        return self.load_source(source, source_file)

    def run(self) -> None:
        """Execute the loaded program."""
        if self.program is None:
            raise VMRuntimeError("No program loaded")

        statements = self.program.statements
        pc = 0

        while pc < len(statements):
            self._tick()
            stmt = statements[pc]

            try:
                self._execute_statement(stmt)
                pc += 1
            except GotoSignal as signal:
                label_key = signal.label.lower()
                if label_key not in self.labels:
                    raise VMRuntimeError(f"Undefined label '{signal.label}'") from None
                pc = self.labels[label_key]
            except ReturnSignal:
                raise VMRuntimeError("RETURN used outside of function") from None

    def run_file(self, source_file: str) -> None:
        """Convenience method: load then execute file."""
        self.load_file(source_file)
        self.run()

    def _index_program(self, program: Program) -> None:
        """Build indices for labels and function declarations."""
        self.labels.clear()
        self.functions.clear()

        for index, statement in enumerate(program.statements):
            if isinstance(statement, LabelStmt):
                self.labels[statement.label.lower()] = index
            elif isinstance(statement, FunctionDefStmt):
                self.functions[statement.name.lower()] = statement

    def _tick(self) -> None:
        """Advance interpreter step count and enforce max-steps guard."""
        self.steps += 1
        if self.steps > self.config.max_steps:
            raise VMRuntimeError(
                f"Maximum instruction steps exceeded ({self.config.max_steps})"
            )

    def _execute_block(self, statements: List[Statement]) -> None:
        """Execute a statement block."""
        for statement in statements:
            self._tick()
            self._execute_statement(statement)

    def _execute_statement(self, statement: Statement) -> None:
        """Execute a single AST statement node."""
        if isinstance(statement, ClrDrawStmt):
            self.gfx.clear_layer()
            return

        if isinstance(statement, PxlOnStmt):
            x = self._to_int(self._eval_expr(statement.x)) & 0xFF
            y = self._to_int(self._eval_expr(statement.y)) & 0xFF
            color = self._to_int(self._eval_expr(statement.color)) & 0xFF
            self.gfx.Vregisters[2] = 0
            self.gfx.Vregisters[0] = x
            self.gfx.Vregisters[1] = y
            self.gfx.set_screen_val(color)
            return

        if isinstance(statement, PxlOffStmt):
            x = self._to_int(self._eval_expr(statement.x)) & 0xFF
            y = self._to_int(self._eval_expr(statement.y)) & 0xFF
            self.gfx.Vregisters[2] = 0
            self.gfx.Vregisters[0] = x
            self.gfx.Vregisters[1] = y
            self.gfx.set_screen_val(0)
            return

        if isinstance(statement, LineStmt):
            self.gfx.draw_line(
                self._to_int(self._eval_expr(statement.x1)),
                self._to_int(self._eval_expr(statement.y1)),
                self._to_int(self._eval_expr(statement.x2)),
                self._to_int(self._eval_expr(statement.y2)),
                self._to_int(self._eval_expr(statement.color)) & 0xFF,
            )
            return

        if isinstance(statement, CircleStmt):
            self.gfx.draw_circle(
                self._to_int(self._eval_expr(statement.x)),
                self._to_int(self._eval_expr(statement.y)),
                abs(self._to_int(self._eval_expr(statement.radius))),
                self._to_int(self._eval_expr(statement.color)) & 0xFF,
                filled=False,
            )
            return

        if isinstance(statement, TextStmt):
            x = self._to_int(self._eval_expr(statement.x))
            y = self._to_int(self._eval_expr(statement.y))
            text = str(self._eval_expr(statement.text))
            color = self._to_int(self._eval_expr(statement.color)) & 0xFF
            self.gfx.draw_string_to_screen(text, x, y, color)
            return

        if isinstance(statement, SetLayerStmt):
            layer = self._to_int(self._eval_expr(statement.layer))
            self.gfx.set_current_layer(layer % 9)
            return

        if isinstance(statement, SpriteOnStmt):
            sprite_id = self._to_int(self._eval_expr(statement.sprite_id)) & 0x0F
            x = self._to_int(self._eval_expr(statement.x)) & 0xFF
            y = self._to_int(self._eval_expr(statement.y)) & 0xFF
            self._set_sprite_enabled(sprite_id, True, x, y)
            return

        if isinstance(statement, SpriteOffStmt):
            sprite_id = self._to_int(self._eval_expr(statement.sprite_id)) & 0x0F
            self._set_sprite_enabled(sprite_id, False, 0, 0)
            return

        if isinstance(statement, PlayToneStmt):
            frequency = self._to_int(self._eval_expr(statement.frequency))
            duration_ms = max(0, self._to_int(self._eval_expr(statement.duration)))
            volume = self._to_int(self._eval_expr(statement.volume)) & 0xFF
            self._play_tone(frequency, duration_ms, volume)
            return

        if isinstance(statement, PlayWaveStmt):
            waveform = self._to_int(self._eval_expr(statement.waveform)) & 0x07
            frequency = self._to_int(self._eval_expr(statement.frequency))
            volume = self._to_int(self._eval_expr(statement.volume)) & 0xFF
            self._play_wave(waveform, frequency, volume)
            return

        if isinstance(statement, StopSoundStmt):
            if self.snd:
                self.snd.sstop()
            return

        if isinstance(statement, SetChannelStmt):
            self.current_channel = self._to_int(self._eval_expr(statement.channel)) & 0x07
            return

        if isinstance(statement, GetKeyStmt):
            key = self._read_key(blocking=True)
            self._set_var("ans", key)
            return

        if isinstance(statement, SerOutStmt):
            value = self._to_int(self._eval_expr(statement.value)) & 0xFF
            self.proc.uart.write_data(value)
            return

        if isinstance(statement, SerInStmt):
            byte = self.proc.uart.read_data() & 0xFF
            self._set_var(statement.variable, byte)
            self._set_var("ans", byte)
            return

        if isinstance(statement, SerStatStmt):
            status = self.proc.uart.read_status_flags() & 0xFF
            self._set_var(statement.variable, status)
            self._set_var("ans", status)
            return

        if isinstance(statement, SerCtrlStmt):
            value = self._to_int(self._eval_expr(statement.value)) & 0xFF
            self.proc.uart.write_control(value)
            return

        if isinstance(statement, InputStmt):
            prompt = "? "
            if statement.prompt is not None:
                prompt = str(self._eval_expr(statement.prompt))
                if not prompt.endswith(" "):
                    prompt += " "
            raw_value = input(prompt)
            parsed: Any
            try:
                parsed = int(raw_value, 0)
            except ValueError:
                try:
                    parsed = float(raw_value)
                except ValueError:
                    parsed = raw_value
            self._set_var(statement.variable, parsed)
            self._set_var("ans", parsed)
            return

        if isinstance(statement, DispStmt):
            value = self._eval_expr(statement.text)
            print(value)
            self._set_var("ans", value)
            return

        if isinstance(statement, PauseStmt):
            input("[Pause] Press Enter to continue...")
            return

        if isinstance(statement, AssignmentStmt):
            value = self._eval_expr(statement.expression)
            self._assign_target(statement.variable, value)
            self._set_var("ans", value)
            return

        if isinstance(statement, ExpressionStmt):
            value = self._eval_expr(statement.expression)
            self._set_var("ans", value)
            return

        if isinstance(statement, IfStmt):
            if self._truthy(self._eval_expr(statement.condition)):
                self._execute_block(statement.then_branch)
            elif statement.else_branch is not None:
                self._execute_block(statement.else_branch)
            return

        if isinstance(statement, ForStmt):
            variable_name = statement.variable
            start_value = self._to_int(self._eval_expr(statement.start))
            end_value = self._to_int(self._eval_expr(statement.end))
            step_value = (
                self._to_int(self._eval_expr(statement.step)) if statement.step is not None else 1
            )
            if step_value == 0:
                raise VMRuntimeError("FOR step cannot be 0")

            self._set_var(variable_name, start_value)
            while True:
                current_value = self._to_int(self._get_var(variable_name))
                if step_value > 0 and current_value > end_value:
                    break
                if step_value < 0 and current_value < end_value:
                    break

                self._execute_block(statement.body)
                self._set_var(variable_name, current_value + step_value)
            return

        if isinstance(statement, WhileStmt):
            while self._truthy(self._eval_expr(statement.condition)):
                self._execute_block(statement.body)
            return

        if isinstance(statement, RepeatStmt):
            while True:
                self._execute_block(statement.body)
                if self._truthy(self._eval_expr(statement.condition)):
                    break
            return

        if isinstance(statement, GotoStmt):
            raise GotoSignal(statement.label)

        if isinstance(statement, LabelStmt):
            return

        if isinstance(statement, StructDeclarationStmt):
            self.struct_defs[statement.name.lower()] = [field.lower() for field in statement.fields]
            return

        if isinstance(statement, VarDeclarationStmt):
            for variable in statement.variables:
                if not self._has_var(variable):
                    self._set_var(variable, 0)
            return

        if isinstance(statement, FunctionDefStmt):
            self.functions[statement.name.lower()] = statement
            return

        if isinstance(statement, FunctionCallStmt):
            value = self._eval_expr(statement.function_call)
            self._set_var("ans", value)
            return

        if isinstance(statement, ReturnStmt):
            value = self._eval_expr(statement.value) if statement.value is not None else None
            raise ReturnSignal(value)

        if isinstance(statement, AsmBlockStmt):
            if self.config.strict_asm:
                raise VMRuntimeError(
                    "Inline Asm blocks are not supported by the interpreter VM. "
                    "Compile to assembly for Asm execution."
                )
            if not self._asm_warning_emitted:
                print(
                    "[NoBASIC VM] Warning: skipping inline Asm block in interpreter mode."
                )
                self._asm_warning_emitted = True
            return

        raise VMRuntimeError(f"Unsupported statement type: {type(statement).__name__}")

    def _eval_expr(self, expression: Expression) -> Any:
        """Evaluate a NoBASIC expression."""
        if isinstance(expression, LiteralExpr):
            return expression.value

        if isinstance(expression, VariableExpr):
            return self._get_var(expression.name)

        if isinstance(expression, GroupingExpr):
            return self._eval_expr(expression.expression)

        if isinstance(expression, ListAccessExpr):
            list_name = expression.list_name
            index = self._to_int(self._eval_expr(expression.index))
            if index <= 0:
                raise VMRuntimeError("List indices are 1-based and must be >= 1")
            value = self._get_var(list_name)
            if not isinstance(value, list):
                value = []
                self._set_var(list_name, value)
            while len(value) < index:
                value.append(0)
            return value[index - 1]

        if isinstance(expression, MatrixAccessExpr):
            matrix_name = expression.matrix_name
            row = self._to_int(self._eval_expr(expression.row))
            col = self._to_int(self._eval_expr(expression.col))
            if row <= 0 or col <= 0:
                raise VMRuntimeError("Matrix indices are 1-based and must be >= 1")
            value = self._get_var(matrix_name)
            if not isinstance(value, list):
                value = []
                self._set_var(matrix_name, value)
            while len(value) < row:
                value.append([])
            while len(value[row - 1]) < col:
                value[row - 1].append(0)
            return value[row - 1][col - 1]

        if isinstance(expression, MemberAccessExpr):
            member = expression.member.lower()
            if isinstance(expression.object, VariableExpr):
                var_name = expression.object.name
                if not self._has_var(var_name):
                    struct_name = self._infer_struct_type(var_name, member)
                    if struct_name is None:
                        raise VMRuntimeError(f"Cannot infer struct type for variable '{var_name}'")
                    self._set_var(var_name, self._create_struct_instance(struct_name))
                obj = self._get_var(var_name)
            else:
                obj = self._eval_expr(expression.object)
            if not isinstance(obj, dict):
                raise VMRuntimeError("Member access requires a struct/dict value")
            struct_name = obj.get("__struct__")
            if struct_name is not None:
                fields = self.struct_defs.get(struct_name, [])
                if member not in fields:
                    raise VMRuntimeError(f"Struct '{struct_name}' has no field '{member}'")
            if member not in obj:
                obj[member] = 0
            return obj[member]

        if isinstance(expression, UnaryExpr):
            operator = expression.operator.lower()

            if operator in ("++", "--"):
                delta = 1 if operator == "++" else -1
                if expression.is_post:
                    old_value = self._to_int(self._eval_target(expression.expression))
                    self._assign_target(expression.expression, old_value + delta)
                    return old_value
                new_value = self._to_int(self._eval_target(expression.expression)) + delta
                self._assign_target(expression.expression, new_value)
                return new_value

            value = self._eval_expr(expression.expression)
            if operator == "-":
                return -self._to_number(value)
            if operator == "not":
                return 0 if self._truthy(value) else 1
            raise VMRuntimeError(f"Unsupported unary operator '{expression.operator}'")

        if isinstance(expression, BinaryExpr):
            left = self._eval_expr(expression.left)
            right = self._eval_expr(expression.right)
            op = expression.operator.lower()

            if op == "+":
                if isinstance(left, str) or isinstance(right, str):
                    return f"{left}{right}"
                return self._to_number(left) + self._to_number(right)
            if op == "-":
                return self._to_number(left) - self._to_number(right)
            if op == "*":
                return self._to_number(left) * self._to_number(right)
            if op == "/":
                denominator = self._to_number(right)
                if denominator == 0:
                    raise VMRuntimeError("Division by zero")
                return self._to_number(left) / denominator
            if op == "^":
                return self._to_number(left) ** self._to_number(right)

            if op == "=":
                return 1 if left == right else 0
            if op == "<>":
                return 1 if left != right else 0
            if op == "<":
                return 1 if left < right else 0
            if op == "<=":
                return 1 if left <= right else 0
            if op == ">":
                return 1 if left > right else 0
            if op == ">=":
                return 1 if left >= right else 0

            if op == "and":
                return 1 if self._truthy(left) and self._truthy(right) else 0
            if op == "or":
                return 1 if self._truthy(left) or self._truthy(right) else 0

            if op == "&":
                return self._to_int(left) & self._to_int(right)
            if op == "|":
                return self._to_int(left) | self._to_int(right)
            if op == "<<":
                return self._to_int(left) << self._to_int(right)
            if op == ">>":
                return self._to_int(left) >> self._to_int(right)

            raise VMRuntimeError(f"Unsupported binary operator '{expression.operator}'")

        if isinstance(expression, FunctionCallExpr):
            arguments = [self._eval_expr(arg) for arg in expression.arguments]
            return self._call_function(expression.name, arguments)

        raise VMRuntimeError(f"Unsupported expression type: {type(expression).__name__}")

    def _eval_target(self, expression: Expression) -> Any:
        """Evaluate current target value for assignment-capable expressions."""
        if isinstance(expression, (VariableExpr, ListAccessExpr, MatrixAccessExpr, MemberAccessExpr)):
            return self._eval_expr(expression)
        raise VMRuntimeError("Expression is not assignable")

    def _assign_target(self, target: Expression, value: Any) -> None:
        """Assign value to variable/list/matrix/member target."""
        if isinstance(target, VariableExpr):
            self._set_var(target.name, value)
            return

        if isinstance(target, ListAccessExpr):
            list_name = target.list_name
            index = self._to_int(self._eval_expr(target.index))
            if index <= 0:
                raise VMRuntimeError("List indices are 1-based and must be >= 1")
            current = self._get_var(list_name)
            if not isinstance(current, list):
                current = []
                self._set_var(list_name, current)
            while len(current) < index:
                current.append(0)
            current[index - 1] = value
            return

        if isinstance(target, MatrixAccessExpr):
            matrix_name = target.matrix_name
            row = self._to_int(self._eval_expr(target.row))
            col = self._to_int(self._eval_expr(target.col))
            if row <= 0 or col <= 0:
                raise VMRuntimeError("Matrix indices are 1-based and must be >= 1")
            matrix = self._get_var(matrix_name)
            if not isinstance(matrix, list):
                matrix = []
                self._set_var(matrix_name, matrix)
            while len(matrix) < row:
                matrix.append([])
            while len(matrix[row - 1]) < col:
                matrix[row - 1].append(0)
            matrix[row - 1][col - 1] = value
            return

        if isinstance(target, MemberAccessExpr):
            member = target.member.lower()
            if isinstance(target.object, VariableExpr):
                var_name = target.object.name
                if not self._has_var(var_name):
                    struct_name = self._infer_struct_type(var_name, member)
                    if struct_name is None:
                        raise VMRuntimeError(f"Cannot infer struct type for variable '{var_name}'")
                    self._set_var(var_name, self._create_struct_instance(struct_name))
                obj = self._get_var(var_name)
            else:
                obj = self._eval_expr(target.object)
            if not isinstance(obj, dict):
                raise VMRuntimeError("Member assignment requires a struct/dict value")
            struct_name = obj.get("__struct__")
            if struct_name is not None:
                fields = self.struct_defs.get(struct_name, [])
                if member not in fields:
                    raise VMRuntimeError(f"Struct '{struct_name}' has no field '{member}'")
            obj[member] = value
            return

        raise VMRuntimeError("Invalid assignment target")

    def _call_function(self, function_name: str, arguments: List[Any]) -> Any:
        """Invoke built-in or user-defined function."""
        name = function_name.lower()

        builtin = self._call_builtin(name, arguments)
        if builtin is not None:
            return builtin

        if name in self.functions:
            return self._call_user_function(self.functions[name], arguments)

        raise VMRuntimeError(f"Unknown function '{function_name}'")

    def _call_builtin(self, name: str, arguments: List[Any]) -> Optional[Any]:
        """Handle built-in NoBASIC functions. Return None if not built-in."""
        if name in ("rand", "rnd"):
            self._check_arity(name, arguments, [0])
            return random.randint(0, 255)

        if name == "rndr":
            self._check_arity(name, arguments, [2])
            low = self._to_int(arguments[0])
            high = self._to_int(arguments[1])
            if low > high:
                low, high = high, low
            return random.randint(low, high)

        if name == "randomize":
            self._check_arity(name, arguments, [1])
            random.seed(self._to_int(arguments[0]))
            return 0

        if name == "sin":
            self._check_arity(name, arguments, [1])
            return math.sin(self._to_number(arguments[0]))
        if name == "cos":
            self._check_arity(name, arguments, [1])
            return math.cos(self._to_number(arguments[0]))
        if name == "tan":
            self._check_arity(name, arguments, [1])
            return math.tan(self._to_number(arguments[0]))
        if name == "sqrt":
            self._check_arity(name, arguments, [1])
            value = self._to_number(arguments[0])
            if value < 0:
                raise VMRuntimeError("sqrt() domain error")
            return math.sqrt(value)
        if name == "abs":
            self._check_arity(name, arguments, [1])
            return abs(self._to_number(arguments[0]))
        if name == "int":
            self._check_arity(name, arguments, [1])
            return int(self._to_number(arguments[0]))
        if name == "round":
            self._check_arity(name, arguments, [1])
            return int(round(self._to_number(arguments[0])))

        if name in ("length", "len"):
            self._check_arity(name, arguments, [1])
            return len(str(arguments[0]))
        if name == "sub":
            self._check_arity(name, arguments, [3])
            text = str(arguments[0])
            start = max(0, self._to_int(arguments[1]))
            length = max(0, self._to_int(arguments[2]))
            return text[start : start + length]
        if name == "concat":
            self._check_arity(name, arguments, [2])
            return f"{arguments[0]}{arguments[1]}"

        if name == "sum":
            self._check_arity(name, arguments, [1])
            value = arguments[0]
            if isinstance(value, list):
                return sum(self._to_number(item) for item in value)
            return self._to_number(value)
        if name == "mean":
            self._check_arity(name, arguments, [1])
            value = arguments[0]
            if isinstance(value, list) and value:
                return sum(self._to_number(item) for item in value) / len(value)
            return 0
        if name == "dim":
            self._check_arity(name, arguments, [1])
            value = arguments[0]
            if isinstance(value, list):
                return len(value)
            if isinstance(value, str):
                return len(value)
            return 1

        if name == "memread":
            self._check_arity(name, arguments, [1])
            address = self._to_int(arguments[0]) & 0xFFFF
            return self.mem.read_byte(address)
        if name == "memwrite":
            self._check_arity(name, arguments, [2])
            address = self._to_int(arguments[0]) & 0xFFFF
            value = self._to_int(arguments[1]) & 0xFF
            self.mem.write_byte(address, value)
            return value

        if name == "getkey":
            self._check_arity(name, arguments, [0])
            return self._read_key(blocking=True)

        if name == "serin":
            self._check_arity(name, arguments, [0])
            return self.proc.uart.read_data() & 0xFF

        if name == "serstat":
            self._check_arity(name, arguments, [0])
            return self.proc.uart.read_status_flags() & 0xFF

        return None

    def _call_user_function(self, function: FunctionDefStmt, arguments: List[Any]) -> Any:
        """Invoke a user-defined NoBASIC function."""
        params = function.params
        min_args = sum(1 for _, default in params if default is None)
        max_args = len(params)

        if not (min_args <= len(arguments) <= max_args):
            raise VMRuntimeError(
                f"Function '{function.name}' expects {min_args}-{max_args} args, got {len(arguments)}"
            )

        frame: Dict[str, Any] = {}
        for index, (param_name, default_expr) in enumerate(params):
            if index < len(arguments):
                frame[param_name.lower()] = arguments[index]
            elif default_expr is not None:
                frame[param_name.lower()] = self._eval_expr(default_expr)
            else:
                raise VMRuntimeError(
                    f"Missing required argument {index + 1} for '{function.name}'"
                )

        self.frames.append(frame)
        try:
            self._execute_block(function.body)
        except ReturnSignal as signal:
            return signal.value
        finally:
            self.frames.pop()

        return None

    def _set_sprite_enabled(self, sprite_id: int, enabled: bool, x: int, y: int) -> None:
        """Enable/disable sprite in memory-mapped sprite control block."""
        base = 0xF000 + (sprite_id * 16)
        self.mem.write_byte(base + 2, x & 0xFF)
        self.mem.write_byte(base + 3, y & 0xFF)

        flags = self.mem.read_byte(base + 6)
        if enabled:
            flags |= 0x01
        else:
            flags &= 0xFE
        self.mem.write_byte(base + 6, flags)

        self.gfx.blit_all_sprites(self.mem)

    def _play_tone(self, frequency: int, duration_ms: int, volume: int) -> None:
        """Play a tone with duration by configuring sound registers."""
        if not self.snd:
            return

        sf = max(0, min(255, frequency))
        sw = 0x80 | ((self.current_channel & 0x07) << 3) | 0x01
        self.snd.update_registers(sf=sf, sv=volume, sw=sw)
        self.snd.splay(self.current_channel)

        if duration_ms > 0:
            time.sleep(duration_ms / 1000.0)
            self.snd.sstop(self.current_channel)

    def _play_wave(self, waveform: int, frequency: int, volume: int) -> None:
        """Play a continuous waveform."""
        if not self.snd:
            return

        sf = max(0, min(255, frequency))
        sw = 0x80 | ((self.current_channel & 0x07) << 3) | (waveform & 0x07)
        self.snd.update_registers(sf=sf, sv=volume, sw=sw)
        self.snd.splay(self.current_channel)

    def _read_key(self, blocking: bool = True) -> int:
        """Read key code from Nova keyboard buffer or console fallback."""
        key_code = self.proc.read_key_from_buffer()
        if key_code:
            return key_code

        if not blocking:
            return 0

        raw = input("[GetKey] Enter key: ")
        if not raw:
            return 0

        key_name = "enter" if raw == "\n" else raw
        if len(key_name) == 1:
            scan_code = self.kbd.get_scan_code(key_name)
        else:
            scan_code = self.kbd.get_scan_code(key_name.lower())
        if scan_code == 0 and len(raw) >= 1:
            scan_code = ord(raw[0]) & 0xFF
        self.proc.add_key_to_buffer(scan_code)
        return self.proc.read_key_from_buffer()

    def _current_frame(self) -> Dict[str, Any]:
        return self.frames[-1]

    def _find_frame_with_var(self, name: str) -> Optional[Dict[str, Any]]:
        key = name.lower()
        for frame in reversed(self.frames):
            if key in frame:
                return frame
        return None

    def _get_var(self, name: str) -> Any:
        key = name.lower()
        frame = self._find_frame_with_var(key)
        if frame is not None:
            return frame[key]

        self.frames[0][key] = 0
        return 0

    def _set_var(self, name: str, value: Any) -> None:
        key = name.lower()
        frame = self._find_frame_with_var(key)
        if frame is not None:
            frame[key] = value
            return
        self._current_frame()[key] = value

    def _has_var(self, name: str) -> bool:
        return self._find_frame_with_var(name.lower()) is not None

    def _create_struct_instance(self, struct_name: str) -> Dict[str, Any]:
        fields = self.struct_defs.get(struct_name)
        if fields is None:
            raise VMRuntimeError(f"Unknown struct '{struct_name}'")
        instance: Dict[str, Any] = {"__struct__": struct_name}
        for field_name in fields:
            instance[field_name] = 0
        return instance

    def _infer_struct_type(self, var_name: str, member: str) -> Optional[str]:
        if not self.struct_defs:
            return None

        matching = [
            name for name, fields in self.struct_defs.items() if member.lower() in fields
        ]
        if len(matching) == 1:
            return matching[0]
        if len(matching) > 1:
            return None

        if len(self.struct_defs) == 1:
            return next(iter(self.struct_defs.keys()))

        return None

    @staticmethod
    def _check_arity(name: str, arguments: List[Any], allowed: List[int]) -> None:
        if len(arguments) not in allowed:
            raise VMRuntimeError(
                f"Function '{name}' expects {allowed} arguments, got {len(arguments)}"
            )

    @staticmethod
    def _to_number(value: Any) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            raise VMRuntimeError(f"Value '{value}' is not numeric") from None

    @staticmethod
    def _to_int(value: Any) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        try:
            return int(value)
        except (TypeError, ValueError):
            raise VMRuntimeError(f"Value '{value}' is not an integer") from None

    @staticmethod
    def _truthy(value: Any) -> bool:
        if isinstance(value, str):
            return len(value) > 0
        return bool(value)

    def export_screen_png(self, output_path: str, scale: int = 2) -> Path:
        """Export current framebuffer as PNG using Nova palette colors."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        self.gfx.set_color_palette()
        indexed = self.gfx.get_screen().astype(np.uint8)
        palette = np.array(self.gfx.get_palette(), dtype=np.uint8)
        rgb = palette[indexed]

        height, width = rgb.shape[:2]
        surface = pygame.Surface((width, height))
        pygame.surfarray.blit_array(surface, rgb.swapaxes(0, 1))

        if scale > 1:
            surface = pygame.transform.scale(surface, (width * scale, height * scale))

        pygame.image.save(surface, str(output))
        return output


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="NoBASIC Interpreter VM (Nova-16 backend)")
    parser.add_argument("source", help="Path to .nobasic source file")
    parser.add_argument("--no-sound", action="store_true", help="Disable sound backend")
    parser.add_argument(
        "--max-steps",
        type=int,
        default=1_000_000,
        help="Maximum interpreter steps before aborting",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--skip-semantic",
        action="store_true",
        help="Skip semantic analysis before execution",
    )
    parser.add_argument(
        "--strict-asm",
        action="store_true",
        help="Treat inline Asm blocks as runtime errors instead of skipping",
    )
    parser.add_argument(
        "--export-screen",
        help="Export final framebuffer to PNG (e.g. .\\out\\screen.png)",
    )
    parser.add_argument(
        "--show-screen",
        action="store_true",
        help="Open exported framebuffer image with default OS viewer",
    )
    parser.add_argument(
        "--screen-scale",
        type=int,
        default=2,
        help="Integer scale multiplier for exported PNG (default: 2)",
    )

    args = parser.parse_args()
    source_path = Path(args.source)

    if not source_path.exists():
        print(f"Source file not found: {source_path}")
        return 1

    config = NoBASICVMConfig(
        enable_sound=not args.no_sound,
        max_steps=args.max_steps,
        verbose=args.verbose,
        skip_semantic=args.skip_semantic,
        strict_asm=args.strict_asm,
    )

    vm = NoBASICVM(config)
    exported_path: Optional[Path] = None

    try:
        vm.run_file(str(source_path))

        should_export = args.export_screen is not None or args.show_screen
        if should_export:
            output_path = args.export_screen
            if not output_path:
                output_path = str(source_path.with_suffix(".vm_screen.png"))

            exported_path = vm.export_screen_png(output_path, scale=max(1, args.screen_scale))
            print(f"Exported framebuffer: {exported_path}")

            if args.show_screen:
                try:
                    os.startfile(str(exported_path))
                except Exception as error:
                    print(f"Could not open exported image automatically: {error}")
    except CompilerError as error:
        print(f"Compiler error: {error}")
        return 1
    except VMRuntimeError as error:
        print(f"VM runtime error: {error}")
        return 1
    except Exception as error:
        print(f"Unexpected error: {error}")
        return 1
    finally:
        if vm.snd:
            vm.snd.cleanup()

    return 0


if __name__ == "__main__":
    sys.exit(main())
