#!/usr/bin/env python3
"""
Critical Bug Isolation Test Suite
Focuses on the most critical bugs found in the Astrid pipeline for targeted debugging
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

def test_critical_bug(name, source_code, description):
    """Test a specific critical bug in isolation."""
    print(f"\n{'='*60}")
    print(f"CRITICAL BUG TEST: {name}")
    print(f"Description: {description}")
    print(f"{'='*60}")
    
    # Step 1: Compile
    compiler = AstridCompiler()
    try:
        print("🔄 Compiling Astrid source...")
        asm_code = compiler.compile(source_code, f"test_{name}.ast", verbose=True)
        print("✅ Compilation successful")
        print("\n📝 Generated Assembly:")
        print("-" * 40)
        for i, line in enumerate(asm_code.split('\n'), 1):
            if line.strip():
                print(f"{i:2d}: {line}")
        print("-" * 40)
    except Exception as e:
        print(f"❌ Compilation failed: {e}")
        return False
    
    # Step 2: Assemble  
    try:
        print("\n🔄 Assembling to binary...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as asm_file:
            asm_file.write(asm_code)
            asm_filename = asm_file.name
        
        base_name = os.path.splitext(asm_filename)[0]
        bin_filename = f"{base_name}.bin"
        
        assembler = Assembler()
        success = assembler.assemble(asm_filename)
        if not success:
            raise Exception("Assembly failed")
        print("✅ Assembly successful")
        
    except Exception as e:
        print(f"❌ Assembly failed: {e}")
        return False
    finally:
        try:
            os.unlink(asm_filename)
            org_filename = f"{os.path.splitext(asm_filename)[0]}.org"
            if os.path.exists(org_filename):
                os.unlink(org_filename)
        except:
            pass
    
    # Step 3: Execute and analyze
    try:
        print("\n🔄 Executing program...")
        result = run_headless(bin_filename, 1000)
        proc, mem, gfx = result
        
        print("✅ Execution completed")
        print(f"\n📊 Execution Results:")
        print(f"   Final PC: 0x{proc.pc:04X}")
        print(f"   Total Cycles: {proc.cycle_count if hasattr(proc, 'cycle_count') else 'Unknown'}")
        
        print(f"\n📋 Register States:")
        print("   R0-R9:", [f"0x{r:04X}" for r in proc.Rregisters[:10]])
        print("   P0-P9:", [f"0x{r:04X}" for r in proc.Pregisters[:10]])
        print(f"   Stack Pointer: 0x{proc.sp:04X}")
        
        print(f"\n🧠 Memory Sample (first 32 bytes):")
        memory_sample = []
        for i in range(32):
            try:
                memory_sample.append(f"{mem.read_byte(i):02X}")
            except:
                memory_sample.append("??")
        print("   " + " ".join(memory_sample))
        
        return True
        
    except Exception as e:
        print(f"❌ Execution failed: {e}")
        return False
    finally:
        try:
            os.unlink(bin_filename)
            org_filename = f"{os.path.splitext(bin_filename)[0]}.org"
            if os.path.exists(org_filename):
                os.unlink(org_filename)
        except:
            pass

def main():
    """Run critical bug isolation tests."""
    print("ASTRID 2.0 CRITICAL BUG ISOLATION TEST SUITE")
    print("=" * 60)
    
    critical_tests = [
        
        # Test 1: Most basic variable assignment
        {
            "name": "basic_variable_assignment",
            "description": "Test if simple variable assignment works at all",
            "source": """
                void main() {
                    int8 x = 42;
                    halt();
                }
            """
        },
        
        # Test 2: Stack initialization
        {
            "name": "stack_initialization",
            "description": "Test if stack pointer is properly initialized",
            "source": """
                void main() {
                    halt();
                }
            """
        },
        
        # Test 3: Simple function call
        {
            "name": "simple_function_call",
            "description": "Test if basic function calls work",
            "source": """
                void test() {
                    return;
                }
                
                void main() {
                    test();
                    halt();
                }
            """
        },
        
        # Test 4: Basic arithmetic
        {
            "name": "basic_arithmetic",
            "description": "Test if simple addition works",
            "source": """
                void main() {
                    int8 a = 5;
                    int8 b = 3;
                    int8 c = a + b;
                    halt();
                }
            """
        },
        
        # Test 5: Simple loop
        {
            "name": "simple_loop",
            "description": "Test if basic for loop works",
            "source": """
                void main() {
                    for(int8 i = 0; i < 3; i++) {
                        // Just loop
                    }
                    halt();
                }
            """
        },
        
        # Test 6: Memory write
        {
            "name": "memory_write",
            "description": "Test if memory_write function works",
            "source": """
                void main() {
                    memory_write(0x2000, 123);
                    halt();
                }
            """
        },
        
        # Test 7: Simple conditional
        {
            "name": "simple_conditional",
            "description": "Test if basic if statement works",
            "source": """
                void main() {
                    int8 x = 10;
                    if (x > 5) {
                        x = 20;
                    }
                    halt();
                }
            """
        },
        
        # Test 8: Register allocation stress
        {
            "name": "register_stress",
            "description": "Test what happens when we run out of registers",
            "source": """
                void main() {
                    int8 a = 1; int8 b = 2; int8 c = 3; int8 d = 4; int8 e = 5;
                    int8 f = 6; int8 g = 7; int8 h = 8; int8 i = 9; int8 j = 10;
                    int8 k = 11; // This should force spill
                    halt();
                }
            """
        },
    ]
    
    passed = 0
    total = len(critical_tests)
    
    for test in critical_tests:
        if test_critical_bug(test["name"], test["source"], test["description"]):
            passed += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"CRITICAL BUG TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed < total:
        print(f"\n❌ {total - passed} critical bugs confirmed")
    else:
        print(f"\n✅ All critical tests passed!")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
