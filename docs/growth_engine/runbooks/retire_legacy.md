# GC2 P9-T05 — Checklist retire đường đăng legacy

**Trạng thái:** checklist chuẩn bị; không có timer, registry, BFF hoặc workflow nào bị thay đổi trong task này. Đây là thao tác có ảnh hưởng vận hành, chỉ làm sau quyết định của Harry.

## Phát hiện từ Make History production — 09/11/2026

Nguồn: Harry đọc trực tiếp History của production scenario `5868920`; thao tác chỉ đọc, không chỉnh Make.

- Một payload Facebook đã khớp cả module đăng Facebook Pages `3` và `12`, nên đăng lên cả hai Page trong cùng lượt chạy.
- Nhánh Instagram production dùng URL Google Drive thay vì signed media URL của Growth Engine.
- Từ module Instagram của Make: Instagram API không tải được file từ Google Drive, kể cả khi file được công khai. Production phải chuyển sang signed media URL của Growth Engine.

**Quyết định Harry (11/11/2026):** đăng cùng một bài Facebook lên cả `Ven Hồ Hotel Hanoi` và `Ven Hồ Hotel` là chủ ý. Sau cutover một slot tạo hai command riêng (`fb_hanoi`, `fb_venho`), mỗi command có receipt/verify riêng. Hai module Facebook cùng chạy không còn được xem là lỗi legacy; v2 phải giữ hai target độc lập.

**Đề xuất retire/cutover:** không sửa Make production trong task này. Giữ bằng chứng về URL Drive làm gate bắt buộc: thay bằng signed media URL trước khi bật Instagram v2. Xác minh từng target/outcome trước khi tắt legacy; không resend Hanoi để xử lý lỗi riêng của Ven Hồ.

## Gỡ filter chữ ký `Venho signature` và xoay literal hex

Blueprint production v2 thay filter cũ bằng điều kiện chung `schema_version = growth.command.v2` AND `environment = production` trước Router; mỗi route lọc `channel_key`. Trước khi import, lưu export production cũ ở nơi riêng tư mode `600`. Không ghi literal hex vào export đã khử bí mật, log, issue hoặc báo cáo.

Trong cùng change window, xác định mọi producer/consumer còn dùng literal 64 ký tự hex. Nếu nó được dùng như bí mật ký, coi như đã lộ: tạo giá trị mới bằng secret manager, cập nhật producer và verifier tương ứng, vô hiệu hóa giá trị cũ, rồi xác minh payload v2 qua History. Không xoay riêng một phía khi legacy sender vẫn cần giá trị cũ; khi đó dừng cutover và lập kế hoạch chuyển đồng bộ. Nếu không còn consumer hợp lệ, retire literal thay vì thay bằng một bí mật mới. Chỉ ghi tên biến/đường dẫn consumer, ngày và kết quả xác minh; không ghi giá trị.

**Quay lui:** nếu phải import lại export cũ, giữ scenario Inactive và runtime `DISABLED` cho đến khi producer/filter cũ được khôi phục nhất quán. Không mở lại publisher legacy chỉ để xử lý một target lỗi.

## Gate trước khi retire

- [ ] Harry phê duyệt retire sau khi P9-T04 đạt đầy đủ G-P9/AC-18: ≥8 slot, ≥16 target outcomes, ≥14 ngày; không duplicate/sai Page/sai ảnh; mọi UNKNOWN đã xử lý.
- [ ] Restore rehearsal AC-18 đã có evidence; backup cuối kỳ, manifest media và checksum đã kiểm tra.
- [ ] Có một publishing authority duy nhất là v2; hai Page đã hoạt động ổn định riêng; không còn execution/queue/grant legacy có thể đăng muộn.
- [ ] Instagram production đã được chuyển từ Google Drive sang signed media URL; Make History chứng minh Meta tải đúng JPEG variant đã duyệt (JPG ≤ 8 MB, tỉ lệ 4:5–1.91:1).
- [ ] Mỗi slot đủ điều kiện có hai delivery Facebook độc lập: Hanoi và Ven Hồ; mỗi target có command, receipt và verify riêng. Một target lỗi không phát lại target đã thành công.
- [ ] Incidents, UNKNOWN, scheduled approvals và import deltas đã đóng/đối soát; bản lưu cần thiết đã được xác định.
- [ ] Chuẩn bị kế hoạch rollback/forward recovery. Sau grant production, không khôi phục registry legacy làm authority.

Nếu thiếu gate, dừng. Không vô hiệu hoá publisher legacy trước khi operator có quyết định và bằng chứng gate.

## Checklist thay đổi có kiểm soát

| Thứ tự | Thay đổi được Harry/operator thực hiện sau phê duyệt | Kiểm tra / kết quả mong đợi | Dừng nếu |
|---|---|---|---|
| 1. Chốt bằng chứng | Đóng báo cáo pilot; ghi release SHA, Page IDs, số slot/target, restore rehearsal, incident dispositions và quyết định. | Evidence index đầy đủ, đã khử secrets; tiêu chí pilot đều đạt. | Còn UNKNOWN, thiếu mẫu, sai Page/ảnh hoặc thiếu restore rehearsal. |
| 2. Chặn legacy publish | Disable vĩnh viễn các timer/unit/workflow chỉ chịu trách nhiệm đăng Growth legacy; giữ nguyên các timer research/maintenance chưa được phê duyệt để tắt. | Liệt kê unit/timer/workflow cụ thể từ inventory; `systemctl --user list-timers 'venho-growth-*'` và lịch GitHub không còn publisher legacy có thể chạy. | Không phân biệt chắc publisher với job khác, hoặc còn execution đang sống. |
| 3. Archive registry | Chụp publication registry JSON cùng checksum vào vùng lưu trữ hạn chế quyền; đổi thành chỉ đọc; giữ nguyên file gốc và nguồn gốc. | SHA-256 trước/sau bằng nhau; archive index ghi đường dẫn, ngày, owner, retention và quyền. Không xoá bản gốc. | Hash mismatch, thiếu file, hoặc bản archive còn writable với service account. |
| 4. Gỡ backend legacy khỏi VENHO OS | Harry/operator cập nhật cấu hình triển khai để `GROWTH_BACKEND=legacy` không còn là lựa chọn; đặt v2 theo quyết định rollout đã duyệt. Không chỉnh trong task tài liệu này. | BFF/API smoke check chứng minh request Growth chỉ dùng v2 và không fallback sang JSON legacy; session actor/auth còn nguyên. | v2 chưa sẵn sàng, dashboard lỗi, dữ liệu bị trộn hoặc phải fallback để duy trì service. |
| 5. Gỡ filter chữ ký Make cũ | Trong scenario production sau khi v2 rollout/cutover được duyệt, gỡ `Venho signature` khỏi liên kết webhook → HTTP và thay bằng filter chung `schema_version = growth.command.v2` AND `environment = production` trước Router. Không thao tác trong checklist tài liệu này. | History chứng minh event legacy bị chặn và envelope v2 hợp lệ đi vào đúng Router; không ghi lại filter literal cũ. | Chưa xác minh common filter hoạt động hoặc còn nguồn gửi payload legacy. |
| 6. Đánh giá literal chữ ký cũ | Xác định ngoài biên bản nếu literal hex cố định trong filter còn được dùng ở nơi khác; bản chất của nó là **CHƯA XÁC MINH**. Vì người có quyền đọc scenario có thể xem cấu hình filter, coi giá trị đó là đã lộ nếu nó là secret; xoay hoặc retire mọi phụ thuộc sau khi xác nhận. Không chép literal vào tài liệu/log. | Ghi quyết định xoay/retire và các phụ thuộc đã kiểm tra, không ghi giá trị literal. | Không rõ phụ thuộc hoặc chưa có kế hoạch chuyển signer/client. |
| 7. Cập nhật ops docs | Cập nhật `ops/asus-server/README.md`, inventory và DR record: v2 là publisher duy nhất; legacy timers/registry đã retired; chỉ dẫn phục hồi không tái cấp quyền legacy tự động. | Tài liệu khớp trạng thái host/workflow và có commit/release SHA, approver, ngày ICT, archive checksum. | Tài liệu và trạng thái thực tế khác nhau. |
| 8. Đóng DR | Ghi kết quả/risks còn lại, owner, recovery route, backup/restore refs, thời điểm đóng và phê duyệt Harry. | DR ticket/log đóng rõ; dashboard, API, worker, alert và backup tiếp tục health-check theo quy trình vận hành. | Health degraded, audit gap hoặc chưa có recovery owner. |

## Quy tắc sau retire

- Không khôi phục timer hoặc registry legacy để xử lý một lỗi v2. Pause v2, đối soát target đã xử lý và dùng forward recovery trên DB v2 theo quyết định operator.
- Nếu sự cố buộc quay lại legacy, yêu cầu quyết định mới của Harry, đối soát từng target đã authorized/reported/unknown và chứng minh không đăng trùng trước khi cấp quyền lại.
- Không xóa JSON, backup, receipts, Make History hoặc audit evidence khi retire.
- Không ghi token, webhook URL, secret, signed URL hoặc thông tin đăng nhập vào biên bản.

## Biên bản retire

| Gate | Evidence ref | Kết quả |
|---|---|---|
| G-P9/AC-18 và quyết định Harry |  | PENDING |
| Restore rehearsal / backup SHA |  | PENDING |
| Legacy publisher units/workflows |  | PENDING |
| Registry archive SHA/read-only |  | PENDING |
| VENHO OS v2-only verification |  | PENDING |
| README / inventory / DR closure |  | PENDING |
| Người thực hiện / thời gian ICT |  | PENDING |
