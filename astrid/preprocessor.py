"""Line-oriented conditional compilation, before Astrid's ordinary lexer.

File units inherit a snapshot of their caller's definitions; they do not export
macros back to the caller. This preserves the parser's include/inherits model.
"""
import re
from dataclasses import dataclass

from astrid.errors import CompileError


class PreprocessorError(CompileError):
    phase = 'preprocessor'


_NAME = r'[A-Za-z_][A-Za-z0-9_]*'
_LITERAL = r'"(?:\\[\s\S]|[^"\\])*"|\'(?:\\[\s\S]|[^\'\\])*\''
_PIECE = re.compile(_LITERAL + r'|0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|\d+(?:\.\d+)?|' + _NAME + r'|[\s\S]')
_LEXICAL = re.compile(_LITERAL + r'|//[^\n]*|/\*[\s\S]*?(?:\*/|\Z)')

# Function-like macros are stored inside `defines` as
#   '\x01' + ','.join(params) + '\x01' + body
# so every existing consumer of the table -- #ifdef, defined(), #undef,
# the per-line snapshots handed to include files -- keeps working on
# presence alone, and only the expander decodes the payload.
_FN_MARKER = '\x01'


def _is_func_macro(value):
    """True when a #define stored value encodes a function-like macro."""
    return (isinstance(value, str) and value.startswith(_FN_MARKER)
            and _FN_MARKER in value[1:])


def _decode_func_macro(value):
    """Split an encoded function-like macro into (params, body)."""
    head, _, body = value[1:].partition(_FN_MARKER)
    return (head.split(',') if head else []), body



@dataclass
class Conditional:
    parent: bool
    active: bool
    taken: bool
    line: int
    saw_else: bool = False


class Preprocessor:
    def __init__(self, source, defines=None, source_path=None):
        self.source = source
        self.source_path = source_path
        self.line = 1
        self.column = 1
        self.defines = {}
        for name, value in (defines or {}).items():
            if not isinstance(name, str) or not re.fullmatch(_NAME, name):
                self.fail(f'invalid macro name: {name!r}')
            value = '1' if value is None else str(value)
            if '\n' in value or '\r' in value:
                self.fail('macro definitions must fit on one line')
            self.defines[name] = value
        self.line_defines = {}
        self.columns = {}

    def fail(self, message):
        raise PreprocessorError(message, filename=self.source_path,
                                line=self.line, column=self.column,
                                source_text=self.source)

    def expand(self, text, disabled=frozenset()):
        """Expand whole tokens only; recursion is suppressed like C macros.

        Function-like macros invoke when their name is followed by '('
        (whitespace allowed between them); arguments are pre-expanded in
        the caller's context like C, then the substituted body is
        rescanned with the macro name painted to stop self-reference.
        Object-like macros expand recursively exactly as before.
        """
        if len(disabled) > 64:
            self.fail('macro expansion exceeds 64 levels')
        return self._walk([m.group() for m in _PIECE.finditer(text)],
                          disabled)

    def _walk(self, tokens, disabled):
        """Token-level expander shared by expand() and macro bodies."""
        if len(disabled) > 64:
            self.fail('macro expansion exceeds 64 levels')
        result = []
        size = 0
        i = 0
        n = len(tokens)
        while i < n:
            word = tokens[i]
            raw = None if word in disabled else self.defines.get(word)
            if raw is None:
                chunk = word
                i += 1
            elif _is_func_macro(raw):
                close = self._invocation_close(tokens, i)
                if close is None:
                    # Bare name with no '(' after it: an ordinary
                    # identifier, per C's function-like macro rule.
                    chunk = word
                    i += 1
                else:
                    chunk, i = self._expand_invocation(tokens, i, close,
                                                        disabled)
            else:
                chunk = ' ' + self.expand(raw, disabled | {word}) + ' '
                i += 1
            size += len(chunk)
            if size > 1048576:
                self.fail('macro expansion exceeds 1 MiB')
            result.append(chunk)
        # Spaces preserve preprocessing token boundaries (e.g. + +, not ++).
        return ''.join(result)

    def _invocation_close(self, tokens, i):
        """Index of the ')' closing the invocation of tokens[i], or None.

        Returns None when no '(' follows the macro name (only whitespace
        may intervene). Fails when a '(' opens an invocation that never
        closes in this token list -- invocations must fit on one line.
        """
        j = i + 1
        while j < len(tokens) and not tokens[j].strip():
            j += 1
        if j >= len(tokens) or tokens[j] != '(':
            return None
        depth = 0
        while j < len(tokens):
            if tokens[j] == '(':
                depth += 1
            elif tokens[j] == ')':
                depth -= 1
                if depth == 0:
                    return j
            j += 1
        self.fail(f'unterminated invocation of function-like macro '
                  f'{tokens[i]!r} (a macro invocation must fit on one line)')
        return None  # unreachable; keeps the contract explicit

    def _expand_invocation(self, tokens, i, close, disabled):
        """Expand function-like macro tokens[i] applied to tokens up to close.

        Returns (replacement, next_index). The replacement is padded with
        spaces so it cannot fuse with neighbouring tokens.
        """
        name = tokens[i]
        params, body = _decode_func_macro(self.defines[name])
        # Locate the '(' the same way _invocation_close did (whitespace
        # may sit between the macro name and the paren).
        open_idx = i + 1
        while open_idx < close and not tokens[open_idx].strip():
            open_idx += 1
        # Split argument tokens at top-level commas; parentheses and
        # string/char literals are single tokens, so nesting is safe.
        args = []
        current = []
        inner = 0
        for t in tokens[open_idx + 1:close]:
            if t == '(':
                inner += 1
            elif t == ')':
                inner -= 1
            if t == ',' and inner == 0:
                args.append(current)
                current = []
            else:
                current.append(t)
        args.append(current)
        if not params and len(args) == 1 and not args[0]:
            args = []  # zero-parameter macro invoked as NAME()
        if len(args) != len(params):
            self.fail(f"macro {name!r} expects {len(params)} argument(s), "
                      f"got {len(args)}")
        # C treats an argument as a preprocessing-token sequence, so edge
        # whitespace (the space after a separating comma) is not part of it.
        def strip_ws(toks):
            start = 0
            end = len(toks)
            while start < end and not toks[start].strip():
                start += 1
            while end > start and not toks[end - 1].strip():
                end -= 1
            return toks[start:end]
        # C pre-expands each argument in the caller's context (the macro
        # name is not yet painted there), then rescans the substituted
        # body with the name painted.
        expanded_args = [''.join(self._walk(strip_ws(arg), disabled))
                         for arg in args]
        pset = set(params)
        sub = []
        for m in _PIECE.finditer(body):
            token = m.group()
            if token in pset:
                sub.extend(p.group() for p in
                           _PIECE.finditer(
                               expanded_args[params.index(token)]))
            else:
                sub.append(token)
        replacement = ' ' + self._walk(sub, disabled | {name}) + ' '
        return replacement, close + 1

    def condition(self, text):
        def defined(match):
            return str(int((match[1] or match[2]) in self.defines))
        text = re.sub(r'\bdefined\b\s*(?:\(\s*(' + _NAME + r')\s*\)|(' + _NAME + r'))',
                      defined, text)
        return bool(Expression(self.expand(text), self.fail).evaluate())

    def process(self):
        # Mask comments, not delete them: both token boundaries and source
        # coordinates must survive. Quoted spans protect apparent directives.
        clean = list(self.source)
        protected = [False] * len(clean)
        for match in _LEXICAL.finditer(self.source):
            if match.group().startswith(('/',)):
                for i in range(match.start(), match.end()):
                    if clean[i] not in '\r\n':
                        clean[i] = ' '
            else:
                protected[match.start():match.end()] = [True] * len(match.group())
        output = []
        stack = []
        offset = 0
        for self.line, text in enumerate(''.join(clean).splitlines(keepends=True), 1):
            active = not stack or stack[-1].active
            stripped = text.lstrip(' \t\r')
            start = len(text) - len(stripped)
            self.column = start + 1
            self.line_defines[self.line] = self.defines
            if stripped.startswith('#') and not protected[offset + start]:
                self.directive(stripped[1:].strip(), stack, active)
                output.append(''.join(c if c in '\r\n' else ' ' for c in text))
            elif not active:
                output.append(''.join(c if c in '\r\n' else ' ' for c in text))
            else:
                matches = list(_PIECE.finditer(text))
                toks = [m.group() for m in matches]
                pieces, columns = [], []
                mi = 0
                while mi < len(matches):
                    match = matches[mi]
                    word = toks[mi]
                    raw = (None if protected[offset + match.start()]
                           else self.defines.get(word))
                    if raw is None:
                        pieces.append(word)
                        columns.extend(
                            range(match.start() + 1, match.end() + 1))
                        mi += 1
                        continue
                    if _is_func_macro(raw):
                        close = self._invocation_close(toks, mi)
                        if close is None:
                            # Bare name: an ordinary identifier (C rule).
                            pieces.append(word)
                            columns.extend(
                                range(match.start() + 1, match.end() + 1))
                            mi += 1
                            continue
                        chunk, mi = self._expand_invocation(toks, mi, close,
                                                            frozenset())
                    else:
                        chunk = (' ' + self.expand(raw,
                                                   frozenset({word})) + ' ')
                        mi += 1
                    pieces.append(chunk)
                    columns.extend([match.start() + 1] * len(chunk))
                self.columns[self.line] = columns
                output.append(''.join(pieces))
            offset += len(text)
        if stack:
            self.line = stack[-1].line
            self.column = 1
            self.fail('unterminated conditional: expected #endif')
        return ''.join(output)

    def directive(self, text, stack, active):
        parts = text.split(None, 1)
        if not parts:
            return
        name, arg = parts[0], parts[1].strip() if len(parts) > 1 else ''
        if name in ('if', 'ifdef', 'ifndef'):
            if not arg:
                self.fail(f'#{name} requires a condition')
            if name != 'if' and not re.fullmatch(_NAME, arg):
                self.fail(f'#{name} requires one macro name')
            selected = False
            if active:
                selected = (self.condition(arg) if name == 'if' else
                            (arg in self.defines) == (name == 'ifdef'))
            stack.append(Conditional(active, selected, selected, self.line))
        elif name in ('elif', 'else', 'endif'):
            if not stack:
                self.fail(f'#{name} without matching #if')
            frame = stack[-1]
            if name != 'elif' and arg:
                self.fail(f'#{name} does not accept arguments')
            if name == 'endif':
                stack.pop()
                return
            if frame.saw_else:
                self.fail(f'#{name} after #else')
            if name == 'elif' and not arg:
                self.fail('#elif requires a condition')
            eligible = frame.parent and not frame.taken
            frame.active = eligible and (name == 'else' or self.condition(arg))
            frame.taken |= frame.active
            frame.saw_else = name == 'else'
        elif not active:
            return
        elif name == 'define':
            match = re.fullmatch('(' + _NAME + r')(.*)', arg)
            if not match:
                self.fail('#define requires a macro name')
            macro, value = match.groups()
            if value.endswith('\\'):
                self.fail('multiline macro definitions are not supported')
            if value.startswith('('):
                # Function-like macro: the '(' must immediately follow the
                # name (C's rule -- `#define F (x)` with a space is an
                # object-like macro whose body happens to be parenthesized).
                # Variadic parameters are rejected the same way variadic
                # functions are: this preprocessor has no __VA_ARGS__.
                close = value.find(')')
                if close < 0:
                    self.fail('unterminated macro parameter list')
                head = value[1:close]
                body = value[close + 1:].strip()
                params = ([] if not head.strip()
                          else [p.strip() for p in head.split(',')])
                for p in params:
                    if p == '...':
                        self.fail('variadic macros are not supported')
                    if not re.fullmatch(_NAME, p):
                        self.fail(f'invalid macro parameter {p!r} in #define')
                stored = _FN_MARKER + ','.join(params) + _FN_MARKER + body
            else:
                stored = value.strip()
            if macro in self.defines and self.defines[macro] != stored:
                self.fail(f'macro {macro!r} redefined; use #undef first')
            self.defines = {**self.defines, macro: stored}
        elif name == 'undef':
            if not re.fullmatch(_NAME, arg):
                self.fail('#undef requires one macro name')
            self.defines = dict(self.defines)
            self.defines.pop(arg, None)
        elif name == 'error':
            self.fail(arg or '#error')
        else:
            self.fail(f'unknown directive #{name}')


class Expression:
    """Integer Pratt parser, with short-circuit evaluation and no host eval."""
    precedence = {'||': 1, '&&': 2, '|': 3, '^': 4, '&': 5,
                  '==': 6, '!=': 6, '<': 7, '<=': 7, '>': 7, '>=': 7,
                  '<<': 8, '>>': 8, '+': 9, '-': 9, '*': 10, '/': 10, '%': 10}
    pattern = re.compile(r'\s+|0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|\d+|'
                         + _NAME + r'|\|\||&&|==|!=|<=|>=|<<|>>|[()!~+*/%<>&|^\-]|.')

    def __init__(self, text, fail):
        self.tokens = [m.group() for m in self.pattern.finditer(text) if not m.group().isspace()]
        self.pos = 0
        self.fail = fail

    def take(self):
        if self.pos == len(self.tokens):
            self.fail('incomplete #if expression')
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def evaluate(self):
        try:
            result = self.parse(1, True)
        except (RecursionError, ValueError, ZeroDivisionError) as exc:
            self.fail(f'invalid #if expression: {exc}')
        if self.pos != len(self.tokens):
            self.fail(f'unexpected token {self.tokens[self.pos]!r} in #if expression')
        return result

    def parse(self, minimum, enabled):
        token = self.take()
        if token in ('!', '~', '+', '-'):
            value = self.parse(11, enabled)
            left = {'!': lambda: int(not value), '~': lambda: ~value,
                    '+': lambda: value, '-': lambda: -value}[token]()
        elif token == '(':
            left = self.parse(1, enabled)
            if self.take() != ')':
                self.fail('expected closing parenthesis in #if expression')
        elif re.fullmatch(_NAME, token):
            if token == 'defined':
                self.fail('defined requires a macro name, optionally in parentheses')
            left = 0
        elif re.fullmatch(r'0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+|\d+', token):
            left = int(token, 0 if token.lower().startswith(('0x', '0b', '0o')) else 10)
        else:
            self.fail(f'invalid token {token!r} in #if expression')
        while self.pos < len(self.tokens):
            op = self.tokens[self.pos]
            level = self.precedence.get(op, 0)
            if level < minimum:
                break
            self.pos += 1
            rhs_enabled = enabled and not (op == '&&' and not left or op == '||' and left)
            right = self.parse(level + 1, rhs_enabled)
            left = self.apply(op, left, right) if enabled else 0
        return left

    def apply(self, op, a, b):
        if op in ('/', '%'):
            q = (abs(a) // abs(b)) * (-1 if (a < 0) != (b < 0) else 1)
            return q if op == '/' else a - q * b
        if op in ('<<', '>>') and not 0 <= b <= 65535:
            self.fail('shift count in #if must be between 0 and 65535')
        return {'+': lambda: a + b, '-': lambda: a - b, '*': lambda: a * b,
                '<<': lambda: a << b, '>>': lambda: a >> b,
                '&': lambda: a & b, '|': lambda: a | b, '^': lambda: a ^ b,
                '==': lambda: int(a == b), '!=': lambda: int(a != b),
                '<': lambda: int(a < b), '<=': lambda: int(a <= b),
                '>': lambda: int(a > b), '>=': lambda: int(a >= b),
                '&&': lambda: int(bool(a) and bool(b)),
                '||': lambda: int(bool(a) or bool(b))}[op]()
