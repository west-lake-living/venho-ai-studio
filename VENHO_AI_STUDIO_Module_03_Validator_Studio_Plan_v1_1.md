VENHO AI STUDIO
MODULE 03 — VALIDATOR STUDIO — Development Plan v1.1 (QC Consolidated)
Workspace mẹ: THE WEST LAKE LIVING Repo: venho-ai-studio Module: validator_studio/ Phụ thuộc: Module 01 (DNA JSON contract v1.1) · Module 02 (Prompt contract v1.0) · shared/vision AI Engine: OpenAI + Claude Mục tiêu: Chấm điểm output AI (ảnh, prompt, face, content) so với Knowledge/DNA chuẩn hóa — bằng phương pháp TẤT ĐỊNH, có giải thích, có gợi ý sửa.


0. Kết quả QC v1.0 → v1.1
LỖI NỀN TẢNG (nghiêm trọng)

1. Hàm match→score vô định  → SỬA: kiến trúc chấm 2 lớp; AI trả trạng thái RỜI RẠC,

                              CODE quy ra số theo rubric cố định (§8)

2. Forbidden tính như 25%   → SỬA: kill-switch — vi phạm nặng → cap REJECT (§8.4)

LỖI RANH GIỚI

3. Prompt validation trùng M02 → SỬA: phân vai. M02 = cổng pass/fail lúc build;

                                 M03 = điểm chất lượng + fix suggestion (advisory) (§4.3)

4. Face validator phát minh lại → SỬA: triển khai rubric 07F (kill-switch nhị phân +

                                  weighted); DÙNG CHUNG cổng với M01 Step 13 (§4.2)

LỖ HỔNG

5. §8.2 vs §8.3 lệch danh mục → đồng bộ category ↔ weights (§8.2)

6. Thiếu mock + đọc sai prompt → thêm mock vision; đọc prompt.json (§11, §6)

7. Enum/severity/artifact mờ  → định nghĩa enum; ảnh là artifact ngoài (Flow/GPT Image) (§6)


1. Vai trò của Module 03
Module 01 biến ảnh → Knowledge/DNA. Module 02 biến Knowledge → Prompt. Module 03 trả lời:

Output này có đúng DNA, đúng intent, đủ chất lượng để đưa vào Production không?

Validator Studio KHÔNG tạo Knowledge mới, KHÔNG tạo prompt chính, KHÔNG sản xuất nội dung, KHÔNG tự sửa output. Nó chỉ đo và khuyến nghị.

Output AI + Knowledge/DNA → Validation → Score Report + Fix Suggestions

Lưu ý phạm vi: ảnh cần chấm là artifact sinh từ công cụ ngoài (Google Flow, GPT Image...). VENHO chưa có module tạo ảnh nội bộ (Visual Studio là tương lai). Module 03 nhận file ảnh do người dùng đưa vào.


2. Nguyên tắc thiết kế
2.1 Knowledge-based, không cảm tính. Validator đọc DNA + prompt + output + rules + forbidden + allowed_imperfections rồi mới chấm.

2.2 Score + giải thích. Mọi kết quả có: score, reason, evidence, fix_suggestion.

2.3 Không sửa output. Chỉ báo: lỗi gì / vì sao / sửa hướng nào / có nên regenerate. Việc sửa thuộc Module 02 / Visual / Content.

2.4 Dùng lại shared/vision (Module 01). Không viết lại vision client; dùng lại cả mock provider và error layer.

2.5 Project-agnostic. Không hard-code Ven Hồ. Rule đọc từ data/projects/<project>/knowledge/ và config/projects/<project>/.

2.6 Code quyết điểm, AI chỉ quan sát (kỷ luật kế thừa M01/M02). Đây là nguyên tắc cốt lõi, được cụ thể hóa ở §8.


3. Kiến trúc chấm điểm — HAI LỚP (trọng tâm sửa lỗi)
Đây là điểm quan trọng nhất của v1.1. Chấm điểm KHÔNG bao giờ để AI tự phán con số.

LỚP 1 — AI OBSERVE (rời rạc, freedom thấp, temperature 0)

  Với MỖI required_dna key: trả match_state ∈ {match, partial, mismatch, not_visible}

  Với MỖI forbidden rule:   trả violated ∈ {true, false} + confidence

  Với allowed_imperfection: trả present ∈ {true, false}

  → Output BẮT BUỘC là JSON enum. KHÔNG số 0–100. KHÔNG văn xuôi tự do.

LỚP 2 — CODE SCORING (tất định 100%)

  match_state → điểm theo rubric cố định:

      match = 100 · partial = 60 · mismatch = 0 · not_visible = loại khỏi mẫu

  điểm mỗi key nhân trọng số theo DNA (evidence_count/confidence của invariant)

  gộp category score → overall theo weights trong validation.yaml

LỚP 3 — KILL-SWITCH (code, ghi đè weighted)

  forbidden nặng bị violated=true → cap overall = REJECT (bất kể phần khác)

  face: rớt cổng nhận dạng nhị phân → FAIL (bất kể weighted)

Lý do: quan sát rời rạc (match/partial/mismatch) tái lập tốt hơn nhiều so với bắt AI cho "72". Cho cùng một observation JSON, điểm là tất định tuyệt đối — test được bằng mock, không tốn token.

Khử nhiễu ảnh đơn (tùy chọn, config observe_samples): quan sát N lần, lấy match_state đa số cho mỗi key.


4. Các loại Validation
4.1 Image Validation
Input: generated image (artifact ngoài) + Project/Subject DNA JSON + forbidden + allowed_imperfections + prompt.json đã dùng. Quy trình: theo kiến trúc 2 lớp (§3). Forbidden là kill-switch (§8.4). Output: Image Validation Report (DNA match, section scores, forbidden violations, issues, fix, regenerate?).
4.2 Face / Character Validation — TRIỂN KHAI RUBRIC 07F
Input: generated character image + Face DNA + project face QC rubric (07F). Rubric 07F gồm hai phần, cả hai bắt buộc:

BINARY KILL-SWITCH GATES (nhị phân): rớt bất kỳ gate nào → QC FAIL ngay,

    bất kể weighted score. Ví dụ gate: cấu trúc khuôn mặt lệch identity,

    tỉ lệ mắt sai, xuất hiện đặc điểm cấm.

WEIGHTED SCORE: chỉ tính khi đã qua toàn bộ binary gate.

Quy tắc cứng: grounding/web search TẮT; không nhận diện/so khớp người thật hay celebrity; chỉ đối chiếu với nhân vật hư cấu đã định nghĩa. Đây là CÙNG một cổng với Module 01 Step 13 — dùng chung một file rubric, không tạo cổng thứ hai. Ảnh Linh An chỉ được vào tập nguồn Face DNA (M01) nếu đã PASS cổng này.
4.3 Prompt Validation — ADVISORY, KHÔNG trùng Module 02
Phân vai rõ để tránh hai validator bất đồng:

MODULE 02 (internal validator)  = CỔNG PASS/FAIL lúc build.

    Chặn không cho lưu prompt vi phạm hợp đồng (forbidden mất, invariant thiếu,

    quá max_length). Nhị phân. Đã có sẵn.

MODULE 03 (prompt validation)   = ĐIỂM CHẤT LƯỢNG (0–100) + fix suggestion.

    Advisory, phong phú hơn: token efficiency, độ rõ, độ đặc thị, mức rủi ro loãng.

    KHÔNG lặp lại logic pass/fail của M02.

    M02 CÓ THỂ gọi scorer của M03; hai bên không tự viết trùng.

Input: prompt .json (hợp đồng M02, có sẵn required_dna/forbidden/source_knowledge) — KHÔNG parse .md. + DNA JSON. Output: Completeness/DNA-coverage/contradiction/token-efficiency/production-readiness score + fix.
4.4 Content Validation (thiết kế trước, triển khai sau)
Input: draft content + Brand DNA + prompt_rules (tone/CTA) + platform + target_language (từ M02). Output: brand_fit, tone, clarity, CTA, (SEO nếu có) + fix. Lưu ý chấm theo đúng target_language, không phạt vì viết tiếng Việt.


5. MVP Scope v0.1
LÀM:      Image Validation · Prompt Validation (advisory)

CHƯA LÀM: Content nâng cao · Video validation · Automation · Dashboard UI

Face:     làm sau MVP (cần Face DNA + rubric 07F ổn định) — Phase 3


6. Input / Output
6.1 Input
data/projects/<project>/knowledge/<subject>_DNA.json     (DNA đã merge overlay)

data/projects/<project>/prompts/**/<...>.json            (prompt contract M02)

<generated image file>                                    (artifact ngoài, người dùng đưa vào)

config/validation.yaml

config/projects/<project>/face_qc_rubric.yaml            (07F, cho face)

Enum bắt buộc: status ∈ {ok, warning, fail} · severity ∈ {low, medium, high} · match_state ∈ {match, partial, mismatch, not_visible} · recommendation ∈ {approve, revise, regenerate, reject}.
6.2 Output
data/projects/<project>/validation/reports/<id>.md + .json

data/projects/<project>/validation/logs/

data/projects/<project>/validation/validation_manifest.json

id gắn hash artifact + timestamp để truy nguyên đúng ảnh/prompt đã chấm.


7. Output Report
7.1 Markdown
# VALIDATION REPORT

## META

## OVERALL SCORE (+ verdict + kill-switch status)

## DNA MATCH SCORE

## SECTION SCORES

## FORBIDDEN VIOLATIONS

## ALLOWED IMPERFECTIONS CHECK

## ISSUES FOUND

## FIX SUGGESTIONS

## REGENERATION RECOMMENDATION

## VALIDATION NOTES
7.2 JSON (hợp đồng M03)
{

  "contract_version": "1.0",

  "module": "validator_studio",

  "project": "venho_hotel",

  "subject": "lake_view_room",

  "validation_type": "image",

  "artifact_ref": { "type": "image", "file": "test_001.png", "hash": "sha256..." },

  "source_knowledge": [

    { "file": "VENHO_LAKE_VIEW_ROOM_DNA.json", "dna_version": "1.0", "dna_contract_version": "1.1", "hash": "sha256..." }

  ],

  "prompt_ref": { "file": "..._IMAGE_PROMPT_v1.0.json", "prompt_version": "1.0" },

  "generated_at": "ISO datetime",

  "observer": { "provider": "openai", "model": "...", "samples": 1 },

  "kill_switch": { "triggered": true, "reason": "high-severity forbidden violated" },

  "overall_score": 0,

  "verdict": "reject",

  "dna_match_score": 84,

  "section_scores": [

    { "section": "window_dna", "match_state": "partial", "score": 60,

      "status": "warning", "reason": "Window appears near floor-to-ceiling glass." }

  ],

  "forbidden_violations": [

    { "rule": "no floor-to-ceiling glass wall", "source": "curated",

      "severity": "high", "violated": true }

  ],

  "allowed_imperfections_check": [

    { "item": "minor curtain wrinkles", "present": true, "penalized": false }

  ],

  "issues": [

    { "issue": "Window geometry does not match DNA.", "severity": "high",

      "suggestion": "Strengthen prompt: medium-height black aluminum window with sill." }

  ],

  "recommendation": "regenerate"

}

Ghi chú: khi kill_switch.triggered = true, overall_score bị cap về vùng reject và verdict = reject/regenerate bất kể dna_match_score.


8. Scoring System
8.1 Thang & verdict
90–100 approve · 80–89 usable(revise nhẹ) · 70–79 revise · 60–69 weak · <60 reject
8.2 Category ↔ Weights (ĐÃ ĐỒNG BỘ)
Image: dna_match, forbidden, authenticity, composition, lighting, material, technical_quality. Prompt: dna_coverage, forbidden_conflict, clarity, token_efficiency, output_specificity, production_readiness. Mỗi category trong danh sách này PHẢI có mặt trong weights (§8.3), không thừa không thiếu.
8.3 Weights mặc định (tổng = 1.00, kiểm bằng test)
image_validation_weights:

  dna_match: 0.30

  authenticity: 0.15

  composition: 0.10

  lighting: 0.10

  material: 0.10

  technical_quality: 0.05

  forbidden: 0.20          # vẫn có mặt trong weighted, NHƯNG chịu kill-switch (§8.4)

# tổng = 1.00

prompt_validation_weights:

  dna_coverage: 0.35

  forbidden_conflict: 0.25

  clarity: 0.15

  token_efficiency: 0.10

  output_specificity: 0.10

  production_readiness: 0.05

# tổng = 1.00
8.4 Kill-switch (ghi đè weighted — MỚI v1.1)
Image:  bất kỳ forbidden severity=high nào violated=true → overall cap = 40 (reject),

        verdict = regenerate, kill_switch.triggered = true.

Face:   rớt bất kỳ binary gate 07F → verdict = fail, weighted không cứu được.

Lý do:  điều cấm và nhận dạng là rule toàn vẹn, không phải biến trọng số.
8.5 Allowed imperfections — whitelist không phạt
present & nằm trong allowed set  → KHÔNG trừ điểm (đây là điều được phép).

imperfection NGOÀI allowed set   → ghi issue severity=low (cân nhắc), không kill.

KHÔNG bắt buộc phải có imperfection.


9. Folder Structure
venho-ai-studio/

├── validator_studio/

│   ├── image_validator.py

│   ├── prompt_validator.py

│   ├── face_validator.py

│   ├── content_validator.py

│   ├── scoring.py                 # Lớp 2 + kill-switch, code thuần, tất định

│   ├── observe_adapter.py         # gọi shared/vision, ép enum match_state

│   ├── report_builder.py

│   ├── validation_manifest.py

│   ├── validation_pipeline.py

│   ├── cli.py

│   ├── schemas/

│   │   ├── validation_base.py

│   │   ├── image_validation.py

│   │   ├── prompt_validation.py

│   │   └── face_validation.py

│   ├── prompts/

│   │   ├── observe_image_against_dna.md    # trả enum match_state, KHÔNG số

│   │   ├── validate_prompt_quality.md

│   │   └── observe_face_against_dna.md

│   └── renderers/

│       ├── validation_report_md.py

│       └── validation_report_json.py

│

├── shared/vision/  (dùng lại M01, gồm mock_vision)

│

├── config/

│   ├── settings.yaml

│   ├── validation.yaml

│   └── projects/<project>/face_qc_rubric.yaml   (07F)

│

└── data/projects/<project>/

    ├── knowledge/

    ├── production/images/          (artifact ngoài đưa vào)

    └── validation/{reports, logs, validation_manifest.json}


10. Config validation.yaml
validation:

  default_project: venho_hotel

  observe_samples: 1               # tăng để khử nhiễu ảnh đơn

  thresholds: { approve: 90, usable: 80, revise: 70, reject: 60 }

  rubric:

    match: 100

    partial: 60

    mismatch: 0

  kill_switch:

    forbidden_high_cap: 40

  image_validation_weights: { dna_match: 0.30, authenticity: 0.15, composition: 0.10,

    lighting: 0.10, material: 0.10, technical_quality: 0.05, forbidden: 0.20 }

  prompt_validation_weights: { dna_coverage: 0.35, forbidden_conflict: 0.25, clarity: 0.15,

    token_efficiency: 0.10, output_specificity: 0.10, production_readiness: 0.05 }

  face_validation:

    grounding: false

    rubric_file: config/projects/venho_hotel/face_qc_rubric.yaml   # 07F


11. AI Engine Use
Vision (OpenAI/Claude) = LỚP 1 observe: trả enum match_state, temperature 0, grounding off.

Claude                  = viết fix suggestion / phân tích mâu thuẫn (chữ, không phải điểm).

CODE                    = LỚP 2 scoring + kill-switch. AI KHÔNG BAO GIỜ tự chấm số.

Mock                    = observe_adapter có chế độ mock (dùng shared/vision mock)

                          → test không tốn token; cho cùng observation → cùng score.


12. Validation Workflow
Image:

Generated image → observe_adapter (Lớp 1, enum) → load DNA JSON

→ scoring.py (Lớp 2) → kill-switch (Lớp 3) → report_builder → .md + .json + manifest

Prompt (advisory):

prompt.json (M02) → load DNA JSON → chấm coverage/clarity/token/specificity

→ scoring → fix suggestion → report. KHÔNG lặp cổng pass/fail của M02.


13. CLI
venho validate                     # menu: [A] Image [B] Prompt [C] Face [D] Content (MVP: A,B)

venho validate image  --project venho_hotel --subject lake_view_room --image <path> [--prompt <prompt.json>]

venho validate prompt --project venho_hotel --subject lake_view_room --prompt-file <prompt.json>

venho validate face   --project venho_hotel --subject linh_an --image <path>

--samples N ghi đè observe_samples. Có run report cuối mỗi lần chạy.


14. Kế hoạch phát triển theo GIAI ĐOẠN
GIAI ĐOẠN 0 — Nền tảng
Step 0 — Chuẩn bị module. Cây validator_studio/, config/validation.yaml, data/.../validation/. DoD: import không lỗi; config load được; nối shared/vision (gồm mock); enum (§6.1) khai báo trong schema.

Step 1 — Validation Schemas. schemas/{validation_base, image_validation, prompt_validation}.py. DoD: report validate được; JSON round-trip; có contract_version, verdict, kill_switch, match_state enum.

Step 2 — Report Builder. report_builder.py, renderers/*. DoD: từ object mẫu sinh .md + .json; section §7.1 cố định; kill_switch hiển thị ở OVERALL.
GIAI ĐOẠN 1 — Chấm điểm tất định (backbone)
Step 3 — Scoring Engine (Lớp 2 + kill-switch). scoring.py. DoD: match/partial/mismatch → điểm theo rubric; áp weights; tổng weights=1.00 (test); cùng observation JSON → cùng score (tất định); forbidden high → cap reject; verdict đúng thang.

Step 4 — Observe Adapter (Lớp 1). observe_adapter.py, prompts/observe_image_against_dna.md. DoD: gọi shared/vision trả enum match_state (không số); temperature 0; mock mode chạy không mạng; observe_samples>1 lấy đa số.
GIAI ĐOẠN 2 — MVP (Prompt + Image)
Step 5 — Prompt Validator (advisory). prompt_validator.py, prompts/validate_prompt_quality.md. DoD: đọc prompt .json (M02); chấm coverage/clarity/token/specificity + fix; KHÔNG lặp cổng pass/fail M02; report .md+.json.

Step 6 — Image Validator. image_validator.py. DoD: ảnh → observe_adapter → DNA compare → scoring → kill-switch; DNA mismatch phát hiện; forbidden violation kích kill-switch; report .md+.json.

Step 7 — CLI + Manifest. cli.py, validation_manifest.py, validation_pipeline.py. DoD: venho validate menu; image & prompt chạy; direct command chạy; manifest ghi verdict mới nhất theo artifact; run report.

Step 8 — MVP nghiệm thu. ◀ MỐC GIÁ TRỊ ĐẦU TIÊN Test: 1 prompt tốt / 1 prompt cố ý sai / 1 ảnh đúng / 1 ảnh sai (có điều cấm). DoD: bắt đúng lỗi; ảnh có forbidden → kill-switch → reject; report dễ đọc; suggestion hữu ích; không gọi lại DNA generation. ➜ Dừng, review.
GIAI ĐOẠN 3 — Face (rubric 07F)
Step 9 — Face Validator. face_validator.py, schemas/face_validation.py, prompts/observe_face_against_dna.md. DoD: load rubric 07F; binary kill-switch gate + weighted; rớt gate → FAIL bất kể điểm; grounding off; không nhận diện người thật; là CÙNG cổng với M01 Step 13.
GIAI ĐOẠN 4 — Content & Tích hợp
Step 10 — Content Validator. content_validator.py. DoD: chấm brand_fit/tone/clarity/CTA theo target_language (không phạt tiếng Việt); report.

Step 11 — Integration với Module 02. Feedback loop. DoD: prompt.json của M02 validate trực tiếp; fix suggestion của M03 quay lại M02 để regenerate; M02 gọi được scorer M03 (không viết trùng logic).


15. MVP Definition of Done
- Prompt & Image validation chạy được, đọc prompt.json/DNA.json đúng contract.

- Chấm điểm HAI LỚP: AI observe enum → code scoring tất định.

- Kill-switch forbidden hoạt động (violation nặng → reject).

- Report .md + .json; mỗi score có reason; mỗi issue có suggestion.

- CLI đủ; manifest theo dõi verdict; mock để test không tốn token.

- Dùng lại shared/vision; project-agnostic; KHÔNG sửa Knowledge/DNA.


16. Rủi ro và cách phòng tránh
1. Validator cảm tính        → AI chỉ observe enum; code chấm; schema cố định

2. Điểm số ảo (không tái lập)  → chấm 2 lớp; cùng observation → cùng score; mock test

3. Forbidden bị "trung bình hóa" → kill-switch, không phải trọng số (§8.4)

4. Trùng validator với M02    → phân vai: M02 cổng pass/fail, M03 điểm advisory

5. Face → nhận diện người thật → chỉ nhân vật hư cấu; grounding off; rubric 07F

6. Face có 2 cổng khác nhau   → dùng CHUNG rubric 07F với M01 Step 13

7. Hard-code Ven Hồ           → đọc project/subject từ CLI + config

8. Validator tự sửa output    → chỉ báo cáo; sửa/regenerate thuộc module khác

9. Test tốn token             → mock vision; xác định tính tất định ở lớp code


17. Thứ tự ưu tiên thực tế
Nền tảng:  Schemas → Report Builder

Backbone:  Scoring Engine (2 lớp + kill-switch) → Observe Adapter

MVP:       Prompt Validator (advisory) → Image Validator → CLI/Manifest → nghiệm thu

Mở rộng:   Face (07F) → Content → Integration M02

Scoring engine làm trước cả validator cụ thể — vì nó là xương sống tất định; validator chỉ cấp observation cho nó.


18. Kết luận
Điểm cần giữ tuyệt đối:

AI CHỈ quan sát (trạng thái rời rạc); CODE quyết điểm (tất định).

Forbidden và nhận dạng là KILL-SWITCH, không phải trọng số.

Module 02 sở hữu cổng pass/fail của prompt; Module 03 cho điểm chất lượng + gợi ý.

Face validation = rubric 07F, dùng chung một cổng với Module 01.

Validator chỉ đo và khuyến nghị — không tạo, không sửa, không publish.

Project-agnostic; Ven Hồ chỉ là project đầu tiên.

END OF DOCUMENT v1.1 (QC Consolidated)

