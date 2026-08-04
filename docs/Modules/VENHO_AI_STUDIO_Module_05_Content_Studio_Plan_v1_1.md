VENHO AI STUDIO
MODULE 05 — CONTENT STUDIO — Development Plan v1.1 (QC Consolidated)
Workspace mẹ: THE WEST LAKE LIVING Repo: venho-ai-studio Module: content_studio/ Phụ thuộc: Module 01 (DNA) · Module 02 (Content/SEO Prompt) · Module 03 (Content Validator) · Module 04 (Automation) · shared/ AI Engine: OpenAI + Claude Mục tiêu: Biến Knowledge/DNA thành nội dung marketing/SEO/social/website THẬT — dựa trên tri thức chuẩn hóa, không viết theo cảm tính, không tự publish.


0. Kết quả QC v1.0 → v1.1
LỖI RANH GIỚI (nghiêm trọng)

1. Trùng "sản xuất nội dung" với Module 02 → SỬA: phân vai. M02 DỰNG prompt nội dung;

   M05 THỰC THI prompt đó để viết prose. M05 không dựng lại prompt (§1.1, §10.2)

2. Mâu thuẫn nguồn (Knowledge vs Prompt)   → SỬA: M05 LUÔN đi qua content-prompt của M02;

   DNA facts đến qua prompt, không tự parse lại (§4, §12)

LỖI KỶ LUẬT HỆ THỐNG

3. Forbidden chỉ phát hiện, không phòng    → SỬA: chèn forbidden/CTA vào SINH (qua prompt M02)

   + tiền lọc ở M05 + validator ở M03 (§2.5, §10.3)

4. source_knowledge thiếu version/hash     → SỬA: {file, version, hash} (§8, §9)

5. Thiếu manifest + staleness             → SỬA: content_manifest + cờ source_updated (§9.1)

6. Phụ thuộc chéo M03 chưa khai báo        → SỬA: bridge degradation khi content validator chưa có (§10.3)

LỖ HỔNG NỘI DUNG & CHIẾN LƯỢC

7. language đơn trị, lệch tên M02          → SỬA: target_language + hỗ trợ bilingual (§8)

8. Campaign không có cơ chế               → SỬA: một message-core → tạo hình theo kênh (§6.8)

9. Calendar không có input model          → SỬA: cadence + topic từ pillar (§6.7)

10. OTA có Booking.com                     → SỬA: Agoda + Google Business + direct (§6.4)

11. forbidden_claims trùng/ba lớp mờ       → SỬA: single-source + phân cấp engine/builder rõ (§7)


1. Vai trò của Content Studio
Content Studio trả lời: "Nội dung cuối cùng để đăng/dùng/xuất bản là gì?" Nó biến Knowledge → nội dung thật, KHÔNG viết tùy hứng.
1.1 Phân vai dứt khoát với Module 02 (sửa lỗi trùng lặp)
MODULE 02 (Prompt Studio)  = DỰNG PROMPT nội dung/SEO:

   chỉ dẫn có cấu trúc, sinh tất định từ DNA, đã gắn required_dna, forbidden,

   CTA rules, target_language, và đã qua cổng faithfulness của M02.

   → M02 KHÔNG gọi AI viết bài.

MODULE 05 (Content Studio) = THỰC THI prompt đó:

   gọi AI viết prose thật · tạo hình theo từng kênh (độ dài, hashtag, format) ·

   render .md+.json · đa kênh/campaign · calendar · gửi validator · lưu draft.

   → M05 KHÔNG dựng lại prompt, KHÔNG tự phán faithfulness (đã là việc của M02).

Hệ quả: templates/ của M05 là template ĐỊNH HÌNH OUTPUT (bố cục section .md + rule kênh như max_length, hashtag), KHÔNG phải template dựng prompt. Việc dựng prompt thuộc M02.


2. Nguyên tắc thiết kế
2.1 Knowledge First. Mọi nội dung bắt nguồn từ Knowledge — nhưng đến M05 qua content-prompt của M02, không tự nhớ, không bịa, không thêm claim vô nguồn.

2.2 Brand Consistency. Giữ Brand DNA, tone, audience, content pillars, SEO, CTA rules, forbidden claims.

2.3 Multi-channel, Single Source. Một Knowledge → nhiều định dạng, không viết rời rạc lại từ đầu.

2.4 Draft First, Publish Later. M05 chỉ tạo draft (status=draft). Publish thuộc Automation hoặc thao tác người dùng.

2.5 Forbidden: phòng ngừa TRƯỚC, phát hiện SAU. Forbidden claims + CTA rules được chèn vào chỉ dẫn sinh (đã có trong content-prompt của M02) để AI không viết ra; M05 tiền lọc chuỗi forbidden trước khi lưu; M03 validator chấm cuối. Ba lớp.

2.6 Ngoại lệ nhiệt độ có kiểm soát (mới v1.1). Đây là module DUY NHẤT mà sáng tạo của AI là sản phẩm → cho phép temperature > 0 khi viết prose. NHƯNG: cấu trúc output vẫn render từ JSON (không để AI tự bịa bố cục); faithfulness vẫn ràng bằng prompt M02 + forbidden injection + validator M03. Tất định áp cho CẤU TRÚC và NGUỒN, không áp cho câu chữ sáng tạo.

2.7 Project-agnostic. Core không hard-code Ven Hồ; đọc rule từ config project.


3. Phạm vi Module 05
CÓ:    social · blog SEO · website copy · OTA · FAQ · email draft · content calendar ·

       campaign đa kênh · nhiều bản theo tone/length/platform · .md+.json ·

       lịch sử nội dung + manifest · gửi Validator

CHƯA:  đăng tự động · chạy ads · quản lý inbox · thay CMS · thay scheduler ·

       UI phức tạp · tự quyết publish


4. Input của Content Studio
ĐI QUA MODULE 02 (nguồn tri thức nội dung):

  content-prompt do M02 dựng (đã nhúng DNA facts + forbidden + CTA + target_language)

ĐỌC TRỰC TIẾP (config lớp nội dung — KHÔNG phải DNA):

  config/projects/<project>/content/{content_pillars, tone_of_voice, platform_rules,

                                     seo_keywords, calendar_rules}.yaml

  data/projects/<project>/content/_archive/   (nội dung cũ để tránh lặp)

Quy tắc single-source (sửa lỗi trùng forbidden): forbidden_claims và CTA rules KHÔNG đặt riêng ở M05 — chúng sống ở lớp prompt (prompt_rules/overlay của M01/M02) và tới M05 qua content-prompt. Tránh hai danh sách forbidden lệch nhau. content/ config của M05 chỉ giữ thứ thuần nội dung: pillars, platform rules, SEO keywords, cadence.

Nếu thiếu Knowledge → M02 báo Missing Knowledge; M05 dừng, KHÔNG bịa.


5. Output
data/projects/<project>/content/{facebook, instagram, threads, blog, website,

                                 ota, email, faq, calendar}/

   <date>_<slug>.md + .json

data/projects/<project>/content/content_manifest.json

data/projects/<project>/content/_archive/

Dạng kép .md (người) + .json (máy/Automation).


6. Các loại Content
6.1 Social (Facebook, Instagram, Threads, TikTok caption)
Output: hook, body, CTA, hashtags, visual note (tham chiếu asset/ image-prompt cần có — M05 KHÔNG tạo ảnh), suggested posting note.
6.2 Blog SEO
Output: SEO title, meta description, slug, outline, article, internal links, FAQ, keywords, search intent.
6.3 Website Copy
Output: hero, about, room description, location, CTA block, FAQ, SEO metadata. Thường bilingual (vi + en).
6.4 OTA Description (Agoda + Google Business + direct — KHÔNG Booking.com giai đoạn này)
Output: short/long description, facilities highlight, location highlight, guest-fit messaging, rules/notes. Align chiến lược kênh: Agoda + đặt trực tiếp; Booking.com để sau.
6.5 Email Draft
Output: subject options, preview text, body, CTA, follow-up variation. KHÔNG gửi thật.
6.6 FAQ
Output: question, short answer, long answer, source knowledge, related CTA. KHÔNG bịa chính sách chưa có.
6.7 Content Calendar (đã định nghĩa input)
Input model: calendar_rules.yaml (cadence: số bài/tuần theo kênh) + content_pillars (nguồn topic) + tháng. Output: date, channel, topic (dẫn xuất từ pillar), pillar, format, status, required asset, CTA. Calendar là công cụ LẬP LỊCH — nó không viết nội dung, chỉ xếp chỗ.
6.8 Campaign — cơ chế một MESSAGE-CORE (mới v1.1)
1 message-core (thông điệp gốc + CTA strategy, sinh một lần từ content-prompt M02)

     ↓ tạo hình theo từng kênh (platform_rules: độ dài, giọng, hashtag)

Facebook / Instagram / Threads ...   → mỗi bản KHÁC câu chữ, CÙNG thông điệp & CTA

Không sinh N lần độc lập (tránh trùng nguyên văn hoặc lệch ngẫu nhiên).


7. Cấu trúc repo (phân cấp rõ)
content_studio/

├── content_engine.py            # ORCHESTRATOR: request → context → build → render → validate

├── content_request.py

├── content_context.py           # nạp config nội dung + gọi M02 lấy content-prompt

├── prompt_bridge.py             # MỚI: gọi Module 02 (adapter) lấy content/SEO prompt

├── campaign_generator.py        # đa kênh từ 1 message-core (đổi tên từ content_generator)

├── content_calendar.py

├── content_validator_bridge.py  # gọi Module 03 (có degradation)

├── content_manifest.py          # MỚI: theo dõi + staleness

├── cli.py

├── builders/                    # per-type: THỰC THI prompt → prose + tạo hình kênh

│   ├── social_builder.py  blog_builder.py  website_builder.py

│   ├── ota_builder.py  email_builder.py  faq_builder.py

├── templates/                   # ĐỊNH HÌNH OUTPUT (section + rule kênh), KHÔNG dựng prompt

│   ├── facebook.yaml ... faq.yaml

├── schemas/

│   ├── content_request.py  content_output.py  social.py  blog.py  website.py  calendar.py

└── renderers/

    ├── markdown_renderer.py  json_renderer.py

config/projects/<project>/content/

├── content_pillars.yaml  tone_of_voice.yaml  platform_rules.yaml

├── seo_keywords.yaml  calendar_rules.yaml

# (forbidden_claims + cta KHÔNG ở đây — single-source tại prompt_rules/overlay của M01/M02)

Phân cấp: content_engine điều phối → builders/ thực thi từng loại → campaign_generator lo đa kênh. Test dùng mock provider (kế thừa shared) — không tốn token.


8. Content Request Model
{

  "project": "venho_hotel",

  "content_type": "facebook_post",

  "topic": "morning at West Lake",

  "target_audience": "Vietnamese leisure guests",

  "content_pillar": "Khám phá Hồ Tây",

  "tone": "warm, clear, trustworthy",

  "length": "medium",

  "target_language": "vi",

  "cta_type": "booking_soft",

  "source_knowledge": [

    { "file": "VENHO_WESTLAKE_DNA.json", "dna_version": "1.0", "hash": "sha256..." },

    { "file": "VENHO_HOTEL_BRAND_DNA.json", "dna_version": "1.0", "hash": "sha256..." }

  ],

  "validation_required": true

}

target_language ∈ {vi, en, bilingual} (chuẩn hóa theo Module 02). source_knowledge là object có version/hash.


9. Content Output Model
{

  "contract_version": "1.0",

  "module": "content_studio",

  "project": "venho_hotel",

  "content_type": "facebook_post",

  "target_language": "vi",

  "generated_at": "ISO",

  "source_knowledge": [

    { "file": "VENHO_WESTLAKE_DNA.json", "dna_version": "1.0", "hash": "sha256..." }

  ],

  "source_prompt": { "file": "...CONTENT_PROMPT_v1.0.json", "prompt_version": "1.0" },

  "generator": { "provider": "claude", "model": "...", "temperature": 0.6 },

  "title": "Một buổi sáng bên Hồ Tây",

  "body": "...",

  "cta": "...",

  "hashtags": ["#venhohotelhanoi", "#hotay", "#hanoi"],

  "visual_note": "cần ảnh phòng lake view buổi sáng (ref: image prompt lake_view_room)",

  "status": "draft",

  "validation": { "required": true, "status": "pending" }

}
9.1 Content Manifest & Staleness (mới v1.1)
content_manifest.json ghi mỗi content: id, type, source_knowledge_hashes, source_prompt_version,

   target_language, generated_at, status.

Staleness (advisory): khi DNA nguồn đổi hash → đánh cờ content cũ = "source_updated"

   (KHÔNG tự xóa/regenerate — nội dung theo ngày có thể vẫn dùng được; người quyết).


10. Quan hệ với các Module
10.1 Knowledge Studio (M01): M05 KHÔNG đọc/sửa DNA trực tiếp cho content facts — DNA facts đến qua content-prompt của M02.

10.2 Prompt Studio (M02): M05 gọi M02 (qua prompt_bridge) để dựng content/SEO prompt, rồi THỰC THI prompt đó. M05 không dựng prompt.

10.3 Validator Studio (M03) — có degradation: M05 gửi draft sang M03 content validator (brand/tone/SEO/forbidden/CTA/hallucination). Nếu content validator của M03 chưa build (M03 xếp ở Phase sau) → bridge trả validation.status = "not_available", draft vẫn lưu, ghi rõ chưa validate. Không chặn tiến độ M05.

10.4 Automation Studio (M04): M04 điều phối Generate → Validate → Save → Notify → (publish sau). M05 không tự publish.


11. CLI
venho content --project venho_hotel --type facebook --topic "morning at West Lake" --lang vi

venho content --project venho_hotel --type blog --keyword "khách sạn gần Hồ Tây" --lang vi

venho content calendar --project venho_hotel --month 2026-08

venho content campaign --project venho_hotel --topic "lake view room" --channels facebook,instagram,threads

Có --lang {vi,en,bilingual}; mặc định lấy từ platform_rules. Test có cờ --mock.


12. Workflow chuẩn (đã sửa nguồn)
ContentRequest

↓

Load content config (pillars, platform rules, tone)

↓

prompt_bridge → Module 02 dựng content/SEO prompt (đã gắn DNA + forbidden + CTA + lang)

↓

Builder THỰC THI prompt → prose (temp>0 có kiểm soát) + tạo hình theo kênh

↓

Tiền lọc forbidden (deterministic) 

↓

Render .md + .json (section cố định từ JSON)

↓

Validator bridge → Module 03 (hoặc not_available)

↓

Save draft + cập nhật manifest


13. Markdown Output chuẩn
Social:

# FACEBOOK POST DRAFT

## META

## SOURCE KNOWLEDGE

## SOURCE PROMPT

## AUDIENCE

## HOOK

## BODY

## CTA

## HASHTAGS

## VISUAL NOTE

## VALIDATION STATUS

Blog:

# BLOG ARTICLE DRAFT

## META

## SOURCE KNOWLEDGE

## SEO INTENT

## KEYWORDS

## TITLE OPTIONS

## META DESCRIPTION

## OUTLINE

## ARTICLE

## FAQ

## INTERNAL LINKS

## CTA

## VALIDATION STATUS


14. Kế hoạch phát triển theo GIAI ĐOẠN
GIAI ĐOẠN 0 — Nền tảng & hợp đồng
Step 0 — Module setup. Cây content_studio/, config/content/, test folder. DoD: import không lỗi; README; nối shared (gồm mock).

Step 1 — Request/Output Schema. schemas/{content_request, content_output}.py. DoD: validate request+output mẫu; có contract_version; source_knowledge dạng {file,version,hash}; target_language enum.

Step 2 — Project Content Config. config/.../content/*.yaml (pillars, tone, platform_rules, seo_keywords, calendar_rules). DoD: load được; fallback khi thiếu; KHÔNG chứa forbidden_claims/cta (single-source ở prompt layer); không hard-code Ven Hồ.
GIAI ĐOẠN 1 — Cầu nối & ngữ cảnh
Step 3 — Prompt Bridge (gọi Module 02). prompt_bridge.py. DoD: gọi M02 dựng content-prompt qua adapter; nhận prompt.json (đã có DNA+forbidden+CTA+lang); thiếu Knowledge → báo Missing, không bịa.

Step 4 — Content Context Loader. content_context.py. DoD: nạp config nội dung + prompt từ bridge cho một FB post; báo missing đúng.
GIAI ĐOẠN 2 — MVP Social
Step 5 — Social Builder. builders/social_builder.py, templates facebook/instagram/threads. DoD: thực thi content-prompt → FB/IG/Threads draft; tạo hình theo kênh (length/hashtag); temp>0 có kiểm soát; tiền lọc forbidden; .md+.json.

Step 6 — Renderer. renderers/{markdown,json}_renderer.py. DoD: section cố định từ JSON; round-trip; AI không tự bịa bố cục.

Step 7 — Validator Bridge (có degradation). content_validator_bridge.py. DoD: gửi draft sang M03; nhận pass/warning/fail; M03 content validator chưa có → not_available, không chặn; ghi status vào output.

Step 8 — MVP Acceptance (Social). ◀ MỐC GIÁ TRỊ ĐẦU TIÊN Test: topic "Morning at West Lake", 3 kênh, nguồn West Lake DNA + Brand DNA (qua prompt M02). DoD: 3 draft đúng tone tiếng Việt; không bịa (source_prompt truy được); CTA hợp; forbidden sạch; validator không fail (hoặc not_available); .md+.json + manifest. ➜ Dừng, review.
GIAI ĐOẠN 3 — Mở rộng loại nội dung
Step 9 — Blog SEO Builder. DoD: title/meta/outline/article/FAQ/CTA; keyword không nhồi; theo target_language. Step 10 — Website Copy Builder. DoD: hero/about/room/location/CTA/SEO metadata; hỗ trợ bilingual. Step 11 — OTA Builder. DoD: short/long/facilities/location/guest-fit; Agoda+Google+direct; không claim quá mức. Step 12 — FAQ Builder. DoD: FAQ từ Knowledge; có source; không bịa chính sách. Step 13 — Email Builder. DoD: subject options/preview/body/CTA; KHÔNG gửi thật.
GIAI ĐOẠN 4 — Đa kênh, lịch & vận hành
Step 14 — Campaign Generator (message-core). campaign_generator.py. DoD: 1 topic → 1 message-core → FB+IG+Threads khác câu chữ, cùng thông điệp & CTA; không lặp nguyên văn. Step 15 — Content Calendar. content_calendar.py, calendar_rules.yaml. DoD: lịch theo tháng từ cadence + pillar; gắn channel/asset/CTA; .md+.json. Step 16 — Manifest + CLI. content_manifest.py, cli.py. DoD: manifest ghi source hash + staleness (source_updated); venho content + calendar + campaign chạy; --lang, --mock; lưu đúng folder.


15. Definition of Done — Module 05
- Sinh được social, blog SEO, website, OTA, FAQ, email, calendar; đa kênh campaign.

- MỌI nội dung đi QUA content-prompt của M02 (không dựng prompt lại, không bịa DNA).

- Output .md+.json; contract_version; source_knowledge {file,version,hash}; source_prompt; validation status.

- Forbidden phòng (qua prompt) + tiền lọc (M05) + phát hiện (M03).

- target_language chuẩn hóa; hỗ trợ bilingual; OTA = Agoda+Google+direct.

- content_manifest + staleness; test bằng mock; project-agnostic; KHÔNG tự publish.


16. Rủi ro chính
1. Content bịa            → luôn qua prompt M02 (có DNA); Missing Knowledge → dừng; validator M03

2. Trùng giữa các kênh    → campaign một message-core + platform rules; không sinh N độc lập

3. Trùng vai với M02      → M02 dựng prompt, M05 thực thi; M05 không dựng prompt lại

4. SEO sáo rỗng           → keyword+intent rõ; FAQ từ Knowledge; không nhồi

5. CTA quá mạnh           → CTA rules ở prompt layer; cta_type soft/direct/informational

6. Forbidden lọt lưới     → phòng (prompt) + tiền lọc (M05) + phát hiện (M03)

7. Nội dung lỗi thời      → manifest + cờ source_updated (advisory)

8. Hard-code Ven Hồ       → config project; core agnostic

9. Publish nhầm           → chỉ draft; publish thuộc M04; mặc định status=draft

10. Chờ M03 mới chạy được → bridge degradation: not_available, không chặn


17. Thứ tự ưu tiên thực tế
Nền tảng:  Schema → Content Config → Prompt Bridge → Context Loader

MVP:       Social Builder → Renderer → Validator Bridge → Acceptance (Social)

Mở rộng:   Blog → Website → OTA → FAQ → Email

Đa kênh:   Campaign → Calendar → Manifest/CLI

Bắt đầu bằng Social — gần nhất nhu cầu hiện tại của Ven Hồ (Linh An làm mặt social).


18. Kết luận
Content Studio là Knowledge-based Content Production Engine — nhưng trung thực về ranh giới: nó không dựng prompt (M02 làm), không tạo ảnh (công cụ ngoài), không validate điểm số (M03 làm), không publish (M04/ người làm). Nó THỰC THI prompt tri thức thành nội dung thật.

Điểm cần giữ tuyệt đối:

M05 THỰC THI content-prompt của M02; không dựng prompt lại, không bịa DNA.

Forbidden phòng ngừa trong sinh, không chỉ phát hiện khi validate.

Đây là module duy nhất AI được sáng tạo (temp>0) — nhưng nguồn & cấu trúc vẫn tất định.

source_knowledge có version/hash; manifest theo dõi staleness.

Chỉ tạo draft; publish thuộc module/thao tác khác.

Ven Hồ là project đầu tiên, không phải lõi.

19. Trạng thái triển khai — 2026-07-09
STATUS: COMPLETE theo phạm vi Module 05 v1.1, với prose generator hiện ở chế độ deterministic/mock để test không tốn token và giữ contract ổn định.

ĐÃ HOÀN THÀNH:

- Step 0 — Module setup: content_studio/ + README + package discovery trong pyproject.

- Step 1 — Request/Output Schema: ContentRequest, ContentOutput, source_knowledge, source_prompt, validation, payload theo loại nội dung.

- Step 2 — Project Content Config: config/projects/venho_hotel/content/{content_pillars,tone_of_voice,platform_rules,seo_keywords,calendar_rules}.yaml; không chứa forbidden_claims/cta_rules.

- Step 3 — Prompt Bridge: content_studio/prompt_bridge.py gọi Module 02 build_content_prompt, lưu prompt .md+.json.

- Step 4 — Content Context Loader: content_studio/content_context.py nạp config + prompt từ bridge, báo missing rõ.

- Step 5 — Social Builder: Facebook/Instagram/Threads/TikTok caption qua builders/social_builder.py; có prefilter forbidden.

- Step 6 — Renderer: renderers/markdown_renderer.py và json_renderer.py; markdown sinh từ JSON/schema, không để AI tự định bố cục.

- Step 7 — Validator Bridge: content_validator_bridge.py gọi M03 validate_content; có degradation not_available nếu validator không có; ghi report khi có.

- Step 8 — MVP Social Acceptance: đã generate topic "Morning at West Lake"; output .md+.json + manifest; validator pass.

- Step 9 — Blog SEO Builder: title/meta/slug/keywords/outline/article/FAQ/internal links/CTA.

- Step 10 — Website Copy Builder: hero/about/room/location/CTA/SEO metadata; hỗ trợ bilingual.

- Step 11 — OTA Builder: Agoda + Google Business + direct; short/long/facilities/location/guest-fit/rules notes.

- Step 12 — FAQ Builder: FAQ có source_prompt/source_knowledge; không tự bịa chính sách.

- Step 13 — Email Builder: subject options/preview/body/CTA/follow-up; không gửi thật.

- Step 14 — Campaign Generator: campaign_generator.py tạo 1 message-core rồi tạo hình theo FB/IG/Threads.

- Step 15 — Content Calendar: content_calendar.py sinh lịch theo month từ cadence + pillars; .md+.json.

- Step 16 — Manifest + CLI: content_manifest.py ghi manifest + staleness source_updated; cli.py có generate/campaign/calendar.

ACCEPTANCE ĐÃ CHẠY:

- Social: data/projects/venho_hotel/content/facebook/2026-07-09_morning-at-west-lake.md — validation pass.

- Blog: data/projects/venho_hotel/content/blog/2026-07-09_morning-at-west-lake.md — validation pass.

- Website: data/projects/venho_hotel/content/website/2026-07-09_ven-ho-website-copy.md — validation pass.

- OTA: data/projects/venho_hotel/content/ota/2026-07-09_ven-ho-ota-description.md — validation pass.

- FAQ: data/projects/venho_hotel/content/faq/2026-07-09_ven-ho-faq.md — validation pass.

- Email: data/projects/venho_hotel/content/email/2026-07-09_morning-at-west-lake-email.md — validation pass.

- Campaign: topic "Lake view room" -> facebook/instagram/threads — validation pass.

- Calendar: data/projects/venho_hotel/content/calendar/2026-08_calendar.md — 32 entries.

TEST STATUS:

- python3 -m pytest tests/test_content_studio.py tests/test_content_prompt_builder.py tests/test_prompt_contract_schema.py tests/test_validator_studio.py

- Result: 41 passed.

LƯU Ý PHẠM VI:

- Content Studio đã hoàn thành workflow/module contract end-to-end, nhưng câu chữ prose hiện dùng deterministic/mock generator. Bước production tiếp theo là thay generator_fn bằng provider AI thật (OpenAI/Claude) trong cùng contract, giữ nguyên prompt bridge, prefilter, renderer, validator, manifest và CLI.

END OF DOCUMENT v1.1 (QC Consolidated)
