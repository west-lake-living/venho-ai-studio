# How to Run Mode B — DNA Builder (v2.4)

Mode B consolidates multiple images of the same subject into a single DNA file
(`VENHO_HOTEL_ROOM_DNA.md` + `.json`). AI uses this DNA to generate accurate images
without seeing the originals.

## Quick Start

```bash
# Single subject
venho vision observe --mode b --project venho_hotel --subject lake_view_room --input data/media/lake_view_room

# All subjects at once (--all)
venho vision observe --all --project venho_hotel
```

## ⚠ ONE SUBJECT = ONE TIER (v2.4 §2.1)

**Critical rule:** All images in the input folder must be the same tier/room type.

- ✅ `data/media/lake_view_room/` — all lake-view room photos → `lake_view_room` subject
- ✅ `data/media/standard_room/` — all standard room photos → `standard_room` subject
- ❌ `data/media/rooms/` — mixed lake-view and standard → DNA polluted, features drift to VARIABLE

The CLI will ask for confirmation before running Mode B.

## Supported Subjects (Ven Hồ Hotel)

| Subject | Description | Schema | Overlay |
|---------|-------------|--------|---------|
| `lake_view_room` | Phòng Đôi View Hồ Tây — 16m², lake-facing | `subjects/lake_view_room.yaml` | `lake_view_room.overrides.yaml` ✅ |
| `deluxe_double` | Phòng Deluxe Đôi — 18m², decorative molding | `subjects/deluxe_double.yaml` | `deluxe_double.overrides.yaml` ✅ |
| `room` | Hotel guest room (generic fallback) | `subjects/room.yaml` | `room.overrides.yaml` |
| `lobby` | Hotel lobby / reception | `subjects/lobby.yaml` | `lobby.overrides.yaml` ✅ |
| `facade` | Building exterior | `subjects/facade.yaml` | `facade.overrides.yaml` ✅ |
| `westlake` | West Lake environment | `subjects/westlake.yaml` | `westlake.overrides.yaml` ✅ |
| `linh_an` | Linh An face DNA | `subjects/linh_an.yaml` | `linh_an.overrides.yaml` |

All configs in `config/projects/venho_hotel/subjects/`.

> **v2.4 §2.1:** Use `lake_view_room` and `deluxe_double` (not the generic `room`) to get accurate per-tier DNA.
> Room images must be separated by tier before running Mode B.

## 🚫 Linh An — QC Gate 07F (MANDATORY)

**Only QC-passing images may enter `data/media/linh_an/`.**

Linh An is an AI-generated character. If low-quality images (facial drift) enter the DNA source:
→ DNA captures the drift → DNA generates more drifted images → **self-contamination loop**

**Rule:** Score every Linh An image using rubric `07F_QC_CHECKLIST_SCORING_RUBRIC.md`:
- ≥ 9.0/10 → ✅ Approved for DNA source (`media/linh_an/`)
- 8.0–8.9 → ⚠ Conditional (use as reference, not DNA source)
- < 8.0 → ❌ Reject — do not add to DNA source

`data/projects/venho_hotel/media/linh_an/` is a **curated selection**, not a dump of all generated images.

## Curated Overlay (v2.4 §5.2)

Each subject can have an `<subject>.overrides.yaml` file in `config/projects/venho_hotel/subjects/`.
This file is written by humans, never touched by DNA regeneration.

Contents:
- `forbidden:` — curated rules (primary source of FORBIDDEN — policy, not observation)
- `allowed_imperfections:` — acceptable imperfections per Authenticity principle
- `wording_overrides:` — replace machine wording with curated canonical wording
- `notes:` → CURATOR NOTES in DNA

**Editing overlay → just render again (no vision API calls, no version bump)**

## --all: Build DNA for Every Subject at Once (v2.4 §17)

Run Mode B for **every subject folder** found under `data/projects/<project>/media/`:

```bash
venho vision observe --all --project venho_hotel
# → discovers: lake_view_room/, deluxe_double/, lobby/, facade/, westlake/, linh_an/
# → runs Mode B for each (skips folders with no images)
```

Requirements: each folder must be named after its subject and contain only images of that subject (§2.1).

## Interactive

```bash
venho vision
# → choose B → enter project, subject, folder → confirm one-tier rule
```

## Output Files (v2.4)

Located in `data/projects/<project>/knowledge/`:
- `VENHO_HOTEL_<SUBJECT>_DNA.md` — Full DNA (INVARIANT / VARIABLE / ALLOWED IMPERFECTIONS / FORBIDDEN / EVIDENCE / CURATOR NOTES)
- `VENHO_HOTEL_<SUBJECT>_DNA.json` — Machine-readable, `contract_version: 1.1`
- `VENHO_HOTEL_<SUBJECT>_DNA_COMPACT.md` — Compact (INVARIANT + ALLOWED + FORBIDDEN only) for pasting into Flow/ChatGPT
- `dna_manifest_<subject>.json` — Version manifest (includes `overlay_applied: true/false`)

## DNA Regeneration

When you add new images and re-run Mode B:
- Same images → "no change" detected, skips re-generation
- New images → old DNA archived to `_archive/`, new version generated (version bumped)
- Overlay changes → re-render only (no vision API, no version bump)

## Pass 2A — Deterministic Logic

| Coverage | Consistency | Classification |
|----------|------------|----------------|
| ≥ 60% AND ≥ 70% | — | INVARIANT |
| ≥ 60% but < 70% | — | VARIABLE |
| < 30% | — | WEAK FEATURE |

`lighting_condition` appearing in ALL images but with different values → VARIABLE (correct per §4).

## Mock Mode (no API cost)

```bash
venho vision observe --mode b --project venho_hotel --subject room --input data/media/rooms --provider mock
```

## Tests

```bash
python3 -m pytest tests/test_pass2a.py tests/test_mock.py -v
```
