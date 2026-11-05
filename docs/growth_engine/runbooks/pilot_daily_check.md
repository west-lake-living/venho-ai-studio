# GC2 P9-T04 — Checklist pilot LIVE_MANUAL hằng ngày

**Trạng thái:** checklist; chưa mở pilot và chưa đăng bài nào trong task này. Pilot chỉ bắt đầu sau cutover được Harry phê duyệt, trên bài đã duyệt và slot lịch hiện hành.

## Gate trước pilot

- [ ] P9-T02 đạt; P9-T03 cutover hoàn tất và có bằng chứng một publishing authority duy nhất.
- [ ] Release/DB/API/worker đúng version; `doctor` PASS, backup gần nhất hợp lệ, heartbeat/incident escalation sẵn sàng.
- [ ] `LIVE_MANUAL` do operator bật có chủ đích; không bật scheduler tự động ngoài quy trình đã duyệt.
- [ ] Ba channel ID đã xác minh riêng: Hanoi Page `1124616474074140`; Ven Hồ Page `803531149684177`; Instagram business account `17841457936965829`. Make/Meta connection và quyền từng target đã có evidence P0.
- [ ] Nội dung, revision, approval còn hiệu lực, ảnh SHA, lịch và Page đích được xem lại trước từng slot.
- [ ] Có quy trình UNKNOWN/incident và restore rehearsal đã hoàn thành, theo `unknown_reconcile.md` và `restore.md`.

Thiếu gate nào thì không mở LIVE_MANUAL; giữ Page ở `PAUSED`/`DISABLED` và ghi lý do.

## Trình tự cho từng slot

1. Trước dispatch, xác nhận slot/revision được duyệt, caption và media variant đúng kênh; mỗi target có delivery và outcome độc lập.
2. Xử lý theo thứ tự Hanoi `fb_hanoi` → Ven Hồ `fb_venho` → Instagram `ig_venho`. Chỉ mở target kế tiếp sau khi target trước có kết quả xác định. Ghi Page ID hoặc IG business ID cùng command/execution/receipt.
3. Với Facebook, kiểm Page ID, caption, ảnh, thời điểm, post ID và permalink. Với Instagram, kiểm business account, variant 4:5, caption, thời điểm, media ID và permalink.
4. Nếu Hanoi không rõ kết quả, không dispatch Ven Hồ/IG. Nếu Ven Hồ lỗi/UNKNOWN, dừng riêng Ven Hồ; không resend Hanoi và chưa mở IG. Nếu IG lỗi/UNKNOWN, dừng riêng IG; không resend hai Page. Chỉ retry target có bằng chứng `NO_SIDE_EFFECT` theo runbook.
5. Kiểm tra incident, Make/Meta response, visibility và dashboard state; lưu evidence refs đã khử secrets. Không dùng webhook ACK làm bằng chứng post.

## Bảng slot / target outcome

| Ngày ICT | Slot / revision | Target | Target ID | Variant / media SHA | Command/execution ref | Receipt | Verify / post or media permalink | Incident / quyết định |
|---|---|---|---|---|---|---|---|---|
| YYYY-MM-DD |  | fb_hanoi | 1124616474074140 | approved Facebook variant / SHA |  | PENDING | PENDING |  |
| YYYY-MM-DD |  | fb_venho | 803531149684177 | approved Facebook variant / SHA |  | PENDING | PENDING |  |
| YYYY-MM-DD |  | ig_venho | 17841457936965829 | approved Instagram 4:5 variant / SHA |  | PENDING | PENDING |  |

Không lưu access token, Make webhook URL, signed media URL hoặc thông tin tài khoản trong bảng hoặc ảnh chụp.

## Checklist cuối ngày

- [ ] Mọi slot trong ngày có outcome riêng cho Hanoi, Ven Hồ và Instagram; đã tính target outcomes (mỗi slot đủ ba target là ba outcomes).
- [ ] So số command, receipt, verify và bài nhìn thấy; mọi chênh lệch gắn incident/evidence.
- [ ] Không có bài trùng, đăng sai Page, sai revision/caption hoặc ảnh khác SHA đã duyệt.
- [ ] Không còn `UNKNOWN` chưa được xử lý; nếu còn thì giữ incident mở, tạm dừng target liên quan và theo runbook đối soát.
- [ ] Ghi số slot đủ điều kiện, slot huỷ/thiếu mẫu và quyết định kéo dài pilot nếu cần.

## Tiêu chí kết thúc pilot (G-P9 / AC-18)

- Tối thiểu 8 slot thực tế, tối thiểu 24 target outcomes và thời gian quan sát ít nhất 14 ngày.
- 0 bài trùng, 0 target/account sai, 0 media variant khác bản duyệt; mọi UNKNOWN được xử lý theo evidence/runbook.
- Có ít nhất một restore rehearsal hợp lệ và xác nhận vận hành; nếu slot bị huỷ làm thiếu mẫu, kéo dài thời gian pilot thay vì hạ ngưỡng.
- Harry ghi quyết định go/no-go, evidence index và incident disposition. Không tự chuyển sang retire legacy khi tiêu chí chưa đủ.

## Dừng / sự cố

Dừng dispatch target liên quan nếu Page/account ID, ownership, caption, variant/hash, approval, outcome hoặc visibility không xác định. Không retry UNKNOWN. Nếu Hanoi đã đăng và Ven Hồ lỗi, giữ receipt Hanoi và điều tra Ven Hồ riêng; không đăng lại Hanoi. Nếu Instagram lỗi sau hai Facebook thành công, điều tra Instagram riêng. Tạm dừng toàn cục nếu có dấu hiệu hai publisher cùng hoạt động hoặc sai target; xử lý incident và thông báo operator theo cấu hình đã duyệt.

## Tóm tắt pilot

| Ngày bắt đầu/kết thúc | Số ngày | Slot thực tế | Target outcomes | Duplicate | Sai Page | Sai ảnh | UNKNOWN còn mở | Restore rehearsal ref | Quyết định Harry |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| PENDING | 0 | 0 | 0 | 0 | 0 | 0 | 0 | PENDING | PENDING |
