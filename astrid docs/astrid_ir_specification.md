# Astrid Intermediate Representation (IR) Specification

## Overview

This document specifies the Intermediate Representation (IR) for the Astrid compiler, designed specifically for the Nova-16 16-bit CPU architecture. The IR serves as the bridge between high-level Astrid language constructs and efficient Nova-16 assembly generation, enabling powerful optimizations while maintaining hardware awareness.

**Key Design Principles:**
- **SSA-Based**: Static Single Assignment form for optimization opportunities
- **Hardware-Aware**: Direct representation of Nova-16 registers and hardware features
- **Type-Safe**: Embedded type information for dynamic language features
- **Optimization-Friendly**: Rich metadata for analysis and transformation passes
- **Memory-Safe**: Explicit memory operations with bounds and safety information

## IR Structure

### Program Representation

An Astrid program in IR consists of:
- **Modules**: Top-level compilation units
- **Functions**: Executable code blocks with parameters and return types
- **Global Variables**: Module-level data with initialization
- **Type Definitions**: User-defined types and structures
- **Constants**: Compile-time constant values

```ir
module "main"
  type Point = {x: i16, y: i16}
  global screen_width: i16 = 320
  global screen_height: i16 = 240

  function @main() -> void {
    ; Function body in IR
  }
```

### Basic Block Structure

Functions are composed of basic blocks with single entry/exit points:

```ir
function @draw_pixel(x: i16, y: i16, color: u8) -> void {
entry:
  %0 = icmp ult %x, @screen_width
  br %0, true: @valid_x, false: @error

valid_x:
  %1 = icmp ult %y, @screen_height
  br %1, true: @draw, false: @error

draw:
  call @set_hardware_coords(%x, %y)
  call @write_pixel(%color)
  ret void

error:
  call @panic("Invalid coordinates")
  unreachable
}
```

## Type System

### Primitive Types

```ir
; Integer types
i8    ; 8-bit signed integer
u8    ; 8-bit unsigned integer
i16   ; 16-bit signed integer
u16   ; 16-bit unsigned integer

; Special types
bool  ; Boolean (0 = false, 1 = true)
ptr   ; Raw pointer (16-bit address)
void  ; No value
```

### Composite Types

```ir
; Arrays
[10 x i16]        ; Fixed-size array
[* x i16]         ; Dynamic array (handle-based)

; Structures
{ x: i16, y: i16 }  ; Anonymous struct
Point              ; Named struct (defined elsewhere)

; Function types
(i16, i16) -> i16  ; Function signature
```

### Dynamic Types

For Astrid's dynamic typing, IR uses tagged unions:

```ir
; Tagged value representation
%value = type { tag: u8, data: u16 }

; Type tags
VALUE_INT    = 0x00  ; Direct 16-bit integer
VALUE_BOOL   = 0x01  ; Boolean (0/1)
VALUE_STRING = 0x02  ; String handle
VALUE_ARRAY  = 0x03  ; Array handle
VALUE_OBJECT = 0x04  ; Object handle
VALUE_NONE   = 0x05  ; None/null value
```

## Instruction Set

### Arithmetic Instructions

```ir
; Binary operations
%result = add i16 %a, %b          ; Addition
%result = sub i16 %a, %b          ; Subtraction
%result = mul i16 %a, %b          ; Multiplication
%result = div i16 %a, %b          ; Division
%result = mod i16 %a, %b          ; Modulo

; Unary operations
%result = neg i16 %a              ; Negation
%result = abs i16 %a              ; Absolute value

; Bitwise operations
%result = and i16 %a, %b          ; Bitwise AND
%result = or i16 %a, %b           ; Bitwise OR
%result = xor i16 %a, %b          ; Bitwise XOR
%result = not i16 %a              ; Bitwise NOT
%result = shl i16 %a, %b          ; Shift left
%result = shr i16 %a, %b          ; Shift right

; Byte access operations (for optimal P register utilization)
%result = byte_and i8 %a, %b      ; 8-bit AND using P register byte access
%result = byte_or i8 %a, %b       ; 8-bit OR using P register byte access
%result = byte_xor i8 %a, %b      ; 8-bit XOR using P register byte access
%result = byte_add i8 %a, %b      ; 8-bit ADD using P register byte access
%result = byte_sub i8 %a, %b      ; 8-bit SUB using P register byte access
%high_byte = load_high_byte p16 %preg    ; Load high byte from P register
%low_byte = load_low_byte p16 %preg      ; Load low byte from P register
store_high_byte p16 %preg, i8 %value     ; Store to high byte of P register
store_low_byte p16 %preg, i8 %value      ; Store to low byte of P register
```

### Comparison Instructions

```ir
; Integer comparisons
%result = icmp eq i16 %a, %b       ; Equal
%result = icmp ne i16 %a, %b       ; Not equal
%result = icmp ult i16 %a, %b      ; Unsigned less than
%result = icmp ule i16 %a, %b      ; Unsigned less or equal
%result = icmp ugt i16 %a, %b      ; Unsigned greater than
%result = icmp uge i16 %a, %b      ; Unsigned greater or equal
%result = icmp slt i16 %a, %b      ; Signed less than
%result = icmp sle i16 %a, %b      ; Signed less or equal
%result = icmp sgt i16 %a, %b      ; Signed greater than
%result = icmp sge i16 %a, %b      ; Signed greater or equal
```

### Memory Instructions

```ir
; Load operations
%value = load i16, ptr %address           ; Load from memory
%value = load volatile i16, ptr %address  ; Volatile load (hardware registers)

; Store operations
store i16 %value, ptr %address            ; Store to memory
store volatile i16 %value, ptr %address   ; Volatile store (hardware registers)

; Address calculations
%addr = getelementptr ptr %base, i16 %offset  ; Calculate address
%addr = getelementptr inbounds ptr %base, i16 %offset  ; Bounds-checked address

; Memory allocation
%handle = alloc_string i16 %length         ; Allocate string
%handle = alloc_array i16 %element_type, %size  ; Allocate array
%handle = alloc_object %type               ; Allocate object

; Reference counting
retain %handle                            ; Increment reference count
release %handle                           ; Decrement reference count
```

### Control Flow Instructions

```ir
; Unconditional branch
br label %target

; Conditional branch
br i1 %condition, label %true_target, label %false_target

; Function calls
%result = call i16 @function_name(i16 %arg1, i16 %arg2)
call void @function_name()                 ; Void return

; Return
ret i16 %value                            ; Return with value
ret void                                  ; Return void

; Phi nodes (SSA)
%result = phi i16 [%val1, %block1], [%val2, %block2]
```

### Hardware Integration Instructions

```ir
; Graphics operations
call void @set_video_mode(i16 %mode)
call void @set_video_layer(i16 %layer)
call void @set_video_coords(i16 %x, i16 %y)
call void @write_pixel(u8 %color)
%color = call u8 @read_pixel()

; Sound operations
call void @set_sound_address(u16 %address)
call void @set_sound_frequency(u16 %freq)
call void @set_sound_volume(u8 %volume)
call void @set_sound_waveform(u8 %waveform)
call void @play_sound()

; Timer operations
call void @set_timer_value(u16 %value)
call void @set_timer_match(u16 %match)
call void @set_timer_control(u8 %control)
call void @set_timer_speed(u8 %speed)
%value = call u16 @get_timer_value()

; Keyboard operations
%available = call i1 @key_available()
%key = call u8 @read_key()
```

## Register Allocation and Hardware Awareness

### Virtual Registers

IR uses virtual registers that map to Nova-16 registers:

```ir
; Virtual register declarations
%vreg_r0 = vreg r8     ; Maps to R0 (8-bit)
%vreg_p0 = vreg p16    ; Maps to P0 (16-bit)
%vreg_vm = vreg hw     ; Maps to VM (hardware register)

; Register hints for allocation
%temp = vreg r8 hint "hot"     ; Prefer register allocation
%local = vreg p16 hint "stack" ; Prefer stack allocation
```

### Hardware Register Mapping

```ir
; Direct hardware register access
%vm = load volatile u8, hwreg "VM"
store volatile u8 %mode, hwreg "VM"

%vx = load volatile u16, hwreg "VX"
store volatile u16 %x, hwreg "VX"

; Hardware register operations
%pixel = call u8 @sread()              ; SREAD instruction
call void @swrite(u8 %color)           ; SWRITE instruction
call void @srolx(u8 %amount)           ; SROLX instruction
```

## Function Representation

### Function Definition

```ir
function @fibonacci(n: i16) -> i16 {
entry:
  %0 = icmp sle i16 %n, 1
  br i1 %0, label %base_case, label %recursive_case

base_case:
  ret i16 %n

recursive_case:
  %1 = sub i16 %n, 1
  %2 = call i16 @fibonacci(%1)
  %3 = sub i16 %n, 2
  %4 = call i16 @fibonacci(%3)
  %5 = add i16 %2, %4
  ret i16 %5
}
```

### Function Attributes

```ir
; Function attributes
function @hot_function() -> void attributes ["inline", "hot_path"] {
  ; This function should be inlined and optimized for performance
}

function @cold_function() -> void attributes ["noinline", "cold_path"] {
  ; This function should not be inlined and optimized for size
}
```

## Optimization Opportunities

### SSA-Based Optimizations

```ir
; Common subexpression elimination
%0 = add i16 %a, %b
; ... other code ...
%1 = add i16 %a, %b  ; Redundant, can be eliminated
%2 = add i16 %0, %1  ; Becomes: %2 = add i16 %0, %0

; After CSE:
%0 = add i16 %a, %b
%2 = add i16 %0, %0
```

### Constant Folding

```ir
; Before optimization
%0 = add i16 5, 3
%1 = mul i16 %0, 2

; After constant folding
%1 = mul i16 8, 2  ; 5 + 3 = 8
%1 = 16            ; 8 * 2 = 16
```

### Dead Code Elimination

```ir
; Dead code
%0 = add i16 %a, %b
%1 = mul i16 %0, 2  ; Used
%2 = sub i16 %c, %d  ; Dead (never used)

; After DCE
%0 = add i16 %a, %b
%1 = mul i16 %0, 2
; %2 eliminated
```

### Register Allocation Hints

```ir
function @render_loop() -> void {
entry:
  %i = vreg p16 hint "loop_counter"  ; Prefer register for loop variable
  %x = vreg p16 hint "hot"           ; Frequently accessed
  %temp = vreg r8 hint "spill"       ; Can be spilled to stack

  br label %loop

loop:
  %i_val = phi p16 [0, %entry], [%i_next, %loop]
  ; ... loop body ...
  %i_next = add p16 %i_val, 1
  %cond = icmp ult p16 %i_next, 100
  br i1 %cond, label %loop, label %exit

exit:
  ret void
}
```

## Memory Safety and Bounds Checking

### Array Bounds Checking

```ir
function @safe_array_access(arr: [* x i16], index: i16, size: i16) -> i16 {
entry:
  %bounds_check = icmp ult i16 %index, %size
  br i1 %bounds_check, label %access, label %bounds_error

access:
  %element_ptr = getelementptr inbounds [* x i16] %arr, i16 %index
  %value = load i16, ptr %element_ptr
  ret i16 %value

bounds_error:
  call void @panic("Array index out of bounds")
  unreachable
}
```

### Null Pointer Checking

```ir
function @safe_dereference(ptr: ptr) -> i16 {
entry:
  %is_null = icmp eq ptr %ptr, null
  br i1 %is_null, label %null_error, label %dereference

dereference:
  %value = load i16, ptr %ptr
  ret i16 %value

null_error:
  call void @panic("Null pointer dereference")
  unreachable
}
```

## Code Generation Mapping

### IR to Nova-16 Assembly

```ir
; IR instruction
%result = add i16 %a, %b

; Generated assembly
MOV P0, %a      ; Load a into P0
ADD P0, %b      ; Add b to P0
MOV %result, P0 ; Store result
```

### Function Call Convention

```ir
; IR call
%result = call i16 @add_numbers(i16 %x, i16 %y)

; Generated assembly
MOV P0, %x      ; First arg in P0
MOV P1, %y      ; Second arg in P1
CALL @add_numbers
MOV %result, P0 ; Result in P0
```

### Hardware Integration

```ir
; IR hardware access
store volatile u8 1, hwreg "VL"

; Generated assembly
MOV VL, 1       ; Direct hardware register access
```

## Implementation Considerations

### IR Builder Architecture

```python
class IRBuilder:
    def __init__(self):
        self.module = Module()
        self.current_function = None
        self.current_block = None
        self.temp_counter = 0

    def create_temp(self, type_hint=None):
        """Create a temporary SSA variable"""
        name = f"%{self.temp_counter}"
        self.temp_counter += 1
        return TemporaryVariable(name, type_hint)

    def build_binary_op(self, op, left, right):
        """Build binary operation instruction"""
        result = self.create_temp()
        instruction = BinaryOpInstruction(op, left, right, result)
        self.current_block.add_instruction(instruction)
        return result
```

### Optimization Passes

```python
class OptimizationPipeline:
    def __init__(self, module):
        self.module = module
        self.passes = [
            ConstantFoldingPass(),
            CommonSubexpressionEliminationPass(),
            DeadCodeEliminationPass(),
            RegisterAllocationPass(),
            InstructionSelectionPass()
        ]

    def run(self):
        """Run all optimization passes"""
        for pass_obj in self.passes:
            pass_obj.run(self.module)
```

### Type Checking

```python
class TypeChecker:
    def check_binary_op(self, op, left_type, right_type):
        """Type check binary operations"""
        if op in ['add', 'sub', 'mul', 'div']:
            if left_type == right_type and left_type in [i8, i16, u8, u16]:
                return left_type
            else:
                raise TypeError(f"Invalid types for {op}: {left_type}, {right_type}")

        elif op in ['icmp']:
            if left_type == right_type:
                return bool
            else:
                raise TypeError(f"Cannot compare {left_type} and {right_type}")
```

## Example: Complete Function Compilation

### Astrid Source
```python
def draw_circle(x, y, radius):
    for angle in range(0, 360, 10):
        px = x + int(radius * cos(angle))
        py = y + int(radius * sin(angle))
        draw_pixel(px, py, 255)
```

### Generated IR
```ir
function @draw_circle(x: i16, y: i16, radius: i16) -> void {
entry:
  br label %loop_header

loop_header:
  %angle = phi i16 [0, %entry], [%angle_next, %loop_body]
  %cond = icmp slt i16 %angle, 360
  br i1 %cond, label %loop_body, label %loop_exit

loop_body:
  ; Calculate cosine
  %cos_val = call float @cos(float %angle)
  %cos_int = call i16 @float_to_int(float %cos_val)
  %radius_cos = mul i16 %radius, %cos_int
  %px = add i16 %x, %radius_cos

  ; Calculate sine
  %sin_val = call float @sin(float %angle)
  %sin_int = call i16 @float_to_int(float %sin_val)
  %radius_sin = mul i16 %radius, %sin_int
  %py = add i16 %y, %radius_sin

  ; Draw pixel
  call void @draw_pixel(i16 %px, i16 %py, u8 255)

  ; Increment angle
  %angle_next = add i16 %angle, 10
  br label %loop_header

loop_exit:
  ret void
}
```

### Generated Nova-16 Assembly
```asm
draw_circle:
    MOV P2, 0          ; angle = 0
    MOV P3, 360        ; loop limit

loop_header:
    CMP P2, P3         ; angle < 360
    JGE loop_exit

loop_body:
    ; Calculate px = x + radius * cos(angle)
    MOV P0, P2         ; angle
    CALL cos
    MUL P0, [FP-6]     ; radius
    ADD P0, [FP-8]     ; x
    MOV VX, P0         ; Set hardware X

    ; Calculate py = y + radius * sin(angle)
    MOV P0, P2         ; angle
    CALL sin
    MUL P0, [FP-6]     ; radius
    ADD P0, [FP-4]     ; y
    MOV VY, P0         ; Set hardware Y

    ; Draw pixel
    MOV R0, 255
    SWRITE R0

    ; angle += 10
    ADD P2, 10
    JMP loop_header

loop_exit:
    RET
```

## Production Process Details

### Important Implementation Notes

1. **SSA Form Maintenance**: All IR transformations must preserve SSA properties. Use phi functions correctly for control flow merges.

2. **Type Consistency**: Ensure type information flows correctly through all operations. Dynamic types should be represented with tagged unions.

3. **Hardware Register Handling**: Treat hardware registers as volatile memory locations. Never assume values persist across operations.

4. **Memory Safety**: Implement bounds checking for all array operations. Use reference counting for dynamic objects.

5. **Optimization Ordering**: Run constant folding and DCE before register allocation. Hardware-specific optimizations last.

6. **Debugging Support**: Include source location information in IR nodes for error reporting and debugging.

7. **Extensibility**: Design IR structures to easily add new instruction types or metadata without breaking existing code.

### Implementation Checklist

- [ ] IR module, function, and basic block classes
- [ ] All instruction types implemented
- [ ] Type system with dynamic typing support
- [ ] SSA construction and validation
- [ ] Hardware register integration
- [ ] Memory safety features
- [ ] Optimization pass framework
- [ ] Serialization/deserialization for debugging

### Testing Strategy

- **Unit Tests**: Test each IR instruction creation and manipulation
- **SSA Validation**: Ensure IR remains in valid SSA form after transformations
- **Type Checking**: Validate type consistency across operations
- **Hardware Integration**: Test all hardware register accesses
- **Optimization Verification**: Ensure optimizations preserve semantics
- **Code Generation**: Verify IR translates correctly to assembly

### Performance Considerations

- **IR Size**: Keep IR compact; use efficient data structures
- **Transformation Speed**: Optimize common IR operations (instruction insertion, traversal)
- **Memory Usage**: Monitor IR memory consumption during compilation
- **Cache Efficiency**: Design IR for good CPU cache performance

### Integration Points

- **Parser to IR**: Semantic analyzer produces initial IR
- **IR to Assembly**: Code generator consumes optimized IR
- **Optimization Pipeline**: Passes transform IR between semantic analysis and code generation
- **Debug Tools**: IR dumper for debugging compilation issues

## Conclusion

The Astrid IR provides a solid foundation for implementing a high-performance compiler targeting the Nova-16 architecture. Its SSA-based design enables powerful optimizations while maintaining hardware awareness and memory safety. The IR's structure supports both the dynamic typing of the Astrid language and the efficient code generation required for embedded systems.

**Key Benefits:**
- **Optimization-Ready**: SSA form enables advanced compiler optimizations
- **Hardware-Aware**: Direct support for Nova-16 registers and instructions
- **Type-Safe**: Embedded type information for dynamic language features
- **Memory-Safe**: Bounds checking and reference counting support
- **Extensible**: Clean structure for adding new language features

This IR specification provides the technical foundation needed to implement the Astrid compiler and achieve the performance and safety goals outlined in the compiler design document.

---

**Document Version**: 1.0
**Date**: September 17, 2025
**Authors**: Astrid IR Design Team
**Status**: Implementation Ready</content>
<parameter name="filePath">c:\Code\Nova\astrid docs\astrid_ir_specification.md