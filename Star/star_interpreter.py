#!/usr/bin/env python3
"""
Star Interpreter
Directly executes NoBASIC code by translating to Python calls.
"""

import sys
import os
import time
import pygame
import numpy as np
from pathlib import Path

# Add the NoBASIC compiler directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'NoBASIC'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'NoBASIC', 'compiler'))

from compiler.lexer.lexer import Lexer
from compiler.parser.parser import Parser
from compiler.semantic.analyzer import SemanticAnalyzer
from compiler.utils.error import CompilerError

# Import AST nodes
from compiler.parser.ast import (
    ClrDrawStmt, PxlOnStmt, PxlOffStmt, LineStmt, CircleStmt, TextStmt,
    SetLayerStmt, DispStmt, PauseStmt, AssignmentStmt, IfStmt, ForStmt,
    WhileStmt, RepeatStmt, GotoStmt, LabelStmt, LiteralExpr, VariableExpr,
    BinaryExpr, UnaryExpr, FunctionCallExpr, GroupingExpr
)

# Import GFX for graphics
sys.path.insert(0, os.path.dirname(__file__))
from star_gfx import GFX


class StarInterpreter:
    """Interpreter for NoBASIC that executes directly using Python calls."""

    def __init__(self, width=256, height=256, headless=False):
        self.gfx = GFX(width, height)
        self.variables = {}  # Variable storage
        self.labels = {}  # Label addresses for GOTO
        self.pc = 0  # Program counter (statement index)
        self.running = True
        self.headless = headless
        self.screen = None  # Pygame screen

    def init_display(self):
        """Initialize pygame display."""
        if not self.headless:
            pygame.init()
            self.screen = pygame.display.set_mode((self.gfx.width, self.gfx.height))
            pygame.display.set_caption("Star - NoBASIC Interpreter")

    def update_display(self):
        """Update the pygame display with current GFX screen."""
        if self.screen:
            # For testing, fill with a gradient
            screen_data = self.gfx.get_screen()
            test_surface = pygame.Surface((self.gfx.width, self.gfx.height))
            for x in range(self.gfx.width):
                for y in range(self.gfx.height):
                    color = screen_data[y, x]
                    r, g, b = self.gfx.palette[color]
                    test_surface.set_at((x, y), (r, g, b))

            self.screen.blit(test_surface, (0, 0))
            pygame.display.flip()

    def evaluate_expression(self, expr):
        """Evaluate an expression and return its value."""
        if isinstance(expr, LiteralExpr):
            return expr.value
        elif isinstance(expr, VariableExpr):
            return self.variables.get(expr.name, 0)
        elif isinstance(expr, BinaryExpr):
            left = self.evaluate_expression(expr.left)
            right = self.evaluate_expression(expr.right)
            if expr.operator == '+':
                return left + right
            elif expr.operator == '-':
                return left - right
            elif expr.operator == '*':
                return left * right
            elif expr.operator == '/':
                return left / right if right != 0 else 0
            elif expr.operator == '=':
                return 1 if left == right else 0
            elif expr.operator == '<>':
                return 1 if left != right else 0
            elif expr.operator == '<':
                return 1 if left < right else 0
            elif expr.operator == '>':
                return 1 if left > right else 0
            elif expr.operator == '<=':
                return 1 if left <= right else 0
            elif expr.operator == '>=':
                return 1 if left >= right else 0
        elif isinstance(expr, UnaryExpr):
            val = self.evaluate_expression(expr.expression)
            if expr.operator == '-':
                return -val
            elif expr.operator == 'NOT':
                return 1 if val == 0 else 0
        elif isinstance(expr, GroupingExpr):
            return self.evaluate_expression(expr.expression)
        elif isinstance(expr, FunctionCallExpr):
            # Handle built-in functions
            if expr.name.upper() == 'ABS':
                return abs(self.evaluate_expression(expr.arguments[0]))
            elif expr.name.upper() == 'SIN':
                import math
                return math.sin(self.evaluate_expression(expr.arguments[0]))
            elif expr.name.upper() == 'COS':
                import math
                return math.cos(self.evaluate_expression(expr.arguments[0]))
            # Add more functions as needed
        return 0

    def execute_statement(self, stmt):
        """Execute a single statement."""
        if isinstance(stmt, ClrDrawStmt):
            self.gfx.clear()
        elif isinstance(stmt, PxlOnStmt):
            x = int(self.evaluate_expression(stmt.x))
            y = int(self.evaluate_expression(stmt.y))
            color = int(self.evaluate_expression(stmt.color))
            self.gfx._set_pixel_fast(x, y, color)
        elif isinstance(stmt, PxlOffStmt):
            x = int(self.evaluate_expression(stmt.x))
            y = int(self.evaluate_expression(stmt.y))
            self.gfx._set_pixel_fast(x, y, 0)
        elif isinstance(stmt, LineStmt):
            x1 = int(self.evaluate_expression(stmt.x1))
            y1 = int(self.evaluate_expression(stmt.y1))
            x2 = int(self.evaluate_expression(stmt.x2))
            y2 = int(self.evaluate_expression(stmt.y2))
            color = int(self.evaluate_expression(stmt.color))
            self.gfx.draw_line(x1, y1, x2, y2, color)
        elif isinstance(stmt, CircleStmt):
            x = int(self.evaluate_expression(stmt.x))
            y = int(self.evaluate_expression(stmt.y))
            radius = int(self.evaluate_expression(stmt.radius))
            color = int(self.evaluate_expression(stmt.color))
            self.gfx.draw_circle(x, y, radius, color)
        elif isinstance(stmt, TextStmt):
            x = int(self.evaluate_expression(stmt.x))
            y = int(self.evaluate_expression(stmt.y))
            text = str(self.evaluate_expression(stmt.text))
            color = int(self.evaluate_expression(stmt.color))
            self.gfx.draw_string(text, x, y, color)
        elif isinstance(stmt, SetLayerStmt):
            layer = int(self.evaluate_expression(stmt.layer))
            self.gfx.set_current_layer(layer)
        elif isinstance(stmt, DispStmt):
            text = str(self.evaluate_expression(stmt.text))
            print(text)  # For now, just print to console
        elif isinstance(stmt, PauseStmt):
            if not self.headless:
                # Wait for a key press
                waiting = True
                while waiting and self.running:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            self.running = False
                            waiting = False
                        elif event.type == pygame.KEYDOWN:
                            waiting = False
                    self.update_display()
                    time.sleep(0.016)
            else:
                time.sleep(1)  # In headless mode, just wait 1 second
        elif isinstance(stmt, AssignmentStmt):
            # Handle variable assignment
            if isinstance(stmt.variable, VariableExpr):
                var_name = stmt.variable.name
            else:
                var_name = str(self.evaluate_expression(stmt.variable))
            value = self.evaluate_expression(stmt.expression)
            self.variables[var_name] = value
        elif isinstance(stmt, IfStmt):
            condition = self.evaluate_expression(stmt.condition)
            if condition != 0:
                for s in stmt.then_branch:
                    self.execute_statement(s)
            elif stmt.else_branch:
                for s in stmt.else_branch:
                    self.execute_statement(s)
        elif isinstance(stmt, LabelStmt):
            self.labels[stmt.label] = self.pc
        elif isinstance(stmt, GotoStmt):
            if stmt.label in self.labels:
                self.pc = self.labels[stmt.label] - 1  # Will be incremented after
        # TODO: Add For, While, Repeat loops

    def run(self, program):
        """Run the NoBASIC program."""
        self.init_display()

        # First pass: collect labels
        self.pc = 0
        for stmt in program.statements:
            if isinstance(stmt, LabelStmt):
                self.labels[stmt.label] = self.pc
            self.pc += 1

        # Second pass: execute
        self.pc = 0
        while self.pc < len(program.statements) and self.running:
            stmt = program.statements[self.pc]
            self.execute_statement(stmt)
            self.pc += 1

            # Handle events during execution
            if not self.headless:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False

            if not self.headless:
                self.update_display()
            time.sleep(0.01)  # Small delay to prevent 100% CPU usage

        # After execution, keep the display open until user closes
        if not self.headless:
            self._main_display_loop()

        if not self.headless:
            pygame.quit()

    def _main_display_loop(self):
        """Main display loop to keep window open after program execution."""
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    # Could handle key input here
                    pass

            self.update_display()
            time.sleep(0.016)  # ~60 FPS


def interpret_nobasic(source_file: str, verbose: bool = False, headless: bool = False):
    """
    Interpret a NoBASIC source file directly.

    Args:
        source_file: Path to the .nobasic source file
        verbose: Enable verbose output
        headless: Run without graphics display
    """
    try:
        # Read source
        with open(source_file, 'r') as f:
            source = f.read()

        if verbose:
            print(f"Interpreting {source_file}...")

        # Lexical analysis
        lexer = Lexer()
        tokens = lexer.tokenize(source, source_file)

        if verbose:
            print(f"Lexical analysis complete: {len(tokens)} tokens")

        # Parsing
        parser = Parser()
        ast = parser.parse(tokens, source_file)

        if verbose:
            print("Parsing complete")

        # Semantic analysis
        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast, source_file)

        if verbose:
            print("Semantic analysis complete")

        # Execute directly
        interpreter = StarInterpreter(headless=headless)
        interpreter.run(ast)

        if verbose:
            print("Execution complete")

    except CompilerError as e:
        print(f"Interpretation error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python star_interpreter.py <source.nobasic> [--verbose] [--headless]")
        sys.exit(1)

    source_file = sys.argv[1]
    verbose = "--verbose" in sys.argv
    headless = "--headless" in sys.argv

    interpret_nobasic(source_file, verbose, headless)


if __name__ == "__main__":
    main()