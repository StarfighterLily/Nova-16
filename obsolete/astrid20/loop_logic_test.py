#!/usr/bin/env python3
"""
Loop Logic Verification Test
Specifically tests the loop comparison logic to confirm the bug
"""

import os
import sys
import tempfile

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from astrid2.main import AstridCompiler
from nova_assembler import Assembler
from nova import run_headless

def test_loop_logic():
    """Test loop comparison logic in detail."""
    print("LOOP LOGIC VERIFICATION TEST")
    print("="*50)
    
    source_code = """
        void main() {
            int8 counter = 0;
            for(int8 i = 0; i < 3; i++) {
                counter = counter + 1;
            }
            halt();
        }
    """
    
    # Compile
    compiler = AstridCompiler()
    try:
        print("🔄 Compiling...")
        asm_code = compiler.compile(source_code, "loop_test.ast", verbose=True)
        print("✅ Compilation successful")
        
        # Print assembly with line numbers for analysis
        print("\n📝 Generated Assembly (for analysis):")
        print("-"*60)
        lines = asm_code.split('\n')
        for i, line in enumerate(lines, 1):
            if line.strip():
                print(f"{i:2d}: {line}")
        print("-"*60)
        
    except Exception as e:
        print(f"❌ Compilation failed: {e}")
        return False
    
    # Execute step by step
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as asm_file:
            asm_file.write(asm_code)
            asm_filename = asm_file.name
        
        base_name = os.path.splitext(asm_filename)[0]
        bin_filename = f"{base_name}.bin"
        
        assembler = Assembler()
        success = assembler.assemble(asm_filename)
        if not success:
            raise Exception("Assembly failed")
            
        print("\n🔄 Executing with step-by-step analysis...")
        result = run_headless(bin_filename, 1000)
        proc, mem, gfx = result
        
        print("✅ Execution completed")
        print(f"\n📊 Final Results:")
        print(f"   PC: 0x{proc.pc:04X}")
        print(f"   R0 (counter): {proc.Rregisters[0]} (expected: 3)")
        print(f"   R1 (i): {proc.Rregisters[1]} (expected: 3)")
        
        # Check if loop executed correctly
        counter_val = proc.Rregisters[0]  # Assuming counter is in R0
        if counter_val == 3:
            print("✅ Loop executed correctly! Counter = 3")
            return True
        elif counter_val == 0:
            print("❌ Loop never executed. Counter = 0")
            print("   This confirms the loop condition bug!")
            return False
        else:
            print(f"❓ Loop executed {counter_val} times instead of 3")
            return False
            
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        return False
    finally:
        try:
            os.unlink(asm_filename)
            if os.path.exists(bin_filename):
                os.unlink(bin_filename)
            org_filename = f"{os.path.splitext(asm_filename)[0]}.org"
            if os.path.exists(org_filename):
                os.unlink(org_filename)
        except:
            pass

def main():
    """Run the loop logic verification test."""
    success = test_loop_logic()
    
    print(f"\n{'='*50}")
    print("LOOP LOGIC TEST CONCLUSION")
    print(f"{'='*50}")
    
    if success:
        print("✅ Loop logic is working correctly")
    else:
        print("❌ Loop logic bug confirmed")
        print("\nRecommended fix:")
        print("- Check loop condition comparison logic")
        print("- Verify JC vs JB instruction usage")
        print("- Review flag handling in comparisons")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
