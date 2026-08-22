"""Multi-site config: Say Less vs Uptown without rewriting the whole yaml."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional


def list_sites(config: dict) -> List[dict]:
    sites = config.get("sites") or {}
    if not sites:
        # Single-site fallback from top-level nvr
        nvr = config.get("nvr") or {}
        return [{
            "id": "default",
            "name": nvr.get("label") or "Default",
            "host": nvr.get("host") or "",
            "active": True,
        }]
    active = config.get("active_site") or next(iter(sites.keys()), "default")
    out = []
    for sid, s in sites.items():
        out.append({
            "id": sid,
            "name": s.get("name") or sid,
            "host": (s.get("nvr") or {}).get("host") or "",
            "active": sid == active,
        })
    return out


def apply_site(config: dict, site_id: Optional[str] = None) -> dict:
    """Return a config copy with nvr/topology/cameras_root from the selected site."""
    cfg = deepcopy(config)
    sites = cfg.get("sites") or {}
    if not sites:
        return cfg
    sid = site_id or cfg.get("active_site") or next(iter(sites.keys()))
    site = sites.get(sid)
    if not site:
        return cfg
    cfg["active_site"] = sid
    if site.get("nvr"):
        base = cfg.get("nvr") or {}
        merged = {**base, **site["nvr"]}
        # cameras map fully replaced if provided
        if "cameras" in site["nvr"]:
            merged["cameras"] = site["nvr"]["cameras"]
        cfg["nvr"] = merged
    if site.get("topology"):
        cfg["topology"] = site["topology"]
    if site.get("cameras_root"):
        cfg["cameras_root"] = site["cameras_root"]
    if site.get("timezone"):
        cfg["timezone"] = site["timezone"]
    return cfg
