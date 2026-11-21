"""
Execution-Guided Self-Repair & Sandbox-Grounded Backtracking Engine for Aria
Grounds error recovery in isolated 4-Tier Safe Execution feedback, distilling tracebacks
into localized Reflexion memory blocks with bounded backtracking (max 3 iterations).
"""

import os
import sys
import re
import ast
import time
import tempfile
import subprocess
import urllib.request
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.test_time_reasoning import ThinkThenActEngine


@dataclass
class LocalizedTraceback:
    """
    Compact, distilled representation of a Python execution failure.
    Strips noise, localized to user code and failing assertions.
    """
    error_type: str
    line_number: Optional[int] = None
    failing_code: Optional[str] = None
    assertion_detail: Optional[str] = None
    message: str = ""
    raw_stderr: str = ""

    def summary(self) -> str:
        parts = [f"Error: {self.error_type}"]
        if self.line_number is not None:
            parts.append(f"at line {self.line_number}")
        if self.failing_code:
            parts.append(f"(`{self.failing_code}`)")
        if self.assertion_detail:
            parts.append(f"Failing assertion: `{self.assertion_detail}`")
        if self.message and not self.assertion_detail:
            parts.append(f"Detail: {self.message}")
        return " | ".join(parts)


class TracebackDistiller:
    """
    Distills raw multi-line Python stderr streams into minimal localized error digests.
    Filters out runtime/test harness frames and pinpoints the defect in user code.
    """

    @staticmethod
    def distill(stderr: str, code: str) -> LocalizedTraceback:
        clean_stderr = stderr.strip()
        if not clean_stderr:
            return LocalizedTraceback(error_type="UnknownFailure", message="Process exited with non-zero code without stderr.")

        code_lines = code.splitlines()

        # 1. Check for Timeout
        if "timed out" in clean_stderr.lower() or "timeoutexpired" in clean_stderr.lower():
            return LocalizedTraceback(
                error_type="TimeoutExpired",
                message="Execution timed out (infinite loop or algorithmic complexity violation).",
                raw_stderr=clean_stderr
            )

        # 2. Check for SyntaxError
        if "SyntaxError" in clean_stderr:
            syntax_match = re.search(r"SyntaxError:\s*(.*?)(?:\s*\(.*?,\s*line\s*(\d+)\))?$", clean_stderr, re.MULTILINE)
            msg = syntax_match.group(1).strip() if syntax_match else "invalid syntax"
            line_str = syntax_match.group(2) if (syntax_match and syntax_match.group(2)) else None
            if not line_str:
                file_line_match = re.search(r'File\s*["\'].*?["\'],\s*line\s*(\d+)', clean_stderr)
                if file_line_match:
                    line_str = file_line_match.group(1)
            line_num = int(line_str) if line_str else None
            failing_code = code_lines[line_num - 1].strip() if line_num and 1 <= line_num <= len(code_lines) else None
            return LocalizedTraceback(
                error_type="SyntaxError",
                line_number=line_num,
                failing_code=failing_code,
                message=msg,
                raw_stderr=clean_stderr
            )

        # 3. Check for AssertionError
        assertion_match = re.search(r"assert\s+(candidate\(.*?\)\s*==\s*.*)", clean_stderr)
        alt_assert_match = re.search(r"assert\s+(.*)", clean_stderr)
        failing_assert = None
        if assertion_match:
            failing_assert = assertion_match.group(0).strip()
        elif alt_assert_match:
            failing_assert = alt_assert_match.group(0).strip()

        # 4. Extract standard Exception class and message (last line of traceback)
        lines = [l.strip() for l in clean_stderr.splitlines() if l.strip()]
        last_line = lines[-1] if lines else "ExecutionError"
        exc_match = re.match(r"^([a-zA-Z_]\w*(?:Error|Exception|Interrupt))(?::\s*(.*))?$", last_line)
        if exc_match:
            error_type = exc_match.group(1)
            error_msg = exc_match.group(2) or ""
        else:
            error_type = "RuntimeError"
            error_msg = last_line

        # 5. Extract localized failing line in candidate code (search for frame pointing to user function)
        # Patterns like: File "<string>", line 4, in <module> or in function_name
        frame_matches = re.findall(r'File\s*["\'].*?["\'],\s*line\s*(\d+)(?:,\s*in\s*(\w+))?', clean_stderr)
        line_num = None
        failing_code = None

        if frame_matches:
            # Check frames in reverse order for user code lines
            for l_str, func_name in reversed(frame_matches):
                cand_line = int(l_str)
                # If within code length and not in test check
                if 1 <= cand_line <= len(code_lines) and func_name != "check":
                    line_num = cand_line
                    failing_code = code_lines[line_num - 1].strip()
                    break
            # Fallback to last frame if none matched user function explicitly
            if line_num is None:
                line_num = int(frame_matches[-1][0])
                if 1 <= line_num <= len(code_lines):
                    failing_code = code_lines[line_num - 1].strip()

        return LocalizedTraceback(
            error_type=error_type,
            line_number=line_num,
            failing_code=failing_code,
            assertion_detail=failing_assert,
            message=error_msg,
            raw_stderr=clean_stderr
        )


@dataclass
class RepairAttempt:
    attempt: int
    raw_response: str
    thought: str
    code: str
    passed: bool
    returncode: int
    traceback: Optional[LocalizedTraceback] = None
    reflection: str = ""
    latency_ms: float = 0.0
    eval_tokens: int = 0


class ReflexionMemory:
    """
    Manages bounded episodic repair memory for a single problem across attempts.
    Formats structured reflection blocks without context explosion.
    """

    def __init__(self, task_id: str, prompt: str):
        self.task_id = task_id
        self.prompt = prompt
        self.attempts: List[RepairAttempt] = []

    def record_attempt(self, attempt: RepairAttempt):
        self.attempts.append(attempt)

    def generate_reflection_block(self, attempt_num: int, tb: LocalizedTraceback) -> str:
        """
        Synthesizes a structured <reflection> block documenting the localized failure,
        root cause hypothesis, and target remediation action.
        """
        err_type = tb.error_type
        loc_str = f" at line {tb.line_number}" if tb.line_number else ""
        code_str = f" in `{tb.failing_code}`" if tb.failing_code else ""
        fail_assert = f" Failed test assertion: `{tb.assertion_detail}`." if tb.assertion_detail else ""

        if err_type == "AssertionError":
            hypothesis = "Candidate code returned an incorrect value or failed an edge case boundary condition."
            action = "Trace variable updates against the failing input values and adjust logic/indexing to satisfy the assertion."
        elif err_type == "IndexError":
            hypothesis = "Array or string index out of range (off-by-one error or unhandled empty container)."
            action = "Check boundary conditions (0 and len-1) and add guard checks for empty or single-element inputs."
        elif err_type == "TypeError":
            hypothesis = f"Mismatched data types or invalid operator invocation: {tb.message}."
            action = "Ensure types match the function signature and handle None or container types explicitly."
        elif err_type == "SyntaxError":
            hypothesis = f"Malformed Python syntax: {tb.message}."
            action = "Fix syntax, closing parentheses/brackets, and indentation."
        elif err_type == "TimeoutExpired":
            hypothesis = "Infinite loop or quadratic/exponential complexity bottleneck."
            action = "Ensure while/for loops make monotonic progress towards termination and optimize redundant traversals."
        else:
            hypothesis = f"Runtime exception {err_type}: {tb.message}."
            action = "Refactor logic to prevent exception and ensure invariants hold across all inputs."

        reflection = (
            f"<reflection>\n"
            f"Attempt {attempt_num} failed with {err_type}{loc_str}{code_str}.{fail_assert}\n"
            f"Root cause hypothesis: {hypothesis}\n"
            f"Remediation strategy: {action}\n"
            f"</reflection>"
        )
        return reflection

    def build_repair_prompt(self, next_attempt: int) -> str:
        """
        Constructs context-budgeted prompt for Attempt k containing task description,
        prior failing code, localized error digest, and reflection memory.
        """
        prev = self.attempts[-1]
        tb = prev.traceback
        tb_summary = tb.summary() if tb else "Process exited with non-zero code."

        prompt_parts = [
            f"### ORIGINAL TASK:\n{self.prompt.strip()}\n",
            f"### PREVIOUS ATTEMPT (Attempt {prev.attempt}):\n```python\n{prev.code.strip()}\n```\n",
            f"### EXECUTION FEEDBACK FROM SANDBOX:\n{tb_summary}\n",
            f"### MEMORY REFLECTION:\n{prev.reflection.strip()}\n",
            f"### INSTRUCTIONS FOR REPAIR ATTEMPT {next_attempt}:\n"
            f"Analyze the exact defect in your previous code identified above.\n"
            f"1. Conduct concise <thought> reasoning isolating the fix.\n"
            f"2. Emit the corrected, complete Python function inside a single ```python ... ``` code block.\n"
            f"3. Do not repeat the same bug."
        ]
        return "\n".join(prompt_parts)


class ExecutionGuidedRepairEngine:
    """
    Executes Sandbox-Grounded Backtracking and Execution-Guided Self-Repair.
    Iteratively executes candidate solutions in an isolated sandbox, captures tracebacks,
    constructs Reflexion memory blocks, and re-prompts until tests pass or bounds are reached.
    """

    def __init__(
        self,
        model: str = "aria:3b",
        ollama_url: str = "http://127.0.0.1:11434",
        max_attempts: int = 3,
        sandbox_timeout: float = 5.0
    ):
        self.model = model
        self.ollama_url = ollama_url
        self.max_attempts = max_attempts
        self.sandbox_timeout = sandbox_timeout
        self.engine = ThinkThenActEngine(thinking_token_budget=512, code_token_budget=400)
        self.distiller = TracebackDistiller()

    def query_model(self, prompt_messages: List[Dict[str, str]], temperature: float = 0.2) -> Dict[str, Any]:
        payload = {
            "model": self.model,
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
            f"{self.ollama_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                res_json = json.loads(resp.read().decode("utf-8"))
            latency_ms = (time.time() - t0) * 1000.0
            return {
                "ok": True,
                "content": res_json.get("message", {}).get("content", ""),
                "eval_count": res_json.get("eval_count", 0),
                "latency_ms": latency_ms
            }
        except Exception as e:
            return {
                "ok": False,
                "content": "",
                "eval_count": 0,
                "latency_ms": 0.0,
                "error": str(e)
            }

    def execute_in_sandbox(self, code: str, test_code: str) -> Dict[str, Any]:
        """
        Executes candidate Python code + test assertions in an isolated subprocess.
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
                timeout=self.sandbox_timeout
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
                "stderr": f"Execution timed out after {self.sandbox_timeout}s",
                "duration_ms": self.sandbox_timeout * 1000.0
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

    def run_repair_loop(self, task_id: str, prompt: str, test_code: str) -> Dict[str, Any]:
        """
        Executes the full execution-guided self-repair backtracking loop.
        Returns complete diagnostic trajectory, repair delta, and execution metrics.
        """
        memory = ReflexionMemory(task_id, prompt)
        initial_passed = False
        final_passed = False
        total_tokens = 0
        total_latency_ms = 0.0

        for attempt_idx in range(1, self.max_attempts + 1):
            if attempt_idx == 1:
                # Attempt 1: Direct or initial prompt
                messages = self.engine.format_prompt(prompt, with_reasoning=True)
            else:
                # Subsequent attempts: Injected with Reflexion memory and execution feedback
                repair_user_prompt = memory.build_repair_prompt(next_attempt=attempt_idx)
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are Aria, an expert algorithmic debugging and self-repair engine. "
                            "You are provided with execution failure telemetry and localized tracebacks from a Python sandbox. "
                            "Rigorously analyze the root cause in <thought>...</thought> and emit the fixed Python code inside a ```python block."
                        )
                    },
                    {"role": "user", "content": repair_user_prompt}
                ]

            # Model generation
            gen_res = self.query_model(messages, temperature=0.2 if attempt_idx == 1 else 0.3)
            if not gen_res["ok"]:
                tb_fail = LocalizedTraceback(error_type="OllamaInferenceError", message=gen_res.get("error", "Failed query"))
                memory.record_attempt(RepairAttempt(
                    attempt=attempt_idx, raw_response="", thought="", code="",
                    passed=False, returncode=-1, traceback=tb_fail, reflection="",
                    latency_ms=0.0, eval_tokens=0
                ))
                break

            total_tokens += gen_res["eval_count"]
            total_latency_ms += gen_res["latency_ms"]

            # Parse thought and code
            parsed = self.engine.parse_response(gen_res["content"])
            code = parsed["clean_code"]
            thought = parsed["scratchpad"]

            # Sandbox execution
            exec_res = self.execute_in_sandbox(code, test_code)
            passed = exec_res["passed"]
            retcode = exec_res["returncode"]

            if attempt_idx == 1:
                initial_passed = passed

            if passed:
                memory.record_attempt(RepairAttempt(
                    attempt=attempt_idx,
                    raw_response=gen_res["content"],
                    thought=thought,
                    code=code,
                    passed=True,
                    returncode=retcode,
                    latency_ms=gen_res["latency_ms"],
                    eval_tokens=gen_res["eval_count"]
                ))
                final_passed = True
                break
            else:
                # Distill traceback
                tb = self.distiller.distill(exec_res["stderr"], code)
                reflection = memory.generate_reflection_block(attempt_idx, tb)

                memory.record_attempt(RepairAttempt(
                    attempt=attempt_idx,
                    raw_response=gen_res["content"],
                    thought=thought,
                    code=code,
                    passed=False,
                    returncode=retcode,
                    traceback=tb,
                    reflection=reflection,
                    latency_ms=gen_res["latency_ms"],
                    eval_tokens=gen_res["eval_count"]
                ))

        attempts_used = len(memory.attempts)
        repaired = (not initial_passed) and final_passed

        return {
            "task_id": task_id,
            "initial_passed": initial_passed,
            "final_passed": final_passed,
            "repaired": repaired,
            "attempts_used": attempts_used,
            "total_tokens": total_tokens,
            "total_latency_ms": total_latency_ms,
            "trajectory": [
                {
                    "attempt": a.attempt,
                    "passed": a.passed,
                    "returncode": a.returncode,
                    "error_type": a.traceback.error_type if a.traceback else None,
                    "error_summary": a.traceback.summary() if a.traceback else None,
                    "code": a.code,
                    "reflection": a.reflection,
                    "thought": a.thought,
                    "latency_ms": a.latency_ms,
                    "tokens": a.eval_tokens
                } for a in memory.attempts
            ]
        }
