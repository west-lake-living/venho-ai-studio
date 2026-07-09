VENHO AI STUDIO
MODULE 02 — PROMPT STUDIO — Development Plan v1.1 (QC Consolidated)
Workspace mẹ: THE WEST LAKE LIVING Repo: venho-ai-studio Module: Module 02 — Prompt Studio Phụ thuộc: Module 01 — Knowledge/DNA Studio (DNA JSON contract v1.1) AI Engine: OpenAI + Claude Mục tiêu: Biến DNA .json (đã merge overlay) thành prompt chất lượng cao, nhất quán, tái sinh được, có version — cho image / video / content / SEO production.


0. Kết quả QC v1.0 → v1.1
Bản v1.1 sửa các lỗi phát hiện khi rà v1.0 và đối chiếu với Module 01 v2.4:

LỖI LOGIC (nghiêm trọng)

1. Pipeline sai thứ tự  → Optimize phải chạy TRƯỚC lần validate cuối (§8)

2. Validator hời hợt    → thêm kiểm NỘI DUNG: invariant xuất hiện, forbidden còn nguyên (§12)

3. required_dna vô định  → định nghĩa rõ, làm cơ sở cho validator (§7.3)

LỖI RANH GIỚI VỚI MODULE 01

4. Đọc trùng overlay    → CHỈ đọc DNA JSON đã merge; KHÔNG đọc overrides.yaml (§3, §2.2)

5. Chưa xử lý shape v1.1 → reader map {rule,source},{value,source}, variable→allowed_variations (§3.4)

LỖ HỔNG

6. Ngôn ngữ/negative áp chung → tách theo loại: image/video có negative;

                                content/SEO có target_language + tone (§5, §10)

7. Video đa DNA chưa xử lý → builder ghép nhiều DNA, có luật xung đột (§5.2, Phase 3)

8. prompt_id trùng        → id = subject + type + brief_slug (§14)

9. Thiếu kỷ luật M01      → thêm settings.yaml, mock provider, DoD tất định,

                            check tương thích contract_version (§9, §17)


1. Vai trò của Module 02
Module 01 trả lời: "Vật thể / địa điểm / nhân vật LÀ GÌ?" Module 02 trả lời: "Từ Knowledge đó, viết prompt thế nào để AI tạo đúng kết quả?"

Prompt Studio không phải nơi người dùng viết prompt tay. Nó là hệ thống tự sinh prompt từ Knowledge đã chuẩn hóa.

Knowledge / DNA → Prompt Studio → Prompt → AI Production


2. Nguyên tắc cốt lõi
2.1 Knowledge First. Prompt không phải nguồn sự thật, chỉ là sản phẩm sinh từ Knowledge. Knowledge đổi → prompt tái sinh.

2.2 Prompt không chứa tri thức gốc. Prompt chỉ lấy thông tin từ:

- DNA .json (ĐÃ merge overlay ở Module 01 — nguồn DUY NHẤT của tri thức)

- Prompt template

- Project prompt rules

- User task brief

KHÔNG đọc overrides.yaml (Module 01 đã merge vào DNA JSON). KHÔNG bịa chi tiết. KHÔNG tự suy diễn thương hiệu. KHÔNG mở rộng ngoài Knowledge.

2.3 Prompt có cấu trúc. Mọi prompt sinh theo template cố định, gồm: objective, subject, context, required_dna, allowed_variations, allowed_imperfections, forbidden, output_format, quality_notes.

2.4 Prompt version được. Lưu kèm: prompt_version, source_knowledge_version, source_dna_version, template_version, generated_at, provider/model (nếu dùng AI optimize).

2.5 Prompt Studio chỉ sinh prompt. Không tạo ảnh, không chấm ảnh, không publish. Các việc đó thuộc module sau.

2.6 Code quyết cấu trúc, AI chỉ gọt chữ (kỷ luật kế thừa Module 01). Cấu trúc prompt tất định; chỉ wording của final_prompt được AI tinh chỉnh, temperature 0.


3. Input của Prompt Studio
3.1 Input chính — CHỈ DNA JSON đã merge
data/projects/<project>/knowledge/*.json     ← nguồn tri thức DUY NHẤT

DNA JSON này đã chứa (do Module 01 merge overlay): invariant, variable, allowed_imperfections (kèm source), forbidden (kèm source), curator_notes. Prompt Studio KHÔNG đọc lại overrides.yaml.

Bản .md chỉ để người tham khảo, không parse. Ưu tiên đọc bản đầy đủ; nếu chỉ cần dán nhanh có thể tham chiếu _COMPACT.md nhưng builder LUÔN dùng .json đầy đủ.
3.2 Input phụ
config/projects/<project>/prompt_rules.yaml   ← rule cấp project (tone, CTA, entity...)

prompt_studio/templates/*.yaml                ← template gốc theo loại prompt

config/settings_prompt.yaml                   ← provider/model optimizer, ngôn ngữ mặc định
3.3 User brief
Một yêu cầu sản xuất cụ thể, ví dụ: "Tạo prompt ảnh phòng lake view theo phong cách booking thật." Brief chỉ định mục tiêu sản xuất, KHÔNG thay thế Knowledge.
3.4 Knowledge Reader — quy tắc đọc DNA v1.1
- Validate source DNA contract_version nằm trong khoảng hỗ trợ (vd ">=1.1, <2.0").

  Ngoài khoảng → báo lỗi rõ, không đoán.

- forbidden: list[{rule, source}]        → giữ nguyên cả source khi đưa vào prompt.

- allowed_imperfections: list[{value, source}]

- variable (DNA)  → ánh xạ thành allowed_variations (prompt).

- invariant       → nguồn của required_dna (§7.3).

- KHÔNG đọc ảnh. KHÔNG đọc overrides.yaml.

- Thiếu field bắt buộc → báo lỗi rõ, dừng, không tạo prompt.


4. Output của Prompt Studio
Dạng kép .md (người đọc/chỉnh) + .json (module khác parse).

data/projects/venho_hotel/prompts/

├── image/    LAKE_VIEW_ROOM__booking-style__IMAGE_PROMPT_v1.0.md + .json

├── video/    LINH_AN_AT_WINDOW__15s__VIDEO_PROMPT_v1.0.md + .json

├── content/  WESTLAKE__fb-stay__CONTENT_PROMPT_v1.0.md + .json

├── seo/       WESTLAKE__blog__SEO_PROMPT_v1.0.md + .json

├── _archive/

└── prompt_manifest.json

Tên file gồm slug từ brief để hai brief khác nhau của cùng subject không đè nhau (§14).


5. Các loại prompt
Điểm sửa quan trọng: negative prompt và ngôn ngữ KHÁC nhau theo loại.
5.1 Image Prompt (image/video family — có negative thị giác)
Output: subject, scene, composition, camera_angle, lighting, material/palette, authenticity_rules (từ allowed_imperfections), forbidden (→ negative_prompt), final_prompt. Ngôn ngữ: final_prompt tiếng Anh (Flow, GPT Image, Flux tiêu thụ tiếng Anh).
5.2 Video Prompt (có negative thị giác + ĐA DNA)
Output: scene_setup, character_lock (nếu có), camera_movement, action_timeline, environment_dna, consistency_rules, forbidden, final_prompt. Đa DNA (mới v1.1): video thường ghép nhiều nguồn, vd linh_an (face DNA) + lake_view_room (environment DNA).

Luật ghép đa DNA:

- source_knowledge nhận nhiều DNA file.

- character invariants  → khóa nhận dạng nhân vật (ưu tiên tuyệt đối cho nhân vật).

- environment invariants → khóa bối cảnh.

- forbidden = union tất cả DNA (dedup), giữ source.

- Xung đột key giữa hai DNA (vd cả hai có 'lighting') → environment thắng cho scene,

  character giữ phần thuộc nhân vật; ghi rõ trong notes.
5.3 Content Prompt (KHÔNG negative thị giác — có ngôn ngữ đích + tone)
Output: audience, message_goal, tone, brand_dna, content_structure, cta_rule, target_language, restrictions (tone/claim don'ts thay cho negative thị giác), final_content_prompt.

target_language (mới v1.1): vi | en | bilingual — ngôn ngữ của NỘI DUNG đích.

  Prompt (chỉ dẫn cho AI) bằng tiếng Anh;

  nhưng chỉ rõ AI phải VIẾT nội dung bằng target_language.

  Khách Ven Hồ chủ yếu Việt + Anh → mặc định theo prompt_rules.yaml.
5.4 SEO Prompt (như content + intent)
Output: keyword_intent, reader_profile, seo_structure, internal_link_hints, location/entity_rules, target_language, final_seo_prompt.
5.5 Negative / Restriction — theo loại
image, video   → negative_prompt (thị giác): nguồn = forbidden của DNA + prompt_rules.

content, seo    → restrictions (tone/claim): "không hứa 5 sao", "không nói 'sang chảnh nhất'"...

                 KHÔNG có negative_prompt thị giác cho content/seo.

Nguồn forbidden luôn từ DNA JSON (đã gồm curated) + prompt_rules.yaml.


6. Kiến trúc module
venho-ai-studio/

├── prompt_studio/

│   ├── schemas/

│   │   ├── base.py

│   │   ├── prompt_contract.py

│   │   ├── image_prompt.py

│   │   ├── video_prompt.py

│   │   ├── content_prompt.py

│   │   └── seo_prompt.py

│   ├── templates/

│   │   ├── image_prompt.yaml

│   │   ├── video_prompt.yaml

│   │   ├── content_prompt.yaml

│   │   ├── seo_prompt.yaml

│   │   └── negative_prompt.yaml

│   ├── builders/

│   │   ├── image_prompt_builder.py

│   │   ├── video_prompt_builder.py

│   │   ├── content_prompt_builder.py

│   │   └── seo_prompt_builder.py

│   ├── knowledge_reader.py

│   ├── optimizer.py

│   ├── optimizer_mock.py          # mới v1.1 — optimizer giả cho test, không tốn token

│   ├── validator.py               # kiểm CẤU TRÚC + NỘI DUNG

│   ├── prompt_renderer.py

│   ├── prompt_store.py

│   ├── prompt_manifest.py

│   ├── pipeline.py

│   └── cli.py

│

├── config/

│   ├── settings_prompt.yaml       # mới v1.1

│   └── projects/venho_hotel/

│       └── prompt_rules.yaml

│

└── data/projects/venho_hotel/prompts/

    ├── image/  video/  content/  seo/  _archive/

    └── prompt_manifest.json

Lưu ý: dùng lại shared/vision/errors.py và pattern mock của Module 01 cho retry/isolation, không viết lại.


7. Prompt Contract
7.1 Prompt JSON
{

  "contract_version": "1.0",

  "module": "prompt_studio",

  "project": "venho_hotel",

  "prompt_type": "image",

  "prompt_id": "lake_view_room__image__booking-style",

  "prompt_version": "1.0",

  "generated_at": "ISO datetime",

  "source_knowledge": [

    { "file": "VENHO_LAKE_VIEW_ROOM_DNA.json", "dna_version": "1.0",

      "dna_contract_version": "1.1", "hash": "sha256..." }

  ],

  "template": { "name": "image_prompt.yaml", "template_version": "1.0" },

  "task_brief": "Create a realistic booking-style image of the lake view room.",

  "target_language": "en",

  "required_dna": [

    { "key": "window_frame", "value": "matte black aluminum window frame" }

  ],

  "allowed_variations": [

    { "key": "lighting", "value_range": ["morning daylight", "indoor warm light"] }

  ],

  "allowed_imperfections": [

    { "value": "minor scuff marks on skirting boards", "source": "curated" }

  ],

  "forbidden": [

    { "rule": "no floor-to-ceiling glass wall", "source": "curated" }

  ],

  "final_prompt": "...",

  "negative_prompt": "...",

  "optimizer": { "used": true, "provider": "claude", "model": "...", "temperature": 0 },

  "validation": { "structural": "pass", "faithfulness": "pass" },

  "notes": []

}

Ghi chú: contract_version (1.0) là của Module 02; source_knowledge[].dna_contract_version (1.1) là của Module 01. Với content/seo: bỏ negative_prompt, thêm restrictions và target_language bắt buộc.
7.2 Prompt Markdown — section cố định
# PROMPT FILE

## META

## TASK BRIEF

## SOURCE KNOWLEDGE

## REQUIRED DNA

## ALLOWED VARIATIONS

## ALLOWED IMPERFECTIONS

## FORBIDDEN / RESTRICTIONS

## FINAL PROMPT

## NEGATIVE PROMPT        (chỉ image/video)

## VALIDATION

## NOTES
7.3 Định nghĩa required_dna (mới v1.1)
required_dna = tập INVARIANT (và forbidden) BẮT BUỘC phải được phản ánh trong final_prompt.

- Mặc định: tất cả invariant của (các) DNA nguồn.

- Template/brief có thể thu hẹp trọng tâm nhưng KHÔNG được bỏ forbidden.

- Đây là cơ sở để validator kiểm faithfulness (§12).


8. Data Flow — ĐÃ SỬA THỨ TỰ
User brief + DNA JSON + Template + prompt_rules

        ↓

Knowledge Reader        (đọc DNA đã merge, map v1.1, check contract)

        ↓

Prompt Builder          (code: dựng cấu trúc tất định, required_dna, forbidden)

        ↓

Validate #1 (structural)  ← cấu trúc, field bắt buộc, contract

        ↓

Prompt Optimizer        (AI: gọt wording final_prompt, temperature 0) [tùy chọn]

        ↓

Validate #2 (faithfulness) ← CỔNG CHÍNH: invariant còn đủ, forbidden còn nguyên,

                             max_length, ngôn ngữ đúng

        ↓ (fail → reject bản optimize, quay lại bản deterministic; fail nữa → chỉ xuất draft)

Prompt Renderer → Prompt Store → .md + .json + manifest

Điểm mấu chốt: Optimizer chạy TRƯỚC lần validate cuối. Không có prompt chính thức nào được xuất mà chưa qua Validate #2 sau khi AI đã đụng vào.


9. AI Engine Usage
9.1 Code quyết cấu trúc: đọc DNA, chọn required_dna, lấy forbidden, lấy allowed_imperfections, render section cố định, lưu metadata, version. Tất định.

9.2 AI chỉ hỗ trợ wording: viết final_prompt mượt hơn, rút gọn, chuẩn hóa tiếng Anh, phát hiện mâu thuẫn nhẹ. temperature 0.

AI KHÔNG được: thêm DNA, bỏ forbidden, đổi source knowledge, đổi contract shape. Output sai schema hoặc rớt faithfulness → reject, dùng bản deterministic từ template.

9.3 settings_prompt.yaml (mới v1.1):

optimizer:

  enabled: true

  provider: claude

  model: "<optimizer_model>"      # điền model hiện hành

  temperature: 0

  max_attempts: 2

default_language:

  prompt_instructions: en          # chỉ dẫn cho AI luôn tiếng Anh

  content_target: vi               # nội dung content/seo mặc định (đổi theo brief)

max_length:

  image: 1800

  video: 2200

  content: 2000

  seo: 2200

9.4 Mock optimizer: test chạy optimizer_mock.py (trả input y nguyên, đúng schema) — không tốn token, kiểm thử tất định. Kế thừa kỷ luật mock của Module 01.


10. Nguyên tắc ngôn ngữ (đã tách theo loại)
- Chỉ dẫn prompt (final_prompt của image/video; khung lệnh của content/seo): TIẾNG ANH (hard rule).

- Value lấy từ DNA: vốn đã tiếng Anh (Module 01 §5.1) → giữ nguyên, không dịch.

- NỘI DUNG ĐÍCH của content/seo: theo target_language (vi | en | bilingual).

  → Prompt tiếng Anh nhưng CHỈ ĐỊNH rõ ngôn ngữ bài viết đầu ra.

- Metadata, tài liệu, CLI: tiếng Việt.


11. Prompt Template System
Mỗi loại một template. Ví dụ image_prompt.yaml:

template_version: "1.0"

prompt_type: image

sections: [objective, subject, environment, composition, lighting, materials,

           camera, authenticity, forbidden, output_style]

rules:

  language: english

  include_forbidden: true

  include_allowed_imperfections: true

  max_length: 1800

Project có thể tinh chỉnh qua prompt_rules.yaml (tone, CTA, entity, target_language mặc định) — template gốc không sửa trực tiếp.


12. Prompt Validation — CẤU TRÚC + NỘI DUNG
Validator chạy HAI tầng (xem §8).

Validate #1 — structural (sau Builder):

- có source_knowledge, template_version, contract_version, prompt_type hợp lệ

- required_dna không rỗng (trừ khi brief hợp lệ cho phép)

- forbidden có mặt nếu DNA có forbidden

- allowed_imperfections có mặt nếu DNA có

Validate #2 — faithfulness (sau Optimizer, CỔNG CHÍNH):

- MỖI required_dna invariant xuất hiện trong final_prompt (đối chiếu chuỗi/khóa)

- MỖI forbidden rule còn nguyên: image/video → có trong negative_prompt;

  content/seo → có trong restrictions

- final_prompt KHÔNG chứa chi tiết ngoài Knowledge (không có key lạ ngoài DNA + brief)

- độ dài <= max_length theo loại

- ngôn ngữ đúng: chỉ dẫn tiếng Anh; nội dung đích đúng target_language

- không mâu thuẫn rõ ràng

Fail Validate #2:

1. thử lại với bản deterministic (bỏ optimize)

2. vẫn fail → KHÔNG xuất prompt chính thức; ghi log; chỉ xuất draft nếu --allow-draft


13. Prompt Regeneration Policy
Knowledge + template không đổi (cùng hash/version)  → no change, không bump

Source DNA version/hash đổi                          → archive cũ, bump prompt_version, sinh lại

template_version đổi                                 → archive cũ, bump prompt_version, sinh lại

settings/optimizer đổi (chỉ wording)                 → tùy chọn re-render, ghi optimizer info mới

Archive theo loại: prompts/<type>/_archive/ giữ bản version cũ kèm hậu tố version.


14. Prompt Manifest
data/projects/<project>/prompts/prompt_manifest.json:

{

  "project": "venho_hotel",

  "prompts": [

    {

      "prompt_id": "lake_view_room__image__booking-style",

      "prompt_type": "image",

      "subject": "lake_view_room",

      "brief_slug": "booking-style",

      "current_version": "1.0",

      "source_knowledge_hashes": ["sha256..."],

      "template_version": "1.0",

      "target_language": "en",

      "generated_at": "ISO datetime",

      "status": "active"

    }

  ]

}

prompt_id = subject + prompt_type + brief_slug → hai brief khác nhau của cùng subject không đè nhau.


15. CLI
venho prompt            # menu chọn loại: [A] Image [B] Video [C] Content [D] SEO

Sau đó hỏi: Project? / Subject / Knowledge file (cho phép NHIỀU file cho video đa DNA)? / Task brief? / Target language (content/seo)? / Output folder?

Flags:

venho prompt --type image  --project venho_hotel --subject lake_view_room --brief "realistic booking-style room image"

venho prompt --type video  --project venho_hotel --subject linh_an,lake_view_room --brief "15s video at lake view window"

venho prompt --type content --project venho_hotel --subject westlake --lang vi --brief "Facebook post about staying near West Lake"

venho prompt --type seo    --project venho_hotel --subject westlake --lang vi --brief "blog about hotels near West Lake Hanoi"

venho prompt --all --project venho_hotel --subject lake_view_room   # sinh nhiều loại một lượt

--subject a,b cho video đa DNA. --allow-draft để xuất bản draft khi Validate #2 fail.


16. Kế hoạch phát triển theo GIAI ĐOẠN
Năm giai đoạn. Mỗi step giao riêng cho Claude Code; step sau chỉ bắt đầu khi DoD xanh.
GIAI ĐOẠN 0 — Nền tảng & hợp đồng
Step 0 — Chuẩn bị module. Tạo cây prompt_studio/, config/settings_prompt.yaml, data/.../prompts/. DoD: import không lỗi; KHÔNG ảnh hưởng Module 01; settings_prompt.yaml đủ field (§9.3).

Step 1 — Prompt Contract Schema. schemas/{base, prompt_contract}.py. DoD: Pydantic validate Prompt JSON mẫu; có contract_version, prompt_type, prompt_id, target_language, required_dna, validation block.

Step 2 — Knowledge Reader (đọc DNA v1.1). knowledge_reader.py. DoD: đọc DNA JSON mẫu của Module 01; check dna_contract_version trong khoảng hỗ trợ; map forbidden/allowed_imperfections dạng {,,source}; map variable→allowed_variations; KHÔNG đọc overrides.yaml; KHÔNG đọc ảnh; thiếu field → lỗi rõ.

Step 3 — Mock Optimizer + error reuse. optimizer_mock.py; nối shared/vision/errors.py. DoD: mock trả output đúng schema, không gọi mạng; pipeline test chạy được offline.
GIAI ĐOẠN 1 — Đường Image tới MVP
Step 4 — Template System. templates/{image,video,content,seo,negative}_prompt.yaml. DoD: load được; có template_version, prompt_type, rules (language, max_length, include_forbidden).

Step 5 — Image Prompt Builder (tất định). builders/image_prompt_builder.py. DoD: nhận DNA + brief → Prompt JSON hợp lệ; điền required_dna từ invariant; forbidden→negative_prompt; allowed_imperfections→authenticity; final_prompt dựng từ template; chạy hai lần cấu trúc GIỐNG NHAU (tất định).

Step 6 — Renderer + Store. prompt_renderer.py, prompt_store.py. DoD: xuất .md + .json; section §7.2 cố định; json round-trip; tên file kèm brief_slug.

Step 7 — Validator (2 tầng). validator.py. DoD: Validate #1 structural đủ check §12; Validate #2 faithfulness kiểm invariant xuất hiện trong final_prompt và forbidden còn trong negative_prompt, max_length, ngôn ngữ; fail → không xuất official, hỗ trợ --allow-draft.

Step 8 — MVP Image Prompt. ◀ MỐC GIÁ TRỊ ĐẦU TIÊN Test: VENHO_LAKE_VIEW_ROOM_DNA.json + brief booking-style → LAKE_VIEW_ROOM image prompt. DoD: prompt đọc được; bám DNA (Validate #2 pass); có forbidden; có allowed imperfections; không bịa ngoài DNA. ➜ Dừng, review.
GIAI ĐOẠN 2 — Optimize có cổng faithfulness
Step 9 — Prompt Optimizer + pipeline order. optimizer.py, pipeline.py. DoD: pipeline chạy đúng thứ tự §8 (Build → V#1 → Optimize → V#2 → Render); optimizer temperature 0; AI optimize KHÔNG làm mất required_dna/forbidden — nếu mất, Validate #2 chặn; sai schema → reject về bản deterministic.
GIAI ĐOẠN 3 — Mở rộng loại prompt
Step 10 — Video Prompt Builder (ĐA DNA). builders/video_prompt_builder.py. DoD: nhận NHIỀU DNA (vd linh_an + lake_view_room); có timeline, camera_movement, character_lock, environment_dna; forbidden = union dedup; xử lý xung đột key theo §5.2; ghi source từng phần.

Step 11 — Content Prompt Builder (target_language). builders/content_prompt_builder.py. DoD: có audience, tone, CTA, brand_dna; target_language điều khiển ngôn ngữ nội dung đích; restrictions thay negative thị giác; bám Brand/Location DNA.

Step 12 — SEO Prompt Builder. builders/seo_prompt_builder.py. DoD: có keyword_intent, seo_structure, entity/location rules, target_language; bám DNA.
GIAI ĐOẠN 4 — Sản xuất & vận hành
Step 13 — Manifest + Regeneration. prompt_manifest.py. DoD: prompt_manifest.json (id gồm brief_slug); Knowledge không đổi→no change; đổi→archive+bump; template đổi→archive+bump.

Step 14 — CLI hoàn chỉnh. cli.py. DoD: venho prompt menu; --type, --subject a,b, --lang, --all, --allow-draft chạy được; có run report.

Step 15 — Test toàn diện với Ven Hồ. Test: lake_view_room image; linh_an+lake_view_room video; westlake content (vi); westlake seo (vi). DoD: cả 4 loại sinh được; Validate #2 pass; KHÔNG thay đổi Knowledge; prompt dùng trực tiếp được trong AI tools; content/seo đúng ngôn ngữ đích.


17. Rủi ro chính
1. Prompt bịa tri thức        → chỉ lấy từ DNA JSON; required_dna rõ; Validate #2 kiểm nội dung

2. Prompt mất forbidden       → forbidden bắt buộc; Validate #2 chặn (image/video: negative; content/seo: restrictions)

3. Optimizer phá prompt sau validate → SỬA: Optimize trước Validate #2 (§8)

4. Prompt quá dài             → max_length theo loại; optimizer rút gọn; có _COMPACT DNA input

5. Prompt không version được  → manifest + source_knowledge_hashes + brief_slug + archive

6. Lệch hợp đồng Module 01    → reader check dna_contract_version; map v1.1; không đọc overlay

7. Sai ngôn ngữ nội dung      → target_language cho content/seo; prompt-instruction luôn English

8. Video đa DNA xung đột      → luật ghép §5.2; environment vs character rõ ràng

9. Test tốn token             → optimizer_mock; determinism DoD

10. Lấn module khác           → không tạo ảnh, không validate ảnh, không publish


18. Thứ tự ưu tiên thực tế
Nền tảng: Contract → Knowledge Reader → Mock

Image path: Template → Image Builder → Renderer/Store → Validator → MVP Image

Optimize: Optimizer + pipeline order + cổng faithfulness

Mở rộng: Video (đa DNA) → Content (target_language) → SEO

Vận hành: Manifest/Regeneration → CLI → Test Ven Hồ

Làm Image trước — cầu nối trực tiếp từ Knowledge sang Visual production.


19. Definition of Done — Module 02
- Đọc DNA JSON đã merge của Module 01 (check contract_version).

- Sinh được Image / Video (đa DNA) / Content (target_language) / SEO prompt.

- Xuất .md + .json; có Prompt Contract; có Manifest; có Version/Archive.

- Validator hai tầng: structural + faithfulness (invariant giữ, forbidden không mất).

- Pipeline đúng thứ tự: Optimize trước Validate cuối.

- CLI đủ menu + flags; có mock để test không tốn token; cấu trúc tất định.

- KHÔNG đọc ảnh gốc; KHÔNG đọc overrides.yaml; KHÔNG đổi Knowledge.

- KHÔNG tạo ảnh, KHÔNG chấm ảnh, KHÔNG publish.


20. Kết luận
Module 02 là cầu nối Knowledge → AI Production: Module 01 biến ảnh thành Knowledge, Module 02 biến Knowledge thành Prompt.

Điểm cần giữ tuyệt đối:

Knowledge (DNA JSON đã merge) là nguồn sự thật DUY NHẤT.

Prompt là sản phẩm sinh ra, tái sinh được, không được bịa.

Code quyết cấu trúc; AI chỉ gọt chữ (temperature 0).

Optimize luôn đứng TRƯỚC cổng validate cuối.

Faithfulness được KIỂM bằng nội dung, không chỉ bằng sự tồn tại của field.

Forbidden không bao giờ được mất; invariant luôn phải xuất hiện.

Prompt Studio chỉ sinh prompt.

END OF DOCUMENT v1.1 (QC Consolidated)

