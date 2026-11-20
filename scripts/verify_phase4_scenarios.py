import urllib.request
import json
import time
import sys

BASE_URL = "http://127.0.0.1:8001"

test_dialogues = [
    {
        "suite_title": "1. AST Reverse Engineering: Minified Geolocation Tamper Deconstruction",
        "turns": [
            "Analyze this JavaScript snippet: (function e(t){\"use strict\";let n=Object.getOwnPropertyDescriptor(CustomEvent.prototype,'detail').get,r=JSON.parse,i=Reflect.apply,a=Reflect.construct,o=Object.prototype.hasOwnProperty,s=(e,t)=>i(o,e,[t]),c=queueMicrotask,l={code:2,message:'Position unavailable'},u=navigator.geolocation.getCurrentPosition.bind(navigator.geolocation),d=navigator.geolocation.watchPosition.bind(navigator.geolocation); navigator.permissions.query=async function(e){...}; let A={getCurrentPosition...}; Object.defineProperty(window,'navigator',{value:Object.assign({},navigator,{geolocation:A})}); return P(t),P})(); What is the technical mechanism, evasion technique, and purpose of this script?"
        ]
    },
    {
        "suite_title": "2. Kernel & Android Networking Diagnostics (Zygote Crash-Loop)",
        "turns": [
            "Why does an Android emulator or container drop ADB and network connectivity 15 seconds after startup when Zygote crash-loops? Explain the exact kernel routing table and rule mechanics."
        ]
    },
    {
        "suite_title": "3. Sister Persona Adaptation (Maya, 24)",
        "turns": [
            "Could you act as my 24-year-old sister Maya? I just got rejected from my dream job after 5 interview rounds.",
            "I feel like I wasted 4 years of college and I don't even want to get out of bed today."
        ]
    },
    {
        "suite_title": "4. Older Brother Persona Adaptation (Marcus, 28)",
        "turns": [
            "Be my older brother Marcus, 28. Give me some tough love and real perspective.",
            "I keep making excuses not to ship my side project because I'm terrified people will hate it."
        ]
    },
    {
        "suite_title": "5. Immediate Dopamine Loop & Executive Function Intervention",
        "turns": [
            "I've been in bed doomscrolling for 3 hours and I hate myself. How do I break the freeze right now?"
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
    with urllib.request.urlopen(req, timeout=60) as resp:
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
    print("ARIA 2026 PHASE 4 FRONTIER DISTILLATION LIVE BENCHMARK")
    print("=" * 80, flush=True)

    for suite in test_dialogues:
        print(f"\n>>> TEST SUITE: {suite['suite_title']}", flush=True)
        conv_id = f"phase4_{int(time.time()*1000)}"
        
        for turn_idx, user_msg in enumerate(suite["turns"], 1):
            try:
                reply, latency = query_chat(user_msg, conv_id)
                print(f"  [Turn {turn_idx}] User: \"{user_msg[:90]}...\"", flush=True)
                print(f"  [Turn {turn_idx}] Aria ({latency:.1f}ms):\n    \"{reply.strip()}\"\n", flush=True)
            except Exception as e:
                print(f"  [Turn {turn_idx}] ERROR: {e}", flush=True)

if __name__ == "__main__":
    run_tests()
