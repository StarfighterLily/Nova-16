# NOVA-16 FORTH Implementation Guide

## Overview

This guide provides a detailed technical overview of the FORTH implementation for the NOVA-16 CPU emulator. It covers the architecture, inner/outer interpreter design, compilation process, and integration with NOVA-16 hardware.

## Architecture Overview

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Outer         │    │   Inner         │    │   Compilation   │
│   Interpreter   │───▶│   Interpreter   │───▶│   Process       │
│                 │    │                 │    │                 │
│ • Token parsing │    │ • Word execution│    │ • Assembly      │
│ • Input handling│    │ • Stack ops     │    │ • Optimization  │
│ • Error handling│    │ • Control flow  │    │ • Linking       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Dictionary    │    │   Parameter     │    │   NOVA-16       │
│   Management    │    │   Stack         │    │   Hardware      │
│                 │    │                 │    │                 │
│ • Word storage  │    │ • Data stack    │    │ • CPU registers │
│ • Hash lookup   │    │ • 16-bit values │    │ • Memory access │
│ • Source debug  │    │ • Bounds check  │    │ • I/O devices   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Outer Interpreter

The outer interpreter handles user input parsing and initial processing.

### Input Processing Flow

```
User Input → Tokenization → Number Parsing → Word Lookup → Execution/Compilation
```

### Tokenization Process

```python
def next_token(self):
    """Extract next token from input buffer"""
    # 1. Skip whitespace
    while whitespace: skip

    # 2. Handle special cases
    if '"': collect_quoted_string()
    if '."': collect_dot_quote_string()
    if 'S"': collect_s_quote_string()

    # 3. Collect regular token
    while not_whitespace_and_not_quote: collect_char

    return token
```

### Token Processing Logic

```python
def process_token(self, token):
    """Process individual FORTH token"""

    # 1. Handle string literals
    if token.startswith('"') or token.startswith('."') or token.startswith('S"'):
        handle_string_literal(token)
        return

    # 2. Try to parse as number
    try:
        num = int(token, self.base)
        if compiling:
            word_definitions.append(str(num))
        else:
            push_param(num)
        return
    except ValueError:
        pass

    # 3. Look up in dictionary
    if token in word_dict:
        if compiling and token not in [":", ";"]:
            if token in control_words:
                execute_for_compilation()
            else:
                word_definitions.append(token)
        else:
            execute_immediately()
        return

    # 4. Handle unknown words
    if compiling:
        word_definitions.append(token)  # Forward reference
    else:
        print(f"Unknown word: {token}")
```

## Inner Interpreter

The inner interpreter executes compiled FORTH code with full control flow support.

### Execution Model

```
Token List → Instruction Pointer → Token Processing → Stack Operations
```

### Control Flow Implementation

#### IF/ELSE/THEN Structure

```python
def execute_if_else_then(tokens, ip):
    """Handle IF/ELSE/THEN control flow"""
    condition = pop_param()

    if condition == 0:  # FALSE
        # Skip to ELSE or THEN
        depth = 1
        while ip < len(tokens) and depth > 0:
            ip += 1
            if tokens[ip] == 'IF': depth += 1
            elif tokens[ip] == 'ELSE' and depth == 1: break
            elif tokens[ip] == 'THEN': depth -= 1
    else:
        # Execute IF branch, skip ELSE
        depth = 1
        while ip < len(tokens) and depth > 0:
            ip += 1
            if tokens[ip] == 'IF': depth += 1
            elif tokens[ip] == 'ELSE' and depth == 1: break
            elif tokens[ip] == 'THEN': depth -= 1
```

#### BEGIN/UNTIL Loop

```python
def execute_begin_until(tokens, ip):
    """Handle BEGIN/UNTIL loop"""
    condition = pop_param()

    if condition == 0:  # Continue loop
        # Find corresponding BEGIN
        depth = 1
        while ip >= 0 and depth > 0:
            ip -= 1
            if tokens[ip] == 'UNTIL': depth += 1
            elif tokens[ip] == 'BEGIN': depth -= 1
    # else: exit loop naturally
```

#### DO/LOOP Structure

```python
def execute_do_loop(tokens, ip):
    """Handle DO/LOOP iteration"""
    # Setup phase
    index = pop_param()
    limit = pop_param()
    push_return(limit)
    push_return(index)

    # Loop execution
    while True:
        index = pop_return()
        limit = pop_return()
        index += 1

        if index < limit:
            # Continue loop
            push_return(limit)
            push_return(index)
            # Jump back to DO
            find_corresponding_do()
        else:
            # Exit loop
            break
```

### Stack Operations

#### Parameter Stack Management

```python
def push_param(self, value):
    """Push 16-bit value to parameter stack"""
    # Check for stack overflow
    if self.cpu.Pregisters[8] <= 0xE000:
        raise IndexError("Stack overflow")

    # Decrement stack pointer
    self.cpu.Pregisters[8] = (self.cpu.Pregisters[8] - 2) & 0xFFFF

    # Store value (convert to unsigned 16-bit)
    addr = self.cpu.Pregisters[8]
    unsigned_value = value & 0xFFFF
    self.memory.write_word(addr, unsigned_value)

def pop_param(self):
    """Pop 16-bit value from parameter stack"""
    # Check for stack underflow
    if self.cpu.Pregisters[8] >= 0xF000:
        raise IndexError("Stack underflow")

    # Get value
    addr = self.cpu.Pregisters[8]
    value = self.memory.read_word(addr)

    # Increment stack pointer
    self.cpu.Pregisters[8] = (self.cpu.Pregisters[8] + 2) & 0xFFFF

    # Convert to signed 16-bit
    if value > 0x7FFF:
        value -= 0x10000

    return value
```

#### Return Stack Management

```python
def push_return(self, value):
    """Push to return stack for control flow"""
    if self.cpu.Pregisters[9] <= 0xF000:
        raise IndexError("Return stack overflow")

    self.cpu.Pregisters[9] = (self.cpu.Pregisters[9] - 2) & 0xFFFF
    addr = self.cpu.Pregisters[9]
    self.memory.write_word(addr, value & 0xFFFF)

def pop_return(self):
    """Pop from return stack"""
    if self.cpu.Pregisters[9] >= 0xFFFF:
        raise IndexError("Return stack underflow")

    addr = self.cpu.Pregisters[9]
    value = self.memory.read_word(addr)
    self.cpu.Pregisters[9] = (self.cpu.Pregisters[9] + 2) & 0xFFFF

    if value > 0x7FFF:
        value -= 0x10000
    return value
```

## Compilation Process

### Word Definition Flow

```
: WORD_NAME ... ; → Token Collection → Function Creation → Dictionary Storage
```

#### Colon Definition Process

```python
def word_colon(self):
    """Start word definition"""
    token = self.next_token()  # Get word name
    self.current_word = token
    self.compiling = True
    self.word_definitions = []  # Start collecting tokens
    self.control_stack = []     # Initialize control flow stack

def word_semicolon(self):
    """End word definition"""
    definition_copy = self.word_definitions.copy()

    def execute_definition():
        self.execute_tokens(definition_copy)

    self.define_word(self.current_word, execute_definition)
    self.word_sources[self.current_word] = self.word_definitions.copy()

    # Reset state
    self.current_word = None
    self.compiling = False
    self.word_definitions = []
    self.control_stack = []
```

### Control Flow Compilation

#### IF/ELSE/THEN Compilation

```python
def word_if(self):
    """Compile IF statement"""
    if self.compiling:
        self.word_definitions.append('IF')
        self.control_stack.append(('IF', len(self.word_definitions) - 1))

def word_else(self):
    """Compile ELSE statement"""
    if self.compiling:
        self.word_definitions.append('ELSE')
        if self.control_stack and self.control_stack[-1][0] == 'IF':
            if_pos = self.control_stack.pop()[1]
            self.control_stack.append(('ELSE', len(self.word_definitions) - 1))

def word_then(self):
    """Compile THEN statement"""
    if self.compiling:
        self.word_definitions.append('THEN')
        if self.control_stack:
            self.control_stack.pop()
```

#### Loop Compilation

```python
def word_begin(self):
    """Compile BEGIN statement"""
    if self.compiling:
        self.word_definitions.append('BEGIN')
        self.control_stack.append(('BEGIN', len(self.word_definitions) - 1))

def word_until(self):
    """Compile UNTIL statement"""
    if self.compiling:
        self.word_definitions.append('UNTIL')
        if self.control_stack and self.control_stack[-1][0] == 'BEGIN':
            self.control_stack.pop()

def word_do(self):
    """Compile DO statement"""
    if self.compiling:
        self.word_definitions.append('DO')
        self.control_stack.append(('DO', len(self.word_definitions) - 1))

def word_loop(self):
    """Compile LOOP statement"""
    if self.compiling:
        self.word_definitions.append('LOOP')
        if self.control_stack and self.control_stack[-1][0] == 'DO':
            self.control_stack.pop()
```

## Dictionary Management

### Word Storage Structure

```python
class WordDefinition:
    def __init__(self, name, handler, source=None):
        self.name = name
        self.handler = handler  # Python function
        self.source = source    # Original token list
        self.is_core = False    # Core word flag
        self.defined_at = None  # Debug information

def define_word(self, name, handler):
    """Add word to dictionary"""
    if not hasattr(self, 'word_dict'):
        self.word_dict = {}

    word_def = WordDefinition(name, handler)
    self.word_dict[name] = handler

    # Store source for debugging
    if hasattr(self, 'word_sources'):
        self.word_sources[name] = {
            'defined_at': f"Line {sys._getframe().f_back.f_lineno}",
            'is_core': name in core_words
        }
```

### Dictionary Lookup

```python
def lookup_word(self, name):
    """Find word in dictionary"""
    if hasattr(self, 'word_dict') and name in self.word_dict:
        return self.word_dict[name]
    return None
```

## NOVA-16 Hardware Integration

### CPU Register Usage

```
P8 (SP): Parameter stack pointer - grows downward from 0xF000
P9 (FP): Frame pointer/Return stack pointer - grows downward from 0xFFFF
R0-R9: General purpose 8-bit registers for calculations
```

### Memory Layout Integration

```python
# FORTH memory constants
FORTH_START = 0x0120      # FORTH kernel start
USER_START = 0x1000       # User code area
PARAM_STACK_START = 0xF000  # Parameter stack (grows down)
RETURN_STACK_START = 0xFFFF # Return stack (grows down)
DICTIONARY_START = 0x0120   # Dictionary storage
```

### Hardware Access Patterns

#### Graphics Integration

```python
def word_pixel(self):
    """Set pixel with hardware integration"""
    color = self.pop_param()
    y = self.pop_param()
    x = self.pop_param()

    # Set coordinate mode
    self.gfx.vmode = 0

    # Set coordinates in hardware registers
    self.gfx.Vregisters[0] = x & 0xFF  # VX
    self.gfx.Vregisters[1] = y & 0xFF  # VY

    # Write pixel via hardware
    self.gfx.swrite(color)
```

#### Sound Integration

```python
def word_sound(self):
    """Configure sound hardware"""
    wave = self.pop_param()
    vol = self.pop_param()
    freq = self.pop_param()
    addr = self.pop_param()

    self.sound.play(addr, freq, vol, wave)
```

#### Input Integration

```python
def word_keyin(self):
    """Read keyboard input"""
    key = self.keyboard.read_key()
    self.push_param(key)

def word_keystat(self):
    """Check key availability"""
    status = self.keyboard.key_available()
    self.push_param(int(status))
```

## Error Handling

### Stack Protection

```python
def check_stack_bounds(self, operation):
    """Validate stack bounds before operations"""
    sp = self.cpu.Pregisters[8]

    if operation == 'push':
        if sp <= 0xE000:
            raise IndexError("Stack overflow")
    elif operation == 'pop':
        if sp >= 0xF000:
            raise IndexError("Stack underflow")
```

### Division by Zero Protection

```python
def word_div(self):
    """Division with error checking"""
    try:
        b = self.pop_param()
        a = self.pop_param()
        if b == 0:
            print("Division by zero")
            self.push_param(0)  # Push zero as error result
            return
        result = a // b
        self.push_param(result)
    except IndexError:
        print("Stack underflow in /")
```

### Memory Bounds Checking

```python
def word_fetch(self):
    """Memory read with bounds checking"""
    try:
        addr = self.pop_param()
        if not (0 <= addr < 0x10000):
            print(f"Invalid memory address: 0x{addr:04X}")
            self.push_param(0)
            return
        value = self.memory.read_word(addr)
        self.push_param(value)
    except IndexError:
        print("Stack underflow in @")
```

## Performance Optimizations

### Stack Operation Optimization

- **Indexed Addressing**: Use `[P8+offset]` instead of direct register access
- **Register Caching**: Minimize memory reads/writes
- **Batch Operations**: Combine multiple stack operations
- **Bounds Checking**: Lazy evaluation for better performance

### Dictionary Optimization

- **Hash-based Lookup**: O(1) word lookup using Python dictionaries
- **Source Storage**: Optional source tracking for debugging
- **Lazy Compilation**: Compile words only when needed
- **Memory Pool**: Efficient memory allocation for word storage

### Control Flow Optimization

- **Depth Tracking**: Efficient control structure nesting
- **Jump Tables**: Direct token processing without string comparisons
- **Stack Discipline**: Strict stack usage patterns
- **Error Recovery**: Graceful handling of malformed control structures

## Testing and Validation

### Test Coverage Strategy

```python
def run_comprehensive_tests(self):
    """Execute full test suite"""
    test_count = 0
    pass_count = 0

    # Core word tests
    test_count += 1
    if self.test_stack_operations(): pass_count += 1

    # Control flow tests
    test_count += 1
    if self.test_control_flow(): pass_count += 1

    # Hardware integration tests
    test_count += 1
    if self.test_hardware_integration(): pass_count += 1

    print(f"Tests passed: {pass_count}/{test_count}")
```

### Validation Methods

- **Stack State Verification**: Check SP/FP values after operations
- **Memory Integrity**: Validate memory contents after operations
- **Hardware State**: Verify register values match expectations
- **Error Handling**: Test edge cases and error conditions

## Future Enhancements

### Native Code Compilation

```python
def compile_to_assembly(self, word_name):
    """Compile FORTH word to NOVA-16 assembly"""
    tokens = self.word_sources[word_name]

    # Generate assembly code
    asm_code = []
    for token in tokens:
        if token in self.compilation_table:
            asm_code.extend(self.compilation_table[token]())

    # Optimize and link
    optimized_code = self.optimize_assembly(asm_code)
    return optimized_code
```

### Advanced Features

- **Multi-threading**: Concurrent FORTH tasks
- **File System**: Persistent storage capabilities
- **Network Support**: Communication protocols
- **Graphics Library**: High-level graphics primitives
- **Debugging Tools**: Single-step execution and inspection

## Conclusion

The NOVA-16 FORTH implementation provides a complete, high-performance programming environment that effectively leverages the target hardware's capabilities. The careful separation of outer/inner interpreters, robust error handling, and seamless hardware integration make it suitable for a wide range of applications from system programming to interactive development.

The architecture is designed for both performance and maintainability, with clear interfaces between components and comprehensive testing coverage.</content>
<parameter name="filePath">c:\Code\Nova\forth\IMPLEMENTATION_GUIDE.md