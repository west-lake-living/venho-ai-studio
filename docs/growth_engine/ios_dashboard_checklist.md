# Growth Engine Dashboard — kiểm tra Safari trên iPhone

**Trạng thái:** chờ Harry kiểm thủ công. Chỉ dùng môi trường TEST hoặc dữ liệu fixture; không đăng bài công khai.

| Thông tin chạy | Giá trị |
|---|---|
| Build / commit venho-os |  |
| API backend / môi trường |  |
| Thiết bị và iOS |  |
| Thời điểm ICT |  |
| Người kiểm tra |  |

Mỗi bước ghi `PASS`, `FAIL` hoặc `BLOCKED`. Chụp ảnh màn hình, che email, URL nội bộ và mọi dữ liệu phiên đăng nhập trước khi lưu.

## 1. CSP và ảnh xem trước qua Access

- Mở Publishing → Growth Engine bằng Safari, đã đăng nhập VENHO OS và qua Cloudflare Access.
- Từ bản duyệt fixture, chạm ảnh để mở đúng artifact đã chuẩn hoá ở kích thước đầy đủ.
- Trong DevTools/proxy log có thể xem, xác nhận ảnh tải trực tiếp trong phiên Access; console không có CSP `img-src` violation và không có trang login HTML bị hiển thị như ảnh.
- Kết quả: ____  ·  Ảnh chụp: ____________________

## 2. Hai Page với trạng thái một phần

- Dùng fixture hiển thị một slot có hai target và trạng thái khác nhau (ví dụ Page Hanoi `PUBLISHED`, Page Ven Hồ `UNKNOWN` hoặc `BLOCKED`). Không gọi publish.
- Xác nhận hai Page nằm trong cùng slot nhưng có nhãn, trạng thái và link riêng; trạng thái một Page không che hoặc ghi đè Page còn lại.
- Với `UNKNOWN`, chỉ thấy **Đối soát**; không có nút thử lại/đăng lại.
- Kết quả: ____  ·  Ảnh chụp: ____________________

## 3. Tab cũ và If-Match

- Mở cùng một delivery ở hai tab test. Lưu một thay đổi ở tab A để tăng `row_version`.
- Thử lưu bản cũ từ tab B. API phải trả `412`; UI hiện thông báo và yêu cầu tải lại, không báo thành công.
- Xác nhận không có public post nào được tạo trong bước này.
- Kết quả: ____  ·  Ảnh chụp: ____________________

## 4. Tải ảnh HEIC từ iPhone

- Chọn một ảnh HEIC trong môi trường TEST, dưới giới hạn 25 MiB.
- Xác nhận upload hiển thị “Đang xử lý”, poll job tới trạng thái kết thúc, xem preview variant đã chuẩn hoá, rồi chủ động bấm **Dùng ảnh này**.
- Bản mới phải trở về trạng thái cần duyệt lại. Upload hoặc xử lý thất bại phải hiện lỗi và không đổi ảnh hiện hành.
- Kết quả: ____  ·  Ảnh chụp: ____________________

## 5. Thao tác một tay

- Kiểm ở Safari chiều rộng 375 px, gồm safe-area phía dưới.
- Thử lọc “Chờ tôi duyệt”, mở/đóng Review Sheet, chọn Page, bấm thanh duyệt dính đáy, mở đối soát và điều khiển pause/resume.
- Xác nhận không cần zoom; nút không bị nav/home indicator che; trạng thái luôn có chữ/icon chứ không chỉ màu.
- Kết quả: ____  ·  Ảnh chụp: ____________________

## Ký xác nhận

- Tổng kết: ____ / 5 PASS · ____ FAIL · ____ BLOCKED
- Lỗi cần xử lý / commit liên quan: __________________________________________
- Harry xác nhận: ____________________  ·  Ngày: ____________________
