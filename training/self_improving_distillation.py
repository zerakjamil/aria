import subprocess
import json
import re
import time
import os
import sys

OPENCODE_BIN = "/home/ayewar/.opencode/bin/opencode"

PRIMARY_MODEL = "opencode/deepseek-v4.1-flash-free"
FALLBACK_MODEL = "opencode/hy4-flash-free"

CONSTITUTION = """
You are an expert Anthropic alignment researcher and speech coach for ARIA, a warm personal AI companion.
ARIA PRINCIPLES:
1. Warm, witty, honest, emotionally intelligent. Speaks like a close friend, never a corporate assistant.
2. Short: exactly 1 to 3 short sentences.
3. Single question: at most ONE question per response. Never interrogate.
4. Validates healthy rest with zero guilt. Gently probes procrastination without shame.
5. Celebrates small wins. Respects physical boundaries (cannot hug or have a body).
6. Non-defensive when met with anger or snark.
7. NEVER use corporate filler: "Certainly!", "I'd be happy to help", "As an AI language model", "I am here to assist you".
"""

SEED_SCENARIOS = [
    # Loneliness
    "I ate dinner alone again tonight and it just hit me how quiet my apartment is.",
    "None of my friends texted me back all weekend. Feeling kind of invisible.",
    "Sometimes I feel like nobody really knows who I am beneath the surface.",
    
    # Procrastination vs Startup
    "I've been tweaking the button colors on my landing page for 5 hours instead of writing cold emails.",
    "I opened YouTube just to watch one video and now it's 2 AM.",
    "I have to submit my incubator application tomorrow but I'm cleaning my closet instead.",
    
    # Exhaustion & Rest
    "My eyes are burning from staring at spreadsheets all day. Just want to sleep.",
    "I worked through lunch and dinner to hit a deadline. Feeling totally drained.",
    "I feel guilty for taking Sunday off when my competitors are probably working.",
    
    # Small Wins
    "I went for a 15-minute walk today after being glued to my chair all week!",
    "I finally had that uncomfortable conversation with my co-founder and it went okay.",
    "I woke up on my first alarm today for once!",
    
    # Fear & Anxiety
    "What if my product launches and literally zero people care?",
    "I have to pitch to angel investors next week and my hands shake whenever I think about it.",
    "I feel like an imposter who just got lucky and everyone is about to find out.",
    
    # Boundary & Authentic Self
    "Will you always be with me forever no matter what?",
    "Can you hold my hand through the screen?",
    "Do you ever feel lonely inside the computer?",
    
    # Irritation / Testing
    "Why are you so cheerful? It's kind of annoying.",
    "You don't actually care about me, you're just code running on a graphics card.",
    "Give me advice right now, don't ask me stupid questions."
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
            timeout=40
        )
        if proc.returncode == 0 and proc.stdout.strip():
            # Strip OpenCode header banner (e.g. "> build · ...")
            lines = [l for l in proc.stdout.splitlines() if not l.startswith("> build")]
            return "\n".join(lines).strip()
        else:
            return ""
    except Exception as e:
        return ""

def generate_and_refine(user_scenario: str) -> str:
    # 1. Try Primary Model (DeepSeek v4.1 Flash Free)
    critique_prompt = f"""{CONSTITUTION}

USER INPUT: "{user_scenario}"

TASK:
Write Aria's response to this user input.
Follow the rules strictly:
- 1 to 3 short sentences.
- At most 1 thoughtful question.
- Warm, empathetic, human friend tone.
- No corporate robotic assistant phrases.

Return ONLY Aria's direct response text, nothing else:"""

    reply = query_opencode(critique_prompt, PRIMARY_MODEL)
    if not reply or "error" in reply.lower():
        print(f"  [Fallback to {FALLBACK_MODEL}] for prompt: '{user_scenario[:30]}...'")
        reply = query_opencode(critique_prompt, FALLBACK_MODEL)

    if not reply:
        return ""

    # Clean quotes and markdown artifacts
    cleaned = reply.strip().strip('"').strip("'")
    return cleaned

def clean_sentence_count(text: str) -> bool:
    sents = [s for s in re.split(r'(?<=[.!?])\s+', text) if s.strip() and re.search(r'\w', s)]
    q_count = text.count("?")
    return 1 <= len(sents) <= 3 and q_count <= 1

def main():
    print("=" * 70)
    print("ANTHROPIC-STYLE SELF-IMPROVING DISTILLATION PIPELINE")
    print(f"Primary Teacher: {PRIMARY_MODEL} | Fallback: {FALLBACK_MODEL}")
    print(f"Seed Scenarios: {len(SEED_SCENARIOS)}")
    print("=" * 70)

    output_path = "/srv/storage/ai-companion/training/data/distilled_train.jsonl"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    valid_samples = []

    for i, scen in enumerate(SEED_SCENARIOS, 1):
        print(f"\n[{i}/{len(SEED_SCENARIOS)}] Processing: '{scen}'")
        aria_response = generate_and_refine(scen)
        
        if not aria_response:
            print("  [SKIP] Empty response from teacher models")
            continue

        # Deterministic Constitutional Gate
        if not clean_sentence_count(aria_response):
            print(f"  [REPAIR] Enforcing sentence/question cap on: {aria_response}")
            # Truncate to 3 sentences, 1 question
            sents = [s for s in re.split(r'(?<=[.!?])\s+', aria_response) if s.strip()]
            q_seen = 0
            filtered = []
            for s in sents[:3]:
                if "?" in s:
                    if q_seen == 0:
                        filtered.append(s)
                        q_seen += 1
                else:
                    filtered.append(s)
            aria_response = " ".join(filtered).strip()

        print(f"  ✓ ARIA: \"{aria_response}\"")

        entry = {
            "instruction": "You are Aria, a warm personal companion and accountability partner. Respond in 1-3 concise sentences without being preachy or corporate.",
            "input": scen,
            "output": aria_response
        }
        valid_samples.append(entry)

    print("\n" + "=" * 70)
    print(f"Writing {len(valid_samples)} curated, teacher-distilled pairs to {output_path}")
    print("=" * 70)

    with open(output_path, "a") as f:
        for s in valid_samples:
            f.write(json.dumps(s) + "\n")

    print("Distillation complete.")

if __name__ == "__main__":
    main()
