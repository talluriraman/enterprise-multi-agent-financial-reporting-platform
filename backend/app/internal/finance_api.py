"""Internal finance API (would be a separate service; colocated for POC demo)."""

import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

_DATA = Path(__file__).resolve().parent.parent.parent / "data" / "sample_expenses_2026.json"


@router.get("/expenses/monthly")
async def monthly_expenses(year: int = 2026):
    data = json.loads(_DATA.read_text(encoding="utf-8"))
    if year != data.get("year"):
        return {"year": year, "monthly": [], "note": "Sample data only includes 2026 in this POC."}
    return {"year": year, "monthly": data["monthly"], "currency": data.get("currency", "USD")}
