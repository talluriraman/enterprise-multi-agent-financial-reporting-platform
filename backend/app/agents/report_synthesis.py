"""
Report Synthesis Agent: combines tool output + RAG context via Azure OpenAI.
"""

from __future__ import annotations

import json
from typing import Any

from app.llm.azure_chat import compose_financial_summary
from app.rag.retriever import retrieve_context


async def run_report_synthesis_agent(
    enhanced_prompt: str, financial_payload: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    rag = await retrieve_context(enhanced_prompt)
    system = (
        "You are a financial reporting assistant for an enterprise. "
        "Produce a concise executive summary with bullet points. "
        "Use only the provided tool data and retrieved internal context; do not invent figures."
    )
    user = (
        f"User request:\n{enhanced_prompt}\n\n"
        f"Tool output (JSON):\n{json.dumps(financial_payload, indent=2)[:12000]}\n\n"
        f"Retrieved internal context:\n{rag}\n"
    )
    return await compose_financial_summary(system, user)
