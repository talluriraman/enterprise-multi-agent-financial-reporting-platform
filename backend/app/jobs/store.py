from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.models.schemas import JobStatus


@dataclass
class JobRecord:
    job_id: UUID
    status: JobStatus
    prompt: str
    callback_url: str | None
    correlation_id: str | None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    result: dict[str, Any] | None = None
    error: str | None = None


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[UUID, JobRecord] = {}

    def create(self, prompt: str, callback_url: str | None, correlation_id: str | None) -> JobRecord:
        jid = uuid4()
        rec = JobRecord(
            job_id=jid,
            status=JobStatus.queued,
            prompt=prompt,
            callback_url=callback_url,
            correlation_id=correlation_id,
        )
        self._jobs[jid] = rec
        return rec

    def get(self, job_id: UUID) -> JobRecord | None:
        return self._jobs.get(job_id)

    def update(
        self,
        job_id: UUID,
        *,
        status: JobStatus | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        rec = self._jobs[job_id]
        if status is not None:
            rec.status = status
        if result is not None:
            rec.result = result
        if error is not None:
            rec.error = error
        rec.updated_at = datetime.now(timezone.utc)

    def set_callback(self, job_id: UUID, callback_url: str) -> bool:
        rec = self._jobs.get(job_id)
        if not rec:
            return False
        rec.callback_url = callback_url
        rec.updated_at = datetime.now(timezone.utc)
        return True


job_store = InMemoryJobStore()
