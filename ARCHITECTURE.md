# AI No Key — Architecture & Design

**Goal**  
Track a specific individual (manager, bartender, hookah staff) from a seed appearance at the start of a shift all the way through the night across ~30 cameras in a busy bar.

---

## UniFi AI Key (research summary)

AI Key is event enrichment + face naming + search, not continuous multi-camera tracking.

Limits that matter in a bar:
- ~1k–1.8k detections/hour, queue of 200 → drops events when busy
- Heavy face dependence
- Weak body ReID when faces fail
- No staff-route topology
- No true Seed → Follow workflow

---

## Our approach

1. **Staff profiles** — multiple reference photos, person-cropped on enrollment  
2. **Multi-modal identity** — body primary, face optional and low-weight until a real face model is installed  
3. **Camera topology** — plausible transitions + travel-time gates  
4. **Seed → Follow** — lock one person, build a continuous trail  
5. **Offline full pass** — no queue limits; cache detections so seed iteration is fast  
6. **Person Trail** — ordered clips + report for morning review  

---

## Priority fixes applied (2026-08-22)

1. **Face embedding** — weak upper-body histogram disabled by default (`face_backend: none`). InsightFace path ready when installed. Face weight capped low.
2. **Detection cache** — tracks + embeddings saved under `output/cache/`. `follow_person` reuses them unless `--force-detect`.
3. **Matcher** — gap penalty, higher score required for long/hard jumps, score-first then time order.
4. **Enrollment** — YOLO person crop before embedding reference photos.
5. **OSNet** — interface reserved (`body_method: osnet`); not wired yet.
6. **Clip paths** — stored relative to trail dir (`clips/...`) so HTML links work. Topology names validated against disk folders.

---

## Still the biggest accuracy lever

Replace hand-crafted body embedding with OSNet / Torchreid. Until then, similar black shirts and lighting changes will cause misses and false links. Topology + gap penalties reduce damage but do not replace a real ReID model.
