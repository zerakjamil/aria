#!/usr/bin/env python3
"""
Phase 7 Autonomous Self-Evolution Engine: On-Device GRPO / RLVR with Graduated Verifiable Rewards.
Executes verifiable self-play reasoning, sampling groups of G=4 candidate completions,
evaluating them in an isolated execution sandbox against ground-truth assertions,
computing graduated rewards to prevent zero-variance stagnation, and calculating
GRPO normalized advantages.
"""

import os
import sys
import re
import json
import time
import math
import tempfile
import subprocess
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Add parent directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.sandbox_runner import SandboxedCommandRunner
from src.test_time_reasoning import ThinkThenActEngine

OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "aria:3b"
GROUP_SIZE = 4  # G = 4 candidate rollouts per prompt (DeepSeek-R1 style)

GRPO_CHALLENGES = [
    {
        "task_id": "GRPO/py_valid_palindrome_iv",
        "entry_point": "valid_palindrome_remove_one",
        "prompt": '''def valid_palindrome_remove_one(s: str) -> bool:
    """ Given a string s, return True if the s can be palindrome after deleting at most one character from it.
    >>> valid_palindrome_remove_one("aba")
    True
    >>> valid_palindrome_remove_one("abca")
    True
    >>> valid_palindrome_remove_one("abc")
    False
    """
''',
        "assertions": [
            'candidate("aba") == True',
            'candidate("abca") == True',
            'candidate("abc") == False',
            'candidate("deeee") == True',
            'candidate("racecar") == True',
            'candidate("a") == True',
            'candidate("ab") == True',
            'candidate("abcdef") == False'
        ]
    },
    {
        "task_id": "GRPO/py_two_sum_sorted",
        "entry_point": "two_sum_sorted",
        "prompt": '''from typing import List

def two_sum_sorted(numbers: List[int], target: int) -> List[int]:
    """ Given a 1-indexed array of integers numbers that is already sorted in non-decreasing order,
    find two numbers such that they add up to a specific target number.
    Return the indices of the two numbers, 1-indexed, as an integer array [index1, index2] of length 2.
    >>> two_sum_sorted([2,7,11,15], 9)
    [1, 2]
    >>> two_sum_sorted([2,3,4], 6)
    [1, 3]
    >>> two_sum_sorted([-1,0], -1)
    [1, 2]
    """
''',
        "assertions": [
            'candidate([2,7,11,15], 9) == [1, 2]',
            'candidate([2,3,4], 6) == [1, 3]',
            'candidate([-1,0], -1) == [1, 2]',
            'candidate([1,2,3,4,4,9,56,90], 8) == [4, 5]',
            'candidate([0,0,3,4], 0) == [1, 2]'
        ]
    },
    {
        "task_id": "GRPO/py_merge_intervals",
        "entry_point": "merge_intervals",
        "prompt": '''from typing import List

def merge_intervals(intervals: List[List[int]]) -> List[List[int]]:
    """ Given an array of intervals where intervals[i] = [start_i, end_i], merge all overlapping intervals,
    and return an array of the non-overlapping intervals that cover all the intervals in the input.
    >>> merge_intervals([[1,3],[2,6],[8,10],[15,18]])
    [[1,6],[8,10],[15,18]]
    >>> merge_intervals([[1,4],[4,5]])
    [[1,5]]
    """
''',
        "assertions": [
            'candidate([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]',
            'candidate([[1,4],[4,5]]) == [[1,5]]',
            'candidate([[1,4],[0,4]]) == [[0,4]]',
            'candidate([[1,4],[2,3]]) == [[1,4]]',
            'candidate([]) == []',
            'candidate([[1,4]]) == [[1,4]]'
        ]
    },
    {
        "task_id": "GRPO/py_valid_parentheses_stack",
        "entry_point": "is_valid_brackets",
        "prompt": '''def is_valid_brackets(s: str) -> bool:
    """ Given a string s containing just the characters '(', ')', '{', '}', '[' and ']',
    determine if the input string is valid.
    >>> is_valid_brackets("()")
    True
    >>> is_valid_brackets("()[]{}")
    True
    >>> is_valid_brackets("(]")
    False
    """
''',
        "assertions": [
            'candidate("()") == True',
            'candidate("()[]{}") == True',
            'candidate("(]") == False',
            'candidate("([)]") == False',
            'candidate("{[]}") == True',
            'candidate("") == True',
            'candidate("[") == False',
            'candidate("]") == False'
        ]
    },
    {
        "task_id": "GRPO/py_search_insert_position",
        "entry_point": "search_insert",
        "prompt": '''from typing import List

def search_insert(nums: List[int], target: int) -> int:
    """ Given a sorted array of distinct integers and a target value, return the index if the target is found.
    If not, return the index where it would be if it were inserted in order in O(log n) runtime.
    >>> search_insert([1,3,5,6], 5)
    2
    >>> search_insert([1,3,5,6], 2)
    1
    >>> search_insert([1,3,5,6], 7)
    4
    """
''',
        "assertions": [
            'candidate([1,3,5,6], 5) == 2',
            'candidate([1,3,5,6], 2) == 1',
            'candidate([1,3,5,6], 7) == 4',
            'candidate([1,3,5,6], 0) == 0',
            'candidate([1], 0) == 0',
            'candidate([1], 2) == 1'
        ]
    }
]


def score_candidate_graduated(code: str, entry_point: str, assertions: List[str], sandbox: SandboxedCommandRunner) -> Tuple[float, int, int, str]:
    """
    Computes graduated verifiable reward R in [-1.0, 1.0]:
    - Syntax error: -1.0
    - Runtime error before assertions: -0.5
    - Partial assertions pass: -0.2 + 0.8 * (k / M)
    - Full assertions pass: +1.0
    """
    if not code.strip():
        return -1.0, 0, len(assertions), "empty_code"

    # Compile test verification script that runs each assertion independently
    test_harness = f"""
import sys
{code}

candidate = {entry_point}
assertions = {json.dumps(assertions)}
passed = 0
failed = 0

for idx, expr in enumerate(assertions):
    try:
        if eval(expr):
            passed += 1
        else:
            failed += 1
    except Exception as e:
        failed += 1

print(f"PASSED={{passed}} FAILED={{failed}}")
if failed > 0:
    sys.exit(1)
sys.exit(0)
"""
    res = sandbox.execute_script(test_harness, interpreter="python3", timeout=2.5)

    if res["exit_code"] == 124:
        return -1.0, 0, len(assertions), "timeout"

    stdout = res["stdout"]
    stderr = res["stderr"]

    if "SyntaxError" in stderr:
        return -1.0, 0, len(assertions), f"syntax_error: {stderr.splitlines()[-1]}"

    match = re.search(r"PASSED=(\d+)\s+FAILED=(\d+)", stdout)
    if not match:
        # Runtime crash before reaching assertions
        return -0.5, 0, len(assertions), f"runtime_crash: {stderr.splitlines()[-1] if stderr else 'unknown'}"

    k = int(match.group(1))
    M = len(assertions)

    if k == M:
        return 1.0, k, M, "full_pass"
    elif k == 0:
        return -0.5, 0, M, "all_failed"
    else:
        # Graduated reward ensures non-zero variance
        reward = -0.2 + (0.8 * (k / M))
        return reward, k, M, f"partial_pass_{k}_{M}"


def query_ollama(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.7) -> Dict[str, Any]:
    """Queries local Ollama inference server."""
    url = f"{OLLAMA_URL}/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 768,
            "stop": ["\nUser:", "\nHuman:", "<|im_end|>", "<|endoftext|>"]
        }
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return {"content": data.get("response", ""), "latency_ms": latency_ms, "ok": True}
    except Exception as e:
        return {"content": "", "latency_ms": 0.0, "ok": False, "error": str(e)}


def run_grpo_evolution_phase7(output_dir: str = "/srv/storage/ai-companion/training/data") -> Dict[str, Any]:
    """Runs Group Relative Policy Optimization rollout & reward collection."""
    print("=" * 80)
    print("ARIA PHASE 7 GRPO / RLVR POLICY OPTIMIZATION ENGINE")
    print(f"Group Size: G={GROUP_SIZE} | Graduated Verifiable Rewards [-1.0, 1.0]")
    print("=" * 80)

    sandbox = SandboxedCommandRunner()
    reasoning_engine = ThinkThenActEngine()
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    golden_trajectories = []
    telemetry_records = []

    for task_idx, task in enumerate(GRPO_CHALLENGES, 1):
        task_id = task["task_id"]
        entry_point = task["entry_point"]
        user_prompt = task["prompt"]
        assertions = task["assertions"]

        print(f"\n[{task_idx:02d}/{len(GRPO_CHALLENGES)}] Generating Rollouts for: {task_id}")

        completions = []
        rewards = []
        parsed_candidates = []

        # Sample G=4 candidates with varying temperatures
        temps = [0.2, 0.5, 0.8, 1.0]
        for g in range(GROUP_SIZE):
            temp = temps[g]
            system_instruction = (
                "You are Aria, an expert sovereign algorithmic engineer. "
                "Think step by step in <thought>...</thought> scratchpad, then write the solution inside ```python```."
            )
            full_prompt = f"{system_instruction}\n\nTask:\n{user_prompt}\nProvide complete Python function."

            gen = query_ollama(full_prompt, temperature=temp)
            if not gen["ok"] or not gen["content"].strip():
                # Fallback to local heuristic synthesis if Ollama is not active
                raw_code = f"# Fallback completion\n{user_prompt}\n    pass"
                parsed = {"clean_code": raw_code, "scratchpad": "Fallback reasoning", "has_scratchpad": True}
            else:
                parsed = reasoning_engine.parse_response(gen["content"])

            reward, k, M, status = score_candidate_graduated(parsed["clean_code"], entry_point, assertions, sandbox)
            completions.append(gen.get("content", ""))
            rewards.append(reward)
            parsed_candidates.append(parsed)

            print(f"   Candidate {g+1} (temp={temp:.1f}): Reward = {reward:+.3f} ({status}, {k}/{M} assertions)")

        # Compute Advantage: A_i = (R_i - mean(R)) / (std(R) + eps)
        mean_r = sum(rewards) / len(rewards)
        variance = sum((r - mean_r) ** 2 for r in rewards) / len(rewards)
        std_r = math.sqrt(variance)
        eps = 1e-4

        advantages = [(r - mean_r) / (std_r + eps) for r in rewards]
        print(f"   Group Mean: {mean_r:+.3f} | Std: {std_r:.3f} | Advantages: {[round(a, 2) for a in advantages]}")

        # Collect golden trajectories (reward == 1.0)
        for g, (r, cand) in enumerate(zip(rewards, parsed_candidates)):
            if r >= 0.99:
                thought = cand.get("scratchpad", "Analyze problem invariants.")
                code = cand["clean_code"]
                formatted_out = f"<thought>\n{thought}\n</thought>\n\n```python\n{code}\n```"
                golden_trajectories.append({
                    "instruction": "You are Aria, an expert sovereign algorithmic engineer and technical copilot. When faced with programming tasks, conduct deep internal scratchpad reasoning before writing any final solution. Enclose your analysis in <thought>...</thought> followed by the code block.",
                    "input": user_prompt.strip(),
                    "output": formatted_out
                })

        telemetry_records.append({
            "task_id": task_id,
            "rewards": rewards,
            "mean_reward": mean_r,
            "std_reward": std_r,
            "advantages": advantages
        })

    # Save golden trajectories
    golden_file = out_path / "rlvr_self_evolved.jsonl"
    with open(golden_file, "w", encoding="utf-8") as f:
        for t in golden_trajectories:
            f.write(json.dumps(t) + "\n")

    print("\n" + "=" * 80)
    print(f"Collected {len(golden_trajectories)} golden trajectories to: {golden_file}")
    print("=" * 80)
    return {"golden_count": len(golden_trajectories), "records": telemetry_records}


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "/srv/storage/ai-companion/training/data"
    run_grpo_evolution_phase7(out_dir)
