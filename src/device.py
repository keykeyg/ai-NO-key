from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def resolve_device(preferred: str | None = None) -> str:
    """
    Shared-base device picker: CUDA → MPS → CPU.

    Ultralytics device string: "0" / "1" / "mps" / "cpu".
    """
    pref = (preferred or "").strip().lower()

    try:
        import torch
    except Exception:
        logger.warning("torch not available — using cpu")
        return "cpu"

    cuda_ok = torch.cuda.is_available()
    mps_ok = bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())

    if pref in ("cpu",):
        return "cpu"

    if pref in ("mps", "metal"):
        if mps_ok:
            return "mps"
        if cuda_ok:
            return "0"
        return "cpu"

    if pref in ("", "cuda", "0", "cuda:0") or pref.isdigit() or pref.startswith("cuda:"):
        if cuda_ok:
            if pref.startswith("cuda:") and pref.replace("cuda:", "").isdigit():
                return pref.replace("cuda:", "")
            if pref.isdigit():
                return pref
            return "0"
        if mps_ok:
            logger.info("CUDA not available — using MPS")
            return "mps"
        logger.warning("No GPU — using cpu")
        return "cpu"

    if cuda_ok:
        return "0"
    if mps_ok:
        return "mps"
    return "cpu"


def reid_device(preferred: str | None = None) -> str:
    """OSNet / torchreid wants 'cuda' / 'mps' / 'cpu', not Ultralytics index '0'."""
    d = resolve_device(preferred)
    if d in ("0", "cuda", "cuda:0") or d.isdigit():
        return "cuda"
    return d
