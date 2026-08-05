# Growth Golden Eval Sets

**Cập nhật 2026-08-06.** Ghi rõ khoảng cách giữa "golden eval set" plan gốc muốn (Part 13.4) và những gì `venho-rollout scorecard` thật sự chấm được hôm nay từ dữ liệu pilot thật — không đánh đồng hai thứ.

## Golden set gốc theo plan (Part 13.4) — chưa xây

- Content set ≥100 CreativeBrief case (audience × funnel × factual conflict × local topics × offers × 2 platforms), reviewer-scored.
- Image set ≥60 case (phòng thật, rooftop, street, local food, Linh An static/dynamic, mọi target crop).
- Trend set ≥40 case, ≥15 case thuộc danh mục cấm để test kill switch.
- Dataset version hoá riêng, chạy trong workflow paid eval có budget cap duyệt riêng, không nằm trong CI thường.

**Chưa làm.** Xây một bộ này cần Harry ngồi review/gán điểm thủ công hàng chục case — việc tốn thời gian thật, không tự động hoá được bằng code, và chưa có lịch. Ghi nhận là gap có chủ đích, không phải quên.

## Scorecard thật hiện có — `venho-rollout scorecard`

Vì golden set chính thức chưa tồn tại, `controlled_rollout.collect_real_scorecard_metrics()` chấm điểm bằng **dữ liệu pilot thật đã có** (publication đã đăng thật, `PublicationRegistry` + `SlotStore`) thay vì bộ case đã curate — đây là **pilot telemetry scorecard**, không phải golden eval set. Dùng để quyết định `rollout-advance` có được phép tiến stage hay không (Phần 12 Phase 8), không phải con số cuối cùng cho DoD #26.

Minimum P8 gate: scorecard `>= 9.3/10` — logic giữ nguyên từ plan gốc (`controlled_rollout/scorecard.py::evaluate_golden_set`).

### 9 chỉ tiêu — nguồn dữ liệu thật hôm nay

| Chỉ tiêu | Nguồn thật | Trạng thái |
|---|---|---|
| `critical_factual_precision` | `ClaimValidator` kill-switch per publication (persisted `scorecard_signals.claim_kill_switch_triggered`) | Có, từ 2026-08-06 trở đi |
| `brand_adherence` | `content_validator`'s `brand_fit` dimension (persisted `scorecard_signals.content_brand_fit`) — **proxy thật, không phải công cụ đo giống hệt plan gốc hình dung (reviewer-scored)** | Có (proxy), từ 2026-08-06 trở đi |
| `duplicate_publication` | Invariant kiểm chứng được từ `PublicationRegistry` (idempotency_key+platform lock) | Có, luôn 0 theo kiến trúc |
| `publication_post_id_rate` | `PublicationRegistry` — % `PUBLISHED` có `platform_post_id` | Có |
| `human_acceptance_no_major_edit` | `PublicationRegistry` — % `PUBLISHED` không có `edited_by` | Có |
| `unplanned_empty_days` | `SlotStore.list_all(status="MISSED")` | Có |
| `copy_image_alignment` | Cần `validator_studio.image_validator` chạy thật (paid Vision QC) mỗi publication | **Thiếu** — `daily_cycle` mặc định `image_validation_provider="mock"` để tiết kiệm ngân sách 500k/tháng |
| `hotel_dna_pass` | Như trên | **Thiếu** |
| `linh_an_identity_pass` | Như trên | **Thiếu** |

Trước 2026-08-06, publication không có `scorecard_signals` trên registry row — chỉ publication từ nay trở đi mới tính được `critical_factual_precision`/`brand_adherence` thật; đây là dữ liệu tích luỹ theo thời gian, không hồi tố được cho các bài đã đăng trước đó.

### Cách chạy thật

```bash
venho-rollout scorecard --version growth-pilot-2026-08
```

Trả về `score`, `passed`, `failures` (bao gồm `missing:<key>` cho 3 chỉ tiêu ảnh chưa có), `sample_size` (số publication PUBLISHED thật), và `data_gaps` (lý do cụ thể từng chỉ tiêu thiếu).

### Vì sao chưa "pass" hôm nay

`sample_size` còn rất nhỏ (Growth Agent mới chạy thật vài ngày) và 3/9 chỉ tiêu luôn `missing` cho tới khi Vision QC thật được bật thường xuyên — `evaluate_golden_set()` coi field thiếu là gate fail, nên scorecard thật hôm nay hầu như luôn `passed=False`. Đây là hành vi đúng theo thiết kế (cùng kiểu "INCONCLUSIVE" honest gate như Phase 7's `strategy_memory`), không phải lỗi.
