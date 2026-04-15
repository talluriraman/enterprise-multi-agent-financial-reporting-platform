from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class SubmitJobRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=16_000)
    callback_url: str | None = Field(
        default=None,
        description="Optional HTTPS URL the platform POSTs completion payloads to.",
    )
    correlation_id: str | None = None


class SubmitJobResponse(BaseModel):
    job_id: UUID
    status: JobStatus = JobStatus.queued


class JobStatusResponse(BaseModel):
    job_id: UUID
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    result: dict[str, Any] | None = None
    error: str | None = None


class CallbackRegistration(BaseModel):
    job_id: UUID
    callback_url: str
