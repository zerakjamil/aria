#!/usr/bin/env python3
"""
Autonomous Self-Evolution Loop: On-Device GRPO / RLVR Engine for Aria
Executes verifiable self-play reasoning, sampling groups of G=4 candidate completions,
evaluating them in an isolated execution sandbox against ground-truth assertions,
computing GRPO normalized advantages, and compiling verified self-evolved trajectories.
"""

import os
import sys
import json
import time
import math
import tempfile
import subprocess
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.test_time_reasoning import ThinkThenActEngine

OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "aria:3b"
GROUP_SIZE = 4  # G = 4 candidate rollouts per prompt (DeepSeek-R1 style)

CHALLENGE_BANK = [
    {
        "task_id": "RLVR/py_valid_palindrome_iv",
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
        "test": '''
def check(candidate):
    assert candidate("aba") == True
    assert candidate("abca") == True
    assert candidate("abc") == False
    assert candidate("deeee") == True
    assert candidate("racecar") == True
    assert candidate("a") == True
    assert candidate("ab") == True
    assert candidate("abcdef") == False

check(valid_palindrome_remove_one)
'''
    },
    {
        "task_id": "RLVR/py_two_sum_sorted",
        "entry_point": "two_sum_sorted",
        "prompt": '''from typing import List

def two_sum_sorted(numbers: List[int], target: int) -> List[int]:
    """ Given a 1-indexed array of integers numbers that is already sorted in non-decreasing order,
    find two numbers such that they add up to target. Return the 1-based indices [index1, index2].
    >>> two_sum_sorted([2, 7, 11, 15], 9)
    [1, 2]
    >>> two_sum_sorted([2, 3, 4], 6)
    [1, 3]
    """
''',
        "test": '''
def check(candidate):
    assert candidate([2, 7, 11, 15], 9) == [1, 2]
    assert candidate([2, 3, 4], 6) == [1, 3]
    assert candidate([-1, 0], -1) == [1, 2]
    assert candidate([1, 2, 3, 4, 4, 9], 8) == [4, 5]

check(two_sum_sorted)
'''
    },
    {
        "task_id": "RLVR/py_merge_intervals",
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
        "test": '''
def check(candidate):
    assert candidate([[1, 3], [2, 6], [8, 10], [15, 18]]) == [[1, 6], [8, 10], [15, 18]]
    assert candidate([[1, 4], [4, 5]]) == [[1, 5]]
    assert candidate([[1, 4], [0, 4]]) == [[0, 4]]
    assert candidate([[1, 4], [2, 3]]) == [[1, 4]]
    assert candidate([]) == []
    assert candidate([[1, 2]]) == [[1, 2]]

check(merge_intervals)
'''
    },
    {
        "task_id": "RLVR/py_max_subarray_kadane",
        "entry_point": "max_sub_array",
        "prompt": '''from typing import List

def max_sub_array(nums: List[int]) -> int:
    """ Given an integer array nums, find the subarray with the largest sum, and return its sum.
    >>> max_sub_array([-2,1,-3,4,-1,2,1,-5,4])
    6
    >>> max_sub_array([1])
    1
    >>> max_sub_array([5,4,-1,7,8])
    23
    """
''',
        "test": '''
def check(candidate):
    assert candidate([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6
    assert candidate([1]) == 1
    assert candidate([5, 4, -1, 7, 8]) == 23
    assert candidate([-1]) == -1
    assert candidate([-3, -2, -5]) == -2

check(max_sub_array)
'''
    },
    {
        "task_id": "RLVR/py_parse_proc_meminfo",
        "entry_point": "parse_proc_meminfo",
        "prompt": '''from typing import Dict

def parse_proc_meminfo(meminfo_content: str) -> Dict[str, int]:
    """ Parses Linux /proc/meminfo string content and returns a dictionary of integer values in kilobytes (kB).
    Ignore lines that do not have the format 'Key: Value kB'.
    >>> parse_proc_meminfo("MemTotal:       16384000 kB\\nMemFree:         4096000 kB")
    {'MemTotal': 16384000, 'MemFree': 4096000}
    """
''',
        "test": '''
def check(candidate):
    sample = """MemTotal:       16384000 kB
MemFree:         4096000 kB
MemAvailable:    8192000 kB
Buffers:          512000 kB
Cached:          2048000 kB
HugePages_Total:       0
"""
    res = candidate(sample)
    assert res['MemTotal'] == 16384000
    assert res['MemFree'] == 4096000
    assert res['MemAvailable'] == 8192000
    assert 'HugePages_Total' not in res
    assert candidate("") == {}

check(parse_proc_meminfo)
'''
    },
    {
        "task_id": "RLVR/py_longest_consecutive",
        "entry_point": "longest_consecutive",
        "prompt": '''from typing import List

def longest_consecutive(nums: List[int]) -> int:
    """ Given an unsorted array of integers nums, return the length of the longest consecutive elements sequence.
    Algorithm must run in O(n) time complexity.
    >>> longest_consecutive([100, 4, 200, 1, 3, 2])
    4
    >>> longest_consecutive([0, 3, 7, 2, 5, 8, 4, 6, 0, 1])
    9
    """
''',
        "test": '''
def check(candidate):
    assert candidate([100, 4, 200, 1, 3, 2]) == 4
    assert candidate([0, 3, 7, 2, 5, 8, 4, 6, 0, 1]) == 9
    assert candidate([]) == 0
    assert candidate([7]) == 1
    assert candidate([1, 2, 0, 1]) == 3

check(longest_consecutive)
'''
    },
    {
        "task_id": "RLVR/py_valid_parentheses_stack",
        "entry_point": "is_valid_brackets",
        "prompt": '''def is_valid_brackets(s: str) -> bool:
    """ Given a string s containing just the characters '(', ')', '{', '}', '[' and ']',
    determine if the input string is valid.
    Open brackets must be closed by the same type of brackets in the correct order.
    >>> is_valid_brackets("()")
    True
    >>> is_valid_brackets("()[]{}")
    True
    >>> is_valid_brackets("(]")
    False
    """
''',
        "test": '''
def check(candidate):
    assert candidate("()") == True
    assert candidate("()[]{}") == True
    assert candidate("(]") == False
    assert candidate("([)]") == False
    assert candidate("{[]}") == True
    assert candidate("") == True
    assert candidate("[") == False
    assert candidate("]") == False

check(is_valid_brackets)
'''
    },
    {
        "task_id": "RLVR/py_binary_search_insert",
        "entry_point": "search_insert_position",
        "prompt": '''from typing import List

def search_insert_position(nums: List[int], target: int) -> int:
    """ Given a sorted array of distinct integers and a target value, return the index if the target is found.
    If not, return the index where it would be if it were inserted in order.
    Must write an algorithm with O(log n) runtime complexity.
    >>> search_insert_position([1, 3, 5, 6], 5)
    2
    >>> search_insert_position([1, 3, 5, 6], 2)
    1
    >>> search_insert_position([1, 3, 5, 6], 7)
    4
    """
''',
        "test": '''
def check(candidate):
    assert candidate([1, 3, 5, 6], 5) == 2
    assert candidate([1, 3, 5, 6], 2) == 1
    assert candidate([1, 3, 5, 6], 7) == 4
    assert candidate([1, 3, 5, 6], 0) == 0
    assert candidate([1], 0) == 0
    assert candidate([1], 2) == 1

check(search_insert_position)
'''
    },
    {
        "task_id": "RLVR/py_cidr_subnet_check",
        "entry_point": "ip_in_cidr",
        "prompt": '''def ip_in_cidr(ip: str, cidr: str) -> bool:
    """ Return True if the given IPv4 address string (e.g. '192.168.1.5') belongs to the given CIDR (e.g. '192.168.1.0/24').
    >>> ip_in_cidr('192.168.1.10', '192.168.1.0/24')
    True
    >>> ip_in_cidr('192.168.2.1', '192.168.1.0/24')
    False
    """
''',
        "test": '''
def check(candidate):
    assert candidate('192.168.1.10', '192.168.1.0/24') == True
    assert candidate('192.168.2.1', '192.168.1.0/24') == False
    assert candidate('10.0.0.1', '10.0.0.0/8') == True
    assert candidate('172.16.5.4', '172.16.0.0/16') == True
    assert candidate('172.17.5.4', '172.16.0.0/16') == False
    assert candidate('8.8.8.8', '8.8.8.8/32') == True
    assert candidate('8.8.8.9', '8.8.8.8/32') == False

check(ip_in_cidr)
'''
    },
    {
        "task_id": "RLVR/py_decode_string_stack",
        "entry_point": "decode_string",
        "prompt": '''def decode_string(s: str) -> str:
    """ Given an encoded string, return its decoded string.
    The encoding rule is: k[encoded_string], where the encoded_string inside the square brackets is repeated exactly k times.
    You may assume that the input string is always valid; no extra white spaces, square brackets are well-formed, etc.
    >>> decode_string("3[a]2[bc]")
    'aaabcbc'
    >>> decode_string("3[a2[c]]")
    'accaccacc'
    >>> decode_string("2[abc]3[cd]ef")
    'abcabccdcdcdef'
    """
''',
        "test": '''
def check(candidate):
    assert candidate("3[a]2[bc]") == "aaabcbc"
    assert candidate("3[a2[c]]") == "accaccacc"
    assert candidate("2[abc]3[cd]ef") == "abcabccdcdcdef"
    assert candidate("abc") == "abc"
    assert candidate("10[a]") == "aaaaaaaaaa"

check(decode_string)
'''
    },
    {
        "task_id": "RLVR/py_top_k_frequent",
        "entry_point": "top_k_frequent",
        "prompt": '''from typing import List

def top_k_frequent(nums: List[int], k: int) -> List[int]:
    """ Given an integer array nums and an integer k, return the k most frequent elements.
    The answer can be returned in any order, but sorted descending by frequency is preferred.
    >>> sorted(top_k_frequent([1,1,1,2,2,3], 2))
    [1, 2]
    >>> top_k_frequent([1], 1)
    [1]
    """
''',
        "test": '''
def check(candidate):
    assert set(candidate([1, 1, 1, 2, 2, 3], 2)) == {1, 2}
    assert candidate([1], 1) == [1]
    assert set(candidate([4, 1, -1, 2, -1, 2, 3], 2)) == {-1, 2}

check(top_k_frequent)
'''
    },
    {
        "task_id": "RLVR/py_rotate_matrix",
        "entry_point": "rotate_image_90",
        "prompt": '''from typing import List

def rotate_image_90(matrix: List[List[int]]) -> List[List[int]]:
    """ Given an n x n 2D matrix representing an image, rotate the matrix by 90 degrees (clockwise).
    Return the rotated matrix.
    >>> rotate_image_90([[1,2,3],[4,5,6],[7,8,9]])
    [[7,4,1],[8,5,2],[9,6,3]]
    """
''',
        "test": '''
def check(candidate):
    assert candidate([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) == [[7, 4, 1], [8, 5, 2], [9, 6, 3]]
    assert candidate([[1, 2], [3, 4]]) == [[3, 1], [4, 2]]
    assert candidate([[1]]) == [[1]]

check(rotate_image_90)
'''
    }
]


def query_ollama_completion(prompt_messages: List[Dict[str, str]], temperature: float = 0.7, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Queries Ollama HTTP API with non-streaming completion.
    """
    payload = {
        "model": model,
        "messages": prompt_messages,
        "stream": False,
        "options": {
            "num_predict": 768,
            "temperature": temperature,
            "top_p": 0.95,
            "min_p": 0.05,
            "repeat_penalty": 1.10,
            "stop": ["\nUser:", "\nHuman:", "<|im_end|>", "<|endoftext|>"]
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
        latency_ms = (time.time() - t0) * 1000.0
        content = res_json.get("message", {}).get("content", "")
        eval_count = res_json.get("eval_count", 0)
        return {"content": content, "latency_ms": latency_ms, "eval_count": eval_count, "ok": True}
    except Exception as e:
        return {"content": "", "latency_ms": 0.0, "eval_count": 0, "ok": False, "error": str(e)}


def execute_in_sandbox(code: str, test_code: str, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Executes Python candidate solution + test assertions in an isolated subprocess.
    """
    full_script = f"{code}\n\n{test_code}"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(full_script)
        temp_path = f.name

    try:
        t0 = time.time()
        proc = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        duration_ms = (time.time() - t0) * 1000.0
        passed = (proc.returncode == 0)
        return {
            "passed": passed,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_ms": duration_ms
        }
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "returncode": -9,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout}s",
            "duration_ms": timeout * 1000.0
        }
    except Exception as e:
        return {
            "passed": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "duration_ms": 0.0
        }
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


def compute_grpo_advantages(rewards: List[float]) -> Tuple[List[float], float, float]:
    """
    Computes Group Relative Policy Optimization (GRPO) advantage:
    A_i = (r_i - mean(rewards)) / (std(rewards) + 1e-4)
    """
    n = len(rewards)
    if n == 0:
        return [], 0.0, 0.0
    mean_r = sum(rewards) / n
    var_r = sum((r - mean_r) ** 2 for r in rewards) / n
    std_r = math.sqrt(var_r)
    eps = 1e-4
    advantages = [(r - mean_r) / (std_r + eps) for r in rewards]
    return advantages, mean_r, std_r


def run_grpo_self_evolution(output_dir: str = "/srv/storage/ai-companion/training/data"):
    engine = ThinkThenActEngine(thinking_token_budget=512, code_token_budget=400)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("ARIA 2026 AUTONOMOUS SELF-EVOLUTION ENGINE (ON-DEVICE GRPO / RLVR)")
    print(f"Model Policy: {DEFAULT_MODEL} | Group Size G = {GROUP_SIZE} | Sandbox: Subprocess Verifier")
    print(f"Total Problem Bank: {len(CHALLENGE_BANK)} challenges")
    print("=" * 80, flush=True)

    golden_trajectories: List[Dict[str, Any]] = []
    total_rollouts = 0
    passed_rollouts = 0
    contrastive_groups = 0

    telemetry_records = []

    for idx, problem in enumerate(CHALLENGE_BANK, 1):
        task_id = problem["task_id"]
        prompt_text = problem["prompt"]
        test_text = problem["test"]

        print(f"\n[{idx:02d}/{len(CHALLENGE_BANK)}] Challenge: {task_id}")
        messages = engine.format_prompt(prompt_text, with_reasoning=True)

        candidate_results = []
        rewards = []

        # 1. Sample G=4 rollouts from the policy
        for g_idx in range(GROUP_SIZE):
            total_rollouts += 1
            gen_res = query_ollama_completion(messages, temperature=0.7)
            if not gen_res["ok"]:
                print(f"   Candidate {g_idx+1}: ERROR ({gen_res.get('error')})")
                rewards.append(-1.0)
                candidate_results.append({"passed": False, "raw": "", "parsed": {}, "exec": {}})
                continue

            parsed = engine.parse_response(gen_res["content"])
            exec_res = execute_in_sandbox(parsed["clean_code"], test_text)

            is_pass = exec_res["passed"]
            r = 1.0 if is_pass else -1.0
            rewards.append(r)
            if is_pass:
                passed_rollouts += 1

            thought_len = parsed["scratchpad_tokens_est"]
            code_len = len(parsed["clean_code"].splitlines())
            status_str = "PASS (+1.0)" if is_pass else f"FAIL (-1.0: exit={exec_res['returncode']})"
            print(f"   Candidate {g_idx+1}: {status_str:<22} | thought={thought_len:3d}tok | code={code_len:2d} lines | {gen_res['latency_ms']:.0f}ms")

            candidate_results.append({
                "passed": is_pass,
                "reward": r,
                "raw": gen_res["content"],
                "parsed": parsed,
                "exec": exec_res,
                "latency_ms": gen_res["latency_ms"]
            })

        # 2. Compute GRPO Advantages for Group
        advantages, mean_r, std_r = compute_grpo_advantages(rewards)
        print(f"   -> GRPO Group Telemetry: mean_reward={mean_r:+.2f}, std_reward={std_r:.2f}, advantages={[round(a, 2) for a in advantages]}")

        # 3. Analyze Contrast and Collect Policy-Reinforced Trajectories
        has_pass = any(c["passed"] for c in candidate_results)
        has_fail = any(not c["passed"] for c in candidate_results)

        if std_r > 0.0:
            contrastive_groups += 1

        if has_pass:
            # Select the passing candidate with the highest reward/advantage
            # If multiple pass, prefer the one with clean structured scratchpad reasoning
            passing_candidates = [c for c in candidate_results if c["passed"]]
            # Sort by scratchpad presence and reasonable length
            best_candidate = max(passing_candidates, key=lambda c: (c["parsed"]["has_scratchpad"], -len(c["parsed"]["clean_code"])))

            scratchpad = best_candidate["parsed"]["scratchpad"]
            clean_code = best_candidate["parsed"]["clean_code"]

            formatted_output = f"<thought>\n{scratchpad}\n</thought>\n\n```python\n{clean_code}\n```"

            golden_trajectories.append({
                "task_id": task_id,
                "instruction": (
                    "You are Aria, an expert sovereign algorithmic engineer and technical copilot. "
                    "When faced with programming and technical reasoning tasks, you MUST conduct deep "
                    "internal scratchpad reasoning before writing any final solution. "
                    "Enclose your analysis in <thought>...</thought> followed by the code block."
                ),
                "input": prompt_text,
                "output": formatted_output,
                "advantage": max(advantages) if advantages else 1.0,
                "verified": True
            })
            print(f"   ✓ Trajectory Reinforced: Added to RLVR self-evolution buffer (advantage={max(advantages):+.2f})")
        else:
            print(f"   ✗ Horizon Choke: 0/{GROUP_SIZE} passed; skipping parameter update for this vector")

        telemetry_records.append({
            "task_id": task_id,
            "rewards": rewards,
            "mean_reward": mean_r,
            "std_reward": std_r,
            "advantages": advantages
        })

    # Summary
    print("\n" + "=" * 80)
    print("GRPO SELF-EVOLUTION ROLLOUT SUMMARY:")
    print(f"  Total Challenges Evaluated:    {len(CHALLENGE_BANK)}")
    print(f"  Total Rollout Candidates (G=4): {total_rollouts}")
    print(f"  Successful Candidate Paths:     {passed_rollouts}/{total_rollouts} ({(passed_rollouts/total_rollouts)*100.0:.1f}%)")
    print(f"  Contrastive Groups (std > 0):   {contrastive_groups}/{len(CHALLENGE_BANK)}")
    print(f"  Golden Verified Trajectories:   {len(golden_trajectories)}/{len(CHALLENGE_BANK)}")
    print("=" * 80)

    # Save RLVR buffer
    rlvr_file = out_path / "rlvr_self_evolved.jsonl"
    with open(rlvr_file, "w") as f:
        for t in golden_trajectories:
            f.write(json.dumps({
                "instruction": t["instruction"],
                "input": t["input"],
                "output": t["output"]
            }) + "\n")
    print(f"\nSaved {len(golden_trajectories)} verified self-evolved trajectories to: {rlvr_file}")

    # Compile Combined Phase 5 Dataset (Anchor v4 + RLVR buffer)
    anchor_file = out_path / "combined_train_v4.jsonl"
    combined_v5_file = out_path / "combined_train_v5_rlvr.jsonl"

    anchor_samples = []
    if anchor_file.exists():
        with open(anchor_file, "r") as f:
            for line in f:
                if line.strip():
                    anchor_samples.append(json.loads(line))

    fused_samples = anchor_samples + [
        {
            "instruction": t["instruction"],
            "input": t["input"],
            "output": t["output"]
        } for t in golden_trajectories
    ]

    with open(combined_v5_file, "w") as f:
        for s in fused_samples:
            f.write(json.dumps(s) + "\n")

    print(f"Compiled Fused Phase 5 Dataset ({len(anchor_samples)} anchors + {len(golden_trajectories)} RLVR = {len(fused_samples)} total) to:\n  {combined_v5_file}")

    # Save Telemetry
    telemetry_file = out_path / "grpo_telemetry.json"
    with open(telemetry_file, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "model": DEFAULT_MODEL,
            "group_size": GROUP_SIZE,
            "total_challenges": len(CHALLENGE_BANK),
            "total_rollouts": total_rollouts,
            "passed_rollouts": passed_rollouts,
            "contrastive_groups": contrastive_groups,
            "golden_count": len(golden_trajectories),
            "records": telemetry_records
        }, f, indent=2)
    print(f"Saved GRPO telemetry log to: {telemetry_file}")

    return {
        "golden_count": len(golden_trajectories),
        "total_rollouts": total_rollouts,
        "passed_rollouts": passed_rollouts,
        "combined_file": str(combined_v5_file)
    }


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "/srv/storage/ai-companion/training/data"
    run_grpo_self_evolution(out_dir)
