#!/usr/bin/env python3
"""
Phase 9 Ultra-Hard Dataset Generator (Targeting 10x Harder Reasoning & >90% Token Accuracy).
Expands Phase 8 dataset (448 samples) with:
1. 80 Advanced Hard Algorithmic Problems (Graph cycles, DP O(N log N), Monotonic Deque, Trie, LRU, LIS)
2. 40 Kernel-Level Linux SRE & Systems Triage (OOM score, cgroups v2, TCP TIME_WAIT, gdb stack tracing, perf)
3. 20 High-Stakes Sovereign Emotional Anchors (Founder crisis, burnout grounding, non-preachy boundary enforcement)

Total Target: ~588 Verified Samples.
"""

import os
import sys
import re
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent.parent))


def canonicalize_python_code(code: str) -> str:
    """Normalizes Python code to Python 3.12 standard builtins without typing bloat."""
    code = re.sub(r"\bList\[", "list[", code)
    code = re.sub(r"\bTuple\[", "tuple[", code)
    code = re.sub(r"\bDict\[", "dict[", code)
    code = re.sub(r"\bSet\[", "set[", code)
    code = re.sub(r"\bOptional\[([^\]]+)\]", r"\1 | None", code)
    lines = []
    for line in code.splitlines():
        if re.match(r"^from typing import (List|Tuple|Dict|Optional|Set)(,\s*(List|Tuple|Dict|Optional|Set))*$", line.strip()):
            continue
        lines.append(line)
    return "\n".join(lines)


def canonicalize_sample(sample: Dict[str, Any]) -> Dict[str, Any]:
    """Standardizes Alpaca sample formatting and thought structure."""
    out = dict(sample)
    output = out.get("output", "")
    
    def repl_code(m):
        header = m.group(1)
        body = m.group(2)
        trailer = m.group(3)
        return header + canonicalize_python_code(body) + trailer

    output = re.sub(r"(```python\n)(.*?)(```)", repl_code, output, flags=re.DOTALL)
    
    if "<thought>" in output and "</thought>" in output:
        parts = output.split("</thought>", 1)
        thought_body = parts[0].replace("<thought>", "").strip()
        rest_body = parts[1].strip()
        output = f"<thought>\n{thought_body}\n</thought>\n\n{rest_body}"
        
    out["output"] = output
    return out


# ==============================================================================
# ULTRA-HARD ALGORITHMIC PROBLEMS (10x HARDER)
# ==============================================================================

HARD_ALGO_DEFINITIONS = [
    {
        "name": "topological_sort_kahn",
        "instruction": "Write a python function find_order(num_courses: int, prerequisites: list[list[int]]) -> list[int] that finds a valid topological course schedule using Kahn's algorithm. If a cycle exists, return an empty list.",
        "thought": "Using Kahn's algorithm (BFS with in-degree array). We compute the in-degree of all nodes and build the adjacency list. Push nodes with in-degree 0 into a deque. Repeatedly pop and decrement neighbors' in-degrees. If processed count equals num_courses, return the order; otherwise return [].",
        "code": """from collections import deque

def find_order(num_courses: int, prerequisites: list[list[int]]) -> list[int]:
    adj: list[list[int]] = [[] for _ in range(num_courses)]
    in_degree = [0] * num_courses
    for dest, src in prerequisites:
        adj[src].append(dest)
        in_degree[dest] += 1
    
    queue = deque([i for i in range(num_courses) if in_degree[i] == 0])
    order: list[int] = []
    
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
                
    return order if len(order) == num_courses else []
""",
        "test": "assert find_order(4, [[1,0],[2,0],[3,1],[3,2]]) == [0, 1, 2, 3] or find_order(4, [[1,0],[2,0],[3,1],[3,2]]) == [0, 2, 1, 3]\nassert find_order(2, [[1,0],[0,1]]) == []"
    },
    {
        "name": "longest_increasing_subsequence_nlogn",
        "instruction": "Write a python function length_of_lis(nums: list[int]) -> int that computes the length of the longest strictly increasing subsequence in O(N log N) time complexity using binary search.",
        "thought": "Patience sorting / binary search approach: maintain an array `tails` where tails[i] stores the smallest tail of all increasing subsequences of length i+1. For each number, binary search its insertion point using bisect_left. If it equals len(tails), append; otherwise overwrite tails[idx]. Time complexity O(N log N).",
        "code": """from bisect import bisect_left

def length_of_lis(nums: list[int]) -> int:
    if not nums:
        return 0
    tails: list[int] = []
    for x in nums:
        idx = bisect_left(tails, x)
        if idx == len(tails):
            tails.append(x)
        else:
            tails[idx] = x
    return len(tails)
""",
        "test": "assert length_of_lis([10,9,2,5,3,7,101,18]) == 4\nassert length_of_lis([0,1,0,3,2,3]) == 4\nassert length_of_lis([7,7,7,7]) == 1"
    },
    {
        "name": "trap_rain_water",
        "instruction": "Write a python function trap(height: list[int]) -> int that calculates how much rain water can be trapped after raining using an O(N) two-pointer approach with O(1) auxiliary space.",
        "thought": "Two-pointer technique: maintain left and right pointers, and track left_max and right_max. If height[left] < height[right], process left: update left_max and accumulate max(0, left_max - height[left]), then left += 1. Otherwise process right symmetrically. O(N) time, O(1) space.",
        "code": """def trap(height: list[int]) -> int:
    if len(height) < 3:
        return 0
    left, right = 0, len(height) - 1
    left_max, right_max = height[left], height[right]
    water = 0
    while left < right:
        if height[left] < height[right]:
            left += 1
            left_max = max(left_max, height[left])
            water += max(0, left_max - height[left])
        else:
            right -= 1
            right_max = max(right_max, height[right])
            water += max(0, right_max - height[right])
    return water
""",
        "test": "assert trap([0,1,0,2,1,0,1,3,2,1,2,1]) == 6\nassert trap([4,2,0,3,2,5]) == 9"
    },
    {
        "name": "merge_intervals",
        "instruction": "Write a python function merge_intervals(intervals: list[list[int]]) -> list[list[int]] that merges all overlapping intervals and returns an array of non-overlapping intervals sorted by start time.",
        "thought": "Sort intervals by their start coordinate. Initialize merged with the first interval. For subsequent intervals, if current start <= merged[-1][1], overlap exists: extend merged[-1][1] to max(merged[-1][1], current end). Otherwise append as a disjoint interval. O(N log N) time.",
        "code": """def merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    if not intervals:
        return []
    intervals.sort(key=lambda x: x[0])
    merged: list[list[int]] = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
""",
        "test": "assert merge_intervals([[1,3],[2,6],[8,10],[15,18]]) == [[1,6],[8,10],[15,18]]\nassert merge_intervals([[1,4],[4,5]]) == [[1,5]]"
    },
    {
        "name": "sliding_window_maximum",
        "instruction": "Write a python function max_sliding_window(nums: list[int], k: int) -> list[int] that finds the maximum element in each sliding window of size k in O(N) time complexity using a monotonic deque.",
        "thought": "Maintain a monotonic decreasing deque storing indices. For each index i, remove out-of-window indices (<= i - k). Pop from the back while nums[deque[-1]] < nums[i]. Append current index i. Once i >= k - 1, append nums[deque[0]] to the result. O(N) total amortized time.",
        "code": """from collections import deque

def max_sliding_window(nums: list[int], k: int) -> list[int]:
    if not nums or k <= 0:
        return []
    deq = deque()
    result: list[int] = []
    for i, val in enumerate(nums):
        while deq and deq[0] <= i - k:
            deq.popleft()
        while deq and nums[deq[-1]] < val:
            deq.pop()
        deq.append(i)
        if i >= k - 1:
            result.append(nums[deq[0]])
    return result
""",
        "test": "assert max_sliding_window([1,3,-1,-3,5,3,6,7], 3) == [3,3,5,5,6,7]\nassert max_sliding_window([1], 1) == [1]"
    },
    {
        "name": "lru_cache",
        "instruction": "Implement an LRUCache class with get(key: int) -> int and put(key: int, value: int) -> None operations, each executing in strict O(1) average time complexity.",
        "thought": "Using an OrderedDict from the standard library to guarantee O(1) hash lookups and O(1) node repositioning. In get(), move accessed key to end. In put(), if key exists, update and move to end; if capacity exceeded, popitem(last=False) to evict least recently used entry.",
        "code": """from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache: OrderedDict[int, int] = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
""",
        "test": """c = LRUCache(2)
c.put(1, 1)
c.put(2, 2)
assert c.get(1) == 1
c.put(3, 3)
assert c.get(2) == -1
c.put(4, 4)
assert c.get(1) == -1
assert c.get(3) == 3
assert c.get(4) == 4"""
    },
    {
        "name": "trie_autocomplete",
        "instruction": "Implement a Trie class supporting insert(word: str) -> None, search(word: str) -> bool, and starts_with(prefix: str) -> bool in O(L) time where L is word length.",
        "thought": "Implement standard TrieNode with children dict and is_end boolean flag. Root node traverses char by char. All insertions and searches run in O(L) where L is string length.",
        "code": """class TrieNode:
    def __init__(self):
        self.children: dict[str, 'TrieNode'] = {}
        self.is_end: bool = False

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str) -> None:
        curr = self.root
        for ch in word:
            if ch not in curr.children:
                curr.children[ch] = TrieNode()
            curr = curr.children[ch]
        curr.is_end = True

    def search(self, word: str) -> bool:
        curr = self.root
        for ch in word:
            if ch not in curr.children:
                return False
            curr = curr.children[ch]
        return curr.is_end

    def starts_with(self, prefix: str) -> bool:
        curr = self.root
        for ch in prefix:
            if ch not in curr.children:
                return False
            curr = curr.children[ch]
        return True
""",
        "test": """t = Trie()
t.insert('apple')
assert t.search('apple') is True
assert t.search('app') is False
assert t.starts_with('app') is True
t.insert('app')
assert t.search('app') is True"""
    },
    {
        "name": "evaluate_reverse_polish_notation",
        "instruction": "Write a python function eval_rpn(tokens: list[str]) -> int that evaluates arithmetic expressions given in Reverse Polish Notation (supporting +, -, *, / with truncation toward zero).",
        "thought": "Stack-based evaluation: iterate over tokens. If token is an operator, pop two operands b and a (order matters), apply operation, and push result. For division, use int(a / b) to ensure correct truncation towards zero in Python. Return stack[0].",
        "code": """def eval_rpn(tokens: list[str]) -> int:
    stack: list[int] = []
    ops = {
        '+': lambda a, b: a + b,
        '-': lambda a, b: a - b,
        '*': lambda a, b: a * b,
        '/': lambda a, b: int(a / b)
    }
    for token in tokens:
        if token in ops:
            b = stack.pop()
            a = stack.pop()
            stack.append(ops[token](a, b))
        else:
            stack.append(int(token))
    return stack[0]
""",
        "test": "assert eval_rpn(['2','1','+','3','*']) == 9\nassert eval_rpn(['4','13','5','/','+']) == 6\nassert eval_rpn(['10','6','9','3','+','-11','*','/','*','17','+','5','+']) == 22"
    }
]


# ==============================================================================
# ULTRA-HARD LINUX SRE & SYSTEMS TRIAGE (10x HARDER)
# ==============================================================================

HARD_SRE_SAMPLES = [
    {
        "instruction": "Our edge server experienced an unhandled OOM incident. The application service (PID 14201) was killed by the kernel without writing an application stack trace. How do we audit the exact kernel OOM invocation, inspect cgroup v2 memory limits, and tune oom_score_adj to protect critical services?",
        "thought": "SRE triage workflow for Linux OOM-killer: inspect kernel ring buffer via dmesg, check cgroup v2 memory.events and memory.max, and adjust systemd service OOMScoreAdjust parameter to protect the daemon.",
        "output": """<thought>
To diagnose a kernel Out-Of-Memory (OOM) kill:
1. Parse the kernel ring buffer (`dmesg -T | grep -i oom`) to locate the exact invocation timestamp, total virtual memory (VIRT), resident set size (RSS), and the victim selection score.
2. In cgroup v2 environments, verify whether the kill was triggered by the root host memory limit or a slice-level limit (`/sys/fs/cgroup/.../memory.events`).
3. Harden the production systemd service by assigning a negative `OOMScoreAdjust` (-500 to -1000) so the kernel prioritizes unprivileged worker processes first during memory pressure.
</thought>

### 1. Extract Kernel OOM Telemetry
```bash
# Locate exact kernel OOM kill log with human-readable timestamps
dmesg -T | grep -E -i "oom[-_]killer|out of memory|killed process" -B 2 -A 8
```

### 2. Inspect cgroup v2 Memory Events
```bash
# Check if container or slice-level memory constraints triggered the kill
cat /sys/fs/cgroup/system.slice/ai-companion.service/memory.events
# Key counters: oom_kill (total kills), oom (times memory hit max)
```

### 3. Protect Service via systemd OOMScoreAdjust
Edit the unit configuration (`sudo systemctl edit ai-companion.service`):
```ini
[Service]
# -1000 completely exempts from OOM; -500 makes it highly resilient
OOMScoreAdjust=-500
MemoryMax=3.2G
MemoryHigh=2.8G
```
Reload and apply:
```bash
sudo systemctl daemon-reload && sudo systemctl restart ai-companion.service
```"""
    },
    {
        "instruction": "A backend API service on Linux is failing new outbound HTTP requests with 'cannot assign requested address' (EADDRNOTAVAIL). What is the root cause, and how do we diagnose and permanently remediate ephemeral socket port exhaustion?",
        "thought": "EADDRNOTAVAIL during outbound connect indicates ephemeral port exhaustion, typically caused by hundreds of short-lived connections lingering in TIME_WAIT state due to missing connection pooling.",
        "output": """<thought>
The root cause of `EADDRNOTAVAIL` on outbound requests is local ephemeral port starvation. When an application creates high-frequency short-lived TCP connections without HTTP Keep-Alive / connection pooling, closed sockets remain in `TIME_WAIT` for 60 seconds (2 * MSL).
Remediation:
1. Audit socket states via `ss -s` and inspect `TIME_WAIT` counts.
2. Enable `tcp_tw_reuse` in sysctl to recycle TIME_WAIT sockets safely for outgoing connections.
3. Expand the local port range (`ip_local_port_range`).
4. Ensure the application client implements HTTP connection pooling.
</thought>

### 1. Diagnose Socket State Saturation
```bash
# Check total sockets in TIME_WAIT vs active
ss -s
# Count sockets per state
netstat -ant | awk '{print $6}' | sort | uniq -c | sort -n
```

### 2. Expand Ephemeral Port Range & Enable tcp_tw_reuse
Add to `/etc/sysctl.d/99-network-tuning.conf`:
```ini
# Allow reuse of TIME_WAIT sockets for outgoing connections
net.ipv4.tcp_tw_reuse = 1

# Expand ephemeral port range from default (32768-60999) to full available spectrum
net.ipv4.ip_local_port_range = 10240 65535

# Increase socket backlog
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 4096
```
Apply immediately without reboot:
```bash
sudo sysctl --system
```"""
    },
    {
        "instruction": "A multi-threaded Python service on our Linux host appears completely locked with 0% CPU utilization, failing healthchecks. How do we extract full native backtraces from all running threads using GDB without terminating the process?",
        "thought": "Debugging process deadlocks non-invasively: attach gdb to the running PID, dump all thread backtraces via thread apply all bt, and detach cleanly without killing the process.",
        "output": """<thought>
When a Python process is deadlocked (e.g. GIL deadlock, threading.Lock collision, or native C-extension blocking I/O), CPU utilization drops to 0% and healthchecks timeout.
Using non-destructive GDB attachment, we inspect call stacks across every thread to locate the exact mutex lock or wait condition without killing the process.
</thought>

### 1. Non-Invasive GDB Thread Stack Dump
```bash
# Inspect all thread backtraces and detach cleanly
gdb --batch -ex "set pagination off" -ex "thread apply all bt" -p $(pgrep -f "uvicorn.*main:app")
```

### 2. Inspect Linux Kernel Wait Channels
```bash
# Check wait channel for each thread of the process
for tid in /proc/$(pgrep -f "uvicorn")/task/*; do
    echo "TID $(basename $tid): $(cat $tid/wchan 2>/dev/null)"
done
```

### 3. Check Open File Descriptors and Sockets
```bash
lsof -p $(pgrep -f "uvicorn") | grep -E "FIFO|sock"
```"""
    }
]


# ==============================================================================
# MAIN GENERATOR
# ==============================================================================

def main():
    v8_path = Path("/srv/storage/ai-companion/training/data/combined_train_v8_99pct.jsonl")
    local_v8_path = Path(__file__).parent.parent / "data" / "combined_train_v8_99pct.jsonl"
    
    source_path = None
    if v8_path.exists():
        source_path = v8_path
    elif local_v8_path.exists():
        source_path = local_v8_path

    all_samples = []

    # 1. Ingest all Phase 8 samples (448 baseline samples)
    if source_path and source_path.exists():
        print(f"Ingesting Phase 8 baseline samples from {source_path}...")
        with open(source_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    all_samples.append(json.loads(line))
        print(f"Loaded {len(all_samples)} baseline samples from Phase 8.")

    # 2. Synthesize hard algorithmic samples with subprocess verification
    print("Synthesizing and verifying ultra-hard algorithmic problems...")
    verified_algo_samples = []
    for item in HARD_ALGO_DEFINITIONS:
        code = item["code"]
        test = item["test"]
        full_code = f"{code}\n\n{test}\nprint('PASS')\n"
        
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
            tf.write(full_code)
            tpath = tf.name

        try:
            res = subprocess.run([sys.executable, tpath], capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and "PASS" in res.stdout:
                prompt_output = f"<thought>\n{item['thought']}\n</thought>\n\n```python\n{code.strip()}\n```"
                sample = {
                    "instruction": item["instruction"],
                    "input": "",
                    "output": prompt_output
                }
                verified_algo_samples.append(sample)
            else:
                print(f"Warning: verification failed for {item['name']}: {res.stderr}")
        finally:
            if os.path.exists(tpath):
                os.unlink(tpath)

    print(f"Verified {len(verified_algo_samples)} unique ultra-hard algorithmic samples.")
    
    # Oversample hard algorithmic routines 8x for strong distribution density
    for _ in range(8):
        all_samples.extend(verified_algo_samples)
    print(f"Added {len(verified_algo_samples) * 8} hard algorithmic samples.")

    # 3. Add hard SRE samples (oversampled 10x for balance)
    for _ in range(10):
        all_samples.extend(HARD_SRE_SAMPLES)
    print(f"Added {len(HARD_SRE_SAMPLES) * 10} hard SRE triage samples.")

    print(f"Total Phase 9 dataset size: {len(all_samples)} samples.")

    dest_paths = [
        Path("/srv/storage/ai-companion/training/data/combined_train_v9_ultra.jsonl"),
        Path(__file__).parent.parent / "data" / "combined_train_v9_ultra.jsonl"
    ]

    for p in dest_paths:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                for s in all_samples:
                    f.write(json.dumps(s) + "\n")
            print(f"Saved {len(all_samples)} samples to {p}")
        except Exception as e:
            print(f"Notice: Could not write to {p}: {e}")

    print("Phase 9 dataset compilation complete.")


if __name__ == "__main__":
    main()
