"""
Test-Time Reasoning & Token Budgeting Engine for Aria
Implements verifiable 'think-then-act' token budgeting enforcing internal scratchpad
reasoning (<thought>...</thought>) prior to code or command emission.
"""

import re
import ast
from typing import Dict, Any, Optional, Tuple, List


THINK_THEN_ACT_SYSTEM_PROMPT = (
    "You are Aria, an expert sovereign algorithmic engineer and technical copilot. "
    "When faced with programming and technical reasoning tasks, you MUST conduct deep "
    "internal scratchpad reasoning before writing any final solution.\n\n"
    "STRICT EXECUTION PROTOCOL:\n"
    "1. Enclose your internal analysis entirely within <thought> and </thought> tags.\n"
    "2. In <thought>, rigorously analyze:\n"
    "   - Algorithmic invariants and complexity bounds (time & space).\n"
    "   - Edge cases: null/empty inputs, boundary conditions, off-by-one errors, singletons.\n"
    "   - Step-by-step logic and variable state transformations.\n"
    "3. After </thought>, emit the complete, self-contained Python solution inside a single "
    "```python ... ``` code block.\n"
    "4. Do NOT output explanatory conversational fluff after the code block."
)

DIRECT_SYSTEM_PROMPT = (
    "You are Aria, a precise Python programming engine. "
    "Provide the solution directly. Output only the executable Python code inside a "
    "```python ... ``` block. Do not provide any internal thinking scratchpad, "
    "preamble, or post-hoc explanation."
)


class ThinkThenActEngine:
    """
    Manages test-time reasoning compute budgets, scratchpad enforcement,
    and syntactic extraction for verifiable code execution.
    """

    def __init__(self, thinking_token_budget: int = 512, code_token_budget: int = 400):
        self.thinking_token_budget = thinking_token_budget
        self.code_token_budget = code_token_budget
        self.total_budget = thinking_token_budget + code_token_budget

    def format_prompt(self, task_prompt: str, with_reasoning: bool = True) -> List[Dict[str, str]]:
        """
        Builds the chat messages array for Ollama / local inference.
        """
        if with_reasoning:
            return [
                {"role": "system", "content": THINK_THEN_ACT_SYSTEM_PROMPT},
                {"role": "user", "content": task_prompt}
            ]
        else:
            return [
                {"role": "system", "content": DIRECT_SYSTEM_PROMPT},
                {"role": "user", "content": task_prompt}
            ]

    def get_generation_options(self, with_reasoning: bool = True) -> Dict[str, Any]:
        """
        Calculates generation options, adjusting num_predict to allocate compute headroom
        for intermediate reasoning tokens.
        """
        predict_tokens = self.total_budget if with_reasoning else self.code_token_budget
        return {
            "num_predict": predict_tokens,
            "temperature": 0.2 if not with_reasoning else 0.3, # Slight variance for search exploration in reasoning
            "top_p": 0.95,
            "min_p": 0.05,
            "repeat_penalty": 1.10,
            "stop": ["\nUser:", "\nHuman:", "<|im_end|>", "<|endoftext|>"]
        }

    def parse_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Extracts scratchpad reasoning and isolates clean executable code.
        Validates Python abstract syntax tree (AST).
        """
        # 1. Extract <thought>...</thought>
        thought_match = re.search(r"<thought>(.*?)(?:</thought>|$)", raw_response, re.DOTALL)
        scratchpad = thought_match.group(1).strip() if thought_match else ""
        has_scratchpad = bool(scratchpad)

        # 2. Extract code block
        # Look for code after </thought> if present, or anywhere
        text_to_search = raw_response
        if thought_match and "</thought>" in raw_response:
            text_to_search = raw_response.split("</thought>", 1)[1]

        code_match = re.search(r"```(?:python)?\n?(.*?)```", text_to_search, re.DOTALL)
        if code_match:
            clean_code = code_match.group(1).strip()
        else:
            # Fallback: check if the text itself is code
            clean_code = text_to_search.strip()

        # 3. Validate Python AST
        syntax_valid = False
        syntax_error = None
        if clean_code:
            try:
                ast.parse(clean_code)
                syntax_valid = True
            except SyntaxError as e:
                syntax_error = f"SyntaxError at line {e.lineno}: {e.msg}"

        # 4. Token estimation (~3.5 chars / token)
        scratchpad_tokens = max(0, int(len(scratchpad) / 3.5))
        code_tokens = max(0, int(len(clean_code) / 3.5))

        return {
            "has_scratchpad": has_scratchpad,
            "scratchpad": scratchpad,
            "scratchpad_tokens_est": scratchpad_tokens,
            "clean_code": clean_code,
            "code_tokens_est": code_tokens,
            "syntax_valid": syntax_valid,
            "syntax_error": syntax_error,
            "raw_response": raw_response
        }
