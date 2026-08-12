import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import nova_disassembler as nd

# Load binary with org info
data = nd.load_org_segments('astrid/simple.bin', 'astrid/simple.org')
sym = nd.load_symbol_table('astrid/simple.sym')

# Disassemble around PC=0x10B2
lines = nd.disassemble(data, sym, start_addr=0x1090, count=40, show_addresses=True, show_hex=True)
for l in lines:
    print(l)
