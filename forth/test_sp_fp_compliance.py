#!/usr/bin/env python3
"""
Test script to validate FORTH SP/FP compliance improvements
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth_compiler import ForthCompiler

def test_stack_addressing_compliance():
    """Test that the compiler generates proper Nova-16 indexed addressing syntax"""
    print("=== Testing Stack Addressing Compliance ===")
    
    compiler = ForthCompiler()
    
    # Test basic stack operations
    test_cases = [
        ("DUP", "Test DUP operation"),
        ("42 DUP", "Test number push and DUP"),
        ("10 20 +", "Test addition"),
        ("10 20 -", "Test subtraction"),
        ("10 20 *", "Test multiplication"),
        ("20 10 /", "Test division"),
        ("10 20 SWAP", "Test SWAP"),
        ("10 20 DROP", "Test DROP"),
        ("10 20 OVER", "Test OVER"),
    ]
    
    compliance_issues = []
    
    for forth_code, description in test_cases:
        print(f"\nTesting: {description}")
        print(f"FORTH: {forth_code}")
        
        try:
            asm_code = compiler.compile_to_lines(forth_code)
            print("Generated assembly:")
            
            for line in asm_code:
                print(f"  {line}")
                
                # Check for compliance violations
                if "DEC P8" in line or "INC P8" in line:
                    compliance_issues.append(f"❌ Found manual pointer manipulation: {line.strip()}")
                elif "[P8]" in line and "[P8+" not in line:
                    compliance_issues.append(f"❌ Found direct stack access without offset: {line.strip()}")
                elif line.strip().startswith("MOV [P8], ") and "[P8+0]" not in line:
                    compliance_issues.append(f"❌ Found direct stack write without indexed addressing: {line.strip()}")
                    
        except Exception as e:
            print(f"  ERROR: {e}")
            compliance_issues.append(f"❌ Compilation error for '{forth_code}': {e}")
            
    return compliance_issues

def test_function_frame_management():
    """Test that word definitions include proper frame management"""
    print("\n=== Testing Function Frame Management ===")
    
    compiler = ForthCompiler()
    
    # Test word definition
    forth_code = ": SQUARE DUP * ;"
    
    try:
        asm_code = compiler.compile_to_lines(forth_code)
        print(f"Testing word definition: {forth_code}")
        print("Generated assembly:")
        
        has_prologue = False
        has_epilogue = False
        
        for line in asm_code:
            print(f"  {line}")
            
            if "Function prologue" in line:
                has_prologue = True
            elif "Function epilogue" in line:
                has_epilogue = True
                
        issues = []
        if not has_prologue:
            issues.append("❌ Missing function prologue")
        if not has_epilogue:
            issues.append("❌ Missing function epilogue")
            
        if not issues:
            print("✅ Function frame management looks good!")
            
        return issues
        
    except Exception as e:
        return [f"❌ Compilation error: {e}"]

def test_performance_optimization():
    """Test that stack operations are optimized"""
    print("\n=== Testing Performance Optimization ===")
    
    compiler = ForthCompiler()
    
    # Test a simple operation that should be optimized
    forth_code = "10 20 +"
    
    try:
        asm_code = compiler.compile_to_lines(forth_code)
        print(f"Testing: {forth_code}")
        print("Generated assembly:")
        
        instruction_count = 0
        optimized_patterns = 0
        
        for line in asm_code:
            stripped = line.strip()
            if stripped and not stripped.startswith(";") and not stripped.endswith(":"):
                instruction_count += 1
                print(f"  {line}")
                
                # Count optimized patterns
                if "ADD P8," in stripped or "SUB P8," in stripped:
                    optimized_patterns += 1
                elif "[P8+" in stripped:
                    optimized_patterns += 1
                    
        print(f"\nInstruction count: {instruction_count}")
        print(f"Optimized patterns found: {optimized_patterns}")
        
        if optimized_patterns > 0:
            print("✅ Found optimized stack operations!")
            return []
        else:
            return ["❌ No optimized patterns detected"]
            
    except Exception as e:
        return [f"❌ Compilation error: {e}"]

def run_comprehensive_test():
    """Run all tests and generate report"""
    print("FORTH SP/FP Compliance Test Suite")
    print("=" * 50)
    
    all_issues = []
    
    # Run tests
    stack_issues = test_stack_addressing_compliance()
    frame_issues = test_function_frame_management()
    perf_issues = test_performance_optimization()
    
    all_issues.extend(stack_issues)
    all_issues.extend(frame_issues)
    all_issues.extend(perf_issues)
    
    # Generate report
    print("\n" + "=" * 50)
    print("FINAL COMPLIANCE REPORT")
    print("=" * 50)
    
    if not all_issues:
        print("🎉 ALL TESTS PASSED! FORTH compiler is Nova-16 SP/FP compliant!")
    else:
        print(f"❌ Found {len(all_issues)} compliance issues:")
        for issue in all_issues:
            print(f"  {issue}")
            
        print("\n📋 Recommendations:")
        print("  1. Address remaining stack addressing violations")
        print("  2. Ensure all functions use proper frame management")
        print("  3. Optimize stack operation patterns")
        
    print(f"\nTested compiler version: ForthCompiler v1.0")
    print(f"Nova-16 target architecture compliance: {'FULL' if not all_issues else 'PARTIAL'}")
    
    return len(all_issues) == 0

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
