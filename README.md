# Night Trail (mac branch)

Tag someone in one frame. Search every mapped camera for a time window (e.g. 8pm–3am).

**Formerly:** AI No Key  
**Default:** NVR pull — only the window you ask for, only mapped cameras.  
**Backup:** local drop-in under `data/cameras/`.

---

## Brother quick start (Mac)

```bash
git clone -b mac https://github.com/keykeyg/ai-NO-key.git
cd ai-NO-key
```

1. Double-click **Install AI No Key.command** (one time — venv + OSNet)
2. Optional: **Build AI No Key App.command** after `brew install --cask platypus`
3. Double-click **AI No Key.command** (or the .app)
4. Wizard → UniFi host / user / password → **Test connection**
5. Tag a person (multi-select crops) → enroll → Search `20:00` → `03:00`

UI: http://127.0.0.1:8787

---

## What’s new in this ship

- **Progress** while NVR pulls and detects (no more black-box spinner)
- **Test connection** for UniFi / Frigate
- **OSNet status** in the top bar (strong model vs weak fallback)
- **Confidence tiers** on each appearance: strong / possible
- **Clip playback** in the trail view
- **Multi-crop enroll** (select several people crops for one profile)
- **Search audit log** at `data/output/audit/searches.jsonl`

---

## Mapped Say Less cameras

See `config.example.yaml` for the full Protect name → folder map (hookah, bars, patio, upstairs, kitchen…).

---

## CLI

```bash
python scripts/search_person.py --profile Marcus --start 20:00 --end 03:00
python scripts/search_person.py --profile Marcus --start 20:00 --end 03:00 --source local
python scripts/pull_nvr.py --start 20:00 --end 03:00
```

---

## Requirements

- Mac reaches Say Less Protect (LAN or VPN)
- UniFi login in wizard
- Camera names in config match Protect **exactly**
- OSNet installed via Install script for best accuracy
