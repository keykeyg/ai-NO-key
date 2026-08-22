#!/usr/bin/env python3
"""Turn global_report.json into a readable text / markdown summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="data/output/global_report.json")
    parser.add_argument("--out", default="data/output/night_summary.md")
    args = parser.parse_args()

    with open(args.report, "r", encoding="utf-8") as f:
        data = json.load(f)

    lines = [
        f"# Night Summary",
        f"",
        f"- Cameras processed: **{data['num_cameras']}**",
        f"- Unique people tracked: **{data['num_global_people']}**",
        f"",
        f"## People",
        f"",
    ]

    for p in data.get("people", []):
        cams = ", ".join(p["cameras_seen"])
        lines.append(
            f"- **Person {p['global_id']}** — seen on {cams} "
            f"({p['first_seen']:.0f}s → {p['last_seen']:.0f}s, "
            f"{p['num_local_tracks']} local tracks)"
        )

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
