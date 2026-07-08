VENHO AI STUDIO
DNA Studio / AI Vision Engine — Master Plan v2.4 (Complete)
Workspace mẹ: THE WEST LAKE LIVING Repo: venho-ai-studio Module: knowledge_studio/vision AI Engine: OpenAI + Claude Mục tiêu: Biến ảnh thật thành file .md + .json để AI engine sử dụng lại mà không cần nhìn lại ảnh gốc.


0. Thay đổi của v2.4 so với v2.3 Final
v2.4 giữ nguyên toàn bộ kiến trúc v2.3 Final (2 Mode, Pass 2 lai coverage+consistency, fixed key + type, subject resolver, dna_manifest, contract_version, mock provider) và bổ sung 6 điểm rút ra từ đối chiếu với thực tế Ven Hồ Hotel:

Luật ngôn ngữ value (§5.1): mọi value trong observation/DNA bắt buộc tiếng Anh — chặn lỗi tất định ẩn khi so khớp chuỗi.
Một subject = một hạng phòng (§2.1): chặn nhiễm DNA khi trộn nhiều hạng phòng vào một subject.
FORBIDDEN là chính sách (§4.3): nguồn chính từ file curated do người khai báo, không phải từ quan sát ảnh.
Curated Overlay (§5.2): file overrides.yaml do người viết, merge lúc render, sống sót qua mọi lần tái sinh DNA.
ALLOWED_IMPERFECTIONS (§13, §14): hạng mục riêng cho nguyên tắc Authenticity — "đáng tin hơn đẹp".
Cổng QC cho face subject (Step 13): chỉ ảnh đạt ngưỡng QC (rubric 07F) mới được vào tập nguồn face DNA — chặn vòng lặp tự nhiễm.

Kèm theo: renderer phụ _COMPACT.md (tùy chọn) cho nhu cầu dán DNA hằng ngày vào Flow/ChatGPT.


1. Tư duy cốt lõi
VENHO AI Studio không chỉ phục vụ Ven Hồ Hotel. Nó là một engine tổng quát:

Ảnh thật

↓

AI Vision

↓

Observation / DNA

↓

Markdown + JSON

↓

AI Engine đọc lại dưới dạng text

Triết lý:

Ảnh chỉ nên được AI nhìn một lần.

Sau đó hệ thống dùng file text có cấu trúc để tái sử dụng lâu dài.

Điều này giúp: tiết kiệm token, dễ version bằng Git, dễ diff, dễ đọc/sửa tay, và dễ dùng lại cho Prompt / Visual / Validator / Content Studio.

Nguyên tắc project-agnostic: nếu thêm project mới mà phải sửa lõi engine, kiến trúc đó sai.

Nguyên tắc tri thức kép: DNA máy sinh từ ảnh + Overlay người tuyển chọn = tri thức hoàn chỉnh. Máy không được ghi đè tri thức người; người không phải sửa lại thứ máy làm đúng.


2. Hai chế độ vận hành
Mode A — General Image to Markdown
Dùng cho ảnh bất kỳ. Input: 1 ảnh hoặc nhiều ảnh không cùng chủ thể. Output: mỗi ảnh → 1 file .md + 1 file .json.

Mode A không sinh DNA. Mode A chỉ sinh observation có cấu trúc.

cafe_001.jpg → cafe_001.md + cafe_001.json

street_001.jpg → street_001.md + street_001.json

Mục tiêu: AI khác đọc file .md/.json hiểu được ảnh mà không cần xem ảnh gốc.
Mode B — Project DNA Builder
Dùng cho nhiều ảnh cùng một chủ thể. Input: nhiều ảnh cùng một phòng / nhân vật / sản phẩm / địa điểm. Output: 1 DNA .md + 1 DNA .json.

Chỉ Mode B mới được dùng chữ DNA.

Nguyên tắc bắt buộc:

1 ảnh = observation

Nhiều ảnh cùng chủ thể = DNA

Chọn Mode B nhưng chỉ có 1 ảnh → cảnh báo: "DNA cần nhiều ảnh cùng chủ thể. Nên dùng Mode A."
2.1 Luật đồng nhất chủ thể — MỘT SUBJECT = MỘT HẠNG
Quy tắc mới (v2.4): "cùng chủ thể" phải hiểu chặt:

MỘT subject = MỘT hạng phòng / MỘT nhân vật / MỘT sản phẩm cụ thể.

KHÔNG trộn hạng.

Ví dụ đúng cho Ven Hồ:

lake_view_room   → data/projects/venho_hotel/media/lake_view_room/

standard_room    → data/projects/venho_hotel/media/standard_room/

lobby            → data/projects/venho_hotel/media/lobby/

Ví dụ SAI:

rooms/  (chứa lẫn lake-view và standard)

→ coverage/consistency bị pha loãng

→ cửa sổ, palette khác nhau giữa các hạng phòng

→ gần như mọi feature rớt xuống VARIABLE

→ DNA vô dụng

CLI khi chạy Mode B phải hiển thị nhắc: "Folder này chỉ chứa MỘT hạng/chủ thể duy nhất?"


3. Kiến trúc 2 Pass
Pass 1 — Observe (Mode A và B)
Ảnh → Observation JSON → (Mode A) Renderer → Markdown

Quy tắc: chỉ mô tả cái nhìn thấy; không suy diễn; không viết prompt; không tạo ảnh; không khen đẹp/xấu; không thêm cảm xúc. Output bắt buộc là JSON đúng schema; Markdown chỉ render từ JSON.
Pass 2 — Consolidate (chỉ Mode B)
Gồm hai phần: 2A code thuần (quyết cấu trúc) và 2B LLM (chỉ gọt câu chữ).


4. Pass 2 chi tiết — TRỌNG TÂM tất định
4.1 Pass 2A — Deterministic Consolidation (CODE THUẦN, không gọi AI)
Pass 2A dùng HAI tín hiệu cho mỗi fixed key:

coverage    = số ảnh thấy key / total_images

consistency = số ảnh có value phổ biến nhất / số ảnh thấy key

Để đo consistency tất định, value so khớp theo kiểu key (§5):

key enum: so khớp chính xác giá trị enum.
key free: chuẩn hóa (lowercase, trim, bỏ khoảng trắng thừa) rồi so khớp; value khác chữ coi như khác (bảo thủ — đẩy về VARIABLE khi nghi ngờ).

Phân loại:

coverage >= consolidation_threshold  AND  consistency >= consistency_threshold

    → INVARIANT     (xuất hiện nhiều VÀ value ổn định)

coverage >= consolidation_threshold  AND  consistency <  consistency_threshold

    → VARIABLE      (xuất hiện nhiều NHƯNG value thay đổi)

coverage <  weak_threshold

    → WEAK FEATURE  (quá ít ảnh để kết luận)

còn lại (giữa weak_threshold và consolidation_threshold)

    → VARIABLE

Ngưỡng mặc định (trong settings.yaml):

consolidation_threshold = 0.6

consistency_threshold   = 0.7

weak_threshold          = 0.3

Ví dụ vì sao cần consistency:

window_frame : 12/12 ảnh, value luôn "black aluminum"

    coverage 1.0, consistency 1.0 → INVARIANT  ✅

lighting : 12/12 ảnh, value mỗi ảnh một khác

    coverage 1.0, consistency thấp → VARIABLE  ✅
4.2 Pass 2B — Canonical Wording (LLM, GIỚI HẠN, MỘT lời gọi gộp)
Chỉ dùng AI để gọt câu chữ. Đầu vào là kết quả 2A đã cố định cấu trúc.

Một lời gọi LLM duy nhất, nhận TẤT CẢ cluster value cần chuẩn hóa,

trả về câu canonical cho từng key. temperature = 0.

AI không được: thêm key, xóa key, đổi INVARIANT↔VARIABLE, đổi evidence_count, đổi kết quả threshold. Output sai schema → reject, dùng value thô từ 2A.
4.3 Nguồn của FORBIDDEN — CHÍNH SÁCH, không phải quan sát (mới v2.4)
Nhận thức quan trọng: ảnh chụp thật của Ven Hồ không bao giờ chứa thứ cần cấm (Dubai-style luxury, floor-to-ceiling glass wall) — vì khách sạn không có chúng. Model không thể quan sát cái-không-tồn-tại.

FORBIDDEN có HAI nguồn, thứ tự ưu tiên:

1. CURATED (nguồn chính)  : forbidden khai báo trong overrides.yaml (§5.2)

                            — đến từ tri thức người (Visual DNA v2.7, quy tắc thương hiệu)

2. OBSERVED (bổ sung)     : union dedup các forbidden_hints hiếm hoi model nêu được

Render: gộp cả hai, đánh dấu nguồn từng rule: [curated] / [observed].
4.4 Các trường còn lại — tất định
INVARIANT item        : key, value (phổ biến nhất), evidence_count, coverage, consistency

VARIABLE item         : key, value_range = tập value phân biệt đã chuẩn hóa

WEAK FEATURE          : key, evidence_count (gợi ý chụp thêm)

FUTURE CAPTURE NOTES  : sinh từ WEAK FEATURE — "cần thêm ảnh thể hiện <key>"

ALLOWED_IMPERFECTIONS : từ key allowed_imperfection (quan sát) + overlay (curated) — §13


5. Fixed Key System
Mode B chỉ chính xác nếu Pass 1 dùng cùng bộ key.

Quy tắc:

Mỗi schema khai báo một tập AGGREGATION KEY cố định.

Mỗi key có type: enum | free.

  - enum: kèm danh sách value hợp lệ (màu, vật liệu, kiểu cấu trúc...).

  - free: text mô tả tự do, chuẩn hóa khi so khớp.

Pass 1 chỉ điền value vào các key đã khai báo.

Không thấy key → value = "not_visible", confidence = 0

  (vẫn tính total_images nhưng không tính vào evidence_count của key đó).

Tách bạch:

AGGREGATION KEYS → dùng để đếm và phân loại trong Pass 2A.

FREE FIELDS      → notable_features, uncertainty:

                   chỉ phục vụ mô tả Mode A, KHÔNG dùng làm đơn vị đếm.

Ưu tiên khai báo enum cho key quyết định identity (màu khung, vật liệu sàn, kiểu cửa sổ). Key khó liệt kê hết thì để free.
5.1 Luật ngôn ngữ value (mới v2.4 — chặn lỗi tất định ẩn)
Pass 2A so khớp value bằng chuỗi. Nếu Pass 1 lúc trả "khung nhôm đen", lúc trả "black aluminum frame" — cùng một sự thật — consistency tính ra HAI value khác nhau → feature đáng lẽ INVARIANT bị đẩy nhầm thành VARIABLE.

QUY TẮC CỨNG:

- Mọi VALUE trong observation và DNA: TIẾNG ANH.

- Ghi rõ trong mọi prompt observe: "Return all values in English."

- Enum list trong schema: định nghĩa bằng tiếng Anh.

- Lý do thêm: downstream (Flow, GPT Image, prompt engine) tiêu thụ tiếng Anh.

- Tài liệu, giao diện CLI, thông báo: vẫn tiếng Việt.
5.2 Curated Overlay — tri thức người sống sót qua tái sinh (mới v2.4)
Vấn đề: nếu người sửa tay file DNA rồi chạy lại Mode B → bản sửa tay bị ghi đè mất. Trong khi Ven Hồ đã có tài sản tri thức viết tay (Visual DNA v2.7, character bible Linh An).

Giải pháp: mỗi subject có một file overlay do NGƯỜI viết, máy không bao giờ đụng:

config/projects/<project>/subjects/<subject>.overrides.yaml

Nội dung overlay:

# Ví dụ: lake_view_room.overrides.yaml

forbidden:                      # nguồn CHÍNH của FORBIDDEN (§4.3)

  - "no floor-to-ceiling glass wall"

  - "no Dubai-style luxury interior"

  - "no generic resort look"

allowed_imperfections:          # nguyên tắc Authenticity (§13)

  - "minor scuff marks on skirting boards acceptable"

  - "slight curtain wrinkles acceptable"

wording_overrides:              # sửa câu chữ một invariant cụ thể

  window_frame: "matte black aluminum window frame, thin profile"

notes:

  - "Palette chuẩn theo Visual DNA v2.7 §12"

Quy tắc merge (lúc render, không phải lúc consolidate):

1. Máy sinh DNA từ ảnh (Pass 2A + 2B)  → phần machine-generated

2. Đọc overrides.yaml                   → phần curated

3. Render = machine-generated ⊕ curated

   - forbidden:   curated đứng trước, observed sau, đánh dấu nguồn

   - wording_overrides: thay value máy sinh bằng value curated (key phải tồn tại)

   - allowed_imperfections + notes: thêm vào section tương ứng

4. Tái sinh DNA → chỉ phần machine-generated thay đổi; overlay sống sót.

Overlay được version bằng Git như code. Đây là cách hợp nhất tri thức cũ (Visual DNA v2.7) vào hệ mới mà không bị nuốt.


6. Subject Resolution
Khi Mode B cần schema cho subject, tra theo thứ tự:

1. config/projects/<project>/subjects/<subject>.yaml

2. config/projects/_shared_subjects/<subject>.yaml

3. config/universal_schema.yaml

Overlay resolution (mới v2.4): chỉ tra MỘT nơi — config/projects/<project>/subjects/<subject>.overrides.yaml. Overlay là đặc thù project, không có overlay dùng chung.

Gom logic vào: knowledge_studio/vision/subject_resolver.py Nhiệm vụ: nhận project + subject; trả schema path + overlay path (nếu có); ghi rõ nguồn đang dùng; báo lỗi rõ nếu schema không hợp lệ.


7. Cấu trúc repo
venho-ai-studio/

│

├── config/

│   ├── settings.yaml

│   ├── universal_schema.yaml

│   └── projects/

│       ├── venho_hotel/

│       │   └── subjects/

│       │       ├── lake_view_room.yaml

│       │       ├── lake_view_room.overrides.yaml

│       │       ├── standard_room.yaml

│       │       ├── lobby.yaml

│       │       ├── westlake.yaml

│       │       ├── linh_an.yaml

│       │       └── linh_an.overrides.yaml

│       └── _shared_subjects/

│           ├── room.yaml

│           ├── product.yaml

│           └── location.yaml

│

├── shared/

│   ├── vision/

│   │   ├── client.py

│   │   ├── providers/

│   │   │   ├── openai_vision.py

│   │   │   ├── claude_vision.py

│   │   │   └── mock_vision.py

│   │   ├── image_loader.py

│   │   ├── structured.py

│   │   └── errors.py

│   ├── io/

│   │   ├── markdown_writer.py

│   │   └── json_store.py

│   └── logging.py

│

├── knowledge_studio/

│   └── vision/

│       ├── schemas/

│       │   ├── base.py

│       │   ├── universal.py

│       │   ├── dna.py

│       │   └── face.py

│       ├── prompts/

│       │   ├── observe_universal.md

│       │   ├── observe_face.md

│       │   ├── consolidate_values.md

│       │   └── classify.md

│       ├── pass0_classify.py

│       ├── pass1_observe.py

│       ├── pass2_consolidate.py

│       ├── overlay_merge.py            # mới v2.4 — merge overrides.yaml lúc render

│       ├── schema_bootstrap.py

│       ├── subject_resolver.py

│       ├── pipeline.py

│       ├── cli.py

│       └── renderers/

│           ├── single_md.py

│           ├── dna_md.py

│           └── dna_compact_md.py       # mới v2.4 — bản _COMPACT để dán hằng ngày

│

├── data/                                # .gitignore

│   └── projects/

│       ├── _inbox/

│       │   ├── media/

│       │   └── output/

│       └── venho_hotel/

│           ├── media/

│           │   ├── lake_view_room/

│           │   ├── standard_room/

│           │   ├── lobby/

│           │   ├── westlake/

│           │   └── linh_an/            # CHỈ ảnh đã qua cổng QC 07F (Step 13)

│           ├── observations/

│           └── knowledge/

│               ├── _archive/

│               └── dna_manifest.json

│

├── tests/

│   ├── fixtures/

│   └── ...

│

├── docs/

│   ├── dna_studio_master_plan_v2_4.md

│   ├── how_to_run_mode_a.md

│   └── how_to_run_mode_b.md

│

├── .env

├── .gitignore

├── pyproject.toml

└── README.md


8. settings.yaml
provider: claude

models:

  claude: "<claude_vision_model>"     # điền model vision hiện hành

  openai: "<openai_vision_model>"     # điền model vision hiện hành

temperature: 0

concurrency: 4

consolidation_threshold: 0.6

consistency_threshold: 0.7

weak_threshold: 0.3

max_image_px: 1568

retry:

  max_attempts: 2

  backoff_seconds: 2

cache_dir: data

grounding: false

output:

  markdown: true

  json: true

  compact: true                # mới v2.4 — sinh thêm bản _COMPACT.md

  archive_old_dna: true

mode_a:

  default_input: data/projects/_inbox/media

  default_output: data/projects/_inbox/output

mode_b:

  default_project: venho_hotel

Nguyên tắc: mọi threshold và giới hạn nằm trong settings.yaml; không hard-code trong code.


9. Xử lý lỗi batch
Quy tắc: một ảnh lỗi không được giết cả batch.

Loại lỗi: file ảnh hỏng, không đọc được file, API timeout, rate limit, JSON sai schema, provider error, output path lỗi.

Cách xử lý:

Retry theo settings.retry

Vẫn lỗi → đưa vào failed list

Tiếp tục ảnh còn lại

Cuối run in report

Run report:

Total images / Processed / Cache hits / Failed / Failed files / Output path

Ảnh failed chạy lại riêng được mà không đụng ảnh đã xong.


10. Concurrency
Pass 1  → song song, giới hạn settings.concurrency (mỗi ảnh độc lập)

Pass 2A → tuần tự (cần đọc toàn bộ observation)

Pass 2B → một lời gọi gộp, có kiểm soát

Rate limit → backoff → retry → vẫn lỗi thì failed


11. Cache System
Cache key:

image_hash + schema_version + prompt_version

Ý nghĩa:

Đổi ảnh → chỉ xử lý ảnh mới

Đổi prompt → cache invalid

Đổi schema → cache invalid

Đổi Pass 2 logic → KHÔNG gọi vision lại (chạy lại 2A/2B từ cache)

Đổi overrides.yaml → KHÔNG gọi vision lại, KHÔNG chạy lại Pass 2 (chỉ render lại)

Observation lưu thêm provider + model để audit và so sánh chất lượng model.


12. Output Mode A
Markdown section cố định:

# IMAGE OBSERVATION

## META

## SUBJECT

## SCENE

## COMPOSITION

## LIGHTING

## PALETTE

## MATERIALS

## NOTABLE DETAILS

## AI-USABLE NOTES

## UNCERTAINTY

Observation JSON:

{

  "contract_version": "1.0",

  "mode": "A",

  "image_hash": "sha256...",

  "image_file": "image_001.jpg",

  "schema_id": "universal",

  "schema_version": "1.0",

  "prompt_version": "1.0",

  "provider": "openai",

  "model": "model_name",

  "observed_at": "ISO datetime",

  "features": [

    {

      "key": "scene_type",

      "type": "enum",

      "value": "hotel room interior",

      "category": "scene",

      "confidence": 0.92

    }

  ],

  "notable_features": ["free-form, English, không dùng để đếm"],

  "uncertainty": ["floor material unclear due to low light in right corner"]

}


13. Output Mode B
Markdown section cố định (thêm ALLOWED IMPERFECTIONS — v2.4):

# PROJECT SUBJECT DNA

## META

## INVARIANT

## VARIABLE

## ALLOWED IMPERFECTIONS

## FORBIDDEN

## EVIDENCE

## WEAK FEATURES

## FUTURE CAPTURE NOTES

## CURATOR NOTES

Ý nghĩa các section:

INVARIANT             — đặc điểm bất biến, luôn phải giữ

VARIABLE              — đặc điểm biến thiên cho phép

ALLOWED IMPERFECTIONS — lỗi tự nhiên ĐƯỢC PHÉP và NÊN CÓ (Authenticity:

                        "phòng đáng tin nhất, không phải phòng đẹp nhất")

FORBIDDEN             — điều cấm; nguồn [curated] trước, [observed] sau

EVIDENCE              — số ảnh xác nhận từng feature

WEAK FEATURES         — feature ít ảnh chứng minh

FUTURE CAPTURE NOTES  — cần chụp thêm gì để củng cố DNA

CURATOR NOTES         — ghi chú người tuyển chọn (từ overlay)

DNA JSON ("hợp đồng" cho downstream):

{

  "contract_version": "1.1",

  "mode": "B",

  "project": "venho_hotel",

  "subject": "lake_view_room",

  "dna_version": "1.0",

  "generated_at": "ISO datetime",

  "source_images": ["hash1", "hash2"],

  "schema_id": "lake_view_room",

  "schema_version": "1.0",

  "prompt_version": "1.0",

  "provider": "claude",

  "model": "model_name",

  "invariant": [

    {

      "key": "window_frame",

      "value": "matte black aluminum window frame, thin profile",

      "value_source": "curated",

      "evidence_count": 12,

      "coverage": 1.0,

      "consistency": 1.0,

      "confidence": 0.95

    }

  ],

  "variable": [

    {

      "key": "lighting",

      "value_range": ["morning daylight", "indoor warm light", "overcast"]

    }

  ],

  "allowed_imperfections": [

    { "value": "minor scuff marks on skirting boards", "source": "curated" },

    { "value": "slight wear on wooden floor near bed", "source": "observed" }

  ],

  "forbidden": [

    { "rule": "no floor-to-ceiling glass wall", "source": "curated" },

    { "rule": "no Dubai-style luxury interior", "source": "curated" }

  ],

  "evidence": {

    "total_images": 12,

    "weak_features": [

      { "key": "decorative_vase", "evidence_count": 1 }

    ]

  },

  "future_capture_notes": [

    "cần thêm ảnh thể hiện decorative_vase để xác nhận invariant"

  ],

  "curator_notes": [

    "Palette chuẩn theo Visual DNA v2.7 §12"

  ]

}

Ghi chú contract: v2.4 nâng contract_version lên 1.1 vì shape thêm allowed_imperfections, curator_notes, source fields. Downstream đọc theo contract_version; đổi shape → bump, không phá ngầm.

Universal schema bổ sung key allowed_imperfection (type free) vào aggregation keys để Pass 1 quan sát được dấu vết sử dụng thật.
13.1 Bản Compact (tùy chọn, bật qua settings.output.compact)
Mục đích: dán hằng ngày vào Flow / ChatGPT — đúng mục tiêu tiết kiệm context ban đầu.

<SUBJECT>_DNA_COMPACT.md gồm CHỈ:

  INVARIANT (key + value)

  ALLOWED IMPERFECTIONS

  FORBIDDEN

Bỏ: META chi tiết, EVIDENCE, WEAK, FUTURE CAPTURE, CURATOR NOTES.

Bản đầy đủ để lưu trữ và audit; bản compact để sản xuất hằng ngày.


14. DNA Regeneration Policy
Khi chạy lại Mode B:

1. Tập ảnh không đổi (cùng hash)  → no change, không bump version

2. Tập ảnh thay đổi:

     archive DNA cũ → bump dna_version → sinh DNA mới

3. Archive: data/projects/<project>/knowledge/_archive/

4. Overlay (overrides.yaml) KHÔNG BAO GIỜ bị ghi đè bởi tái sinh.

   Sửa overlay → chỉ render lại, không bump dna_version

   (bump manifest.render_revision nếu cần theo dõi).

dna_manifest.json cho mỗi subject: current_version, source_hashes, generated_at, schema_version, prompt_version, provider/model, overlay_applied (true/false).


15. Mock Provider
Bắt buộc. Lý do: test không tốn tiền, không cần mạng, CI/CD chạy được, Claude Code phát triển không gọi API thật, kiểm thử hành vi tất định. Mock provider phải trả output đúng schema.


16. Tech Stack
Language: Python 3.11+

Schema: Pydantic v2

CLI: Typer

Config: PyYAML

AI SDK: OpenAI + Anthropic

Image: Pillow

Hash: hashlib sha256

Concurrency: asyncio hoặc concurrent.futures

Test: pytest (+ mock provider)

Storage: local files

Database: chưa cần


17. Trải nghiệm người dùng
$ venho vision

> Bạn muốn chạy chế độ nào?

  [A] Mô tả ảnh bất kỳ thành .md

  [B] Tạo DNA từ nhiều ảnh cùng chủ thể

> Chọn (A/B):

Chọn A → hỏi đường dẫn → Pass 1 → mỗi ảnh thành .md + .json trong _inbox/output/. Chọn B → hỏi project / subject / folder → xác nhận "folder chỉ chứa MỘT hạng/chủ thể?" → (nếu chưa có schema, hỏi bootstrap; nếu <2 ảnh, cảnh báo) → Pass 1 → 2A → 2B → merge overlay → DNA trong <project>/knowledge/.

Flag tự động hóa:

venho vision --mode a --input data/projects/_inbox/media

venho vision --mode b --project venho_hotel --subject lake_view_room --input <folder>

venho vision --all --project venho_hotel

venho vision --mode a --classify


18. Roadmap thực thi
Mỗi step giao riêng cho Claude Code. KHÔNG nhảy step. Step sau chỉ bắt đầu khi DoD xanh.
Step 0 — Khởi tạo repo
Tạo: pyproject.toml, .gitignore, .env.example, README.md, config/settings.yaml (đủ field §8), shared/logging.py, tests/, folder structure. DoD: pip install -e . chạy; import module không lỗi; data/ trong .gitignore; settings.yaml đủ field (gồm consistency_threshold, output.compact).
Step 1 — Shared Vision Client + Error Layer
Tạo: shared/vision/{client, structured, image_loader, errors}.py; providers/{openai_vision, claude_vision, mock_vision}.py. DoD: 1 ảnh + schema → dict đúng schema; đổi provider giữ cấu trúc; temperature=0; grounding=false; mock_vision chạy không cần mạng; JSON lỗi → retry; observation lưu provider+model.
Step 2 — Universal Schema (fixed key + type + English values)
Tạo: schemas/{base, universal, dna}.py; config/universal_schema.yaml. Aggregation keys tối thiểu: subject, scene, composition, lighting, palette, materials, mood, allowed_imperfection (mỗi key có type enum|free). Free fields: notable_features, uncertainty. DoD: Pydantic validate object mẫu; mỗi aggregation key có type; enum kèm danh sách value tiếng Anh; free fields tách khỏi aggregation keys; DNA schema có contract_version 1.1, allowed_imperfections, curator_notes, source fields.
Step 3 — Pass 1 Observe
Tạo: prompts/observe_universal.md; pass1_observe.py. Prompt bắt buộc chứa: "Return all values in English." DoD: 3 ảnh → 3 observation JSON; value tiếng Anh; chạy lại = cache hit; đổi prompt_version = cache invalid; chỉ điền aggregation key; not_visible cho key không thấy; concurrency hoạt động; một ảnh lỗi không giết batch.
Step 4 — Mode A Renderer
Tạo: renderers/single_md.py; shared/io/{markdown_writer, json_store}.py. DoD: mỗi observation → .md + .json; section §12 cố định; json round-trip; chống trùng tên file (nối hash ngắn khi trùng).
Step 5 — CLI chọn A/B + subject resolver
Tạo: pipeline.py; cli.py; subject_resolver.py. DoD: venho vision hiện menu A/B; --mode a/b bỏ qua hỏi; B + <2 ảnh cảnh báo; B hiện xác nhận "một hạng/chủ thể duy nhất"; subject resolution (§6) hoạt động, trả cả overlay path, ghi rõ nguồn schema.
Step 6 — MVP Mode A  ◀── MỐC GIÁ TRỊ ĐẦU TIÊN
Test: 10–20 ảnh chung chung (không phải Ven Hồ). DoD: mỗi ảnh ra .md đúng nội dung; AI engine đọc hiểu không cần ảnh gốc; chạy lại không tốn token; cuối run có report. ➜ Dừng, review trước khi làm tiếp.
Step 7 — Pass 2 Consolidate (2A coverage+consistency, 2B wording)
Tạo: pass2_consolidate.py; prompts/consolidate_values.md. DoD: 2A tính coverage VÀ consistency; phân loại đúng theo §4 (test riêng case "key xuất hiện nhiều nhưng value đổi → VARIABLE"); evidence_count đúng; weak_features đúng; forbidden observed = union dedup forbidden_hints; 2B không đổi cấu trúc 2A; chạy hai lần ra invariant/variable GIỐNG NHAU.
Step 8 — Mode B Renderer + Overlay Merge + Compact
Tạo: renderers/dna_md.py; renderers/dna_compact_md.py; overlay_merge.py. DoD: sinh _DNA.md + .json; section §13 cố định (có ALLOWED IMPERFECTIONS, CURATOR NOTES); contract_version 1.1; json round-trip; overlay merge đúng (forbidden curated trước, wording_overrides thay value, source được đánh dấu); sửa overrides.yaml → render lại không gọi vision; bản _COMPACT.md sinh đúng khi bật settings.
Step 9 — Project Layer + DNA Regeneration
Cập nhật: pipeline.py, cli.py; data/projects/, config/projects/, _archive/, dna_manifest.json. DoD: venho_hotel chạy được; thêm project thứ hai KHÔNG sửa core; chạy lại có archive + bump version; ảnh không đổi → no change; overlay sống sót qua tái sinh; manifest cập nhật đúng (gồm overlay_applied).
Step 10 — MVP Mode B với Ven Hồ Hotel
Test: 10–20 ảnh MỘT hạng phòng thật (vd lake_view_room), kèm overrides.yaml viết từ Visual DNA v2.7. DoD: DNA đúng tầng; người thật đọc thấy đúng phòng; cache hoạt động; evidence_count hợp lý; lighting nằm ở VARIABLE; FORBIDDEN chứa rule curated từ Visual DNA v2.7; ALLOWED IMPERFECTIONS xuất hiện; bản compact dán được vào Flow/ChatGPT.
Step 11 — Schema Bootstrap
Tạo: schema_bootstrap.py. DoD: vài ảnh mẫu → YAML fixed key (kèm type enum|free, value tiếng Anh) hợp lệ; người dùng duyệt; YAML dùng được cho Pass 1.
Step 12 — Auto Classify (tùy chọn)
Tạo: pass0_classify.py; prompts/classify.md. DoD: folder ảnh hỗn hợp phân nhóm tương đối đúng; bật/tắt bằng --classify.
Step 13 — Face Subject / Linh An (có cổng QC — mới v2.4)
Tạo: schemas/face.py; prompts/observe_face.md.

Quy tắc identity:

Tách invariant identity khỏi variable appearance.

Grounding/web search LUÔN tắt.

Mỗi nhân vật một DNA riêng; không dùng chung face DNA giữa project.

Chỉ mô tả đặc điểm cấu trúc, không nhận diện/định danh người thật.

Cổng QC — chặn vòng lặp tự nhiễm:

Ảnh của Linh An là ảnh AI SINH RA (nhân vật không tồn tại).

Nếu trích face DNA từ ảnh trôi nhận dạng → độ trôi bị nướng vào DNA

→ DNA lại sinh ảnh trôi tiếp → vòng lặp tự nhiễm.

LUẬT: chỉ ảnh đã ĐẠT ngưỡng QC theo rubric 07F mới được vào

data/projects/venho_hotel/media/linh_an/.

Folder này là nơi CHỌN LỌC, không phải nơi chứa mọi ảnh đã sinh.

Ghi chú luật này vào docs/how_to_run_mode_b.md.

DoD: Linh An face DNA tách đúng invariant/variable; xác nhận grounding tắt; tài liệu vận hành ghi rõ luật cổng QC 07F.


19. Rủi ro chính
 1. Trộn Mode A và B          → A = observation, B = DNA, cảnh báo <2 ảnh

 2. Hard-code Ven Hồ vào core  → Ven Hồ trong config/projects/, core project-agnostic

 3. Pass 2 không tất định      → 2A code thuần quyết cấu trúc, 2B chỉ gọt câu chữ

 4. Key không cố định          → fixed key + type trong schema

 5. Phân loại sai invariant    → dùng CẢ coverage VÀ consistency, không chỉ tần suất

 6. Value trôi ngôn ngữ        → luật English values trong mọi prompt observe (§5.1)

 7. Trộn hạng phòng            → một subject = một hạng; CLI xác nhận (§2.1)

 8. FORBIDDEN rỗng/vô nghĩa    → nguồn chính từ overlay curated, không chờ quan sát (§4.3)

 9. Tri thức người bị máy nuốt → overrides.yaml merge lúc render, sống sót tái sinh (§5.2)

10. Mất nguyên tắc Authenticity → ALLOWED IMPERFECTIONS là section bắt buộc Mode B (§13)

11. Vòng lặp tự nhiễm face DNA → cổng QC 07F trước folder linh_an (Step 13)

12. Markdown không ổn định     → AI trả JSON, renderer tạo Markdown

13. Tốn token lại              → cache hash + schema_version + prompt_version

14. Một ảnh lỗi giết batch     → retry + isolation + failed report

15. Làm UI quá sớm             → CLI trước, UI sau


20. Thứ tự ưu tiên thực tế
1. Shared vision client

2. Mock provider

3. Universal schema (fixed key + type + English values)

4. Mode A

5. Test ảnh bất kỳ                 ← mốc giá trị đầu tiên

6. Pass 2A (coverage + consistency)

7. Mode B + overlay merge + compact

8. Project layer

9. Test Ven Hồ (một hạng phòng + overrides.yaml từ Visual DNA v2.7)

10. Schema bootstrap

11. Face / Linh An (cổng QC 07F)

Mode A là lõi tổng quát. Mode B là lớp chuyên sâu. Ven Hồ là project đầu tiên để kiểm chứng Mode B.


21. Kết luận
v2.4 là bản hoàn chỉnh sau khi đối chiếu kiến trúc kỹ thuật (v2.3 Final) với thực tế vận hành Ven Hồ Hotel. Sáu bổ sung của v2.4 đều thuộc loại lỗi chỉ lộ ra khi soi bằng dữ liệu thật:

English values      → chặn lỗi tất định ẩn khi so khớp chuỗi

Một subject một hạng → chặn nhiễm DNA giữa các hạng phòng

FORBIDDEN = policy  → không chờ model quan sát cái-không-tồn-tại

Curated Overlay     → tri thức người (Visual DNA v2.7) sống sót qua tái sinh

ALLOWED IMPERFECTIONS → giữ nguyên tắc "đáng tin hơn đẹp" trong mọi DNA

Cổng QC 07F         → chặn vòng lặp tự nhiễm cho nhân vật AI

Điểm cần giữ tuyệt đối:

Mode A là lõi tổng quát.

Mode B là DNA builder.

Pass 2A quyết định cấu trúc bằng code, dùng coverage VÀ consistency.

AI chỉ hỗ trợ quan sát (Pass 1) và chuẩn hóa câu chữ (Pass 2B).

Tri thức máy sinh và tri thức người tuyển chọn tách bạch, merge lúc render.

Ven Hồ không được hard-code vào core.

END OF DOCUMENT v2.4 (Complete)

