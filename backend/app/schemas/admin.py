"""Admin and job-related Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class JobStatus(BaseModel):
    """Background job status."""

    job_id: str
    type: str
    status: str = "pending"
    progress: float = 0.0
    message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
