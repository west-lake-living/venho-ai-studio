# VENHO AI Studio — Knowledge Studio

**Module 01 · Version 0.1**  
Phân tích ảnh theo batch → trích xuất Visual DNA có cấu trúc → xuất Markdown + JSON tái dùng được cho AI production.

---

## Vấn đề giải quyết

Upload ảnh thủ công vào ChatGPT → AI mô tả từng ảnh thay vì tổng hợp DNA → knowledge phân tán, không version-controlled.

**Knowledge Studio** tạo pipeline riêng:

```
Folder ảnh → Gemini Flash (batch analysis) → Gemini Flash (synthesis) → Markdown DNA
```

---

## Cài đặt

```bash
# 1. Clone repo
git clone <repo-url>
cd venho-ai-studio

# 2. Cài dependencies
bash setup.sh

# 3. Tạo .env
cp .env.example .env
# Điền GEMINI_API_KEY vào .env (GOOGLE_API_KEY cũng được chấp nhận)
```

---

## Sử dụng

```bash
# Basic
python3 app/main.py --folder assets/raw/room --category Room

# Với options
python3 app/main.py --folder assets/raw/room --category Room --batch-size 3 --output-name ROOM_DNA_v0.1

# Dry run (kiểm tra plan, không gọi API)
python3 app/main.py --folder assets/raw/room --category Room --dry-run
```

### Options

| Flag | Default | Mô tả |
|------|---------|-------|
| `--folder` | (required) | Path đến folder ảnh |
| `--category` | (required) | Room, Lobby, Reception, Facade, Rooftop, WestLake, LinhAn, Other |
| `--batch-size` | 5 | Số ảnh mỗi batch |
| `--output-name` | `{CATEGORY}_DNA_v0.1` | Tên file output |
| `--version` | `v0.1` | Version label |
| `--dry-run` | false | Chỉ scan, không gọi API |

---

## Workflow

```
Step 1 — User bỏ ảnh vào assets/raw/<category>/
Step 2 — Chạy python3 app/main.py --folder ... --category ...
Step 3 — Gemini Flash phân tích từng batch ảnh
Step 4 — Gemini Flash tổng hợp DNA từ tất cả batches
Step 5 — Tool xuất file .md + .json vào output/
Step 6 — Review output, copy vào 02_KNOWLEDGE/DNA/ nếu đạt
```

---

## Output

```
output/
├── knowledge/
│   └── ROOM_DNA_v0.1.md        ← Markdown cho người đọc
├── json/
│   └── ROOM_DNA_v0.1.json      ← Machine-readable
└── logs/
    ├── knowledge-studio-2026-06.log   ← Processing log
    └── extraction_log.json            ← History tất cả lần chạy
```

### Cấu trúc Markdown output

```markdown
# VENHO AI Studio — Room DNA
**Version:** v0.1 · **Status:** DRAFT

## Visual DNA
## Material DNA
## Color DNA
## Geometry DNA
## Lighting DNA
## Camera Angle DNA

## Fixed Rules       ← Luôn hiện diện — AI PHẢI include
## Allowed Variations
## Negative Rules    ← KHÔNG BAO GIỜ xuất hiện
```

---

## Cấu trúc project

```
venho-ai-studio/
├── app/
│   ├── main.py              # Entry point
│   └── cli.py               # argparse CLI
├── core/
│   ├── media_loader.py      # Scan folder → list ảnh
│   ├── batch_manager.py     # Chia batch
│   ├── dna_extractor.py     # Orchestrate OpenAI extraction
│   ├── knowledge_merger.py  # Claude synthesis
│   ├── markdown_exporter.py # Export .md + .json
│   └── logger.py            # Logging
├── providers/
│   ├── base_provider.py
│   ├── openai_provider.py   # legacy OpenAI vision adapter
│   ├── claude_provider.py   # legacy Claude synthesis adapter
│   └── gemini_vision.py     # Gemini Flash vision + synthesis
├── prompts/
│   ├── visual_dna_extraction_prompt.md
│   └── knowledge_merge_prompt.md
├── schemas/
│   └── visual_dna_schema.json
├── config/
│   └── settings.json
├── assets/raw/              # Input: bỏ ảnh vào đây
└── output/                  # Output: DNA files
```

---

## AI Engines

| Task | Engine | Model |
|------|--------|-------|
| Image analysis (per batch) | Google Gemini | gemini-flash-latest |
| Knowledge synthesis | Google Gemini | gemini-flash-latest |

---

## First Test Case

```bash
# Bỏ 10-20 ảnh phòng thật vào:
assets/raw/room/

# Chạy:
python3 app/main.py --folder assets/raw/room --category Room

# Expected: output/knowledge/ROOM_DNA_v0.1.md
# Phải nhận diện: phòng dài hẹp, cửa sổ nhôm đen, rèm xám, lan can sắt, nội thất gỗ tối, bedding trắng, view Hồ Tây
# Negative rules: không luxury resort, không cửa kính sàn-trần
```

---

## Universe

Một phần của **THE WEST LAKE LIVING** workspace.  
Output sẽ được đưa vào `knowledge-library` repo sau khi validate.

---

*VENHO AI Studio · Knowledge Studio v0.1 · June 2026*
