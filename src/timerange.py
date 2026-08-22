from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


PROTECT_RANGE = re.compile(
    r"(?P<start>[A-Z][a-z]{2}\s+\d{1,2},\s+\d{1,2}:\d{2}(?::\d{2})?\s+[AP]M)"
    r"\s*-\s*"
    r"(?P<end>[A-Z][a-z]{2}\s+\d{1,2},\s+\d{1,2}:\d{2}(?::\d{2})?\s+[AP]M)",
    re.IGNORECASE,
)


def tzinfo_from_name(name: str | None):
    if not name or ZoneInfo is None:
        return datetime.now().astimezone().tzinfo
    try:
        return ZoneInfo(name)
    except Exception:
        return datetime.now().astimezone().tzinfo


def parse_when(value: str, tz_name: str | None = None, default_date: datetime | None = None) -> datetime:
    """Parse wall-clock or ISO time. Bare HH:MM uses default_date (or today)."""
    raw = (value or "").strip()
    if not raw:
        raise ValueError("empty time")

    tz = tzinfo_from_name(tz_name)
    now = datetime.now(tz)
    base = default_date.astimezone(tz) if default_date else now

    if re.fullmatch(r"\d{10,13}", raw):
        n = int(raw)
        if n > 10_000_000_000:
            n = n / 1000.0
        return datetime.fromtimestamp(n, tz=tz)

    iso = raw.replace("T", " ")
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ):
        try:
            dt = datetime.strptime(iso, fmt)
            return dt.replace(tzinfo=tz)
        except ValueError:
            pass

    ampm = re.fullmatch(
        r"(?:(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})\s+)?(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([ap]m)?",
        raw,
        re.IGNORECASE,
    )
    if ampm:
        month, day, year, hh, mm, ss, mer = ampm.groups()
        hour = int(hh)
        minute = int(mm)
        second = int(ss or 0)
        if mer:
            mer = mer.lower()
            if mer == "pm" and hour < 12:
                hour += 12
            if mer == "am" and hour == 12:
                hour = 0
        if month:
            y = int(year)
            if y < 100:
                y += 2000
            return datetime(y, int(month), int(day), hour, minute, second, tzinfo=tz)
        return datetime(base.year, base.month, base.day, hour, minute, second, tzinfo=tz)

    clock = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", raw)
    if clock:
        return datetime(
            base.year, base.month, base.day,
            int(clock.group(1)), int(clock.group(2)), int(clock.group(3) or 0),
            tzinfo=tz,
        )

    raise ValueError(f"Could not parse time: {value!r}")


def parse_seconds(value: str | float | int) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value).strip()
    if re.fullmatch(r"\d+(\.\d+)?", raw):
        return float(raw)
    parts = raw.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise ValueError(f"Could not parse seconds: {value!r}")


def _has_explicit_date(value: str | None) -> bool:
    if not value:
        return False
    raw = value.strip()
    if re.search(r"\d{4}", raw):
        return True
    if re.search(r"\d{1,2}[/-]\d{1,2}", raw):
        return True
    return False


def window(
    start: str | None,
    end: str | None,
    tz_name: str | None = None,
    now: Optional[datetime] = None,
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Parse a search/export window.

    Bare clocks like 21:00–03:00 wrap overnight. If that window is still in
    the future (e.g. it's 1am and you typed 21:00–03:00), shift back one day
    so you search last night, not tonight. Explicit dates are never shifted.
    """
    if not start and not end:
        return None, None
    t0 = parse_when(start, tz_name) if start else None
    t1 = parse_when(end, tz_name, default_date=t0) if end else None
    if t0 and t1 and t1 <= t0:
        t1 = t1 + timedelta(days=1)

    dated = _has_explicit_date(start) or _has_explicit_date(end)
    if not dated and t0 is not None:
        tz = t0.tzinfo
        ref = now.astimezone(tz) if now else datetime.now(tz)
        # Bare clock resolved to a future night → user means the night just ended.
        if t0 > ref:
            t0 = t0 - timedelta(days=1)
            if t1 is not None:
                t1 = t1 - timedelta(days=1)
    return t0, t1



def parse_protect_filename(path: str | Path, tz_name: str | None = None) -> Optional[Tuple[datetime, datetime]]:
    """Parse UniFi Protect export names like '...-Aug 21, 11:33 PM - Aug 21, 11:35 PM.mp4'."""
    name = Path(path).stem
    m = PROTECT_RANGE.search(name)
    if not m:
        return None
    tz = tzinfo_from_name(tz_name)
    year = datetime.now(tz).year

    def _one(s: str) -> Optional[datetime]:
        s = s.strip()
        for fmt in ("%b %d, %I:%M:%S %p", "%b %d, %I:%M %p"):
            try:
                dt = datetime.strptime(s, fmt).replace(year=year, tzinfo=tz)
                return dt
            except ValueError:
                continue
        return None

    a, b = _one(m.group("start")), _one(m.group("end"))
    if a and b:
        if b <= a:
            b = b + timedelta(days=1)
        return a, b
    return None


def track_wall_span(track, tz_name: str | None = None) -> Optional[Tuple[datetime, datetime]]:
    rng = parse_protect_filename(getattr(track, "video_path", "") or "", tz_name)
    if not rng:
        return None
    vid_start, _ = rng
    t0, t1 = track.start_end()
    return vid_start + timedelta(seconds=t0), vid_start + timedelta(seconds=t1)


def overlaps(a0: datetime, a1: datetime, b0: datetime, b1: datetime) -> bool:
    return a0 < b1 and a1 > b0


def filter_tracks_window(
    all_tracks: Dict[str, dict],
    start: Optional[datetime],
    end: Optional[datetime],
    tz_name: str | None = None,
    start_s: Optional[float] = None,
    end_s: Optional[float] = None,
) -> Dict[str, dict]:
    """Keep tracks that overlap the wall-clock window and/or relative seconds window."""
    if start is None and end is None and start_s is None and end_s is None:
        return all_tracks

    kept: Dict[str, dict] = {}
    dropped = 0
    for cam, tracks in all_tracks.items():
        cam_kept = {}
        for lid, tr in tracks.items():
            t0, t1 = tr.start_end()
            ok = True
            if start_s is not None and t1 < start_s:
                ok = False
            if end_s is not None and t0 > end_s:
                ok = False
            if ok and (start is not None or end is not None):
                span = track_wall_span(tr, tz_name)
                if span is None:
                    # No wall clock on this file — relative seconds already applied
                    pass
                else:
                    w0 = start or span[0]
                    w1 = end or span[1]
                    if not overlaps(span[0], span[1], w0, w1):
                        ok = False
            if ok:
                cam_kept[lid] = tr
            else:
                dropped += 1
        if cam_kept:
            kept[cam] = cam_kept
    logger.info("Time window kept tracks on %d cameras (dropped %d)", len(kept), dropped)
    return kept


def filter_embeddings(all_emb: dict, filtered_tracks: dict) -> dict:
    out = {}
    for cam, tracks in filtered_tracks.items():
        src = all_emb.get(cam, {})
        out[cam] = {lid: src[lid] for lid in tracks if lid in src}
    return out
