# GC2 — Manifest đích (2 Page production + 1 Page test)

> **Không ghi secret** vào file này (token, URL webhook, Client Secret). Chỉ ghi định danh và *tên* biến môi trường.
> Sau khi điền, chạy: `python3 scripts/growth_engine/check_manifest_no_secrets.py` (phải trả 0) và
> `python3 scripts/growth_engine/check_manifest_no_secrets.py --require-filled` (phải trả 0 trước G-P0).
> Nguồn máy đọc: `config/projects/venho_hotel/growth_engine/channels.yaml` — hai file phải khớp nhau.

Chuỗi định danh (§8.1.5): `channel_id → remote_page_id → tên Page → Make scenario ID → webhook route ref → connection ref → Graph API version → principal + scopes → owner → ngày xác minh`.
Không map bằng tên hiển thị; đổi tên Page không đổi channel; Page ID khác = channel khác.

## Production

| Trường | Page A (`page_a`) | Page B (`page_b`) |
|---|---|---|
| Tên Page hiển thị | REQUIRED_FROM_P0 | REQUIRED_FROM_P0 |
| `remote_page_id` | REQUIRED_FROM_P0 | REQUIRED_FROM_P0 |
| Make scenario ID | REQUIRED_FROM_P0 | REQUIRED_FROM_P0 |
| Route ref (tên env) | `GE_MAKE_WEBHOOK_URL_PAGE_A` | `GE_MAKE_WEBHOOK_URL_PAGE_B` |
| Make connection (tên) | REQUIRED_FROM_P0 | REQUIRED_FROM_P0 |
| Graph API version | REQUIRED_FROM_P0 | REQUIRED_FROM_P0 |
| Principal | `make-page-a` | `make-page-b` |
| Scopes | `executions.authorize`, `receipts.write`, `media.read` | như Page A |
| Env token đọc Meta (tên) | `GE_META_READ_TOKEN_PAGE_A` | `GE_META_READ_TOKEN_PAGE_B` |
| Owner | REQUIRED_FROM_P0 | REQUIRED_FROM_P0 |
| Ngày xác minh | REQUIRED_FROM_P0 | REQUIRED_FROM_P0 |

## Test (Page test riêng + scenario test riêng)

| Trường | Page test (`page_test`) |
|---|---|
| Tên Page hiển thị | REQUIRED_FROM_P0 |
| `remote_page_id` | REQUIRED_FROM_P0 |
| Make scenario ID | REQUIRED_FROM_P0 |
| Route ref (tên env) | `GE_MAKE_WEBHOOK_URL_PAGE_TEST` |
| Make connection (tên) | REQUIRED_FROM_P0 |
| Graph API version | REQUIRED_FROM_P0 |
| Principal | `make-page-test` |
| Env token đọc Meta (tên) | `GE_META_READ_TOKEN_PAGE_TEST` |
| Owner | REQUIRED_FROM_P0 |
| Ngày xác minh | REQUIRED_FROM_P0 |

`publication_id` chứa `test` chỉ là lớp phụ; Page test và scenario test mới là cơ chế chính ngăn bài test lên Page thật.

## Cách Harry xác minh Page ID (không cần token)
- Facebook → vào Page → *Giới thiệu / About* → *Minh bạch của Trang* → *Page ID*; hoặc URL `facebook.com/profile.php?id=<số>`.
- Ghi dạng **chuỗi**, không có dấu phân tách.
