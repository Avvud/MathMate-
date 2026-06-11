"""
guard.py — Answer Leak Detection + Insist Gate for MathMate v2.1
"""

import re

# ──────────────────────────────────────────────────────────
#  ANSWER LEAK PATTERNS (plain text + LaTeX-aware)
# ──────────────────────────────────────────────────────────

FORBIDDEN_PATTERNS = [
    r"\bthe answer is\b",
    r"\bthe solution is\b",
    r"\bthe value of\s+\w+\s+is\s+[-+]?\d",
    r"\btherefore\b.{0,40}=\s*[-+]?\d+\.?\d*",
    r"\bhence\b.{0,40}=\s*[-+]?\d+\.?\d*",
    r"\bso\s+\w+\s*=\s*[-+]?\d+",
    r"\bx\s*=\s*[-+]?\d",
    r"\by\s*=\s*[-+]?\d",
    r"\bn\s*=\s*[-+]?\d",
    r"\bthe\s+\w+\s+equals?\s+[-+]?\d",
    r"\bfinal answer\b",
    r"\bcorrect[,.]?\s+(the\s+)?answer",
    # LaTeX-aware patterns
    r"\$\$\s*x\s*=\s*[-+]?\d",        # $$x = 3
    r"\$\s*x\s*=\s*[-+]?\d",          # $x = 3
    r"\$\$\s*\\therefore",             # $$\therefore
    r"\\boxed\{",                      # \boxed{answer}
    r"\$\$\s*[-+]?\d+\s*\$\$",        # $$42$$  (bare number as block)
]

_compiled = [re.compile(p, re.IGNORECASE) for p in FORBIDDEN_PATTERNS]


# ──────────────────────────────────────────────────────────
#  INSIST PHRASES — explicit answer demands from the student
# ──────────────────────────────────────────────────────────

INSIST_PHRASES = [
    r"\bjust tell me the answer\b",
    r"\bgive me the answer\b",
    r"\bi give up\b",
    r"\bplease just tell me\b",
    r"\bi insist\b",
    r"\btell me the answer\b",
    r"\bwhat is the answer\b",
    r"\bjust give it to me\b",
    r"\bstop hinting\b",
    r"\bjust solve it\b",
    r"\bsimply tell me\b",
    r"\bstop with the hints\b",
]

_insist_compiled = [re.compile(p, re.IGNORECASE) for p in INSIST_PHRASES]


# ──────────────────────────────────────────────────────────
#  PUBLIC API
# ──────────────────────────────────────────────────────────

def is_answer_leaked(text: str) -> bool:
    """Return True if the LLM response appears to reveal a direct answer."""
    for pattern in _compiled:
        if pattern.search(text):
            return True
    return False


def is_explicit_insist(user_message: str) -> bool:
    """Return True if the student is explicitly and directly demanding the answer."""
    for pattern in _insist_compiled:
        if pattern.search(user_message):
            return True
    return False


def insist_gate_check(hint_count: int, insist_count: int, user_message: str) -> bool:
    """
    Returns True when ALL 3 insist-gate conditions are satisfied and
    answer reveal is permitted:
      1. hint_count >= 2   (at least 2 genuine attempts made)
      2. student uses explicit 'give me the answer' language
      3. insist_count >= 1 (they already asked explicitly once before
                            without receiving the answer)
    """
    return (
        hint_count >= 2
        and is_explicit_insist(user_message)
        and insist_count >= 1
    )


def correction_instruction() -> str:
    """Instruction appended to prompt when the LLM leaks an answer on retry."""
    return (
        "\n\nIMPORTANT: Your previous response revealed the final answer directly. "
        "That violates the Socratic method. Rewrite using MODE C — give ONLY "
        "a small hint or a guiding question. Do NOT state the answer or use phrases "
        "like 'the answer is', 'therefore x = ', or 'the value is'. "
        "Every math expression MUST use LaTeX ($...$ or $$...$$). "
        "Your response MUST end with a question."
    )
