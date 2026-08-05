# Growth Agent Controlled Rollout Runbook

**Cập nhật 2026-08-06.** Mô tả đúng kiến trúc thật đang chạy (GitHub Actions on-demand + `venho-os`, Phần 10 master plan) — không phải thiết kế Mac Mini 24/7 gốc. Vận hành thật qua CLI `venho-rollout`.

## Runbook

- Growth Agent live thật từ 2026-08-03/04. Rollout stage thật hiện tại: **`shadow`** (mặc định — chưa có quyết định nào tiến lên `pilot_25`).
- 4 stage: `shadow -> pilot_25 -> pilot_50 -> pilot_100`. **Mọi stage vẫn giữ nguyên approval thủ công 100%** — tiến stage không tự động bật auto-approval; `final_approval_required`/`m03_mandatory_before_review` không bao giờ tắt (Phần 14). Auto-approval phạm vi hẹp chỉ xảy ra khi có quyết định riêng, tường minh của Harry — chưa có quyết định đó.
- Lane đặc biệt T7 (trend) **không bao giờ** tự động tiến lên auto-approval kể cả ở `pilot_100` — enforce cứng trong `rollout_policy.next_rollout_stage()`.
- Kiểm tra trạng thái: `venho-rollout rollout-status`
- Chấm điểm thật + thử tiến stage: `venho-rollout rollout-advance --scorecard-version <tag> --metrics-days <N>` — luôn chạy `scorecard` thật trước (xem `eval_golden_sets.md`), không có đường nào tiến stage dựa trên tuyên bố chất lượng chưa verify. Exit code 1 nếu bị chặn (đúng hành vi, không phải lỗi).
- Chạy `hotel-content-engine` cho hotel #2 (chỉ đọc config, không sửa core): `venho-rollout productize-run --project <hotel_id> --brief-json <path>`.

## Rollback

- **Tắt dispatch trước khi rollback approval/validation flag** — thứ tự bắt buộc, `rollback_sequence()` raise nếu gọi sai thứ tự.
- Migration forward-only, compatible reads bắt buộc.
- Approved artifacts bất biến — rollback không được sửa artifact đã duyệt.
- Git export luôn khả dụng để phục hồi (registry JSON + vault đều git-tracked, Phần 10.4).
- Lệnh: `venho-rollout rollback-plan --disable-dispatch-done/--no-disable-dispatch-done`.

## Budget

- Cap thật: **500,000 VND/tháng** (Harry chốt 2026-08-06, `config/projects/venho_hotel/growth/budget_policy.yaml`), enforce cứng qua `BudgetGate` quanh 3 điểm gọi API thật (text gen, image gen, vision QC) trong `daily_cycle.py` — chạm cap raise `RuntimeError`, không crash cả pipeline.
- Alert Telegram `budget_threshold_crossed` ở 70/85/100%.
- Chi phí ước tính/lệnh gọi: `paid_call_costs.yaml` (300/1200/400 VND text/ảnh/vision) — **ước lượng thô, chưa đối chiếu hoá đơn thật**, cần Harry hiệu chỉnh khi có billing thật.
- Vision QC mặc định vẫn `mock` trong production hôm nay (chưa bật paid Vision QC thường xuyên) — nghĩa là 3/9 chỉ tiêu scorecard (`copy_image_alignment`/`hotel_dna_pass`/`linh_an_identity_pass`) chưa có dữ liệu thật, xem `eval_golden_sets.md`.

## Ownership

- M03 (`validator_studio/`) sở hữu duy nhất validation.
- M04 (`automation_studio/approval_snapshot.py`) sở hữu approval exact-version.
- M07 (`publishing_gateway/`) sở hữu publish/idempotency/reconciliation.
- M08 (`analytics_feedback/`) sở hữu metrics/attribution.
- M09-adjacent `strategy_memory/` sở hữu advisory recommendation (Phase 7).
- `controlled_rollout/` (Phase 8, gói này) chỉ đọc dữ liệu thật từ các module trên để chấm điểm/quyết định stage — **không tạo, không sửa content, không publish**.
- M10 (`venho-os`) chỉ trình bày; duyệt/dispatch thật xảy ra khi Harry bấm nút trên `venho-os`, không có tiến trình nền nào publish tự động (Phần 10.3).

## Trạng thái thật hôm nay (không giả vờ đã xong)

- Rollout stage: `shadow`, chưa từng tiến lên vì chưa chạy `scorecard` thật đạt ngưỡng.
- Scorecard thật: 6/9 chỉ tiêu có nguồn dữ liệu thật (`critical_factual_precision`, `brand_adherence`, `duplicate_publication`, `publication_post_id_rate`, `human_acceptance_no_major_edit`, `unplanned_empty_days`); 3/9 còn thiếu (ảnh — cần Vision QC thật, tốn phí, chưa bật thường xuyên).
- Golden eval set gốc kiểu plan (>=100 case, reviewer-scored, dataset version riêng) **chưa được xây** — `venho-rollout scorecard` dùng dữ liệu pilot thật thay thế, không phải golden set chính thức. Xem `eval_golden_sets.md`.
