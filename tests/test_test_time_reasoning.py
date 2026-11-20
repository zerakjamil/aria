import pytest
from src.test_time_reasoning import ThinkThenActEngine, THINK_THEN_ACT_SYSTEM_PROMPT, DIRECT_SYSTEM_PROMPT


def test_think_then_act_formatting():
    engine = ThinkThenActEngine(thinking_token_budget=512, code_token_budget=400)
    
    # Mode B (Think-then-act)
    messages_reasoning = engine.format_prompt("Solve 2sum", with_reasoning=True)
    assert len(messages_reasoning) == 2
    assert messages_reasoning[0]["role"] == "system"
    assert "<thought>" in messages_reasoning[0]["content"]
    assert "</thought>" in messages_reasoning[0]["content"]
    assert messages_reasoning[1]["content"] == "Solve 2sum"

    # Mode A (Direct)
    messages_direct = engine.format_prompt("Solve 2sum", with_reasoning=False)
    assert len(messages_direct) == 2
    assert "Directly" in messages_direct[0]["content"] or "directly" in messages_direct[0]["content"]
    assert "<thought>" not in messages_direct[0]["content"]


def test_scratchpad_and_code_extraction():
    engine = ThinkThenActEngine()
    raw_output = """
<thought>
We need to iterate through elements.
Time complexity O(N).
Check empty list.
</thought>
```python
def solve(nums):
    return sum(nums)
```
"""
    parsed = engine.parse_response(raw_output)
    assert parsed["has_scratchpad"] is True
    assert "Time complexity O(N)" in parsed["scratchpad"]
    assert parsed["clean_code"] == "def solve(nums):\n    return sum(nums)"
    assert parsed["syntax_valid"] is True
    assert parsed["syntax_error"] is None
    assert parsed["scratchpad_tokens_est"] > 0
    assert parsed["code_tokens_est"] > 0


def test_syntax_ast_validation_error():
    engine = ThinkThenActEngine()
    raw_output = """
```python
def broken_syntax(
    return 42
```
"""
    parsed = engine.parse_response(raw_output)
    assert parsed["has_scratchpad"] is False
    assert parsed["syntax_valid"] is False
    assert "SyntaxError" in parsed["syntax_error"]


def test_generation_options_compute_budget():
    engine = ThinkThenActEngine(thinking_token_budget=512, code_token_budget=400)
    
    opts_reasoning = engine.get_generation_options(with_reasoning=True)
    assert opts_reasoning["num_predict"] == 912 # 512 + 400
    assert opts_reasoning["temperature"] == 0.3

    opts_direct = engine.get_generation_options(with_reasoning=False)
    assert opts_direct["num_predict"] == 400
    assert opts_direct["temperature"] == 0.2
