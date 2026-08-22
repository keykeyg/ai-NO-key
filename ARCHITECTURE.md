# AI No Key — Architecture & Design

**Goal**  
Track a specific individual (manager, bartender, hookah staff) from a seed appearance at the start of a shift all the way through the night across ~30 cameras in a busy bar environment.

This document captures the full design rationale, how UniFi AI Key actually works, where it fails in a bar, and exactly how we improve on it.

---

## 1. What UniFi AI Key Actually Does (Research Summary)

UniFi AI Key is **not** continuous multi-camera tracking of one person.

It is an **event enrichment + search + face recognition** layer:

- Cameras emit basic “person” smart detections.
- AI Key enriches them (clothing color, accessories, context descriptions, face crops).
- Faces are automatically clustered.
- User names a face in the Recognition tab → becomes a known Person of Interest.
- User can then search by name or set alarms for that face.
- Protect 6.0 added improved re-identification: pause on a frame → select person → find other appearances.

**Hard limits that matter in a busy bar:**
- ~1,000–1,800 detections per hour, internal queue of 200. Excess detections are discarded.
- Heavy dependence on clear frontal faces.
- When faces fail (dark lighting, smoke, crowded floor, staff moving fast, backs turned), recognition collapses.
- Weak use of body/clothing appearance when face is unavailable.
- No true “seed this person at shift start and follow them continuously” workflow.
- No camera topology / staff movement priors.

---

## 2. Our Goal (Improved)

**Seed → Follow**  
1. Pre-enroll key staff with multiple reference photos.  
2. At the beginning of the shift (or any clear early appearance), lock one person as the seed.  
3. Process the entire night’s footage offline on a 3090.  
4. Produce a continuous **Person Trail**: every camera appearance of that individual, ordered by time, with short review clips.

This must work even when faces are not visible for long stretches.

---

## 3. Core Technical Approach

### 3.1 Multi-Modal Identity

We never rely on face alone.

| Signal | When used | Notes |
|--------|-----------|-------|
| Face embedding | Clear frontal or near-frontal face available | High precision |
| Body / clothing ReID | Always (primary in bar) | Survives occlusion, darkness, angle changes |
| Camera transition priors | Always | Staff have predictable routes |
| Temporal windows | Always | Prevents teleportation matches |

### 3.2 Staff Profiles

Each important person (manager, bartender, hookah lead) has a profile containing:
- Multiple reference images (different lighting, angles, with/without apron/hat)
- Pre-computed face + body embeddings
- Optional notes (usual stations, shift times)

### 3.3 Seed → Follow Pipeline

1. **Enrollment** (once per person)  
   `scripts/enroll_staff.py` → builds gallery.

2. **Detection + Tracking** (per camera)  
   YOLO + ByteTrack/BoT-SORT produces local tracks with crops.

3. **Embedding**  
   Every local track receives face (if possible) + body embedding.

4. **Matching against seed**  
   Cosine similarity on the multi-modal embedding, gated by:
   - Time order
   - Maximum plausible travel time between cameras
   - Camera topology graph (which cameras are adjacent / common transitions)

5. **Trail construction**  
   Linked local tracks become one global Person Trail.

6. **Output**  
   - `person_trail.json`
   - Chronological clips under `clips/person_<id>/`
   - HTML + Markdown report focused on that one person

### 3.4 Camera Topology

Bars have structure. Staff do not teleport.

We maintain a simple graph:

```yaml
topology:
  cameras:
    - bar_main
    - bar_service
    - hookah
    - kitchen
    - office
    - entrance
  transitions:          # plausible moves + typical max seconds
    bar_main: [bar_service, hookah, entrance]
    bar_service: [bar_main, kitchen]
    hookah: [bar_main, entrance]
    kitchen: [bar_service, office]
    ...
```

This is a powerful prior that UniFi does not expose.

---

## 4. Why This Beats AI Key for Your Use Case

| Problem in busy bar | UniFi AI Key | AI No Key |
|---------------------|--------------|-----------|
| Queue limits drop detections | Yes | No (offline full pass) |
| Face not visible | Fails | Body ReID + topology still works |
| Crowded scenes | Weak association | Temporal + spatial constraints |
| Want continuous trail of one staff member | Partial (face matches) | Explicit Seed → Follow mode |
| Predictable staff routes | Not used | First-class prior |
| Multiple reference photos per person | Limited | Designed for it |

---

## 5. Implementation Status & Roadmap

**Implemented in this repo**
- Staff profile / enrollment structure
- Multi-modal embedding interface (face + body)
- Improved body embedding (stronger than basic histogram)
- Seed → Follow matching logic with topology support
- Camera topology config
- Person Trail report + clip extraction
- Overnight batch pipeline
- Full documentation

**Immediate next upgrades (easy to plug in)**
- Real OSNet / Torchreid body embeddings (biggest accuracy jump)
- InsightFace or similar high-quality face embeddings
- UniFi Protect / Frigate clip export helpers
- Simple local web UI for picking a seed from early footage

---

## 6. Practical Operating Procedure for the Bars

1. Enroll key staff once (or when they change appearance significantly).
2. At start of shift, either:
   - Use an enrolled profile, or
   - Pick a clear early track/crop as the live seed.
3. Let the overnight job run on the 3090.
4. Next morning open the Person Trail for that staff member and review the ordered clips.

This is the workflow the entire system is built around.
