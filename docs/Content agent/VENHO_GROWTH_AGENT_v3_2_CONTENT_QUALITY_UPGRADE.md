# VENHO GROWTH AGENT v3.2 — CONTENT QUALITY UPGRADE

## Technical Specification & Implementation Plan

| | |
|---|---|
| **Base** | Growth Agent v3.1 (giữ nguyên runtime GitHub Actions + git-sync) |
| **Repo** | `venho-ai-studio` |
| **Phạm vi** | Chất lượng chủ đề tuần + caption/content. **Không** đụng runtime, **không** đụng M07, **không** làm video |
| **Trạng thái** | Implementation Handoff → **[x] Codex implementation + QA/optimization pass DONE (2026-09-09)** |
| **Ngày** | 2026-09-09 |

> **QA sign-off (2026-09-09):** Toàn bộ U1–U5 do Codex dựng đã được rà soát, sửa lỗi và tối ưu.
> - **Bug chặn tính năng đã sửa:** `_THEME_ANGLE_RULES` trong `content_studio/generators/social_prompts.py` dùng template Jinja `{{ }}` nhưng gọi `str.format()` → giá trị ThemeAngle (concrete_details, guest_question…) **không bao giờ tới prompt M05**, vô hiệu hóa toàn bộ U2. Đã chuyển sang lắp chuỗi bằng helper, an toàn với ký tự `{` `}` trong copy vận hành + `rewrite_vi.md`.
> - Sửa thêm: `scan_week` đọc `watchlist.yaml` 3 lần → 1 lần; `_previous_week` raise rõ ràng khi thiếu `-W` và tính đúng tuần 52/53 của năm trước; dọn tham số chết `recent_plans` trong `choose_angle_types`; gộp import trùng.
> - Test: +3 test regression `tests/test_growth_social_prompts_v32.py`. Full suite `1612 passed` (1 fail có sẵn, không liên quan: thiếu `googleapiclient`). Calibration gate: 30/30 AI bắt, 0/30 người viết bị bắt nhầm.
> - **P1 (2026-09-09):** đã có 9 đoạn Voice Corpus thật của Harry (`data/voice_corpus/samples/`, qua phỏng vấn). Chạy gate trên bản trả lời gốc bắt được 2 luật false-positive (`ST-03`, `ST-05`) — đã sửa; xem entry `task_status.md` cùng ngày.
> - **Còn phải làm tay (không phải lỗi code):** xác nhận watchlist thật (≥15 entity) + khoảng cách khách sạn tới tuyến Quảng An; định nghĩa R0–R4 Evidence Ladder; P2 chuẩn hoá đầy đủ trên ~20 mẫu người + bộ AI-draft thật (fixture hiện do Codex tự viết); mở rộng vocab `specificity_check`; chạy thật P6 (4 tuần).

---

> **HƯỚNG DẪN CHO AI CODING AGENT — ĐỌC TRƯỚC KHI VIẾT DÒNG CODE ĐẦU TIÊN**
>
> 1. Đọc `CLAUDE.md`, `task_memory.md`, `task_status.md` trước mọi task.
> 2. Đây là bản nâng cấp **in-place** trên v3.1. Không tạo repo mới, không tạo hệ song song.
> 3. Không đụng: `publishing_gateway/` (M07), `analytics_feedback/` (M08), GitHub Actions workflows, runtime/scheduler.
> 4. M03 vẫn là validator duy nhất. Naturalness Gate là **module con trong M03**, không phải validator thứ hai.
> 5. Mỗi task khai báo `allowed_files`. Chạm file ngoài danh sách = task fail.
> 6. `pytest` mặc định **0 real API call**.
> 7. Không hạ ngưỡng gate để làm test xanh. Gate fail = báo cáo.

---

# 0. Vấn đề và chẩn đoán

## 0.1. Ba triệu chứng do người vận hành báo cáo

1. Bài viết chưa đủ hay, chưa có mở đầu đủ hấp dẫn, chưa truyền tải một ý tưởng giá trị rõ ràng, chưa có kết.
2. Trend Radar không phát hiện các sự kiện nóng của khu vực (ví dụ: dự án cải tạo Hồ Tây và mở rộng đường ven hồ).
3. Nội dung nghèo nàn, lặp đi lặp lại.

## 0.2. Chẩn đoán — đây là một chuỗi nhân quả, không phải ba lỗi độc lập

```
Thiếu chất liệu địa phương cụ thể
        ↓
Brief nghèo → không có gì cụ thể để nói
        ↓
Rơi về evergreen pool hữu hạn
        ↓
Lặp lại theo cấu trúc  (triệu chứng 3)
        ↓
M05 chỉ còn cách viết chung chung, sáo rỗng  (triệu chứng 1)
```

**Gốc nằm ở tầng input, không phải tầng sinh văn bản.** Sửa prompt/rubric trước khi sửa nguồn chất liệu sẽ không có tác dụng.

## 0.3. Vì sao Trend Radar không bắt được — và vì sao KHÔNG sửa Trend Radar

Trend Radar dùng robust z-score trên MAD, cửa sổ 28 ngày, kèm recency half-life. Nó bắt **đột biến** (burst).

Câu chuyện Hồ Tây không đột biến. Nó chảy đều từ tháng 01/2026 (chốt phương án mở rộng 6 phố), lên mốc quan trọng 15/06/2026 (duyệt chủ trương đầu tư), và dự án thành phần đầu tiên chạy từ Q1/2026 đến Q2/2027. Với một detector bắt đột biến, một câu chuyện chảy đều 8 tháng là **đường phẳng** — không có tín hiệu để bắt.

> **Kết luận kiến trúc:** Trend Radar đang làm đúng nhiệm vụ của nó. Cái còn thiếu là một loại cảm biến khác — theo dõi **thay đổi trạng thái** của một tập thực thể địa phương cố định, chứ không phải phát hiện đột biến trong dòng tin toàn cầu.
>
> **AI AGENT: KHÔNG sửa thuật toán trong `research_engine/trend_radar/`.** Thêm module mới song song.

## 0.4. Vì sao văn bản bị nhận ra là AI

Không phải vì viết sai. Vì **chung chung**. Một câu có thể dán vào 500 khách sạn khác là câu AI, bất kể trau chuốt đến đâu.

Hai đòn bẩy, theo thứ tự sức mạnh:

| # | Đòn bẩy | Cơ chế | Sức mạnh |
|---|---|---|---|
| 1 | **Tăng mật độ chi tiết cụ thể** — tên phố, giờ, con số, quan sát trực tiếp | Local Beat + `specificity_score` gate | ★★★★★ |
| 2 | **Chặn dấu hiệu AI bằng luật xác định** — sáo ngữ, cấu trúc bộ ba, câu hỏi tu từ mở bài, kết mời chung chung | Naturalness Gate (deterministic) | ★★★★ |
| 3 | Sửa prompt cho "tự nhiên hơn" | — | ★ (không đo được, không lặp lại được) |

---

# 1. Scope

## 1.1. In scope

- **U1 — Local Beat Monitor**: cảm biến địa phương theo dõi thay đổi trạng thái, song song Trend Radar.
- **U2 — Weekly Theme Planner**: lập chủ đề trục cho cả tuần, 4 góc khác nhau về *loại*, thay vì 4 bài sinh độc lập.
- **U3 — Naturalness Gate**: module con trong M03, kiểm tra xác định các dấu hiệu văn AI + mật độ cụ thể.
- **U4 — Repetition Guard**: chống lặp ở mức câu chữ, không chỉ mức chủ đề.
- **U5 — Voice Corpus**: kho văn mẫu do người thật viết, dùng làm few-shot + thước đo khoảng cách giọng văn.

## 1.2. Out of scope

- Kịch bản Reel / video (dự án riêng).
- Ubuntu Control Plane v4.x.
- Đụng M07, M08, GitHub Actions, cadence 4 bài/tuần (**giữ nguyên**).
- Sửa thuật toán Trend Radar.
- Auto-approve. Human approval giữ nguyên toàn bộ.

## 1.3. Invariant giữ nguyên

1. M03 là validator duy nhất. Naturalness Gate nằm **trong** M03.
2. Chỉ fact R3 active mới được dùng làm factual claim.
3. Approval gắn exact copy version + asset version + validation snapshot.
4. Budget gate fail-closed.
5. Test mặc định 0 real API call.
6. Cadence 4 bài/tuần T2/T4/T6/T7 không đổi.

---

# 2. Kiến trúc tổng thể sau nâng cấp

```text
┌─────────────────── TẦNG CHẤT LIỆU (INPUT) ───────────────────┐
│                                                               │
│  Research OS ──────────┐                                      │
│  Trend Radar ──────────┤  (giữ nguyên — bắt đột biến)         │
│  Local Beat Monitor ★──┤  (MỚI — bắt thay đổi trạng thái)     │
│  Weather ──────────────┤                                      │
│  M01 Knowledge Facts ──┘                                      │
└───────────────────────────┬───────────────────────────────────┘
                            ▼
┌─────────────────── TẦNG KẾ HOẠCH ─────────────────────────────┐
│  Weekly Theme Planner ★  (MỚI)                                │
│    → 1 spine + 4 góc khác LOẠI cho T2/T4/T6/T7                │
└───────────────────────────┬───────────────────────────────────┘
                            ▼
┌─────────────────── TẦNG SINH ─────────────────────────────────┐
│  M05 Content Studio  (sửa: nhận ThemeAngle thay vì brief thô) │
│    → N candidate                                              │
└───────────────────────────┬───────────────────────────────────┘
                            ▼
┌─────────────────── TẦNG KIỂM ĐỊNH (M03) ──────────────────────┐
│  Claim Validator      (giữ nguyên)                            │
│  Brand Policy         (giữ nguyên)                            │
│  Naturalness Gate ★   (MỚI — xác định, không dùng LLM)        │
│  Repetition Guard ★   (MỚI)                                   │
│    → PASS | REWRITE(lý do cụ thể) | ESCALATE_HUMAN            │
└───────────────────────────┬───────────────────────────────────┘
                            ▼
                    Human Approval → M07 (không đổi)
```

**Vòng rewrite:** Gate fail → trả về M05 kèm **danh sách vi phạm cụ thể** (không phải "hãy viết tự nhiên hơn") → tối đa 2 vòng → vòng 3 vẫn fail thì đưa lên người duyệt với các đoạn vi phạm được highlight.

---

# 3. File Tree

> File có `★` là tạo mới. File có `✎` là sửa file đã có.

```text
venho-ai-studio/
│
├── research_engine/
│   ├── trend_radar/                       # KHÔNG SỬA
│   ├── local_beat/                     ★  # ═══ MODULE MỚI U1 ═══
│   │   ├── __init__.py
│   │   ├── watchlist.yaml                 # tập thực thể theo dõi (§4.1)
│   │   ├── entities.py                    # BeatEntity, BeatItem, BeatStatus
│   │   ├── scanner.py                     # quét tuần, 1 query/entity
│   │   ├── differ.py                      # so tuần này vs snapshot tuần trước
│   │   ├── timeline_store.py              # trạng thái + lịch sử mỗi entity
│   │   ├── angle_extractor.py             # BeatItem → GuestAngle (LLM, schema-bound)
│   │   ├── vault_writer.py                # ghi note markdown vào Obsidian vault
│   │   └── cli.py                         # `venho-beat scan --week`
│   └── ...
│
├── growth_orchestrator/
│   ├── weekly_theme/                   ★  # ═══ MODULE MỚI U2 ═══
│   │   ├── __init__.py
│   │   ├── models.py                      # WeeklyThemePlan, ThemeAngle, AngleType
│   │   ├── planner.py                     # thuật toán chọn spine + 4 góc (§5)
│   │   ├── angle_types.yaml               # định nghĩa 6 loại góc
│   │   ├── diversity_rules.py             # ràng buộc khác loại, khác nguồn
│   │   └── cli.py                         # `venho-theme plan --week`
│   └── ...
│
├── validator_studio/                      # M03 — validator DUY NHẤT
│   ├── claim_validator.py                 # KHÔNG SỬA
│   ├── naturalness/                    ★  # ═══ MODULE MỚI U3 + U4 ═══
│   │   ├── __init__.py
│   │   ├── gate.py                        # điều phối: chạy tất cả check, tổng hợp verdict
│   │   ├── lexical_rules.yaml             # sáo ngữ tiếng Việt bị cấm (§6.2)
│   │   ├── lexical_check.py
│   │   ├── structural_check.py            # bộ ba, câu hỏi tu từ, đối xứng mở-kết (§6.3)
│   │   ├── specificity_check.py           # mật độ danh từ riêng/số/thời gian (§6.4)
│   │   ├── rhythm_check.py                # phương sai độ dài câu (§6.5)
│   │   ├── emoji_check.py                 # mẫu emoji máy móc (§6.6)
│   │   ├── repetition_guard.py            # n-gram vs 12 bài gần nhất (§7)
│   │   ├── voice_distance.py              # khoảng cách tới Voice Corpus (§8)
│   │   └── report.py                      # NaturalnessReport → phản hồi cho M05
│   └── ...
│
├── content_studio/                        # M05
│   ├── generator.py                    ✎  # nhận ThemeAngle; vòng rewrite có phản hồi
│   ├── prompts/
│   │   ├── caption_vi.md               ✎  # viết lại theo §9
│   │   └── rewrite_vi.md               ★  # prompt sửa theo danh sách vi phạm
│   └── ...
│
├── data/
│   ├── voice_corpus/                   ★  # U5 — văn mẫu người thật viết
│   │   ├── README.md                      # hướng dẫn thu thập
│   │   └── samples/*.md
│   └── local_beat/                     ★
│       ├── snapshots/                     # snapshot tuần, dùng để diff
│       └── timelines/                     # trạng thái mỗi entity
│
├── vault/                                 # Obsidian — đã có
│   └── local_beat/                     ★  # note markdown, người đọc được
│
└── tests/
    ├── local_beat/                     ★
    ├── weekly_theme/                   ★
    ├── naturalness/                    ★  # ⚠️ nhiều fixture tiếng Việt thật
    └── fixtures/
        ├── ai_sounding_vi.md           ★  # 30 đoạn văn AI điển hình → PHẢI fail
        └── human_written_vi.md         ★  # 30 đoạn người viết → PHẢI pass
```

---

# 4. U1 — Local Beat Monitor

## 4.1. Watchlist

```yaml
# research_engine/local_beat/watchlist.yaml
# AI AGENT: đây là dữ liệu cấu hình, không hard-code vào Python.
# Người vận hành sẽ tự thêm/bớt entity mà không cần deploy.

version: 1
scan_cadence: weekly          # KHÔNG phải daily — beat thay đổi chậm
locale: vi-VN
region: "Tây Hồ, Hà Nội"

entities:
  - id: ho-tay-project
    name: "Dự án cải tạo Hồ Tây"
    queries:
      - "cải tạo Hồ Tây"
      - "đường ven Hồ Tây mở rộng"
      - "cầu cạn Hồ Tây"
    category: infrastructure
    guest_relevance: high        # ảnh hưởng trực tiếp trải nghiệm khách
    tracked_since: "2026-01"

  - id: quang-an-road
    name: "Đường Quảng An"
    queries: ["đường Quảng An", "Phủ Tây Hồ Từ Hoa mở rộng"]
    category: infrastructure
    guest_relevance: critical    # dự án thành phần đầu tiên, gần khách sạn
                                 # ⚠️ NGƯỜI VẬN HÀNH XÁC NHẬN khoảng cách tới khách sạn

  # Các nhóm entity bắt buộc có (điền tiếp khi triển khai):
  #   infrastructure : bến thuyền Hồ Tây, sàn ngắm cảnh, bãi đỗ xe ngầm,
  #                    Nhà hát Opera Hà Nội, thu hồi đất quanh hồ Tây
  #   streets        : Nhật Chiêu, Trích Sài, Vệ Hồ, Nguyễn Đình Thi,
  #                    Quảng Bá, Từ Hoa, Đặng Thai Mai
  #   culture        : Phủ Tây Hồ, chùa Trấn Quốc, sen Hồ Tây, lễ hội phường
  #   food_scene     : quán mới/đóng cửa quanh hồ
  #   seasonal       : mùa sen, mùa cúc họa mi, sương mù Hồ Tây, thời tiết cực đoan
  #   policy         : quy định du lịch/lưu trú Hà Nội, vùng phát thải thấp
```

Tối thiểu **15 entity**, tối đa 30. Vượt 30 thì chi phí quét vượt giá trị.

## 4.2. Cơ chế: DIFF, không phải SCORE

```python
# research_engine/local_beat/differ.py
#
# AI AGENT: KHÔNG cài z-score, không cài burst detection, không cài trend score.
# Trend Radar đã làm việc đó. Module này làm việc KHÁC:
# so tập kết quả tuần này với snapshot tuần trước, cái gì MỚI thì nổi lên.
#
# Lý do: sự kiện địa phương quan trọng thường chảy đều nhiều tháng,
# không tạo đột biến. Detector bắt đột biến sẽ luôn bỏ lỡ chúng.

def diff_week(current: list[SearchResult],
              previous_snapshot: WeekSnapshot) -> list[BeatItem]:
    """
    Trả về các BeatItem MỚI so với tuần trước.

    "Mới" nghĩa là:
      - URL chưa từng thấy, HOẶC
      - Đã thấy URL nhưng tiêu đề/nội dung đổi đáng kể (similarity < 0.85), HOẶC
      - Entity chuyển trạng thái (xem BeatStatus bên dưới)

    KHÔNG trả về: kết quả trùng URL, bài tổng hợp lại tin cũ,
    nội dung không nhắc tới entity trong 200 từ đầu.
    """
```

## 4.3. Timeline trạng thái

```python
class BeatStatus(StrEnum):
    """Trạng thái vòng đời của một sự việc địa phương.

    Giá trị của module này nằm ở đây: biết một dự án ĐANG Ở GIAI ĐOẠN NÀO
    quan trọng hơn biết nó được nhắc bao nhiêu lần.
    """
    RUMORED           = "rumored"            # có tin đồn/đề xuất
    APPROVED          = "approved"           # đã duyệt chủ trương
    SCHEDULED         = "scheduled"          # đã có mốc thời gian
    IN_PROGRESS       = "in_progress"        # đang thi công/diễn ra
    AFFECTING_GUESTS  = "affecting_guests"   # ⚠️ đang ảnh hưởng khách (rào đường, ồn)
    COMPLETED         = "completed"
    STALLED           = "stalled"            # chậm tiến độ
```

`AFFECTING_GUESTS` là trạng thái **ưu tiên cao nhất** — nó vừa là chất liệu nội dung, vừa là thông tin khách cần biết, và là loại nội dung hữu ích nhất mà một khách sạn có thể đăng.

## 4.4. Đầu ra: GuestAngle, không phải tin tức

```python
@dataclass(frozen=True)
class GuestAngle:
    """Một góc nhìn CÓ THỂ VIẾT THÀNH BÀI, không phải một mẩu tin.

    AI AGENT: angle_extractor.py dùng LLM nhưng output PHẢI khớp schema này.
    Nếu LLM trả về không khớp schema → coi như không có angle, KHÔNG cứu bằng regex.
    """
    entity_id: str
    beat_item_id: str
    status: BeatStatus

    # Góc nhìn cho khách — cụ thể, không chung chung
    guest_question: str      # câu hỏi thật khách sẽ có, vd "Đường trước khách sạn có bị rào không?"
    concrete_details: list[str]   # tên phố, mốc thời gian, con số — nguyên liệu cho specificity
    what_we_can_say: str          # điều khách sạn nói được với tư cách người ở đây
    what_we_cannot_claim: list[str]  # điều CHƯA có fact R3 → cấm nêu như sự thật

    evidence_urls: list[str]
    evidence_date: date
    fact_ids_r3: list[str]        # fact đã lên R3 trong M01, được phép trích dẫn
```

## 4.5. Ranh giới Evidence

> **AI AGENT — QUY TẮC BẤT BIẾN:**
> BeatItem là **chất liệu bối cảnh**, không tự động thành sự thật được trích dẫn.
>
> - Được phép: viết về bối cảnh, quan sát trực tiếp, cảm nhận, hướng dẫn thực dụng.
> - **Cấm**: nêu số liệu cụ thể (tổng mức đầu tư, chiều dài, mốc hoàn thành) như sự thật khi chưa có `fact_id` R3 active trong M01.
> - Muốn dùng số liệu → phải đi qua quy trình đưa fact lên R3 của M01 trước.
>
> ⚠️ **Cần xác nhận với người vận hành:** định nghĩa chính xác R0–R4 trong Evidence Ladder hiện tại, để `angle_extractor` gán đúng cấp. Tôi chưa đọc định nghĩa đó.

## 4.6. Ghi vault

Mỗi entity một note markdown trong `vault/local_beat/<entity-id>.md`, có timeline dạng bảng, để **người đọc được** — không chỉ máy đọc. Đây là tài sản dùng lại cho mọi việc sau này, kể cả kịch bản video.

---

# 5. U2 — Weekly Theme Planner

## 5.1. Vấn đề đang có

4 slot sinh độc lập → 4 bài rời rạc → không có mạch → và khi thiếu chất liệu thì cả 4 rơi về cùng một vùng an toàn của evergreen pool → lặp.

## 5.2. Thiết kế: 1 spine + 4 góc KHÁC LOẠI

```python
class AngleType(StrEnum):
    """Sáu LOẠI góc. Ràng buộc: 4 bài trong tuần phải thuộc 4 loại KHÁC NHAU.

    Đây là cơ chế chống lặp mạnh nhất — mạnh hơn chống trùng chủ đề,
    vì hai bài cùng loại thì dù khác chủ đề vẫn "nghe giống nhau".
    """
    PRACTICAL      = "practical"       # thông tin dùng được ngay: đường, giờ, lối đi
    OBSERVATION    = "observation"     # quan sát trực tiếp từ khách sạn, có thời điểm cụ thể
    GUIDE          = "guide"           # hướng dẫn: đi đâu, ăn gì, đi thế nào
    STORY          = "story"           # chuyện khách, chuyện nhân viên, chuyện đã xảy ra
    CONTEXT        = "context"         # bối cảnh khu vực đang thay đổi ra sao
    SERVICE        = "service"         # thông tin dịch vụ khách sạn — TỐI ĐA 1 bài/tuần
```

```python
@dataclass(frozen=True)
class WeeklyThemePlan:
    iso_week: str                  # "2026-W37"
    spine: str                     # chủ đề trục, 1 câu, cụ thể
    spine_source: Literal["local_beat", "seasonal", "trend_radar", "evergreen"]
    angles: dict[Weekday, ThemeAngle]   # T2, T4, T6, T7
    banned_openers: list[str]      # câu mở của 12 bài gần nhất — cấm dùng lại
    banned_phrases: list[str]      # cụm đặc trưng đã dùng trong 4 tuần
```

## 5.3. Thuật toán chọn

```
1. Lấy beat items tuần này, ưu tiên theo:
       AFFECTING_GUESTS > IN_PROGRESS > SCHEDULED > APPROVED > khác
2. Nếu có beat guest_relevance ∈ {critical, high}:
       spine = beat đó                     source = local_beat
   elif có sự kiện mùa vụ trong 14 ngày tới:
       spine = mùa vụ                       source = seasonal
   elif Trend Radar có candidate qua brand safety:
       spine = trend                        source = trend_radar
   else:
       spine = evergreen chưa dùng ≥ 8 tuần  source = evergreen
       ⚠️ ghi cảnh báo: tuần này thiếu chất liệu tươi
3. Sinh 4 angle từ spine, ràng buộc:
       - 4 AngleType khác nhau
       - ≤ 1 bài SERVICE
       - mỗi angle phải có ≥ 2 concrete_details
       - angle không trùng AngleType với cùng thứ trong tuần của 3 tuần gần nhất
4. Nếu không đủ 4 angle khác loại → giảm còn 3 bài + 1 evergreen,
   VÀ cảnh báo Telegram: "tuần W thiếu chất liệu, chỉ dựng được N góc"
```

> **AI AGENT:** bước 4 là tính năng, không phải lỗi. Thà đăng 3 bài có nội dung còn hơn 4 bài trong đó 1 bài rỗng. **Không** được lấp đầy bằng cách nới lỏng ràng buộc khác loại.

---

# 6. U3 — Naturalness Gate

## 6.1. Nguyên tắc

> **Toàn bộ gate này là XÁC ĐỊNH (deterministic). Không dùng LLM để chấm điểm "độ tự nhiên".**
>
> Lý do: dùng LLM chấm văn LLM là vòng lặp không có điểm neo — kết quả không lặp lại được, không kiểm thử được, và trôi theo model. Luật xác định thì viết test được, giải thích được cho M05 sửa, và không tốn token.

Đầu ra:

```python
@dataclass(frozen=True)
class NaturalnessReport:
    verdict: Literal["PASS", "REWRITE", "ESCALATE_HUMAN"]
    violations: list[Violation]     # mỗi vi phạm có: rule_id, đoạn văn, gợi ý sửa
    specificity_score: float
    rewrite_round: int              # tối đa 2
```

## 6.2. Lexical check — sáo ngữ tiếng Việt

```yaml
# validator_studio/naturalness/lexical_rules.yaml
# AI AGENT: đây là danh sách khởi điểm. Người vận hành sẽ bổ sung theo thời gian.
# Không hard-code vào Python.

banned_openers:        # xuất hiện trong 15 từ đầu → vi phạm nặng
  - "Trong nhịp sống hối hả"
  - "Giữa lòng Hà Nội"
  - "Giữa lòng thủ đô"
  - "Bạn đã bao giờ"
  - "Hãy cùng"
  - "Nếu bạn đang tìm kiếm"
  - "Có một nơi"
  - "Không đâu xa"

banned_phrases:        # ở bất kỳ đâu → vi phạm
  - "nép mình"
  - "chốn bình yên"
  - "điểm đến lý tưởng"
  - "đắm chìm"
  - "hòa quyện"
  - "trọn vẹn từng khoảnh khắc"
  - "trải nghiệm đích thực"
  - "không gian ấm cúng"
  - "hương vị khó quên"
  - "tinh tế đến từng chi tiết"
  - "níu chân du khách"
  - "dấu ấn khó phai"
  - "thổi hồn"
  - "bức tranh thiên nhiên"

banned_connectors:     # cấu trúc quá quen của văn AI
  - "không chỉ ... mà còn"
  - "không những ... mà còn"
  - "chính vì vậy"
  - "hơn thế nữa"
  - "đặc biệt hơn cả"

banned_closers:        # trong 20 từ cuối
  - "hãy đến và cảm nhận"
  - "chúng tôi luôn sẵn sàng"
  - "đừng bỏ lỡ"
  - "còn chần chừ gì nữa"
  - "hãy để chúng tôi"
```

## 6.3. Structural check

| rule_id | Phát hiện | Ngưỡng |
|---|---|---|
| `ST-01` | **Bộ ba song song** — 3 cụm cùng cấu trúc nối bằng dấu phẩy ("yên bình, thư thái, gần gũi") | ≥ 1 lần = vi phạm |
| `ST-02` | **Câu hỏi tu từ mở bài** — câu đầu kết thúc bằng `?` | vi phạm |
| `ST-03` | **Đối xứng mở–kết** — câu cuối lặp lại ≥ 3 từ nội dung của câu đầu | vi phạm |
| `ST-04` | **Aside bằng dấu gạch ngang** — `—` chèn mệnh đề giữa câu | ≥ 2 lần = vi phạm |
| `ST-05` | **Signpost thừa** — "Đầu tiên", "Tiếp theo", "Cuối cùng" trong bài < 200 từ | vi phạm |
| `ST-06` | **Kết bằng lời mời chung chung** không kèm thông tin cụ thể (giờ, giá, địa chỉ, cách đặt) | vi phạm |

## 6.4. Specificity check — chỉ số quan trọng nhất

```python
# validator_studio/naturalness/specificity_check.py
#
# AI AGENT: đây là check có sức mạnh lớn nhất trong toàn bộ gate.
# Văn AI bị nhận ra vì THIẾU chi tiết cụ thể, không phải vì viết dở.

def specificity_score(text: str) -> float:
    """
    Đếm số 'neo cụ thể' trên 100 từ.

    Neo cụ thể gồm:
      - tên riêng địa phương  (Quảng An, Phủ Tây Hồ, Trích Sài, Đặng Thai Mai)
      - con số có đơn vị      (5 phút, 21m, 40.000đ, tầng 3)
      - mốc thời gian cụ thể  (6h sáng, thứ Ba, tháng 10, mùa sen)
      - danh từ vật thể cụ thể (ban công, xe máy, bát bún, cây bàng)

    KHÔNG tính là neo cụ thể:
      - tính từ ca ngợi (yên bình, tuyệt vời, ấn tượng)
      - danh từ trừu tượng (trải nghiệm, không gian, hành trình, cảm xúc)

    Ngưỡng: >= 4.0 neo/100 từ  → PASS
            2.5 - 4.0          → CẢNH BÁO, cho qua nhưng ghi log
            < 2.5              → REWRITE
    """
```

> **AI AGENT:** ngưỡng 4.0 là điểm khởi đầu, phải hiệu chỉnh bằng fixture ở §11. Chạy trên 30 đoạn người viết và 30 đoạn AI, chọn ngưỡng phân tách tốt nhất. **Không** tự đoán ngưỡng.

## 6.5. Rhythm check

```
Tính phương sai độ dài câu (số từ).
Văn AI: câu dài đều nhau, phương sai thấp.
Văn người: xen câu rất ngắn với câu dài.

variance < 15  → vi phạm RH-01
Bài < 80 từ    → bỏ qua check này (mẫu quá nhỏ)
```

## 6.6. Emoji check

```
EM-01: emoji xuất hiện đúng 1 lần ở đầu mỗi dòng/bullet → vi phạm (mẫu máy móc)
EM-02: > 1 emoji / 40 từ → vi phạm
EM-03: emoji nằm giữa câu, không phải cuối câu/đoạn → cảnh báo
```

## 6.7. Vòng rewrite

```
Vòng 1: gate fail → gửi lại M05 kèm violations
        prompt rewrite_vi.md nhận DANH SÁCH CỤ THỂ:
        "Câu 1 dùng mở đầu bị cấm 'Giữa lòng Hà Nội' → viết lại bằng
         một quan sát cụ thể có thời điểm"
        KHÔNG gửi "hãy viết tự nhiên hơn" — vô nghĩa với model.

Vòng 2: fail tiếp → rewrite lần cuối, tăng nhiệt độ, ép dùng
        concrete_details từ GuestAngle

Vòng 3: vẫn fail → ESCALATE_HUMAN
        Đưa lên duyệt với các đoạn vi phạm được highlight,
        người viết tay đoạn đó. KHÔNG tự động hạ ngưỡng để cho qua.
```

---

# 7. U4 — Repetition Guard

```python
# validator_studio/naturalness/repetition_guard.py

def check_repetition(candidate: str, recent_posts: list[str]) -> list[Violation]:
    """
    So với 12 bài gần nhất (khoảng 3 tuần).

    RP-01  Trùng 5-gram: >= 3 chuỗi 5 từ liên tiếp trùng với BẤT KỲ bài nào  → vi phạm
    RP-02  Trùng mở bài: similarity câu đầu >= 0.75 với câu đầu bài nào đó   → vi phạm
    RP-03  Trùng vân cấu trúc: cùng (số đoạn, vị trí CTA, kiểu kết)
           lặp >= 3 lần trong 12 bài                                          → vi phạm
    RP-04  Trùng cụm đặc trưng: cụm 3+ từ không phải tên riêng
           xuất hiện >= 3 lần trong 12 bài                                    → cảnh báo

    Dùng chuẩn hoá tiếng Việt trước khi so: bỏ dấu câu, hạ chữ thường,
    GIỮ dấu thanh (bỏ dấu sẽ tạo trùng giả).
    """
```

---

# 8. U5 — Voice Corpus

## 8.1. Vì sao cần

Cách chắc chắn nhất để văn không giống AI là có **văn mẫu của người thật** làm neo. Không có neo thì mọi hiệu chỉnh đều là cảm tính.

## 8.2. Yêu cầu với người vận hành

Viết tay **8–12 đoạn**, mỗi đoạn 100–200 từ, **không dùng AI**, về đúng chủ đề khách sạn thường đăng. Viết như đang nhắn cho một người bạn sắp đến ở. Sai chính tả nhẹ, câu cụt, ý rẽ ngang — **giữ nguyên**, đừng sửa cho đẹp. Chính những chỗ đó là thứ AI không tạo ra được.

Đây là **vài giờ công một lần**, và là đầu vào có giá trị cao nhất trong toàn bộ bản nâng cấp này.

## 8.3. Dùng thế nào

1. **Few-shot exemplar** trong prompt M05 — chọn 2–3 mẫu gần nhất với AngleType đang viết.
2. **voice_distance.py** — đo khoảng cách thống kê của candidate tới corpus: phân bố độ dài câu, tỉ lệ từ Hán-Việt, mật độ tính từ, tần suất đại từ ngôi thứ nhất. Lệch quá xa → cảnh báo.

> **AI AGENT:** `voice_distance` là **cảnh báo**, không phải gate cứng, ở giai đoạn đầu. Corpus 8–12 mẫu quá nhỏ để làm ngưỡng chặn. Chỉ nâng thành gate khi corpus ≥ 30 mẫu.

---

# 9. Sửa prompt M05

Thay đổi cốt lõi trong `content_studio/prompts/caption_vi.md`:

```markdown
## Nguyên liệu bắt buộc dùng
Bạn PHẢI dùng ít nhất 3 chi tiết từ danh sách `concrete_details` dưới đây.
Nếu không dùng được, hãy trả về lý do thay vì viết bài chung chung.

concrete_details: {{ angle.concrete_details }}

## Cấm tuyệt đối
- Không mở bài bằng câu hỏi.
- Không dùng cấu trúc "không chỉ ... mà còn".
- Không kết bằng lời mời chung chung; kết phải có thông tin dùng được
  (giờ, địa chỉ, cách đi, cách đặt) hoặc một quan sát cụ thể.
- Không dùng tính từ ca ngợi khi có thể thay bằng chi tiết cụ thể.
  Thay "không gian yên bình" bằng cái gì tạo ra sự yên bình đó.

## Điều bạn KHÔNG được khẳng định
{{ angle.what_we_cannot_claim }}
```

> **AI AGENT:** đổi prompt là việc **cuối cùng**, sau khi U1–U4 xong. Đổi prompt trước sẽ không đo được tác dụng vì chưa có gate để đo.

---

# 10. Thứ tự triển khai

| Phase | Nội dung | Ước tính | DoD |
|---|---|---|---|
| **P1** | Voice Corpus (người vận hành viết) + fixture `ai_sounding_vi.md` / `human_written_vi.md` | 1 ngày công người + 0.5 ngày code | 30 đoạn mỗi loại, đã gán nhãn — **[x] một phần (2026-09-09): 9 đoạn Voice Corpus thật (`data/voice_corpus/samples/`); fixture 30/30 vẫn do Codex viết, cần thay bằng mẫu thật ở P2** |
| **P2** | Naturalness Gate (U3) + Repetition Guard (U4), hiệu chỉnh ngưỡng trên fixture | 3–4 ngày | ≥ 90% đoạn AI bị bắt, ≤ 10% đoạn người bị bắt nhầm — **[x] hiệu chỉnh trên 48 caption thật (2026-09-09)**: đạt FP 0% trên văn người, nhưng chỉ ~56% AI isolated / ~79–91% khi có lịch sử bài. **90% xác định là không đạt được trên corpus này** (bài "ổn" lặp gần như bài "nhạt"; khác biệt là giọng) — phần còn lại thuộc tầng chất liệu U1/U2 + prompt. Thêm luật `DNA-LEAK`; `ST-04` 2→3; Repetition Guard strip scaffold + 6-gram; `RP-03`→warning. Gate chạy **warn-only** tới khi bật `naturalness_enforce`. Chi tiết: `task_status.md` 2026-09-09. |
| **P3** | Local Beat Monitor (U1) | 3–4 ngày | Quét 1 tuần thật, phát hiện được ≥ 3 beat item mới có thật, trong đó có sự việc Hồ Tây |
| **P4** | Weekly Theme Planner (U2) | 2–3 ngày | Sinh được plan tuần với 4 AngleType khác nhau; tuần thiếu chất liệu thì cảnh báo đúng |
| **P5** | Nối vào M05 + prompt mới + vòng rewrite | 2 ngày | 4 bài liên tiếp PASS gate ở vòng ≤ 2 |
| **P6** | Chạy thật 4 tuần, hiệu chỉnh | 4 tuần chạy nền | — |

**Tổng code: khoảng 11–14 ngày.** P1 và P2 độc lập với P3/P4 — có thể làm song song nếu muốn.

> Làm P2 **trước** P3 là cố ý: gate là thước đo. Có thước trước, rồi mới cải thiện nguyên liệu, thì mới biết cải thiện có tác dụng không.

---

# 11. Acceptance Tests

## 11.1. Naturalness Gate (bắt buộc, chặn merge)

```python
# tests/naturalness/test_gate_calibration.py
#
# AI AGENT: hai test này là thước đo chính của cả bản nâng cấp.
# KHÔNG được sửa fixture hay hạ ngưỡng để làm test xanh.

def test_catches_ai_sounding_vietnamese():
    """>= 27/30 đoạn văn AI điển hình phải bị gate bắt."""

def test_does_not_flag_human_written():
    """<= 3/30 đoạn người viết bị bắt nhầm (false positive <= 10%)."""
```

## 11.2. Local Beat

```
BE-01  Quét tuần chứa sự việc Hồ Tây → phát hiện được, có URL và ngày
BE-02  Quét lại cùng tuần → 0 item mới (idempotent)
BE-03  Bài tổng hợp lại tin cũ → KHÔNG được coi là item mới
BE-04  Số liệu chưa lên fact R3 → nằm trong what_we_cannot_claim
```

## 11.3. Weekly Theme

```
TH-01  Plan có đúng 4 AngleType khác nhau
TH-02  <= 1 bài SERVICE mỗi tuần
TH-03  Thiếu chất liệu → trả 3 góc + cảnh báo, KHÔNG nới ràng buộc
TH-04  Không lặp AngleType với cùng thứ trong tuần của 3 tuần trước
```

## 11.4. Repetition

```
RP-T1  Đưa lại nguyên văn 1 bài cũ → bị chặn
RP-T2  Bài mới cùng chủ đề, khác câu chữ → PASS
RP-T3  Bài mở đầu giống bài tuần trước 80% → bị chặn
```

---

# 12. Rủi ro

| # | Rủi ro | Giảm thiểu |
|---|---|---|
| 1 | Gate quá chặt → mọi bài đều ESCALATE, người vận hành phải viết tay | Hiệu chỉnh ngưỡng trên fixture trước khi bật; giới hạn false positive ≤ 10%; tuần đầu chạy ở chế độ **cảnh báo, không chặn** |
| 2 | Danh sách cấm làm văn cụt lủn, mất giọng thương hiệu | Voice Corpus làm neo; cấm cụm sáo rỗng, **không** cấm cảm xúc |
| 3 | Local Beat quét ra toàn tin rác | Watchlist cố định + yêu cầu entity xuất hiện trong 200 từ đầu + allowlist nguồn của Research OS |
| 4 | Chi phí LLM tăng vì vòng rewrite | Gate là xác định, không tốn token. Rewrite tối đa 2 vòng. Bù lại giảm 3→2 candidate nếu cần |
| 5 | Scope creep sang video/Reels | Đã tách thành dự án riêng. Mọi đề xuất thêm phải là task riêng |
| 6 | Ngưỡng specificity đoán sai | Bắt buộc hiệu chỉnh trên fixture, cấm hard-code số tự nghĩ ra |

---

# 13. Cần người vận hành xác nhận

| # | Câu hỏi | Ảnh hưởng |
|---|---|---|
| 1 | Địa chỉ chính xác Ven Hồ Hotel, và khoảng cách tới tuyến Quảng An – Phủ Tây Hồ – Từ Hoa | Quyết định `guest_relevance` của entity quan trọng nhất |
| 2 | Định nghĩa R0–R4 trong Evidence Ladder hiện tại | `angle_extractor` gán cấp bằng chứng |
| 3 | 12 bài gần nhất lấy từ đâu — `publication_registry.json` hay store nào? | Repetition Guard đọc nguồn nào |
| 4 | M05 hiện sinh mấy candidate/bài, prompt nằm ở file nào? | Điểm nối vòng rewrite |
| 5 | Sẵn sàng viết 8–12 đoạn văn mẫu tay không? | P1 là điều kiện của P2 |

---

# 14. Vị trí kỹ thuật

> v3.2 không thêm hạ tầng, không đổi runtime, không đụng đường publish.
> Nó sửa đúng **tầng chất liệu** và thêm một **thước đo xác định** cho chất lượng văn bản — hai thứ mà v3.1 thiếu, và là nguyên nhân gốc của cả ba triệu chứng đang gặp.
>
> Nguyên tắc xuyên suốt: **văn tự nhiên đến từ chi tiết cụ thể, không đến từ tính từ hay prompt hay hơn.**
