# VENHO AI STUDIO — MOTHER PLAN IMPLEMENTATION ROADMAP v1.5

**Ngày khóa hiện trạng:** 2026-07-16  
**Thay thế baseline điều hành:** `VENHO_AI_STUDIO_MOTHER_PLAN_ROADMAP_v1_4_RECONCILED_2026-07-15.md`  
**Phạm vi:** `venho-ai-studio` + `venho-os`  
**Mục tiêu:** biến workflow AI Image Studio đang chạy thật thành pipeline ổn định, truy vết được, mở rộng wardrobe an toàn và có QC đáng tin cậy.

---

# 1. KẾT LUẬN ĐIỀU HÀNH

Sau chuỗi triển khai và test thực tế ngày 2026-07-15–16, roadmap cần đổi thứ tự ưu tiên so với v1.4:

1. Không build lại M01–M10. M01–M09 tiếp tục là core engine; M10 tiếp tục thuộc `venho-os` Next.js.
2. Bottleneck hiện tại không phải thiếu thêm module, mà là **độ tin cậy của Image Studio đang dùng thật**: schema Mode C, face identity, outfit traceability, location authenticity và job lifecycle.
3. Mode C hiện mới là UX wrapper gọi Mode B engine. Run Nike Pink đã fallback sang `universal_schema`, vì vậy artifact này chưa phải Wardrobe DNA hợp lệ.
4. Face generation đã cải thiện từ reject lên **80/revise**, nhưng chưa đạt cổng duyệt 90 và Face Validator chưa đối chiếu trực tiếp với bộ ảnh master.
5. West Lake Validator đạt 100 nhưng mới kiểm tra Hồ Tây tổng quát; chưa kiểm tra đầy đủ hình học riêng của đường Nguyễn Đình Thi.
6. Phải khóa sạch Git, dữ liệu và contract trước khi mở rộng C0–C7 hoặc Agent automation.
7. Thực thi theo thin slice: hoàn thiện hai outfit đang có trước; chỉ xây compatibility matrix cấp item khi có nhu cầu thật và đủ dữ liệu.

> **Thứ tự mới:** Baseline & Security → Mode C Data Integrity → Image/Validator Quality → Durable Jobs → Wardrobe Contracts → M02–M06 Integration → M04/M09/Living Lab.

---

# 2. BASELINE ĐÃ XÁC MINH NGÀY 2026-07-16

## 2.1 Tests và runtime

| Repo | Acceptance hiện tại | Kết quả |
|---|---|---:|
| `venho-ai-studio` | `python3 -m pytest -q` | **424/424 pass**, offline |
| `venho-ai-studio` M03 | Validator tests | **27/27 pass** |
| `venho-os` | `npm test -- --run` | **54/54 pass**, 9 files |
| `venho-os` Studio subset | Studio unit tests | **16/16 pass**, 3 files |
| `venho-os` | ESLint + TypeScript + production build | **Pass** |

Baseline 423 tests và M03 26 tests trong v1.4 đã lỗi thời do thêm regression test cho face-score normalization.

## 2.2 Git baseline

| Repo | Trạng thái |
|---|---|
| `venho-os` | Commit `84426f7` đã push; còn 5 file Image Studio chưa commit |
| `venho-ai-studio` | Các thay đổi từ 2026-07-15 chưa được commit; worktree còn nhiều thay đổi không cùng scope |

Không được gom toàn bộ dirty worktree AI Studio vào một commit. Mỗi nhóm thay đổi phải được audit và commit độc lập.

## 2.3 Live generation evidence mới nhất

Run: `run-20260716150633190/variant-001`

| Gate | Kết quả |
|---|---:|
| Nguyễn Đình Thi / West Lake image DNA | **100 — approve** |
| Linh An Face | **80 — revise** |
| Overall manifest status | **needs_review** |
| Reference mode | `face-reference` |
| Input fidelity | `automatic-high` |

Kết luận: pipeline đã chạy lại thành công sau lỗi API, nhưng chưa đủ điều kiện công bố `APPROVED` vì Face còn `revise`.

---

# 3. NHỮNG VIỆC ĐÃ LÀM TRONG CHUỖI CHAT

Quy ước trạng thái:

- **DONE-COMMITTED:** đã nằm trong commit `venho-os`.
- **DONE-UNCOMMITTED:** code và tests đã pass nhưng chưa commit.
- **PARTIAL:** dùng được trong phạm vi hiện tại, chưa đạt contract đích.

| ID | Hạng mục đã triển khai | Trạng thái | Bằng chứng chính |
|---|---|---|---|
| CHAT-01 | Đặt Mode A/B trong Workbench; Mode C Linh An trong Knowledge | DONE-COMMITTED | `WorkbenchSection.tsx`, `KnowledgeSection.tsx` |
| CHAT-02 | Upload ảnh cho Mode A, B và C | DONE-COMMITTED | `ImageUploadField.tsx`, `upload-images/route.ts` |
| CHAT-03 | Chuẩn hóa HEIC/HEIF/AVIF sang PNG ở server | DONE-COMMITTED | `image-normalize.ts` |
| CHAT-04 | Sửa đường dẫn VenHo OS → AI Studio và lỗi `ENOENT` | DONE-COMMITTED | `src/lib/studio/paths.ts` |
| CHAT-05 | Loại prompt xác nhận tương tác làm timeout 300s; thêm checkbox xác nhận 1 folder = 1 subject | DONE-COMMITTED | `observe/route.ts`, Workbench/Knowledge UI |
| CHAT-06 | Mode C có trạng thái đang chạy, thành công, thất bại và kiểm tra artifact | DONE-COMMITTED / PARTIAL | `KnowledgeSection.tsx`, `linh-an-wardrobe-status/route.ts` |
| CHAT-07 | Topic được đưa vào generation prompt; Linh An bắt buộc là người thực hiện hành động | DONE-COMMITTED | `prompt-builder.ts` |
| CHAT-08 | Cycling khóa người–xe: tay trên ghi đông, người trên yên, chân ở bàn đạp | DONE-COMMITTED | `image-policy.ts`, `prompt-builder.ts` |
| CHAT-09 | Cấm empty scene và unattended action prop | DONE-COMMITTED | Prompt negative/action lock |
| CHAT-10 | Sport action tự ép đúng activewear, loại váy/túi/cardigan/casual outfit | DONE-COMMITTED | `constants.ts`, `generate-image/route.ts` |
| CHAT-11 | Cho user chọn outfit family + variant; hiện có Mint Green và Nike Pink Running | DONE-COMMITTED / PARTIAL | `OUTFIT_VARIANTS`, Creative Studio UI |
| CHAT-12 | Tăng độ thật Nguyễn Đình Thi: vỉa hè hẹp, lan can trắng, cây, xe máy, nhà thấp tầng, nước xanh xám | DONE-COMMITTED | `ENV_BLOCKS`, negative block |
| CHAT-13 | Mỗi generation có run/variant riêng, manifest, reference mode, QC, history, progress, cancel và retry | DONE-COMMITTED | generation API + Creative Studio |
| CHAT-14 | Đọc credential từ env và trả lỗi thân thiện khi thiếu key | DONE-COMMITTED | `generate-image/route.ts`, `generate_image.py` |
| CHAT-15 | Chạy Image Validator khi scenario có DNA và Face Validator khi có Linh An | DONE-COMMITTED | `validate_generated.py`, manifest validation |
| CHAT-16 | Khóa mạnh identity cho ảnh chạy nhìn thẳng, mồ hôi tự nhiên, biểu cảm rạng rỡ | DONE-UNCOMMITTED | `prompt-builder.ts` + tests |
| CHAT-17 | Xử lý đúng `gpt-image-2`: reference luôn high fidelity tự động; không gửi tham số API bị cấm | DONE-UNCOMMITTED | `generate_image.py`; manifest `automatic-high` |
| CHAT-18 | Sửa Face Validator về thang 0–100 và regression test | DONE-UNCOMMITTED | `observe_face_against_dna.md`, `scoring.py`, tests |

Ghi chú: giao diện gọi là “Mode C complete”, nhưng engine hiện vẫn chạy Mode B để build DNA. Đây là mô tả UX, chưa phải bằng chứng full Mode C C0–C7.

---

# 4. PHÁT HIỆN QUAN TRỌNG SAU AUDIT

## 4.1 Mode C đang có rủi ro làm bẩn Knowledge

Run `Nike_pink_running` đã tạo:

- `mode: B`;
- `schema_id: universal`;
- các thuộc tính kiểu `subject_type`, `lighting_condition`, `composition`;
- forbidden gồm `Facial features`, `Facial expressions`, `outdoor setting`.

Các forbidden này xung đột trực tiếp với use case Linh An chạy ngoài trời. Nguyên nhân: `subject_resolver` fallback im lặng sang `config/universal_schema.yaml` khi tên subject user nhập không trùng tên schema canonical.

**Quyết định:** artifact `LINH_AN_NIKE_PINK_RUNNING_DNA.*` hiện tại phải được đánh dấu `quarantined/legacy`, không được Creative Studio tiêu thụ như Wardrobe DNA approved.

## 4.2 Wardrobe selector chưa thực sự đọc Wardrobe DNA

Hai outfit Mint Green và Nike Pink hiện nằm trong registry TypeScript hardcode. Thêm outfit mới vẫn phải sửa `constants.ts`; pipeline chưa đọc Wardrobe Index từ AI Studio.

## 4.3 Face Validator chưa đủ chặt

Rubric yêu cầu ba gate:

1. `identity_structure`;
2. `eye_ratio`;
3. `forbidden_traits`.

Report live gần nhất chỉ trả một gate nhưng vẫn được tính điểm 80. Validator hiện so artifact với text DNA, chưa so trực tiếp với master/multi-view face reference. Identity, hairstyle, pose và capture style cũng chưa được tách rõ.

## 4.4 West Lake Validator còn quá tổng quát

DNA hiện chủ yếu kiểm tra nước, trời, skyline, ánh sáng, cây và presence của path/railing. Nó chưa khóa:

- hình học lan can Nguyễn Đình Thi;
- bề rộng và chất liệu vỉa hè;
- quan hệ đường–vỉa hè–lan can–mặt hồ;
- nhà phố thấp tầng và traffic địa phương;
- reference ảnh địa điểm hiện hành.

Overlay cũ còn ghi `green lamp posts` và `green metal railing`, mâu thuẫn với hiện trạng prompt 2026 dùng lan can trắng và không có cột đèn.

## 4.5 Job lifecycle vẫn đồng bộ và dễ timeout

Mode A/B/C và generation vẫn dựa vào process dài + timeout. Dashboard chưa có durable job record để resume/reconcile sau refresh, crash hoặc mất kết nối.

## 4.6 Git, docs và test artifacts chưa sạch

- `task_status.md` và `task_memory.md` còn mâu thuẫn 423/424, mock/real M05 và Streamlit/Next.js.
- Unit test generation đang tạo artifact giả trong `photos-ai/2026/test`, có thể lọt vào history như run thật.
- Một số API mới chưa có test đầy đủ: upload, normalize thật, history, wardrobe status, cancellation và concurrency.

## 4.7 Security

Một API key đã từng được gửi trực tiếp trong chat. Không được ghi key này vào roadmap, source, log hoặc commit. Key phải được revoke/rotate trước production run tiếp theo.

---

# 5. KIẾN TRÚC ĐÍCH TỐI ƯU

```text
VenHo OS UI
  -> AiStudioPort / Job Controller
     -> Knowledge Engine (Mode A/B/C)
     -> Prompt + Image Generator
     -> Validator Studio
  -> Immutable Artifacts + Versioned Manifests
  -> Dashboard Result / Review / Retry
```

## 5.1 Repo ownership

| Repo | Ownership khóa |
|---|---|
| `venho-ai-studio` | Knowledge contracts, Wardrobe Index, prompt/validator/workflow engines M01–M09 |
| `venho-os` | Next.js UI, BFF/API boundary, job UX, generation runner, artifact presentation |

## 5.2 Contracts cần tạo hoặc nâng version

| Contract | Target | Nội dung bắt buộc |
|---|---:|---|
| Wardrobe Item | 1.0 | `item_id`, garment, colors, material, branding, refs, forbidden |
| Wardrobe Outfit | 1.0 | `outfit_id`, family, variant, item refs, prompt snippet, context fit |
| Wardrobe Index | 1.0 | approved variants, default, availability, version, status |
| Generation Manifest | 1.1 | action, outfit ID, scenario profile, refs, model, fidelity mode, prompt hash, QC contracts |
| Validator Observation | 1.1 | exact gate set, exact score keys, explicit scale 0–100 |
| AiStudio Job | 1.0 | status, progress, artifact refs, error, retry, cancel, timestamps |

## 5.3 Status contract

```text
queued -> running -> validating -> approved
                              -> needs_review
                              -> unvalidated
         -> failed
         -> cancelled
```

`approved` chỉ được gán khi tất cả validator bắt buộc đều approve. Validator thiếu, lỗi hoặc trả schema sai phải là `unvalidated`, không được suy đoán pass.

---

# 6. ROADMAP TRIỂN KHAI TỐI ƯU

## PHASE 0 — BASELINE, SECURITY & GIT FREEZE

**Priority:** P0  
**Mục tiêu:** tạo điểm xuất phát sạch trước mọi feature mới.

Deliverables:

1. Revoke/rotate API key đã lộ; chạy secret scan hai repo.
2. Commit/push riêng 5 file Image Studio đang treo trong `venho-os`.
3. Commit riêng Face Validator fix trong `venho-ai-studio`; không kéo theo các xóa/sửa không cùng scope.
4. Đưa roadmap v1.5 vào commit tài liệu riêng.
5. Đồng bộ `task_status.md`, `task_memory.md`, changelog với baseline 424/54.
6. Loại run test khỏi production history; unit tests dùng temp directory.
7. Ghi lại build warning Turbopack thành known issue, không để warning che failure mới.

**Exit Gate:** hai repo có commit rõ scope; key cũ bị revoke; tests 424/54 pass; không có test artifact trong production history.

## PHASE 1 — MODE C DATA INTEGRITY

**Priority:** P0  
**Mục tiêu:** không cho Mode C sinh hoặc publish DNA sai schema.

Deliverables:

1. Tạo `ModeCRequest` tách ba khái niệm:
   - `display_label`: tên người dùng nhìn thấy;
   - `outfit_id`: ID variant ổn định;
   - `schema_subject`: schema canonical.
2. Khóa mapping đầu tiên:
   - family: `sport_active`;
   - schema subject: `outfit_e_sport`;
   - variants: `mint_green`, `nike_pink_running`.
3. Mode C phải hard-fail nếu `schema_source == config/universal_schema.yaml`.
4. Quarantine/migrate `LINH_AN_NIKE_PINK_RUNNING_DNA.*` hiện tại.
5. Dedupe hai folder upload `wardrobe/nike_pink_running` và `wardrobe/sport_active` bằng manifest, không xóa dữ liệu gốc trước audit.
6. Mode C success phải xác minh artifact của **chính run hiện tại**, không dựa vào file cũ cùng tên.
7. Upload phải atomic, không âm thầm ghi đè file trùng tên.
8. Sửa hoặc bỏ field Mode A `outputDir` nếu API không sử dụng.

**Tests bắt buộc:** canonical routing, unknown variant, universal fallback rejection, stale artifact rejection, duplicate upload, run provenance.

**Exit Gate:** không có Mode C run nào fallback `universal`; Nike Pink tạo đúng 22-key wardrobe schema và không chứa forbidden xung đột với use case.

## PHASE 2 — IMAGE IDENTITY, OUTFIT & LOCATION QC

**Priority:** P1  
**Mục tiêu:** QC phản ánh đúng điều người dùng nhìn thấy, không chỉ đúng schema hình thức.

### 2A. Face identity

1. Enforce đúng ba gate và đúng năm score keys của rubric 07F.
2. Thiếu gate/key, sai range hoặc sai contract version → `UNVALIDATED`.
3. Nâng VisionClient để so candidate với Master Face và bộ multi-view approved.
4. Tách immutable identity khỏi pose, hairstyle, expression, camera angle và sweat.
5. Thay normalization heuristic 0–1 bằng migration có contract version; sau migration reject payload sai scale.
6. Lưu evidence/reason theo từng gate và score.

### 2B. Action/reference policy

| Action | Policy tạm khóa |
|---|---|
| Static portrait/standing/leaning | Face reference ON |
| Running/jogging nhìn rõ mặt | Face reference ON, `automatic-high` |
| Cycling/jumping/swimming/dancing | Standing reference OFF cho tới khi có action-compatible refs |
| User override | Chỉ cho phép khi UI hiển thị conflict warning và manifest ghi lý do |

Policy này thay phần mô tả cũ “mọi dynamic action đều tắt reference”.

### 2C. Outfit QC

1. Validator đọc `outfit_id` từ manifest và Wardrobe Outfit 1.0.
2. Kiểm top, bottom, color, footwear, signature details và forbidden conflicts.
3. User selection luôn thắng default; AI auto-selection mặc định OFF.
4. Manifest ghi `requested_outfit_id`, `effective_outfit_id`, selection reason.

### 2D. Nguyễn Đình Thi location profile

1. Tạo scenario profile `nguyen_dinh_thi_street_2026` tách khỏi `westlake_general`.
2. Curate trusted environment references hiện hành.
3. Validate railing geometry, sidewalk, road, local frontage, lake adjacency và skyline.
4. Gỡ/xử lý xung đột `green railing/lamp posts` trong overlay cũ.

### 2E. Generation Manifest 1.1

Thêm:

- `prompt_hash` và `user_prompt`;
- `outfit_id` + Wardrobe DNA version;
- `scenario_profile_id` + environment reference hash;
- face reference set/version;
- `input_fidelity: automatic-high` cho `gpt-image-2`;
- validator contract/version;
- latency và retry count;
- partial validation errors.

**Exit Gate:** hai run liên tiếp cho mỗi test case đạt actor/action pass, outfit ≥90, location ≥90 và face ≥90; không gate nào bị thiếu.

## PHASE 3 — DURABLE JOBS & DASHBOARD UX

**Priority:** P1  
**Mục tiêu:** không để request dài phụ thuộc vào một kết nối HTTP hoặc timeout cứng.

Deliverables:

1. `POST /studio/jobs` trả `job_id` ngay.
2. File-backed job store trước; chỉ nâng DB/queue khi load thực tế yêu cầu.
3. API status, SSE events, cancel và retry theo job.
4. Tách trạng thái `generating` và `validating`.
5. Refresh dashboard vẫn tiếp tục theo dõi được job.
6. Timeout tạo failure record có thể retry; không mất artifact đã tạo.
7. History đọc index thay vì scan đệ quy toàn bộ `photos-ai` mỗi request.
8. UI hiển thị lỗi thân thiện nhưng giữ technical error trong detail/audit.

**Exit Gate:** restart UI hoặc mất kết nối không làm mất job; cancel/retry có audit; render page không gọi provider.

## PHASE 4 — FORMAL WARDROBE C0–C7, THIN SLICE FIRST

**Priority:** P2  
**Mục tiêu:** chuyển hai outfit đang dùng từ registry hardcode sang Wardrobe Index thật.

### Thin slice bắt buộc

1. Outfit-level contract trước; item-level chỉ tách khi có dữ liệu đủ.
2. Import Mint Green và Nike Pink vào Wardrobe Outfit 1.0.
3. Tạo Wardrobe Index 1.0 với default explicit.
4. Creative Studio đọc index động; thêm outfit không cần sửa TypeScript.
5. Mode C UI cho thấy status: draft, needs_review, approved, quarantined.
6. AI auto-selection chỉ mở bằng opt-in và phải ghi selection reason.

### Mở rộng sau thin slice

| Step | Deliverable |
|---|---|
| C0 | Classify item / outfit / mixed |
| C1 | Item observation schema |
| C2 | Dedupe + identity match |
| C3 | Item DNA 1.0 |
| C4 | Outfit extraction 1.0 |
| C5 | Compatibility + forbidden pairings |
| C6 | Wardrobe Index + manifest |
| C7 | Compact Wardrobe Context |

Không xây compatibility matrix phức tạp trước khi có ít nhất 5 outfit approved hoặc một workflow thật cần phối item tự động.

**Exit Gate:** UI tự thấy outfit mới từ index; hai outfit hiện tại trace được từ source images → DNA → prompt → manifest → validation.

## PHASE 5 — INTEGRATE M02/M03/M05/M06

**Priority:** P3

1. M02 Prompt 1.1 đọc Character DNA + Outfit Capsule + Scenario Profile.
2. M03 đọc contract IDs thay vì mô tả rời rạc.
3. M05 dùng outfit context khi nội dung thực sự cần; không tự chọn outfit khi request không cho phép.
4. M06 Video 1.1 khóa `outfit_id`, item refs và continuity xuyên shot.
5. M05 real Claude adapter có unit test bằng fake client; production adapter không chạy trong pytest.
6. Backward compatibility cho package 1.0.

**Exit Gate:** một `outfit_id` trace xuyên M01 → M02 → M05/M06 → M03; tests vẫn 0 paid API call.

## PHASE 6 — M04/M09, AISTUDIOPORT & LIVING LAB

**Priority:** P4

1. M04 thêm `wardrobe_ingest`: build → validate → human review → index update.
2. Validation fail chặn index update.
3. M09 hard-stop khi thiếu knowledge; không dispatch request tiếp theo.
4. AiStudioPort chuẩn hóa các coarse capabilities trên Job Contract 1.0.
5. Approval, execute và publish giữ là ba transition riêng.
6. Living Lab đo: số output dùng thật, tỷ lệ approve lần đầu, retry, thời gian tiết kiệm và cost/run.

**Exit Gate:** workflow chạy hàng tuần, output được dùng thật, QC/audit đầy đủ và có quyết định Continue/Simplify/Pivot/Kill.

---

# 7. BACKLOG ƯU TIÊN ĐỂ BẮT ĐẦU TRIỂN KHAI

| Order | ID | Repo | Hạng mục | Gate |
|---:|---|---|---|---|
| 1 | SEC-01 | cả hai | Rotate key + secret scan | key cũ revoked, scan sạch |
| 2 | GIT-01 | `venho-os` | Commit 5 file Image Studio đang treo | 54 tests + build pass |
| 3 | GIT-02 | `venho-ai-studio` | Isolate Face Validator commit | 424 tests pass |
| 4 | DATA-01 | AI Studio | Quarantine Nike Pink universal DNA | không consumer nào đọc artifact cũ |
| 5 | MODEC-01 | AI Studio | Canonical Mode C request/routing | universal fallback hard-fail |
| 6 | MODEC-02 | OS + Studio | Run-scoped artifact verification | file cũ không tạo false success |
| 7 | VAL-01 | AI Studio | Exact Face gate/key enforcement | thiếu gate → unvalidated |
| 8 | VAL-02 | AI Studio | Reference-backed Face QC | master/multi-view evidence |
| 9 | LOC-01 | cả hai | Nguyễn Đình Thi profile + refs | scenario validator ≥90 |
| 10 | MAN-01 | OS | Generation Manifest 1.1 | trace đủ face/outfit/location |
| 11 | OUTFIT-01 | cả hai | Wardrobe Outfit/Index thin slice | selector không hardcode |
| 12 | JOB-01 | OS | Durable file-backed job store | refresh/retry/cancel an toàn |
| 13 | QA-01 | cả hai | Controlled live evaluation matrix | 2 consecutive approved runs/case |
| 14 | DOC-01 | cả hai | Đồng bộ status/memory/changelog | không còn baseline mâu thuẫn |

Không bắt đầu Phase 5/6 khi DATA-01, MODEC-01 và VAL-01 chưa qua gate.

---

# 8. QUALITY EVALUATION MATRIX

## 8.1 Controlled live cases

| Case | Action | Outfit | Scenario | Face ref |
|---|---|---|---|---|
| E1 | Running front-facing | Mint Green | Nguyễn Đình Thi | ON |
| E2 | Running 3/4 angle | Nike Pink | Nguyễn Đình Thi | ON |
| E3 | Cycling | Mint Green | Nguyễn Đình Thi | OFF |
| E4 | Cycling | Nike Pink | Nguyễn Đình Thi | OFF |
| E5 | Static portrait | Mint Green | West Lake | ON |
| E6 | Static portrait | Nike Pink | West Lake | ON |

## 8.2 Acceptance

| Criterion | Gate |
|---|---:|
| Linh An là actor thật, đúng action geometry | Pass/fail bắt buộc |
| Face identity | ≥90 approve; 80–89 revise; <80 reject |
| Outfit match | ≥90 |
| Scenario/location match | ≥90 |
| Technical quality | ≥85 |
| Missing validator/gate | UNVALIDATED |
| Two-run stability | cả hai run đạt gate |

Mỗi release chỉ chạy controlled matrix sau khi offline tests pass. Không chạy paid generation trong unit/integration tests.

---

# 9. QUYẾT ĐỊNH ĐÃ KHÓA CHO TRIỂN KHAI

| ID | Quyết định |
|---|---|
| D-01 | Nike Pink là variant `sport_active/nike_pink_running`, không phải schema subject tự do |
| D-02 | Mode C không bao giờ được fallback sang universal schema |
| D-03 | User-selected outfit luôn thắng default; AI auto-select mặc định OFF |
| D-04 | Running giữ face reference; action có conflict như cycling tắt standing reference |
| D-05 | `gpt-image-2` dùng high fidelity tự động; không gửi `input_fidelity` parameter |
| D-06 | Job store dùng file-backed index trước để tiết kiệm; chưa cần queue/DB ngoài |
| D-07 | Validator chỉ approve khi đủ contract; trực giác hình ảnh không thay validator verdict |
| D-08 | Nguyễn Đình Thi là scenario profile riêng, không chỉ là West Lake general |

Tham chiếu kỹ thuật D-05: [OpenAI Image Generation Guide — Image input fidelity](https://developers.openai.com/api/docs/guides/image-generation#image-input-fidelity).

---

# 10. DEFINITION OF DONE v1.5

Roadmap v1.5 chỉ hoàn thành khi:

1. Hai repo có baseline sạch, commit rõ scope và không lộ secrets.
2. Mode C không fallback universal; artifact cũ sai schema đã quarantine/migrate.
3. Wardrobe Index động thay registry outfit hardcode cho hai variant hiện tại.
4. Manifest truy vết đầy đủ user input, action, outfit, face refs, scenario refs và validators.
5. Face Validator bắt buộc đủ gate và đối chiếu reference approved.
6. Nguyễn Đình Thi có location profile/reference-backed QC riêng.
7. Dashboard dùng durable jobs; refresh/cancel/retry không mất trạng thái.
8. Controlled matrix đạt hai run liên tiếp cho mỗi case trước khi gán production-ready.
9. Full offline suites pass và không gọi paid API.
10. M04/M09 chỉ mở automation sau khi data integrity và validator gates ổn định.

---

# 11. CHANGELOG v1.4 → v1.5

| Thay đổi | v1.4 | v1.5 |
|---|---|---|
| AI Studio baseline | 423 tests | 424 tests |
| VenHo OS baseline | 37 tests | 54 tests |
| Image workflow | Có generation/manifest cơ bản | Đã có upload, history, QC, actor/outfit/location locks |
| Mode C | Scaffold/partial | Xác định rõ wrapper Mode B và lỗi universal fallback |
| Wardrobe strategy | Build full C0–C7 trước | Data integrity + outfit thin slice trước |
| Face QC | Text DNA + rubric | Bắt buộc reference-backed và exact gates |
| West Lake QC | Generic subject | Thêm Nguyễn Đình Thi scenario profile riêng |
| AiStudioPort | Phase muộn | Job contract được kéo lên trước integration rộng |
| Security | Chưa ghi | Rotate key và secret scan là P0 |
| Production gate | Validator chung | Controlled matrix + two-run stability |

---

**END OF DOCUMENT**
