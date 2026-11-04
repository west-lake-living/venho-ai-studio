# GC2 — Kiểm kê hạ tầng & dữ liệu legacy

## Host
Nguồn: `ops/asus-server/growth-engine/preflight-host.sh`, Harry chạy trên asus-server ngày 2026-11-05.

| Mục | Kết quả | Đánh giá |
|---|---|---|
| Python runtime (`~/venho/growth-runtime/.../.venv`) | 3.11.16 | OK (`>=3.9`) |
| SQLite của Python runtime | **3.53.1** | OK, ≥ 3.51.3 (ADR-01) |
| Python hệ thống | 3.14.4, SQLite **3.46.1** | **Dưới ngưỡng ADR-01** — service GC2 không được chạy bằng Python hệ thống |
| WAL + `BEGIN IMMEDIATE` + `foreign_keys` | `ok journal_mode=wal foreign_keys=1` | OK |
| Dung lượng trống | ~795 GB | OK |
| Timezone hệ thống | `Etc/UTC` | OK; GC2 dùng `Asia/Ho_Chi_Minh` tường minh qua `BusinessCalendar`, không dựa timezone host |
| Lệch đồng hồ | 0 s | OK |
| Linger (`systemctl --user`) | yes | OK |
| `uv` / `cloudflared` | có / có | OK |
| `age` | **không có** | Cần cài trước P6 (backup mã hoá, GC2-D06) |
| `STATE_DIR` `~/venho/state/growth-engine` | chưa tồn tại | Tạo ở P2/P9 |

Cổng đang nghe: 22, 53, 3000, 3099, 4321, 5678, 8000, 8011, 8020, 8022, 8043, 8088, 8642, 8787, 8843, 9098, 20241, và các cổng cao.
**Cổng trống đề xuất cho `growth-engine-api`: 8021** (dự phòng 8023, 8024). Tránh 8020/8022 (đang dùng) và 8011 (đã bị spec v1.0 cảnh báo, chủ sở hữu chưa xác minh).

### Việc phát sinh
- [ ] Chạy lại bản script mới (`ssh <host> 'bash -s' < preflight-host.sh`) để ghi thêm `python_uv` (kết quả 05/11 là bản script cũ, chưa có khoá này).
- [ ] Cài `age` trên server trước P6.
- [ ] Ghi vào ADR-01: service GC2 chạy bằng venv runtime riêng (Python 3.11, SQLite 3.53.1); `doctor` phải kiểm `sqlite3.sqlite_version` của đúng interpreter đó.
- [ ] Xác minh chủ sở hữu cổng 8011 và 8020/8022 nếu cần dùng dải khác.

## Dữ liệu legacy

Nguồn đọc tại checkout ngày 04/11/2026; chỉ đọc, không sửa dữ liệu trong `data/`.

### Publication registry

`data/projects/venho_hotel/publishing/publication_registry.json` có root key `publications` và **265** bản ghi. Tổng khớp báo cáo 04/11, không có chênh lệch.

| Trạng thái | Facebook | Instagram | Threads | Zalo | Tổng |
|---|---:|---:|---:|---:|---:|
| `APPROVED_SCHEDULED` | 6 | 6 | 0 | 0 | 12 |
| `CANCELLED` | 15 | 10 | 4 | 0 | 29 |
| `DISABLED` | 1 | 0 | 0 | 6 | 7 |
| `FAILED` | 13 | 4 | 0 | 0 | 17 |
| `GATEWAY_ACCEPTED` | 1 | 1 | 4 | 0 | 6 |
| `PENDING_APPROVAL` | 4 | 4 | 0 | 0 | 8 |
| `PUBLISHED` | 35 | 46 | 0 | 0 | 81 |
| `REJECTED` | 11 | 4 | 1 | 1 | 17 |
| `STALE_APPROVAL` | 1 | 2 | 0 | 0 | 3 |
| `SUPERSEDED` | 22 | 21 | 21 | 21 | 85 |
| **Tổng** | **109** | **98** | **30** | **28** | **265** |

Các field cấp bản ghi (không lưu giá trị nhạy cảm trong inventory): `approval_revoked_reason`, `approval_scope`, `approval_snapshot`, `approved_at`, `approved_by`, `cancellation_reason`, `cancelled_by`, `cancelled_reason`, `claims`, `content`, `content_package_id`, `created_at`, `creative_brief`, `creative_brief_id`, `day`, `dna_subject`, `edit_validation`, `edited_by`, `gateway_error`, `gateway_status`, `idempotency_key`, `incident_retired_at`, `incident_retired_reason`, `package_snapshot`, `permalink`, `pillar`, `platform`, `platform_post_id`, `published_at`, `reconciled_by`, `reconciliation_proof`, `rejected_by`, `rejected_reason`, `replacement_publication_id`, `replaces_publication_id`, `rollout_stage`, `scene_summary`, `scorecard_signals`, `shadow_held_reason`, `shadow_override_by`, `slot_id`, `stale_at`, `stale_reason`, `status`, `superseded_by_publication_id`, `topic`, `updated_at`.

### `growth.db` và đối soát slot

Đọc SQLite ở chế độ read-only bằng Python local SQLite 3.51.0. DB có các bảng ứng dụng:

| Bảng | Dòng | Field |
|---|---:|---|
| `budget_events` | 633 | `id`, `reservation_id`, `action`, `amount_minor`, `currency`, `created_at` |
| `budget_overrides` | 0 | `id`, `reservation_id`, `amount_minor`, `currency`, `reason`, `approved_by`, `created_at` |
| `jobs` | 7 | `id`, `idempotency_key`, `job_type`, `version`, `status`, `attempt`, `max_attempt`, `lease_owner`, `lease_expiry`, `scheduled_at`, `trace_id`, `payload`, `last_error`, `last_heartbeat_at` |
| `publishing_slots` | 58 | `slot_id`, `slot_date`, `slot_type`, `lane`, `status`, `content_package_id`, `filled_from`, `updated_at`, `closed_reason` |

`publishing_slots.status`: 43 `COMPLETED`, 10 `PENDING_APPROVAL`, 5 `MISSED`. Registry có 63 `slot_id` duy nhất; 58 khớp DB, 5 chỉ có trong registry, 0 chỉ có trong DB. Không có bảng publication trong SQLite này; trạng thái publication lấy từ JSON registry.

Có 23 cặp lặp `slot_id + platform` (33 dòng vượt ngoài một bản ghi/cặp), với các trạng thái hủy, lỗi, từ chối, đã đăng và thay thế. Một cặp đáng đối soát riêng là slot 15/08 trên Instagram có **hai** bản ghi `PUBLISHED`; không tự retry/import như một bài chưa đăng. Các dòng `publishing_slots` có `slot_id` riêng, không bị trùng.

### Trường hợp cần giữ nguyên khi migration

- 6 `GATEWAY_ACCEPTED`: Facebook 1, Instagram 1, Threads 4; cả sáu thiếu `platform_post_id`, `permalink` và `published_at`. Không nâng thành `PUBLISHED` nếu chưa có bằng chứng.
- 3 `STALE_APPROVAL`: Facebook 1, Instagram 2; approval cũ không đủ để tự khôi phục.
- Instagram có 98 dòng; Threads có 30 dòng lịch sử; Zalo có 28 dòng. Threads/Zalo không được biến thành delivery v2.
- Hai dòng Facebook `PUBLISHED` mang `platform_post_id = "3. Post ID"`; đây là placeholder, không phải ID bài thật.
- Slot 07/11 có bản Facebook và Instagram `APPROVED_SCHEDULED`; commit `9ab0a22` đổi ảnh được chọn sang `U2`. `image_run_path` không có file local. URL ảnh trong snapshot nằm trên Google Drive; không truy cập Drive theo giới hạn lượt chạy nên **chưa xác định được SHA-256**.

Fixture đã lọc/anonymize đặt trong `tests/growth_engine/fixtures/legacy/`; không commit registry, database, nội dung bài, URL ảnh hoặc thông tin duyệt thật. Fixture đánh dấu `_synthetic: true` theo yêu cầu prompt và cần thay bằng fixture thật từ P0-T03/P0-T04.
