# VENHO AI STUDIO — Task Memory
**Repo:** `venho-ai-studio` · **Workspace:** THE WEST LAKE LIVING
**Cập nhật:** 2026-07-09 (Kết thúc Task M10 Dashboard MVP) · **Đọc bởi:** AI Engine, Claude Code sessions

---

## 1. Mục tiêu hệ thống

Biến ảnh thực và Brand DNA thành nội dung marketing chất lượng cao — hoàn toàn trên nền tảng tri thức chuẩn hóa, có approval gate trước khi phân phối, không tự publish khi chưa được duyệt.

Pipeline tổng quát:

```
Ảnh thực → [M01] DNA JSON → [M02] Prompt → [AI Engine ngoài tạo ảnh/video] → [M03] Validate
                           → [M05] Content prose → [M03] Validate
                           → [M06] Video storyboard → [AI Engine ngoài render video]
[M09] nhận goal tự nhiên → lập plan/risk/module requests → [M04] điều phối + approval gate → [M07] Publishing Gateway dry-run/publish receipt → [M08] Analytics Feedback
[M10] Dashboard đọc artifacts/config của M01-M09 → hiển thị unified presentation layer
```

---

## 2. Kiến trúc tổng thể

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
| **M10** Dashboard | Unified presentation UI đọc M01-M09 artifacts/config và hiển thị trạng thái | Lưu DB nghiệp vụ, tính lại score/HMAC, build prompt/ModuleRequest, render/upload/publish |

### Nguyên tắc bất biến

1. **M02 dựng prompt, M05 thực thi** — không hoán đổi vai.
2. **M04 chỉ điều phối qua adapter** — không import sâu logic module con.
3. **Archive thuộc module con** — M04 không overwrite file production.
4. **Draft/approval first** — mọi output là draft cho tới khi M04 approval hợp lệ; M07 chỉ thực thi package đã duyệt.
5. **0 API call trong tests** — tất cả offline/mock.
6. **Config-first** — workflow/rule khai báo YAML, không hard-code.
7. **Project-agnostic core** — Ven Hồ là project đầu tiên, không phải core.
8. **Kết thúc task = cập nhật memory/status** — khi người dùng nói "kết thúc task", Codex tự động cập nhật `task_memory.md` và `task_status.md` trước khi chốt.
9. **M10 presentation-only** — Dashboard degrade bằng advisory khi module con thiếu artifact; không làm sập toàn UI và không sao chép business logic.

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
| M10 Dashboard snapshot | `contract = "presentation_only"` | Read-only normalized view over module artifacts |

### DNA subjects (venho_hotel)
`lake_view_room` · `deluxe_double` · `lobby` · `facade` · `linh_an` · `westlake` · `outside`

Mỗi subject có: `_DNA.md` + `_DNA.json` + `_DNA_COMPACT.md` + `overrides.yaml` + `dna_manifest_*.json`

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
streamlit run ui/studio_app.py
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
- M10 snapshot: `dashboard.gateway` đọc config/artifacts của M01-M09, Face Lock display threshold, graceful advisory khi thiếu dữ liệu; không gọi API và không mutate data ✅

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
├── dashboard/                 ← M10 read-only presentation gateway for Streamlit Dashboard
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
├── tests/                     ← 428 tests, 0 API call
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
- Follow-up hardening: khi missing required knowledge, flow nên dừng cứng ngay sau detector; hiện response trả `FAILED / ERR_MISSING_KNOWLEDGE` nhưng mock module requests vẫn được chuẩn bị.
- Follow-up execution: `--execute` hiện vẫn là prepared/mock M04 bridge; khi chuyển sang execution thật phải nối qua public API của M04, vẫn giữ approval gate.

---

## 11. M10 Dashboard — hoàn thành 2026-07-09

**Status:** ✅ COMPLETE — Streamlit presentation MVP  
**Plan:** `VENHO_AI_STUDIO_Module_10_Dashboard_Plan_v1_2.md`  
**Tests:** `python3 -m pytest` → 428/428 pass, 0 API call  
**Module tests:** 5 tests — `tests/test_dashboard.py`

### Quyết định kiến trúc

M10 mở rộng Studio Shell Streamlit hiện có (`ui/studio_app.py`) thay vì tạo Next/Nuxt/Vite app riêng. Lý do: repo đã có local-first Studio Shell tại `localhost:8501`, nên M10 giữ một entrypoint duy nhất và tránh thêm stack mới.

### Core files

- `dashboard/gateway.py` — read-only adapter đọc M01-M09 config/artifacts và tạo `DashboardSnapshot`.
- `dashboard/__init__.py` — module metadata (`MODULE_ID = "M10"`).
- `ui/studio_app.py` — thêm màn hình `M10 Dashboard — Unified Control Center`.
- `docs/how_to_run_studio_ui.md` — hướng dẫn chạy shell + dashboard.

### M10 boundaries

- Không có DB nghiệp vụ riêng; chỉ đọc `config/projects/`, `data/projects/`, `data/automation_runs/`.
- Không tính lại score/verdict/HMAC; chỉ hiển thị output do module core tạo.
- Không build prompt, không build ModuleRequest, không render/upload/publish.
- Missing artifact tạo advisory theo module thay vì làm sập dashboard.
- Face Lock gate chỉ là display mapping theo plan: `>=9.0 APPROVED`, `8.0-8.9 CONDITIONAL`, `<8.0 REJECT`; score 0-100 được normalize để hiển thị.

---

## 12. Task Closing Protocol

Khi người dùng nói **"kết thúc task"**, Codex phải tự động:

1. Cập nhật `task_memory.md` nếu có quy ước, kiến trúc, contract, CLI, hoặc integration seam mới.
2. Cập nhật `task_status.md` nếu module/stage/test count/commit/package mẫu thay đổi.
3. Ghi rõ commit hash, test command/kết quả, output mẫu nếu có.
4. Kiểm tra `git status --short` và báo working tree còn sạch hay còn thay đổi.
