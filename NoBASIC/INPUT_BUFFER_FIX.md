# Input Buffer Fix - Variable Display Issue

## Problem
After implementing the Input statement, the prompt displayed correctly but the variable content did not print after input was complete.

## Root Cause
The input buffer was being allocated using `DEFSTR` (define string), which creates a **read-only string constant**. The buffer was initialized with 63 spaces:

```assembly
L2: DEFSTR "                                                               "
```

When the user typed characters, they were being written to this buffer, but since it was defined as a string constant with spaces, the display showed spaces instead of the typed content.

## Solution
Changed the buffer allocation from `DEFSTR` to `DEFB` (define bytes), creating a **writable buffer** initialized with zeros:

```assembly
L2: DEFB 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ...
```

### Code Changes

**Before:**
```python
self.strings.append((input_buffer_label, " " * 63))  # 63 spaces + null
```

**After:**
```python
self.strings.append((input_buffer_label, "__BUFFER__64__"))  # Special marker
```

**String Output Handling:**
```python
for label, string_value in self.strings:
    if string_value.startswith("__BUFFER__"):
        # Special buffer allocation
        size = int(string_value.split("__")[2])
        self.current_output.append(f"{label}: DEFB " + ", ".join(["0"] * size))
    else:
        self.current_output.append(f"{label}: DEFSTR \"{string_value}\"")
```

## Technical Details

### DEFSTR vs DEFB
- **DEFSTR**: Creates a null-terminated string constant (read-only in many systems)
- **DEFB**: Creates a byte array that can be modified at runtime

### Buffer Initialization
- **Size**: 64 bytes (63 characters + null terminator)
- **Initial Value**: All zeros (0x00)
- **Null Termination**: Maintained throughout input process

### Why This Matters
1. **Writability**: DEFB creates writable memory, allowing character storage
2. **Display**: Zero-initialized buffer displays as empty string initially
3. **Modification**: Characters can be written and will display correctly
4. **Null Termination**: Proper string termination for TEXT instruction

## Assembly Comparison

### Before (Broken)
```assembly
STR0: DEFSTR "Hello?"
L2: DEFSTR "                                                               "
```
- Buffer filled with spaces
- Displays spaces instead of typed text

### After (Fixed)
```assembly
STR0: DEFSTR "Hello?"
L2: DEFB 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ...
```
- Buffer filled with zeros
- Displays typed text correctly

## Testing

### Test Program
```nobasic
Input("Hello?", Str1)
Disp Str1
Disp "Hello!"
```

### Expected Behavior
1. Display prompt: "Hello?"
2. User types input (e.g., "World")
3. Display "World" (the typed input)
4. Display "Hello!"

### Generated Assembly
The corrected implementation now generates:
- Proper writable buffer allocation
- Correct character storage during input
- Proper variable display after input

## Impact
This fix ensures that:
- Input buffers are writable
- Typed characters are stored correctly
- Variable display shows actual input content
- String operations work with input data

## Related Files
- `NoBASIC/compiler/codegen/generator.py` - Buffer allocation logic
- `NoBASIC/strings.nb` - Test file
- `NoBASIC/strings.asm` - Generated assembly output
