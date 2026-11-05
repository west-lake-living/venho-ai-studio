# GC2 task status — 2026-11-05

`task_status.md` was absent on this branch at the start of the run. This file records the requested work from this run; human-only gates remain open where noted.

### GC2-P0-T03 — Đồng bộ checklist Make Router v1.2 (2026-11-05)
**Status:** PARTIAL
**Commit:** `8c4575f`
**Files:** `docs/growth_engine/runbooks/make_blueprint_v2.md`, `operator_session_1.md`, `make_capabilities.md`
**Verify:** Review against §8.1.4; Router 3 nhánh, IG image URL, MK-1…MK-11 present.
**DoD:** [x] TEST blueprint/checklist aligned [ ] TEST Make evidence reviewed by Harry
**INV/AC liên quan:** INV-10; MK-1…MK-11
**Rủi ro / việc để lại:** Không mở Make; TEST destinations, API TEST, Cloudflare and module History evidence await operator.

### GC2-T0-04 — Shared Meta read client (2026-11-05)
**Status:** DONE
**Commit:** `11cf1fc`
**Files:** `shared/meta/graph_client.py`, `tests/growth_engine/unit/adapters/outbound/meta/test_graph_client.py`
**Verify:** targeted client tests → 14 passed; VERIFY_DEV → 476 passed; VERIFY_LEGACY → 2116 passed, 79 baseline failures, 8 skipped, 0 new failures.
**DoD:** [x] GET-only shared client supports optional period for candidate IG media metrics [x] fake transport only
**INV/AC liên quan:** 0 pytest network
**Rủi ro / việc để lại:** None for client code.

### GC2-T0-05 — Legacy channel reconciliation (2026-11-05)
**Status:** PARTIAL
**Commit:** `e96592a`
**Files:** `analytics_feedback/channel_reconcile.py`, `analytics_feedback/cli.py`, `ops/asus-server/venho-growth-reconcile.{service,timer}`, `tests/test_legacy_channel_reconcile.py`
**Verify:** targeted tests → 2 passed; VERIFY_LEGACY → 2116 passed, 79 baseline failures, 8 skipped, 0 new failures.
**DoD:** [x] legacy registry/cadence read-only reconciliation [x] report outside Git [x] alert dedupe [ ] first real `fb_venho` report reviewed
**INV/AC liên quan:** không ghi registry; không dùng DB v2
**Rủi ro / việc để lại:** Requires read tokens and timer installation on server.

### GC2-T0-06 — Legacy Meta Insights backfill/report (2026-11-05)
**Status:** PARTIAL
**Commit:** `f4c6c43`
**Files:** `analytics_feedback/insights_backfill.py`, `analytics_feedback/cli.py`, `ops/asus-server/venho-growth-insights.{service,timer}`, `tests/test_legacy_insights_backfill.py`
**Verify:** targeted tests → 8 passed; VERIFY_LEGACY → 2116 passed, 79 baseline failures, 8 skipped, 0 new failures.
**DoD:** [x] independent external SQLite/report [x] replay idempotent per observation [x] no v2 DB dependency [ ] first report sent/reviewed
**INV/AC liên quan:** no migration edited; external report state only
**Rủi ro / việc để lại:** Requires P0-T04 metric verification, read tokens and timer installation.

### GC2-P9-T01 — Release build pin (2026-11-05)
**Status:** PARTIAL
**Commit:** `aca38c8`
**Files:** `ops/asus-server/growth-engine/deploy-release.sh`, `README.md`
**Verify:** `bash -n ops/asus-server/growth-engine/deploy-release.sh` → passed; build command/worker instances reviewed.
**DoD:** [x] managed Python 3.11 command [x] API + publish/jobs units retained [ ] server deploy/doctor run
**INV/AC liên quan:** release-only venv; production remains untouched
**Rủi ro / việc để lại:** Server deployment requires operator action; no SSH was used.

### GC2-P0-T04 — Meta probe candidates and runner (2026-11-05)
**Status:** PARTIAL
**Commit:** `4bf77f4`
**Files:** `config/projects/venho_hotel/growth_engine/meta_probe_candidates.yaml`, `scripts/growth_engine/probe_meta_read.py`, `docs/growth_engine/meta_capabilities.md`, probe tests
**Verify:** targeted probe/client tests → 24 passed; VERIFY_DEV → 476 passed; VERIFY_ARCH → 2 passed; VERIFY_LEGACY → 2116 passed, 79 baseline failures, 8 skipped, 0 new failures.
**DoD:** [x] candidate config and token-only commands [x] unsupported metric continues [ ] three account probes run and evidence reviewed
**INV/AC liên quan:** read-only GET; no production write
**Rủi ro / việc để lại:** Requires `GE_META_READ_TOKEN_FB_HANOI`, `GE_META_READ_TOKEN_FB_VENHO`, `GE_META_READ_TOKEN_IG_VENHO`.
