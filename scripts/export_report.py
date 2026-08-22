#!/usr/bin/env python3
"""Turn global_report.json into a readable markdown timeline + simple HTML viewer."""

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


def build_markdown(data: dict) -> str:
    lines = [
        "# Night Summary — AI No Key",
        "",
        f"- Cameras processed: **{data['num_cameras']}**",
        f"- Unique people tracked: **{data['num_global_people']}**",
        "",
        "## Timeline",
        "",
    ]

    # Sort people by first appearance
    people = sorted(data.get("people", []), key=lambda p: p.get("first_seen", 0))

    for p in people:
        cams = ", ".join(p["cameras_seen"])
        lines.append(
            f"### Person {p['global_id']}"
        )
        lines.append(
            f"- Seen: {seconds_to_hms(p['first_seen'])} → {seconds_to_hms(p['last_seen'])}"
        )
        lines.append(f"- Cameras: {cams}")
        lines.append(f"- Local tracks: {p['num_local_tracks']}")

        if p.get("clips"):
            lines.append("- Clips:")
            for c in p["clips"]:
                lines.append(
                    f"  - `{c['camera']}` ({seconds_to_hms(c['start_s'])}–{seconds_to_hms(c['end_s'])}) → `{c['clip']}`"
                )
        lines.append("")

    return "\n".join(lines)


def build_html(data: dict, output_dir: Path) -> str:
    people = sorted(data.get("people", []), key=lambda p: p.get("first_seen", 0))

    rows = []
    for p in people:
        cams = ", ".join(p["cameras_seen"])
        clip_links = []
        for c in p.get("clips", []):
            # Relative path from the HTML file location (output_dir)
            rel = c["clip"]
            clip_links.append(
                f'<a href="{rel}" target="_blank">{c["camera"]} ({seconds_to_hms(c["start_s"])})</a>'
            )
        clips_html = " · ".join(clip_links) if clip_links else "—"

        rows.append(
            f"""
            <tr>
              <td><strong>#{p['global_id']}</strong></td>
              <td>{seconds_to_hms(p['first_seen'])}</td>
              <td>{seconds_to_hms(p['last_seen'])}</td>
              <td>{cams}</td>
              <td>{p['num_local_tracks']}</td>
              <td>{clips_html}</td>
            </tr>
            """
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>AI No Key — Night Report</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; margin: 2rem; background: #0f1115; color: #e6e6e6; }}
    h1 {{ color: #7dd3a7; }}
    .meta {{ color: #9aa0a6; margin-bottom: 1.5rem; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #2a2f3a; padding: 0.6rem 0.8rem; text-align: left; }}
    th {{ color: #9aa0a6; font-weight: 600; }}
    a {{ color: #7dd3a7; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    tr:hover {{ background: #1a1f2a; }}
  </style>
</head>
<body>
  <h1>AI No Key — Night Report</h1>
  <div class="meta">
    {data['num_cameras']} cameras · {data['num_global_people']} unique people
  </div>
  <table>
    <thead>
      <tr>
        <th>Person</th>
        <th>First seen</th>
        <th>Last seen</th>
        <th>Cameras</th>
        <th>Tracks</th>
        <th>Clips</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""
    return html


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="data/output/global_report.json")
    parser.add_argument("--out-md", default="data/output/night_summary.md")
    parser.add_argument("--out-html", default="data/output/report.html")
    args = parser.parse_args()

    report_path = Path(args.report)
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    out_dir = report_path.parent

    md = build_markdown(data)
    Path(args.out_md).write_text(md, encoding="utf-8")
    print(f"Wrote {args.out_md}")

    html = build_html(data, out_dir)
    Path(args.out_html).write_text(html, encoding="utf-8")
    print(f"Wrote {args.out_html}")
    print("Open the HTML file in a browser to click through clips.")


if __name__ == "__main__":
    main()
