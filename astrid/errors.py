"""Diagnostics infrastructure for the Astrid compiler.

This module centralizes how the Astrid compiler reports errors:

- ``CompileError`` is the base class for every user-facing compiler error.
  It subclasses ``SyntaxError`` so existing callers (and tests) that catch
  ``SyntaxError`` keep working unchanged.
- Errors carry structured position information (file / line / column), the
  offending source line, and an optional ``hint`` with an actionable fix.
- ``str(error)`` renders the full diagnostic, e.g.::

      parser error: Expected ';', found 'x'
        --> game.ast:14:9
         14 |     int a = 1 x
            |               ^
        hint: did you mean ';'?

  so every entry point (CLI, compiler API, MCP server) surfaces the same
  rich diagnostic without extra plumbing.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

__all__ = [
    'CompileError', 'LexerError', 'ParserError', 'CodeGenError',
    'did_you_mean', 'levenshtein',
]


def levenshtein(a: str, b: str) -> int:
    """Edit distance between two strings (classic DP, O(len*len))."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(
                prev[j] + 1,        # deletion
                cur[j - 1] + 1,     # insertion
                prev[j - 1] + (ca != cb),  # substitution
            ))
        prev = cur
    return prev[-1]


def did_you_mean(name: str, candidates: Iterable[str],
                 max_distance: int = 2) -> Optional[str]:
    """Return the closest candidate to ``name`` within ``max_distance``.

    Comparison is case-insensitive (Astrid identifiers/keywords are
    lowercase by convention, but be forgiving). Returns ``None`` when
    nothing is close enough -- callers should only attach a hint then.
    """
    if not name:
        return None
    name_l = name.lower()
    best: Optional[str] = None
    best_dist = max_distance + 1
    for cand in candidates:
        if not cand or cand == name:
            continue
        dist = levenshtein(name_l, str(cand).lower())
        if dist < best_dist:
            best, best_dist = str(cand), dist
    return best


class CompileError(SyntaxError):
    """Base class for all Astrid compiler errors.

    Subclasses ``SyntaxError`` for backward compatibility: existing code
    that catches ``SyntaxError`` around compilation continues to work.

    Attributes:
        message:     The core error message (no position info embedded).
        filename:    Source file the error came from (``None`` for stdin).
        line:        1-based line number (``None`` when unknown).
        column:      1-based column number (``None`` when unknown).
        length:      Number of characters to underline in the snippet.
        hint:        Optional actionable suggestion shown after the snippet.
        source_text: Full source text used to render the snippet.
    """

    phase = 'compile'

    def __init__(self, message: str, filename: Optional[str] = None,
                 line: Optional[int] = None, column: Optional[int] = None,
                 length: int = 1, hint: Optional[str] = None,
                 source_text: Optional[str] = None):
        self.message = message
        self.filename = filename
        self.line = line
        self.column = column
        self.length = max(1, length)
        self.hint = hint
        self.source_text = source_text
        # Keep the plain message in args so generic tooling (logging,
        # pickling, IDE consoles) sees something sensible; ``__str__``
        # renders the rich diagnostic.
        super().__init__(message)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _location(self) -> str:
        """Render the ``--> file:line:col`` location string."""
        if self.filename and self.line is not None:
            loc = f"{self.filename}:{self.line}"
            if self.column is not None:
                loc += f":{self.column}"
            return loc
        if self.filename:
            return self.filename
        if self.line is not None:
            loc = f"line {self.line}"
            if self.column is not None:
                loc += f", column {self.column}"
            return loc
        return ''

    def _snippet(self) -> List[str]:
        """Render the source excerpt with a caret under the position."""
        if self.source_text is None or self.line is None:
            return []
        src_lines = self.source_text.splitlines()
        if self.line < 1 or self.line > len(src_lines):
            return []
        num_w = max(2, len(str(self.line)))
        text = src_lines[self.line - 1]
        # Guard against pathological positions (e.g. after a CRLF split).
        col = self.column if self.column is not None else 1
        col = max(1, col)
        caret_pad = ' ' * (col - 1)
        caret = '^' * self.length
        return [
            f" {' ' * num_w} |",
            f" {self.line:>{num_w}} | {text}",
            f" {' ' * num_w} | {caret_pad}{caret}",
        ]

    def render(self) -> str:
        """Render the full multi-line diagnostic."""
        out = [f"{self.phase} error: {self.message}"]
        loc = self._location()
        if loc:
            out.append(f"  --> {loc}")
        out.extend(self._snippet())
        if self.hint:
            out.append(f"  hint: {self.hint}")
        return '\n'.join(out)

    def __str__(self) -> str:
        return self.render()


class LexerError(CompileError):
    """Error while tokenizing the source text."""
    phase = 'lexer'


class ParserError(CompileError):
    """Error while parsing the token stream."""
    phase = 'parser'


class CodeGenError(CompileError):
    """Error while generating assembly from the AST."""
    phase = 'codegen'
