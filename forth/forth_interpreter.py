"""
NOVA-16 FORTH Implementation
A complete FORTH language interpreter for the Nova-16 CPU emulator.

FORTH is a stack-based programming language with the following key concepts:
- Dictionary: Linked list of defined words
- Parameter Stack: Data stack for operations
- Return Stack: Control flow stack
- Inner Interpreter: Executes compiled words
- Outer Interpreter: Parses input and compiles words

Memory Layout for FORTH:
- 0x0000-0x00FF: Zero page (fast access)
- 0x0100-0x011F: Interrupt vectors
- 0x0120-0x0FFF: System area (FORTH kernel)
- 0x1000-0xDFFF: User code space
- 0xE000-0xEFFF: Parameter stack (grows downward)
- 0xF000-0xFFFF: Return stack (grows downward)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from nova_cpu import CPU
from nova_memory import Memory
from nova_gfx import GFX
from nova_keyboard import NovaKeyboard
from nova_sound import NovaSound

class ForthInterpreter:
    """
    FORTH interpreter for Nova-16 CPU
    """

    def __init__(self, memory_size=0x10000):  # 64KB
        # Initialize Nova-16 components
        self.memory = Memory(memory_size)
        self.gfx = GFX()
        self.keyboard = NovaKeyboard()
        self.sound = NovaSound()
        self.sound.set_memory_reference(self.memory)

        self.cpu = CPU(self.memory, self.gfx, self.keyboard, self.sound)

        # FORTH memory layout
        self.FORTH_START = 0x0120
        self.USER_START = 0x1000
        self.PARAM_STACK_START = 0xF000  # Grows downward
        self.RETURN_STACK_START = 0xFFFF  # Grows downward
        self.DICTIONARY_START = 0x0120

        # FORTH state variables
        self.dictionary_head = 0  # Address of latest word in dictionary
        self.here = self.USER_START  # Next free memory location
        self.state = 0  # 0 = interpret, 1 = compile
        self.base = 10  # Number base (decimal by default)

        # Stacks (using CPU registers for stack pointers)
        self.cpu.Pregisters[8] = self.PARAM_STACK_START  # SP
        self.cpu.Pregisters[9] = self.RETURN_STACK_START  # RP (FP used as RP in FORTH)

        # Input buffer
        self.input_buffer = ""
        self.input_ptr = 0

        # Compilation state
        self.current_word = None  # Current word being defined
        self.compiling = False    # Are we in compile mode?
        self.word_definitions = []  # List to store the word's definition
        self.control_stack = []  # Stack for control flow structures
        self.word_sources = {}  # Store source tokens for debugging

        # File I/O state
        self.open_files = {}  # fileid -> file object
        self.next_fileid = 1  # Next available file ID

        # Initialize FORTH kernel
        self.init_forth_kernel()

    def init_forth_kernel(self):
        """Initialize the FORTH kernel with core words"""
        print("Initializing FORTH kernel...")

        # Core FORTH words will be implemented as assembly routines
        # For now, we'll implement them in Python for bootstrapping

        # Set up initial dictionary
        self.dictionary_head = 0

        # Define core words
        self.define_core_words()

        print("FORTH kernel initialized.")

    def define_core_words(self):
        """Define the core FORTH words"""

        # Stack manipulation words
        self.define_word("DUP", self.word_dup)
        self.define_word("DROP", self.word_drop)
        self.define_word("SWAP", self.word_swap)
        self.define_word("OVER", self.word_over)
        self.define_word("ROT", self.word_rot)
        self.define_word("NIP", self.word_nip)
        self.define_word("TUCK", self.word_tuck)
        self.define_word("?DUP", self.word_qdup)

        # Arithmetic words
        self.define_word("+", self.word_add)
        self.define_word("-", self.word_sub)
        self.define_word("*", self.word_mul)
        self.define_word("/", self.word_div)
        self.define_word("MOD", self.word_mod)
        self.define_word("NEGATE", self.word_negate)
        self.define_word("ABS", self.word_abs)
        self.define_word("MIN", self.word_min)
        self.define_word("MAX", self.word_max)
        self.define_word("SQRT", self.word_sqrt)
        self.define_word("SIN", self.word_sin)
        self.define_word("COS", self.word_cos)

        # Comparison words
        self.define_word("=", self.word_equals)
        self.define_word("<", self.word_less)
        self.define_word(">", self.word_greater)
        self.define_word("<>", self.word_not_equals)
        self.define_word("<=", self.word_less_equals)
        self.define_word(">=", self.word_greater_equals)

        # Logic words
        self.define_word("AND", self.word_and)
        self.define_word("OR", self.word_or)
        self.define_word("XOR", self.word_xor)
        self.define_word("INVERT", self.word_invert)

        # Control flow words
        self.define_word(":", self.word_colon)  # Start word definition
        self.define_word(";", self.word_semicolon)  # End word definition
        self.define_word("IF", self.word_if)
        self.define_word("ELSE", self.word_else)
        self.define_word("THEN", self.word_then)
        self.define_word("BEGIN", self.word_begin)
        self.define_word("UNTIL", self.word_until)
        self.define_word("DO", self.word_do)
        self.define_word("LOOP", self.word_loop)
        self.define_word("RECURSE", self.word_recurse)

        # I/O words
        self.define_word(".", self.word_dot)  # Print number
        self.define_word("EMIT", self.word_emit)  # Print character
        self.define_word("CR", self.word_cr)  # Carriage return
        self.define_word("WORDS", self.word_words)  # List all words
        self.define_word("SPACES", self.word_spaces)
        self.define_word("SPACE", self.word_space)

        # String handling words
        self.define_word('."', self.word_dot_quote)
        self.define_word('S"', self.word_s_quote)
        self.define_word("!", self.word_store)
        self.define_word("@", self.word_fetch)

        # Variable and constant words
        self.define_word("VARIABLE", self.word_variable)
        self.define_word("CONSTANT", self.word_constant)

        # System words
        self.define_word("BYE", self.word_bye)  # Exit
        self.define_word("BASE", self.word_base)
        self.define_word("HEX", self.word_hex)
        self.define_word("DECIMAL", self.word_decimal)
        self.define_word("I", self.word_i)  # Loop index
        self.define_word("J", self.word_j)  # Outer loop index
        # --- Hardware Integration Words ---
        self.define_word("PIXEL", self.word_pixel)
        self.define_word("LAYER", self.word_layer)
        self.define_word("VMODE", self.word_vmode)
        self.define_word("SPRITE", self.word_sprite)
        self.define_word("SOUND", self.word_sound)
        self.define_word("KEYIN", self.word_keyin)
        self.define_word("KEYSTAT", self.word_keystat)
        self.define_word("SWRITE", self.word_swrite)
        self.define_word("SPLAY", self.word_splay)

        # Additional hardware register access
        self.define_word("VX!", self.word_set_vx)
        self.define_word("VY!", self.word_set_vy)
        self.define_word("TT!", self.word_set_tt)
        self.define_word("TM!", self.word_set_tm)
        self.define_word("TS!", self.word_set_ts)
        self.define_word("TC!", self.word_set_tc)

        # File I/O words
        self.define_word("OPEN-FILE", self.word_open_file)
        self.define_word("CLOSE-FILE", self.word_close_file)
        self.define_word("READ-FILE", self.word_read_file)
        self.define_word("WRITE-FILE", self.word_write_file)
        self.define_word("INCLUDE-FILE", self.word_include_file)
    # --- Hardware Word Implementations ---
    def word_pixel(self):
        # Usage: x y color PIXEL
        color = self.pop_param()
        y = self.pop_param()
        x = self.pop_param()
        
        # Ensure coordinate mode
        self.gfx.vmode = 0
        
        # Ensure active layer (use layer 1 if none set)
        if self.gfx.VL == 0:
            self.gfx.VL = 1
            
        # Set coordinates in hardware registers
        self.gfx.Vregisters[0] = x & 0xFF  # VX
        self.gfx.Vregisters[1] = y & 0xFF  # VY
        
        # Write pixel
        self.gfx.swrite(color)  # This will write to current layer

    def word_layer(self):
        # Usage: layer_num LAYER
        layer = self.pop_param()
        self.gfx.set_current_layer(layer)

    def word_vmode(self):
        # Usage: mode VMODE
        mode = self.pop_param()
        self.gfx.set_vmode(mode)

    def word_sprite(self):
        # Usage: sprite_id SPRITE
        sprite_id = self.pop_param()
        self.gfx.activate_sprite(sprite_id)

    def word_sound(self):
        # Usage: addr freq vol wave SOUND
        wave = self.pop_param()
        vol = self.pop_param()
        freq = self.pop_param()
        addr = self.pop_param()
        self.sound.play(addr, freq, vol, wave)

    def word_keyin(self):
        # Usage: KEYIN ( -- key )
        key = self.keyboard.read_key()
        self.push_param(key)

    def word_keystat(self):
        # Usage: KEYSTAT ( -- status )
        status = self.keyboard.key_available()
        self.push_param(int(status))

    def word_swrite(self):
        # Usage: value SWRITE
        value = self.pop_param()
        self.gfx.set_vram_val(value)

    def word_splay(self):
        # Usage: SPLAY
        self.sound.splay()

    def word_set_vx(self):
        # Usage: value VX!
        value = self.pop_param()
        self.gfx.Vregisters[0] = value & 0xFF

    def word_set_vy(self):
        # Usage: value VY!
        value = self.pop_param()
        self.gfx.Vregisters[1] = value & 0xFF

    def word_set_tt(self):
        # Usage: value TT!
        value = self.pop_param()
        self.cpu.timer[0] = value & 0xFF

    def word_set_tm(self):
        # Usage: value TM!
        value = self.pop_param()
        self.cpu.timer[1] = value & 0xFF

    def word_set_tc(self):
        # Usage: value TC!
        value = self.pop_param()
        self.cpu.timer[2] = value & 0xFF

    def word_set_ts(self):
        # Usage: value TS!
        value = self.pop_param()
        self.cpu.timer[3] = value & 0xFF

    # --- File I/O Word Implementations ---
    def word_open_file(self):
        """OPEN-FILE: ( c-addr u fam -- fileid ior )"""
        fam = self.pop_param()  # File access method (0=read, 1=write, 2=read-write)
        length = self.pop_param()
        addr = self.pop_param()
        
        # Read filename from memory
        filename = ""
        for i in range(length):
            char = self.memory.read_byte(addr + i)
            if char == 0:
                break
            filename += chr(char)
        
        try:
            if fam == 0:  # Read
                mode = 'r'
            elif fam == 1:  # Write
                mode = 'w'
            elif fam == 2:  # Read-write
                mode = 'r+'
            else:
                self.push_param(0)  # Invalid fileid
                self.push_param(-1)  # IOR error
                return
            
            file_obj = open(filename, mode)
            fileid = self.next_fileid
            self.next_fileid += 1
            self.open_files[fileid] = file_obj
            
            self.push_param(fileid)
            self.push_param(0)  # Success
        except Exception as e:
            print(f"Error opening file {filename}: {e}")
            self.push_param(0)  # Invalid fileid
            self.push_param(-1)  # IOR error

    def word_close_file(self):
        """CLOSE-FILE: ( fileid -- ior )"""
        fileid = self.pop_param()
        
        if fileid in self.open_files:
            try:
                self.open_files[fileid].close()
                del self.open_files[fileid]
                self.push_param(0)  # Success
            except Exception as e:
                print(f"Error closing file: {e}")
                self.push_param(-1)  # IOR error
        else:
            self.push_param(-1)  # File not open

    def word_read_file(self):
        """READ-FILE: ( c-addr u1 fileid -- u2 ior )"""
        fileid = self.pop_param()
        u1 = self.pop_param()
        addr = self.pop_param()
        
        if fileid not in self.open_files:
            self.push_param(0)
            self.push_param(-1)  # File not open
            return
        
        try:
            file_obj = self.open_files[fileid]
            data = file_obj.read(u1)
            bytes_read = len(data)
            
            # Write data to memory
            for i in range(bytes_read):
                self.memory.write_byte(addr + i, ord(data[i]))
            
            self.push_param(bytes_read)
            self.push_param(0)  # Success
        except Exception as e:
            print(f"Error reading file: {e}")
            self.push_param(0)
            self.push_param(-1)

    def word_write_file(self):
        """WRITE-FILE: ( c-addr u fileid -- ior )"""
        fileid = self.pop_param()
        u = self.pop_param()
        addr = self.pop_param()
        
        if fileid not in self.open_files:
            self.push_param(-1)  # File not open
            return
        
        try:
            file_obj = self.open_files[fileid]
            data = ""
            for i in range(u):
                data += chr(self.memory.read_byte(addr + i))
            
            file_obj.write(data)
            self.push_param(0)  # Success
        except Exception as e:
            print(f"Error writing file: {e}")
            self.push_param(-1)

    def word_include_file(self):
        """INCLUDE-FILE: ( c-addr u -- )"""
        length = self.pop_param()
        addr = self.pop_param()
        
        # Read filename from memory
        filename = ""
        for i in range(length):
            char = self.memory.read_byte(addr + i)
            if char == 0:
                break
            filename += chr(char)
        
        try:
            with open(filename, 'r') as f:
                content = f.read()
                self.interpret(content)
        except Exception as e:
            print(f"Error including file {filename}: {e}")

    def define_word(self, name, handler):
        """Define a new FORTH word with validation"""
        if not name:
            raise ValueError("Word name cannot be empty")
            
        if not callable(handler):
            raise TypeError("Word handler must be callable")
            
        # Initialize dictionary if needed
        if not hasattr(self, 'word_dict'):
            self.word_dict = {}
            
        # Check for name conflicts with core words
        if name in self.word_dict:
            if name in [":", ";", "IF", "ELSE", "THEN", "DO", "LOOP", "BEGIN", "UNTIL"]:
                raise ValueError(f"Cannot redefine core word '{name}'")
            print(f"Warning: Redefining word '{name}'")
            
        # Validate word name format
        if not all(c.isalnum() or c in '+-*/<>=_.?":;\'!@' for c in name):
            raise ValueError(f"Invalid word name '{name}'. Use only alphanumeric and +-*/<>=_.?\":;\'!@ characters")
            
        # Store the word definition
        self.word_dict[name] = handler
        
        # Store source information for debugging
        if not hasattr(self, 'word_sources'):
            self.word_sources = {}
        self.word_sources[name] = {
            'defined_at': f"Line {sys._getframe().f_back.f_lineno}",
            'is_core': name in [":", ";", "IF", "ELSE", "THEN", "DO", "LOOP", "BEGIN", "UNTIL"]
        }

    def execute_tokens(self, tokens):
        """Execute a list of tokens with control flow support"""
        ip = 0  # Instruction pointer
        while ip < len(tokens):
            token = tokens[ip]
            
            # Debug print
            # print(f"Executing token[{ip}]: {token}")
            
            # Handle control flow
            if token == 'IF':
                condition = self.pop_param()
                if condition == 0:  # FALSE
                    # Find the corresponding ELSE or THEN
                    depth = 1
                    while ip < len(tokens) and depth > 0:
                        ip += 1
                        if ip >= len(tokens):
                            break
                        if tokens[ip] == 'IF':
                            depth += 1
                        elif tokens[ip] == 'ELSE' and depth == 1:
                            break
                        elif tokens[ip] == 'THEN':
                            depth -= 1
                            if depth == 0:
                                break
                ip += 1
                continue
            elif token == 'ELSE':
                # Skip to THEN
                depth = 1
                while ip < len(tokens) and depth > 0:
                    ip += 1
                    if ip >= len(tokens):
                        break
                    if tokens[ip] == 'IF':
                        depth += 1
                    elif tokens[ip] == 'THEN':
                        depth -= 1
                        if depth == 0:
                            break
                ip += 1
                continue
            elif token == 'THEN':
                ip += 1
                continue
            elif token == 'BEGIN':
                # Mark the beginning of a loop
                begin_ip = ip
                ip += 1
                continue
            elif token == 'UNTIL':
                condition = self.pop_param()
                if condition == 0:  # FALSE, continue loop
                    # Find the corresponding BEGIN
                    depth = 1
                    while ip >= 0 and depth > 0:
                        ip -= 1
                        if tokens[ip] == 'UNTIL':
                            depth += 1
                        elif tokens[ip] == 'BEGIN':
                            depth -= 1
                            if depth == 0:
                                break
                    ip += 1  # Will be incremented again at end of loop
                else:
                    ip += 1
                continue
            elif token == 'DO':
                # DO loop setup
                index = self.pop_param()  # Pop index first (top of stack)
                limit = self.pop_param()  # Pop limit second
                self.push_return(limit)  # Push limit to return stack
                self.push_return(index)  # Push index to return stack
                ip += 1
                continue
            elif token == 'LOOP':
                # LOOP increment and check
                index = self.pop_return()
                limit = self.pop_return()
                index += 1
                if index < limit:
                    # Continue loop
                    self.push_return(limit)
                    self.push_return(index)
                    # Find the corresponding DO
                    depth = 1
                    while ip >= 0 and depth > 0:
                        ip -= 1
                        if tokens[ip] == 'LOOP':
                            depth += 1
                        elif tokens[ip] == 'DO':
                            depth -= 1
                            if depth == 0:
                                break
                    ip += 1  # Will be incremented again at end of loop
                else:
                    ip += 1
                continue
            
            # Execute normal words
            if token in self.word_dict:
                self.word_dict[token]()
            elif token.startswith('PRINT_STR:'):
                # Handle string printing in definitions
                string_content = token[10:]  # Remove 'PRINT_STR:' prefix
                print(string_content, end="")
            else:
                # Try to parse as number
                try:
                    num = int(token, self.base)
                    self.push_param(num)
                except ValueError:
                    print(f"Unknown word in definition: {token}")
            
            ip += 1

    def interpret(self, input_text):
        """Interpret FORTH input"""
        self.input_buffer = input_text.upper()  # FORTH is case-insensitive
        self.input_ptr = 0

        while self.input_ptr < len(self.input_buffer):
            token = self.next_token()
            if not token:
                break

            self.process_token(token)

    def next_token(self):
        """Get next token from input buffer"""
        # Skip whitespace
        while self.input_ptr < len(self.input_buffer):
            char = self.input_buffer[self.input_ptr]
            if char.isspace():
                self.input_ptr += 1
                continue
            else:
                break

        if self.input_ptr >= len(self.input_buffer):
            return None

        # Check for quoted strings
        if self.input_buffer[self.input_ptr] == '"':
            # Collect quoted string
            start = self.input_ptr
            self.input_ptr += 1  # Skip opening quote
            while self.input_ptr < len(self.input_buffer) and self.input_buffer[self.input_ptr] != '"':
                self.input_ptr += 1
            if self.input_ptr < len(self.input_buffer):
                self.input_ptr += 1  # Skip closing quote
            return self.input_buffer[start:self.input_ptr]
        
        # Check for ."
        if (self.input_ptr + 1 < len(self.input_buffer) and 
            self.input_buffer[self.input_ptr:self.input_ptr + 2] == '."'):
            # Collect .\" string
            start = self.input_ptr
            self.input_ptr += 2  # Skip ."
            while self.input_ptr < len(self.input_buffer) and self.input_buffer[self.input_ptr] != '"':
                self.input_ptr += 1
            if self.input_ptr < len(self.input_buffer):
                self.input_ptr += 1  # Skip closing quote
            return self.input_buffer[start:self.input_ptr]
        
        # Check for S"
        if (self.input_ptr + 1 < len(self.input_buffer) and 
            self.input_buffer[self.input_ptr:self.input_ptr + 2] == 'S"'):
            # Collect S\" string
            self.input_ptr += 2  # Skip S"
            # Skip whitespace after S"
            while self.input_ptr < len(self.input_buffer) and self.input_buffer[self.input_ptr].isspace():
                self.input_ptr += 1
            # Now start collecting
            start = self.input_ptr
            # Collect until closing quote
            while self.input_ptr < len(self.input_buffer) and self.input_buffer[self.input_ptr] != '"':
                self.input_ptr += 1
            if self.input_ptr < len(self.input_buffer):
                self.input_ptr += 1  # Skip closing quote
            return 'S"' + self.input_buffer[start:self.input_ptr]  # Include the closing quote

        # Collect regular token
        start = self.input_ptr
        while (self.input_ptr < len(self.input_buffer) and 
               not self.input_buffer[self.input_ptr].isspace() and
               self.input_buffer[self.input_ptr] != '"'):
            self.input_ptr += 1

        return self.input_buffer[start:self.input_ptr]

    def process_token(self, token):
        """Process a FORTH token"""
        # Handle string literals
        if token.startswith('"') or token.startswith('."') or token.startswith('S"'):
            self.handle_string_literal(token)
            return
        
        # Check if it's a number
        try:
            num = int(token, self.base)
            if self.compiling:
                # In compile mode, add the number as a literal
                self.word_definitions.append(str(num))
            else:
                self.push_param(num)
            return
        except ValueError:
            pass

        # Check if it's a defined word
        if hasattr(self, 'word_dict') and token in self.word_dict:
            if self.compiling and token not in [":", ";"]:
                # For control flow words and RECURSE, execute them for compilation logic
                if token in ['IF', 'ELSE', 'THEN', 'BEGIN', 'UNTIL', 'DO', 'LOOP', 'RECURSE']:
                    self.word_dict[token]()
                else:
                    # For regular words, add to definition
                    self.word_definitions.append(token)
            else:
                # Execute immediately
                self.word_dict[token]()
            return

        # Unknown word
        if self.compiling:
            # In compile mode, add unknown words to definition (for forward references)
            self.word_definitions.append(token)
        else:
            print(f"Unknown word: {token}")

    def handle_string_literal(self, token):
        """Handle string literals"""
        if token.startswith('."'):
            # ."
            if self.compiling:
                # Extract string content
                string_start = token.find('"')
                if string_start >= 0:
                    string_content = token[string_start + 1:]
                    if not string_content.endswith('"'):
                        print("Error: Unterminated string")
                        return
                    
                    string_content = string_content[:-1]  # Remove closing quote
                    
                    # Add string printing to the definition
                    self.word_definitions.append(f'PRINT_STR:{string_content}')
                else:
                    print("Error: Invalid string syntax")
            else:
                print('." can only be used in word definitions')
                
        elif token.startswith('S"'):
            # S"
            string_start = token.find('"')
            if string_start >= 0:
                string_content = token[string_start + 1:]
                if not string_content.endswith('"'):
                    print("Error: Unterminated string")
                    return
                
                string_content = string_content[:-1]  # Remove closing quote
                
                # Store string in memory and push address/length
                string_addr = self.here
                self.memory.write_word(string_addr, len(string_content))  # Length
                self.memory.write_word(string_addr + 2, string_addr + 4)  # Address
                
                # Store string data
                for i, char in enumerate(string_content):
                    self.memory.write_byte(string_addr + 4 + i, ord(char))
                
                self.here += 4 + len(string_content)
                
                # Push address and length
                self.push_param(string_addr + 4)  # String address
                self.push_param(len(string_content))  # String length
            else:
                print("Error: Invalid string syntax")
                
        elif token.startswith('"'):
            # Regular string literal
            string_content = token[1:]
            if not string_content.endswith('"'):
                print("Error: Unterminated string")
                return
            
            string_content = string_content[:-1]  # Remove closing quote
            print(string_content, end="")

    def push_param(self, value):
        """Push value onto parameter stack"""
        if self.cpu.Pregisters[8] <= 0xE000:  # Prevent stack overflow
            raise IndexError("Stack overflow")
        self.cpu.Pregisters[8] = (int(self.cpu.Pregisters[8]) - 2) & 0xFFFF  # Decrement SP
        addr = self.cpu.Pregisters[8]
        # Convert to unsigned 16-bit for storage
        unsigned_value = value & 0xFFFF
        self.memory.write_word(addr, unsigned_value)

    def pop_param(self):
        """Pop value from parameter stack"""
        if self.cpu.Pregisters[8] >= self.PARAM_STACK_START:
            raise IndexError("Stack underflow - The parameter stack is empty")
        try:
            addr = self.cpu.Pregisters[8]
            value = self.memory.read_word(addr)
            self.cpu.Pregisters[8] = (int(self.cpu.Pregisters[8]) + 2) & 0xFFFF  # Increment SP
            # Convert to signed 16-bit value
            if value & 0x8000:
                return value - 0x10000
            else:
                return value
        except Exception as e:
            raise RuntimeError(f"Stack error: Failed to pop value from parameter stack: {str(e)}")
            
        return value

    def push_return(self, value):
        """Push value onto return stack"""
        # Check for stack overflow with safety margin
        if self.cpu.Pregisters[9] <= 0xF000:
            raise IndexError("Return stack overflow - Maximum return stack depth exceeded")
        try:
            self.cpu.Pregisters[9] = (int(self.cpu.Pregisters[9]) - 2) & 0xFFFF  # Decrement RP
            addr = self.cpu.Pregisters[9]
            # Convert to unsigned 16-bit for storage
            unsigned_value = value & 0xFFFF
            self.memory.write_word(addr, unsigned_value)
        except Exception as e:
            self.cpu.Pregisters[9] = (int(self.cpu.Pregisters[9]) + 2) & 0xFFFF  # Restore RP on error
            raise RuntimeError(f"Return stack error: Failed to push value: {str(e)}")

    def pop_return(self):
        """Pop value from return stack"""
        if self.cpu.Pregisters[9] >= self.RETURN_STACK_START:
            raise IndexError("Return stack underflow - Return stack is empty")
        try:
            addr = self.cpu.Pregisters[9]
            value = self.memory.read_word(addr)
            self.cpu.Pregisters[9] = (int(self.cpu.Pregisters[9]) + 2) & 0xFFFF  # Increment RP
            # Convert to signed 16-bit value
            if value & 0x8000:
                return value - 0x10000
            else:
                return value
        except Exception as e:
            self.cpu.Pregisters[9] = (int(self.cpu.Pregisters[9]) - 2) & 0xFFFF  # Restore RP on error
            raise RuntimeError(f"Return stack error: Failed to pop value: {str(e)}")

    # Core FORTH word implementations

    def word_dup(self):
        """DUP: Duplicate top of stack"""
        val = self.pop_param()
        self.push_param(val)
        self.push_param(val)

    def word_drop(self):
        """DROP: Remove top of stack"""
        try:
            self.pop_param()
        except IndexError:
            print("Stack underflow in DROP")
            return

    def word_swap(self):
        """SWAP: Swap top two stack items"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            self.push_param(a)
            self.push_param(b)
        except IndexError:
            print("Stack underflow in SWAP")
            return

    def word_over(self):
        """OVER: Copy second item to top"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            self.push_param(b)
            self.push_param(a)
            self.push_param(b)
        except IndexError:
            print("Stack underflow in OVER")
            return

    def word_rot(self):
        """ROT: Rotate top three items"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            c = self.pop_param()
            self.push_param(b)
            self.push_param(a)
            self.push_param(c)
        except IndexError:
            print("Stack underflow in ROT")
            return

    def word_nip(self):
        """NIP: Remove second item from stack"""
        try:
            a = self.pop_param()
            self.pop_param()  # Remove second item
            self.push_param(a)
        except IndexError:
            print("Stack underflow in NIP")
            return

    def word_tuck(self):
        """TUCK: Copy top item under second item"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            self.push_param(a)
            self.push_param(b)
            self.push_param(a)
        except IndexError:
            print("Stack underflow in TUCK")
            return

    def word_qdup(self):
        """?DUP: Duplicate if non-zero"""
        val = self.pop_param()
        if val != 0:
            self.push_param(val)
        self.push_param(val)

    def word_negate(self):
        """NEGATE: Negate top of stack (two's complement)"""
        val = self.pop_param()
        # Two's complement negation for 16-bit
        negated = (-val) & 0xFFFF
        self.push_param(negated)

    def word_abs(self):
        """ABS: Absolute value"""
        val = self.pop_param()
        self.push_param(abs(val))

    def word_min(self):
        """MIN: Minimum of two numbers"""
        a = self.pop_param()
        b = self.pop_param()
        self.push_param(min(a, b))

    def word_max(self):
        """MAX: Maximum of two numbers"""
        a = self.pop_param()
        b = self.pop_param()
        self.push_param(max(a, b))

    def word_sqrt(self):
        """SQRT: Integer square root"""
        n = self.pop_param()
        if n < 0:
            print("Error: SQRT of negative number")
            self.push_param(0)
            return
        if n == 0 or n == 1:
            self.push_param(n)
            return
        
        # Binary search for integer square root
        left, right = 1, n
        result = 1
        while left <= right:
            mid = (left + right) // 2
            if mid * mid == n:
                result = mid
                break
            elif mid * mid < n:
                left = mid + 1
                result = mid
            else:
                right = mid - 1
        self.push_param(result)

    def word_sin(self):
        """SIN: Sine of angle in degrees (0-359), returns scaled value 0-100"""
        angle = self.pop_param() % 360
        if angle < 0:
            angle += 360
        
        val = self.word_sin_impl(angle)
        
        # Adjust sign based on quadrant
        if 180 < angle <= 360:
            val = -val
        
        self.push_param(val)

    def word_cos(self):
        """COS: Cosine of angle in degrees (0-359), returns scaled value 0-100"""
        angle = self.pop_param() % 360
        if angle < 0:
            angle += 360
        
        # COS(angle) = SIN(90 - angle)
        cos_angle = (90 - angle) % 360
        val = self.word_sin_impl(cos_angle)
        
        # Adjust sign based on quadrant
        if 90 < cos_angle <= 270:
            val = -val
        
        self.push_param(val)

    def word_sin_impl(self, angle):
        """Helper for SIN calculation"""
        sin_table = [0, 17, 34, 50, 64, 76, 86, 94, 100, 100, 100]
        index = angle // 10
        frac = angle % 10
        return sin_table[index] + (sin_table[index + 1] - sin_table[index]) * frac // 10

    def word_not_equals(self):
        """<>: Not equal"""
        a = self.pop_param()
        b = self.pop_param()
        self.push_param(-1 if a != b else 0)

    def word_less_equals(self):
        """<=: Less than or equal"""
        a = self.pop_param()
        b = self.pop_param()
        self.push_param(-1 if b <= a else 0)

    def word_greater_equals(self):
        """>=: Greater than or equal"""
        a = self.pop_param()
        b = self.pop_param()
        self.push_param(-1 if b >= a else 0)

    def word_and(self):
        """AND: Bitwise AND"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            self.push_param(a & b)
        except IndexError:
            print("Stack underflow in AND")
            return

    def word_or(self):
        """OR: Bitwise OR"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            self.push_param(a | b)
        except IndexError:
            print("Stack underflow in OR")
            return

    def word_xor(self):
        """XOR: Bitwise XOR"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            self.push_param(a ^ b)
        except IndexError:
            print("Stack underflow in XOR")
            return

    def word_invert(self):
        """INVERT: Bitwise NOT"""
        try:
            val = self.pop_param()
            self.push_param(~val)
        except IndexError:
            print("Stack underflow in INVERT")
            return

    def word_spaces(self):
        """SPACES: Print n spaces"""
        try:
            n = self.pop_param()
            print(" " * n, end="")
        except IndexError:
            print("Stack underflow in SPACES")
            return

    def word_space(self):
        """SPACE: Print one space"""
        print(" ", end="")

    def word_base(self):
        """BASE: Get or set current number base"""
        # If there's a value on the stack, use it to set the base
        # Otherwise, push the current base
        try:
            # Try to peek at the stack without popping
            if self.cpu.Pregisters[8] < self.PARAM_STACK_START:
                addr = self.cpu.Pregisters[8]
                new_base = self.memory.read_word(addr)
                if 2 <= new_base <= 36:  # Valid base range
                    self.base = new_base
                    self.pop_param()  # Remove the base value from stack
                else:
                    print(f"Invalid base: {new_base} (must be 2-36)")
            else:
                # Stack is empty, push current base
                self.push_param(self.base)
        except:
            self.push_param(self.base)

    def word_hex(self):
        """HEX: Set base to 16"""
        self.base = 16

    def word_decimal(self):
        """DECIMAL: Set base to 10"""
        self.base = 10

    def word_fetch(self):
        """@: Fetch value from memory address"""
        try:
            addr = self.pop_param()
            # Ensure address is treated as unsigned for memory access
            addr = addr & 0xFFFF
            value = self.memory.read_word(addr)
            self.push_param(value)
        except IndexError:
            print("Stack underflow in @")
            return

    def word_store(self):
        """!: Store value to memory address"""
        try:
            addr = self.pop_param()   # Pop address first (top of stack)
            value = self.pop_param()  # Pop value second
            # Ensure address is treated as unsigned for memory access
            addr = addr & 0xFFFF
            self.memory.write_word(addr, value)
        except IndexError:
            print("Stack underflow in !")
            return

    def word_add(self):
        """+: Add top two numbers"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            self.push_param(a + b)
        except IndexError:
            print("Stack underflow in +")
            return

    def word_sub(self):
        """-: Subtract top two numbers"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            self.push_param(b - a)
        except IndexError:
            print("Stack underflow in -")
            return

    def word_mul(self):
        """*: Multiply top two numbers"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            self.push_param(a * b)
        except IndexError:
            print("Stack underflow in *")
            return

    def word_div(self):
        """/: Divide top two numbers"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            if a == 0:
                raise ZeroDivisionError("Division by zero in /")
            self.push_param(b // a)
        except IndexError:
            print("Stack underflow in /")
            return

    def word_mod(self):
        """MOD: Modulo operation"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            if a == 0:
                raise ZeroDivisionError("Division by zero in MOD")
            self.push_param(b % a)
        except IndexError:
            print("Stack underflow in MOD")
            return

    def word_equals(self):
        """=: Test equality"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            self.push_param(-1 if a == b else 0)
        except IndexError:
            print("Stack underflow in =")
            return

    def word_less(self):
        """<: Test less than"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            self.push_param(-1 if b < a else 0)
        except IndexError:
            print("Stack underflow in <")
            return

    def word_greater(self):
        """>: Test greater than"""
        try:
            a = self.pop_param()
            b = self.pop_param()
            self.push_param(-1 if b > a else 0)
        except IndexError:
            print("Stack underflow in >")
            return

    def word_colon(self):
        """: Start word definition"""
        # Get the word name
        token = self.next_token()
        if not token:
            print("Error: Expected word name after :")
            return

        self.current_word = token
        self.compiling = True
        self.word_definitions = []  # List to store the word's definition
        self.control_stack = []  # Reset control stack

        print(f"Defining word: {token}")

    def word_semicolon(self):
        """; End word definition"""
        if not self.compiling:
            print("Error: ; without :")
            return

        if not self.current_word:
            print("Error: No word being defined")
            return

        # Create a new word that executes the stored definition
        definition_copy = self.word_definitions.copy()  # Capture a copy to avoid closure issues
        def execute_definition():
            self.execute_tokens(definition_copy)

        # Define the new word
        self.define_word(self.current_word, execute_definition)
        self.word_sources[self.current_word] = self.word_definitions.copy()  # Store for debugging

        print(f"Defined word: {self.current_word}")
        self.current_word = None
        self.compiling = False
        self.word_definitions = []
        self.control_stack = []

    def word_if(self):
        """IF: Conditional execution"""
        if self.compiling:
            self.word_definitions.append('IF')
            self.control_stack.append(('IF', len(self.word_definitions) - 1))
        else:
            print("IF can only be used in word definitions")

    def word_else(self):
        """ELSE: Alternative branch"""
        if self.compiling:
            self.word_definitions.append('ELSE')
            # Find the corresponding IF
            if self.control_stack and self.control_stack[-1][0] == 'IF':
                if_pos = self.control_stack.pop()[1]
                self.control_stack.append(('ELSE', len(self.word_definitions) - 1))
            else:
                print("ELSE without IF")
        else:
            print("ELSE can only be used in word definitions")

    def word_then(self):
        """THEN: End conditional"""
        if self.compiling:
            self.word_definitions.append('THEN')
            # Remove the IF or ELSE from control stack
            if self.control_stack:
                self.control_stack.pop()
        else:
            print("THEN can only be used in word definitions")

    def word_begin(self):
        """BEGIN: Start loop"""
        if self.compiling:
            self.word_definitions.append('BEGIN')
            self.control_stack.append(('BEGIN', len(self.word_definitions) - 1))
        else:
            print("BEGIN can only be used in word definitions")

    def word_until(self):
        """UNTIL: End loop with condition"""
        if self.compiling:
            self.word_definitions.append('UNTIL')
            # Find the corresponding BEGIN
            if self.control_stack and self.control_stack[-1][0] == 'BEGIN':
                self.control_stack.pop()
            else:
                print("UNTIL without BEGIN")
        else:
            print("UNTIL can only be used in word definitions")

    def word_do(self):
        """DO: Start definite loop"""
        if self.compiling:
            self.word_definitions.append('DO')
            self.control_stack.append(('DO', len(self.word_definitions) - 1))
        else:
            print("DO can only be used in word definitions")

    def word_loop(self):
        """LOOP: End definite loop"""
        if self.compiling:
            self.word_definitions.append('LOOP')
            # Find the corresponding DO
            if self.control_stack and self.control_stack[-1][0] == 'DO':
                self.control_stack.pop()
            else:
                print("LOOP without DO")
        else:
            print("LOOP can only be used in word definitions")

    def word_recurse(self):
        """RECURSE: Call the current word being defined"""
        if self.compiling and self.current_word:
            self.word_definitions.append(self.current_word)
        else:
            print("RECURSE can only be used in word definitions")

    def word_dot(self):
        """.: Print number"""
        try:
            val = self.pop_param()
            # Handle 16-bit signed display
            if val & 0x8000:  # If sign bit is set
                display_val = val - 0x10000  # Convert to negative
            else:
                display_val = val
            print(display_val, end=" ")
        except IndexError:
            print("Stack underflow in .")
            return

    def word_emit(self):
        """EMIT: Print character"""
        try:
            val = self.pop_param()
            print(chr(val), end="")
        except IndexError:
            print("Stack underflow in EMIT")
            return

    def word_cr(self):
        """CR: Carriage return"""
        print()

    def word_words(self):
        """WORDS: List all defined words"""
        if hasattr(self, 'word_dict'):
            for word in sorted(self.word_dict.keys()):
                print(word, end=" ")
            print()

    def word_bye(self):
        """BYE: Exit FORTH"""
        print("Goodbye!")
        sys.exit(0)

    def word_i(self):
        """I: Get current loop index"""
        # Check if we're in a loop (return stack has loop info)
        if self.cpu.Pregisters[9] >= self.RETURN_STACK_START:
            print("I can only be used in DO/LOOP constructs")
            return
        # The loop index is the top item on the return stack
        index = self.pop_return()
        self.push_param(index)
        self.push_return(index)  # Put it back

    def word_j(self):
        """J: Get outer loop index (for nested loops)"""
        # Check if we're in nested loops
        if self.cpu.Pregisters[9] >= self.RETURN_STACK_START:
            print("J can only be used in nested DO/LOOP constructs")
            return
        # The outer loop index is the third item on the return stack
        # Return stack: [outer_limit, outer_index, inner_limit, inner_index]
        # So we need to pop 4 items, get the third one, then push them back
        inner_index = self.pop_return()
        inner_limit = self.pop_return()
        outer_index = self.pop_return()
        outer_limit = self.pop_return()
        
        self.push_param(outer_index)
        
        # Push everything back
        self.push_return(outer_limit)
        self.push_return(outer_index)
        self.push_return(inner_limit)
        self.push_return(inner_index)

    def word_variable(self):
        """VARIABLE: Create a variable"""
        # Get variable name from input stream
        token = self.next_token()
        if not token:
            print("Error: Expected variable name after VARIABLE")
            return
        
        # Allocate space for the variable
        var_addr = self.here
        self.here += 2  # Variables are 16-bit
        
        # Initialize variable to 0
        self.memory.write_word(var_addr, 0)
        
        # Create a word that pushes the variable address
        def variable_word():
            self.push_param(var_addr)
        
        # Define the variable word
        self.define_word(token, variable_word)
        print(f"Variable {token} created at address 0x{var_addr:04X}")

    def word_constant(self):
        """CONSTANT: Create a constant"""
        # Get the value from stack
        value = self.pop_param()
        
        # Get constant name from input stream
        token = self.next_token()
        if not token:
            print("Error: Expected constant name after CONSTANT")
            return
        
        # Create a word that pushes the constant value
        def constant_word():
            self.push_param(value)
        
        # Define the constant word
        self.define_word(token, constant_word)
        print(f"Constant {token} = {value}")

    def word_dot_quote(self):
        """.": Print string literal"""
        # This is handled in process_token for string literals
        print('." should be followed by a string in quotes')

    def word_s_quote(self):
        """S": Create string literal on stack"""
        # This is handled in process_token for string literals
        print('S" should be followed by a string in quotes')

    def repl(self):
        """Read-Eval-Print Loop"""
        print("NOVA-16 FORTH Interpreter")
        print("Type 'BYE' to exit")

        while True:
            try:
                line = input("> ")
                if line.strip():
                    self.interpret(line)
            except KeyboardInterrupt:
                print("\nUse BYE to exit")
            except EOFError:
                break

def main():
    """Main entry point"""
    forth = ForthInterpreter()
    forth.repl()

if __name__ == "__main__":
    main()
