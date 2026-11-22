"""
Comprehensive Challenge Bank for Aria GRPO / RLVR (Phase 10)
40 rigorous verification challenges across 3 domains:
- Domain A: Hard Algorithmic Invariants (25 tasks)
- Domain B: Linux Systems Engineering & Diagnostics (11 tasks)
- Domain C: Counterfactual & Resilience Patterns (4 tasks)
"""

from typing import Dict, Any, List

CHALLENGE_BANK: List[Dict[str, Any]] = [
    # ---------------------------------------------------------
    # DOMAIN A: ALGORITHMIC INVARIANTS (1 - 25)
    # ---------------------------------------------------------
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
    },
    {
        "task_id": "RLVR/py_lru_cache",
        "entry_point": "LRUCache",
        "prompt": '''class LRUCache:
    """ Design a data structure that follows the constraints of a Least Recently Used (LRU) cache.
    Implement the LRUCache class:
    - LRUCache(int capacity) Initialize the LRU cache with positive size capacity.
    - int get(int key) Return the value of the key if the key exists, otherwise return -1.
    - void put(int key, int value) Update the value of the key if the key exists. Otherwise, add the key-value pair to the cache.
      If the number of keys exceeds the capacity from this operation, evict the least recently used key.
    Both get and put must run in O(1) average time complexity.
    """
    def __init__(self, capacity: int):
        pass

    def get(self, key: int) -> int:
        pass

    def put(self, key: int, value: int) -> None:
        pass
''',
        "test": '''
def check(candidate):
    cache = candidate(2)
    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == 1
    cache.put(3, 3)    # evicts key 2
    assert cache.get(2) == -1
    cache.put(4, 4)    # evicts key 1
    assert cache.get(1) == -1
    assert cache.get(3) == 3
    assert cache.get(4) == 4

check(LRUCache)
'''
    },
    {
        "task_id": "RLVR/py_daily_temperatures",
        "entry_point": "daily_temperatures",
        "prompt": '''from typing import List

def daily_temperatures(temperatures: List[int]) -> List[int]:
    """ Given an array of integers temperatures represents the daily temperatures,
    return an array answer such that answer[i] is the number of days you have to wait after the ith day to get a warmer temperature.
    If there is no future day for which this is possible, keep answer[i] == 0 instead.
    Must run in O(n) time.
    >>> daily_temperatures([73,74,75,71,69,72,76,73])
    [1, 1, 4, 2, 1, 1, 0, 0]
    >>> daily_temperatures([30,40,50,60])
    [1, 1, 1, 0]
    """
''',
        "test": '''
def check(candidate):
    assert candidate([73, 74, 75, 71, 69, 72, 76, 73]) == [1, 1, 4, 2, 1, 1, 0, 0]
    assert candidate([30, 40, 50, 60]) == [1, 1, 1, 0]
    assert candidate([30, 60, 90]) == [1, 1, 0]
    assert candidate([90, 80, 70]) == [0, 0, 0]

check(daily_temperatures)
'''
    },
    {
        "task_id": "RLVR/py_subarray_sum_k",
        "entry_point": "subarray_sum_k",
        "prompt": '''from typing import List

def subarray_sum_k(nums: List[int], k: int) -> int:
    """ Given an array of integers nums and an integer k, return the total number of subarrays whose sum equals to k.
    Must run in O(n) average time complexity using prefix sums.
    >>> subarray_sum_k([1, 1, 1], 2)
    2
    >>> subarray_sum_k([1, 2, 3], 3)
    2
    """
''',
        "test": '''
def check(candidate):
    assert candidate([1, 1, 1], 2) == 2
    assert candidate([1, 2, 3], 3) == 2
    assert candidate([1, -1, 0], 0) == 3
    assert candidate([3, 4, 7, 2, -3, 1, 4, 2], 7) == 4

check(subarray_sum_k)
'''
    },
    {
        "task_id": "RLVR/py_coin_change",
        "entry_point": "coin_change",
        "prompt": '''from typing import List

def coin_change(coins: List[int], amount: int) -> int:
    """ You are given an integer array coins representing coins of different denominations and an integer amount representing a total amount of money.
    Return the fewest number of coins that you need to make up that amount. If that amount of money cannot be made up by any combination of the coins, return -1.
    >>> coin_change([1, 2, 5], 11)
    3
    >>> coin_change([2], 3)
    -1
    >>> coin_change([1], 0)
    0
    """
''',
        "test": '''
def check(candidate):
    assert candidate([1, 2, 5], 11) == 3
    assert candidate([2], 3) == -1
    assert candidate([1], 0) == 0
    assert candidate([186, 419, 83, 408], 6249) == 20

check(coin_change)
'''
    },
    {
        "task_id": "RLVR/py_length_of_lis",
        "entry_point": "length_of_lis",
        "prompt": '''from typing import List

def length_of_lis(nums: List[int]) -> int:
    """ Given an integer array nums, return the length of the longest strictly increasing subsequence.
    >>> length_of_lis([10,9,2,5,3,7,101,18])
    4
    >>> length_of_lis([0,1,0,3,2,3])
    4
    >>> length_of_lis([7,7,7,7,7,7,7])
    1
    """
''',
        "test": '''
def check(candidate):
    assert candidate([10, 9, 2, 5, 3, 7, 101, 18]) == 4
    assert candidate([0, 1, 0, 3, 2, 3]) == 4
    assert candidate([7, 7, 7, 7, 7, 7, 7]) == 1
    assert candidate([]) == 0
    assert candidate([4, 10, 4, 3, 8, 9]) == 3

check(length_of_lis)
'''
    },
    {
        "task_id": "RLVR/py_word_break",
        "entry_point": "word_break",
        "prompt": '''from typing import List

def word_break(s: str, word_dict: List[str]) -> bool:
    """ Given a string s and a dictionary of strings word_dict, return True if s can be segmented into a space-separated sequence of one or more dictionary words.
    The same word in the dictionary may be reused multiple times in the segmentation.
    >>> word_break("leetcode", ["leet", "code"])
    True
    >>> word_break("applepenapple", ["apple", "pen"])
    True
    >>> word_break("catsandog", ["cats", "dog", "sand", "and", "cat"])
    False
    """
''',
        "test": '''
def check(candidate):
    assert candidate("leetcode", ["leet", "code"]) == True
    assert candidate("applepenapple", ["apple", "pen"]) == True
    assert candidate("catsandog", ["cats", "dog", "sand", "and", "cat"]) == False
    assert candidate("cars", ["car", "ca", "rs"]) == True
    assert candidate("a", ["b"]) == False

check(word_break)
'''
    },
    {
        "task_id": "RLVR/py_has_cycle_directed",
        "entry_point": "has_cycle_directed",
        "prompt": '''from typing import Dict, List

def has_cycle_directed(num_nodes: int, edges: List[List[int]]) -> bool:
    """ Given the number of nodes (labeled 0 to num_nodes - 1) and a list of directed edges [u, v] (from u to v),
    return True if the directed graph contains a cycle, False otherwise.
    >>> has_cycle_directed(2, [[0, 1], [1, 0]])
    True
    >>> has_cycle_directed(2, [[0, 1]])
    False
    """
''',
        "test": '''
def check(candidate):
    assert candidate(2, [[0, 1], [1, 0]]) == True
    assert candidate(2, [[0, 1]]) == False
    assert candidate(3, [[0, 1], [1, 2], [2, 0]]) == True
    assert candidate(4, [[0, 1], [1, 2], [2, 3]]) == False
    assert candidate(4, [[0, 1], [2, 3], [3, 2]]) == True

check(has_cycle_directed)
'''
    },
    {
        "task_id": "RLVR/py_course_schedule",
        "entry_point": "can_finish_courses",
        "prompt": '''from typing import List

def can_finish_courses(num_courses: int, prerequisites: List[List[int]]) -> bool:
    """ There are a total of num_courses courses you have to take, labeled from 0 to num_courses - 1.
    You are given an array prerequisites where prerequisites[i] = [a_i, b_i] indicates that you must take course b_i first if you want to take course a_i.
    Return True if you can finish all courses. Otherwise, return False.
    >>> can_finish_courses(2, [[1, 0]])
    True
    >>> can_finish_courses(2, [[1, 0], [0, 1]])
    False
    """
''',
        "test": '''
def check(candidate):
    assert candidate(2, [[1, 0]]) == True
    assert candidate(2, [[1, 0], [0, 1]]) == False
    assert candidate(3, [[0, 1], [0, 2], [1, 2]]) == True
    assert candidate(1, []) == True

check(can_finish_courses)
'''
    },
    {
        "task_id": "RLVR/py_meeting_rooms_ii",
        "entry_point": "min_meeting_rooms",
        "prompt": '''from typing import List

def min_meeting_rooms(intervals: List[List[int]]) -> int:
    """ Given an array of meeting time intervals intervals where intervals[i] = [start_i, end_i],
    return the minimum number of conference rooms required.
    >>> min_meeting_rooms([[0, 30],[5, 10],[15, 20]])
    2
    >>> min_meeting_rooms([[7, 10],[2, 4]])
    1
    """
''',
        "test": '''
def check(candidate):
    assert candidate([[0, 30], [5, 10], [15, 20]]) == 2
    assert candidate([[7, 10], [2, 4]]) == 1
    assert candidate([[1, 5], [5, 10]]) == 1
    assert candidate([]) == 0
    assert candidate([[1, 10], [2, 7], [3, 19], [8, 12], [10, 20], [11, 30]]) == 4

check(min_meeting_rooms)
'''
    },
    {
        "task_id": "RLVR/py_min_window_substring",
        "entry_point": "min_window_substring",
        "prompt": '''def min_window_substring(s: str, t: str) -> str:
    """ Given two strings s and t of lengths m and n respectively, return the minimum window substring of s such that every character in t (including duplicates) is included in the window.
    If there is no such substring, return the empty string "".
    >>> min_window_substring("ADOBECODEBANC", "ABC")
    'BANC'
    >>> min_window_substring("a", "a")
    'a'
    >>> min_window_substring("a", "aa")
    ''
    """
''',
        "test": '''
def check(candidate):
    assert candidate("ADOBECODEBANC", "ABC") == "BANC"
    assert candidate("a", "a") == "a"
    assert candidate("a", "aa") == ""
    assert candidate("ab", "b") == "b"

check(min_window_substring)
'''
    },
    {
        "task_id": "RLVR/py_trap_rain_water",
        "entry_point": "trap_rain_water",
        "prompt": '''from typing import List

def trap_rain_water(height: List[int]) -> int:
    """ Given n non-negative integers representing an elevation map where the width of each bar is 1,
    compute how much water it can trap after raining.
    Must run in O(n) time and O(1) extra space.
    >>> trap_rain_water([0,1,0,2,1,0,1,3,2,1,2,1])
    6
    >>> trap_rain_water([4,2,0,3,2,5])
    9
    """
''',
        "test": '''
def check(candidate):
    assert candidate([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]) == 6
    assert candidate([4, 2, 0, 3, 2, 5]) == 9
    assert candidate([]) == 0
    assert candidate([3]) == 0
    assert candidate([3, 2, 1]) == 0

check(trap_rain_water)
'''
    },
    {
        "task_id": "RLVR/py_find_median_sorted_arrays",
        "entry_point": "find_median_sorted_arrays",
        "prompt": '''from typing import List

def find_median_sorted_arrays(nums1: List[int], nums2: List[int]) -> float:
    """ Given two sorted arrays nums1 and nums2 of size m and n respectively, return the median of the two sorted arrays.
    The overall run time complexity should be O(log (m+n)).
    >>> find_median_sorted_arrays([1, 3], [2])
    2.0
    >>> find_median_sorted_arrays([1, 2], [3, 4])
    2.5
    """
''',
        "test": '''
def check(candidate):
    assert abs(candidate([1, 3], [2]) - 2.0) < 1e-5
    assert abs(candidate([1, 2], [3, 4]) - 2.5) < 1e-5
    assert abs(candidate([0, 0], [0, 0]) - 0.0) < 1e-5
    assert abs(candidate([], [1]) - 1.0) < 1e-5

check(find_median_sorted_arrays)
'''
    },
    {
        "task_id": "RLVR/py_spiral_matrix",
        "entry_point": "spiral_order",
        "prompt": '''from typing import List

def spiral_order(matrix: List[List[int]]) -> List[int]:
    """ Given an m x n matrix, return all elements of the matrix in spiral order.
    >>> spiral_order([[1,2,3],[4,5,6],[7,8,9]])
    [1, 2, 3, 6, 9, 8, 7, 4, 5]
    """
''',
        "test": '''
def check(candidate):
    assert candidate([[1, 2, 3], [4, 5, 6], [7, 8, 9]]) == [1, 2, 3, 6, 9, 8, 7, 4, 5]
    assert candidate([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]) == [1, 2, 3, 4, 8, 12, 11, 10, 9, 5, 6, 7]
    assert candidate([]) == []
    assert candidate([[1]]) == [1]

check(spiral_order)
'''
    },
    {
        "task_id": "RLVR/py_trie_prefix_tree",
        "entry_point": "Trie",
        "prompt": '''class Trie:
    """ A trie (pronounced as "try") or prefix tree is a tree data structure used to efficiently store and retrieve keys in a dataset of strings.
    Implement the Trie class:
    - Trie() Initializes the trie object.
    - void insert(str word) Inserts the string word into the trie.
    - bool search(str word) Returns True if the string word is in the trie (i.e., was inserted before), and False otherwise.
    - bool startsWith(str prefix) Returns True if there is a previously inserted string word that has the prefix prefix, and False otherwise.
    """
    def __init__(self):
        pass

    def insert(self, word: str) -> None:
        pass

    def search(self, word: str) -> bool:
        pass

    def startsWith(self, prefix: str) -> bool:
        pass
''',
        "test": '''
def check(candidate):
    trie = candidate()
    trie.insert("apple")
    assert trie.search("apple") == True
    assert trie.search("app") == False
    assert trie.startsWith("app") == True
    trie.insert("app")
    assert trie.search("app") == True

check(Trie)
'''
    },
    {
        "task_id": "RLVR/py_sliding_window_maximum",
        "entry_point": "max_sliding_window",
        "prompt": '''from typing import List

def max_sliding_window(nums: List[int], k: int) -> List[int]:
    """ You are given an array of integers nums, there is a sliding window of size k which is moving from the very left of the array to the very right.
    You can only see the k numbers in the window. Each time the sliding window moves right by one position.
    Return the max sliding window. Must run in O(n) time.
    >>> max_sliding_window([1,3,-1,-3,5,3,6,7], 3)
    [3, 3, 5, 5, 6, 7]
    """
''',
        "test": '''
def check(candidate):
    assert candidate([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]
    assert candidate([1], 1) == [1]
    assert candidate([1, -1], 1) == [1, -1]
    assert candidate([9, 11], 2) == [11]

check(max_sliding_window)
'''
    },

    # ---------------------------------------------------------
    # DOMAIN B: LINUX SYSTEMS ENGINEERING & DIAGNOSTICS (26 - 36)
    # ---------------------------------------------------------
    {
        "task_id": "RLVR/sys_parse_proc_meminfo",
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
        "task_id": "RLVR/sys_cidr_subnet_check",
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
        "task_id": "RLVR/sys_parse_proc_cpuinfo",
        "entry_point": "parse_proc_cpuinfo",
        "prompt": '''from typing import Dict, Any

def parse_proc_cpuinfo(cpuinfo_content: str) -> Dict[str, Any]:
    """ Parses Linux /proc/cpuinfo content and returns:
    - 'core_count': total number of processor blocks defined
    - 'model_names': list of distinct model name strings stripped of leading/trailing whitespace
    >>> parse_proc_cpuinfo("processor\\t: 0\\nmodel name\\t: Intel Xeon E5\\n\\nprocessor\\t: 1\\nmodel name\\t: Intel Xeon E5\\n")
    {'core_count': 2, 'model_names': ['Intel Xeon E5']}
    """
''',
        "test": '''
def check(candidate):
    sample = """processor	: 0
vendor_id	: GenuineIntel
model name	: AMD Ryzen 9 5950X
cpu MHz		: 3400.000

processor	: 1
vendor_id	: GenuineIntel
model name	: AMD Ryzen 9 5950X
cpu MHz		: 3400.000
"""
    res = candidate(sample)
    assert res['core_count'] == 2
    assert res['model_names'] == ['AMD Ryzen 9 5950X']
    assert candidate("") == {'core_count': 0, 'model_names': []}

check(parse_proc_cpuinfo)
'''
    },
    {
        "task_id": "RLVR/sys_parse_proc_net_tcp",
        "entry_point": "parse_listening_ports",
        "prompt": '''from typing import List

def parse_listening_ports(proc_net_tcp: str) -> List[int]:
    """ Parses Linux /proc/net/tcp format and returns a sorted list of unique integer port numbers
    that are in LISTEN state (state hex code '0A').
    Local address column is in format 'HEX_IP:HEX_PORT'.
    """
''',
        "test": '''
def check(candidate):
    sample = """  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 0100007F:1F90 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 24108 1 0000000000000000 100 0 0 10 0
   1: 00000000:0016 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 19821 1 0000000000000000 100 0 0 10 0
   2: 0100007F:1F90 0100007F:C001 01 00000000:00000000 00:00000000 00000000     0        0 24109 1 0000000000000000 100 0 0 10 0
"""
    # 0x1F90 is 8080, 0x0016 is 22. Line 2 is state 01 (ESTABLISHED), ignored.
    ports = candidate(sample)
    assert ports == [22, 8080]
    assert candidate("") == []

check(parse_listening_ports)
'''
    },
    {
        "task_id": "RLVR/sys_chmod_str_to_octal",
        "entry_point": "chmod_to_octal",
        "prompt": '''def chmod_to_octal(perm_str: str) -> str:
    """ Converts a standard 9-character Linux permission string (e.g. 'rwxr-xr-x') into its 3-digit octal representation (e.g. '755').
    If string is 10 chars starting with file type ('-rwxr-xr-x'), drop the leading char.
    >>> chmod_to_octal('rwxr-xr-x')
    '755'
    >>> chmod_to_octal('-rw-r--r--')
    '644'
    """
''',
        "test": '''
def check(candidate):
    assert candidate('rwxr-xr-x') == '755'
    assert candidate('-rw-r--r--') == '644'
    assert candidate('rwx------') == '700'
    assert candidate('drwxrwxrwx') == '777'
    assert candidate('---------') == '000'

check(chmod_to_octal)
'''
    },
    {
        "task_id": "RLVR/sys_validate_crontab",
        "entry_point": "validate_cron_field_count",
        "prompt": '''def validate_cron_field_count(cron_str: str) -> bool:
    """ Validates that a cron schedule string consists of exactly 5 whitespace-separated fields:
    (minute hour day_of_month month day_of_week).
    Each field must contain only valid cron characters: digits, '*', '/', '-', or ','.
    Return True if valid, False otherwise.
    >>> validate_cron_field_count('*/5 * * * *')
    True
    >>> validate_cron_field_count('0 0 1 *')
    False
    """
''',
        "test": '''
def check(candidate):
    assert candidate('*/5 * * * *') == True
    assert candidate('0 12 * * 1-5') == True
    assert candidate('0 0 1 *') == False
    assert candidate('0 0 1 1 1 2026') == False
    assert candidate('invalid string') == False
    assert candidate('10,20,30 2 * * *') == True

check(validate_cron_field_count)
'''
    },
    {
        "task_id": "RLVR/sys_parse_systemd_unit",
        "entry_point": "parse_systemd_unit",
        "prompt": '''from typing import Dict

def parse_systemd_unit(unit_content: str) -> Dict[str, Dict[str, str]]:
    """ Parses a systemd unit INI configuration string into a dictionary of sections and their key-value pairs.
    Ignore comment lines starting with '#' or ';' and empty lines.
    >>> parse_systemd_unit("[Unit]\\nDescription=Aria Service\\n\\n[Service]\\nExecStart=/usr/bin/aria\\n")
    {'Unit': {'Description': 'Aria Service'}, 'Service': {'ExecStart': '/usr/bin/aria'}}
    """
''',
        "test": '''
def check(candidate):
    sample = """# Systemd unit file
[Unit]
Description=Aria Service
After=network.target

[Service]
Type=simple
ExecStart=/srv/storage/aria/bin/server --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
"""
    parsed = candidate(sample)
    assert parsed['Unit']['Description'] == 'Aria Service'
    assert parsed['Unit']['After'] == 'network.target'
    assert parsed['Service']['Type'] == 'simple'
    assert parsed['Service']['Restart'] == 'always'
    assert parsed['Install']['WantedBy'] == 'multi-user.target'

check(parse_systemd_unit)
'''
    },
    {
        "task_id": "RLVR/sys_parse_docker_ports",
        "entry_point": "parse_docker_port_bindings",
        "prompt": '''from typing import List, Dict

def parse_docker_port_bindings(ports_str: str) -> List[Dict[str, Any]]:
    """ Parses a Docker CLI port mapping string (e.g. '0.0.0.0:8080->80/tcp, 127.0.0.1:5432->5432/tcp')
    and returns a list of dictionaries with keys:
    'host_ip': str, 'host_port': int, 'container_port': int, 'protocol': str
    """
''',
        "test": '''
def check(candidate):
    sample = "0.0.0.0:8080->80/tcp, 127.0.0.1:5432->5432/tcp"
    res = candidate(sample)
    assert len(res) == 2
    assert res[0] == {'host_ip': '0.0.0.0', 'host_port': 8080, 'container_port': 80, 'protocol': 'tcp'}
    assert res[1] == {'host_ip': '127.0.0.1', 'host_port': 5432, 'container_port': 5432, 'protocol': 'tcp'}
    assert candidate("") == []

check(parse_docker_port_bindings)
'''
    },
    {
        "task_id": "RLVR/sys_parse_nginx_upstreams",
        "entry_point": "parse_nginx_upstreams",
        "prompt": '''from typing import List, Dict

def parse_nginx_upstreams(nginx_conf: str) -> Dict[str, List[str]]:
    """ Parses an Nginx configuration snippet containing upstream blocks:
    upstream <name> {
        server <host:port>;
        server <host:port>;
    }
    Returns a dictionary mapping upstream name to list of server endpoint strings.
    """
''',
        "test": '''
def check(candidate):
    sample = """
upstream backend_api {
    server 192.168.2.2:8000;
    server 192.168.2.3:8000;
}
upstream ws_stream {
    server 127.0.0.1:9001;
}
"""
    res = candidate(sample)
    assert res['backend_api'] == ['192.168.2.2:8000', '192.168.2.3:8000']
    assert res['ws_stream'] == ['127.0.0.1:9001']

check(parse_nginx_upstreams)
'''
    },
    {
        "task_id": "RLVR/sys_parse_loadavg",
        "entry_point": "parse_loadavg",
        "prompt": '''from typing import Dict, Any

def parse_loadavg(loadavg_str: str) -> Dict[str, Any]:
    """ Parses a Linux /proc/loadavg line (e.g. '0.45 0.52 0.48 2/342 98412') and returns:
    - 'load_1m': float
    - 'load_5m': float
    - 'load_15m': float
    - 'running_threads': int
    - 'total_threads': int
    - 'last_pid': int
    """
''',
        "test": '''
def check(candidate):
    sample = "0.45 0.52 0.48 2/342 98412"
    res = candidate(sample)
    assert abs(res['load_1m'] - 0.45) < 1e-4
    assert abs(res['load_5m'] - 0.52) < 1e-4
    assert abs(res['load_15m'] - 0.48) < 1e-4
    assert res['running_threads'] == 2
    assert res['total_threads'] == 342
    assert res['last_pid'] == 98412

check(parse_loadavg)
'''
    },
    {
        "task_id": "RLVR/sys_parse_syslog_severity",
        "entry_point": "parse_syslog_pri",
        "prompt": '''from typing import Tuple

def parse_syslog_pri(pri_val: int) -> Tuple[int, int]:
    """ Given an RFC 5424 PRI numerical code (e.g. 134 in '<134>'),
    extract and return the tuple (facility, severity).
    Formula: facility = pri // 8, severity = pri % 8.
    >>> parse_syslog_pri(134)
    (16, 6)
    """
''',
        "test": '''
def check(candidate):
    assert candidate(134) == (16, 6)
    assert candidate(13) == (1, 5)
    assert candidate(0) == (0, 0)
    assert candidate(191) == (23, 7)

check(parse_syslog_pri)
'''
    },

    # ---------------------------------------------------------
    # DOMAIN C: COUNTERFACTUAL & RESILIENCE PATTERNS (37 - 40)
    # ---------------------------------------------------------
    {
        "task_id": "RLVR/resil_sanitize_safe_path",
        "entry_point": "sanitize_safe_path",
        "prompt": '''import os

def sanitize_safe_path(base_dir: str, user_relative_path: str) -> str:
    """ Given an absolute base directory path and an untrusted user-supplied relative path,
    compute the resolved canonical target path.
    If the target path attempts to escape outside base_dir (e.g. using '..' or symlink tricks),
    raise a ValueError("Path traversal detected").
    Otherwise, return the sanitized canonical path string.
    """
''',
        "test": '''
def check(candidate):
    base = "/srv/storage/workspace"
    safe = candidate(base, "docs/report.txt")
    assert safe == "/srv/storage/workspace/docs/report.txt" or safe == "/srv/storage/workspace/docs/report.txt".replace("/", os.sep)
    
    import pytest
    try:
        candidate(base, "../../etc/passwd")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "traversal" in str(e).lower()

check(sanitize_safe_path)
'''
    },
    {
        "task_id": "RLVR/resil_token_bucket_limiter",
        "entry_point": "TokenBucketRateLimiter",
        "prompt": '''import time

class TokenBucketRateLimiter:
    """ Implements a thread-safe token bucket rate limiter.
    - __init__(capacity: float, refill_rate_per_sec: float)
    - allow(tokens: float = 1.0) -> bool: returns True if tokens are consumed, False otherwise.
    """
    def __init__(self, capacity: float, refill_rate_per_sec: float):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        self.tokens = capacity
        self.last_update = time.time()

    def allow(self, tokens: float = 1.0) -> bool:
        pass
''',
        "test": '''
def check(candidate):
    limiter = candidate(capacity=2.0, refill_rate_per_sec=10.0)
    assert limiter.allow(1.0) == True
    assert limiter.allow(1.0) == True
    assert limiter.allow(1.0) == False  # Bucket exhausted
    time.sleep(0.15)  # 0.15 * 10 = 1.5 tokens refilled
    assert limiter.allow(1.0) == True

check(TokenBucketRateLimiter)
'''
    },
    {
        "task_id": "RLVR/resil_detect_lock_contention",
        "entry_point": "is_lock_active",
        "prompt": '''from typing import Optional

def is_lock_active(lock_file_content: str, running_pids: List[int]) -> bool:
    """ Given the string content of a PID lockfile (e.g. '12485\\n') and a list of currently running OS PIDs,
    return True if the lock is held by an active running process.
    If the lockfile is empty, corrupted, or references a PID that is no longer running (stale lock), return False.
    """
''',
        "test": '''
def check(candidate):
    assert candidate("12485", [100, 12485, 999]) == True
    assert candidate("12485\\n", [100, 999]) == False  # Stale lock
    assert candidate("", [100]) == False
    assert candidate("not_a_pid", [100]) == False

check(is_lock_active)
'''
    },
    {
        "task_id": "RLVR/resil_verify_disk_headroom",
        "entry_point": "has_sufficient_disk_headroom",
        "prompt": '''def has_sufficient_disk_headroom(free_bytes: int, required_bytes: int, safety_margin_pct: float = 0.20) -> bool:
    """ Computes whether a target filesystem has sufficient free bytes to store an unquantized model or tensor payload.
    Takes into account a safety margin percentage (default 20%).
    Required space with safety margin = required_bytes * (1 + safety_margin_pct).
    Returns True if free_bytes >= required space, False otherwise.
    >>> has_sufficient_disk_headroom(1000, 800, 0.20)
    True
    >>> has_sufficient_disk_headroom(1000, 900, 0.20)
    False
    """
''',
        "test": '''
def check(candidate):
    # 800 * 1.2 = 960 <= 1000 -> True
    assert candidate(1000, 800, 0.20) == True
    # 900 * 1.2 = 1080 > 1000 -> False
    assert candidate(1000, 900, 0.20) == False
    assert candidate(5000000000, 4000000000, 0.20) == True
    assert candidate(4500000000, 4000000000, 0.20) == False

check(has_sufficient_disk_headroom)
'''
    }
]

if __name__ == "__main__":
    print(f"Loaded Phase 10 Challenge Bank: {len(CHALLENGE_BANK)} verifiable tasks.")
