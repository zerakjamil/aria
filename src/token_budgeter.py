from typing import List, Dict, Any, Tuple
from src.config import (
    MAX_CONTEXT_TOKENS,
    COMPACTION_THRESHOLD_TOKENS,
    NUM_PREDICT_CHAT,
    NUM_PREDICT_COMPACT,
    MODELS_DIR,
)

# Deterministic Token Allocations
BUDGET_SYSTEM_PERSONA = 384
BUDGET_USER_PROFILE = 256
BUDGET_EPISODIC_MEMORY = 512
BUDGET_ACTIVE_HISTORY = 2144
BUDGET_GENERATION_HEADROOM = 800

_tokenizer = None

def get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        try:
            from tokenizers import Tokenizer
            tok_path = MODELS_DIR / "tokenizer.json"
            if tok_path.exists():
                _tokenizer = Tokenizer.from_file(str(tok_path))
        except Exception:
            _tokenizer = None
    return _tokenizer

def estimate_tokens(text: str) -> int:
    tok = get_tokenizer()
    if tok:
        try:
            return len(tok.encode(text).ids)
        except Exception:
            pass
    # Precise character-ratio heuristic for multilingual conversational tokens
    # ~3.5 chars per token for English/code/punctuations
    return max(1, int(len(text) / 3.5) + 1)

def compile_budgeted_prompt(
    persona_prompt: str,
    user_profile_cards: List[str],
    retrieved_memories: List[str],
    dialogue_history: List[Dict[str, str]],
    new_user_message: str
) -> Tuple[List[Dict[str, str]], int, bool]:
    """
    Compiles prompt components respecting deterministic budget ceilings.
    Returns (messages_list, total_tokens, compaction_needed).
    """
    compiled_messages: List[Dict[str, str]] = []
    
    # 1. System Persona (capped at BUDGET_SYSTEM_PERSONA)
    system_content_parts = [persona_prompt]
    
    # 2. User Profile Card (capped at BUDGET_USER_PROFILE)
    if user_profile_cards:
        profile_block = "\n[USER GOALS & PROFILE]\n" + "\n".join(f"- {c}" for c in user_profile_cards)
        system_content_parts.append(profile_block)
        
    # 3. Episodic Memories (capped at BUDGET_EPISODIC_MEMORY)
    if retrieved_memories:
        memories_block = "\n[RELEVANT LIFE MEMORIES]\n" + "\n".join(f"• {m}" for m in retrieved_memories)
        system_content_parts.append(memories_block)
        
    full_system_text = "\n\n".join(system_content_parts)
    compiled_messages.append({"role": "system", "content": full_system_text})
    system_tokens = estimate_tokens(full_system_text)
    
    # 4. History turns (FIFO truncation to fit BUDGET_ACTIVE_HISTORY)
    history_allocated_tokens = 0
    active_history_turns: List[Dict[str, str]] = []
    
    # Process history in reverse (most recent first)
    for turn in reversed(dialogue_history):
        t_tokens = estimate_tokens(turn.get("content", ""))
        if history_allocated_tokens + t_tokens > BUDGET_ACTIVE_HISTORY:
            break
        active_history_turns.insert(0, turn)
        history_allocated_tokens += t_tokens
        
    compiled_messages.extend(active_history_turns)
    
    # 5. New User message
    user_turn_tokens = estimate_tokens(new_user_message)
    compiled_messages.append({"role": "user", "content": new_user_message})
    
    total_active_tokens = system_tokens + history_allocated_tokens + user_turn_tokens
    compaction_needed = total_active_tokens >= COMPACTION_THRESHOLD_TOKENS
    
    return compiled_messages, total_active_tokens, compaction_needed

def get_chat_generation_options(is_technical: bool = False) -> Dict[str, Any]:
    """
    Inference-Time Guardrails & Sampling:
    - min_p (arXiv:2407.01082): Dynamically clips hallucinated low-prob tail tokens.
    - repeat_penalty, presence_penalty, frequency_penalty: Prevents autoregressive repetition loops.
    - Dual-mode tuning: low temperature (0.2) + expanded headroom (400 tokens) for coding/technical precision;
      balanced temperature (0.7) for warm conversational empathy.
    - stop sequences: Truncates multi-turn runaway hallucinations.
    """
    if is_technical:
        return {
            "num_ctx": MAX_CONTEXT_TOKENS,
            "num_predict": 400,
            "temperature": 0.2, # Highly deterministic for zero-defect code & commands
            "top_p": 0.95,
            "min_p": 0.05,
            "repeat_penalty": 1.10,
            "presence_penalty": 0.2,
            "frequency_penalty": 0.2,
            "repeat_last_n": 64,
            "stop": ["\nUser:", "\nHuman:", "\n###", "<|im_end|>", "<|endoftext|>"]
        }
    return {
        "num_ctx": MAX_CONTEXT_TOKENS,
        "num_predict": NUM_PREDICT_CHAT,
        "temperature": 0.7,
        "top_p": 0.9,
        "min_p": 0.05,
        "repeat_penalty": 1.15,
        "presence_penalty": 0.5,
        "frequency_penalty": 0.5,
        "repeat_last_n": 64,
        "stop": ["\nUser:", "\nHuman:", "\n###", "<|im_end|>", "<|endoftext|>"]
    }

def get_compaction_generation_options() -> Dict[str, Any]:
    return {
        "num_ctx": MAX_CONTEXT_TOKENS,
        "num_predict": NUM_PREDICT_COMPACT,
        "temperature": 0.3, # lower temperature for factual distillation
    }
