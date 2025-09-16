#!/usr/bin/env python3
"""
Simple test to validate individual FORTH stack operations
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth_compiler import ForthCompiler

def test_individual_operations():
    """Test individual stack operations to verify Nova-16 compliance"""
    print("=== Testing Individual Stack Operations ===")
    
    compiler = ForthCompiler()
    
    # Test individual operations
    operations = [
        ("DUP", compiler._compile_dup),
        ("ADD", compiler._compile_add),
        ("SUB", compiler._compile_sub),
        ("MUL", compiler._compile_mul),
        ("DIV", compiler._compile_div),
        ("SWAP", compiler._compile_swap),
        ("DROP", compiler._compile_drop),
        ("OVER", compiler._compile_over),
        ("FETCH", compiler._compile_fetch),
        ("STORE", compiler._compile_store),
        ("EQUALS", compiler._compile_equals),
    ]
    
    compliance_issues = []
    compliant_operations = 0
    
    for op_name, op_func in operations:
        print(f"\nTesting {op_name}:")
        try:
            asm_lines = op_func()
            
            has_violations = False
            has_optimizations = False
            
            for line in asm_lines:
                print(f"  {line}")
                
                # Check for violations
                if "DEC P8" in line or "INC P8" in line:
                    compliance_issues.append(f"❌ {op_name}: Manual pointer manipulation: {line.strip()}")
                    has_violations = True
                elif "[P8]" in line and "[P8+" not in line:
                    compliance_issues.append(f"❌ {op_name}: Direct stack access without offset: {line.strip()}")
                    has_violations = True
                elif "MOV [P8]," in line and "[P8+0]" not in line:
                    compliance_issues.append(f"❌ {op_name}: Direct stack write without indexed addressing: {line.strip()}")
                    has_violations = True
                    
                # Check for optimizations
                if "ADD P8," in line or "SUB P8," in line:
                    has_optimizations = True
                elif "[P8+" in line:
                    has_optimizations = True
                    
            if not has_violations and has_optimizations:
                print(f"  ✅ {op_name} is Nova-16 compliant!")
                compliant_operations += 1
            elif not has_violations:
                print(f"  ⚠️ {op_name} has no violations but could be more optimized")
            else:
                print(f"  ❌ {op_name} has compliance violations")
                
        except Exception as e:
            print(f"  ERROR: {e}")
            compliance_issues.append(f"❌ {op_name}: Compilation error: {e}")
    
    print(f"\n=== SUMMARY ===")
    print(f"Total operations tested: {len(operations)}")
    print(f"Compliant operations: {compliant_operations}")
    print(f"Compliance rate: {(compliant_operations/len(operations)*100):.1f}%")
    
    if compliance_issues:
        print(f"\nIssues found ({len(compliance_issues)}):")
        for issue in compliance_issues:
            print(f"  {issue}")
    else:
        print("\n🎉 All operations are Nova-16 compliant!")
        
    return compliance_issues

def test_push_pop_operations():
    """Test the push/pop helper functions"""
    print("\n=== Testing Push/Pop Helper Functions ===")
    
    compiler = ForthCompiler()
    
    # Test push operation
    print("Testing _push_param(42):")
    push_lines = compiler._push_param(42)
    for line in push_lines:
        print(f"  {line}")
    
    print("\nTesting _pop_param():")
    pop_lines = compiler._pop_param()
    for line in pop_lines:
        print(f"  {line}")
        
    # Check compliance
    issues = []
    for line in push_lines + pop_lines:
        if "DEC P8" in line or "INC P8" in line:
            issues.append(f"❌ Found manual pointer manipulation: {line.strip()}")
        elif "[P8]" in line and "[P8+" not in line:
            issues.append(f"❌ Found direct stack access: {line.strip()}")
            
    if not issues:
        print("✅ Push/Pop operations are compliant!")
    else:
        print("❌ Push/Pop operations have issues:")
        for issue in issues:
            print(f"  {issue}")
            
    return issues

def main():
    """Run all individual tests"""
    print("FORTH Individual Operation Compliance Test")
    print("=" * 50)
    
    all_issues = []
    
    # Test individual operations
    op_issues = test_individual_operations()
    push_pop_issues = test_push_pop_operations()
    
    all_issues.extend(op_issues)
    all_issues.extend(push_pop_issues)
    
    print("\n" + "=" * 50)
    print("FINAL INDIVIDUAL OPERATION REPORT")
    print("=" * 50)
    
    if not all_issues:
        print("🎉 ALL INDIVIDUAL OPERATIONS ARE NOVA-16 COMPLIANT!")
        print("✅ Stack addressing uses proper indexed syntax")
        print("✅ Stack pointer manipulation uses arithmetic instructions")
        print("✅ No direct memory access violations found")
    else:
        print(f"❌ Found {len(all_issues)} individual operation issues")
        print("\nRemaining work needed:")
        print("  - Fix any remaining stack addressing patterns")
        print("  - Ensure consistent use of indexed addressing")
        print("  - Replace manual pointer manipulation with arithmetic")
        
    return len(all_issues) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
