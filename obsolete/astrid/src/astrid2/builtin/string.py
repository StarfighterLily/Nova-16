"""
Astrid Built-in String Functions
Provides string manipulation operations for Nova-16.
"""

from typing import Dict, List, Any
from ..utils.logger import get_logger

logger = get_logger(__name__)


class StringBuiltins:
    """Built-in string functions for Astrid."""

    def __init__(self):
        self.functions = {
            'strlen': self._strlen,
            'strcpy': self._strcpy,
            'strcat': self._strcat,
            'strcmp': self._strcmp,
            'strchr': self._strchr,
            'substr': self._substr,
            'print_string': self._print_string,
            'char_at': self._char_at,
            'string_to_int': self._string_to_int,
            'int_to_string': self._int_to_string,
            'string_clear': self._string_clear,
            'string_fill': self._string_fill,
        }

    def get_function(self, name: str):
        """Get a built-in function by name."""
        return self.functions.get(name)

    def _strlen(self, string_ptr: int) -> str:
        """
        Calculate the length of a null-terminated string.

        Args:
            string_ptr: Memory address of the string

        Returns:
            Assembly code for string length calculation
        """
        return f"""
; strlen(string_ptr) - calculate string length
; Input: P0 = string pointer
; Output: R0 = string length
MOV P1, {string_ptr}      ; Load string pointer
MOV R0, 0                 ; Initialize counter
strlen_loop:
    MOV R1, [P1]          ; Load character
    CMP R1, 0             ; Check for null terminator
    JZ strlen_done        ; If zero, we're done
    INC R0                ; Increment counter
    INC P1                ; Move to next character
    JMP strlen_loop       ; Continue loop
strlen_done:
    ; R0 now contains string length
"""

    def _strcpy(self, dest_ptr: int, src_ptr: int) -> str:
        """
        Copy string from source to destination.

        Args:
            dest_ptr: Destination memory address
            src_ptr: Source memory address

        Returns:
            Assembly code for string copy
        """
        return f"""
; strcpy(dest, src) - copy string
; Input: P0 = destination pointer, P1 = source pointer
MOV P0, {dest_ptr}        ; Load destination pointer
MOV P1, {src_ptr}         ; Load source pointer
strcpy_loop:
    MOV R0, [P1]          ; Load character from source
    MOV [P0], R0          ; Store character to destination
    CMP R0, 0             ; Check for null terminator
    JZ strcpy_done        ; If zero, we're done
    INC P0                ; Move destination pointer
    INC P1                ; Move source pointer
    JMP strcpy_loop       ; Continue loop
strcpy_done:
    ; String copied successfully
"""

    def _strcat(self, dest_ptr: int, src_ptr: int) -> str:
        """
        Concatenate source string to destination string.

        Args:
            dest_ptr: Destination memory address
            src_ptr: Source memory address

        Returns:
            Assembly code for string concatenation
        """
        return f"""
; strcat(dest, src) - concatenate strings
; Input: P0 = destination pointer, P1 = source pointer
MOV P0, {dest_ptr}        ; Load destination pointer
MOV P1, {src_ptr}         ; Load source pointer

; Find end of destination string
strcat_find_end:
    MOV R0, [P0]          ; Load character
    CMP R0, 0             ; Check for null terminator
    JZ strcat_copy        ; If zero, start copying
    INC P0                ; Move to next character
    JMP strcat_find_end   ; Continue searching

; Copy source string to end of destination
strcat_copy:
    MOV R0, [P1]          ; Load character from source
    MOV [P0], R0          ; Store character to destination
    CMP R0, 0             ; Check for null terminator
    JZ strcat_done        ; If zero, we're done
    INC P0                ; Move destination pointer
    INC P1                ; Move source pointer
    JMP strcat_copy       ; Continue loop
strcat_done:
    ; Strings concatenated successfully
"""

    def _strcmp(self, str1_ptr: int, str2_ptr: int) -> str:
        """
        Compare two strings.

        Args:
            str1_ptr: First string memory address
            str2_ptr: Second string memory address

        Returns:
            Assembly code for string comparison
        """
        return f"""
; strcmp(str1, str2) - compare strings
; Input: P0 = first string pointer, P1 = second string pointer
; Output: R0 = result (0 = equal, <0 = str1 < str2, >0 = str1 > str2)
MOV P0, {str1_ptr}        ; Load first string pointer
MOV P1, {str2_ptr}        ; Load second string pointer
strcmp_loop:
    MOV R0, [P0]          ; Load character from first string
    MOV R1, [P1]          ; Load character from second string
    CMP R0, R1            ; Compare characters
    JNZ strcmp_diff       ; If different, handle difference
    CMP R0, 0             ; Check for end of string
    JZ strcmp_equal       ; If both null, strings are equal
    INC P0                ; Move first string pointer
    INC P1                ; Move second string pointer
    JMP strcmp_loop       ; Continue loop
strcmp_diff:
    SUB R0, R1            ; Calculate difference
    JMP strcmp_done       ; Done
strcmp_equal:
    MOV R0, 0             ; Strings are equal
strcmp_done:
    ; R0 contains comparison result
"""

    def _strchr(self, string_ptr: int, char_value: int) -> str:
        """
        Find first occurrence of character in string.

        Args:
            string_ptr: String memory address
            char_value: Character to find

        Returns:
            Assembly code for character search
        """
        return f"""
; strchr(string, char) - find character in string
; Input: P0 = string pointer, R0 = character to find
; Output: P1 = pointer to first occurrence (0 if not found)
MOV P0, {string_ptr}      ; Load string pointer
MOV R1, {char_value}      ; Load character to find
strchr_loop:
    MOV R2, [P0]          ; Load current character
    CMP R2, R1            ; Compare with target character
    JZ strchr_found       ; If match, we found it
    CMP R2, 0             ; Check for end of string
    JZ strchr_not_found   ; If null, character not found
    INC P0                ; Move to next character
    JMP strchr_loop       ; Continue loop
strchr_found:
    MOV P1, P0            ; Return pointer to character
    JMP strchr_done       ; Done
strchr_not_found:
    MOV P1, 0             ; Return null pointer
strchr_done:
    ; P1 contains result pointer
"""

    def _substr(self, string_ptr: int, start: int, length: int, dest_ptr: int) -> str:
        """
        Extract substring from string.

        Args:
            string_ptr: Source string memory address
            start: Starting index
            length: Length of substring
            dest_ptr: Destination memory address

        Returns:
            Assembly code for substring extraction
        """
        return f"""
; substr(string, start, length, dest) - extract substring
; Input: P0 = source string, R0 = start index, R1 = length, P1 = destination
MOV P0, {string_ptr}      ; Load source string pointer
MOV R0, {start}           ; Load start index
MOV R1, {length}          ; Load length
MOV P1, {dest_ptr}        ; Load destination pointer

; Skip to start position
MOV R2, 0                 ; Initialize counter
substr_skip:
    CMP R2, R0            ; Check if we've reached start
    JZ substr_copy        ; Start copying
    MOV R3, [P0]          ; Load character
    CMP R3, 0             ; Check for end of string
    JZ substr_done        ; If end, stop
    INC P0                ; Move source pointer
    INC R2                ; Increment counter
    JMP substr_skip       ; Continue skipping

; Copy substring
substr_copy:
    CMP R1, 0             ; Check if length is zero
    JZ substr_terminate   ; If zero, terminate string
    MOV R3, [P0]          ; Load character from source
    CMP R3, 0             ; Check for end of source string
    JZ substr_terminate   ; If end, terminate destination
    MOV [P1], R3          ; Store character to destination
    INC P0                ; Move source pointer
    INC P1                ; Move destination pointer
    DEC R1                ; Decrement length counter
    JMP substr_copy       ; Continue copying

substr_terminate:
    MOV [P1], 0           ; Null terminate destination string
substr_done:
    ; Substring extracted successfully
"""

    def _print_string(self, string_ptr: str, x: int, y: int, color: int) -> str:
        """
        Print string to output using Nova-16 TEXT instruction.

        Args:
            string_ptr: String literal or register containing string pointer
            x: X coordinate (0-639)
            y: Y coordinate (0-479)
            color: Color value (0-255)

        Returns:
            Assembly code for string printing
        """
        return f"""
; print_string(string, x, y, color) - print string using Nova-16 TEXT instruction
; Input: String pointer in register, coordinates, color
MOV P0, {string_ptr}      ; Load string pointer into P0
MOV VM, 0                 ; Set coordinate mode for VX,VY positioning
MOV VX, {x}               ; Set X coordinate
MOV VY, {y}               ; Set Y coordinate  
TEXT P0, {color}          ; Draw string at VX,VY coordinates with specified color
"""

    def _char_at(self, string_ptr: int, index: int) -> str:
        """
        Get character at specific index in string.

        Args:
            string_ptr: String memory address
            index: Character index

        Returns:
            Assembly code for character access
        """
        return f"""
; char_at(string, index) - get character at index
; Input: P0 = string pointer, R0 = index
; Output: R1 = character at index (0 if out of bounds)
MOV P0, {string_ptr}      ; Load string pointer
MOV R0, {index}           ; Load index
ADD P0, R0                ; Calculate address = string + index
MOV R1, [P0]              ; Load character at index
; R1 now contains the character (or 0 if out of bounds)
"""

    def _string_to_int(self, string_ptr: int) -> str:
        """
        Convert string to integer.

        Args:
            string_ptr: String memory address

        Returns:
            Assembly code for string to integer conversion
        """
        return f"""
; string_to_int(string) - convert string to integer
; Input: P0 = string pointer
; Output: P1 = integer value
MOV P0, {string_ptr}      ; Load string pointer
MOV P1, 0                 ; Initialize result
MOV R2, 10                ; Base 10 multiplier

str_to_int_loop:
    MOV R0, [P0]          ; Load character
    CMP R0, 0             ; Check for null terminator
    JZ str_to_int_done    ; If zero, we're done
    CMP R0, 48            ; Check if character is '0' or higher
    JL str_to_int_done    ; If less than '0', stop
    CMP R0, 57            ; Check if character is '9' or lower
    JG str_to_int_done    ; If greater than '9', stop
    
    ; Convert ASCII digit to number
    SUB R0, 48            ; Convert ASCII to digit (R0 = char - '0')
    MUL P1, R2            ; Multiply result by 10
    ADD P1, R0            ; Add digit to result
    
    INC P0                ; Move to next character
    JMP str_to_int_loop   ; Continue loop

str_to_int_done:
    ; P1 contains the integer result
"""

    def _int_to_string(self, value: int, dest_ptr: int) -> str:
        """
        Convert integer to string.

        Args:
            value: Integer value to convert
            dest_ptr: Destination string memory address

        Returns:
            Assembly code for integer to string conversion
        """
        return f"""
; int_to_string(value, dest) - convert integer to string
; Input: P0 = integer value, P1 = destination pointer
MOV P0, {value}           ; Load integer value
MOV P1, {dest_ptr}        ; Load destination pointer
MOV R2, 10                ; Base 10 divisor
MOV R3, 0                 ; Digit counter

; Handle special case of zero
CMP P0, 0
JNZ int_to_str_extract
MOV [P1], 48              ; Store '0'
INC P1
MOV [P1], 0               ; Null terminate
JMP int_to_str_done

; Extract digits in reverse order
int_to_str_extract:
    CMP P0, 0             ; Check if value is zero
    JZ int_to_str_reverse ; If zero, start reversing
    MOV R0, P0            ; Copy value
    MOD R0, R2            ; Get last digit (value % 10)
    DIV P0, R2            ; Remove last digit (value / 10)
    ADD R0, 48            ; Convert digit to ASCII
    PUSH R0               ; Push digit onto stack
    INC R3                ; Increment digit counter
    JMP int_to_str_extract ; Continue extraction

; Pop digits from stack and store in string
int_to_str_reverse:
    CMP R3, 0             ; Check if more digits
    JZ int_to_str_terminate ; If no more digits, terminate
    POP R0                ; Pop digit from stack
    MOV [P1], R0          ; Store digit in string
    INC P1                ; Move destination pointer
    DEC R3                ; Decrement digit counter
    JMP int_to_str_reverse ; Continue reversing

int_to_str_terminate:
    MOV [P1], 0           ; Null terminate string
int_to_str_done:
    ; Integer converted to string successfully
"""

    def _string_clear(self, string_ptr: int, max_length: int) -> str:
        """
        Clear string by filling with null characters.

        Args:
            string_ptr: String memory address
            max_length: Maximum length to clear

        Returns:
            Assembly code for string clearing
        """
        return f"""
; string_clear(string, max_length) - clear string
; Input: P0 = string pointer, R0 = max length
MOV P0, {string_ptr}      ; Load string pointer
MOV R0, {max_length}      ; Load max length
MOV R1, 0                 ; Null character

str_clear_loop:
    CMP R0, 0             ; Check if length is zero
    JZ str_clear_done     ; If zero, we're done
    MOV [P0], R1          ; Store null character
    INC P0                ; Move to next position
    DEC R0                ; Decrement length counter
    JMP str_clear_loop    ; Continue loop
str_clear_done:
    ; String cleared successfully
"""

    def _string_fill(self, string_ptr: int, char_value: int, length: int) -> str:
        """
        Fill string with specific character.

        Args:
            string_ptr: String memory address
            char_value: Character to fill with
            length: Number of characters to fill

        Returns:
            Assembly code for string filling
        """
        return f"""
; string_fill(string, char, length) - fill string with character
; Input: P0 = string pointer, R0 = character, R1 = length
MOV P0, {string_ptr}      ; Load string pointer
MOV R0, {char_value}      ; Load fill character
MOV R1, {length}          ; Load length

str_fill_loop:
    CMP R1, 0             ; Check if length is zero
    JZ str_fill_terminate ; If zero, terminate string
    MOV [P0], R0          ; Store fill character
    INC P0                ; Move to next position
    DEC R1                ; Decrement length counter
    JMP str_fill_loop     ; Continue loop
str_fill_terminate:
    MOV [P0], 0           ; Null terminate string
str_fill_done:
    ; String filled successfully
"""


# Create the global instance
string_builtins = StringBuiltins()
