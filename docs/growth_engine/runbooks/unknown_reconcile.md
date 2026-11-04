# Đối soát bài `UNKNOWN`

`UNKNOWN` nghĩa là hệ thống chưa thể chứng minh bài đã được tạo hay chưa. Không gửi lại command khi trạng thái còn `UNKNOWN`.

## Nếu tìm thấy bài trên Page

1. Mở đúng Facebook Page theo Page ID của delivery; kiểm tra bài có đúng caption/ảnh và thời điểm không.
2. Mở bài, sao chép permalink hoặc ID bài, rồi đối chiếu quyền sở hữu Page trong công cụ xác minh.
3. Chỉ chọn **Đã tìm thấy bài** khi `PlatformReader` trả `EXISTS` và `ownership=MATCH`. Hệ thống sẽ chuyển về `REPORTED_PUBLISHED` để chạy verify; không tạo command mới.

## Nếu cho rằng Make không tạo bài

1. Mở scenario History theo đúng `command_id`/Make execution và xem module cuối cùng đã chạy.
2. Kiểm tra Page đích trực tiếp theo Page ID, gồm bài đang chờ tải hoặc permalink; nếu kết quả còn mơ hồ, giữ `UNKNOWN`.
3. Chỉ chọn **Không có side effect** khi log Make chứng minh bước tạo bài chưa chạy hoặc đã trả lỗi đã xác minh là không tạo bài. Ghi execution ref và lý do. Sau đó delivery chuyển sang `BLOCKED`.

## Yêu cầu retry an toàn

`UNKNOWN` không có nút retry trực tiếp. Sau khi operator đã ghi nhận `NO_SIDE_EFFECT`, yêu cầu retry chỉ hợp lệ khi không còn execution live, mọi execution trước đều `NO_SIDE_EFFECT`, approval của revision hiện tại còn hiệu lực, deadline còn hơn hai phút và row version chưa đổi. Retry tạo sequence mới; thay nội dung cần revision mới và duyệt lại.

Nếu không còn cửa sổ retry, đóng delivery thành `FAILED_FINAL` với actor và lý do. Không xóa delivery hoặc receipt để dọn lịch sử.
