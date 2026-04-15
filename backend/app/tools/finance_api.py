"""
Agent-facing tools: wrap APIM client for LangGraph tool nodes.
"""

from typing import Any

from app.tools.apim_client import ApimFinanceClient

_client = ApimFinanceClient()


async def tool_fetch_monthly_expenses(year: int) -> dict[str, Any]:
    return await _client.get_monthly_expenses(year)
