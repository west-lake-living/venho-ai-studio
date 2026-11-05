# GC2 P9-T02 — DRY_RUN song song 3–7 ngày

## Mục tiêu và giới hạn

So sánh kế hoạch Growth Engine v2 với lịch legacy trong 3–7 ngày liên tục. DRY_RUN chỉ tạo và lưu đề xuất vào DB v2; tuyệt đối không gửi command tới Make, không gọi module đăng Facebook/Instagram và không tạo bài công khai. Không chuyển publishing authority trong giai đoạn này.

Runbook này là checklist, không phải bằng chứng đã chạy. Chỉ bắt đầu sau khi backend v2, jobs lane và chế độ DRY_RUN đã được triển khai, `doctor` đạt yêu cầu, và Harry xác nhận thời gian quan sát. Jobs lane đã được compose; DRY_RUN mode và host gates vẫn phải được xác minh trước khi quan sát.

## Điều kiện trước khi bắt đầu

- [ ] Có release v2 đã được deploy ở `DISABLED`; `venho-engine doctor` không có FAIL.
- [ ] Jobs lane và DRY_RUN chỉ-ghi-DB hoạt động; test chứng minh không tạo command/outbox hoặc external side effect.
- [ ] Lịch legacy và các nguồn dữ liệu được snapshot chỉ đọc; không có hai scheduler cùng quyền đăng.
- [ ] Mapping rõ Hanoi `fb_hanoi` → `1124616474074140`, Ven Hồ `fb_venho` → `803531149684177`, Instagram `ig_venho` → business account `17841457936965829`; không suy channel từ tên hiển thị.
- [ ] Có nơi lưu báo cáo đã lọc bí mật và Telegram digest được cấu hình; không ghi URL webhook, token, signed URL hoặc thông tin đăng nhập.
- [ ] Ghi mốc bắt đầu/kết thúc, timezone `Asia/Ho_Chi_Minh`, release SHA và người vận hành.

## Chu trình hằng ngày

1. Chụp danh sách slot legacy cho ngày quan sát ở chế độ chỉ đọc; ghi slot ID, giờ ICT, pillar/chủ đề, media SHA đã duyệt, và mapping riêng cho hai Facebook Page cùng Instagram account.
2. Cho v2 sinh đề xuất DRY_RUN vào DB riêng. Xác nhận số bản ghi mới và trạng thái; dừng nếu thấy command có thể gửi, trạng thái LIVE, hoặc external mutation.
3. Ghép slot theo ID nghiệp vụ; so lịch, chủ đề/pillar, revision/caption và từng target độc lập. So từng Facebook Page với ảnh đã duyệt; so Instagram với revision và variant Instagram 4:5 đã duyệt. Không gộp target outcomes, reach hay kết quả giữa các kênh.
4. Ghi mọi sai khác, thiếu dữ liệu và bằng chứng nguồn. Không tự sửa dữ liệu legacy hay đổi nội dung đã duyệt trong lúc đối chiếu.
5. Gửi digest Telegram đã lọc bí mật: tổng slot, số khớp, số khác, số thiếu, Page mapping và liên kết nội bộ tới báo cáo.

## Bảng ghi nhận

| Ngày (ICT) | Slot | Lịch | Chủ đề/pillar | Revision/variant | SHA ảnh đã duyệt | Hanoi Page ID | Ven Hồ Page ID | IG business ID | Kết quả | Sai khác / evidence ref |
|---|---|---|---|---|---|---|---|---|---|---|
| YYYY-MM-DD |  |  |  |  |  | 1124616474074140 | 803531149684177 | 17841457936965829 | PENDING |  |

Evidence ref phải trỏ đến bản ghi/report nội bộ đã khử bí mật; không chép nội dung credential hoặc URL có chữ ký vào bảng.

## Kết thúc và điều kiện đạt

- Quan sát tối thiểu 3 ngày và tối đa 7 ngày; ghi đủ từng ngày, kể cả ngày không có slot.
- Đạt khi không còn sai khác lịch hoặc mapping Page chưa được giải thích; mọi khác biệt về chủ đề/ảnh có quyết định và evidence rõ ràng.
- Nếu thiếu ngày/slot hoặc còn sai khác, giữ v2 ở `DISABLED`, ghi owner và lý do, rồi xin quyết định kéo dài hoặc dừng. Không bật LIVE để bù mẫu.
- Lưu bản tổng kết gồm số slot, số khớp, sai khác đã giải thích/chưa giải thích, lỗi vận hành và xác nhận không có side effect.

## Dừng ngay

Dừng chu trình và giữ v2 `DISABLED` nếu phát hiện command/outbox gửi được, Page ID mơ hồ, ảnh không khớp SHA duyệt, legacy/v2 cùng có quyền đăng, thiếu audit/evidence, hoặc có bất kỳ bài công khai nào do DRY_RUN gây ra. Ghi execution/incident ref đã khử bí mật; không retry hay xóa lịch sử.
