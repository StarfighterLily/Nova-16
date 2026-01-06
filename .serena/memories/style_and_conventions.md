# Style & Conventions
- General: Follow Nova-16 Development Guidelines (.github/copilot-instructions) — make no assumptions without checking, double-check work, implement in small steps and test often, prefer MCP tools for assemble/run/debug.
- Architecture notes: 64KB unified memory; registers R0-R9 (8-bit), P0-P9 (16-bit; P8=SP, P9=FP); graphics regs VX/VY/VM/VL/VC; sound regs SA/SF/SV/SW; timer TT/TM/TC/TS; zero page 0x0000-0x00FF is fast; interrupt vectors 0x0100-0x011F; sprite control 0xF000-0xF0FF.
- Stack: grows downward from 0xFFFF; CALL/RET use stack; prefer PUSH/POP; manage FP (P9) when building frames.
- Assembly quirks: labels case-sensitive; comments start with ';'; P registers accessible as high/low via P0:/ :P0 syntax.
- No formal lint/format config detected; use standard Python style and keep ASCII unless file already uses Unicode.
- Testing mindset: small, incremental changes; verify with emulator/headless runs or MCP debugger; avoid destructive git commands.