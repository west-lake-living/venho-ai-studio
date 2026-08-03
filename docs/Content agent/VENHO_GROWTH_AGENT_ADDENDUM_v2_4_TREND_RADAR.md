# VENHO GROWTH AGENT — ADDENDUM v2.4: TREND RADAR & DAILY PUBLISHING

**Trạng thái:** Bổ sung, thay thế v2.3 (đã gộp toàn bộ nội dung v2.3 + 4 sửa lỗi + 5 năng lực mới)
**Ngày:** 2026-08-03
**Đọc cùng:** `VENHO_GROWTH_CONTENT_IMAGE_AGENT_MASTER_PLAN_v2_2_QC.md`
**Mã:** `RS` (Research) · `TR` (Trend Radar) · `PB` (Publishing cadence)

---

# 0. Bốn sửa lỗi từ v2.3

| # | Lỗi v2.3 | Sửa trong v2.4 |
|---|---|---|
| RS-F1 | Skill đặt ở `skills/` root — sai vị trí Claude Code đọc | Chuyển sang `.claude/skills/` (project-level) |
| RS-F2 | Skill liệt kê phẳng, không tách atomic/composite | Tách hai tầng: atomic skill (một việc) + composite skill (điều phối) — §5 |
| RS-F3 | Thiếu YouTube/video làm nguồn nghiên cứu | Bổ sung nguồn video (metadata + transcript) vào 3 domain — §2 |
| RS-F4 | `CLAUDE.md` không có cơ chế quản trị thay đổi | Claude *đề xuất diff*, founder duyệt + commit thủ công — §6 |

---

# 1. Năm yêu cầu mới và xung đột phải giải quyết

| # | Yêu cầu của Harry | Xung đột phát hiện | Cách giải |
|---|---|---|---|
| Y1 | Agent tự tìm hiểu đa kênh (social, YouTube) | Scraping Facebook/Instagram/TikTok vi phạm ToS và vỡ liên tục | Chỉ dùng nguồn hợp pháp — §2.2 |
| Y2 | Lưu thông tin "hot" + sự kiện quanh Hồ Tây vào vault | Thông tin hot hỏng rất nhanh; Evidence Ladder chưa có cấp cho tin thời sự | Thêm cấp **R2-T** (time-sensitive) với expiry theo giờ/ngày — §3.2 |
| Y3 | Harry duyệt danh sách bài trên VenHo OS dashboard | Duyệt từng bài không kịp nhịp 7 bài/tuần | **Batch approval queue** + queue depth alert — §4 |
| Y4 | Tự động đăng 1 bài/ngày 9AM, chất lượng, đúng trọng tâm, chuẩn SEO | (a) 3→7 bài/tuần là tăng 2,3× — rủi ro fatigue; (b) "chuẩn SEO" không áp dụng cho FB/IG theo cách thông thường | Ramp có gate — §6.1; tách 3 bề mặt SEO — §6.3 |
| Y5 | Thứ 7 đăng bài chủ đề "hot" nhất tuần | (a) Trend cần duyệt gấp, mâu thuẫn approval lead time; (b) newsjacking rủi ro thương hiệu cao | Trend lane riêng có cutoff cứng + **Brand Safety Gate** — §7 |

---

# 2. Trend Radar — thu thập đa kênh

## 2.1. Vị trí kiến trúc

Trend Radar là một sub-package của `research_engine`, KHÔNG phải hệ thống mới. Nó chỉ sinh note R1/R2-T vào vault; mọi thứ sau đó đi qua Evidence Ladder như cũ.

```text
Nguồn hợp pháp → collector → normalize → dedupe → relevance score
   → note R1/R2-T vào vault → Trend Digest → dashboard → Harry duyệt
```

## 2.2. Nguồn được phép và không được phép

**ĐƯỢC PHÉP:**

| Nguồn | Cách lấy | Domain phục vụ | Chi phí |
|---|---|---|---|
| Google Trends | pytrends / export thủ công | `social_trend` | Miễn phí |
| YouTube Data API | API chính thức, metadata + transcript | `competitor`, `local_intel`, `social_trend` | Free quota 10k units/ngày |
| Meta Insights (trang CỦA MÌNH) | Graph API — đã có trong M08 | `platform_trend` | Miễn phí |
| Google Business Profile | API chính thức | `local_intel` | Miễn phí |
| News RSS (VnExpress, Hanoi Times, Tuổi Trẻ…) | RSS feed công khai | `social_trend`, `local_events` | Miễn phí |
| Sự kiện chính thức | Web sự kiện, trang thành phố, trang venue | `local_events` | Miễn phí |
| Review OTA | **Export thủ công** từ dashboard Agoda/Booking | `guest_voice` | Miễn phí |
| Google Maps Places | API chính thức | `local_intel` | Có phí thấp |

**KHÔNG ĐƯỢC PHÉP (ghi rõ để agent không tự ý làm):**

- Scrape Facebook/Instagram của đối thủ — vi phạm ToS, ban account, vỡ liên tục.
- Scrape TikTok — tương tự.
- Tải và tái sử dụng nội dung video/ảnh của người khác. Chỉ lấy **metadata + transcript** để phân tích nội bộ.
- Bất kỳ wrapper reverse-engineer nào dùng session cookie tài khoản Google/Meta cá nhân.

> **Nguyên tắc:** thà thiếu một nguồn còn hơn mất một tài khoản. Đối chiếu sự cố rotate `OPENAI_API_KEY` tháng 7 — rủi ro credential là rủi ro đã xảy ra thật, không phải giả định.

## 2.3. Domain mở rộng (từ 6 lên 8)

Bổ sung vào bảng §4 của v2.3:

| Domain | Câu hỏi | Nguồn | Nhịp | Expiry mặc định |
|---|---|---|---|---|
| `social_trend` | Tuần này xã hội chú ý gì mà Ven Hồ nói được? | Google Trends, News RSS, YouTube | **Hằng ngày** | 7 ngày |
| `local_events` | Quanh Hồ Tây sắp có sự kiện gì? | Trang sự kiện, GBP, báo địa phương | 2 lần/tuần | **Ngày kết thúc sự kiện** |

`local_events` có contract riêng vì sự kiện là dữ liệu có ngày chết cứng:

```yaml
---
rs_id: RS-2026-08-0031
type: event
domain: local_events
evidence_level: R2-T
event_name: "Lễ hội sen Hồ Tây"
event_start: 2026-08-15
event_end: 2026-08-17
venue: "Công viên nước Hồ Tây"
distance_from_hotel_km: 1.2
source_uri: "https://..."
expires_at: 2026-08-17          # = event_end, BẮT BUỘC
verified_by_human: false        # phải true trước khi thành proof point
relevance_to_guest: high
---
```

Quy tắc: sự kiện **không bao giờ** được nhắc trong content nếu `verified_by_human=false`. Đăng sai ngày/địa điểm một lễ hội là lỗi factual nghiêm trọng với khách đã đặt phòng.

## 2.4. Relevance scoring — chống nhiễu

Không phải trend nào cũng dùng được. Mỗi trend được chấm trước khi vào vault:

```yaml
# config/projects/venho_hotel/research/trend_policy.yaml
relevance_dimensions:
  geographic:   # Hồ Tây > Hà Nội > Việt Nam > quốc tế
    westlake: 1.0
    hanoi: 0.7
    vietnam: 0.4
    global: 0.1
  thematic:     # chủ đề có giao với khách sạn không
    travel_stay: 1.0
    food_local: 0.8
    lifestyle_culture: 0.6
    seasonal_weather: 0.5
    unrelated: 0.0
  actionability: # có thể tạo content đúng brand không
    direct: 1.0        # trực tiếp về Hồ Tây/lưu trú
    adjacent: 0.6      # liên quan gián tiếp
    stretch: 0.2       # phải gượng ép
min_score_to_vault: 0.35
min_score_to_saturday_lane: 0.60
```

Trend dưới ngưỡng bị loại và ghi lý do — không đưa vào vault để tránh làm loãng kho tri thức.

---

# 3. Evidence Ladder mở rộng cho tin thời sự

## 3.1. Vấn đề

Evidence Ladder v2.3 giả định tri thức tương đối ổn định (số phòng, điểm review). Tin "hot" hỏng trong vài ngày. Nếu ép tin thời sự qua promotion gate R2→R3 thủ công như fact thường, Harry sẽ thành bottleneck mỗi ngày.

## 3.2. Cấp mới R2-T

| Cấp | Đặc điểm | Được dùng thế nào |
|---|---|---|
| **R2-T** | Time-sensitive insight, expiry tính bằng giờ/ngày | Được dùng làm **góc nhìn / hook / bối cảnh** trong brief |
| **R3** | Fact được duyệt, ổn định | Được dùng làm **claim** trong content |

Ranh giới quyết định — quan trọng nhất trong toàn addendum này:

> **R2-T định hình GÓC NHÌN. R3 cung cấp SỰ THẬT.**

Ví dụ cụ thể:

| Câu trong bài | Cấp cần | Hợp lệ? |
|---|---|---|
| "Cuối tuần này Hồ Tây vào mùa sen" | R2-T (bối cảnh mùa vụ) | ✅ Được — mô tả chung, không phải cam kết |
| "Lễ hội sen diễn ra 15–17/8 tại Công viên nước Hồ Tây" | **R3** (fact có ngày/địa điểm) | ⛔ Cần verify human + promote |
| "Phòng lake view của chúng tôi cách đó 1,2km" | **R3** | ⛔ Cần fact `hotel.distance.westlake_park` |
| "Một buổi sáng chậm bên hồ" | Không cần | ✅ Ngôn ngữ chủ quan |

Claim Validator (v2.2 §5.2) đã enforce điều này — R2-T không map được `fact_key` nên mọi câu mang tính khẳng định dựa trên R2-T sẽ bị chặn. Đây là hành vi đúng, không phải bug.

## 3.3. Auto-expiry và dọn vault

`detect_stale_knowledge.py` chạy hằng ngày:

- R2-T quá hạn → chuyển `status: archived`, không xóa (giữ audit).
- Fact R3 quá hạn → revoke approval của mọi package chưa publish tham chiếu nó + alert dashboard.
- Sự kiện đã qua `event_end` → archived, nhưng giữ lại làm dữ liệu mùa vụ cho năm sau (giá trị thật: lễ hội thường lặp lại).

---

# 4. Approval Queue trên VenHo OS Dashboard

## 4.1. Vì sao không duyệt từng bài

7 bài/tuần × duyệt riêng lẻ = 7 lần context switch. Founder mobile-first sẽ trễ, và trễ đúng một ngày là mất một slot đăng.

## 4.2. Thiết kế: Batch queue có runway

```text
┌─ VENHO OS · Content Queue ────────────────────────────┐
│ Runway: 6 ngày ✅        Cần duyệt: 4 bài             │
├───────────────────────────────────────────────────────┤
│ ☐ T2 04/08 · Lake view sáng sớm      [ảnh] ✅QC 9.2  │
│ ☐ T3 05/08 · Cà phê ven hồ           [ảnh] ✅QC 9.0  │
│ ☐ T4 06/08 · Phòng đôi cho cặp đôi   [ảnh] ⚠️QC 8.4  │
│ ☐ T5 07/08 · Đường Nguyễn Đình Thi   [ảnh] ✅QC 9.1  │
│ ☐ T7 09/08 · 🔥 TREND (chờ thứ 6)    [ ]    —        │
├───────────────────────────────────────────────────────┤
│ [Duyệt tất cả ✅]  [Duyệt đã chọn]  [Xem chi tiết]   │
└───────────────────────────────────────────────────────┘
```

Mỗi dòng mở ra được Final Review đầy đủ (v2.2 §19.2): FB/IG preview, ảnh + crops, claims + evidence, validation theo chiều, cost, revision history.

**Duyệt hàng loạt vẫn tuân thủ exact-version approval** — mỗi bài sinh một `ApprovalRequest` riêng với snapshot copy_version_id + asset_version_id. "Duyệt tất cả" là tiện ích UI, không phải nới lỏng invariant.

## 4.3. Runway policy — chống ngày trống

| Runway | Trạng thái | Hành động hệ thống |
|---|---|---|
| ≥5 ngày | 🟢 Healthy | Không làm gì |
| 3–4 ngày | 🟡 Warning | Thông báo dashboard + sinh thêm draft |
| 1–2 ngày | 🟠 Critical | Alert (email/Zalo) + ưu tiên sinh draft |
| 0 ngày | 🔴 Empty | Dùng **Evergreen Pool** (§4.4) |

## 4.4. Evergreen Pool — mạng an toàn

10–15 bài đã duyệt trước, **không chứa claim thời sự** (không sự kiện, không giá, không promotion, không số liệu có expiry). Chỉ nội dung ổn định: kiến trúc, view hồ, trải nghiệm phòng, câu chuyện thương hiệu.

Quy tắc:

1. Evergreen **cũng phải qua approval đầy đủ** — không có ngoại lệ cho "publish không duyệt".
2. Mỗi bài evergreen dùng lại tối đa 1 lần/90 ngày (chống fatigue).
3. Dùng evergreen → alert cho Harry biết queue đã cạn.
4. Nếu evergreen cũng hết → **bỏ trống ngày đó + alert**. Hệ thống KHÔNG BAO GIỜ tự sinh và tự đăng bài chưa duyệt.

---

# 5. Skill architecture — atomic + composite

## 5.1. Vị trí đúng

```text
.claude/
├── skills/
│   ├── venho-source-collect/SKILL.md      # atomic
│   ├── venho-trend-scan/SKILL.md          # atomic
│   ├── venho-synth/SKILL.md               # atomic
│   ├── venho-fact-propose/SKILL.md        # atomic
│   ├── venho-content-package/SKILL.md     # atomic
│   ├── venho-research-cycle/SKILL.md      # composite
│   ├── venho-daily-queue/SKILL.md         # composite
│   ├── venho-weekly-trend/SKILL.md        # composite
│   └── _productize/
│       ├── hotel-review-intelligence/
│       ├── hotel-trend-radar/
│       └── hotel-content-engine/
CLAUDE.md
```

## 5.2. Quy tắc composition

- **Atomic skill:** làm đúng một việc, không gọi skill khác, có eval riêng.
- **Composite skill:** chỉ điều phối atomic skill theo chuỗi + xử lý lỗi. Không chứa business logic.
- Nếu composite bắt đầu chứa logic nghiệp vụ → logic đó thuộc về một module Python, không thuộc Skill.

Lợi ích productize: khách sạn khác mua đúng atomic skill họ cần (`hotel-trend-radar`) mà không phải lấy cả pipeline.

## 5.3. Ba composite chính

```text
venho-research-cycle    domain + question → collect → synth → insight note
venho-daily-queue       insight pool → brief → copy → image → validate → queue
venho-weekly-trend      trend scan (T4-T5) → relevance → brand safety → T6 digest
```

---

# 6. Publishing cadence 09:00 hằng ngày

## 6.1. Ramp có gate — đề xuất khác yêu cầu

Nhảy thẳng từ 3 lên 7 bài/tuần là tăng 2,3× khối lượng. Rủi ro cụ thể, không phải lý thuyết:

- Duplicate detector v2.2 chặn ở similarity ≥0,88. Với 12 phòng và một địa điểm cố định, không gian chủ đề hữu hạn — 7 bài/tuần chạm trần chủ đề nhanh hơn nhiều.
- Fatigue detection 28/90 ngày sẽ bắt đầu cảnh báo.
- Chi phí ảnh × 2,3.
- Reach trung bình/bài thường giảm khi tăng tần suất đột ngột — tổng reach có thể không tăng.

Đề xuất ramp:

| Giai đoạn | Nhịp | Điều kiện lên nhịp tiếp |
|---|---|---|
| A (tuần 1–4) | 3 bài/tuần (T2/T4/T6) | Queue runway ổn định ≥5 ngày, QC pass ≥90% |
| B (tuần 5–8) | 5 bài/tuần (+T3/T5) | Reach/bài không giảm >15%, duplicate block <10% |
| C (tuần 9+) | **7 bài/tuần** | QBSR không giảm so với baseline giai đoạn B |

Nếu bất kỳ gate nào fail → tự động lùi về nhịp trước + alert. Đây là dữ liệu quyết định, không phải cảm tính. Anh vẫn đạt mục tiêu 1 bài/ngày, chỉ là đến đó bằng đường có bằng chứng.

## 6.2. Dispatch pipeline 09:00

```text
08:45  Pre-flight check
       ├─ Fact expiry check → có fact hết hạn? → revoke → lấy bài kế tiếp
       ├─ Approval còn hiệu lực? (không bị revoke bởi edit)
       ├─ Asset còn truy cập được? (URL, hash khớp)
       └─ Fail toàn bộ → dùng Evergreen → vẫn fail → alert + bỏ trống

09:00  Dispatch qua M07
       ├─ Facebook publication (row riêng)
       ├─ Instagram publication (row riêng)
       └─ HTTP 200 → GATEWAY_ACCEPTED (KHÔNG phải PUBLISHED)

09:00+ Callback từ gateway → PUBLISHED + platform_post_id
09:30  Chưa có callback → UNKNOWN → reconciliation
10:00  Vẫn UNKNOWN → NEEDS_OPERATOR + alert
```

Scheduler: idempotent dispatch, timezone `Asia/Ho_Chi_Minh`, GitHub cron chỉ là fallback (v2.2 Phase 5). Trigger trùng → đúng 1 job nhờ idempotency key.

## 6.3. "Chuẩn SEO" — cần tách ba bề mặt

Đây là chỗ tôi cần nói thẳng: **Facebook và Instagram gần như không phải bề mặt SEO.** Nội dung trong đó Google index rất hạn chế. Tối ưu hashtag không phải SEO.

Ba bề mặt khác nhau, ba chiến lược khác nhau:

| Bề mặt | Bản chất | Tối ưu gì | Module |
|---|---|---|---|
| **Facebook / Instagram** | Discovery trong nền tảng | Hook 3 giây đầu, alt text, geo tag, hashtag tập trung, saves/shares | M05 social builder (đã có) |
| **Google Business Profile** | **SEO local thật** | Keyword "khách sạn Hồ Tây", post định kỳ, ảnh, Q&A, review | GBP post — Roadmap A4 |
| **Website blog** | **SEO organic thật** | Từ khóa, cấu trúc H, internal link, schema, độ dài | **M05 blog SEO builder — đã có sẵn, chưa dùng** |

Đề xuất bổ sung: cùng nội dung nghiên cứu sinh ra **1 bài blog SEO/tuần** cho website, bên cạnh social hằng ngày. M05 đã có `blog SEO` builder trong 16 steps hoàn thành — năng lực có sẵn, chưa được kích hoạt. Đây là đòn bẩy SEO thật cho "khách sạn Hồ Tây", và nó feed thẳng vào mục tiêu direct share ≥25% của Roadmap. Chi phí thêm gần như bằng 0 vì research đã có.

---

# 7. Thứ 7 — Trend Lane

## 7.1. Timeline cứng

```text
T4 (thứ 4)  09:00  Trend scan tự động (7 ngày qua)
T5 (thứ 5)  09:00  Synthesis + relevance scoring → top 3 candidate
T6 (thứ 6)  08:00  Trend Digest lên dashboard — Harry chọn 1 trong 3
T6 (thứ 6)  12:00  CUTOFF — chưa chọn → hủy lane, dùng bài thường
T6 (thứ 6)  14:00  Generate copy + image cho chủ đề đã chọn
T6 (thứ 6)  17:00  Final review → Harry duyệt
T6 (thứ 6)  20:00  CUTOFF CUỐI — chưa duyệt → fallback queue thường
T7 (thứ 7)  09:00  Publish
```

Hai cutoff cứng là bắt buộc. Không có chúng, trend lane sẽ tạo áp lực duyệt gấp vào tối thứ 6 — đúng lúc founder ít sẵn sàng nhất, và duyệt vội là nơi lỗi thương hiệu xảy ra.

## 7.2. Brand Safety Gate — kill switch bắt buộc

Đây là phần rủi ro cao nhất trong toàn bộ yêu cầu mới. "Chủ đề hot nhất xã hội" thường xuyên là những thứ mà một khách sạn bám vào sẽ tự hủy hoại thương hiệu.

**Danh mục CẤM tuyệt đối** (kill switch, không cần điểm số):

```yaml
# config/projects/venho_hotel/research/brand_safety.yaml
forbidden_trend_categories:
  - politics_governance        # chính trị, chính sách nhạy cảm
  - disaster_accident          # thiên tai, tai nạn, thương vong
  - death_tragedy              # tang lễ, mất mát
  - crime_scandal              # tội phạm, bê bối
  - celebrity_personal         # đời tư người nổi tiếng
  - health_crisis              # dịch bệnh, khủng hoảng y tế
  - religion_ethnicity         # tôn giáo, dân tộc
  - competitor_negative        # tin xấu về đối thủ
  - social_conflict            # tranh cãi xã hội đang chia rẽ

required_intersection:         # trend PHẢI giao ít nhất 1 mục
  - travel_accommodation
  - hanoi_westlake_local
  - food_culinary
  - seasonal_weather_nature
  - culture_festival_positive

min_relevance_score: 0.60
human_approval: mandatory      # không bao giờ tự động, kể cả sau này
```

Quy tắc bất biến: **trend lane không bao giờ được auto-approve**, kể cả khi các lane khác đã được nới lỏng trong tương lai. Rủi ro bất đối xứng — 52 bài trend/năm chạy tốt không bù được một bài sai bối cảnh.

## 7.3. Ba loại trend phù hợp

Để định hướng cụ thể thay vì "hot chung chung":

1. **Mùa vụ / thiên nhiên** — mùa sen Hồ Tây, sương sớm mùa đông, hoàng hôn tháng 9, hoa sưa. An toàn nhất, ăn khớp Visual DNA sẵn có.
2. **Sự kiện văn hóa tích cực** — lễ hội, triển lãm, marathon quanh hồ, Tết. Cần verify human vì có ngày/địa điểm cụ thể.
3. **Trend lifestyle liên quan lưu trú** — workcation, staycation cuối tuần, "chữa lành", du lịch chậm. Bám được mà không cần bám tin tức.

Ba loại này phủ gần hết nhu cầu thực tế và tránh hoàn toàn vùng nguy hiểm.

---

# 8. CLAUDE.md governance

Không cho phép Claude tự viết lại `CLAUDE.md` (đây là cơ chế character drift ở cấp dự án — mâu thuẫn nguyên tắc decision locking của OS).

Cơ chế đúng, giống hệt promotion gate R2→R3:

```bash
# Cuối mỗi task, Claude Code ghi đề xuất — KHÔNG sửa file gốc
.claude/CLAUDE.md.proposed     # diff đề xuất + lý do từng thay đổi
```

Harry review, merge thủ công, commit. `CLAUDE.md` được version bằng git như mọi decision khác.

---

# 9. Bổ sung file tree (chỉ phần MỚI so với v2.3)

```text
venho-ai-studio/
│
├── .claude/                                  # ★ SỬA vị trí (RS-F1)
│   ├── skills/                               #   atomic + composite (§5)
│   └── CLAUDE.md.proposed                    #   ★ governance (§8)
├── CLAUDE.md
│
├── research/
│   ├── trends/{YYYY-WW}/                     # ★ MỚI — trend theo tuần
│   │   ├── _scan.md                          #   raw scan output
│   │   ├── _digest.md                        #   top 3 candidate cho T6
│   │   └── {trend_slug}.md                   #   R2-T note
│   ├── events/                               # ★ MỚI — sự kiện quanh Hồ Tây
│   │   └── {YYYY-MM}_{event_slug}.md         #   expires_at = event_end
│   └── ...                                   #   (giữ nguyên v2.3)
│
├── research_engine/
│   ├── trend_radar/                          # ★ MỚI
│   │   ├── domain/
│   │   │   ├── trend_candidate.py            #   aggregate + relevance model
│   │   │   └── brand_safety.py               #   kill switch categories
│   │   ├── collectors/                       #   một file/nguồn, đều có rate limit
│   │   │   ├── google_trends.py
│   │   │   ├── youtube_data.py               #   metadata + transcript, KHÔNG tải video
│   │   │   ├── news_rss.py
│   │   │   ├── gbp_local.py
│   │   │   └── event_calendar.py
│   │   ├── application/
│   │   │   ├── scan_trends.py                #   T4 09:00
│   │   │   ├── score_relevance.py            #   §2.4
│   │   │   ├── build_digest.py               #   T5 → top 3
│   │   │   └── verify_event.py               #   gate verified_by_human
│   │   └── cli.py                            #   venho-trend scan|digest|verify
│   └── ...
│
├── growth_orchestrator/
│   ├── application/
│   │   ├── manage_queue.py                   # ★ runway policy §4.3
│   │   ├── daily_dispatch.py                 # ★ pre-flight + 09:00 §6.2
│   │   └── evergreen_pool.py                 # ★ §4.4
│   └── ...
│
├── config/projects/venho_hotel/research/
│   ├── trend_policy.yaml                     # ★ relevance scoring §2.4
│   ├── brand_safety.yaml                     # ★ kill switch §7.2
│   └── event_sources.yaml                    # ★ nguồn sự kiện đã duyệt
│
├── config/projects/venho_hotel/growth/
│   ├── cadence_policy.yaml                   # ★ ramp A/B/C §6.1
│   └── queue_policy.yaml                     # ★ runway thresholds §4.3
│
└── tests/
    ├── test_trend_relevance.py               # ★ trend dưới ngưỡng bị loại
    ├── test_brand_safety_gate.py             # ★ danh mục cấm luôn bị chặn
    ├── test_event_verification.py            # ★ event chưa verify không vào content
    ├── test_queue_runway.py                  # ★ queue cạn → evergreen → alert
    ├── test_daily_dispatch.py                # ★ pre-flight, fact expiry, idempotency
    └── test_r2t_expiry.py                    # ★ R2-T không thành claim
```

---

# 10. Bổ sung roadmap

## Phase 1.6 — Trend Radar (tuần 6–8, sau Phase 1.5)

| Task | Nội dung | Phụ thuộc |
|---|---|---|
| TR-001 | `trend_policy.yaml` + `brand_safety.yaml` + relevance model | RS-003 |
| TR-002 | Collectors: Google Trends, News RSS (2 nguồn dễ nhất trước) | TR-001 |
| TR-003 | Collector YouTube Data API (metadata + transcript) | TR-002 |
| TR-004 | `local_events` domain + `verify_event.py` gate | TR-001 |
| TR-005 | R2-T evidence level + auto-expiry | RS-003 |
| TR-006 | Trend Digest generator → dashboard | TR-002 |
| TR-007 | Skill `venho-trend-scan` + `venho-weekly-trend` | TR-006 |

**Exit gate:** một trend chạy trọn vòng scan → score → digest → duyệt → bài T7 · danh mục cấm bị chặn 100% trên test set · sự kiện chưa verify không lọt vào content · R2-T không thể thành claim.

## Phase 4.5 — Daily cadence (sau Phase 4 publishing reliability)

| Task | Nội dung |
|---|---|
| PB-001 | Queue UI + batch approval trên VenHo OS |
| PB-002 | Runway policy + alert |
| PB-003 | Evergreen Pool (10–15 bài duyệt trước) |
| PB-004 | Pre-flight check 08:45 |
| PB-005 | Scheduler 09:00 idempotent |
| PB-006 | Cadence ramp A→B→C có gate tự động |
| PB-007 | Blog SEO tuần (kích hoạt M05 blog builder) |

**Exit gate:** 14 ngày liên tục đăng đúng 09:00, 0 duplicate, 0 ngày trống ngoài ý muốn · pre-flight bắt được fact hết hạn · ramp gate tự lùi nhịp khi metric xấu.

---

# 11. Decisions bổ sung

| ID | Quyết định | Đề xuất | Lý do |
|---|---|---|---|
| **TR-D1** | Scrape social đối thủ? | **Không.** Chỉ nguồn có API/RSS chính thức | ToS + rủi ro credential |
| **TR-D2** | Nhịp đăng 7 bài/tuần ngay? | **Ramp A→B→C có gate** | Duplicate/fatigue/cost là rủi ro đo được |
| **TR-D3** | Trend lane auto-approve? | **Không bao giờ** | Rủi ro bất đối xứng |
| **TR-D4** | Bổ sung blog SEO tuần? | **Có** — M05 đã có builder, chi phí ~0 | Đây mới là SEO thật |
| **TR-D5** | Evergreen pool bắt buộc? | **Có**, 10–15 bài trước khi bật daily | Không có thì ngày trống là chắc chắn |
| **TR-D6** | Ai verify sự kiện? | **Harry** — sự kiện có ngày/địa điểm là fact | Sai ngày lễ hội = lỗi nghiêm trọng |

---

# 12. Bổ sung Definition of Done

Thêm vào 19 điều kiện của v2.2 + v2.3:

20. Không collector nào truy cập nguồn ngoài danh sách được duyệt trong `event_sources.yaml`/`trend_policy.yaml`.
21. Mọi trend thuộc danh mục cấm bị chặn ở gate, có test chứng minh.
22. R2-T không tồn tại code path nào cho phép trở thành claim publish.
23. Sự kiện chưa `verified_by_human` không xuất hiện trong bất kỳ content nào.
24. 14 ngày đăng liên tục 09:00, 0 duplicate, 0 ngày trống ngoài kế hoạch.
25. Cadence ramp tự động lùi nhịp khi gate metric fail.
26. `CLAUDE.md` chỉ thay đổi qua diff được founder duyệt và commit.
