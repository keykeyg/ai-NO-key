# AI No Key — **mac** branch

Tag someone in one frame. Search every camera **8pm–3am**.

**Default: NVR pull** — only downloads the time window you ask for (not 90GB).  
**Backup: local drop-in** — use clips already under `data/cameras/`.

---

## Brother (easiest)

```bash
git clone -b mac https://github.com/keykeyg/ai-NO-key.git
cd ai-NO-key
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
chmod +x "AI No Key.command"
```

1. Double-click **AI No Key.command**
2. First-run wizard → UniFi IP / user / password / timezone
3. Tag a person → Search `20:00`–`03:00` (source = NVR pull)

---

## How search works now

| Source | What it does |
|--------|----------------|
| **NVR** (default) | Pulls only that window from UniFi Protect / Frigate in 15-min chunks, then searches |
| **Local** | Uses clips already dropped in `data/cameras/<cam>/` |

CLI:

```bash
# NVR (default) — pulls 8pm–3am only
python scripts/search_person.py --profile Marcus --start 20:00 --end 03:00

# Local backup
python scripts/search_person.py --profile Marcus --start 20:00 --end 03:00 --source local
```

Brother can run this from home if the Protect box is reachable (VPN / port forward / LAN).

---

## Web UI

```bash
python scripts/serve_ui.py   # or double-click AI No Key.command
# http://127.0.0.1:8787
```

Search panel has a **Source** dropdown: NVR pull vs Local drop-in.
