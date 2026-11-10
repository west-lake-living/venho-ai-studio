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

### Ánh xạ Meta token production

`channels.yaml` và probe hiện dùng hai họ tên biến cho cùng ba tài khoản. Giữ cả hai họ trong production environment file cho đến khi mã được thống nhất; mỗi cặp dưới đây phải nhận cùng Page/account token tương ứng:

| `channels.yaml` tham chiếu | Kênh | Tên biến probe | Giá trị |
|---|---|---|---|
| `GE_META_READ_TOKEN_PAGE_A` | `fb_hanoi` / Page `1124616474074140` | `GE_META_READ_TOKEN_FB_HANOI` | Cùng token của Page Hanoi |
| `GE_META_READ_TOKEN_PAGE_B` | `fb_venho` / Page `803531149684177` | `GE_META_READ_TOKEN_FB_VENHO` | Cùng token của Page Ven Hồ |
| `GE_META_READ_TOKEN_IG_VENHO` | `ig_venho` / account `17841457936965829` | `GE_META_READ_TOKEN_IG_VENHO` | Cùng token dùng cho account Instagram |

`Settings` đọc mọi biến có tiền tố `GE_META_READ_TOKEN_` và trong production chỉ yêu cầu có ít nhất một biến; nếu biến được khai báo thì từng giá trị không được rỗng hoặc chứa `REQUIRED_FROM_P0`. Nó không kiểm tra các tên biến riêng lẻ trong `channels.yaml`. Để thỏa manifest và probe, production file cần đủ cả năm tên production trong bảng ánh xạ (ba tên probe và hai alias PAGE_A/PAGE_B). TEST refs `GE_META_READ_TOKEN_PAGE_TEST` và `GE_META_READ_TOKEN_IG_TEST` thuộc environment TEST; chúng không phải các token probe production.

## Test (Page/Instagram test riêng + scenario test riêng)

| Trường | Page test (`page_test`) |
|---|---|
| Tên Page hiển thị | Ven Hồ Growth Test |
| `remote_page_id` | `1363761820162798` |
| Make scenario ID | `6924867` — VenHo Growth Agent TEST |
| Route ref (tên env) | `GE_MAKE_WEBHOOK_URL_PAGE_TEST` |
| Make connection (tên) | `Ven Ho Hotel Hanoi (Ha Pham)` — ID số CHƯA XÁC MINH; runner đăng thử không dùng trường này |
| Graph API version | `v27.0` — Harry đọc từ Graph API Explorer của Meta app đang dùng ngày 2026-11-10 |
| Principals | `make-fb-hanoi`, `make-fb-venho` (bearer TEST riêng cho từng nhánh) |
| Env token đọc Meta (tên) | `GE_META_READ_TOKEN_PAGE_TEST` |
| Owner | Harry |
| Ngày xác minh | 2026-11-10 |

Page TEST Graph API ID là `1363761820162798`. Cảnh báo: `61596076389732` trong URL `facebook.com/profile.php?id=61596076389732` là định danh URL hồ sơ, **không phải** Graph API Page ID; không dùng giá trị đó làm `remote_page_id`.

`publication_id` chứa `test` chỉ là lớp phụ; Page test và scenario test mới là cơ chế chính ngăn bài test lên Page thật.

Instagram TEST dùng tài khoản `@hanhpham1504`, ID `17841472240799413`, đã được chuyển sang Business và liên kết với Page TEST `1363761820162798`. ID do Harry cung cấp; không thay bằng ID production `17841457936965829`. Kênh dùng scenario `6924867`, Graph API `v27.0` (Harry đọc trong Graph API Explorer của Meta app đang dùng ngày 2026-11-10), connection tên `Ven Ho Hotel Hanoi (Ha Pham)`, owner Harry và ngày xác minh 2026-11-10. ID số của connection Make CHƯA XÁC MINH; runner `fb_hanoi` không đọc `make_connection_ref`, nên không cần ID đó để tạo/gửi command TEST. Không dùng `ig_venho` cho thử nghiệm có side effect.

## Cách Harry xác minh Page ID (không cần token)
- Facebook → vào Page → *Giới thiệu / About* → *Minh bạch của Trang* → *Page ID*; hoặc URL `facebook.com/profile.php?id=<số>`.
- Ghi dạng **chuỗi**, không có dấu phân tách.
