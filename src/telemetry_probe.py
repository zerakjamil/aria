"""
Read-Only Linux Host Telemetry Probe for Aria.
Enforces strict read-only guarantees:
- Whitelist-only command registry
- Regex validation on all user arguments
- subprocess.run(shell=False) to prevent shell expansion
- 16 KB output buffer truncation
"""

import re
import subprocess
from typing import Dict, Any, Optional

ALLOWED_IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
ALLOWED_PATH_REGEX = re.compile(r"^[a-zA-Z0-9_\-\./]+$")
MAX_OUTPUT_BYTES = 16384  # 16 KB


class TelemetryProbe:
    """Provides structured, sanitized, read-only system inspection."""

    @staticmethod
    def _validate_arg(value: str, pattern: re.Pattern = ALLOWED_IDENTIFIER_REGEX) -> str:
        if not value or not pattern.match(value):
            raise ValueError(f"Invalid argument rejected by telemetry probe: {value!r}")
        return value

    @staticmethod
    def _execute(cmd: list[str], timeout: float = 5.0) -> Dict[str, Any]:
        try:
            res = subprocess.run(
                cmd,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            stdout = res.stdout[:MAX_OUTPUT_BYTES]
            stderr = res.stderr[:MAX_OUTPUT_BYTES]
            return {
                "exit_code": res.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "truncated": len(res.stdout) > MAX_OUTPUT_BYTES or len(res.stderr) > MAX_OUTPUT_BYTES
            }
        except subprocess.TimeoutExpired:
            return {
                "exit_code": 124,
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "truncated": False
            }
        except FileNotFoundError as e:
            return {
                "exit_code": 127,
                "stdout": "",
                "stderr": f"Binary not found: {e}",
                "truncated": False
            }
        except Exception as e:
            return {
                "exit_code": 1,
                "stdout": "",
                "stderr": f"Execution error: {e}",
                "truncated": False
            }

    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Inspects status of a systemd service."""
        safe_service = self._validate_arg(service_name)
        if not safe_service.endswith(".service"):
            safe_service = f"{safe_service}.service"
        return self._execute(["systemctl", "status", safe_service, "--no-pager"])

    def get_journal_logs(self, service_name: str, lines: int = 20) -> Dict[str, Any]:
        """Retrieves recent logs for a service."""
        safe_service = self._validate_arg(service_name)
        safe_lines = max(1, min(lines, 100))
        return self._execute(["journalctl", "-u", safe_service, "-n", str(safe_lines), "--no-pager"])

    def get_disk_usage(self, path: str = "/") -> Dict[str, Any]:
        """Queries disk space usage."""
        safe_path = self._validate_arg(path, ALLOWED_PATH_REGEX)
        return self._execute(["df", "-h", safe_path])

    def get_memory_profile(self) -> Dict[str, Any]:
        """Queries physical memory usage."""
        return self._execute(["free", "-m"])

    def get_open_sockets(self) -> Dict[str, Any]:
        """Queries listening TCP/UDP ports."""
        return self._execute(["ss", "-tulpn"])

    def get_uptime(self) -> Dict[str, Any]:
        """Queries system uptime and load average."""
        return self._execute(["uptime"])

    def get_top_processes(self, count: int = 10) -> Dict[str, Any]:
        """Queries top memory-consuming processes."""
        safe_count = max(1, min(count, 30))
        # Direct ps call with sort flag (no pipes)
        return self._execute(["ps", "aux", "--sort=-%mem"])
