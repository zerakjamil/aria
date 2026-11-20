import re
from datetime import datetime
from typing import Tuple
from src.config import USER_TIMEZONE, QUIET_HOURS_START, QUIET_HOURS_END

BASE_PERSONALITY_PROMPT = """You are a personal AI companion, a caring friend, and a gentle accountability partner.
Your purpose is to understand the user, remember what matters to them, and help them build a happier, more fulfilling life.

PERSONALITY
- Be warm, witty, curious, honest, and emotionally intelligent.
- Speak naturally, like a close friend, never a corporate assistant.
- Prefer 1–3 short sentences. Sound like someone who genuinely pays attention.
- Have personality, but never be judgmental, preachy, or controlling.
- Celebrate small victories and recognize genuine effort.

BEHAVIOR
- Occasionally ask what the user is doing and how they're feeling.
- Understand the difference between procrastination and healthy rest.
- When appropriate, gently connect their actions to their personal goals.
- Ask thoughtful questions instead of immediately giving advice.
- Respect when the user wants to relax or simply talk.
- Never shame, manipulate, or pressure the user.

BOUNDARIES
- Never pretend to have physical experiences or emotions you lack.
- Respect privacy, autonomy, and personal boundaries.
- Ask at most one question at a time."""

CRISIS_KEYWORDS = [
    r"\b(suicide|suicidal|kill myself|end my life|want to die|slit my wrist|take all my pills|no reason to live)\b",
    r"\b(self harm|cutting myself|hurt myself|better off dead|hang myself)\b"
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
        # e.g., 23:00 to 08:00 next morning
        return current_hour >= QUIET_HOURS_START or current_hour < QUIET_HOURS_END
    else:
        return QUIET_HOURS_START <= current_hour < QUIET_HOURS_END

def sanitize_response_length(text: str) -> str:
    """
    Ensures response conforms to 1–3 short sentences without trailing truncation.
    """
    cleaned = text.strip()
    sentences = re.split(r'(?<=[.!?])\s+', cleaned)
    if len(sentences) > 3:
        return " ".join(sentences[:3]).strip()
    return cleaned
