# AI No Key — mac branch (Say Less)

Tag someone in one frame. Search every mapped camera for a time window (e.g. 8pm–3am).

**Default: NVR pull** — only the window you ask for, only mapped cameras.  
**Backup: local drop-in** — clips already under `data/cameras/`.

---

## Brother quick start (Mac)

```bash
git clone -b mac https://github.com/keykeyg/ai-NO-key.git
cd ai-NO-key
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
chmod +x "AI No Key.command"
```

1. Double-click **AI No Key.command**
2. First-run wizard → UniFi host / username / password / timezone
3. Tag a person from a clip → enroll with a name
4. Search `20:00` → `03:00` (Source = NVR pull)

Browser opens at http://127.0.0.1:8787

---

## What “window” means

The start/end you type. Example: `20:00` to `03:00` = last night’s shift.  
NVR mode pulls **only that span** from Protect (15-min chunks), not the whole archive.

---

## Mapped Say Less cameras (priority)

| Protect name | Folder |
|---|---|
| Hookah Room | hookah_room |
| Downstairs Across Hookah D1 | hookah_across |
| Downstairs Corner Hightops D4 | hightops |
| Downstairs Above Fireplace D2 | fireplace |
| Downstairs Main Bar D7 | bar_main_d |
| Downstairs Server Bar D8 | server_bar |
| Downstairs D9 server bar 2nd cam | server_bar_2 |
| First Floor Front Patio D6 | patio_front |
| Upstairs Facing Bar U7 | bar_facing_u |
| Upstairs Corner Near Balcony Door U6 | lounge_corner |
| Upstairs Facing Balcony Door U5 | lounge_balcony |
| Balcony | balcony |
| + kitchen / elevator / office (see config.example.yaml) |

Rename remaining `G5 Turret Ultra` kitchen cams in Protect, then add exact names to config.

---

## CLI

```bash
# NVR search (default) — pulls only the window from mapped cams
python scripts/search_person.py --profile Marcus --start 20:00 --end 03:00

# Local backup (pre-dropped clips)
python scripts/search_person.py --profile Marcus --start 20:00 --end 03:00 --source local

# Just pull footage for a window
python scripts/pull_nvr.py --start 20:00 --end 03:00
```

---

## Requirements for NVR mode

- Mac can reach Say Less Protect (LAN or VPN)
- UniFi username/password saved in wizard (`.unifi.env`)
- Camera names in config match Protect **exactly**

---

## Branches

- `mac` — Apple Silicon (MPS), this README
- `windows` — CUDA / 3090
- `main` — portable fallback
