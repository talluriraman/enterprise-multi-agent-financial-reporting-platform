# Enterprise Multi-Agent Financial Reporting Platform

POC for an enterprise-style multi-agent financial reporting stack: **LangGraph** orchestration, **input/output guard rails**, **tool calls** through an **APIM-style** HTTP client, **RAG** over internal sample 2026 ledger data, **OBO** (bearer) authentication hooks, **MSI** hooks for Azure AI Foundry, a **service bus** abstraction (no-op implementation), and **deployment** artifacts for **AKS** plus an **Azure Pipelines** skeleton.

**Recording / demo prep:** step-by-step script and code walkthrough aligned to the architecture diagram — see [docs/RECORDING_GUIDE.md](docs/RECORDING_GUIDE.md).

## Architecture (POC)

| Layer | Role |
| --- | --- |
| **Client (Vite + React)** | Demo UI titled **Enterprise Multi Agent Financial Reporting Platform**; calls REST APIs. |
| **Platform API (FastAPI)** | Standard endpoints: **Submit**, **Callback** (register webhook), **Check status**. |
| **Orchestrator (LangGraph)** | Workflow state, routing, and sequencing; agents do not call each other directly. |
| **Agents (≥2)** | **Financial Data Agent** (tools / structured data) and **Report Synthesis Agent** (LLM + RAG). |
| **Tools** | HTTP client targets APIM base URL; permission/consent **stubs**; optional local JSON fallback when the API is down (`DEMO_MODE=true`). |
| **Memory** | Short-term: LangGraph state; long-term: SQLite summaries (`backend/data/platform_memory.sqlite3`). |
| **Service Bus** | `ServiceBusPublisher` interface + **NoOp** publisher (swap for Azure Service Bus in production). |
| **Hosting** | `deploy/Dockerfile.*`, `deploy/helm/financial-platform`, `deploy/azure-pipelines.yml`. |

## Standard endpoints

Base path: `/api/v1`

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/jobs/submit` | Body: `{ "prompt": "...", "callback_url": "https://optional", "correlation_id": "optional" }` → `{ job_id, status }`. |
| `GET` | `/jobs/{job_id}/status` | Poll job; includes `result` when `succeeded`. |
| `POST` | `/jobs/callback` | Register/update `callback_url` for a job. On success the platform `POST`s JSON to the callback (best-effort). |
| `GET` | `/health` | Liveness. |

Internal (colocated for demo): `GET /internal/finance/expenses/monthly?year=2026`.

## Security model (POC vs production)

- **Client → platform (OBO):** `Authorization: Bearer` is accepted; set `OBO_REQUIRE_AUTH=true` and implement full JWT validation (issuer, audience, signature via JWKS) for production.
- **Platform → Azure (MSI):** `USE_MANAGED_IDENTITY=true` uses `DefaultAzureCredential` for Azure OpenAI / embeddings when API keys are not set.
- **Tools via APIM:** `APIM_BASE_URL` + optional `Ocp-Apim-Subscription-Key`; throttling and OAuth policies belong on APIM. **Permission service** is stubbed in `app/tools/permission.py` (consent / token refresh flags for high-sensitivity tools).

## Local run (backend)

```bash
cd backend
python -m pip install -r requirements.txt
copy .env.example .env   # Windows: copy; adjust variables
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- With **no** Azure credentials, the **Report Synthesis Agent** uses an offline template (still consumes tool + RAG context in the prompt).
- Set `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` (or MSI), `AZURE_CHAT_DEPLOYMENT`, and `AZURE_EMBEDDING_DEPLOYMENT` for full **Azure AI Foundry / Azure OpenAI** behavior.

## Local run (client)

Requires Node.js 20+.

```bash
cd client
npm install
npm run dev
```

The dev server proxies `/api` to `http://127.0.0.1:8000`.

## Docker (from repository root)

```bash
docker build -f deploy/Dockerfile.backend -t financial-platform-api .
docker build -f deploy/Dockerfile.client -t financial-platform-web .
```

The web image serves static files and proxies `/api` to a service named `platform-api` (adjust `deploy/nginx.default.conf` / Helm to match your cluster service names).

## Deployment

- **Helm:** `deploy/helm/financial-platform` — set image repositories and tune `values.yaml`.
- **Azure Pipelines:** `deploy/azure-pipelines.yml` — replace service connections, ACR name, and Helm release parameters.

## Agent Development / Prototype

This section summarizes how the POC implements **model consumption**, **tool calling**, and **input/output guard rails** so you can extend it toward production.

### Model consumption (Azure AI Foundry / Azure OpenAI)

- Chat completions: `app/llm/azure_chat.py` uses `AsyncAzureOpenAI` with either **API key** or **managed identity** token provider (`azure-identity`).
- Embeddings (RAG): `app/rag/retriever.py` calls the configured **embedding deployment** when credentials exist; otherwise it uses a deterministic pseudo-embedding for offline demos.
- Prompt construction for the synthesis agent includes **tool JSON** plus **retrieved internal chunks** to reduce hallucination risk.

### Tool calling

- Agents invoke tools only through orchestrator-mediated steps (see `app/orchestrator/graph.py`).
- `app/tools/apim_client.py` wraps HTTP calls to the internal finance API path; failures fall back to packaged JSON sample data when `DEMO_MODE=true`.
- `app/tools/permission.py` models **explicit consent** and **user token refresh** requirements for sensitive tools (implementation is intentionally minimal).

### Input guard rails

- `app/guardrails/input.py` applies **prompt-injection heuristics** and length limits; blocked prompts are replaced with a safe refusal string before any agent or tool runs.
- `app/guardrails/enhance.py` **rewrites** the user task into a finance-focused instruction block (production: use a constrained LLM rewrite with schema validation).

### Output guard rails

- `app/guardrails/output.py` applies **basic redaction** (e.g., card-like number patterns) and length caps before returning the report to the client.

## Demo prompt

> Provide me 2026 Monthly expenses report

The **Financial Data Agent** pulls monthly expense rows (sample data in `backend/data/sample_expenses_2026.json`). The **Report Synthesis Agent** combines that payload with **RAG** context from the same file’s policy snippets to produce a summarized report.

## Repository layout

```
backend/           # FastAPI + LangGraph + agents + tools + RAG
client/            # Vite + React demo UI
deploy/            # Dockerfiles, Helm chart, Azure Pipelines skeleton
```

## License

Use and modify for internal POCs; add your organization’s license as needed.

![Reference architecture (illustrative)](https://github.com/user-attachments/assets/e8b28825-3327-4f80-903d-a39228f12d35)
