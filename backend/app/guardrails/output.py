"""
Output guard rails: redact obvious secrets and cap length for demo safety.
"""

import re
from dataclasses import dataclass


@dataclass
class OutputGuardResult:
    text: str
    redactions: list[str]


_SECRET_PATTERNS = [
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "credit_card_like"),
]


def guard_output(text: str, max_chars: int = 24_000) -> OutputGuardResult:
    redactions: list[str] = []
    out = text
    for rx, label in _SECRET_PATTERNS:
        if rx.search(out):
            out = rx.sub("[REDACTED]", out)
            redactions.append(label)
    if len(out) > max_chars:
        out = out[: max_chars - 20] + "\n...[truncated]"
        redactions.append("length_cap")
    return OutputGuardResult(text=out, redactions=redactions)
