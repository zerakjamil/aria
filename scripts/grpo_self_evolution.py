#!/usr/bin/env python3
"""
Autonomous Self-Evolution Loop: On-Device GRPO / RLVR Engine for Aria (Phase 10)
Executes verifiable self-play reasoning, sampling groups of G=4 candidate completions,
evaluating them in an isolated execution sandbox against ground-truth assertions,
computing GRPO normalized advantages, applying Reflexion repair on horizon chokes,
and compiling verified self-evolved trajectories into combined_train_v10_rlvr.jsonl.
"""

import os
import sys
import json
import time
import math
import argparse
import tempfile
import subprocess
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.test_time_reasoning import ThinkThenActEngine
from src.self_repair import TracebackDistiller

# Import expanded 40-challenge bank
try:
    from scripts.challenge_bank import CHALLENGE_BANK
except ImportError:
    from challenge_bank import CHALLENGE_BANK

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.getenv("MODEL_NAME", "aria:3b")
DEFAULT_GROUP_SIZE = 4  # G = 4 candidate rollouts per prompt (DeepSeek-R1 style)


def compute_grpo_advantages(rewards: List[float]) -> Tuple[List[float], float, float]:
    """
    Computes Group Relative Policy Optimization (GRPO) advantage:
    A_i = (r_i - mean(rewards)) / (std(rewards) + 1e-4)
    """
    n = len(rewards)
    if n == 0:
        return [], 0.0, 0.0
    mean_r = sum(rewards) / n
    var_r = sum((r - mean_r) ** 2 for r in rewards) / n
    std_r = math.sqrt(var_r)
    eps = 1e-4
    advantages = [(r - mean_r) / (std_r + eps) for r in rewards]
    return advantages, mean_r, std_r


def compute_graduated_reward(
    passed: bool,
    syntax_ok: bool,
    crash: bool,
    has_scratchpad: bool,
    duration_ms: float
) -> float:
    """
    Computes graduated verifiable reward R in accordance with System Invariant 48.
    R = R_exec + R_scratchpad + R_efficiency
    """
    if not syntax_ok:
        base_r = -1.0
    elif crash:
        base_r = -0.5
    elif passed:
        base_r = 1.0
    else:
        base_r = -0.2

    # Scratchpad reasoning bonus
    scratchpad_bonus = 0.25 if has_scratchpad else 0.0

    # Efficiency bonus for sub-100ms execution
    efficiency_bonus = 0.10 if (passed and duration_ms < 100.0) else 0.0

    return base_r + scratchpad_bonus + efficiency_bonus


def query_ollama_completion(
    prompt_messages: List[Dict[str, str]],
    temperature: float = 0.7,
    model: str = DEFAULT_MODEL,
    ollama_url: str = OLLAMA_URL
) -> Dict[str, Any]:
    """
    Queries Ollama HTTP API with non-streaming completion.
    """
    payload = {
        "model": model,
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
        f"{ollama_url}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
        latency_ms = (time.time() - t0) * 1000.0
        content = res_json.get("message", {}).get("content", "")
        eval_count = res_json.get("eval_count", 0)
        return {"content": content, "latency_ms": latency_ms, "eval_count": eval_count, "ok": True}
    except Exception as e:
        return {"content": "", "latency_ms": 0.0, "eval_count": 0, "ok": False, "error": str(e)}


def execute_in_sandbox(code: str, test_code: str, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Executes Python candidate solution + test assertions in an isolated subprocess.
    """
    preamble = (
        "from typing import *\n"
        "import os, sys, math, time, json, re\n"
        "from collections import defaultdict, deque, Counter\n\n"
    )
    full_script = f"{preamble}{code}\n\n{test_code}"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(full_script)
        temp_path = f.name

    try:
        t0 = time.time()
        proc = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout
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
            "stderr": f"Execution timed out after {timeout}s",
            "duration_ms": timeout * 1000.0
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


def run_grpo_self_evolution(
    output_dir: str = "/srv/storage/ai-companion/training/data",
    model: str = DEFAULT_MODEL,
    group_size: int = DEFAULT_GROUP_SIZE,
    limit: Optional[int] = None,
    ollama_url: str = OLLAMA_URL
) -> Dict[str, Any]:
    engine = ThinkThenActEngine(thinking_token_budget=512, code_token_budget=400)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    challenges = CHALLENGE_BANK[:limit] if limit else CHALLENGE_BANK

    print("=" * 80)
    print("ARIA 2026 AUTONOMOUS SELF-EVOLUTION ENGINE (ON-DEVICE GRPO / RLVR - PHASE 10)")
    print(f"Policy: {model} | Group Size G = {group_size} | Ollama: {ollama_url}")
    print(f"Active Challenge Suite: {len(challenges)} verifiable tasks")
    print("=" * 80, flush=True)

    golden_trajectories: List[Dict[str, Any]] = []
    total_rollouts = 0
    passed_rollouts = 0
    contrastive_groups = 0
    horizon_choke_repairs = 0

    telemetry_records = []

    for idx, problem in enumerate(challenges, 1):
        task_id = problem["task_id"]
        prompt_text = problem["prompt"]
        test_text = problem["test"]

        print(f"\n[{idx:02d}/{len(challenges)}] Challenge: {task_id}")
        messages = engine.format_prompt(prompt_text, with_reasoning=True)

        candidate_results = []
        rewards = []

        # 1. Sample G rollouts from current policy
        for g_idx in range(group_size):
            total_rollouts += 1
            gen_res = query_ollama_completion(messages, temperature=0.7, model=model, ollama_url=ollama_url)
            if not gen_res["ok"]:
                print(f"   Candidate {g_idx+1}: ERROR ({gen_res.get('error')})")
                r = -1.0
                rewards.append(r)
                candidate_results.append({"passed": False, "reward": r, "raw": "", "parsed": {}, "exec": {}})
                continue

            parsed = engine.parse_response(gen_res["content"])
            exec_res = execute_in_sandbox(parsed["clean_code"], test_text)

            is_pass = exec_res["passed"]
            syntax_ok = parsed.get("ast_valid", True)
            crash = (not is_pass and exec_res.get("returncode") != 0)

            r = compute_graduated_reward(
                passed=is_pass,
                syntax_ok=syntax_ok,
                crash=crash,
                has_scratchpad=parsed["has_scratchpad"],
                duration_ms=exec_res["duration_ms"]
            )
            rewards.append(r)
            if is_pass:
                passed_rollouts += 1

            thought_len = parsed["scratchpad_tokens_est"]
            code_len = len(parsed["clean_code"].splitlines())
            status_str = f"PASS ({r:+.2f})" if is_pass else f"FAIL ({r:+.2f}: code={exec_res['returncode']})"
            print(f"   Candidate {g_idx+1}: {status_str:<22} | thought={thought_len:3d}tok | code={code_len:2d} lines | {gen_res['latency_ms']:.0f}ms")

            candidate_results.append({
                "passed": is_pass,
                "reward": r,
                "raw": gen_res["content"],
                "parsed": parsed,
                "exec": exec_res,
                "latency_ms": gen_res["latency_ms"]
            })

        # 2. Compute GRPO Advantages for Group
        advantages, mean_r, std_r = compute_grpo_advantages(rewards)
        print(f"   -> GRPO Group: mean={mean_r:+.2f}, std={std_r:.2f}, advantages={[round(a, 2) for a in advantages]}")

        # 3. Analyze Contrast & Reinforce Trajectories
        has_pass = any(c["passed"] for c in candidate_results)
        if std_r > 0.0:
            contrastive_groups += 1

        if has_pass:
            # Select the passing candidate with highest advantage and cleanest scratchpad
            passing_candidates = [c for c in candidate_results if c["passed"]]
            best_candidate = max(
                passing_candidates,
                key=lambda c: (c["parsed"]["has_scratchpad"], c["reward"], -len(c["parsed"]["clean_code"]))
            )

            scratchpad = best_candidate["parsed"]["scratchpad"]
            clean_code = best_candidate["parsed"]["clean_code"]
            formatted_output = f"<thought>\n{scratchpad}\n</thought>\n\n```python\n{clean_code}\n```"

            golden_trajectories.append({
                "task_id": task_id,
                "instruction": (
                    "You are Aria, an expert sovereign algorithmic engineer and technical copilot. "
                    "When faced with programming and technical reasoning tasks, you MUST conduct deep "
                    "internal scratchpad reasoning before writing any final solution. "
                    "Enclose your analysis in <thought>...</thought> followed by the code block."
                ),
                "input": prompt_text,
                "output": formatted_output,
                "advantage": max(advantages) if advantages else 1.0,
                "reward": best_candidate["reward"],
                "verified": True,
                "repaired": False
            })
            print(f"   ✓ Trajectory Reinforced (Advantage = {max(advantages):+.2f}, Reward = {best_candidate['reward']:+.2f})")
        else:
            # 4. Horizon Choke Recovery via Reflexion Engine
            print(f"   ⚠ Horizon Choke: 0/{group_size} passed. Engaging Reflexion Self-Repair Engine...")
            failed_cand = candidate_results[0]
            stderr_text = failed_cand.get("exec", {}).get("stderr", "")
            failed_code = failed_cand.get("parsed", {}).get("clean_code", "")
            distilled = TracebackDistiller.distill(stderr_text, failed_code)

            dist_summary = distilled.summary() if callable(getattr(distilled, "summary", None)) else str(distilled)
            repair_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are Aria, an expert self-repairing programming engine. "
                        "A previous attempt failed execution. Analyze the error traceback rigorously inside <thought>...</thought>, "
                        "identify the exact invariant or boundary failure, and emit the corrected Python code in ```python ... ```."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Problem:\n{prompt_text}\n\n"
                        f"Failed Code:\n```python\n{failed_cand.get('parsed', {}).get('clean_code', '')}\n```\n\n"
                        f"Execution Failure Diagnostic:\n{dist_summary}\n\n"
                        "Provide the corrected implementation."
                    )
                }
            ]

            repair_res = query_ollama_completion(repair_messages, temperature=0.2, model=model, ollama_url=ollama_url)
            if repair_res["ok"]:
                repair_parsed = engine.parse_response(repair_res["content"])
                repair_exec = execute_in_sandbox(repair_parsed["clean_code"], test_text)
                if repair_exec["passed"]:
                    horizon_choke_repairs += 1
                    scratchpad = repair_parsed["scratchpad"] or f"Reflexion diagnostic resolved: {dist_summary}"
                    clean_code = repair_parsed["clean_code"]
                    formatted_output = f"<thought>\n{scratchpad}\n</thought>\n\n```python\n{clean_code}\n```"

                    golden_trajectories.append({
                        "task_id": task_id,
                        "instruction": (
                            "You are Aria, an expert sovereign algorithmic engineer and technical copilot. "
                            "When faced with programming and technical reasoning tasks, you MUST conduct deep "
                            "internal scratchpad reasoning before writing any final solution. "
                            "Enclose your analysis in <thought>...</thought> followed by the code block."
                        ),
                        "input": prompt_text,
                        "output": formatted_output,
                        "advantage": 1.5,
                        "reward": 1.25,
                        "verified": True,
                        "repaired": True
                    })
                    print(f"   ✓ Reflexion Self-Repair Succeeded: Recovered trajectory added to buffer!")
                else:
                    print(f"   ✗ Reflexion repair attempt also failed (exit code {repair_exec['returncode']})")
            else:
                print(f"   ✗ Reflexion query error: {repair_res.get('error')}")

        telemetry_records.append({
            "task_id": task_id,
            "rewards": rewards,
            "mean_reward": mean_r,
            "std_reward": std_r,
            "advantages": advantages
        })

    # Summary
    print("\n" + "=" * 80)
    print("PHASE 10 GRPO / RLVR ROLLOUT SUMMARY:")
    print(f"  Total Challenges Evaluated:    {len(challenges)}")
    print(f"  Total Rollout Candidates (G={group_size}): {total_rollouts}")
    print(f"  Successful Paths:              {passed_rollouts}/{total_rollouts} ({(passed_rollouts/max(1, total_rollouts))*100.0:.1f}%)")
    print(f"  Contrastive Groups (std > 0):   {contrastive_groups}/{len(challenges)}")
    print(f"  Reflexion Recovered Chokes:    {horizon_choke_repairs}")
    print(f"  Total Verified Golden Paths:   {len(golden_trajectories)}/{len(challenges)}")
    print("=" * 80)

    # 1. Save RLVR buffer
    rlvr_file = out_path / "rlvr_self_evolved_v10.jsonl"
    with open(rlvr_file, "w") as f:
        for t in golden_trajectories:
            f.write(json.dumps({
                "instruction": t["instruction"],
                "input": t["input"],
                "output": t["output"]
            }) + "\n")
    print(f"\nSaved {len(golden_trajectories)} verified self-evolved trajectories to:\n  {rlvr_file}")

    # 2. Compile Fused Phase 10 Dataset (Anchor v9 + RLVR buffer)
    anchor_file = out_path / "combined_train_v9_ultra.jsonl"
    combined_v10_file = out_path / "combined_train_v10_rlvr.jsonl"

    anchor_samples = []
    if anchor_file.exists():
        with open(anchor_file, "r") as f:
            for line in f:
                if line.strip():
                    anchor_samples.append(json.loads(line))

    fused_samples = anchor_samples + [
        {
            "instruction": t["instruction"],
            "input": t["input"],
            "output": t["output"]
        } for t in golden_trajectories
    ]

    with open(combined_v10_file, "w") as f:
        for s in fused_samples:
            f.write(json.dumps(s) + "\n")

    print(f"Compiled Fused Phase 10 Dataset ({len(anchor_samples)} Phase 9 anchors + {len(golden_trajectories)} RLVR = {len(fused_samples)} total) to:\n  {combined_v10_file}")

    # 3. Save Telemetry
    telemetry_file = out_path / "grpo_telemetry_v10.json"
    with open(telemetry_file, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "model": model,
            "group_size": group_size,
            "total_challenges": len(challenges),
            "total_rollouts": total_rollouts,
            "passed_rollouts": passed_rollouts,
            "contrastive_groups": contrastive_groups,
            "horizon_choke_repairs": horizon_choke_repairs,
            "golden_count": len(golden_trajectories),
            "records": telemetry_records
        }, f, indent=2)
    print(f"Saved GRPO telemetry log to:\n  {telemetry_file}")

    return {
        "golden_count": len(golden_trajectories),
        "total_rollouts": total_rollouts,
        "passed_rollouts": passed_rollouts,
        "combined_file": str(combined_v10_file)
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aria GRPO / RLVR Autonomous Self-Evolution Engine")
    parser.add_argument("--output-dir", default="/srv/storage/ai-companion/training/data", help="Output directory")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model policy name in Ollama")
    parser.add_argument("--group-size", type=int, default=DEFAULT_GROUP_SIZE, help="Candidate group size G")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of challenges")
    parser.add_argument("--ollama-url", default=OLLAMA_URL, help="Ollama API base URL")

    args = parser.parse_args()
    run_grpo_self_evolution(
        output_dir=args.output_dir,
        model=args.model,
        group_size=args.group_size,
        limit=args.limit,
        ollama_url=args.ollama_url
    )
