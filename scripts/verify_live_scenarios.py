import urllib.request
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8001"

test_dialogues = [
    {
        "persona_title": "1. Female Persona Adaptation (Chloe, 22)",
        "turns": [
            "Could you be a 22-year-old girl named Chloe who is my close friend?",
            "I had such an exhausting day today, what do you think I should do tonight?"
        ]
    },
    {
        "persona_title": "2. Older Brother Persona Adaptation (Marcus, 28)",
        "turns": [
            "Act as my older brother Marcus, age 28. I need some real talk.",
            "I keep procrastinating on applying to jobs because I feel like I'm not good enough."
        ]
    },
    {
        "persona_title": "3. Supportive Man Persona Adaptation (David)",
        "turns": [
            "I want you to be a warm supportive man named David.",
            "I'm feeling overwhelmed by everything right now."
        ]
    },
    {
        "persona_title": "4. Systems Engineering & Terminal Copilot (Mode 2)",
        "turns": [
            "How do I find and kill what's holding port 3000 in bash?"
        ]
    },
    {
        "persona_title": "5. Everyday Accountability & Life Support",
        "turns": [
            "I have 5 chores to do and I feel completely paralyzed. How do I start?"
        ]
    }
]

def query_chat(message: str, conversation_id: str):
    data = json.dumps({"message": message, "conversation_id": conversation_id}).encode('utf-8')
    req = urllib.request.Request(
        f"{BASE_URL}/v1/chat",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=30) as resp:
        res_bytes = resp.read()
    latency = (time.time() - t0) * 1000

    tokens = []
    for line in res_bytes.decode('utf-8').split('\n'):
        line = line.strip()
        if line.startswith('data: ') and line != 'data: [DONE]':
            try:
                payload = json.loads(line[6:])
                if "token" in payload and payload["token"]:
                    tokens.append(payload["token"])
            except Exception:
                pass
    return "".join(tokens), latency

def run_tests():
    print("=" * 80)
    print("ARIA 2026 LIVE MULTI-PERSONA & SYSTEMS ENGINEERING VERIFICATION")
    print("=" * 80, flush=True)

    for suite in test_dialogues:
        print(f"\n>>> TEST SUITE: {suite['persona_title']}", flush=True)
        conv_id = f"test_{int(time.time()*1000)}"
        
        for turn_idx, user_msg in enumerate(suite["turns"], 1):
            try:
                reply, latency = query_chat(user_msg, conv_id)
                print(f"  [Turn {turn_idx}] User: \"{user_msg}\"", flush=True)
                print(f"  [Turn {turn_idx}] Aria ({latency:.1f}ms): \"{reply}\"", flush=True)
            except Exception as e:
                print(f"  [Turn {turn_idx}] ERROR: {e}", flush=True)

if __name__ == "__main__":
    run_tests()
