from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Enterprise Multi-Agent Financial Reporting Platform"
    api_prefix: str = "/api/v1"

    # OBO / JWT (validate signature against JWKS in production)
    obo_tenant_id: str = ""
    obo_audience: str = "api://financial-reporting-platform"
    obo_require_auth: bool = False

    # Azure OpenAI / AI Foundry (OpenAI-compatible)
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_chat_deployment: str = "gpt-4o"
    azure_embedding_deployment: str = "text-embedding-3-small"

    # Internal services (APIM base URL for tool calls)
    apim_base_url: str = "http://127.0.0.1:8000"
    apim_subscription_key: str = ""
    internal_finance_path: str = "/internal/finance"

    # MSI: use managed identity for outbound calls when True
    use_managed_identity: bool = False

    # Persistence
    sqlite_path: str = "./data/platform_memory.sqlite3"

    # Demo
    demo_mode: bool = True


settings = Settings()
