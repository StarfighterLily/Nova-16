#!/usr/bin/env python3
"""
Astrid 2.0 Debug Adapter Protocol (DAP) Implementation
Provides debugging support with source line mapping and breakpoint management.
"""

import json
import sys
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

# DAP protocol types
@dataclass
class Source:
    """Represents a source file."""
    name: Optional[str] = None
    path: Optional[str] = None
    sourceReference: Optional[int] = None

@dataclass
class Breakpoint:
    """Represents a breakpoint."""
    id: int
    verified: bool
    line: Optional[int] = None
    source: Optional[Source] = None

@dataclass
class StackFrame:
    """Represents a stack frame."""
    id: int
    name: str
    source: Optional[Source] = None
    line: int = 0
    column: int = 0

@dataclass
class Scope:
    """Represents a scope (local variables, etc.)."""
    name: str
    variablesReference: int
    expensive: bool = False

@dataclass
class Variable:
    """Represents a variable."""
    name: str
    value: str
    type: Optional[str] = None
    variablesReference: int = 0

class AstridDebugAdapter:
    """Astrid 2.0 Debug Adapter implementation."""

    def __init__(self):
        self.breakpoints: Dict[str, List[Breakpoint]] = {}
        self.source_lines: Dict[str, List[str]] = {}
        self.current_line: int = 0
        self.current_source: Optional[str] = None
        self.variables: Dict[str, Variable] = {}
        self.logger = logging.getLogger(__name__)

    def handle_request(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle DAP requests."""
        if command == "initialize":
            return self.handle_initialize(args)
        elif command == "launch":
            return self.handle_launch(args)
        elif command == "setBreakpoints":
            return self.handle_set_breakpoints(args)
        elif command == "threads":
            return self.handle_threads()
        elif command == "stackTrace":
            return self.handle_stack_trace(args)
        elif command == "scopes":
            return self.handle_scopes(args)
        elif command == "variables":
            return self.handle_variables(args)
        elif command == "continue":
            return self.handle_continue(args)
        elif command == "next":
            return self.handle_next(args)
        elif command == "stepIn":
            return self.handle_step_in(args)
        elif command == "stepOut":
            return self.handle_step_out(args)
        else:
            self.logger.warning(f"Unhandled command: {command}")
            return {}

    def handle_initialize(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "supportsConfigurationDoneRequest": True,
            "supportsFunctionBreakpoints": False,
            "supportsConditionalBreakpoints": False,
            "supportsHitConditionalBreakpoints": False,
            "supportsEvaluateForHovers": True,
            "supportsStepBack": False,
            "supportsSetVariable": False,
            "supportsRestartFrame": False,
            "supportsGotoTargetsRequest": False,
            "supportsCompletionsRequest": False,
            "completionTriggerCharacters": [],
            "supportsModulesRequest": False,
            "supportsExceptionOptions": False,
            "supportsValueFormattingOptions": False,
            "supportsExceptionInfoRequest": False,
            "supportTerminateDebuggee": True,
            "supportSuspendDebuggee": False,
            "supportsDelayedStackTraceLoading": False,
            "supportsLoadedSourcesRequest": False,
            "supportsLogPoints": False,
            "supportsTerminateThreadsRequest": False,
            "supportsSetExpression": False,
            "supportsTerminateRequest": True,
            "supportsDataBreakpoints": False,
            "supportsReadMemoryRequest": False,
            "supportsWriteMemoryRequest": False,
            "supportsDisassembleRequest": False,
            "supportsCancelRequest": False,
            "supportsBreakpointLocationsRequest": False,
            "supportsClipboardContext": False,
            "supportsSteppingGranularity": False,
            "supportsInstructionBreakpoints": False,
            "supportsExceptionFilterOptions": False
        }

    def handle_launch(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle launch request."""
        program = args.get("program")
        if program:
            self.current_source = program
            self.load_source_file(program)
            self.current_line = 0

            # Initialize some sample variables for debugging
            self.variables = {
                "counter": Variable("counter", "42", "int8"),
                "address": Variable("address", "0x1000", "int16"),
                "x": Variable("x", "128", "pixel"),
                "color": Variable("color", "31", "color")
            }

        return {}

    def handle_set_breakpoints(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle setBreakpoints request."""
        source = args.get("source", {})
        source_path = source.get("path")
        breakpoints = args.get("breakpoints", [])

        if not source_path:
            return {"breakpoints": []}

        # Clear existing breakpoints for this source
        self.breakpoints[source_path] = []

        verified_breakpoints = []
        for i, bp in enumerate(breakpoints):
            line = bp.get("line", 0)
            # For now, verify all breakpoints (in a real implementation,
            # we'd check if the line contains executable code)
            breakpoint_obj = Breakpoint(
                id=i + 1,
                verified=True,
                line=line,
                source=Source(path=source_path)
            )
            self.breakpoints[source_path].append(breakpoint_obj)
            verified_breakpoints.append({
                "id": breakpoint_obj.id,
                "verified": breakpoint_obj.verified,
                "line": breakpoint_obj.line
            })

        return {"breakpoints": verified_breakpoints}

    def handle_threads(self) -> Dict[str, Any]:
        """Handle threads request."""
        return {
            "threads": [
                {
                    "id": 1,
                    "name": "Main Thread"
                }
            ]
        }

    def handle_stack_trace(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stackTrace request."""
        thread_id = args.get("threadId", 1)

        frames = []
        if self.current_source:
            frames.append({
                "id": 1,
                "name": "main",
                "source": {
                    "name": Path(self.current_source).name,
                    "path": self.current_source
                },
                "line": self.current_line + 1,  # DAP uses 1-based line numbers
                "column": 0
            })

        return {
            "stackFrames": frames,
            "totalFrames": len(frames)
        }

    def handle_scopes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scopes request."""
        frame_id = args.get("frameId", 1)

        return {
            "scopes": [
                {
                    "name": "Local",
                    "variablesReference": 1,
                    "expensive": False
                },
                {
                    "name": "Registers",
                    "variablesReference": 2,
                    "expensive": False
                }
            ]
        }

    def handle_variables(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle variables request."""
        variables_reference = args.get("variablesReference", 1)

        variables = []
        if variables_reference == 1:  # Local variables
            for var in self.variables.values():
                variables.append({
                    "name": var.name,
                    "value": var.value,
                    "type": var.type,
                    "variablesReference": var.variablesReference
                })
        elif variables_reference == 2:  # Registers
            # Sample register values
            registers = [
                ("R0", "0x2A"), ("R1", "0x00"), ("P0", "0x1000"), ("P1", "0x03E8"),
                ("VX", "0x80"), ("VY", "0x64"), ("VM", "0x00"), ("VL", "0x01")
            ]
            for name, value in registers:
                variables.append({
                    "name": name,
                    "value": value,
                    "type": "register",
                    "variablesReference": 0
                })

        return {"variables": variables}

    def handle_continue(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle continue request."""
        # In a real implementation, this would resume execution
        return {"allThreadsContinued": True}

    def handle_next(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle next (step over) request."""
        # Simulate stepping to next line
        if self.current_source and self.current_source in self.source_lines:
            lines = self.source_lines[self.current_source]
            if self.current_line < len(lines) - 1:
                self.current_line += 1

        return {}

    def handle_step_in(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle step in request."""
        # For now, same as step over
        return self.handle_next(args)

    def handle_step_out(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle step out request."""
        # For now, same as step over
        return self.handle_next(args)

    def load_source_file(self, file_path: str):
        """Load source file for debugging."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.source_lines[file_path] = f.readlines()
        except Exception as e:
            self.logger.error(f"Failed to load source file {file_path}: {e}")

    def get_current_line_content(self) -> Optional[str]:
        """Get the content of the current line."""
        if self.current_source and self.current_source in self.source_lines:
            lines = self.source_lines[self.current_source]
            if 0 <= self.current_line < len(lines):
                return lines[self.current_line].rstrip()
        return None


def main():
    """Main DAP server entry point."""
    adapter = AstridDebugAdapter()

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
            command = request.get("command")
            args = request.get("arguments", {})

            response = adapter.handle_request(command, args)

            # Send response
            response_body = {
                "type": "response",
                "request_seq": request.get("seq"),
                "success": True,
                "command": command,
                "body": response
            }

            response_json = json.dumps(response_body)
            sys.stdout.write(f"Content-Length: {len(response_json)}\r\n\r\n{response_json}")
            sys.stdout.flush()

        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.error(f"DAP Server error: {e}")
            continue


if __name__ == "__main__":
    main()
