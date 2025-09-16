# Astrid Debugging and Diagnostic Tools

This suite of tools provides comprehensive debugging, analysis, and diagnostic capabilities for Astrid programs. Each tool is designed to help developers identify issues, optimize performance, and understand their code better.

## 🛠️ Available Tools

### 1. Astrid Syntax Checker (`astrid_syntax_checker.py`)
**Purpose**: Comprehensive syntax validation and error reporting

**Features**:
- Lexical analysis and token validation
- Syntax tree parsing and validation  
- Semantic analysis and type checking
- Code statistics and metrics
- Detailed error reporting with line numbers

**Usage**:
```powershell
python astrid_syntax_checker.py program.ast
python astrid_syntax_checker.py program.ast --verbose
python astrid_syntax_checker.py program.ast --json
```

**Output**: 
- Syntax validation status
- Error and warning reports
- Code statistics (lines, tokens, functions, etc.)
- Keyword and operator frequency analysis

---

### 2. Astrid Performance Profiler (`astrid_profiler.py`)
**Purpose**: Performance analysis and optimization recommendations

**Features**:
- Assembly code analysis for performance bottlenecks
- Execution profiling with cycle counting
- Register usage analysis
- Memory operation optimization
- Performance metrics calculation
- Optimization suggestions with priority levels

**Usage**:
```powershell
python astrid_profiler.py program.ast
python astrid_profiler.py program.ast --cycles 10000
python astrid_profiler.py program.ast --json
```

**Output**:
- Performance rating (Excellent/Good/Average/Poor)
- Instruction frequency analysis
- Memory and graphics operation percentages
- Optimization suggestions with impact assessment
- Execution cycle estimates

---

### 3. Astrid Variable Tracker (`astrid_variable_tracker.py`)
**Purpose**: Variable usage analysis and scope tracking

**Features**:
- Variable declaration tracking
- Read/write operation counting
- Scope analysis and nesting depth
- Unused variable detection
- Potential uninitialized variable warnings
- Variable lifetime analysis

**Usage**:
```powershell
python astrid_variable_tracker.py program.ast
python astrid_variable_tracker.py program.ast --verbose
python astrid_variable_tracker.py program.ast --json
```

**Output**:
- Variable usage statistics
- Unused variable warnings
- Scope depth analysis
- Read-only and write-only variable identification
- Variable lifecycle information

---

### 4. Astrid Assembly Inspector (`astrid_assembly_inspector.py`)
**Purpose**: Generated assembly code analysis and optimization

**Features**:
- Assembly code parsing and analysis
- Instruction timing estimation
- Register pressure analysis
- Addressing mode usage statistics
- Source-to-assembly correlation
- Assembly optimization opportunities

**Usage**:
```powershell
python astrid_assembly_inspector.py program.ast
python astrid_assembly_inspector.py program.ast --verbose
python astrid_assembly_inspector.py program.ast --json
```

**Output**:
- Assembly code statistics
- Instruction frequency and timing
- Register utilization analysis
- Source code expansion ratios
- Optimization score and suggestions

---

### 5. Astrid Test Generator (`astrid_test_generator.py`)
**Purpose**: Automated test case generation and validation

**Features**:
- Multiple test categories (syntax, variables, control flow, graphics, etc.)
- Difficulty levels (basic, intermediate, advanced)
- Edge case and stress testing
- Automatic test execution and validation
- Test result analysis and reporting

**Usage**:
```powershell
# Generate tests
python astrid_test_generator.py --types basic_syntax variable_operations

# Generate and run tests
python astrid_test_generator.py --types control_flow --run

# Generate tests with custom count
python astrid_test_generator.py --types graphics edge_cases --count 3

# Save generated tests to file
python astrid_test_generator.py --types all --output test_suite.ast
```

**Test Categories**:
- `basic_syntax`: Variable declarations, functions, arithmetic
- `variable_operations`: Scope, type conversion, assignments
- `control_flow`: If/else, loops, nested structures
- `function_calls`: Parameters, recursion, call chains
- `graphics`: Pixel operations, layers, graphics loops
- `edge_cases`: Boundary values, error conditions
- `performance`: Computationally intensive operations
- `stress`: Deep nesting, many operations

---

### 6. Astrid Debug Toolkit (`astrid_debug_toolkit.py`)
**Purpose**: Unified interface for all debugging tools

**Features**:
- Comprehensive analysis using multiple tools
- Interactive debugging mode
- Tool coordination and result correlation
- Summary generation and recommendations
- Batch analysis capabilities

**Usage**:
```powershell
# Comprehensive analysis
python astrid_debug_toolkit.py --analyze program.ast

# Interactive mode
python astrid_debug_toolkit.py --interactive

# Run specific tool
python astrid_debug_toolkit.py --tool syntax program.ast --verbose
```

**Interactive Commands**:
- `analyze <file>`: Run comprehensive analysis
- `run <tool> <args>`: Run specific tool
- `help`: Show available commands
- `quit`: Exit interactive mode

---

## 🔧 Integration with Existing Tools

These tools integrate seamlessly with the existing Nova-16 debugging ecosystem:

### Existing Nova Tools:
- `nova.py --headless`: Headless execution for automated testing
- `nova_debugger.py`: Interactive step-by-step debugging
- `nova_assembler.py`: Assembly compilation
- `nova_disassembler.py`: Binary disassembly
- `nova_graphics_monitor.py`: Graphics output analysis
- `astrid/astrid_debug_tool.py`: Existing Astrid debugging tool

### Workflow Integration:
1. **Development Phase**: Use `astrid_syntax_checker.py` for real-time validation
2. **Testing Phase**: Use `astrid_test_generator.py` for comprehensive testing
3. **Optimization Phase**: Use `astrid_profiler.py` and `astrid_assembly_inspector.py`
4. **Debugging Phase**: Use `astrid_variable_tracker.py` and existing debugger tools
5. **Analysis Phase**: Use `astrid_debug_toolkit.py` for comprehensive analysis

---

## 📊 Example Analysis Workflow

Here's a typical debugging workflow using these tools:

```powershell
# 1. Check syntax and basic issues
python astrid_syntax_checker.py starfield.ast --verbose

# 2. Analyze variables and scope
python astrid_variable_tracker.py starfield.ast

# 3. Profile performance
python astrid_profiler.py starfield.ast --cycles 10000

# 4. Inspect generated assembly
python astrid_assembly_inspector.py starfield.ast --verbose

# 5. Run comprehensive analysis
python astrid_debug_toolkit.py --analyze starfield.ast

# 6. Generate and run test cases
python astrid_test_generator.py --types graphics performance --run
```

---

## 🎯 Tool Output Examples

### Syntax Checker Output:
```
=== ASTRID SYNTAX CHECKER ===
File: starfield.ast
Status: ✅ VALID

📊 STATISTICS:
  Lines of code: 63
  Total tokens: 234
  Functions: 4
  Variables: 12
  Function calls: 8
  Max nesting depth: 3

🔧 FUNCTIONS:
  - main
  - roll_screen
  - draw_layer1
  - draw_layer2
```

### Performance Profiler Output:
```
=== ASTRID PERFORMANCE PROFILER ===
Source: starfield.ast
✅ Compilation: SUCCESS

📊 ASSEMBLY ANALYSIS:
   Instructions: 156
   Memory ops: 45 (28.8%)
   Graphics ops: 23 (14.7%)
   Control flow: 12 (7.7%)

🎯 PERFORMANCE METRICS:
   Performance rating: Good
   Memory efficiency: Average
   Register utilization: 65%

💡 OPTIMIZATION SUGGESTIONS:
   1. 🟡 [Memory] High memory operation percentage
      → Consider using more register-based operations
```

### Variable Tracker Output:
```
=== ASTRID VARIABLE TRACKER ===
File: starfield.ast

📊 STATISTICS:
  Total variables: 12
  Unused variables: 1
  Parameters: 0
  Read-only variables: 2
  Scopes: 5

🗑️ UNUSED VARIABLES (1):
  - temp_var

⚠️ WARNINGS (2):
  1. ⚠️ Line 45: Variable 'temp_var' is declared but never used
  2. ℹ️ Line 12: Variable 'counter' is written to but never read
```

---

## 🚀 Getting Started

1. **Ensure Python Environment**: Make sure you're in the Nova directory with Python 3.8+

2. **Run a Quick Check**:
```powershell
python astrid_syntax_checker.py astrid/gfxtest.ast
```

3. **Try Interactive Mode**:
```powershell
python astrid_debug_toolkit.py --interactive
```

4. **Run Comprehensive Analysis**:
```powershell
python astrid_debug_toolkit.py --analyze astrid/starfield.ast
```

---

## 🔍 Troubleshooting

### Common Issues:

1. **Import Errors**: Ensure you're running from the Nova root directory
2. **File Not Found**: Use absolute paths or ensure files exist
3. **Tool Failures**: Check that the Astrid compiler is working: `cd astrid && python run_astrid.py test.ast`

### Debug Tool Dependencies:
- Nova-16 emulator components
- Astrid compiler in `astrid/` directory
- Python 3.8+ with standard libraries

---

## 📈 Future Enhancements

Potential additions to the debugging toolkit:

1. **Live Debugging**: Real-time variable watching during execution
2. **Memory Visualization**: Graphical memory usage analysis
3. **Call Graph Analysis**: Function call relationship mapping
4. **Performance Benchmarking**: Comparison with reference implementations
5. **Code Coverage**: Test coverage analysis for generated tests
6. **Optimization Engine**: Automatic code optimization suggestions

These tools provide a comprehensive debugging and analysis environment for Astrid development, helping developers write better, more efficient code for the Nova-16 platform.
