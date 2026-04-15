"""
Prompt validation for financial reporting tasks (post injection guard).

Requires BOTH a concrete financial topic AND a time scope. This avoids false passes from
common English words like "report" or "may" (modal verb) that previously satisfied loose regexes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# At least one strong signal: domain/metric (NOT bare "report"/"reporting" alone).
_STRONG_FINANCIAL = re.compile(
    r"\b("
    r"expenses?|revenue|financial|finance|ledger|budget|forecast|"
    r"p\s*&\s*l|profit\s+and\s+loss|balance\s+sheet|cash\s+flow|"
    r"payroll|opex|capex|ebitda|burn\s+rate|run\s*rate|"
    r"accounts?\s+payable|accounts?\s+receivable|gl\b|general\s+ledger|"
    r"operating\s+expenses?|capital\s+expenditure|gross\s+margin|net\s+income|"
    r"ebit|ebitda|yoy|variance|accrual|reconciliation"
    r")\b",
    re.IGNORECASE,
)

# "report" / "reporting" only count when paired with financial context (avoid "weather report").
_REPORT_WITH_CONTEXT = re.compile(
    r"\b("
    r"financial\s+report|expense\s+report|management\s+report|executive\s+report|"
    r"monthly\s+report|quarterly\s+report|annual\s+report|budget\s+report|"
    r"reporting\s+package|management\s+reporting|financial\s+reporting"
    r")\b",
    re.IGNORECASE,
)

_YEAR = re.compile(r"\b(20[2-9]\d)\b")

# Time scope: years, quarters, fiscal, monthly/annual as reporting periods. Excludes "may" (modal vs month ambiguity).
_TIME_SCOPE = re.compile(
    r"\b("
    r"20[2-9]\d|"
    r"q[1-4]\b|quarter|quarterly|monthly|annual|annualized|ytd|mtd|fy\s*\d{2,4}|"
    r"fiscal\s*(year)?|calendar\s+year|semester|h[12]\b|"
    r"january|february|march|april|june|july|august|september|october|november|december|"
    r"(last|this|next)\s+quarter|(last|this|next)\s+month|(last|this|next)\s+fiscal\s+year"
    r")\b",
    re.IGNORECASE,
)


@dataclass
class PromptValidationResult:
    acceptable: bool
    code: str
    guidance: str
    hints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "acceptable": self.acceptable,
            "code": self.code,
            "guidance": self.guidance,
            "hints": self.hints,
        }


def _guidance_for(_code: str, hints: list[str]) -> str:
    body = (
        "### We need a clearer financial reporting request\n\n"
        "This assistant only generates **enterprise financial reports** using approved tools and internal context. "
        "Your message must name a **financial topic** (for example expenses, revenue, budget, P&L) "
        "and a **time scope** (for example **2026**, **Q1**, **monthly**, **fiscal year**).\n\n"
        "**Examples that validate:**\n\n"
        "- Provide me **2026 monthly expenses** report\n"
        "- **Q1 vs Q2** operating **expenses** summary\n"
        "- **P&L** for **fiscal year 2025**\n\n"
        "**Avoid:** single generic words, unrelated topics, or time-only / topic-only prompts.\n"
    )
    if hints:
        body += "\n**Checks:** " + " · ".join(hints) + "\n"
    return body


def _has_financial_topic(text: str) -> bool:
    return bool(_STRONG_FINANCIAL.search(text) or _REPORT_WITH_CONTEXT.search(text))


def _has_time_scope(text: str) -> bool:
    return bool(_YEAR.search(text) or _TIME_SCOPE.search(text))


def _is_punctuation_or_whitespace_only(text: str) -> bool:
    """True if there are no letters or digits (e.g. '?', '???', '...')."""
    if not text:
        return True
    return not any(ch.isalnum() for ch in text)


def assess_financial_prompt_quality(user_text: str) -> PromptValidationResult:
    """
    Heuristic validation: require financial topic AND time scope.

    Not a security boundary—injection is handled separately in `input.py`.
    """
    text = (user_text or "").strip()
    hints: list[str] = []

    if _is_punctuation_or_whitespace_only(text):
        hints.append("Use words and numbers (financial topic + time period), not only punctuation.")
        return PromptValidationResult(
            False,
            "invalid_prompt",
            _guidance_for("invalid_prompt", hints),
            hints,
        )

    if len(text) < 10:
        hints.append("Prompt is too short; add a financial topic and a time period.")
        return PromptValidationResult(
            False,
            "too_short",
            _guidance_for("too_short", hints),
            hints,
        )

    has_topic = _has_financial_topic(text)
    has_time = _has_time_scope(text)

    if not has_topic and not has_time:
        hints.append("No clear financial topic and no time scope detected.")
        return PromptValidationResult(
            False,
            "missing_topic_and_time",
            _guidance_for("missing_topic_and_time", hints),
            hints,
        )

    if not has_topic:
        hints.append("Add a financial topic (expenses, revenue, budget, P&L, ledger, payroll, etc.).")
        return PromptValidationResult(
            False,
            "missing_financial_topic",
            _guidance_for("missing_financial_topic", hints),
            hints,
        )

    if not has_time:
        hints.append("Add a time scope (for example calendar year 2026, Q1, monthly, or fiscal year).")
        return PromptValidationResult(
            False,
            "missing_time_scope",
            _guidance_for("missing_time_scope", hints),
            hints,
        )

    return PromptValidationResult(True, "ok", "", [])
