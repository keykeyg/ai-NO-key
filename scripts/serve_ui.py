#!/usr/bin/env python3
"""Night Trail web UI.  python scripts/serve_ui.py  →  http://127.0.0.1:8787"""
from __future__ import annotations
import argparse, base64, json, logging, mimetypes, sys, threading, traceback, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
WEB = ROOT / "web"
logger = logging.getLogger("serve_ui")

def _load_cfg(path: str = "config.yaml") -> dict:
    try:
        from src.utils import load_config
        for p in (ROOT / path, ROOT / "config.example.yaml"):
            if p.exists():
                return load_config(str(p))
    except Exception as e:
        logger.warning("Config: %s", e)
    return {"cameras_root": "data/cameras", "output_dir": "data/output", "profiles_dir": "data/profiles",
            "timezone": "America/Chicago", "model": "yolo11n.pt", "device": "mps", "source_mode": "nvr",
            "reid": {"body_method": "osnet", "face_backend": "none", "device": "mps"}}

CFG = _load_cfg()

def _pipeline_ok() -> bool:
    try:
        import cv2  # noqa: F401
        from ultralytics import YOLO  # noqa: F401
        return True
    except Exception:
        return False

LIVE = _pipeline_ok()

def _cfg_path() -> Path:
    return ROOT / "config.yaml"

def _secrets_path() -> Path:
    return ROOT / ".unifi.env"

def _example_cfg() -> Path:
    return ROOT / "config.example.yaml"

def _osnet_status() -> dict:
    try:
        from torchreid.utils import FeatureExtractor  # noqa: F401
        return {"osnet": True, "body_method": "osnet", "label": "OSNet ready"}
    except Exception:
        return {"osnet": False, "body_method": "enhanced", "label": "Weak fallback (OSNet missing)"}

def setup_status() -> dict:
    cfg_p = _cfg_path()
    sec_p = _secrets_path()
    configured = cfg_p.exists()
    has_secrets = sec_p.exists()
    host = ""
    timezone = "America/Chicago"
    nvr_type = "unifi"
    source_mode = CFG.get("source_mode") or "nvr"
    if configured:
        try:
            import yaml
            data = yaml.safe_load(cfg_p.read_text()) or {}
            nvr = data.get("nvr") or {}
            host = nvr.get("host") or ""
            timezone = data.get("timezone") or timezone
            nvr_type = nvr.get("type") or nvr_type
            source_mode = data.get("source_mode") or source_mode
        except Exception:
            pass
    return {
        "configured": configured and bool(host or has_secrets),
        "has_config": configured,
        "has_secrets": has_secrets,
        "host": host,
        "timezone": timezone,
        "nvr_type": nvr_type,
        "username_set": has_secrets,
        "source_mode": source_mode,
    }

def save_setup(body: dict) -> dict:
    import yaml
    host = (body.get("host") or "").strip()
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    timezone = (body.get("timezone") or "America/Chicago").strip()
    nvr_type = (body.get("nvr_type") or "unifi").strip().lower()
    port = int(body.get("port") or (5000 if nvr_type == "frigate" else 443))
    source_mode = (body.get("source_mode") or "nvr").strip().lower()

    cfg_p = _cfg_path()
    if cfg_p.exists():
        data = yaml.safe_load(cfg_p.read_text()) or {}
    elif _example_cfg().exists():
        data = yaml.safe_load(_example_cfg().read_text()) or {}
    else:
        data = {}

    data["timezone"] = timezone
    data["source_mode"] = source_mode if source_mode in ("nvr", "local") else "nvr"
    nvr = data.get("nvr") or {}
    nvr["type"] = nvr_type
    nvr["host"] = host
    nvr["port"] = port
    nvr["username"] = ""
    nvr["password"] = ""
    data["nvr"] = nvr
    cfg_p.write_text(yaml.safe_dump(data, default_flow_style=False, sort_keys=False))

    if username or password or host:
        import os
        if nvr_type == "frigate":
            lines = [f'export FRIGATE_HOST="{host}"', f'export FRIGATE_PORT="{port}"']
            os.environ["FRIGATE_HOST"] = host
            os.environ["FRIGATE_PORT"] = str(port)
        else:
            lines = [
                f'export UNIFI_HOST="{host}"',
                f'export UNIFI_USERNAME="{username}"',
                f'export UNIFI_PASSWORD="{password}"',
            ]
            os.environ["UNIFI_HOST"] = host
            os.environ["UNIFI_USERNAME"] = username
            os.environ["UNIFI_PASSWORD"] = password
        _secrets_path().write_text("\n".join(lines) + "\n")

    global CFG
    CFG = _load_cfg("config.yaml")
    return setup_status()

def _json(h: BaseHTTPRequestHandler, code: int, payload: Any) -> None:
    body = json.dumps(payload).encode()
    h.send_response(code)
    h.send_header("Content-Type", "application/json")
    h.send_header("Content-Length", str(len(body)))
    h.send_header("Access-Control-Allow-Origin", "*")
    h.end_headers()
    h.wfile.write(body)

def _read_json(h: BaseHTTPRequestHandler) -> dict:
    n = int(h.headers.get("Content-Length") or 0)
    return json.loads(h.rfile.read(n).decode() or "{}") if n else {}

def _reid_dev(preferred=None) -> str:
    try:
        from src.device import reid_device
        return reid_device(preferred)
    except Exception:
        try:
            from src.device import resolve_device
            return resolve_device(preferred)
        except Exception:
            return preferred or "cpu"

def list_cameras() -> list:
    root = Path(CFG.get("cameras_root") or "data/cameras")
    if not root.is_absolute():
        root = ROOT / root
    out = []
    if not root.exists():
        return out
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        vids = sorted(p for p in d.iterdir() if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".avi"})
        sample = vids[0].name if vids else None
        out.append({"name": d.name, "videos": len(vids), "sample": sample,
                    "path": str(vids[0].relative_to(ROOT)).replace("\\", "/") if vids else f"data/cameras/{d.name}"})
    return out

def list_profiles() -> list:
    try:
        from src.profiles import ProfileStore
        from src.reid import MultiModalEmbedder
        r = CFG.get("reid") or {}
        emb = MultiModalEmbedder(body_method=r.get("body_method", "osnet"), face_backend=r.get("face_backend", "none"),
                                 face_weight=r.get("face_weight", 0.15), device=_reid_dev(r.get("device") or CFG.get("device")))
        store = ProfileStore(CFG.get("profiles_dir", "data/profiles"), emb)
        out = []
        for n in store.list_profiles():
            p = store.load(n)
            crops = len(getattr(p, "body_embeddings", []) or []) if p else 0
            out.append({"name": n, "role": getattr(p, "role", "") if p else "", "crops": crops})
        return out
    except Exception:
        root = Path(CFG.get("profiles_dir") or "data/profiles")
        if not root.is_absolute():
            root = ROOT / root
        return [{"name": p.stem, "role": "", "crops": 0} for p in sorted(root.glob("*.json"))] if root.exists() else []

def list_trails() -> list:
    root = Path(CFG.get("output_dir") or "data/output") / "trails"
    if not root.is_absolute():
        root = ROOT / root
    if not root.exists():
        return []
    out = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        n = strong = possible = None
        report = d / "person_trail.json"
        if report.exists():
            try:
                data = json.loads(report.read_text())
                n = data.get("num_appearances")
                strong = data.get("strong")
                possible = data.get("possible")
            except Exception:
                pass
        out.append({"name": d.name, "num_appearances": n, "strong": strong, "possible": possible})
    return out

def get_trail(name: str) -> Optional[dict]:
    root = Path(CFG.get("output_dir") or "data/output") / "trails" / name
    if not root.is_absolute():
        root = ROOT / root
    report = root / "person_trail.json"
    return json.loads(report.read_text()) if report.exists() else None

def api_status() -> dict:
    device = "cpu"
    try:
        from src.device import resolve_device
        device = resolve_device(CFG.get("device") or (CFG.get("reid") or {}).get("device"))
    except Exception:
        pass
    return {
        "product": "Night Trail",
        "mode": "live" if LIVE else "demo",
        "device": device,
        "cameras": list_cameras(),
        "profiles": list_profiles(),
        "root": str(ROOT),
        "source_mode": CFG.get("source_mode") or "nvr",
        "reid": _osnet_status(),
    }

def _b64_jpg(img) -> str:
    import cv2
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    return base64.b64encode(buf.tobytes()).decode("ascii") if ok else ""

def api_tag(body: dict) -> dict:
    if not LIVE:
        raise RuntimeError("Pipeline deps not installed — UI uses demo mode")
    from src.tag import save_tag_session
    video, at = body.get("video") or "", body.get("at") or "5"
    vpath = Path(video)
    if not vpath.is_absolute():
        vpath = ROOT / vpath
    if not vpath.exists():
        raise FileNotFoundError(f"Video not found: {video}")
    out = ROOT / (CFG.get("output_dir") or "data/output") / "tags" / "ui"
    session = save_tag_session(vpath, at, out, model_name=CFG.get("model", "yolo11n.pt"))
    overview_b64 = base64.b64encode(Path(session["overview"]).read_bytes()).decode("ascii") if Path(session["overview"]).exists() else ""
    people = [{"index": p["index"], "conf": p["conf"], "box": p["box"],
               "crop_b64": _b64_jpg(p["crop"]) if p.get("crop") is not None else ""} for p in session.get("people") or []]
    return {"video": str(vpath), "at_s": session["at_s"], "overview_b64": overview_b64, "num_people": len(people), "people": people}

def api_enroll(body: dict) -> dict:
    if not LIVE:
        raise RuntimeError("Pipeline deps not installed")
    from src.profiles import ProfileStore
    from src.reid import MultiModalEmbedder
    from src.tag import save_tag_session
    video, at = body.get("video") or "", body.get("at") or "5"
    picks = body.get("picks") or body.get("pick")
    if picks is None:
        picks = [0]
    if isinstance(picks, int):
        picks = [picks]
    picks = [int(x) for x in picks]
    name, role = (body.get("name") or "").strip(), (body.get("role") or "").strip()
    if not name:
        raise ValueError("name required")
    vpath = Path(video)
    if not vpath.is_absolute():
        vpath = ROOT / vpath
    out = ROOT / (CFG.get("output_dir") or "data/output") / "tags" / "ui"
    session = save_tag_session(vpath, at, out, model_name=CFG.get("model", "yolo11n.pt"))
    people_by_idx = {p["index"]: p for p in session["people"]}
    crops, paths = [], []
    for pick in picks:
        chosen = people_by_idx.get(pick)
        if not chosen:
            continue
        crops.append(chosen["crop"])
        paths.append(next((c["path"] for c in session["crops"] if c["index"] == pick), f"crop_{pick}"))
    if not crops:
        raise KeyError(f"No people for picks {picks}")
    r = CFG.get("reid") or {}
    emb = MultiModalEmbedder(body_method=r.get("body_method", "osnet"), face_backend=r.get("face_backend", "none"),
                             face_weight=r.get("face_weight", 0.15), device=_reid_dev(r.get("device") or CFG.get("device")))
    store = ProfileStore(CFG.get("profiles_dir", "data/profiles"), emb)
    # Merge with existing profile crops if present
    existing = store.load(name)
    if existing and existing.body_embeddings:
        # re-enroll: add new crops on top by reloading images isn't available; append via enroll_from_crops replaces
        # For v1: re-enroll with new crops only OR merge by calling enroll with all new crops
        pass
    store.enroll_from_crops(
        name=name, crops=crops, saved_paths=paths, role=role or (existing.role if existing else ""),
        notes=f"ui tag {vpath.name} @ {session['at_s']:.1f}s picks={picks}",
    )
    return {"ok": True, "name": name, "crops": len(crops), "profiles": list_profiles()}

def api_test_nvr() -> dict:
    from src.nvr import test_connection, NvrError
    try:
        return test_connection(CFG)
    except NvrError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _run_search_job(job_id: str, body: dict) -> None:
    from src import progress as prog
    from src.pipeline import OvernightPipeline
    try:
        profile = (body.get("profile") or "").strip()
        if not profile:
            raise ValueError("profile required")
        start, end = body.get("start"), body.get("end")
        source = (body.get("source") or CFG.get("source_mode") or "nvr").lower()

        def on_progress(phase, cur, total, detail=""):
            labels = {"pull": "Pulling from NVR", "detect": "Detecting people", "match": "Matching profile"}
            prog.update(
                job_id,
                phase=phase,
                message=labels.get(phase, phase),
                current=cur,
                total=total,
                detail=str(detail or ""),
            )

        pipeline = OvernightPipeline(CFG)
        report = pipeline.search_person(
            profile_name=profile,
            start=start,
            end=end,
            start_s=float(body["start_s"]) if body.get("start_s") is not None else None,
            end_s=float(body["end_s"]) if body.get("end_s") is not None else None,
            source=source,
            force_detect=bool(body.get("force")),
            progress=on_progress,
        )
        prog.complete(job_id, report)
    except Exception as e:
        logger.error("search job failed: %s\n%s", e, traceback.format_exc())
        prog.fail(job_id, str(e))

def api_search_start(body: dict) -> dict:
    if not LIVE:
        raise RuntimeError("Pipeline deps not installed")
    from src import progress as prog
    job_id = uuid.uuid4().hex[:12]
    prog.start_job(job_id, label="search")
    t = threading.Thread(target=_run_search_job, args=(job_id, body), daemon=True)
    t.start()
    return {"job_id": job_id}

def api_search_sync(body: dict) -> dict:
    """Legacy sync search (CLI-style). Prefer /api/search/start + poll."""
    if not LIVE:
        raise RuntimeError("Pipeline deps not installed")
    from src.pipeline import OvernightPipeline
    profile = (body.get("profile") or "").strip()
    if not profile:
        raise ValueError("profile required")
    pipeline = OvernightPipeline(CFG)
    return pipeline.search_person(
        profile_name=profile,
        start=body.get("start"),
        end=body.get("end"),
        start_s=float(body["start_s"]) if body.get("start_s") is not None else None,
        end_s=float(body["end_s"]) if body.get("end_s") is not None else None,
        source=(body.get("source") or CFG.get("source_mode") or "nvr").lower(),
        force_detect=bool(body.get("force")),
    )

class Handler(BaseHTTPRequestHandler):
    server_version = "NightTrail/1.2"
    def log_message(self, fmt, *args):
        logger.info("%s - %s", self.address_string(), fmt % args)
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            return _json(self, 200, {**api_status(), "setup": setup_status()})
        if path == "/api/setup":
            return _json(self, 200, setup_status())
        if path == "/api/cameras":
            return _json(self, 200, {"cameras": list_cameras()})
        if path == "/api/profiles":
            return _json(self, 200, {"profiles": list_profiles()})
        if path == "/api/trails":
            return _json(self, 200, list_trails())
        if path.startswith("/api/trails/"):
            trail = get_trail(unquote(path.split("/api/trails/", 1)[1]))
            return _json(self, 200, trail) if trail else _json(self, 404, {"error": "not found"})
        if path.startswith("/api/jobs/"):
            from src import progress as prog
            jid = path.split("/api/jobs/", 1)[1]
            if jid.endswith("/result"):
                jid = jid[: -len("/result")]
                res = prog.get_result(jid)
                return _json(self, 200, res) if res is not None else _json(self, 404, {"error": "no result"})
            job = prog.get(jid)
            return _json(self, 200, job) if job else _json(self, 404, {"error": "unknown job"})
        # Serve trail clips: /media/trails/<name>/clips/<file>
        if path.startswith("/media/"):
            rel = unquote(path[len("/media/"):])
            if ".." in rel:
                return self.send_error(400)
            fpath = ROOT / (CFG.get("output_dir") or "data/output") / rel
            if not fpath.is_file():
                return self.send_error(404)
            data = fpath.read_bytes()
            ctype = mimetypes.guess_type(str(fpath))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        rel = path.lstrip("/") or "index.html"
        if ".." in rel:
            return self.send_error(400)
        fpath = WEB / rel
        if not fpath.is_file():
            fpath = WEB / "index.html"
        if not fpath.exists():
            return self.send_error(404)
        data = fpath.read_bytes()
        ctype = mimetypes.guess_type(str(fpath))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)
    def do_POST(self):
        path = urlparse(self.path).path
        try:
            body = _read_json(self)
            if path == "/api/setup":
                return _json(self, 200, save_setup(body))
            if path == "/api/test_nvr":
                return _json(self, 200, api_test_nvr())
            if path == "/api/tag":
                return _json(self, 200, api_tag(body))
            if path == "/api/enroll":
                return _json(self, 200, api_enroll(body))
            if path == "/api/search/start":
                return _json(self, 200, api_search_start(body))
            if path == "/api/search":
                return _json(self, 200, api_search_sync(body))
            return _json(self, 404, {"error": "unknown endpoint"})
        except Exception as e:
            logger.error("%s\n%s", e, traceback.format_exc())
            return _json(self, 500, {"error": str(e)})

def main() -> None:
    global CFG, LIVE
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--config", default="config.yaml")
    args = p.parse_args()
    CFG = _load_cfg(args.config)
    LIVE = _pipeline_ok()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not WEB.exists():
        raise SystemExit(f"Missing {WEB}")
    reid = _osnet_status()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Night Trail  [{'LIVE' if LIVE else 'DEMO'}]  source={CFG.get('source_mode', 'nvr')}  {reid['label']}")
    print(f"  http://{args.host}:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")

if __name__ == "__main__":
    main()
