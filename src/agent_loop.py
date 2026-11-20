import asyncio
import json
import re
import time
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel

from src.executor import SafeExecutor, ExecutionResult, BlastRadius
from src.tools import CodebaseTools, default_tools
from src.token_budgeter import get_chat_generation_options, estimate_tokens
from src.config import OLLAMA_URL, MODEL_NAME
import httpx

class AgentStep(BaseModel):
    step_number: int
    thought: str
    action_type: str  # "command" | "read_file" | "search" | "vitals" | "finish"
    action_payload: str
    observation: str
    exit_code: int
    duration_ms: float
    is_safe: bool

class AgentTaskResult(BaseModel):
    task: str
    status: str  # "completed" | "failed" | "max_steps_exceeded"
    steps: List[AgentStep]
    final_answer: str
    total_duration_ms: float
    slots_satisfied: List[str]

class SlotClosedAgentLoop:
    """
    Slot-Closed Runtime Governance for Small Language Models (arXiv:2609.33315).
    Constrains 3B SLM execution loops to prevent token bloat, infinite tool calling,
    and out-of-distribution hallucinations by enforcing deterministic slot tracking.
    """
    def __init__(self, tools: Optional[CodebaseTools] = None, max_steps: int = 5):
        self.tools = tools or default_tools
        self.max_steps = max_steps

    def extract_action(self, response_text: str) -> Tuple[str, str, str]:
        """
        Extracts (thought, action_type, action_payload) from structured or tagged response.
        Formats supported:
        1. JSON: {"thought": "...", "action": "command", "payload": "git status"}
        2. Tagged: <thought>...</thought> <action type="command">git status</action>
        3. Heuristic fallback: detect shell command line
        """
        # Try JSON extraction
        json_match = re.search(r"\{[\s\S]*?\}", response_text)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
                thought = data.get("thought", "Analyzing system state.")
                action = data.get("action", data.get("action_type", "finish"))
                payload = data.get("payload", data.get("command", ""))
                return thought, action, payload
            except Exception:
                pass

        # Try XML/Tag extraction
        thought_match = re.search(r"<thought>([\s\S]*?)</thought>", response_text)
        thought = thought_match.group(1).strip() if thought_match else "Evaluating execution step."

        action_match = re.search(r'<action\s+type=[\'"](\w+)[\'"]>([\s\S]*?)</action>', response_text)
        if action_match:
            return thought, action_match.group(1), action_match.group(2).strip()

        # Check for bash markdown block
        bash_match = re.search(r"```(?:bash|sh)?\n([\s\S]*?)```", response_text)
        if bash_match:
            cmd = bash_match.group(1).strip()
            # only first line or compound command
            return thought, "command", cmd

        # Default: task is finished or conversational
        return thought, "finish", response_text.strip()

    async def query_model(self, prompt: str) -> str:
        """Query local Ollama aria:3b with deterministic low temperature."""
        system_prompt = (
            "You are Aria, an autonomous systems engineering agent.\n"
            "Given the user's task and historical observations, plan and execute the next action.\n"
            "AVAILABLE ACTIONS:\n"
            "1. 'vitals': Instant CPU, RAM, GPU, and disk metrics. Payload: ''\n"
            "2. 'command': Run standard Linux commands (e.g. 'df -h', 'free -m', 'ps aux', 'git status', 'uptime'). Payload: command string\n"
            "3. 'read_file': Inspect code or config file. Payload: file path\n"
            "4. 'search': Grep codebase for pattern. Payload: search string\n"
            "5. 'finish': Complete the task and provide final synthesis. Payload: final summary string\n\n"
            "OUTPUT FORMAT (JSON ONLY):\n"
            "{\"thought\": \"reasoning about what to do next\", \"action\": \"vitals|command|read_file|search|finish\", \"payload\": \"argument\"}"
        )
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 250,
                "stop": ["\nUser:", "<|im_end|>"]
            }
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
                if resp.status_code == 200:
                    return resp.json().get("message", {}).get("content", "")
                return ""
        except Exception:
            return ""

    async def execute_task(self, task_description: str, required_slots: Optional[List[str]] = None) -> AgentTaskResult:
        """
        Executes an autonomous task through the slot-closed agent loop.
        """
        start_time = time.perf_counter()
        steps: List[AgentStep] = []
        slots_needed = required_slots or ["diagnosis", "verification"]
        slots_satisfied: List[str] = []

        observation_context = ""

        for step_idx in range(1, self.max_steps + 1):
            prompt = (
                f"TASK: {task_description}\n\n"
                f"REQUIRED SLOTS: {', '.join(slots_needed)}\n"
                f"SATISFIED SLOTS: {', '.join(slots_satisfied)}\n"
                f"PREVIOUS OBSERVATIONS:\n{observation_context or 'None yet.'}\n\n"
                f"Current Step: {step_idx}/{self.max_steps}. Decide the next action or finish."
            )

            raw_reply = await self.query_model(prompt)
            thought, action_type, payload = self.extract_action(raw_reply)

            if action_type == "finish" or (action_type != "vitals" and not payload):
                total_duration_ms = (time.perf_counter() - start_time) * 1000.0
                clean_final = payload or (thought if thought and thought != "Evaluating execution step." else raw_reply) or "Task completed successfully."
                return AgentTaskResult(
                    task=task_description,
                    status="completed",
                    steps=steps,
                    final_answer=clean_final,
                    total_duration_ms=total_duration_ms,
                    slots_satisfied=slots_satisfied
                )

            # Execute action through SafeExecutor
            step_start = time.perf_counter()
            obs_text = ""
            exit_code = 0
            is_safe = True

            if action_type == "command":
                res = self.tools.execute_terminal_command(payload)
                exit_code = res["exit_code"]
                is_safe = res["is_safe"]
                obs_text = res["stdout"] if exit_code == 0 else f"ERROR (exit {exit_code}): {res['stderr']}"
                if res.get("remediation_hint"):
                    obs_text += f"\n[REMEDIATION]: {res['remediation_hint']}"

            elif action_type == "read_file":
                res = self.tools.read_code_file(payload)
                obs_text = res.get("content", res.get("error", "Failed to read file."))

            elif action_type == "search":
                res = self.tools.search_codebase(payload)
                matches = res.get("matches", [])
                obs_text = "\n".join(matches[:15]) if matches else "No matches found."

            elif action_type == "vitals":
                res = self.tools.get_system_vitals()
                obs_text = json.dumps(res, indent=2)

            else:
                obs_text = f"Unknown action '{action_type}'. Proceeding to finish."
                action_type = "finish"

            step_duration_ms = (time.perf_counter() - step_start) * 1000.0

            # Record step
            step_record = AgentStep(
                step_number=step_idx,
                thought=thought,
                action_type=action_type,
                action_payload=payload,
                observation=obs_text[:1500],
                exit_code=exit_code,
                duration_ms=round(step_duration_ms, 2),
                is_safe=is_safe
            )
            steps.append(step_record)

            # Update slot closure heuristics
            if step_idx == 1 and "diagnosis" in slots_needed:
                slots_satisfied.append("diagnosis")
            if exit_code == 0 and "verification" in slots_needed and "verification" not in slots_satisfied:
                slots_satisfied.append("verification")

            # Check if all slots satisfied
            if set(slots_needed).issubset(set(slots_satisfied)) and step_idx >= 2:
                # Trigger synthesis step
                synthesis_prompt = (
                    f"TASK: {task_description}\n"
                    f"OBSERVATIONS ACCUMULATED:\n"
                    + "\n".join(f"Step {s.step_number} [{s.action_type} {s.action_payload}]: {s.observation[:300]}" for s in steps)
                    + "\n\nSynthesize the final executive answer and fix/report concisely for the user:"
                )
                final_synth = await self.query_model(synthesis_prompt)
                _, _, clean_answer = self.extract_action(final_synth)
                total_duration_ms = (time.perf_counter() - start_time) * 1000.0
                return AgentTaskResult(
                    task=task_description,
                    status="completed",
                    steps=steps,
                    final_answer=clean_answer or final_synth,
                    total_duration_ms=total_duration_ms,
                    slots_satisfied=slots_satisfied
                )

            # Append to ongoing context
            observation_context += f"\n[Step {step_idx} - {action_type} {payload}]:\n{obs_text[:500]}\n"

        # Max steps exceeded
        total_duration_ms = (time.perf_counter() - start_time) * 1000.0
        return AgentTaskResult(
            task=task_description,
            status="max_steps_exceeded",
            steps=steps,
            final_answer="Maximum execution steps reached. Review step history for partial findings.",
            total_duration_ms=total_duration_ms,
            slots_satisfied=slots_satisfied
        )

# Global Agent Loop Instance
agent_loop = SlotClosedAgentLoop()
