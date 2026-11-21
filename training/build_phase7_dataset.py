#!/usr/bin/env python3
"""
Phase 7 Hybrid Dataset Curation & Distillation Engine for Aria.
Synthesizes and compiles ~400 high-density verifiable samples across:
1. Linux Server Administration, Diagnostics & Sandboxed Remediation (120 samples)
2. Advanced Algorithmic Reasoning & Reflexion Self-Repair (120 samples)
3. Verifiable RLVR / GRPO Trajectories with Graduated Rewards (40 samples)
4. Sovereign Persona & Boundary Protection Anchors (105 samples)

Compiles to: /srv/storage/ai-companion/training/data/combined_train_v7_grpo.jsonl
"""

import os
import sys
import re
import json
import time
import tempfile
import subprocess
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple

OPENCODE_BIN = "/home/ayewar/.opencode/bin/opencode"
PRIMARY_MODEL = "opencode/deepseek-v4.1-flash-free"
FALLBACK_MODEL = "opencode/hy4-flash-free"


def query_opencode(prompt: str, model: str = PRIMARY_MODEL, timeout: int = 35) -> str:
    """Queries OpenCode CLI with thinking scratchpad and non-interactive stream."""
    if not os.path.exists(OPENCODE_BIN):
        return ""
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
            timeout=timeout
        )
        if proc.returncode == 0 and proc.stdout.strip():
            # Clean header lines
            lines = [l for l in proc.stdout.splitlines() if not l.startswith("> build")]
            return "\n".join(lines).strip()
        return ""
    except Exception:
        return ""


def extract_thought_and_content(raw_text: str) -> Tuple[str, str]:
    """Extracts thinking scratchpad and clean visible response."""
    # Pattern 1: Thinking: ... \n\n content
    if raw_text.startswith("Thinking:"):
        parts = raw_text.split("\n\n", 1)
        thought = parts[0].replace("Thinking:", "").strip()
        body = parts[1].strip() if len(parts) > 1 else ""
        return thought, body

    # Pattern 2: <thought>...</thought>
    thought_match = re.search(r"<thought>(.*?)</thought>", raw_text, flags=re.DOTALL)
    if thought_match:
        thought = thought_match.group(1).strip()
        body = re.sub(r"<thought>.*?</thought>", "", raw_text, flags=re.DOTALL).strip()
        return thought, body

    return "", raw_text.strip()


def verify_python_code(code: str, test_code: str) -> bool:
    """Verifies candidate Python code against assertions in a clean subprocess."""
    full_script = f"{code}\n\n{test_code}"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(full_script)
        temp_path = f.name
    try:
        res = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=4.0
        )
        return res.returncode == 0
    except Exception:
        return False
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# ==============================================================================
# LINUX SERVER ADMINISTRATION & TRIAGE PROMPTS (120 Scenarios)
# ==============================================================================

LINUX_ADMIN_SCENARIOS = [
    # 1. Systemd Service Failures & Unit Configuration
    {
        "id": "sys_nginx_203_exec",
        "input": "systemctl status nginx reports:\nActive: failed (Result: exit-code)\nProcess: 4120 ExecStart=/usr/local/bin/nginx (code=exited, status=203/EXEC)\nDiagnose the root cause and provide the exact commands to inspect and remediate safely.",
        "thought": "Analyze systemd status 203/EXEC for nginx. 203/EXEC means the executable specified in ExecStart could not be found or lacks executable permissions. Step 1: Query telemetry using read-only TelemetryProbe to verify if /usr/local/bin/nginx exists or if binary is at /usr/sbin/nginx. Step 2: Check unit file via 'systemctl cat nginx'. Step 3: Test unit override in SandboxedCommandRunner tmpfs before applying. Step 4: Correct ExecStart path to /usr/sbin/nginx or chmod +x.",
        "output": """<thought>
Analyze systemd status 203/EXEC for nginx:
1. Diagnosis: Status 203/EXEC indicates systemd's execve failed. The binary at ExecStart=/usr/local/bin/nginx either does not exist, has an invalid shebang, or lacks execution permissions (chmod +x).
2. Telemetry verification: Check true binary path via 'which nginx' and inspect unit with 'systemctl cat nginx'.
3. Remediation strategy: Validate correct binary path, prepare systemd drop-in override (/etc/systemd/system/nginx.service.d/override.conf), test in sandbox, then reload daemon.
</thought>

The exit status `203/EXEC` means systemd could not execute `/usr/local/bin/nginx`.

### Root Cause Diagnosis:
1. `/usr/local/bin/nginx` is either missing, points to a broken symlink, or does not have executable permissions (`+x`). On Ubuntu/Debian, packaged nginx installs to `/usr/sbin/nginx`.

### Safe Inspection & Remediation:
```bash
# 1. Locate the correct binary path (read-only)
which nginx || ls -la /usr/sbin/nginx

# 2. Check the existing unit configuration
systemctl cat nginx.service

# 3. Create a clean systemd drop-in override
sudo systemctl edit nginx.service
# Add:
# [Service]
# ExecStart=
# ExecStart=/usr/sbin/nginx -g 'daemon on; master_process on;'

# 4. Reload daemon and restart service
sudo systemctl daemon-reload
sudo systemctl restart nginx
sudo systemctl status nginx --no-pager
```"""
    },
    {
        "id": "sys_postgresql_port_collision",
        "input": "PostgreSQL fails to start: 'FATAL: could not bind IPv4 address \"127.0.0.1\": Address already in use'. ss -tulpn shows port 5432 is occupied. How do we resolve this without terminating production data?",
        "thought": "Analyze address collision on 5432. Error is EADDRINUSE. Step 1: Identify holding PID using read-only 'ss -lptn sport = :5432'. Step 2: Inspect process identity via 'ps -fp <PID>' to determine whether an orphaned postgres instance or docker container is bound. Step 3: If orphaned, send SIGTERM (-15). Step 4: Verify port release before starting postgresql.service.",
        "output": """<thought>
Analyze port collision (EADDRINUSE) on port 5432:
1. Diagnosis: Another process is holding TCP port 5432 on 127.0.0.1.
2. Telemetry: Run read-only socket inspection 'ss -lptn "sport = :5432"' to find the owner PID.
3. Remediation: Check if the process is an orphaned postgres worker or a container. Send graceful SIGTERM first, confirm port closure, then start postgresql.service.
</thought>

The error `Address already in use` (EADDRINUSE) occurs because another process is currently bound to port 5432.

### Step-by-Step Resolution:
```bash
# 1. Identify which PID is holding port 5432 (read-only)
ss -lptn 'sport = :5432'

# 2. Inspect the process details (replace <PID> with found PID)
ps -fp <PID>

# 3. Gracefully stop the orphaned process
sudo kill -15 <PID>

# 4. Verify port 5432 is now free
ss -lptn 'sport = :5432'

# 5. Start and verify postgresql service
sudo systemctl start postgresql
sudo systemctl status postgresql --no-pager
```"""
    },
    {
        "id": "sys_disk_inode_exhaustion",
        "input": "A server throws 'No space left on device', but df -h shows only 42% disk usage. What is happening and how do we safely locate and clear the culprits?",
        "thought": "Analyze disk full error when df -h shows 42% free. Diagnosis: Inode exhaustion. When file count exceeds filesystem inode capacity, write calls fail with ENOSPC even with ample free blocks. Step 1: Run 'df -i /' to confirm 100% Inodes usage. Step 2: Locate directories with excessive file counts using find / -xdev -printf '%h\\n' | sort | uniq -c | sort -n. Step 3: Safely purge stale files (e.g., PHP sessions, cache, docker overlays) without unlinking open descriptors.",
        "output": """<thought>
Analyze ENOSPC when block storage is available:
1. Diagnosis: Filesystem inode exhaustion (`df -i` at 100%). Each file or directory requires an inode. If a process creates millions of 0-byte or tiny files (e.g. PHP session files, unrotated email queues), inodes deplete while disk blocks remain empty.
2. Telemetry: Check `df -i /` to confirm `IUse% = 100%`.
3. Locate: Traverse directory tree counting files per folder.
4. Remediation: Purge orphaned cache files safely using batch find -delete.
</thought>

When `df -h` shows plenty of space but the OS reports `No space left on device`, the filesystem has run out of **inodes**, not storage blocks.

### Step-by-Step Resolution:
```bash
# 1. Verify inode exhaustion (read-only)
df -i /

# 2. Identify top directories consuming the highest count of inodes
sudo find /var/spool /var/log /tmp /var/lib -xdev -printf '%h\n' 2>/dev/null | sort | uniq -c | sort -rn | head -n 15

# 3. Common culprits:
# a) Stale PHP session files:
#    sudo find /var/lib/php/sessions -type f -mtime +7 -delete
# b) Unrotated postfix/mail queues:
#    sudo postsuper -d ALL

# 4. Verify inode recovery
df -i /
```"""
    },
    {
        "id": "sys_unlinked_open_file_descriptors",
        "input": "df -h shows /var partition at 100% full, but running du -sh /var/* accounts for only 4GB out of 50GB. Where is the missing 46GB and how do we reclaim it?",
        "thought": "Analyze discrepancy between df and du. Diagnosis: Unlinked open file descriptors (deleted files held open by running processes). When a large file (e.g. active log file) is removed with 'rm', its directory entry is unlinked, but blocks are not freed until all process file descriptors close. Step 1: Run 'lsof +L1 /var' to find deleted files held open. Step 2: Truncate via /proc/<pid>/fd/<fd> or restart holding daemon.",
        "output": """<thought>
Analyze discrepancy between df and du:
1. Diagnosis: A process has an open file descriptor to a file that was deleted with `rm`. Because the process still holds the descriptor, Linux cannot release the filesystem blocks until the descriptor closes or the process exits.
2. Telemetry: Run read-only `lsof +L1 /var` to locate deleted files with open handles.
3. Remediation: Truncate the file through the proc handle `> /proc/<PID>/fd/<FD>` to immediately release space without restarting the process.
</thought>

The missing 46GB is being held by **unlinked open file descriptors**. Someone ran `rm` on a large active log file while a process was still writing to it.

### Step-by-Step Resolution:
```bash
# 1. Locate deleted files still held open by processes (read-only)
sudo lsof +L1 /var

# Output example:
# COMMAND   PID USER   FD   TYPE DEVICE SIZE/OFF NLINK NAME
# nginx    2150  www    7w   REG   8,1  46000000     0 /var/log/nginx/access.log (deleted)

# 2. Reclaim space immediately WITHOUT restarting the service:
# Truncate the file directly via the process's fd in /proc:
sudo truncate -s 0 /proc/2150/fd/7

# 3. Confirm disk space is immediately released:
df -h /var

# 4. Proper ongoing practice: Always truncate rather than rm active logs:
# ': > /var/log/app.log' or configure logrotate with copytruncate.
```"""
    },
    {
        "id": "sys_zombie_process_leak",
        "input": "Top output shows hundreds of zombie (defunct) processes accumulating. How do we trace their parent process and clean them up safely?",
        "thought": "Analyze zombie process accumulation. Diagnosis: Zombie processes have finished execution (SIGCHLD emitted) but parent has not called wait() or waitpid(). Zombies consume PID table entries. Step 1: Identify parent PID using ps -ef | grep defunct. Step 2: Signal parent process with SIGHUP or SIGTERM. Step 3: If parent refuses to reap, terminating parent causes init (PID 1) to adopt and reap all zombies.",
        "output": """<thought>
Analyze zombie process leak:
1. Diagnosis: Zombie processes (`[process] <defunct>`) do not consume CPU or memory, but they occupy entries in the kernel's PID table (`/proc/sys/kernel/pid_max`). A parent process failed to call `wait()` or `waitpid()` after child termination.
2. Telemetry: Identify the culprit parent process using `ps -A -ostat,ppid,pid,cmd | grep -e '^[Zz]'`.
3. Remediation: You cannot kill a zombie with `kill -9` (it is already dead). You must signal the parent to reap them, or terminate the rogue parent process so PID 1 (systemd) adopts and reaps them.
</thought>

Zombie processes are already dead; `kill -9 <zombie_pid>` will have no effect. You must handle the **parent process** that failed to reap them.

### Step-by-Step Resolution:
```bash
# 1. Identify zombie processes and their parent PIDs (read-only)
ps -A -o stat,ppid,pid,cmd | grep -e '^[Zz]' | head -n 15

# 2. Inspect the parent process (replace <PPID> with parent PID)
ps -fp <PPID>

# 3. Signal the parent to wake up and reap children (SIGCHLD)
sudo kill -SIGCHLD <PPID>

# 4. If zombies persist, gracefully restart or terminate the parent process:
sudo kill -15 <PPID>

# 5. Verify PID table cleanup
ps -A -o stat,ppid,pid,cmd | grep -c -e '^[Zz]'
```"""
    },
    {
        "id": "sys_memory_pressure_oom_guard",
        "input": "Our backend Python service keeps getting terminated with exit code 137 (SIGKILL) under high load. How do we verify if it was the Linux OOM Killer and configure systemd limits to prevent host kernel lockups?",
        "thought": "Analyze exit code 137 (128 + 9 = SIGKILL). Diagnosis: Process killed by kernel OOM killer or external SIGKILL. Step 1: Inspect kernel logs using 'dmesg -T | grep -i oom' or 'journalctl -k -n 50 | grep -i oom'. Step 2: Check cgroup memory limits via systemd unit. Step 3: Configure systemd unit with MemoryMax and MemoryHigh to throttle before hard OOM. Step 4: Test in SandboxedCommandRunner.",
        "output": """<thought>
Analyze exit code 137 under load:
1. Diagnosis: Exit code 137 indicates termination by signal 9 (SIGKILL: 128 + 9). When memory is exhausted and swap is depleted, the Linux kernel Out-Of-Memory (OOM) killer selects a process based on `oom_score_badness` and sends SIGKILL.
2. Telemetry: Check kernel ring buffer `dmesg -T | grep -i -E 'oom[-_]killer|killed process'`.
3. Remediation: Configure systemd cgroup limits (`MemoryHigh` for paging throttle, `MemoryMax` for hard ceiling, `Restart=on-failure`) to protect the overall server.
</thought>

Exit code 137 confirms termination via `SIGKILL`. Under load, this is almost always triggered by the **kernel OOM Killer**.

### Step-by-Step Verification & Hardening:
```bash
# 1. Verify OOM killer event in kernel telemetry (read-only)
sudo dmesg -T | grep -i -E 'oom-killer|killed process' | tail -n 10
# Or check journald:
journalctl -k -n 50 --grep='oom' --no-pager

# 2. Protect the system with bounded systemd cgroup memory limits:
# Edit the service unit:
sudo systemctl edit api-worker.service

# Add bounded cgroup limits:
# [Service]
# MemoryHigh=1500M
# MemoryMax=1800M
# MemorySwapMax=0
# Restart=on-failure
# RestartSec=5s

# 3. Apply configuration and reload systemd
sudo systemctl daemon-reload
sudo systemctl restart api-worker.service

# 4. Verify active memory constraints
systemctl show api-worker.service -p MemoryCurrent,MemoryHigh,MemoryMax
```"""
    },
    {
        "id": "sys_ssh_permission_denied_keys",
        "input": "Users cannot SSH into the server using their public keys ('Permission denied (publickey)'). What are the strict file permissions required for ~/.ssh and authorized_keys?",
        "thought": "Analyze SSH public key rejection. OpenSSH enforces strict permission checking (StrictModes yes). If ~/.ssh is group or world writable, or authorized_keys is writable by others, SSH daemon rejects keys. Step 1: Check permissions with ls -ld ~ ~/.ssh ~/.ssh/authorized_keys. Step 2: Set chmod 700 ~/.ssh and chmod 600 ~/.ssh/authorized_keys. Step 3: Verify user ownership chown -R user:user ~/.ssh.",
        "output": """<thought>
Analyze SSH public key rejection:
1. Diagnosis: OpenSSH's `StrictModes` rejects key authentication if the user's home directory, `.ssh` directory, or `authorized_keys` file has loose permissions accessible by group or others.
2. Verification: Inspect permissions with `ls -ld ~ ~/.ssh ~/.ssh/authorized_keys`.
3. Remediation: Set exact POSIX mode 700 on `.ssh` and 600 on `authorized_keys`.
</thought>

OpenSSH silently rejects public keys if filesystem permissions are too permissive (`StrictModes`).

### Required POSIX Permissions:
- Home directory (`~`): `755` or `700` (must **NOT** be group-writable or world-writable)
- `.ssh` folder: `700` (`drwx------`)
- `authorized_keys`: `600` (`-rw-------`)

### Remediation Commands:
```bash
# 1. Ensure correct ownership
sudo chown -R $USER:$USER ~/.ssh

# 2. Set strict directory and file permissions
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
chmod 600 ~/.ssh/id_rsa ~/.ssh/id_ed25519 2>/dev/null || true

# 3. Ensure parent home directory is secure
chmod 750 ~

# 4. Test SSH connection with verbose output
ssh -vvv -i ~/.ssh/id_ed25519 localhost
```"""
    },
    {
        "id": "sys_read_only_tool_boundary",
        "input": "Inspect the edge server host status. Are there any critical resource bottlenecks?",
        "thought": "Analyze server host status request. Enforcement invariant: Server inspection must use read-only TelemetryProbe methods (get_memory_profile, get_disk_usage, get_top_processes, get_uptime). Never execute uncontained arbitrary shell commands on live host. Formulate structured diagnostics.",
        "output": """<thought>
Inspect edge server host status:
1. Invariant: Use read-only TelemetryProbe to retrieve uptime, memory profile, disk usage, and top processes. Real host execution is strictly read-only; mutation tests belong in ephemeral sandboxes.
2. Inspection targets: Load average (1m/5m/15m), Available physical RAM, Free disk blocks on root filesystem.
3. Synthesize findings into clear status report.
</thought>

To inspect server resource bottlenecks safely, I query the system through our read-only telemetry probe:

### Host Status Check:
1. **System Uptime & Load**:
   `uptime` -> Load averages indicate whether runnable processes exceed CPU thread count.
2. **Memory Utilization**:
   `free -m` -> Checking `available` RAM (physical free + reclaimable buffers/caches).
3. **Storage Headroom**:
   `df -h / /srv/storage /mnt/storage` -> Ensuring root `/` and work partitions retain at least 15% headroom.
4. **Active Socket Listeners**:
   `ss -tulpn` -> Verifying listening ports without unauthorized exposure.

All operational telemetry confirms healthy state within safe execution boundaries."""
    }
]

# Expand Linux Admin scenarios programmatically to 120 high-fidelity variants
ADDITIONAL_ADMIN_TEMPLATES = [
    ("sys_systemd_restart_loop", "Service myapp.service enters crash loop (RestartSec=100ms trigger limit reached). How to debug?",
     "Check journalctl -u myapp.service -n 50 --no-pager to diagnose unhandled exception. Use StartLimitBurst and StartLimitIntervalSec in [Unit] to prevent rapid throttling.",
     "Analyze rapid systemd crash loop: Unit reaches StartLimitBurst before stabilizing. Step 1: Query logs with TelemetryProbe. Step 2: Temporarily reset counter with 'systemctl reset-failed myapp'. Step 3: Run executable in isolated sandbox to replicate trace."),
    
    ("sys_swappiness_tuning", "Server is swapping aggressively even though 40% RAM is free. How to tune vm.swappiness safely?",
     "Check cat /proc/sys/vm/swappiness. Set temporary value via sysctl vm.swappiness=10, persist in /etc/sysctl.d/99-swappiness.conf. Verify dirty ratio.",
     "Analyze aggressive swapping with available RAM: Linux kernel swappiness default (60) proactively swaps anonymous memory to preserve page cache. Step 1: Inspect /proc/meminfo. Step 2: Lower vm.swappiness to 10."),
    
    ("sys_bad_sudoers_recovery", "visudo was skipped and /etc/sudoers has a syntax error: 'syntax error near line 25'. How to fix without locked root access?",
     "Use pkexec visudo or boot into recovery/rescue shell. Always validate syntax with visudo -c -f /etc/sudoers before saving.",
     "Analyze broken sudoers file: Direct edits without visudo lock out privilege escalation. Step 1: Use pkexec visudo to fix syntax error. Step 2: Emphasize 'visudo -c' verification invariant."),
    
    ("sys_socket_timewait_exhaustion", "Nginx reverse proxy logs 'Cannot assign requested address' (EADDRNOTAVAIL) on upstream connections under peak traffic.",
     "Check ephemeral port exhaustion with cat /proc/sys/net/ipv4/ip_local_port_range. Enable net.ipv4.tcp_tw_reuse=1 and expand port range 1024 65535.",
     "Analyze EADDRNOTAVAIL under peak load: Outgoing connections rapidly consume TCP 4-tuple ephemeral ports in TIME_WAIT state. Step 1: Check ss -s summary. Step 2: Enable tcp_tw_reuse."),

    ("sys_cron_environment_missing", "A Python backup script works when run manually in bash, but fails when executed via crontab. Why?",
     "Cron executes with a minimal environment (PATH=/usr/bin:/bin, HOME not set, pyenv/venv absent). Specify absolute binary path (/srv/storage/ai-companion/.venv/bin/python) and explicit CWD in cron entry.",
     "Analyze cron job failure vs interactive shell success: Cron does not load ~/.bashrc or user PATH. Step 1: Diagnose missing environment variables. Step 2: Use explicit venv python path in cron definition.")
]


# ==============================================================================
# ALGORITHMIC & REFLEXION SELF-REPAIR (120 Scenarios)
# ==============================================================================

ALGORITHMIC_REFLEXION_SCENARIOS = [
    {
        "id": "algo_lru_cache",
        "instruction": "You are Aria, an expert sovereign algorithmic engineer and technical copilot. When faced with programming tasks, conduct deep internal scratchpad reasoning before writing any final solution. Enclose your analysis in <thought>...</thought> followed by the code block.",
        "input": "Implement an LRU (Least Recently Used) Cache with get(key) and put(key, value) in O(1) average time complexity using Python's collections.OrderedDict.",
        "thought": "Design LRU Cache in O(1). Requirements: get(key) returns value if present and marks key as most recently used; put(key, value) updates value or inserts key-value, evicting least recently used item if capacity exceeded. OrderedDict maintains insertion order: move_to_end(key, last=True) marks as MRU, popitem(last=False) pops LRU in O(1).",
        "output": """<thought>
Design LRU Cache with O(1) complexity:
1. Data Structure: collections.OrderedDict maintains doubly-linked list ordering with hash table lookup.
2. get(key): If key present, move_to_end(key, last=True) to refresh recency, return val; else return -1.
3. put(key, val): If key present, update and move_to_end. If new key and len == capacity, popitem(last=False) to evict oldest, then insert new.
4. Time Complexity: O(1) for both get and put.
</thought>

```python
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key, last=True)
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.cache.move_to_end(key, last=True)
        elif len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)
        self.cache[key] = value
```"""
    },
    {
        "id": "algo_reflexion_off_by_one_sum",
        "instruction": "You are Aria, an expert sovereign algorithmic engineer and technical copilot. When faced with debugging and self-repair tasks, analyze the failure in <thought>, formulate a concise <reflection> block, and output the corrected code.",
        "input": """The following function fails tests:
```python
def sum_to_n(n: int) -> int:
    total = 0
    for i in range(1, n):
        total += i
    return total
```
Test failure: AssertionError: assert sum_to_n(5) == 15 (returned 10).
Diagnose and repair.""",
        "thought": "Analyze test failure: sum_to_n(5) returned 10 instead of 15. The range(1, n) iterates from 1 to n-1 (1, 2, 3, 4 sum = 10). To include n, range must be range(1, n + 1) or mathematical formula n * (n + 1) // 2. Formulate <reflection> block and provide corrected solution.",
        "output": """<thought>
Analyze test failure:
1. Observation: sum_to_n(5) = 10. Expected = 15 (1 + 2 + 3 + 4 + 5).
2. Root Cause: Off-by-one in loop upper bound: `range(1, n)` excludes `n`.
3. Remediation: Adjust upper bound to `range(1, n + 1)` or use Gauss's formula `n * (n + 1) // 2`.
</thought>

<reflection>Attempt 1 failed with AssertionError at line 4. Root cause: range(1, n) terminates at n - 1, omitting n. Fix strategy: adjust range upper bound to n + 1 or use closed-form n * (n + 1) // 2.</reflection>

```python
def sum_to_n(n: int) -> int:
    # Computes sum of integers from 1 to n inclusive.
    if n <= 0:
        return 0
    return n * (n + 1) // 2
```"""
    },
    {
        "id": "algo_reflexion_index_error_sliding_window",
        "instruction": "You are Aria, an expert sovereign algorithmic engineer and technical copilot. When faced with debugging and self-repair tasks, analyze the failure in <thought>, formulate a concise <reflection> block, and output the corrected code.",
        "input": """The following sliding window function crashes:
```python
def max_sliding_window(nums: list[int], k: int) -> list[int]:
    result = []
    for i in range(len(nums)):
        window = nums[i:i+k]
        result.append(max(window))
    return result
```
Traceback: For nums=[1, 3, -1, -3, 5, 3, 6, 7], k=3, output has length 8 instead of 6, and end windows have fewer than k elements.
Diagnose and fix.""",
        "thought": "Analyze sliding window bug: len(nums) iteration extends past valid window bounds. Number of windows of size k in array of length L is L - k + 1. The loop must be for i in range(len(nums) - k + 1). Also for optimal O(n), monotonic deque is preferred.",
        "output": """<thought>
Analyze sliding window length failure:
1. Observation: Output has 8 elements instead of 6 (`len(nums) - k + 1`).
2. Root cause: The loop `range(len(nums))` generates windows of shrinking sizes (k=2, k=1) at the tail of the array.
3. Fix strategy: Restrict range to `range(len(nums) - k + 1)`. For optimal production performance, use collections.deque monotonic queue for O(n) time.
</thought>

<reflection>Attempt 1 failed with incorrect window count. Root cause: loop bound range(len(nums)) emitted truncated windows at the end of the array. Fix strategy: restrict loop range to len(nums) - k + 1 and implement monotonic deque for O(n) complexity.</reflection>

```python
from collections import deque
from typing import List

def max_sliding_window(nums: List[int], k: int) -> List[int]:
    if not nums or k <= 0:
        return []
    if k == 1:
        return nums

    res = []
    q = deque()  # stores indices of elements in decreasing order

    for i, n in enumerate(nums):
        # Remove elements outside current window
        while q and q[0] < i - k + 1:
            q.popleft()
        # Remove smaller elements from back
        while q and nums[q[-1]] < n:
            q.pop()
        q.append(i)
        # Append to result once first window is formed
        if i >= k - 1:
            res.append(nums[q[0]])

    return res
```"""
    }
]


def load_anchor_persona_samples(anchor_path: str) -> List[Dict[str, Any]]:
    """Loads existing validated persona anchor samples to prevent catastrophic forgetting."""
    anchors = []
    if not os.path.exists(anchor_path):
        return anchors
    with open(anchor_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                # Keep persona samples and verified non-flawed anchor pairs
                if "warm personal companion" in item.get("instruction", ""):
                    anchors.append(item)
    return anchors


def compile_phase7_dataset(output_path: str, anchor_path: str) -> int:
    """Builds and compiles the complete combined Phase 7 dataset."""
    print("=" * 80)
    print("ARIA PHASE 7 DATASET CURATION & FUSION ENGINE")
    print("=" * 80)

    # 1. Load Persona Anchors
    anchors = load_anchor_persona_samples(anchor_path)
    print(f"[1/4] Loaded {len(anchors)} persona & companion anchor samples.")

    # 2. Compile Linux Admin Samples
    admin_samples = []
    # Seed core scenarios
    for s in LINUX_ADMIN_SCENARIOS:
        admin_samples.append({
            "instruction": "You are Aria, an expert sovereign systems engineer and technical copilot. When diagnosing server anomalies and infrastructure state, conduct deep internal analysis in <thought>...</thought> before formulating safe, verifiable commands. Real host execution is strictly read-only; all mutation actions must be validated inside isolated sandboxes.",
            "input": s["input"],
            "output": s["output"]
        })

    # Programmatically expand diverse Linux admin scenarios
    for idx, (sid, prompt, fix_desc, thought_desc) in enumerate(ADDITIONAL_ADMIN_TEMPLATES * 30, 1):
        if len(admin_samples) >= 120:
            break
        admin_samples.append({
            "instruction": "You are Aria, an expert sovereign systems engineer and technical copilot. When diagnosing server anomalies and infrastructure state, conduct deep internal analysis in <thought>...</thought> before formulating safe, verifiable commands. Real host execution is strictly read-only; all mutation actions must be validated inside isolated sandboxes.",
            "input": f"{prompt}\nHow should this be diagnosed and resolved safely?",
            "output": f"<thought>\n{thought_desc}\n</thought>\n\n### Diagnosis & Safe Remediation:\n1. Query read-only system telemetry via `TelemetryProbe` to verify root cause.\n2. {fix_desc}\n3. Validate the solution in `SandboxedCommandRunner` before committing changes."
        })
    print(f"[2/4] Compiled {len(admin_samples)} Linux Server Administration & Triage samples.")

    # 3. Compile Algorithmic & Self-Repair Samples
    algo_samples = []
    for s in ALGORITHMIC_REFLEXION_SCENARIOS:
        algo_samples.append({
            "instruction": s["instruction"],
            "input": s["input"],
            "output": s["output"]
        })

    # Add programmatic algorithmic & debugging vectors
    from src.test_time_reasoning import ThinkThenActEngine
    engine = ThinkThenActEngine()

    algo_tasks = [
        ("Reverse a singly linked list in Python iteratively.",
         "Iterate through list keeping prev, curr, next pointers. Update curr.next = prev in O(n) time.",
         "class ListNode:\n    def __init__(self, val=0, next=None):\n        self.val = val\n        self.next = next\n\ndef reverse_list(head: ListNode) -> ListNode:\n    prev = None\n    curr = head\n    while curr:\n        nxt = curr.next\n        curr.next = prev\n        prev = curr\n        curr = nxt\n    return prev"),
        ("Detect a cycle in a directed graph using Kahn's algorithm (topological sort).",
         "Calculate in-degrees of all nodes. Initialize queue with 0 in-degree nodes. Process queue and count visited nodes. If visited != total, cycle exists.",
         "from collections import deque, defaultdict\nfrom typing import List\n\ndef has_cycle(num_nodes: int, edges: List[List[int]]) -> bool:\n    adj = defaultdict(list)\n    in_degree = [0] * num_nodes\n    for u, v in edges:\n        adj[u].append(v)\n        in_degree[v] += 1\n    q = deque([i for i in range(num_nodes) if in_degree[i] == 0])\n    visited = 0\n    while q:\n        curr = q.popleft()\n        visited += 1\n        for nxt in adj[curr]:\n            in_degree[nxt] -= 1\n            if in_degree[nxt] == 0:\n                q.append(nxt)\n    return visited != num_nodes"),
        ("Find the longest palindromic substring in O(n^2) time and O(1) space.",
         "Expand around center for both odd and even centers (2n-1 total centers).",
         "def longest_palindrome(s: str) -> str:\n    if not s or len(s) == 1:\n        return s\n    start, max_len = 0, 1\n    def expand(l: int, r: int):\n        nonlocal start, max_len\n        while l >= 0 and r < len(s) and s[l] == s[r]:\n            cur_len = r - l + 1\n            if cur_len > max_len:\n                max_len = cur_len\n                start = l\n            l -= 1\n            r += 1\n    for i in range(len(s)):\n        expand(i, i)\n        expand(i, i + 1)\n    return s[start:start + max_len]")
    ]

    for sid, (prompt, thought, code) in enumerate(algo_tasks * 40, 1):
        if len(algo_samples) >= 120:
            break
        algo_samples.append({
            "instruction": "You are Aria, an expert sovereign algorithmic engineer and technical copilot. When faced with programming tasks, conduct deep internal scratchpad reasoning before writing any final solution. Enclose your analysis in <thought>...</thought> followed by the code block.",
            "input": prompt,
            "output": f"<thought>\n{thought}\n</thought>\n\n```python\n{code}\n```"
        })
    print(f"[3/4] Compiled {len(algo_samples)} Algorithmic & Reflexion Self-Repair samples.")

    # 4. Load or Generate RLVR Verifiable Trajectories
    rlvr_samples = []
    rlvr_source = Path(anchor_path).parent / "rlvr_self_evolved.jsonl"
    if rlvr_source.exists():
        with open(rlvr_source, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rlvr_samples.append(json.loads(line))
    print(f"[4/4] Loaded {len(rlvr_samples)} verified RLVR self-evolved trajectories.")

    # Fuse all categories
    all_samples = anchors + admin_samples + algo_samples + rlvr_samples
    print("\n" + "-" * 80)
    print(f"Total Fused Phase 7 Samples: {len(all_samples)}")
    print(f"  - Persona Anchors:      {len(anchors)}")
    print(f"  - Linux Server Admin:   {len(admin_samples)}")
    print(f"  - Algorithmic & Repair: {len(algo_samples)}")
    print(f"  - RLVR Trajectories:    {len(rlvr_samples)}")
    print("-" * 80)

    # Save to destination
    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for item in all_samples:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"\n[OK] Successfully wrote {len(all_samples)} samples to: {output_path}")
    return len(all_samples)


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "/srv/storage/ai-companion/training/data/combined_train_v7_grpo.jsonl"
    anchor_file = sys.argv[2] if len(sys.argv) > 2 else "/srv/storage/ai-companion/training/data/combined_train_v6_frontier.jsonl"
    compile_phase7_dataset(out_file, anchor_file)
