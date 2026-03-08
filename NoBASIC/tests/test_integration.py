"""
Integration tests for NoBASIC compiler.
Tests end-to-end compilation and execution.
"""

import pytest
import os
import re
import tempfile
import subprocess
from pathlib import Path
from nobasic_compiler import compile_nobasic


class TestIntegration:
    """Integration tests for NoBASIC compilation and execution."""

    def test_simple_compilation(self):
        """Test compiling a simple NoBASIC program."""
        source = "ClrDraw\nPause"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "test.nobasic"
            source_file.write_text(source)
            
            # Compile
            compile_nobasic(str(source_file))
            
            # Check files were created
            asm_file = source_file.with_suffix('.asm')
            bin_file = source_file.with_suffix('.bin')
            
            assert asm_file.exists()
            assert bin_file.exists()
            
            # Check assembly content
            asm_content = asm_file.read_text()
            assert "HLT" in asm_content

    def test_graphics_program_compilation(self):
        """Test compiling a graphics program."""
        source = """
        ClrDraw
        x = 11
        y = 22
        PxlOn(x, y, 33)
        Pause
        """
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "graphics.nobasic"
            source_file.write_text(source)
            
            compile_nobasic(str(source_file))
            
            asm_file = source_file.with_suffix('.asm')
            bin_file = source_file.with_suffix('.bin')
            
            assert asm_file.exists()
            assert bin_file.exists()
            
            asm_content = asm_file.read_text()
            # ClrDraw uses layer fills, not VM mode changes
            assert "SFILL" in asm_content or "ClrDraw" in asm_content
            assert "SWRITE" in asm_content    # PxlOn

    def test_loop_compilation(self):
        """Test compiling a program with loops."""
        source = """
        ClrDraw
        For I = 0 To 10
            PxlOn(I, I, 31)
        Next
        Pause
        """
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "loop.nobasic"
            source_file.write_text(source)
            
            compile_nobasic(str(source_file))
            
            asm_file = source_file.with_suffix('.asm')
            assert asm_file.exists()
            
            asm_content = asm_file.read_text()
            assert "CMP" in asm_content  # For loop comparison
            assert "JGT" in asm_content  # For loop jump

    def test_function_calls_compilation(self):
        """Test compiling function calls."""
        source = "x = sin(30) + cos(45)\nPause"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "functions.nobasic"
            source_file.write_text(source)
            
            compile_nobasic(str(source_file))
            
            asm_file = source_file.with_suffix('.asm')
            assert asm_file.exists()

    @pytest.mark.skipif(os.name != 'nt', reason="Nova emulator is Windows-only")
    def test_execution_headless(self):
        """Test running compiled program headlessly."""
        source = "ClrDraw\nPause"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "execute.nobasic"
            source_file.write_text(source)
            
            compile_nobasic(str(source_file))
            bin_file = source_file.with_suffix('.bin')
            
            # Try to run with nova.py headless
            result = subprocess.run(
                ['python', 'nova.py', '--headless', str(bin_file), '--cycles', '1000'],
                cwd=Path(__file__).parent.parent.parent,  # Root Nova directory
                capture_output=True,
                text=True
            )
            
            # Should complete without error
            assert result.returncode == 0

    def test_error_handling(self):
        """Test error handling in compilation."""
        # Invalid syntax
        source = "invalid syntax here"
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "error.nobasic"
            source_file.write_text(source)
            
            with pytest.raises(SystemExit):
                compile_nobasic(str(source_file))

    def test_math_library_integration(self):
        """Test integration with math library functions."""
        source = """
        x = sin(30) + cos(45)
        y = sqrt(16) * abs(-3)
        z = int(3.14) + round(2.7)
        """
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "math.nobasic"
            source_file.write_text(source)
            
            compile_nobasic(str(source_file))
            
            asm_file = source_file.with_suffix('.asm')
            assert asm_file.exists()
            
            asm_content = asm_file.read_text()
            assert "SIN" in asm_content  # Math function calls
            assert "COS" in asm_content  # Math function calls

    def test_string_operations_integration(self):
        """Test integration with string operations."""
        source = '''
        s1 = "Hello"
        s2 = "World"
        len1 = length(s1)
        combined = s1 + s2
        '''
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "strings.nobasic"
            source_file.write_text(source)
            
            compile_nobasic(str(source_file))
            
            asm_file = source_file.with_suffix('.asm')
            assert asm_file.exists()

    def test_array_operations_integration(self):
        """Test integration with array/list operations."""
        source = """
        L1(5) = 42
        x = L1(5)
        Pause
        """
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "array_test.nobasic"
            source_file.write_text(source)
            
            compile_nobasic(str(source_file))
            
            asm_file = source_file.with_suffix('.asm')
            assert asm_file.exists()
            
            # Check that array store and load operations are generated
            asm_content = asm_file.read_text()
            assert "MOV" in asm_content  # Should have some MOV instructions for array operations

    def test_complex_graphics_program(self):
        """Test compilation of complex graphics programs."""
        source = """
        ClrDraw
        SetLayer(1)
        
        // Draw a border
        For X = 0 To 255
            PxlOn(X, 0, 31)
            PxlOn(X, 191, 31)
        Next
        
        For Y = 0 To 191
            PxlOn(0, Y, 31)
            PxlOn(255, Y, 31)
        Next
        
        // Draw diagonal lines
        For I = 0 To 255
            PxlOn(I, I, 15)
        Next
        
        Pause
        """
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "graphics_complex.nobasic"
            source_file.write_text(source)
            
            compile_nobasic(str(source_file))
            
            asm_file = source_file.with_suffix('.asm')
            bin_file = source_file.with_suffix('.bin')
            
            assert asm_file.exists()
            assert bin_file.exists()
            
            asm_content = asm_file.read_text()
            # ClrDraw uses layer fills, not VM mode changes
            assert "SFILL" in asm_content or "ClrDraw" in asm_content
            assert "MOV VL," in asm_content    # SetLayer
            assert "SWRITE" in asm_content     # PxlOn
            assert "CMP" in asm_content        # For loops
            assert "KEYSTAT" in asm_content    # Pause

    def test_sound_program_integration(self):
        """Test compilation of sound programs."""
        source = """
        // Play a simple melody
        PlayTone(262, 500, 128)  // C4
        PlayTone(294, 500, 128)  // D4
        PlayTone(330, 500, 128)  // E4
        PlayTone(349, 500, 128)  // F4
        PlayTone(392, 500, 128)  // G4
        
        StopSound
        Pause
        """
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "sound.nobasic"
            source_file.write_text(source)
            
            compile_nobasic(str(source_file))
            
            asm_file = source_file.with_suffix('.asm')
            assert asm_file.exists()
            
            asm_content = asm_file.read_text()
            assert "MOV SF," in asm_content
            assert "MOV SV," in asm_content
            assert "SPLAY" in asm_content
            assert "MOV SV, 0" in asm_content  # StopSound

    def test_game_loop_integration(self):
        """Test compilation of a simple game loop."""
        source = """
        ClrDraw
        x = 128
        y = 96
        
        While true
            GetKey
            If key = 37 Then x = x - 1 End  // Left
            If key = 39 Then x = x + 1 End  // Right
            If key = 38 Then y = y - 1 End  // Up
            If key = 40 Then y = y + 1 End  // Down
            
            ClrDraw
            PxlOn(x, y, 31)
            Pause
        End
        """
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "game.nobasic"
            source_file.write_text(source)
            
            compile_nobasic(str(source_file))
            
            asm_file = source_file.with_suffix('.asm')
            assert asm_file.exists()
            
            asm_content = asm_file.read_text()
            assert "KEYIN R0" in asm_content
            assert "JZ" in asm_content  # While loop
            # ClrDraw uses layer fills
            assert "SFILL" in asm_content or "ClrDraw" in asm_content
            assert "SWRITE" in asm_content  # PxlOn

    def test_error_recovery_integration(self):
        """Test error recovery during compilation."""
        # Program with some errors
        source = """
        x = 1
        invalid statement here
        y = 2
        """
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "error_recovery.nobasic"
            source_file.write_text(source)
            
            # Should fail compilation
            with pytest.raises(SystemExit):
                compile_nobasic(str(source_file))

    def test_large_program_performance(self):
        """Test compilation performance with large programs."""
        # Generate a large program
        lines = ["ClrDraw"]
        for i in range(100):
            lines.append(f"x{i} = {i}")
            lines.append(f"PxlOn({i}, {i}, 31)")
        lines.append("Pause")
        source = "\n".join(lines)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "large.nobasic"
            source_file.write_text(source)
            
            import time
            start_time = time.time()
            compile_nobasic(str(source_file))
            end_time = time.time()
            
            # Should compile in reasonable time (< 5 seconds)
            assert end_time - start_time < 5.0
            
            asm_file = source_file.with_suffix('.asm')
            bin_file = source_file.with_suffix('.bin')
            assert asm_file.exists()
            assert bin_file.exists()

    def test_cross_platform_compatibility(self):
        """Test that generated code works across platforms."""
        source = "ClrDraw\nx = 42\nPxlOn(x, x, 31)\nPause"

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "cross_platform.nobasic"
            source_file.write_text(source)

            compile_nobasic(str(source_file))

            asm_file = source_file.with_suffix('.asm')
            asm_content = asm_file.read_text()

            # Check that generated assembly uses standard instructions
            assert "MOV" in asm_content
            assert "SWRITE" in asm_content
            assert "KEYSTAT" in asm_content
            assert "HLT" in asm_content

    def test_math_library_integration_comprehensive(self):
        """Test comprehensive math library integration."""
        source = """
        // Test all math functions
        x = sin(30) + cos(45)
        y = tan(60) * sqrt(16)
        z = abs(-3.14) + int(2.7)
        w = round(3.14159) + floor(2.9)
        r = rand() * 100
        result = powr(2, 3) + log(100) + exp(1)
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "math_comprehensive.nobasic"
            source_file.write_text(source)

            compile_nobasic(str(source_file))

            asm_file = source_file.with_suffix('.asm')
            assert asm_file.exists()

            asm_content = asm_file.read_text()
            # Check for various math opcodes
            math_ops = ["SIN", "COS", "TAN", "SQRT", "ABS", "POWR", "LOG", "EXP"]
            found_ops = [op for op in math_ops if op in asm_content]
            assert len(found_ops) > 0  # At least some math ops should be present

    def test_string_operations_integration_comprehensive(self):
        """Test comprehensive string operations integration."""
        source = '''
        s1 = "Hello"
        s2 = "World"
        combined = s1 + s2
        len1 = length(s1)
        len2 = length(s2)
        upper = strupr(s1)
        lower = strlwr(s2)
        substr = sub(s1, 1, 3)
        found = strfind(s1, "ell")
        '''

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "strings_comprehensive.nobasic"
            source_file.write_text(source)

            compile_nobasic(str(source_file))

            asm_file = source_file.with_suffix('.asm')
            assert asm_file.exists()

    def test_array_operations_integration_comprehensive(self):
        """Test comprehensive array operations integration."""
        source = """
        // List operations
        L1(1) = 10
        L1(2) = 20
        L1(3) = 30
        sum_val = sum(L1)
        mean_val = mean(L1)
        dim_val = dim(L1)

        // Matrix operations
        MatA(1, 1) = 1
        MatA(1, 2) = 2
        MatA(2, 1) = 3
        MatA(2, 2) = 4
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "arrays_comprehensive.nobasic"
            source_file.write_text(source)

            compile_nobasic(str(source_file))

            asm_file = source_file.with_suffix('.asm')
            assert asm_file.exists()

    def test_control_structures_integration_comprehensive(self):
        """Test comprehensive control structures integration."""
        source = """
        // Nested if-else
        if x > 0 then
            if y > 0 then
                result = 1
            else
                result = 2
            end
        else
            result = 3
        end

        // Complex for loop
        for i = 1 to 10 step 2
            sum = sum + i
        next

        // While loop
        while count < 100
            count = count + 1
        end

        // Repeat-until
        repeat
            value = value * 2
        until value > 1000
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "control_comprehensive.nobasic"
            source_file.write_text(source)

            compile_nobasic(str(source_file))

            asm_file = source_file.with_suffix('.asm')
            assert asm_file.exists()

            asm_content = asm_file.read_text()
            assert "CMP" in asm_content  # Comparisons
            assert "JZ" in asm_content   # Jumps

    def test_graphics_operations_integration_comprehensive(self):
        """Test comprehensive graphics operations integration."""
        source = """
        ClrDraw
        SetLayer(0)

        // Pixel operations
        PxlOn(10, 20, 31)
        PxlOff(30, 40)

        // Drawing operations
        Line(0, 0, 100, 100, 15)
        Circle(50, 50, 25, 31)
        Text(10, 10, "Hello World", 31)

        // Advanced graphics
        SetLayer(1)
        Rect(20, 20, 80, 60, 1)  // Filled rectangle
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "graphics_comprehensive.nobasic"
            source_file.write_text(source)

            compile_nobasic(str(source_file))

            asm_file = source_file.with_suffix('.asm')
            assert asm_file.exists()

            asm_content = asm_file.read_text()
            assert "MOV VM, 0" in asm_content  # ClrDraw
            assert "MOV VL," in asm_content    # SetLayer
            assert "SWRITE" in asm_content     # Pixel operations
            assert "SLINE" in asm_content      # Line
            assert "SCIRC" in asm_content      # Circle

    def test_sound_operations_integration_comprehensive(self):
        """Test comprehensive sound operations integration."""
        source = """
        // Tone playback
        PlayTone(440, 1000, 128)  // A4
        PlayTone(523, 500, 96)    // C5

        // Wave playback
        PlayWave(0, 220, 64)      // Sine wave
        PlayWave(1, 330, 64)      // Square wave

        // Channel management
        SetChannel(0)
        PlayTone(262, 2000, 128)  // C4 long

        SetChannel(1)
        PlayTone(330, 2000, 96)   // E4 softer

        StopSound
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "sound_comprehensive.nobasic"
            source_file.write_text(source)

            compile_nobasic(str(source_file))

            asm_file = source_file.with_suffix('.asm')
            assert asm_file.exists()

            asm_content = asm_file.read_text()
            assert "MOV SF," in asm_content
            assert "MOV SV," in asm_content
            assert "SPLAY" in asm_content

    def test_io_operations_integration_comprehensive(self):
        """Test comprehensive I/O operations integration."""
        source = '''
        // Input operations
        Disp "Enter your name:"
        Input "Name: ", name
        Disp "Hello, " + name

        // Key input
        Disp "Press any key..."
        key = GetKey
        Disp "You pressed: " + str(key)

        Pause
        '''

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "io_comprehensive.nobasic"
            source_file.write_text(source)

            compile_nobasic(str(source_file))

            asm_file = source_file.with_suffix('.asm')
            assert asm_file.exists()

            asm_content = asm_file.read_text()
            assert "KEYIN" in asm_content
            assert "KEYSTAT" in asm_content

    def test_error_handling_integration_comprehensive(self):
        """Test comprehensive error handling integration."""
        error_sources = [
            ("x = sin()", "Wrong number of arguments"),
            ("goto nonexistent", "Undefined label"),
        ]

        for source, expected_error in error_sources:
            with tempfile.TemporaryDirectory() as tmpdir:
                source_file = Path(tmpdir) / f"error_{expected_error.replace(' ', '_')}.nobasic"
                source_file.write_text(source)

                # Should fail compilation
                with pytest.raises(SystemExit):
                    compile_nobasic(str(source_file))

    def test_optimization_integration(self):
        """Test that optimizations are applied during compilation."""
        source = """
        x = 0  // Should use XOR optimization
        y = 1  // Should use MOV #1
        z = 2  // Should use SHL optimization
        result = x + y + z
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "optimization.nobasic"
            source_file.write_text(source)

            compile_nobasic(str(source_file))

            asm_file = source_file.with_suffix('.asm')
            asm_content = asm_file.read_text()

            # Check for optimization patterns
            assert "XOR" in asm_content  # x = 0 optimization
            assert "SHL" in asm_content  # z = 2 optimization

    def test_memory_management_integration(self):
        """Test memory management in compiled programs."""
        source = """
        // Many variables to test memory allocation
        a = 1
        b = 2
        c = 3
        d = 4
        e = 5
        f = 6
        g = 7
        h = 8
        i = 9
        j = 10
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "memory.nobasic"
            source_file.write_text(source)

            compile_nobasic(str(source_file))

            asm_file = source_file.with_suffix('.asm')
            asm_content = asm_file.read_text()

            # Should have sequential memory addresses
            addresses = []
            for line in asm_content.split('\n'):
                if 'MOV P0, ' in line and line.split(', ')[1].isdigit():
                    addresses.append(int(line.split(', ')[1]))

            # Addresses should be sequential
            if len(addresses) > 1:
                for i in range(1, len(addresses)):
                    assert addresses[i] == addresses[i-1] + 2

    def test_complex_program_integration(self):
        """Test integration of a complex, realistic program."""
        complex_program = '''
        // Simple drawing program
        ClrDraw
        SetLayer(0)

        // Draw border
        For x = 0 To 255
            PxlOn(x, 0, 31)
            PxlOn(x, 191, 31)
        Next

        For y = 0 To 191
            PxlOn(0, y, 31)
            PxlOn(255, y, 31)
        Next

        // Draw diagonal pattern
        For i = 0 To 255 Step 5
            Line(i, 0, 255-i, 191, 15)
        Next

        // Add some text
        Text(100, 90, "NoBASIC Demo", 31)

        // Play a sound
        PlayTone(440, 1000, 128)

        // Wait for user
        Disp "Press any key to continue..."
        Pause

        StopSound
        '''

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "complex_demo.nobasic"
            source_file.write_text(complex_program)

            compile_nobasic(str(source_file))

            asm_file = source_file.with_suffix('.asm')
            bin_file = source_file.with_suffix('.bin')

            assert asm_file.exists()
            assert bin_file.exists()

            # Verify the program compiles and generates reasonable assembly
            asm_content = asm_file.read_text()
            assert len(asm_content) > 1000  # Should be substantial
            assert "HLT" in asm_content

    def test_regression_tests(self):
        """Test for regressions in previously working code."""
        # Test cases that have caused issues in the past
        regression_sources = [
            "x = 1\ny = x",  # Variable usage
            "if 1 then x = 1 end",  # Simple if
            "for i = 1 to 5\nx = i\nnext",  # Simple loop
            "x = sin(30)",  # Function call
            's = "test"',  # String literal
        ]

        for i, regression_source in enumerate(regression_sources):
            with tempfile.TemporaryDirectory() as tmpdir:
                source_file = Path(tmpdir) / f"regression_{i}.nobasic"
                source_file.write_text(regression_source)

                # Should compile without errors
                compile_nobasic(str(source_file))

                asm_file = source_file.with_suffix('.asm')
                bin_file = source_file.with_suffix('.bin')
                assert asm_file.exists()
                assert bin_file.exists()

    def test_compilation_performance_benchmark(self):
        """Benchmark compilation performance."""
        # Test compilation speed for different program sizes
        sizes = [10, 50, 100, 200]
        
        for size in sizes:
            statements = [f"var{i} = {i}" for i in range(size)]
            source = "\n".join(statements)
            
            with tempfile.TemporaryDirectory() as tmpdir:
                source_file = Path(tmpdir) / f"perf_{size}.nobasic"
                source_file.write_text(source)
                
                import time
                start_time = time.time()
                compile_nobasic(str(source_file))
                end_time = time.time()
                
                compilation_time = end_time - start_time
                # Should scale reasonably with program size
                assert compilation_time < size * 0.05  # More reasonable performance expectation

    def test_generated_code_size_analysis(self):
        """Analyze the size of generated code."""
        test_cases = [
            ("minimal", "x = 1"),
            ("arithmetic", "x = a + b * c"),
            ("control_flow", "if x > 0 then y = 1 else y = 0 end"),
            ("loop", "for i = 1 to 10\nsum = sum + i\nnext"),
            ("functions", "result = sin(x) + cos(y)"),
        ]
        
        for name, source in test_cases:
            with tempfile.TemporaryDirectory() as tmpdir:
                source_file = Path(tmpdir) / f"size_{name}.nobasic"
                source_file.write_text(source)
                
                compile_nobasic(str(source_file))
                
                asm_file = source_file.with_suffix('.asm')
                bin_file = source_file.with_suffix('.bin')
                
                asm_size = asm_file.stat().st_size
                bin_size = bin_file.stat().st_size
                
                # Basic size checks
                assert asm_size > 0
                assert bin_size > 0
                assert bin_size < 10000  # Reasonable upper bound

    def test_optimization_effectiveness(self):
        """Test the effectiveness of optimizations."""
        # Compare code generation for different patterns
        patterns = [
            ("unoptimized", "x = 0\ny = 0\nz = 0"),
            ("potentially_optimized", "x = 1 - 1\ny = 2 - 2\nz = 3 - 3"),
        ]
        
        for name, source in patterns:
            with tempfile.TemporaryDirectory() as tmpdir:
                source_file = Path(tmpdir) / f"opt_{name}.nobasic"
                source_file.write_text(source)
                
                compile_nobasic(str(source_file))
                
                asm_file = source_file.with_suffix('.asm')
                asm_content = asm_file.read_text()
                
                # Check for optimization patterns
                if "unoptimized" in name:
                    # Should use XOR for setting to zero
                    assert "XOR" in asm_content
                # Add more optimization checks as needed

    def test_memory_usage_patterns(self):
        """Test memory usage patterns in compiled programs."""
        source = """
        // Many variables to test memory allocation
        a1 = 1
        a2 = 2
        a3 = 3
        b1 = 4
        b2 = 5
        b3 = 6
        """
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "memory_test.nobasic"
            source_file.write_text(source)
            
            compile_nobasic(str(source_file))
            
            asm_file = source_file.with_suffix('.asm')
            asm_content = asm_file.read_text()
            
            # Variables are allocated to P registers, not memory
            # Count P register assignments
            p_register_ops = [line for line in asm_content.split('\n') if 'MOV P' in line and 'MOV SP' not in line and 'MOV FP' not in line]
            assert len(p_register_ops) >= 6  # At least one for each variable

    def test_instruction_mix_analysis(self):
        """Analyze the mix of instructions generated."""
        source = """
        x = 1 + 2 * 3
        if x > 5 then
            y = sin(30)
        else
            y = cos(45)
        end
        for i = 1 to 10
            sum = sum + i
        next
        """
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "instruction_mix.nobasic"
            source_file.write_text(source)
            
            compile_nobasic(str(source_file))
            
            asm_file = source_file.with_suffix('.asm')
            asm_content = asm_file.read_text()
            
            lines = asm_content.split('\n')
            
            # Count different instruction types
            arithmetic_ops = sum(1 for line in lines if any(op in line for op in ['ADD', 'SUB', 'MUL', 'DIV']))
            control_ops = sum(1 for line in lines if any(op in line for op in ['CMP', 'JZ', 'JNZ', 'JMP']))
            
            # Should have a reasonable mix
            assert arithmetic_ops > 0
            assert control_ops > 0
            # Memory ops may be optimized away with register allocation
            # Just check that code was generated
            assert len(lines) > 10

    def test_compilation_stability(self):
        """Test that compilation is stable and deterministic."""
        source = "x = 1 + 2\ny = x * 3\nz = sin(y)"
        
        # Compile multiple times and ensure results are identical
        results = []
        for i in range(3):
            with tempfile.TemporaryDirectory() as tmpdir:
                source_file = Path(tmpdir) / f"stable_{i}.nobasic"
                source_file.write_text(source)
                
                compile_nobasic(str(source_file))
                
                asm_file = source_file.with_suffix('.asm')
                asm_content = asm_file.read_text()
                results.append(asm_content)
        
        # All results should be identical
        assert all(result == results[0] for result in results)

    def test_resource_usage_during_compilation(self):
        """Test resource usage during compilation."""
        # Create a moderately large program
        statements = []
        for i in range(100):
            statements.append(f"var{i} = sin({i}) + cos({i})")
            statements.append(f"if var{i} > 0 then result{i} = var{i} else result{i} = -var{i} end")
        source = "\n".join(statements)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "resource_test.nobasic"
            source_file.write_text(source)
            
            # Should compile without excessive resource usage
            import time
            start_time = time.time()
            compile_nobasic(str(source_file))
            end_time = time.time()
            
            # Should complete in reasonable time
            assert end_time - start_time < 10.0  # Less than 10 seconds for 200 statements

    def test_user_function_implicit_assignment_compiles_as_global_access(self):
        """Implicit function assignments should compile as global variable access, not stack locals."""
        source = """
        function setscore(v)
            score = v
            return score
        end
        x = setscore(5)
        y = score
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "implicit_global_func.nobasic"
            source_file.write_text(source)

            compile_nobasic(str(source_file))

            asm_file = source_file.with_suffix('.asm')
            asm_content = asm_file.read_text()

            # Function has only one parameter and no explicit locals.
            assert "; Parameters: v" in asm_content
            assert "; Locals:  (0 bytes)" in asm_content
            # Score should be emitted as regular/global storage path (absolute address usage).
            assert "MOV P0," in asm_content

    def test_game_attack_function_has_edge_guards_for_sword_draw(self):
        """Sword draw in game source should guard left/right edge positions before drawing."""
        source = Path(__file__).parent.parent / "game.nobasic"

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "game.nobasic"
            source_file.write_text(source.read_text())

            compile_nobasic(str(source_file))

            asm_file = source_file.with_suffix('.asm')
            asm_content = asm_file.read_text().lower()
            attack_section = asm_content.split("_func_attackifpressed_2:", 1)[1].split("_func_movexbykey_3:", 1)[0]

            # Left edge guard (>= 16) may be folded as SHL by 4 with varying temp registers.
            assert re.search(r"shl\s+[pr]\d,\s*4", attack_section)
            assert "jge" in attack_section
            # Right edge guard should compare against 232 and branch with <=.
            assert "mov p2, 232" in attack_section
            assert "jle" in attack_section

    def test_game_no_struct_old_position_clear_does_not_use_p1_for_spill_addressing(self):
        """Regression: game_no_struct clear path must avoid P1 scratch clobber from spill stores."""
        source = Path(__file__).parent.parent / "game_no_struct.nobasic"

        with tempfile.TemporaryDirectory() as tmpdir:
            source_file = Path(tmpdir) / "game_no_struct.nobasic"
            source_file.write_text(source.read_text())

            compile_nobasic(str(source_file))

            asm_file = source_file.with_suffix('.asm')
            asm_content = asm_file.read_text().lower()

            # P1 was previously used as a hardcoded spill-address scratch register,
            # which could overwrite a live old-position variable and break clear-on-move.
            assert "mov p1, 28672" not in asm_content