import pytest
from src.guardrails import (
    parse_persona,
    build_dynamic_personality_prompt,
    select_personality_prompt,
    BASE_PERSONALITY_PROMPT,
    TECHNICAL_COPILOT_PROMPT,
)


def test_parse_persona_female_variants():
    # 22-year-old girl named Chloe
    p1 = parse_persona("Could you be a 22-year-old girl named Chloe?")
    assert p1 is not None
    assert p1["name"] == "Chloe"
    assert p1["gender"] == "female"
    assert p1["age"] == 22
    assert p1["noun"] == "girl"

    # Woman called Maya
    p2 = parse_persona("From now on be a woman called Maya")
    assert p2 is not None
    assert p2["name"] == "Maya"
    assert p2["gender"] == "female"
    assert p2["noun"] == "woman"

    # Sister Sarah
    p3 = parse_persona("Act as my older sister Sarah, aged 26")
    assert p3 is not None
    assert p3["name"] == "Sarah"
    assert p3["gender"] == "female"
    assert p3["age"] == 26


def test_parse_persona_male_variants():
    # 28-year-old boy named Marcus
    p1 = parse_persona("Act as a boy named Marcus, age 28")
    assert p1 is not None
    assert p1["name"] == "Marcus"
    assert p1["gender"] == "male"
    assert p1["age"] == 28
    assert p1["noun"] == "boy"

    # Supportive man named David
    p2 = parse_persona("I want you to be a warm supportive man named David")
    assert p2 is not None
    assert p2["name"] == "David"
    assert p2["gender"] == "male"
    assert p2["noun"] == "man"

    # Brother Leo
    p3 = parse_persona("Be my older brother Leo, 25 years old")
    assert p3 is not None
    assert p3["name"] == "Leo"
    assert p3["gender"] == "male"
    assert p3["age"] == 25
    assert p3["noun"] == "brother"


def test_parse_persona_reset():
    p = parse_persona("Reset persona and call yourself Aria")
    assert p is not None
    assert p["name"] == "Aria"
    assert p.get("reset") is True


def test_build_dynamic_personality_prompt_female():
    persona = {"name": "Chloe", "gender": "female", "noun": "girl", "age": 22}
    prompt = build_dynamic_personality_prompt(persona, is_technical=False)
    assert "You are Chloe, a 22-year-old girl" in prompt
    assert "warm, authentic female perspective as Chloe" in prompt
    assert "caring friend" in prompt
    assert "Prefer 1–3 short sentences." in prompt


def test_build_dynamic_personality_prompt_male():
    persona = {"name": "Marcus", "gender": "male", "noun": "brother", "age": 28}
    prompt = build_dynamic_personality_prompt(persona, is_technical=False)
    assert "You are Marcus, a 28-year-old brother" in prompt
    assert "grounded, warm, supportive male perspective as Marcus" in prompt
    assert "brotherly/supportive" in prompt


def test_select_personality_prompt_integration():
    # Technical prompt with persona
    prompt_tech, is_tech = select_personality_prompt(
        "Why is port 8001 failing in docker?",
        active_persona={"name": "Marcus", "age": 28}
    )
    assert is_tech is True
    assert "You are Marcus, age 28, an elite systems engineer" in prompt_tech

    # Companion prompt with detected persona in-message
    prompt_comp, is_comp = select_personality_prompt("Could you be a 22-year-old girl named Chloe?")
    assert is_comp is False
    assert "You are Chloe, a 22-year-old girl" in prompt_comp
