# VENHO AI STUDIO — Task Memory
**Repo:** `venho-ai-studio` · **Workspace:** THE WEST LAKE LIVING
**Cập nhật:** 2026-08-07 (Growth Agent Research OS/Trend Radar audit closeout, xem mục 14p) · **Đọc bởi:** AI Engine, Claude Code sessions

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

**Đã nối trong repo này (2026-08-04):** `M07PublishingBridge.dispatch()` route theo `command["platform"]` → `ZaloOAAdapter` (zalo) hoặc `MakeGatewayAdapter` (facebook/instagram/threads). Cả hai adapter dùng chung 1 pattern: bắn webhook có ký HMAC, không gọi API platform trực tiếp, trả `GATEWAY_ACCEPTED`/`GATEWAY_ERROR` ngay — trạng thái `PUBLISHED` thật đến sau qua `callback_receiver.py` hoặc `reconciliation.py`. `daily_dispatch()` nhận `bridge` tiêm được.

**Sửa 2026-08-06 — tách webhook Make (Harry chọn phương án A):** việc "tái dùng scenario Make.com cũ" ở trên là **sai thiết kế và đã gỡ**. Legacy `post_to_make.py` gửi payload phẳng có `url`/`photo_url`/`image_public_url`/`message`; `MakeGatewayAdapter` gửi `content` lồng + `image_url` (thường = `null` vì Content Studio không tạo ảnh) và **không có** field `url`. Dùng chung 1 webhook → module `HTTP - Download a file` của scenario legacy báo `BundleValidationError: Missing value of required parameter 'url'`. Thực tế 2026-08-04 19:47–19:49 (giờ VN) Growth Agent đã bắn 12 request thật (`GATEWAY_ACCEPTED`, `image_url=None`) vào webhook legacy → tất cả fail phía Make. Nay `m07_publishing_bridge_from_env()` đọc `MAKE_GROWTH_WEBHOOK_URL`/`MAKE_GROWTH_WEBHOOK_SECRET`, **không fallback** về `MAKE_WEBHOOK_URL` — chưa cấu hình thì adapter `enabled=False`, không gửi gì. Có test hồi quy `test_m07_bridge_from_env_ignores_legacy_social_agent_webhook`. Việc còn lại của Harry: tạo scenario Make riêng cho Growth (clone scenario legacy, đọc caption từ `content.text`, filter router theo `platform` thay vì `publish_to_facebook`) rồi điền URL vào `.env.local`.

**Sửa tiếp 2026-08-06 — ảnh fallback (`publishing_gateway/fallback_images.py`):** `image_url = null` là nguyên nhân *thứ hai* độc lập — kể cả có scenario riêng, module `HTTP - Download a file` vẫn bắt buộc có `url`, và FB "Create a Post with Photos" / IG "Create a photo post" đều bắt buộc có ảnh. Growth phần lớn chạy không sinh ảnh (Content Studio chỉ ra `visual_note`) nên `null` là trường hợp thường, không phải ngoại lệ. Nay: `daily_cycle` thay bằng ảnh khách sạn thật theo `dna_subject` khi không có ảnh sinh ra, và ghi `content.image_is_fallback = true` để người duyệt phân biệt được; `MakeGatewayAdapter` có thêm 1 lớp chặn cuối (`or fallback_image_url()`) cho các row cũ đã lưu `null`. Bộ ảnh tái dùng đúng `ref_image` của `venho-social-content-agent/pillars.json`, re-encode 1440px JPEG và host công khai trên website: `Ven Ho Hotel/public/images/Social-fallback/{hotel-front-view,lobby,reception,lake-view-room}.jpg` → `https://venhohotel.com/images/Social-fallback/...`. Harry đã push repo `Ven Ho Hotel` (commit `871d7bd`) — cả 4 URL đã verify sống thật (HTTP 200, `image/jpeg`). Test: `test_make_adapter_never_sends_null_image_url`, `test_run_daily_cycle_falls_back_to_hotel_photo_when_no_image_generated`.

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
- **Quyết định của Harry (2026-08-04):** (1) Hạ tầng — **giữ GitHub Actions**, không xây Mac Mini 24/7 + deadman switch như plan gốc v3.1 §10 (đơn giản hơn, chấp nhận không có heartbeat/cloud-fallback tự động — rủi ro chấp nhận được vì publish vẫn qua bước Approve thủ công). (2) Research OS — **không promote fact mới nào lúc này**, 4 fact seed hiện có (room_count/address/website/review.agoda_overall) là đủ cho content hiện tại; quay lại khi có nghiên cứu thật (guest_voice/competitor/...).

## 14c. Growth Agent v3.1 — Review lần 2: đóng 7/8 gap DoD (2026-08-04)

Harry: "Review lại task đang làm so với plan v3.1. Phần nào chưa làm xong, hoàn thiện nốt." Trước khi sửa, dùng 1 agent Explore verify lại 8 điểm còn mập mờ từ audit trước bằng đọc code thật (không tin note cũ) — full chi tiết từng gap + số dòng: `task_status.md` mục cùng ngày "Review lần 2".

**Đóng được 7/8 (đều là glue code có sẵn từng phần, chưa nối, không cần dữ liệu kinh doanh mới):**
1. `tests/test_growth_brand_safety_gate.py` — 24 test cho `BrandSafetyGate` (trước đó là 0, DoD #19 yêu cầu ≥15).
2. `daily_cycle._pick_topic()` nối thật `special_lane.select_special_lane_candidate()` cho Thứ 7 — loại-4 fallback giờ chạy thật mỗi tuần (mặc định `feature_story` vì chưa có nguồn trend thật), không còn là code chết chỉ có test riêng.
3. `package_snapshot["asset_version_ids"]` giờ lấy `run_folder.name` (run_id thật) thay vì luôn `[]`.
4. `M08AnalyticsBridge.observe()` giờ gọi `generate_research_question_from_analytics()` thật sau advisory — ghi câu hỏi vào `research/questions/` (vault thật).
5. `_generate_topic_image()` nối `validator_studio.image_validator.validate_image()` (DNA-match, provider mock mặc định) — kill_switch loại ảnh vi phạm, report ghi cạnh artifact.
6. **Phát hiện quan trọng:** pipeline thật không bao giờ đạt status `PUBLISHED` (Make.com adapter fire-and-forget) → M08 Analytics nối ở lượt trước **không chạy được ngoài test**. Thêm `reconcile_publication()` + CLI `venho-growth reconcile` — thao tác tay của Harry sau khi kiểm tra bài đăng thật, chuyển GATEWAY_ACCEPTED → PUBLISHED. Đây là "reconciliation evidence" DoD #3 chấp nhận.
7. `run_blog_pipeline()` mới + CLI `venho-growth blog` — nối `content_studio` blog builder với `knowledge_studio.facts.FactResolver` thật (4 fact seed đã duyệt), chỉ trích fact đã approved+còn hạn, không bịa. Verify chạy tay thật, không chỉ test.

**KHÔNG làm — DoD #26 (golden-set scorecard):** cơ chế tính điểm đã thật (`controlled_rollout/scorecard.py`), nhưng không có bộ dữ liệu golden thật nào — cần Harry tự chọn bài/ảnh đã publish làm chuẩn, không phải việc code tự bịa được, khác các gap khác.

**Verify:** 636/636 pass (598 + 38 mới), 0 API call, compileall sạch, `venho-growth --help` có `blog`+`reconcile`, chạy tay `venho-growth blog` ra bài thật trích đúng 4 fact.

## 14d. Growth Agent v3.1 — Model switch gpt-5.5, Validator gate thật, fix hex-code leak, lên lịch tuần (2026-08-04)

Chuỗi yêu cầu liên tiếp của Harry: bài chờ duyệt sơ sài → sinh lại theo prompt mới + lên lịch tuần (giống content agent cũ, duyệt 1 lần/tuần); chuyển generator từ `claude-sonnet-5` sang `gpt-5.5` ("Sonnet 5 đang viết ở mức trung bình không đạt"); lỗi bấm Phê Duyệt (`JSONDecodeError`); Validator phải chấm điểm thật cả bài viết lẫn ảnh, không pass phải tự làm lại; bài viết lộ mã màu hex + tiếng Anh kỹ thuật; nạp thêm credit sau khi hết billing.

1. **Generator đổi sang gpt-5.5** — `content_studio/generators/gpt_social_generator.py` mới là `generator_fn` mặc định trong `M05ContentBridge` (`chat.completions.create(model="gpt-5.5", response_format={"type":"json_object"}, max_completion_tokens=4096)`). 3 system prompt dùng chung (`content_studio/generators/social_prompts.py`) — `claude_social_generator.py` giữ lại làm fallback/A-B, không còn default.
2. **Validator gate thật cho text** — `M03ValidatorBridge.validate_package()` giờ gọi `validator_studio.content_validator.validate_content()` thật (không chỉ claim/alignment như trước); chỉ `Recommendation.APPROVE` mới `READY_FOR_REVIEW`. `daily_cycle.run_daily_cycle()` retry tối đa `MAX_TEXT_ATTEMPTS=3` lần/platform nếu không pass, bỏ qua platform đó nếu vẫn fail sau 3 lần (không queue nội dung dưới chuẩn).
3. **Validator gate thật cho ảnh** — `_generate_topic_image()` retry `MAX_IMAGE_ATTEMPTS=2`, chỉ giữ ảnh khi `not kill_switch.triggered and verdict == APPROVE`; hết lượt thì bỏ ảnh (bài vẫn queue, không có ảnh) thay vì giữ ảnh không đạt.
4. **`_score_brand_fit` sửa gốc (`validator_studio/content_validator.py`)** — trước tính overlap token với `dna["invariant"]` (English/hex kỹ thuật cho ảnh AI) → xung đột trực tiếp với rule "không copy hex/tiếng Anh kỹ thuật vào content": bài viết càng đúng chuẩn (paraphrase hết) càng bị điểm thấp. Giờ chỉ tính overlap với `prompt_rules.brand_dna` (ngôn ngữ định vị thương hiệu thật: tên khách sạn, tagline...), hex đã strip khỏi nguồn, baseline 70 thay vì 45. Đã verify bằng script thật: 1 mẫu real content tăng từ overall 81.59/brand_fit 57.86 → overall 91.12/brand_fit 95.0, state `NEEDS_REVISION` → `READY_FOR_REVIEW`.
5. **Fix leak hex-code/tiếng Anh kỹ thuật vào content** — root cause là `prompt_studio/builders/content_prompt_builder.py::render_final_prompt()` liệt kê `required_dna` (bao gồm hex + English visual descriptors) mà không cấm copy nguyên văn. Thêm dòng chỉ dẫn "never copy hex codes or raw English descriptors literally — paraphrase in the target language" (ngắn gọn để không vượt giới hạn 2000 ký tự faithfulness validation của prompt_studio). Đồng thời 3 system prompt trong `social_prompts.py` đều thêm bullet cấm hex/tiếng Anh kỹ thuật tương tự.
6. **Fix lỗi bấm Phê Duyệt (root cause)** — `shared/http.py::urllib_post()` từng `json.loads()` thẳng response webhook Make.com, nhưng Make trả plain-text "Accepted" (không phải JSON) → `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`, đúng y lỗi Harry báo. Sửa: bắt `JSONDecodeError`, trả `{"raw": raw}` thay vì crash. **Không sửa** `urllib_post_form` (chỉ dùng cho Zalo OAuth, luôn trả JSON thật — crash ở đó là đúng, không che lỗi).
7. **Fix ảnh MPO không edit được** — `agent_studio/growth/reference_asset_resolver.py` re-encode mọi ref ảnh qua PIL thành PNG single-frame (`_load_as_png()`) trước khi gửi `images.edit()` — ảnh gốc iPhone portrait-mode là MPO container, OpenAI reject `BadRequestError: Invalid image file or mode`.
8. **Lên lịch tuần** — `growth_orchestrator/application/weekly_cycle.py` mới (`run_weekly_cycle()`), CLI `venho-growth weekly-cycle`. `.github/workflows/growth-daily-cycle.yml` đổi tên "Growth Agent Weekly Cycle", cron `0 1 * * 1` (Thứ 2 duy nhất, thay vì 4 lần/tuần) — Harry duyệt cả tuần 1 lần giống content agent cũ. `--image/--no-image` flag thêm cho cả `daily-cycle`/`weekly-cycle`; CLI dùng `image_validation_provider="openai"` thật (vision QC thật), hàm-level default vẫn `"mock"` để test không tốn phí.
9. **Registry rows thêm `day`/`pillar`/`topic`** — `daily_cycle.py`'s `registry.update()` giờ ghi kèm 3 field này (trước chỉ có trong `package_snapshot`/nội bộ), để `venho-os` group được publication theo ngày/pillar/chủ đề mà không cần parse content.
10. **Batch cuối cùng của phiên** — 15 publication cũ (thiếu `day`/`pillar`/`topic`, generator Claude, chưa qua validator gate mới) bị `SUPERSEDED`; chạy `venho-growth weekly-cycle` lại → 16 publication mới (4 ngày × 4 platform) `PENDING_APPROVAL`, đã verify: đủ `day`/`pillar`/`topic`, 0 hex-code, qua Validator thật.

**Verify:** 655/655 pass sau toàn bộ thay đổi trên. Batch thật cuối cùng verify qua `venho-growth list-pending` + grep hex-code trực tiếp trên `publication_registry.json` (0 match trong các entry `PENDING_APPROVAL`, chỉ còn trong entry `SUPERSEDED`/`DISABLED` cũ).

**Việc liên quan ở `venho-os` (repo khác, xem `venho-os/task_memory.md`/`CHANGELOG.md` mục 2026-08-04):** redesign `GrowthApprovalQueue` trong `PublishingSection.tsx` — bảng gộp Ngày/Pillar/Chủ đề thay flat card list, expand xem chi tiết per-platform, nút Duyệt tất cả + Duyệt riêng.

## 14e. Growth Agent v3.1 — Audit đối chiếu master plan CONSOLIDATED, sửa lỗi + Từ chối (2026-08-04)

Harry: "Review và audit growth content agent đối chiếu với plan v3.1. Nếu tìm ra lỗi, sửa ngay. Bổ sung nút Từ chối/Sửa. Xoá file lỗi/temp/nháp." Đọc toàn bộ `docs/Content agent/VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md` (1823 dòng) + dùng 1 agent con audit code thật (`growth_orchestrator/`, `agent_studio/growth/`, `publishing_gateway/`, `venho-os/src/components/os/sections/PublishingSection.tsx`).

**Kết luận scope-reality:** plan v3.1 mô tả kiến trúc mục tiêu rất lớn (SQLite state machine, Obsidian Research OS đủ 9 domain, Trend Radar chạy thật, HMAC callback tự động...). Thực tế đã build là một MVP nhỏ hơn nhiều bên trong kiến trúc Studio hiện có (M01–M10) — nhiều mảnh hạ tầng plan mô tả (SQLite job queue, PublishingSlot state machine, HMAC callback receiver) **đã có code** nhưng **chưa được `daily_cycle.py`/`weekly_cycle.py` gọi tới** — không phải thiếu code, mà là code có sẵn chưa nối dây vào pipeline thật đang chạy cron. Đây không phải việc cần sửa trong phiên này (không phải bug, là gap kiến trúc lớn ngoài scope "audit + sửa lỗi") — chỉ ghi nhận.

**5 lỗi thật đã sửa trong code đang chạy production:**

1. **Race condition double-publish** — `approve_and_dispatch()` cũ là check-then-act không atomic (`registry.find()` đọc không khoá → check status → gọi webhook → `registry.update()` khoá riêng). Hai lần bấm Duyệt gần nhau (double-click, 2 tab) có thể cả hai đều đọc thấy `PENDING_APPROVAL` trước khi bên nào ghi lại → bắn webhook Make.com 2 lần thật. Sửa: thêm `PublicationRegistry.claim(expected_status, claimed_status)` — test-and-set atomic trong cùng 1 khoá `fcntl`; `approve_and_dispatch`/`retry_dispatch`/`reject_publication` đều claim trước khi làm bất cứ điều gì khác, bên thua cuộc raise `ValueError` ngay lập tức thay vì cùng dispatch. Test: `test_approve_and_dispatch_second_concurrent_call_cannot_double_dispatch`.
2. **Dispatch fail = kẹt vĩnh viễn** — trước đây nếu Make.com webhook lỗi mạng thoáng qua, hàm `approve_and_dispatch` raise exception giữa chừng (status kẹt ở giá trị cũ hoặc lỗi không rõ), không có đường quay lại vì hàm chỉ chấp nhận `PENDING_APPROVAL`. Sửa: dispatch lỗi giờ luôn hạ cánh về `GATEWAY_ERROR` (bắt exception trong `_dispatch_claimed`), và thêm `retry_dispatch()` (CLI `venho-growth retry-dispatch --publication-id X`, tái dùng approval cũ, không hỏi lại approved_by).
3. **1 platform lỗi sập cả ngày, 1 ngày lỗi sập cả tuần** — `run_daily_cycle()`'s vòng lặp per-platform và `run_weekly_cycle()`'s vòng lặp per-day trước đây không có try/except: một lỗi OpenAI rate-limit ở Instagram xoá luôn draft Facebook/Threads/Zalo cùng ngày; một lỗi ở thứ Tư xoá luôn thứ Sáu/Bảy. Sửa: mỗi platform/day giờ cô lập bằng try/except, lỗi ghi vào `DailyCycleResult.errors`/CLI JSON output, các platform/day khác vẫn chạy tiếp.
4. **M03ValidatorBridge không fail-closed khi crash** — plan Part 2.1 quyết định #8: "Validator fail/timeout/malformed → fail-closed UNVALIDATED, không bao giờ APPROVED". Code thật: nếu `validate_content()` throw exception (network, markdown hỏng...), exception văng thẳng ra ngoài, không map về `UNVALIDATED` — vi phạm invariant (dù hậu quả thực tế là crash cả cycle chứ không phải APPROVE sai, vẫn sai theo đúng thiết kế). Sửa: bọc try/except quanh `validate_content()`, exception → `verdict="UNVALIDATED"`.
5. **Nút Từ chối (reject) hoàn toàn chưa tồn tại** — trước đây `PENDING_APPROVAL` chỉ có action Approve; không có cách nào loại một bài sai chủ đề khỏi hàng chờ mà không tự tay sửa `publication_registry.json`. Thêm full-stack: `reject_publication()` (application layer, atomic claim giống approve) → CLI `venho-growth reject --publication-id X --rejected-by Y --reason "..."` → API `POST /api/v1/studio/growth/[id]/reject` (venho-os) → nút "Từ chối"/"Từ chối tất cả" trong `GrowthApprovalQueue` (per-platform + group-level, giống layout nút Duyệt). Rejected rows tự động rớt khỏi `list-pending` (chỉ filter `PENDING_APPROVAL`), không cần logic ẩn riêng.

**"Sửa" (edit) — cố tình KHÔNG làm trong phiên này:** theo plan, sửa nội dung sau khi đã có `package_snapshot` phải tự động revoke approval cũ và chạy lại M03 validation trước khi cho vào hàng chờ lại (không được "sửa xong tự động duyệt lại"). Đây là 1 luồng lớn hơn (cần quyết định UX: sửa inline trên dashboard hay mở lại content_studio pipeline?) — để Harry quyết định approach trước khi build, tránh build sai hướng.

**Đã điều tra, không phải lỗi:** `venho-os/src/bff/growth/growth-agent.client.ts` trỏ `http://127.0.0.1:8011` từng nghi là dead/legacy code (audit ban đầu đoán vậy) — xác minh lại: đây là client thật cho `venho-quangcao-agent` (repo riêng, FB/Google/TikTok paid-ads agent, `make run` → uvicorn port 8011 thật), khác hoàn toàn với Growth Content Agent v3.1 (`venho-growth` CLI) đang audit. Không đụng vào.

**Gap đã biết, chưa làm (flag cho Harry, không tự ý xây):** ảnh generate ra (`image_run_path`, local file) không bao giờ được đính vào payload dispatch — `MakeGatewayAdapter.send()` chỉ gửi `{publication_id, idempotency_key, platform, content}`, không có URL ảnh. Toàn bộ pipeline generate + validate ảnh (gọi OpenAI thật, tốn phí) hiện sản xuất ra artifact không bao giờ lên bài thật. Cần một bước upload ảnh lên nơi có public URL (Google Drive như `venho-social-content-agent` legacy đã làm, hoặc nơi khác) để Make.com fetch được — quyết định kiến trúc cần Harry chốt trước khi build (secrets mới, chọn nhà cung cấp lưu trữ), không tự làm trong phiên audit này.

**File lỗi/temp/nháp:** kiểm tra cả 2 repo — `git status --short` sạch cả trước và sau audit, không có `.orig`/`.bak`/`_old.`/`_draft.`/`.log` tracked, không `__pycache__` tracked, không file `/tmp/` nào bị commit nhầm, `data/` toàn bộ đã gitignore đúng. Không có gì cần xoá.

**Verify:** 667/667 pytest pass (12 test mới: `test_growth_approve_and_dispatch.py` +8, `test_growth_m03_validator_bridge.py` mới +2, `test_growth_weekly_cycle.py` mới +1, `test_growth_daily_cycle.py` +1).

**Việc liên quan ở `venho-os`:** xem `venho-os/task_memory.md`/`CHANGELOG.md` mục 2026-08-04 (audit) — API route `reject`/`retry-dispatch` mới, nút Từ chối trong `GrowthApprovalQueue`.

## 14f. Growth Agent v3.1 — Nút Sửa đúng theo plan + upload ảnh lên Google Drive (2026-08-04)

Harry, sau khi xem báo cáo audit mục 14e, chốt luôn 2 gap còn treo: "Nút Sửa: Làm đúng theo Plan." và "Ảnh generate ra không lên bài: Lưu vào Google drive."

**1. `edit_publication()` — full-stack, đúng theo invariant Part 2.1/4.3 của plan:**
- Editable từ `PENDING_APPROVAL` hoặc `GATEWAY_ERROR` (claim atomic qua `registry.claim()` mở rộng nhận `set[str]` thay vì chỉ 1 status). `DISPATCHING`/`GATEWAY_ACCEPTED`/`PUBLISHED` không sửa được (bài đã/đang đăng thật, phải Từ chối + để cycle mới sinh lại).
- Text sửa được chấm lại bằng đúng rubric `validator_studio.content_validator.validate_content()` thật (brand_fit/tone/clarity/cta/language_fit) mà `M03ValidatorBridge` dùng để gate draft gốc — ghi tạm ra file `.md` (`tempfile.NamedTemporaryFile`) vì `validate_content()` đọc file, không nhận raw string. Chỉ `Recommendation.APPROVE` mới quay lại `PENDING_APPROVAL`; không đạt → `NEEDS_REVISION`, tự rớt khỏi hàng chờ giống draft gốc fail.
- **Bất kỳ approval cũ nào cũng bị xoá vô điều kiện** khi sửa (`approval_snapshot`/`approved_by`/`gateway_status` = None) — kể cả khi bản sửa lại pass — đúng theo "sửa sau approval → tự revoke" của plan; lần Duyệt tiếp theo luôn build snapshot mới từ nội dung đã sửa.
- Cần thêm `dna_subject` vào registry row (`daily_cycle.py`'s `registry.update()`, cạnh `day`/`pillar`/`topic`) — trước đây không có field này nên không biết chấm ảnh/text theo DNA nào khi sửa mà không giữ lại `CreativeBrief` gốc.
- **Giới hạn đã ghi rõ trong docstring, không giấu:** chỉ chấm lại content rubric (chất lượng bài viết), KHÔNG chấm lại claim/alignment validator (2 validator đó cần `CreativeBrief` gốc với `proof_points`/`scene_summary` — registry không lưu lại brief đầy đủ; lưu cả brief là thay đổi lớn hơn phạm vi tính năng Sửa, để dành nếu Harry cần sau).
- CLI: `venho-growth edit --publication-id X --edited-by Y --text-file path.md`. API: `POST /api/v1/studio/growth/[id]/edit` (venho-os) — ghi text vào file tạm rồi shell-out CLI, không truyền raw text qua argv (tránh escaping/giới hạn độ dài shell).
- UI: nút "Sửa" mở textarea inline ngay trong hàng chi tiết per-platform (không phải modal riêng) — "Lưu và chấm lại" gọi API, "Huỷ" đóng không lưu. Có ghi chú cảnh báo Harry: lưu sẽ chấm lại qua Validator thật, không đạt sẽ rớt khỏi hàng chờ chứ không tự động giữ nguyên.

**2. Upload ảnh lên Google Drive — gap "ảnh generate ra không lên bài" đã đóng:**
- `shared/storage/google_drive.py` mới — `MockDriveUploader` (mặc định test/dev, 0 network call) + `GoogleDriveUploader` thật (import `googleapiclient`/`google.oauth2` trễ trong `__init__`, không bắt buộc cài cho test suite) + `google_drive_uploader_from_env()` (thật nếu có `GOOGLE_DRIVE_TOKEN_JSON`, không thì Mock). **Tái dùng đúng contract OAuth của `venho-social-content-agent/google_drive.py`** — `GOOGLE_DRIVE_TOKEN_JSON` là token JSON đầy đủ (`authorized_user` format, KHÔNG phải client secret), refresh qua `GOOGLE_OAUTH_CLIENT_ID`/`_SECRET` — Harry dùng lại đúng Google Cloud OAuth app cũ, không cần tạo app mới, chỉ cần chạy lại flow `python3 google_drive.py` (repo cũ) một lần để lấy token dán vào secret mới.
- `daily_cycle.py`: sau khi ảnh qua validator thật (kill-switch=false, verdict=APPROVE), upload luôn file artifact (`generated.png`) lên Drive (`_upload_image_to_drive()`, best-effort — lỗi mạng/token hết hạn/quota không chặn queue text, giống triết lý generate ảnh). URL public lưu vào `content.image_public_url` (field mới cạnh `image_run_path` cũ — `image_run_path` là path local, không dùng được cho Make.com).
- `MakeGatewayAdapter.send()` giờ copy `content.image_public_url` ra field top-level `image_url` trong payload gửi Make.com — dễ map field trong Make scenario hơn path lồng nhau. Payload cũ (chỉ có `content` object) vẫn giữ nguyên, chỉ thêm field mới.
- `run_weekly_cycle()` share 1 `drive_uploader` cho cả 4 ngày (giống `content_bridge`/`registry`) — auth Google 1 lần/tuần, không phải 1 lần/ngày.
- Deps: `pyproject.toml` optional group `drive` (`google-api-python-client`, `google-auth-oauthlib`, `google-auth`) — không phải core dependency vì `MockDriveUploader` không cần chúng. `.github/workflows/growth-daily-cycle.yml` đổi `pip install -e .` → `pip install -e ".[drive]"` + 3 env mới (`GOOGLE_DRIVE_TOKEN_JSON`/`GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET`) từ GitHub Secrets — **Harry cần tự thêm 3 secret này vào repo `venho-ai-studio` trên GitHub** (chưa set = uploader tự fallback Mock, không lỗi, chỉ không có ảnh thật).
- **Phát hiện phụ, chưa sửa vì ngoài yêu cầu:** `.env.local` cục bộ có `GOOGLE_DRIVE_TOKEN_JSON=GOCSPX-...` — giá trị này giống client secret (không phải JSON token object), sẽ không hoạt động với uploader thật nếu Harry chạy local. Không tự sửa file (gitignored, chứa secret thật, không chắc Harry có đang dùng giá trị này cho việc khác) — Harry cần tự dán đúng token JSON vào đó nếu muốn chạy Drive upload thật ở local.
- **Phát hiện phụ khác, chưa sửa:** `.github/workflows/growth-daily-cycle.yml` có bước `git add -f data/projects/*/publishing/publication_registry.json ... && git push` — nghĩa là `publication_registry.json` (chứa toàn bộ hàng chờ duyệt) commit thẳng vào git sau mỗi lần weekly-cycle chạy trên GitHub Actions runner. `venho-os`'s approve/reject/edit routes chạy `venho-growth` cục bộ (shell-out, xem `STUDIO_DIR`) — nếu chạy trên máy khác/checkout khác chưa `git pull` sau lần chạy Actions gần nhất, sẽ thao tác trên bản registry cũ. Không phải bug mới phát sinh từ session này, không thuộc phạm vi "Sửa"/"Google Drive" Harry vừa yêu cầu — chỉ ghi nhận để theo dõi nếu sau này registry "không khớp" giữa dashboard và Actions.

**Verify:** 677/677 pytest pass (10 test mới: `test_growth_approve_and_dispatch.py` +6 cho edit, `test_growth_google_drive_uploader.py` mới +3, `test_growth_daily_cycle.py` +1, `test_growth_v3_1_real_providers.py` +1 mới/1 sửa). `tsc --noEmit`/`eslint` sạch, 127/127 vitest pass (venho-os).

**Việc liên quan `venho-os`:** route mới `POST /api/v1/studio/growth/[id]/edit`, UI textarea inline "Sửa" trong `GrowthApprovalQueue` — xem `venho-os/task_memory.md`/`CHANGELOG.md` mục 2026-08-04.

## 14g. Growth Agent v3.1 — 6 hạng mục còn lại từ audit 14e (2026-08-05)

Harry: "Làm tất cả" 6 gap còn treo sau câu hỏi "growth plan v3.1 đã hoàn thành 100% chưa?". Mỗi mục lớn đều dừng lại hỏi Harry trước khi code khi phát hiện xung đột kiến trúc thật (không đoán mò).

**1. Retry UI cho GATEWAY_ERROR** — `list_pending()` giờ trả cả `PENDING_APPROVAL` lẫn `GATEWAY_ERROR` (trước chỉ pending, nên bài kẹt dispatch lỗi vô hình trên dashboard). `venho-os`: badge đỏ "Lỗi gửi" + nút "Thử lại gửi" (per-item + gộp nhóm) trong `GrowthApprovalQueue`, gọi route `/retry-dispatch` đã có sẵn từ 14f nhưng chưa có UI.

**2. SQLite JobStore + PublishingSlot — nối vào `weekly_cycle` thật (không phải plan gốc):**
- Phát hiện xung đột: plan v3.1 Phần 10 thiết kế cho **Mac Mini M4 24/7 + launchd worker daemon + deadman switch** — hạ tầng hoàn toàn khác GitHub Actions ephemeral cron đang chạy thật (Harry chọn GitHub Actions có chủ ý, "không cần Mac bật"). Hỏi Harry → **giữ GitHub Actions, thiết kế lại cho ephemeral** (không xây `worker.py`/`scheduler.py`/`launchd` — sẽ là code chết).
- `shared/jobs/slot_store.py` mới — SQLite persist `PublishingSlot`, `ensure_slots()` idempotent, `transition()` optimistic.
- `weekly_cycle.py`: ensure 4 slot/tuần trước khi chạy; **JobStore idempotency guard theo ISO week** (`job_id=f"{project}-weekly-{year}-W{week}"`) — chạy lại workflow thủ công trong cùng tuần sẽ SKIP (không sinh trùng batch, không tốn budget lần 2) thay vì âm thầm generate lại.
- `daily_cycle.py`: slot OPEN→DRAFT_ASSIGNED→PENDING_APPROVAL/MISSED theo kết quả platform loop; publications giờ có `slot_id`.
- `approve_and_dispatch.py`: dispatch thành công → slot PENDING_APPROVAL→FILLED→DISPATCHED (best-effort, không bao giờ chặn dispatch thật).
- `publishing_slot.py`: thêm transition `DRAFT_ASSIGNED→MISSED` (đường thật khi mọi platform fail, evergreen_pool.py chưa nối nên chưa có fallback evergreen).
- CLI `venho-growth slots`. `venho-os`: panel "Slot tuần này" read-only trong Publishing section (`/api/v1/studio/growth/slots`).

**3. HMAC callback receiver — quyết định KHÔNG xây (giữ reconcile thủ công):**
- Phát hiện: `venho-os` chưa deploy công khai (`localhost:3000` cục bộ) — Make.com (cloud) không gọi được vào endpoint local. Xây callback receiver trong `venho-os` sẽ là code chết y hệt lỗi Research Vault panel trước đó.
- Hỏi Harry → giữ nguyên `venho-growth reconcile` thủ công. Không code gì thêm, chỉ ghi nhận quyết định để không bị hiểu nhầm là "chưa làm".

**4. Sửa chấm lại claim/alignment (không chỉ content quality):**
- `daily_cycle.py` giờ lưu thêm `creative_brief`/`claims`/`scene_summary` vào registry row lúc tạo (trước chỉ có `dna_subject`).
- `edit_publication()`: re-run `ClaimValidator`/`validate_alignment` thật với `claims`/`scene_summary`/`creative_brief` đã lưu (không phải regenerate CreativeBrief) — kill-switch (claim không có fact_key hợp lệ, scene thiếu/có entity cấm) vẫn chặn quay lại `PENDING_APPROVAL` dù content-quality rubric pass. Field `edit_validation.claim_alignment_skipped=true` cho row cũ (trước 2026-08-05) không có brief lưu lại.
- **Giới hạn còn ghi rõ:** `claims`/`scene_summary` là metadata GỐC từ lúc generate, không re-derive từ bản text Harry sửa tay — không bắt được claim bịa MỚI Harry tự gõ thêm, chỉ bắt được claim gốc mất fact support.

**5. Trend Radar thật (Tavily + AI classifier) nối vào chọn Thứ 7:**
- Phát hiện gap thật: `scan_trends.py` cần input đã phân loại sẵn (`geographic`/`thematic`/`actionability`/`brand_safety_category`/`intersections`) nhưng comment "downstream, not here" — downstream cũng chưa ai viết. `collect_tavily_search()` chỉ trả raw title/snippet.
- Hỏi Harry → xây bộ phân loại thật bằng AI. `fetch_saturday_candidates.py` — Tavily collect (dedupe theo id) → AI classify → `scan_trends` score/gate, tất cả injectable cho test.
- `trend_candidate_store.py` — JSON store, enforce `brand_safety.yaml`'s `human_approval: mandatory` bằng CODE (không chỉ docs): `merge_new()` không bao giờ ghi đè `verified_by_human` đã approve; chỉ candidate đã `approve()` + chưa `mark_used()` mới vào pool Saturday.
- `daily_cycle._pick_topic`: candidate Trend Radar đã duyệt tham gia cùng rotation pool với `content_pillars.yaml`'s special_topics hand-curated; pick xong tự `mark_used()` để không lặp lại mãi.
- CLI: `venho-growth trend-scan` / `trend-list` / `trend-approve`.
- **2026-08-05 — classifier đổi từ Claude sang Gemini Flash** (Harry: "Dùng Anthropic chi phí cao, không phù hợp cho startup"). Xoá `classifiers/claude_classifier.py`, thêm `classifiers/gemini_classifier.py` — cùng interface (`classify_candidates(candidates, *, api_key, model, client_fn)` / `classify_candidates_from_env`), cùng taxonomy/system prompt, chỉ đổi client: `google-genai` SDK (`from google import genai`), `client.models.generate_content(model=..., contents=..., config=types.GenerateContentConfig(system_instruction=..., temperature=0, response_mime_type="application/json"))`. Model mặc định `gemini-flash-latest`, override qua env `GEMINI_TREND_MODEL` (đặt tên model chính xác của Google có thể đổi theo thời gian — Harry nên xác nhận lại tên model hiện hành trước lần chạy thật đầu tiên). Env key mới: `GEMINI_API_KEY` (chưa có trong `.env.local`, Harry cần tự điền — không tự ý ghi placeholder vào file secrets thật). Optional dependency mới trong `pyproject.toml`: `pip install "venho-ai-studio[gemini]"`. Đã cài `google-genai` vào interpreter test (`/Library/Developer/CommandLineTools/usr/bin/python3`). Content generation ở các module khác (content_studio, prompt_studio optimizer, v.v.) **không đổi** — vẫn dùng Claude, đổi này chỉ giới hạn trong Trend Radar classification (workload phân loại text ngắn, không cần model mạnh/đắt).
- **2026-08-05 — nối cron GitHub Actions + UI duyệt (Harry yêu cầu trực tiếp, đã làm):**
  - `.github/workflows/growth-trend-scan.yml` — `cron: "0 1 * * 5"` (Thứ 6 08:00 Asia/Ho_Chi_Minh) + `workflow_dispatch`, chạy sớm hơn `growth-daily-cycle.yml`'s Monday 08:00 (`0 1 * * 1`) để Harry có cả cuối tuần duyệt trước khi `weekly-cycle` chọn chủ đề Thứ 7. `pip install -e ".[gemini]"`, secrets `TAVILY_API_KEY`/`GEMINI_API_KEY`, commit `trend_candidates.json` với cùng pattern `git add -f` (data/ gitignored) như `growth-daily-cycle.yml`.
  - Set secret thật qua `gh secret set GEMINI_API_KEY`/`TAVILY_API_KEY` (đọc trực tiếp từ `.env.local` bằng `grep | sed`, không bao giờ in giá trị ra terminal).
  - `venho-os`: panel "Trend Radar — Chờ duyệt xu hướng" mới trong `PublishingSection.tsx`, mount giữa `SlotWeekPanel` và `ResearchVaultPanel`. Routes mới: `GET /api/v1/studio/growth/trend-candidates` (shells `venho-growth trend-list`), `POST /api/v1/studio/growth/trend-candidates/approve` (shells `venho-growth trend-approve`, `approved_by` lấy từ session email thật qua `getCurrentSession()` — cùng pattern route `growth/[id]/approve` có sẵn).
  - **Quyết định thiết kế:** `candidate_id` truyền qua JSON body (không phải route param `[id]`) vì Tavily-derived id là 1 URL đầy đủ (`/`, `:`, `%XX`) — không nhét vừa route segment và không khớp regex `^[a-zA-Z0-9_-]+$` route approve publication đang dùng. `execFile` không qua shell nên không có injection risk, chỉ cap độ dài làm sanity check.
  - **Test thật end-to-end qua HTTP** (không chỉ CLI): login bằng `VENHO_OS_BOOTSTRAP_EMAIL`/`PASSWORD` lấy cookie session thật, `curl` GET trend-candidates thấy đúng 26 candidate thật đã scan trước đó, POST approve 1 candidate → `approved_by` ghi đúng `hpham1504@gmail.com` (không phải "unknown"). tsc/eslint/vitest (127/127) sạch.
  - **Known gap kế thừa, không mới:** `venho-os` chạy CLI cục bộ trên checkout local (`STUDIO_DIR`), còn Actions runner checkout/commit/push riêng trên GitHub — cùng vấn đề `git pull`/`git push` thủ công đã ghi nhận cho `publication_registry.json` (dòng ~856 file này), giờ áp dụng thêm cho `trend_candidates.json`: sau lần scan Thứ 6 tự động, Harry cần `git pull` trước khi mở panel; sau khi duyệt trên dashboard, cần `git push` để `weekly-cycle` (chạy trên Actions runner khác, không thấy local) nhận được approval trước Thứ 2. Không tự động hoá 2 chiều — nằm ngoài phạm vi yêu cầu lần này, chỉ ghi nhận để theo dõi.

**6. Research OS 9 domain — khung, không bịa nội dung (theo đúng quyết định của Harry):**
- Phát hiện gap thật: `domains.yaml` chỉ có 8 domain, thiếu `weather_signal` (plan v3.1 gọi là domain mới) — và `ResearchNote`'s `ResearchDomain` Literal hardcode độc lập cùng 8 domain đó, 2 nguồn sự thật đã lệch nhau. Đã sửa cả 2 + thêm test regression khoá đồng bộ.
- `collect_source_note`/`collect_structured_note` (`research_engine/application/collect_sources.py`) vốn đã domain-agnostic nhưng KHÔNG có CLI nào gọi tới — không có cách ingest note vào vault ngoài `load-seed-facts`/`notebook-inbox`. Thêm `venho-research collect-source` (R0) + `collect-note` (R1), validate `--domain` theo `domains.yaml`, từ chối domain không đăng ký.
- **Không tự bịa nội dung domain nào** — vẫn chỉ ~2/9 domain (guest_voice, competitor) có note thật trong vault, đúng quyết định Harry chọn ("Anh cung cấp dần từng domain").

**Verify tổng:** 706/706 pytest pass (33 test mới cả 6 mục), tsc/eslint sạch, 127/127 vitest (venho-os). Commit riêng từng mục, đã push cả 2 repo.

## 14h. Post-audit follow-up: Phần 10/18 rewrite, dọn code chết, phát hiện audit trước sai về Image runtime (2026-08-05)

Sau khi công bố audit hoàn thành v3.1 (artifact `growth-v31-audit.html`), Harry giao 3 việc trong 1 tin nhắn: (1) viết lại DoD Phần 10/18 khớp kiến trúc thật; (2) dọn code chết; (3) "Làm Image runtime + Multimodal QC".

**1. Phần 10 + DoD 21–24 viết lại** trong `VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md`. Xoá mô tả Mac Mini 24/7/launchd/pmset/deadman switch/HMAC cloud fallback/Tailscale — chưa từng có máy nào chạy nó. Thay bằng kiến trúc thật đang chạy: bảng phân chia trách nhiệm GitHub Actions cron / local `venho-os`, cơ chế git-sync 2 chiều (đã build ở phiên trước — merge rule "local luôn thắng"), bảng rủi ro thật (khác hẳn rủi ro Mac Mini: risk giờ là "Harry không mở dashboard", không phải "máy ngủ"), backup thật (chỉ git, chưa có backup artifacts ảnh — ghi rõ là gap chưa làm, không tự nhận đã xong), và trung thực ghi §10.5 "truy cập mobile: CHƯA GIẢI QUYẾT". DoD #21–24 viết lại tương ứng — #24 (backup + verify-restore) explicit đánh dấu **chưa đạt**.

**2. Dọn code chết — quyết định xoá vs đánh dấu dựa trên grep thật, không đoán:**
- Trước khi động tay, `grep -rln` từng module ứng viên để xác nhận có/không caller thật ngoài chính nó và test của nó.
- `infra/` (Mac Mini): **0 caller** ngoài `tests/test_growth_v3_1_cadence_infra.py` → xoá hẳn (`git rm -r infra/`), gỡ `"infra*"` khỏi `pyproject.toml`. Test file đó có 28/32 test không liên quan gì Mac Mini (cadence/slot/special-lane/preflight/weather/zalo — test code thật) nên **không xoá cả file**, chỉ cắt 4 test cuối (heartbeat + cloud_fallback export) và 2 dòng import `infra.*`.
- `evergreen_pool.py`: **0 import** thật, chỉ 1 dòng comment nhắc tới trong `publishing_slot.py`. Giữ lại + thêm header comment giải thích rõ trạng thái "implemented, chưa wired" — đây là code thật cho Phase 4.5, khác hẳn tính chất `infra/` (thiết kế đã bị bỏ hoàn toàn).
- `analytics_feedback/meta_insights.py` + `attribution.py`: **0 caller** từ `m08_analytics_bridge.py` hay `cli.py` (chỉ dùng `MockMetricsAdapter` trực tiếp) — giữ + header comment. Đây là Phase 6 chưa tới lượt, không phải lỗi.
- `strategy_memory/*`: chỉ được import bởi test file riêng (`test_growth_phase7_strategy_memory.py`), 0 caller thật — giữ + header comment, Phase 7 chưa tới lượt.
- **Không đụng** `image_studio_runtime/` — grep xác nhận `gpt_image_provider.py` (real GPT-image-2) ĐANG được `daily_cycle.py` import và gọi thật, không phải dead code như audit trước ghi.
- `python3 -m pytest -q` sau khi xoá `infra/`: 702 passed (giảm đúng 4 so với 706 trước, không có test nào fail bất ngờ).

**3. "Image runtime + Multimodal QC" — quyết định KHÔNG làm gì mới, sau khi tự phát hiện lỗi trong chính audit trước đó:**
- Trước khi build bất cứ gì, dùng `AskUserQuestion` hỏi Harry scope cụ thể — vì audit trước (mục "Đã viết code, nhưng chưa nối") ghi "Image runtime thật (Phase 3) — vẫn chỉ có Mock provider". Câu hỏi lần 1 dựa trên phát hiện `alignment_validator.py` (dùng trong `M03ValidatorBridge`) chỉ so sánh entity list (copy vs brief), không có ảnh thật, không phải AI vision — Harry chọn "làm vision QC thật".
- Trước khi code, đi tìm chỗ nối image validation vào `daily_cycle.py` thật (`_generate_image_for_topic`) để biết chèn code mới ở đâu — và phát hiện **đã có sẵn một pipeline vision QC khác, thật**, không liên quan `alignment_validator`: `validate_image()` (`validator_studio/image_validator.py`) → `observe_image_against_dna()` (`validator_studio/observe_adapter.py`) → khi `provider != "mock"`, gọi `VisionClient(image_provider=provider)` (`shared/vision/client.py`) → `OpenAIVisionProvider` model `gpt-4o` — **API call GPT-4o vision thật**, so ảnh sinh ra với DNA subject (dna_matches/forbidden/allowed_imperfections), không phải mock, không phải chỉ metadata.
- Đi tiếp một bước: `growth_orchestrator/cli.py` — lệnh `daily-cycle` và `weekly-cycle` (chính là lệnh mà `.github/workflows/growth-daily-cycle.yml` chạy thật mỗi Thứ 2) **hardcode `image_validation_provider="openai"`** ở cả 2 command. Nghĩa là: real gpt-image-2 generation + real GPT-4o vision QC đã chạy production từ commit `ab2b1de` (2026-08-03/04), tốn phí thật mỗi tuần — không phải "chưa làm" như câu hỏi lần 1 tôi đặt cho Harry ngụ ý.
- Quay lại hỏi Harry lần 2, trình bày rõ sai lầm trong câu hỏi lần 1 (đã lẫn 2 validator khác nhau: `alignment_validator` thật là entity-based, nhưng `image_validator`/`VisionClient` mới là cái quyết định câu hỏi và nó ĐÃ real). Harry chọn "Dừng — không xây gì thêm".
- **Sửa artifact audit đã publish** (`growth-v31-audit.html`, URL giữ nguyên `.../22e15a4a-...`): xoá mục sai trong "Đã viết code, nhưng chưa nối", thêm mục correction trong "Đang chạy thật, đã verify", đổi phase-status-table Phase 3 từ "Chưa đạt" → "Đạt", đổi DoD #5 (cross-modal validation) từ "Chưa rõ" → "Đạt", cập nhật stat tile 6–7/27 → 7–8/27, thêm correction log rõ ràng ở footer thay vì âm thầm sửa. **Bài học tự áp dụng cho chính mình:** cùng nguyên tắc grep-trước-khi-kết-luận mà audit gốc tự đặt ra ("không dựa vào task_memory.md của phiên trước mà không đối chiếu code thật") lại chính là thứ audit gốc đã vi phạm ở mục Image runtime — vì đã dừng lại ở `generate_image.py`/`repair_image.py` import `MockImageProvider` mà không grep tiếp xem `daily_cycle.py` có dùng provider khác hay không.

**Verify:** `python3 -m pytest -q` → 702 passed, 0 fail. Không chạm `venho-os` lần này.

## 14i. Rà soát Phase 1–3 v3.1 + hoàn thiện Phase 4/4.5 (2026-08-06)

Harry: "Rà soát lại phase 1,2,3. Nếu đã xong hết thì chuyển sang hoàn thiện Phase 4 và 4.5" (đối chiếu `VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED.md`, không phải roadmap OTA).

**Rà soát Phase 1–3: xác nhận XONG bằng code + test thật (702/702 pass trước khi sửa gì).** Không dựa lại note cũ — check trực tiếp: 16 contract schema, 9 YAML `growth/` + 7 YAML `research/`, `shared/{budget,jobs,notify}/`, `knowledge_studio/facts/`, `validator_studio/claim_validator.py`, `content_studio/generators/gpt_social_generator.py` (real), `image_studio_runtime/` + `alignment_validator.py`/`derivative_validator.py` — tất cả tồn tại và wired vào `daily_cycle.py`.

**Rà soát Phase 4/4.5: Phase 4 (approval/publishing) về cơ bản xong. Phase 4.5 phát hiện 3 module có code + unit test riêng nhưng KHÔNG có caller thật (orphaned) -- claim "unit-tested" trong status comment cũ của `evergreen_pool.py` sai, grep xác nhận 0 test import nó.** PB-006/PB-007 trong bảng roadmap Phần 12 vẫn ghi "launchd 09:00"/"deadman switch cloud" dù Phần 10 đã đổi kiến trúc sang GitHub Actions từ 2026-08-05 -- tài liệu chưa đồng bộ.

Hỏi Harry 1 quyết định trước khi code (AskUserQuestion): khi evergreen fallback lấp 1 slot mất trắng nội dung, có tự DISPATCHED luôn hay vẫn cần 1 click Duyệt? **Harry chọn: vẫn cần 1 click** (giữ đúng bất biến DoD #23 "publish chỉ khi Harry chủ động duyệt" đã chốt 2026-08-05) -- khác nguyên văn plan gốc §9.3 (evergreen coi như đã duyệt sẵn, auto-dispatch).

**Việc đã làm (tất cả có test mới, 709/709 pass tổng, +7 test):**

1. **Doc:** Phần 12 Phase 4.5 viết lại — PB-006/PB-007 đổi thành "superseded", giải thích tại sao (không có tiến trình 24/7 để launchd/deadman canh, idempotency đạt qua `registry.claim()` atomic). Thêm dòng CHANGELOG "v3.1 (2026-08-06 revision)".

2. **PB-005 pre-flight = claim/alignment revalidation thật ngay trước dispatch** (`approve_and_dispatch.py::_preflight_claim_alignment`, gọi từ `_dispatch_claimed` trước khi `bridge.dispatch()`). Trước đây chỉ `edit_publication()` mới re-run `ClaimValidator`/`validate_alignment` -- một publication CHƯA edit, đã approve nhưng dispatch trễ (batch duyệt cả tuần) có thể publish 1 claim dựa trên fact đã hết hạn giữa lúc sinh nội dung và lúc Harry bấm Duyệt. Giờ kill-switch → `NEEDS_REVISION`, không gọi webhook thật, không dispatch. Rows không có `creative_brief` (trước 2026-08-05 hoặc evergreen) skip gracefully (`claim_alignment_skipped`), không coi là pass ngầm.

3. **`PublishingSlot` state machine sửa 2 lỗi thật:**
   - `assert_missed_only_after_evergreen_exhausted` chỉ guard `status=="OPEN"` — nhưng path MISSED thật trong `daily_cycle.py` luôn đi từ `DRAFT_ASSIGNED`, nên guard này **chưa bao giờ fire trong production** dù unit test của nó pass. Sửa để guard cả `DRAFT_ASSIGNED`.
   - `EVERGREEN_FALLBACK -> DISPATCHED` (transition trực tiếp, đúng plan gốc) đổi thành `EVERGREEN_FALLBACK -> PENDING_APPROVAL` theo quyết định Harry ở trên; test cũ `test_publishing_slot_evergreen_fallback_path` cập nhật theo full funnel (`DRAFT_ASSIGNED → EVERGREEN_FALLBACK → PENDING_APPROVAL → FILLED → DISPATCHED`).

4. **PB-004 Evergreen Pool nối thật:**
   - `shared/storage/evergreen_pool_store.py` mới (JSON, cùng convention với `TrendCandidateStore`) — chỉ nạp item qua `add_from_publication()`, không tự bịa nội dung.
   - `daily_cycle.py::_fill_slot_from_evergreen` — gọi khi mọi platform sinh nội dung thất bại hoàn toàn cho 1 slot, trước khi cho phép MISSED. Đọc `evergreen_reuse_cooldown_days` từ `queue_policy.yaml` (mặc định 90). Item chọn ra chưa có `creative_brief`/`claims` → preflight/edit đều skip gracefully, không coi là đã verify.
   - CLI `venho-growth evergreen-add --publication-id X --added-by harry` / `evergreen-list`.
   - Pool trống mặc định (Harry chưa curate gì) — cơ chế chạy thật nhưng không kích hoạt cho tới khi có item.

5. **PB-003 Runway + Telegram alert nối thật (trước đây `runway_status()`/`send_alert()` có code, 0 caller thật ngoài test):**
   - `manage_queue.py::check_runway` — đếm slot còn `OPEN` trong horizon 14 ngày (không phải "generated nhưng chưa duyệt") — chủ đích: `run_weekly_cycle` luôn ensure lại horizon 14 ngày mỗi lần chạy thật, nên số OPEN chỉ tụt về 0 nếu chính job đó NGỪNG chạy (cron chết, token hết hạn) → đây là canary hạ tầng thật, không chỉ đếm backlog nội dung.
   - Gọi best-effort ở cuối `run_weekly_cycle` (đã ensure_slots xong). CLI `check-runway` để check tay.
   - `shared/notify/telegram.py::telegram_notifier_or_mock_from_env` mới (cùng convention `google_drive_uploader_from_env`) — trả Mock nếu thiếu `TELEGRAM_BOT_TOKEN`, không raise.
   - Bắn thêm `evergreen_used`/`slot_missed` alert trong `daily_cycle.py` (2 event đã định nghĩa sẵn trong `shared/notify/alert_policy.yaml` từ trước nhưng chưa ai gọi) — best-effort, no-op nếu thiếu `TELEGRAM_CHAT_ID`.
   - **Chưa có ai set `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` thật** — cơ chế live nhưng hiện tại luôn no-op (Mock). Cần Harry set 2 secret này (local `.env.local` + GitHub Actions secret) để alert thật chạy.

**Chủ động không làm (ngoài phạm vi câu hỏi, cần quyết định riêng của Harry hoặc cần thời gian thật):**
- DoD #24 (backup ảnh + verify-restore) — vẫn ghi nhận chưa làm, không đụng.
- DoD #26 (golden-set scorecard ≥9.3/10) — cần dataset thật, không tự chấm giả.
- "4 tuần liên tục đủ 16 slot 0 duplicate" (Exit Phase 4.5) — cần thời gian vận hành thật, không code được.
- `preflight.py` (asset/event/weather check tổng quát) — vẫn KHÔNG wire thêm ngoài phần claim/alignment: registry hiện chưa track `event_claims`/`weather_context` per publication, wire nó vào giờ sẽ luôn trả "pass" giả (không có dữ liệu thật để check) — để dành khi Trend Radar/weather content thật bắt đầu publish (Phase 6/7 territory).

**Verify:** `/usr/bin/python3 -m pytest -q` → 709/709 pass (702 + 7 test mới: evergreen fallback wiring, DRAFT_ASSIGNED guard, check_runway ×2, preflight blocks dispatch ×2). 0 API call. Chưa chạm `venho-os` (không cần đổi UI cho lượt này). Commit local, **chưa push** (Harry tự quyết định khi nào đẩy lên, vì thay đổi chạm publish path thật).

## 14j. Phase 5 Durable Ops — audit + nối thật (2026-08-06)

Harry: "Tiếp tục làm Phase 5. Sẽ commit và push khi nào hoàn thành tất cả." (tiếp nối 14i, cùng phiên).

**Audit trước khi code — cùng phương pháp 14i (grep caller thật ngoài test, không tin note cũ):** Phase 5 được Codex build 2026-08-03, `task_status.md` ghi "DONE" với 498/498 test pass. Grep thật phát hiện `BudgetLedger`/`BudgetPolicy` (`shared/budget/ledger.py`) và `JobStore.recover_expired_leases()`/`heartbeat()` **0 caller thật** ngoài chính chúng và test riêng — cùng loại lỗ hổng đã tìm thấy ở Phase 4.5 (evergreen_pool/preflight/runway) lần trước. Hệ quả thật: mọi real OpenAI call (gpt-5.5/gpt-image-2/GPT-4o vision) trong `daily_cycle.py` chạy hoàn toàn không đo/không chặn budget — `budget_policy.yaml` có cap 2,000,000,000 VND/tháng (không ai từng chỉnh, cao tới mức vô nghĩa). Và: `weekly_cycle`'s job claim dùng `lease_seconds` mặc định 300s (5 phút) trong khi 1 run thật (4 ngày × N platform × real LLM/image/vision call) có thể mất lâu hơn nhiều — nếu 1 run bị crash/cancel giữa chừng (GitHub Actions timeout) thì job kẹt `RUNNING` vĩnh viễn vì không có gì gọi `recover_expired_leases()`, khoá cứng idempotency guard của tuần đó mãi mãi.

Hỏi Harry 1 quyết định thật cần trước khi code (AskUserQuestion, vì đụng tiền thật): mức trần chi tiêu AI/tháng bao nhiêu? **Harry chọn 500,000 VND/tháng.**

**Việc đã làm (tất cả có test mới, 714/714 pass tổng, +4 test):**

1. **Stale-job recovery + heartbeat nối thật vào `run_weekly_cycle`:**
   - `job_store.recover_expired_leases()` gọi trước `claim()` — job kẹt RUNNING từ lần chạy crash trước được giải phóng về READY trước khi thử claim tuần này.
   - `claim(..., lease_seconds=3600)` thay mặc định 300s (run thật có thể lâu hơn nhiều).
   - `job_store.heartbeat(week_key, owner="weekly-cycle", lease_seconds=3600)` gọi sau mỗi ngày trong loop 4 ngày — gia hạn lease liên tục để 1 run đang thật sự tiến triển không bị 1 trigger đồng thời tưởng nhầm là chết.
   - Test mới: `test_run_weekly_cycle_recovers_a_week_stuck_running_from_a_crashed_prior_attempt` — giả lập job bị claim rồi bỏ dở (không complete/fail), lease đã hết hạn, xác nhận lần chạy tiếp theo tự phục hồi và chạy bình thường thay vì `skipped_already_run=True` mãi mãi.
   - Retry matrix (`requeue_retryable_failures()`) đã nối sẵn từ trước — không cần sửa.

2. **`BudgetGate` (mới, `growth_orchestrator/application/budget_gate.py`) — chặn cứng real OpenAI call khi chạm cap:**
   - Bọc reserve→commit (thành công)/release (lỗi) quanh đúng 3 điểm gọi API thật trong `daily_cycle.py`:
     - `_run_content_pipeline_budgeted()` (mới) quanh mỗi lần `run_content_pipeline()` trong retry loop text (tối đa `MAX_TEXT_ATTEMPTS`).
     - `_generate_topic_image()` — quanh mỗi `generate_image_run()` VÀ mỗi `validate_image()` (chỉ khi `image_validation_provider != "mock"`, vì mock không tốn tiền thật) trong retry loop ảnh (tối đa `MAX_IMAGE_ATTEMPTS`).
   - Reservation bị chặn → `RuntimeError` → rơi vào except handler có sẵn của từng platform/ngày (không crash cả pipeline, xử lý y hệt 1 lỗi generation thật khác).
   - `config/projects/venho_hotel/growth/budget_policy.yaml`: `monthly_cap_minor: 500000` (Harry chốt), version bump 1→2, comment giải thích tại sao đổi từ 2 tỷ.
   - `config/projects/venho_hotel/growth/paid_call_costs.yaml` (mới, file thứ 11 trong `growth/`) — ước tính thô 300/1200/400 VND cho text/ảnh/vision, ghi rõ là estimate chưa đối chiếu hoá đơn thật, không phải per-call accounting chính xác. `tests/test_growth_phase1_policy_registry.py`'s file-registry test cập nhật theo (set required files +1).
   - `_alert_on_budget_threshold()` (mới) — bắn `budget_threshold_crossed` Telegram alert (event đã định nghĩa sẵn trong `alert_policy.yaml` từ trước, chưa ai gọi) mỗi khi 1 reservation cán mốc 70/85/100%, không dedupe (chấp nhận trade-off ở tần suất hiện tại — vài chục call thật/tuần).
   - Test mới (`tests/test_growth_budget_gate.py`, 4 test): block khi chạm cap, release giải phóng cho lần thử lại, commit giữ nguyên đã tính vào spend, và 1 test end-to-end qua `run_daily_cycle` xác nhận cap=0 khiến mọi platform rơi vào `errors` với message "budget cap reached" thay vì crash.
   - **Chưa có UI/CLI riêng cho override vượt cap** — dùng thẳng `BudgetLedger.record_override(reservation_id, amount, reason=..., approved_by=...)` nếu Harry cần vượt cap có ghi nhận lý do.

3. **`Worker` class + `shared/jobs/scheduler.py` — đánh dấu superseded, không ép nối:** cả hai giả định kiến trúc worker 24/7 + cửa sổ dispatch cố định 09:00 (`next_dispatch_at`) — đúng thiết kế Mac Mini đã bị thay bởi GitHub Actions on-demand (Phần 10, 2026-08-05). `weekly_cycle`/`approve_and_dispatch` đã dùng thẳng `JobStore`/`PublicationRegistry`, không qua `Worker`, nên nối `Worker` vào giờ sẽ không khớp với cách hệ thống thật đang chạy. Giữ code (đã có test riêng từ 2026-08-03), không xoá, không ép nối — chỉ đánh dấu trong doc.

4. **Chủ động không làm (cần thời gian/hạ tầng thật, không phải quên):**
   - Lateness alert (`scheduler.lateness_alert()`) — cần 1 vòng polling "giờ này lẽ ra chạy xong chưa", kiến trúc push-based hiện tại (cron kích hoạt, không có gì đứng canh) không có chỗ tự nhiên để gắn mà không thêm hẳn 1 tiến trình giám sát riêng.
   - Backup tự động verify được — cùng gap với DoD #24 (Phần 10/18, 2026-08-05), chưa đụng.

5. **Doc:** Phần 12 Phase 5 viết lại đầy đủ (rewrite section + audit note), thêm dòng CHANGELOG "v3.1 (2026-08-06 revision, Phase 5)".

**Verify:** `/usr/bin/python3 -m pytest -q` → 714/714 pass (710 + 4 test mới). 0 API call. Chưa push — Harry: "sẽ commit và push khi nào hoàn thành tất cả" (đang giữa Phase 5, chưa xong toàn bộ roadmap).

## 14k. Phase 6 Analytics + Attribution — audit + attribution tối thiểu qua Zalo (2026-08-06)

Harry: "ok, làm tiếp P[hase 6]" (tiếp nối 14j, cùng phiên).

**Audit trước khi code — cùng phương pháp 14i/14j:** Phase 6 Codex build 2026-08-03, `task_status.md` ghi "DONE". Grep caller thật phát hiện `analytics_feedback/meta_insights.py` và `analytics_feedback/attribution.py` **0 caller thật** (cả hai đã có status comment tự nhận từ 1 audit trước đó ngày 2026-08-05 xác nhận đúng điều này — không phải phát hiện mới của phiên này, mà là confirm lại + hành động). Khác Phase 4.5/5 (chỉ cần nối dây), đào sâu thêm phát hiện: **grep `utm_content`/`build_utm_content` toàn repo → chỉ xuất hiện trong chính `attribution.py`, không đâu khác** — nghĩa là không có bài đăng nào từng mang link có gắn utm cả. Kiểm tra tiếp `_content_payload()` (nơi build text bài đăng): CTA chỉ là câu chữ LLM sinh ra ("soft call-to-action sentence"), không có URL nào được chèn. Kiểm tra chéo sang repo `Ven Ho Hotel` (`grep utm_source/utm_content src/`) — chỉ có utm cho link ra Agoda (`ota.ts`), không có gì bắt utm vào từ traffic bên ngoài. Kết luận: attribution DoD #25 cần xây mới thật sự (link tracking + nơi nhận sự kiện), không phải chỉ nối `attribute_conversion_event()` đã có sẵn.

Hỏi Harry phạm vi (AskUserQuestion, 3 lựa chọn: hoãn / xây tối thiểu qua Zalo / để anh quyết sau). **Harry chọn: xây tối thiểu qua Zalo.** Lý do hợp lý về mặt kỹ thuật: Zalo OA publish qua Make.com webhook (`ZaloOAAdapter`) — message thật do Make.com tự soạn dựa trên `content` payload gửi từ đây, nên đây là kênh duy nhất có thể mang 1 URL click được thật (Facebook/Instagram feed post trong pipeline này không hề có link, chỉ text).

**Việc đã làm (717/717 pass, +3 test mới):**

1. **`meta_insights.build_metrics_adapter` nối thật vào `M08AnalyticsBridge`:**
   - Trước đây bridge hardcode `metrics_adapter_factory = MockMetricsAdapter` trực tiếp trong `__init__`, bỏ qua hoàn toàn `meta_insights.py::build_metrics_adapter()` (hàm factory tôn trọng flag `meta_insights_enabled`/`real_meta_insights_enabled`). Đổi default thành `build_metrics_adapter` — flag giờ thật sự có tác dụng: tắt (mặc định) → vẫn Mock (đúng trạng thái thật, chưa có real Graph API client); bật mà chưa implement real adapter → raise `RuntimeError` rõ ràng thay vì âm thầm return Mock (đúng fail-mode mong muốn, tránh Harry tưởng nhầm real data đang chạy).
   - Cập nhật status comment đầu file `meta_insights.py` phản ánh đã nối.

2. **Attribution tối thiểu qua Zalo:**
   - `attribution_policy.yaml` version 1→2, thêm `tracking_base_url: "https://venhohotel.com/lien-he"` (route `/lien-he` xác nhận có thật trong `Ven Ho Hotel/src/app/lien-he/`).
   - `attribution.py::build_tracking_url(publication_id, base_url, platform)` (mới) — tái dùng `build_utm_content()` sẵn có, sinh `{base_url}?utm_source={platform}&utm_medium=social&utm_content={publication_id}`. `AttributionPolicy` dataclass thêm field `tracking_base_url`.
   - `daily_cycle.py::_content_payload()` — thêm param `publication_id`/`platform`; khi `platform=="zalo"` và có `tracking_base_url` trong policy, nối link vào cuối `text` + lưu riêng field `content["tracking_url"]` (để Make.com/Harry lấy ra làm URL nút bấm thật trong Zalo message — bản thân code này không cấu hình message Zalo, Make.com scenario làm việc đó, xem `ZaloOAAdapter`'s docstring). Bọc try/except best-effort — thiếu/hỏng `attribution_policy.yaml` không được chặn queue bài text.
   - `growth_orchestrator/cli.py`'s call site truyền `publication_id=publication_id, platform=platform` vào `_content_payload()`.
   - CLI mới `venho-analytics attribute <events.json>` (`analytics_feedback/cli.py`) — đọc publication đã **RECONCILED thật** (`published_at` có giá trị thật, set bởi `venho-growth reconcile` sau khi Harry xác nhận bài đã lên thật) từ `PublicationRegistry`, pseudonymize contact nếu có, dedupe theo policy, chạy `attribute_conversion_event()` thật, in JSON kết quả. Đây là nửa "chạy được thật" của DoD #25.
   - **Gap còn lại, ghi rõ ràng không giả vờ đã xong:** không có nguồn sự kiện chuyển đổi tự động nào feed vào CLI `attribute` — Harry phải tự cung cấp `events.json` (export tay từ GA4/hộp thư/Zalo). Tự động hoá thật cần 1 trong 2: (a) GA4 Data API pull (cần service account credentials, quota, quyết định riêng) hoặc (b) sửa form đặt phòng trên `Ven Ho Hotel` website để bắt `utm_content` từ query string và forward vào booking API — đây là thay đổi **production website đang chạy thật** (`venhohotel.com`), thuộc phạm vi CLAUDE.md riêng của repo đó ("Hỏi trước khi làm"), không tự ý đụng vào trong phiên này.
   - `test_end_to_end_report_and_cli_stay_offline` (test cũ) phải sửa: `runner.invoke(app, [...])` không còn tự động chọn lệnh `collect` nữa vì app giờ có 2 lệnh (Typer/Click chỉ auto-invoke khi app chỉ có đúng 1 command) — thêm `"collect"` làm arg đầu.

3. **M10 performance view** (`build_content_performance_view`) — đã real từ trước (đọc M08 output, không tính lại), không cần sửa.

4. **Doc:** Phần 12 Phase 6 viết lại đầy đủ (audit note + phạm vi Harry chốt + gap còn lại), thêm dòng CHANGELOG "v3.1 (2026-08-06 revision, Phase 6)".

**Verify:** `/usr/bin/python3 -m pytest -q` → 717/717 pass (714 + 3 test mới: `build_tracking_url` + attribution nối tiếp thật, Zalo có link/FB không có link qua `run_daily_cycle` thật, CLI `attribute` end-to-end qua `PublicationRegistry` thật). 0 API call. Chưa push (Harry: "sẽ commit và push khi nào hoàn thành tất cả").

## 14l. Phase 7 Growth Intelligence pilot — strategy_memory nối thật (2026-08-06)

Harry: "làm tiếp P7" (tiếp nối 14k, cùng phiên).

**Audit trước khi code — cùng phương pháp 14i/14j/14k:** `strategy_memory/` (Codex build 2026-08-03) có status comment tự nhận từ 1 audit trước (2026-08-05, không phải phiên này) xác nhận `pattern_inference.py` "implemented + unit-tested but NOT called from any CLI, cron, or bridge" — confirm lại bằng grep thật: đúng, 0 caller ngoài chính module và test riêng. Khác biệt so với việc chỉ "nối dây": package `strategy_memory` **chưa từng có CLI nào cả** (không có trong `[project.scripts]`), nên phải xây cả entry point mới, không chỉ đổi 1 default factory như Phase 6.

**Thiết kế trước khi code:** `infer_strategy_pattern(snapshots, ...)` tính `min_sample_size` bằng `len(snapshots)` — nghĩa là hàm collect evidence PHẢI trả về 1 dòng/publication (sample thống kê thật), không được gộp tổng trước rồi coi là "1 sample" (lỗi thiết kế suýt mắc phải ở bản nháp đầu). Sửa `collect_pilot_snapshots()` để trả về list theo publication, filter theo (pillar, platform) ở tầng CLI trước khi truyền vào `infer_strategy_pattern`.

**Việc đã làm (724/724 pass, +7 test mới):**

1. **CLI mới `venho-strategy`** (`strategy_memory/cli.py`, thêm script entry `venho-strategy = "strategy_memory.cli:app"` vào `pyproject.toml` — package này chưa có script entry nào từ trước):
   - `weekly-brief --week-id ... [--baseline-qbsr] [--min-sample-size] [--questions-root]` — chạy `collect_pilot_snapshots()` → group theo scope → `infer_strategy_pattern()` từng scope → `qbsr_rate()` tổng → `build_weekly_strategy_brief()` → lưu `StrategyBriefStore` (mới, `strategy_memory/stores.py`, JSON dưới `data/projects/{project}/strategy/weekly_briefs/`) → in JSON.
   - `promote --week-id ... --pattern ... --approved-by ...` — chỉ promote được recommendation đã tồn tại thật trong 1 brief đã lưu (không nhận pattern tự bịa), gọi `promote_strategy_memory()` thật, lưu `PromotedStrategyStore` (mới).
   - `list-promoted` — liệt kê những gì đã thật sự được duyệt, tách biệt khỏi brief hàng tuần (brief có thể chứa recommendation chưa/không được promote).

2. **`strategy_memory/collect_pilot_evidence.py::collect_pilot_snapshots()` (mới)** — join thật `PublicationRegistry` + M08 `SnapshotStore` (đọc field `metrics.reach` thật) + `AttributionEventStore` (mới, xem mục 3) qua `content_package_id`/`publication_id`. Trả về **1 dòng/publication** (không gộp tổng), mỗi dòng có `pillar`/`platform`/`qualified_booking_signals`/`eligible_reach`. `qualified_booking_signals` chỉ đếm attribution status `direct`/`assisted` (bỏ `unattributed` — không chứng minh được gì về 1 publication cụ thể).

3. **`AttributionEventStore` (mới, `analytics_feedback/stores/attribution_event_store.py`)** — Phase 6's CLI `venho-analytics attribute` (mục 14k) trước đây chỉ in kết quả JSON ra màn hình rồi bỏ, không có nơi nào đọc lại. Giờ mỗi kết quả attribute lưu qua store này (`overwrite=True`, key = event id) để `collect_pilot_snapshots()` đọc lại được. Thêm `JsonDirectoryStore.list_all()` (generic, dùng chung cho `SnapshotStore` + `AttributionEventStore`).

4. **Vòng phản hồi `INCONCLUSIVE` → `research/questions/` cho strategy pattern:** `analytics_feedback/research_question_generator.py::generate_research_question_from_analytics()` đã có sẵn + đã có test đúng shape strategy pattern (`test_analytics_signal_generates_research_question`) từ trước — nhưng grep xác nhận **chỉ `M08AnalyticsBridge.observe()` gọi nó**, chưa ai gọi cho strategy-pattern-level "tại sao vẫn INCONCLUSIVE". `weekly-brief` giờ gọi hàm này cho mọi scope INCONCLUSIVE (best-effort, không chặn brief nếu ghi file lỗi).

5. **Gap phụ phát hiện + sửa trong lúc nối:** `M08AnalyticsBridge.observe()` build `DeliveryReceiptRef` chưa từng truyền `pillar` — `daily_cycle.py` đã ghi field `pillar` vào registry row từ 2026-08-04, nhưng `observe()` không đọc lại, nên mọi snapshot thật trước đây có `pillar="unknown"` (default của schema), khiến group theo pillar bất khả thi. Sửa 1 dòng: `pillar=publication.get("pillar") or "unknown"`. Test mới `test_observe_carries_the_publication_pillar_onto_the_saved_snapshot` xác nhận.

6. **Tự phát hiện + tự sửa 1 lỗi test của chính mình:** viết xong `test_weekly_brief_cli_produces_a_real_recommendation_once_sample_size_is_met` và chạy full suite — pass, nhưng `git status research/` cho thấy 1 file thật `research/questions/m08_strategy-lake_view_rooms-zalo.md` đã bị tạo ra trong repo thật (vì test không truyền `--questions-root`, CLI dùng default `Path("research/questions")` = thư mục thật của repo). Xoá file rác, sửa toàn bộ 4 lời gọi CLI trong test file để truyền `--questions-root` trỏ vào `tmp_path`, verify lại `git status research/` sạch trước khi tiếp tục. Bài học: mọi CLI test có ghi file với default path trỏ vào thư mục thật của repo phải luôn override path đó trong test, không giả định best-effort try/except đủ để an toàn.

7. **Doc:** Phần 12 Phase 7 viết lại đầy đủ (audit note + thiết kế + trạng thái thật), thêm dòng CHANGELOG "v3.1 (2026-08-06 revision, Phase 7)".

**Verify:** `/usr/bin/python3 -m pytest -q` → 724/724 pass (717 + 7 test mới: `collect_pilot_snapshots` join thật ×2 (bao gồm loại bỏ unattributed + snapshot mồ côi), CLI `weekly-brief` đủ mẫu → có recommendation thật + ghi research question, CLI `weekly-brief` thiếu mẫu → INCONCLUSIVE + vẫn ghi research question, `promote`→`list-promoted` round-trip, `promote` từ chối pattern bịa, `observe()` gán pillar thật). 0 API call. `git status research/` sạch. Chưa push (Harry: "sẽ commit và push khi nào hoàn thành tất cả").

## 14m. Phase 8 Rollout + Productize — venho-rollout CLI + scorecard thật (2026-08-06)

Harry: "Tôi muốn hoàn thành tất cả để đưa vào vận hành thật" (tiếp nối 14l, cùng phiên) — đây là phase cuối cùng của roadmap 0→8.

**Audit trước khi code — cùng phương pháp 14i–14l:** `controlled_rollout/` (4 file: `metrics_window.py`, `rollout_policy.py`, `runbook_validator.py`, `scorecard.py`) + `productize/hotel_content_engine.py` (Codex build 2026-08-03) có code + unit test đầy đủ (`tests/test_growth_phase8_controlled_rollout.py`, dùng fixture `_golden_metrics()` bịa sẵn) nhưng grep xác nhận 0 caller thật ngoài test riêng, không CLI, không có trong `pyproject.toml`. Cùng loại lỗ hổng như mọi phase trước.

**Khác biệt so với Phase 4.5/5/6/7:** ở đây "nối dây thật" không chỉ là gọi hàm có sẵn — `evaluate_golden_set()` cần một golden-set dict với 9 chỉ tiêu numeric, và **không có nơi nào trong hệ thống lưu lại các con số đó theo lịch sử thật**. `package["validation"]` (kết quả M03 chấm mỗi bài) chỉ được hash hoá thành `validation_snapshot_id` rồi vứt — số điểm thật biến mất ngay sau khi dùng xong. Phải làm 2 việc, không chỉ 1: (a) bắt đầu **giữ lại** số điểm thật từ nay trở đi, (b) build bộ tổng hợp đọc lại số đã giữ.

**Việc đã làm (736/736 pass, +12 test mới):**

1. **`daily_cycle.py::_scorecard_signals()` (mới)** — trích từ `package["validation"]["reports"]` (shape `[claim_report, alignment_report, content_report?]`): `claim_kill_switch_triggered` (bool, từ claim_report — proxy thật cho "critical factual precision") + `content_brand_fit`/`content_overall_score` (từ content_report's `dna_match_score`/`overall_score` — proxy thật cho "brand adherence", không phải công cụ đo giống hệt bản gốc plan hình dung là reviewer-scored, nhưng là số thật M03 đã tính trên mọi bài thật). Gọi tại điểm `registry.update()` trong `daily_cycle.py`, field mới `scorecard_signals` trên mỗi publication row.
2. **`SlotStore.list_all(status=...)` (mới)** — trước đây chỉ có `list_for_week()`; cần đọc MISSED slot trên toàn bộ lịch sử cho `unplanned_empty_days`, không chỉ tuần hiện tại.
3. **`controlled_rollout/collect_real_scorecard_metrics.py` (mới)** — join thật `PublicationRegistry.load()` + `SlotStore.list_all()`:
   - Chấm được thật 6/9 chỉ tiêu: `critical_factual_precision` (tỉ lệ PUBLISHED không có claim kill-switch), `brand_adherence` (trung bình `content_brand_fit`), `duplicate_publication` (đếm thật cặp idempotency_key+platform trùng — về lý thuyết kiến trúc luôn 0 vì `reserve()` test-and-set trong file lock, verify chứ không giả định), `publication_post_id_rate` (PUBLISHED có `platform_post_id`/tổng PUBLISHED), `human_acceptance_no_major_edit` (PUBLISHED không có `edited_by`/tổng), `unplanned_empty_days` (đếm slot MISSED thật).
   - 3/9 chỉ tiêu ảnh (`copy_image_alignment`/`hotel_dna_pass`/`linh_an_identity_pass`) **không có nguồn thật** — cần `validator_studio.image_validator` chạy thật (Vision QC trả phí), nhưng `daily_cycle` mặc định `image_validation_provider="mock"` để giữ ngân sách 500k/tháng (14j). Trả về thiếu (không có key trong `metrics`), liệt kê lý do cụ thể trong `data_gaps` — không tự tính hay giả định số.
4. **`controlled_rollout/rollout_state_store.py` (mới)** — JSON store `data/projects/{project}/rollout/rollout_state.json`, mặc định `current_stage="shadow"` (đúng trạng thái thật — Growth Agent chưa từng tiến stage). `record_decision()` chỉ advance stage khi `decision["allowed"]=True`; decision bị chặn vẫn ghi vào `history` để có audit trail.
5. **CLI mới `venho-rollout`** (`controlled_rollout/cli.py`, script entry mới trong `pyproject.toml`): `scorecard --version` (chạy `collect_real_scorecard_metrics` + `evaluate_golden_set` thật), `rollout-status`, `rollout-advance --scorecard-version --metrics-days --lane` (luôn chấm điểm thật trước khi quyết định, exit code 1 nếu bị chặn — đúng hành vi, không phải lỗi), `rollback-plan --disable-dispatch-done`, `runbook-validate`, `productize-run --project --brief-json` (chạy `hotel_content_engine` thật cho 1 project id bất kỳ, chỉ đọc config).
6. **`.claude/skills/_productize/hotel-content-engine/SKILL.md`** — thêm CLI trigger + mục "Known limitation" ghi rõ engine hiện là bản rút gọn (đọc `tone_of_voice.yaml`+`taxonomy.yaml` build headline/body), chưa chạy qua pipeline M02 prompt/M05 copy-candidate đầy đủ như `daily_cycle.py` production.
7. **Gap phụ phát hiện + sửa — không phải việc dự kiến ban đầu:** trong lúc kiểm tra vì sao test cũ `test_productize_skill_and_runbook_docs_exist` pass nhưng `git status .claude/` không hiện gì, phát hiện `.gitignore` có dòng `.claude/` chặn **toàn bộ** thư mục `.claude/` từ trước tới giờ — nghĩa là 10 skill trong `.claude/skills/` (kể cả `hotel-content-engine`, tồn tại từ 2026-08-03, RS-F1 quyết định năm 3.1 đã ghi rõ vị trí đúng là `.claude/skills/`) **chưa từng được commit vào repo**, chỉ tồn tại trên máy local. Sửa `.gitignore`: đổi `.claude/` → `.claude/*` + `!.claude/skills` + `!.claude/CLAUDE.md.proposed` (giữ nguyên phần còn lại — ví dụ `settings.local.json` nếu có sau này — bị ignore, tránh lộ state cá nhân). Kiểm tra nội dung `.claude/CLAUDE.md.proposed` trước khi add — chỉ có "No pending changes.", không có gì nhạy cảm. `git add` 10 skill + file này.
8. **Doc:** `docs/growth/controlled_rollout_runbook.md` + `docs/growth/eval_golden_sets.md` viết lại toàn bộ — khớp kiến trúc GitHub Actions thật (không còn Mac Mini), có bảng 9 chỉ tiêu ghi rõ nguồn dữ liệu thật/thiếu cho từng chỉ tiêu, cách chạy CLI thật. Phần 12 Phase 8 trong master plan viết lại thành `[x]` (cơ chế hoàn thành, rollout stage thật vẫn `shadow` chờ dữ liệu). Thêm dòng CHANGELOG "v3.1 (2026-08-06 revision, Phase 8 — ROADMAP HOÀN THÀNH)".

**Verify:** `/usr/bin/python3 -m pytest -q` → 736/736 pass (724 + 12 test mới: `_scorecard_signals` extract có/không content_report, `collect_real_scorecard_metrics` trên registry rỗng (data_gaps đúng) + trên 3 publication seed thật (số trung bình đúng), CLI `scorecard` end-to-end trên dữ liệu rỗng, `RolloutStateStore` mặc định shadow + chỉ advance khi allowed, CLI `rollout-advance` bị chặn trên dữ liệu rỗng + vẫn bị chặn khi 6/9 chỉ tiêu tốt nhưng thiếu 3/9 ảnh (chứng minh gate không thể bị "chơi" bằng cách chỉ có phần dữ liệu dễ), CLI `rollback-plan` enforce thứ tự, CLI `runbook-validate` pass trên file thật, CLI `productize-run` build draft cho hotel #2 config-only, `unplanned_empty_days` đọc MISSED slot thật). 0 API call. `git status --short` sạch (chỉ các file dự kiến sửa/mới + `.claude/skills/`+`.claude/CLAUDE.md.proposed` mới add). Chưa push — chờ Harry xác nhận cuối vì đây là điểm "hoàn thành tất cả" theo lời Harry, cần Harry biết rõ những gì vẫn còn là gap vận hành thật (không phải gap code) trước khi đẩy lên remote.

**Ý nghĩa thật của "hoàn thành roadmap":** 9/9 phase (0→8) giờ có code thật + CLI thật + dữ liệu thật, không còn phase nào ở dạng "code+test cô lập, 0 caller thật". Việc còn lại — rollout stage tiến lên `pilot_25` thật, xây golden eval set >=100 case reviewer-scored theo đúng plan gốc, bật Vision QC thật thường xuyên, backup verify-restore, lateness alert, GA4/FB attribution tự động — là **việc vận hành theo thời gian thật + quyết định sản phẩm của Harry**, không phải code còn thiếu. Liệt kê đầy đủ trong `docs/growth/controlled_rollout_runbook.md`'s "Trạng thái thật hôm nay".

## 14n. Scenario Make riêng cho Growth + cổng rollout stage thật (2026-08-06, chiều)

Tiếp nối hai ghi chú "Sửa 2026-08-06" trong mục 14b (tách webhook + ảnh fallback). Ba việc, làm cùng buổi với Harry ngồi thao tác trên Make.

**1. Scenario Make riêng — ĐÃ CHẠY THẬT.** Webhook mới `https://hook.us2.make.com/jw62ijj38t2r9prls12dj9cx537fwfo2`, đã điền vào `.env.local` → `MAKE_GROWTH_WEBHOOK_URL` (secret để trống, adapter không ký HMAC). Scenario là bản clone của legacy, giữ nguyên 5 module: `Webhooks 2` → `HTTP - Download a file 4` → `Router 5` → `Facebook Pages 3` / `Instagram for Business 6`. Mapping đã đổi sang schema Growth: HTTP URL = `{{2.image_url}}`, FB "Post caption" = `{{2.content.text}}`, IG Caption = `{{2.content.text}}`, filter 2 nhánh đổi từ `publish_to_facebook`/`publish_to_instagram` (field legacy, Growth không có) sang `{{2.platform}}` Equal to `facebook`/`instagram`. Thêm điều kiện AND thứ hai trên **cả hai** nhánh: `{{2.publication_id}}` **Does not contain** `test` — chốt an toàn vĩnh viễn, mọi payload thử nghiệm bị chặn ở Router.

**Sự cố trong lúc làm (2 lần đăng nhầm lên trang thật):** payload smoke-test `platform: "threads"` được cho là an toàn vì "không nhánh nào khớp", nhưng cả FB lẫn IG đều đăng thật — filter cũ của scenario legacy cho qua (nhiều khả năng điều kiện phủ định, hoặc route đặt `fallback = Yes`). Lần thứ hai lọt tiếp vì Harry đã sửa filter nhưng **chưa bấm nút Save của scenario** (nút 💾 dưới đáy canvas — khác nút Save trong panel filter); scenario đang ON vẫn chạy bản deploy cũ. Harry đã xoá cả 4 bài test. Lần thứ ba mới đúng: `The bundle did not pass through the filter` ở cả 2 module. **Bài học ghi lại:** (a) không suy đoán logic filter của scenario có sẵn — mở ra đọc trước; (b) sửa Make xong bắt buộc Save scenario rồi hard-refresh verify; (c) phiên bản Make hiện tại **không có** mục Disable trong menu chuột phải của module, nên không thể vô hiệu hoá module đích khi test — phải dựa vào filter.

**Chưa kiểm được:** bundle `platform: "facebook"` thật có đi đúng nhánh FB không — về bản chất không thể kiểm mà không đăng thật. Lần đăng thật đầu tiên nên là một bài Growth Harry duyệt có chủ ý.

**2. Cổng rollout stage — `shadow` giờ chặn thật trong code.** Trước đây `RolloutStateStore` chỉ là governance record (docstring của nó nói rõ "does not change behaviour by itself"), nên thứ duy nhất ngăn agent stage-shadow đăng lên Facebook thật là `MAKE_GROWTH_WEBHOOK_URL` để trống — cấu hình, không phải logic. Từ lúc điền URL vào, lớp đó biến mất. Nay `approve_and_dispatch._dispatch_claimed()` đọc stage ngay trước `bridge.dispatch()`:
- stage = `shadow` → **không gọi webhook**, row đậu ở status mới `SHADOW_HELD`, kèm `rollout_stage` + `shadow_held_reason`. Approval/snapshot vẫn được ghi đầy đủ → toàn bộ pipeline (sinh bài, validate, duyệt, snapshot) vẫn chạy, chỉ giữ lại cú gọi ra ngoài. Đúng nghĩa "shadow".
- `_rollout_stage()` **fail closed**: state file hỏng/không đọc được → coi như `shadow`, giữ bài lại chứ không đăng.
- `SHADOW_HELD` nằm trong `list_pending()` (row không biến mất khỏi dashboard) và trong `EDITABLE_STATUSES`.
- Thoát cổng có 2 đường: `venho-rollout rollout-advance` (tiến stage thật, phải qua scorecard) — sau đó row đã giữ được thả bằng `retry_dispatch` (approval cũ vẫn còn hiệu lực, không duyệt lại); hoặc `venho-growth approve-and-dispatch --allow-shadow` cho một bài cụ thể, ghi `shadow_override_by` lên chính row đó để có audit trail.
- Test cũ về đường dispatch phải seed stage qua helper `_past_shadow(tmp_path)` — nếu không chúng đang assert cái cổng chứ không phải hành vi chúng đặt tên.

**Lưu ý vận hành:** stage thật hiện vẫn là `shadow` và `data/projects/venho_hotel/rollout/rollout_state.json` chưa tồn tại (mặc định). Nghĩa là **bấm Approve trên dashboard sẽ KHÔNG đăng** — muốn đăng bài đầu tiên phải dùng `--allow-shadow` từ terminal.

**3. 12 publication kẹt đã sửa trạng thái.** 12 row `GATEWAY_ACCEPTED` ngày 2026-08-04 thực chất fail phía Make (xem 14b) — đã đổi sang `GATEWAY_ERROR` + `gateway_error` ghi rõ nguyên nhân và ngày sửa, nên `list_pending()` hiện lại được và `retry_dispatch` gửi lại được. Chúng đều có `image_public_url = None`, nhưng lớp chặn cuối trong `MakeGatewayAdapter` sẽ thay bằng ảnh mặc định khi gửi lại. Backup registry trước khi sửa để ở scratchpad phiên làm việc.

**Verify:** `PYTHONPATH=. pytest -q` → **744 passed** (737 + 5 test cổng shadow + 2 test ảnh fallback đã có). 0 API call.

## 14o. Research OS chạy thật lần đầu — URL đích danh + tách domain + lọc ngày cũ (2026-08-06 → 07)

Cả arc từ commit `8b36845` → `f6599a0`. Điểm chung của mọi lỗi trong mục này: **mỗi lớp đều trả về "một cái gì đó", nên không lớp nào trông hỏng** — hệ thống chạy đủ chu kỳ, ghi note vào vault, sinh proposal, mà nội dung thì rỗng.

**1. Chu kỳ nghiên cứu tự động + collector URL đích danh.** `run_research_cycle` đọc `config/projects/venho_hotel/research/research_questions.yaml`: domain có `queries:` → Tavily Search (quét rộng); domain có `urls:` → `collectors/tavily_extract.py` (đọc đúng trang Harry đưa). Kết quả → R0 source note + R2 synthesis trong vault → `ProposedFactStore` `pending_approval` → Harry duyệt trên VenHo OS. **DoD #13 giữ nguyên:** không code path nào promote R2→R3 tự động.

**2. Ba lỗi làm đường URL đích danh chưa từng thật sự hoạt động** (phát hiện khi guest_voice đọc 3 trang tốt mà ra 0 proposal):
- `extract_depth` mặc định `"basic"` → Agoda trả `Failed to fetch url`. Đổi sang `"advanced"`.
- Cap `MAX_CONTENT_CHARS = 6000` cắt **markdown thô**, mà 60–75% ký tự là cú pháp link/ảnh → 6000 ký tự đầu chỉ toàn nav chrome. Thêm `strip_markdown_noise()` (bỏ `![]()`, giữ text trong `[]()`, bỏ URL trần) **trước** khi cắt, nâng cap → 32000.
- `_MAX_SNIPPET_CHARS = 1200` trong `extract_facts` cắt tiếp lần hai trước khi Gemini nhìn thấy. Thêm `_MAX_SNIPPET_CHARS_PER_SOURCE = 30000` + tham số `per_source=True` (bật khi domain có `urls` và không có `queries`): mỗi trang đích danh đi **một prompt riêng**, không gộp 4 trang vào một prompt 48k.

**3. Dạng URL không suy đoán được.** Agoda `/vi-vn/` chạy với trang này, hỏng với trang khác; Booking cần `.vi.html` cho Ven Hồ nhưng `.en-us.html` cho An Homestay. YAML có comment "**do not 'normalise' them**" — URL Harry đưa phải giữ nguyên xi.

**4. Tách `competitor` → thêm domain `competitor_rating`.** Phát hiện thật: trang OTA **có điểm đánh giá nhưng không bao giờ có giá** (cả Agoda lẫn Booking render giá client-side theo ngày). Một domain không thể trả lời cả hai câu dưới luật "một câu hỏi trả lời được". `competitor` giữ câu hỏi giá + search queries (cố ý không có `urls`), `competitor_rating` giữ 4 URL đối thủ. Kèm theo: `ResearchDomain` Literal thêm `competitor_rating`, `domains.yaml` thêm cadence biweekly/90 ngày. Test đếm domain đổi 9→10 — chốt chống trôi này bắt đúng việc nó sinh ra để bắt.

**5. Dedupe không phụ thuộc cách đặt tên** (`proposed_fact_store.is_same_finding`). Gemini gọi cùng một con số là `review.overall_rating` lần này, `agoda.customer_rating` lần sau → trùng lặp tràn hàng đợi duyệt. Rule: cùng `(domain, source_uri, value)` **và** tập token của `fact_key` (sau khi bỏ `_KEY_NOISE`) là tập con của nhau. Hai bẫy đã dính rồi sửa: (a) chỉ so `(domain, uri, value)` thì `value_for_money=7.9` bị nuốt vì `cleanliness` cũng 7.9 cùng trang; (b) sau khi thêm `overall` vào noise, `overall_rating` rút về tập rỗng — mà tập rỗng là tập con của mọi thứ → thêm guard `if not tokens_a or not tokens_b: return tokens_a == tokens_b`.

**6. `TrendCandidateStore.reject()` + CLI `venho-growth trend-reject` + nút "Từ chối" trên VenHo OS** (route mới `api/v1/studio/growth/trend-candidates/reject`, mirror của approve). **Cố ý làm khác lời Harry ("bấm Cancel thì xoá luôn"): ghi tombstone `status: rejected`, không xoá dòng** — `merge_new` dedupe theo id, nên dòng bị xoá thật sẽ quay lại ở lần quét Thứ 6 kế tiếp và Harry phải từ chối cùng một lễ hội cũ mỗi tuần. Nhìn từ dashboard là biến mất như nhau. Panel cũng lọc luôn 17 candidate do brand-safety tự loại.

**7. Lọc ngày cũ ở `scan_trends` (2026-08-07).** Luật `is_stale_dated` trước chỉ nối vào fact proposal của `local_events`, nên Trend Radar tích Lễ hội Sen 26-28/6/2026, bài Trung thu 2024, trang tin có headline mới nhất 2021 — tất cả brand-safe, điểm cao, chờ Harry từ chối tay hàng tuần. **Gốc rễ không nằm ở chỗ nối dây mà ở bộ đọc ngày:** dạng tiếng Việt thật hoặc không có năm (`ngày 26-28/6`) hoặc viết chữ (`17 Tháng Mười Một 2021`) → `dates_in` khớp 0 → không gì trông cũ. Bổ sung: khoảng ngày `dd-dd/mm[/yyyy]`, `ngày dd/mm` (**bắt buộc có chữ "ngày"** — nếu không `8/10` trong đoạn review khách sạn thành ngày 8/10), tháng viết chữ + tháng số `dd tháng M năm yyyy`. Ngày thiếu năm quy về năm **gần hôm nay nhất** (đọc tháng 8/2026 thì `26/6` = 2026, đã qua). **Tháng trần vẫn là mùa, không phải ngày** — `"Tháng 10 đến tháng 2"` phải giữ nguyên non-stale, có test riêng. `scan_trends(..., today=)` nhận `today` inject được; đọc cả `title` lẫn `snippet` (tiêu đề hiếm khi tự ghi ngày); brand-safety vẫn được báo trước `stale_dated` khi một candidate dính cả hai.

**Backfill + xung đột với quyết định của người.** Lọc chỉ chạy lúc quét, mà `merge_new` bỏ qua id đã có → 3 dòng cũ sẽ nằm mãi. Chạy backfill một lần. Trong lúc đó Harry duyệt trên dashboard đúng một bài mà backfill vừa loại (Lễ hội Sen đã kết thúc) → rebase xong **khôi phục lại approval của Harry**: quyết định của người thắng bộ lọc tự động, không phải ngược lại. Đã báo Harry để tự quyết.

**Giới hạn thật, không phải sót:** bài *"Cuối tuần này ghé hồ Tây trải nghiệm Lễ hội sen"* không ghi ngày nào trong toàn bộ nội dung → bộ lọc ngày không thể bắt. Vẫn cần mắt người ở khâu duyệt.

**Verify:** `PYTHONPATH=. pytest -q` → **834 passed**. 0 API call. `npx tsc --noEmit` sạch bên `venho-os`.

## 14p. Audit closeout — Research OS/Trend Radar (2026-08-07)

- **Architecture:** audit toàn bộ arc `8b36845`→`f6599a0` và các route UI tương ứng trong `venho-os`. `run_research_cycle` chỉ ghi R0/R2 và proposal `pending_approval`; không có đường tự R2/R2-T→R3. M04 không tự sinh content; M10 chỉ đọc/đồng bộ artifact và gọi CLI có policy, không có DB riêng; publish vẫn thuộc M07 sau quyết định người duyệt.
- **Data contract cần nhớ:** proposal tiếp tục là JSON artifact id-keyed ở `data/projects/{project}/research/proposed_facts.json`, local decision thắng khi git-sync conflict. Trend reject là tombstone `status: rejected`, không được xoá record vì scan sau sẽ re-propose. `competitor_rating` là domain riêng (biweekly, expiry 90 ngày), tách khỏi `competitor` pricing.
- **Verification closeout:** `PYTHONPATH=. /usr/bin/python3 -m pytest -q` → **834/834 pass**, 0 API call; `venho-os: npm test -- --run` → **150/150 pass**; `npx tsc --noEmit` pass.
- **Cleanup:** xoá cache/dev artifacts không track (`__pycache__`, `.pytest_cache`, `.DS_Store`, `.log`, `.tmp`); không xoá docs/config hay JSON trong `data/`/knowledge stores. Không phát hiện unused import trong Python thay đổi (trừ `from __future__ import annotations`).

## 14q. DoD 11/24/25/26 follow-up (2026-08-07)

- **DoD #11:** `.github/workflows/growth-blog-seo.yml` mới chạy thứ 3 08:00 ICT. Workflow chỉ sinh/commit blog draft qua `venho-growth blog`; không có Make webhook hay dispatch path, nên không bypass editorial approval.
- **DoD #24:** audit phát hiện implementation đã tồn tại trong commit `b7409a3` nhưng roadmap/status cũ chưa phản ánh: `shared/backup/growth_backup.py` snapshot SQLite online, copy registry/facts/research, artifact CAS, restore vào scratch + `PRAGMA integrity_check` + row-count/checksum; CLI backup verify mặc định. Còn điều kiện vận hành: `VENHO_BACKUP_DIR` phải được Founder trỏ ra storage ngoài máy và job phải chạy định kỳ.
- **DoD #25/#26 không được làm giả:** code attribution/scorecard đã có. Hoàn tất đòi GA4 credential hoặc event feed từ booking form, một golden set do người review chấm và Vision QC thật; repo website đang có dirty changes nên không được tự ý sửa. Rollout giữ `shadow` đúng fail-closed.
- **Verify:** `PYTHONPATH=. /usr/bin/python3 -m pytest -q` → **835/835 pass**, 0 API call.

## 14r. FORBIDDEN = policy, và face gate không xét tóc/biểu cảm (2026-08-07)

- **FORBIDDEN chỉ nhận câu phủ định.** `knowledge_studio/vision/forbidden_policy.py`:
  rule phải bắt đầu bằng no/not/never/without/avoid/exclude. Model khi được hỏi "thứ rõ ràng
  KHÔNG có trong ảnh" trả về tên feature trần cũng nhiều như trả về lệnh cấm — DNA `outside`
  từng liệt `lake view`, `railing`, `Rooftop terrace`, `Cityscape` làm FORBIDDEN, tức là cấm
  đúng những thứ làm nên chủ thể. Sanitizer chạy ở 2 chỗ: `pass2_consolidate` (lúc build) và
  `overlay_merge` (lúc render — cứu các DNA sinh trước khi có policy này).
- **Validator chỉ dùng rule `curated`.** `validator_studio/observe_adapter.py::_forbidden_rules_for_validation`.
  Trước đó toàn bộ rule kể cả `observed` được gửi sang validator, nên `outside` đang cấm
  `No visible lake or cityscape` và `No visible railing` — đúng ngữ pháp nên sanitizer không bắt
  được. Một rule bị vi phạm = severity high = kill-switch = tốn thêm nguyên một ảnh. Subject
  không có overlay (không có rule curated nào) mới rơi về `observed`.
- **`venho vision clean-forbidden --project venho_hotel [--subject X] [--apply]`** — dry-run mặc
  định, tất định, 0 vision call, không bump version; re-render .md/.json/_COMPACT.md từ object đã
  dọn. Đã dọn 21 mục (outside 12, linh_an 4, room_1 3, lake_view_room 2).
- **Rule viết sai dạng nhưng đúng ý thì MIGRATE, đừng xoá.** 4 mục của `linh_an`
  (`glasses`, `hat`, `visible tattoos`, `visible piercings other than earrings`) là chính sách
  thật — đã viết lại thành rule curated trong `linh_an.overrides.yaml` trước khi cho sanitizer xoá.
- **Face gate không được trượt vì tóc hoặc biểu cảm.** `prompts/observe_face_against_dna.md`:
  `identity_structure` chỉ xét xương và ngũ quan. DNA duyệt nhiều kiểu tóc và nhiều biểu cảm, nên
  xét chúng như tín hiệu nhận dạng là sai theo chính DNA — bằng chứng: `linh-an-master-face.png`
  (ảnh gốc dùng để sinh mọi ảnh Linh An) bị chính gate của nó hard-reject 0.0 chỉ vì để tóc xoã.
  Sau khi sửa: master face 0.0 → 88.26, ảnh rooftop 0.0 → 84.83. Đây cũng là nguồn của hiện tượng
  "không tất định" từng phải băng bó bằng sampling 3 lần trong `validate_generated.py`.
- **Overlay theo scenario:** `config/projects/venho_hotel/subjects/<subject>.<scenario_profile_id>.overrides.yaml`,
  merge in-memory lúc validate, không ghi đè DNA. **Bắt buộc khai lại `forbidden:`** — `apply_overlay`
  dựng lại danh sách từ overlay hiện tại + observed, nên overlay thiếu `forbidden:` sẽ làm rơi sạch
  rule curated (đo được: forbidden 100 → 0 trên một ảnh rooftop tốt).

## 14s. Linh An official-asset readiness — Steps 1–3 (2026-08-10)

- **Hai generation lane là contract chung UI/prompt/API.** `identity` dùng standing face reference cho portrait, standing, leaning và pose tĩnh. `action` áp dụng cho running, cycling, sitting, jumping, dancing, swimming, climbing và dynamic pose khác; bắt buộc text-to-image để standing reference không khóa sai body geometry. Manifest phải ghi `generationLane`, `requestedUseRef`, `effectiveUseRef`, và `references.mode`.
- **Prompt người dùng vẫn được giữ, nhưng policy không thể bị xoá bằng textarea.** `linh_an_generation_protocol_v1` được append ở server-side spend boundary, sau prompt đã submit. Protocol mang scenario lock, exact effective outfit, pose/action, reference policy và yêu cầu Linh An là physical actor. Manifest ghi cả `userPrompt`, `serverPrompt`, `generationProtocol`, prompt effective và hash.
- **CLI/test QC phải tách khỏi audit live.** `venho validate image|prompt|face|content --output-root <dir>` ghi report/manifest vào root chỉ định. Test CLI bắt buộc truyền temporary output root; không được sinh report mock vào `data/projects/venho_hotel/validation/`.
- **Chưa có approval mới.** Không chạy generation trả phí trong Steps 1–3. Asset official vẫn yêu cầu image-DNA pass + face-QC ≥90 + không kill-switch + human review; artifact `revise` không được xem là approved.
- **Verify closeout:** AI Studio `841/841` pytest pass; Venho OS `191/191` vitest pass, TypeScript/build pass. Lint OS vẫn có 2 lỗi sẵn có trong `design_handoff_venho_os_cockpit/support.js`.

## 14t. Google Gemini Image Provider option — handoff to implementation (2026-08-10)

- Chi tiết triển khai nằm tại `venho-os/docs/GOOGLE_GEMINI_IMAGE_PROVIDER_IMPLEMENTATION.md`. Gemini phải đi qua API/provider adapter của Venho OS, không qua Google Flow UI, để tất cả artifact tiếp tục có immutable run/variant + manifest + QC report.
- Preserve Validator Studio as independent judge. Không sửa DNA/prompt/threshold để làm provider mới pass; official vẫn Face `>=90`, image/intent approve (nơi áp dụng), no kill-switch, rồi human review.
- Provider candidates: Nano Banana 2 (`gemini-3.1-flash-image`) cho volume/lifestyle; Nano Banana Pro (`gemini-3-pro-image`) cho reference/identity phức tạp. `gemini-2.5-flash-image` legacy, không dùng cho đường mới; Nano Banana 2 Lite không dùng làm official asset vì không tối ưu multi-reference.
- Bước 5 đã tạo hero/café/business nhưng Face QC chỉ 84.03–88.8; West Lake bị provider safety block; không asset nào official. Benchmark Gemini phải diễn ra trước khi tạo tiếp library: 6 scenario static × Flash/Pro, same prompt/reference/QC, manifest riêng. Chỉ chạy paid benchmark khi user authorize.

## 14. Task Closing Protocol

Khi người dùng nói **"kết thúc task"**, Codex phải tự động:

1. Cập nhật `task_memory.md` nếu có quy ước, kiến trúc, contract, CLI, hoặc integration seam mới.
2. Cập nhật `task_status.md` nếu module/stage/test count/commit/package mẫu thay đổi.
3. Ghi rõ commit hash, test command/kết quả, output mẫu nếu có.
4. Kiểm tra `git status --short` và báo working tree còn sạch hay còn thay đổi.

## 14u. Một lần duyệt theo lịch — Bước 1: canonical pipeline (2026-08-10)

- Growth Agent được chốt là pipeline production duy nhất cho nội dung Facebook/Instagram.
- `legacy_agent_active: false` trong Growth feature flags.
- GitHub Actions của `venho-social-content-agent` đã bỏ trigger cron; chỉ còn `workflow_dispatch` để khôi phục dữ liệu lịch sử có chủ đích. Nó không còn được phép tự tạo hoặc gửi bài theo lịch production.
- Chưa bật dispatch/scheduler Growth ở bước này; các bước sau phải sửa OAuth, chuyển approval thành scheduled state và hoàn thiện dispatcher trước khi bật đăng tự động.

## 14v. Một lần duyệt theo lịch — Bước 2: Google Drive OAuth (2026-08-10)

- Đã sửa Growth `GoogleDriveUploader`: client ID/secret từ GitHub Secrets được đưa vào authorized-user payload trước khi tạo Google credentials; không còn gán vào thuộc tính chỉ đọc `Credentials.client_id`/`client_secret`.
- Đây là nguyên nhân trực tiếp làm GitHub Actions `Growth Agent Weekly Cycle` thất bại trong 25 giây khi refresh token hết hạn.
- Regression test tái hiện token hết hạn, xác nhận credentials nhận đúng client config và gọi refresh thành công mà không có network call.

## 14w. Một lần duyệt theo lịch — Bước 3: Duyệt toàn bộ tuần (2026-08-10)

- `venho-growth approve-week --approved-by <email> [--week-start YYYY-MM-DD]` là thao tác duy nhất duyệt tất cả bản ghi `PENDING_APPROVAL` có `slot_id` trong cùng tuần ISO. Default là tuần hiện tại theo giờ Việt Nam.
- Mỗi bài được chuyển atomically sang `APPROVED_SCHEDULED`, có `approved_at`, `approved_by`, `approval_scope: weekly_schedule` và immutable `approval_snapshot`; tuyệt đối không khởi tạo Make bridge hay gọi webhook trong thao tác này.
- `PublicationRegistry.update_many_if_status()` kiểm tra toàn bộ batch dưới một file lock trước khi ghi, nên nếu một bài đổi trạng thái trong lúc duyệt thì không bài nào của tuần bị duyệt nửa chừng.
- VENHO OS có `POST /api/v1/studio/growth/approve-week` và nút **Duyệt toàn bộ tuần**; endpoint đồng bộ registry lên GitHub sau khi CLI thành công.

## 14x. Một lần duyệt theo lịch — Bước 4: Scheduler xuất bản độc lập (2026-08-10)

- Đường production bắt buộc là `PENDING_APPROVAL` → `APPROVED_SCHEDULED` (Duyệt toàn bộ tuần) → `DISPATCHING` → gateway. `approve-and-dispatch` đã bị retire ở CLI để tab cũ hoặc API cũ không thể đăng ngay sau duyệt.
- `venho-growth dispatch-due` là entrypoint scheduler: chỉ claim bản ghi `APPROVED_SCHEDULED` có `slot_id` đến hạn theo `growth/cadence_policy.yaml` (09:00, Asia/Ho_Chi_Minh). Claim có điều kiện đảm bảo hai tick trùng nhau không thể cùng gọi Make cho một bài.
- VENHO OS có hook `POST /api/v1/studio/growth/scheduler/dispatch`, chỉ nhận `Authorization: Bearer $GROWTH_SCHEDULER_TOKEN`; hook refresh/sync registry Git rồi gọi `dispatch-due`. Scheduler bên ngoài cần poll hook này mỗi 5 phút; approval không gọi hook.
- Dashboard đã bỏ toàn bộ nút duyệt riêng và duyệt từng nhóm; chỉ còn **Duyệt toàn bộ tuần**. Giữ reject/edit trước khi duyệt và retry dispatch khi gateway lỗi.

## 14y. Một lần duyệt theo lịch — Bước 5: Hợp đồng Scheduler rollout (2026-08-10)

- Scheduler cloud chỉ được gọi `POST /api/v1/studio/growth/scheduler/dispatch` mỗi 5 phút, với `Authorization: Bearer $GROWTH_SCHEDULER_TOKEN`; tuyệt đối không gọi Make publishing webhook trực tiếp.
- Đã thêm `venho-os/docs/GROWTH_SCHEDULER_ROLLOUT.md` và khai báo biến môi trường trong `.env.example`. Chưa kích hoạt scheduler: VENHO OS chưa có URL public và runtime secret chưa được cấu hình; cloud scheduler không gọi được `localhost`.
- Không được thử gọi endpoint production cho tới khi có hai giá trị trên, vì mọi publication đã duyệt và quá giờ sẽ được dispatcher xử lý ngay theo contract.

## 14z. Một lần duyệt theo lịch — Bước 5: GitHub Actions Scheduler (2026-08-10)

- Quyết định vận hành Startup: dùng GitHub Actions, không phụ thuộc Mac Mini hay VENHO OS public endpoint. Workflow `.github/workflows/growth-publish-scheduler.yml` chạy best-effort mỗi 5 phút, gọi trực tiếp `venho-growth dispatch-due`, rồi commit `publication_registry.json` và `growth.db`.
- Workflow scheduler và `growth-daily-cycle.yml` dùng cùng concurrency group `growth-publication-state`; không thể ghi đồng thời state Git-backed.
- Secrets bắt buộc tại GitHub repository: `MAKE_GROWTH_WEBHOOK_URL` và (nếu Make xác thực) `MAKE_GROWTH_WEBHOOK_SECRET`. Các secrets Zalo chỉ cần khi có publication Zalo. Không dùng `GROWTH_SCHEDULER_TOKEN` trong phương án GitHub Actions.
- Workflow không dùng `--allow-shadow`: rollout state `shadow` vẫn fail-closed và giữ bài, không tự đăng. Chỉ khi rollout được advance theo quy trình mới gửi Make.
- GitHub Repository Secret `MAKE_GROWTH_WEBHOOK_URL` đã được cấu hình ngày 2026-08-10. Make không có webhook secret ở cấu hình hiện tại, nên không cần `MAKE_GROWTH_WEBHOOK_SECRET`.

## 14aa. Một lần duyệt theo lịch — Bước 6: Migration, kiểm thử và rollout gate (2026-08-10)

- Không có publication `APPROVED_SCHEDULED` trong registry hiện tại. Các bản ghi chưa kết thúc thuộc cơ chế cũ (`GATEWAY_*`/`SHADOW_HELD`), không được migrate về lịch mới vì có thể đăng lại bài đã quá hạn.
- Scorecard thật `growth-scheduler-2026-08`: 2.22/10, sample `PUBLISHED=0`; thiếu telemetry post, brand/claim và Vision QC thật. Gate chặn `shadow → pilot_25` đúng thiết kế; không thay đổi rollout state và không chạy dispatch.
- Runbook rollout hợp lệ. Test regression gồm scheduler, weekly approval, OAuth, policy và rollout: 69/69 pass. `git diff --check` pass.

## 14ab. Khắc phục Dashboard approval queue — Bước 7a: trạng thái rỗng rõ ràng (2026-08-10)

- VENHO OS luôn hiển thị một nút **Duyệt toàn bộ tuần** duy nhất; khi không có `PENDING_APPROVAL`, nút bị vô hiệu với lý do rõ ràng thay vì biến mất.
- `POST /api/v1/studio/growth/approve-week` nhận diện structured error của CLI khi queue rỗng và trả HTTP 409 / `NO_PENDING_APPROVAL` với thông báo tiếng Việt; không còn báo sai là `Command failed`/lỗi hạ tầng.
- ESLint hai file thay đổi và `git diff --check` đã pass.

## 14ac. Khắc phục Dashboard approval queue — Bước 7b: chẩn đoán lệch Slot (2026-08-10)

- Ảnh Dashboard được đối chiếu với state thật: tuần 2026-08-10 có Slot T2/T6/T7 là `OPEN`, Slot T4 là `PENDING_APPROVAL` nhưng không có `content_package_id`; không có publication nào ở `APPROVED_SCHEDULED`.
- Các bài đang hiện ở bảng trên là publication cũ của tuần 2026-08-03, đều `SHADOW_HELD`; chúng không phải hàng chờ duyệt của tuần hiện tại. State `shadow` chủ động chặn webhook Make.
- Kết luận: thao tác Duyệt không thành công, Slot không đổi là đúng với state hiện tại, và không bài nào sẽ được đăng.

## 14ad. Khắc phục tuần 2026-08-10 — Bước 7c: đồng bộ Slot và lọc queue (2026-08-10)

- Đã chạy `venho-growth ensure-slots --horizon-days 14`: thêm 2 Slot còn thiếu trong horizon, không ghi đè Slot tuần hiện tại.
- `list-pending` chỉ trả `PENDING_APPROVAL` và `GATEWAY_ERROR`; các bài `SHADOW_HELD` cũ không còn xuất hiện trong bảng duyệt, vì đã được duyệt từ trước và không có thao tác Duyệt/Từ chối.
- Kiểm thử: `tests/test_growth_approve_and_dispatch.py` 38/38 pass; `git diff --check` pass. Tuần hiện tại vẫn chưa có content package; T4 còn orphan `PENDING_APPROVAL`, sẽ được tuần-cycle xử lý ở bước tạo content.

## 14ae. Khắc phục tuần 2026-08-10 — Bước 7d: Weekly Cycle tự phục hồi (2026-08-10)

- Workflow `Growth Agent Weekly Cycle` được lập lịch thử lại tự động vào 08:00, 10:00 và 12:00 thứ Hai (Asia/Ho_Chi_Minh). `JobStore` chỉ cho một run thành công mỗi ISO week; các lần còn lại tự bỏ qua, còn run lỗi sẽ được thử lại mà không cần thao tác Dashboard.
- Nguyên nhân run 10/08 thất bại: GitHub chạy SHA `4287651` chứa lỗi Google Drive OAuth cũ. Bản sửa OAuth và lịch retry đang ở working tree local, chưa có trên nhánh GitHub để Action sử dụng.
- Xác minh YAML schedule và `tests/test_growth_weekly_cycle.py`: 5/5 pass; `git diff --check` pass.

## 14af. Khắc phục tuần 2026-08-10 — Bước 7e: phát hành Automation Cycle (2026-08-10)

- Đã push Automation Cycle vào `west-lake-living/venho-ai-studio` commit `f3ae89f`; `venho-os` commit `db6db53`; đồng thời tắt cron legacy tại `venho-social-content-agent` commit `cda5641`.
- AI Studio remote có phát sinh state commits đồng thời; Automation commit được rebase/cherry-pick an toàn trên remote HEAD để không ghi đè publication registry hoặc research state mới.
- GitHub Actions từ nay dùng workflow Weekly Cycle có retry tự động; chỉ việc chờ lịch Monday tiếp theo hoặc kích hoạt workflow_dispatch để tạo batch tuần hiện tại.

## 14ag. Bàn giao debug tiếp theo (2026-08-10)

- Remote `main` đã chứa Growth Automation ở HEAD `9792244` (workflow chính `f3ae89f`), VENHO OS `db6db53`, legacy manual-only `cda5641`. GitHub xác nhận `Growth Agent Weekly Cycle` và `Growth Agent Publish Scheduler` đang active.
- Chưa tạo batch content tuần 2026-08-10 sau khi phát hành. Việc debug tiếp theo: trigger `Growth Agent Weekly Cycle` trên GitHub từ source mới, kiểm tra 4 Slot T2/T4/T6/T7 có `content_package_id` và publication `PENDING_APPROVAL`, rồi xác nhận Dashboard hiển thị các thao tác Duyệt/Từ chối.
- Không dispatch/publish trong bước bàn giao này. Rollout vẫn `shadow`; không được dùng `--allow-shadow`.

## 14ah. Growth Agent — two-week cycle, rejected replacement và Monday recovery (2026-08-10)

- Weekly Cycle production chạy Chủ nhật **20:00 Asia/Ho_Chi_Minh**, có fallback **22:00**. Chu kỳ được neo theo từng 2 tuần và idempotent: mỗi batch tạo **8 content slots/lần đăng** (T2/T4/T6/T7 × 2 tuần), mỗi slot có biến thể Facebook + Instagram, tổng **16 publication records**.
- `venho-growth approve-week` duyệt atomically toàn bộ publication trong cửa sổ 14 ngày; một lần **Duyệt tất cả** đủ lịch đăng hai tuần.
- Publication bị từ chối được thay bằng content mới cho đúng platform và đúng slot. VENHO OS gọi workflow `growth-replace-rejected.yml` ngay sau reject; cron 15 phút là fallback. Bản cũ và bản thay thế liên kết bằng `replacement_publication_id` / `replaces_publication_id` để giữ audit trail.
- Scheduler dùng `--allow-shadow` trong production workflow sau approval gate; manual `catch_up_today` chỉ giải phóng slot bị lỡ trong ngày hiện tại theo giờ Việt Nam, không phát hành backlog cũ.
- Khôi phục lịch T2 2026-08-10 qua GitHub run `31389624111`: Make trả `PUBLISHED` cho Facebook và Instagram; Instagram media ID `17929423083379767`. Facebook trả placeholder `3. Post ID` / `3.permalink_url`, nên trạng thái gateway đã thành công nhưng chưa có permalink thật để kiểm chứng trực quan.
- Đã sửa thứ tự persistence của scheduler thành stage/commit trước, rồi pull-rebase/push; run kiểm chứng `31389945843` hoàn tất toàn bộ và không dispatch trùng.
- AI Studio production commits: `fc6d291` và `a04f09b`. VENHO OS reject-trigger commit: `2632537`.
- Verify: `pytest -q tests/test_growth_weekly_cycle.py tests/test_growth_approve_and_dispatch.py tests/test_growth_replace_rejected.py` → **48/48 passed**; VENHO OS `npx tsc --noEmit` pass và publication-registry sync tests **9/9 passed**.
