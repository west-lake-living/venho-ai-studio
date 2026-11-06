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

### GC2 handoff H3 — Meta token environment mapping (2026-11-06)
**Status:** DONE — repository mapping established; token values remain outside Git.
**Files:** `docs/growth_engine/environment_manifest.md`, `docs/growth_engine/runbooks/operator_session_1.md`
**Findings:** `PAGE_A` maps to `fb_hanoi`; `PAGE_B` maps to `fb_venho`; `IG_VENHO` maps to `ig_venho`. Probe uses `FB_HANOI`, `FB_VENHO`, `IG_VENHO`. `Settings` validates presence generically, not exact channel variable names. Production needs the three probe names plus PAGE_A/PAGE_B aliases for the existing manifest references; the paired names carry the same channel token.
**Verify:** source review of `channels.yaml`, `meta_probe_candidates.yaml`, `Settings`, and production validation; no secret values read or written.

### GC2 handoff H4 — Make UI observations and TEST blueprint (2026-11-06)
**Status:** DOCS READY — no Make configuration changed; all MK evidence remains `NOT_RUN`.
**Files:** `docs/growth_engine/runbooks/make_blueprint_v2.md`, `docs/growth_engine/make_capabilities.md`
**Evidence:** Recorded production scenario `5868920` and inactive TEST copy `6924867` from the supplied Make UI observations. Documented platform/publication filters, missing `channel_key`, module/response placement, pre-Router image download, and required TEST mapping/filters/responses. No History/module output was supplied, so sequential/retry/output-field evidence remains `CHƯA XÁC MINH`.
**Verify:** document review against §8.1.4 and supplied observations; no Make or network access.

### GC2 handoff H5 — TEST webhook structure sample (2026-11-06)
**Status:** READY FOR OPERATOR — no webhook request sent.
**Files:** `docs/growth_engine/runbooks/make_test_sample_payload.json`, `docs/growth_engine/runbooks/operator_session_1.md`
**Evidence:** Sample follows `contracts/growth_engine/command_envelope.v2.schema.json` with synthetic identity, hash, token shape and `.invalid` media host. The actual envelope schema has no `content`, `image_url`, or `publication_id`; Instagram maps its posting image URL from `media_url`, and caption is returned by authorize. The synthetic `command_token` satisfies only the JSON pattern and is not cryptographically valid. Runbook requires downstream modules disconnected before sending.
**Verify:** JSON Schema validation; no webhook/network request or provider call.

### GC2 handoff H6 — migration, service token hashing, TEST Settings (2026-11-06)
**Status:** DONE — code facts documented; no server migration or secret operation performed.
**Files:** `scripts/growth_engine/hash_service_token.py`, `tests/growth_engine/test_hash_service_token.py`, `docs/growth_engine/runbooks/operator_session_1.md`
**Findings:** `venho-engine migrate` applies the SQLite migrations; deployment script only runs `migrate --check`. Bearers are SHA-256 hex of trimmed UTF-8 and auth maps fixed route principals to one channel each. TEST uses separate hashes in its isolated env file; suffix `-test` principal names are not in the auth policy and are not usable. API TEST/doctor requires DB path, media root, public base URL, capability keys, service-token mapping; optional prefixed settings, if set, must be filled. The test command factory has additional channel/destination/webhook/Graph-version requirements.
**Verify:** `uv run --no-sync pytest -q tests/growth_engine/test_hash_service_token.py` → 1 passed; synthetic migrated TEST DB Settings/doctor → `Settings complete: PASS`, 10 checks, 0 FAIL. No server, secrets, or network accessed.

### GC2 handoff H7 — safe env-file entry and status check (2026-11-06)
**Status:** DONE — runbook-only; no environment file was opened or changed.
**Files:** `docs/growth_engine/runbooks/operator_session_1.md`
**Evidence:** Added hidden `read -rs` input, one-variable replacement via stdin, mode `600`, xtrace guard, and a status command that prints only requested variable names, presence/placeholder state, and file mode.
**Verify:** `bash -n` syntax check of the documented setter; synthetic-only review; no real env file or secret accessed.

### GC2 handoff H8 — synchronized status and remaining human gates (2026-11-06)
**Status:** IN PROGRESS — repository preparation complete; external gates remain with Harry.
**Files:** root `task_status.md`, `docs/growth_engine/task_status.md`
**Human gates still open:** (1) finish production env (`GE_HEARTBEAT_URL`, Telegram bot/chat, the three Meta probe tokens plus PAGE_A/PAGE_B aliases) and the isolated TEST env; (2) record the numeric Instagram TEST ID; (3) choose a TEST hostname, configure Cloudflare Tunnel/Access, deploy/run TEST API on `8022`; (4) update Make TEST filters/responses, isolate posting modules while capturing webhook structure, then obtain Harry's approval before any public TEST post; (5) run TEST commands, record MK-1…MK-11, restore rehearsal, install T0-05/T0-06 timers; (6) copy the age identity to 1Password; (7) Harry reviews and pushes; (8) renew Instagram token before expiry and remove/pause Healthchecks `My First Check`. No external system was changed in this handoff.
**Unresolved implementation constraint:** separate TEST bearer values can use the isolated TEST env file, but unique `*-test` principal names are not supported by the current fixed auth policy. TEST helper/config uses the existing one-channel principal labels; do not invent suffix names.
**H1–H7 commits:** H1 `ca178a1`; H2 `a721b75`; H3 `05663d7`; H4 `9ada4c2`; H5 `b6abe9a`; H6 `d3cb731`; H7 `996cede`.
**Final verify:** `VERIFY_DEV` → 490 passed, 4 warnings; `VERIFY_ARCH` → 2 passed; baseline `VERIFY_LEGACY` → 2131 passed, 79 failed, 8 skipped, 12 warnings. All 79 failing node IDs exactly match `legacy_test_baseline.txt`; 0 new failures. Manifest secret scan and `git diff --check` pass. No external systems or network calls.
**H8 commit:** this record is committed as `GC2-HANDOFF-H8: synchronize status and gates`; SHA is reported in the handoff summary.

### GC2 handoff K1 — Instagram TEST account ID (2026-11-06)
**Status:** DONE
**Commit:** `f916506`
**Files:** `config/projects/venho_hotel/growth_engine/channels.yaml`, `docs/growth_engine/environment_manifest.md`
**Evidence:** Set `ig_test.remote_account_id` to the supplied ID `17841472240799413` for `@hanhpham1504`, linked to TEST Page `1363761820162798`. Kept the production Instagram ID separate.
**Verify:** YAML parse and manifest secret scan; no external system accessed.

### GC2 handoff K2 — legacy Make signature and TEST replacement (2026-11-06)
**Status:** DONE — documentation only; no Make scenario changed.
**Commit:** `1bef7fc`
**Files:** `docs/growth_engine/runbooks/make_blueprint_v2.md`, `docs/growth_engine/runbooks/retire_legacy.md`
**Findings:** Recorded the signature filter placement and visible 64-character hex literal without copying its value; purpose is `CHƯA XÁC MINH`. TEST blueprint removes this legacy filter and uses the common `schema_version`/`environment` condition. Added the production cutover removal/rotation assessment and noted the reported Free plan limit of two active scenarios.
**Verify:** documentation review; no Make, network or secret access.

### GC2 handoff K3 — safe Meta token transfer script (2026-11-06)
**Status:** IN PROGRESS — local implementation and fake-transport tests; not run against Meta or server.
**Commit:** pending
**Files:** `ops/asus-server/growth-engine/push-meta-tokens.py`, `tests/growth_engine/test_push_meta_tokens.py`, `docs/growth_engine/runbooks/operator_session_1.md`
**Verify:** `uv run --no-sync pytest -q tests/growth_engine/test_push_meta_tokens.py` → 4 passed; full VERIFY_DEV/VERIFY_ARCH/legacy baseline pending.
**Safety:** Page selection uses exact IDs; token input is hidden; no live credentials or remote operation were used in this work.
