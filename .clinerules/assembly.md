### 1. The Golden Rule of Comments: Explain the "Why," Not the "What"
- Assembly is often jokingly called a "write-only" language. You fix this with meticulous commentary. Anyone reading your code already knows what the mnemonics do. Your comments must explain the broader intent.

Bad: mov r0, 10 ; Move 10 into R0 (Redundant and useless)

Good: mov r0, 10 ; Initialize retry counter for the I/O bus (Explains the state machine)

Pro-tip: Use block comments at the start of every subroutine detailing the inputs, outputs, registers modified (clobbered), and the overall algorithmic goal.

### 2. Respect the ABI (Application Binary Interface)
- The ABI is the sacred treaty between your assembly code and the system. Violating it means silent, catastrophic crashes that only appear under specific loads.

Caller-Saved vs. Callee-Saved: Memorize which registers you are allowed to destroy (caller-saved/volatile) and which you must restore before returning (callee-saved/non-volatile).

### 3. Structural Discipline
- Assembly can turn into "spaghetti code" faster than almost any other language. Impose strict structure on your files.

Align Your Columns: Visually structure your code so that labels, mnemonics, operands, and comments all line up in neat vertical columns. Your eyes should be able to scan down the operation column without jumping horizontally.

Use Local Labels: When writing loops or conditional jumps, use local labels (often prefixed with a . or @ depending on the assembler) so you don't pollute the global namespace.

Macros vs. Subroutines: Don't repeat yourself. Use both tools strategically:
* Macro (inlined by assembler): Binary size increases if used heavily. Best for short, frequent operations (e.g., complex bitwise masking)
* Subroutine: Call/Return branch latency. Best for minimal complex, multi-step logic that isn't performance-critical

### 4. Mechanical Sympathy
- To write high-quality assembly, you have to write code the way the processor wants to read it.

Respect Branch Prediction: Jumps are expensive. The CPU tries to guess which way a branch will go. Structure your code so the "happy path" (the most common scenario) falls straight through without jumping. Put error handling at the bottom of the function.

Memory is a Bottleneck: Registers are instant. L1 Cache is fast. Main memory is an eternity. Pack your data tightly, process it sequentially, and avoid jumping randomly through memory to prevent cache misses.

### 5. Defense in Depth
- When you are this close to the metal, a single off-by-one error doesn't throw an exception—it overwrites the return address and executes garbage.

Clear Sensitive Data: If your routine handles passwords, cryptographic keys, or sensitive buffers, manually zero out those registers and memory locations before returning.

Watch the Flags: Instructions often modify status flags (Zero, Carry, Overflow) as a side effect. Be acutely aware of which instructions silently change your flags before your conditional jumps.