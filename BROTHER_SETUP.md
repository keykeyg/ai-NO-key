# Night Trail — Brother Setup (Mac at Say Less)

You are at the bar with an Apple Silicon MacBook. Goal: connect to the **local** UNVR, tag a person, search a short window.

Product name in the UI: **Night Trail**  
Repo branch: **mac**

---

## 1) Get the code

Open **Terminal** and run:

```bash
cd ~
git clone -b mac https://github.com/keykeyg/ai-NO-key.git
cd ai-NO-key
chmod +x "Install AI No Key.command" "AI No Key.command" scripts/*.sh
xattr -cr .
```

If the folder already exists:

```bash
cd ~/ai-NO-key
git fetch origin
git checkout mac
git pull origin mac
```

---

## 2) Install (one time)

**Preferred:** double-click **Install AI No Key.command**

If that fails, paste this in Terminal:

```bash
cd ~/ai-NO-key

# Apple Silicon Python
if [ ! -x /opt/homebrew/bin/python3.11 ]; then
  brew install python@3.11
fi

rm -rf .venv
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install "numpy>=1.24,<2.0"
python -m pip install -r requirements.txt
python -m pip install Cython tensorboard
python -m pip install --no-build-isolation "git+https://github.com/KaiyangZhou/deep-person-reid.git"
python -c "from torchreid.utils import FeatureExtractor; print('OSNet OK')"
```

You want **`OSNet OK`**. If that line fails, stop and text Keyan the error.

---

## 3) Find the UNVR IP (local network only)

You must be on **Say Less Wi‑Fi** (same LAN as the cameras / UNVR).

1. Open UniFi Protect / Console for **Say Less NVR**
2. **Control Plane → About This Console** (or Console network settings)
3. Copy the **current IP** — **not** the “Fallback IP”
4. Test from Terminal:

```bash
ping <UNVR_IP>
```

Ping must work before the app will.

---

## 4) Launch

Double-click **AI No Key.command**  
or:

```bash
cd ~/ai-NO-key
source .venv/bin/activate
./AI\ No\ Key.command
```

Wait until Terminal shows something like:

```text
Night Trail  [LIVE]  source=nvr  OSNet ready
http://127.0.0.1:8787
```

Safari should open the UI. If not, go to: **http://127.0.0.1:8787**

---

## 5) Connect NVR (wizard)

| Field | Value |
|--------|--------|
| System | UniFi Protect |
| Host / IP | the live UNVR IP from step 3 |
| Username | local UniFi OS admin |
| Password | that account’s password |
| Port | 443 |

Click **Test connection** → want **OK — N cameras**.  
Then set timezone **America/Chicago** → **Save**.  

Password stays only on this Mac (`.unifi.env`).

---

## 6) First real sample (keep it small)

1. **Seed from NVR** — camera you know (e.g. Hookah Room), time like `20:43`, minutes `2` → **Pull seed clip**
2. **Detect people** → select 1–3 crops of the same person → name them → **Save profile**
3. **Search** that profile, short window only (e.g. `20:40` → `21:00`), source **NVR pull**
4. Check trail: cameras, strong/possible, play clips, mark ✓/✗

Do **not** run a full 8pm–3am on the first try.

---

## If something breaks

| Symptom | Fix |
|---------|-----|
| `Bad CPU type` / wrong Python | Use `/opt/homebrew/bin/python3.11` as above |
| `OSNet missing` | Re-run the pip torchreid lines |
| Test connection failed | Ping UNVR IP; must be on bar Wi‑Fi; use local admin user |
| Safari can’t connect | Wait for “OSNet ready” line; open http://127.0.0.1:8787 |
| Permissions on .command | `chmod +x` and `xattr -cr .` |

Text Keyan a screenshot of any error.
