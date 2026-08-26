# Astrid Language Parser
# File: astrid/parser/parser.py
"""Enhanced parser with do-while loops, switch/case statements, and char literals."""
from __future__ import annotations

from typing import List, Optional, Dict
from astrid.lexer.lexer import Lexer, Token

# Storage qualifiers are accepted and ignored: the declared entity behaves
# exactly like its unqualified counterpart (Astrid has no linker/optimizer
# semantics attached to them).
STORAGE_QUALIFIERS = {'const', 'register', 'volatile', 'extern', 'static', 'inline'}
# Type modifiers normalize to their base type ('int' unless a base type
# follows): Astrid's type system only distinguishes the base widths.
TYPE_MODIFIERS = {'signed', 'unsigned', 'long', 'short'}
BASE_TYPES = {'int', 'char', 'string', 'binary', 'void'}

# AST Node Classes
class ASTNode:
    pass

# Expression AST nodes
class Expression(ASTNode):
    pass

class StringLiteral(Expression):
    def __init__(self, value: str):
        self.value = value

class CharLiteral(Expression):
    """Character literal expression node (e.g., 'A', '\\n')."""
    def __init__(self, char_value: int):
        self.char_value = char_value

class Number(Expression):
    def __init__(self, value):
        self.value = value

class Identifier(Expression):
    def __init__(self, name):
        self.name = name

class BinaryOp(Expression):
    def __init__(self, left: "Expression", op: str, right: "Expression"):
        self.left = left
        self.op = op
        self.right = right

class UnaryOp(Expression):
    def __init__(self, op: str, right: "Expression"):
        self.op = op
        self.right = right

class PostfixOp(Expression):
    def __init__(self, left: "Expression", op: str):
        self.left = left
        self.op = op

class Program(ASTNode):
    def __init__(self, functions: List["FunctionDef"], globals_: Optional[List["VarDecl"]] = None,
                 enum_constants: Optional[Dict[str, int]] = None,
                 structs: Optional[Dict[str, List[str]]] = None):
        self.functions = functions
        # Top-level (global) variable declarations. Empty for sources that
        # only define functions; populated when the source declares variables
        # outside of any function body.
        self.globals: List["VarDecl"] = globals_ or []
        # Named integer constants from enum declarations (name -> value).
        # Shared dict instance also held by the parser so enums declared
        # inside function bodies are visible program-wide.
        self.enum_constants: Dict[str, int] = enum_constants if enum_constants is not None else {}
        # Struct definitions (tag -> ordered list of field names). Every
        # field occupies one 16-bit word slot, so a struct's byte size is
        # len(fields) * 2 and field i lives at byte offset i * 2.
        self.structs: Dict[str, List[str]] = structs if structs is not None else {}

class FunctionDef(ASTNode):
    def __init__(self, return_type: str, name: str, params: List["VarDecl"], body: List["ASTNode"]):
        self.return_type = return_type
        self.name = name
        self.params = params
        self.body = body

class VarDecl(ASTNode):
    def __init__(self, var_type: str, name: str, value: Optional["ASTNode"],
                 array_size: Optional["Expression"] = None,
                 init_list: Optional[List["Expression"]] = None,
                 pointer_depth: int = 0,
                 is_array_param: bool = False,
                 struct_tag: Optional[str] = None,
                 array_syntax: bool = False):
        self.var_type = var_type
        self.name = name
        self.value = value
        # Array support: `int arr[10];` sets array_size to the constant size
        # expression. `int arr[] = {1, 2, 3};` leaves array_size None and
        # infers the count from init_list.
        self.array_size = array_size
        # True when the declarator used explicit `[ ... ]` brackets
        # (`int arr[4]`, `int arr[] = {...}`, `struct Point pts[2]`).
        # Distinct from init_list: `struct Point p = {10, 20}` is a SCALAR
        # struct with an initializer list, not an array of structs.
        self.array_syntax = array_syntax
        # Initializer list: `int arr[3] = {1, 2, 3};` or scalar `int x = 5;`
        # uses `value` instead. init_list is a list of expressions.
        self.init_list = init_list
        # Pointer declarations (`int *p`, `char **s`) record how many '*'
        # preceded the name. Pointers occupy 2 bytes (a 16-bit address).
        self.pointer_depth = pointer_depth
        # Array parameters (`void f(int arr[])`) decay to an address; the
        # parameter slot holds the caller's array base address (2 bytes).
        self.is_array_param = is_array_param
        # Struct declarations (`struct Point p;`): var_type is 'struct' and
        # struct_tag names the definition providing the field layout.
        self.struct_tag = struct_tag

    @property
    def is_pointer(self) -> bool:
        return self.pointer_depth > 0

    @property
    def is_array(self) -> bool:
        # Note: init_list marks a declaration as an array for plain types
        # (`int arr[] = {1,2,3}`, `char buf[] = "Hi"`). Struct scalars with
        # an initializer list (`struct Point p = {10,20}`) report is_array
        # here too, but the codegen distinguishes true arrays via
        # array_syntax/array_size and treats those as scalar structs.
        return (self.array_syntax or self.array_size is not None
                or self.init_list is not None)

class Assignment(ASTNode):
    def __init__(self, name: str, value: "ASTNode"):
        self.name = name
        self.value = value

class Return(ASTNode):
    def __init__(self, value: Optional["ASTNode"]):
        self.value = value

class If(ASTNode):
    def __init__(self, cond: "Expression", then_body: List["ASTNode"], else_body: Optional[List["ASTNode"]]=None):
        self.cond = cond
        self.then_body = then_body
        self.else_body = else_body

class While(ASTNode):
    def __init__(self, cond: "Expression", body: List["ASTNode"]):
        self.cond = cond
        self.body = body

class DoWhile(ASTNode):
    """AST node for do-while loops: do { body } while (cond);"""
    def __init__(self, body: List["ASTNode"], cond: "Expression"):
        self.body = body
        self.cond = cond

class For(ASTNode):
    def __init__(self, init: Optional["ASTNode"], cond: Optional["Expression"], update: Optional["ASTNode"], body: List["ASTNode"]):
        self.init = init
        self.cond = cond
        self.update = update
        self.body = body

class Switch(ASTNode):
    """AST node for switch/case statements."""
    def __init__(self, expr: "Expression", cases: List["Case"], default_body: Optional[List["ASTNode"]]):
        self.expr = expr
        self.cases = cases
        self.default_body = default_body

class Case(ASTNode):
    """AST node for a single case label and its body."""
    def __init__(self, value: Optional["ASTNode"], body: List["ASTNode"]):
        self.value = value  # None for 'default' case
        self.body = body

class Break(ASTNode):
    """break statement - exits the innermost loop or switch."""

class Continue(ASTNode):
    """continue statement - skips to next loop iteration."""

class FuncCall(ASTNode):
    def __init__(self, name: str, args: List["Expression"]):
        self.name = name
        self.args = args

class Cast(Expression):
    """Type cast expression node: (int)expr, (char)expr, (string)expr, (binary)expr."""
    def __init__(self, target_type: str, expr: "Expression"):
        self.target_type = target_type
        self.expr = expr

class ArrayAccess(Expression):
    """Array element access: arr[index]."""
    def __init__(self, name: str, index: "Expression"):
        self.name = name
        self.index = index

class ArrayAssignment(ASTNode):
    """Assignment to an array element: arr[index] = value (or compound op)."""
    def __init__(self, target: "ArrayAccess", value: "Expression"):
        self.target = target
        self.value = value

class MemberAccess(Expression):
    """Struct member access: base.field (dot) or base->field (arrow).

    base is an Identifier (struct variable or pointer to struct) or an
    ArrayAccess (element of an array of structs)."""
    def __init__(self, base: "Expression", field: str, arrow: bool = False):
        self.base = base
        self.field = field
        self.arrow = arrow

    def root_name(self) -> Optional[str]:
        """Name of the identifier at the base of the access chain, if any."""
        node = self.base
        while isinstance(node, MemberAccess):
            node = node.base
        if isinstance(node, Identifier):
            return node.name
        if isinstance(node, ArrayAccess):
            return node.name
        return None

class MemberAssignment(ASTNode):
    """Assignment to a struct member: p.field = value (or compound op)."""
    def __init__(self, target: "MemberAccess", value: "Expression"):
        self.target = target
        self.value = value

class TernaryOp(Expression):
    """Ternary conditional expression: cond ? then_expr : else_expr."""
    def __init__(self, cond: "Expression", then_expr: "Expression", else_expr: "Expression"):
        self.cond = cond
        self.then_expr = then_expr
        self.else_expr = else_expr

class PrefixOp(Expression):
    """Prefix increment/decrement: ++i or --i (yields the NEW value)."""
    def __init__(self, op: str, operand: "Expression"):
        self.op = op
        self.operand = operand

class AddressOf(Expression):
    """Unary & operator: address-of a variable or array element."""
    def __init__(self, operand: "Expression"):
        self.operand = operand

class Deref(Expression):
    """Unary * operator: dereference a pointer (load through an address)."""
    def __init__(self, operand: "Expression"):
        self.operand = operand

class DerefAssignment(ASTNode):
    """Assignment through a pointer: *ptr = value (or compound op)."""
    def __init__(self, target: "Deref", value: "Expression"):
        self.target = target
        self.value = value

class SizeofExpr(Expression):
    """sizeof(type) or sizeof(expr): compile-time size in bytes."""
    def __init__(self, target):
        # target is either a type-name string ('int', 'char', ...) or an
        # expression node whose inferred type determines the size.
        self.target = target

class Parser:
    def __init__(self, tokens: List[Token], source_path: Optional[str] = None,
                 include_state: Optional[Dict] = None):
        # Normalize storage qualifiers / type modifiers up front so every
        # grammar rule can expect exactly one base-type keyword (see
        # _normalize_type_tokens).
        self.tokens = Parser._normalize_type_tokens(tokens)
        self.pos = 0
        self.current = self.tokens[self.pos]
        # Enum constants accumulate here as enum declarations are parsed;
        # shared with the resulting Program node.
        self.enum_constants: Dict[str, int] = {}
        # Struct definitions accumulate here as `struct Tag { ... };`
        # declarations are parsed; shared with the resulting Program node.
        self.struct_defs: Dict[str, List[str]] = {}
        # Multi-file support: source_path anchors relative include/inherits
        # paths to the directory of the file being parsed. include_state is
        # shared across the whole compilation so cycles are detected and
        # diamond includes deduped regardless of nesting depth.
        import os as _os
        self.source_path = source_path
        self.base_dir = (
            _os.path.dirname(_os.path.abspath(source_path))
            if source_path else _os.getcwd()
        )
        if include_state is None:
            include_state = {'stack': [], 'seen': set()}
        self.include_state = include_state
        # Programs pulled in via `inherits` are buffered during parsing and
        # merged at EOF, because override decisions require the complete
        # set of names the inheriting program defines for itself.
        self.inherited_units: List["Program"] = []
        # Names merged via plain `include`. At EOF an inherited unit's
        # definition shadows a same-named included definition (the
        # inherited chain is "more derived"), while definitions written
        # directly in this file always win over both.
        self.included_fn_names: set = set()
        self.included_gl_names: set = set()

    @staticmethod
    def _normalize_type_tokens(tokens: List[Token]) -> List[Token]:
        """Collapse runs of storage qualifiers / type modifiers / base types
        into a single base-type KEYWORD token.

        C allows declarations like `static unsigned int x;` or functions
        like `long helper(void)`. Astrid's type system only distinguishes
        the base types, so any run of consecutive qualifier/modifier/
        base-type keywords is merged into its base type (defaulting to
        'int' when only modifiers appear). Single base-type keywords pass
        through unchanged, so constructs like the `int(x)` conversion call
        are unaffected."""
        mergeable = STORAGE_QUALIFIERS | TYPE_MODIFIERS | BASE_TYPES
        out: List[Token] = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok.type == 'KEYWORD' and tok.value in mergeable:
                j = i
                while (j < len(tokens) and tokens[j].type == 'KEYWORD'
                       and tokens[j].value in mergeable):
                    j += 1
                base = 'int'
                for k in range(i, j):
                    if tokens[k].value in BASE_TYPES:
                        base = tokens[k].value
                out.append(Token('KEYWORD', base, tok.line, tok.column))
                i = j
                continue
            out.append(tok)
            i += 1
        return out

    def advance(self):
        self.pos += 1
        if self.pos < len(self.tokens):
            self.current = self.tokens[self.pos]
        else:
            self.current = Token('EOF', '', self.current.line, self.current.column)

    def expect(self, type_, value=None):
        if self.current.type != type_ or (value is not None and self.current.value != value):
            raise SyntaxError(f"Expected {type_} {value}, got {self.current.type} {self.current.value}")
        self.advance()

    def _skip_const(self):
        """Consume any leading 'const' qualifiers."""
        while self.current.type == 'KEYWORD' and self.current.value == 'const':
            self.advance()

    @staticmethod
    def _unescape_string(s: str) -> str:
        """Resolve backslash escapes in a raw string/char literal.

        Handles \\n \\t \\r \\\\ \\" \\' \\0 and \\xNN hex escapes. Unknown
        escapes keep the escaped character itself (lenient, like many C
        compilers' warnings).
        """
        out = []
        i = 0
        simple = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\',
                  '"': '"', "'": "'", '0': '\0',
                  # Extended C escape sequences:
                  'a': '\a',   # bell (7)
                  'b': '\b',   # backspace (8)
                  'f': '\f',   # form feed (12)
                  'v': '\v',   # vertical tab (11)
                  '?': '?',    # trigraph-escape question mark
                  }
        while i < len(s):
            ch = s[i]
            if ch == '\\' and i + 1 < len(s):
                nxt = s[i + 1]
                if nxt in simple:
                    out.append(simple[nxt])
                    i += 2
                    continue
                if nxt in ('x', 'X') and i + 3 <= len(s):
                    try:
                        out.append(chr(int(s[i + 2:i + 4], 16)))
                        i += 4
                        continue
                    except ValueError:
                        pass
                out.append(nxt)
                i += 2
                continue
            out.append(ch)
            i += 1
        return ''.join(out)

    def parse(self) -> "Program":
        functions = []
        globals_: List[VarDecl] = []
        while self.current.type != 'EOF':
            # Multi-file directives: include / inherits "file";
            if (self.current.type == 'KEYWORD'
                    and self.current.value in ('include', 'inherits')):
                mode = self.current.value
                self._parse_file_directive(mode, functions, globals_)
                continue
            # Enum declarations introduce named integer constants usable
            # anywhere a compile-time number is expected.
            if self.current.type == 'KEYWORD' and self.current.value == 'enum':
                self.parse_enum()
                continue
            # Top-level const qualifiers prefix either functions or globals.
            if self.current.type == 'KEYWORD' and self.current.value == 'const':
                self.advance()
                continue
            # Top-level struct definitions and struct-typed global variables:
            #   struct Tag { int a; int b };   -- definition
            #   struct Tag p;  struct Tag pts[4];  -- variables
            if self.current.type == 'KEYWORD' and self.current.value == 'struct':
                tag_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
                if tag_tok is None or tag_tok.type != 'IDENTIFIER':
                    raise SyntaxError(
                        f"Expected a struct tag name after 'struct' "
                        f"(line {self.current.line})")
                after = (self.tokens[self.pos + 2]
                         if self.pos + 2 < len(self.tokens) else None)
                if after is not None and after.type == 'DELIMITER' and after.value == '{':
                    self.parse_struct_definition()
                    continue
                # Function returning a struct (`struct Point make()`) is not
                # supported: the name would be followed by '('.
                name_tok = after
                call_tok = (self.tokens[self.pos + 3]
                            if self.pos + 3 < len(self.tokens) else None)
                if (name_tok is not None and name_tok.type == 'IDENTIFIER'
                        and call_tok is not None
                        and call_tok.type == 'DELIMITER'
                        and call_tok.value == '('):
                    raise SyntaxError(
                        f"Returning structs from functions is not supported "
                        f"(line {self.current.line})")
                new_globals = self.parse_var_decl(struct_tag=tag_tok.value)
                for g in new_globals:
                    if any(e.name == g.name for e in globals_):
                        raise SyntaxError(
                            f"Duplicate definition of global '{g.name}' "
                            f"at top level")
                    globals_.append(g)
                continue
            if (self.current.type == 'KEYWORD'
                    and self.current.value in {'int', 'char', 'string', 'binary', 'void'}):
                # Distinguish a function definition/prototype from a global
                # variable declaration by looking ahead past any pointer
                # stars: `type [*]* name(` is a function, anything else
                # (`type name;`, `type name[N];`, `type name = ...`) is a
                # global variable declaration.
                j = self.pos + 1
                while (j < len(self.tokens) and self.tokens[j].type == 'OPERATOR'
                       and self.tokens[j].value == '*'):
                    j += 1
                name_tok = self.tokens[j] if j < len(self.tokens) else None
                after_tok = self.tokens[j + 1] if j + 1 < len(self.tokens) else None
                if (name_tok is not None and name_tok.type == 'IDENTIFIER'
                        and after_tok is not None and after_tok.type == 'DELIMITER'
                        and after_tok.value == '('):
                    func = self.parse_function()
                    if func is not None:  # None => prototype-only declaration
                        if any(e.name == func.name for e in functions):
                            raise SyntaxError(
                                f"Duplicate definition of function "
                                f"'{func.name}' at top level")
                        functions.append(func)
                elif self.current.value == 'void':
                    raise SyntaxError(
                        f"Unexpected 'void' at top level (line {self.current.line})")
                else:
                    new_globals = self.parse_var_decl()
                    for g in new_globals:
                        if any(e.name == g.name for e in globals_):
                            raise SyntaxError(
                                f"Duplicate definition of global '{g.name}' "
                                f"at top level")
                        globals_.append(g)
            else:
                func = self.parse_function()
                if any(e.name == func.name for e in functions):
                    raise SyntaxError(
                        f"Duplicate definition of function '{func.name}' "
                        f"at top level")
                functions.append(func)
        # Apply inherited ("base") units now that the inheriting program's
        # own definitions are fully known: a base function/global is used
        # only when the child does not define its own version (override).
        own_fn_names = {f.name for f in functions} - self.included_fn_names
        own_gl_names = {g.name for g in globals_} - self.included_gl_names
        for unit in self.inherited_units:
            for f in unit.functions:
                if f.name in own_fn_names:
                    continue  # this file's own definition wins
                idx = next((i for i, e in enumerate(functions)
                            if e.name == f.name), None)
                if idx is not None:
                    functions[idx] = f  # shadow a plain-include definition
                else:
                    functions.append(f)
                own_fn_names.add(f.name)
            for g in unit.globals:
                if g.name in own_gl_names:
                    continue
                idx = next((i for i, e in enumerate(globals_)
                            if e.name == g.name), None)
                if idx is not None:
                    globals_[idx] = g
                else:
                    globals_.append(g)
                own_gl_names.add(g.name)
            # Base-file enum constants fill gaps only; names the inheriting
            # program declared itself keep their own values.
            for name, value in unit.enum_constants.items():
                self.enum_constants.setdefault(name, value)
            # Base-file struct definitions fill gaps only (same override
            # rule as enums: the child's own definitions win).
            for tag, fields in unit.structs.items():
                self.struct_defs.setdefault(tag, fields)
        return Program(functions, globals_, self.enum_constants, self.struct_defs)

    # ------------------------------------------------------------------
    # Multi-file compilation units: include / inherits
    # ------------------------------------------------------------------

    def _parse_file_directive(self, mode: str,
                              functions: List["FunctionDef"],
                              globals_: List["VarDecl"]):
        """Parse `include "file";` / `inherits "file";` and merge the file.

        include  -- strict splice: every definition is added; redefining an
                    existing function/global is an error.
        inherits -- buffered as a base unit and merged at EOF; definitions
                    from this program shadow (override) the base's.
        """
        self.advance()  # consume 'include' / 'inherits' keyword
        tok = self.current
        if tok.type != 'STRING':
            raise SyntaxError(
                f"Expected a quoted file name after '{mode}' "
                f"(line {tok.line}), got {tok.type} {tok.value!r}")
        raw = tok.value
        line = tok.line
        self.advance()
        if self.current.type == 'DELIMITER' and self.current.value == ';':
            self.advance()
        unit = self._load_unit(raw[1:-1], mode, line)
        if unit is None:
            return  # duplicate include: already merged elsewhere (pragma-once style)
        if mode == 'include':
            self._merge_include_unit(unit, functions, globals_)
        else:
            self.inherited_units.append(unit)

    def _resolve_include_path(self, filename: str, mode: str, line: int) -> str:
        """Resolve an include/inherits path relative to the current file."""
        import os as _os
        if _os.path.isabs(filename):
            resolved = filename
        else:
            resolved = _os.path.join(self.base_dir, filename)
        resolved = _os.path.normpath(resolved)
        if not _os.path.isfile(resolved):
            raise SyntaxError(
                f"{mode} file not found: {filename!r} "
                f"(resolved to {resolved!r}, line {line})")
        return _os.path.abspath(resolved)

    def _load_unit(self, filename: str, mode: str, line: int) -> Optional["Program"]:
        """Tokenize + parse an included/inherited file into a Program.

        Returns None when the same file was already pulled in anywhere in
        the compilation (diamond includes are merged exactly once). Raises
        on missing files and include cycles."""
        import os as _os
        resolved = self._resolve_include_path(filename, mode, line)
        stack = self.include_state['stack']
        seen = self.include_state['seen']
        if resolved in stack:
            chain = ' -> '.join(stack + [resolved])
            raise SyntaxError(
                f"Circular {mode} detected (line {line}): {chain}")
        if resolved in seen:
            return None
        seen.add(resolved)
        with open(resolved, 'r', encoding='utf-8') as f:
            source = f.read()
        sub_tokens = Lexer(source).tokenize()
        sub_parser = Parser(sub_tokens, source_path=resolved,
                            include_state=self.include_state)
        stack.append(resolved)
        try:
            unit = sub_parser.parse()
        finally:
            stack.pop()
        return unit

    def _merge_include_unit(self, unit: "Program",
                            functions: List["FunctionDef"],
                            globals_: List["VarDecl"]):
        """Strictly merge an included Program: duplicates are errors.

        Enum constants merge too; conflicting values for the same constant
        name are errors (identical values are tolerated)."""
        existing_fns = {f.name for f in functions}
        existing_gls = {g.name for g in globals_}
        for f in unit.functions:
            if f.name in existing_fns:
                raise SyntaxError(
                    f"Duplicate definition of function '{f.name}' after "
                    f"include (previously defined in this unit or another "
                    f"included file)")
            existing_fns.add(f.name)
            functions.append(f)
        for g in unit.globals:
            if g.name in existing_gls:
                raise SyntaxError(
                    f"Duplicate definition of global '{g.name}' after "
                    f"include (previously defined in this unit or another "
                    f"included file)")
            existing_gls.add(g.name)
            globals_.append(g)
        self.included_fn_names |= {f.name for f in unit.functions}
        self.included_gl_names |= {g.name for g in unit.globals}
        for name, value in unit.enum_constants.items():
            if name in self.enum_constants and \
                    self.enum_constants[name] != value:
                raise SyntaxError(
                    f"Enum constant '{name}' redefined with a different "
                    f"value via include "
                    f"({self.enum_constants[name]} != {value})")
            self.enum_constants.setdefault(name, value)
        # Struct definitions merge strictly: redefining a tag with a
        # different layout after an include is an error.
        for tag, fields in unit.structs.items():
            if tag in self.struct_defs and self.struct_defs[tag] != fields:
                raise SyntaxError(
                    f"Struct '{tag}' redefined with a different layout via "
                    f"include")
            self.struct_defs.setdefault(tag, fields)

    def parse_enum(self):
        """Parse an enum declaration: enum [Tag] { A, B = 5, C };

        Constant names and values are recorded in self.enum_constants
        (shared with the Program node). Values auto-increment from 0 and
        reset when an explicit `= expr` is given, matching C semantics."""
        self.expect('KEYWORD', 'enum')
        if self.current.type == 'IDENTIFIER':
            self.advance()  # optional tag name (not tracked further)
        if not (self.current.type == 'DELIMITER' and self.current.value == '{'):
            # Bare tag reference or forward declaration: nothing to record.
            if self.current.type == 'DELIMITER' and self.current.value == ';':
                self.advance()
            return
        self.advance()  # consume '{'
        next_value = 0
        while not (self.current.type == 'DELIMITER' and self.current.value == '}'):
            cname = self.current.value
            self.expect('IDENTIFIER')
            if self.current.type == 'OPERATOR' and self.current.value == '=':
                self.advance()
                next_value = self._parse_enum_const_value()
            self.enum_constants[cname] = next_value
            next_value += 1
            if self.current.type == 'DELIMITER' and self.current.value == ',':
                self.advance()
        self.expect('DELIMITER', '}')
        if self.current.type == 'DELIMITER' and self.current.value == ';':
            self.advance()

    def _parse_enum_const_value(self) -> int:
        """Parse an explicit enum constant value: NUMBER, CHAR, another
        enum constant, optionally negated."""
        sign = 1
        if self.current.type == 'OPERATOR' and self.current.value == '-':
            sign = -1
            self.advance()
        tok = self.current
        if tok.type == 'NUMBER':
            self.advance()
            return sign * int(tok.value, 0)
        if tok.type == 'CHAR':
            self.advance()
            return sign * ord(Parser._unescape_string(tok.value.strip("'")))
        if tok.type == 'IDENTIFIER':
            self.advance()
            if tok.value in self.enum_constants:
                return sign * self.enum_constants[tok.value]
            raise SyntaxError(f"Unknown enum constant '{tok.value}' in enum initializer")
        raise SyntaxError(f"Invalid enum constant value near {tok}")

    def parse_struct_definition(self):
        """Parse a struct definition: struct Tag { int x; int y, z; };

        Every field occupies one 16-bit word slot regardless of its base
        type (mirroring how Astrid locals give char variables full word
        slots), so field i lives at byte offset i*2 and the struct's byte
        size is len(fields) * 2. The definition is recorded in
        self.struct_defs; redefining a tag with a different layout is an
        error."""
        self.expect('KEYWORD', 'struct')
        tag = self.current.value
        self.expect('IDENTIFIER')
        self.expect('DELIMITER', '{')
        fields: List[str] = []
        while not (self.current.type == 'DELIMITER' and self.current.value == '}'):
            ftype = self.current.value
            if self.current.type != 'KEYWORD' or \
                    ftype not in {'int', 'char', 'string', 'binary'}:
                raise SyntaxError(
                    f"Unsupported struct field type '{ftype}' in struct "
                    f"'{tag}' (line {self.current.line})")
            self.advance()
            while True:
                fname = self.current.value
                self.expect('IDENTIFIER')
                if fname in fields:
                    raise SyntaxError(
                        f"Duplicate field '{fname}' in struct '{tag}' "
                        f"(line {self.current.line})")
                fields.append(fname)
                if self.current.type == 'DELIMITER' and self.current.value == ',':
                    self.advance()
                else:
                    break
            # Field terminator: ';' is the C form, but a '}' directly after
            # the last field is accepted for leniency.
            if self.current.type == 'DELIMITER' and self.current.value == ';':
                self.advance()
        self.expect('DELIMITER', '}')
        if not fields:
            raise SyntaxError(f"Struct '{tag}' has no fields")
        if tag in self.struct_defs and self.struct_defs[tag] != fields:
            raise SyntaxError(
                f"Struct '{tag}' redefined with a different layout")
        self.struct_defs[tag] = fields
        if self.current.type == 'DELIMITER' and self.current.value == ';':
            self.advance()

    def parse_function(self) -> Optional["FunctionDef"]:
        return_type = self.current.value
        self.expect('KEYWORD')
        # Pointer-returning functions: `int *get_ptr() { ... }`
        pointer_depth = 0
        while self.current.type == 'OPERATOR' and self.current.value == '*':
            pointer_depth += 1
            self.advance()
        name = self.current.value
        self.expect('IDENTIFIER')
        self.expect('DELIMITER', '(')
        params = self.parse_params()
        self.expect('DELIMITER', ')')
        # Prototype declaration: `int add(int a, int b);` — no body. The
        # definition elsewhere provides the implementation; forward calls
        # resolve because the code generator pre-registers all functions.
        if self.current.type == 'DELIMITER' and self.current.value == ';':
            self.advance()
            return None
        self.expect('DELIMITER', '{')
        body = self.parse_block()
        self.expect('DELIMITER', '}')
        return FunctionDef(return_type, name, params, body)

    def parse_params(self) -> List["VarDecl"]:
        params = []
        # Empty parameter list: f() or f(void)
        if self.current.type == 'DELIMITER' and self.current.value == ')':
            return params
        if self.current.type == 'KEYWORD' and self.current.value == 'void':
            nxt = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if nxt is not None and nxt.type == 'DELIMITER' and nxt.value == ')':
                self.advance()  # consume 'void'; caller consumes ')'
                return params
        while True:
            self._skip_const()
            var_type = self.current.value
            self.expect('KEYWORD')
            if var_type == 'struct':
                tag_tok = self.current
                if tag_tok.type != 'IDENTIFIER':
                    raise SyntaxError(
                        f"Expected a struct tag name after 'struct' in "
                        f"parameter list (line {tag_tok.line})")
                raise SyntaxError(
                    f"Struct parameters are not supported "
                    f"(parameter near line {tag_tok.line}); pass a pointer "
                    f"(struct Tag *p) or individual fields instead")
            pointer_depth = 0
            while self.current.type == 'OPERATOR' and self.current.value == '*':
                pointer_depth += 1
                self.advance()
            name = self.current.value
            self.expect('IDENTIFIER')
            is_array_param = False
            if self.current.type == 'DELIMITER' and self.current.value == '[':
                # Array parameter: void f(int arr[], int n). Arrays decay to
                # the base address, so the parameter slot holds an address.
                self.advance()
                if not (self.current.type == 'DELIMITER' and self.current.value == ']'):
                    self.parse_expression()  # size ignored (decay semantics)
                self.expect('DELIMITER', ']')
                is_array_param = True
            params.append(VarDecl(var_type, name, None,
                                  pointer_depth=pointer_depth,
                                  is_array_param=is_array_param))
            if self.current.type == 'DELIMITER' and self.current.value == ',':
                self.advance()
            else:
                break
        return params

    def parse_block(self) -> List[ASTNode]:
        stmts = []
        while self.current.type != 'DELIMITER' or self.current.value != '}':
            stmts.extend(self.parse_statement())
        return stmts

    def parse_statement(self):
        # Empty statement: a lone ';' is valid C and produces no code.
        if self.current.type == 'DELIMITER' and self.current.value == ';':
            self.advance()
            return []
        # Enum declarations are valid statements inside function bodies.
        if self.current.type == 'KEYWORD' and self.current.value == 'enum':
            self.parse_enum()
            return []
        # Struct definitions and struct-typed local variable declarations
        # are valid statements inside function bodies. A definition
        # (`struct Tag { ... };`) produces no code; a declaration
        # (`struct Tag p;` / `struct Tag pts[4] = {...};`) is a VarDecl.
        if self.current.type == 'KEYWORD' and self.current.value == 'struct':
            tag_tok = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            after = self.tokens[self.pos + 2] if self.pos + 2 < len(self.tokens) else None
            if tag_tok is not None and tag_tok.type == 'IDENTIFIER' and \
                    after is not None and after.type == 'DELIMITER' and after.value == '{':
                self.parse_struct_definition()
                return []
            if tag_tok is None or tag_tok.type != 'IDENTIFIER':
                raise SyntaxError(
                    f"Expected a struct tag name after 'struct' "
                    f"(line {self.current.line})")
            return self.parse_var_decl(struct_tag=tag_tok.value)
        # const-qualified declarations: `const int K = 5;` — consume the
        # qualifier, then fall through to the declaration handling below.
        if self.current.type == 'KEYWORD' and self.current.value == 'const':
            self.advance()
            self._skip_const()
        if self.current.type == 'KEYWORD' and self.current.value in {'int', 'char', 'void', 'string', 'binary'}:
            # int(x), char(x), string(x), binary(x) at statement start is a
            # function call, not a variable declaration. Peek for '(' after
            # the type keyword to distinguish.
            peek_pos = self.pos + 1
            if peek_pos < len(self.tokens) and self.tokens[peek_pos].value == '(':
                func_name = self.current.value
                self.advance()  # skip keyword
                self.expect('DELIMITER', '(')
                args = []
                if self.current.type != 'DELIMITER' or self.current.value != ')':
                    while True:
                        args.append(self.parse_expression())
                        if self.current.type == 'DELIMITER' and self.current.value == ',':
                            self.advance()
                        else:
                            break
                self.expect('DELIMITER', ')')
                self.expect('DELIMITER', ';')
                return [FuncCall(func_name, args)]
            return self.parse_var_decl()
        elif self.current.type == 'KEYWORD' and self.current.value == 'return':
            return [self.parse_return()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'if':
            return [self.parse_if()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'while':
            return [self.parse_while()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'do':
            return [self.parse_do_while()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'for':
            return [self.parse_for()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'switch':
            return [self.parse_switch()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'break':
            self.advance()
            self.expect('DELIMITER', ';')
            return [Break()]
        elif self.current.type == 'KEYWORD' and self.current.value == 'continue':
            self.advance()
            self.expect('DELIMITER', ';')
            return [Continue()]
        elif self.current.value == '{':
             self.advance()
             block = self.parse_block()
             self.expect('DELIMITER', '}')
             return block
        else:
            # Fallback to expression statement
            expr = self.parse_expression()
            self.expect('DELIMITER', ';')
            return [expr]

    def parse_var_decl(self, expect_semicolon=True, struct_tag=None):
        """Parse one or more variable declarators.

        struct_tag, when given, continues a declaration whose `struct Tag`
        header was already consumed by the caller (top level or statement
        start); the declared variables get var_type='struct'."""
        if struct_tag is None:
            var_type = self.current.value
            self.expect('KEYWORD')
        else:
            var_type = 'struct'
            # Consume the `struct Tag` header the caller peeked at.
            self.expect('KEYWORD', 'struct')
            self.expect('IDENTIFIER')
        decls = []
        while True:
            pointer_depth = 0
            while self.current.type == 'OPERATOR' and self.current.value == '*':
                pointer_depth += 1
                self.advance()
            name = self.current.value
            self.expect('IDENTIFIER')
            array_size = None
            init_list = None
            value = None
            is_array = False
            # Array declaration: int arr[SIZE]; or int arr[]; (size inferred)
            array_syntax = False
            if self.current.type == 'DELIMITER' and self.current.value == '[':
                self.advance()
                is_array = True
                array_syntax = True
                if not (self.current.type == 'DELIMITER' and self.current.value == ']'):
                    array_size = self.parse_expression()
                self.expect('DELIMITER', ']')
            if self.current.value == '=':
                self.advance()
                if self.current.type == 'DELIMITER' and self.current.value == '{':
                    # Initializer list: = { expr, expr, ... }
                    self.advance()
                    init_list = []
                    if not (self.current.type == 'DELIMITER' and self.current.value == '}'):
                        while True:
                            init_list.append(self.parse_expression())
                            if self.current.value == ',':
                                self.advance()
                            else:
                                break
                    self.expect('DELIMITER', '}')
                else:
                    value = self.parse_expression()
                    # C-style string initialization of char arrays:
                    #   char buf[] = "Hi";   /   char buf[16] = "Hi";
                    # Expands to per-character initializers plus a NUL
                    # terminator so strlen/strcpy-style builtins work.
                    if var_type == 'char' and is_array and isinstance(value, StringLiteral):
                        text = Parser._unescape_string(value.value)
                        init_list = [CharLiteral(ord(c)) for c in text]
                        init_list.append(CharLiteral(0))
                        if array_size is None:
                            array_size = Number(str(len(init_list)))
                        value = None
            decls.append(VarDecl(var_type, name, value, array_size, init_list,
                                 pointer_depth=pointer_depth,
                                 struct_tag=struct_tag,
                                 array_syntax=array_syntax))
            if self.current.value == ',':
                self.advance()
            else:
                break
        if expect_semicolon:
            self.expect('DELIMITER', ';')
        return decls

    def parse_return(self):
        self.expect('KEYWORD', 'return')
        value = None
        if self.current.value != ';':
            value = self.parse_expression()
        self.expect('DELIMITER', ';')
        return Return(value)

    def parse_if(self):
        self.expect('KEYWORD', 'if')
        self.expect('DELIMITER', '(')
        cond = self.parse_expression()
        self.expect('DELIMITER', ')')
        then_body = self.parse_statement()
        else_body = None
        if self.current.value == 'else':
            self.advance()
            else_body = self.parse_statement()
        return If(cond, then_body, else_body)

    def parse_while(self):
        self.expect('KEYWORD', 'while')
        self.expect('DELIMITER', '(')
        cond = self.parse_expression()
        self.expect('DELIMITER', ')')
        body = self.parse_statement()
        return While(cond, body)

    def parse_do_while(self):
        """Parse: do { body } while (cond);"""
        self.expect('KEYWORD', 'do')
        body = self.parse_statement()
        self.expect('KEYWORD', 'while')
        self.expect('DELIMITER', '(')
        cond = self.parse_expression()
        self.expect('DELIMITER', ')')
        self.expect('DELIMITER', ';')
        return DoWhile(body, cond)

    def parse_for(self):
        self.expect('KEYWORD', 'for')
        self.expect('DELIMITER', '(')

        init = None
        if self.current.value != ';':
            if self.current.type == 'KEYWORD' and self.current.value in {'int', 'char', 'string', 'binary'}:
                init = self.parse_var_decl(expect_semicolon=False)  # This returns a list of decls
            else:
                init = self.parse_expression()
        self.expect('DELIMITER', ';')

        cond = None
        if self.current.value != ';':
            cond = self.parse_expression()
        self.expect('DELIMITER', ';')

        update = None
        if self.current.value != ')':
            update = self.parse_expression()
        self.expect('DELIMITER', ')')

        body = self.parse_statement()
        return For(init, cond, update, body)

    def parse_switch(self):
        """Parse: switch (expr) { case val1: ... case val2: ... default: ... }"""
        self.expect('KEYWORD', 'switch')
        self.expect('DELIMITER', '(')
        expr = self.parse_expression()
        self.expect('DELIMITER', ')')
        self.expect('DELIMITER', '{')

        cases: List[Case] = []
        default_body: Optional[List[ASTNode]] = None
        current_case: Optional[Case] = None

        while not (self.current.type == 'DELIMITER' and self.current.value == '}'):
            if self.current.type == 'KEYWORD' and self.current.value == 'case':
                self.advance()
                case_value = self.parse_expression()
                self.expect('DELIMITER', ':')
                current_case = Case(case_value, [])
                cases.append(current_case)
            elif self.current.type == 'KEYWORD' and self.current.value == 'default':
                self.advance()
                self.expect('DELIMITER', ':')
                current_case = Case(None, [])  # default case
                default_body = []
                current_case = None
            elif self.current.type == 'KEYWORD' and self.current.value == 'break':
                self.advance()
                self.expect('DELIMITER', ';')
                # break is a statement within a case body
                if current_case is not None:
                    current_case.body.append(Break())
                elif default_body is not None:
                    default_body.append(Break())
            elif self.current.value == '{':
                self.advance()
                # Allow block scope within a case
                block = self.parse_block()
                if current_case is not None:
                    current_case.body.extend(block)
                elif default_body is not None:
                    default_body.extend(block)
            else:
                # Regular statement
                stmt = self.parse_statement()
                # parse_statement returns a list of statements
                if current_case is not None:
                    current_case.body.extend(stmt)
                elif default_body is not None:
                    default_body.extend(stmt)

        self.expect('DELIMITER', '}')
        return Switch(expr, cases, default_body)

    def parse_expression(self):
        return self.parse_binary_op(1)  # Start with lowest precedence

    def get_precedence(self, op):
        if op in ['=', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>=']: return 1
        if op in ['||']: return 2
        if op in ['&&']: return 3
        if op in ['|']: return 4
        if op in ['^']: return 5
        if op in ['&']: return 6
        if op in ['==', '!=']: return 7
        if op in ['<', '>', '<=', '>=']: return 8
        if op in ['<<', '>>']: return 9
        if op in ['+', '-']: return 10
        if op in ['*', '/', '%']: return 11
        return 0

    def parse_binary_op(self, precedence=0):
        left = self.parse_unary()
        while True:
            op = self.current.value
            op_prec = self.get_precedence(op)
            if self.current.type != 'OPERATOR' or op_prec < precedence:
                break

            self.advance()

            if op_prec == 1:  # Right-associative assignment
                right = self.parse_binary_op(op_prec)
            else:  # Left-associative
                right = self.parse_binary_op(op_prec + 1)

            # Handle assignment as a special kind of binary op
            if op_prec == 1:
                if isinstance(left, Identifier):
                    # Handle compound assignment: x += 2 becomes x = x + 2
                    if op in ['+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>=']:
                        base_op = op[:-1]  # Remove trailing '=': '+', '-', '*', '/', '%', '&', '|', '^', '<<', '>>'
                        right = BinaryOp(Identifier(left.name), base_op, right)
                    left = Assignment(left.name, right)
                elif isinstance(left, ArrayAccess):
                    # Array element assignment: arr[i] = v, with compound
                    # forms decomposed like scalars (arr[i] += v becomes
                    # arr[i] = arr[i] + v).
                    if op in ['+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>=']:
                        base_op = op[:-1]
                        right = BinaryOp(ArrayAccess(left.name, left.index), base_op, right)
                    left = ArrayAssignment(left, right)
                elif isinstance(left, Deref):
                    # Assignment through a pointer: *p = v. Compound forms
                    # decompose the same way (*p += v becomes *p = *p + v).
                    if op in ['+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>=']:
                        base_op = op[:-1]
                        right = BinaryOp(Deref(left.operand), base_op, right)
                    left = DerefAssignment(left, right)
                elif isinstance(left, MemberAccess):
                    # Struct member assignment: p.x = v. Compound forms
                    # decompose like scalars/arrays (p.x += v becomes
                    # p.x = p.x + v); the codegen matches the compound
                    # shape structurally.
                    if op in ['+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>=']:
                        base_op = op[:-1]
                        right = BinaryOp(
                            MemberAccess(left.base, left.field, left.arrow),
                            base_op, right)
                    left = MemberAssignment(left, right)
                else:
                    raise SyntaxError("Invalid assignment target")
            else:
                left = BinaryOp(left, op, right)

        # Ternary conditional operator (?:). Binds tighter than assignment
        # but looser than ||, and is right-associative:
        #   a || b ? c : d  parses as (a || b) ? c : d
        #   a ? b : c ? d : e parses as a ? b : (c ? d : e)
        if (precedence <= 2 and self.current.value == '?'
                and self.current.type in ('OPERATOR', 'DELIMITER')):
            self.advance()
            then_expr = self.parse_binary_op(1)
            self.expect('DELIMITER', ':')
            else_expr = self.parse_binary_op(1)
            left = TernaryOp(left, then_expr, else_expr)

        return left

    def parse_unary(self):
        # Prefix increment/decrement: ++i / --i (C semantics: yields the
        # updated value, unlike postfix which yields the old value).
        if self.current.type == 'OPERATOR' and self.current.value in ('++', '--'):
            op = self.current.value
            self.advance()
            operand = self.parse_unary()
            if isinstance(operand, Deref):
                # ++(*p) / --(*p): increment/decrement the pointee VALUE.
                return PrefixOp(op, operand)
            if isinstance(operand, MemberAccess):
                # ++p.x / --p.y: increment/decrement the member in place.
                return PrefixOp(op, operand)
            if not isinstance(operand, Identifier):
                raise SyntaxError(f"Prefix '{op}' requires a variable operand")
            return PrefixOp(op, operand)

        if self.current.type == 'OPERATOR' and self.current.value in ('-', '+', '!', '~', '&', '*'):
            op = self.current.value
            self.advance()
            if op == '+':
                # Unary plus is a no-op in C.
                return self.parse_unary()
            if op == '&':
                operand = self.parse_unary()
                if not isinstance(operand, (Identifier, ArrayAccess, MemberAccess)):
                    raise SyntaxError("'&' requires a variable or array element operand")
                return AddressOf(operand)
            if op == '*':
                return Deref(self.parse_unary())
            right = self.parse_unary()
            return UnaryOp(op, right)

        expr = self.parse_primary()
        # Handle postfix operators
        while self.current.value in ['++', '--']:
            op = self.current.value
            self.advance()
            expr = PostfixOp(expr, op)
        return expr

    def parse_primary(self):
        token = self.current
        if token.type == 'NUMBER':
            self.advance()
            return Number(token.value)
        elif token.type == 'STRING':
            self.advance()
            raw = token.value.strip('"')
            # Adjacent string literal concatenation ("abc" "def" -> "abcdef"),
            # as in C. Escapes are resolved later by _unescape_string users.
            while self.current.type == 'STRING':
                raw += self.current.value.strip('"')
                self.advance()
            return StringLiteral(raw)
        elif token.type == 'CHAR':
            self.advance()
            # Parse char literal value, resolving all escape sequences
            # (\n, \t, \r, \0, \\, \', \xNN) via the shared unescaper.
            char_content = token.value.strip("'")
            unescaped = Parser._unescape_string(char_content)
            if len(unescaped) != 1:
                raise SyntaxError(f"Invalid char literal: {token.value}")
            return CharLiteral(ord(unescaped))
        elif token.type == 'IDENTIFIER':
            self.advance()
            if self.current.type == 'DELIMITER' and self.current.value == '(':
                self.advance()
                args = []
                if self.current.type != 'DELIMITER' or self.current.value != ')':
                    while True:
                        args.append(self.parse_expression())
                        if self.current.type == 'DELIMITER' and self.current.value == ',':
                            self.advance()
                        else:
                            break
                self.expect('DELIMITER', ')')
                return FuncCall(token.value, args)
            # Array indexing: arr[expr] (chained indexing not needed for
            # 1-D arrays, but allow postfix on the result for future use).
            node = None
            if self.current.type == 'DELIMITER' and self.current.value == '[':
                self.advance()
                index = self.parse_expression()
                self.expect('DELIMITER', ']')
                node = ArrayAccess(token.value, index)
            if node is None:
                node = Identifier(token.value)
            # Struct member access: p.field and arrays/pointers chain on
            # afterwards: pts[i].field, ptr->field. Repeated '.'/'->'
            # would be nested structs (unsupported); the codegen rejects
            # those bases with a clear error.
            while True:
                if self.current.type == 'DELIMITER' and self.current.value == '.':
                    self.advance()
                    field = self.current.value
                    self.expect('IDENTIFIER')
                    node = MemberAccess(node, field, arrow=False)
                elif self.current.type == 'OPERATOR' and self.current.value == '->':
                    self.advance()
                    field = self.current.value
                    self.expect('IDENTIFIER')
                    node = MemberAccess(node, field, arrow=True)
                else:
                    break
            return node
        elif token.type == 'KEYWORD' and token.value == 'sizeof':
            # sizeof(type) or sizeof(expr): compile-time byte size.
            self.advance()
            self.expect('DELIMITER', '(')
            if (self.current.type == 'KEYWORD'
                    and self.current.value in {'int', 'char', 'string', 'binary', 'void'}):
                type_name = self.current.value
                self.advance()
                # Allow pointer forms: sizeof(int*)
                while self.current.type == 'OPERATOR' and self.current.value == '*':
                    self.advance()
                self.expect('DELIMITER', ')')
                return SizeofExpr(type_name)
            if (self.current.type == 'KEYWORD'
                    and self.current.value == 'struct'):
                # sizeof(struct Tag): total byte size of the struct layout.
                self.advance()
                tag_tok = self.current
                self.expect('IDENTIFIER')
                self.expect('DELIMITER', ')')
                return SizeofExpr(('struct', tag_tok.value))
            inner = self.parse_expression()
            self.expect('DELIMITER', ')')
            return SizeofExpr(inner)
        elif token.type == 'KEYWORD' and token.value in {'int', 'char', 'string', 'binary'}:
            # Builtin conversion functions used inside expressions, e.g.
            # `int b = int(a);` or `return char(c);`. The lexer classifies
            # these names as KEYWORDs, so they never reach the IDENTIFIER
            # branch above. A type keyword directly followed by '(' is a
            # function call; anything else is a syntax error (casts like
            # `(int)x` are handled by the '(' delimiter branch below).
            next_token = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if next_token is not None and next_token.type == 'DELIMITER' and next_token.value == '(':
                func_name = token.value
                self.advance()          # consume type keyword
                self.expect('DELIMITER', '(')
                args = []
                if self.current.type != 'DELIMITER' or self.current.value != ')':
                    while True:
                        args.append(self.parse_expression())
                        if self.current.type == 'DELIMITER' and self.current.value == ',':
                            self.advance()
                        else:
                            break
                self.expect('DELIMITER', ')')
                return FuncCall(func_name, args)
            raise SyntaxError(f"Unexpected token in expression: {self.current}")
        elif token.type == 'DELIMITER' and token.value == '(':
            self.advance()
            # Check for type cast: (int)expr, (char)expr, (string)expr, (binary)expr
            if self.current.type == 'KEYWORD' and self.current.value in {'int', 'char', 'string', 'binary'}:
                target_type = self.current.value
                self.advance()
                self.expect('DELIMITER', ')')
                cast_expr = self.parse_unary()
                return Cast(target_type, cast_expr)
            expr = self.parse_expression()
            self.expect('DELIMITER', ')')
            return expr
        else:
            raise SyntaxError(f"Unexpected token in expression: {self.current}")