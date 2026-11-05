# GC2 — Manifest đích (2 Facebook Page + Instagram production ID + Facebook/Instagram TEST)

> **Không ghi secret** vào file này (token, URL webhook, Client Secret). Chỉ ghi định danh và *tên* biến môi trường.
> Sau khi điền, chạy: `python3 scripts/growth_engine/check_manifest_no_secrets.py` (phải trả 0) và
> `python3 scripts/growth_engine/check_manifest_no_secrets.py --require-filled` (phải trả 0 trước G-P0).
> Nguồn máy đọc: `config/projects/venho_hotel/growth_engine/channels.yaml` — hai file phải khớp nhau.

Chuỗi định danh (§8.1.5): `channel_id → remote_page_id → tên Page → Make scenario ID → webhook route ref → connection ref → Graph API version → principal + scopes → owner → ngày xác minh`.
Không map bằng tên hiển thị; đổi tên Page không đổi channel; Page ID khác = channel khác.

## Production

| Trường | Page A (`page_a`) | Page B (`page_b`) |
|---|---|---|
| Tên Page hiển thị | Ven Hồ Hotel Hanoi | Ven Hồ Hotel |
| `remote_page_id` | `1124616474074140` | `803531149684177` |
| Make scenario ID | `null` — chưa xác minh | `null` — chưa xác minh |
| Route ref (tên env) | `GE_MAKE_WEBHOOK_URL_PAGE_A` | `GE_MAKE_WEBHOOK_URL_PAGE_B` |
| Make connection (tên) | `null` — chưa xác minh | `null` — chưa xác minh |
| Graph API version | `null` — chưa probe P0-T04 | `null` — chưa probe P0-T04 |
| Principal | `make-fb-hanoi` | `make-fb-venho` |
| Scopes | `executions.authorize`, `receipts.write`, `media.read` | như Page A |
| Env token đọc Meta (tên) | `GE_META_READ_TOKEN_PAGE_A` | `GE_META_READ_TOKEN_PAGE_B` |
| Owner | `null` — chưa chỉ định | `null` — chưa chỉ định |
| Ngày xác minh route | `null` — ID do Harry cung cấp, route chưa xác minh | `null` — ID do Harry cung cấp, route chưa xác minh |
| Trạng thái | disabled | disabled |

Instagram là kênh đăng v2: `ig_venho` → `instagram_business_account.id` `17841457936965829`; Make route/connection và Graph API version/token chưa probe; channel disabled tới khi xác minh.

## Test (Page/Instagram test riêng + scenario test riêng)

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

Instagram TEST dùng `ig_test`; account ID, scenario, connection, owner và ngày xác minh đều `REQUIRED_FROM_P0`. Không dùng `ig_venho` cho thử nghiệm có side effect.

## Cách Harry xác minh Page ID (không cần token)
- Facebook → vào Page → *Giới thiệu / About* → *Minh bạch của Trang* → *Page ID*; hoặc URL `facebook.com/profile.php?id=<số>`.
- Ghi dạng **chuỗi**, không có dấu phân tách.
