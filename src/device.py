from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def resolve_device(preferred: str | None = None) -> str:
    """
    Resolve compute device for Apple Silicon.

    Preferred order on Mac branch:
      mps → cpu
    Explicit values like "mps", "cpu" are respected.
    "cuda" / "0" are mapped to mps when available, else cpu.
    """
    pref = (preferred or "").strip().lower()

    try:
        import torch
    except Exception:
        logger.warning("torch not available — using cpu")
        return "cpu"

    mps_ok = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())

    if pref in ("mps", "metal"):
        if mps_ok:
            return "mps"
        logger.warning("MPS requested but not available — using cpu")
        return "cpu"

    if pref in ("cpu",):
        return "cpu"

    # cuda / 0 / empty → prefer mps on this branch
    if mps_ok:
        if pref in ("cuda", "0", "cuda:0", ""):
            logger.info("Mac branch: using MPS instead of CUDA device '%s'", pref or "auto")
        return "mps"

    logger.warning("MPS not available — using cpu")
    return "cpu"
