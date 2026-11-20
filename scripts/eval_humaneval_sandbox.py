#!/usr/bin/env python3
"""
Standardized HumanEval Verifiable Programming Sandbox
Evaluates Aria (Qwen2.5-3B-Instruct fine-tuned adapter) across 20 standard HumanEval problems.
Judged strictly by isolated subprocess exit codes ($? == 0) and assertion verifications.
Compares:
  Mode A: Direct Code Generation (No Test-Time Reasoning)
  Mode B: Test-Time Reasoning (Think-Then-Act with <thought> Scratchpad)
"""

import os
import sys
import json
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List

# Add parent dir to sys.path for src imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.test_time_reasoning import ThinkThenActEngine


HUMANEVAL_PROBLEMS = [
    {
        "task_id": "HumanEval/0",
        "entry_point": "has_close_elements",
        "prompt": '''from typing import List

def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers closer to each other than
    given threshold.
    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)
    False
    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3)
    True
    """
''',
        "test": '''
def check(candidate):
    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) == True
    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05) == False
    assert candidate([1.0, 2.0, 5.9, 4.0, 5.0], 0.95) == True
    assert candidate([1.0, 2.0, 5.9, 4.0, 5.0], 0.8) == False
    assert candidate([1.0, 2.0, 3.0, 4.0, 5.0, 2.0], 0.1) == True
    assert candidate([1.1, 2.2, 3.1, 4.1, 5.1], 1.0) == True
    assert candidate([1.1, 2.2, 3.1, 4.1, 5.1], 0.5) == False

check(has_close_elements)
'''
    },
    {
        "task_id": "HumanEval/1",
        "entry_point": "separate_paren_groups",
        "prompt": '''from typing import List

def separate_paren_groups(paren_string: str) -> List[str]:
    """ Input to this function is a string containing multiple groups of nested parentheses. Your goal is to
    separate those group into separate strings and return the list of those.
    Separate groups are balanced (each open brace is properly closed) and not nested within each other
    Ignore any spaces in the input string.
    >>> separate_paren_groups('( ) (( )) (( )( ))')
    ['()', '(())', '(()())']
    """
''',
        "test": '''
def check(candidate):
    assert candidate('(()()) ((())) () ((())()())') == ['(()())', '((()))', '()', '((())()())']
    assert candidate('() (()) ((())) (((())))') == ['()', '(())', '((()))', '(((())))']
    assert candidate('(()(())((())))') == ['(()(())((())))']
    assert candidate('( ) (( )) (( )( ))') == ['()', '(())', '(()())']

check(separate_paren_groups)
'''
    },
    {
        "task_id": "HumanEval/2",
        "entry_point": "truncate_number",
        "prompt": '''def truncate_number(number: float) -> float:
    """ Given a positive floating point number, it can be decomposed into
    and integer part (largest integer smaller than given number) and decimals
    (leftover part always smaller than 1, also known as fractional part).

    Return the decimal part of the number.
    >>> truncate_number(3.5)
    0.5
    """
''',
        "test": '''
def check(candidate):
    assert abs(candidate(3.5) - 0.5) < 1e-4
    assert abs(candidate(1.33) - 0.33) < 1e-4
    assert abs(candidate(123.456) - 0.456) < 1e-4

check(truncate_number)
'''
    },
    {
        "task_id": "HumanEval/3",
        "entry_point": "below_zero",
        "prompt": '''from typing import List

def below_zero(operations: List[int]) -> bool:
    """ You're given a list of deposit and withdrawal operations on a bank account that starts with
    zero balance. Your task is to detect if at any point the balance of account fallls below zero, and
    at that point function should return True. Otherwise it should return False.
    >>> below_zero([1, 2, 3])
    False
    >>> below_zero([1, 2, -4, 5])
    True
    """
''',
        "test": '''
def check(candidate):
    assert candidate([]) == False
    assert candidate([1, 2, -3, 1, 2, -3]) == False
    assert candidate([1, 2, -4, 5, 6]) == True
    assert candidate([1, -1, 2, -2, 5, -5, 4, -4]) == False
    assert candidate([1, -1, 2, -2, 5, -5, 4, -5]) == True
    assert candidate([1, -2, 2, -2, 5, -5, 4, -4]) == True

check(below_zero)
'''
    },
    {
        "task_id": "HumanEval/4",
        "entry_point": "mean_absolute_deviation",
        "prompt": '''from typing import List

def mean_absolute_deviation(numbers: List[float]) -> float:
    """ For a given list of input numbers, calculate Mean Absolute Deviation
    around the mean of this dataset.
    Mean Absolute Deviation is the average absolute difference between each
    element and a centerpoint (mean in this case):
    MAD = average |x - x_mean|
    >>> mean_absolute_deviation([1.0, 2.0, 3.0, 4.0])
    1.0
    """
''',
        "test": '''
def check(candidate):
    assert abs(candidate([1.0, 2.0, 3.0]) - 2.0/3.0) < 1e-4
    assert abs(candidate([1.0, 2.0, 3.0, 4.0]) - 1.0) < 1e-4
    assert abs(candidate([1.0, 2.0, 3.0, 4.0, 5.0]) - 6.0/5.0) < 1e-4

check(mean_absolute_deviation)
'''
    },
    {
        "task_id": "HumanEval/5",
        "entry_point": "intersperse",
        "prompt": '''from typing import List

def intersperse(numbers: List[int], delimeter: int) -> List[int]:
    """ Insert a number 'delimeter' between every two consecutive elements of input list `numbers'
    >>> intersperse([], 4)
    []
    >>> intersperse([1, 2, 3], 4)
    [1, 4, 2, 4, 3]
    """
''',
        "test": '''
def check(candidate):
    assert candidate([], 7) == []
    assert candidate([5, 6, 3, 2], 8) == [5, 8, 6, 8, 3, 8, 2]
    assert candidate([2, 2, 2], 2) == [2, 2, 2, 2, 2]

check(intersperse)
'''
    },
    {
        "task_id": "HumanEval/6",
        "entry_point": "parse_nested_parens",
        "prompt": '''from typing import List

def parse_nested_parens(paren_string: str) -> List[int]:
    """ Input to this function is a string represented multiple groups for nested parentheses separated by spaces.
    For each group, output the deepest level of nesting of parentheses.
    E.g. (()()) has maximum two levels of nesting while ((())) has three.

    >>> parse_nested_parens('(()()) ((())) () ((())()())')
    [2, 3, 1, 3]
    """
''',
        "test": '''
def check(candidate):
    assert candidate('(()()) ((())) () ((())()())') == [2, 3, 1, 3]
    assert candidate('() (()) ((())) (((())))') == [1, 2, 3, 4]
    assert candidate('(()(())((())))') == [4]

check(parse_nested_parens)
'''
    },
    {
        "task_id": "HumanEval/7",
        "entry_point": "filter_by_substring",
        "prompt": '''from typing import List

def filter_by_substring(strings: List[str], substring: str) -> List[str]:
    """ Filter an input list of strings only for ones that contain given substring
    >>> filter_by_substring([], 'a')
    []
    >>> filter_by_substring(['abc', 'bacd', 'cde', 'array'], 'a')
    ['abc', 'bacd', 'array']
    """
''',
        "test": '''
def check(candidate):
    assert candidate([], 'john') == []
    assert candidate(['xxx', 'asd', 'xxy', 'john doe', 'xxxAAA', 'xxx'], 'xxx') == ['xxx', 'xxy', 'xxxAAA', 'xxx']
    assert candidate(['grunt', 'trumpet', 'prune', 'gruff'], 'run') == ['grunt', 'prune']

check(filter_by_substring)
'''
    },
    {
        "task_id": "HumanEval/8",
        "entry_point": "sum_product",
        "prompt": '''from typing import List, Tuple

def sum_product(numbers: List[int]) -> Tuple[int, int]:
    """ For a given list of integers, return a tuple consisting of a sum and a product of all the integers in a list.
    Empty sum should be equal to 0 and empty product should be equal to 1.
    >>> sum_product([])
    (0, 1)
    >>> sum_product([1, 2, 3, 4])
    (10, 24)
    """
''',
        "test": '''
def check(candidate):
    assert candidate([]) == (0, 1)
    assert candidate([1, 1, 1]) == (3, 1)
    assert candidate([100, 0]) == (100, 0)
    assert candidate([3, 5, 7]) == (3 + 5 + 7, 3 * 5 * 7)
    assert candidate([10]) == (10, 10)

check(sum_product)
'''
    },
    {
        "task_id": "HumanEval/9",
        "entry_point": "rolling_max",
        "prompt": '''from typing import List

def rolling_max(numbers: List[int]) -> List[int]:
    """ From a given list of integers, generate a list of rolling maximum element found until given moment
    in the sequence.
    >>> rolling_max([1, 2, 3, 2, 3, 4, 2])
    [1, 2, 3, 3, 3, 4, 4]
    """
''',
        "test": '''
def check(candidate):
    assert candidate([]) == []
    assert candidate([1, 2, 3, 4]) == [1, 2, 3, 4]
    assert candidate([4, 3, 2, 1]) == [4, 4, 4, 4]
    assert candidate([3, 2, 3, 100, 3]) == [3, 3, 3, 100, 100]

check(rolling_max)
'''
    },
    {
        "task_id": "HumanEval/10",
        "entry_point": "make_palindrome",
        "prompt": '''def is_palindrome(string: str) -> bool:
    """ Test if given string is a palindrome """
    return string == string[::-1]

def make_palindrome(string: str) -> str:
    """ Find the shortest palindrome that begins with a supplied string.
    Algorithm idea is simple:
    - Find the longest postfix of supplied string that is a palindrome.
    - Append to the end of the string reverse of a prefix that comes before the palindromic postfix.
    >>> make_palindrome('')
    ''
    >>> make_palindrome('cat')
    'catac'
    >>> make_palindrome('cata')
    'catac'
    """
''',
        "test": '''
def check(candidate):
    assert candidate('') == ''
    assert candidate('x') == 'x'
    assert candidate('xyz') == 'xyzyx'
    assert candidate('xyx') == 'xyx'
    assert candidate('jerry') == 'jerryrrej'

check(make_palindrome)
'''
    },
    {
        "task_id": "HumanEval/11",
        "entry_point": "string_xor",
        "prompt": '''def string_xor(a: str, b: str) -> str:
    """ Input are two strings a and b consisting only of 1s and 0s.
    Perform binary XOR on these inputs and return result also as a string.
    >>> string_xor('010', '110')
    '100'
    """
''',
        "test": '''
def check(candidate):
    assert candidate('111000', '101010') == '010010'
    assert candidate('1', '1') == '0'
    assert candidate('0101', '0000') == '0101'

check(string_xor)
'''
    },
    {
        "task_id": "HumanEval/12",
        "entry_point": "longest",
        "prompt": '''from typing import List, Optional

def longest(strings: List[str]) -> Optional[str]:
    """ Out of list of strings, return the longest one. Return the first one in case of multiple
    strings of the same length. Return None in case the input list is empty.
    >>> longest([])
    None
    >>> longest(['a', 'b', 'c'])
    'a'
    >>> longest(['a', 'bb', 'ccc'])
    'ccc'
    """
''',
        "test": '''
def check(candidate):
    assert candidate([]) == None
    assert candidate(['x', 'y', 'z']) == 'x'
    assert candidate(['x', 'yyy', 'zzzz', 'www', 'kkkk', 'abc']) == 'zzzz'

check(longest)
'''
    },
    {
        "task_id": "HumanEval/13",
        "entry_point": "greatest_common_divisor",
        "prompt": '''def greatest_common_divisor(a: int, b: int) -> int:
    """ Return a greatest common divisor of two integers a and b
    >>> greatest_common_divisor(3, 5)
    1
    >>> greatest_common_divisor(25, 15)
    5
    """
''',
        "test": '''
def check(candidate):
    assert candidate(3, 7) == 1
    assert candidate(10, 15) == 5
    assert candidate(49, 14) == 7
    assert candidate(144, 60) == 12

check(greatest_common_divisor)
'''
    },
    {
        "task_id": "HumanEval/14",
        "entry_point": "all_prefixes",
        "prompt": '''from typing import List

def all_prefixes(string: str) -> List[str]:
    """ Return list of all prefixes from shortest to longest of the input string
    >>> all_prefixes('abc')
    ['a', 'ab', 'abc']
    """
''',
        "test": '''
def check(candidate):
    assert candidate('') == []
    assert candidate('asdfgh') == ['a', 'as', 'asd', 'asdf', 'asdfg', 'asdfgh']
    assert candidate('WWW') == ['W', 'WW', 'WWW']

check(all_prefixes)
'''
    },
    {
        "task_id": "HumanEval/15",
        "entry_point": "string_sequence",
        "prompt": '''def string_sequence(n: int) -> str:
    """ Return a string containing space-delimited numbers starting from 0 upto n inclusive.
    >>> string_sequence(0)
    '0'
    >>> string_sequence(5)
    '0 1 2 3 4 5'
    """
''',
        "test": '''
def check(candidate):
    assert candidate(0) == '0'
    assert candidate(3) == '0 1 2 3'
    assert candidate(10) == '0 1 2 3 4 5 6 7 8 9 10'

check(string_sequence)
'''
    },
    {
        "task_id": "HumanEval/16",
        "entry_point": "count_distinct_characters",
        "prompt": '''def count_distinct_characters(string: str) -> int:
    """ Given a string, find out how many distinct characters (regardless of case) does it consist of
    >>> count_distinct_characters('xyzXYZ')
    3
    >>> count_distinct_characters('Jerry')
    4
    """
''',
        "test": '''
def check(candidate):
    assert candidate('') == 0
    assert candidate('abcde') == 5
    assert candidate('abcde' + 'cade' + 'CADE') == 5
    assert candidate('aaaaAAAAaaaa') == 1
    assert candidate('Jerry jERRY JeRrY') == 5

check(count_distinct_characters)
'''
    },
    {
        "task_id": "HumanEval/17",
        "entry_point": "parse_music",
        "prompt": '''from typing import List

def parse_music(music_string: str) -> List[int]:
    """ Input to this function is a string representing musical notes in a special ASCII format.
    Your task is to parse this string and return list of integers corresponding to how many beats does each
    not last.

    Here is a legend:
    'o' - whole note, lasts four beats
    'o|' - half note, lasts two beats
    '.|' - quater note, lasts one beat

    >>> parse_music('o o| .| o| o| .| .| .| .| o o')
    [4, 2, 1, 2, 2, 1, 1, 1, 1, 4, 4]
    """
''',
        "test": '''
def check(candidate):
    assert candidate('') == []
    assert candidate('o o o o') == [4, 4, 4, 4]
    assert candidate('.| .| .| .|') == [1, 1, 1, 1]
    assert candidate('o| o| .| .| o o o|') == [2, 2, 1, 1, 4, 4, 2]
    assert candidate('o| .| o| .| o o| o o|') == [2, 1, 2, 1, 4, 2, 4, 2]

check(parse_music)
'''
    },
    {
        "task_id": "HumanEval/18",
        "entry_point": "how_many_times",
        "prompt": '''def how_many_times(string: str, substring: str) -> int:
    """ Find how many times a given substring can be found in the original string. Count overlaping cases.
    >>> how_many_times('', 'a')
    0
    >>> how_many_times('aaa', 'a')
    3
    >>> how_many_times('aaaa', 'aa')
    3
    """
''',
        "test": '''
def check(candidate):
    assert candidate('', 'x') == 0
    assert candidate('xyxyxyx', 'x') == 4
    assert candidate('cacacacac', 'cac') == 4
    assert candidate('john doe', 'john') == 1

check(how_many_times)
'''
    },
    {
        "task_id": "HumanEval/19",
        "entry_point": "sort_numbers",
        "prompt": '''def sort_numbers(numbers: str) -> str:
    """ Input is a space-delimited string of numberals from 'zero' to 'nine'.
    Valid choices are 'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight' and 'nine'.
    Return the string with numbers sorted from smallest to largest
    >>> sort_numbers('three one five')
    'one three five'
    """
''',
        "test": '''
def check(candidate):
    assert candidate('') == ''
    assert candidate('three') == 'three'
    assert candidate('three five nine') == 'three five nine'
    assert candidate('five zero four seven nine eight') == 'zero four five seven eight nine'
    assert candidate('six five four three two one zero') == 'zero one two three four five six'

check(sort_numbers)
'''
    }
]


def query_ollama(messages: List[Dict[str, str]], options: Dict[str, Any], model: str = "aria:3b") -> Dict[str, Any]:
    import urllib.request
    url = "http://127.0.0.1:11434/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "options": options,
        "stream": False
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as resp:
        res = json.loads(resp.read().decode("utf-8"))
    elapsed_ms = (time.time() - t0) * 1000.0
    return {
        "content": res.get("message", {}).get("content", ""),
        "eval_count": res.get("eval_count", 0),
        "prompt_eval_count": res.get("prompt_eval_count", 0),
        "latency_ms": elapsed_ms
    }


def execute_in_sandbox(code: str, test_suite: str, timeout_sec: float = 3.0) -> Dict[str, Any]:
    """
    Executes generated code + test suite in an isolated subprocess sandbox.
    Judged strictly by exit code $? == 0 and assertion passes.
    Conforms to standard HumanEval execution harness by providing standard typing symbols.
    """
    standard_prelude = (
        "from typing import List, Tuple, Optional, Dict, Any, Union, Set\n"
        "import math\n"
        "import re\n\n"
    )
    full_script = f"{standard_prelude}{code}\n\n{test_suite}\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
        tf_name = tf.name
        tf.write(full_script)

    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, tf_name],
            capture_output=True,
            text=True,
            timeout=timeout_sec
        )
        sandbox_ms = (time.time() - t0) * 1000.0
        passed = (proc.returncode == 0)
        return {
            "passed": passed,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "sandbox_ms": sandbox_ms,
            "error_type": "None" if passed else ("AssertionError" if "AssertionError" in proc.stderr else "RuntimeError")
        }
    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "returncode": -1,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout_sec}s",
            "sandbox_ms": timeout_sec * 1000.0,
            "error_type": "Timeout"
        }
    finally:
        try:
            os.remove(tf_name)
        except OSError:
            pass


def run_benchmark(output_dir: str = "data", model: str = "aria:3b"):
    engine = ThinkThenActEngine(thinking_token_budget=512, code_token_budget=400)
    
    print("=" * 90)
    print("ARIA STANDARDIZED PROGRAMMING BENCHMARK HARNESS (HumanEval Subset N=20)")
    print(f"Target Model: {model} on Ollama (Local NVMe/GPU)")
    print("Validation Criteria: Strict isolated execution sandbox, exit code $? == 0, unit assertions")
    print("Comparing: Direct Generation vs Think-Then-Act Test-Time Reasoning")
    print("=" * 90)

    results_direct = []
    results_reasoning = []

    print("\n--- PHASE 1: DIRECT CODE GENERATION (Zero Test-Time Reasoning) ---")
    for i, p in enumerate(HUMANEVAL_PROBLEMS):
        task_id = p["task_id"]
        messages = engine.format_prompt(p["prompt"], with_reasoning=False)
        options = engine.get_generation_options(with_reasoning=False)
        
        gen_res = query_ollama(messages, options, model=model)
        parsed = engine.parse_response(gen_res["content"])
        
        exec_res = execute_in_sandbox(parsed["clean_code"], p["test"])
        
        outcome = "PASS" if exec_res["passed"] else "FAIL"
        print(f"[{i+1:02d}/20] {task_id:<14} -> {outcome:<5} (exit={exec_res['returncode']}, gen={gen_res['latency_ms']:.0f}ms, eval_tok={gen_res['eval_count']})")
        if not exec_res["passed"]:
            first_err = exec_res["stderr"].splitlines()[-1] if exec_res["stderr"] else "Non-zero exit"
            print(f"       Err: {first_err[:80]}")

        results_direct.append({
            "task_id": task_id,
            "mode": "direct",
            "passed": exec_res["passed"],
            "returncode": exec_res["returncode"],
            "latency_ms": gen_res["latency_ms"],
            "eval_count": gen_res["eval_count"],
            "stderr": exec_res["stderr"],
            "code": parsed["clean_code"]
        })

    print("\n--- PHASE 2: THINK-THEN-ACT TEST-TIME REASONING (<thought> Scratchpad) ---")
    for i, p in enumerate(HUMANEVAL_PROBLEMS):
        task_id = p["task_id"]
        messages = engine.format_prompt(p["prompt"], with_reasoning=True)
        options = engine.get_generation_options(with_reasoning=True)
        
        gen_res = query_ollama(messages, options, model=model)
        parsed = engine.parse_response(gen_res["content"])
        
        exec_res = execute_in_sandbox(parsed["clean_code"], p["test"])
        
        outcome = "PASS" if exec_res["passed"] else "FAIL"
        thought_status = f"thought={parsed['scratchpad_tokens_est']}tok" if parsed["has_scratchpad"] else "no_scratchpad"
        print(f"[{i+1:02d}/20] {task_id:<14} -> {outcome:<5} (exit={exec_res['returncode']}, gen={gen_res['latency_ms']:.0f}ms, {thought_status})")
        if not exec_res["passed"]:
            first_err = exec_res["stderr"].splitlines()[-1] if exec_res["stderr"] else "Non-zero exit"
            print(f"       Err: {first_err[:80]}")

        results_reasoning.append({
            "task_id": task_id,
            "mode": "think_then_act",
            "passed": exec_res["passed"],
            "returncode": exec_res["returncode"],
            "has_scratchpad": parsed["has_scratchpad"],
            "scratchpad_tokens_est": parsed["scratchpad_tokens_est"],
            "latency_ms": gen_res["latency_ms"],
            "eval_count": gen_res["eval_count"],
            "stderr": exec_res["stderr"],
            "code": parsed["clean_code"],
            "scratchpad": parsed["scratchpad"]
        })

    # Summary Metrics
    pass_direct = sum(1 for r in results_direct if r["passed"])
    pass_reasoning = sum(1 for r in results_reasoning if r["passed"])
    n = len(HUMANEVAL_PROBLEMS)
    
    rate_direct = (pass_direct / n) * 100.0
    rate_reasoning = (pass_reasoning / n) * 100.0
    delta = rate_reasoning - rate_direct

    print("\n" + "=" * 90)
    print("EMPIRICAL BENCHMARK RESULTS & TEST-TIME REASONING DELTA:")
    print(f"  Total Problems Evaluated:           {n}")
    print(f"  Mode A (Direct Generation) Pass@1:   {pass_direct}/{n} ({rate_direct:.1f}%)")
    print(f"  Mode B (Think-Then-Act) Pass@1:      {pass_reasoning}/{n} ({rate_reasoning:.1f}%)")
    print(f"  Delta Accuracy (Gain):              +{delta:+.1f}%")
    print(f"  Mean Latency (Direct):              {sum(r['latency_ms'] for r in results_direct)/n:.1f} ms")
    print(f"  Mean Latency (Think-Then-Act):      {sum(r['latency_ms'] for r in results_reasoning)/n:.1f} ms")
    print(f"  Mean Reasoning Tokens:              {sum(r['scratchpad_tokens_est'] for r in results_reasoning)/n:.1f} tokens")
    print("=" * 90)

    out_path = Path(output_dir) / "humaneval_reasoning_benchmark.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            "benchmark": "HumanEval_20_Subset",
            "model": model,
            "metrics": {
                "total_problems": n,
                "direct_passed": pass_direct,
                "direct_pass_rate_pct": rate_direct,
                "reasoning_passed": pass_reasoning,
                "reasoning_pass_rate_pct": rate_reasoning,
                "delta_pass_rate_pct": delta,
                "direct_mean_latency_ms": sum(r['latency_ms'] for r in results_direct)/n,
                "reasoning_mean_latency_ms": sum(r['latency_ms'] for r in results_reasoning)/n,
                "mean_scratchpad_tokens": sum(r['scratchpad_tokens_est'] for r in results_reasoning)/n,
            },
            "results_direct": results_direct,
            "results_reasoning": results_reasoning
        }, f, indent=2)
    print(f"Saved complete benchmark execution traces to: {out_path}")


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "/srv/storage/ai-companion/data"
    run_benchmark(out_dir)
