# Test compound conditionals in If statements

def test_if_compound_conditionals(tmp_path):
    from NoBASIC.nobasic_compiler import compile_nobasic
    import tempfile
    import os

    # NoBASIC source with compound AND/OR
    source = '''
    x = 1
    y = 2
    z = 0
    if x = 1 and y = 2 then
        z = 10
    else
        z = 20
    end
    if x = 0 or y = 2 then
        z = z + 1
    end
    '''
    src_file = tmp_path / "compound_if.nb"
    src_file.write_text(source)
    compile_nobasic(str(src_file))
    asm_file = src_file.with_suffix('.asm')
    assert asm_file.exists()
    asm = asm_file.read_text()
    # Should have at least 3 conditional jumps (for both ifs)
    cond_jumps = [line for line in asm.splitlines() if any(j in line for j in ["JZ", "JNZ", "JLT", "JLE", "JGT", "JGE"])]
    assert len(cond_jumps) >= 3
    # Should not materialize boolean temporaries for AND/OR
    assert not any('MOV' in line and 'bool' in line for line in asm.splitlines())
