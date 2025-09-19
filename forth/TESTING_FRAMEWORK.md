# NOVA-16 FORTH Testing Framework

## Overview

This document outlines the comprehensive testing framework for the NOVA-16 FORTH implementation. The framework includes unit tests, integration tests, performance benchmarks, and validation procedures to ensure code quality and reliability.

## Test Architecture

### Test Organization Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_forth_core.py   # Core FORTH word tests
│   ├── test_forth_stack.py  # Stack operation tests
│   ├── test_forth_control.py # Control flow tests
│   ├── test_forth_memory.py # Memory access tests
│   └── test_forth_hw.py     # Hardware integration tests
├── integration/             # Integration tests
│   ├── test_forth_system.py # Full system tests
│   ├── test_forth_compiler.py # Compilation tests
│   └── test_forth_examples.py # Example program tests
├── performance/             # Performance benchmarks
│   ├── benchmark_forth.py   # FORTH performance tests
│   ├── benchmark_compiler.py # Compilation benchmarks
│   └── benchmark_memory.py  # Memory usage tests
├── fixtures/                # Test data and fixtures
│   ├── forth_programs.py    # Sample FORTH programs
│   ├── test_data.py         # Test data generators
│   └── expected_outputs.py  # Expected test results
└── conftest.py             # Pytest configuration
```

### Test Categories

#### 1. Unit Tests
**Purpose**: Test individual components in isolation
**Scope**: Single functions, methods, or small modules
**Framework**: pytest with unittest.mock for dependencies

#### 2. Integration Tests
**Purpose**: Test component interactions and full system behavior
**Scope**: Multi-component workflows and end-to-end scenarios
**Framework**: pytest with test fixtures

#### 3. Performance Tests
**Purpose**: Validate performance requirements and identify bottlenecks
**Scope**: Execution speed, memory usage, compilation time
**Framework**: Custom benchmarking framework

#### 4. Regression Tests
**Purpose**: Prevent reintroduction of known bugs
**Scope**: Previously fixed issues and edge cases
**Framework**: Automated test suite with CI integration

## Core Test Implementation

### Unit Test Examples

#### Stack Operation Tests

```python
import pytest
from forth_interpreter import ForthInterpreter

class TestForthStack:
    """Test FORTH stack operations"""

    def setup_method(self):
        """Set up test interpreter"""
        self.interpreter = ForthInterpreter()

    def test_dup_operation(self):
        """Test DUP operation"""
        # Push initial value
        self.interpreter.push_param(42)

        # Execute DUP
        self.interpreter.word_dup()

        # Verify stack state
        assert len(self.interpreter.param_stack) == 2
        assert self.interpreter.param_stack == [42, 42]
        assert self.interpreter.cpu.Pregisters[8] == 0xF000 - 4  # SP decremented by 4 bytes

    def test_drop_operation(self):
        """Test DROP operation"""
        # Set up stack
        self.interpreter.push_param(10)
        self.interpreter.push_param(20)

        # Execute DROP
        self.interpreter.word_drop()

        # Verify stack state
        assert len(self.interpreter.param_stack) == 1
        assert self.interpreter.param_stack == [10]
        assert self.interpreter.cpu.Pregisters[8] == 0xF000 - 2  # SP decremented by 2 bytes

    def test_swap_operation(self):
        """Test SWAP operation"""
        # Set up stack
        self.interpreter.push_param(10)
        self.interpreter.push_param(20)

        # Execute SWAP
        self.interpreter.word_swap()

        # Verify stack state
        assert len(self.interpreter.param_stack) == 2
        assert self.interpreter.param_stack == [20, 10]

    @pytest.mark.parametrize("a,b,expected", [
        (5, 3, 8),
        (-1, 1, 0),
        (100, 200, 300),
    ])
    def test_add_operation(self, a, b, expected):
        """Test ADD operation with multiple test cases"""
        # Set up stack
        self.interpreter.push_param(a)
        self.interpreter.push_param(b)

        # Execute ADD
        self.interpreter.word_add()

        # Verify result
        assert len(self.interpreter.param_stack) == 1
        assert self.interpreter.param_stack[0] == expected
```

#### Control Flow Tests

```python
class TestForthControlFlow:
    """Test FORTH control flow structures"""

    def setup_method(self):
        self.interpreter = ForthInterpreter()

    def test_if_then_structure(self):
        """Test IF/THEN conditional"""
        # Test true condition
        program = "5 0 > IF 42 THEN"
        self.interpreter.interpret(program)

        assert self.interpreter.pop_param() == 42

        # Reset interpreter
        self.interpreter = ForthInterpreter()

        # Test false condition
        program = "5 0 < IF 42 THEN"
        self.interpreter.interpret(program)

        # Stack should be empty (IF branch not taken)
        assert len(self.interpreter.param_stack) == 0

    def test_if_else_then_structure(self):
        """Test IF/ELSE/THEN conditional"""
        # Test true condition (should take IF branch)
        program = ": TEST 5 0 > IF 100 ELSE 200 THEN ; TEST"
        self.interpreter.interpret(program)

        assert self.interpreter.pop_param() == 100

        # Reset and test false condition
        self.interpreter = ForthInterpreter()
        program = ": TEST 5 0 < IF 100 ELSE 200 THEN ; TEST"
        self.interpreter.interpret(program)

        assert self.interpreter.pop_param() == 200

    def test_begin_until_loop(self):
        """Test BEGIN/UNTIL loop"""
        program = """
        VARIABLE COUNTER 0 COUNTER !
        BEGIN
          COUNTER @ 1 + COUNTER !
          COUNTER @ 5 >
        UNTIL
        COUNTER @
        """

        self.interpreter.interpret(program)
        result = self.interpreter.pop_param()

        assert result == 6  # Loop runs until counter > 5

    def test_do_loop_structure(self):
        """Test DO/LOOP iteration"""
        program = """
        VARIABLE SUM 0 SUM !
        5 0 DO
          I SUM @ + SUM !
        LOOP
        SUM @
        """

        self.interpreter.interpret(program)
        result = self.interpreter.pop_param()

        assert result == 10  # 0+1+2+3+4 = 10
```

#### Memory Access Tests

```python
class TestForthMemory:
    """Test FORTH memory access operations"""

    def setup_method(self):
        self.interpreter = ForthInterpreter()

    def test_variable_operations(self):
        """Test variable creation and access"""
        program = "VARIABLE TEST 42 TEST ! TEST @"
        self.interpreter.interpret(program)

        result = self.interpreter.pop_param()
        assert result == 42

    def test_constant_operations(self):
        """Test constant creation and access"""
        program = "314 CONSTANT PI PI"
        self.interpreter.interpret(program)

        result = self.interpreter.pop_param()
        assert result == 314

    def test_memory_fetch_store(self):
        """Test direct memory access"""
        # Store value at address 0x2000
        program = "42 0x2000 ! 0x2000 @"
        self.interpreter.interpret(program)

        result = self.interpreter.pop_param()
        assert result == 42

        # Verify memory state
        memory_value = self.interpreter.memory.read_word(0x2000)
        assert memory_value == 42

    def test_memory_bounds_checking(self):
        """Test memory access bounds validation"""
        # Test invalid address (should not crash)
        program = "42 0xFFFF ! 0xFFFF @"  # Address beyond valid range
        self.interpreter.interpret(program)

        # Should handle error gracefully
        # (Specific behavior depends on implementation)
```

### Integration Test Examples

#### System Integration Tests

```python
class TestForthSystemIntegration:
    """Test complete FORTH system integration"""

    def setup_method(self):
        self.interpreter = ForthInterpreter()

    def test_factorial_function(self):
        """Test recursive factorial implementation"""
        program = """
        : FACT DUP 1 > IF DUP 1 - RECURSE * ELSE DROP 1 THEN ;
        5 FACT
        """

        self.interpreter.interpret(program)
        result = self.interpreter.pop_param()

        assert result == 120  # 5! = 120

    def test_fibonacci_sequence(self):
        """Test Fibonacci sequence generation"""
        program = """
        : FIB DUP 1 > IF DUP 1 - RECURSE SWAP 2 - RECURSE + ELSE DROP 1 THEN ;
        8 FIB
        """

        self.interpreter.interpret(program)
        result = self.interpreter.pop_param()

        assert result == 21  # F(8) = 21

    def test_string_processing(self):
        """Test string handling capabilities"""
        program = '''
        S" HELLO WORLD" ."
        S" Test string" ."
        '''

        # Capture output
        import io
        from contextlib import redirect_stdout

        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            self.interpreter.interpret(program)

        output = output_buffer.getvalue()
        assert "HELLO WORLD" in output
        assert "Test string" in output

    def test_graphics_integration(self):
        """Test graphics hardware integration"""
        program = "100 120 15 PIXEL"  # White pixel at (100,120)

        self.interpreter.interpret(program)

        # Verify graphics state
        assert self.interpreter.gfx.Vregisters[0] == 100  # VX
        assert self.interpreter.gfx.Vregisters[1] == 120  # VY
        # Note: Actual pixel setting depends on graphics implementation

    def test_sound_integration(self):
        """Test sound hardware integration"""
        program = "0x2000 440 128 0 SOUND SPLAY"

        self.interpreter.interpret(program)

        # Verify sound state
        # (Specific verification depends on sound implementation)
```

#### Compiler Integration Tests

```python
class TestForthCompilerIntegration:
    """Test FORTH compiler integration"""

    def setup_method(self):
        self.compiler = ForthCompiler()

    def test_simple_compilation(self):
        """Test basic FORTH to assembly compilation"""
        forth_program = ": SQUARE DUP * ; 5 SQUARE ."

        # Compile to assembly
        asm_output = self.compiler.compile_program(forth_program)

        # Verify assembly contains expected instructions
        assert "MOV R0, [P8+0]" in asm_output  # DUP operation
        assert "MUL R0, R1" in asm_output     # Multiplication
        assert "SWRITE" in asm_output         # Output operation

    def test_optimization_verification(self):
        """Test compiler optimizations"""
        forth_program = ": TEST 2 3 + ;"

        # Compile with optimization
        optimized = self.compiler.compile_program(forth_program, optimize=True)

        # Should contain constant folding result
        assert "MOV R0, 5" in optimized  # 2 + 3 = 5

        # Compile without optimization
        unoptimized = self.compiler.compile_program(forth_program, optimize=False)

        # Should contain separate operations
        assert "MOV R0, 2" in unoptimized
        assert "MOV R1, 3" in unoptimized
        assert "ADD R0, R1" in unoptimized
```

### Performance Benchmark Tests

```python
import time
import statistics

class TestForthPerformance:
    """Performance benchmarks for FORTH system"""

    def setup_method(self):
        self.interpreter = ForthInterpreter()

    def benchmark_interpretation_speed(self):
        """Benchmark FORTH interpretation performance"""
        program = """
        : FIB DUP 1 > IF DUP 1 - RECURSE SWAP 2 - RECURSE + ELSE DROP 1 THEN ;
        """

        # Warm up
        self.interpreter.interpret(program + "10 FIB DROP")

        # Benchmark
        iterations = 100
        times = []

        for _ in range(iterations):
            start_time = time.perf_counter()
            self.interpreter.interpret("25 FIB DROP")
            end_time = time.perf_counter()
            times.append(end_time - start_time)

            # Reset interpreter
            self.interpreter = ForthInterpreter()
            self.interpreter.interpret(program)

        avg_time = statistics.mean(times)
        std_dev = statistics.stdev(times)

        print(".4f")
        print(".4f")

        # Performance assertions
        assert avg_time < 1.0  # Should complete in less than 1 second
        assert std_dev / avg_time < 0.1  # Low variance

    def benchmark_memory_usage(self):
        """Benchmark memory usage patterns"""
        import psutil
        import os

        process = psutil.Process(os.getpid())

        # Baseline memory
        baseline = process.memory_info().rss

        # Run memory-intensive program
        program = """
        1000 0 DO
          I VARIABLE (create many variables)
        LOOP
        """

        self.interpreter.interpret(program)

        # Check memory usage
        current = process.memory_info().rss
        memory_increase = current - baseline

        print(".2f")

        # Memory usage should be reasonable
        assert memory_increase < 50 * 1024 * 1024  # Less than 50MB increase

    def benchmark_compilation_speed(self):
        """Benchmark FORTH compilation performance"""
        large_program = """
        : COMPLEX-WORD
          DUP DUP * SWAP DUP * +
          DUP 1 > IF 2 - RECURSE THEN
        ;

        100 0 DO
          I COMPLEX-WORD DROP
        LOOP
        """

        compiler = ForthCompiler()

        start_time = time.perf_counter()
        asm_output = compiler.compile_program(large_program)
        end_time = time.perf_counter()

        compilation_time = end_time - start_time

        print(".4f")
        print(f"Generated {len(asm_output.split())} assembly instructions")

        # Compilation should be fast
        assert compilation_time < 5.0  # Less than 5 seconds
```

## Test Automation and CI/CD

### Continuous Integration Setup

#### GitHub Actions Configuration

```yaml
# .github/workflows/test-forth.yml
name: FORTH Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10]

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements-test.txt

    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=forth --cov-report=xml

    - name: Run integration tests
      run: |
        pytest tests/integration/ -v

    - name: Run performance tests
      run: |
        pytest tests/performance/ -v --tb=short

    - name: Upload coverage reports
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml

  benchmark:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v2

    - name: Run performance benchmarks
      run: |
        python -m pytest tests/performance/ -v --benchmark-only

    - name: Store benchmark results
      uses: benchmark-action/github-action-benchmark@v1
      with:
        tool: 'pytest'
        output-file-path: output.json
        github-token: ${{ secrets.GITHUB_TOKEN }}
        auto-push: true
```

### Test Coverage Requirements

#### Coverage Targets
- **Unit Tests**: >90% coverage of individual components
- **Integration Tests**: >80% coverage of component interactions
- **Performance Tests**: Key performance-critical paths
- **Regression Tests**: All previously identified bugs

#### Coverage Configuration

```ini
# .coveragerc
[run]
source = forth
omit =
    */tests/*
    */test_*
    setup.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:

[html]
directory = htmlcov
```

## Test Data and Fixtures

### Test Data Generators

```python
# tests/fixtures/test_data.py
import random

def generate_forth_programs():
    """Generate test FORTH programs"""
    return {
        'arithmetic': [
            "5 3 + .",
            "10 4 - .",
            "6 7 * .",
            "15 3 / .",
        ],
        'stack_ops': [
            "1 2 3 DUP DROP SWAP",
            "5 6 OVER NIP TUCK",
            "1 2 3 ROT",
        ],
        'control_flow': [
            "5 0 > IF 42 THEN .",
            ": TEST DUP 10 > IF 100 ELSE 50 THEN ; 15 TEST .",
            "BEGIN DUP . 1 - DUP 0 = UNTIL DROP",
        ]
    }

def generate_large_dataset(size=1000):
    """Generate large test dataset"""
    return [random.randint(-32768, 32767) for _ in range(size)]

def generate_forth_variables(count=100):
    """Generate FORTH variable declarations"""
    variables = []
    for i in range(count):
        variables.append(f"VARIABLE VAR{i} {i} VAR{i} !")
    return " ".join(variables)
```

### Expected Results Database

```python
# tests/fixtures/expected_outputs.py
EXPECTED_RESULTS = {
    'factorial_5': 120,
    'fibonacci_8': 21,
    'sum_1_to_10': 55,
    'arithmetic_precedence': -4,  # (5 + 3) * (10 - 8) / 2 - 7
}

def get_expected_result(test_name):
    """Get expected result for test"""
    return EXPECTED_RESULTS.get(test_name)

def validate_result(test_name, actual_result):
    """Validate test result against expected value"""
    expected = get_expected_result(test_name)
    if expected is None:
        raise ValueError(f"No expected result for test: {test_name}")

    if isinstance(expected, (int, float)):
        return abs(actual_result - expected) < 0.001
    else:
        return actual_result == expected
```

## Error Handling and Edge Cases

### Error Condition Tests

```python
class TestForthErrorHandling:
    """Test FORTH error handling and edge cases"""

    def setup_method(self):
        self.interpreter = ForthInterpreter()

    def test_stack_underflow_protection(self):
        """Test protection against stack underflow"""
        # Try to pop from empty stack
        with pytest.raises(IndexError, match="Stack underflow"):
            self.interpreter.word_drop()

    def test_division_by_zero_protection(self):
        """Test division by zero handling"""
        program = "10 0 /"
        self.interpreter.interpret(program)

        # Should handle gracefully (specific behavior may vary)
        # At minimum, should not crash the interpreter

    def test_memory_bounds_checking(self):
        """Test memory access bounds validation"""
        # Invalid memory access
        program = "42 -1 !"  # Negative address
        self.interpreter.interpret(program)

        # Should handle error gracefully
        program = "42 0x10000 !"  # Address beyond memory
        self.interpreter.interpret(program)

        # Should handle error gracefully

    def test_invalid_word_handling(self):
        """Test handling of undefined words"""
        program = "INVALID_WORD"
        self.interpreter.interpret(program)

        # Should report error but not crash
        # (Check that interpreter remains functional)

    def test_nested_control_flow_limits(self):
        """Test limits of nested control structures"""
        # Deeply nested IF/THEN structures
        deep_nest = "IF " * 50 + "42" + " THEN" * 50
        self.interpreter.interpret(deep_nest)

        result = self.interpreter.pop_param()
        assert result == 42

    def test_large_number_handling(self):
        """Test handling of large numbers"""
        # Numbers near 16-bit limits
        program = "32767 1 + ."  # Max 16-bit signed + 1
        self.interpreter.interpret(program)

        # Should handle overflow gracefully
```

## Test Reporting and Analysis

### Test Result Analysis

```python
class TestResultAnalyzer:
    """Analyze test results and generate reports"""

    def __init__(self, test_results):
        self.test_results = test_results

    def generate_summary_report(self):
        """Generate test summary report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed_tests = total_tests - passed_tests

        report = f"""
FORTH Test Summary Report
==========================
Total Tests: {total_tests}
Passed: {passed_tests}
Failed: {failed_tests}
Success Rate: {passed_tests/total_tests*100:.1f}%

Failed Tests:
"""

        for result in self.test_results:
            if result['status'] == 'FAIL':
                report += f"- {result['test_name']}: {result['error']}\n"

        return report

    def identify_performance_regressions(self, baseline_results):
        """Identify performance regressions"""
        regressions = []

        for current in self.test_results:
            if current['test_type'] == 'performance':
                baseline = next((b for b in baseline_results
                               if b['test_name'] == current['test_name']), None)

                if baseline:
                    degradation = (current['execution_time'] - baseline['execution_time'])
                    if degradation > baseline['execution_time'] * 0.1:  # 10% degradation
                        regressions.append({
                            'test_name': current['test_name'],
                            'degradation': degradation,
                            'percentage': degradation / baseline['execution_time'] * 100
                        })

        return regressions

    def generate_coverage_report(self):
        """Generate code coverage report"""
        # Integration with coverage.py
        import coverage

        cov = coverage.Coverage()
        cov.load()
        cov.report()

        return cov.report()
```

## Conclusion

The comprehensive testing framework ensures the reliability, performance, and correctness of the NOVA-16 FORTH implementation. The multi-layered approach covering unit tests, integration tests, performance benchmarks, and regression tests provides confidence in the system's stability and helps identify issues early in the development process.

Key benefits of this testing framework:
- **Early Bug Detection**: Comprehensive test coverage catches issues before they reach production
- **Performance Monitoring**: Benchmarks ensure the system meets performance requirements
- **Regression Prevention**: Automated tests prevent reintroduction of known bugs
- **Maintainability**: Well-structured tests make the codebase easier to maintain and extend
- **CI/CD Integration**: Automated testing ensures quality in the development pipeline

The framework is designed to scale with the FORTH implementation, supporting both current functionality and future enhancements while maintaining high standards of code quality and reliability.</content>
<parameter name="filePath">c:\Code\Nova\forth\TESTING_FRAMEWORK.md