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
**Preflight gate:** current `channels.yaml` still has `page_test.graph_api_version: REQUIRED_FROM_P0`. The runner refuses before prompting for the webhook or modifying env until that value is verified/configured; no command was created and no public post was attempted.
**Verify:** fake orchestration/SQLite tests → 9 passed; `py_compile`, `bash -n`, and `git diff --check` passed. No server, webhook, Make or public-page request was made by this code task.
