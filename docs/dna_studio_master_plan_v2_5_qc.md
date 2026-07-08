# VENHO AI STUDIO
## DNA Studio / AI Vision Engine — Development Roadmap v2.5 QC

**Workspace:** THE WEST LAKE LIVING
**Repo:** `venho-ai-studio`
**Module:** `knowledge_studio/vision`
**Source:** DNA Studio / AI Vision Engine — Master Plan v2.4 Complete
**Purpose:** Phased development plan, quality-checked, for deployment with Claude Code / VS Code.

---

# 1. Quality Review Summary

v2.4 reached high quality and is ready for deployment. Core decisions validated:

1. **Mode A is the general engine** — any image → observation `.md + .json`
2. **Mode B is the specialized layer** — multiple images of same subject → DNA `.md + .json`
3. **Ven Hồ Hotel is not in core** — it is the first project in `config/projects/venho_hotel/`
4. **Pass 2A is deterministic (code-only)** — DNA structure is not decided by LLM
5. **Pass 2B only canonicalizes wording** — LLM cannot change keys, invariant/variable, evidence
6. **Fixed key + type is a survival condition** — without fixed keys, evidence count is unreliable
7. **English values is the right call** — enables stable string matching for downstream AI
8. **Curated Overlay is necessary** — human knowledge (Visual DNA, forbidden rules, allowed imperfections) survives every regeneration
9. **ALLOWED IMPERFECTIONS is important** — upholds "trustworthy over beautiful" philosophy
10. **Face QC gate is mandatory** — prevents Linh An self-contamination loop

---

# 2. Risks Identified and Mitigations

## 2.1 No phase-level project management

**Problem:** v2.4 had great step-by-step roadmap but no phase grouping for progress tracking.
**Mitigation:** v2.5 groups steps into 8 phases (0–7), each with Objective, Scope, DoD, and Quality Gate.

## 2.2 No phase-level quality gate

**Problem:** Per-step DoD existed but no phase gate.
**Mitigation:** Every phase in v2.5 has a Stop Condition — cannot advance to next phase if gate not met.

## 2.3 Downstream contract needs stronger protection

**Problem:** v2.4 had `contract_version` but contract tests were missing.
**Mitigation:** Phase 7 adds `test_mode_a_contract.py` and `test_mode_b_contract.py`. Contract changes must bump `contract_version`.

## 2.4 Overlay misuse risk

**Problem:** Overlay is powerful but can be misused to create fake machine evidence.
**Mitigation:** Overlay rules:
- Only use for policy, forbidden, allowed imperfections, curator notes, wording overrides
- Overlay must not create fake evidence
- Overlay must not add invariant keys not observed (unless explicitly `curated_only`)

## 2.5 Mode A deprioritized too early

**Problem:** Project tends to pull toward Ven Hồ / DNA before Mode A is stable.
**Mitigation:** v2.5 enforces: **Do not start Mode B before Mode A runs reliably.**

## 2.6 Face DNA self-contamination

**Problem:** v2.4 mentioned QC 07F but did not make it a separate phase.
**Mitigation:** Phase 6 dedicated entirely to Face Subject / Linh An. Only begins after Mode B is stable on non-face subjects.

---

# 3. Final Product Architecture

```text
venho-ai-studio/
│
├── config/
│   ├── settings.yaml
│   ├── universal_schema.yaml
│   └── projects/
│       └── venho_hotel/
│           └── subjects/
│               ├── lake_view_room.yaml + .overrides.yaml
│               ├── deluxe_double.yaml + .overrides.yaml
│               ├── lobby.yaml + .overrides.yaml
│               ├── facade.yaml + .overrides.yaml
│               ├── westlake.yaml + .overrides.yaml
│               ├── outside.yaml + .overrides.yaml
│               └── linh_an.yaml + .overrides.yaml
│
├── shared/vision/
│   ├── client.py           ← VisionClient, MockVisionClient
│   ├── image_loader.py     ← load_images, read_exif, image_hash
│   ├── structured.py
│   └── errors.py
│
├── knowledge_studio/vision/
│   ├── schemas/            ← base.py, universal.py, room.py, face.py, linh_an.py …
│   ├── prompts/            ← observe_universal.md, observe_linh_an.md, consolidate_values.md
│   ├── pass0_classify.py   ← Auto classify mixed folder
│   ├── pass1_observe.py    ← Image → observation (with cache)
│   ├── pass2_consolidate.py ← Observations → DNA (2A deterministic + 2B wording)
│   ├── overlay_merge.py    ← Curated overlay → final DNA
│   ├── schema_bootstrap.py ← Bootstrap starter schema from sample images
│   ├── subject_resolver.py ← Project/subject → SubjectDef
│   ├── dna_manifest.py     ← Versioning, archiving, change detection
│   ├── pipeline.py         ← run_mode_a, run_mode_b, run_all
│   ├── cli.py              ← venho vision + venho vault commands
│   ├── vault_search.py     ← Full-text search across DNA files
│   ├── vault_diff.py       ← Unified diff between archived and current DNA
│   └── vault_export.py     ← Export DNA as GPT-ready text block
│
├── data/                   ← .gitignore
│   └── projects/venho_hotel/
│       ├── media/          ← Source images (one subject per subfolder)
│       ├── observations/   ← Observation cache
│       └── knowledge/      ← DNA output + archive + manifests
│
├── tests/                  ← All test files (248 tests, all mock)
│   ├── test_mock.py
│   ├── test_pass2a.py
│   ├── test_phase5.py      ← overlay, subject resolution, run_all
│   ├── test_phase6.py      ← cache key, new subjects
│   ├── test_phase7.py      ← bootstrap, classify, linh_an
│   ├── test_phase8.py      ← recursive loader, model config
│   ├── test_vault.py       ← vault search/diff/export, EXIF
│   ├── test_mode_a_contract.py
│   ├── test_mode_b_contract.py
│   ├── test_regeneration_policy.py
│   ├── test_subject_resolver.py
│   ├── test_overlay_merge.py
│   ├── test_cache.py
│   └── test_cli.py
│
└── docs/
    ├── dna_studio_master_plan_v2_4.md
    ├── dna_studio_master_plan_v2_5_qc.md  ← This file
    ├── contracts.md
    ├── how_to_run_mode_a.md
    ├── how_to_run_mode_b.md
    ├── how_to_create_new_project.md
    ├── how_to_create_new_subject.md
    ├── how_to_use_overrides.md
    ├── how_to_run_face_subject.md
    └── troubleshooting.md
```

---

# 4. Phased Development Plan

## PHASE 0 — Project Foundation ✅

**Objective:** Create clean `venho-ai-studio` repo, runnable locally.

**DoD:**
- `pip install -e .` works
- Module imports without error
- `data/` in `.gitignore`
- `settings.yaml` has all required fields
- No real API calls yet
- No Ven Hồ hard-coding in core

**Quality Gate:** Cannot advance if repo cannot run or config is missing thresholds.

---

## PHASE 1 — Shared Vision Core ✅

**Objective:** Provider-agnostic vision client with mock provider.

**DoD:**
- One image + simple schema → valid dict
- Switching provider doesn't change output shape
- Mock tests don't call real API
- Invalid JSON → retry per settings
- One image failure doesn't kill batch
- Observation saves provider + model metadata

**Quality Gate:** Cannot advance without mock provider and structured output validation.

---

## PHASE 2 — Mode A MVP ✅

**Objective:** Any image → observation `.md + .json`.

**DoD:**
- 10–20 arbitrary images process correctly
- Each image produces `.md + .json`
- Same image run twice → cache hit
- `prompt_version` change → cache invalidated
- Markdown has fixed sections
- JSON round-trips
- Duplicate filenames handled via hash suffix
- End-of-run report: total / processed / cache hits / failed / output path

**Quality Gate:** Must stop and review Mode A before starting Mode B.

---

## PHASE 3 — Mode B Core ✅

**Objective:** N observations of same subject → DNA JSON + Markdown.

**DoD:**
- Pass 2A runs without AI (code-only)
- Pass 2A tests for invariant / variable / weak
- Evidence count, coverage, consistency correct
- Pass 2B does not change structure
- Two runs → same invariant / variable
- DNA `.json` round-trips
- DNA `.md` has fixed sections
- Compact renders when `output.compact: true`

**Quality Gate:** Cannot advance if Pass 2A depends on LLM or invariant/variable can change between runs.

---

## PHASE 4 — Project Layer + Overlay + Ven Hồ MVP ✅

**Objective:** Project-aware engine without hard-coding Ven Hồ.

**DoD:**
- `venho_hotel` runs correctly
- Adding second project doesn't touch core
- Subject resolver logs schema source
- CLI confirms one-tier rule before Mode B
- Overlay merge correct
- Curated forbidden appears in output
- Allowed imperfections section present
- Archive works
- No-change detection works
- Manifest updated correctly

**Quality Gate:** Cannot advance if core has Ven Hồ hard-coding or overlay can overwrite evidence.

---

## PHASE 5 — Schema Bootstrap + Auto Classify ✅

**Objective:** Expand Studio to new projects/subjects without heavy manual schema writing.

**DoD:**
- Bootstrap creates valid YAML with fixed keys + enum values in English
- Human must approve before schema is used
- Classify can be enabled/disabled with `--classify`
- No auto-routing to Mode B without subject confirmation

**Quality Gate:** Cannot advance if bootstrap creates free-form keys or classify routes automatically.

---

## PHASE 6 — Face Subject / Linh An ✅

**Objective:** Safe face DNA for AI character Linh An without self-contamination.

**DoD:**
- Linh An face DNA separates invariant identity from variable appearance
- Grounding is off (confirmed in prompt file)
- QC 07F rules documented
- No unscored images in source folder
- Overlay merge correct for linh_an
- Compact DNA usable for production prompts

**Quality Gate:** Cannot advance if face DNA source contains unscored images or prompt allows identity recognition.

---

## PHASE 7 — Hardening, Tests, Documentation ✅

**Objective:** Stabilize system before UI / Automation / Prompt Studio expansion.

**Test files (all passing, zero real API calls):**
- `test_mode_a_contract.py` — Mode A JSON + Markdown contract
- `test_mode_b_contract.py` — Mode B DNA JSON + Markdown contract
- `test_regeneration_policy.py` — hashes_changed, needs_regeneration, bump_version, archive_dna
- `test_subject_resolver.py` — _dna_filename, resolve, schema priority
- `test_overlay_merge.py` — all 4 merge rules + load_overlay
- `test_cache.py` — cache key format, _load_cache behavior
- `test_cli.py` — all commands registered, help exits 0
- `test_vault.py` — vault search/diff/export + EXIF reading
- + 8 files from previous phases (test_mock, test_pass2a, test_phase5, test_phase6, test_phase7, test_phase8)

**Total: 248 tests, 0 failed.**

**Docs created:**
- `contracts.md`
- `how_to_run_mode_a.md`
- `how_to_run_mode_b.md`
- `how_to_create_new_project.md`
- `how_to_create_new_subject.md`
- `how_to_use_overrides.md`
- `how_to_run_face_subject.md`
- `troubleshooting.md`
- `dna_studio_master_plan_v2_5_qc.md` (this file)

**Bug fixed during Phase 7:**
- `_load_cache()` in `pass1_observe.py` now handles corrupt JSON gracefully (returns `None` instead of raising)

**Quality Gate:** Cannot advance to Phase 8 if tests require real API or docs are incomplete.

---

## PHASE 8 — Studio Shell / UI (Future)

**Objective:** Only begin after CLI engine is stable.

**Scope (future):**
- Select Mode A / Mode B via UI
- Choose input folder
- View progress
- View failed images
- View output Markdown
- View DNA manifest
- Re-render overlay
- Export compact DNA
- No changes to core engine

**Principle:** UI only calls pipeline. UI contains no business logic. If CLI and UI produce different results, UI is wrong.

---

# 5. Implementation Order

```
PHASE 0  Project Foundation        ✅
PHASE 1  Shared Vision Core        ✅
PHASE 2  Mode A MVP                ✅
PHASE 3  Mode B Core               ✅
PHASE 4  Project Layer + Ven Hồ   ✅
PHASE 5  Schema Bootstrap + Classify ✅
PHASE 6  Face Subject / Linh An    ✅
PHASE 7  Hardening + Documentation ✅
PHASE 8  Studio Shell / UI         [ Future ]
```

**Practical priority:**
1. Mode A first
2. Then Mode B
3. Then Ven Hồ
4. Then Linh An
5. UI last

---

# 6. Unbreakable Rules

1. Mode A does not produce DNA.
2. Mode B is the only DNA producer.
3. One subject = one tier / one character / one specific product.
4. Pass 2A decides structure by code.
5. Pass 2B only canonicalizes wording.
6. Fixed key + type is mandatory.
7. All values in observations and DNA must be in English.
8. FORBIDDEN primarily comes from curated overlay.
9. ALLOWED IMPERFECTIONS is a mandatory section in Mode B output.
10. Human edits overlay — machine never overwrites overlay.
11. Ven Hồ is not in core.
12. UI comes after CLI is stable.

---

# 7. Final Acceptance Criteria

DNA Studio / AI Vision Engine is considered complete as a foundation when:

1. ✅ Mode A works with any image
2. ✅ Mode B works with multiple images of same subject
3. ✅ Ven Hồ Hotel has at least one trustworthy DNA file
4. ✅ Output always has `.md + .json`
5. ✅ JSON has `contract_version`
6. ✅ Markdown renders from JSON
7. ✅ Cache works
8. ✅ Pass 2A is deterministic
9. ✅ Overlay survives regeneration
10. ✅ Mock provider tests work without API
11. ✅ No Ven Hồ hard-coding in core
12. ✅ CLI is fully usable
13. ✅ Docs are complete enough to run from scratch
14. ✅ Linh An face subject has QC gate
15. UI not required

**Current status: All 15 criteria met as of 2026-07-08.**

---

*VENHO AI Studio v2.5 QC — The West Lake Living Universe*
*Original roadmap: Harry Pham · QC-checked and phased: 2026-07-08*
