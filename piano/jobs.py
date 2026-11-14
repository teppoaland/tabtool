"""A tiny in-memory job registry for the long steps (download, analysis, model).

One worker thread per job is enough for a local, single-user tool; the UI polls
``/api/piano/jobs/{id}`` and shows the stage text.
"""

from __future__ import annotations

import threading
import time
import traceback
import uuid

from piano import config

JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()


def _now() -> float:
    return time.time()


def create(kind: str) -> dict:
    job = {
        "id": uuid.uuid4().hex[:12],
        "kind": kind,
        "status": config.STAGE_QUEUED,
        "stage": "Jonossa…",
        "progress": 0.0,
        "error": None,
        "result": None,
        "created": _now(),
        "updated": _now(),
    }
    with _LOCK:
        JOBS[job["id"]] = job
    return job


def update(job_id: str, **fields) -> dict:
    with _LOCK:
        job = JOBS[job_id]
        job.update(fields)
        job["updated"] = _now()
        return dict(job)


def get(job_id: str) -> dict | None:
    with _LOCK:
        job = JOBS.get(job_id)
        return dict(job) if job else None


def submit(kind: str, work) -> dict:
    """Start ``work(progress)`` in a thread and return the job record."""
    job = create(kind)
    job_id = job["id"]

    def progress(stage: str, value: float = 0.0) -> None:
        update(
            job_id,
            status=config.STAGE_RUNNING,
            stage=str(stage),
            progress=max(0.0, min(1.0, float(value))),
        )

    def runner() -> None:
        update(job_id, status=config.STAGE_RUNNING, progress=0.02)
        try:
            result = work(progress)
            update(
                job_id,
                status=config.STAGE_READY,
                stage="Valmis",
                progress=1.0,
                result=result,
            )
        except Exception as error:  # noqa: BLE001 - the UI needs the message
            update(
                job_id,
                status=config.STAGE_FAILED,
                stage="Virhe",
                error=str(error) or error.__class__.__name__,
                traceback=traceback.format_exc()[-4000:],
            )

    threading.Thread(target=runner, name=f"piano-{kind}-{job_id}", daemon=True).start()
    return job
