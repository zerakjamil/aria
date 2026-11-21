"""
Unit tests for Aria's Execution-Guided Self-Repair & Reflexion Backtracking Engine.
Verifies traceback distillation, reflection generation, context containment,
bounded loop termination, and execution sandbox exit codes.
"""

try:
    import pytest
except ImportError:
    pytest = None
from src.self_repair import (
    LocalizedTraceback,
    TracebackDistiller,
    ReflexionMemory,
    RepairAttempt,
    ExecutionGuidedRepairEngine,
)


def test_traceback_distiller_assertion_error():
    code = (
        "def add(a, b):\n"
        "    return a - b\n"
    )
    stderr = (
        'Traceback (most recent call last):\n'
        '  File "/tmp/test.py", line 6, in <module>\n'
        '    check(add)\n'
        '  File "/tmp/test.py", line 4, in check\n'
        '    assert candidate(1, 2) == 3\n'
        'AssertionError\n'
    )
    distiller = TracebackDistiller()
    tb = distiller.distill(stderr, code)

    assert tb.error_type == "AssertionError"
    assert "assert candidate(1, 2) == 3" in (tb.assertion_detail or "")
    summary = tb.summary()
    assert "AssertionError" in summary
    assert "assert candidate(1, 2) == 3" in summary


def test_traceback_distiller_index_error():
    code = (
        "def get_first(items):\n"
        "    return items[5]\n"
    )
    stderr = (
        'Traceback (most recent call last):\n'
        '  File "/tmp/test.py", line 5, in <module>\n'
        '    check(get_first)\n'
        '  File "/tmp/test.py", line 2, in get_first\n'
        '    return items[5]\n'
        'IndexError: list index out of range\n'
    )
    distiller = TracebackDistiller()
    tb = distiller.distill(stderr, code)

    assert tb.error_type == "IndexError"
    assert tb.line_number == 2
    assert tb.failing_code == "return items[5]"
    assert "list index out of range" in tb.message


def test_traceback_distiller_syntax_error():
    code = (
        "def broken():\n"
        "    return 1 +\n"
    )
    stderr = (
        '  File "/tmp/test.py", line 2\n'
        '    return 1 +\n'
        '             ^\n'
        'SyntaxError: invalid syntax\n'
    )
    distiller = TracebackDistiller()
    tb = distiller.distill(stderr, code)

    assert tb.error_type == "SyntaxError"
    assert tb.line_number == 2
    assert "return 1 +" in (tb.failing_code or "")


def test_traceback_distiller_timeout():
    code = "while True: pass"
    stderr = "Execution timed out after 5.0s"
    distiller = TracebackDistiller()
    tb = distiller.distill(stderr, code)

    assert tb.error_type == "TimeoutExpired"
    assert "infinite loop" in tb.message.lower() or "timed out" in tb.message.lower()


def test_reflexion_memory_generation_and_prompt_containment():
    memory = ReflexionMemory(
        task_id="Fix/test_0",
        prompt="Write a function `multiply(a, b)` that returns product."
    )
    tb = LocalizedTraceback(
        error_type="AssertionError",
        line_number=2,
        failing_code="return a + b",
        assertion_detail="assert candidate(2, 3) == 6",
        message=""
    )
    reflection = memory.generate_reflection_block(attempt_num=1, tb=tb)

    assert "<reflection>" in reflection
    assert "</reflection>" in reflection
    assert "Attempt 1 failed with AssertionError" in reflection
    assert "Root cause hypothesis:" in reflection
    assert "Remediation strategy:" in reflection

    # Record attempt
    attempt = RepairAttempt(
        attempt=1,
        raw_response="```python\ndef multiply(a, b):\n    return a + b\n```",
        thought="Simple addition",
        code="def multiply(a, b):\n    return a + b",
        passed=False,
        returncode=1,
        traceback=tb,
        reflection=reflection,
        latency_ms=120.0,
        eval_tokens=45
    )
    memory.record_attempt(attempt)

    repair_prompt = memory.build_repair_prompt(next_attempt=2)
    assert "### ORIGINAL TASK:" in repair_prompt
    assert "### PREVIOUS ATTEMPT (Attempt 1):" in repair_prompt
    assert "### EXECUTION FEEDBACK FROM SANDBOX:" in repair_prompt
    assert "### MEMORY REFLECTION:" in repair_prompt
    assert "<reflection>" in repair_prompt
    assert "### INSTRUCTIONS FOR REPAIR ATTEMPT 2:" in repair_prompt


def test_sandbox_execution_clean_exit():
    engine = ExecutionGuidedRepairEngine()
    good_code = "def solve(): return 42"
    test_code = "assert solve() == 42"

    res = engine.execute_in_sandbox(good_code, test_code)
    assert res["passed"] is True
    assert res["returncode"] == 0
    assert res["stderr"] == ""


def test_sandbox_execution_assertion_failure():
    engine = ExecutionGuidedRepairEngine()
    bad_code = "def solve(): return 0"
    test_code = "assert solve() == 42"

    res = engine.execute_in_sandbox(bad_code, test_code)
    assert res["passed"] is False
    assert res["returncode"] != 0
    assert "AssertionError" in res["stderr"]


def test_bounded_loop_termination_mocked():
    """Verify loop strictly terminates at max_attempts without runaway recursion."""
    engine = ExecutionGuidedRepairEngine(max_attempts=3)

    # Mock query_model to always return buggy code
    call_count = [0]
    def mock_query(messages, temperature=0.2):
        call_count[0] += 1
        return {
            "ok": True,
            "content": "<thought>Failing deliberately</thought>\n```python\ndef solve(): return -1\n```",
            "eval_count": 30,
            "latency_ms": 50.0
        }

    engine.query_model = mock_query

    task_id = "test_loop_bound"
    prompt = "Return positive integer 1."
    test_code = "assert solve() == 1"

    res = engine.run_repair_loop(task_id, prompt, test_code)
    assert res["initial_passed"] is False
    assert res["final_passed"] is False
    assert res["repaired"] is False
    assert res["attempts_used"] == 3
    assert call_count[0] == 3
    assert len(res["trajectory"]) == 3
