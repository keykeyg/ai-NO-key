from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def resolve_device(preferred: str | None = None) -> str:
    """
    Resolve compute device for Windows / NVIDIA.

    Preferred order on Windows branch:
      cuda:0 → cpu
    Accepts "0", "cuda", "cuda:0".
    """
    pref = (preferred or "").strip().lower()

    try:
        import torch
    except Exception:
        logger.warning("torch not available — using cpu")
        return "cpu"

    cuda_ok = torch.cuda.is_available()

    if pref in ("cpu",):
        return "cpu"

    if pref in ("mps", "metal"):
        logger.warning("MPS requested on Windows branch — using cuda if available else cpu")
        return "0" if cuda_ok else "cpu"

    if cuda_ok:
        if pref in ("", "cuda", "0", "cuda:0"):
            return "0"
        # allow cuda:1 etc.
        if pref.startswith("cuda:"):
            return pref.replace("cuda:", "")
        return pref if pref.isdigit() else "0"

    logger.warning("CUDA not available — using cpu")
    return "cpu"
