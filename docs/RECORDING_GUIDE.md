# Recording preparation: Agent platform walkthrough

Use this guide to prepare a **short recording** that explains the **architecture**, then **walks the code** in the same order. Two length options:

| Format | Total time | Best for |
|--------|------------|----------|
| **Short** | **5–7 minutes** | Executive / demo; hits all five themes once |
| **Standard** | **8–12 minutes** | Deeper code + one live demo per theme |

Align narration with the **sequence diagram** (user → gateway → orchestrator → agents → skills/tools → internal API → return path; optional **PendingApproval / NeedsReauth** as future work).

**Reference diagram (save alongside your deck):**  
`assets/c__Users_ramtalluri_AppData_Roaming_Cursor_User_workspaceStorage_ca993fe3a81882af70aec0f16be07d06_images_image-5f27aa86-3459-4ee6-84e9-eaee88adeab9.png`  
(Also under `.cursor/projects/.../assets/` in this workspace.)

---

## Quick reference — five themes → repo locations

| Theme | Say this in one line | Primary files |
|-------|----------------------|---------------|
| **Agent development** | LangGraph orchestrates two agents: data via tools, report via LLM+RAG. | `orchestrator/graph.py`, `agents/*.py` |
| **Model calling (AI Foundry)** | Azure OpenAI chat (+ embeddings for RAG); demo path if not configured. | `llm/azure_chat.py`, `rag/retriever.py`, `config.py` |
| **Guard rails** | Injection block → financial validation → enhancement → output redaction. | `guardrails/input.py`, `validation.py`, `enhance.py`, `output.py` |
| **Prompt validation vs enrichment** | **Validation** = accept/reject + branch; **enrichment** = structured framing for *accepted* prompts only. | `validation.py` + `graph.py` (branch); `enhance.py` |
| **Deployment & hosting** | Docker → optional ACR → Helm on AKS; pipeline builds/pushes/deploys. | `deploy/*` |

---

## 0. Sequence diagram — narration script (30–60 sec)

Use this when your recording shows the **architecture image**. Read slowly; pause on the horizontal “swim” from left to right.

1. **User (impersonated / delegated token)** submits a request into the **Finance Report Platform** (gateway): token validation, claims, **Request ID**.
2. **Agent Orchestrator (LangGraph)** receives the work: discovers route, maintains workflow state, invokes agents (streaming optional in a full product).
3. **Agents** (Planner / Researcher / Reporter style — in code: financial + synthesis) may use the **Skills registry** (RBAC / registration — POC: `permission.py`).
4. **Tools** go through **APIM / MCP gateway + permission service**: validate operation, scopes, token exchange, approval, refresh, **NeedsReauth** (stub in POC).
5. **Internal or external APIs** return data; responses flow **back** through tools → agents → orchestrator → platform → user.
6. **Optional async path:** “Pending approval / needs re-auth” notifications — **not** fully implemented; mention as roadmap.

Then say: *“Our POC implements the center of this diagram: gateway API, LangGraph, two agents, APIM-style tool client, and sample internal finance API.”*

---

## 1. Recording goals

| Goal | What viewers should remember |
|------|------------------------------|
| Architecture | Request flows: **User (OBO)** → **Platform API** → **LangGraph orchestrator** → **agents** → **tools (APIM-style)** → **internal finance API** → response path back. |
| Agent development | At least two agent roles in code: **financial data** (tools) + **report synthesis** (LLM + RAG). |
| Model calling | **Azure OpenAI / AI Foundry** via `compose_financial_summary`; **demo template** when no endpoint/credentials. |
| Guard rails | **Injection** → **validation** → optional **guidance-only** path; **output** redaction. |
| Deployment | **Docker**, **Helm/AKS**, **Azure Pipelines** skeleton; not full production. |

---

## 2. Architecture map (diagram ↔ this repo)

Use this table when you point at the diagram and then switch to the IDE.

| Diagram concept | What to say (one sentence) | Where in code |
|-------------------|----------------------------|---------------|
| User + delegated token | Client sends jobs; production uses **OBO** bearer token. | `backend/app/auth/obo.py`, `POST /api/v1/jobs/submit` |
| Finance Report Platform / gateway | FastAPI exposes **Submit**, **Status**, **Callback**; creates **Request ID**. | `backend/app/main.py`, `backend/app/api/jobs.py` |
| Token validation / RequestId | POC: optional auth; **job_id** = correlation handle. | `obo.py`, `jobs/store.py` |
| Agent Orchestrator (LangGraph) | **State graph**: guard → validate → enhance → agents → output guard. | `backend/app/orchestrator/graph.py`, `state.py` |
| Planner / Researcher / Reporter | POC: **Financial Data Agent** + **Report Synthesis Agent** (names map to “specialized workers”). | `backend/app/agents/financial_data.py`, `report_synthesis.py` |
| Skills registry | Stub: permission checks on **tool** calls. | `backend/app/tools/permission.py` |
| Tool APIM + permission | HTTP client to internal APIs; subscription key; consent flags (POC). | `backend/app/tools/apim_client.py` |
| Internal API | Sample **2026 expenses** JSON + `/internal/finance/...`. | `backend/app/internal/finance_api.py`, `backend/data/sample_expenses_2026.json` |
| Async / bus | **No-op** publisher; swap for Service Bus later. | `backend/app/servicebus/noop.py` |
| UI | Demo client; **Report** + **Download PDF**; diagnostics collapsed. | `client/src/App.tsx`, `pdfReport.ts` |

---

## 3. Suggested recording structure (step by step)

### A. Opening (30–45 sec)

1. Show the **architecture diagram** full screen.
2. Say in one breath: *“User hits the finance report platform; the orchestrator runs LangGraph; agents call tools through an APIM-style gateway; data comes back and we synthesize a report.”*
3. State scope: *“This is a POC: real patterns, stubbed enterprise pieces (full OBO, APIM policies, Service Bus).”*

### B. Agent development & orchestration (2–3 min)

**Talking points**

- **Why LangGraph:** workflow **state** (short-term memory), explicit nodes, no agent-to-agent shortcuts—everything goes through the orchestrator.
- **Two agents:** one pulls **structured finance data** via tools; one **summarizes** with LLM + **RAG** over internal chunks.

**Code walkthrough (in order)**

1. `backend/app/orchestrator/graph.py` — scroll the graph: `input_guard` → `validate_prompt` → branch `guidance_only` **or** `enhance` → `financial_data` → `report_synthesis` → `output_guard`.
2. `backend/app/agents/financial_data.py` — tool call path, year detection.
3. `backend/app/agents/report_synthesis.py` — builds system/user messages, calls LLM compose.

**Optional live demo:** run one valid job (or show Swagger `POST /jobs/submit`) and mention **Request ID**.

### C. Model calling — Azure AI Foundry / OpenAI (1.5–2 min)

**Talking points**

- Production uses **Azure OpenAI** (AI Foundry–compatible endpoint): chat completions for synthesis; embeddings for RAG when configured.
- **Managed identity** path for platform → Azure when keys are not used.

**Code walkthrough**

1. `backend/app/llm/azure_chat.py` — `compose_financial_summary`: Azure path vs **demo** `{ source: demo }`.
2. `backend/app/config.py` — env vars: `AZURE_OPENAI_ENDPOINT`, deployments, `USE_MANAGED_IDENTITY`.
3. `backend/app/rag/retriever.py` — embeddings + retrieval (mention **demo** deterministic vectors if no Azure).

**Optional:** show `.env.example` without secrets.

### D. Guard rails + prompt validation / enrichment (2–3 min)

**Talking points**

- **Layers:** (1) **Injection / policy** input guard, (2) **financial intent + time scope** validation, (3) **enhancement** (orchestrator framing), (4) **output** guard.
- **Wrong prompt:** short user message; full detail stays in diagnostics JSON.

**Prompt validation vs prompt enrichment (say this clearly)**

| | Prompt **validation** | Prompt **enrichment** |
|---|------------------------|------------------------|
| **Purpose** | Decide if the user prompt is a **valid financial reporting ask** (topic + time scope; reject junk). | Frame **accepted** prompts so agents get **clear instructions + policy context**. |
| **When it runs** | Node `validate_prompt` **before** agents; can route to `guidance_only` (no agents). | Node `enhance` only on the **continue** path (validation passed; not injection-blocked). |
| **Code** | `guardrails/validation.py`, `graph.py` (`route_after_validate`) | `guardrails/enhance.py` (`build_prompt_enhancement`) |

**Code walkthrough**

1. `backend/app/guardrails/input.py` — patterns, risk, blocked safe prompt.
2. `backend/app/guardrails/validation.py` — topic + time required; punctuation-only rejected.
3. `backend/app/guardrails/enhance.py` — structured prompt for agents.
4. `backend/app/guardrails/user_messages.py` — short validation message for UI.
5. `backend/app/guardrails/output.py` — redaction.

**Live demo (30 sec):** UI — invalid prompt → **Result** line only; expand **Diagnostics** to show JSON. Valid prompt → **Report** + **Download PDF**.

### E. Deployment and hosting (1.5–2 min)

**Talking points**

- **Container images:** API + static web (nginx proxy sketch).
- **Kubernetes:** Helm chart values (images, env, MSI flags).
- **CI/CD:** Azure Pipelines YAML builds and deploys (replace service connections).

**Code / files to show**

1. `deploy/Dockerfile.backend`, `deploy/Dockerfile.client`, `deploy/nginx.default.conf`
2. `deploy/helm/financial-platform/` — `values.yaml`, templates
3. `deploy/azure-pipelines.yml` — stages overview (no need to run pipeline)

### F. Close (20–30 sec)

- Recap: *“Gateway + LangGraph + agents + tools + RAG + Azure models; guard rails at input and output; path to AKS via Helm and pipeline.”*
- CTA: *“Next: wire full OBO validation, APIM policies, and Service Bus for async jobs.”*

---

## 4. Short “chapter” scripts (read aloud)

Use if you want tighter timing.

**Agent prototype (45 sec)**  
*“The orchestrator is implemented in LangGraph. Nodes handle input guard, validation, prompt enhancement, then the financial agent calls internal APIs through an APIM-style client, and the report agent combines tool JSON with retrieved internal text and calls Azure OpenAI when configured.”*

**Model calling (45 sec)**  
*“Chat completion goes through Azure OpenAI in AI Foundry style: endpoint, deployment name, API key or managed identity. If the service isn’t configured, we return a demo template so the UI still works, and we expose that in the API metadata.”*

**Guard rails (45 sec)**  
*“We block obvious prompt injection, then validate that the user asked for a financial topic with a time scope. If not, we don’t run the agents—we return a short message. Enhancement adds policy framing for valid prompts, and output guard does basic redaction.”*

**Deployment (45 sec)**  
*“The repo includes Dockerfiles for API and web, a Helm chart for AKS, and an Azure Pipelines skeleton that builds images and runs Helm upgrade—teams plug in their registry and cluster connections.”*

---

## 5. Pre-recording checklist

- [ ] API runs: `uvicorn` on `8000`, client `npm run dev` or static preview.
- [ ] `.env` for Azure **optional** — decide whether to show live model or demo.
- [ ] Browser zoom ~100%; IDE font readable; hide unrelated tabs.
- [ ] Diagram image on second monitor or first slide.
- [ ] Test flows once: **valid** sample → report + PDF; **invalid** (`?`) → short result; **diagnostics** expand.

---

## 6. What to avoid in a short recording

- Long JSON on screen (keep diagnostics **collapsed** until you intentionally open them).
- Reading every file line-by-line—show **structure**, then **one deep example** (e.g. `graph.py` only).
- Apologizing for POC stubs—**name them** (Service Bus no-op, permission stubs) and move on.

---

## 7. Optional slide outline (5 slides)

1. Title + one-line problem statement  
2. Architecture diagram (full)  
3. LangGraph node list + agent split  
4. Guard rails stack (4 layers)  
5. Deploy path: Docker → ACR → AKS (Helm) + pipeline  

---

## 8. “Short recording” storyboard (5–7 minutes)

| Min | Segment | Screen | Action |
|-----|---------|--------|--------|
| 0:00–0:45 | Architecture | Diagram slide or image | Read **§0** narration; point to gateway → orchestrator → agents → tools → API |
| 0:45–2:00 | Agents | IDE: `graph.py` → `financial_data.py` → `report_synthesis.py` | Trace one vertical slice: validate branch → tools → LLM |
| 2:00–3:15 | AI Foundry / model | IDE: `azure_chat.py`, `config.py` | Show `compose_financial_summary`; mention MSI + deployments |
| 3:15–4:30 | Guard rails + validation vs enrichment | IDE: `input.py`, `validation.py`, `enhance.py` | Use **§D** table; optional 20 sec UI: invalid vs valid |
| 4:30–5:45 | Deployment | IDE: `deploy/` folder | Open Dockerfiles + `values.yaml` + pipeline YAML headline |
| 5:45–6:30 | Close | Diagram or README | Recap + roadmap (Service Bus, full OBO, APIM policies) |

---

## 9. Practical recording setup (optional)

- **Resolution:** 1920×1080; scale IDE ~100–110% for readability.  
- **Layout:** Diagram on one monitor, IDE on the other; or picture-in-picture diagram corner.  
- **Audio:** Quiet room; test levels; avoid loud keyboard if mic is hot.  
- **Cursor:** Move slowly; pause 1–2 sec after opening a file before scrolling.  
- **Secrets:** Never show `.env` with real keys; use `.env.example` or redacted values.

---

This document is **inline with** the provided sequence diagram: impersonated user / gateway validation, orchestrator, agents, skills/permissions, tool gateway (APIM), and internal API—mapped explicitly to folders and files in this repository.
