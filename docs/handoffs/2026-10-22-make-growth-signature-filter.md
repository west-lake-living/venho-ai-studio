# Handoff: thêm filter chữ ký `X-Venho-Signature` vào scenario Growth trên Make.com

- **Ngày giao:** 22/10/2026
- **Người giao:** Harry Pham (soạn bởi Claude Code)
- **Người làm:** Codex, thao tác trên Make.com qua Chrome extension, trong trình duyệt Harry đã đăng nhập sẵn
- **Hạn:** trước lượt đăng bài thật lúc **09:00 ngày 23/10/2026** (giờ Việt Nam). Không kịp thì đừng làm dở: để scenario nguyên như cũ.

## 1. Mục tiêu

Hiện ai có URL webhook của scenario Growth đều đăng được bài lên Page Facebook và Instagram của Ven Hồ Hotel. Server đã ký mọi request gửi đi, nhưng Make chưa kiểm tra chữ ký nên chưa chặn được gì.

Việc cần làm: thêm **một filter ngay sau module webhook**. Filter này chỉ cho đi tiếp những request có header `X-Venho-Signature` đúng.

## 2. Phía server đã có sẵn (không cần làm)

- Server (asus-server) gửi bài lên Make mỗi Thứ 2/4/6/7, lúc 09:00 và 17:00.
- Mỗi request có header `X-Venho-Signature` = `HMAC-SHA256(secret, "<publication_id>:<idempotency_key>")`, viết dạng hex chữ thường. Code: `publishing_gateway/adapters/make_gateway.py`, hàm `build_make_webhook_signature`.
- `publication_id` và `idempotency_key` nằm ở cấp gốc của body JSON. Body còn có `platform`, `content` (object) và `image_url`.
- Secret là giá trị `MAKE_GROWTH_WEBHOOK_SECRET`. Bản trên Mac (`venho-ai-studio/.env.local`) và bản trên server (`~/venho/secrets/growth.env`) đã được kiểm là giống nhau.
- Script gửi request thử: `ops/asus-server/make-signature-test.sh`. Script chạy trên server và **không in secret** ra.

## 3. Quy tắc an toàn (bắt buộc)

1. **Không đăng bài thật nào.** Ngày 06/08/2026 đã có payload test lên nhầm Page thật 2 lần:
   - lần 1 vì filter được suy đoán là chặn, chứ không ai mở ra đọc;
   - lần 2 vì sửa filter xong nhưng chưa Save scenario.
2. **Mở ra đọc mọi filter liên quan, không suy đoán.** Với mỗi route, kiểm cả ô **"Set the route as a fallback"**: phải là `No`.
3. **Secret:**
   - Harry tự dán secret vào ô của filter.
   - Không chép secret vào chat, ghi chú hay báo cáo.
   - Không chụp màn hình khi ô chứa secret đang mở.
4. **Lưu đúng cách:**
   - Nút Save trong panel module chỉ đóng panel, không lưu scenario.
   - Phải bấm nút Save (💾) ở thanh công cụ dưới đáy canvas.
   - Sau đó `Cmd+R` tải lại trang, mở lại filter và kiểm xem đã lưu thật chưa.
5. **Sửa một ô:** bấm vào ô, `Cmd+A`, xoá trắng, rồi mới chèn chip hoặc gõ. Kéo chip vào ô đang có nội dung chỉ nối thêm, không thay thế.
6. **Dừng lại và báo Harry, không tự xử lý,** nếu gặp bất kỳ trường hợp nào ở mục 5.

## 4. Các bước

### Bước 1: Tìm đúng scenario và đọc cấu trúc

1. Có 2 scenario riêng biệt, cần chọn đúng:
   - Scenario **Growth Agent**: đúng scenario cần sửa. Nhận biết qua router lọc theo `{{<số module webhook>.platform}}`, caption lấy từ `content.text`, và có một **chốt chặn mọi `publication_id` chứa `test`**.
   - Scenario **legacy** (`venho-social-content-agent`, payload phẳng `url`/`message`/`publish_to_facebook`): **không đụng vào**.
2. Ghi lại các điểm sau, không ghi secret:
   - số module webhook (ví dụ `2`);
   - thứ tự các module ngay sau webhook;
   - chốt `test` nằm ở đâu, điều kiện chính xác là gì;
   - mỗi route Facebook/Instagram có filter gì, ô fallback để `Yes` hay `No`.
3. **Điều kiện để làm tiếp:** chốt `test` phải nằm **trước** mọi module Facebook/Instagram. Không đúng thì dừng lại (mục 5).

### Bước 2: Bật đọc header

1. Mở module **Webhooks > Custom webhook**.
2. Vào **Show advanced settings**, bật **Get request headers** = `Yes`.
3. Bấm OK hoặc Save của panel.

### Bước 3: Thêm filter chữ ký

1. Bấm vào **đường nối ngay sau module webhook**, tức đường nối đầu tiên, trước router và trước chốt `test`. Chọn **Set up a filter**.
2. **Label:** `Venho signature`.
3. **Condition (bên trái):**
   ```
   {{get(map(2.headers; "value"; "name"; "x-venho-signature"); 1)}}
   ```
   Thay `2` bằng số module webhook ghi ở Bước 1.
4. **Operator:** `Text operators` → `Equal to`.
5. **Bên phải:**
   ```
   {{sha256(2.publication_id:2.idempotency_key; "hex"; "SECRET")}}
   ```
   - Thay `2` như trên.
   - Phải có dấu hai chấm `:` nằm giữa hai chip `publication_id` và `idempotency_key`.
   - Thay `SECRET` bằng secret: **Harry tự dán vào**. Khi có tham số thứ ba (key), hàm `sha256` của Make tính HMAC, và `"hex"` cho ra chữ thường, đúng như server.
6. Bấm OK, rồi **Save scenario** (nút dưới đáy canvas). `Cmd+R`, mở lại filter để kiểm cả 3 phần đã lưu đúng.

### Bước 4: Kiểm tra bằng request thử

Chỉ làm bước này khi Bước 1 đã xác nhận chốt `test` nằm trước mọi module Facebook/Instagram.

1. Scenario phải đang **ON** (scheduling bật).
2. Nhờ Harry, hoặc Claude Code theo lời Harry, chạy trên server:
   ```
   ssh asus-server 'bash ~/venho/growth-runtime/venho-ai-studio/ops/asus-server/make-signature-test.sh'
   ```
   Script gửi 2 request:
   - `test-sigcheck-<thời gian>-good`: ký đúng;
   - `test-sigcheck-<thời gian>-bad`: ký sai.
3. Mở **History** của scenario, xem 2 lượt chạy mới nhất:

   | Request | Kết quả đúng |
   |---|---|
   | `...-good` | **Qua** filter `Venho signature`, rồi dừng ở chốt `test` |
   | `...-bad` | **Dừng ngay** ở filter `Venho signature` |
   | Cả hai | **Không** chạm tới module Facebook/Instagram nào |

4. Nếu `-good` cũng bị chặn ở filter chữ ký, mở bundle đầu ra của webhook và xem mảng `headers`:
   - Nếu `name` của header không phải đúng chuỗi `x-venho-signature` (ví dụ có chữ hoa), sửa chuỗi trong `map(...)` cho khớp, Save, rồi thử lại.
   - Nếu `name` đã khớp mà vẫn bị chặn, kiểm lại dấu `:` và tham số `"hex"` ở vế phải.
   - Không đoán thêm, báo Harry.

### Bước 5: Theo dõi bài thật đầu tiên

Bài thật đầu tiên đi qua filter là lượt **09:00 ngày 23/10**.

**Rủi ro cần biết:** nếu filter chặn nhầm một bài thật, Make vẫn trả về "Accepted". Server sẽ ghi bài đó là `GATEWAY_ACCEPTED` và không báo lỗi, nghĩa là bài mất âm thầm.

Cách kiểm sau 09:00 (Harry hoặc Claude Code làm):
- Trên Dashboard, hoặc trong `publication_registry.json`, bài Facebook/Instagram của slot 23/10 phải ở trạng thái `PUBLISHED` và có `platform_post_id`.
- Nếu là `GATEWAY_ACCEPTED`, coi như filter đã chặn nhầm: làm ngay mục 6, rồi đăng bù.

## 5. Khi nào dừng lại và báo Harry

- Không tìm thấy chốt `test`, hoặc chốt nằm sau một module Facebook/Instagram.
- Có route nào để fallback = `Yes`.
- Cấu trúc scenario khác hẳn mô tả ở Bước 1, hoặc không chắc đâu là scenario Growth.
- Kết quả Bước 4 khác bảng ở trên, đặc biệt nếu có lượt chạy chạm tới module Facebook/Instagram.
- Không còn đủ thời gian để xong và kiểm trước 09:00 ngày 23/10.

## 6. Hoàn tác

1. Xoá filter `Venho signature` trên đường nối sau webhook. Có thể để nguyên tuỳ chọn **Get request headers**: nó không ảnh hưởng gì.
2. Save scenario, `Cmd+R`, kiểm lại.

Scenario khi đó chạy đúng như trước khi sửa.

## 7. Báo cáo lại cho Harry

- Tên scenario đã sửa, và số module webhook.
- Cấu trúc đọc được ở Bước 1: chốt `test` nằm ở đâu, điều kiện là gì, các route đặt fallback ra sao.
- Đã bật Get request headers chưa. Filter đã lưu chưa, và đã kiểm lại sau khi `Cmd+R` chưa.
- Kết quả Bước 4: trạng thái của 2 lượt `-good` và `-bad` trong History, kèm thời gian.
- Mọi điểm khác với tài liệu này.
- **Không** đưa secret vào báo cáo.
