from __future__ import annotations

import json
import logging
import os
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .timerange import parse_when, tzinfo_from_name, window as parse_window
from .utils import ensure_dir

logger = logging.getLogger(__name__)


def _env(name: str, fallback: str = "") -> str:
    return os.environ.get(name, fallback) or fallback


class NvrError(RuntimeError):
    pass


def export_range(
    config: dict,
    start: str,
    end: str,
    cameras: Optional[List[str]] = None,
    out_root: Optional[str] = None,
) -> Dict[str, List[Path]]:
    """Download NVR footage for a time window into data/cameras/<folder>/.

    If cameras is None, only pulls cameras listed under config nvr.cameras
    (your mapped set) — never the entire Protect site.
    """
    nvr = config.get("nvr") or {}
    kind = (nvr.get("type") or "unifi").lower()
    tz_name = config.get("timezone") or nvr.get("timezone") or "America/Chicago"
    t0, t1 = parse_window(start, end, tz_name)
    if t0 is None or t1 is None:
        raise NvrError("Need both --start and --end to pull NVR footage")

    dest = Path(out_root or config.get("cameras_root") or "data/cameras")
    ensure_dir(dest)

    # Default: only the mapped Protect names (not every camera on the NVR)
    if cameras is None:
        mapped = nvr.get("cameras") or {}
        cameras = list(mapped.keys()) if mapped else None

    if kind in ("unifi", "protect", "unifi-protect"):
        return _pull_unifi(nvr, t0, t1, cameras, dest, tz_name)
    if kind == "frigate":
        return _pull_frigate(nvr, t0, t1, cameras, dest)
    raise NvrError(f"Unknown nvr.type: {kind}")


def _name_map(nvr: dict) -> Dict[str, str]:
    """Protect/Frigate camera name → local folder name."""
    raw = nvr.get("cameras") or {}
    out = {}
    for k, v in raw.items():
        out[str(k).strip().lower()] = str(v).strip()
    return out


def _folder_for(cam_name: str, mapping: Dict[str, str]) -> str:
    key = cam_name.strip().lower()
    if key in mapping:
        return mapping[key]
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in cam_name.strip())
    return safe or "camera"


def _chunk_bounds(t0: datetime, t1: datetime, minutes: int = 15):
    step = timedelta(minutes=max(1, minutes))
    cur = t0
    while cur < t1:
        nxt = min(cur + step, t1)
        yield cur, nxt
        cur = nxt


# ---------------------------------------------------------------------------
# UniFi Protect (login cookie + video/export)
# ---------------------------------------------------------------------------

def _pull_unifi(nvr: dict, t0: datetime, t1: datetime, cameras, dest: Path, tz_name: str) -> Dict[str, List[Path]]:
    host = nvr.get("host") or _env("UNIFI_HOST") or _env("UFP_HOST")
    if not host:
        raise NvrError("Set nvr.host or UNIFI_HOST")
    port = int(nvr.get("port") or _env("UNIFI_PORT") or 443)
    user = nvr.get("username") or _env("UNIFI_USERNAME") or _env("UFP_USERNAME")
    password = nvr.get("password") or _env("UNIFI_PASSWORD") or _env("UFP_PASSWORD")
    verify = bool(nvr.get("verify_ssl", False))
    chunk_min = int(nvr.get("chunk_minutes") or 15)
    mapping = _name_map(nvr)

    # Prefer official-ish uiprotect if installed
    pulled = _try_uiprotect(host, port, user, password, nvr, t0, t1, cameras, dest, mapping, chunk_min, verify)
    if pulled is not None:
        return pulled

    if not user or not password:
        raise NvrError("UniFi needs username/password (config nvr.* or UNIFI_USERNAME / UNIFI_PASSWORD)")

    opener = _unifi_login(host, port, user, password, verify)
    cam_list = _unifi_cameras(opener, host, port)
    logger.info("UniFi Protect: %d cameras on site", len(cam_list))

    wanted = {c.lower() for c in cameras} if cameras else None
    written: Dict[str, List[Path]] = {}

    for cam in cam_list:
        name = cam.get("name") or cam.get("id")
        cid = cam.get("id")
        if not name or not cid:
            continue
        folder = _folder_for(name, mapping)
        if wanted and name.lower() not in wanted and folder.lower() not in wanted:
            continue
        cam_dir = ensure_dir(dest / folder)
        files: List[Path] = []
        for a, b in _chunk_bounds(t0, t1, chunk_min):
            out = cam_dir / f"{folder}_{a.strftime('%Y%m%d_%H%M%S')}_{b.strftime('%H%M%S')}.mp4"
            if out.exists() and out.stat().st_size > 1000:
                files.append(out)
                continue
            ok = _unifi_export(opener, host, port, cid, a, b, out)
            if ok:
                files.append(out)
        if files:
            written[folder] = files
            logger.info("Exported %s → %d clips", name, len(files))
    return written


def _ssl_ctx(verify: bool):
    if verify:
        return ssl.create_default_context()
    ctx = ssl._create_unverified_context()
    return ctx


def _unifi_login(host: str, port: int, user: str, password: str, verify: bool):
    url = f"https://{host}:{port}/api/auth/login"
    body = json.dumps({"username": user, "password": password, "rememberMe": True}).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    ctx = _ssl_ctx(verify)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            cookie = resp.headers.get("Set-Cookie", "")
    except Exception as e:
        raise NvrError(f"UniFi login failed: {e}") from e

    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ctx),
        urllib.request.HTTPCookieProcessor(),
    )
    # Re-login through opener so cookies persist
    req2 = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        opener.open(req2, timeout=30).read()
    except Exception as e:
        raise NvrError(f"UniFi login (cookie jar) failed: {e}") from e
    logger.info("Logged into UniFi OS at %s", host)
    _ = cookie
    return opener


def _unifi_cameras(opener, host: str, port: int) -> list:
    url = f"https://{host}:{port}/proxy/protect/api/cameras"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with opener.open(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        raise NvrError(f"Could not list Protect cameras: {e}") from e
    if isinstance(data, dict) and "data" in data:
        data = data["data"]
    return data if isinstance(data, list) else []


def _unifi_export(opener, host, port, camera_id, t0: datetime, t1: datetime, out_path: Path) -> bool:
    start_ms = int(t0.timestamp() * 1000)
    end_ms = int(t1.timestamp() * 1000)
    qs = urllib.parse.urlencode({"camera": camera_id, "start": start_ms, "end": end_ms})
    url = f"https://{host}:{port}/proxy/protect/api/video/export?{qs}"
    req = urllib.request.Request(url, headers={"Accept": "video/mp4,application/octet-stream"})
    try:
        with opener.open(req, timeout=180) as resp:
            data = resp.read()
    except Exception as e:
        logger.warning("Export failed %s %s–%s: %s", camera_id, t0.time(), t1.time(), e)
        return False
    if not data or len(data) < 500:
        logger.warning("Empty export for %s %s–%s", camera_id, t0, t1)
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    return True


def _try_uiprotect(host, port, user, password, nvr, t0, t1, cameras, dest, mapping, chunk_min, verify):
    try:
        import asyncio
        from uiprotect import ProtectApiClient  # type: ignore
    except Exception:
        return None

    api_key = nvr.get("api_key") or _env("UNIFI_API_KEY") or _env("UFP_API_KEY") or None

    async def _run():
        client = ProtectApiClient(
            host, port, user or "", password or "",
            api_key=api_key, verify_ssl=verify,
        )
        await client.update()
        wanted = {c.lower() for c in cameras} if cameras else None
        written: Dict[str, List[Path]] = {}
        for cam in client.bootstrap.cameras.values():
            name = getattr(cam, "name", None) or str(cam.id)
            folder = _folder_for(name, mapping)
            if wanted and name.lower() not in wanted and folder.lower() not in wanted:
                continue
            cam_dir = ensure_dir(dest / folder)
            files = []
            for a, b in _chunk_bounds(t0, t1, chunk_min):
                out = cam_dir / f"{folder}_{a.strftime('%Y%m%d_%H%M%S')}_{b.strftime('%H%M%S')}.mp4"
                if out.exists() and out.stat().st_size > 1000:
                    files.append(out)
                    continue
                try:
                    if hasattr(cam, "get_video"):
                        data = await cam.get_video(a, b)
                        if data:
                            Path(out).write_bytes(data if isinstance(data, bytes) else data)
                            files.append(out)
                except Exception as e:
                    logger.warning("uiprotect get_video failed for %s: %s", name, e)
            if files:
                written[folder] = files
        await client.close_session()
        return written

    try:
        return asyncio.run(_run())
    except Exception as e:
        logger.warning("uiprotect path failed (%s) — trying HTTP export", e)
        return None


# ---------------------------------------------------------------------------
# Frigate
# ---------------------------------------------------------------------------

def _pull_frigate(nvr: dict, t0: datetime, t1: datetime, cameras, dest: Path) -> Dict[str, List[Path]]:
    host = nvr.get("host") or _env("FRIGATE_HOST") or "127.0.0.1"
    port = int(nvr.get("port") or _env("FRIGATE_PORT") or 5000)
    scheme = nvr.get("scheme") or "http"
    mapping = _name_map(nvr)
    cam_names = cameras or list((nvr.get("cameras") or {}).keys())
    if not cam_names:
        url = f"{scheme}://{host}:{port}/api/config"
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                cfg = json.loads(resp.read().decode())
            cam_names = list((cfg.get("cameras") or {}).keys())
        except Exception as e:
            raise NvrError(f"Could not list Frigate cameras: {e}") from e

    written: Dict[str, List[Path]] = {}
    start_ts = int(t0.timestamp())
    end_ts = int(t1.timestamp())
    for name in cam_names:
        folder = _folder_for(name, mapping)
        cam_dir = ensure_dir(dest / folder)
        out = cam_dir / f"{folder}_{t0.strftime('%Y%m%d_%H%M%S')}_{t1.strftime('%H%M%S')}.mp4"
        url = f"{scheme}://{host}:{port}/api/{urllib.parse.quote(name)}/start/{start_ts}/end/{end_ts}/clip.mp4"
        try:
            with urllib.request.urlopen(url, timeout=180) as resp:
                data = resp.read()
        except Exception as e:
            logger.warning("Frigate clip failed for %s: %s", name, e)
            continue
        if data and len(data) > 500:
            out.write_bytes(data)
            written.setdefault(folder, []).append(out)
            logger.info("Frigate %s → %s", name, out.name)
    return written
