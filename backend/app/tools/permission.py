"""
Permission service integration (APIM + consent + token refresh) — POC stubs.

Production flow:
- Tool declares required OAuth scopes / sensitivity.
- Permission service checks user consent; may trigger interactive consent.
- If downstream needs a refreshed user token, broker token exchange via OBO.
"""


from dataclasses import dataclass
from enum import Enum


class ToolSensitivity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


@dataclass
class PermissionDecision:
    allowed: bool
    requires_consent: bool
    requires_user_token_refresh: bool
    notes: str


def evaluate_tool_call(tool_name: str, sensitivity: ToolSensitivity) -> PermissionDecision:
    # POC: allow all low/medium; flag high for demo messaging
    if sensitivity == ToolSensitivity.high:
        return PermissionDecision(
            allowed=True,
            requires_consent=True,
            requires_user_token_refresh=False,
            notes="High-sensitivity tool; production would enforce explicit consent.",
        )
    return PermissionDecision(
        allowed=True,
        requires_consent=False,
        requires_user_token_refresh=False,
        notes="OK",
    )
