import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from src.executor import SafeExecutor, ExecutionResult, BlastRadius

class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

class ToolCallResponse(BaseModel):
    tool_name: str
    success: bool
    result: Any
    error: Optional[str] = None

class CodebaseTools:
    def __init__(self, executor: Optional[SafeExecutor] = None):
        self.executor = executor or SafeExecutor()

    def execute_terminal_command(self, command: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes a terminal command through the SafeExecutor sandbox with blast-radius control.
        """
        work_dir = Path(cwd).resolve() if cwd else Path.cwd()
        res = self.executor.execute(command, cwd=work_dir)
        return {
            "command": res.command,
            "blast_radius": res.blast_radius.value,
            "exit_code": res.exit_code,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "duration_ms": round(res.duration_ms, 2),
            "is_safe": res.is_safe,
            "remediation_hint": res.remediation_hint,
            "security_warning": res.security_warning,
        }

    def read_code_file(self, file_path: str, start_line: int = 1, end_line: Optional[int] = None) -> Dict[str, Any]:
        """
        Safely reads a code or configuration file with line-range bounding.
        """
        path = Path(file_path).resolve()
        if not self.executor.is_path_safe(path):
            return {"error": f"Access denied: path '{path}' is outside authorized workspaces."}

        if not path.exists():
            return {"error": f"File '{path}' does not exist."}

        if not path.is_file():
            return {"error": f"Path '{path}' is a directory, not a file."}

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, end_line) if end_line else total_lines

            sliced_lines = lines[start_idx:end_idx]
            numbered = [f"{i + start_idx + 1:4d} | {line}" for i, line in enumerate(sliced_lines)]

            return {
                "file_path": str(path),
                "total_lines": total_lines,
                "start_line": start_line,
                "end_line": end_idx,
                "content": "".join(numbered)
            }
        except Exception as e:
            return {"error": f"Failed to read file: {str(e)}"}

    def write_code_file(self, file_path: str, content: str, create_backup: bool = True) -> Dict[str, Any]:
        """
        Writes or updates a code file safely with optional automatic backup creation.
        """
        path = Path(file_path).resolve()
        if not self.executor.is_path_safe(path):
            return {"error": f"Access denied: path '{path}' is outside authorized workspaces."}

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if create_backup and path.exists():
                backup_path = path.with_suffix(path.suffix + ".bak")
                shutil.copy2(path, backup_path)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "file_path": str(path),
                "bytes_written": len(content.encode("utf-8")),
                "status": "success",
                "backup_created": create_backup and path.exists()
            }
        except Exception as e:
            return {"error": f"Failed to write file: {str(e)}"}

    def search_codebase(self, query: str, search_dir: Optional[str] = None, max_results: int = 30) -> Dict[str, Any]:
        """
        Performs high-speed code search across files in authorized workspaces.
        """
        target_dir = Path(search_dir).resolve() if search_dir else Path.cwd()
        if not self.executor.is_path_safe(target_dir):
            return {"error": f"Access denied: search directory '{target_dir}' is unauthorized."}

        cmd = f"grep -rnI --exclude-dir='.git' --exclude-dir='.venv' --exclude-dir='__pycache__' --exclude-dir='node_modules' -m {max_results} {shlex.quote(query)} {shlex.quote(str(target_dir))}"
        res = self.executor.execute(cmd, cwd=target_dir)
        return {
            "query": query,
            "directory": str(target_dir),
            "matches": res.stdout.strip().splitlines() if res.stdout else [],
            "match_count": len(res.stdout.strip().splitlines()) if res.stdout else 0
        }

    def get_system_vitals(self) -> Dict[str, Any]:
        """
        Captures real-time host vitals (CPU, RAM, GPU VRAM, Disk) safely.
        """
        vitals: Dict[str, Any] = {}
        try:
            # Memory
            free_res = self.executor.execute("free -m")
            vitals["memory_raw"] = free_res.stdout.strip()

            # Disk
            df_res = self.executor.execute("df -h / /srv/storage 2>/dev/null || df -h /")
            vitals["disk_raw"] = df_res.stdout.strip()

            # Uptime & Load
            uptime_res = self.executor.execute("uptime")
            vitals["uptime"] = uptime_res.stdout.strip()

            # GPU (if nvidia-smi exists)
            gpu_res = self.executor.execute("nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader 2>/dev/null")
            if gpu_res.stdout.strip():
                vitals["gpu"] = gpu_res.stdout.strip()
            else:
                vitals["gpu"] = "No NVIDIA GPU detected or nvidia-smi unavailable"

        except Exception as e:
            vitals["error"] = str(e)

        return vitals

# Global tool instance
default_tools = CodebaseTools()
