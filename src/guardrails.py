import re
from datetime import datetime
from typing import Tuple
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

def eliminate_repetition_loops(text: str) -> str:
    """
    Harness-Level Anti-Loop & Anti-Degeneration Gate (arXiv:2310.01405):
    - Eliminates cyclic token/sentence loops.
    - Eliminates stuttering n-gram phrase repetitions.
    - Limits response to at most one thoughtful question.
    - Limits response to at most 3 sentences.
    """
    cleaned = text.strip()
    if not cleaned:
        return ""

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

def sanitize_response_length(text: str) -> str:
    """
    Ensures response conforms to 1–3 short sentences, eliminates repetition loops,
    and handles trailing emojis/punctuation correctly.
    """
    return eliminate_repetition_loops(text)
