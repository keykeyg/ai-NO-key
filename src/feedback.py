"""Match verification feedback (thumbs up/down) for threshold tuning."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import ensure_dir


def _path(output_dir: str | Path) -> Path:
    return ensure_dir(Path(output_dir) / "audit") / "match_feedback.jsonl"


def log_feedback(
    output_dir: str | Path,
    *,
    profile: str,
    camera: str,
    local_id: int,
    score: float,
    confidence: str,
    verdict: str,
    trail: Optional[str] = None,
) -> Path:
    """verdict: correct | wrong | unsure"""
    path = _path(output_dir)
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "trail": trail or profile,
        "camera": camera,
        "local_id": local_id,
        "score": score,
        "confidence": confidence,
        "verdict": verdict,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return path


def summary(output_dir: str | Path) -> Dict[str, Any]:
    path = _path(output_dir)
    if not path.exists():
        return {"total": 0, "correct": 0, "wrong": 0, "unsure": 0}
    counts = {"correct": 0, "wrong": 0, "unsure": 0}
    total = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        v = row.get("verdict") or "unsure"
        counts[v] = counts.get(v, 0) + 1
        total += 1
    return {"total": total, **counts}
