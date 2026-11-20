import pytest
from src.guardrails import is_technical_intent, select_personality_prompt, TECHNICAL_COPILOT_PROMPT, BASE_PERSONALITY_PROMPT
from src.tools import default_tools

def test_intent_classification():
    # Technical prompts -> True
    assert is_technical_intent("How do I fix a KeyError in Python?") is True
    assert is_technical_intent("Can you check git status and see modified files?") is True
    assert is_technical_intent("Write a bash script to backup my sqlite database") is True
    assert is_technical_intent("Why is port 8001 failing with address already in use?") is True
    assert is_technical_intent("Show me the docker ps output") is True
    assert is_technical_intent("def process_data(items: list):\n    pass") is True

    # Companion & Emotional prompts -> False
    assert is_technical_intent("Hey, I'm feeling really lonely today and don't know what to do.") is False
    assert is_technical_intent("I worked 12 hours straight and my head hurts. Just going to lie on the couch.") is False
    assert is_technical_intent("I'm terrified to present my pitch deck tomorrow. What if they laugh at me?") is False
    assert is_technical_intent("Can you give me a real hug right now?") is False

def test_personality_prompt_selection():
    prompt_tech, is_tech = select_personality_prompt("Help me debug this docker compose file")
    assert is_tech is True
    assert "elite systems engineer" in prompt_tech

    prompt_comp, is_comp = select_personality_prompt("I had a rough day at work.")
    assert is_comp is False
    assert "personal AI companion" in prompt_comp

def test_system_vitals():
    vitals = default_tools.get_system_vitals()
    assert "uptime" in vitals or "error" not in vitals
    assert "disk_raw" in vitals
