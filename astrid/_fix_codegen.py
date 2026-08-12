"""One-shot fix: remove stray diff markers and fix builtin_set_pointers clobber."""
import ast

path = 'astrid/astrid_codegen.py'
lines = open(path, encoding='utf-8').read().split('\n')
cleaned = []
for ln in lines:
    s = ln.strip()
    if s in ('>>>>>>>', '</task_progress>', '<<<<<<<', '======='):
        continue
    cleaned.append(ln)
text = '\n'.join(cleaned)

# Fix builtin_set_pointers: MOV P0, R2 clobbers the return-address temp P0
# before PUSH P0. Use P2 as the destination temp so P0 (ret addr) survives.
old = ('self.emit_label("builtin_set_pointers")\n'
       '        self.emit("    POP P0"); self.emit("    POP R1"); self.emit("    POP R2"); '
       'self.emit("    MOV P0, R2"); self.emit("    MOV P1, R1"); self.emit("    PUSH P0"); self.emit("    RET")')
new = ('self.emit_label("builtin_set_pointers")\n'
       '        self.emit("    POP P0"); self.emit("    POP R1"); self.emit("    POP R2"); '
       '# Use P2 as scratch so P0 (return address) is preserved\n'
       '        self.emit("    MOV P2, R2"); self.emit("    MOV P1, R1"); '
       'self.emit("    MOV P0, P2"); self.emit("    PUSH P0"); self.emit("    RET")')
text = text.replace(old, new)

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)

ast.parse(open(path, encoding='utf-8').read())
print('FIXED: removed stray markers, patched set_pointers, syntax OK')
