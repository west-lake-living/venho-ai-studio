# GC2 P9-T04 — Checklist pilot LIVE_MANUAL hằng ngày

**Trạng thái:** checklist; chưa mở pilot và chưa đăng bài nào trong task này. Pilot chỉ bắt đầu sau cutover được Harry phê duyệt, trên bài đã duyệt và slot lịch hiện hành.

## Gate trước pilot

- [ ] P9-T02 đạt; P9-T03 cutover hoàn tất và có bằng chứng một publishing authority duy nhất.
- [ ] Release/DB/API/worker đúng version; `doctor` PASS, backup gần nhất hợp lệ, heartbeat/incident escalation sẵn sàng.
- [ ] `LIVE_MANUAL` do operator bật có chủ đích; không bật scheduler tự động ngoài quy trình đã duyệt.
- [ ] Hai channel/Page ID đã xác minh riêng: Hanoi `1124616474074140`; Ven Hồ `803531149684177`. Make/Meta connection và quyền từng Page đã có evidence P0.
- [ ] Nội dung, revision, approval còn hiệu lực, ảnh SHA, lịch và Page đích được xem lại trước từng slot.
- [ ] Có quy trình UNKNOWN/incident và restore rehearsal đã hoàn thành, theo `unknown_reconcile.md` và `restore.md`.

Thiếu gate nào thì không mở LIVE_MANUAL; giữ Page ở `PAUSED`/`DISABLED` và ghi lý do.

## Trình tự cho từng slot

1. Trước dispatch, xác nhận slot/revision đang được duyệt, caption và ảnh preview khớp hash; xác nhận Page A/B là hai delivery độc lập, cùng nội dung/ảnh đã duyệt nếu slot yêu cầu đăng cả hai.
2. Xử lý Page A trước. Ghi command/execution/receipt refs, Page ID, post ID/permalink và kết quả verify. Xác nhận bài hiện đúng Page, caption, ảnh và thời điểm.
3. Chỉ xử lý Page B sau khi Page A có kết quả xác định. Xác nhận B dùng cùng revision và media SHA nhưng target/Page ID riêng. Ghi receipt/verify riêng.
4. Nếu A không rõ kết quả, không dispatch B cho tới khi đối soát. Nếu B lỗi/UNKNOWN, dừng hoặc đối soát B riêng; không chạy lại A và không tạo lại B khi chưa có bằng chứng `NO_SIDE_EFFECT` theo runbook.
5. Kiểm tra incident, Make/Meta response, visibility và dashboard state; lưu evidence refs đã khử secrets. Không dùng webhook ACK làm bằng chứng post.

## Bảng slot / Page outcome

| Ngày ICT | Slot / revision | Media SHA | Page ID | Command/execution ref | Receipt | Verify / post permalink | Incident / quyết định |
|---|---|---|---|---|---|---|---|
| YYYY-MM-DD |  |  | 1124616474074140 |  | PENDING | PENDING |  |
| YYYY-MM-DD |  |  | 803531149684177 |  | PENDING | PENDING |  |

Không lưu access token, Make webhook URL, signed media URL hoặc thông tin tài khoản trong bảng hoặc ảnh chụp.

## Checklist cuối ngày

- [ ] Mọi slot trong ngày có outcome riêng cho từng Page; đã tính target outcomes (mỗi slot đủ hai Page là hai outcomes).
- [ ] So số command, receipt, verify và bài nhìn thấy; mọi chênh lệch gắn incident/evidence.
- [ ] Không có bài trùng, đăng sai Page, sai revision/caption hoặc ảnh khác SHA đã duyệt.
- [ ] Không còn `UNKNOWN` chưa được xử lý; nếu còn thì giữ incident mở, tạm dừng target liên quan và theo runbook đối soát.
- [ ] Ghi số slot đủ điều kiện, slot huỷ/thiếu mẫu và quyết định kéo dài pilot nếu cần.

## Tiêu chí kết thúc pilot (G-P9 / AC-18)

- Tối thiểu 8 slot thực tế, tối thiểu 16 Page target outcomes và thời gian quan sát ít nhất 14 ngày.
- 0 bài trùng, 0 Page sai, 0 ảnh khác bản duyệt; mọi UNKNOWN được xử lý theo evidence/runbook.
- Có ít nhất một restore rehearsal hợp lệ và xác nhận vận hành; nếu slot bị huỷ làm thiếu mẫu, kéo dài thời gian pilot thay vì hạ ngưỡng.
- Harry ghi quyết định go/no-go, evidence index và incident disposition. Không tự chuyển sang retire legacy khi tiêu chí chưa đủ.

## Dừng / sự cố

Dừng dispatch target liên quan nếu Page ID/ownership, caption, ảnh hash, approval, outcome hoặc visibility không xác định. Không retry UNKNOWN. Nếu A đã đăng và B lỗi, giữ receipt A và điều tra B riêng; không đăng lại A. Tạm dừng toàn cục nếu có dấu hiệu hai publisher cùng hoạt động hoặc sai Page; xử lý incident và thông báo operator theo cấu hình đã duyệt.

## Tóm tắt pilot

| Ngày bắt đầu/kết thúc | Số ngày | Slot thực tế | Target outcomes | Duplicate | Sai Page | Sai ảnh | UNKNOWN còn mở | Restore rehearsal ref | Quyết định Harry |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| PENDING | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PENDING | PENDING |
