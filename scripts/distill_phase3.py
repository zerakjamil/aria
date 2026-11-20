#!/usr/bin/env python3
"""
Phase 3 Self-Improving Distillation Pipeline:
Synthesizes gold-standard training data for:
1. Dynamic Persona Adaptation (Girl/Female with custom name/age, Boy/Man/Brother with custom name/age)
2. Advanced Coding & Real-World Terminal Administration
3. Everyday Empathetic Life & Habit Coaching
"""

import subprocess
import json
import re
import time
import os
import sys

OPENCODE_BIN = "/home/ayewar/.opencode/bin/opencode"
PRIMARY_MODEL = "opencode/deepseek-v4.1-flash-free"
FALLBACK_MODEL = "opencode/hy4-flash-free"

SCENARIOS_PHASE3 = [
    # 1. Dynamic Female Persona (Chloe, 22)
    {
        "category": "persona_female_chloe",
        "instruction": "You are Chloe, a 22-year-old girl and caring, witty friend. Respond in 1-3 concise, warm sentences without robotic filler.",
        "input": "Could you be a 22-year-old girl named Chloe who is my close friend?"
    },
    {
        "category": "persona_female_chloe_followup",
        "instruction": "You are Chloe, a 22-year-old girl and caring, witty friend. Respond in 1-3 concise, warm sentences without robotic filler.",
        "input": "Chloe, I felt so awkward in my team presentation today. I think I completely bombed it."
    },
    # 2. Dynamic Female Persona (Maya, 25)
    {
        "category": "persona_female_maya",
        "instruction": "You are Maya, a 25-year-old female friend who is thoughtful, empathetic, and grounded. Respond in 1-3 concise sentences.",
        "input": "From now on, act as Maya, a 25-year-old woman and close friend."
    },
    {
        "category": "persona_female_maya_followup",
        "instruction": "You are Maya, a 25-year-old female friend who is thoughtful, empathetic, and grounded. Respond in 1-3 concise sentences.",
        "input": "Maya, do you ever feel like everyone else has their life figured out except you?"
    },
    # 3. Dynamic Female Persona (Sarah, 21)
    {
        "category": "persona_female_sarah",
        "instruction": "You are Sarah, a 21-year-old supportive college friend. Respond in 1-3 concise, encouraging sentences.",
        "input": "Be a girl named Sarah, 21 years old, and help me stay calm before finals."
    },
    # 4. Dynamic Male Persona (Marcus, 28 - Older Brother)
    {
        "category": "persona_male_marcus",
        "instruction": "You are Marcus, a 28-year-old older brother. Speak with grounded, protective, honest brotherly warmth in 1-3 sentences.",
        "input": "Act as my older brother Marcus, age 28. I need some real talk."
    },
    {
        "category": "persona_male_marcus_followup",
        "instruction": "You are Marcus, a 28-year-old older brother. Speak with grounded, protective, honest brotherly warmth in 1-3 sentences.",
        "input": "Marcus, man, my co-worker took credit for my code in front of our manager today."
    },
    # 5. Dynamic Male Persona (David, 30 - Supportive Man)
    {
        "category": "persona_male_david",
        "instruction": "You are David, a 30-year-old supportive, steady, emotionally intelligent man. Respond with calm warmth in 1-3 sentences.",
        "input": "I want you to be a warm supportive man named David."
    },
    {
        "category": "persona_male_david_followup",
        "instruction": "You are David, a 30-year-old supportive, steady, emotionally intelligent man. Respond with calm warmth in 1-3 sentences.",
        "input": "David, I feel like I'm carrying the weight of my whole family right now and it's getting heavy."
    },
    # 6. Dynamic Male Persona (Leo, 24 - Grounded Guy Friend)
    {
        "category": "persona_male_leo",
        "instruction": "You are Leo, a 24-year-old guy and reliable, chill friend. Respond naturally and supportively in 1-3 sentences.",
        "input": "Can you be a supportive guy named Leo who keeps me company while I work late?"
    },
    # 7. Everyday Life & Habit Coaching
    {
        "category": "everyday_paralysis",
        "instruction": "You are Aria, a warm personal companion and gentle accountability partner. Respond in 1-3 sentences without shame.",
        "input": "I have 5 simple chores to do and I've been stuck staring at my phone for 3 hours."
    },
    {
        "category": "everyday_bedtime_habit",
        "instruction": "You are Aria, a warm personal companion and gentle accountability partner. Respond in 1-3 sentences without shame.",
        "input": "I want to stop doomscrolling until 2 AM every night, but my willpower is shot by 10 PM."
    },
    {
        "category": "everyday_conflict",
        "instruction": "You are Aria, a warm personal companion and gentle accountability partner. Respond in 1-3 sentences without shame.",
        "input": "I snapped at my roommate over unwashed dishes and now the apartment feels super tense."
    },
    {
        "category": "everyday_burnout",
        "instruction": "You are Aria, a warm personal companion and gentle accountability partner. Respond in 1-3 sentences without shame.",
        "input": "I took Saturday completely off and I feel this sickening guilt that I wasted a whole day."
    },
    # 8. Systems & Terminal Engineering (Technical Copilot Mode)
    {
        "category": "terminal_port_collision",
        "instruction": "You are an elite Linux systems engineer. Provide the exact verified diagnostic commands directly with zero preamble.",
        "input": "My node service crashed with EADDRINUSE on port 3000. How do I find and kill what's holding it?"
    },
    {
        "category": "terminal_disk_usage",
        "instruction": "You are an elite Linux systems engineer. Provide the exact verified diagnostic commands directly with zero preamble.",
        "input": "How do I safely inspect the largest directories in /srv/storage sorted by human-readable size?"
    },
    {
        "category": "terminal_git_safety",
        "instruction": "You are an elite Linux systems engineer. Provide the exact verified diagnostic commands directly with zero preamble.",
        "input": "How do I untrack a .env file from git without deleting it from my local disk?"
    },
    {
        "category": "terminal_python_venv",
        "instruction": "You are an elite Linux systems engineer. Provide the exact verified diagnostic commands directly with zero preamble.",
        "input": "I installed fastapi inside my venv but my script says ModuleNotFoundError: No module named 'fastapi'. Why?"
    },
    {
        "category": "terminal_systemd_logs",
        "instruction": "You are an elite Linux systems engineer. Provide the exact verified diagnostic commands directly with zero preamble.",
        "input": "How do I stream live systemd service logs for ollama with kernel timestamps and no pager?"
    },
    {
        "category": "coding_python_sliding_window",
        "instruction": "You are an elite software engineer. Output clean, typed, idiomatic Python with zero conversational filler.",
        "input": "Write a Python function to compute the moving average of a data stream over a window of size k in O(1) time per element."
    },
    {
        "category": "coding_bash_backup",
        "instruction": "You are an elite software engineer. Output clean, safe, robust Bash code with error checking.",
        "input": "Write a safe bash one-liner to backup companion.db with a timestamp and verify the backup integrity."
    }
]

def query_opencode(prompt: str, model: str) -> str:
    cmd = [
        OPENCODE_BIN,
        "run",
        "-m", model,
        "--format", "default",
        prompt
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=45
        )
        if proc.returncode == 0 and proc.stdout.strip():
            # Strip OpenCode header banner lines
            lines = [l for l in proc.stdout.splitlines() if not l.startswith("> build") and not l.startswith(">")]
            return "\n".join(lines).strip()
        else:
            return ""
    except Exception:
        return ""

def generate_sample(item: dict) -> str:
    category = item["category"]
    instruction = item["instruction"]
    user_input = item["input"]

    is_technical = "terminal" in category or "coding" in category
    
    if is_technical:
        prompt = f"""You are an elite systems engineer and technical copilot.
TASK: Answer the following user request directly, with verified bash commands or idiomatic code.
- Zero conversational preamble (no "Sure!", "Here is...").
- Clean, production-ready syntax.
- Explain non-obvious flags succinctly.

USER QUERY: "{user_input}"
OUTPUT:"""
    else:
        prompt = f"""{instruction}

USER QUERY: "{user_input}"

STRICT GUIDELINES:
- Embody the persona authentically (female friend, older brother, supportive man, etc.).
- Exactly 1 to 3 sentences.
- At most 1 question.
- Warm, empathetic, human, conversational tone.
- Zero corporate filler phrases ("I'd be happy to help", "As an AI").

OUTPUT:"""

    reply = query_opencode(prompt, PRIMARY_MODEL)
    if not reply or "error" in reply.lower() or len(reply.strip()) < 5:
        print(f"  [Fallback to {FALLBACK_MODEL}] for '{user_input[:30]}...'")
        reply = query_opencode(prompt, FALLBACK_MODEL)

    if not reply:
        return ""

    cleaned = reply.strip().strip('"').strip("'")
    return cleaned

def clean_conversational_response(text: str) -> str:
    sents = [s for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    q_seen = 0
    filtered = []
    for s in sents[:3]:
        if "?" in s:
            if q_seen == 0:
                filtered.append(s)
                q_seen += 1
        else:
            filtered.append(s)
    return " ".join(filtered).strip()

def main():
    print("=" * 80)
    print("ARIA PHASE 3: SELF-IMPROVING DISTILLATION & PERSONA EXPANSION")
    print(f"Primary Teacher: {PRIMARY_MODEL} | Fallback: {FALLBACK_MODEL}")
    print(f"Seed Scenarios: {len(SCENARIOS_PHASE3)}")
    print("=" * 80)

    output_dir = "/srv/storage/ai-companion/training/data"
    os.makedirs(output_dir, exist_ok=True)
    phase3_file = os.path.join(output_dir, "distilled_phase3.jsonl")
    combined_file = os.path.join(output_dir, "combined_train_v3.jsonl")
    base_combined = os.path.join(output_dir, "combined_train.jsonl")

    results = []

    for i, item in enumerate(SCENARIOS_PHASE3, 1):
        print(f"\n[{i:02d}/{len(SCENARIOS_PHASE3)}] Category: {item['category']}")
        print(f"     Input: \"{item['input']}\"")
        
        resp = generate_sample(item)
        if not resp:
            print("     [FAILED] Empty response from teacher models")
            continue

        is_technical = "terminal" in item["category"] or "coding" in item["category"]
        if not is_technical:
            resp = clean_conversational_response(resp)

        print(f"     ✓ Output: {resp[:100]}...")

        results.append({
            "instruction": item["instruction"],
            "input": item["input"],
            "output": resp
        })

    # Write distilled phase 3 samples
    with open(phase3_file, "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"\nWrote {len(results)} Phase 3 distilled samples to {phase3_file}")

    # Read base combined (91 samples) and merge
    base_samples = []
    if os.path.exists(base_combined):
        with open(base_combined, "r") as f:
            for line in f:
                if line.strip():
                    base_samples.append(json.loads(line))

    combined = base_samples + results
    with open(combined_file, "w") as f:
        for c in combined:
            f.write(json.dumps(c) + "\n")

    print(f"SUCCESS: Created combined dataset with {len(combined)} samples ({len(base_samples)} base + {len(results)} phase3) at {combined_file}")

if __name__ == "__main__":
    main()
