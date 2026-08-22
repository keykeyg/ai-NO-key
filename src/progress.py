"""In-memory job progress for long NVR pull / detect / match runs."""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

_lock = threading.Lock()
_jobs: Dict[str, Dict[str, Any]] = {}


def start_job(job_id: str, label: str = "search") -> str:
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "label": label,
            "status": "running",
            "phase": "starting",
            "message": "Starting…",
            "current": 0,
            "total": 0,
            "detail": "",
            "error": None,
            "result": None,
            "cancel": False,
            "started": time.time(),
            "updated": time.time(),
        }
    return job_id


def update(
    job_id: str,
    *,
    phase: Optional[str] = None,
    message: Optional[str] = None,
    current: Optional[int] = None,
    total: Optional[int] = None,
    detail: Optional[str] = None,
) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        if phase is not None:
            job["phase"] = phase
        if message is not None:
            job["message"] = message
        if current is not None:
            job["current"] = current
        if total is not None:
            job["total"] = total
        if detail is not None:
            job["detail"] = detail
        job["updated"] = time.time()


def request_cancel(job_id: str) -> bool:
    with _lock:
        job = _jobs.get(job_id)
        if not job or job.get("status") != "running":
            return False
        job["cancel"] = True
        job["message"] = "Cancel requested…"
        job["updated"] = time.time()
        return True


def is_cancelled(job_id: str) -> bool:
    with _lock:
        job = _jobs.get(job_id)
        return bool(job and job.get("cancel"))


def complete(job_id: str, result: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job["status"] = "done"
        job["phase"] = "done"
        job["message"] = "Done"
        job["result"] = result
        job["updated"] = time.time()


def fail(job_id: str, error: str) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job["status"] = "error" if error != "cancelled" else "cancelled"
        job["phase"] = job["status"]
        job["message"] = error
        job["error"] = error
        job["updated"] = time.time()


def get(job_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return None
        out = {k: v for k, v in job.items() if k != "result"}
        out["has_result"] = job.get("result") is not None
        return out


def get_result(job_id: str) -> Any:
    with _lock:
        job = _jobs.get(job_id)
        return None if not job else job.get("result")
