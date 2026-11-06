# GC2 task status — 2026-11-06

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
**Commit:** `e96592a`, timer schedule correction `c52370f`
**Files:** `analytics_feedback/channel_reconcile.py`, `analytics_feedback/cli.py`, `ops/asus-server/venho-growth-reconcile.{service,timer}`, `tests/test_legacy_channel_reconcile.py`
**Verify:** targeted tests → 2 passed; VERIFY_LEGACY → 2116 passed, 79 baseline failures, 8 skipped, 0 new failures.
**DoD:** [x] legacy registry/cadence read-only reconciliation [x] report outside Git [x] alert dedupe [ ] first real `fb_venho` report reviewed
**INV/AC liên quan:** không ghi registry; không dùng DB v2
**Rủi ro / việc để lại:** Requires read tokens and timer installation on server.

The plan snapshot and code-delta table were refreshed to include the production channel IDs and current implementation state in `4ce6e9f`.

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
**DoD:** [x] candidate config and token-only commands [x] unsupported metric continues [x] three account probes run and evidence reviewed
**INV/AC liên quan:** read-only GET; no production write
**Rủi ro / việc để lại:** Requires `GE_META_READ_TOKEN_FB_HANOI`, `GE_META_READ_TOKEN_FB_VENHO`, `GE_META_READ_TOKEN_IG_VENHO`.

### GC2-P0-T04b — Facebook engagement re-probe (2026-11-06)
**Status:** DONE
**Commit:** `GC2-P0-T04b: fb_hanoi engagement supported`
**Files:** `scripts/growth_engine/probe_meta_read.py`, `config/projects/venho_hotel/growth_engine/metrics_registry.yaml`, `docs/growth_engine/meta_capabilities.md`, `tests/fixtures/growth_engine/fb_engagement_probe_20261106.json`, probe and metric registry tests, `docs/growth_engine/task_status.md`
**Evidence:** Sanitized v27.0 results supplied for five `fb_hanoi` posts; reactions/comments were readable on all five with totals `1/0`, `1/0`, `0/0`, `0/0`, and `2/0`. The probe validates Facebook engagement fields and uses the same configured list for post-ID and `--list-recent` modes. No tokens or private credentials were recorded.
**Verify:** focused → 27 passed; VERIFY_DEV → 486 passed, 4 warnings; VERIFY_ARCH → 2 passed.
**DoD:** [x] `facebook_engagement` is `SUPPORTED` for `fb_hanoi` and `fb_venho`; [x] post-ID and `--list-recent` share the validated Facebook field list; [x] evidence is sanitized.
**Rủi ro / việc để lại:** P0-T04b is complete. `fb_venho` internal engagement rate remains `DATA_INCOMPLETE` until matching `post_total_media_view_unique` denominators are collected.

### GC2 operator session — TEST routing preparation (2026-11-06)
**Status:** PARTIAL — local TEST sender and manifest preparation complete; live TEST and deployment gates remain open.
**Files:** `scripts/growth_engine/send_test_command.py`, `tests/growth_engine/integration/sqlite/test_test_command_factory.py`, `config/projects/venho_hotel/growth_engine/channels.yaml`, `docs/growth_engine/environment_manifest.md`, `docs/growth_engine/runbooks/{operator_session_1,make_blueprint_v2}.md`
**Evidence:** Facebook TEST Page `Ven Hồ Growth Test`, ID `1363761820162798`, created in the Ven Ho Hotel Business portfolio. One TEST Facebook Page is shared across the two logical Facebook routes using separate TEST databases. The sender now emits the Router's three channel keys, checks the matching principal and refuses production destination IDs.
**Verify:** SQLite factory + API authorize tests exercise all three TEST channel keys and wrong-channel rejection; VERIFY_DEV → 489 passed, 4 warnings; VERIFY_ARCH → 2 passed; manifest secret scan → OK. No public test post sent.
**Outstanding:** Numeric Instagram TEST account ID, complete TEST/production environment, DNS/Cloudflare, Make TEST, 1Password backup copy, server deployment and restore rehearsal.

### GC2 handoff H1 — review `6a5545a` against current operator facts (2026-11-06)
**Status:** REVIEWED
**Findings:** `6a5545a` matches the v1.2 TEST sender contract for `fb_hanoi`, `fb_venho`, and `ig_venho`; maps both Facebook keys to TEST Page `1363761820162798`; keeps TEST DB isolation; and rejects production destination IDs. Its recorded `Outstanding` line is stale: Instagram TEST is now reported converted and linked to the TEST Page. The current `ig_test.remote_account_id` remains `REQUIRED_FROM_P0` because no numeric TEST Instagram account ID was supplied in this handoff. The Make TEST scenario remains inactive and its router/posting path is not verified by a real run; MK evidence stays `NOT_RUN`.
**Verify:** source review of `6a5545a`, `channels.yaml`, sender/auth contract, and supplied Make observations; no external systems or network accessed.

### GC2 handoff H2 — TEST destination IDs and URL-ID warning (2026-11-06)
**Status:** PARTIAL — Facebook TEST Graph API Page ID recorded; Instagram TEST link recorded, numeric ID remains `CHƯA XÁC MINH`.
**Files:** `config/projects/venho_hotel/growth_engine/channels.yaml`, `docs/growth_engine/environment_manifest.md`
**Evidence:** Page TEST ID `1363761820162798`; the supplied `profile.php?id=61596076389732` value is explicitly documented as not being its Graph API Page ID. `@hanhpham1504` is reported linked to the TEST Page, but no numeric Instagram TEST ID was present to store. No production destination ID was used for TEST.
**Verify:** YAML/manifest source review; no external systems or network accessed.
