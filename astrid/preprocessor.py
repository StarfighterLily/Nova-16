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
        """Expand whole tokens only; recursion is suppressed like C macros."""
        if len(disabled) > 64:
            self.fail('macro expansion exceeds 64 levels')
        result = []
        size = 0
        for match in _PIECE.finditer(text):
            word = match.group()
            if word in self.defines and word not in disabled:
                word = ' ' + self.expand(self.defines[word], disabled | {word}) + ' '
            size += len(word)
            if size > 1048576:
                self.fail('macro expansion exceeds 1 MiB')
            result.append(word)
        # Spaces preserve preprocessing token boundaries (e.g. + +, not ++).
        return ''.join(result)

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
                pieces, columns = [], []
                for match in _PIECE.finditer(text):
                    word = match.group()
                    if word in self.defines and not protected[offset + match.start()]:
                        word = ' ' + self.expand(self.defines[word], frozenset({word})) + ' '
                        columns.extend([match.start() + 1] * len(word))
                    else:
                        columns.extend(range(match.start() + 1, match.end() + 1))
                    pieces.append(word)
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
            if value.startswith('('):
                self.fail('function-like macros are not supported')
            if value.endswith('\\'):
                self.fail('multiline macro definitions are not supported')
            value = value.strip()
            if macro in self.defines and self.defines[macro] != value:
                self.fail(f'macro {macro!r} redefined; use #undef first')
            self.defines = {**self.defines, macro: value}
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
