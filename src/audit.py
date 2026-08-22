"""Append-only search audit log (who/what/when)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .utils import ensure_dir


def log_search(
    output_dir: str | Path,
    *,
    profile: str,
    start: Optional[str],
    end: Optional[str],
    source: str,
    num_appearances: int,
    strong: int = 0,
    possible: int = 0,
    extra: Optional[Dict[str, Any]] = None,
) -> Path:
    root = ensure_dir(Path(output_dir) / "audit")
    path = root / "searches.jsonl"
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "start": start,
        "end": end,
        "source": source,
        "num_appearances": num_appearances,
        "strong": strong,
        "possible": possible,
    }
    if extra:
        row.update(extra)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return path
