#!/usr/bin/env python3
"""Apply fixes to astrid/codegen/codegen.py"""

filepath = 'astrid/codegen/codegen.py'

with open(filepath, 'r') as f:
    content = f.read()

# Fix 1: Remove P3 from allocation_order
old_alloc = "        self.allocation_order = [\n            'P0', 'P1', 'P2', 'P3', 'P4', 'P5', 'P6',\n            'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9',\n        ]"
new_alloc = "        self.allocation_order = [\n            'P0', 'P1', 'P2', 'P4', 'P5', 'P6',\n            'R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9',\n        ]"
content = content.replace(old_alloc, new_alloc)

# Fix 2: Fix excluded set to use string 'P3'
old_excluded = "        excluded = {3} | (exclude or set())"
new_excluded = "        excluded = {'P3'} | (exclude or set())"
content = content.replace(old_excluded, new_excluded)

# Fix 3: Fix free_register to actually clear temp registers
old_free = "    def free_register(self):\n        pass\n"
new_free = "    def free_register(self):\n        # Free temporary registers after last use.\n        self._clear_temp_registers()\n"
content = content.replace(old_free, new_free)

with open(filepath, 'w') as f:
    f.write(content)

print("Fixes applied successfully")

# Verify
with open(filepath, 'r') as f:
    result = f.read()

checks = [
    ("P3 not in allocation_order", "'P3', 'P4'" not in result),
    ("excluded uses string 'P3'", "excluded = {'P3'}" in result),
    ("free_register calls _clear_temp_registers", "self._clear_temp_registers()" in result),
]

for desc, passed in checks:
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {desc}")
