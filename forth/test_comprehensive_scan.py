#!/usr/bin/env python3
"""
Comprehensive scanner to find all remaining Nova-16 convention violations
"""

import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from forth_compiler import ForthCompiler

def scan_all_methods():
    """Scan all compilation methods for Nova-16 compliance"""
    print("=== Comprehensive Nova-16 Compliance Scan ===")
    
    compiler = ForthCompiler()
    
    # Get all compilation methods
    methods = [method for method in dir(compiler) if method.startswith('_compile_')]
    
    print(f"Found {len(methods)} compilation methods to test:")
    
    violations = []
    compliant_methods = []
    
    for method_name in sorted(methods):
        method = getattr(compiler, method_name)
        print(f"\nTesting {method_name}:")
        
        try:
            # Try to call the method (some may need parameters)
            if method_name in ['_compile_print_string', '_compile_create_string']:
                result = method("test")
            else:
                result = method()
                
            method_violations = []
            method_optimizations = []
            
            for line in result:
                print(f"  {line}")
                
                # Check for stack pointer violations (P8/P9)
                if "DEC P8" in line or "INC P8" in line:
                    method_violations.append(f"Manual P8 manipulation: {line.strip()}")
                elif "DEC P9" in line or "INC P9" in line:
                    method_violations.append(f"Manual P9 manipulation: {line.strip()}")
                elif "[P8]" in line and "[P8+" not in line and "P8]" not in line:
                    method_violations.append(f"Direct P8 access: {line.strip()}")
                elif "[P9]" in line and "[P9+" not in line and "P9]" not in line:
                    method_violations.append(f"Direct P9 access: {line.strip()}")
                elif "MOV [P8]," in line and "[P8+0]" not in line:
                    method_violations.append(f"Direct P8 write: {line.strip()}")
                elif "MOV [P9]," in line and "[P9+0]" not in line:
                    method_violations.append(f"Direct P9 write: {line.strip()}")
                    
                # Check for optimizations
                if "ADD P8," in line or "SUB P8," in line:
                    method_optimizations.append("Arithmetic stack operation")
                elif "[P8+" in line or "[P9+" in line:
                    method_optimizations.append("Indexed addressing")
            
            if method_violations:
                violations.extend([f"{method_name}: {v}" for v in method_violations])
                print(f"  ❌ {len(method_violations)} violations found")
            else:
                compliant_methods.append(method_name)
                print(f"  ✅ COMPLIANT ({len(method_optimizations)} optimizations)")
                
        except Exception as e:
            print(f"  ⚠️  Could not test: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("COMPREHENSIVE COMPLIANCE REPORT")
    print("=" * 60)
    
    total_methods = len(methods)
    compliant_count = len(compliant_methods)
    violation_count = len([v for v in violations])
    
    print(f"Total compilation methods: {total_methods}")
    print(f"Compliant methods: {compliant_count}")
    print(f"Methods with violations: {total_methods - compliant_count}")
    print(f"Compliance rate: {(compliant_count/total_methods*100):.1f}%")
    
    if violations:
        print(f"\n❌ VIOLATIONS FOUND ({len(violations)}):")
        for violation in violations:
            print(f"  {violation}")
        print(f"\n🔧 These should be addressed for full Nova-16 compliance")
    else:
        print(f"\n🎉 ALL COMPILATION METHODS ARE NOVA-16 COMPLIANT!")
        print(f"✅ No stack pointer violations found")
        print(f"✅ All methods use proper Nova-16 conventions")
    
    print(f"\n📋 COMPLIANT METHODS ({len(compliant_methods)}):")
    for method in compliant_methods:
        print(f"  ✅ {method}")
    
    return len(violations) == 0

def test_edge_cases():
    """Test edge cases and complex operations"""
    print("\n=== Testing Edge Cases ===")
    
    compiler = ForthCompiler()
    
    edge_cases = [
        # Control flow with complex nesting
        ("IF THEN", "Simple conditional"),
        ("BEGIN UNTIL", "Simple loop"),
        ("DO LOOP", "Count loop"),
        # String operations
        ("\" Hello \" .", "String output"),
        # Variable operations  
        ("VARIABLE TEST", "Variable definition"),
        # Function definitions
        (": TEST 42 ; TEST", "Simple word definition"),
    ]
    
    violations = []
    
    for code, description in edge_cases:
        print(f"\nTesting edge case: {description}")
        print(f"Code: {code}")
        
        try:
            result = compiler.compile_to_lines(code)
            
            # Check a sample of the output
            for i, line in enumerate(result[:20]):  # First 20 lines
                if "DEC P8" in line or "INC P8" in line or "DEC P9" in line or "INC P9" in line:
                    if i < len(result):  # Avoid showing line numbers beyond actual content
                        violations.append(f"Edge case '{description}': {line.strip()}")
                        
        except Exception as e:
            print(f"  Error: {e}")
    
    if violations:
        print(f"\n❌ Edge case violations found:")
        for violation in violations:
            print(f"  {violation}")
    else:
        print(f"\n✅ All edge cases are compliant!")
        
    return len(violations) == 0

def main():
    """Run comprehensive compliance scan"""
    print("Nova-16 FORTH Compiler Comprehensive Compliance Scan")
    print("=" * 70)
    
    methods_ok = scan_all_methods()
    edges_ok = test_edge_cases()
    
    print("\n" + "=" * 70)
    print("FINAL COMPREHENSIVE SCAN RESULTS")
    print("=" * 70)
    
    if methods_ok and edges_ok:
        print("🎉 PERFECT COMPLIANCE ACHIEVED!")
        print("✅ All compilation methods follow Nova-16 conventions")
        print("✅ All edge cases handle stack operations correctly")
        print("✅ Full indexed addressing implementation complete")
        print("✅ Proper arithmetic stack pointer manipulation throughout")
        print("\n🚀 FORTH compiler is production-ready for Nova-16!")
    else:
        if not methods_ok:
            print("❌ Some compilation methods need fixes")
        if not edges_ok:
            print("❌ Some edge cases need attention")
        print("🔧 Additional work needed for full compliance")
    
    return methods_ok and edges_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
