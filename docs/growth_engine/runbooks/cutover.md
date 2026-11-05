# GC2 P9-T03 — Runbook cutover Growth Engine v2

**Trạng thái:** checklist soạn sẵn; chưa cutover. Mọi bước dưới đây cần được thực hiện tuần tự bởi operator sau các gate đã duyệt. Không chạy trong phạm vi task hiện tại.

## Điều kiện vào

- [ ] Harry xác nhận cửa sổ cutover xa lịch đăng và chịu trách nhiệm vận hành.
- [ ] P9-T02 đạt: không còn sai khác lịch/Page mapping chưa giải thích.
- [ ] Release/DB/schema và backup đã kiểm tra; `venho-engine doctor` không FAIL. Runtime phục vụ API và hai worker lane `publish`/`jobs` đã được triển khai và kiểm tra ở mode `DISABLED`.
- [ ] P7 dashboard/BFF đã được tích hợp, đúng môi trường và sẵn sàng chuyển backend; có banner bảo trì và đường khôi phục.
- [ ] Facebook Page IDs `fb_hanoi` (`1124616474074140`), `fb_venho` (`803531149684177`) và Instagram business account ID `ig_venho` (`17841457936965829`), Make route/schema filter, quyền, media, TLS/Access và callback evidence đã được xác minh trong hồ sơ P0; không dùng tên hiển thị thay ID.
- [ ] Có bản sao chỉ đọc các nguồn legacy, manifest ảnh, blueprint, snapshot approval và version deploy; danh sách nguồn có SHA-256.
- [ ] Có kế hoạch liên hệ operator và cửa sổ đủ dài để chờ hết capability grant TTL (60 giây theo policy) trước khi chuyển bước.

Nếu bất kỳ gate nào thiếu, giữ backend v2 `DISABLED` và dừng trước cửa sổ cutover.

## Cutover tuần tự

| Bước | Thao tác trong cửa sổ được duyệt | Kiểm tra và kết quả mong đợi | Dừng / khôi phục |
|---|---|---|---|
| 1. Chế độ bảo trì | Hiển thị banner; đặt runtime v2 ở `DISABLED`. | Dashboard báo bảo trì; mọi lệnh ghi Growth cũ bị chặn (503); `doctor`/controls cho thấy DISABLED. | Nếu ghi vẫn được hoặc trạng thái không rõ: dừng, không thay authority. |
| 2. Dừng publisher legacy | Disable các timer `venho-growth-*` liên quan publish; chặn Dashboard ghi JSON Growth cũ. Không dừng timer chỉ phục vụ ngoài phạm vi nếu chưa xác định phụ thuộc. | `systemctl --user list-timers 'venho-growth-*'` cho thấy không còn timer publish đang chờ; kiểm tra trạng thái unit và log. Kết quả phải khớp inventory hiện hành. | Nếu không xác định được unit hoặc timer còn active/queued: dừng; không bật v2. Khôi phục cấu hình cũ chỉ khi v2 vẫn DISABLED và chưa có grant. |
| 3. Drain execution | Kiểm Make History, outbox, worker và mọi queue có thể gửi muộn; chờ hết grant TTL. | Không còn Make execution/queue có khả năng mutation; không còn grant còn hiệu lực. Ghi evidence ref và thời điểm kiểm. | Bất kỳ execution/command nào còn sống hoặc kết quả mơ hồ: dừng, đối soát theo `unknown_reconcile.md`; tuyệt đối không phát lệnh mới. |
| 4. Snapshot cuối | Chụp DB/media/registry/approval/manifest/blueprint/deploy snapshot; tính SHA-256, lưu nguyên bản chỉ đọc. | Báo cáo liệt kê đủ nguồn, số bản ghi và checksum; backup/restore checks PASS. | Thiếu nguồn, hash lệch hoặc backup không đọc/verify được: không import, không chuyển backend. |
| 5. Import delta | Chạy `legacy-import --dry-run` trên snapshot delta và kiểm report theo AC-15. Sau khi Harry duyệt report, chạy `legacy-import --apply --target-db <đã-migrate-DB> --source <snapshot-delta> --report <evidence-report>` một lần. | Từng dòng có mapping Page/route bằng bằng chứng; thiếu dữ liệu thành `LEGACY_UNVERIFIED`/issue, không tự cấp approval. Apply yêu cầu DB đích đã migrate, idempotent theo source/key/hash; report khớp counts/mapping. | Nếu dry-run/report chưa được duyệt, DB chưa có schema mục tiêu, hoặc mapping khác dự kiến: không chạy `--apply`; giữ production `DISABLED`. Nếu apply dở/lỗi, dừng và đối soát `legacy_imports` trước khi retry; không xoá DB hoặc nhập lại dữ liệu đã có. |
| 6. Epoch và cấu hình | Sau import được duyệt, đặt epoch mới không tồn tại trong backup; cấu hình service và runtime controls cùng epoch, còn `DISABLED`. | `doctor` PASS, epoch hai nơi bằng nhau, epoch cũ không được chấp nhận. | Sai khác/placeholder/doctor FAIL: dừng ở DISABLED; không chuyển BFF. |
| 7. Backend Dashboard | Chuyển BFF `GROWTH_BACKEND=v2`; route legacy trả proxy an toàn hoặc 410 theo release đã review. | Read/write smoke checks trên TEST hoặc không mutation: BFF chỉ gọi API v2; không còn fallback lẫn dữ liệu legacy; auth/actor vẫn server-side. | Bất kỳ response sai nguồn, 5xx không phân biệt, hoặc auth bị lộ: quay về maintenance/DISABLED; không mở publish. |
| 8. Make route | Đóng webhook legacy hoặc giới hạn để chỉ nhận `schema_version = growth.command.v2`; xác minh TEST/probe đã duyệt và từng route production Facebook/Instagram chỉ nhận envelope v2. | History/blueprint evidence chứng minh route legacy không còn nhận command mới và không có route mơ hồ. | Không chứng minh được filter/route: giữ mọi publisher DISABLED; không gửi test công khai. |
| 9. DRY_RUN và LIVE_MANUAL | Đối chiếu slot tiếp theo. Khi mọi gates đạt, mở từng target theo thứ tự `fb_hanoi` → `fb_venho` → `ig_venho`; chờ receipt+verify xác định ở target trước rồi mới mở target kế tiếp. | Mỗi target có delivery/receipt/verify riêng; đúng Facebook Page ID hoặc Instagram business ID, revision, variant ảnh theo kênh và permalink/media ID; một authority duy nhất. | Lỗi hoặc UNKNOWN ở Hanoi: không mở Ven Hồ/IG. Lỗi ở Ven Hồ: dừng riêng Ven Hồ, không resend Hanoi và chưa mở IG. Lỗi ở IG: dừng riêng IG, không resend hai Page. UNKNOWN theo runbook reconcile, không retry trực tiếp. |
| 10. Chốt authority | Archive JSON cũ read-only; giữ GitHub `growth-publish-scheduler.yml` ở `workflow_dispatch` trỏ runbook v2 hoặc vô hiệu hoá; cập nhật inventory/evidence. | Có bằng chứng scheduler duy nhất; archive checksum khớp snapshot; mọi timer/job cũ không đăng. | Nếu còn khả năng dual-write/dual-publish: chưa kết thúc cutover; giữ DISABLED và gọi operator. |

## Quy tắc rollback và kết thúc

- Trước grant production đầu tiên, chỉ khôi phục cấu hình sau khi xác nhận queue v2 bị chặn và dữ liệu/snapshot còn nguyên.
- Sau grant production đầu tiên, mặc định forward recovery trên DB v2. Không khôi phục registry legacy làm publishing authority.
- Nếu buộc phải quay lại legacy: pause v2; đối soát tất cả delivery `AUTHORIZED`/`REPORTED`/`UNKNOWN`; xác minh legacy không đăng lại target đã xử lý; chỉ sau quyết định của Harry mới cấp quyền legacy.
- Không coi webhook ACK là bằng chứng bài đăng. Kết quả cần receipt, Page verification, Page ID và permalink/evidence phù hợp.
- Ghi người thao tác, thời gian ICT, commit/deploy SHA, backup SHA, import report, epoch mới, kết quả từng bước, decision và incident refs đã khử bí mật. Không đưa secrets, webhook URLs hoặc signed URLs vào evidence.

## Biên bản

| Bắt đầu/kết thúc (ICT) | Release SHA | Snapshot SHA/report | Import report | `fb_hanoi` | `fb_venho` | `ig_venho` | Authority duy nhất | Quyết định / operator |
|---|---|---|---|---|---|---|---|---|
| PENDING |  |  |  | NOT RUN | NOT RUN | NOT RUN | NOT VERIFIED |  |
