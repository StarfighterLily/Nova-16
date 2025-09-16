# Astrid 2.0 Project Structure

**Status**: Updated September 3, 2025  
**Implementation**: 88% Complete  

This document outlines the current directory structure of the Astrid 2.0 compiler implementation.

## Root Directory Structure

```
astrid2.0/
├── src/                    # Main source code (✅ Complete)
├── examples/              # Example programs and demos (✅ Working)
├── tests/                 # Test suite and test data (✅ 11/11 passing)
├── docs/                  # Documentation (✅ Complete)
├── tools/                 # Development and build tools (🚧 Basic)
├── vscode-extension/      # VS Code integration (🚧 75% complete)
├── requirements.txt       # Python dependencies (✅ Complete)
├── setup.py              # Package setup script (✅ Complete)
├── run_astrid.py         # Main runner script (✅ Complete)
├── README.md             # Project overview (✅ Updated)
├── API_REFERENCE.md      # Complete API documentation (✅ Updated)
├── USER_GUIDE.md         # User documentation (✅ Complete)
├── IMPLEMENTATION_STATUS.md  # Current status (✅ New)
└── Astrid2.0_Specification.md  # Complete specification (✅ Complete)
```

## Source Code Structure (`src/`) - ✅ Complete

### Core Compiler Components (100% Implemented)
```
src/astrid2/
├── __init__.py           # Package initialization (✅ Complete)
├── main.py              # Main compiler entry point (✅ Complete)
├── lexer/               # Lexical analysis (✅ Complete)
│   ├── __init__.py
│   ├── lexer.py        # Main lexer implementation
│   └── tokens.py       # Token definitions
├── parser/              # Syntax analysis (✅ Complete)
│   ├── __init__.py
│   ├── parser.py       # Main parser implementation
│   └── ast.py          # Abstract Syntax Tree definitions
├── semantic/            # Semantic analysis (✅ Complete)
│   ├── __init__.py
│   ├── analyzer.py     # Semantic analyzer with type checking
│   └── scope.py        # Symbol table and scope management
├── ir/                  # Intermediate representation (✅ Complete)
│   ├── __init__.py
│   └── builder.py      # IR construction utilities
├── optimizer/           # Optimization passes (✅ Complete)
│   ├── __init__.py
│   ├── optimizer.py    # Main optimization coordinator
│   └── register_allocator.py  # Graph coloring register allocation
├── codegen/             # Code generation (✅ Complete)
│   ├── __init__.py
│   └── generator.py    # Assembly code generation
├── builtin/             # Built-in function library (✅ Complete)
│   ├── __init__.py
│   ├── graphics.py     # Graphics functions (16 functions)
│   ├── simplified_graphics.py  # Optimized graphics functions
│   ├── sound.py        # Sound functions (7 functions)
│   ├── string.py       # String functions (12 functions)
│   └── system.py       # System functions (15+ functions)
├── lsp/                 # Language Server Protocol (🚧 75% complete)
│   ├── __init__.py
│   └── server.py       # LSP server implementation
├── debug/               # Debug Adapter Protocol (🚧 50% complete)
│   ├── __init__.py
│   └── adapter.py      # DAP adapter implementation
├── utils/               # Utilities (✅ Complete)
│   ├── __init__.py
│   ├── error.py        # Error handling
│   └── logger.py       # Logging utilities
└── nova16/              # Nova-16 specific utilities (✅ Complete)
    └── __init__.py
```
│   ├── dce.py            # Dead code elimination
│   └── regalloc.py       # Register allocation
├── codegen/               # Code generation
│   ├── __init__.py
│   ├── generator.py      # Main code generator
│   ├── nova16.py         # Nova-16 specific code generation
│   ├── registers.py      # Register management
│   └── instructions.py   # Instruction selection
└── builtin/               # Built-in function library
    ├── __init__.py
    ├── graphics.py       # Graphics functions
    ├── sound.py          # Sound functions
    ├── system.py         # System functions
    └── library.py        # Built-in function registry
```

### Utility Modules
```
src/
├── utils/
│   ├── __init__.py
│   ├── error.py          # Error handling and reporting
│   ├── logger.py         # Logging utilities
│   └── config.py         # Configuration management
└── nova16/               # Nova-16 hardware definitions
    ├── __init__.py
    ├── registers.py      # Hardware register definitions
    ├── instructions.py   # Instruction set definitions
    ├── memory.py         # Memory layout definitions
    └── hardware.py       # Hardware feature definitions
```

## Examples Structure (`examples/`)

### Example Categories
```
examples/
├── basic/                # Basic language features
│   ├── hello_world.ast
│   ├── variables.ast
│   ├── functions.ast
│   └── control_flow.ast
├── graphics/             # Graphics programming
│   ├── layers.ast
│   ├── sprites.ast
│   ├── blending.ast
│   └── starfield.ast
├── sound/                # Sound programming
│   ├── waveforms.ast
│   ├── channels.ast
│   ├── samples.ast
│   └── music.ast
├── games/                # Game examples
│   ├── pong.ast
│   ├── tetris.ast
│   ├── space_invaders.ast
│   └── demo_game.ast
├── system/               # System programming
│   ├── interrupts.ast
│   ├── memory.ast
│   ├── timer.ast
│   └── io.ast
└── benchmarks/           # Performance benchmarks
    ├── graphics_bench.ast
    ├── sound_bench.ast
    └── system_bench.ast
```

## Test Structure (`tests/`)

### Test Organization
```
tests/
├── __init__.py
├── conftest.py           # Pytest configuration
├── unit/                 # Unit tests
│   ├── test_lexer.py
│   ├── test_parser.py
│   ├── test_semantic.py
│   ├── test_ir.py
│   ├── test_optimizer.py
│   └── test_codegen.py
├── integration/          # Integration tests
│   ├── test_compilation.py
│   ├── test_hardware.py
│   └── test_examples.py
├── fixtures/             # Test data and fixtures
│   ├── sample_programs/
│   ├── expected_outputs/
│   └── test_configs/
└── benchmarks/           # Performance tests
    ├── compile_time.py
    ├── runtime_perf.py
    └── code_size.py
```

## Documentation Structure (`docs/`)

### Documentation Files
```
docs/
├── language_reference.md     # Complete language reference
├── hardware_guide.md         # Hardware integration guide
├── optimization_guide.md     # Writing optimized code
├── debugging_guide.md        # Debug support and tools
├── api_reference.md          # Built-in functions API
├── tutorials/                # Tutorial documentation
│   ├── getting_started.md
│   ├── graphics_tutorial.md
│   ├── sound_tutorial.md
│   └── advanced_features.md
├── examples/                 # Documented examples
└── development/              # Development documentation
    ├── architecture.md
    ├── contributing.md
    ├── testing.md
    └── release_process.md
```

## Tools Structure (`tools/`)

### Development Tools
```
tools/
├── build.py              # Build automation
├── test_runner.py        # Test execution
├── benchmark.py          # Performance benchmarking
├── codegen_test.py       # Code generation testing
├── format.py             # Code formatting
├── lint.py               # Code linting
└── docs/                 # Tool documentation
    ├── build_guide.md
    ├── testing_guide.md
    └── development_tools.md
```

## File Naming Conventions

### Source Files
- Use snake_case for Python files: `lexer.py`, `parser.py`
- Use descriptive names: `register_allocation.py` not `regalloc.py`
- Group related functionality in modules

### Test Files
- Prefix with `test_`: `test_lexer.py`
- Use descriptive names: `test_graphics_codegen.py`
- Group by functionality: `unit/`, `integration/`

### Documentation Files
- Use lowercase with hyphens: `language-reference.md`
- Group by topic: `tutorials/`, `examples/`
- Include README files in subdirectories

## Build and Distribution

### Build Artifacts
```
build/                    # Build output (generated)
├── astrid2/             # Compiled package
├── dist/                # Distribution packages
└── temp/                # Temporary build files
```

### Distribution Files
```
dist/
├── astrid2-2.0.0.tar.gz
├── astrid2-2.0.0-py3-none-any.whl
└── astrid2-2.0.0.zip
```

## Configuration Files

### Root Level Configuration
```
.gitignore               # Git ignore patterns
.gitattributes          # Git attributes
.pre-commit-config.yaml # Pre-commit hooks
pyproject.toml          # Python project configuration
setup.cfg              # Setuptools configuration
tox.ini                # Testing configuration
```

### Development Configuration
```
.vscode/                 # VS Code settings
├── settings.json
├── launch.json
└── tasks.json
```

This structure provides a solid foundation for the Astrid 2.0 compiler development, ensuring maintainability, scalability, and clear organization of components.
