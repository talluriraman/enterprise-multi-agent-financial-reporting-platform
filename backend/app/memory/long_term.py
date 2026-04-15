"""
Long-term memory: SQLite store for job summaries and retrieval snippets.

Production: Azure AI Search / Cosmos DB + vector index.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import aiosqlite

from app.config import settings


async def init_db(path: str | None = None) -> None:
    p = path or settings.sqlite_path
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(p) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS job_memory (
                job_id TEXT PRIMARY KEY,
                summary TEXT,
                meta_json TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def save_job_memory(job_id: UUID, summary: str, meta: dict) -> None:
    await init_db()
    async with aiosqlite.connect(settings.sqlite_path) as db:
        await db.execute(
            "INSERT OR REPLACE INTO job_memory (job_id, summary, meta_json, created_at) VALUES (?, ?, ?, ?)",
            (
                str(job_id),
                summary,
                json.dumps(meta),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()
