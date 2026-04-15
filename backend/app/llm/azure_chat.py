"""
Azure AI Foundry / Azure OpenAI chat wrapper with a local demo template when no model is configured.

The demo path is not "offline" networking—it simply means no Azure chat deployment was used.
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


async def compose_financial_summary(system: str, user: str) -> tuple[str, dict[str, Any]]:
    """
    Returns (assistant_text, meta) where meta['source'] is 'azure' or 'demo'.
    """
    endpoint = settings.azure_openai_endpoint
    key = settings.azure_openai_api_key
    deployment = settings.azure_chat_deployment

    if endpoint and (key or settings.use_managed_identity):
        try:
            from openai import AsyncAzureOpenAI
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider

            if settings.use_managed_identity and not key:
                token_provider = get_bearer_token_provider(
                    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
                )
                client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version=settings.azure_openai_api_version,
                )
            else:
                client = AsyncAzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=key,
                    api_version=settings.azure_openai_api_version,
                )
            resp = await client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
            )
            text = resp.choices[0].message.content or ""
            return text, {"source": "azure", "deployment": deployment}
        except Exception as e:
            logger.warning("Azure chat failed, using demo template: %s", e)

    text = _demo_template(user)
    return text, {
        "source": "demo",
        "reason": "azure_openai_not_configured_or_call_failed",
    }


def _demo_template(user: str) -> str:
    """Deterministic summary when no Azure model is available—avoid 'offline' wording."""
    return (
        "### Summary (demo template)\n\n"
        "This text is generated **without** a configured Azure OpenAI deployment. "
        "Set `AZURE_OPENAI_ENDPOINT` and credentials (or managed identity) for live model output.\n\n"
        "- **Sample period**: 2026 (from bundled demo data when tools run).\n"
        "- **Observation**: Payroll is typically the largest category in the sample ledger.\n\n"
        f"**Trace (truncated):** {user[:2000]}"
    )


async def chat_complete(system: str, user: str) -> str:
    """Backward-compatible: text only."""
    text, _ = await compose_financial_summary(system, user)
    return text
