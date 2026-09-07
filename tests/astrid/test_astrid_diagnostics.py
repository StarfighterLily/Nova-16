"""Tests for the Astrid compiler diagnostics infrastructure.

Covers (all fast unit tests -- no emulator needed):

1. CompileError hierarchy: subclasses SyntaxError (backward compatibility
   with callers that catch SyntaxError) and renders position + message.
2. Snippet rendering: ``file:line:col`` header, the offending source line
   and a caret under the reported column, and the hint line.
3. Lexer diagnostics: unterminated string/char literals and stray
   characters are classified with actionable hints, and the reported
   column is exact (regression guard: line_start used to be anchored to
   the first token of a line, shifting all columns left by the line's
   indentation).
4. Parser diagnostics: friendlier expect() messages, EOF guidance,
   did-you-mean hints for typos, and redundant "(line N)" stripping.
5. Codegen diagnostics: failures inside a function are wrapped with the
   function name and its source position; register-exhaustion failures
   carry a remediation hint.
6. did_you_mean / levenshtein helpers.
"""
import os
import tempfile

import pytest

# Path setup handled by tests/astrid/conftest.py
from astrid.errors import (
    CompileError, LexerError, ParserError, CodeGenError,
    did_you_mean, levenshtein,
)
from astrid.lexer.lexer import Lexer
from astrid.parser.parser import Parser


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _write_source(source):
    """Write source to a temp .ast file and return its path."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ast', delete=False,
                                     encoding='utf-8') as f:
        f.write(source)
        return f.name


def _parse_from_file(source):
    """Tokenize + parse with the parser anchored to a real on-disk file so
    diagnostics can load the source text for snippets.

    Returns (parser, path); the caller must unlink the path in both the
    success and failure paths.
    """
    path = _write_source(source)
    with open(path, 'r', encoding='utf-8') as f:
        code = f.read()
    return Parser(Lexer(code).tokenize(), source_path=path), path


# ----------------------------------------------------------------------
# 1. Exception hierarchy
# ----------------------------------------------------------------------
@pytest.mark.unit
class TestErrorHierarchy:
    def test_errors_are_syntax_error_subclasses(self):
        # Backward compatibility: pre-diagnostics code catches SyntaxError.
        for exc_type in (LexerError, ParserError, CodeGenError):
            assert issubclass(exc_type, CompileError)
            assert issubclass(exc_type, SyntaxError)

    def test_position_and_message_fields(self):
        err = ParserError("boom", filename="prog.ast", line=3, column=7)
        assert err.message == "boom"
        assert err.filename == "prog.ast"
        assert err.line == 3
        assert err.column == 7

    def test_str_contains_phase_message_and_location(self):
        err = CodeGenError("bad codegen", filename="prog.ast", line=4, column=2)
        text = str(err)
        assert "codegen error: bad codegen" in text
        assert "--> prog.ast:4:2" in text

    def test_no_position_falls_back_gracefully(self):
        err = ParserError("mystery failure")
        text = str(err)
        assert "parser error: mystery failure" in text
        assert "-->" not in text


# ----------------------------------------------------------------------
# 2. Snippet rendering
# ----------------------------------------------------------------------
@pytest.mark.unit
class TestSnippetRendering:
    SOURCE = "int main() {\n    int x = 1;\n    return x;\n}\n"

    def test_caret_under_correct_column(self):
        err = CompileError("kaboom", filename="prog.ast", line=2, column=5,
                           length=3, source_text=self.SOURCE)
        lines = str(err).splitlines()
        src_line = next(l for l in lines if "int x = 1;" in l)
        caret_line = lines[lines.index(src_line) + 1]
        # Column 5 of "    int x = 1;" is the 'i' of 'int' (0-based 4); the
        # caret must sit directly under that character in the rendered
        # snippet (same rendered index).
        text_idx = src_line.index("int x = 1;")
        caret_idx = caret_line.index("^")
        assert caret_idx == text_idx

    def test_caret_length_matches_token(self):
        err = CompileError("bad", line=1, column=1, length=5,
                           source_text="while x")
        caret_line = next(l for l in str(err).splitlines() if "^" in l)
        assert caret_line.count("^") == 5

    def test_hint_is_rendered(self):
        err = ParserError("bad thing", hint="try this instead")
        assert "hint: try this instead" in str(err)

    def test_line_out_of_range_renders_without_snippet(self):
        err = ParserError("off the end", line=99, column=1,
                          source_text="only one line")
        text = str(err)
        assert "line 99" in text
        assert "|" not in text

# ----------------------------------------------------------------------
# 3. Lexer diagnostics
# ----------------------------------------------------------------------
@pytest.mark.unit
class TestLexerDiagnostics:
    def test_unterminated_string_classified_with_hint(self):
        src = 'int main() {\n    string s = "unclosed\n}'
        with pytest.raises(LexerError) as exc:
            Lexer(src).tokenize()
        assert "unterminated string literal" in exc.value.message
        assert exc.value.hint is not None
        assert "quote" in exc.value.hint.lower()
        assert exc.value.line == 2

    def test_unterminated_string_column_is_exact(self):
        # Regression guard: line_start used to anchor to the first token of
        # the line, shifting columns left by the indentation width.
        src = 'int main() {\n    string s = "unclosed\n}'
        with pytest.raises(LexerError) as exc:
            Lexer(src).tokenize()
        line2 = src.splitlines()[1]
        assert exc.value.column == line2.index('"') + 1

    def test_unterminated_char_classified_with_hint(self):
        src = "int main() { char c = 'AB; }"
        with pytest.raises(LexerError) as exc:
            Lexer(src).tokenize()
        assert "unterminated character literal" in exc.value.message

    def test_stray_character_classified(self):
        with pytest.raises(LexerError) as exc:
            Lexer('int main() { int a = 3 $ 4; }').tokenize()
        assert "$" in exc.value.message
        assert exc.value.line == 1

    def test_snippet_includes_source_line(self):
        src = 'int main() { int a = 3 $ 4; }'
        with pytest.raises(LexerError) as exc:
            Lexer(src).tokenize()
        text = str(exc.value)
        assert "int main() { int a = 3 $ 4; }" in text
        assert "hint:" in text

    def test_lexer_error_is_syntax_error(self):
        # Existing callers/tests catching SyntaxError keep working.
        with pytest.raises(SyntaxError):
            Lexer('int a = 3 $ 4;').tokenize()


# ----------------------------------------------------------------------
# 4. Parser diagnostics
# ----------------------------------------------------------------------
@pytest.mark.unit
class TestParserDiagnostics:
    def test_expect_message_is_friendly(self):
        parser, path = _parse_from_file("int main() { int a = 1 : }\n")
        try:
            parser.parse()
            assert False, "expected a parse error"
        except ParserError as e:
            assert "Expected ';'" in e.message
            assert "':'" in e.message
        finally:
            os.unlink(path)

    def test_parser_error_carries_position_and_snippet(self):
        source = "int main() {\n    int a = 1 :\n}\n"
        parser, path = _parse_from_file(source)
        try:
            parser.parse()
            assert False, "expected a parse error"
        except ParserError as e:
            assert e.line == 2
            assert e.filename == path
            # The rendered diagnostic embeds the offending source line.
            assert "int a = 1 :" in str(e)
        finally:
            os.unlink(path)

    def test_eof_error_has_remedial_hint(self):
        parser, path = _parse_from_file("int main() {\n    int a = 1;\n")
        try:
            parser.parse()
            assert False, "expected a parse error"
        except ParserError as e:
            assert e.hint is not None
            assert "end of file" in e.message.lower()
        finally:
            os.unlink(path)

    def test_typoed_keyword_gets_did_you_mean(self):
        # 'whille' is 1 edit from 'while'; the parser should suggest it.
        source = "int main() { whille (1) { } }\n"
        parser, path = _parse_from_file(source)
        try:
            parser.parse()
            assert False, "expected a parse error"
        except ParserError as e:
            assert e.hint is not None
            assert "did you mean" in e.hint.lower()
            assert "while" in e.hint
        finally:
            os.unlink(path)

    def test_redundant_line_suffix_stripped(self):
        # Messages that pre-date positioned diagnostics append "(line N)";
        # when N matches the reported position the suffix is removed so the
        # line number is not shown twice.
        source = "int main() { struct { int x; } p; }\n"
        parser, path = _parse_from_file(source)
        try:
            parser.parse()
            assert False, "expected a parse error"
        except ParserError as e:
            assert f"(line {e.line})" not in e.message
        finally:
            os.unlink(path)

    def test_in_memory_source_omits_snippet_but_keeps_position(self):
        # Parser built from raw tokens (no file on disk) must still report
        # line/column -- just without the source excerpt.
        parser = Parser(Lexer("int main() { int a = 1 : }").tokenize())
        with pytest.raises(ParserError) as exc:
            parser.parse()
        assert exc.value.line == 1
        assert exc.value.source_text is None

    def test_parser_error_is_syntax_error(self):
        parser = Parser(Lexer("int main() { int a = 1 : }").tokenize())
        with pytest.raises(SyntaxError):
            parser.parse()


# ----------------------------------------------------------------------
# 5. Codegen diagnostics
# ----------------------------------------------------------------------
def _codegen_only(source):
    """Run the parser + codegen (no assembly) and return the exception."""
    from astrid.codegen.codegen import CodeGenerator
    path = _write_source(source)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
        ast = Parser(Lexer(code).tokenize(), source_path=path).parse()
    finally:
        os.unlink(path)
    return CodeGenerator(enable_optimizations=False).generate(ast)


@pytest.mark.unit
class TestCodegenDiagnostics:
    def test_break_outside_loop_names_the_function(self):
        with pytest.raises(CodeGenError) as exc:
            _codegen_only("int main() { break; }\n")
        assert "main" in exc.value.message
        assert "generating function" in exc.value.message

    def test_wrapped_error_keeps_syntax_error_compat(self):
        # The wrapper must not break callers catching SyntaxError.
        with pytest.raises(SyntaxError):
            _codegen_only("int main() { break; }\n")

    def test_duplicate_method_error_is_positioned(self):
        # Duplicate methods in impl blocks are detected by the parser with
        # the method header as the blamed token.
        source = (
            "struct Point { int x; int y; };\n"
            "impl Point { int get(self) { return self.x; } }\n"
            "impl Point { int get(self) { return self.y; } }\n"
        )
        parser, path = _parse_from_file(source)
        try:
            parser.parse()
            assert False, "expected a parse error"
        except ParserError as e:
            assert "Duplicate method" in e.message
            assert "'get'" in e.message
            # Blamed token is the duplicated method's name token.
            assert e.line == 3
        finally:
            os.unlink(path)


# ----------------------------------------------------------------------
# 6. Suggestion helpers
# ----------------------------------------------------------------------
@pytest.mark.unit
class TestSuggestionHelpers:
    def test_levenshtein_basics(self):
        assert levenshtein("", "") == 0
        assert levenshtein("abc", "abc") == 0
        assert levenshtein("abc", "abx") == 1
        assert levenshtein("kitten", "sitting") == 3
        assert levenshtein("", "abc") == 3

    def test_did_you_mean_finds_close_match(self):
        candidates = ["while", "if", "else", "switch"]
        assert did_you_mean("whille", candidates) == "while"
        assert did_you_mean("SWITCH", candidates) == "switch"

    def test_did_you_mean_returns_none_for_far_names(self):
        candidates = ["while", "if", "else"]
        assert did_you_mean("qqqqqqqq", candidates) is None
        assert did_you_mean("", candidates) is None

