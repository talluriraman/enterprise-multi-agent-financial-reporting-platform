"""
Managed Service Identity (MSI) for platform → Azure resources (AI Foundry, Key Vault, etc.).

When USE_MANAGED_IDENTITY=true, DefaultAzureCredential chains environment, managed identity,
and other Azure login methods. APIM or downstream APIs may require a user token refresh flow
handled by the permission service (stubbed in this POC).
"""

from azure.identity import DefaultAzureCredential

from app.config import settings

_credential = None


def get_azure_credential():
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential(exclude_interactive_browser_credential=False)
    return _credential


def get_token_for_scope(scope: str) -> str | None:
    if not settings.use_managed_identity and not settings.azure_openai_api_key:
        return None
    try:
        cred = get_azure_credential()
        return cred.get_token(scope).token
    except Exception:
        return None
