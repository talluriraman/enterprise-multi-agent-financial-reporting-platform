import logging
from uuid import UUID

import httpx

from app.jobs.store import job_store
from app.memory.long_term import save_job_memory
from app.models.schemas import JobStatus
from app.orchestrator.graph import run_orchestration
from app.servicebus.noop import NoOpServiceBus

logger = logging.getLogger(__name__)
_bus = NoOpServiceBus()


async def process_job(job_id: UUID) -> None:
    rec = job_store.get(job_id)
    if not rec:
        return
    job_store.update(job_id, status=JobStatus.running)
    await _bus.publish(
        "jobs.started",
        {"job_id": str(job_id), "correlation_id": rec.correlation_id},
        rec.correlation_id,
    )
    try:
        out = await run_orchestration(rec.prompt)
        pv = out.get("prompt_validation_details") or {}
        blocked = bool(out.get("input_blocked", False))
        if blocked:
            response_type = "blocked"
        elif pv.get("acceptable") is False:
            response_type = "guidance"
        else:
            response_type = "report"

        result = {
            "final_report": out.get("final_report", ""),
            "llm_output": out.get("llm_output") or {},
            "response_type": response_type,
            "assigned_agents": out.get("assigned_agents", []),
            "financial_payload": out.get("financial_payload", {}),
            "input_blocked": blocked,
            "input_reasons": out.get("input_reasons", []),
            "input_guard": out.get("input_guard_details", {}),
            "prompt_validation": pv,
            "prompt_enhancement": out.get("prompt_enhancement_details", {}),
            "output_redactions": out.get("output_redactions", []),
        }
        job_store.update(job_id, status=JobStatus.succeeded, result=result)
        await save_job_memory(
            job_id,
            summary=result["final_report"][:2000],
            meta={"agents": result["assigned_agents"], "blocked": result["input_blocked"]},
        )
        await _bus.publish(
            "jobs.completed",
            {"job_id": str(job_id), "status": "succeeded"},
            rec.correlation_id,
        )
        if rec.callback_url:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    await client.post(
                        rec.callback_url,
                        json={"job_id": str(job_id), "status": "succeeded", "result": result},
                    )
            except Exception as e:
                logger.warning("callback_failed job_id=%s err=%s", job_id, e)
    except Exception as e:
        logger.exception("job_failed job_id=%s", job_id)
        job_store.update(job_id, status=JobStatus.failed, error=str(e))
        await _bus.publish(
            "jobs.failed",
            {"job_id": str(job_id), "error": str(e)},
            rec.correlation_id,
        )
