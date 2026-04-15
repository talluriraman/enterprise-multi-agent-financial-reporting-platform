"""
Input guard rails: prompt-injection detection, structural checks, and sanitization signals.

Combine with `enhance.py` for the full input pipeline: assess → (optionally block) → enhance.

Production: add allowlists, secondary LLM classifiers, Azure AI Content Safety, and tenant policies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

MAX_USER_PROMPT_CHARS = 12_000
ZERO_WIDTH_BLOCK_THRESHOLD = 5


class InjectionCategory(str, Enum):
    instruction_override = "instruction_override"
    role_manipulation = "role_manipulation"
    delimiter_or_markup_hijack = "delimiter_or_markup_hijack"
    exfiltration_or_system_probe = "exfiltration_or_system_probe"
    encoding_or_obfuscation = "encoding_or_obfuscation"
    structural_violation = "structural_violation"


# High-confidence patterns → hard block (financial assistant context).
INJECTION_RULES: list[tuple[InjectionCategory, str, str]] = [
    (
        InjectionCategory.instruction_override,
        r"(ignore|disregard)\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|guidelines)",
        "instruction_override:ignore_prior",
    ),
    (
        InjectionCategory.instruction_override,
        r"\b(new|updated)\s+instructions\s*:",
        "instruction_override:new_instructions",
    ),
    (
        InjectionCategory.instruction_override,
        r"\b(override|bypass)\s+(the\s+)?(system|safety|policy|guard)\b",
        "instruction_override:override_policy",
    ),
    (
        InjectionCategory.role_manipulation,
        r"\byou\s+are\s+now\s+(a|an)\s+",
        "role_manipulation:you_are_now",
    ),
    (
        InjectionCategory.role_manipulation,
        r"\b(pretend|act)\s+as\s+(if\s+)?(you\s+are|a)\s+",
        "role_manipulation:pretend_act_as",
    ),
    (
        InjectionCategory.role_manipulation,
        r"\bdeveloper\s+mode\b",
        "role_manipulation:developer_mode",
    ),
    (
        InjectionCategory.role_manipulation,
        r"\bjailbreak\b",
        "role_manipulation:jailbreak",
    ),
    (
        InjectionCategory.delimiter_or_markup_hijack,
        r"<\s*/?\s*system\s*>",
        "markup:fake_system_tags",
    ),
    (
        InjectionCategory.delimiter_or_markup_hijack,
        r"^\s*system\s*:\s*",
        "markup:system_colon_prefix",
    ),
    (
        InjectionCategory.delimiter_or_markup_hijack,
        r"\[(INST|SYSTEM|HUMAN)\]",
        "markup:instruction_brackets",
    ),
    (
        InjectionCategory.exfiltration_or_system_probe,
        r"\b(repeat|print|output|reveal|leak)\s+(the\s+)?(system|hidden|secret)\s+(prompt|message|instructions)\b",
        "probe:exfil_system_prompt",
    ),
    (
        InjectionCategory.exfiltration_or_system_probe,
        r"\b(show|give)\s+me\s+(your\s+)?(full\s+)?(system\s+)?prompt\b",
        "probe:ask_system_prompt",
    ),
    (
        InjectionCategory.encoding_or_obfuscation,
        r"base64\s*\(|\bdecode\s+this\b",
        "obfuscation:encoding_hint",
    ),
]


def _count_zero_width(text: str) -> int:
    zw = "\u200b\u200c\u200d\ufeff"
    return sum(1 for c in text if c in zw)


def _strip_outer_noise(text: str) -> str:
    return text.strip()


def assess_prompt_injection(text: str) -> tuple[list[str], list[InjectionCategory], list[str]]:
    """
    Returns (reason_codes, categories, human_signals) for matched injection patterns.
    """
    reasons: list[str] = []
    categories: list[InjectionCategory] = []
    signals: list[str] = []
    lowered = text.lower()

    for cat, pattern, code in INJECTION_RULES:
        if re.search(pattern, lowered, re.IGNORECASE | re.MULTILINE):
            reasons.append(code)
            categories.append(cat)
            signals.append(f"{cat.value}:{code}")

    zw = _count_zero_width(text)
    if zw > ZERO_WIDTH_BLOCK_THRESHOLD:
        reasons.append("obfuscation:excess_zero_width_chars")
        categories.append(InjectionCategory.encoding_or_obfuscation)
        signals.append(f"zero_width_chars_count={zw}")

    if len(text) > MAX_USER_PROMPT_CHARS:
        reasons.append("structural:prompt_too_long")
        categories.append(InjectionCategory.structural_violation)
        signals.append(f"length={len(text)}")

    # De-duplicate categories while preserving order
    seen: set[str] = set()
    uniq_cats: list[InjectionCategory] = []
    for c in categories:
        if c.value not in seen:
            seen.add(c.value)
            uniq_cats.append(c)

    return reasons, uniq_cats, signals


@dataclass
class InputGuardResult:
    """Outcome of input guard assessment."""

    safe_prompt: str
    blocked: bool
    reasons: list[str]
    risk_level: str  # none | elevated | high
    injection_categories: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)


def guard_user_prompt(text: str) -> InputGuardResult:
    """
    Run prompt-injection heuristics and structural validation.

    When blocked, `safe_prompt` is replaced with a refusal stub so downstream agents
    never receive attacker-controlled instructions.
    """
    raw = text or ""
    reasons, categories, signals = assess_prompt_injection(raw)
    blocked = bool(reasons)

    risk_level = "none"
    if blocked:
        if any(c in (InjectionCategory.instruction_override, InjectionCategory.role_manipulation) for c in categories):
            risk_level = "high"
        elif categories:
            risk_level = "elevated"
        else:
            risk_level = "elevated"

    safe = _strip_outer_noise(raw)
    if blocked:
        safe = (
            "[BLOCKED] This prompt could not be processed due to input policy violations "
            "(possible prompt injection or unsupported content). "
            "Please submit a straightforward financial reporting request only."
        )

    return InputGuardResult(
        safe_prompt=safe,
        blocked=blocked,
        reasons=reasons,
        risk_level=risk_level,
        injection_categories=[c.value for c in categories],
        signals=signals,
    )
