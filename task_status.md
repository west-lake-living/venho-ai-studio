# VENHO AI STUDIO — Task Status
**Repo:** `venho-ai-studio` · **Workspace:** THE WEST LAKE LIVING
**Cập nhật:** 2026-07-16 (AI Studio v1.5 Phase 7 QA/DOC closeout) · **Tests:** 443/443 pass · 0 API call

---

## Tổng quan

| Module | Tên | Status | Tests |
|--------|-----|--------|-------|
| M01 | Knowledge Studio / DNA Studio / AI Vision Engine | ✅ COMPLETE | 258 |
| M02 | Prompt Studio | ✅ COMPLETE | 347 |
| M03 | Validator Studio | ✅ COMPLETE | 26 |
| M04 | Automation Studio | ✅ COMPLETE | 7 |
| M05 | Content Studio | ✅ COMPLETE — real Claude generator (2026-07-15) | 22 |
| M06 | Video Studio | ✅ COMPLETE (MVP — bugs fixed, design hardened) | 15 |
| M07 | Publishing Gateway | ✅ COMPLETE (offline dry-run MVP) | 19 |
| M08 | Analytics & Feedback Loop | ✅ COMPLETE (offline MVP) | 7 |
| M09 | Agent Studio | ✅ COMPLETE (offline planning/orchestration MVP) | 10 |
| M10 | **VenHo OS Dashboard** (Next.js `localhost:3000/os`) | ✅ COMPLETE v3.0 — Next.js OS Stage A+B+C (2026-07-13) · Streamlit đã xóa (2026-07-13): Workbench (Mode A+B SSE), Creative Studio, Knowledge (DNA Library+Vault Search+Mode C), Reports (DNA Status+Social Log), Shared UI, 7 API routes, 0 TS error | 0 |

> Tests ghi theo module-specific. Full suite = 443 (M01+M02+M03+M04+M05+M06+M07+M08+M09+shared — M10 runtime/API tests nằm ở repo `venho-os`).

### QA/DOC — Phase 7 Closeout (2026-07-16)
- Roadmap v1.5 chỉ có Phase 0–6; Phase 7 được map vào backlog `QA-01` + `DOC-01`.
- Controlled live matrix canonical: `config/quality/controlled_live_matrix.json`.
- Offline evaluator: `validator_studio/controlled_matrix.py`.
- Production-ready image workflow yêu cầu 2 run approved liên tiếp cho mỗi case E1–E6.
- Missing validator/gate luôn là `UNVALIDATED`, không được tính approved.
- VenHo OS expose matrix qua `/api/v1/studio/quality-matrix`, không chạy paid generation.

### M04/M09/AiStudioPort/Living Lab — Phase 6 Ops integration (2026-07-16)
- M04 thêm `automation_studio.wardrobe_ingest`: tạo review file, validation fail chặn index update.
- M04 thêm `automation_studio.wardrobe_index_update`: chỉ update Wardrobe Index khi `validation_status=pass` và `approved_for_index=true`.
- M09 hard-stop khi thiếu required knowledge; không dispatch M04 kể cả dry-run/execute.
- `JobContract 1.0` tách transition `approved → executed → published`; không cho publish nhảy cóc.
- `AiStudioPort` expose coarse capabilities: `wardrobe_ingest`, `content_generate`, `video_package`, `publish_content`.
- Living Lab metrics ghi `output_used`, `approved_first_try`, retry, minutes saved, cost/run, decision `continue/simplify/pivot/kill`.

### M02/M03/M05/M06 — Phase 5 Contract Refs integration (2026-07-16)
- M02 prompt contracts có optional `contract_refs` để trace `character_id`, `outfit_id`, `scenario_profile`.
- Content prompt 1.0 vẫn backward compatible, nhưng khi request có `outfit_id` sẽ render Outfit Capsule có ID rõ ràng.
- M05 `ContentRequest` nhận `outfit_id`; output copy `contract_refs` từ M02, không tự chọn outfit.
- M06 `VideoRequest` nhận `outfit_id`; package ghi `contract_refs`, continuity thêm `outfit_id:<id>` và scene prompts khóa wardrobe xuyên shot.
- M03 prompt/content validator đọc `contract_refs` từ prompt contract; không suy luận outfit từ prose.
- Claude adapter đã có fake-client unit test; pytest không gọi production Claude API.

### M10 / Mode C — Data Integrity (2026-07-16)
- Mode C có CLI/runtime riêng: `venho vision observe --mode c`.
- Request tách `outfit_id`, `schema_subject`, `display_label`.
- Locked variants hiện tại: `mint_green`, `nike_pink_running` → schema canonical `outfit_e_sport`.
- Universal schema fallback bị chặn trong Mode C.
- Artifact output vẫn theo variant (`LINH_AN_NIKE_PINK_RUNNING_DNA.*`) nhưng schema lấy từ `outfit_e_sport`.
- VenHo OS status chỉ báo success khi artifact mới hơn run hiện tại; upload trùng tên bị chặn thay vì overwrite.
- `wardrobe_manifest.json` quarantine Nike Pink artifact cũ và đánh dấu `sport_active` upload folder là legacy alias.

### M03 / Image QC — Phase 2 contract hardening (2026-07-16)
- Face Validator bắt buộc đúng 3 gate: `identity_structure`, `eye_ratio`, `forbidden_traits`.
- Face Validator bắt buộc đúng 5 score keys: `facial_shape`, `eyes`, `hair`, `expression`, `technical_quality`.
- `weighted_scores` phải là điểm 0–100; payload dùng rubric weight 0–1 bị reject.
- VenHo OS Generation Manifest nâng lên `schemaVersion: 1.1` với `promptHash`, outfit trace, `scenarioProfile`, face reference set version, validation contract và latency.

---

## M01 — Knowledge Studio / DNA Studio / AI Vision Engine ✅ COMPLETE

**Plan:** `docs/dna_studio_master_plan_v2_5_qc.md` (v2.5 QC)
**Git:** `7a9e10b`, `0df848f`, `dfac10c`, `daf033e`, `3d38661`
**Tests:** 258/258 — xem `tests/test_mock.py`, `test_pass2a.py`, `test_phase5–8.py`, `test_vault.py`, `test_mode_a/b_contract.py`, `test_overlay_merge.py`, `test_cache.py`, `test_cli.py`, `test_subject_resolver.py`, `test_regeneration_policy.py`

**Các Phase hoàn thành:**
- Phase 0 Project Foundation · Phase 1 Shared Vision Core
- Phase 2 Mode A MVP · Phase 3 Mode B Core
- Phase 4 Project Layer + Overlay + Ven Hồ MVP
- Phase 5 Schema Bootstrap + Auto Classify
- Phase 6 Face Subject / Linh An (QC gate 07F)
- Phase 7 Hardening + Documentation (248 tests, contracts, docs đầy đủ)
- Phase 8 Studio Shell / UI (Next.js VenHo OS → localhost:3000/os)

**DNA subjects:** `lake_view_room` · `deluxe_double` · `lobby` · `facade` · `linh_an` · `westlake` · `outside`
**DNA contract:** `1.1` · **assets/raw/** và `output/` excluded khỏi git (.gitignore)

---

## M02 — Prompt Studio ✅ COMPLETE

**Plan:** `VENHO_AI_STUDIO_Module_02_Prompt_Studio_Plan_v1.1.md`
**Git:** `07535a4`
**Tests:** 347/347 — xem `test_image_prompt_builder.py`, `test_video_prompt_builder.py`, `test_content_prompt_builder.py`, `test_seo_prompt_builder.py`, `test_prompt_manifest.py`, `test_optimizer.py`, `test_optimizer_mock.py`, `test_mvp_image_prompt.py`, `test_pipeline.py`, `test_pipeline_manifest_integration.py`, `test_knowledge_reader.py`, `test_template_loader.py`, `test_prompt_renderer_and_store.py`, `test_prompt_cli.py`, `test_step15_comprehensive.py`, `test_prompt_contract_schema.py`

**Các Stage hoàn thành:** 5 stages / 16 steps
- Stage 1 Foundation · Stage 2 Image Prompt · Stage 3 Video Prompt
- Stage 4 Content + SEO Prompt · Stage 5 Manifest + CLI + Optimization

**Pipeline:** Build → Validate #1 (structural) → Optimize (Claude, temp 0) → Validate #2 (faithfulness) → Manifest-aware Render/Store
**Prompt types:** `image` · `video` · `content` · `seo`
**Manifest + Regeneration Policy:** DNA/template không đổi → `no_change` · đổi → archive `_archive/` + bump version
**⚠️ Test discipline:** luôn dùng `optimize_fn=optimize_mock` — default gọi Claude API thật

---

## M03 — Validator Studio ✅ COMPLETE

**Plan:** `VENHO_AI_STUDIO_Module_03_Validator_Studio_Plan_v1_1.md`
**Git:** `9b6c76b`
**Tests:** 26/26 — xem `test_validator.py`, `test_validator_studio.py`

**4 validator types hoàn thành:**
- `image_validator.py` — DNA match, forbidden kill-switch (cap=40 nếu severity=high), authenticity
- `prompt_validator.py` — advisory (không chặn M02), DNA coverage, forbidden conflict
- `face_validator.py` — 07F binary gates + weighted score; grounding OFF
- `content_validator.py` — brand_fit/tone/clarity/CTA/language_fit/production_readiness

**Scoring:** AI observe enum (match/partial/mismatch/not_visible) → code score deterministic
**Kill-switch:** forbidden severity=high → cap overall=40, verdict=regenerate
**CLI:** `venho validate image|prompt|face|content ...`
**Docs:** `docs/how_to_run_validator_studio.md`

---

## M04 — Automation Studio ✅ COMPLETE

**Plan:** `VENHO_AI_STUDIO_Module_04_Automation_Studio_Plan_v1_1.md`
**Git:** `bceef45`
**Tests:** 7/7 — xem `test_automation_studio.py`

**Tính năng chính:**
- Workflow config YAML-first: `config/workflows/` (4 workflows sẵn)
- Action registry: 7 actions (3 knowledge, 1 prompt, 2 validator, 1 manual_gate)
- Run lock (chặn chạy song song) + Resume từ `resumable_from`
- `skip_dependents`: BFS transitive — bước fail → bước `needs` nó skip, không chạy input rỗng
- Dry-run: kiểm config/params/paths trước khi chạy thật
- Manual gate: two-half pipeline (Nửa 1: DNA→Prompt; Nửa 2: image→validate)
- Scheduler: parse nhưng chưa bật (manual first)

**CLI:** `venho auto run {workflow_id}` · `venho auto resume {run_id}` · `venho auto list` · `venho auto actions`

---

## M05 — Content Studio ✅ COMPLETE (deterministic + real Claude adapter gated)

**Plan:** `VENHO_AI_STUDIO_Module_05_Content_Studio_Plan_v1_1.md` (§19 ghi status hoàn thành)
**Git:** `8c95194`
**Tests:** 22/22 — xem `test_content_studio.py`, `test_content_prompt_builder.py`, `test_prompt_contract_schema.py`

**16 steps hoàn thành** (Giai đoạn 0–4):

| Giai đoạn | Steps | Nội dung |
|-----------|-------|---------|
| 0 Nền tảng | 0–2 | Module setup, Request/Output schema, Project content config |
| 1 Cầu nối | 3–4 | Prompt Bridge (gọi M02), Content Context Loader |
| 2 MVP Social | 5–8 | Social Builder, Renderer, Validator Bridge, Acceptance test |
| 3 Mở rộng | 9–13 | Blog SEO, Website, OTA, FAQ, Email |
| 4 Đa kênh | 14–16 | Campaign Generator, Content Calendar, Manifest + CLI |

**Content types:** social (FB/IG/Threads/TikTok) · blog SEO · website copy · OTA (Agoda+Google+direct) · FAQ · email draft · campaign · calendar

**Runtime policy:**
- Deterministic builders/mock generator vẫn là default trong tests — 0 API call.
- Real Claude adapter đã có và chỉ chạy khi được gọi rõ ràng với credentials; pytest dùng fake-client coverage.
- Phase 5 đã thêm `contract_refs/outfit_id` trace từ M02 → M05 → M03.

---

## M06 — Video Studio ✅ COMPLETE (MVP — bugs fixed, design hardened)

**Plan:** `VENHO_AI_STUDIO_Module_06_Video_Studio_Plan_v1_1.md`
**Git:** `155b5f9` scaffold; các bug fix 2026-07-09 và Phase 5/6/7 hardening đã commit trong lịch sử sau đó.
**Tests:** 15/15 — xem `tests/test_video_studio.py` (9) + `tests/test_video_prompt_builder.py` (6)

**Pipeline đầy đủ:**
- `video_engine.py` orchestrates: context → concept → storyboard → shot list → per-scene M02 prompt → engine format → M05 caption/hook/CTA → M03 validation bridge → MD/JSON output → manifest
- M02 bridge: scene prompts qua `build_video_prompt`, M06 không tự dựng prompt cảnh
- M05 bridge: caption/hook/CTA lấy từ Content Studio, M06 không tự sinh text
- M03 bridge: prompt validation per scene, degrade advisory (`warning`/`not_available`)
- Continuity: DNA invariants + Face DNA khi `include_character=true`; thiếu Face DNA → fail rõ
- Renderers: `.md` + `.json`; manifest `data/projects/<project>/video/video_manifest.json`
- CLI: `venho-video generate --topic "..." --duration 15 --type social_reel --subjects lake_view_room,westlake`

**Bugs đã fix (2026-07-09):**
- `engine_formatter.py` — aspect ratio thực (`"9:16"`) điền vào engine prompt, không còn là prose
- `content_bridge.py` — `youtube_shorts` → `tiktok_caption` (không còn fallback sai sang `facebook_post`)
- `validator_bridge.py` — subject lấy từ primary env DNA (non-linh_an/non-character) thay vì `[-1]`

**Design improvements (2026-07-09):**
- `storyboard_builder.py` — 5 bộ scene templates theo `video_type`: social_reel · character · hotel_lifestyle · website_hero · explainer
- `shot_list_builder.py` — angle/motion_note/lighting_note động theo scene position và camera_movement
- `engine_formatter.py` + `templates/*.yaml` — template notes được embed vào engine prompt (AI-facing, không còn internal references)
- Xóa `video_studio/video_request.py` (redundant re-export)
- `venho-video` CLI available trong PATH sau `pip install -e .`

**Ranh giới giữ nguyên:**
- Chỉ tạo pre-render package; không render, không upload, không publish
- Post-render video validation là future work
- Spatial/brand forbidden single-source qua M02/DNA; video config chỉ giữ motion/camera/character rules
- Phase 5 đã thêm `outfit_id` continuity lock và `contract_refs` vào video package.

---

## M07 — Publishing Gateway ✅ COMPLETE (offline dry-run MVP)

**Plan:** `VENHO_AI_STUDIO_Module_07_Publishing_Gateway_Development_Plan_v1_2_QC.md`
**Tests:** 19/19 — xem `tests/test_publishing_gateway_scaffold.py`, `tests/test_publishing_gateway.py`
**CLI smoke:** `python3 -m publishing_gateway.cli publish --package-file data/projects/venho_hotel/publishing/fixtures/approved_package.json --approval-secret test-secret --dry-run --data-root /tmp/venho_m07_cli_check`

**Vai trò:** Nhận package đã duyệt từ M04 → kiểm contract/approval/brand/capability → queue/adapters → delivery receipt cho M08. Không tạo content, không sửa caption/hashtag, không quyết định giờ đăng, không chứa logic Agent.

**Đã hoàn thành:**
- Step 0–2 — Scaffold, schemas/contracts, base adapter + mock adapter
- Step 3–7 — Approval verifier (HMAC/TTL), contract validator, brand guard, platform capability, idempotency + receipt store
- Step 8–11 — Publisher queue, circuit breaker, rate-limit policy, token vault
- Step 12–15 — Facebook/Instagram Core MVP adapters + Threads/Google Business conditional adapters (offline payload mapping)
- Step 16–18 — Gateway router, delivery receipt JSON/Markdown, M08 handoff contract docs
- Step 19–20 — CLI publish/retry/receipt/queue/version + end-to-end dry-run acceptance
- Step 21 — Controlled real API checklist documented; not run in pytest

**MVP scope theo plan v1.2:**
- Core MVP: Facebook Page + Instagram Business
- Conditional MVP: Threads + Google Business Profile, mặc định feature-flag off
- Automated tests luôn offline, không đọc secret thật, không gọi API thật

**Artifacts chính:**
- Package: `publishing_gateway/`
- Config: `config/projects/venho_hotel/publishing/`
- Fixture: `data/projects/venho_hotel/publishing/fixtures/approved_package.json`
- Docs: `docs/how_to_run_publishing_gateway.md`, `docs/contracts/m07_to_m08_delivery_receipt.md`

**Ranh giới còn giữ:**
- Real API publish là controlled manual test, không chạy tự động.
- Adapter live chưa gọi network; hiện map payload và dry-run an toàn.
- M07 chỉ phân phối package đã duyệt, không sáng tạo hay chỉnh nội dung.

---

## M08 — Analytics & Feedback Loop ✅ COMPLETE (offline MVP, code reviewed)

**Plan:** `VENHO_AI_STUDIO_Module_08_Analytics_Feedback_Development_Plan_v1_2_QC.md`
**Tests:** 7/7 — xem `tests/test_analytics_feedback.py`
**Historical full suite at completion:** `430/430` pass, 0 API call. **Current full suite:** `443/443` pass.
**Code review:** 2026-07-09 — 5 bugs fixed (commit `373b1cc`)

**Vai trò:** Nhận Delivery Receipt từ M07 → tạo collection tasks → mock collect metrics → chuẩn hóa unified metrics → tính derived stats/baseline/score → sentiment guardrail → sinh alert/advisory/report. M08 chỉ sinh output advisory, không tự apply vào M01/M05.

**Đã hoàn thành MVP:**
- Step 0–2 — Scaffold, schemas/contracts, base metrics adapter + mock adapter offline
- Step 3–5 — Ingestion router, collection scheduler, raw/snapshot stores idempotent
- Step 6–9 — Unified Metrics Standardizer, stats calculator, baseline calculator, performance scorer, score store
- Step 10–11 — Rule-based sentiment scorer song ngữ vi/en + critical alert generator/store
- Step 12–14 — Feedback advisory generator, advisory/report renderers và stores
- CLI entrypoint: `venho-analytics` / `analytics_feedback.cli`

**Artifacts chính:**
- Package: `analytics_feedback/`
- Config: `config/projects/venho_hotel/analytics/`
- Test: `tests/test_analytics_feedback.py`

**Ranh giới còn giữ:**
- Không gọi API thật trong pytest; mock metrics adapter là mặc định.
- Không tự publish, không tự sửa Knowledge, không tự đổi Content Strategy.
- Advisory luôn `pending_approval`, `approval_required=true`, route qua `M04_AUTOMATION_STUDIO` / `M09_AGENT_STUDIO`.

---

## M09 — Agent Studio ✅ COMPLETE (offline planning/orchestration MVP, reviewed + bugs fixed)

**Plan:** `VENHO_AI_STUDIO_Module_09_Agent_Studio_Development_Plan_v2_2_QC.md`
**Tests:** 10/10 — xem `tests/test_agent_studio.py`
**Historical full suite at completion:** `430/430` pass, 0 API call. **Current full suite:** `443/443` pass.
**Code review:** 2026-07-09 — 3 bugs fixed (commit `373b1cc`)

**Vai trò:** Cognitive Interface / Agent Orchestration Layer. Nhận goal tự nhiên → validate request → route persona → load context → detect missing knowledge → tạo TaskPlan → classify risk → đóng gói ModuleRequest qua M04 → aggregate response Markdown/JSON. M09 không tự publish, không tự sửa Knowledge, không bypass M04.

**Đã hoàn thành MVP:**
- Step 0–2 — Scaffold, contracts/schemas, BaseAgent interface offline
- Step 3–7 — Request validator, router, persona resolver, context loader, missing knowledge detector
- Step 8–10 — Task planner, risk classifier đọc `agent_policy.yaml`, module request builder luôn route qua `M04_AUTOMATION_STUDIO`
- Step 11–13 — Automation bridge mock/dry-run, result aggregator + execution log, Markdown/JSON renderers
- Step 14–18 — Generic agent classes + templates: documentation, research, content planning, visual planning, analytics insight
- Step 19–23 — Base persona template, Ven Hồ agent policy, marketing agent config, Linh An brand agent config, project acceptance
- Step 24–26 — CLI `venho-agent` / `agent_studio.cli`, E2E dry-run, MVP acceptance

**Artifacts chính:**
- Package: `agent_studio/`
- Config: `config/projects/venho_hotel/agents/`
- Test: `tests/test_agent_studio.py`
- CLI: `venho-agent --agent marketing_agent --project venho_hotel --goal "..." --plan-only`

**Ranh giới còn giữ:**
- M09 chỉ lập kế hoạch và đóng gói yêu cầu; M04 là execution gateway.
- Publishing request chỉ thành manual gate / module request; M09 không gọi M07 trực tiếp.
- Required knowledge thiếu trả `ERR_MISSING_KNOWLEDGE`.
- Destructive action bị block theo policy; external impact yêu cầu approval.

**Phase 6 hardening đã xong:**
- Missing knowledge hiện hard-stop trước M04 dispatch và trả `ERR_MISSING_KNOWLEDGE`.
- `--execute` vẫn qua M04 boundary; execution thật phải dùng workflow runner/capability contract, không bypass M04.

---

## M10 — VenHo OS Dashboard ✅ COMPLETE v3.0 (Next.js OS Stage A+B+C — Streamlit đã xóa 2026-07-13)

**Plan:** `VENHO_AI_STUDIO_Module_10_Dashboard_Plan_v1_2.md`
**Repo runtime:** `venho-os` Next.js 16 App Router (`/os`)  
**Current OS tests:** `npm test -- --run` → 65/65; `npm run lint`; `npx tsc --noEmit`; `npm run build` pass  
**AI Studio Python suite:** 443/443 pass, 0 API call  

**Quyết định kiến trúc:** M10 đã chuyển hẳn khỏi Python/Streamlit. `venho-ai-studio` giữ engine/contracts M01–M09; `venho-os` giữ UI/BFF/job boundary.

**Current Image Studio trong `venho-os`:**
- Workbench: Mode A/B SSE, upload ảnh, normalize ảnh server-side, output dir dùng thật.
- Knowledge: DNA Library, Vault Search, Mode C Linh An, status artifact theo run, upload duplicate bị chặn.
- Creative Studio: Tạo Ảnh AI, Social Post, Video Script.
- Image generation: durable file-backed jobs, status API, cancel, history, manifest 1.1.
- Wardrobe: dynamic Wardrobe Index 1.0; selector không còn hardcode hai outfit trong UI.
- QC: image/face validation, manifest trace face/outfit/location/reference, partial validation errors là `UNVALIDATED`.
- QA: `/api/v1/studio/quality-matrix` đọc controlled live matrix; không chạy paid generation.

**Historical note:** Các dòng cũ về `ui/studio_app.py`, Streamlit path bugs và Command Palette là lịch sử trước 2026-07-13, không còn là runtime hiện tại.

---

## Git Log gần nhất liên quan AI Studio v1.5

```
AI Studio:
b975466 Add Phase 7 QA closeout matrix
b01c429 Add Phase 6 ops workflow controls
7291eeb Integrate contract refs across prompt content video validation
484dc20 Add Linh An wardrobe index
811c473 Enforce face validation contract
b8c34e3 Record Mode C wardrobe quarantine registry
976922b Add strict Mode C wardrobe routing
5d918d8 Sanitize Phase 0 baseline note

VenHo OS:
6beff50 Expose Studio quality matrix
7ce0548 Integrate dynamic Studio wardrobe index
0138168 Add durable Studio generation jobs
b54059e Complete image QC manifest handling
736c18e Upgrade image generation manifest contract
70a4ee7 Honor Mode C quarantine and Mode A output
836e503 Wire Mode C wardrobe data integrity
4aa6651 Isolate image route tests from production artifacts
6e2a93c Improve image generation identity controls
```

---

## Cách cập nhật file này

Cập nhật `task_status.md` mỗi khi:
- Hoàn thành một module hoặc stage quan trọng
- Test count thay đổi
- Commit mới liên quan đến status module
