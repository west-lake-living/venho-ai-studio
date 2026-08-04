# VENHO AI STUDIO — Task Memory
**Repo:** `venho-ai-studio` · **Workspace:** THE WEST LAKE LIVING
**Cập nhật:** 2026-07-16 (AI Studio v1.5 closeout audit after Phase 7 QA/DOC) · **Đọc bởi:** AI Engine, Claude Code sessions

---

## 1. Mục tiêu hệ thống

Biến ảnh thực và Brand DNA thành nội dung marketing chất lượng cao — hoàn toàn trên nền tảng tri thức chuẩn hóa, có approval gate trước khi phân phối, không tự publish khi chưa được duyệt.

Pipeline tổng quát:

```
Ảnh thực → [M01] DNA JSON → [M02] Prompt → [AI Engine ngoài tạo ảnh/video] → [M03] Validate
                           → [M05] Content prose → [M03] Validate
                           → [M06] Video storyboard → [AI Engine ngoài render video]
[M09] nhận goal tự nhiên → lập plan/risk/module requests → [M04] điều phối + approval gate → [M07] Publishing Gateway dry-run/publish receipt → [M08] Analytics Feedback
[M10] VENHO OS Home Workspace đọc artifacts/config của M01-M09 → hướng founder tới đúng việc cần làm ngay bây giờ
```

---

## 2. Kiến trúc tổng thể

### Growth Agent v3.0 Phase 1 Baseline (2026-08-03)

Phase 1 is complete in `venho-ai-studio`.

- Contract-first baseline is in `contracts/` with 15 schemas and pass/fail fixtures.
- Growth policy registry is in `config/projects/venho_hotel/growth/`.
- Research policy registry is in `config/projects/venho_hotel/research/`.
- Durable local state foundation is `shared/jobs/` + `shared/budget/` using SQLite.
- Real providers remain feature-flagged off by default; tests stay offline/mock.
- Full verification after Phase 1: `465/465` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 Phase 1.5 + Phase 2 Baseline (2026-08-03)

Phase 1.5 and Phase 2 are complete in `venho-ai-studio`.

- Research OS now supports validated vault frontmatter, R0/R1 collection, R2 synthesis, NotebookLM manual handoff verification, and controlled R2 -> R3 promotion.
- R2-T remains context-only and cannot become R3.
- Stale R3 facts can be detected and can revoke approvals that reference expired facts.
- M01 Knowledge Facts has a seed loader and resolver with validity-window handling.
- M03 Claim Validator blocks unsupported critical claims and distinguishes missing vs expired evidence.
- M09 can compile and lock CreativeBriefs only when proof points resolve to active R3 facts.
- M05 can generate three distinct mock/provider candidates and select one using a rubric.
- Full verification after Phase 2: `477/477` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 Phase 3 Baseline (2026-08-03)

Phase 3 is complete in `venho-ai-studio`.

- `agent_studio/growth/scenario_registry.py` resolves Visual DNA v2.7 scenario profiles from `config/projects/venho_hotel/growth/scenario_registry.yaml`.
- `image_studio_runtime` now creates immutable image run folders with complete paid manifests, mock-provider artifacts, DNA/reference trace, and no overwrite path.
- Paid image policy is enforced: maximum one paid generation plus one targeted repair; after that the package remains `NEEDS_REVIEW`.
- 429/5xx provider failures back off without creating any variant artifact.
- M03 alignment and derivative validators cover required-subject omission, forbidden entities, alignment score, crop safety, and OCR/critical text gates.
- Full verification after Phase 3: `482/482` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 Phase 4 Baseline (2026-08-03)

Phase 4 is complete in `venho-ai-studio`.

- M04 approval snapshots now bind exact package versions by checksum: copy, asset, validation snapshot, fact versions, and brief version.
- Dispatch is blocked if any approved package version changes after approval; Final Review state can present approved/pending/blocked without duplicating M03 logic.
- M07 keeps a local `PublicationRegistry` for idempotent publication reservation and status updates.
- Make.com remains only an M07 adapter; `GATEWAY_ACCEPTED` is not published.
- Callbacks require signed payloads and a post ID for `PUBLISHED`; reconciliation can close unknown states with proof.
- Duplicate chaos test reserves exactly one publication for repeated idempotency key/platform attempts.
- Full verification after Phase 4: `493/493` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 Phase 5 Baseline (2026-08-03)

Phase 5 is complete in `venho-ai-studio`.

- `shared/jobs/JobStore` supports idempotent dispatch triggers, worker heartbeat/lease extension, expired lease recovery, retryable-failure requeue, and terminal failure after max attempts.
- `shared/jobs/scheduler.py` can enqueue daily dispatch idempotently and emit structured late-run alerts.
- `shared/budget/BudgetLedger` now supports policy evaluation, budget override audit records, and paid-call reservation through `BudgetPolicy`.
- Budget policy alerts fire at 70/85/100%; 100% cap blocks paid calls unless an override with reason and approver is recorded.
- Full verification after Phase 5: `498/498` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 Phase 6 Baseline (2026-08-03)

Phase 6 is complete in `venho-ai-studio`.

- M08 attribution resolves inquiries through `utm_content=publication_id`, direct/assisted windows, policy dedupe fields, and SHA-256 pseudonymized contacts.
- Metric observations preserve semantic state: real value, zero, null, and provider-unavailable are not collapsed together.
- Sample metrics are asserted against raw source values before downstream reporting.
- Meta Insights remains feature-flagged off; mock metrics adapter is still the default in tests and local execution.
- Analytics collection windows are now `1h`, `24h`, `72h`, `7d`, and `28d`.
- M10 content performance projection reads M08 snapshot/score outputs only and does not recalculate analytics.
- Full verification after Phase 6: `504/504` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 Phase 7 Baseline (2026-08-03)

Phase 7 is complete in `venho-ai-studio`.

- `strategy_memory/` now supports Bayesian-smoothed QBSR pattern inference with confidence, scope, evidence, limitations, expiry, and approval-gated promotion.
- Strategy memories from insufficient samples return `INCONCLUSIVE` and cannot be promoted.
- Weekly strategy briefs are advisory-only, `pending_approval`, and suppress recommendations if QBSR drops below guardrail.
- M08 can generate a written research question into Research OS through `M08SignalBridge`, closing the analytics -> research loop.
- Every recommendation in the weekly brief must carry evidence and limitations.
- Full verification after Phase 7: `510/510` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 Phase 8 Baseline (2026-08-03)

Phase 8 is complete in `venho-ai-studio`.

- `controlled_rollout/` evaluates versioned golden scorecards, confirms 90-day baseline/candidate metrics readiness, manages rollout stage decisions, enforces rollback sequencing, and validates rollout runbook docs.
- P8 scorecard requires `>=9.3/10` on a versioned golden set; duplicate publication and unplanned empty days remain hard gates.
- Rollout stage progression is `shadow -> pilot_25 -> pilot_50 -> pilot_100`; human approval remains required, and trend lane is blocked from auto-approval.
- Rollback code requires dispatch disabled first, forward-only migrations, compatible reads, and immutable approved artifacts.
- First `_productize` skill is present: `.claude/skills/_productize/hotel-content-engine/SKILL.md`; `productize/hotel_content_engine.py` runs for hotel #2 from config only without core changes.
- Runbook docs are present under `docs/growth/controlled_rollout_runbook.md` and `docs/growth/eval_golden_sets.md`.
- `pyproject.toml` now packages `controlled_rollout*`, `productize*`, and `strategy_memory*`.
- Full verification after Phase 8: `517/517` AI Studio tests pass with 0 API calls.

### Growth Agent v3.0 QC Pass on Phase 1–3 (2026-08-03)

Senior QC review of all Codex-authored Growth Agent code. Fixed and regression-tested:

- `JobStore.claim()` was SELECT-then-UPDATE (non-atomic across two implicit transactions) — two concurrent workers could claim the same job. Now a single atomic `UPDATE ... RETURNING`.
- `publishing_gateway/callback_receiver.py` signed only `body`, leaving `timestamp` unauthenticated — defeated the "replay window" guard it was supposed to enforce. `timestamp` is now part of the signed message.
- `fact_key` / `rs_id` / `domain` / `title` / `topic_slug` were used unvalidated as filesystem path components (path traversal risk) in `FactStore`, `NotebookLMHandoff`, `collect_source_note`, `collect_structured_note`, `synthesize_notes`. Added `shared/security.py::ensure_safe_slug()` at each sink.
- `growth_orchestrator/` and `research_engine/trend_radar/` are untested scaffolding (stub bridges, e.g. `M07PublishingBridge` always fakes `GATEWAY_ACCEPTED`) — not yet wired to the real M03/M05/M07/M08 pipelines despite `pyproject.toml` exposing `venho-growth` as a live CLI entrypoint. Do not treat as production-ready; next phase must wire these bridges to the real modules instead of reimplementing simplified logic.
- Verify: `488/488` AI Studio tests pass (482 prior + 6 new in `tests/test_growth_qc_hardening.py`), 0 API calls, `compileall` clean.

### Growth Agent v3.0 QC Pass on Phase 4–8 (2026-08-03)

Senior QC review of all Codex-authored Phase 4–8 code (job/budget extensions, publication registry, approval snapshot, controlled rollout, strategy memory, productize, analytics attribution). Fixed and regression-tested:

- `publishing_gateway/publication_registry.py` did an unlocked JSON load → modify → save in `reserve()`/`update()` — two concurrent callers (retried dispatch vs. inbound webhook) could both read stale state and the second writer would silently clobber the first, breaking the idempotency guarantee the registry exists for. The existing "duplicate chaos" test only ran sequentially in one thread, so it never caught this. Fixed with an `fcntl.flock` exclusive lock around both methods; added a real 20-thread `ThreadPoolExecutor` regression test in `tests/test_growth_qc_hardening.py`.
- Everything else in Phase 4–8 reviewed clean: `JobStore` heartbeat/lease-recovery/retry-requeue extensions stayed single-atomic-statement SQLite (consistent with the earlier `claim()` fix), `BudgetLedger`/`BudgetPolicy` SQLite-backed with no cross-process race, `approval_snapshot.py` pure deterministic logic, `controlled_rollout/*` and `strategy_memory/*` pure functions, and `analytics_feedback/research_question_generator.py` already reuses `shared/security.py::ensure_safe_slug()` from the Phase 1–3 QC pass.
- `growth_orchestrator/` re-confirmed still zero references anywhere (`grep -rln growth_orchestrator` outside its own package) — unchanged from the prior QC finding, no new risk from Phase 4–8.
- `productize/hotel_content_engine.py` builds a path from a `project` string with no `ensure_safe_slug` guard, same shape as the fixed sinks — left as-is because `project` is currently a deploy-time config identifier, not attacker-controlled input; revisit if `project` ever becomes agent-/user-suppliable.
- Verify: `518/518` AI Studio tests pass (517 prior + 1 new), 0 API calls, `compileall` clean.

### Growth Agent v3.1 — Delta vs v3.0 (2026-08-03)

Read `docs/Content agent/VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md` and diffed it against everything Codex already built for v3.0. Most of v3.1's architecture already existed (contracts, jobs, budget, facts, image runtime, approval, scheduler, analytics, strategy memory, controlled rollout, and `research_engine/trend_radar/` with a real brand-safety gate + relevance scorer + 5 empty collector stubs). The actual delta implemented this pass:

- **Cadence 4 posts/week (TR-D2, PB-001):** `cadence_policy.yaml` v1->v2 -- removed the A(3)->B(5)->C(7) ramp entirely, fixed Mon/Wed/Fri (regular) + Sat (special) + Tue blog SEO. New `growth_orchestrator/domain/publishing_slot.py::PublishingSlot` state machine (`OPEN->DRAFT_ASSIGNED->PENDING_APPROVAL->FILLED->DISPATCHED->COMPLETED`, plus `EVERGREEN_FALLBACK` and a `MISSED` path that asserts the evergreen pool was actually exhausted first). New `growth_orchestrator/application/manage_slots.py::generate_slots()` -- deterministic, idempotent slot IDs from `(date, weekday)` so re-running over an overlapping horizon is safe.
- **Slot-based runway (PB-003):** `queue_policy.yaml` `runway_days` -> `runway_slots` (healthy>=6, warning 4-5, critical 2-3, empty 0-1 per §9.2); `manage_queue.runway_status()` updated, with a fallback read of the old `runway_days` key in case anything else still uses it.
- **Special lane T3->T7 with mandatory fallback (PB-008):** `growth_orchestrator/application/special_lane.py` -- priority order seasonal_nature > cultural_event (only if `verified_by_human`) > lifestyle_trend > feature_story (mandatory fallback, raises if absent -- this is what stops the Saturday slot from ever going empty or bending brand safety to force a trend). `special_lane_timeline_state()` enforces the hard Friday 20:00 cutoff -> `fallback_evergreen` if not yet approved.
- **Pre-flight check (PB-005):** `growth_orchestrator/application/preflight.py::run_preflight_check()` -- fact expiry, approval validity, asset reachability/hash match, event `verified_by_human` + not-yet-passed, weather R2-T not expired. Returns every failing reason, not just a boolean.
- **Weather signal is R2-T only, never a claim (§5.5, §6.6):** `research_engine/trend_radar/domain/weather_signal.py::WeatherSignal.fact_key` is typed `Literal[None]` -- Pydantic itself rejects any attempt to set it, enforced at the type level rather than only in a validator function. `contracts/weather_signal.schema.json` mirrors this with `fact_key: const null`. `scan_weather()` always derives `expires_at` from `weather_policy.yaml["expiry_hours"]`, never from the provider payload, so a provider can't hand back a signal that outlives policy. `weather_api.py` collector is an empty stub matching the existing 5.
- **`shared/notify/telegram.py` (IN-D4):** `MockTelegramNotifier` (default everywhere) + real `TelegramNotifier` requiring an injected `http_post` (never called anywhere in this repo). `send_alert()` resolves severity/channel from `shared/notify/alert_policy.yaml`, raises on an unknown event name.
- **`publishing_gateway/adapters/zalo_oa.py` (IN-D5):** mirrors `make_gateway.py` exactly -- disabled by default returns `DISABLED`, enabled returns `GATEWAY_ACCEPTED` (never `PUBLISHED`).
- **New `infra/` package (§10, IN-001/002/003):** `heartbeat.py` (payload builder + injected-`http_post` sender + staleness check), `deadman_config.yaml` (5-min heartbeat / 15-min stale / 09:15-09:30-10:00 dispatch-check thresholds), `cloud_fallback/export_approved.py` (only exports packages already `approval_status: approved`, HMAC-signs, and -- critically -- has no parameter or code path that can set `approval_status`, so the security invariant "cloud never creates an approval" is structural, not just documented), `backup.sh`, 5 `launchd/*.plist` templates, `setup_macmini.md` runbook. `infra*` added to `pyproject.toml` package discovery.
- **Contracts:** added `weather_signal.schema.json` + `publishing_slot.schema.json` + fixtures -> 17 schemas total. (The plan's own §5.10 header says "16" but its enumerated list has 17 entries -- a typo in the master plan itself, not a miscount here.)
- New test file `tests/test_growth_v3_1_cadence_infra.py`, 31 tests covering every item above.
- **Explicitly NOT done this pass (needs Harry, outside code scope):** buying/configuring a physical Mac Mini M4, running real `pmset`/`launchd`/Tailscale, registering real API keys (Tavily, Exa, Weather API, YouTube Data API, Telegram bot token, Zalo OA app), standing up a real healthchecks.io or Make.com data-store endpoint for heartbeat/cloud-fallback. Everything above is mock/stub/flag-off until those exist.
- Verify: `549/549` AI Studio tests pass (518 prior + 31 new), 0 API calls, `compileall` clean.

### Growth Agent v3.1 — Real provider wiring: Tavily + Telegram + Zalo token refresh (2026-08-03)

Harry now has `TAVILY_API_KEY`, `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`, `ZALO_ACCESS_TOKEN` + `ZALO_REFRESH_TOKEN` + `ZALO_APP_ID` + `ZALO_APP_SECRET` in `.env.local`. **Security gap found and fixed immediately:** `.env.local` was never actually covered by `.gitignore` (it only matched the literal name `.env`) -- confirmed via `git log` it was never committed, but the next `git add -A` would have leaked all 5+ secrets. Fixed `.gitignore` to `.env.*` + `!.env.example`. Also renamed 2 typo'd keys Harry had pasted in (`zalo_appp_id`, `app_secret_key`) to `ZALO_APP_ID`/`ZALO_APP_SECRET` -- renamed the key only, never read/echoed the actual secret values into the transcript.

- **`shared/http.py` (new):** `urllib_post`/`urllib_post_form`/`urllib_get` -- stdlib-only transport (`urllib`), no new dependency (repo had zero HTTP libraries before this). Every adapter takes an injectable transport param (`http_post=None` -> defaults to the real one); tests always inject a fake, so the suite stays at 0 API calls even though real network code now exists.
- **`shared/notify/telegram.py`:** `TelegramNotifier` now defaults `http_post` to the real `urllib_post` instead of requiring injection; added `telegram_notifier_from_env(env)` reading `TELEGRAM_BOT_TOKEN`, raises `KeyError` if missing.
- **`research_engine/trend_radar/collectors/tavily_search.py`:** added `collect_tavily_search(query, api_key=..., http_post=...)` -- real call to `https://api.tavily.com/search`, normalizes into R0 entries (`id`/`title`/`source_uri`/`snippet`/`relevance_hint`). Classification into geographic/thematic/actionability/brand_safety_category deliberately stays downstream in `scan_trends`, not guessed here. Old `collect_tavily_search_stub()` left in place.
- **`publishing_gateway/adapters/zalo_oa.py`:** added `refresh_zalo_access_token(app_id, app_secret, refresh_token)` -- correct Zalo OAuth v4 shape (`POST https://oauth.zalo.me/v4/oa/access_token`, `x-www-form-urlencoded` body, `app_secret` in a `secret_key` header, not JSON/query string -- this project had no form-encoded POST helper before, added `urllib_post_form`). **`ZaloOAAdapter.send()` real path intentionally NOT implemented** -- Zalo OA has no public "feed post" API like Facebook Pages; real sending targets a specific follower `user_id` (7-day consultation window) or an approved broadcast template. Guessing the endpoint/payload risks burning real OA quota or messaging the wrong audience -- left as a documented open question for Harry: is Zalo meant as an internal alert channel (like Telegram, to Harry's own `user_id`) or a guest/follower content channel?
- **No feature flags flipped** (`trend_radar_enabled`, `zalo_enabled`, `real_meta_insights_enabled`, etc.) -- real keys now exist but turning a flag on means real API calls / real messages start firing, left for Harry to decide after review.
- New test file `tests/test_growth_v3_1_real_providers.py`, 8 tests -- Telegram default transport identity check + correct URL/payload via injected fake + `from_env` missing-token raises; Tavily missing-key raises + result normalization; Zalo refresh missing-credential raises + correct form-body/header shape.
- Verify: `557/557` AI Studio tests pass (549 prior + 8 new), 0 API calls, `compileall` clean.

### Growth Agent v3.1 — Zalo OA publish via Make.com webhook (2026-08-03)

Harry's integration decision: `ZaloOAAdapter` does not call the Zalo API directly -- it fires a webhook to Make.com, and Make's own HTTP / Custom API Request module (Harry configures this in the Make UI) makes the real Zalo OA call right after "Approve" is clicked on VENHO OS Dashboard. This resolves the endpoint ambiguity flagged in the prior pass -- Zalo OA has no public feed-post API, so picking the exact endpoint (broadcast/article/consultation message) is Harry's call inside Make.com, not a guess in code.

- **`publishing_gateway/adapters/zalo_oa.py`:** `ZaloOAAdapter` gained `webhook_url`, `webhook_secret` (optional, HMAC-SHA256 signs an `X-Venho-Signature` header, same convention as `approval_verifier.build_approval_signature`), `access_token_provider` (called once per `send()` to fetch a live Zalo token, meant to wrap `refresh_zalo_access_token` -- keeps all OAuth refresh logic in Python instead of duplicating it in Make.com), and `http_post` (injectable). **No `webhook_url` -> old mock behavior unchanged**, so the existing `tests/test_growth_v3_1_cadence_infra.py` assertions still pass untouched. With `webhook_url` set, POSTs `{publication_id, idempotency_key, platform: "zalo_oa", content, access_token?}` to Make.com; an `HttpError` from the webhook returns `GATEWAY_ERROR` rather than raising, consistent with the existing accept-async-then-callback pattern in `callback_receiver.py`.
- `.env.example`: added `ZALO_APP_ID`/`ZALO_APP_SECRET` (missed in the prior pass) + new `MAKE_ZALO_WEBHOOK_URL`/`MAKE_ZALO_WEBHOOK_SECRET`.
- 4 new tests in `tests/test_growth_v3_1_real_providers.py`.
- **Real remaining gap, not glossed over:** `growth_orchestrator/bridges/m07_publishing_bridge.py::M07PublishingBridge.dispatch()` is still a pure stub that returns a fake `GATEWAY_ACCEPTED` -- it does not call `ZaloOAAdapter` or any adapter, and there is no platform-based routing yet. The "Approve" button itself lives in `venho-os` (a separate TS/Next.js repo) and it's unconfirmed how/whether it calls into this Python M07 bridge at all. So "clicking Approve auto-posts to Zalo" is NOT true end-to-end yet -- only the adapter's webhook-trigger capability is real and tested. No Make.com scenario has been created/tested against a live `MAKE_ZALO_WEBHOOK_URL` either.
- Verify: `561/561` AI Studio tests pass (557 prior + 4 new), 0 API calls, `compileall` clean.

### Content Studio — Zalo platform rules + dedicated hotline CTA (2026-08-03)

Harry: Vietnamese Zalo users want short, direct copy with a clear contact/booking line -- specifically "Liên hệ Hotline/Zalo 0936871234 để đặt phòng view Hồ Tây ngay hôm nay." Instead of a one-off manual instruction to an AI agent (easy to forget, inconsistent run to run), wired this into config + the M02 Prompt Studio pipeline so it's deterministic and test-covered -- consistent with the project's config-first principle.

- **`content_studio/schemas/content_request.py`:** added `"zalo_post"` to the `ContentType` Literal -- `ContentRequest` could not represent Zalo at all before this.
- **`content_studio/content_engine.py::_builder_for`:** routes `zalo_post` to `build_social_draft` (same social group as facebook/instagram/threads/tiktok).
- **`config/projects/venho_hotel/content/platform_rules.yaml`:** added `zalo:` -- `max_length: 300` (shorter than `threads`'s 500, per "shorter than Facebook"), `max_hashtags: 0` (Zalo culture doesn't hashtag-search like FB/IG).
- **`config/projects/venho_hotel/prompt_rules.yaml`:** added `platform_cta_overrides.zalo` with Harry's exact CTA text + phone number. Deliberately placed in the prompt layer, not `content/` -- `load_content_config()` already hard-forbids a `content/cta_rules.yaml` existing (raises `ContentConfigError`), so CTA wording has to live here.
- **`prompt_studio/builders/content_prompt_builder.py`:** `render_final_prompt()`/`build_content_prompt()` gained an optional `platform` param; the `Call-to-action:` line in `final_prompt` now checks `platform_cta_overrides[platform]` first, falling back to the global `cta_rule` -- fully backward compatible (omitting `platform` reproduces the old behavior exactly, no existing test needed changes).
- **`content_studio/prompt_bridge.py`:** now passes `platform=request.platform` (existing derived property) through to `build_content_prompt`.
- Checked `validator_studio/content_validator.py::_score_cta` -- it scores on generic `CTA_TERMS` keywords ("liên hệ", "đặt phòng"), not an exact match against `cta_rule`, so the new Zalo CTA text scores correctly without touching the validator.
- 3 new tests: 2 in `test_content_prompt_builder.py` (platform="zalo" gets the override + phone number; other platforms keep the generic rule, no phone number), 1 end-to-end in `test_content_studio.py` (generating a `zalo_post` produces empty hashtags, a shorter `max_length` than facebook, and the phone number in `final_prompt`).
- **Scope note:** this only affects the new M02/M05 content-generation layer (Growth Agent v3.1 pipeline, this repo). The older `VenHoSocialManager` system (separate `venho-os` repo, GitHub Actions T2/T4/T6 for FB/IG/Threads) is a different pipeline that does not read `platform_rules.yaml`/`prompt_rules.yaml` here -- applying the Zalo CTA there would need a separate change in `venho-os`.
- Verify: `564/564` AI Studio tests pass (561 prior + 3 new), 0 API calls, `compileall` clean.

### Module Roles (KHÔNG chồng lấn)

| Module | Vai trò | KHÔNG làm |
|--------|---------|-----------|
| **M01** Knowledge Studio | Ảnh → DNA JSON (structured observation) | Viết content, tạo prompt |
| **M02** Prompt Studio | DNA → Prompt JSON (structured, deterministic) | Gọi AI viết prose |
| **M03** Validator Studio | Kiểm output (ảnh, prompt, face, content) | Tạo output |
| **M04** Automation Studio | Điều phối M01–M03 thành workflow | Chứa business logic module khác |
| **M05** Content Studio | Thực thi content-prompt M02 → prose | Dựng prompt lại, tự parse DNA |
| **M06** Video Studio | DNA + character → storyboard + engine prompt package | Render video, publish video |
| **M07** Publishing Gateway | Phân phối package đã duyệt, dry-run/publish receipt cho M08 | Tạo/sửa content, tự quyết giờ đăng, phân tích performance |
| **M08** Analytics & Feedback Loop | Đo metrics, score performance, sentiment guardrail, sinh feedback advisory | Đăng bài, tự sửa Knowledge/Content Strategy, tự apply advisory |
| **M09** Agent Studio | Cognitive interface: goal → request validation → persona/context → task plan/risk/module requests qua M04 | Tự publish, tự sửa Knowledge, tự tính metrics, gọi M07 trực tiếp |
| **M10** VENHO OS Home Workspace | Founder-first UI đọc M01-M09 artifacts/config, hiển thị Today's Focus, Current Work, Needs Review, Ready to Publish, Quick Actions, Recent Activity | Lưu DB nghiệp vụ, tính lại score/HMAC, build prompt/ModuleRequest, render/upload/publish, đưa raw JSON/pipeline/analytics/system health lên Home |

### Nguyên tắc bất biến

1. **M02 dựng prompt, M05 thực thi** — không hoán đổi vai.
2. **M04 chỉ điều phối qua adapter** — không import sâu logic module con.
3. **Archive thuộc module con** — M04 không overwrite file production.
4. **Draft/approval first** — mọi output là draft cho tới khi M04 approval hợp lệ; M07 chỉ thực thi package đã duyệt.
5. **0 API call trong tests** — tất cả offline/mock.
6. **Config-first** — workflow/rule khai báo YAML, không hard-code.
7. **Project-agnostic core** — Ven Hồ là project đầu tiên, không phải core.
8. **Kết thúc task = cập nhật memory/status** — khi người dùng nói "kết thúc task", Codex tự động cập nhật `task_memory.md` và `task_status.md` trước khi chốt.
9. **M10 presentation-only** — Operating Center degrade bằng advisory khi module con thiếu artifact; không làm sập toàn UI và không sao chép business logic.
10. **M10 Home Workspace v1.0** — Home trả lời “What should I do now to move my business forward?”; Home chỉ có Today's Focus, Current Work, Needs Review, Ready to Publish, Quick Actions, Recent Activity. Pipeline nằm ở Workbench; raw JSON/token/cache/runtime internals nằm trong Settings, không nằm ở Home.
11. **M10 action-first** — Status quan trọng phải dẫn tới contextual action label/button; button MVP chỉ điều hướng/placeholder, không chạy live workflow ngầm.
12. **M05 real generator = claude_longform_generator** — inject qua `generator_fn` param; `None` → template mock (tests an toàn); chỉ dùng cho non-social (blog/OTA/FAQ/email/website); social posts thuộc VenHoSocialManager.
13. **VenHoSocialManager QC gate (2026-07-15)** — `generate_image_with_qc()` dùng GPT-4o-mini vision (score 1–10, ngưỡng 7); max 2 retry với tightened prompt; fail sau retry → skip Drive+Make.com, gửi `send_qc_alert()`; không thay đổi social posting logic.
14. **AI Studio v1.5 Phase 0 baseline (2026-07-16)** — historical baseline: AI Studio `424/424` pass; VenHo OS `54/54` pass + build pass; roadmap v1.5 và Phase 0 baseline note đã commit/push; exposed API key phải revoke/rotate ngoài repo.
15. **AI Studio v1.5 Phase 1 Mode C data integrity (2026-07-16)** — Mode C tách `outfit_id/schema_subject/display_label`; `mint_green` và `nike_pink_running` dùng schema canonical `outfit_e_sport`; universal fallback bị hard-fail; OS status dùng `since` để tránh stale artifact false success; upload trùng tên bị chặn; `wardrobe_manifest.json` quarantine Nike Pink artifact cũ và đánh dấu `sport_active` là legacy upload alias.
16. **AI Studio v1.5 Phase 2 Image QC contract (2026-07-16)** — Face Validator hard-fail nếu thiếu 3 gate hoặc 5 score keys; face score scale phải là 0–100; VenHo OS manifest `1.1` ghi prompt hash, outfit requested/effective, scenario profile, face reference set, validator contract, latency/retry.
17. **AI Studio v1.5 Phase 3 Durable Jobs (2026-07-16)** — VenHo OS image generation dùng file-backed job store, `/api/v1/studio/jobs`, status/cancel/polling, audit `queued→generating→validating→succeeded/failed/cancelled`.
18. **AI Studio v1.5 Phase 4 Wardrobe Index (2026-07-16)** — Linh An `wardrobe_index.json` contract 1.0 là source of truth cho outfit selector; OS đọc `/api/v1/studio/wardrobe-index`; user-selected outfit thắng default; AI auto-selection mặc định off.
19. **AI Studio v1.5 Phase 5 Contract Refs (2026-07-16)** — M02/M03/M05/M06 dùng optional `contract_refs` để trace `character_id/outfit_id/scenario_profile`; M05/M06 không tự chọn outfit; Claude adapter có fake-client test, không gọi API thật trong pytest.
20. **AI Studio v1.5 Phase 6 Ops/Living Lab (2026-07-16)** — M04 có `wardrobe_ingest` + `wardrobe_index_update` với validation/human-review gate; M09 hard-stop khi thiếu knowledge; `JobContract 1.0` tách `approved→executed→published`; Living Lab đo output used/approval/retry/time/cost/decision.
21. **AI Studio v1.5 Phase 7 QA/DOC closeout (2026-07-16)** — v1.5 không có Phase 7 chính thức; closeout map vào `QA-01/DOC-01`. Controlled matrix canonical ở `config/quality/controlled_live_matrix.json`; OS expose `/api/v1/studio/quality-matrix`; production-ready cần 2 approved runs liên tiếp/case.
22. **Current verification baseline (updated 2026-07-20)** — AI Studio `454/454` pass, 0 API call; VenHo OS `65/65` pass + lint + TypeScript + build pass. Build warning Turbopack NFT trace ở `upload-images/route.ts` là known issue, không phải failure.
23. **VAL-01 + LOC-01 real-run fixes (2026-07-17)** — Audit 16 run thật (2026-07-15/16) cho thấy 0/16 đạt `approved`. Root cause 1 (VAL-01): `observe_face_against_dna.md` chỉ ví dụ 1/3 gate → LLM luôn bỏ sót `eye_ratio`/`forbidden_traits` → `Face gates mismatch` chặn cứng mọi run. Root cause 2 (LOC-01): `westlake.overrides.yaml` curated stale ("green lamp posts/railing") trong khi thực tế 2026 (Harry xác nhận) là lan can trắng ngà, không cột đèn — validator chấm sai so với `constants.ts` thật. Sửa cả 2 (chỉ code/data, không API call để fix); thêm cơ chế scenario-aware overlay merge-at-validate-time (`image_validator.py::_apply_scenario_overlay`, tham số mới `scenario_profile_id`, threaded qua CLI/OS) để scenario Nguyễn Đình Thi có wording cây/lan can riêng, không đụng overlay chung. Live-verify case E1 thật: Image/DNA score 84.91→**100 approve**; Face không còn lỗi contract, score 80→**85** (vẫn dưới ngưỡng approve 90 — chưa xong). Case E5 vướng bug riêng, đã fix cùng phiên: `assets/Rooftop-Panorama-view.jpeg` là MPO container (ảnh iPhone portrait/burst nhiều frame) khiến `openai.images.edit` reject khi dùng làm ref-env thứ 2 (`400 invalid_image_file`). Convert sang PNG đơn-frame sạch (`Rooftop-Panorama-view.png`, giữ file gốc), cập nhật `constants.ts`. Live-verify lại: HTTP 200, Image/DNA 100/approve, Face 83.5/revise. **SEC-01 xác nhận done** (Harry đã tự rotate key lộ). OUTFIT-01 xác nhận đã xong từ Phase 4 (không phải làm mới). Kết luận trung thực: cả E1 và E5 đạt Image/DNA 100/approve nhưng Face score (85, 83.5) đều dưới ngưỡng approve 90 — production-ready gate (2 run approved liên tiếp/case E1–E6) vẫn chưa đạt; Face QC là gap lớn nhất còn lại (có thể cần VAL-02 — so khớp ảnh master thật — thay vì chỉ prompt contract).
25. **Prompt quality tuning + validator scoring reliability concern (2026-07-17)** — Sửa prompt-builder.ts (Living Expression rõ hơn cho running shot, thêm anti-artifact/sharpness cues) để cải thiện expression/technical_quality. Live-verify E1: 5 category score ra **giống hệt tuyệt đối** lần chạy VAL-02 trước đó (90/85/80/75/70) dù ảnh và prompt khác nhau — nghi ngờ Face Validator chấm theo khuôn mẫu mặc định, chưa chắc nhạy với input thật. Harry quyết định debug sau, không đốt thêm phí thử prompt cho tới khi rõ nguyên nhân.
26. **Git hygiene + backlog re-verification (2026-07-17)** — Commit toàn bộ thay đổi phiên này theo nhóm scope rõ ràng (không gộp bừa): `venho-ai-studio` 4 commit (VAL-01+LOC-01, VAL-02, docs, +1 MAN-01 gap không áp dụng ở repo này), `venho-os` 5 commit (LOC-01 threading, VAL-02 default refs, MPO image fix, prompt tuning, MAN-01 gap fix). Verify lại các mục task_status.md từng ghi "done": DATA-01/MODEC-01/MODEC-02 **CONFIRMED chính xác** bằng code thật, không cần sửa. JOB-01 **phần lớn đúng nhưng có gap thật**: server restart giữa lúc generate làm job kẹt vĩnh viễn ở `generating` (chưa có reconcile/resume, chưa có test cancel) — chưa fix, cần Harry quyết định ưu tiên. MAN-01 **tìm ra 1 bug thật và đã fix**: `faceReferenceSetVersion` là literal hardcode không liên kết với 4 ảnh reference VAL-02 thật, và gate sai theo `effectiveUseRef` thay vì `hasLinhAn` — đã sửa (commit `f15da8a` venho-os), thêm field `faceReferenceImages`, cập nhật test.
27. **JOB-01 gap fix (2026-07-17, commit `85785b5` venho-os)** — Harry yêu cầu fix gap đã tìm ra ở mục 26. Thêm `job-store.ts::reconcileOrphanedJobs()`, gọi 1 lần lúc `jobs/route.ts` module load (an toàn vì `controllers` map chắc chắn rỗng lúc đó) — mọi job còn `queued/generating/validating` trên đĩa được đánh dấu `failed`/`orphaned_by_restart` thay vì treo vô thời hạn. Khi viết test phát hiện thêm bug thật thứ 2: `cancelJob()` fallback path ép status thành `cancelled` vô điều kiện kể cả khi job đã `succeeded` — DELETE lên job đã xong sẽ phá hỏng kết quả đã ghi; đã sửa chỉ cancel job còn in-progress, trả 409 nếu đã terminal. Test mới: `job-store.test.ts` + 2 case cancel trong `jobs-route.test.ts`. 78/78 pass, build clean (NFT warning cũ không đổi).
30. **Full matrix v2 với sampling — kết quả cuối, sự cố bảo mật, khuyến nghị ngưỡng (2026-07-17/18)** — Chạy lại E1-E6 với sampling 3x. Kết quả: E1/E3/E4/E6 Image 100/approve; E2 lần 1 và E5 reject vì lý do thật khác nhau (green railing ngẫu nhiên, modern high-rise — bỏ ref-env chỉ giảm chứ không hết xu hướng model tự thêm nhà cao tầng ở góc panorama). Face score toàn bộ ~13 run thật trong phiên **chưa từng đạt 90** (dao động 0-85). Giữa chừng: (a) sự cố bảo mật — lệnh `source <(grep ... .env.local)` của tôi vô tình dump toàn bộ env ra output, làm lộ `OPENAI_API_KEY` trong transcript; đã dừng ngay, yêu cầu Harry rotate key; (b) tài khoản chạm billing hard limit thật giữa lúc chạy E4-E6, phải dừng và đợi Harry xử lý billing. Cả 2 đã được Harry xử lý xong, resume thành công. Kết luận cuối: khuyến nghị Harry xem xét lại ngưỡng `face_identity_min: 90` — có thể không thực tế với khả năng hiện tại của gpt-image-2, chưa tự ý đổi.
29. **Face Validator non-determinism xác nhận thật + fix bằng sampling (2026-07-17)** — Xem trực tiếp ảnh E3/E4/E6 (Read tool, không tốn phí) và ảnh master face — bằng mắt thường không thấy khác biệt rõ ràng giải thích được vì sao E3=82.5 còn E4/E6=0. Làm thí nghiệm rẻ: chạy lại Face Validator qua CLI trực tiếp (không tạo ảnh mới) 3 lần/ảnh trên 3 ảnh có sẵn. Kết quả: E3, E4 ổn định qua các lần lặp. **E6 "lật kèo" thật** — cùng ảnh, cùng reference, cùng code, nhưng run gốc cho 0/reject còn 3 lần lặp lại ngay sau đó đều cho 82.5/revise. Xác nhận đây là non-determinism thật của model ở temperature=0, không phải templating hay bug input. Fix: thêm `samples` param vào `validate_face()`, sample N lần + `_merge_face_samples()` (majority-vote gates, average weighted_scores, cùng pattern với `observe_adapter.py::_merge_samples` đã có cho Image Validator). `venho-os/validate_generated.py` mặc định `samples=3` cho production. Cũng fix E6 vấn đề Image: env-ref `Rooftop-Panorama-view.png` thực chất là ảnh 1 sân thượng cụ thể (xem bằng Read tool), làm ảnh AI lẫn chi tiết sai (lan can đen/gạch nung/cục nóng + nhà cao tầng thật) → bỏ ref-env cho scenario này (commit `531571c` venho-os). 451/451 test pass. Live-verify qua CLI thật: sampling hoạt động đúng thiết kế.
28. **Face Validator caching điều tra + full E1–E6 matrix live run (2026-07-17)** — Điều tra kỹ hiện tượng điểm giống hệt: rà toàn bộ call path, xác nhận **không có bug cache** (0 kết quả grep cache/lru_cache/memoiz trong `shared/vision/`, `validator_studio/`), mỗi lần gọi đều tạo client mới và gọi API OpenAI thật. Sau đó chạy đủ 6/6 case E1–E6 thật (trước đó mới có E1/E5): E1/E3/E5 approve Image, Face 82.5–85/revise; **E2 ban đầu 40/reject** vì DNA cấm cột đèn nhưng prompt sinh ảnh chưa từng cấm — **đã fix** (thêm "no lamp posts" vào `ENV_BLOCKS`/`SCENARIO_LOCATION_QC`/`NEGATIVE_BLOCK`, verify lại 40→100/approve, commit `88c19c6` venho-os); **E4 Face 0/reject đúng như kỳ vọng** (cycling tự tắt face-ref theo D-04 → mất identity thật, không phải bug); **E6 vẫn reject cả Image (postcard aesthetic) lẫn Face (identity fail dù có đủ reference) — CHƯA fix**, cần điều tra riêng. Phát hiện quan trọng nhất: report Face của E4 (không ref) và E6 (có đủ ref) cho **weighted_scores + văn bản lý giải giống hệt gần như từng chữ** dù input khác biệt cực lớn — bằng chứng mạnh Face Validator's `weighted_scores` có tính templating thật, trong khi `gates` (True/False) vẫn phân biệt đúng. Cũng phát hiện `controlled_matrix.py` không thể tính production-ready vì validator hiện tại thiếu field `outfit_match`/`actor_geometry_ok` mà matrix yêu cầu. Kết luận: production-ready vẫn chưa đạt ở bất kỳ case nào.
24. **VAL-02 implemented (2026-07-17, cùng phiên)** — Face Validator giờ so trực tiếp với 4 ảnh reference thật (B3_Hero primary, A2_Front, C_LeftProfile, D_RightProfile) thay vì chỉ text DNA. Thêm multi-image vision support (`shared/vision/providers/openai_vision.py::analyze_many`, `VisionClient.analyze_images`) — OpenAI chat API vốn hỗ trợ N ảnh/message, không cần workaround. `face_validator.py::validate_face` nhận `reference_image_paths` optional, `None` giữ nguyên hành vi cũ; thiếu file reference → raise lỗi rõ ràng trước khi gọi API (Harry chọn "fail loud", không âm thầm fallback, cùng nguyên tắc với fix universal_schema trước đó). `venho-os/validate_generated.py` tự truyền 4 path chuẩn khi có `--face`, không cần sửa route.ts. 450/450 test pass. **Live-verify E1:** report xác nhận thật sự dùng 4 ảnh reference (note + lý giải model trích dẫn "Comparison with reference images"), nhưng Face score = 82.5 (so với 85 không-reference trước đó) — **không cải thiện, giảm nhẹ**. Kết luận trung thực: điểm số giờ đáng tin cậy hơn (có căn cứ so ảnh thật) nhưng chưa đủ để đạt ngưỡng 90 — gap còn lại là chất lượng ảnh sinh ra thật (expression/technical_quality thấp), không còn là lỗi validator/contract. Đã verify 3/6 case-run tổng cộng (E1 x2, E5 x1); E2–E4/E6 chưa chạy.

---

## 3. Quy ước kỹ thuật

### Naming
- **Brand trong AI prompt:** `"Ven Ho Hotel"` (không dấu) — áp dụng toàn bộ prompt/instruction sinh bởi hệ thống.
- **Brand trên website/content hiển thị:** `"Ven Hồ Hotel"` (có dấu) — không đổi.
- **Hashtag:** không dấu (`#HoTay`, không phải `#HồTây`).

### Contract versions
| Module | Contract | Ghi chú |
|--------|----------|---------|
| M01 DNA | `contract_version = "1.1"` | M02 accept `[1.1, 2.0)` |
| M02 Prompt | `contract_version = "1.0"` | Per prompt type |
| M05 Content output | `contract_version = "1.0"` | |
| M06 Video package | `contract_version = "1.0"` | Pre-render package only |
| M07 Publishing request/receipt | `contract_version = "1.0"` | Dry-run/publish receipt cho M08 |
| M08 Analytics outputs | `contract_version = "1.0"` | Raw metrics, unified snapshot, score, alert, advisory |
| M09 Agent request/response | `contract_version = "1.0"` | Plan/module request/risk/approval contract |
| M10 Home Workspace snapshot | `contract = "presentation_only"` | Read-only normalized view over module artifacts + founder-first home workspace snapshot |

### DNA subjects (venho_hotel)
`lake_view_room` · `deluxe_double` · `lobby` · `facade` · `linh_an` · `westlake` · `outside`

Mỗi subject có: `_DNA.md` + `_DNA.json` + `_DNA_COMPACT.md` + `overrides.yaml` + `dna_manifest_*.json`

### DNA subjects (linh_an) — Mode C Wardrobe Studio
`wardrobe` (base/custom) · `outfit_a_cafe` · `outfit_b_west_lake` · `outfit_c_street` · `outfit_d_business` · `outfit_e_sport`

Configs: `config/projects/linh_an/subjects/{subject}.yaml` — 22 aggregation keys: brand, garment_category, color_primary/secondary, top/bottom/dress description, fit, logo_branding, signature_design_elements, footwear, accessories, hair_style_suggestion, occasion_context, content_pillar_fit, **prompt_snippet**
Output: `data/projects/linh_an/knowledge/LINH_AN_{SUBJECT_UPPER}_DNA.md`
UI: Workbench → Tab "Linh An DNA — Mode C"

Mode C variant routing:
- `outfit_id = mint_green` → `schema_subject = outfit_e_sport` → `LINH_AN_MINT_GREEN_DNA.*`
- `outfit_id = nike_pink_running` → `schema_subject = outfit_e_sport` → `LINH_AN_NIKE_PINK_RUNNING_DNA.*`
- Không cho fallback `config/universal_schema.yaml` trong Mode C.
- `config/projects/linh_an/wardrobe_manifest.json` là registry tạm cho Phase 1: quarantine artifact cũ và ghi legacy aliases trước khi có Wardrobe Index 1.0 ở Phase 4.

### CLI commands (venho global PATH: `/Users/hanhpham/Library/Python/3.9/bin`)
```bash
venho vision observe --mode b --project venho_hotel --subject {subject} --input {dir}
venho vault search "từ khóa"
venho prompt --type {image,video,content,seo} --project venho_hotel --subject ... --brief "..."
venho validate image|prompt|face|content ...
venho auto run {workflow_id}
venho auto resume {run_id}
venho content --project venho_hotel --type {facebook,blog,...} --topic "..." --lang vi
venho content campaign --project venho_hotel --topic "..." --channels facebook,instagram,threads
venho content calendar --project venho_hotel --month 2026-08
venho-video generate --topic "lake view room morning" --duration 15 --type social_reel --subjects lake_view_room,westlake
python3 -m publishing_gateway.cli publish --package-file data/projects/venho_hotel/publishing/fixtures/approved_package.json --approval-secret test-secret --dry-run
python3 -m publishing_gateway.cli retry --package-file data/projects/venho_hotel/publishing/fixtures/approved_package.json --platform instagram --approval-secret test-secret --dry-run
python3 -m agent_studio.cli --agent marketing_agent --project venho_hotel --goal "Tạo campaign trải nghiệm mùa hè Hồ Tây" --plan-only
# VenHo OS UI (Next.js — Streamlit đã xóa 2026-07-13)
npm run dev   # → localhost:3000/os
```

### Integration seams đã verify (2026-07-09)
- M01→M02: DNA contract 1.1 nằm trong range M02 chấp nhận `[1.1, 2.0)` ✅
- M02→M05: `prompt_bridge` import `build_content_prompt` — signature khớp ✅
- M03→M05: `content_validator_bridge` gọi `validate_content` có degradation ✅
- M04 adapters → M01/02/03: cả 3 adapter gọi đúng public API ✅
- M02→M06: `prompt_bridge` gọi `build_video_prompt` cho từng scene prompt ✅
- M05→M06: `content_bridge` gọi Content Studio để lấy hook/caption/CTA ✅
- M03→M06: `validator_bridge` dùng prompt validation per scene; video-package validation degrade advisory ✅
- M04→M07: M07 kiểm `package_status=approved`, HMAC approval signature và TTL trước khi publish/dry-run ✅
- M07→M08: delivery receipt contract có `platform_results`, `public_url/post_id/status`, circuit breaker info và `analytics_handoff.ready_for_m08=true` ✅
- M08 loop: receipt → mock metrics → unified snapshot → score → sentiment → advisory/report chạy offline ✅
- M09→M04: goal → TaskPlan → ModuleRequest package luôn target `M04_AUTOMATION_STUDIO`; external impact cần manual gate, không gọi M07 trực tiếp ✅
- M10 Home Workspace v1.0: `dashboard.gateway` đọc config/artifacts của M01-M09, Face Lock display threshold, graceful advisory khi thiếu dữ liệu; Home dùng Today's Focus + Current Work + Needs Review + Ready to Publish + Quick Actions + Recent Activity; pipeline chuyển vào Workbench, system/debug chuyển vào Settings; không gọi API và không mutate data ✅

---

## 4. Cấu trúc thư mục chính

```
venho-ai-studio/
├── knowledge_studio/vision/   ← M01 core engine
├── prompt_studio/             ← M02 prompt builders + pipeline
├── validator_studio/          ← M03 validators + scoring
├── automation_studio/         ← M04 workflow runner + adapters
│   └── adapters/              ← lớp cô lập interface M01/M02/M03
├── content_studio/            ← M05 content builders + manifest
│   └── builders/              ← social, blog, website, OTA, FAQ, email
├── video_studio/              ← M06 video package pipeline
│   └── builders/              ← character, lifestyle, reel, explainer, hero
├── publishing_gateway/        ← M07 publishing guardrails, adapters, receipt
│   ├── adapters/              ← facebook, instagram, threads, google_business, mock
│   ├── schemas/               ← publishing request, delivery receipt, approval, result
│   ├── renderers/             ← receipt JSON/Markdown
│   └── utils/                 ← idempotency, time, URL, media upload helpers
├── shared/vision/             ← VisionClient, MockVisionClient, image_loader
├── agent_studio/              ← M09 request validation, routing, personas, planning, risk, M04 bridge
│   ├── agents/                ← base + generic agents
│   ├── schemas/               ← request/response/persona/task/module/risk contracts
│   ├── renderers/             ← response Markdown/JSON
│   └── templates/             ← persona/agent templates
├── [dashboard/ — DELETED 2026-07-13, thay bởi Next.js VenHo OS]
├── config/
│   ├── settings.yaml
│   ├── validation.yaml
│   └── projects/venho_hotel/
│       ├── subjects/          ← subject YAML + overrides.yaml
│       ├── content/           ← content_pillars, tone, platform_rules, SEO, calendar
│       ├── video/             ← camera_rules, character_rules, motion_rules...
│       ├── publishing/        ← platforms, approval, brand display, schedule, rate limit
│       ├── analytics/         ← metrics mapping, schedule, scoring, sentiment, feedback policy
│       ├── agents/            ← M09 personas + agent_policy
│       └── prompt_rules.yaml
├── data/projects/venho_hotel/ ← .gitignore (output data)
│   ├── knowledge/             ← DNA files
│   ├── prompts/               ← prompt JSON per type
│   ├── content/               ← draft content per channel
│   ├── video/                 ← video packages + video_manifest
│   ├── publishing/            ← fixture package + receipt store
│   ├── analytics/             ← raw metrics, snapshots, scores, advisories, alerts, reports
│   └── validation/            ← validation reports
├── tests/                     ← 430 tests, 0 API call
├── docs/                      ← plan docs + how-to guides
├── task_memory.md             ← file này — context chung AI Engine
└── task_status.md             ← status từng module
```

---

## 5. Linh An — AI KOL (quan trọng với M05/M06)

**Face Lock v3.1 (dùng khi không có `--ref`):**
```
Linh An, Vietnamese female influencer, 24 years old,
soft elongated oval face, slightly fuller cheeks, balanced facial proportions,
slim natural nose bridge, long almond eyes, horizontal eye emphasis,
slightly narrow eye opening, thin upper eyelid, warm brown irises,
very subtle outer corner lift, natural eye asymmetry,
low-position eyebrows, minimal arch, close eye-brow distance,
natural full lips with slightly thinner upper lip and slightly fuller lower lip,
very subtle upward lip corners, slightly shorter philtrum,
soft feminine jawline, delicate chin,
fair warm ivory skin, healthy natural glow, realistic skin texture, natural pores,
long dark chocolate brown layered wavy hair, natural center part,
small pearl drop earrings,
gentle feminine beauty, elegant Vietnamese appearance,
luxury lifestyle creator, consistent facial identity,
photorealistic, natural beauty,
no plastic skin, no doll face, no exaggerated makeup
```

**Reference images:** `ops/VenHoSocialManager/assets/` (trong Ven Ho Hotel repo)
- `B3_Hero.png` — 3/4 trái, score 9.4–9.5 **(PRIMARY)**
- `linh-an-master-face.png` — Master Face #001, lifestyle

**QC threshold:** ≥ 9.0 APPROVED · 8.0–8.9 CONDITIONAL · < 8.0 REJECT

---

## 6. Test discipline

- **KHÔNG BAO GIỜ** gọi real API trong pytest.
- Prompt Studio: luôn truyền `optimize_fn=optimize_mock` trong tests (default gọi Claude API thật, tốn tiền).
- Validator Studio: provider schema guards — test dùng fake clients.
- Content Studio: prose generator ở mock/deterministic mode trong tests.
- Video Studio (M06): prompt/content/validator bridges đều chạy offline/mock trong tests.
- Publishing Gateway (M07): pytest chỉ dùng dry-run/mock adapters; không đọc real token, không gọi platform API.
- Analytics Feedback (M08): pytest chỉ dùng `MockMetricsAdapter`; không gọi insights API thật.

---

## 7. Quyết định thiết kế quan trọng (không thay đổi)

| Quyết định | Lý do |
|-----------|-------|
| Pass 2A tất định (code-only) | Nếu LLM quyết định cấu trúc DNA → không tái lập được |
| Forbidden ở curated overlay | Single source, không bị overwrite khi regenerate |
| M05 prose dùng temperature > 0 | Module DUY NHẤT cho phép AI sáng tạo câu chữ |
| Manual gate trong M04 | Ảnh sinh bởi Flow/GPT Image (ngoài hệ thống) — không thể tự động hóa khâu này |
| M07 idempotency theo package/project/platform/content/schedule | Chặn duplicate publish; partial success chỉ retry failed platform |
| M07 adapters dry-run trước live | Bảo toàn 0 API call trong tests và tránh publish nhầm |
| Threads/Google Business feature-flag off mặc định | Conditional MVP cho tới khi đủ API access |
| M08 advisory-only | Feedback không tự apply vào M01/M05; luôn qua M04/M09 approval route |
| M08 raw/unified tách riêng | Audit được provenance và tránh mất raw platform metrics |
| M09 plans, M04 executes | Agent Studio chỉ tạo TaskPlan/ModuleRequest qua M04; không tự publish, không sửa Knowledge, không gọi M07 trực tiếp |
| M09 approval policy tập trung | Risk rules đọc từ `config/projects/<project>/agents/agent_policy.yaml`; destructive blocked, external impact approval |
| Staleness advisory (không auto-regen) | Nội dung theo ngày vẫn dùng được dù DNA nguồn cập nhật |
| Archive thuộc module con | M04 không biết format file của module khác |
| M06 storyboard templates theo video_type | character/social_reel/website_hero/explainer cần scene arc khác nhau — không dùng generic |
| M06 engine templates = AI-facing notes | Templates `video_studio/templates/{engine}.yaml` được embed vào engine prompt; không chứa nội bộ "Module XX" |
| M06 validator bridge dùng primary env subject | Lấy source_knowledge đầu tiên không phải linh_an/character để xác định subject cho M03 |

---

## 8. M07 Publishing Gateway — hoàn thành 2026-07-09

**Status:** ✅ COMPLETE — offline dry-run MVP  
**Plan:** `VENHO_AI_STUDIO_Module_07_Publishing_Gateway_Development_Plan_v1_2_QC.md`  
**Tests:** `python3 -m pytest` → 406/406 pass, 0 API call  
**Module tests:** 19 tests — `tests/test_publishing_gateway.py`, `tests/test_publishing_gateway_scaffold.py`

### Luồng M07 chính

```
PublishingRequest
→ Contract Validator
→ Approval Verifier
→ Brand Guard
→ Platform Capability Check
→ Idempotency / Receipt Store
→ Queue + Rate Limit + Circuit Breaker
→ Platform Adapter
→ Delivery Receipt
→ M08 Analytics Handoff
```

### Core files

- `publishing_gateway/gateway_router.py` — orchestrates guardrails, adapters, queue, receipt.
- `publishing_gateway/schemas/` — request/receipt/result/approval contracts.
- `publishing_gateway/approval_verifier.py` — HMAC-SHA256 signature + TTL.
- `publishing_gateway/receipt_store.py` — persistence source for idempotency and receipts.
- `publishing_gateway/adapters/` — Facebook, Instagram, Threads, Google Business, Mock.
- `publishing_gateway/cli.py` — `publish`, `retry`, `receipt`, `queue`, `version`.
- `config/projects/venho_hotel/publishing/` — platform flags, approval policy, brand display, schedule, rate limits.
- `docs/contracts/m07_to_m08_delivery_receipt.md` — M08 handoff contract.
- `docs/how_to_run_publishing_gateway.md` — dry-run and controlled live checklist.

### M07 boundaries

- M07 không tạo caption, hashtag, metadata, ảnh hoặc video.
- M07 không sửa nội dung đã duyệt.
- M07 không tự quyết định giờ đăng; MVP mặc định `publish_now=true`, scheduled execution là hậu-MVP.
- M07 không phân tích performance; chỉ ghi receipt cho M08.
- Real API publish chỉ là controlled manual test, không nằm trong pytest.

---

## 9. M08 Analytics & Feedback Loop — hoàn thành 2026-07-09

**Status:** ✅ COMPLETE — offline MVP  
**Plan:** `VENHO_AI_STUDIO_Module_08_Analytics_Feedback_Development_Plan_v1_2_QC.md`  
**Tests:** `python3 -m pytest` → 413/413 pass, 0 API call  
**Module tests:** 7 tests — `tests/test_analytics_feedback.py`

### Luồng M08 chính

```
M07 Delivery Receipt
→ Ingestion Router
→ Collection Scheduler
→ Mock Metrics Adapter
→ Raw Metrics Store
→ Unified Metrics Standardizer
→ Stats Calculator
→ Snapshot Store
→ Baseline Calculator
→ Performance Scorer
→ Sentiment Guardrail
→ Alert / Feedback Advisory / Report
```

### Core files

- `analytics_feedback/schemas/` — delivery receipt ref, raw metrics, unified metrics, score, alert, advisory.
- `analytics_feedback/adapters/mock_metrics.py` — deterministic offline metrics/comments.
- `analytics_feedback/ingestion_router.py` + `collection_scheduler.py` — M07 receipt to collection tasks.
- `analytics_feedback/metrics_standardizer.py` + `utils/stats_calculator.py` — raw to unified + derived metrics.
- `analytics_feedback/baseline_calculator.py` + `performance_scorer.py` — baseline group and labels.
- `analytics_feedback/sentiment_scorer.py` + `alert_generator.py` — vi/en keyword guardrail and critical alerts.
- `analytics_feedback/feedback_advisory_generator.py` + `report_generator.py` — pending approval advisory/report outputs.
- `config/projects/venho_hotel/analytics/` — schedule, mapping, scoring, sentiment, feedback policy.

### M08 boundaries

- M08 không publish, không sửa content đã đăng, không gọi M07 để publish lại.
- M08 không tự ghi M01 Knowledge hoặc M05 Content Strategy.
- M08 chỉ tạo advisory/alert/report; apply phải qua M04 Manual Gate hoặc M09 workflow có approval.
- Real platform insights adapters là phase sau; pytest giữ offline 100%.

---

## 10. M09 Agent Studio — hoàn thành 2026-07-09

**Status:** ✅ COMPLETE — offline planning/orchestration MVP, reviewed  
**Plan:** `VENHO_AI_STUDIO_Module_09_Agent_Studio_Development_Plan_v2_2_QC.md`  
**Tests:** `python3 -m pytest` → 423/423 pass, 0 API call  
**Module tests:** 10 tests — `tests/test_agent_studio.py`

### Luồng M09 chính

```
AgentRequest
→ Request Validator
→ Agent Router
→ Persona Resolver
→ Context Loader
→ Missing Knowledge Detector
→ Task Planner
→ Risk Classifier
→ Module Request Builder
→ M04 Automation Bridge
→ Result Aggregator
→ Markdown / JSON Response
```

### Core files

- `agent_studio/schemas/` — request/response/persona/task/module/risk/execution contracts.
- `agent_studio/request_validator.py` — validates required request fields and contract shape.
- `agent_studio/agent_router.py` — routes generic/project-specific agent ids.
- `agent_studio/persona_resolver.py` — loads persona config from project YAML.
- `agent_studio/context_loader.py` — loads knowledge, analytics, prompt refs without inventing missing data.
- `agent_studio/missing_knowledge.py` — detects required knowledge gaps and returns `ERR_MISSING_KNOWLEDGE`.
- `agent_studio/task_planner.py` — deterministic goal-to-task-plan MVP.
- `agent_studio/risk_classifier.py` — reads `agent_policy.yaml`, marks approval gates, blocks destructive actions.
- `agent_studio/module_request_builder.py` — packages every task as M04-targeted `ModuleRequest`.
- `agent_studio/automation_bridge.py` — offline/mock M04 bridge for MVP.
- `agent_studio/result_aggregator.py` + `renderers/` — AgentResponse Markdown/JSON.
- `agent_studio/cli.py` — `python3 -m agent_studio.cli --agent marketing_agent --project venho_hotel --goal "..." --plan-only`.
- `config/projects/venho_hotel/agents/` — `agent_policy.yaml`, `marketing_agent.yaml`, `linh_an_brand_agent.yaml`, `hotel_ops_agent.yaml`.

### M09 boundaries

- M09 là cognitive interface / orchestration layer, không phải execution engine.
- M09 không tự publish, không gọi Meta/Google/Threads API, không gọi M07 trực tiếp.
- M09 không tự sửa Knowledge hoặc Content Strategy.
- M09 chỉ đọc M08 advisory; không tự thu thập hoặc tính metrics.
- M09 luôn đóng gói execution intent qua M04.

### Review notes / follow-up

- Review 2026-07-09: MVP đạt, module tests 10/10 và full suite 423/423 pass.
- **Fixed (373b1cc):** execute mode bị block khi missing_knowledge (fallback dry_run); gate task không bị slice; status đổi thành `PARTIAL` thay vì `FAILED` khi plan vẫn valid.
- **Superseded by Phase 6 (2026-07-16):** missing knowledge giờ hard-stop trước M04 dispatch; không còn fallback/dry-run dispatch khi thiếu required knowledge.
- Follow-up execution: `--execute` hiện vẫn là prepared/mock M04 bridge; khi chuyển sang execution thật phải nối qua public API của M04, vẫn giữ approval gate.

---

## 11. M10 VENHO OS Home Workspace — historical Streamlit milestone, superseded 2026-07-13

**Status:** HISTORICAL. Runtime hiện tại là Next.js `venho-os`; block này giữ lại để truy vết trước khi Streamlit bị xóa.
**Tên chính thức:** **Mother Dashboard** — đặt bởi Harry 2026-07-13
**Plan:** `VENHO_AI_STUDIO_Module_10_Dashboard_Plan_v1_2.md`  
**Design:** `/Users/hanhpham/Developer/VENHO_OS_HOME_WORKSPACE_UI_SPEC_v1.0.md` + `/Users/hanhpham/Developer/VENHO_OS_UI_DESIGN_SPEC_v1.0.md`
**Tests:** `python3 -m pytest -q` → 430/430 pass, 0 API call
**Module tests:** 7 tests — `tests/test_dashboard.py`

### Quyết định kiến trúc

M10 mở rộng Studio Shell Streamlit hiện có (`ui/studio_app.py`) thay vì tạo Next/Nuxt/Vite app riêng. Lý do: repo đã có local-first Studio Shell tại `localhost:8501`, nên M10 giữ một entrypoint duy nhất và tránh thêm stack mới.

Sau bản `VENHO_OS_HOME_WORKSPACE_UI_SPEC_v1.0.md` và `VENHO_OS_UI_DESIGN_SPEC_v1.0.md`, M10 không được xem là technical dashboard nữa. M10 là Business Operating Workspace cho founder: workspace-first, execution-first, one primary mission, giảm tải nhận thức, Home ưu tiên việc cần làm tiếp theo thay vì module internals.

### Core files

- `dashboard/gateway.py` — read-only adapter đọc M01-M09 config/artifacts và tạo `DashboardSnapshot` + `operating_center` workspace fields (`header`, `today_focus`, `current_focus`, `needs_review`, `ready_to_publish`, `quick_actions`).
- `dashboard/__init__.py` — module metadata (`MODULE_ID = "M10"`).
- `ui/studio_app.py` — render `VENHO OS — Home Workspace` với navigation Home Workspace, Projects, Tasks, Knowledge, Workbench, Creative Studio, Publishing, Reports, Settings; đồng thời giữ Studio Shell Mode A / Mode B.
- `docs/how_to_run_studio_ui.md` — hướng dẫn chạy shell + dashboard.

### Home Workspace UI v1.0

- Header: `VENHO OS (Home Workspace)`, project `Ven Hồ Hotel`, last sync, notifications/user affordances, build Home Workspace v1.0.
- Sidebar label: `VENHO OS` / `Business Operating Workspace`.
- Sidebar navigation: Home Workspace, Projects, Tasks, Knowledge, Workbench, Creative Studio, Publishing, Reports, Settings.
- Priority order: Today's Focus → Current Work → Needs Review + Ready to Publish → Quick Actions → Recent Activity.
- Home không hiển thị pipeline, analytics, system health, large KPI counters, raw JSON.
- Pipeline/workflow nằm trong Workbench; raw JSON/debug/system tools nằm trong Settings.
- Quick Actions: Build DNA, Generate Prompt, Validate, Publish, Video, Automation.

### Studio Shell upload/output UX

- Mode A có `Nguồn ảnh input`: Folder có sẵn hoặc Upload ảnh; upload lưu vào `data/projects/_inbox/media`.
- Mode B có `Nguồn ảnh input`: Folder có sẵn hoặc Upload ảnh; upload lưu vào `data/projects/{project}/media/{subject}`.
- Mode A/B provider mặc định là `mock` để test offline, không cần `OPENAI_API_KEY`; `openai`, `claude`, `config mặc định` vẫn chọn được khi có credentials.
- Mode A hiển thị output path và nút `Mở folder output`; mặc định `data/projects/_inbox/output`.
- Mode B hiển thị output path và nút `Mở folder output`; mặc định `data/projects/{project}/knowledge`.
- Nút mở folder tự tạo folder nếu chưa có và mở Finder trên macOS.

### Workflow pages v2.0

- Projects, Tasks, Knowledge, Workbench, Creative Studio, Publishing, Reports dùng card-based panels thay vì dense tables.
- Workbench ưu tiên Continue Working, Pending Reviews, Draft Outputs, Ready To Publish, Failed Items.
- Publishing tách Ready, Waiting Approval, Scheduled, Published, Failed dưới dạng cards.
- Insights giữ advisory-only; khi có dữ liệu hiển thị Overview + Recommendations cards, khi chưa có dữ liệu hiển thị empty state rõ ràng.
- Raw JSON và dataframes chỉ còn trong `System` developer area.

### M10 boundaries

- Không có DB nghiệp vụ riêng; chỉ đọc `config/projects/`, `data/projects/`, `data/automation_runs/`.
- Không tính lại score/verdict/HMAC; chỉ hiển thị output do module core tạo.
- Không build prompt, không build ModuleRequest, không render/upload/publish.
- Missing artifact tạo advisory theo module thay vì làm sập dashboard.
- Face Lock gate chỉ là display mapping theo plan: `>=9.0 APPROVED`, `8.0-8.9 CONDITIONAL`, `<8.0 REJECT`; score 0-100 được normalize để hiển thị.
- Quick actions trong Workbench là UI entrypoints/disabled placeholders ở MVP; không kích hoạt business logic hay external workflow trực tiếp.
- Phase 5 Command Palette (`Cmd+K`) là follow-up của Streamlit MVP cũ, không còn là acceptance gate của runtime Next.js hiện tại.

---

## 12. Creative Studio — M10 Extension (2026-07-09)

**Status:** ✅ COMPLETE — 3 modes tích hợp vào `ui/studio_app.py`

### Các mode

| Mode | Chức năng |
|------|----------|
| **Tạo Ảnh AI** | Topic/scenario/outfit/action → assemble prompt → `generate_image.py` subprocess → hiển thị ảnh trong UI |
| **Tạo Social Post** | Content Strategy v2.0 analysis (persona/funnel/golden rule) → caption prompt template → tạo ảnh AI + lưu `meta.json` |
| **Tạo Video Script** | Auto-number → sinh script 3 scene × Seedance prompt → preview + Lưu `.md` vào `scripts/` |

### Path constants (đầu `studio_app.py`)
```python
VENHO_HOTEL_DIR = BASE_DIR.parent.parent / "Ven Ho Hotel"   # projects/Ven Ho Hotel/
SOCIAL_MANAGER_DIR = VENHO_HOTEL_DIR / "ops" / "VenHoSocialManager"
VIDEO_SCRIPTS_DIR = VENHO_HOTEL_DIR / "local-generated" / "social-video" / "scripts"
```

### Fix quan trọng

1. **`Path(__file__).resolve()`** — Streamlit đôi khi truyền `__file__` = `ui/studio_app.py` (relative). Không có `.resolve()` → `SOCIAL_MANAGER_DIR` = `Ven Ho Hotel/ops/...` (relative, không tồn tại). Bắt buộc dùng `.resolve()`.

2. **Timeout 300s** — gpt-image-2 + `--ref` (image editing) thường mất 90–150s. 120s không đủ.

3. **Action prompt formula v2 (2026-07-10)** — single integrated sentence, NO `\n\n` break. gpt-image-2 treats `\n\n` as paragraph separator → renders two separate entities → character disappears. Công thức: `"Linh An {action}, she is a Vietnamese female lifestyle influencer, 24 years old, ... wearing {outfit}, ... she is the MAIN SUBJECT in the foreground, full body visible, no conical hat, photorealistic."` — tất cả một câu liên tục. Thêm `"MAIN SUBJECT in the foreground, full body visible"` để AI giữ nhân vật ở foreground. Lens: 35mm (không phải 85mm portrait) cho full-body action shots.

4. **`use_ref` toggle** — gpt-image-2 `--ref` dùng image editing từ ảnh gốc (Linh An đứng) → không thể thay đổi toàn bộ body pose (đạp xe, chạy, ngồi). Bỏ `--ref` = text-to-image mode → AI tự do tạo bất kỳ pose.

5. **Outfit E — Nike AeroSwift** (cập nhật 2026-07-13 từ ảnh thật) — `"mint-green Nike racerback loose crop tank top, dual Swoosh logos at collar, perforated ventilation panels on chest and back, mint-green Nike running shorts (3-inch inseam) with mesh waistband and small Swoosh logo on leg, white Nike running shoes, white ankle socks, sleek high ponytail"`. Khi outfit_key bắt đầu bằng "E — Sport", hair tự động đổi sang `"tied back in a sporty ponytail"`.

6. **Textarea cache bug (fix 2026-07-13)** — `st.text_area(key="tai_prompt")` khiến Streamlit cache giá trị cũ khi user thay inputs (checkbox/outfit/action). Fix: bỏ `key` khỏi textarea. Prompt luôn reflect trạng thái inputs hiện tại.

7. **Prompt structure action mode (fix 2026-07-13)** — Character + environment giờ join `\n` (1 dòng) thành 1 block duy nhất thay vì `\n\n` riêng. Format mới: `"Linh An {action} in the scene, she is the MAIN SUBJECT prominently in the foreground...\nSetting: {env}"` — gpt-image-2 không còn coi character/env là 2 entity độc lập.

8. **Quick Actions nav pattern (fix 2026-07-13)** — Không thể set `st.session_state["m10_section"]` sau khi sidebar radio widget đã instantiate (StreamlitAPIException). Fix: dùng `_m10_nav_pending` key trung gian; apply vào `m10_section` ở đầu `_render_dashboard()` TRƯỚC khi sidebar radio được tạo.

### Quy tắc `use_ref`

| Checkbox | Dùng khi | Face score | Kết quả |
|----------|----------|-----------|---------|
| ✅ Có ref | Portrait / Standing / Leaning / Tựa lan can | ~9/10 | Linh An đúng khuôn mặt ✅ |
| ☐ Không ref | Full-body action (đạp xe, chạy, ngồi, nhảy) | 7–8.5/10 | Action đúng, nhân vật xuất hiện ✅, face generic |

### Outfit mapping

| Key | Mô tả | Hair tự động | Dùng khi |
|-----|-------|-------------|---------|
| A — Cafe Girl | cream knit top, beige A-line skirt | wavy | Cafe, lifestyle |
| B — West Lake Sunset | flowing white dress, minimal gold jewelry | wavy | Hoàng hôn, lãng mạn |
| C — Street Style | white button-up, high-waist trousers, denim jacket | wavy | Phố phường |
| D — Business Travel | light beige blazer, white blouse | wavy | Professional |
| E — Sport & Active | mint-green Nike racerback crop tank + running shorts (3-inch), white Nike shoes | ponytail | Cycling, running, active |

### Caption generation decision

`/tao-social-post` trong UI **không** gọi AI API trực tiếp để viết caption — sinh sẵn prompt template để Harry copy sang ChatGPT. Lý do: M05 Content Studio dùng mock prose generator, không nối API thật; tránh thêm API key/cost vào Streamlit UI.

---

## 13. VenHo OS — Next.js Dashboard (2026-07-13)

**Status:** ✅ Stage A+B+C COMPLETE · Build 34/34 pages, 0 TS error
**Location:** `Ven Ho Hotel/src/app/os/` + `src/components/os/` + `src/app/api/v1/studio/`
**URL:** `localhost:3000/os` (chạy bằng `npm run dev` hoặc `run-venho-os.command`)

### Architecture
- RSC page `src/app/os/page.tsx` reads `?section=` query param, routes to section components
- Section routing via `<Link href="/os?section=xxx">` — no `useSearchParams()` in client components
- `src/lib/studio/paths.ts` — path constants (venho-ai-studio, VenHoSocialManager, video scripts)
- `src/lib/studio/constants.ts` — Python constants ported to TS (outfits, env blocks, pillars, scenes)
- `src/lib/studio/prompt-builder.ts` — pure TS port of 3 Python functions (assembleImagePrompt, buildCaptionPrompt, generateVideoScript)
- `src/components/os/shared/ui.tsx` — shared UI primitives (SectionHeader, Field, PrimaryBtn, CopyBtn, TabBar)

### API Routes (`/api/v1/studio/`)
| Route | Method | Chức năng |
|-------|--------|-----------|
| `observe` | POST | SSE stream `venho vision observe` (Mode A/B) |
| `generate-image` | POST | `generate_image.py` subprocess → imagePath |
| `file` | GET | Serve local files (generated images) — whitelist dirs + exts |
| `save-script` | GET/POST | Next script number / save `.md` to scripts dir |
| `dna` | GET | List DNA subjects + read COMPACT content |
| `vault-search` | POST | Full-text search across all `*_DNA*.md` files |
| `social-index` | GET | Read `database/index.json` → social post history |

### Sections implemented
| Section | Tabs |
|---------|------|
| Workbench | Mode A (Observe) · Mode B (Build DNA) — SSE live log |
| Creative Studio | Tạo Ảnh AI · Tạo Social Post · Tạo Video Script |
| Knowledge | DNA Library · Vault Search · Mode C — Linh An |
| Reports | DNA Status · Social Content Log |
| Others (8) | PlaceholderSection — Projects, Tasks, Agents, Operations, Publishing, Settings |

### Quan trọng
- `venho` CLI path: `/Users/hanhpham/Library/Python/3.9/bin` phải inject vào `PATH` trong spawn
- DNA content dir: `data/projects/venho_hotel/knowledge/` trong venho-ai-studio
- Social post index: `ops/VenHoSocialManager/database/index.json` trong Ven Ho Hotel repo
- File API whitelist: `SOCIAL_MANAGER_DIR`, `VIDEO_SCRIPTS_DIR`, `STUDIO_DIR`
- Next.js 16: `searchParams` là `Promise<{section?: string}>` — bắt buộc `await`

### Cleanup 2026-07-13 — Xóa Streamlit
- `ui/studio_app.py` + `ui/` — DELETED (2.335 dòng)
- `dashboard/gateway.py` + `dashboard/__init__.py` + `dashboard/` — DELETED (774 dòng)
- `tests/test_dashboard.py` — DELETED (149 dòng); test suite giảm từ 430 → 423
- `docs/how_to_run_studio_ui.md` — DELETED
- Next.js VenHo OS (`localhost:3000/os`) là entrypoint UI duy nhất

---

## 14b. Growth Agent v3.1 — Cutover thay VenHoSocialManager (2026-08-04)

Harry chốt: Growth Agent v3.1 (repo này) sẽ **thay thế hoàn toàn** `VenHoSocialManager` (repo `venho-os`, GitHub Actions T2/T4/T6 8AM, đăng thẳng FB/IG/Threads qua Make.com không qua duyệt thủ công) — không chạy song song. Thêm T7 (nội dung đặc biệt) cùng giờ.

**Đã nối trong repo này (2026-08-04):** `M07PublishingBridge.dispatch()` route theo `command["platform"]` → `ZaloOAAdapter` (zalo) hoặc `MakeGatewayAdapter` (facebook/instagram/threads, tái dùng scenario Make.com cũ của VenHoSocialManager qua `MAKE_WEBHOOK_URL`/`MAKE_WEBHOOK_SECRET`). Cả hai adapter dùng chung 1 pattern: bắn webhook có ký HMAC, không gọi API platform trực tiếp, trả `GATEWAY_ACCEPTED`/`GATEWAY_ERROR` ngay — trạng thái `PUBLISHED` thật đến sau qua `callback_receiver.py` hoặc `reconciliation.py`. `daily_dispatch()` nhận `bridge` tiêm được.

**3 gap kiến trúc thật còn lại trước khi cutover được (không phải việc nhỏ, cần thiết kế riêng từng cái):**
1. **Không có orchestrating command nào** nối `preflight → trend_lane/special_lane → run_content_pipeline → manage_queue → daily_dispatch` thành 1 lệnh chạy được — cần cho lịch T2/T4/T6/T7.
2. **Approve trên VENHO OS Dashboard chưa nối vào đây.** Section "Publishing & Schedule" hiện tại (`venho-os/src/components/os/sections/PublishingSection.tsx` + API `/api/v1/studio/topic-schedule`) là hệ thống cũ — duyệt **topic** cho VenHoSocialManager, ghi thẳng vào 1 file JSON + `git commit`, hoàn toàn không đụng tới `PublicationRegistry`/M07 của repo Python này. Cần route/section mới ở `venho-os` gọi ngược vào Python (shell-out CLI hoặc API nội bộ) mới có "bấm Approve → dispatch thật".
3. **Chưa có tạo ảnh thật.** `content_studio/builders/social_builder.py::mock_social_generator` là mock thuần. M02 Prompt Studio đã build prompt ảnh thật từ DNA (`venho prompt --type image`, complete) — còn thiếu đúng adapter gọi OpenAI images API (gpt-image-2 + ref ảnh), theo pattern dependency-injected-HTTP giống Tavily/Telegram/Zalo (§ test discipline).

**Cập nhật 2026-08-04 — cả 3 gap đã có glue thật (chi tiết đầy đủ: `task_status.md` mục cùng ngày):**
1. `growth_orchestrator/application/daily_cycle.py::run_daily_cycle(day)` + CLI `venho-growth daily-cycle` + `.github/workflows/growth-daily-cycle.yml` (cron Mon/Wed/Fri/Sat 08:00 ICT) — sinh draft thật qua `content_studio.generate_content()`, queue `PENDING_APPROVAL` trong `PublicationRegistry`, KHÔNG dispatch.
2. `growth_orchestrator/application/approve_and_dispatch.py` + CLI `venho-growth approve-and-dispatch` — Approve gọi `M07PublishingBridge.dispatch()` thật. Nối sang `venho-os` qua 2 route mới (`/api/v1/studio/growth/pending`, `/api/v1/studio/growth/[id]/approve`) shell-out `venho-growth` (pattern có sẵn từ `generate-image`/`observe`), UI thêm vào `PublishingSection.tsx`. **venho-os hiện có rất nhiều uncommitted WIP không liên quan (~60 file, có vẻ refactor design-token) — code mới nằm trong working tree đó nhưng CHƯA được `git add`/commit, cố tình để Harry tự commit.**
3. `image_studio_runtime/adapters/gpt_image_provider.py::GPTImageProvider.generate()` hết `NotImplementedError` — gọi thật `client.images.generate()`/`.edit()` (dependency-injected client, mặc định `openai.OpenAI()`). Còn thiếu: resolve `reference_asset_ids` → file ảnh thật (ref ảnh nằm ở `venho-os/ops/VenHoSocialManager/assets/`, cross-repo, chưa nối), và `generate_image_run()` chưa được gọi từ `daily_cycle.py` (pipeline hàng ngày chưa tự sinh ảnh).

Chỉ tắt workflow `venho-os/.github/workflows/social-content.yml` sau khi 3 gap trên hoàn thiện thật (đặc biệt: ref ảnh thật + daily_cycle gọi image gen + venho-os UI test qua browser) và test tay ít nhất 1 chu kỳ thật.

**Cập nhật 2026-08-04 — audit theo 27 DoD của `docs/Content agent/VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md` Phần 18 + việc 1-5 (chi tiết: `task_status.md` mục cùng ngày):**
- **Phát hiện gốc:** `daily_cycle.py` (bản 2026-08-04 sáng) bỏ qua toàn bộ safety rail v3.1 thật — không CreativeBrief, không qua M03, không khoá exact-version khi duyệt. Đã sửa: giờ build `CreativeBrief` LOCKED thật (contract-validated) → `run_content_pipeline` → `M05ContentBridge` (thật, gọi `content_studio`) → `M03ValidatorBridge` (claim + alignment gate) → chỉ queue khi `READY_FOR_REVIEW`. `approve_and_dispatch()` giờ dùng `automation_studio/approval_snapshot.py` thật (đã có sẵn từ trước, chưa ai dùng) để khoá exact-version tại thời điểm duyệt.
- **Research OS:** không dùng weather để demo R3 (R2-T theo thiết kế KHÔNG BAO GIỜ lên R3 — xem Phần 6.6 "Ranh giới quyết định", đây là hành vi đúng không phải bug). Thay vào đó phát hiện `seed_facts.json` đã có 4 fact `approved_by: harry` từ trước nhưng chưa từng persist — thêm CLI `venho-research load-seed-facts`, đã chạy thật. KHÔNG tự ý promote fact mới nào (founder gate, DoD #13 cấm auto-promote) — cần Harry xác nhận trước.
- **Ảnh:** ref ảnh thật hoá ra nằm ngay trong repo này (`assets/raw/`), không phải `venho-os` như ghi nhận cũ ở trên (đã kiểm tra lại). `agent_studio/growth/reference_asset_resolver.py` + `config/projects/venho_hotel/growth/reference_assets.yaml` map ID → file thật (chọn tạm, Harry nên duyệt lại). `daily_cycle.py` giờ sinh 1 ảnh thật/ngày qua M02 (`build_image_prompt`) → `GPTImageProvider`/`MockImageProvider`. Còn thiếu: ảnh chưa gắn vào payload webhook Make.com (cần bước upload lấy URL công khai, kiểu Google Drive upload cũ của VenHoSocialManager).
- **M08 Analytics:** `observe()` hết trả `pending_observation` giả — chạy chain thật (standardize/baseline/score/sentiment/advisory/report, lưu store thật) khi publication có `platform_post_id`. `metrics_adapter_factory` mặc định `MockMetricsAdapter` — chưa có adapter thật gọi FB/IG Insights hay Zalo OA (việc riêng, cần credentials).
- **Rủi ro thật phát hiện, CHƯA sửa (ngoài phạm vi việc 1-5):** `providers/openai_provider.py` gọi `load_dotenv(BASE_DIR / ".env")` ở top-level module import — bất kỳ test nào import module này rò `OPENAI_API_KEY` thật (từ file `.env` gốc, khác `.env.local`) vào `os.environ` cho cả tiến trình pytest. Đã tự vệ trong test của mình (luôn tiêm provider/`generate_image=False` tường minh, không dựa vào env default), nhưng bug gốc vẫn còn đó — bất kỳ ai thêm code mới đọc `os.environ` cho default nhạy cảm sẽ dính lại.
- **Audit tổng:** ~3/27 DoD đạt chắc chắn sau việc 1-5, phần lớn (Research OS 8/9 domain thật, hạ tầng Mac Mini/deadman switch, Analytics thật, blog SEO T3, 16-slot/4-tuần) vẫn chưa chạm — hệ thống ở khoảng Phase 3-4/8 theo roadmap gốc, không phải "growth agent hoàn chỉnh".

## 14. Task Closing Protocol

Khi người dùng nói **"kết thúc task"**, Codex phải tự động:

1. Cập nhật `task_memory.md` nếu có quy ước, kiến trúc, contract, CLI, hoặc integration seam mới.
2. Cập nhật `task_status.md` nếu module/stage/test count/commit/package mẫu thay đổi.
3. Ghi rõ commit hash, test command/kết quả, output mẫu nếu có.
4. Kiểm tra `git status --short` và báo working tree còn sạch hay còn thay đổi.
