#!/usr/bin/env python3
"""
HumanEval-Fix Comparative Debugging Benchmark
Evaluates Aria (3B parameter model on edge GPU) across 20 real-world debugging tasks.
Compares:
  Condition A: Single-Shot Generation (Zero Execution Feedback)
  Condition B: Sandbox-Grounded Backtracking & Execution-Guided Self-Repair (Reflexion Loop)
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.self_repair import ExecutionGuidedRepairEngine

HUMANEVAL_FIX_20 = [
    {
        "task_id": "Fix/0_has_close_elements",
        "entry_point": "has_close_elements",
        "prompt": '''from typing import List

# BUGGY IMPLEMENTATION: Inverted threshold comparison
def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers closer to each other than
    given threshold.
    """
    for i in range(len(numbers)):
        for j in range(i + 1, len(numbers)):
            # BUG: inverted check (>= instead of <)
            if abs(numbers[i] - numbers[j]) >= threshold:
                return True
    return False

# TASK: Fix the bug in has_close_elements so it passes all unit test assertions.
''',
        "test": '''
def check(candidate):
    assert candidate([1.0, 2.0, 3.0], 0.5) == False
    assert candidate([1.0, 2.8, 3.0, 4.0, 5.0, 2.0], 0.3) == True
    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) == True
    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05) == False

check(has_close_elements)
'''
    },
    {
        "task_id": "Fix/1_truncate_number",
        "entry_point": "truncate_number",
        "prompt": '''# BUGGY IMPLEMENTATION: Returns integer part instead of fractional part
def truncate_number(number: float) -> float:
    """ Given a positive floating point number, return the decimal part.
    >>> truncate_number(3.5)
    0.5
    """
    # BUG: returns int(number) instead of number % 1.0 or number - int(number)
    return float(int(number))

# TASK: Fix the bug in truncate_number so it returns the decimal fraction.
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
        "task_id": "Fix/2_below_zero",
        "entry_point": "below_zero",
        "prompt": '''from typing import List

# BUGGY IMPLEMENTATION: Returns True immediately on positive balance
def below_zero(operations: List[int]) -> bool:
    """ Detects if balance ever falls below zero. """
    balance = 0
    for op in operations:
        balance += op
        # BUG: checking > 0 instead of < 0
        if balance > 0:
            return True
    return False

# TASK: Fix below_zero so it accurately detects if balance ever goes below zero.
''',
        "test": '''
def check(candidate):
    assert candidate([1, 2, 3]) == False
    assert candidate([1, 2, -4, 5]) == True
    assert candidate([1, -1, 2, -2, 5, -5, 4, -4]) == False
    assert candidate([1, -1, 2, -2, 5, -5, 4, -5]) == True
    assert candidate([1, -2, 2, -2, 5, -5, 4, -4]) == True

check(below_zero)
'''
    },
    {
        "task_id": "Fix/3_mean_absolute_deviation",
        "entry_point": "mean_absolute_deviation",
        "prompt": '''from typing import List

# BUGGY IMPLEMENTATION: Divides by len(numbers)-1 instead of len(numbers)
def mean_absolute_deviation(numbers: List[float]) -> float:
    """ Calculate Mean Absolute Deviation around the mean. """
    mean = sum(numbers) / len(numbers)
    # BUG: off-by-one in divisor len(numbers) - 1
    return sum(abs(x - mean) for x in numbers) / (len(numbers) - 1)

# TASK: Fix mean_absolute_deviation to divide by len(numbers).
''',
        "test": '''
def check(candidate):
    assert abs(candidate([1.0, 2.0, 3.0, 4.0]) - 1.0) < 1e-4
    assert abs(candidate([1.0, 2.0, 3.0, 4.0, 5.0]) - 1.2) < 1e-4

check(mean_absolute_deviation)
'''
    },
    {
        "task_id": "Fix/4_intersperse",
        "entry_point": "intersperse",
        "prompt": '''from typing import List

# BUGGY IMPLEMENTATION: Adds trailing delimiter at the end
def intersperse(numbers: List[int], delimeter: int) -> List[int]:
    """ Insert a number 'delimeter' between every two consecutive elements of input list. """
    result = []
    for n in numbers:
        result.append(n)
        result.append(delimeter)
    # BUG: trailing delimiter is left attached
    return result

# TASK: Fix intersperse so no trailing delimiter is appended, and handles empty list.
''',
        "test": '''
def check(candidate):
    assert candidate([], 4) == []
    assert candidate([1, 2, 3], 4) == [1, 4, 2, 4, 3]
    assert candidate([5, 6, 3, 2], 8) == [5, 8, 6, 8, 3, 8, 2]

check(intersperse)
'''
    },
    {
        "task_id": "Fix/5_sum_product",
        "entry_point": "sum_product",
        "prompt": '''from typing import List, Tuple

# BUGGY IMPLEMENTATION: Product accumulator initialized to 0 instead of 1
def sum_product(numbers: List[int]) -> Tuple[int, int]:
    """ For a given list of integers, return a tuple consisting of a sum and a product of all the integers in a list.
    Empty sum should be equal to 0 and empty product should be equal to 1.
    """
    sum_val = 0
    # BUG: product initialized to 0 makes all products 0
    prod_val = 0
    for n in numbers:
        sum_val += n
        prod_val *= n
    return sum_val, prod_val

# TASK: Fix sum_product so the product accumulator is 1.
''',
        "test": '''
def check(candidate):
    assert candidate([]) == (0, 1)
    assert candidate([1, 2, 3, 4]) == (10, 24)
    assert candidate([2, 5, 7]) == (14, 70)

check(sum_product)
'''
    },
    {
        "task_id": "Fix/6_rolling_max",
        "entry_point": "rolling_max",
        "prompt": '''from typing import List

# BUGGY IMPLEMENTATION: Crashes on empty list due to numbers[0] indexing
def rolling_max(numbers: List[int]) -> List[int]:
    """ From a given list of integers, generate a list of rolling maximum element found until given moment. """
    # BUG: IndexError when numbers is []
    cur_max = numbers[0]
    res = []
    for n in numbers:
        if n > cur_max:
            cur_max = n
        res.append(cur_max)
    return res

# TASK: Fix rolling_max to safely handle empty list.
''',
        "test": '''
def check(candidate):
    assert candidate([]) == []
    assert candidate([1, 2, 3, 2, 3, 4, 2]) == [1, 2, 3, 3, 3, 4, 4]
    assert candidate([1, 2, 3, 4]) == [1, 2, 3, 4]
    assert candidate([4, 3, 2, 1]) == [4, 4, 4, 4]

check(rolling_max)
'''
    },
    {
        "task_id": "Fix/7_string_xor",
        "entry_point": "string_xor",
        "prompt": '''# BUGGY IMPLEMENTATION: Logical OR instead of XOR
def string_xor(a: str, b: str) -> str:
    """ Input are two strings a and b consisting only of 1s and 0s.
    Perform binary XOR on these inputs and return result also as a string.
    >>> string_xor('010', '110')
    '100'
    """
    res = []
    for c1, c2 in zip(a, b):
        # BUG: checks OR instead of XOR
        if c1 == '1' or c2 == '1':
            res.append('1')
        else:
            res.append('0')
    return "".join(res)

# TASK: Fix string_xor so '1' and '1' yields '0'.
''',
        "test": '''
def check(candidate):
    assert candidate('010', '110') == '100'
    assert candidate('1', '0') == '1'
    assert candidate('1', '1') == '0'
    assert candidate('0101', '0000') == '0101'

check(string_xor)
'''
    },
    {
        "task_id": "Fix/8_longest",
        "entry_point": "longest",
        "prompt": '''from typing import List, Optional

# BUGGY IMPLEMENTATION: Returns shortest string instead of longest string
def longest(strings: List[str]) -> Optional[str]:
    """ Out of list of strings, return the longest one. Return the first one in case of multiple
    strings of the same length. Return None in case the input list is empty.
    """
    if not strings:
        return None
    res = strings[0]
    for s in strings:
        # BUG: < instead of >
        if len(s) < len(res):
            res = s
    return res

# TASK: Fix longest so it returns the longest string.
''',
        "test": '''
def check(candidate):
    assert candidate([]) == None
    assert candidate(['a', 'b', 'c']) == 'a'
    assert candidate(['a', 'bb', 'ccc']) == 'ccc'
    assert candidate(['x', 'yyy', 'zzzz', 'www', 'kkkk', 'abc']) == 'zzzz'

check(longest)
'''
    },
    {
        "task_id": "Fix/9_greatest_common_divisor",
        "entry_point": "greatest_common_divisor",
        "prompt": '''# BUGGY IMPLEMENTATION: Swapped arguments in modulo causing ZeroDivisionError or wrong order
def greatest_common_divisor(a: int, b: int) -> int:
    """ Return a greatest common divisor of two integers a and b """
    while b != 0:
        # BUG: a, b = a % b, b causes infinite loop or zero division
        a = a % b
    return a

# TASK: Fix greatest_common_divisor using Euclid algorithm: a, b = b, a % b.
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
        "task_id": "Fix/10_all_prefixes",
        "entry_point": "all_prefixes",
        "prompt": '''from typing import List

# BUGGY IMPLEMENTATION: Off-by-one slice [:i] misses full string
def all_prefixes(string: str) -> List[str]:
    """ Return list of all prefixes from shortest to longest of the input string """
    res = []
    # BUG: range(len(string)) with [:i] starts with empty string and misses final full string
    for i in range(len(string)):
        res.append(string[:i])
    return res

# TASK: Fix all_prefixes to return prefixes from 1 character up to len(string).
''',
        "test": '''
def check(candidate):
    assert candidate('') == []
    assert candidate('asdf') == ['a', 'as', 'asd', 'asdf']
    assert candidate('WWW') == ['W', 'WW', 'WWW']

check(all_prefixes)
'''
    },
    {
        "task_id": "Fix/11_string_sequence",
        "entry_point": "string_sequence",
        "prompt": '''# BUGGY IMPLEMENTATION: range(n) excludes n
def string_sequence(n: int) -> str:
    """ Return a string containing space-delimited numbers starting from 0 upto n inclusive.
    >>> string_sequence(0)
    '0'
    >>> string_sequence(5)
    '0 1 2 3 4 5'
    """
    # BUG: range(n) stops at n-1
    return " ".join(str(x) for x in range(n))

# TASK: Fix string_sequence to include n (range(n+1)).
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
        "task_id": "Fix/12_count_distinct_characters",
        "entry_point": "count_distinct_characters",
        "prompt": '''# BUGGY IMPLEMENTATION: Does not normalize case, counting 'A' and 'a' separately
def count_distinct_characters(string: str) -> int:
    """ Given a string, find out how many distinct characters (regardless of case) it consists of
    >>> count_distinct_characters('xyzXYZ')
    3
    >>> count_distinct_characters('Jerry')
    4
    """
    # BUG: set(string) is case-sensitive
    return len(set(string))

# TASK: Fix count_distinct_characters to be case-insensitive.
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
        "task_id": "Fix/13_parse_music",
        "entry_point": "parse_music",
        "prompt": '''from typing import List

# BUGGY IMPLEMENTATION: Dictionary key mismatch
def parse_music(music_string: str) -> List[int]:
    """ Parse legendary music notes: 'o' -> 4 beats, 'o|' -> 2 beats, '.|' -> 1 beat. """
    note_map = {'o': 4, 'o|': 2, '.|': 1}
    # BUG: splits by character instead of spaces
    notes = list(music_string)
    return [note_map[n] for n in notes if n in note_map]

# TASK: Fix parse_music to split notes by whitespace.
''',
        "test": '''
def check(candidate):
    assert candidate('') == []
    assert candidate('o o o o') == [4, 4, 4, 4]
    assert candidate('.| .| .| .|') == [1, 1, 1, 1]
    assert candidate('o| o| .| .| o o o| o') == [2, 2, 1, 1, 4, 4, 2, 4]

check(parse_music)
'''
    },
    {
        "task_id": "Fix/14_how_many_times",
        "entry_point": "how_many_times",
        "prompt": '''# BUGGY IMPLEMENTATION: Uses string.count which does not count overlapping occurrences
def how_many_times(string: str, substring: str) -> int:
    """ Find how many times a given substring can be found in the original string.
    Count overlapping cases.
    >>> how_many_times('aaa', 'a')
    3
    >>> how_many_times('aaaa', 'aa')
    3
    """
    # BUG: string.count('aaaa', 'aa') returns 2 instead of 3 (non-overlapping)
    return string.count(substring)

# TASK: Fix how_many_times to count overlapping substring occurrences.
''',
        "test": '''
def check(candidate):
    assert candidate('', 'a') == 0
    assert candidate('aaa', 'a') == 3
    assert candidate('aaaa', 'aa') == 3
    assert candidate('xyxyxyx', 'xyx') == 3
    assert candidate('cacacacac', 'cac') == 4
    assert candidate('john doe', 'john') == 1

check(how_many_times)
'''
    },
    {
        "task_id": "Fix/15_sort_numbers",
        "entry_point": "sort_numbers",
        "prompt": '''# BUGGY IMPLEMENTATION: UnboundLocalError on empty input string
def sort_numbers(numbers: str) -> str:
    """ Input is space-delimited numeral words 'zero' through 'nine'. Return sorted. """
    numeral_map = {'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
                   'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9}
    inv_map = {v: k for k, v in numeral_map.items()}
    # BUG: numbers.split() on empty string produces [], but list comprehension fails on empty return
    nums = [numeral_map[w] for w in numbers.split()]
    nums.sort()
    return " ".join(inv_map[n] for n in nums)

# TASK: Fix sort_numbers so candidate('') == ''.
''',
        "test": '''
def check(candidate):
    assert candidate('') == ''
    assert candidate('three') == 'three'
    assert candidate('three five nine') == 'three five nine'
    assert candidate('five zero four seven nine eight') == 'zero four five seven eight nine'

check(sort_numbers)
'''
    },
    {
        "task_id": "Fix/16_find_closest_elements",
        "entry_point": "find_closest_elements",
        "prompt": '''from typing import List, Tuple

# BUGGY IMPLEMENTATION: Compares element with itself (distance 0)
def find_closest_elements(numbers: List[float]) -> Tuple[float, float]:
    """ From a supplied list of numbers (of length at least two) select and return two that are the closest to each
    other and return them in order (smaller number, larger number).
    """
    closest_pair = None
    min_diff = None
    for i in range(len(numbers)):
        for j in range(len(numbers)):
            # BUG: i == j compares element with itself yielding distance 0.0
            diff = abs(numbers[i] - numbers[j])
            if min_diff is None or diff < min_diff:
                min_diff = diff
                closest_pair = tuple(sorted([numbers[i], numbers[j]]))
    return closest_pair

# TASK: Fix find_closest_elements so j > i (avoid comparing element with itself).
''',
        "test": '''
def check(candidate):
    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2]) == (3.9, 4.0)
    assert candidate([1.0, 2.0, 5.9, 4.0, 5.0]) == (5.0, 5.9)
    assert candidate([1.0, 2.0, 3.0, 4.0, 5.0, 2.2]) == (2.0, 2.2)

check(find_closest_elements)
'''
    },
    {
        "task_id": "Fix/17_separate_paren_groups",
        "entry_point": "separate_paren_groups",
        "prompt": '''from typing import List

# BUGGY IMPLEMENTATION: Does not ignore whitespace in input
def separate_paren_groups(paren_string: str) -> List[str]:
    """ Separate groups of balanced parentheses into strings. Ignore spaces. """
    res = []
    current = []
    depth = 0
    # BUG: spaces are added to current group
    for c in paren_string:
        if c == '(':
            depth += 1
            current.append(c)
        elif c == ')':
            depth -= 1
            current.append(c)
            if depth == 0:
                res.append("".join(current))
                current = []
    return res

# TASK: Fix separate_paren_groups to ignore spaces.
''',
        "test": '''
def check(candidate):
    assert candidate('(()()) ((())) () ((())()())') == ['(()())', '((()))', '()', '((())()())']
    assert candidate('() (()) ((())) (((())))') == ['()', '(())', '((()))', '(((())))']
    assert candidate('( ) (( )) (( )( ))') == ['()', '(())', '(()())']

check(separate_paren_groups)
'''
    },
    {
        "task_id": "Fix/18_unique_elements",
        "entry_point": "unique",
        "prompt": '''from typing import List

# BUGGY IMPLEMENTATION: Does not sort the returned unique elements
def unique(l: List[int]) -> List[int]:
    """ Return sorted unique elements in a list
    >>> unique([5, 3, 5, 2, 3, 3, 9, 0, 123])
    [0, 2, 3, 5, 9, 123]
    """
    # BUG: list(set(l)) does not guarantee sorted order
    return list(set(l))

# TASK: Fix unique to return sorted list.
''',
        "test": '''
def check(candidate):
    assert candidate([5, 3, 5, 2, 3, 3, 9, 0, 123]) == [0, 2, 3, 5, 9, 123]
    assert candidate([]) == []
    assert candidate([1, 1, 1, 1]) == [1]

check(unique)
'''
    },
    {
        "task_id": "Fix/19_filter_by_prefix",
        "entry_point": "filter_by_prefix",
        "prompt": '''from typing import List

# BUGGY IMPLEMENTATION: Inverted startswith condition
def filter_by_prefix(strings: List[str], prefix: str) -> List[str]:
    """ Filter an input list of strings only for ones that start with a given prefix. """
    # BUG: inverted check (not startswith instead of startswith)
    return [s for s in strings if not s.startswith(prefix)]

# TASK: Fix filter_by_prefix so it keeps strings that start with prefix.
''',
        "test": '''
def check(candidate):
    assert candidate([], 'a') == []
    assert candidate(['abc', 'bcd', 'cde', 'array'], 'a') == ['abc', 'array']
    assert candidate(['grunt', 'trumpet', 'prune', 'gruff'], 'gru') == ['grunt', 'gruff']

check(filter_by_prefix)
'''
    }
]


def run_benchmark(output_dir: str = "/srv/storage/ai-companion/data", model: str = "aria:3b"):
    engine = ExecutionGuidedRepairEngine(model=model, max_attempts=3, sandbox_timeout=5.0)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print("=" * 90)
    print("HUMANEVAL-FIX COMPARATIVE BENCHMARK: EXECUTION-GUIDED SELF-REPAIR")
    print(f"Target Model: {model} | Benchmark Size N = {len(HUMANEVAL_FIX_20)} | Max Iterations: 3")
    print("Comparing: Condition A (Single-Shot) vs Condition B (Execution-Guided Sandbox Repair)")
    print("=" * 90, flush=True)

    results = []

    single_shot_passed = 0
    repair_loop_passed = 0
    total_repairs_achieved = 0
    initial_failures = 0

    total_tokens_all = 0
    total_latency_all_ms = 0.0

    for idx, prob in enumerate(HUMANEVAL_FIX_20, 1):
        task_id = prob["task_id"]
        prompt = prob["prompt"]
        test_code = prob["test"]

        print(f"\n[{idx:02d}/{len(HUMANEVAL_FIX_20)}] Testing Task: {task_id}")
        t_start = time.time()
        repair_res = engine.run_repair_loop(task_id, prompt, test_code)
        duration_s = time.time() - t_start

        init_pass = repair_res["initial_passed"]
        fin_pass = repair_res["final_passed"]
        repaired = repair_res["repaired"]
        attempts = repair_res["attempts_used"]

        if init_pass:
            single_shot_passed += 1
        else:
            initial_failures += 1

        if fin_pass:
            repair_loop_passed += 1

        if repaired:
            total_repairs_achieved += 1

        total_tokens_all += repair_res["total_tokens"]
        total_latency_all_ms += repair_res["total_latency_ms"]

        init_status = "PASS" if init_pass else "FAIL"
        fin_status = "PASS" if fin_pass else "FAIL"
        outcome_label = "REPAIRED (+)" if repaired else ("MAINTAINED" if init_pass else "UNRESOLVED")

        print(f"   -> Single-Shot: {init_status} | Final (Attempts={attempts}): {fin_status} | Status: {outcome_label}")
        for step in repair_res["trajectory"]:
            status_str = "PASS (exit=0)" if step["passed"] else f"FAIL (exit={step['returncode']})"
            err_str = f" | {step['error_summary']}" if step["error_summary"] else ""
            print(f"      Attempt {step['attempt']}: {status_str:<14} | tokens={step['tokens']:3d} | latency={step['latency_ms']:.0f}ms{err_str}")

        results.append(repair_res)

    n = len(HUMANEVAL_FIX_20)
    single_shot_rate = (single_shot_passed / n) * 100.0
    repair_loop_rate = (repair_loop_passed / n) * 100.0
    repair_delta = repair_loop_rate - single_shot_rate
    repair_success_rate = (total_repairs_achieved / initial_failures * 100.0) if initial_failures > 0 else 0.0

    print("\n" + "=" * 90)
    print("EMPIRICAL REPAIR BENCHMARK SUMMARY:")
    print(f"  Total Debugging Problems Evaluated:  {n}")
    print(f"  Condition A (Single-Shot Pass@1):    {single_shot_passed}/{n} ({single_shot_rate:.1f}%)")
    print(f"  Condition B (Repair Loop Pass@1):    {repair_loop_passed}/{n} ({repair_loop_rate:.1f}%)")
    print(f"  Absolute Pass@1 Delta:               +{repair_delta:+.1f}%")
    print(f"  Initial Defects Corrected:           {total_repairs_achieved}/{initial_failures} ({repair_success_rate:.1f}% repair success rate)")
    print(f"  Mean Latency Per Task:               {total_latency_all_ms / n:.1f} ms")
    print(f"  Mean Tokens Per Task:                {total_tokens_all / n:.1f} tokens")
    print("=" * 90)

    summary_file = out_path / "humaneval_fix_repair_benchmark.json"
    with open(summary_file, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "model": model,
            "total_problems": n,
            "single_shot_passed": single_shot_passed,
            "single_shot_pass_rate_pct": single_shot_rate,
            "repair_loop_passed": repair_loop_passed,
            "repair_loop_pass_rate_pct": repair_loop_rate,
            "absolute_delta_pct": repair_delta,
            "initial_failures": initial_failures,
            "repairs_achieved": total_repairs_achieved,
            "repair_success_rate_pct": repair_success_rate,
            "mean_latency_ms": total_latency_all_ms / n,
            "mean_tokens": total_tokens_all / n,
            "results": results
        }, f, indent=2)

    print(f"Saved complete comparative repair telemetry to: {summary_file}")
    return summary_file


if __name__ == "__main__":
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "/srv/storage/ai-companion/data"
    run_benchmark(out_dir)
