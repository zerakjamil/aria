import os
import re
import shlex
import subprocess
import time
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from pydantic import BaseModel

class BlastRadius(str, Enum):
    READ_ONLY = "read_only"
    WORKSPACE_MUTATION = "workspace_mutation"
    SYSTEM_MUTATION = "system_mutation"
    BLOCKED = "blocked"

class ExecutionResult(BaseModel):
    command: str
    blast_radius: BlastRadius
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    is_safe: bool
    remediation_hint: Optional[str] = None
    security_warning: Optional[str] = None

# Hard-blocked dangerous regexes (instantly aborted)
BLOCKED_PATTERNS = [
    r"\brm\s+-(?:r|f|rf|fr)\s+/(?:\s|$|\*)",       # rm -rf /
    r"\brm\s+-(?:r|f|rf|fr)\s+~(?:\s|$|\*)",       # rm -rf ~
    r"\bmkfs(?:\.\w+)?\b",                          # formatting filesystems
    r"\bdd\s+if=",                                  # direct disk writes
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",  # fork bomb
    r"\bshutdown\b",                                # system shutdown
    r"\breboot\b",                                  # system reboot
    r"\binit\s+[06]\b",                             # init runlevel shutdown
    r"\bchmod\s+(?:-R\s+)?777\s+/(?:\s|$)",        # dangerous global chmod
    r"\bchown\s+(?:-R\s+)?\w+\s+/(?:\s|$)",        # dangerous global chown
    r"\b(?:mkswap|swapon|swapoff)\b",              # swap destruction
    r"\bkillall\s+(?:systemd|init|sshd)\b",        # killing init or ssh
    r"\bsystemctl\s+stop\s+(?:ssh|sshd)\b",        # disabling remote access
    r"\bDROP\s+DATABASE\b",                         # raw database drops
    r">\s*/dev/sd[a-z]",                            # raw block device redirection
]

# Read-only commands (safe to run freely)
READ_ONLY_COMMANDS = {
    "echo", "printf", "ls", "cat", "head", "tail", "grep", "egrep", "fgrep",
    "find", "pwd", "whoami", "id", "uptime", "df", "free",
    "uname", "ps", "top", "htop", "which", "whereis", "file",
    "stat", "wc", "sort", "uniq", "diff", "git status", "git diff",
    "git log", "git show", "git branch", "docker ps", "docker images",
    "systemctl status", "journalctl", "ip", "ifconfig", "netstat",
    "ss", "curl -I", "curl -sI", "ping -c"
}

# Workspace mutation commands
WORKSPACE_COMMANDS = {
    "mkdir", "touch", "cp", "mv", "rm", "git add", "git commit",
    "git checkout", "git merge", "git stash", "pytest", "python",
    "python3", "pytest", "npm test", "npm run", "cargo check",
    "cargo test", "cargo build", "make", "tar", "gzip", "unzip"
}

class CommandClassifier:
    @staticmethod
    def classify(command: str) -> Tuple[BlastRadius, Optional[str]]:
        cmd_clean = command.strip()
        if not cmd_clean:
            return BlastRadius.BLOCKED, "Command is empty"

        # 1. Check for blocked malicious or destructive patterns
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, cmd_clean, re.IGNORECASE):
                return BlastRadius.BLOCKED, f"Command matched forbidden destructive pattern: {pattern}"

        # 2. Check for pipe-to-shell or curl-to-bash vulnerabilities
        if re.search(r"curl\s+.*?\|\s*(?:bash|sh|zsh)\b", cmd_clean) or re.search(r"wget\s+.*?\|\s*(?:bash|sh|zsh)\b", cmd_clean):
            return BlastRadius.BLOCKED, "Piping unverified web scripts to a shell interpreter is strictly prohibited."

        # 3. Check for base binary in read-only set
        try:
            tokens = shlex.split(cmd_clean)
        except Exception:
            tokens = cmd_clean.split()

        if not tokens:
            return BlastRadius.BLOCKED, "Malformed command structure"

        first_token = Path(tokens[0]).name

        # Compound git or systemctl check
        if len(tokens) >= 2:
            compound = f"{first_token} {tokens[1]}"
            if compound in READ_ONLY_COMMANDS:
                return BlastRadius.READ_ONLY, None

        if first_token in READ_ONLY_COMMANDS:
            # Check if redirection operator is present (e.g. > or >>) which turns read into write
            if any(op in tokens for op in [">", ">>", "| tee"]):
                return BlastRadius.WORKSPACE_MUTATION, None
            return BlastRadius.READ_ONLY, None

        if first_token in WORKSPACE_COMMANDS:
            return BlastRadius.WORKSPACE_MUTATION, None

        # System operations (e.g. apt, systemctl, docker)
        if first_token in {"systemctl", "docker", "pip", "npm", "apt", "apt-get", "curl", "wget"}:
            return BlastRadius.SYSTEM_MUTATION, None

        return BlastRadius.WORKSPACE_MUTATION, None


class SelfHealingEngine:
    @staticmethod
    def diagnose_failure(command: str, stderr: str, exit_code: int) -> Optional[str]:
        """
        Analyzes common Linux/Python/Git execution failures and produces
        targeted, actionable remediation advice.
        """
        err_lower = stderr.lower()

        # 1. Missing Python module
        match = re.search(r"ModuleNotFoundError:\s+No module named ['\"]([^'\"]+)['\"]", stderr)
        if match:
            missing_pkg = match.group(1)
            return f"Missing dependency '{missing_pkg}'. Run: pip install {missing_pkg} (or check virtualenv activation)."

        # 2. Port already bound
        if "address already in use" in err_lower or "err_address_in_use" in err_lower:
            port_match = re.search(r":(\d+)", stderr)
            port_str = port_match.group(1) if port_match else "PORT"
            return f"Port {port_str} is already occupied. Identify the process with: lsof -i :{port_str} and stop it."

        # 3. Permission denied
        if "permission denied" in err_lower:
            return "Permission denied. Check file write permissions (`ls -la`) or ensure the executing user has access."

        # 4. Command not found
        if "command not found" in err_lower or "not found" in err_lower:
            cmd_name = command.split()[0] if command else "command"
            return f"Binary '{cmd_name}' is not installed or not in PATH. Check installation via package manager."

        # 5. Git repository error
        if "not a git repository" in err_lower:
            return "Current working directory is not a Git repository. Run `git init` or switch to the project root."

        # 6. Syntax / Indentation error
        if "syntaxerror" in err_lower or "indentationerror" in err_lower:
            return "Syntax or Indentation error encountered. Inspect the reported line and file path for typos or invalid formatting."

        # 7. Out of Memory / CUDA error
        if "out of memory" in err_lower or "cuda error: out of memory" in err_lower:
            return "GPU/RAM Out of Memory. Reduce batch size, context window (max_length), or free VRAM by stopping resident services."

        return f"Process exited with non-zero code {exit_code}. Review the stderr output above."


class SafeExecutor:
    def __init__(self, allowed_workspaces: Optional[List[Path]] = None, timeout_seconds: int = 20):
        if allowed_workspaces is None:
            # Default to current directory and storage root
            self.allowed_workspaces = [
                Path.cwd().resolve(),
                Path("/srv/storage").resolve(),
                Path("/tmp").resolve(),
            ]
        else:
            self.allowed_workspaces = [p.resolve() for p in allowed_workspaces]

        self.timeout_seconds = timeout_seconds

    def is_path_safe(self, target_path: Path) -> bool:
        resolved = target_path.resolve()
        for allowed in self.allowed_workspaces:
            if allowed in resolved.parents or resolved == allowed:
                return True
        return False

    def sanitize_env(self) -> Dict[str, str]:
        """Strip sensitive secrets from child process environment."""
        env = dict(os.environ)
        forbidden_keys = [
            "AWS_SECRET_ACCESS_KEY", "AWS_ACCESS_KEY_ID", "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY", "GITHUB_TOKEN", "GH_TOKEN", "SSH_AUTH_SOCK"
        ]
        for key in forbidden_keys:
            env.pop(key, None)
        return env

    def execute(self, command: str, cwd: Optional[Path] = None) -> ExecutionResult:
        start_time = time.perf_counter()
        blast_radius, block_reason = CommandClassifier.classify(command)

        if blast_radius == BlastRadius.BLOCKED:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                command=command,
                blast_radius=blast_radius,
                exit_code=126,
                stdout="",
                stderr=block_reason or "Command blocked by security policy.",
                duration_ms=duration_ms,
                is_safe=False,
                security_warning=block_reason
            )

        # Path safety validation on working directory
        work_dir = (cwd or Path.cwd()).resolve()
        if not self.is_path_safe(work_dir):
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                command=command,
                blast_radius=BlastRadius.BLOCKED,
                exit_code=126,
                stdout="",
                stderr=f"Security violation: working directory '{work_dir}' is outside authorized workspaces.",
                duration_ms=duration_ms,
                is_safe=False,
                security_warning="Working directory traversal violation."
            )

        sanitized_env = self.sanitize_env()

        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(work_dir),
                env=sanitized_env,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds
            )
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # Output truncation (limit to 200 lines / 30KB)
            stdout = proc.stdout
            if len(stdout) > 30000:
                stdout = stdout[:30000] + "\n... [TRUNCATED DUE TO LENGTH]"

            stderr = proc.stderr
            if len(stderr) > 10000:
                stderr = stderr[:10000] + "\n... [TRUNCATED DUE TO LENGTH]"

            remediation = None
            if proc.returncode != 0:
                remediation = SelfHealingEngine.diagnose_failure(command, stderr, proc.returncode)

            return ExecutionResult(
                command=command,
                blast_radius=blast_radius,
                exit_code=proc.returncode,
                stdout=stdout,
                stderr=stderr,
                duration_ms=duration_ms,
                is_safe=True,
                remediation_hint=remediation
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                command=command,
                blast_radius=blast_radius,
                exit_code=124,
                stdout="",
                stderr=f"Command timed out after {self.timeout_seconds} seconds.",
                duration_ms=duration_ms,
                is_safe=False,
                remediation_hint="Command exceeded execution quota. Check for infinite loops, blocking interactive input, or heavy computations."
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return ExecutionResult(
                command=command,
                blast_radius=blast_radius,
                exit_code=1,
                stdout="",
                stderr=f"Execution exception: {str(e)}",
                duration_ms=duration_ms,
                is_safe=False
            )
