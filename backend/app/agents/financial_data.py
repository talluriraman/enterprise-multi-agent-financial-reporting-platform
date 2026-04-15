"""
Financial Data Agent: resolves structured data via tools (APIM → internal finance API).
"""

from __future__ import annotations

import re
from typing import Any

from app.tools.finance_api import tool_fetch_monthly_expenses


async def run_financial_data_agent(enhanced_prompt: str) -> dict[str, Any]:
    year = 2026
    m = re.search(r"\b(20\d{2})\b", enhanced_prompt)
    if m:
        year = int(m.group(1))
    if re.search(r"monthly\s+expenses|expenses\s+report", enhanced_prompt, re.I):
        data = await tool_fetch_monthly_expenses(year)
        return {"agent": "financial_data", "year": year, "data": data}
    return {
        "agent": "financial_data",
        "year": year,
        "data": {"note": "No expense-specific keywords; returning minimal context."},
    }
