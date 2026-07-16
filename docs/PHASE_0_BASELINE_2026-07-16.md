# VENHO AI STUDIO — PHASE 0 BASELINE

**Date:** 2026-07-16  
**Scope:** Phase 0 — Baseline, Security & Git Freeze for AI Studio v1.5 rollout.

---

## Verified Baseline

### venho-os

- Branch: `main`
- Remote: `origin/main`
- Latest Phase 0 commit: `4aa6651` — `Isolate image route tests from production artifacts`
- Image Studio commit: `6e2a93c` — `Improve image generation identity controls`
- Security placeholder commit: `6c45c9a` — `Avoid key-shaped placeholders`
- Tests: `54/54` pass
- Lint: pass
- TypeScript: pass
- Build: pass
- Known warning: Turbopack NFT trace warning in `src/app/api/v1/studio/observe/route.ts`; tracked as known issue, not a build failure.

### venho-ai-studio

- Branch: `main`
- Remote: `origin/main`
- Roadmap commit: `d521e48` — `Add AI Studio implementation roadmap v1.5`
- Face Validator commit: `2ad75f7` — `Improve face validation score handling`
- Security placeholder commit: `11c2481` — `Avoid key-shaped environment placeholders`
- Tests: `424/424` pass

---

## Security Status

- Repo text scan found no active OpenAI/Anthropic key-shaped placeholders.
- `.env.example` placeholders now use non-secret-shaped values.
- External action still required: revoke/rotate the exposed OpenAI API key in the OpenAI dashboard.

---

## Artifact Hygiene

- Removed local test artifact path from VenHoSocialManager production tree:
  - `photos-ai/2026/test`
- Updated `generate-image-route` unit test to use a temp directory instead of production `photos-ai`.

---

## Git Hygiene

### Clean / controlled

- `venho-os` Phase 0 work is committed and pushed.
- `venho-ai-studio` roadmap, validator fix, and placeholder cleanup are committed and pushed.

### Not included in Phase 0 commits

The following `venho-ai-studio` worktree changes existed outside this Phase 0 scope and were intentionally not committed:

- M10 design/document deletions
- Streamlit/dashboard deletion files
- Content Studio generator changes
- `task_status.md` and `task_memory.md` broad historical edits
- `config/projects/linh_an/`
- `content_studio/generators/`
- `docs/VENHO_AI_STUDIO_MOTHER_PLAN_ROADMAP_v1_4_RECONCILED_2026-07-15.md`

These need a separate classification/commit pass before Phase 1 starts.

---

## Phase 0 Gate Status

| Gate | Status |
|---|---|
| Secret-shaped placeholders removed from repo examples | Done |
| `venho-os` Image Studio pending files committed | Done |
| AI Studio Face Validator fix committed | Done |
| Roadmap v1.5 committed | Done |
| Test artifacts removed from production history | Done |
| Build warning documented as known issue | Done |
| AI Studio tests baseline verified | Done — `424/424` |
| VenHo OS tests/build baseline verified | Done — `54/54` + build pass |
| Exposed OpenAI key revoked/rotated | Pending external action |
| `task_status.md` / `task_memory.md` fully synced | Pending separate dirty-worktree cleanup |
