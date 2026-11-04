# VENHO Growth Content Agent — Báo cáo trạng thái

**Ngày:** 04/11/2026 · **Người lập:** Claude (theo yêu cầu của Harry) · **Phạm vi:** Growth Agent v3.1/v3.2 đang chạy production trên asus-server

> Số liệu lấy trực tiếp từ server ngày 04/11/2026: `publication_registry.json`, `growth.db`, `venho-rollout scorecard`, `rollout-status`, git log. Phần "đã biết" lấy từ task_memory và các lần sửa lỗi trước.

---

## 1. Tóm tắt

| Mục | Trạng thái |
|---|---|
| Hệ thống | **Đang chạy**, là hệ thống social duy nhất còn đăng (legacy `venho-social-content-agent` đã nghỉ) |
| Lịch đăng | T2 / T4 / T6 / T7 lúc 09:00 ICT, Facebook Page + Instagram, chạy bằng systemd timer trên asus-server |
| Rollout stage | **`shadow`**. Bài vẫn đăng nhờ cờ `--allow-shadow` trong `growth-dispatch.sh` |
| Scorecard (04/11) | **8,89/10, chưa đạt**. Chỉ còn trượt `unplanned_empty_days` do ngày trống 07/10, ngày này ra khỏi cửa sổ 28 ngày từ **05/11** |
| Bài đã lên | 87 lượt (81 `PUBLISHED` + 6 `GATEWAY_ACCEPTED` cũ). Theo tháng: T8 22 · T9 29 · T10 30 · T11 4 |
| Lịch sắp tới | 6 slot đã duyệt (06–14/11), 4 slot chờ duyệt (16–21/11) |
| Lỗi mới nhất | Ảnh tự upload bị xoay ngang khi đăng (04/11). **Đã sửa** ở `a7da11b`, nhưng bài 04/11 đã lên sai và ảnh bài 07/11 vẫn sai trên Drive |

**Kết luận:** pipeline đã ổn định về giờ giấc và đường đăng từ khi chuyển lên server (21/10). Từ 26/10, ảnh đúng chủ đề đã thay cho ảnh dự phòng. Ba điểm yếu lớn còn lại:
1. Không đo hiệu quả bài thật. Analytics vẫn là mock.
2. Lỗi thường hỏng âm thầm và chỉ phát hiện khi Harry nhìn thấy bài.
3. Hệ thống phụ thuộc vào việc Harry duyệt tay đúng hạn.

---

## 2. Cấu trúc agent

### 2.1 Luồng tổng thể

```
NGHIÊN CỨU            LÊN KẾ HOẠCH            SOẠN BÀI                  DUYỆT                 ĐĂNG
─────────────         ──────────────          ─────────────             ──────────            ─────────────
Research cycle  ┐                             Creative Brief            VENHO OS Dashboard    growth-dispatch.sh
(local_intel)   │     Weekly cycle            → Prompt Studio (M02)     "Duyệt bài"           (09:00 / 17:00)
Trend Radar     ├──►  CN 20:00 + 22:00   ──►  → Content Studio (M05) ─► + Telegram album ──►  → Publishing Gateway
(Google News)   │     soạn 2 tuần tới         → Naturalness gate        chọn ảnh A/B/C/U      → Make.com webhook
Topic ideation  │     slot T2/T4/T6/T7        → Ảnh A/B/C + QC ảnh      Approve / Reject      → Facebook + Instagram
(Gemini+lịch    ┘     Fast lane (mỗi giờ)     → Drive public URL                              → registry PUBLISHED
 mùa)                 Replace-rejected (:25)                                                   → Telegram tóm tắt
```

### 2.2 Thành phần chính

| Lớp | Thành phần | Vị trí / lịch |
|---|---|---|
| **Nghiên cứu** | Research cycle (`local_intel`: 1 địa điểm/fact, tối đa 8 đề xuất) | GitHub Actions, hằng ngày / T5 |
| | Trend Radar: Google News RSS (13 truy vấn) + Gemini trích sự kiện + gộp trùng | Server, 07:15 + 19:15 |
| | Topic ideation: Gemini Flash từ `seasonal_calendar.yaml`, loại trùng 120 ngày | Chạy trong weekly cycle |
| | guest_voice (khen/chê của khách) | Hằng tháng, lần đầu 05/11 |
| **Kế hoạch** | Slot T2/T4/T6/T7, lanes `daily`, `saturday_trend`, fast lane | `growth.db` → `publishing_slots` |
| | Weekly cycle (soạn 2 tuần) | Server, CN 20:00 + 22:00 |
| | Replace-rejected (thay bài bị loại hoặc hết hạn) | Server, mỗi giờ phút :25 |
| | Expire-stale + `reconcile-slots` (đóng slot COMPLETED/MISSED) | Server, 07:05 |
| **Soạn bài** | Creative brief (khoá checksum) → M02 prompt → M05 văn bản FB/IG | `growth_orchestrator/` |
| | Naturalness gate v3.2 (luật cấu trúc ST-xx, chống "giọng AI") | `validator_studio/naturalness/` |
| | Ảnh: A = AI theo scenario khớp topic, B = AI cảnh khác, C = ảnh thật thư viện, U = Harry tải lên | `image_options.py` |
| | QC ảnh theo DNA (M03), kill-switch khi vi phạm `forbidden` | `validator_studio/` |
| | Ảnh dự phòng: vòng xoay 49 ảnh thật theo subject | `publishing_gateway/fallback_images.py` |
| **Duyệt** | Dashboard "Duyệt bài" trên os.venhohotel.com (Cloudflare Access) | repo `venho-os` |
| | Telegram: album ảnh mỗi bài mới, cảnh báo lỗi, tóm tắt bài đã đăng | bot Hermes |
| **Đăng** | Publishing Gateway → Make.com (scenario Growth riêng, filter chữ ký `X-Venho-Signature`, chặn `publication_id` chứa `test`) | Make.com |
| | Chuẩn hoá ảnh: JPEG ≤ 2048px, pad về tỉ lệ IG 4:5 | `to_upload_jpeg`, `normalize_for_instagram` |
| | Idempotency key + `--require-dispatch`, giới hạn trễ 30 phút | `growth-dispatch.sh` |
| **Trạng thái** | `publication_registry.json` + `growth.db`, commit vào git, `growth_state_merge.py` gộp khi push xung đột | clone `~/venho/growth-runtime/venho-ai-studio` |
| **Giám sát** | OnFailure → Telegram; Dashboard watch / deploy alerts; `venho-rollout scorecard` | server |
| **Đo lường** | M08 Analytics → **MockMetricsAdapter** (chưa nối Meta Insights) | `analytics_feedback/` |

### 2.3 Repo và máy liên quan

| Repo / nơi chạy | Vai trò |
|---|---|
| `venho-ai-studio` (GitHub `west-lake-living`) | Toàn bộ logic agent, config, registry |
| `venho-os` | Dashboard duyệt bài, API upload/chọn ảnh |
| asus-server `~/venho/growth-runtime/` | Runtime production (venv riêng, secrets `~/venho/secrets/growth.env`) |
| asus-server `~/venho/03_AI_STUDIO/` | Bản checkout Dashboard đọc (sync 5 phút/lần, chỉ fast-forward) |
| Mac `assets/raw/` | Thư viện ảnh gốc; **phải rsync tay lên server** |
| GitHub Actions | Research cycle, blog-seo, tests; publish chỉ còn `workflow_dispatch` dự phòng |
| Make.com | Cầu nối đăng FB/IG |

---

## 3. Số liệu vận hành

### 3.1 Registry (toàn bộ 265 dòng)

| Trạng thái | Số dòng | Ghi chú |
|---|---|---|
| SUPERSEDED | 85 | Bản cũ bị thay khi soạn lại |
| PUBLISHED | 81 | |
| CANCELLED | 29 | Gồm bài curated bị fast lane thay |
| FAILED | 17 | 2 lỗi gần nhất (07/10, 12/10 IG) do GitHub cron trễ 2 ngày; nguyên nhân này đã hết từ khi chuyển lên server |
| REJECTED | 17 | Harry loại |
| APPROVED_SCHEDULED | 12 | 6 slot 06–14/11 |
| PENDING_APPROVAL | 8 | 4 slot 16–21/11 |
| DISABLED | 7 | |
| GATEWAY_ACCEPTED | 6 | Từ T8–T9 (FB/IG 03/08 + 4 bài Threads), chưa bao giờ đối soát |
| STALE_APPROVAL | 3 | 19/09 ×2, 14/10 IG |

### 3.2 Từ 05/10 (4 tuần gần nhất)

30 bài đăng · 7 bị loại · 2 lỗi · 1 hết hạn duyệt · 2 huỷ. Có 2 slot không đăng được: **07/10** (lỗi + bị loại) và 21/10 (Harry tự huỷ, không tính vào scorecard).

### 3.3 Ảnh

- **Lịch sử:** 70/87 bài đã đăng dùng ảnh dự phòng. Nguyên nhân là từ 28/08 đến 21/10 runner GitHub không có `assets/raw/` nên âm thầm rơi về ảnh dự phòng.
- **Từ 26/10:** chỉ 1 lượt dùng ảnh dự phòng.
- **Harry chọn ảnh nào (31 lượt từ 26/10):**

| Lựa chọn | Số lượt | Tỉ lệ |
|---|---|---|
| A (AI khớp chủ đề) | 12 | 39% |
| U (Harry tự tải) | 9 | 29% |
| C (ảnh thật thư viện) | 8 | 26% |
| B (AI cảnh khác) | 2 | 6% |

→ **55% bài chọn ảnh thật** (U + C). Lựa chọn B gần như không được dùng.

### 3.4 Scorecard rollout (04/11/2026)

```json
{ "score": 8.89, "passed": false, "failures": ["unplanned_empty_days"], "sample_size": 81,
  "data_gaps": ["linh_an_identity_pass: not applicable -- no published post features Linh An"] }
```

Chỉ tiêu ảnh (`hotel_dna_pass`, `copy_image_alignment`) đã đủ dữ liệu QC thật. Lỗi duy nhất còn lại là ngày 07/10, sẽ tự ra khỏi cửa sổ vào 05/11.

---

## 4. Điểm mạnh

1. **Đăng đúng giờ.** Chuyển từ GitHub cron (trễ 4–7 giờ) sang systemd timer trên server. Không còn lỗi "đăng trễ quá 30 phút" kể từ 21/10.
2. **Có người duyệt và nhiều lớp an toàn.** Brief khoá checksum, approval snapshot khoá ảnh, idempotency key, stage `shadow`, Make chặn `test` + kiểm chữ ký, giới hạn trễ. Chưa có lần đăng trùng nào kể từ khi bỏ chạy song song.
3. **Ảnh khớp nội dung.** Có A/B/C + upload ngay trên Dashboard và album Telegram. Tỉ lệ ảnh dự phòng giảm từ ~80% xuống ~3%.
4. **Chủ đề đa dạng và kịp thời.** Topic ideation theo mùa, Trend Radar bắt sự kiện thật (backtest: đua thuyền, pháo hoa), có lane nhanh cho sự kiện 3–10 ngày tới.
5. **Báo lỗi chủ động.** Unit hỏng có OnFailure → Telegram, có tin tóm tắt mỗi lần đăng, Dashboard có cảnh báo deploy.
6. **Scorecard trung thực.** Thiếu dữ liệu thì báo `data_gaps` chứ không bịa số. Lỗi so sai thang 100/1 đã được sửa.
7. **Test phủ rộng.** Khoảng 170 file test, mỗi lỗi đã sửa đều có test hồi quy (YAML topic, xoay vòng ảnh, EXIF…).
8. **Chỉ dùng chi tiết khách sạn có thật.** Ideation bị giới hạn trong `hotel_angles`, không cho bịa tiện nghi.

---

## 5. Điểm yếu

1. **Không có vòng phản hồi hiệu quả.** M08 vẫn dùng `MockMetricsAdapter`, chưa gọi Meta Insights. Agent không biết bài nào được tương tác, nên không học được chủ đề, giờ đăng hay loại ảnh nào hiệu quả.
2. **Lỗi thường âm thầm, chỉ lộ khi Harry nhìn thấy.** Các ví dụ:
   - YAML topic hỏng (3 ngày không đăng).
   - Ảnh dự phòng thay ảnh thật suốt 2 tháng.
   - Checkout Dashboard kẹt nhánh 4 ngày.
   - Ảnh phòng ngủ gắn vào bài quán cà phê.
   - Ảnh xoay ngang (04/11).

   Hệ thống không tự kiểm tra **kết quả đầu ra** (bài lên trông thế nào), chỉ kiểm tra các bước đã chạy hay chưa.
3. **Phụ thuộc Harry duyệt đúng hạn.** Bài không được duyệt kịp sẽ hết hạn (STALE), và slot có thể mất hẳn (19/09).
4. **Lưu trạng thái trong file JSON commit vào git.** Nhiều tiến trình cùng ghi (server, CI, Dashboard) nên phải có script gộp và cờ skip-worktree. Cách này dễ xung đột, và xoá dòng trên GitHub không lan sang Dashboard.
5. **Nhiều bộ phận, trải trên nhiều repo.** `venho-ai-studio`, `venho-os`, script ở `~/venho/scripts`, Make.com, 2 checkout trên server, thư viện ảnh trên Mac. Muốn chẩn đoán phải biết đúng chỗ.
6. **Thư viện ảnh phụ thuộc Mac.** Ảnh mới phải rsync tay lên server; quên bước này là lại rơi về ảnh dự phòng.
7. **Stage `shadow` mang nghĩa khó hiểu.** Stage ghi "shadow" nhưng bài vẫn đăng thật nhờ `--allow-shadow`. Nếu ai đó bỏ cờ này trong lúc còn shadow thì toàn bộ việc đăng dừng lại.
8. **QC ảnh có điểm mù.** Validator không nhận ra sai hình dáng lan can Hồ Tây (ảnh vẫn được 100). QC growth không đọc `overrides.yaml`.
9. **Một máy chủ duy nhất.** asus-server chết thì chỉ còn đường chạy tay `workflow_dispatch` trên GitHub.

---

## 6. Vấn đề đang tồn tại, chưa xử lý xong

| # | Vấn đề | Mức | Trạng thái / việc cần làm |
|---|---|---|---|
| 1 | **Bài 04/11 (Phủ Tây Hồ) đã đăng với ảnh xoay ngang** trên FB + IG | Cao | Code đã sửa (`a7da11b`). Bài đã đăng không đổi ảnh được qua API → Harry quyết: xoá và đăng lại bằng tay, hoặc để nguyên |
| 2 | **Ảnh bài T7 07/11 (hoa sen) đang nằm ngang trên Drive** | Cao | Harry upload lại ảnh gốc trên Dashboard **trước 09:00 ngày 07/11**. Cần kiểm tra việc đổi ảnh có làm bài phải duyệt lại không |
| 3 | Scorecard đạt từ 05/11 → quyết định `rollout-advance` | Trung bình | Chạy lại scorecard ngày 05/11, **hỏi Harry** trước khi nâng stage, sau đó mới bỏ `--allow-shadow` |
| 4 | Analytics mock, chưa đo hiệu quả thật | Trung bình | Xem nâng cấp U1 |
| 5 | 18 đề xuất Trend Radar đang chờ duyệt (`needs_human_approval`) | Trung bình | Sự kiện đã qua vẫn nằm trong danh sách → cần tự hết hạn + digest |
| 6 | Fast lane chưa được xác nhận đã sinh bài thật end-to-end | Trung bình | Soi kết quả lần đầu có sự kiện được duyệt |
| 7 | guest_voice chạy lần đầu 05/11 | Thấp | Kiểm tra fact sinh ra có đúng dạng "Tháng MM/YYYY · …" |
| 8 | 6 dòng `GATEWAY_ACCEPTED` từ T8–T9 (FB/IG 03/08 + 4 Threads) chưa đối soát | Thấp | Đối soát hoặc đóng lại; Threads không còn dùng |
| 9 | Bảng `publishing_slots` ghi slot 06–14/11 là `PENDING_APPROVAL` trong khi registry đã `APPROVED_SCHEDULED` | Thấp | Trạng thái slot cập nhật trễ; chưa gây lỗi nhưng dễ đọc nhầm khi chẩn đoán |
| 10 | Dashboard: chưa có xác nhận trên trình duyệt rằng ảnh A/B/C hiển thị sau khi sửa CSP (26/10) | Thấp | Harry hard-reload và xác nhận |
| 11 | venho-os trên server còn ~11 commit vn-stock chưa push → auto-deploy Dashboard bị chặn | Trung bình | PR `server/vn-stock-20261022` → main khi phiên vn-stock tiếp tục |
| 12 | Validator không bắt lỗi hình dáng lan can Hồ Tây | Thấp | Xem nâng cấp U7 |
| 13 | Thư viện ảnh mới phải rsync tay từ Mac | Thấp | Xem nâng cấp U5 |

---

## 7. Đề xuất nâng cấp

Xếp theo giá trị/công sức. **Mọi mục đều cần Harry duyệt trước khi làm.**

### Ưu tiên 1: làm ngay (nhỏ, giảm rủi ro trực tiếp)

**U2. Cổng kiểm tra ảnh trước khi đăng (0 chi phí API)**
Ngay trước khi gửi Make, kiểm tra file ảnh cuối cùng:
- Đúng chiều (không còn EXIF xoay).
- Tỉ lệ nằm trong cửa sổ IG.
- Dung lượng < 5 MB.
- URL Drive tải được và đúng ảnh đã chọn.

Có bất thường thì giữ bài lại và báo Telegram, không đăng. Lỗi 04/11 sẽ bị chặn ở bước này.

**U3. Dashboard xem trước đúng file sẽ đăng**
Thumbnail trên Duyệt bài phải là file đã qua `to_upload_jpeg` + `normalize_for_instagram`, không phải ảnh gốc. Harry duyệt đúng thứ sẽ lên.

**U4. Kiểm tra sau khi đăng**
Khoảng 5 phút sau khi đăng, gọi Graph API lấy bài theo `platform_post_id`: kiểm tra bài tồn tại, có ảnh, kích thước ảnh. Gửi Telegram kèm link bài để Harry xem nhanh. Bài vào `GATEWAY_ACCEPTED` mà không lên `PUBLISHED` sau 1 giờ → cảnh báo.

**U6. Dọn tồn đọng**
- Trend candidate có ngày sự kiện đã qua → tự `expired`.
- Đóng 6 dòng `GATEWAY_ACCEPTED` cũ.
- Đồng bộ trạng thái `publishing_slots` theo registry.

### Ưu tiên 2: tạo giá trị kinh doanh

**U1. Nối Meta Insights thật (vòng phản hồi)**
- Thay `MockMetricsAdapter` bằng Graph API: reach, engagement, saves, link clicks (UTM đã có sẵn trong `tracking_url`).
- Lấy số 24h / 72h / 7 ngày sau khi đăng.
- Báo cáo tuần qua Telegram: top/bottom bài, theo pillar, theo loại ảnh (AI / ảnh thật / upload).
- Giai đoạn đầu chỉ báo cáo, không tự điều chỉnh. Agent đưa gợi ý (advisory) để Harry duyệt.
- Dùng Page token đã có từ dự án MCE-02 nếu đủ quyền `read_insights`.

**U8. Bỏ hoặc thay lựa chọn ảnh B**
B chỉ được chọn 2/31 lần. Thay B bằng một **ảnh thật thứ hai** từ thư viện để giảm chi phí sinh ảnh AI và tăng lựa chọn ảnh thật, vì Harry chọn ảnh thật 55% số lần.

**U9. Giảm phụ thuộc duyệt đúng hạn**
- Nhắc Telegram lúc 24h và 6h trước khi bài hết hạn duyệt.
- Có thể cho phép **tự duyệt có điều kiện** cho lane evergreen sau khi rollout lên stage cao hơn: QC ảnh ≥ ngưỡng, naturalness pass, không có fact mới. Việc này cần Harry quyết.

### Ưu tiên 3: nền tảng (làm khi có thời gian)

**U5. Thư viện ảnh không phụ thuộc Mac**
Một thư mục Google Drive "Growth Library" để Harry thả ảnh từ điện thoại; server tự kéo về hằng ngày (HEIC → JPEG, xoay đúng chiều, gán subject theo thư mục).

**U7. Bịt điểm mù QC ảnh**
- Thêm kiểm tra hình dáng lan can bằng ảnh tham chiếu thật đã có trong assets.
- Cho QC growth đọc scenario overlay, hoặc ghi rõ trong docs rằng luật phải sửa thẳng vào DNA JSON.

**U10. Chuyển trạng thái khỏi JSON-trong-git**
Server giữ `growth.db` làm nguồn chính duy nhất. Dashboard đọc qua API của server thay vì đồng bộ file qua GitHub. Git chỉ giữ bản xuất định kỳ để backup. Việc này bỏ được script gộp, cờ skip-worktree và các xung đột push.

**U11. Làm rõ rollout stage**
Sau khi nâng stage: bỏ `--allow-shadow` và đổi tên hoặc ghi chú để "shadow" nghĩa đúng là "không đăng". Thêm test bảo đảm script dispatch và stage luôn khớp nhau.

**U12. Dự phòng máy chủ**
- Watchdog từ bên ngoài (GitHub Actions hoặc Mac) kiểm tra server có chạy lượt 09:00 không.
- Nếu không: báo Telegram và hướng dẫn bấm `workflow_dispatch` (không tự chạy, để tránh đăng trùng).
- Backup `growth.db` + registry hằng ngày lên Drive.

### Lộ trình gợi ý

| Tuần | Việc |
|---|---|
| 05–08/11 | Xử lý vấn đề #1, #2, #3; U2, U6 |
| 09–15/11 | U3, U4, U8 |
| 16–30/11 | U1 (Insights, chỉ báo cáo), U9 nhắc hạn duyệt |
| 12/2026 | U5, U7, U10, U11, U12 |

---

## 8. Quy tắc vận hành cần giữ

- **Không** thêm lại `schedule` vào workflow publish trên GitHub (đăng trùng).
- **Không** bỏ `--allow-shadow` khi stage còn `shadow` (dừng toàn bộ việc đăng).
- **Không** `uv run` trong `~/venho/growth-runtime/venho-ai-studio`, vì lệnh này gỡ extras drive/gemini khỏi `.venv`. Chạy test bằng `uv run --no-sync --with pytest`, khôi phục bằng `uv pip install --python .venv/bin/python -e ".[drive,gemini]"`.
- **Không** commit hay đổi nhánh trong `~/venho/03_AI_STUDIO/venho-ai-studio` (checkout của Dashboard).
- Test không đăng thật: `publication_id` phải chứa `test`.
- Ảnh thư viện mới: thả vào `assets/raw/<subject>/` trên Mac rồi rsync lên server.
- Thêm thư viện Python: `uv lock` và commit `uv.lock` cùng lúc.
- Luật QC ảnh của growth phải sửa trong DNA JSON, không phải `overrides.yaml`.
