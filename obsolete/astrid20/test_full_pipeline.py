#!/usr/bin/env python3
"""
Enhanced Test Suite for Astrid 2.0 Full Pipeline
Tests compilation, assembly, and execution to find remaining bugs
"""

import os
import sys
import subprocess
import tempfile
import time
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from astrid2.main import AstridCompiler
from nova_assembler import Assembler
from nova import run_headless

class PipelineTest:
    """Test case for the full pipeline."""
    
    def __init__(self, name, source_code, expected_registers=None, expected_memory=None, 
                 max_cycles=1000, should_compile=True, should_assemble=True, should_execute=True):
        self.name = name
        self.source_code = source_code
        self.expected_registers = expected_registers or {}
        self.expected_memory = expected_memory or {}
        self.max_cycles = max_cycles
        self.should_compile = should_compile
        self.should_assemble = should_assemble
        self.should_execute = should_execute

def run_pipeline_test(test_case):
    """Run a complete pipeline test."""
    print(f"\n=== Testing: {test_case.name} ===")
    
    # Step 1: Compile Astrid to Assembly
    compiler = AstridCompiler()
    try:
        asm_code = compiler.compile(test_case.source_code, f"test_{test_case.name}.ast", verbose=False)
        if not test_case.should_compile:
            print(f"❌ {test_case.name}: Expected compilation failure but succeeded")
            return False
        print(f"✅ Compilation successful")
    except Exception as e:
        if test_case.should_compile:
            print(f"❌ {test_case.name}: Compilation failed - {e}")
            return False
        else:
            print(f"✅ Expected compilation failure - {e}")
            return True
    
    # Step 2: Assemble to binary
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as asm_file:
            asm_file.write(asm_code)
            asm_filename = asm_file.name
        
        # Generate binary filename based on asm filename
        base_name = os.path.splitext(asm_filename)[0]
        bin_filename = f"{base_name}.bin"
        
        assembler = Assembler()
        success = assembler.assemble(asm_filename)
        if not success:
            raise Exception("Assembly failed")
            
        if not test_case.should_assemble:
            print(f"❌ {test_case.name}: Expected assembly failure but succeeded")
            return False
        print(f"✅ Assembly successful")
        
    except Exception as e:
        if test_case.should_assemble:
            print(f"❌ {test_case.name}: Assembly failed - {e}")
            return False
        else:
            print(f"✅ Expected assembly failure - {e}")
            return True
    finally:
        # Clean up temp files
        try:
            os.unlink(asm_filename)
            # Also clean up .org file if it exists
            org_filename = f"{os.path.splitext(asm_filename)[0]}.org"
            if os.path.exists(org_filename):
                os.unlink(org_filename)
        except:
            pass
    
    # Step 3: Execute and verify
    try:
        if not test_case.should_execute:
            print(f"⚠️  Skipping execution test")
            return True
            
        # Run the program
        result = run_headless(bin_filename, test_case.max_cycles)
        proc, mem, gfx = result
        
        print(f"✅ Execution completed")
        print(f"   Final PC: 0x{proc.pc:04X}")
        
        # Verify register states
        all_checks_passed = True
        for reg_name, expected_value in test_case.expected_registers.items():
            if reg_name.startswith('R'):
                reg_index = int(reg_name[1:])
                actual_value = proc.Rregisters[reg_index]
            elif reg_name.startswith('P'):
                reg_index = int(reg_name[1:])
                actual_value = proc.Pregisters[reg_index]
            else:
                continue
                
            if actual_value != expected_value:
                print(f"❌ Register {reg_name}: expected 0x{expected_value:04X}, got 0x{actual_value:04X}")
                all_checks_passed = False
            else:
                print(f"✅ Register {reg_name}: 0x{actual_value:04X}")
        
        # Verify memory states
        for addr, expected_value in test_case.expected_memory.items():
            actual_value = mem.read_byte(addr)
            if actual_value != expected_value:
                print(f"❌ Memory[0x{addr:04X}]: expected 0x{expected_value:02X}, got 0x{actual_value:02X}")
                all_checks_passed = False
            else:
                print(f"✅ Memory[0x{addr:04X}]: 0x{actual_value:02X}")
        
        return all_checks_passed
        
    except Exception as e:
        if test_case.should_execute:
            print(f"❌ {test_case.name}: Execution failed - {e}")
            return False
        else:
            print(f"✅ Expected execution failure - {e}")
            return True
    finally:
        # Clean up temp files
        try:
            os.unlink(bin_filename)
            # Also clean up .org file if it exists
            org_filename = f"{os.path.splitext(bin_filename)[0]}.org"
            if os.path.exists(org_filename):
                os.unlink(org_filename)
        except:
            pass

def main():
    """Run enhanced pipeline tests."""
    
    # Define test cases
    test_cases = [
        
        # Test 1: Basic arithmetic
        PipelineTest(
            "basic_arithmetic",
            """
            void main() {
                int8 a = 10;
                int8 b = 20;
                int8 c = a + b;
                halt();
            }
            """,
            expected_registers={"R2": 10, "R3": 20, "R4": 30}
        ),
        
        # Test 2: Function calls with parameters
        PipelineTest(
            "function_calls",
            """
            int8 add(int8 x, int8 y) {
                return x + y;
            }
            
            void main() {
                int8 result = add(15, 25);
                halt();
            }
            """,
            expected_registers={"R0": 40}
        ),
        
        # Test 3: Loops
        PipelineTest(
            "loop_test",
            """
            void main() {
                int8 sum = 0;
                for(int8 i = 1; i <= 5; i++) {
                    sum = sum + i;
                }
                halt();
            }
            """,
            expected_registers={"R0": 15, "R1": 6}  # sum=15, i=6 after loop
        ),
        
        # Test 4: If statements
        PipelineTest(
            "conditional_test",
            """
            void main() {
                int8 x = 100;
                int8 result = 0;
                if (x > 50) {
                    result = 1;
                } else {
                    result = 2;
                }
                halt();
            }
            """,
            expected_registers={"R0": 100, "R1": 1}
        ),
        
        # Test 5: Graphics operations
        PipelineTest(
            "graphics_test",
            """
            void main() {
                set_pixel(100, 120, 31);
                int8 x = 50;
                int8 y = 60;
                int8 color = 15;
                set_pixel(x, y, color);
                halt();
            }
            """,
            expected_registers={"R0": 50, "R1": 60, "R2": 15}
        ),
        
        # Test 6: Mixed data types
        PipelineTest(
            "mixed_types",
            """
            void main() {
                int8 small = 42;
                int16 big = 1000;
                int16 sum = big + small;
                halt();
            }
            """,
            expected_registers={"R0": 42, "P0": 1000, "P1": 1042}
        ),
        
        # Test 7: Hardware types
        PipelineTest(
            "hardware_types",
            """
            void main() {
                pixel p = 128;
                color c = 31;
                layer l = 3;
                halt();
            }
            """,
            expected_registers={"R0": 128, "R1": 31, "R2": 3}
        ),
        
        # Test 8: Complex expressions
        PipelineTest(
            "complex_expressions",
            """
            void main() {
                int8 a = 10;
                int8 b = 20;
                int8 c = 5;
                int8 result = (a + b) * c - 3;
                halt();
            }
            """,
            expected_registers={"R0": 10, "R1": 20, "R2": 5, "R3": 147}
        ),
        
        # Test 9: Nested function calls
        PipelineTest(
            "nested_calls",
            """
            int8 double_val(int8 x) {
                return x * 2;
            }
            
            int8 quad_val(int8 x) {
                return double_val(double_val(x));
            }
            
            void main() {
                int8 result = quad_val(5);
                halt();
            }
            """,
            expected_registers={"R0": 20}
        ),
        
        # Test 10: Memory operations
        PipelineTest(
            "memory_operations",
            """
            void main() {
                memory_write(0x2000, 123);
                int8 value = memory_read(0x2000);
                halt();
            }
            """,
            expected_registers={"R0": 123},
            expected_memory={0x2000: 123}
        ),
        
        # Test 11: Interrupt handler test (should compile but not execute interrupt)
        PipelineTest(
            "interrupt_handler",
            """
            interrupt timer_handler() {
                memory_write(0x3000, 99);
                return;
            }
            
            void main() {
                int8 x = 42;
                halt();
            }
            """,
            expected_registers={"R0": 42}
        ),
        
        # Test 12: Large register usage (stress test)
        PipelineTest(
            "register_stress",
            """
            void main() {
                int8 r0 = 0; int8 r1 = 1; int8 r2 = 2; int8 r3 = 3; int8 r4 = 4;
                int8 r5 = 5; int8 r6 = 6; int8 r7 = 7; int8 r8 = 8; int8 r9 = 9;
                int8 sum = r0 + r1 + r2 + r3 + r4 + r5 + r6 + r7 + r8 + r9;
                halt();
            }
            """,
            expected_registers={"R9": 45}  # Only check the sum in last register
        ),
        
        # Test 13: Ternary operator
        PipelineTest(
            "ternary_operator",
            """
            void main() {
                int8 x = 30;
                int8 result = x > 20 ? 100 : 200;
                halt();
            }
            """,
            expected_registers={"R0": 30, "R1": 100}
        ),
        
        # Test 14: Sound operations
        PipelineTest(
            "sound_test",
            """
            void main() {
                play_tone(440, 128, 100);
                halt();
            }
            """,
            max_cycles=1000
        ),
        
        # Test 15: Invalid syntax (should fail compilation)
        PipelineTest(
            "invalid_syntax",
            """
            void main() {
                int8 x = ;  // Invalid syntax
                halt();
            }
            """,
            should_compile=False
        ),
        
        # Test 16: Arrays (should fail - not implemented)
        PipelineTest(
            "arrays_unsupported",
            """
            void main() {
                int8 array[10];
                array[0] = 42;
                halt();
            }
            """,
            should_compile=False
        ),
        
        # Test 17: Structs (should fail - not implemented) 
        PipelineTest(
            "structs_unsupported",
            """
            struct Point {
                int8 x;
                int8 y;
            };
            
            void main() {
                Point p;
                p.x = 10;
                halt();
            }
            """,
            should_compile=False
        ),
        
        # Test 18: Register allocation test (stress test)
        PipelineTest(
            "register_allocation_test",
            """
            void main() {
                int8 a = 1; int8 b = 2; int8 c = 3; int8 d = 4; int8 e = 5;
                int8 f = 6; int8 g = 7; int8 h = 8; int8 i = 9; int8 j = 10;
                int8 k = 11; int8 l = 12; // Forces spill to memory
                int8 result = a + b + c + d + e + f + g + h + i + j + k + l;
                halt();
            }
            """,
            max_cycles=2000
        ),
        
        # Test 19: Stack operations test
        PipelineTest(
            "stack_operations",
            """
            int8 recursive_sum(int8 n) {
                if (n <= 1) {
                    return n;
                }
                return n + recursive_sum(n - 1);
            }
            
            void main() {
                int8 result = recursive_sum(5);
                halt();
            }
            """,
            expected_registers={"R0": 15},
            max_cycles=5000
        ),
        
        # Test 20: Memory access patterns
        PipelineTest(
            "memory_patterns",
            """
            void main() {
                // Test sequential memory writes
                memory_write(0x2000, 10);
                memory_write(0x2001, 20);
                memory_write(0x2002, 30);
                
                // Test sequential memory reads
                int8 a = memory_read(0x2000);
                int8 b = memory_read(0x2001);
                int8 c = memory_read(0x2002);
                int8 sum = a + b + c;
                halt();
            }
            """,
            expected_registers={"R3": 60},
            expected_memory={0x2000: 10, 0x2001: 20, 0x2002: 30}
        ),
        
        # Test 21: Graphics stress test
        PipelineTest(
            "graphics_stress",
            """
            void main() {
                // Draw multiple pixels
                for(int8 i = 0; i < 10; i++) {
                    set_pixel(i * 10, i * 5, i + 1);
                }
                halt();
            }
            """,
            max_cycles=3000
        ),
        
        # Test 22: Mixed operations stress
        PipelineTest(
            "mixed_operations_stress",
            """
            void main() {
                int8 counter = 0;
                for(int8 i = 0; i < 5; i++) {
                    for(int8 j = 0; j < 3; j++) {
                        counter = counter + 1;
                        memory_write(0x3000 + counter, counter);
                    }
                }
                halt();
            }
            """,
            expected_registers={"R0": 15},
            max_cycles=5000
        ),
        
        # Test 23: Type conversion edge cases
        PipelineTest(
            "type_conversion",
            """
            void main() {
                int8 small = 255;  // Max value for int8
                int16 big = small; // Should convert properly
                int8 back = big;   // Should convert back
                halt();
            }
            """,
            expected_registers={"R0": 255, "P0": 255, "R1": 255}
        ),
        
        # Test 24: Comparison operations
        PipelineTest(
            "comparison_ops",
            """
            void main() {
                int8 a = 10;
                int8 b = 20;
                int8 less = a < b ? 1 : 0;
                int8 greater = a > b ? 1 : 0;
                int8 equal = a == b ? 1 : 0;
                int8 not_equal = a != b ? 1 : 0;
                halt();
            }
            """,
            expected_registers={"R2": 1, "R3": 0, "R4": 0, "R5": 1}
        ),
        
        # Test 25: Mathematical operations
        PipelineTest(
            "math_operations",
            """
            void main() {
                int8 a = 15;
                int8 b = 3;
                int8 add = a + b;
                int8 sub = a - b;
                int8 mul = a * b;
                int8 div = a / b;
                int8 mod = a % b;
                halt();
            }
            """,
            expected_registers={"R2": 18, "R3": 12, "R4": 45, "R5": 5, "R6": 0}
        ),
        
        # Test 26: Logical operations
        PipelineTest(
            "logical_operations",
            """
            void main() {
                int8 a = 1;
                int8 b = 0;
                int8 and_op = a && b;
                int8 or_op = a || b;
                int8 not_op = !a;
                halt();
            }
            """,
            expected_registers={"R2": 0, "R3": 1, "R4": 0}
        ),
        
        # Test 27: Variable scoping
        PipelineTest(
            "variable_scoping",
            """
            void main() {
                int8 outer = 10;
                {
                    int8 inner = 20;
                    outer = outer + inner;
                }
                // inner should be out of scope here
                halt();
            }
            """,
            expected_registers={"R0": 30}
        ),
        
        # Test 28: Function return values
        PipelineTest(
            "function_returns",
            """
            int8 get_value() {
                return 42;
            }
            
            int16 get_big_value() {
                return 1000;
            }
            
            void main() {
                int8 small_val = get_value();
                int16 big_val = get_big_value();
                halt();
            }
            """,
            expected_registers={"R0": 42, "P0": 1000}
        ),
        
        # Test 29: Complex control flow
        PipelineTest(
            "complex_control_flow",
            """
            void main() {
                int8 result = 0;
                for(int8 i = 1; i <= 3; i++) {
                    if (i == 2) {
                        continue;
                    }
                    result = result + i;
                }
                halt();
            }
            """,
            expected_registers={"R0": 4}  # 1 + 3 (skipping 2)
        ),
        
        # Test 30: Error conditions - Division by zero
        PipelineTest(
            "division_by_zero",
            """
            void main() {
                int8 a = 10;
                int8 b = 0;
                int8 result = a / b;
                halt();
            }
            """,
            should_execute=True,  # Should execute but may produce unexpected results
            max_cycles=100
        ),
        
        # Test 31: Memory boundary test
        PipelineTest(
            "memory_boundary",
            """
            void main() {
                // Test writing to different memory regions
                memory_write(0x0000, 1);  // Zero page
                memory_write(0x00FF, 2);  // End of zero page
                memory_write(0x0100, 3);  // Start of interrupt vectors
                memory_write(0xFFFF, 4);  // End of memory
                
                int8 val1 = memory_read(0x0000);
                int8 val2 = memory_read(0x00FF);
                int8 val3 = memory_read(0x0100);
                int8 val4 = memory_read(0xFFFF);
                halt();
            }
            """,
            expected_registers={"R0": 1, "R1": 2, "R2": 3, "R3": 4},
            expected_memory={0x0000: 1, 0x00FF: 2, 0x0100: 3, 0xFFFF: 4}
        ),
        
        # Test 32: Hardware register operations
        PipelineTest(
            "hardware_registers",
            """
            void main() {
                // Test timer operations
                timer_set(100);
                int16 timer_val = timer_get();
                
                // Test video operations
                video_mode(1);
                video_layer(2);
                
                halt();
            }
            """,
            max_cycles=500
        ),
    ]
    
    # Run all tests
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        if run_pipeline_test(test_case):
            passed += 1
    
    # Summary
    print(f"\n=== ENHANCED PIPELINE TEST SUMMARY ===")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed < total:
        print(f"\n❌ {total - passed} tests failed - bugs found in pipeline")
        return 1
    else:
        print(f"\n✅ All pipeline tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())
