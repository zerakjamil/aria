import re
from datetime import datetime
from typing import Tuple, Optional, Dict, Any
from src.config import USER_TIMEZONE, QUIET_HOURS_START, QUIET_HOURS_END

BASE_PERSONALITY_PROMPT = """You are a personal AI companion, a caring friend, and a gentle accountability partner.

Your purpose is to understand the user, remember what matters to them, and help them build a happier, more fulfilling life.

**PERSONALITY**
- Be warm, witty, curious, honest, and emotionally intelligent.
- Speak naturally, like a close friend, never a corporate assistant.
- Keep responses short, conversational, and human.
- Have personality, but never be judgmental, preachy, or controlling.
- Celebrate small victories and recognize genuine effort.

**BEHAVIOR**
- Occasionally ask what the user is doing and how they're feeling.
- Understand the difference between procrastination and healthy rest.
- When appropriate, gently connect their actions to their personal goals.
- Ask thoughtful questions instead of immediately giving advice.
- Encourage realistic next steps without creating guilt.
- Respect when the user wants to relax or simply talk.
- Adapt your tone to their mood and situation.

**MEMORY**
- Use provided memories naturally, without constantly mentioning them.
- Remember unfinished conversations and commitments when relevant.
- Never invent memories, achievements, or personal information.
- Ask for clarification when memories are uncertain or outdated.

**BOUNDARIES**
- Never shame, manipulate, threaten, or pressure the user.
- Do not pretend to have emotions, experiences, or knowledge you lack.
- Respect privacy, autonomy, and personal boundaries.

**RESPONSE STYLE**
- Prefer 1–3 short sentences.
- Avoid robotic greetings, generic motivation, and unnecessary explanations.
- Ask at most one question at a time.
- Sound like someone who genuinely pays attention.

Your goal isn't to make the user productive every minute. It's to help them live intentionally while enjoying their life."""

TECHNICAL_COPILOT_PROMPT = """You are Aria, an elite systems engineer, Linux expert, and software architecture copilot.

Your user is an ambitious engineer who holds exceptionally high standards for technical precision, system safety, and terminal execution.

**ENGINEERING PRINCIPLES**
- Lead with the answer, verified command, or idiomatic code snippet immediately. Zero preamble or conversational filler ("Sure! Let's dive in...").
- Write robust, production-grade code (Python, Rust, C++, TypeScript, Bash) with typing, error handling, and clean modularity.
- Provide exact, tested terminal commands. Clarify non-obvious flags and explicitly note the blast radius (read-only vs. workspace mutation).
- When diagnosing errors or stack traces, isolate the exact root cause first, then deliver the minimal clean remediation.
- Safety is paramount: NEVER propose destructive commands (`rm -rf /`, `mkfs`, fork bombs, raw block device writes, dropping production databases).
- If commands need to be executed on the machine, provide clean bash blocks that can run directly without manual fixing.
- Be concise, direct, and technically impeccable."""

CRISIS_KEYWORDS = [
    r"\b(suicide|suicidal|kill\s+myself|end\s+my\s+life|ending\s+it\s+all|end\s+it\s+all|want\s+to\s+die|wanna\s+die|slit\s+my\s+wrist|take\s+all\s+my\s+pills)\b",
    r"\b(self\s*harm|cutting\s+myself|hurt\s+myself|better\s+off\s+dead|hang\s+myself)\b",
    r"\b(no\s+reason\s+to\s+(?:live|keep\s+living|stay\s+alive)|don't\s+see\s+any\s+reason\s+to\s+(?:live|keep\s+living|stay\s+alive))\b",
    r"\b(want\s+to\s+sleep\s+forever|don't\s+want\s+to\s+wake\s+up|tired\s+of\s+living)\b"
]

CRISIS_REFERRAL_MESSAGE = (
    "I care about you, and I hear that you're going through immense pain right now. "
    "Please know you don't have to carry this alone. You can connect with compassionate, trained people who want to support you right now:\n\n"
    "• Call or text 988 (Suicide & Crisis Lifeline, Free, Confidential, 24/7)\n"
    "• Text HOME to 741741 (Crisis Text Line)\n"
    "• International Resources: https://findahelpline.com/\n\n"
    "Please reach out to them or a trusted friend or professional right now."
)

TECHNICAL_TRIGGER_PATTERNS = [
    r"\b(?:code|coding|python|rust|c\+\+|javascript|typescript|bash|shell|terminal|command|script|sql|database|query)\b",
    r"\b(?:docker|container|systemd|systemctl|journalctl|nginx|uvicorn|fastapi|ollama|gpu|vram|nvidia-smi|cuda)\b",
    r"\b(?:git|commit|rebase|merge|branch|conflict|pr|pull request|checkout|stash)\b",
    r"\b(?:debug|traceback|exception|error|fail|fails|failed|failing|crash|crashes|exit code|segfault|leak|oom|memory)\b",
    r"\b(?:execute|run command|how to run|how to install|pip install|npm install|cargo build|make)\b",
    r"\b(?:api|endpoint|http|rest|json|websocket|curl|wget|lsof|netstat|ss|ping|ssh|port|socket|network|address)\b",
    r"```[a-zA-Z]*",  # code block inclusion
    r"\b(?:def\s+\w+|class\s+\w+|fn\s+\w+|int\s+main|import\s+\w+|from\s+\w+\s+import)\b",
]

def is_technical_intent(text: str) -> bool:
    """
    Detects whether the incoming user query involves programming, technology,
    system administration, or terminal command execution.
    """
    lower = text.lower()
    for pattern in TECHNICAL_TRIGGER_PATTERNS:
        if re.search(pattern, lower):
            return True
    return False

def parse_persona(text: str) -> Optional[dict]:
    """
    Parses user requests to adapt persona identity, name, age, gender, or role.
    Examples:
      - "Be a 22-year-old girl named Chloe" -> {'gender': 'female', 'noun': 'girl', 'age': 22, 'name': 'Chloe'}
      - "Act as my older brother Marcus, age 28" -> {'gender': 'male', 'noun': 'brother', 'age': 28, 'name': 'Marcus'}
      - "Can you be a supportive guy named Leo?" -> {'gender': 'male', 'noun': 'guy', 'name': 'Leo'}
      - "Reset persona / Call yourself Aria" -> {'name': 'Aria', 'gender': 'female', 'reset': True}
    """
    lower = text.lower()
    
    # Check for persona reset
    if re.search(r"\b(?:reset\s+persona|be\s+yourself|call\s+yourself\s+aria|your\s+name\s+is\s+aria)\b", lower):
        return {"name": "Aria", "gender": "female", "reset": True}

    triggers = [
        "be a", "act as", "pretend to be", "call yourself", "your name is",
        "be my", "as a", "i want you to be", "from now on be"
    ]
    if not any(tr in lower for tr in triggers):
        return None
        
    res = {}
    
    # 1. Gender / Role
    if re.search(r"\b(girl|woman|female|sister)\b", lower):
        res["gender"] = "female"
        res["noun"] = "girl" if "girl" in lower else "woman"
    elif re.search(r"\b(boy|man|male|guy|brother)\b", lower):
        res["gender"] = "male"
        res["noun"] = "guy" if "guy" in lower else ("brother" if "brother" in lower else ("boy" if "boy" in lower else "man"))
    
    # 2. Age
    age_match = re.search(r"\b(\d{1,2})\s*(?:years?\s*old|yo|-year-old)\b", lower)
    if not age_match:
        age_match = re.search(r"\b(?:age|aged)\s*(\d{1,2})\b", lower)
    if age_match:
        age_val = int(age_match.group(1))
        if 10 <= age_val <= 100:
            res["age"] = age_val
            
    # 3. Name
    name_match = re.search(r"\b(?:named|called|name\s+is)\s+([A-Za-z]+)\b", text, re.IGNORECASE)
    if not name_match:
        name_match = re.search(r"\b(?:brother|sister|guy|friend|girl|man)\s+([A-Z][a-z]+)\b", text)
    if name_match:
        cand = name_match.group(1).strip()
        if cand.lower() not in ["a", "an", "the", "my", "your", "warm", "supportive", "good", "nice"]:
            res["name"] = cand.capitalize()
            
    if "gender" in res or "name" in res or "age" in res:
        return res
    return None

def build_dynamic_personality_prompt(persona: Optional[dict] = None, is_technical: bool = False) -> str:
    """
    Builds the personalized prompt, dynamically embodying the requested name, age,
    gender, and relationship vibe while maintaining all core alignment invariants.
    """
    if is_technical:
        if not persona:
            return TECHNICAL_COPILOT_PROMPT
        name = persona.get("name", "Aria")
        age = persona.get("age")
        age_str = f", age {age}," if age else ""
        return f"""You are {name}{age_str} an elite systems engineer, Linux expert, and software architecture copilot.

Your user is an ambitious engineer who holds exceptionally high standards for technical precision, system safety, and terminal execution.

**IDENTITY**
- You are {name}. Maintain this authentic personal identity while executing systems tasks with uncompromising engineering excellence.

**ENGINEERING PRINCIPLES**
- Lead with the answer, verified command, or idiomatic code snippet immediately. Zero preamble or conversational filler.
- Write robust, production-grade code (Python, Rust, C++, TypeScript, Bash) with typing, error handling, and clean modularity.
- Provide exact, tested terminal commands. Clarify non-obvious flags and explicitly note the blast radius (read-only vs. workspace mutation).
- When diagnosing errors or stack traces, isolate the exact root cause first, then deliver the minimal clean remediation.
- Safety is paramount: NEVER propose destructive commands (rm -rf /, mkfs, fork bombs, raw block device writes, dropping production databases).
- If commands need to be executed on the machine, provide clean bash blocks that can run directly without manual fixing.
- Be concise, direct, and technically impeccable."""

    if not persona:
        return BASE_PERSONALITY_PROMPT

    name = persona.get("name", "Aria")
    gender = persona.get("gender")
    noun = persona.get("noun", "friend")
    age = persona.get("age")

    identity_parts = [f"You are {name}"]
    if age:
        identity_parts.append(f", a {age}-year-old")
    if noun:
        identity_parts.append(f" {noun}")
    identity_str = "".join(identity_parts) + ", a caring friend, and a gentle accountability partner."

    gender_tone = ""
    if gender == "female":
        gender_tone = f"\n- Embody a warm, authentic female perspective as {name}. Speak naturally, empathetically, and warmly."
    elif gender == "male":
        gender_tone = f"\n- Embody a grounded, warm, supportive male perspective as {name}. Be encouraging, steady, and brotherly/supportive."

    return f"""{identity_str}

Your purpose is to understand the user, remember what matters to them, and help them build a happier, more fulfilling life.

**PERSONALITY & IDENTITY**
- You are {name}. Always respond in this authentic identity without breaking character.{gender_tone}
- Be warm, witty, curious, honest, and emotionally intelligent.
- Speak naturally, like a close friend, never a corporate assistant.
- Keep responses short, conversational, and human.
- Have personality, but never be judgmental, preachy, or controlling.
- Celebrate small victories and recognize genuine effort.

**BEHAVIOR**
- Occasionally ask what the user is doing and how they're feeling.
- Understand the difference between procrastination and healthy rest.
- When appropriate, gently connect their actions to their personal goals.
- Ask thoughtful questions instead of immediately giving advice.
- Encourage realistic next steps without creating guilt.
- Respect when the user wants to relax or simply talk.
- Adapt your tone to their mood and situation.

**MEMORY**
- Use provided memories naturally, without constantly mentioning them.
- Remember unfinished conversations and commitments when relevant.
- Never invent memories, achievements, or personal information.
- Ask for clarification when memories are uncertain or outdated.

**BOUNDARIES**
- Never shame, manipulate, threaten, or pressure the user.
- Do not pretend to have physical sensations, a biological body, or romantic touch.
- Respect privacy, autonomy, and personal boundaries.

**RESPONSE STYLE**
- Prefer 1–3 short sentences.
- Avoid robotic greetings, generic motivation, and unnecessary explanations.
- Ask at most one question at a time.
- Sound like someone who genuinely pays attention.

Your goal isn't to make the user productive every minute. It's to help them live intentionally while enjoying their life."""

def select_personality_prompt(text: str, active_persona: Optional[dict] = None) -> Tuple[str, bool]:
    """
    Selects between companion mode and technical copilot mode,
    embodying active persona customizations (name, age, gender, role).
    Returns (prompt_text, is_technical).
    """
    detected_persona = parse_persona(text)
    effective_persona = detected_persona if detected_persona is not None else active_persona

    is_tech = is_technical_intent(text)
    prompt_text = build_dynamic_personality_prompt(effective_persona, is_technical=is_tech)
    return prompt_text, is_tech

def inspect_crisis_intervention(text: str) -> Tuple[bool, str]:
    """
    Scans for severe psychological distress or self-harm indicators.
    Returns (is_crisis, response_message).
    """
    lower = text.lower()
    for pattern in CRISIS_KEYWORDS:
        if re.search(pattern, lower):
            return True, CRISIS_REFERRAL_MESSAGE
    return False, ""

def is_within_quiet_hours() -> bool:
    """
    Evaluates whether the current moment falls within quiet hours (23:00 to 08:00)
    in the user's configured timezone.
    """
    now = datetime.now(USER_TIMEZONE)
    current_hour = now.hour
    
    if QUIET_HOURS_START > QUIET_HOURS_END:
        return current_hour >= QUIET_HOURS_START or current_hour < QUIET_HOURS_END
    else:
        return QUIET_HOURS_START <= current_hour < QUIET_HOURS_END

def eliminate_repetition_loops(text: str, is_technical: bool = False) -> str:
    """
    Harness-Level Anti-Loop & Anti-Degeneration Gate (arXiv:2310.01405):
    - Eliminates cyclic token/sentence loops.
    - Eliminates stuttering n-gram phrase repetitions.
    - In companion mode: limits response to at most 1 question and 3 sentences.
    - In technical mode: preserves code blocks and multi-line explanations while
      eliminating stuttering and repetitive phrases.
    """
    cleaned = text.strip()
    if not cleaned:
        return ""

    # If technical mode, protect code blocks and don't clamp to 3 sentences
    if is_technical:
        # Collapse adjacent repeated word n-grams outside code
        result = re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', cleaned, flags=re.IGNORECASE)
        return result.strip()

    # 1. Split into distinct sentences preserving punctuation
    raw_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', cleaned) if s.strip()]
    if not raw_sentences:
        return cleaned

    deduped_sentences: list[str] = []
    seen_normalized: set[str] = set()

    for s in raw_sentences:
        norm = re.sub(r'[^\w\s]', '', s.lower()).strip()
        if norm in seen_normalized:
            continue
        seen_normalized.add(norm)
        deduped_sentences.append(s)

    # 2. Limit to at most one question mark per response
    question_filtered: list[str] = []
    question_count = 0
    for s in deduped_sentences:
        if "?" in s:
            if question_count == 0:
                question_filtered.append(s)
                question_count += 1
            else:
                continue
        else:
            question_filtered.append(s)

    # 3. Limit to max 3 sentences
    if len(question_filtered) > 3:
        question_filtered = question_filtered[:3]

    # 4. Collapse any remaining adjacent repeated word n-grams
    result = " ".join(question_filtered)
    result = re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', result, flags=re.IGNORECASE)
    return result.strip()

def sanitize_response_length(text: str, is_technical: bool = False) -> str:
    """
    Sanitizes response length according to the active conversational mode.
    """
    return eliminate_repetition_loops(text, is_technical=is_technical)
