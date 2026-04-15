from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends

from app.auth.obo import OboContext, get_obo_context
from app.jobs.runner import process_job
from app.jobs.store import job_store
from app.models.schemas import (
    CallbackRegistration,
    JobStatus,
    JobStatusResponse,
    SubmitJobRequest,
    SubmitJobResponse,
)

router = APIRouter()


@router.post("/jobs/submit", response_model=SubmitJobResponse)
async def submit_job(
    body: SubmitJobRequest,
    background: BackgroundTasks,
    _ctx: OboContext = Depends(get_obo_context),
):
    rec = job_store.create(body.prompt, body.callback_url, body.correlation_id)
    background.add_task(process_job, rec.job_id)
    return SubmitJobResponse(job_id=rec.job_id, status=JobStatus.queued)


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def check_status(job_id: UUID, _ctx: OboContext = Depends(get_obo_context)):
    rec = job_store.get(job_id)
    if not rec:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown job_id")
    return JobStatusResponse(
        job_id=rec.job_id,
        status=rec.status,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
        result=rec.result,
        error=rec.error,
    )


@router.post("/jobs/callback")
async def register_callback(body: CallbackRegistration, _ctx: OboContext = Depends(get_obo_context)):
    ok = job_store.set_callback(body.job_id, body.callback_url)
    if not ok:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown job_id")
    return {"ok": True}
