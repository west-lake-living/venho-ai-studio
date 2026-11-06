# GC2 P9-T05 — Checklist retire đường đăng legacy

**Trạng thái:** checklist chuẩn bị; không có timer, registry, BFF hoặc workflow nào bị thay đổi trong task này. Đây là thao tác có ảnh hưởng vận hành, chỉ làm sau quyết định của Harry.

## Gate trước khi retire

- [ ] Harry phê duyệt retire sau khi P9-T04 đạt đầy đủ G-P9/AC-18: ≥8 slot, ≥16 target outcomes, ≥14 ngày; không duplicate/sai Page/sai ảnh; mọi UNKNOWN đã xử lý.
- [ ] Restore rehearsal AC-18 đã có evidence; backup cuối kỳ, manifest media và checksum đã kiểm tra.
- [ ] Có một publishing authority duy nhất là v2; hai Page đã hoạt động ổn định riêng; không còn execution/queue/grant legacy có thể đăng muộn.
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
