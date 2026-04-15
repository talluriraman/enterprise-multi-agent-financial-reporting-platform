"""
HTTP client for internal finance APIs exposed via APIM.

APIM enforces rate limits, OAuth scopes, and routes to permission service for consent.
"""

import json
import logging
from pathlib import Path
from typing import Any

import httpx

from app.config import settings
from app.tools.permission import ToolSensitivity, evaluate_tool_call

logger = logging.getLogger(__name__)

_SAMPLE = Path(__file__).resolve().parent.parent.parent / "data" / "sample_expenses_2026.json"


class ApimFinanceClient:
    def __init__(self) -> None:
        self._base = settings.apim_base_url.rstrip("/")
        self._key = settings.apim_subscription_key

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self._key:
            h["Ocp-Apim-Subscription-Key"] = self._key
        return h

    def _local_sample(self, year: int) -> dict[str, Any]:
        data = json.loads(_SAMPLE.read_text(encoding="utf-8"))
        if year != data.get("year"):
            return {"year": year, "monthly": [], "note": "Sample data only includes 2026 in this POC."}
        return {"year": year, "monthly": data["monthly"], "currency": data.get("currency", "USD")}

    async def get_monthly_expenses(self, year: int) -> dict[str, Any]:
        decision = evaluate_tool_call("get_monthly_expenses", ToolSensitivity.medium)
        if not decision.allowed:
            raise PermissionError(decision.notes)
        url = f"{self._base}{settings.internal_finance_path}/expenses/monthly"
        params = {"year": year}
        data: dict[str, Any]
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(url, params=params, headers=self._headers())
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            if settings.demo_mode:
                logger.warning("apim fallback local sample (demo_mode): %s", e)
                data = self._local_sample(year)
            else:
                raise
        logger.info(
            "apim.tool_call tool=get_monthly_expenses consent=%s refresh=%s",
            decision.requires_consent,
            decision.requires_user_token_refresh,
        )
        return data
