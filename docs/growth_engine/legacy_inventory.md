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
(Chưa làm — GC2-P0-T07.)
