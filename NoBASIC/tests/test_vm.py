"""Tests for NoBASIC interpreter VM runtime behavior."""

from __future__ import annotations

import pytest

from nobasic_vm import NoBASICVM, NoBASICVMConfig, VMRuntimeError


def run_vm(source: str, *, max_steps: int = 10_000, skip_semantic: bool = False) -> NoBASICVM:
    """Create a VM, load source, run, and return VM instance for assertions."""
    vm = NoBASICVM(
        NoBASICVMConfig(enable_sound=False, max_steps=max_steps, skip_semantic=skip_semantic)
    )
    vm.load_source(source, "<test>")
    vm.run()
    return vm


def test_vm_executes_assignments_and_tracks_ans():
    vm = run_vm(
        """
        x = 10
        y = x + 5
        z = y * 2
        """
    )

    assert vm._get_var("x") == 10
    assert vm._get_var("y") == 15.0
    assert vm._get_var("z") == 30.0
    assert vm._get_var("ans") == 30.0


def test_vm_for_loop_negative_step_executes_expected_iterations():
    vm = run_vm(
        """
        total = 0
        For i = 3 To 1 Step -1
            total = total + i
        Next
        """
    )

    assert vm._get_var("total") == 6.0
    assert vm._get_var("i") == 0


def test_vm_for_loop_rejects_zero_step():
    vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=1_000, skip_semantic=True))
    vm.load_source(
        """
        For i = 1 To 3 Step 0
            x = 1
        Next
        """,
        "<test>",
    )

    with pytest.raises(VMRuntimeError, match="FOR step cannot be 0"):
        vm.run()


def test_vm_list_and_matrix_assignment_auto_expand():
    vm = run_vm(
        """
        L1(3) = 42
        a = L1(1)
        b = L1(3)
        MatA(2,3) = 7
        c = MatA(1,1)
        d = MatA(2,3)
        """
    )

    assert vm._get_var("a") == 0
    assert vm._get_var("b") == 42
    assert vm._get_var("c") == 0
    assert vm._get_var("d") == 7


def test_vm_randomize_and_rndr_are_deterministic_and_bounds_safe():
    source = """
    randomize(123)
    a = rndr(10, 1)
    b = rndr(10, 1)
    """

    vm1 = run_vm(source)
    vm2 = run_vm(source)

    a1 = vm1._get_var("a")
    b1 = vm1._get_var("b")
    a2 = vm2._get_var("a")
    b2 = vm2._get_var("b")

    assert 1 <= a1 <= 10
    assert 1 <= b1 <= 10
    assert (a1, b1) == (a2, b2)


def test_vm_memwrite_then_memread_roundtrips():
    vm = run_vm(
        """
        x = memwrite(0x2345, 0xAB)
        y = memread(0x2345)
        """
    )

    assert vm._get_var("x") == 0xAB
    assert vm._get_var("y") == 0xAB


def test_vm_user_function_supports_default_args_and_return():
    vm = run_vm(
        """
        Function add(a, b = 5)
            Return a + b
        End

        x = add(2)
        y = add(2, 8)
        """
    )

    assert vm._get_var("x") == 7.0
    assert vm._get_var("y") == 10.0


def test_vm_getkey_reads_from_keyboard_buffer_without_prompt():
    vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=1_000, skip_semantic=True))
    vm.proc.add_key_to_buffer(27)
    vm.load_source("k = getkey()", "<test>")
    vm.run()

    assert vm._get_var("k") == 27


def test_vm_enforces_max_steps_guard():
    vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=20, skip_semantic=True))
    vm.load_source(
        """
        While 1
            x = x + 1
        End
        """,
        "<test>",
    )

    with pytest.raises(VMRuntimeError, match="Maximum instruction steps exceeded"):
        vm.run()


def test_vm_goto_skips_intermediate_statements():
    vm = run_vm(
        """
        x = 0
        Goto done
        x = 99
        done:
        x = x + 1
        """
    )

    assert vm._get_var("x") == 1.0


def test_vm_builtin_string_and_collection_helpers():
    vm = run_vm(
        """
        s = concat("ab", "cd")
        len_s = length(s)
        part = sub("abcdef", 2, 3)
        L1(1) = 10
        L1(2) = 20
        total = sum(L1)
        avg = mean(L1)
        d1 = dim(L1)
        d2 = dim("xyz")
        """,
        skip_semantic=True,
    )

    assert vm._get_var("s") == "abcd"
    assert vm._get_var("len_s") == 4
    assert vm._get_var("part") == "cde"
    assert vm._get_var("total") == 30.0
    assert vm._get_var("avg") == 15.0
    assert vm._get_var("d1") == 2
    assert vm._get_var("d2") == 3


def test_vm_reports_division_by_zero_and_sqrt_domain_errors():
    vm_div = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=1_000, skip_semantic=True))
    vm_div.load_source("x = 1 / 0", "<test>")
    with pytest.raises(VMRuntimeError, match="Division by zero"):
        vm_div.run()

    vm_sqrt = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=1_000, skip_semantic=True))
    vm_sqrt.load_source("x = sqrt(-1)", "<test>")
    with pytest.raises(VMRuntimeError, match=r"sqrt\(\) domain error"):
        vm_sqrt.run()


def test_vm_getkey_falls_back_to_console_input(monkeypatch: pytest.MonkeyPatch):
    vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=1_000, skip_semantic=True))
    monkeypatch.setattr("builtins.input", lambda _prompt: "A")
    vm.load_source("k = getkey()", "<test>")
    vm.run()

    assert vm._get_var("k") == vm.kbd.get_scan_code("A")


def test_vm_inline_asm_warns_once_when_not_strict(capsys: pytest.CaptureFixture[str]):
    vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=1_000, skip_semantic=True))
    vm.load_source(
        """
        Asm
            MOV R0, 1
        End
        Asm
            MOV R1, 2
        End
        x = 5
        """,
        "<test>",
    )
    vm.run()

    out = capsys.readouterr().out
    assert out.count("skipping inline Asm block") == 1
    assert vm._get_var("x") == 5


def test_vm_inline_asm_raises_in_strict_mode():
    vm = NoBASICVM(
        NoBASICVMConfig(
            enable_sound=False,
            max_steps=1_000,
            skip_semantic=True,
            strict_asm=True,
        )
    )
    vm.load_source(
        """
        Asm
            MOV R0, 1
        End
        """,
        "<test>",
    )

    with pytest.raises(VMRuntimeError, match="Inline Asm blocks are not supported"):
        vm.run()


def test_vm_reports_user_function_arity_errors():
    vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=1_000, skip_semantic=True))
    vm.load_source(
        """
        Function add(a, b)
            Return a + b
        End
        x = add(1)
        """,
        "<test>",
    )

    with pytest.raises(VMRuntimeError, match="expects 2-2 args"):
        vm.run()


def test_vm_reports_invalid_list_and_matrix_indices():
    vm_list = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=1_000, skip_semantic=True))
    vm_list.load_source("x = L1(0)", "<test>")
    with pytest.raises(VMRuntimeError, match="List indices are 1-based"):
        vm_list.run()

    vm_mat = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=1_000, skip_semantic=True))
    vm_mat.load_source("x = MatA(0, 1)", "<test>")
    with pytest.raises(VMRuntimeError, match="Matrix indices are 1-based"):
        vm_mat.run()


def test_vm_evaluates_bitwise_and_logical_operators():
    vm = run_vm(
        """
        a = 5 & 3
        b = 5 | 2
        c = 1 << 3
        d = 8 >> 1
        e = not 0
        f = 1 and 0
        g = 1 or 0
        """
    )

    assert vm._get_var("a") == 1
    assert vm._get_var("b") == 7
    assert vm._get_var("c") == 8
    assert vm._get_var("d") == 4
    assert vm._get_var("e") == 1
    assert vm._get_var("f") == 0
    assert vm._get_var("g") == 1


def test_vm_struct_member_assignment_auto_initializes_instance():
    vm = run_vm(
        """
        struct Point x y end
        p.x = 7
        q = p.x
        r = p.y
        """
    )

    p_value = vm._get_var("p")
    assert isinstance(p_value, dict)
    assert p_value["x"] == 7
    assert p_value["y"] == 0
    assert vm._get_var("q") == 7
    assert vm._get_var("r") == 0


def test_vm_struct_member_assignment_errors_when_struct_inference_is_ambiguous():
    vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=1_000, skip_semantic=True))
    vm.load_source(
        """
        struct Point x y end
        struct Pixel x c end
        p.x = 1
        """,
        "<test>",
    )

    with pytest.raises(VMRuntimeError, match="Cannot infer struct type for variable 'p'"):
        vm.run()


def test_vm_struct_member_assignment_infers_unique_struct_with_multiple_definitions():
    vm = run_vm(
        """
        struct Point x y end
        struct Size w h end
        p.x = 7
        s.w = 11
        q = p.y
        r = s.h
        """,
        skip_semantic=True,
    )

    p_value = vm._get_var("p")
    s_value = vm._get_var("s")
    assert p_value["__struct__"] == "point"
    assert s_value["__struct__"] == "size"
    assert p_value["x"] == 7
    assert s_value["w"] == 11
    assert vm._get_var("q") == 0
    assert vm._get_var("r") == 0


def test_vm_struct_member_access_is_case_insensitive():
    vm = run_vm(
        """
        struct Point X Y end
        p.x = 7
        q = P.Y
        """
    )

    p_value = vm._get_var("p")
    assert isinstance(p_value, dict)
    assert p_value["x"] == 7
    assert vm._get_var("q") == 0


def test_vm_struct_member_assignment_unknown_field_errors():
    vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=1_000, skip_semantic=True))
    vm.load_source(
        """
        struct Point x y end
        p.z = 1
        """,
        "<test>",
    )

    with pytest.raises(VMRuntimeError, match="has no field 'z'"):
        vm.run()


def test_vm_struct_member_read_auto_initializes_instance():
    vm = run_vm(
        """
        struct Point x y end
        q = p.x
        r = p.y
        """
    )

    p_value = vm._get_var("p")
    assert isinstance(p_value, dict)
    assert p_value["x"] == 0
    assert p_value["y"] == 0
    assert vm._get_var("q") == 0
    assert vm._get_var("r") == 0


def test_vm_struct_member_read_requires_declared_structs_for_inference():
    vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=1_000, skip_semantic=True))
    vm.load_source("q = p.x", "<test>")

    with pytest.raises(VMRuntimeError, match="Cannot infer struct type for variable 'p'"):
        vm.run()


def test_vm_struct_member_read_unknown_field_errors():
    vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=1_000, skip_semantic=True))
    vm.load_source(
        """
        struct Point x y end
        q = p.z
        """,
        "<test>",
    )

    with pytest.raises(VMRuntimeError, match="has no field 'z'"):
        vm.run()


def test_vm_member_access_and_assignment_work_for_plain_dict_values():
    vm = NoBASICVM(NoBASICVMConfig(enable_sound=False, max_steps=1_000, skip_semantic=True))
    vm.load_source(
        """
        q = p.x
        p.y = 9
        r = p.y
        """,
        "<test>",
    )
    vm._set_var("p", {"x": 4})

    vm.run()

    p_value = vm._get_var("p")
    assert p_value["x"] == 4
    assert p_value["y"] == 9
    assert vm._get_var("q") == 4
    assert vm._get_var("r") == 9
