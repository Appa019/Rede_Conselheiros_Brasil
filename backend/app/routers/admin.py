"""Admin endpoints for triggering ETL, metrics computation, and ML training."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from app.graph.neo4j_client import Neo4jClient
from app.graph.metrics import compute_and_save_metrics, invalidate_graph_cache
from app.etl.orchestrator import run_etl
from app.ml.train import run_training_pipeline
from app.schemas.common import JobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

# In-memory job store
_jobs: dict[str, dict[str, Any]] = {}
_running_types: set[str] = set()
MAX_JOBS = 50


def _create_job(job_type: str) -> str:
    """Create a new job entry and return its ID."""
    if job_type in _running_types:
        raise HTTPException(
            status_code=409,
            detail=f"A {job_type} job is already running",
        )

    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {
        "job_id": job_id,
        "type": job_type,
        "status": "pending",
        "progress": 0.0,
        "message": "",
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "result": None,
    }
    _running_types.add(job_type)

    # Evict old jobs
    if len(_jobs) > MAX_JOBS:
        oldest = sorted(_jobs, key=lambda k: _jobs[k]["started_at"])
        for k in oldest[: len(_jobs) - MAX_JOBS]:
            _jobs.pop(k, None)

    return job_id


def _update_job(job_id: str, **kwargs: Any) -> None:
    """Update fields on an existing job."""
    if job_id in _jobs:
        _jobs[job_id].update(kwargs)


def _finish_job(job_id: str, status: str, result: dict[str, Any] | None = None, message: str = "") -> None:
    """Mark a job as finished and release the running lock."""
    job = _jobs.get(job_id)
    if job:
        job["status"] = status
        job["progress"] = 100.0 if status == "completed" else job["progress"]
        job["message"] = message
        job["completed_at"] = datetime.now(timezone.utc)
        job["result"] = result
        _running_types.discard(job["type"])


async def _run_etl_job(job_id: str) -> None:
    """Execute ETL pipeline as a background task."""
    try:
        _update_job(job_id, status="running", progress=0, message="Iniciando pipeline ETL...")

        def on_progress(pct: float, msg: str) -> None:
            _update_job(job_id, progress=pct, message=msg)

        summary = await run_etl(on_progress=on_progress)

        invalidate_graph_cache()
        _finish_job(job_id, "completed", result=summary, message="ETL concluido com sucesso")
    except Exception as exc:
        logger.exception("ETL job failed: %s", exc)
        _finish_job(job_id, "failed", message=str(exc))


async def _run_metrics_job(job_id: str) -> None:
    """Execute metrics computation as a background task."""
    try:
        _update_job(job_id, status="running", progress=0, message="Iniciando computacao de metricas...")

        def on_progress(pct: float, msg: str) -> None:
            _update_job(job_id, progress=pct, message=msg)

        async with Neo4jClient() as client:
            result = await compute_and_save_metrics(client, on_progress=on_progress)

        invalidate_graph_cache()
        _finish_job(job_id, "completed", result=result, message="Metricas computadas com sucesso")
    except Exception as exc:
        logger.exception("Metrics job failed: %s", exc)
        _finish_job(job_id, "failed", message=str(exc))


async def _run_train_job(job_id: str) -> None:
    """Execute ML training pipeline as a background task."""
    try:
        _update_job(job_id, status="running", progress=0, message="Iniciando treinamento...")

        def on_progress(pct: float, msg: str) -> None:
            _update_job(job_id, progress=pct, message=msg)

        async with Neo4jClient() as client:
            result = await run_training_pipeline(client, skip_pinecone=True, on_progress=on_progress)

        _finish_job(job_id, "completed", result=result, message="Treinamento concluido com sucesso")
    except Exception as exc:
        logger.exception("Training job failed: %s", exc)
        _finish_job(job_id, "failed", message=str(exc))


@router.post("/etl", response_model=JobStatus)
async def trigger_etl() -> JobStatus:
    """Launch ETL pipeline as a background task."""
    job_id = _create_job("etl")
    asyncio.create_task(_run_etl_job(job_id))
    return JobStatus(**_jobs[job_id])


@router.post("/compute-metrics", response_model=JobStatus)
async def trigger_compute_metrics() -> JobStatus:
    """Launch metrics computation as a background task."""
    job_id = _create_job("metrics")
    asyncio.create_task(_run_metrics_job(job_id))
    return JobStatus(**_jobs[job_id])


@router.post("/train", response_model=JobStatus)
async def trigger_train() -> JobStatus:
    """Launch ML training pipeline as a background task."""
    job_id = _create_job("train")
    asyncio.create_task(_run_train_job(job_id))
    return JobStatus(**_jobs[job_id])


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str) -> JobStatus:
    """Poll the status of a background job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(**job)


@router.get("/jobs", response_model=list[JobStatus])
async def list_jobs() -> list[JobStatus]:
    """List the most recent jobs (up to 20)."""
    sorted_jobs = sorted(_jobs.values(), key=lambda j: j["started_at"], reverse=True)
    return [JobStatus(**j) for j in sorted_jobs[:20]]
