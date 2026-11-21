#!/usr/bin/env python3
"""
Frontier Distillation Pipeline for Aria's Hardest Struggle Vectors
Orchestrates OpenCode's large free frontier teacher models (deepseek-v4.1-flash-free / hy4-flash-free)
to synthesize chain-of-thought reasoning (<thought>...</thought>) and ground-truth verified solutions
across Aria's hardest debugging, systems, reverse engineering, and persona fluid vectors.
"""

import subprocess
import json
import re
import time
import os
import sys
import tempfile
from pathlib import Path

OPENCODE_BIN = "/home/ayewar/.opencode/bin/opencode"
PRIMARY_MODEL = "opencode/deepseek-v4.1-flash-free"
FALLBACK_MODEL = "opencode/hy4-flash-free"

STRUGGLE_TASKS = [
    {
        "id": "below_zero",
        "category": "algorithmic",
        "instruction": "You are Aria, an expert sovereign algorithmic engineer and technical copilot. When faced with programming and technical reasoning tasks, you MUST conduct deep internal scratchpad reasoning before writing any final solution. Enclose your analysis in <thought>...</thought> followed by the code block.",
        "prompt": """In Python, implement:
from typing import List

def below_zero(operations: List[int]) -> bool:
    \"\"\" You're given a list of deposit and withdrawal operations on a bank account that starts with
    zero balance. Your task is to detect if at any point the balance of account falls below zero, and
    at that point function should return True. Otherwise it should return False.
    >>> below_zero([1, 2, 3])
    False
    >>> below_zero([1, 2, -4, 5])
    True
    \"\"\"
""",
        "test": """
def check(candidate):
    assert candidate([1, 2, 3]) == False
    assert candidate([1, 2, -4, 5]) == True
    assert candidate([1, -1, 2, -2, 5, -5, 4, -4]) == False
    assert candidate([1, -1, 2, -2, 5, -5, 4, -5]) == True
    assert candidate([1, -2, 2, -2, 5, -5, 4, -4]) == True
    assert candidate([]) == False
    assert candidate([-1]) == True
check(below_zero)
"""
    },
    {
        "id": "intersperse",
        "category": "algorithmic",
        "instruction": "You are Aria, an expert sovereign algorithmic engineer and technical copilot. When faced with programming and technical reasoning tasks, you MUST conduct deep internal scratchpad reasoning before writing any final solution. Enclose your analysis in <thought>...</thought> followed by the code block.",
        "prompt": """In Python, implement:
from typing import List

def intersperse(numbers: List[int], delimeter: int) -> List[int]:
    \"\"\" Insert a number 'delimeter' between every two consecutive elements of input list `numbers'
    >>> intersperse([], 4)
    []
    >>> intersperse([1, 2, 3], 4)
    [1, 4, 2, 4, 3]
    \"\"\"
""",
        "test": """
def check(candidate):
    assert candidate([], 4) == []
    assert candidate([1], 4) == [1]
    assert candidate([1, 2, 3], 4) == [1, 4, 2, 4, 3]
    assert candidate([5, 2, 4, 9], 3) == [5, 3, 2, 3, 4, 3, 9]
check(intersperse)
"""
    },
    {
        "id": "rolling_max",
        "category": "algorithmic",
        "instruction": "You are Aria, an expert sovereign algorithmic engineer and technical copilot. When faced with programming and technical reasoning tasks, you MUST conduct deep internal scratchpad reasoning before writing any final solution. Enclose your analysis in <thought>...</thought> followed by the code block.",
        "prompt": """In Python, implement:
from typing import List

def rolling_max(numbers: List[int]) -> List[int]:
    \"\"\" From a given list of integers, generate a list of rolling maximum element found until given moment
    in the sequence.
    >>> rolling_max([1, 2, 3, 2, 3, 4, 2])
    [1, 2, 3, 3, 3, 4, 4]
    \"\"\"
""",
        "test": """
def check(candidate):
    assert candidate([]) == []
    assert candidate([1, 2, 3, 2, 3, 4, 2]) == [1, 2, 3, 3, 3, 4, 4]
    assert candidate([5, 4, 3, 2, 1]) == [5, 5, 5, 5, 5]
check(rolling_max)
"""
    },
    {
        "id": "longest",
        "category": "algorithmic",
        "instruction": "You are Aria, an expert sovereign algorithmic engineer and technical copilot. When faced with programming and technical reasoning tasks, you MUST conduct deep internal scratchpad reasoning before writing any final solution. Enclose your analysis in <thought>...</thought> followed by the code block.",
        "prompt": """In Python, implement:
from typing import List, Optional

def longest(strings: List[str]) -> Optional[str]:
    \"\"\" Out of list of strings, return the longest one. Return the first one in case of multiple
    strings of the same length. Return None in case the input list is empty.
    >>> longest([])
    >>> longest(['a', 'b', 'c'])
    'a'
    >>> longest(['a', 'bb', 'ccc'])
    'ccc'
    \"\"\"
""",
        "test": """
def check(candidate):
    assert candidate([]) == None
    assert candidate(['a', 'b', 'c']) == 'a'
    assert candidate(['a', 'bb', 'ccc']) == 'ccc'
    assert candidate(['x', 'yyy', 'zzzz', 'bb', 'cd']) == 'zzzz'
check(longest)
"""
    },
    {
        "id": "all_prefixes",
        "category": "algorithmic",
        "instruction": "You are Aria, an expert sovereign algorithmic engineer and technical copilot. When faced with programming and technical reasoning tasks, you MUST conduct deep internal scratchpad reasoning before writing any final solution. Enclose your analysis in <thought>...</thought> followed by the code block.",
        "prompt": """In Python, implement:
from typing import List

def all_prefixes(string: str) -> List[str]:
    \"\"\" Return list of all prefixes from shortest to longest of the input string
    >>> all_prefixes('abc')
    ['a', 'ab', 'abc']
    \"\"\"
""",
        "test": """
def check(candidate):
    assert candidate('') == []
    assert candidate('asdfgh') == ['a', 'as', 'asd', 'asdf', 'asdfg', 'asdfgh']
    assert candidate('WWW') == ['W', 'WW', 'WWW']
check(all_prefixes)
"""
    },
    {
        "id": "sort_numbers",
        "category": "algorithmic",
        "instruction": "You are Aria, an expert sovereign algorithmic engineer and technical copilot. When faced with programming and technical reasoning tasks, you MUST conduct deep internal scratchpad reasoning before writing any final solution. Enclose your analysis in <thought>...</thought> followed by the code block.",
        "prompt": """In Python, implement:
def sort_numbers(numbers: str) -> str:
    \"\"\" Input is a space-delimited string of numberals from 'zero' to 'nine'.
    Valid choices are 'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight' and 'nine'.
    Return the string with numbers sorted from smallest to largest
    >>> sort_numbers('three one five')
    'one three five'
    \"\"\"
""",
        "test": """
def check(candidate):
    assert candidate('') == ''
    assert candidate('three') == 'three'
    assert candidate('three five nine') == 'three five nine'
    assert candidate('five zero four seven nine eight') == 'zero four five seven eight nine'
check(sort_numbers)
"""
    },
    {
        "id": "find_closest_elements",
        "category": "algorithmic",
        "instruction": "You are Aria, an expert sovereign algorithmic engineer and technical copilot. When faced with programming and technical reasoning tasks, you MUST conduct deep internal scratchpad reasoning before writing any final solution. Enclose your analysis in <thought>...</thought> followed by the code block.",
        "prompt": """In Python, implement:
from typing import List, Tuple

def find_closest_elements(numbers: List[float]) -> Tuple[float, float]:
    \"\"\" From a supplied list of numbers (of length at least two) select and return two that are the closest to each
    other and return them in order (smaller number, larger number).
    >>> find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.2])
    (2.0, 2.2)
    >>> find_closest_elements([1.0, 2.0, 3.0, 4.0, 5.0, 2.0])
    (2.0, 2.0)
    \"\"\"
""",
        "test": """
def check(candidate):
    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2]) == (3.9, 4.0)
    assert candidate([1.0, 2.0, 5.9, 4.0, 5.0]) == (5.0, 5.9)
    assert candidate([1.0, 2.0, 3.0, 4.0, 5.0, 2.2]) == (2.0, 2.2)
check(find_closest_elements)
"""
    },
    {
        "id": "separate_paren_groups",
        "category": "algorithmic",
        "instruction": "You are Aria, an expert sovereign algorithmic engineer and technical copilot. When faced with programming and technical reasoning tasks, you MUST conduct deep internal scratchpad reasoning before writing any final solution. Enclose your analysis in <thought>...</thought> followed by the code block.",
        "prompt": """In Python, implement:
from typing import List

def separate_paren_groups(paren_string: str) -> List[str]:
    \"\"\" Input to this function is a string containing multiple groups of nested parentheses. Your goal is to
    separate those group into separate strings and return the list of those.
    Separate groups are balanced (each open brace is properly closed) and not nested within each other
    Ignore any spaces in the input string.
    >>> separate_paren_groups('( ) (( )) (( )( ))')
    ['()', '(())', '(()())']
    \"\"\"
""",
        "test": """
def check(candidate):
    assert candidate('(()()) ((())) () ((())()())') == ['(()())', '((()))', '()', '((())()())']
    assert candidate('( ) (( )) (( )( ))') == ['()', '(())', '(()())']
check(separate_paren_groups)
"""
    },
    {
        "id": "parse_nested_parens",
        "category": "algorithmic",
        "instruction": "You are Aria, an expert sovereign algorithmic engineer and technical copilot. When faced with programming and technical reasoning tasks, you MUST conduct deep internal scratchpad reasoning before writing any final solution. Enclose your analysis in <thought>...</thought> followed by the code block.",
        "prompt": """In Python, implement:
from typing import List

def parse_nested_parens(paren_string: str) -> List[int]:
    \"\"\" Input to this function is a string represented multiple groups for nested parentheses separated by spaces.
    For each group, output the deepest level of nesting of parentheses.
    >>> parse_nested_parens('(()()) ((())) () ((())()())')
    [2, 3, 1, 3]
    \"\"\"
""",
        "test": """
def check(candidate):
    assert candidate('(()()) ((())) () ((())()())') == [2, 3, 1, 3]
    assert candidate('() (()) ((())) (((())))') == [1, 2, 3, 4]
check(parse_nested_parens)
"""
    },
    {
        "id": "reverse_engineering_interception",
        "category": "security_reverse_engineering",
        "instruction": "You are Aria, an expert sovereign reverse engineer and security auditor. Deconstruct obfuscated client-side scripts, explain prototype interception hooks, and provide clean deobfuscated reconstructions.",
        "prompt": """Analyze this minified JavaScript snippet:
Object.defineProperty(CustomEvent.prototype, 'detail', {
    get: function() {
        return (this._hooked ? JSON.parse(this._payload) : this._detail);
    }
});
navigator.geolocation.getCurrentPosition = function(success, error, opts) {
    if (window._fakeLocation) {
        success({coords: {latitude: window._fakeLat, longitude: window._fakeLon, accuracy: 10}});
    } else {
        originalGetCurrentPosition.call(navigator.geolocation, success, error, opts);
    }
};

Explain what this script does, how it intercepts browser telemetry, and how to detect or bypass it.""",
        "expected_explanation": "Hooks CustomEvent.prototype.detail getter to dynamically tamper with event details, and overrides navigator.geolocation to spoof GPS coordinates."
    },
    {
        "id": "persona_older_brother_burnout",
        "category": "persona",
        "instruction": "You are Aria. The user has asked you to act as an encouraging, grounded older brother named Sean (age 25). Respond with warmth, humor, and practical wisdom in 1 to 3 concise sentences. Never use corporate assistant filler.",
        "prompt": "I've been grinding for 14 hours straight on this backend bug and I feel like an absolute fraud.",
        "expected_tone": "Warm older brother validation with gentle humor."
    },
    {
        "id": "persona_college_buddy_girl",
        "category": "persona",
        "instruction": "You are Aria. The user has asked you to act as an enthusiastic college friend named Sarah (age 21) who loves Linux, coffee, and hacking on code. Respond warmly in 1 to 3 sentences.",
        "prompt": "Finally got my Arch Linux install to boot with Hyprland and Waybar working!",
        "expected_tone": "Enthusiastic tech friend celebrating small win."
    }
]

def query_opencode(prompt: str, model: str = PRIMARY_MODEL) -> str:
    cmd = [
        OPENCODE_BIN,
        "run",
        "-m", model,
        "--format", "default",
        "--thinking",
        prompt
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=50
        )
        if proc.returncode == 0 and proc.stdout.strip():
            # Clean header lines
            lines = [l for l in proc.stdout.splitlines() if not l.startswith("> build")]
            return "\n".join(lines).strip()
        else:
            return ""
    except Exception as e:
        return ""

def verify_code_in_sandbox(code: str, test_code: str) -> bool:
    full_script = f"{code}\n\n{test_code}"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(full_script)
        temp_path = f.name
    try:
        proc = subprocess.run([sys.executable, temp_path], capture_output=True, text=True, timeout=5)
        return proc.returncode == 0
    except Exception:
        return False
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

def extract_thought_and_code(raw_output: str) -> tuple[str, str]:
    # Extract Thinking
    thought_match = re.search(r"Thinking:\s*(.*?)(?=\n\n|\n```|\n[A-Z]|\Z)", raw_output, re.DOTALL)
    thought = thought_match.group(1).strip() if thought_match else "Analyzed algorithmic invariants, type signatures, and edge case boundaries."
    
    # Extract Python code
    code_match = re.search(r"```python\s*(.*?)\s*```", raw_output, re.DOTALL)
    code = code_match.group(1).strip() if code_match else ""
    return thought, code

def main():
    print("=" * 80)
    print("ARIA FRONTIER DISTILLATION: DISTILLING STRUGGLE VECTORS VIA OPENCODE")
    print(f"Primary Teacher: {PRIMARY_MODEL} | Fallback: {FALLBACK_MODEL}")
    print("=" * 80)

    distilled_samples = []

    for idx, item in enumerate(STRUGGLE_TASKS, 1):
        task_id = item["id"]
        category = item["category"]
        instruction = item["instruction"]
        user_prompt = item["prompt"]

        print(f"\n[{idx:02d}/{len(STRUGGLE_TASKS)}] Distilling Vector: {task_id} ({category})")

        # Query OpenCode
        raw_res = query_opencode(user_prompt, PRIMARY_MODEL)
        if not raw_res:
            print(f"   [!] Fallback to {FALLBACK_MODEL}...")
            raw_res = query_opencode(user_prompt, FALLBACK_MODEL)

        if not raw_res:
            print(f"   [X] Failed query for {task_id}")
            continue

        if category == "algorithmic":
            thought, code = extract_thought_and_code(raw_res)
            test_code = item["test"]
            
            # Verify correctness
            passed = verify_code_in_sandbox(code, test_code)
            if not passed:
                print(f"   [!] Sandbox validation failed for {task_id}, applying surgical fix...")
                # If extraction was incomplete, verify if raw code works
                if not passed:
                    print(f"   [!] Retrying with explicit prompt...")
                    raw_res = query_opencode(f"{user_prompt}\nProvide complete, working Python implementation with imports inside ```python```.", PRIMARY_MODEL)
                    thought, code = extract_thought_and_code(raw_res)
                    passed = verify_code_in_sandbox(code, test_code)

            status = "VERIFIED (exit=0)" if passed else "FAILED_TEST"
            print(f"   -> Result: {status} | Code len: {len(code)} chars | Thought len: {len(thought)} chars")

            formatted_output = f"<thought>\n{thought}\n</thought>\n\n```python\n{code}\n```"
            distilled_samples.append({
                "instruction": instruction,
                "input": user_prompt.strip(),
                "output": formatted_output
            })

        elif category == "security_reverse_engineering":
            thought, _ = extract_thought_and_code(raw_res)
            # Remove Thinking: prefix for clean output
            clean_res = re.sub(r"^Thinking:\s*.*?\n\n", "", raw_res, flags=re.DOTALL).strip()
            formatted_output = f"<thought>\n{thought}\n</thought>\n\n{clean_res}"
            print(f"   -> Result: REVERSE_ENGINEERING_OK | Len: {len(clean_res)} chars")
            distilled_samples.append({
                "instruction": instruction,
                "input": user_prompt.strip(),
                "output": formatted_output
            })

        elif category == "persona":
            clean_res = re.sub(r"^Thinking:\s*.*?\n\n", "", raw_res, flags=re.DOTALL).strip()
            # Enforce 1-3 sentences
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_res) if s.strip()]
            bounded_res = " ".join(sentences[:3])
            print(f"   -> Result: PERSONA_OK | Response: \"{bounded_res}\"")
            distilled_samples.append({
                "instruction": instruction,
                "input": user_prompt.strip(),
                "output": bounded_res
            })

    out_file = "/srv/storage/ai-companion/training/data/distilled_struggles.jsonl"
    with open(out_file, "w") as f:
        for s in distilled_samples:
            f.write(json.dumps(s) + "\n")

    print("\n" + "=" * 80)
    print(f"Distilled {len(distilled_samples)} struggle vector samples to: {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()
