# VENHO AI STUDIO — Task Memory
**Repo:** `venho-ai-studio` · **Workspace:** THE WEST LAKE LIVING
**Cập nhật:** 2026-07-09 · **Đọc bởi:** AI Engine, Claude Code sessions

---

## 1. Mục tiêu hệ thống

Biến ảnh thực và Brand DNA thành nội dung marketing chất lượng cao — hoàn toàn trên nền tảng tri thức chuẩn hóa, không viết cảm tính, không tự publish.

Pipeline tổng quát:

```
Ảnh thực → [M01] DNA JSON → [M02] Prompt → [AI Engine ngoài tạo ảnh/video] → [M03] Validate
                           → [M05] Content prose → [M03] Validate
                           → [M06] Video storyboard → [AI Engine ngoài render video]
[M04] điều phối toàn bộ chuỗi
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
| **M06** Video Studio | DNA + character → storyboard + engine prompt | Render video |
| **M07** *(planned)* | Publishing Gateway — đăng lên các platform | Tạo content |
| **M08** *(planned)* | Analytics & Feedback Loop | Đăng bài |

### Nguyên tắc bất biến

1. **M02 dựng prompt, M05 thực thi** — không hoán đổi vai.
2. **M04 chỉ điều phối qua adapter** — không import sâu logic module con.
3. **Archive thuộc module con** — M04 không overwrite file production.
4. **Draft first** — mọi output là draft, publish thuộc M07 hoặc người dùng.
5. **0 API call trong tests** — tất cả offline/mock.
6. **Config-first** — workflow/rule khai báo YAML, không hard-code.
7. **Project-agnostic core** — Ven Hồ là project đầu tiên, không phải core.

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
```

### Integration seams đã verify (2026-07-09)
- M01→M02: DNA contract 1.1 nằm trong range M02 chấp nhận `[1.1, 2.0)` ✅
- M02→M05: `prompt_bridge` import `build_content_prompt` — signature khớp ✅
- M03→M05: `content_validator_bridge` gọi `validate_content` có degradation ✅
- M04 adapters → M01/02/03: cả 3 adapter gọi đúng public API ✅

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
├── video_studio/              ← M06 scaffold (chưa implement)
│   └── builders/              ← character, lifestyle, reel, explainer, hero
├── shared/vision/             ← VisionClient, MockVisionClient, image_loader
├── config/
│   ├── settings.yaml
│   ├── validation.yaml
│   └── projects/venho_hotel/
│       ├── subjects/          ← subject YAML + overrides.yaml
│       ├── content/           ← content_pillars, tone, platform_rules, SEO, calendar
│       ├── video/             ← camera_rules, character_rules, motion_rules...
│       └── prompt_rules.yaml
├── data/projects/venho_hotel/ ← .gitignore (output data)
│   ├── knowledge/             ← DNA files
│   ├── prompts/               ← prompt JSON per type
│   ├── content/               ← draft content per channel
│   └── validation/            ← validation reports
├── tests/                     ← 384 tests, 0 API call
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
- Video Studio (M06): cần giữ nguyên quy tắc này khi implement.

---

## 7. Quyết định thiết kế quan trọng (không thay đổi)

| Quyết định | Lý do |
|-----------|-------|
| Pass 2A tất định (code-only) | Nếu LLM quyết định cấu trúc DNA → không tái lập được |
| Forbidden ở curated overlay | Single source, không bị overwrite khi regenerate |
| M05 prose dùng temperature > 0 | Module DUY NHẤT cho phép AI sáng tạo câu chữ |
| Manual gate trong M04 | Ảnh sinh bởi Flow/GPT Image (ngoài hệ thống) — không thể tự động hóa khâu này |
| Staleness advisory (không auto-regen) | Nội dung theo ngày vẫn dùng được dù DNA nguồn cập nhật |
| Archive thuộc module con | M04 không biết format file của module khác |
