#!/usr/bin/env python3
"""Export a Person Trail to Markdown + HTML."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def seconds_to_hms(s: float) -> str:
    s = int(s)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"{m:02d}:{sec:02d}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trail", required=True, help="Path to person_trail.json")
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    trail_path = Path(args.trail)
    with open(trail_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    out_dir = Path(args.out_dir) if args.out_dir else trail_path.parent
    name = data.get("name", "person")

    # Markdown
    lines = [
        f"# Person Trail — {name}",
        "",
        f"Appearances: **{data['num_appearances']}**",
        "",
        "| # | Camera | Start | End | Score | Clip |",
        "|---|--------|-------|-----|-------|------|",
    ]
    for i, a in enumerate(data.get("appearances", []), 1):
        clip = a.get("clip", "—")
        lines.append(
            f"| {i} | {a['camera']} | {seconds_to_hms(a['start_s'])} | "
            f"{seconds_to_hms(a['end_s'])} | {a.get('score', 0):.2f} | `{clip}` |"
        )

    md_path = out_dir / "trail.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {md_path}")

    # HTML
    rows = []
    for i, a in enumerate(data.get("appearances", []), 1):
        clip = a.get("clip")
        link = f'<a href="{clip}" target="_blank">open</a>' if clip else "—"
        rows.append(
            f"<tr><td>{i}</td><td>{a['camera']}</td>"
            f"<td>{seconds_to_hms(a['start_s'])}</td>"
            f"<td>{seconds_to_hms(a['end_s'])}</td>"
            f"<td>{a.get('score', 0):.2f}</td><td>{link}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Trail — {name}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #0f1115; color: #e6e6e6; }}
h1 {{ color: #7dd3a7; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border-bottom: 1px solid #2a2f3a; padding: 0.5rem 0.8rem; text-align: left; }}
a {{ color: #7dd3a7; }}
</style></head>
<body>
<h1>Person Trail — {name}</h1>
<p>{data['num_appearances']} appearances</p>
<table>
<thead><tr><th>#</th><th>Camera</th><th>Start</th><th>End</th><th>Score</th><th>Clip</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody></table>
</body></html>"""

    html_path = out_dir / "report.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"Wrote {html_path}")


if __name__ == "__main__":
    main()
