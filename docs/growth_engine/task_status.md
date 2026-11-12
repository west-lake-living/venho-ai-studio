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
**Outstanding:** Complete TEST/production environment, DNS/Cloudflare, Make TEST, 1Password backup copy, server deployment and restore rehearsal. The numeric Instagram TEST ID was added by K1 below.

### GC2 handoff H1 — review `6a5545a` against current operator facts (2026-11-06)
**Status:** REVIEWED
**Findings:** `6a5545a` matches the v1.2 TEST sender contract for `fb_hanoi`, `fb_venho`, and `ig_venho`; maps both Facebook keys to TEST Page `1363761820162798`; keeps TEST DB isolation; and rejects production destination IDs. At H1, `ig_test.remote_account_id` was still `REQUIRED_FROM_P0`; K1 below subsequently recorded the supplied ID `17841472240799413`. The Make TEST scenario remains inactive and its router/posting path is not verified by a real run; MK evidence stays `NOT_RUN`.
**Verify:** source review of `6a5545a`, `channels.yaml`, sender/auth contract, and supplied Make observations; no external systems or network accessed.

### GC2 handoff H2 — TEST destination IDs and URL-ID warning (2026-11-06)
**Status:** PARTIAL as of H2 — superseded by K1, which records the Instagram TEST ID.
**Files:** `config/projects/venho_hotel/growth_engine/channels.yaml`, `docs/growth_engine/environment_manifest.md`
**Evidence at H2:** Page TEST ID `1363761820162798`; the supplied `profile.php?id=61596076389732` value is explicitly documented as not being its Graph API Page ID. At that point, `@hanhpham1504` was reported linked to the TEST Page but its numeric Instagram ID had not been supplied. K1 later records the ID; no production destination ID was used for TEST.
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
**Human gates still open:** (1) finish production env (`GE_HEARTBEAT_URL`, Telegram bot/chat, the three Meta probe tokens plus PAGE_A/PAGE_B aliases) and the isolated TEST env; (2) choose a TEST hostname, configure Cloudflare Tunnel/Access, deploy/run TEST API on `8023`; (3) update Make TEST filters/responses, isolate posting modules while capturing webhook structure, then obtain Harry's approval before any public TEST post; (4) run TEST commands, record MK-1…MK-11, restore rehearsal, install T0-05/T0-06 timers; (5) copy the age identity to 1Password; (6) Harry reviews and pushes; (7) renew Instagram token before expiry and remove/pause Healthchecks `My First Check`. Numeric Instagram TEST ID was subsequently recorded by K1. No external system was changed in this handoff.
**Unresolved implementation constraint:** separate TEST bearer values can use the isolated TEST env file, but unique `*-test` principal names are not supported by the current fixed auth policy. TEST helper/config uses the existing one-channel principal labels; do not invent suffix names.
**H1–H7 commits:** H1 `ca178a1`; H2 `a721b75`; H3 `05663d7`; H4 `9ada4c2`; H5 `b6abe9a`; H6 `d3cb731`; H7 `996cede`.
**Final verify:** `VERIFY_DEV` → 490 passed, 4 warnings; `VERIFY_ARCH` → 2 passed; baseline `VERIFY_LEGACY` → 2131 passed, 79 failed, 8 skipped, 12 warnings. All 79 failing node IDs exactly match `legacy_test_baseline.txt`; 0 new failures. Manifest secret scan and `git diff --check` pass. No external systems or network calls.
**H8 commit:** this record is committed as `GC2-HANDOFF-H8: synchronize status and gates`; SHA is reported in the handoff summary.

### GC2 handoff K1 — Instagram TEST account ID (2026-11-06)
**Status:** DONE — không cần cập nhật ID trong lượt rà soát này; đã có trong cấu hình.
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
**Status:** DONE — script and fake-transport tests complete; live Meta/server transfer remains an operator gate.
**Commit:** `8bd2d50`
**Files:** `ops/asus-server/growth-engine/push-meta-tokens.py`, `tests/growth_engine/test_push_meta_tokens.py`, `docs/growth_engine/runbooks/operator_session_1.md`
**Verify:** focused fake-transport tests → 4 passed; final VERIFY_DEV → 494 passed; VERIFY_ARCH → 2 passed; VERIFY_LEGACY → 2135 passed, 79 baseline failures, 8 skipped, 12 warnings; 0 new failures.
**Safety:** Page selection uses exact IDs; token input is hidden; no live credentials or remote operation were used in this work.

### GC2 handoff K4 — Make TEST blueprint import draft (2026-11-06)
**Status:** BLOCKED — required export file is absent.
**Commit:** `105a084`
**Files:** `.gitignore`, `docs/growth_engine/task_status.md`
**Finding:** `_incoming/make_test_export.json` was not present. No import blueprint was created or committed. Ignore rules protect both the export and import paths if supplied later.
**Modules to add in Make TEST:** Facebook `F1–F6` on `fb_hanoi`; Facebook `F1–F6` on `fb_venho`; Instagram `I1–I6` on `ig_venho`; and a `Webhook response` after the receipt on the `fb_venho` branch. Apply the common schema/environment filter, three fixed channel-key Router filters, fallback Off, and branch-local Facebook image downloads per `make_blueprint_v2.md`.
**Verify:** file-existence check only; no Make or network access.

### GC2 handoff K5 — final status and operator gates (2026-11-06)
**Status:** DONE — K1–K4 statuses and remaining human gates synchronized; K4 remains blocked pending the TEST export.
**Commit:** this status-record commit; SHA reported in the final handoff.
**K1–K5 summary (verification is on final repository HEAD):**

| Task | Commit | Result | VERIFY_DEV / VERIFY_ARCH / legacy baseline |
|---|---|---|---|
| K1 | `f916506` | DONE — TEST Instagram ID recorded | 494 passed / 2 passed / 79 of 79 baseline failures, 0 new |
| K2 | `1bef7fc` | DONE — legacy signature behavior documented; no Make edit | 494 passed / 2 passed / 79 of 79 baseline failures, 0 new |
| K3 | `8bd2d50` | DONE — safe transfer script; fake transport only | 494 passed / 2 passed / 79 of 79 baseline failures, 0 new; focused 4 passed |
| K4 | `105a084` | BLOCKED — missing `_incoming/make_test_export.json`; no blueprint fabricated | 494 passed / 2 passed / 79 of 79 baseline failures, 0 new |
| K5 | current commit | DONE — status synchronized | 494 passed / 2 passed / 79 of 79 baseline failures, 0 new |

**Verification commands:** `UV_OFFLINE=1 uv run --extra api --with pytest --with httpx pytest -q tests/growth_engine` → 494 passed, 4 warnings; `UV_OFFLINE=1 uv run --with pytest pytest -q tests/growth_engine/architecture` → 2 passed; the `VERIFY_LEGACY` command recorded in `legacy_test_baseline.txt` → 2135 passed, 79 failed, 8 skipped, 12 warnings. The 79 failing test IDs exactly match baseline; 0 new, 0 resolved.

**Phát hiện:** K3 fake tests caught and fixed an ordering bug that treated the IG user token as missing before adding it to the variable map. H1/H2/H8 contained historical statements that the Instagram TEST ID was still missing; K1 supersedes those statements and closes that gate. K4 export was absent, so Make blueprint editing was not safe to perform. No remaining code/plan mismatch requiring a change was found in K1–K5.

**Chưa xác minh:** live Meta `/me/accounts` response and token transfer; SSH host/remote file update; Make export structure, importability, placeholders and module references; TEST hostname, Cloudflare/Access and API; Make module outcomes; restore rehearsal; and timer installation. None was exercised.

**Gates còn chờ Harry:** (1) choose TEST hostname, configure Cloudflare Tunnel/Access and service token, complete TEST env/API on port 8023; (2) fill production heartbeat, two Telegram values and five Meta token variables using the K3 script when ready; (3) send the sample payload to the TEST webhook, provide/import the TEST scenario export, capture MK-1…MK-11, run restore rehearsal, and install T0-05/T0-06 timers; (4) review and push the branch, copy the age identity to 1Password, and pause/delete Healthchecks `My First Check`.

### GC2 handoff K4 — resume with TEST export (2026-11-10)
**Status:** BLOCKED_SAFE — export is present, but its module schema is insufficient for a safe import draft.
**Commit:** `GC2-HANDOFF-K4: record TEST export schema gate` (SHA in handoff report).
**Files:** `docs/growth_engine/runbooks/make_blueprint_v2.md`, `scripts/growth_engine/check_make_blueprint.py`, `tests/growth_engine/test_make_blueprint_static.py`, `docs/growth_engine/task_status.md`.
**UI observations recorded:** webhook module 2 has 15 fields; common filter is `schema_version = growth.command.v2` AND `environment = test`; Router 5 has ordered `fb_hanoi` → 3 → response 8, `ig_venho` → 6 → response 7, `fb_venho` → 12 → response 13 routes; all fallbacks Off; image HTTP 4 is still before the Router. These are operator-supplied observations, not independently verified in Make.
**Finding:** export contains Webhook, HTTP `Download a file`, Router, Facebook/Instagram posting and Webhook response modules. It does not contain an HTTP request module example for authorize/receipt or an error-handler example for F6/I6. Existing response mapper bodies also contain URL literals. No `_incoming/make_test_import.json` was produced; copying those values or inventing the missing module structures could create an unsafe/invalid scenario. Export and import remain gitignored.
**Verify:** focused checker tests → 6 passed; `VERIFY_DEV` → 500 passed, 4 warnings; `VERIFY_ARCH` → 2 passed; `VERIFY_LEGACY` → 2141 passed, 79 failed, 8 skipped, 12 warnings; all 79 failures match baseline, 0 new/0 resolved. Static check parses the source export, finds 9 modules/3 routes/18 mappings, and fails only `literal_url`; no matched value was printed. This validates the supplied export structure only, not importability or the missing modules.
**Remaining K4 gate:** provide a redacted Make export/template containing an HTTP request module with custom headers and JSON body plus a representative module error-handler route, or manually add those modules in a disposable TEST draft and export again. Then build the ignored import draft, validate all module references/IDs/placeholder fields and review it before import. Make credential-storage/redaction behavior remains **CHƯA XÁC MINH**.

### GC2 handoff K4 — build TEST import draft (2026-11-10)
**Status:** DONE — private import draft generated and statically validated. Make import/run and MK evidence remain unverified.
**Commit:** `GC2-HANDOFF-K4: generate TEST import draft` (SHA in handoff report).
**Files:** `docs/growth_engine/runbooks/make_blueprint_v2.md`, `scripts/growth_engine/{check_make_blueprint,prepare_make_test_blueprint}.py`, `tests/growth_engine/test_{make_blueprint_static,prepare_make_test_blueprint}.py`, `docs/growth_engine/task_status.md`. `_incoming/make_test_import.json` remains gitignored, mode `600`, and uncommitted.
**Draft:** 23 modules, 3 Router routes, 106 mapping references. Common filter and all three channel filters are preserved; the route order is preserved; Page/IG destinations and Make connections are unchanged. The image download is branch-local on both Facebook routes, Facebook binary/caption references are route-local, Instagram uses `media_url`, and each response follows its success receipt. Sample modules `14/15` were removed; new IDs start at `16`. Each post error route sends `OUTCOME_UNKNOWN`, then uses the exported `Ignore`/Skip directive to avoid retry or resume; Make execution semantics still require TEST confirmation.
**URL cleanup:** legacy literal URLs in `mapper.body` for Webhook response modules `7` and `8` were replaced in the draft by receipt acknowledgements. Their source locations are recorded above; the literal values are not recorded.
**Placeholders:** bearer per route, Access Client ID/Secret and `https://set-in-make.invalid` host only. HTTP module Authentication type `API key` remains an unverified alternative; draft uses a custom bearer header. The draft is mode `600` and secret scan is clear.
**Verify:** focused checker/generator tests → 9 passed; `VERIFY_DEV` → 503 passed, 4 warnings; `VERIFY_ARCH` → 2 passed; `VERIFY_LEGACY` → 2144 passed, 79 failed, 8 skipped, 12 warnings; all 79 failures match baseline, 0 new/0 resolved. Import JSON check → 23 modules, 3 routes, 106 mappings, secret scan clear.
**CHƯA XÁC MINH:** Make importability; auth/receipt HTTP behavior; posting module ID output fields; HTTP response status/header field paths; grant-expiry expression syntax; API-key credential storage; error-handler Skip routing; scenario trigger/active state and all MK-1…MK-11.
**Supersedes:** K4's prior `BLOCKED_SAFE` status above; the updated export supplied the missing HTTP request/error-handler template. No Make UI, server, network, or public post was used.

### GC2 handoff K4 — apply production History output fields (2026-11-10)
**Status:** DONE — refreshed the ignored TEST import draft using operator-supplied read-only module output evidence.
**Commit:** `GC2-HANDOFF-K4: use verified post output ids` (SHA in handoff report).
**Files:** `docs/growth_engine/runbooks/{make_blueprint_v2,retire_legacy}.md`, `scripts/growth_engine/prepare_make_test_blueprint.py`, checker/generator tests, `docs/growth_engine/task_status.md`. The ignored export/import remain uncommitted.
**Mapping audit:** Facebook Pages modules `3/12` now map `{{3.id}}` / `{{12.id}}` verbatim to receipt `platform_post_id`; no Make mapping uses `post_id`. Instagram I5 remains `{{6.id}}`. No ID splitting was added in Make. The checker now rejects a Facebook module `.post_id` alias.
**HTTP media fields:** F1/I1 filters and authorize media report now use numeric `statusCode` and lowercase `headers.content-type` per supplied History output.
**Production record:** the two read-only findings were added only to `retire_legacy.md`; Make production was not edited.
**Verify:** focused K4 checker/generator tests → 10 passed; `VERIFY_DEV` → 504 passed, 4 warnings; `VERIFY_ARCH` → 2 passed; `VERIFY_LEGACY` → 2145 passed, 79 failed, 8 skipped, 12 warnings; all 79 failures match baseline, 0 new/0 resolved. Import static check → 23 modules, 3 routes, 106 mappings, secret scan clear.
**CHƯA XÁC MINH:** HTTP `Make a request` authorize/receipt output fields; `formatDate(now; "x")`; Skip behavior; Authentication type `API key`; Make import/runtime and MK-1…MK-11.

### GC2 handoff K4 — correct Make HTTP enums and sequential mode (2026-11-10)
**Status:** DONE — refreshed the ignored TEST import draft and added static checks for request methods and immediate scheduling metadata.
**Observed:** Make TEST showed HTTP Method blank after import although the canvas label showed POST; comparison with export sample module 14 found the method enum is stored in `mapper.method` as lowercase `post`. I1 (25) showed an empty JSON body; it must be a bodyless GET. Make also displayed `Every 15 minutes` although source export metadata says `instant = true`.
**Changes:** generated HTTP methods use lowercase; I1 uses `get` and has no body mapper fields; generator preserves `metadata.instant = true`; checker rejects missing/noncanonical HTTP methods and a non-immediate scenario. Per Harry's decision A, generator sets `metadata.scenario.sequential = true` and removes Webhook response modules 8/7/13; checker rejects responders with sequential processing. `make_capabilities.md` records MK-1 as CONFIGURED, with run evidence pending.
**Preserved observations:** 23 modules before this update; three route filters/targets/connections unchanged; Facebook 3 retained its TEST connection and caption mapping from `16.data.caption`. Only the three responders were removed from route output.
**Verify:** focused checker/generator tests → 14 passed; static import check → 20 modules, 3 routes, 97 mappings, secret scan clear; method/scheduling audit → 10 lowercase nonempty HTTP methods, I1 bodyless GET, immediate trigger, sequential true, no responders; draft mode `600`.
**Unverified:** re-import UI schedule, HTTP method/body rendering, Make execution/History, authorization/receipt response fields, `formatDate`, Skip behavior and API-key auth. No Make scenario was modified in this code task.
**Supersedes:** the prior K4 draft instructions to append Webhook response modules and the prior import flow ending with responders; current output is sequential and has no explicit Webhook responders.


### GC2 TEST API bootstrap and media cache headers (2026-11-10)
**Status:** DONE — repository preparation only. No server command or network request was executed.
**API TEST host:** `https://ge-test.venhohotel.com`; locally-managed tunnel `venho-n8n` proxies `/internal` and `/media/publish` to `127.0.0.1:8023`; other paths return 404. Access app `growth-engine-test-internal` uses Service Auth token `make-growth-engine-test` on `/internal`; `/media/publish` bypasses Access but validates signed capabilities.
**Port mapping:** production Growth API `8021`; hotel-concierge-api `8022`; Growth API TEST `8023`. Earlier TEST instructions using `8022` were corrected.
**Files:** added `ops/asus-server/growth-engine/setup-test-env.sh` and `growth-engine-api-test.service`; the script is idempotent, writes only TEST paths, mode `600` env and temporary Make bearer handoff, stores only SHA-256 bearer hashes in `GE_SERVICE_TOKENS`, and does not print bearer values. Runbook now covers TEST migration/start/local health and remote curl probes using Access headers from environment.
**Media cache:** RequestMiddleware applies `Cache-Control: private, no-store` to `/media/publish` successes and handled errors; generic 500 responses on that path also carry the directive. Added fake tests for success, invalid capability, method/path errors and unhandled failure.
**Make:** import needs manual schedule reset to Immediately as data arrives and HTTP 25 opened+saved. MK-1 state is `CONFIGURED — chờ bằng chứng run`.
**Separate production gate:** operator reports `growth-api.venhohotel.com` is not provisioned. GC2-D08 production hostname remains a separate pending gate; no production hostname or tunnel change was made.
**Verify:** fake bootstrap/media/API/settings tests → 22 passed, 1 dependency deprecation warning; `bash -n`, static service-unit assertions and `git diff --check` passed. No live TEST env, systemd unit, DB migration, Healthcheck, Cloudflare or Make operation was performed.

### GC2 TEST server verification and private Make import filler (2026-11-10)
**Server observations supplied by Harry:** TEST API is running from `~/venho/gc2-src` at source SHA `8ca8661` in transient user unit `growth-engine-api-test-src`; the persistent `growth-engine-api-test.service` was not used because `~/venho/growth-engine/current` is not present before production deploy. TEST DB migration reached schema `9`. Local live/ready probes returned `200/200`; `/internal` without Access returned `403`; invalid `/media/publish` capability returned API `403` with `Cache-Control: private, no-store`.
**Runbook:** records the independent-before-production-deploy path, the confirmed source/unit/migration facts, reproducible command forms, and redacted local/remote checks. The full original shell history was not supplied.
**Implementation:** added stdlib-only `scripts/growth_engine/fill_make_test_secrets.py`. It reads the Make import draft and mode-600 bearer handoff; prompts hidden for both Access values; validates the three `channel_key` filters, route-specific bearer placeholders, all nine `/internal` modules (authorize, success receipt, error receipt), and required Access headers; writes `_incoming/make_test_import.secret.json` mode `600` and prints replacement counts only. Added `.gitignore` patterns for secret JSON and bearer handoff files.
**Safety:** test credentials were synthetic. No server, network, Make import, or credential-filled file was accessed or created during this repository task.
**Verify:** filler + Make blueprint regression tests → 19 passed; in-memory fill against the ignored real-shape draft with synthetic values replaced 9 host URLs, 3 bearer values per route, and 9 each Access ID/Secret headers; no credential file was written. `py_compile`, `git check-ignore` for both sensitive paths, and `git diff --check` passed.

### GC2 first fb_hanoi TEST command runner (2026-11-10)
**Make/API observations supplied by Harry:** secret blueprint import succeeded with 20 modules, sequential processing, Immediately scheduling and nine `/internal` modules filled for the three routes. Intermediate secret import and bearer files were deleted from Mac/server. Scenario `6924867` remains Inactive. API TEST continues in transient unit `growth-engine-api-test-src` on `:8023`; `growth-engine-test.env` was recreated, with prior file preserved as `.bak-20261110102217`.
**Implementation:** added `ops/asus-server/growth-engine/run-test-command.sh` and its Python orchestration helper. It safely/idempotently writes only the fb_hanoi TEST channel/page/webhook settings, creates and preserves a canonical UUID in `GE_TEST_CHANNEL_ID`, enters the webhook URL hidden, runs `send_test_command.py --create-command`, prints only the safe command summary, requires `ACTIVE` then exact `GUI` before `--send --confirm-test-remote-id`, and polls the TEST DB read-only for up to 120 seconds to report execution/receipt/outcome/post ID/failed step. State fields are allowlisted and post IDs must match the TEST Page format. The private command envelope stays mode `600`; child process environment excludes inherited `GE_*` production values.
**Preflight gate at implementation time:** `channels.yaml` had `page_test.graph_api_version: REQUIRED_FROM_P0`. The runner refused before prompting for the webhook or modifying env; no command was created and no public post was attempted. Resolved by the manifest update below.
**Verify:** fake orchestration/SQLite tests → 9 passed; `py_compile`, `bash -n`, and `git diff --check` passed. No server, webhook, Make or public-page request was made by this code task.

### GC2 TEST manifest values confirmed (2026-11-10)
**Changes:** filled TEST Facebook `page_test` and Instagram `ig_test` with Make scenario `6924867`, Graph API `v27.0`, owner Harry and verification date `2026-11-10`; Facebook TEST Page ID remains `1363761820162798`; IG TEST ID is `17841472240799413`. The Graph API version source is Harry's reading in Graph API Explorer for the Meta app in use. All three production Graph API versions remain `null` pending P0-T04.
**Make connection:** set `make_connection_ref` to the displayed connection name `Ven Ho Hotel Hanoi (Ha Pham)`. Numeric connection ID remains **CHƯA XÁC MINH**. The `fb_hanoi` command runner and `send_test_command.py` do not read this field, so a numeric connection ID is not required for this TEST command.
**Verify:** runner/manifest/factory/secret-scanner tests → 31 passed, 1 existing Starlette deprecation warning. `check_manifest_no_secrets.py` passed; `channels.yaml --require-filled` passed. The combined docs check still reports the documented production token gate in `environment_manifest.md`. Runner preflight checks only the `page_test` target, route reference, `fb_hanoi` principal and Graph API version needed for this command; it does not require scenario/connection metadata. No TEST command or public post was sent.

### GC2 TEST media PENDING-state and fetch-error handling (2026-11-10)
**Observed first run, supplied by Harry:** command `ef36800e-41a9-45da-b9df-209d98bcf754`, `fb_hanoi`, webhook ACK; F1/HTTP 4 received API 403 `ERR_GC2_CAPABILITY_INVALID` at 11:58:54Z before `execute_before_ms`; no execution, receipt or post. Make disabled the scenario after the unhandled HTTP error.
**Root cause/reproduction:** the URL query token is the separate five-part signed media capability (key ID, command ID and expiry, with HMAC bound to the media SHA); it has no audience claim. `command_token` is the separate audience-bound authorize token. An integration test created a fresh command still `PENDING` and GETed its media URL through the local TestClient: it returned 403 before the fix. Media validation excluded `PENDING` despite valid approval/revision/hash/QC state. Adding `PENDING` to the permitted command states made the same test return 200 with exact JPEG bytes and `private, no-store`; all other approval, QC, variant, SHA and expiry checks remain.
**Runner:** before asking `ACTIVE`/`GUI`, it now requests the private media URL via direct loopback `127.0.0.1:8023`; it requires 200, `image/jpeg`, `private, no-store`, bounded non-empty bytes and SHA match. Failures stop without printing URL/token or sending the webhook.
**Make:** generator/checker add a one-module `Ignore` error handler to both Facebook F1 downloads and Instagram I1. Since these fetches precede authorize, errors stop the branch before authorization with no retry or receipt. Updated draft is 23 modules; the imported scenario remains the previous 20-module version, so the TEST blueprint must be regenerated and re-imported. MK-12 is CONFIGURED pending Make History proof.
**Verify:** focused media/runner/command-factory/blueprint tests → 43 passed; full `tests/growth_engine` → 537 passed, 4 warnings; architecture tests → 2 passed; `py_compile` and `git diff --check` passed. No server process, Make UI, network endpoint or public post was touched. After deploying the code to `~/venho/gc2-src`, restart transient unit `growth-engine-api-test-src` to load the media handler change; no DB migration is needed. Re-import the updated blueprint separately to install F1/I1 error handlers in Make.

### GC2 TEST run 2: Make mapping key syntax (2026-11-10)
**Observed, supplied by Harry:** command `76b7ca61-a7d9-4dd9-82a0-dd425030324e` selected the `fb_hanoi` Router branch. HTTP 4 / F1 returned status `200`, `image/jpeg`, `private,no-store`, `cf-cache-status=BYPASS`, and output keys `statusCode` (number), lowercase `headers.*`, `fileName`, `fileSize`, `data`. The F1 filter blocked because Make parsed unquoted `headers.content-type` as subtraction; authorize and post modules did not run.
**Changes:** generator now uses backticks around the hyphenated `content-type` key in F1/I1 filters and authorize `media_report.content_type`; the static checker rejects any unquoted hyphen in a Make mapping and regression tests cover both accepted and rejected forms. TEST History records the Router selected one intended branch, not all three routes.
**Wrapper:** `run-test-command.py` now reports a safe refusal reason code for recognized `REFUSED` results and never echoes untrusted child text. A refused send is recorded as `NOT_SENT` and does not wait or retry. `TEST_CHANNEL_ALREADY_EXISTS` is surfaced distinctly.
**TEST handling:** runbooks require archiving/removing old TEST SQLite DB/WAL/SHM and media before recreating the TEST environment, preventing an existing TEST channel from blocking command creation. Keep the mode-600 server bearer handoff until TEST phase cleanup; remove Mac copies after each import and delete server/archive plaintext only at final cleanup. Setup script messaging matches this lifecycle.
**Verify:** focused blueprint/runner/setup tests → 40 passed; full `tests/growth_engine` → 542 passed, 4 existing warnings; architecture tests → 2 passed. Generated ignored `_incoming/make_test_import.json` and checker both report 23 modules, 3 routes, 97 mappings, secret scan clear; file mode `600`. Mapping audit found six backticked `content-type` references and zero unquoted references. `py_compile`, `bash -n`, and `git diff --check` passed. Ruff is not installed in the project environment. No Make/server/network operation or public post was performed.

### GC2 TEST run 3: apply Make receipt without starting scheduler (2026-11-10)
**Observed, supplied by Harry:** Make History run at 22:33 ICT for command `cd73c43a-1a28-4922-bd4d-29aeaf6d665d`, `fb_hanoi`, completed webhook → F1/HTTP 4 (`200 image/jpeg`) → authorize/HTTP 16 → Facebook Pages 3 → receipt/HTTP 17; 5 operations, 8 seconds. Router entered `fb_hanoi`; `ig_venho` and `fb_venho` were filtered. Facebook output ID was `1363761820162798_122106835935535879`. TEST DB initially showed command/execution `AUTHORIZED`, external outcome `None`, receipt `RECEIVED`, because no TEST worker had applied it yet.
**Implementation:** added `ProcessReceiptJobs` shared by the publish lane and `venho-engine apply-test-receipts`. The one-shot CLI command processes one due receipt-job batch only; it refuses unless `GE_ENV=test` and `GE_DB_PATH` resolves inside `~/venho/state/growth-engine-test`. It does not start a scheduler, outbox dispatch, timeout watcher or jobs lane. Runbook documents a transient `systemd-run --user --wait --collect` invocation and a read-only SQLite query requiring execution `REPORTED`, receipt `APPLIED`, `POST_CREATED`, and the stored Page TEST post ID matching Make History.
**Runner:** `run_test_command.py` now polls past `receipt_inbox=RECEIVED` until receipt/execution reaches a final state or the configured 120-second deadline, prints `receipt_inbox.processing_state`, and identifies final-state completion. No resend was added.
**Evidence ledger:** `make_capabilities.md` records MK-1 CONFIGURED and MK-4/5/6/9 PASS for the exercised Hanoi path, with explicit per-route limits; MK-2/3/7/8/10/11 remain NOT_RUN. Proposed next tests are IG publish, duplicate command (`ALREADY_AUTHORIZED`), broken image/F1 Ignore, and invalid command token. The actual receipt apply command has not been run against the server DB in this repository task; Harry's last DB snapshot still reflects `RECEIVED`.
**Verify:** focused receipt processor/CLI/runner tests → 36 passed; SQLite publish/receipt integration → 11 passed, 1 existing Starlette deprecation warning; full `tests/growth_engine` → 549 passed, 4 existing warnings; architecture tests → 2 passed. `py_compile`, CLI `--help`, and `git diff --check` passed. No TEST server DB, Make, network endpoint or new public post was operated by this repository task.

### GC2 TEST run 3 closure and next four cases (2026-11-11)
**Status:** run 3 closed by Harry: `apply-test-receipts claimed=1 completed=1`; receipt `APPLIED`; execution `REPORTED`; outcome `POST_CREATED`; stored ID `1363761820162798_122106835935535879` matches Make History. `outbox_commands.AUTHORIZED` is the intended terminal transport state after authorize; receipt lifecycle does not transition that row to `COMPLETED`. Master plan, receipt-store comment and SQLite integration assertion document this.
**Cases prepared, not executed:** added `run-test-case.sh` and `run_test_case.py` for (a) IG TEST `17841472240799413`, (b) exact envelope replay and `ALREADY_AUTHORIZED`/one post, (c) TEST signed-media signature failure and F1 `Ignore`, (d) invalid TEST command token and authorize rejection. Each creates a fresh TEST DB/channel, temporarily runs API on `:8023` with isolated env, requires `ACTIVE` + `GUI`, polls/applies any received receipt, writes a redacted result, and restores `growth-engine-api-test-src`.
**Make:** authorize requests now have terminal `Ignore` handlers so HTTP token rejection cannot proceed to posting or disable the scenario. The generated blueprint is 26 modules. Re-import is required before these four cases, especially case (d); verify TEST filters/destinations/connections/credentials and sequential + Immediately settings afterward.
**MK ledger:** MK-2/3 remain NOT_RUN. All four upcoming cases remain NOT_RUN pending Make History confirmation. Case (c) intentionally probes an HTTP media-capability failure, not JPEG decoder behavior.
**Verify:** focused TEST runner/blueprint/receipt tests → 40 passed, 1 existing Starlette deprecation warning; full `tests/growth_engine` → 556 passed, 4 warnings (Starlette deprecation + three existing unknown `slow` marks); architecture → 2 passed. Current ignored `_incoming/make_test_import.json` regenerated and checked: 26 modules, 3 routes, 97 mappings, secret scan clear, mode `600`. `py_compile`, `bash -n`, and `git diff --check` passed. No Make/server/network run or new TEST/public post was performed; four cases remain pending operator confirmations.

### GC2 Make TEST follow-up cases completed and production gates (2026-11-11)
**Evidence supplied by Harry, checked against Make History:** duplicate run 10:03:33 created one post (`…_122107375689535879`) and applied receipt; replay 10:03:46 ran three operations, authorize returned `ALREADY_AUTHORIZED`, Facebook Pages module was filtered, and DB had no second execution/receipt. Invalid token run 10:14:07: authorize HTTP 16 error caught → `Ignore`, no Facebook module, run Success and scenario stayed Active. Broken media run 11:32:45: F1 HTTP 4 error caught → `Ignore`, no authorize/post, scenario Active. Instagram run 12:16:35: I1/25 → authorize/26 → Instagram/6 (~9.7s) → receipt/27; media ID `18453049759135668`, execution `REPORTED`, receipt `APPLIED`.
**Make result at that point:** MK-2 PASS for the no-resume policy and duplicate stopping before post; MK-3 was PARTIAL until the later read-only setting inspection recorded below as PASS. MK-7/8 PASS for caught pre-publication errors and active scenario; MK-10 PASS for Meta fetching signed IG media and receiving an Instagram media ID. MK-1 was CONFIGURED before the sequential History run; the later Stage B closeout records PASS. MK-11 remains NOT_RUN (container versus publish-stage errors not injected). MK-9 is partial because `fb_venho` is not run. MK-12 is partial: Hanoi F1 error passed; IG I1 and FB Ven Ho F1 error handlers were not fault-tested. The runner now accepts a `PASS` response case-insensitively; History evidence supersedes the earlier `PENDING_REVIEW` summary.
**API restore bug:** previous `finally` called only `systemctl --user start growth-engine-api-test-src`, which does not recreate a transient unit after systemd unloads it. It now tries `restart`, recreates the transient API with the original TEST env and command if needed, falls back to `start`, and requires readiness on `127.0.0.1:8023` before `test_api_restore=PASS`. Added tests for unloaded and loaded transient units.
**TEST cleanup policy:** runbook now stops `growth-engine-api-test-src`, deletes current and archived bearer handoff files, keeps the TEST env only while more TEST cases need it, and retains public test posts until History evidence is saved/reviewed; deletion after review is a manual operator decision.
**Remaining gates before production:** deploy v2 with `DISABLED` and migrate the production DB; provision `growth-api.venhohotel.com` plus production Cloudflare Access; provision Meta read tokens; configure and verify Telegram plus heartbeat; retire legacy filter/scenario per `retire_legacy.md`; verify remaining TEST route `fb_venho` and MK-11 where needed. Open production routes only in order `fb_hanoi` → `fb_venho` → `ig_venho`, verifying each destination before opening the next.
**Verify:** focused runner tests → 7 passed; full `tests/growth_engine` → 559 passed, 4 existing warnings; architecture → 2 passed. Make blueprint checker → 26 modules, 3 routes, 97 mappings, secret scan clear. `py_compile`, `bash -n`, and `git diff --check` passed. Systemd restore behavior is covered with fakes for both unloaded and loaded transient units; no server restart or Make action was performed in this repo task.

### GC2 decision and MK follow-up — 2026-11-11
**DR-GC2-D02:** Harry confirms each Facebook slot intentionally posts to both production Pages. It must create separate `fb_hanoi` and `fb_venho` deliveries/commands/receipts/verifications, with the same approved Facebook caption and image bytes. The existing four-slot cadence remains; two Pages each receive four posts per week. `EnsureSlots` covers enabled targets per slot; grouped approval supports both Facebook deliveries plus Instagram atomically without dispatch. Production channels are still disabled.
**Make inspection:** MK-3 = PASS. Read-only inspection found no retry setting on Facebook Pages 3 or Instagram 6; advanced settings only show a blank Publish date. All error routes use Skip (discard bundle and continue scenario); no Retry/Break/Resume; Store incomplete executions = No.
**Instagram:** Make module says the Instagram API cannot fetch even public Google Drive files. Signed media URLs are mandatory in production. Configured IG output is JPEG, ≤5 MiB and exact 4:5, within Make's ≤8 MB and 4:5–1.91:1 bounds.
**Sequential case:** at the time of this entry the runner was implemented but Make History evidence had not arrived. This status is superseded by the MK-1 PASS evidence in the Stage B closeout below.

### GC2 Stage B preparation and MK-1 closeout (2026-11-11)

**MK-1:** Harry supplied Make History evidence for the sequential case: two distinct `fb_hanoi` webhooks sent 300 ms apart; run 1 started 15:22:30 ICT (7 s), run 2 started 15:22:39 after run 1 ended (5 s); different post IDs `…_122107590483535879` and `…_122107590693535879`; both receipts APPLIED. MK-1 is PASS. MK-1…MK-6 are PASS and meet the Make capability gate for `LIVE_MANUAL`; production runtime remains DISABLED until staged cutover. `fb_venho` route and MK-11 are checked when their channels open.

**Production cutover runbook:** added `runbooks/production_cutover.md` with sequenced commands, expected results, stop conditions and rollback for DB/runtime deploy, production tunnel/Access, secrets, Make import after Harry approval, four-slot cadence/group approval, staged route opening and TEST cleanup. The production port is fixed by the unit/inventory at 8021; 8022 concierge and 8023 TEST remain separate.

**Fail-closed tooling:** added `initialize-production-controls.py` (DISABLED + global pause + audit), `configure-production-cloudflared-ingress.py` (backup, candidate validation, atomic install, exact `cloudflared.service` restart and automatic restore), `setup-production-make-bearers.py` (three bearer hashes, capability key and mode-600 handoff), and `manage-production-channels.py` (verified manifest provisioning disabled; audited channel toggles enforce Page IDs, paused runtime and opening order). The Make blueprint generator now accepts `--environment production`, writes the three fixed production IDs and production filters, and retains the existing connection mappings from the export.

**Open human gates:** production `channels.yaml` still has unverified Make scenario/connection and Graph metadata; verify/fill it before provisioning. Fill production env secrets before the first `deploy-release.sh`, because `doctor --pre-switch` requires them. Create production DNS/Access in the Cloudflare dashboard, and approve the production Make import. No server, Make, Meta, Telegram or Cloudflare settings were changed in this task; no production post was sent.

**Verify:** new utility fakes + Make generator tests → 18 passed. `compileall` and `git diff --check` passed. No production/config state changed.

### Production DISABLED service, doctor and Meta expiry follow-up (2026-11-11)
**Observed, supplied by Harry:** production release `7eedfa3`; fresh GC2 DB schema 9; runtime `DISABLED`, global pause on; all three channels provisioned disabled; API and `publish`/`jobs` workers active. `systemctl --user enable` failed because both unit files lacked `[Install]`.
**Changes:** API and templated worker units now install under `default.target`; runbook verifies `loginctl` linger and enables explicit `publish`/`jobs` instances. `systemd-analyze --user verify` is after release deploy, when `current/.venv` exists. Doctor reads `/proc/locks` and matches the exclusive lock owner PID to the active systemd publish unit MainPID: the valid sole unit is PASS, an unowned/second process is FAIL, and ownership unavailable is WARN.
**Meta expiry and Telegram:** production `doctor` reports WARN when either IG long-lived-token or Data Access expiry is missing/invalid or within 14 days. The publish worker checks every six hours and enqueues deduplicated durable Telegram notices per expiry/date; running doctor also queues any due notice. `GE_META_TOKEN_EXPIRY_IG_VENHO` is estimated as `2027-01-10`; `GE_META_DATA_ACCESS_EXPIRY_IG_VENHO` is provisionally `2027-02-09` (90-day estimate). Confirm both against Access Token Debugger and correct the server env if different. Runbook and env template require production bot `@venho_growth_alerts_bot`, never `@Venhohotel_bot`.
**Deployment:** these fixes are not live on the running server. Deploy a new release after push; no DB migration is added, and the current schema 9 DB/bootstrap/channel records should be preserved. After deploy, enable the three units and confirm linger. No server, Telegram, Meta, Make or Cloudflare operation was run here.
**Verify:** `tests/growth_engine` → 589 passed, 4 existing warnings; architecture → 2 passed; `compileall` and `git diff --check` passed. Added coverage for both lock ownership cases, expiry threshold/dedup notification, worker interval, install sections, and linger runbook check.

### Production cutover plan and Make secret tooling (2026-11-12)
**Status:** PREPARED — no Make/server action performed.
**Decision:** Harry selected hard cutover A; T−0 Monday 16/11/2026 09:00 ICT. Rollout publishes Hanoi first; `fb_venho` and `ig_venho` are prepared for the next scheduled slot Wednesday 18/11. Slot 16/11 is a documented transition exception: it is not a two-Page Facebook post.
**Readiness:** production content generation/group approval has not been run on the empty schema-9 database. Existing legacy importer does not restore approvals and is not production-safe; use newly generated v2 delivery/revisions and approve through VENHO OS v2.
**Changes:** added explicit `--rotate-existing` to production bearer provisioning and a stdlib production Make filler. Rotation writes hashes to `GE_SERVICE_TOKENS`, mode-600 plaintext handoff only, and the filler prompts hidden for production Cloudflare Access values, substitutes the production base URL, checks the route-to-bearer mapping and writes ignored mode-600 `_incoming/make_production_import.secret.json`. Runbook has dated T−3/T−1/T−0/T+next-slot steps and safe rollback gates.
**Outstanding gate:** `retire_legacy.md` requires P9-T04 evidence of ≥8 slots, ≥16 target outcomes, ≥14 days stable, and a restore rehearsal. With the reported fresh production DB and DISABLED runtime, that evidence is not established; 16/11 is conditional and must be deferred if the gate has not already passed. Server release `7eedfa3` must receive the systemd/doctor/token-expiry fixes before any cutover.
**Verify:** `uv run --no-sync pytest -q tests/growth_engine` → 593 passed, 4 existing warnings; architecture → 2 passed; changed-script `compileall`, production filler `--help`, and `git diff --check` passed. No Make/server/Meta/Cloudflare action was performed.
