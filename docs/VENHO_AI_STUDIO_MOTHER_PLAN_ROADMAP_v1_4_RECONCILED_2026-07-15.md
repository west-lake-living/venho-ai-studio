# VENHO AI STUDIO — MOTHER PLAN RECONCILED ROADMAP v1.4

> **⚠️ SUPERSEDED BY v1.5** — `VENHO_AI_STUDIO_MOTHER_PLAN_ROADMAP_v1_5_IMPLEMENTATION_2026-07-16.md` (2026-07-16) là baseline điều hành hiện hành. v1.5 đảo thứ tự ưu tiên (Baseline/Security → Mode C Data Integrity → Image/Validator Quality → ... thay vì build Mode C C0–C7 đầy đủ trước) dựa trên bằng chứng run thật cho thấy Mode C có bug fallback schema và Face Validator thiếu gate. Giữ file này làm tài liệu lịch sử/audit trail — **không dùng làm baseline thực thi**.

**Ngày chốt hiện trạng:** 2026-07-15  
**Thay thế bản điều hành:** `VENHO_AI_STUDIO_MOTHER_PLAN_ROADMAP_v1_3_QC_PROGRESS_BASELINE.md`  
**Phạm vi đối chiếu:** `venho-ai-studio` + `venho-os`  
**Nguyên tắc:** code và acceptance test là bằng chứng ưu tiên; tài liệu cũ được giữ làm lịch sử, không dùng làm baseline build.

---

# 1. KẾT LUẬN RECONCILIATION

AI Studio không còn ở trạng thái của baseline 2026-07-09 trong v1.3. Đến 2026-07-15:

1. M01–M09 vẫn hoàn thành trong scope baseline; không build lại.
2. Full Python suite hiện tại là **423/423 pass, 0 API call**, không phải 430/430.
3. Chênh lệch 7 tests đến từ việc xóa M10 Streamlit và `tests/test_dashboard.py` ngày 2026-07-13.
4. M10 đã chuyển hoàn toàn sang **VenHo OS Dashboard bằng Next.js**; Streamlit không còn là runtime hiện tại.
5. Repo `venho-os` đã tồn tại và được tách thành repo độc lập ngày 2026-07-14. Phase 6 trong v1.3 không còn là external dependency chưa tồn tại.
6. Mode C Linh An Wardrobe DNA đã có scaffold thực dụng trong config và UI, nhưng chưa đạt full contract pipeline C0–C7 của Mother Plan.
7. Creative image generation đã có user-triggered API route, prompt builder, manifest và validator. Tuy nhiên chưa có AiStudioPort chuẩn hóa theo 6 coarse capabilities.
8. M05 đã có real Claude generator cho non-social content từ 2026-07-15; test suite vẫn dùng mock/offline để không phát sinh API cost.

> **Baseline lock mới:** mọi agent phải bắt đầu từ trạng thái trên. Không khôi phục Streamlit, không tạo lại repo `venho-os`, không build lại M01–M09, và không dùng mốc 430 tests làm acceptance hiện tại.

---

# 2. NGUỒN SỰ THẬT HIỆN HÀNH

| Ưu tiên | Nguồn | Vai trò |
|---:|---|---|
| 1 | Code + tests trong `venho-ai-studio` và `venho-os` | Bằng chứng implementation hiện tại |
| 2 | `venho-ai-studio/task_status.md` cập nhật 2026-07-15 | Module status và acceptance baseline |
| 3 | `venho-ai-studio/task_memory.md` | Quyết định, history và known gaps |
| 4 | `venho-os/CHANGELOG.md` | Bằng chứng tách repo và thay đổi dashboard |
| 5 | Mother Plan v1.4 này | Roadmap điều hành sau reconciliation |
| 6 | Mother Plan v1.3 và các bản cũ | Tài liệu lịch sử để truy vết, không phải execution baseline |

Nếu tài liệu và code mâu thuẫn, phải kiểm tra code + tests trước, sau đó cập nhật tài liệu. Không sửa code chỉ để khớp một mô tả đã lỗi thời.

---

# 3. ACCEPTANCE BASELINE NGÀY 2026-07-15

| Repo | Acceptance đã verify | Kết quả |
|---|---|---|
| `venho-ai-studio` | `python3 -m pytest -q` | **423 passed**, 0 API call |
| `venho-os` | `npm test -- --run` | **37 passed** trong 6 test files |

Ghi chú:

- M10 có **0 Python unit test** trong AI Studio vì runtime và test ownership đã chuyển sang `venho-os`.
- Số test theo từng module trong `task_status.md` là milestone/module-specific, không cộng dồn để suy ra full suite.
- Mỗi phase mới phải giữ `423/423` Python tests và không làm giảm test baseline của `venho-os`.

---

# 4. MA TRẬN HIỆN TRẠNG M01–M10

| Module | Hiện trạng đã có | Trạng thái reconciled | Gap thực sự còn lại |
|---|---|---|---|
| M01 Knowledge Studio | Mode A/B, cache, overlay, versioning, DNA 1.1; Mode C scaffold + 6 subject YAML | **COMPLETE baseline / MODE C PARTIAL** | Formal C0–C7, item/outfit/index contracts, dedupe, matrix, manifest, compact context |
| M02 Prompt Studio | Image/video/content/SEO prompt pipeline, manifest, optimizer | **COMPLETE baseline** | Wardrobe refs, forbidden styling, traceability; contract 1.1 |
| M03 Validator Studio | Image, prompt, face, content validators; deterministic scoring | **COMPLETE baseline** | Wardrobe validators, `identity_fit`, continuity, thresholds |
| M04 Automation Studio | YAML workflows, registry, dry-run, resume, manual gate | **COMPLETE baseline** | `wardrobe_ingest`; real M09 bridge |
| M05 Content Studio | 8 content types; real Claude generator cho non-social, mock-safe tests | **COMPLETE baseline** | Wardrobe-aware rotation/context; production QC theo contract |
| M06 Video Studio | Storyboard, shot list, Face continuity, M02/M03/M05 bridges | **COMPLETE baseline** | Wardrobe outfit lock và cross-shot continuity; contract 1.1 |
| M07 Publishing Gateway | Offline dry-run MVP, approval/request/receipt | **COMPLETE baseline** | Không build lại; giữ Core FB+IG, Conditional Threads+GBP |
| M08 Analytics | Offline analytics/advisory pipeline | **COMPLETE baseline** | Agent consumption loop |
| M09 Agent Studio | AS0–AS2 planning/orchestration MVP | **COMPLETE baseline / MATURITY PARTIAL** | Hard-stop missing knowledge; AS3–AS6 |
| M10 Dashboard | VenHo OS Next.js v3.0; Workbench, Creative Studio, Knowledge, Reports, Mode C UI | **COMPLETE current runtime** | Full Wardrobe Workspace UX; formal coarse adapter boundary |

---

# 5. RECONCILIATION CÁC ĐIỂM SAI CỦA v1.3

| ID | Mô tả trong v1.3 | Thực tế 2026-07-15 | Xử lý trong v1.4 |
|---|---|---|---|
| R1 | M10 v4.0 là Streamlit, có 7 tests | Streamlit và test dashboard đã xóa | Đánh dấu **SUPERSEDED**; M10 runtime là Next.js trong `venho-os` |
| R2 | Full suite 430/430 | Full suite hiện tại 423/423 | Khóa baseline mới là 423 |
| R3 | `venho-os` chưa tồn tại, cần DR-OS-01 để khởi tạo | Repo đã tồn tại và đã tách độc lập | DR-OS-01 chuyển thành governance catch-up, không còn là entry blocker |
| R4 | Mode C hoàn toàn là gap | Đã có UI tab, Wardrobe DNA Library và 6 YAML schemas | Đánh dấu **PARTIAL IMPLEMENTATION**; chỉ build phần contract/pipeline còn thiếu |
| R5 | Phase 5 cần re-scope M10 trong tương lai | Migration đã xảy ra 2026-07-13 | CR-M10-01 chuyển thành retrospective architecture record |
| R6 | Mother Dashboard là phase xa trong tương lai | VenHo OS Dashboard đang vận hành và đã mở rộng thêm bounded contexts | Tập trung adapter/coarse capability hardening, không build dashboard mới |
| R7 | Creative Studio subprocess trong Streamlit | Next.js API route đang gọi generator/validator | Giữ user-triggered flow; chuẩn hóa contract và isolation, không phục hồi flow cũ |
| R8 | M05 prose generator chỉ deterministic/mock | Real Claude generator đã có cho non-social | Cập nhật COMPLETE; vẫn giữ offline test discipline |

---

# 6. KIẾN TRÚC ĐÍCH ĐÃ KHÓA

## 6.1 Repo ownership

| Repo | Ownership |
|---|---|
| `venho-ai-studio` | M01–M09, knowledge contracts, prompt/validation/automation/content/video/publishing/analytics/agent core |
| `venho-os` | M10 presentation/runtime, founder workspace, API/BFF adapters, Creative Studio UI, OS bounded contexts |

M10 không được đưa trở lại AI Studio Python/Streamlit. AI Studio cung cấp contract và engine; VenHo OS cung cấp UI và orchestration boundary cho người dùng.

## 6.2 Image generation contract hiện hành

Input bắt buộc: `topic`, `scenario`, `size`, `prompt`, `linhAn`.  
Input tùy chọn: `action`, `outfit`, `faceReference`, `dnaVersion`.

Mỗi generation thành công phải có:

- `image.png`;
- `manifest.json`;
- run/variant directory duy nhất;
- input và prompt snapshot;
- DNA subject/version;
- reference mode;
- QC result hoặc validation error rõ ràng.

Quy tắc vận hành:

- Không provider call khi render trang.
- User-triggered generation được phép.
- Scenario reference chỉ lấy từ trusted server mapping.
- Linh An có mặt thì phải chạy face validation.
- Scenario có DNA subject thì phải chạy image validation.
- Validator fail là `UNVALIDATED`, không được gán `APPROVED`.
- Generation mới không ghi đè artifact cũ.

## 6.3 Mode C boundary

Mode C hiện tại là implementation scaffold, không được ghi là full Wardrobe DNA system cho tới khi có đủ:

- Item Contract 1.0;
- Outfit Contract 1.0;
- Wardrobe Index Contract 1.0;
- compatibility matrix và forbidden pairings;
- wardrobe manifest;
- compact wardrobe context;
- M03 `identity_fit` và wardrobe validation;
- traceability qua M02/M03/M06;
- M04 `wardrobe_ingest` có Human Review gate.

Core path phải generic:

```text
data/projects/<project>/knowledge/wardrobe/<character>/
```

Linh An là instance đầu tiên qua config, không hard-code trong core engine.

---

# 7. CONTRACT VERSION BASELINE

| Contract | Version hiện tại | Thay đổi dự kiến |
|---|---:|---|
| M01 DNA | 1.1 | Giữ; M02 accept `[1.1, 2.0)` |
| Wardrobe Item / Outfit / Index | Chưa formal | Tạo mới 1.0 |
| M02 Prompt | 1.0 | Bump 1.1 khi thêm wardrobe refs |
| M05 Content output | 1.0 | Giữ nếu output schema không đổi |
| M06 Video package | 1.0 | Bump 1.1 khi thêm outfit/item continuity |
| M07/M08/M09 | 1.0 | Giữ |
| AiStudioPort job contract | Chưa formal | Tạo mới 1.0 |

Quy ước brand tiếp tục giữ:

- AI prompt: `Ven Ho Hotel`;
- UI/display: `Ven Hồ Hotel`;
- hashtag: không dấu.

---

# 8. ROADMAP GAP-BASED TỪ 2026-07-15

## PHASE 0 — DOCUMENTATION & GOVERNANCE CATCH-UP

**Trạng thái:** bắt đầu bằng tài liệu v1.4 này.

Gap work:

1. Lập retrospective architecture record cho việc M10 chuyển từ Streamlit sang `venho-os` Next.js.
2. Đóng CR-M10-01 và DR-OS-01 theo kết quả đã implemented; không để chúng tiếp tục làm blocker giả.
3. Gắn nhãn historical/superseded cho các dòng còn ghi 430 tests/Streamlit trong `task_status.md` và `task_memory.md`; không xóa history.
4. Đăng ký contract versions mới trước khi code Mode C formal.

**Exit Gate:** tài liệu và task records không còn đưa ra hai baseline vận hành mâu thuẫn.

## PHASE 1 — FORMALIZE MODE C WARDROBE C0–C7

**Baseline đã có:** Mode C UI, project `linh_an`, wardrobe schema và 5 outfit presets.

| Step | Gap deliverable |
|---|---|
| C0 | Classifier: item / outfit / mixed |
| C1 | Item observation schema và pipeline |
| C2 | Deterministic dedupe và identity match |
| C3 | Item DNA Markdown + JSON, contract 1.0 |
| C4 | Outfit extraction và outfit contract |
| C5 | Compatibility matrix + curated forbidden pairings |
| C6 | Generic Wardrobe Index + manifest |
| C7 | Compact Wardrobe Context cho prompt/agent |

**Exit Gate:** batch wardrobe thật tạo đủ item/outfit/index/manifest; overlay sống qua regenerate; core không hard-code `linh_an`; full offline suite pass.

## PHASE 2 — INTEGRATE WARDROBE INTO M02/M03/M05/M06

Gap work:

1. M02 Prompt 1.1: Character DNA + Outfit Capsule + Context DNA + negative wardrobe rules.
2. M03: item consistency, outfit consistency, palette, forbidden styling, context suitability, cross-shot continuity và `identity_fit`.
3. M05: outfit-aware description và rotation/overuse context; không tự chọn item khi request không cho phép.
4. M06 Video 1.1: khóa `wardrobe_outfit_id`, item refs và continuity qua shot.
5. Khóa threshold `identity_fit` trong `wardrobe_rules.yaml`; trước thời điểm đó không gán pass/reject tùy ý.

**Exit Gate:** wardrobe ID trace được từ prompt → content/video package → validation; forbidden rule có prevention và detection; backward compatibility pass.

## PHASE 3 — M04 WARDROBE WORKFLOW & MVP 3

Thêm workflow `wardrobe_ingest`:

```text
New Wardrobe Folder
  -> M01 Mode C
  -> M03 Wardrobe Validation
  -> Human Review Gate
  -> Wardrobe Index Update
  -> M02 Availability
```

MVP 3 end-to-end:

```text
Wardrobe Images
  -> Mode C
  -> Index
  -> M02 Outfit Prompt
  -> M06 Video Package
  -> M03 Wardrobe Continuity Validation
```

**Exit Gate:** mock E2E pass; một controlled real run có manifest/QC; validation fail chặn index update.

## PHASE 4 — M09 AGENT MATURITY

| Stage | Trạng thái | Gap |
|---|---|---|
| AS0 Runtime Foundation | DONE | Bảo vệ regression |
| AS1 Read-only Copilots | DONE | Bảo vệ regression |
| AS2 Planning Agents | DONE | Bảo vệ plan-only boundary |
| AS3 Workflow Copilots | GAP | Nối public M04 bridge, không bypass approval |
| AS4 Guarded Operator | GAP | Approval, idempotency, action log, kill switch |
| AS5 Feedback-aware Advisor | PARTIAL | Tiêu thụ M08 advisory và wardrobe overuse |
| AS6 Productized Agent | GAP | Chỉ mở sau Living Lab evidence |

Hardening ưu tiên: `detect_missing_knowledge` phải hard-stop và không build/dispatch request tiếp theo.

**Exit Gate:** agent không gọi M07 trực tiếp; external impact có approval record; missing knowledge trả lỗi rõ và không dispatch.

## PHASE 5 — M10 WARDROBE WORKSPACE COMPLETION

**Không build lại dashboard.** Mở rộng surface Next.js hiện tại bằng artifact read-only:

- item browser;
- outfit capsule browser;
- filter và signature badge;
- overuse warning;
- missing reference alert;
- continuity preview;
- curator notes;
- validation, approval, receipt và agent plan detail.

**Exit Gate:** người dùng ingest, review và trace Mode C qua UI; score và business logic vẫn thuộc module chủ quản, không copy vào component.

## PHASE 6 — AISTUDIOPORT & VENHO OS ADAPTER HARDENING

**Baseline đã có:** `venho-os`, Creative Studio UI, direct Studio API routes, generator, prompt builder, manifest và validators.

Gap work:

1. Định nghĩa AiStudioPort contract 1.0.
2. Chuẩn hóa 6 coarse capabilities:
   - `creative.create_social_package`;
   - `creative.create_video_script`;
   - `creative.validate_artifact`;
   - `creative.prepare_publication`;
   - `creative.get_job_status`;
   - `creative.open_studio_workspace`.
3. Chuẩn hóa durable job status, partial error, stale và retry/reconciliation behavior.
4. Giữ approve, execute và publish là ba transition riêng.
5. Không để VenHo OS gọi sâu vào internal M01–M09 ngoài public adapter.

**Exit Gate:** VenHo OS chỉ dùng coarse capabilities; Studio down không làm sập OS shell; render path có 0 provider call; side effect có job/audit evidence.

## PHASE 7 — LIVING LAB & PRODUCTIZATION

Chỉ productize khi có bằng chứng dùng thật:

- workflow chạy hàng tuần;
- output được dùng thật;
- founder hours saved được đo;
- lỗi và QC verdict được log;
- module có quyết định Continue / Simplify / Pivot / Kill;
- core không cần sửa riêng cho mỗi project;
- contract, mock, test và approval gate đầy đủ.

---

# 9. THỨ TỰ ƯU TIÊN THỰC THI

| Ưu tiên | Hạng mục | Lý do |
|---:|---|---|
| P0 | Documentation/governance catch-up | Loại baseline mâu thuẫn và tránh build trùng |
| P1 | Mode C contracts C0–C7 | Gap sản phẩm lớn nhất và là nền cho các phase sau |
| P2 | M02/M03/M05/M06 wardrobe integration | Tạo traceability và QC thật |
| P3 | M04 `wardrobe_ingest` + MVP 3 | Biến các module thành workflow vận hành |
| P4 | M09 AS3 + missing-knowledge hard-stop | Cho phép agent dùng workflow mà vẫn giữ approval |
| P5 | M10 Wardrobe Workspace | Hoàn thiện UX trên artifact đã ổn định |
| P6 | AiStudioPort hardening | Giảm coupling giữa OS và Studio trước khi mở rộng |
| P7 | AS4–AS6 + productization | Chỉ đầu tư khi Living Lab có evidence |

Không ước lượng lại toàn bộ M01–M10. Chỉ ước lượng gap work sau khi contract Phase 1 được khóa và batch wardrobe thật được chọn.

---

# 10. OPEN DECISIONS

| ID | Quyết định cần khóa | Trạng thái 2026-07-15 |
|---|---|---|
| OD-01 | Threshold `identity_fit` pass/conditional/reject | OPEN; phải khóa trước M03 wardrobe verdict |
| OD-02 | Batch wardrobe thật đầu tiên và expected labels | OPEN; cần cho acceptance Phase 1 |
| OD-03 | AiStudioPort transport: local HTTP/job file/queue abstraction | OPEN; khóa trong Phase 6 contract, không ảnh hưởng Phase 1 |
| OD-04 | Disclosure policy cho Linh An AI KOL theo từng kênh | OPEN; cần trước productization, không block Mode C core |

---

# 11. DEFINITION OF DONE TOÀN ROADMAP

Roadmap này chỉ được xem là hoàn thành khi:

1. Mode C đạt full C0–C7 và generic cho character/project.
2. Wardrobe traceability chạy qua M02, M03, M05 và M06.
3. `wardrobe_ingest` có Human Review gate và controlled real-run evidence.
4. M09 AS3 vận hành qua M04, hard-stop khi thiếu knowledge.
5. M10 Next.js có Wardrobe Workspace đầy đủ, không copy business logic.
6. VenHo OS tiêu thụ AI Studio qua AiStudioPort coarse capabilities.
7. Approval, execution và publication không bị gộp thành một action.
8. Full test suites pass, test không gọi paid API.
9. Mọi live generation có manifest và validator status trung thực.
10. Living Lab chứng minh output được dùng và tiết kiệm thời gian vận hành.

---

# 12. CHANGELOG v1.3 → v1.4

| Thay đổi | Nội dung |
|---|---|
| Baseline date | 2026-07-09 → 2026-07-15 |
| Python tests | 430/430 → 423/423 do xóa 7 M10 Streamlit tests |
| M10 runtime | Streamlit v4.0 → VenHo OS Next.js v3.0 |
| Repo dependency | `venho-os` chưa tồn tại → đã tồn tại, tách repo 2026-07-14 |
| Mode C | GAP toàn bộ → PARTIAL scaffold, còn thiếu formal C0–C7 |
| M05 | Mock-only → real Claude generator cho non-social, mock-safe tests |
| Governance | CR-M10-01/DR-OS-01 là future blockers → retrospective records cần đóng |
| Phase 5 | Re-scope M10 → hoàn thiện Wardrobe Workspace trên runtime hiện tại |
| Phase 6 | Khởi tạo Mother Dashboard → harden AiStudioPort và adapter |
| Execution rule | Không build lại M01–M10; chỉ build gap đã liệt kê |

---

**END OF DOCUMENT**
