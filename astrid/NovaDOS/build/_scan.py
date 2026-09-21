from pathlib import Path
p = Path(r"c:\Code\projects\Nova\astrid\NovaDOS\src\kernel\kernel.ast")
c = p.read_text(encoding="utf-8")
for name in ["void shell_dir", "void shell_type", "void shell_help", "shell_cmd = 1", "ndf_find", "void shell_mem"]:
    print(name, c.find(name))
print("len", len(c))
# show lines around help
lines = c.splitlines()
for i, line in enumerate(lines):
    if "shell_help" in line or "shell_cmd = 6" in line or "shell_type" in line and "void" in line:
        print(f"{i+1}: {line}")
