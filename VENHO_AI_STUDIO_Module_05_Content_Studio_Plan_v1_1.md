VENHO AI STUDIO
MODULE 06 — VIDEO STUDIO — Development Plan v1.1 (QC Consolidated)
Workspace mẹ: THE WEST LAKE LIVING Repo: venho-ai-studio Module: video_studio/ Phụ thuộc: Module 01 (DNA + Face DNA) · Module 02 (Video Prompt) · Module 03 (Validator) · Module 04 (Automation) · Module 05 (Content text) · shared/ AI Engine: OpenAI + Claude Mục tiêu: Biến Knowledge/DNA thành GÓI SẢN XUẤT VIDEO có cấu trúc (concept → storyboard → shot list → prompt cảnh → continuity) để render nhất quán ở engine ngoài (Veo/Kling/Runway/Seedance).


0. Kết quả QC v1.0 → v1.1
LỖI RANH GIỚI (nghiêm trọng)

1. Trùng dựng video prompt với M02 → SỬA: M02 dựng prompt DNA-faithful từng cảnh;

   M06 lo temporal/narrative + package; M06 gọi M02 (§1.1, §11.2)

LỖI THÀNH THẬT VỀ PHẠM VI

2. Ngụ ý gói đảm bảo kết quả render → SỬA: render ở engine NGOÀI; M06 validate GÓI (pre-render);

   trôi identity per-frame là hậu-render/ngoài, tương lai (§2.5, §11.3)

3. Continuity không cơ chế         → SỬA: continuity_keys (invariant DNA + face-lock)

   phải có trong MỌI cảnh; checker khẳng định (§7.1)

4. Character không nối Face DNA/07F → SỬA: character rules từ Face DNA (M01) + rubric 07F (M03) (§6.2)

LỖI KỶ LUẬT HỆ THỐNG

5. source_knowledge thiếu version/hash → {file,version,hash} + manifest (§9,§10)

6. Ngôn ngữ lẫn lộn                  → engine_prompt English; caption/voiceover target_language (§12.1)

7. Caption/voiceover trùng M05       → text đến TỪ M05; M06 chỉ nhúng (§11.5)

8. Forbidden trùng/chỉ phát hiện     → không gian/brand qua prompt M02 (phòng);

   negative chuyển động ở config video; validator phát hiện (§2.6, §8)

LỖ HỔNG VIDEO

9. Không kiểm tổng thời lượng        → Σ scene_duration = duration_seconds (§7.2)

10. target_engine đơn vs "2 engine"  → một engine chính + biến thể tùy chọn (§9)

11. Bridge chưa degradation          → not_available + dùng prompt-validation per cảnh (§11.3)


1. Vai trò của Video Studio
Video Studio biến Knowledge thành gói sản xuất video có cấu trúc — không phải công cụ dựng phim. Output cốt lõi:

Concept → Storyboard → Shot List → Scene Prompts → Negative → Continuity → Validation
1.1 Phân vai dứt khoát với Module 02 (sửa lỗi trùng)
MODULE 02 (Prompt Studio) = DỰNG PROMPT VIDEO cho TỪNG CẢNH:

   prompt DNA-faithful, đa DNA (Linh An + phòng), character_lock, environment_dna,

   camera, forbidden union — đã qua cổng faithfulness của M02.

MODULE 06 (Video Studio)  = lớp THỜI GIAN / TƯỜNG THUẬT + ĐÓNG GÓI:

   concept · storyboard (cấu trúc cảnh, thời lượng, DNA mỗi cảnh) · shot list ·

   continuity giữa các cảnh · định dạng theo engine (Veo/Kling...) · đóng gói package.

   → M06 GỌI M02 để dựng prompt mỗi cảnh; KHÔNG dựng prompt lại.

Chia rõ: Module 02 lo DNA đúng cho từng cảnh; Module 06 lo chuỗi cảnh, liên tục, định dạng engine, đóng gói.


2. Nguyên tắc thiết kế
2.1 Knowledge First. Mọi prompt cảnh bắt nguồn từ Knowledge — nhưng đến qua prompt của M02. Không tạo cảnh ngoài Knowledge; không biến Ven Hồ thành resort luxury; không làm Linh An trôi identity.

2.2 Prompt is not the source. Prompt là output từ Knowledge + production goal + platform rules.

2.3 Storyboard before Prompt. Concept → Storyboard → Shot List → (gọi M02) Scene Prompt. Vì video cần logic thời gian, chuỗi shot, camera, kiểm soát identity qua nhiều frame.

2.4 Draft First. M06 chỉ tạo package. Không render, không upload, không publish. Workflow dài thuộc M04.

2.5 Thành thật về render ngoài (mới v1.1). Video render ở engine NGOÀI. M06 validate GÓI trước render; kết quả render (trôi identity per-frame, artifact chuyển động) chỉ kiểm được sau render trên file video — hiện là thủ công/ngoài phạm vi (Video Validation của M03 là tương lai). M06 tối đa hóa cơ hội khớp bằng continuity + negative mạnh, KHÔNG đảm bảo render.

2.6 Forbidden: phòng TRƯỚC, phát hiện SAU + single-source. Forbidden không gian/brand (no glass wall, no luxury) đến từ DNA qua prompt M02 (phòng ngừa). Negative CHUYỂN ĐỘNG video (no fast cuts, no shaky cam) ở config video. Validator M03 phát hiện. Không có hai danh sách forbidden không gian lệch nhau.

2.7 Project-agnostic. Core không hard-code Ven Hồ.


3. Phạm vi Module 06
CÓ:    concept · storyboard · shot list · scene prompt (qua M02) · prompt đa engine ·

       negative chuyển động · continuity · character rules · camera/motion ·

       package .md+.json · gửi validator (pre-render)

CHƯA:  render video · upload · hậu kỳ · ghép nhạc · timeline editor · UI phức tạp ·

       validate video đã render (post-render — tương lai)


4. Input
QUA MODULE 02 (prompt cảnh DNA-faithful, đa DNA)

QUA MODULE 05 (text: caption, hook, voiceover, CTA)

ĐỌC TRỰC TIẾP (config lớp video — KHÔNG phải DNA/forbidden không gian):

  config/projects/<project>/video/{video_style, platform_rules, camera_rules,

                                   motion_rules, character_rules, motion_negatives}.yaml

QUA MODULE 01 (gián tiếp): Face DNA + DNA invariants → nguồn continuity_keys

Thiếu Knowledge → M02 báo Missing Knowledge; M06 dừng, không bịa.


5. Output
data/projects/<project>/video/{concepts, storyboards, shot_lists, prompts,

                               packages, validation}/

   <date>_<slug>_<duration>.md + .json

data/projects/<project>/video/video_manifest.json


6. Các loại Video
6.1 Hotel Lifestyle — room view, lobby, rooftop, West Lake walk. Vd 15s vertical morning lake view room. 6.2 Character (Linh An) — YÊU CẦU đặc biệt, nối vào tài sản đã có:

- Character rules LẤY TỪ Face DNA (M01, đã qua cổng 07F ở Step 13), KHÔNG phát minh lại.

- Face-lock descriptor của Linh An là continuity_key bắt buộc trong MỌI cảnh.

- Pre-render: validate face-lock có trong prompt mỗi cảnh (M03 prompt validation).

- Post-render drift (per-frame): NGOÀI phạm vi hiện tại — cần Video Validation tương lai.

6.3 Social Reel / Short — hook visual, 3–5 shot, caption overlay (TỪ M05), CTA end card, music mood note. 6.4 Website / Hero — calm movement, clean, brand-safe, no hard sale, no unrealistic luxury. 6.5 Explainer / Service — script + shot list + voiceover (TỪ M05) + visual notes + CTA.


7. Video Production Package
Concept · Storyboard · Shot List · Scene Prompts (từ M02) · Motion Negatives ·

Continuity Rules · Character Rules · Camera/Motion Rules · Platform Rules ·

Validation Checklist · Export Notes
7.1 Cơ chế Continuity (mới v1.1)
continuity_keys = INVARIANT từ DNA (window_frame, bedding, room geometry...)

                + face-lock descriptor (nếu include_character)

Luật: MỖI scene prompt PHẢI chứa TẤT CẢ continuity_keys giống hệt nhau.

continuity_checker khẳng định (deterministic); thiếu ở cảnh nào → FAIL cảnh đó.

Đây là cách giữ nhất quán qua nhiều frame ở mức prompt (mức duy nhất M06 kiểm được trước render).
7.2 Kiểm thời lượng (mới v1.1)
Σ scene_duration PHẢI = duration_seconds. Lệch → storyboard builder báo lỗi, không xuất.


8. Cấu trúc repo (phân cấp rõ)
video_studio/

├── video_engine.py              # ORCHESTRATOR: request → context → concept → storyboard

│                                #   → shot list → (M02 scene prompts) → continuity → package

├── video_request.py

├── video_context.py             # nạp config video + Face DNA/invariants (continuity_keys)

├── prompt_bridge.py             # MỚI: gọi Module 02 dựng scene prompt (đa DNA)

├── content_bridge.py            # MỚI: lấy caption/voiceover/hook/CTA từ Module 05

├── concept_builder.py

├── storyboard_builder.py        # cấu trúc cảnh + kiểm Σ duration

├── shot_list_builder.py

├── engine_formatter.py          # MỚI: định dạng prompt theo Veo/Kling/Runway/Seedance

├── continuity_checker.py        # khẳng định continuity_keys trong mọi cảnh

├── validator_bridge.py          # có degradation

├── video_manifest.py            # MỚI: theo dõi + staleness

├── cli.py

├── builders/                    # preset cấu hình pipeline theo LOẠI video

│   ├── lifestyle_video_builder.py  character_video_builder.py

│   ├── reel_builder.py  website_hero_builder.py  explainer_builder.py

├── templates/                   # ĐỊNH DẠNG ENGINE (Veo/Kling...) + preset thời lượng

│   ├── veo.yaml kling.yaml runway.yaml seedance.yaml

│   ├── reel_15s.yaml reel_30s.yaml hero_video.yaml

├── schemas/

│   ├── video_request.py video_package.py storyboard.py shot.py engine_prompt.py

└── renderers/{markdown_renderer.py, json_renderer.py}

config/projects/<project>/video/

├── video_style.yaml platform_rules.yaml camera_rules.yaml

├── motion_rules.yaml character_rules.yaml motion_negatives.yaml

# (forbidden KHÔNG GIAN/BRAND không ở đây — single-source qua prompt M02)

Phân cấp: video_engine điều phối → concept/storyboard/shot/continuity là các stage → builders/ là preset theo loại video. Test dùng mock (kế thừa shared).


9. Video Request Model
{

  "project": "venho_hotel",

  "video_type": "social_reel",

  "topic": "lake view room morning",

  "duration_seconds": 15,

  "aspect_ratio": "9:16",

  "platform": "instagram_reels",

  "caption_language": "vi",

  "include_character": false,

  "target_audience": "Vietnamese leisure guests",

  "source_knowledge": [

    { "file": "VENHO_LAKE_VIEW_ROOM_DNA.json", "dna_version": "1.0", "hash": "sha256..." },

    { "file": "VENHO_WESTLAKE_DNA.json", "dna_version": "1.0", "hash": "sha256..." }

  ],

  "target_engine": "veo",

  "alt_engines": ["kling"],

  "validation_required": true

}

caption_language (không phải language) — rõ đây là ngôn ngữ caption/voiceover, KHÔNG phải ngôn ngữ prompt. target_engine = engine chính; alt_engines = biến thể tùy chọn (sửa mâu thuẫn "2 engine").


10. Video Package Model
{

  "contract_version": "1.0",

  "module": "video_studio",

  "project": "venho_hotel",

  "video_type": "social_reel",

  "duration_seconds": 15,

  "aspect_ratio": "9:16",

  "target_engine": "veo",

  "generated_at": "ISO",

  "source_knowledge": [

    { "file": "VENHO_LAKE_VIEW_ROOM_DNA.json", "dna_version": "1.0", "hash": "sha256..." }

  ],

  "continuity_keys": ["black aluminum window frame", "white bedding", "narrow room geometry"],

  "concept": { "title": "Morning by West Lake", "objective": "...", "tone": "warm, natural" },

  "storyboard": [

    { "scene_number": 1, "duration_seconds": 4,

      "description": "...", "camera_movement": "slow handheld push-in",

      "visual_dna_required": ["narrow hotel room", "black aluminum window frame"],

      "scene_prompt_ref": { "source": "module_02", "prompt_version": "1.0" },

      "engine_prompt": "...(English)...",

      "forbidden": [ { "rule": "no floor-to-ceiling glass wall", "source": "curated" } ] }

  ],

  "duration_check": { "sum_scenes": 15, "target": 15, "ok": true },

  "continuity_check": { "all_scenes_have_keys": true },

  "text_from_content": { "caption": "(từ M05)", "voiceover": null, "cta": "(từ M05)",

                         "caption_language": "vi" },

  "engine_prompt_full": "...(English)...",

  "motion_negative_prompt": "no fast cuts, no shaky cam",

  "validation": { "scope": "pre_render", "required": true, "status": "pending" }

}

validation.scope = pre_render nói rõ chỉ kiểm gói, không kiểm video đã render.


11. Quan hệ với các Module
11.1 Knowledge (M01): đọc DNA invariants + Face DNA để lấy continuity_keys; không sửa Knowledge. 11.2 Prompt (M02): M06 gọi M02 dựng scene prompt DNA-faithful (đa DNA); M06 không dựng prompt lại. 11.3 Validator (M03) — pre-render + degradation:

CÓ NGAY:  prompt validation cho TỪNG scene prompt (M03 đã có) + kiểm continuity_keys.

TƯƠNG LAI: video-package validation / post-render frame validation → chưa có

           → bridge trả status "not_available", không chặn; ghi scope=pre_render.

11.4 Automation (M04): điều phối Generate package → Validate (pre-render) → Save → (render ngoài thủ công) → sau này validate post-render. 11.5 Content (M05): caption/hook/voiceover/CTA ĐẾN TỪ M05 (qua content_bridge); M06 nhúng, KHÔNG tự sinh text.


12. Video Prompt Strategy
Prompt cảnh (do M02 dựng) chia section: Scene · Subject · Environment · Camera · Motion · Lighting · Style · Continuity · Negative · Duration · Aspect Ratio.
12.1 Ngôn ngữ (đã tách)
engine_prompt (gửi Veo/Kling...): TIẾNG ANH (hard rule — engine tiêu thụ English).

caption / voiceover: theo caption_language (vi | en | bilingual), lấy từ M05.

Metadata/CLI: tiếng Việt.


13. Markdown Output chuẩn
# VIDEO PRODUCTION PACKAGE

## META

## SOURCE KNOWLEDGE

## CONTINUITY KEYS

## VIDEO OBJECTIVE

## TARGET PLATFORM / ENGINE

## CONCEPT

## STORYBOARD (per scene: duration, DNA required, camera, forbidden)

## SHOT LIST

## ENGINE PROMPT (English)

## MOTION NEGATIVE

## CONTINUITY RULES

## CHARACTER RULES (nếu có, từ Face DNA)

## CAMERA / MOTION RULES

## CAPTION / VOICEOVER (từ Content Studio)

## DURATION CHECK

## VALIDATION (scope: pre_render)


14. Kế hoạch phát triển theo GIAI ĐOẠN
GIAI ĐOẠN 0 — Nền tảng & hợp đồng
Step 0 — Module setup. Cây video_studio/, config/video/, test folder. DoD: import không lỗi; README; nối shared (mock).

Step 1 — Request/Package Schema. schemas/{video_request, video_package, storyboard, shot}.py. DoD: validate request+package mẫu; contract_version; source_knowledge {file,version,hash}; continuity_keys; caption_language; duration_check/continuity_check fields.

Step 2 — Project Video Config. config/.../video/*.yaml (style, platform, camera, motion, character, motion_negatives). DoD: load được; fallback; KHÔNG chứa forbidden không gian/brand (single-source qua M02); không hard-code Ven Hồ.
GIAI ĐOẠN 1 — Cầu nối & ngữ cảnh
Step 3 — Prompt Bridge (M02) + Content Bridge (M05). prompt_bridge.py, content_bridge.py. DoD: prompt_bridge gọi M02 dựng scene prompt (đa DNA, đã có forbidden/character_lock); content_bridge lấy caption/voiceover/CTA từ M05; thiếu Knowledge → Missing, không bịa.

Step 4 — Video Context Loader. video_context.py. DoD: nạp config video + Face DNA/invariants → dựng continuity_keys; báo missing đúng.
GIAI ĐOẠN 2 — Chuỗi thời gian & MVP
Step 5 — Concept Builder. DoD: objective/tone/platform/source từ request. Step 6 — Storyboard Builder (+ duration check). DoD: 3–5 cảnh cho 15s; mỗi cảnh có duration + visual_dna_required; Σ duration = duration_seconds; không vi phạm forbidden. Step 7 — Shot List Builder. DoD: mỗi scene có camera angle/movement/motion/lighting notes. Step 8 — Scene Prompt qua M02 + Engine Formatter. engine_formatter.py. DoD: mỗi cảnh gọi M02 lấy prompt DNA-faithful; format theo target_engine (+ alt_engines); engine_prompt tiếng Anh; AI không viết prompt tự do (M02 lo cấu trúc). Step 9 — Continuity Checker. continuity_checker.py. DoD: continuity_keys từ DNA invariants (+ face-lock nếu character); khẳng định mọi cảnh chứa đủ keys; thiếu → fail cảnh; character continuity khi include_character. Step 10 — Renderer. DoD: .md+.json; section §13 cố định; round-trip. Step 11 — Validator Bridge (pre-render + degradation). validator_bridge.py. DoD: gửi từng scene prompt sang M03 prompt validation + kiểm continuity; video-package validation chưa có → not_available; ghi scope=pre_render. Step 12 — MVP Lifestyle Reel. ◀ MỐC GIÁ TRỊ ĐẦU TIÊN Test: lake view room morning, 15s, 9:16, Veo, nguồn Lake View Room + West Lake + Brand DNA. DoD: full package; storyboard hợp lý; Σ duration=15; mỗi cảnh có continuity_keys; prompt đúng DNA (qua M02); không luxury/không glass wall; caption từ M05; validator pre-render pass hoặc not_available; .md+.json + manifest. ➜ Dừng, review.
GIAI ĐOẠN 3 — Nhân vật (nối Face DNA/07F)
Step 13 — Character Video Builder. builders/character_video_builder.py. DoD: character rules TỪ Face DNA (M01); face-lock là continuity_key bắt buộc; identity continuity mọi cảnh; pre-render validate face-lock trong prompt (M03); ghi rõ post-render drift NGOÀI phạm vi; outfit/expression/motion rules.
GIAI ĐOẠN 4 — Mở rộng loại & vận hành
Step 14 — Reel Builder. DoD: 15s+30s; hook visual; caption overlay (từ M05); CTA end card. Step 15 — Website Hero Builder. DoD: motion nhẹ; brand-safe; no hard sale; đúng Location DNA. Step 16 — Explainer Builder. DoD: script + shot list + voiceover (từ M05) + CTA + source. Step 17 — Manifest + CLI. video_manifest.py, cli.py. DoD: manifest ghi source hash + staleness; venho video chọn project/type/topic/duration/engine; --lang, --mock; lưu đúng folder.


15. Definition of Done — Module 06
- Sinh concept/storyboard/shot list/scene prompt (qua M02)/negative/continuity/package.

- Prompt cảnh đi QUA M02 (DNA-faithful, đa DNA); M06 không dựng prompt lại.

- Continuity_keys có trong mọi cảnh; Σ duration khớp; engine_prompt tiếng Anh.

- Caption/voiceover từ M05; character rules từ Face DNA + 07F.

- Validate scope=pre_render (post-render là tương lai); bridge degradation.

- .md+.json; contract_version; source {file,version,hash}; manifest+staleness.

- Test mock; project-agnostic; KHÔNG render/publish.


16. Rủi ro chính
1. Prompt dài thiếu cấu trúc   → concept→storyboard→shot→(M02) prompt; section rõ

2. Sai DNA không gian          → prompt qua M02 (DNA-faithful); validator pre-render

3. Trôi Linh An                → face-lock là continuity_key mọi cảnh; nhưng post-render

                                 drift NGOÀI phạm vi — thừa nhận, không giả vờ chặn được

4. Trùng dựng prompt với M02   → M02 dựng prompt cảnh; M06 lo temporal+package

5. Video quá luxury            → forbidden không gian qua M02; motion negatives ở config

6. Ngôn ngữ sai                → engine_prompt English; caption theo caption_language

7. Caption trùng M05           → text từ M05; M06 chỉ nhúng

8. Thời lượng lệch             → Σ scene_duration = duration_seconds (bắt buộc)

9. Hard-code Ven Hồ            → config project; core agnostic

10. Publish nhầm               → chỉ package; publish thuộc M04; status=draft

11. Chờ video validation M03   → bridge not_available; dùng prompt-validation per cảnh


17. Thứ tự ưu tiên thực tế
Nền tảng:  Schema → Video Config → Prompt/Content Bridge → Context (continuity_keys)

Chuỗi:     Concept → Storyboard(+duration) → Shot List → Scene Prompt(M02)+Formatter

           → Continuity Checker → Renderer → Validator Bridge → MVP Lifestyle Reel

Nhân vật:  Character Video (Face DNA + 07F)

Mở rộng:   Reel → Hero → Explainer → Manifest/CLI

Bắt đầu: Lake View Room Morning — 15s vertical reel (gần Ven Hồ nhất, dễ kiểm DNA).


18. Kết luận
Video Studio là cầu nối Knowledge → sản xuất video — nhưng trung thực về ranh giới: nó không dựng prompt (M02 làm), không tạo text (M05 làm), không render (engine ngoài), không đảm bảo kết quả render (chỉ tối đa hóa cơ hội qua continuity + negative). Nó tạo lớp chỉ dẫn có cấu trúc để video AI hoạt động nhất quán hơn.

Điểm cần giữ tuyệt đối:

M06 lo THỜI GIAN/TƯỜNG THUẬT + ĐÓNG GÓI; M02 dựng prompt cảnh DNA-faithful.

continuity_keys phải xuất hiện trong MỌI cảnh — đây là cách giữ nhất quán trước render.

Render ở engine NGOÀI; M06 validate GÓI, không đảm bảo video render.

Character từ Face DNA + 07F; caption/voiceover từ M05; engine_prompt tiếng Anh.

Chỉ tạo package; không render/publish. Ven Hồ là project đầu tiên, không phải lõi.

END OF DOCUMENT v1.1 (QC Consolidated)

