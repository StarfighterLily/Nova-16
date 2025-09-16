#!/usr/bin/env python3
"""
Astrid 2.0 Language Server Protocol (LSP) Implementation
Provides IDE integration with syntax highlighting, error reporting, and code intelligence.
"""

import json
import logging
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re

# LSP protocol types
@dataclass
class Position:
    """Represents a position in a text document."""
    line: int
    character: int

@dataclass
class Range:
    """Represents a range in a text document."""
    start: Position
    end: Position

@dataclass
class Diagnostic:
    """Represents a diagnostic (error/warning/info)."""
    range: Range
    severity: int  # 1=Error, 2=Warning, 3=Info, 4=Hint
    message: str
    source: str = "astrid2"

@dataclass
class TextDocumentItem:
    """Represents a text document."""
    uri: str
    languageId: str
    version: int
    text: str

class AstridLanguageServer:
    """Astrid 2.0 Language Server implementation."""

    def __init__(self):
        self.documents: Dict[str, TextDocumentItem] = {}
        self.logger = logging.getLogger(__name__)

    def handle_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle LSP requests."""
        if method == "initialize":
            return self.handle_initialize(params)
        elif method == "textDocument/didOpen":
            return self.handle_did_open(params)
        elif method == "textDocument/didChange":
            return self.handle_did_change(params)
        elif method == "textDocument/didClose":
            return self.handle_did_close(params)
        elif method == "textDocument/completion":
            return self.handle_completion(params)
        elif method == "textDocument/hover":
            return self.handle_hover(params)
        elif method == "textDocument/signatureHelp":
            return self.handle_signature_help(params)
        elif method == "textDocument/definition":
            return self.handle_definition(params)
        elif method == "textDocument/documentSymbol":
            return self.handle_document_symbol(params)
        elif method == "workspace/symbol":
            return self.handle_workspace_symbol(params)
        elif method == "textDocument/publishDiagnostics":
            return self.handle_publish_diagnostics(params)
        else:
            self.logger.warning(f"Unhandled method: {method}")
            return None

    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "capabilities": {
                "textDocumentSync": 1,  # Full document sync
                "completionProvider": {
                    "resolveProvider": False,
                    "triggerCharacters": [".", "(", ","]
                },
                "hoverProvider": True,
                "signatureHelpProvider": {
                    "triggerCharacters": ["("],
                    "retriggerCharacters": [","]
                },
                "definitionProvider": True,
                "documentSymbolProvider": True,
                "workspaceSymbolProvider": True,
                "diagnosticProvider": {
                    "interFileDependencies": False,
                    "workspaceDiagnostics": False
                }
            }
        }

    def handle_did_open(self, params: Dict[str, Any]) -> None:
        """Handle textDocument/didOpen notification."""
        doc = params["textDocument"]
        self.documents[doc["uri"]] = TextDocumentItem(
            uri=doc["uri"],
            languageId=doc["languageId"],
            version=doc["version"],
            text=doc["text"]
        )
        # Trigger diagnostics
        self._publish_diagnostics(doc["uri"])

    def handle_did_change(self, params: Dict[str, Any]) -> None:
        """Handle textDocument/didChange notification."""
        uri = params["textDocument"]["uri"]
        if uri in self.documents:
            # Update document content
            for change in params["contentChanges"]:
                if "text" in change:
                    self.documents[uri].text = change["text"]
                    self.documents[uri].version = params["textDocument"]["version"]
            # Trigger diagnostics
            self._publish_diagnostics(uri)

    def handle_did_close(self, params: Dict[str, Any]) -> None:
        """Handle textDocument/didClose notification."""
        uri = params["textDocument"]["uri"]
        if uri in self.documents:
            del self.documents[uri]

    def handle_completion(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle textDocument/completion request."""
        position = params["position"]
        uri = params["textDocument"]["uri"]

        if uri not in self.documents:
            return {"items": []}

        doc = self.documents[uri]
        line = position["line"]
        character = position["character"]

        # Get the current line
        lines = doc.text.split('\n')
        if line >= len(lines):
            return {"items": []}

        current_line = lines[line][:character]

        # Determine completion context
        context = self._analyze_completion_context(current_line, character)

        items = []

        if context["type"] == "function_call":
            # Complete function parameters or function names
            items.extend(self._get_function_completion_items(context))
        elif context["type"] == "variable_declaration":
            # Complete type names
            items.extend(self._get_type_completion_items())
        elif context["type"] == "expression":
            # Complete variables, functions, keywords
            items.extend(self._get_expression_completion_items(doc, context))
        else:
            # General completion
            items.extend(self._get_general_completion_items())

        return {"items": items}

    def handle_hover(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle textDocument/hover request."""
        position = params["position"]
        uri = params["textDocument"]["uri"]

        if uri not in self.documents:
            return None

        doc = self.documents[uri]
        lines = doc.text.split('\n')
        if position["line"] >= len(lines):
            return None

        line = lines[position["line"]]
        word = self._get_word_at_position(line, position["character"])

        # Provide hover information for keywords and builtins
        hover_info = self._get_hover_info(word)
        if hover_info:
            return {
                "contents": {
                    "kind": "markdown",
                    "value": hover_info
                }
            }

        return None

    def handle_signature_help(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle textDocument/signatureHelp request."""
        position = params["position"]
        uri = params["textDocument"]["uri"]

        if uri not in self.documents:
            return None

        doc = self.documents[uri]
        lines = doc.text.split('\n')
        if position["line"] >= len(lines):
            return None

        line = lines[position["line"]]
        character = position["character"]

        # Find function call context
        call_context = self._find_function_call_context(line, character)
        if not call_context:
            return None

        function_name = call_context["function"]
        param_index = call_context["param_index"]

        # Get signature information for the function
        signature = self._get_function_signature(function_name)
        if not signature:
            return None

        return {
            "signatures": [signature],
            "activeSignature": 0,
            "activeParameter": param_index
        }

    def handle_definition(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle textDocument/definition request."""
        position = params["position"]
        uri = params["textDocument"]["uri"]

        if uri not in self.documents:
            return None

        doc = self.documents[uri]
        lines = doc.text.split('\n')
        if position["line"] >= len(lines):
            return None

        line = lines[position["line"]]
        word = self._get_word_at_position(line, position["character"])

        # Find definition location
        definition = self._find_definition(doc, word)
        if definition:
            return {
                "uri": uri,
                "range": definition
            }

        return None

    def handle_document_symbol(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle textDocument/documentSymbol request."""
        uri = params["textDocument"]["uri"]

        if uri not in self.documents:
            return []

        doc = self.documents[uri]
        return self._extract_document_symbols(doc)

    def handle_workspace_symbol(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle workspace/symbol request."""
        query = params.get("query", "")
        symbols = []

        for uri, doc in self.documents.items():
            doc_symbols = self._extract_document_symbols(doc)
            for symbol in doc_symbols:
                if query.lower() in symbol["name"].lower():
                    symbols.append({
                        "name": symbol["name"],
                        "kind": symbol["kind"],
                        "location": {
                            "uri": uri,
                            "range": symbol["range"]
                        }
                    })

        return symbols
        """Handle diagnostic publishing."""
        uri = params["textDocument"]["uri"]
        return self._publish_diagnostics(uri)

    def _publish_diagnostics(self, uri: str) -> Dict[str, Any]:
        """Analyze document and publish diagnostics."""
        if uri not in self.documents:
            return {"uri": uri, "diagnostics": []}

        doc = self.documents[uri]
        diagnostics = self._analyze_document(doc)

        return {
            "uri": uri,
            "diagnostics": [self._diagnostic_to_dict(d) for d in diagnostics]
        }

    def _analyze_document(self, doc: TextDocumentItem) -> List[Diagnostic]:
        """Analyze document for syntax and semantic errors."""
        diagnostics = []
        lines = doc.text.split('\n')

        for i, line in enumerate(lines):
            # Check for basic syntax issues
            stripped = line.strip()

            # Missing semicolon
            if stripped and not stripped.startswith('//') and not stripped.endswith(';') and not stripped.endswith('{') and not stripped.endswith('}') and not stripped.endswith(':'):
                # Check if it's a declaration or statement that should end with semicolon
                if any(keyword in stripped for keyword in ['int8', 'int16', 'pixel', 'color', 'void', 'if', 'while', 'for', 'return']):
                    diagnostics.append(Diagnostic(
                        range=Range(
                            start=Position(i, len(line.rstrip())),
                            end=Position(i, len(line))
                        ),
                        severity=1,  # Error
                        message="Missing semicolon"
                    ))

            # Unmatched braces (basic check)
            open_braces = line.count('{')
            close_braces = line.count('}')
            if open_braces != close_braces:
                diagnostics.append(Diagnostic(
                    range=Range(
                        start=Position(i, 0),
                        end=Position(i, len(line))
                    ),
                    severity=2,  # Warning
                    message="Possible unmatched braces"
                ))

        return diagnostics

    def _get_word_at_position(self, line: str, character: int) -> str:
        """Get the word at the given character position."""
        # Find word boundaries
        start = character
        while start > 0 and (line[start-1].isalnum() or line[start-1] == '_'):
            start -= 1

        end = character
        while end < len(line) and (line[end].isalnum() or line[end] == '_'):
            end += 1

        return line[start:end]

    def _get_hover_info(self, word: str) -> Optional[str]:
        """Get hover information for a word."""
        hover_data = {
            # Types
            "int8": "**int8**\n\n8-bit integer type using R registers (R0-R9)",
            "int16": "**int16**\n\n16-bit integer type using P registers (P0-P9)",
            "pixel": "**pixel**\n\nScreen coordinate type (0-255)",
            "color": "**color**\n\nColor value type (0-31)",
            "sound": "**sound**\n\nAudio sample type",
            "layer": "**layer**\n\nGraphics layer type (0-7)",
            "sprite": "**sprite**\n\nSprite index type (0-15)",
            "interrupt": "**interrupt**\n\nInterrupt handler type",

            # Keywords
            "void": "**void**\n\nFunction return type for procedures",
            "if": "**if**\n\nConditional statement",
            "else": "**else**\n\nAlternative branch for if statement",
            "while": "**while**\n\nLoop construct",
            "for": "**for**\n\nCounted loop construct",
            "return": "**return**\n\nReturn from function",

            # Builtin functions
            "set_pixel": "**set_pixel(x, y, color)**\n\nSets a pixel at coordinates (x,y) to the specified color",
            "get_pixel": "**get_pixel(x, y)**\n\nGets the color of the pixel at coordinates (x,y)",
            "play_sound": "**play_sound(channel, frequency, volume)**\n\nPlays a sound on the specified channel",
            "delay": "**delay(milliseconds)**\n\nPauses execution for the specified time"
        }

        return hover_data.get(word)

    def _find_function_call_context(self, line: str, character: int) -> Optional[Dict[str, Any]]:
        """Find function call context at the given position."""
        # Look backwards from the character position to find function call
        before_cursor = line[:character]
        
        # Find the last opening parenthesis
        paren_index = before_cursor.rfind('(')
        if paren_index == -1:
            return None
        
        # Extract function name
        function_part = before_cursor[:paren_index].strip()
        function_name = function_part.split()[-1]  # Get last word
        
        # Count commas to determine parameter index
        after_paren = before_cursor[paren_index + 1:]
        param_index = after_paren.count(',')
        
        return {
            "function": function_name,
            "param_index": param_index
        }

    def _get_function_signature(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get signature information for a function."""
        signatures = {
            "set_pixel": {
                "label": "set_pixel(x: int8, y: int8, color: int8)",
                "documentation": "Sets a pixel at coordinates (x,y) to the specified color",
                "parameters": [
                    {"label": "x: int8", "documentation": "X coordinate (0-255)"},
                    {"label": "y: int8", "documentation": "Y coordinate (0-255)"},
                    {"label": "color: int8", "documentation": "Color value (0-31)"}
                ]
            },
            "get_pixel": {
                "label": "get_pixel(x: int8, y: int8) -> int8",
                "documentation": "Gets the color of the pixel at coordinates (x,y)",
                "parameters": [
                    {"label": "x: int8", "documentation": "X coordinate (0-255)"},
                    {"label": "y: int8", "documentation": "Y coordinate (0-255)"}
                ]
            },
            "play_sound": {
                "label": "play_sound(channel: int8, frequency: int16, volume: int8)",
                "documentation": "Plays a sound on the specified channel",
                "parameters": [
                    {"label": "channel: int8", "documentation": "Sound channel (0-7)"},
                    {"label": "frequency: int16", "documentation": "Sound frequency in Hz"},
                    {"label": "volume: int8", "documentation": "Volume level (0-255)"}
                ]
            },
            "delay": {
                "label": "delay(milliseconds: int16)",
                "documentation": "Pauses execution for the specified time",
                "parameters": [
                    {"label": "milliseconds: int16", "documentation": "Delay time in milliseconds"}
                ]
            }
        }
        
        if function_name in signatures:
            return signatures[function_name]
        return None

    def _find_definition(self, doc: TextDocumentItem, word: str) -> Optional[Dict[str, Any]]:
        """Find the definition location of a word in the document."""
        lines = doc.text.split('\n')
        
        for i, line in enumerate(lines):
            # Look for function definitions
            if f"void {word}(" in line or f"int8 {word}(" in line or f"int16 {word}(" in line:
                return {
                    "start": {"line": i, "character": line.find(word)},
                    "end": {"line": i, "character": line.find(word) + len(word)}
                }
            
            # Look for variable declarations
            if f"int8 {word}" in line or f"int16 {word}" in line or f"pixel {word}" in line or f"color {word}" in line:
                return {
                    "start": {"line": i, "character": line.find(word)},
                    "end": {"line": i, "character": line.find(word) + len(word)}
                }
        
        return None

    def _extract_document_symbols(self, doc: TextDocumentItem) -> List[Dict[str, Any]]:
        """Extract symbols from a document for outline view."""
        symbols = []
        lines = doc.text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Function definitions
            if line.startswith("void ") and "(" in line:
                func_name = line.split("(")[0].replace("void ", "").strip()
                symbols.append({
                    "name": func_name,
                    "kind": 12,  # Function
                    "range": {
                        "start": {"line": i, "character": 0},
                        "end": {"line": i, "character": len(lines[i])}
                    },
                    "selectionRange": {
                        "start": {"line": i, "character": lines[i].find(func_name)},
                        "end": {"line": i, "character": lines[i].find(func_name) + len(func_name)}
                    }
                })
            
            # Variable declarations
            for var_type in ["int8", "int16", "pixel", "color", "sound", "layer", "sprite", "interrupt"]:
                if line.startswith(f"{var_type} "):
                    var_name = line.split()[1].split(";")[0].split("=")[0].strip()
                    symbols.append({
                        "name": var_name,
                        "kind": 13,  # Variable
                        "range": {
                            "start": {"line": i, "character": 0},
                            "end": {"line": i, "character": len(lines[i])}
                        },
                        "selectionRange": {
                            "start": {"line": i, "character": lines[i].find(var_name)},
                            "end": {"line": i, "character": lines[i].find(var_name) + len(var_name)}
                        }
                    })
        
        return symbols

    def _analyze_completion_context(self, line: str, character: int) -> Dict[str, Any]:
        """Analyze the completion context at the given position."""
        before_cursor = line[:character]
        
        # Check if we're in a function call
        if "(" in before_cursor and ")" not in before_cursor.split("(")[-1]:
            return {"type": "function_call", "prefix": before_cursor.split("(")[-1].strip()}
        
        # Check if we're declaring a variable
        words = before_cursor.split()
        if len(words) >= 1 and words[-1] in ["int8", "int16", "pixel", "color", "sound", "layer", "sprite", "interrupt"]:
            return {"type": "variable_declaration", "prefix": ""}
        
        # Check if we're in an expression
        if "=" in before_cursor or "+" in before_cursor or "-" in before_cursor:
            return {"type": "expression", "prefix": before_cursor.split()[-1]}
        
        # General context
        return {"type": "general", "prefix": before_cursor.split()[-1] if before_cursor.split() else ""}

    def _get_function_completion_items(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get completion items for function calls."""
        items = []
        prefix = context.get("prefix", "")
        
        builtin_functions = [
            {"name": "set_pixel", "detail": "(x, y, color)", "doc": "Sets a pixel at coordinates (x,y) to the specified color"},
            {"name": "get_pixel", "detail": "(x, y)", "doc": "Gets the color of the pixel at coordinates (x,y)"},
            {"name": "clear_screen", "detail": "()", "doc": "Clears the entire screen"},
            {"name": "set_layer", "detail": "(layer)", "doc": "Sets the active graphics layer"},
            {"name": "play_sound", "detail": "(channel, frequency, volume)", "doc": "Plays a sound on the specified channel"},
            {"name": "stop_sound", "detail": "(channel)", "doc": "Stops sound playback on the specified channel"},
            {"name": "set_volume", "detail": "(channel, volume)", "doc": "Sets the volume for a sound channel"},
            {"name": "set_frequency", "detail": "(channel, frequency)", "doc": "Sets the frequency for a sound channel"},
            {"name": "delay", "detail": "(milliseconds)", "doc": "Pauses execution for the specified time"},
            {"name": "get_time", "detail": "()", "doc": "Gets the current system time"},
            {"name": "set_interrupt", "detail": "(vector, handler)", "doc": "Sets an interrupt handler"},
            {"name": "clear_interrupt", "detail": "(vector)", "doc": "Clears an interrupt handler"}
        ]
        
        for func in builtin_functions:
            if func["name"].startswith(prefix):
                items.append({
                    "label": func["name"],
                    "kind": 3,  # Function
                    "detail": f"builtin function {func['detail']}",
                    "documentation": func["doc"],
                    "insertText": func["name"]
                })
        
        return items

    def _get_type_completion_items(self) -> List[Dict[str, Any]]:
        """Get completion items for type declarations."""
        types = [
            {"name": "int8", "detail": "8-bit integer (R registers)"},
            {"name": "int16", "detail": "16-bit integer (P registers)"},
            {"name": "pixel", "detail": "Screen coordinate type"},
            {"name": "color", "detail": "Color value type (0-31)"},
            {"name": "sound", "detail": "Audio sample type"},
            {"name": "layer", "detail": "Graphics layer type (0-7)"},
            {"name": "sprite", "detail": "Sprite index type (0-15)"},
            {"name": "interrupt", "detail": "Interrupt handler type"}
        ]
        
        return [{
            "label": t["name"],
            "kind": 7,  # Class/Type
            "detail": t["detail"],
            "documentation": f"Hardware-specific type: {t['detail']}"
        } for t in types]

    def _get_expression_completion_items(self, doc: TextDocumentItem, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get completion items for expressions."""
        items = []
        prefix = context.get("prefix", "")
        
        # Extract variables from the document
        variables = self._extract_variables_from_document(doc)
        for var in variables:
            if var.startswith(prefix):
                items.append({
                    "label": var,
                    "kind": 6,  # Variable
                    "detail": "variable"
                })
        
        # Add builtin functions
        builtin_functions = ["set_pixel", "get_pixel", "clear_screen", "set_layer", "play_sound", "delay"]
        for func in builtin_functions:
            if func.startswith(prefix):
                items.append({
                    "label": func,
                    "kind": 3,  # Function
                    "detail": "builtin function"
                })
        
        return items

    def _get_general_completion_items(self) -> List[Dict[str, Any]]:
        """Get general completion items."""
        items = []
        
        # Keywords
        keywords = [
            {"name": "void", "detail": "function return type"},
            {"name": "if", "detail": "conditional statement"},
            {"name": "else", "detail": "alternative branch"},
            {"name": "while", "detail": "loop construct"},
            {"name": "for", "detail": "counted loop"},
            {"name": "return", "detail": "return from function"},
            {"name": "true", "detail": "boolean true"},
            {"name": "false", "detail": "boolean false"}
        ]
        
        for keyword in keywords:
            items.append({
                "label": keyword["name"],
                "kind": 14,  # Keyword
                "detail": keyword["detail"]
            })
        
        # Types
        types = ["int8", "int16", "pixel", "color", "sound", "layer", "sprite", "interrupt"]
        for t in types:
            items.append({
                "label": t,
                "kind": 7,  # Class/Type
                "detail": "hardware type"
            })
        
        return items

    def _extract_variables_from_document(self, doc: TextDocumentItem) -> List[str]:
        """Extract variable names from a document."""
        variables = []
        lines = doc.text.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for variable declarations
            for var_type in ["int8", "int16", "pixel", "color", "sound", "layer", "sprite", "interrupt"]:
                if line.startswith(f"{var_type} "):
                    var_name = line.split()[1].split(";")[0].split("=")[0].strip()
                    if var_name not in variables:
                        variables.append(var_name)
        
        return variables

    def _diagnostic_to_dict(self, diagnostic: Diagnostic) -> Dict[str, Any]:
        return {
            "range": {
                "start": {"line": diagnostic.range.start.line, "character": diagnostic.range.start.character},
                "end": {"line": diagnostic.range.end.line, "character": diagnostic.range.end.character}
            },
            "severity": diagnostic.severity,
            "message": diagnostic.message,
            "source": diagnostic.source
        }


def main():
    """Main LSP server entry point."""
    server = AstridLanguageServer()

    # Read from stdin, write to stdout
    while True:
        try:
            # Read message header
            content_length = None
            while True:
                line = sys.stdin.readline().strip()
                if not line:
                    break
                if line.startswith("Content-Length:"):
                    content_length = int(line.split(":")[1].strip())

            if content_length is None:
                continue

            # Read message body
            message = sys.stdin.read(content_length)
            request = json.loads(message)

            # Handle request
            method = request.get("method")
            params = request.get("params", {})

            response = server.handle_request(method, params)

            if response is not None:
                # Send response
                response_body = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": response
                }
                response_json = json.dumps(response_body)
                sys.stdout.write(f"Content-Length: {len(response_json)}\r\n\r\n{response_json}")
                sys.stdout.flush()

        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.error(f"LSP Server error: {e}")
            continue


if __name__ == "__main__":
    main()
