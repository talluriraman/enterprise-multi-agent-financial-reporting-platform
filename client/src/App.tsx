import { useCallback, useState } from "react";
import { downloadReportPdf } from "./pdfReport";

type JobStatus = "queued" | "running" | "succeeded" | "failed";

type ResponseType = "report" | "guidance" | "blocked";

type StatusResponse = {
  job_id: string;
  status: JobStatus;
  result?: {
    final_report?: string;
    response_type?: ResponseType;
    assigned_agents?: string[];
    input_blocked?: boolean;
    input_reasons?: string[];
    input_guard?: Record<string, unknown>;
    prompt_validation?: { acceptable?: boolean; code?: string; guidance?: string; hints?: string[] };
    prompt_enhancement?: Record<string, unknown>;
    output_redactions?: string[];
    llm_output?: { source?: string; reason?: string; deployment?: string };
  };
  error?: string | null;
};

const API = "/api/v1";

async function submitPrompt(prompt: string): Promise<string> {
  const r = await fetch(`${API}/jobs/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!r.ok) throw new Error(await r.text());
  const j = await r.json();
  return j.job_id as string;
}

async function pollStatus(jobId: string): Promise<StatusResponse> {
  const r = await fetch(`${API}/jobs/${jobId}/status`);
  if (!r.ok) throw new Error(await r.text());
  return (await r.json()) as StatusResponse;
}

function deriveResponseType(result: StatusResponse["result"]): ResponseType {
  if (!result) return "report";
  if (result.input_blocked) return "blocked";
  if (result.prompt_validation && result.prompt_validation.acceptable === false) return "guidance";
  return (result.response_type as ResponseType) || "report";
}

export default function App() {
  const [prompt, setPrompt] = useState("Provide me 2026 Monthly expenses report");
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("");
  const [report, setReport] = useState<string>("");
  const [responseType, setResponseType] = useState<ResponseType | null>(null);
  const [guardJson, setGuardJson] = useState<string>("");
  const [enhanceJson, setEnhanceJson] = useState<string>("");
  const [validationJson, setValidationJson] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [llmSource, setLlmSource] = useState<string | null>(null);

  const clearOutputs = useCallback(() => {
    setReport("");
    setResponseType(null);
    setGuardJson("");
    setEnhanceJson("");
    setValidationJson("");
    setLlmSource(null);
    setErr(null);
  }, []);

  const run = useCallback(async () => {
    setBusy(true);
    clearOutputs();
    try {
      const id = await submitPrompt(prompt);
      setJobId(id);
      setStatus("queued");
      let s: StatusResponse | null = null;
      for (let i = 0; i < 120; i++) {
        s = await pollStatus(id);
        setStatus(s.status);
        if (s.status === "succeeded" || s.status === "failed") break;
        await new Promise((r) => setTimeout(r, 500));
      }
      if (!s) throw new Error("No status");
      if (s.status === "failed") throw new Error(s.error || "Job failed");
      const fr = s.result?.final_report || "";
      const rt = deriveResponseType(s.result);
      setReport(fr);
      setResponseType(rt);
      if (s.result?.input_guard) {
        setGuardJson(JSON.stringify(s.result.input_guard, null, 2));
      }
      if (s.result?.prompt_enhancement) {
        setEnhanceJson(JSON.stringify(s.result.prompt_enhancement, null, 2));
      }
      if (s.result?.prompt_validation) {
        setValidationJson(JSON.stringify(s.result.prompt_validation, null, 2));
      }
      setLlmSource((s.result?.llm_output?.source as string | undefined) ?? null);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, [prompt, clearOutputs]);

  const onPromptChange = (value: string) => {
    setPrompt(value);
    clearOutputs();
    setJobId(null);
    setStatus("");
  };

  const showDiagnostics = guardJson || validationJson || enhanceJson;

  const resultTitle =
    responseType === "guidance"
      ? "Result"
      : responseType === "blocked"
        ? "Request blocked"
        : "Report";

  return (
    <div className="shell">
      <header>
        <h1>Enterprise Multi Agent Financial Reporting Platform</h1>
        <p>LangGraph orchestrator · guard rails · validation · RAG · APIM-style tools (POC)</p>
      </header>
      <main>
        <div className="card">
          <label htmlFor="prompt">User prompt</label>
          <p className="hint">
            Valid requests produce a <strong>Report</strong> you can download as PDF. Invalid prompts return a short
            message (no full report).
          </p>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => onPromptChange(e.target.value)}
            disabled={busy}
          />
          <div className="row">
            <button type="button" onClick={run} disabled={busy || !prompt.trim()}>
              {busy ? "Running…" : "Submit"}
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => onPromptChange("Provide me 2026 Monthly expenses report")}
              disabled={busy}
            >
              Load sample
            </button>
            {jobId && <span className="status">Request ID: {jobId}</span>}
            {status && <span className="status">Status: {status}</span>}
          </div>
          {err && <p className="error">{err}</p>}
        </div>

        {showDiagnostics && (
          <details className="details-diagnostics">
            <summary>Diagnostics (JSON — optional)</summary>
            <div className="card card-guard">
              {guardJson && (
                <>
                  <h3 className="subh">Prompt injection and policy assessment</h3>
                  <pre className="json-block">{guardJson}</pre>
                </>
              )}
              {validationJson && (
                <>
                  <h3 className="subh">Prompt validation</h3>
                  <pre className="json-block">{validationJson}</pre>
                </>
              )}
              {enhanceJson && (
                <>
                  <h3 className="subh">Prompt augmentation</h3>
                  <pre className="json-block">{enhanceJson}</pre>
                </>
              )}
            </div>
          </details>
        )}

        {report && (
          <div className={`card card-report ${responseType === "guidance" ? "card-guidance" : ""}`}>
            <div className="report-header">
              <h2 style={{ margin: 0 }}>{resultTitle}</h2>
              {responseType === "report" && (
                <button
                  type="button"
                  className="btn-pdf"
                  onClick={() => downloadReportPdf(report, jobId)}
                >
                  Download PDF
                </button>
              )}
            </div>

            {responseType === "report" && llmSource === "demo" && (
              <p className="banner-demo">
                Demo template (configure Azure OpenAI for live model output).
              </p>
            )}

            {responseType === "blocked" && (
              <p className="banner-blocked">This request was blocked by input policy.</p>
            )}

            <div className="report-pdf">{report}</div>
          </div>
        )}
      </main>
    </div>
  );
}
