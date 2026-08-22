# AI No Key — **mac** branch

Tag someone in one frame. Search every camera **8pm–3am**. Apple Silicon (MPS).

---

## For your brother (easiest)

One-time setup:

```bash
git clone -b mac https://github.com/keykeyg/ai-NO-key.git
cd ai-NO-key
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
chmod +x "AI No Key.command"
```

Every night after that:

1. **Double-click** `AI No Key.command` (Browser opens)
2. First launch → setup wizard (UniFi IP, user, password, timezone)
3. **Tag** a person → **Search all cameras** `20:00`–`03:00`

Password is saved only on that Mac in `.unifi.env` (gitignored). Not in GitHub.

---

## Web UI

```bash
# or double-click AI No Key.command
python scripts/serve_ui.py
# http://127.0.0.1:8787
```

| Tab | What |
|-----|------|
| Tag | One frame → number people → enroll |
| Search | Profile + time window → trail across cameras |
| Trails | Open saved nights |
| ⚙ | Re-open setup (UniFi / Frigate) |

---

## CLI (same pipeline)

```bash
python scripts/tag_person.py --video "data/cameras/hookah/clip.mp4" --at 5
python scripts/tag_person.py --video "data/cameras/hookah/clip.mp4" --at 5 --pick 0 --name Marcus --role hookah
python scripts/search_person.py --profile Marcus --start 20:00 --end 03:00
```

Pull night from Protect:

```bash
# after setup wizard, or:
export UNIFI_HOST=... UNIFI_USERNAME=... UNIFI_PASSWORD=...
python scripts/pull_nvr.py --start "2026-08-21 20:00" --end "2026-08-22 03:00"
python scripts/process_night.py --config config.yaml --force
```

---

## Notes

- Real DMG / App Store app would still wrap this Python stack (YOLO + MPS). Double-click `.command` is the practical Mac distribution for now.
- `config.yaml` and `.unifi.env` stay local (gitignored).
