# GC2 production cutover — 26/11/2026 ICT

Harry chốt **phương án A** sau khi T3 ngày 24/11 không chạy. Giữ lượt legacy 25/11 đã duyệt và đổi slot v2 đầu tiên sang 27/11. Legacy dừng cả ba kênh từ slot 27/11. Ngày 27/11 chỉ Hanoi đăng, Page Ven Hồ và Instagram bỏ trống. Cadence thứ Hai/Tư/Sáu/Bảy lúc 09:00 ICT.

| Mốc | Việc thực hiện |
|---|---|
| T4 · 25/11 sau 09:30 | Legacy đã qua slot 09:00. Chạy `t2`, xác nhận `PREPARE_27`, export Make 5868920. |
| T5 · 26/11 | `stop-legacy` → `snapshot` → `switch-and-epoch` → `rotate` → `dry-run` → duyệt Hanoi → `live`. |
| T6 · 27/11 | Hanoi đăng lúc 09:00. Sau 09:30 chạy `expand` khi bài đã đối soát. Tối duyệt nhóm và chạy `resume-three`. |
| T7 · 28/11 | Ba kênh đăng lúc 09:00. Sau 09:30 đối soát từng đích. |

Wrapper lấy lịch từ đầu `cutover-window.sh`, kiểm hai slot theo cadence và lưu evidence tại `~/venho/state/growth-engine/cutover-20261126/`. Thư mục 24/11 nếu có chỉ được báo cảnh báo.

Mốc operator cung cấp: GC2 `9c9e8dff`, schema 10, `DISABLED` + `global_pause=1`; P4/readiness PASS cho 21/11 09:00. VENHO OS `28beaefe367567ddbe89541d945a793196be85e5` có health route. API `127.0.0.1:8021`, hostname `growth-api.venhohotel.com`, Access app `growth-engine-production-internal`, service token `make-growth-engine-production`. Make hiện có scenario `5868920`; IP/port, DNS và quyền Meta được kiểm tra qua UI, không đổi nếu khớp.

**Dừng cứng:** hết gate nào thì giữ pause. Từ 08:30 đến hết phút 09:30, wrapper chặn toàn bộ khối dưới đây. Vào giờ đăng 25/11, 27/11 và 28/11 xem Make History/Page **chỉ đọc qua UI**; chạy khối server sau 09:30. Không Run once, resend, đăng thử hoặc bắt slot cũ. Gate P9-T04 vẫn dành cho gỡ hẳn legacy. Quy trình bên dưới chỉ tạm dừng có thể đảo ngược, theo §12.2–12.3.

## Cách chạy các khối

Deploy **SHA bàn giao của nhánh này** tối 24/11 hoặc sáng 25/11 sau hết phút 09:30 theo khối deploy từ origin trong [P4 runbook](p4_production_dry_run.md), vẫn giữ `DISABLED`/pause. GC2 không có migration mới. Dùng bootstrap độc lập bên dưới cho mỗi bước. Mỗi dòng gọi tự sinh file Bash riêng, xóa khi kết thúc và chuyển xác nhận qua wrapper TTY. Chạy từng dòng rồi kiểm kết quả trước khi chạy dòng tiếp theo.

```bash
gc2_cutover() {
  local job
  job="$(mktemp "$HOME/venho/gc2-cutover.XXXXXX")" || return
  cat > "$job" <<'SCRIPT'
#!/usr/bin/env bash
set -Eeuo pipefail
trap 'rm -f -- "$0"' EXIT
printf 'CUTOVER_STEP=%s\n' "$1"
bash "$HOME/venho/growth-engine/current/ops/asus-server/growth-engine/cutover-window.sh" "$@"
SCRIPT
  bash "$job" "$@"
}
```

## Tham chiếu — backup và rehearsal ban đầu ngày 20/11

```bash
gc2_cutover friday-backup
```

Deploy SHA mới trước khi chạy khối này. Gõ `FIRST_BACKUP` để tạo snapshot bằng Online Backup API, rehearsal trong thư mục tạm, bật timer user `growth-engine-backup.timer` mỗi giờ và kiểm Doctor `Backup age` PASS. Khối này không prepare slot, không thao tác legacy hay Make. Giữ production `DISABLED` + pause.

Snapshot ở thư mục `backup-staging` cạnh DB thật (`~/venho/state/growth-engine/backup-staging/`), thư mục 700, archive 600. Manifest gồm `object_key` + SHA-256 cho originals/variants; thiếu/sai hash làm backup thất bại. Retention theo UTC giữ bản mới nhất của 48 bucket giờ, 14 ngày, 8 tuần, một file có thể thuộc nhiều bucket. Rehearsal kiểm integrity, foreign keys, manifest toàn bộ artifact, và làm bản copy `DISABLED` + pause + epoch mới; DB thật được mở read-only khi snapshot. Doctor Backup age PASS khi staging có bản hoàn tất ≤2 giờ; gate cutover yêu cầu **<1 giờ**. Archive staging chưa mã hóa, giữ trên ASUS trong vùng 700. Backup cùng đĩa có thể mất cùng DB nếu ổ hỏng, máy mất hoặc dữ liệu bị xóa. Theo [runbook offsite](backup_offsite.md), hoàn tất upload đã kiểm checksum và diễn tập Mac trước khi mở ba kênh tối 27/11. T5 chỉ WARN nếu offsite còn thiếu hoặc quá cũ. Heartbeat sender hiện có; Doctor Heartbeat age vẫn WARN vì chưa có nguồn timestamp xác thực healthchecks.io, không suy ra PASS từ cấu hình URL.

## T4 25/11 — sau 09:30 ICT

```bash
gc2_cutover t2
```

Wrapper chặn `t2` nếu còn incident `GENERATION_UNKNOWN` mở, rồi kiểm snapshot dưới một giờ trước khi hỏi `PREPARE_27`. Với job 25/11 `fc57dcac-e569-4d6b-851a-dee66a7e447e`, dùng wrapper `resolve-generation-unknown --job <id> --actual-minor 6200` và xác nhận `RESOLVE` trong lúc production `DISABLED` + pause. `generation-recovery-status --job <id>` phải báo job `FAILED`, recovery `CLOSED_WITHOUT_RETRY`, paid call `SETTLED` và incident `RESOLVED`. Đây là chi phí do operator xác nhận và job cũ được đóng. Sau đó `cutover-ops generation-clear --date 2026-11-27` phải báo 0.

Nếu một slot tương lai báo `ERR_GC2_GENERATION_POST_RESPONSE_FAILED`, kiểm `reprocess-generation-evidence --job <id>` qua wrapper. Chỉ xác nhận `REPROCESS` khi preflight READY và mode/pause còn đúng. Lệnh dùng evidence đã lọc và bản gốc media đã lưu, tạo package/delivery trong một transaction và báo 0 provider/paid call mới. Nếu evidence hoặc media thiếu, giữ nguyên trạng thái và đối soát trước khi quyết định bước tiếp theo. Chỉ bật Hanoi `--prepare-only` và queue slot 27/11 09:00. Kỳ vọng `QUEUED`; theo dõi `gc2_cutover status 2026-11-27` tới `IN_REVIEW`. Lượt 25/11 đã duyệt vẫn do legacy đăng. Delivery v2 đã chuẩn bị cho 25/11 nếu còn `IN_REVIEW` sẽ tự chuyển `EXPIRED` sau deadline 09:30, theo tick 60 giây của publish worker kể cả khi `DISABLED` và pause. Tại 09:31 nếu tick chưa chạy, chờ rồi kiểm `gc2_cutover status 2026-11-25`. Trước `live`, kiểm delivery 21/11 (`2509f430…`) và 25/11 đều `EXPIRED`, không có outbox/command hay execution mới. Nếu còn nonterminal sau một tick, kiểm worker và dừng tại gate. Nếu snapshot cũ, kiểm timer trước và chạy `gc2_cutover backup-check` riêng.

**Make UI T4:** xuất riêng blueprint nguyên trạng scenario production `5868920` qua **Copy blueprint to clipboard**. Lưu vào `_incoming/make_production_export.json` mode 600, ghi SHA-256 và xóa clipboard; không ghi nội dung. Giữ bản gốc để rollback. Chuẩn bị bản scaffold TEST trước import có Webhook 2, HTTP Download 4, Router 5, posts 3/6/12 và mẫu HTTP/Ignore 14/15. Bản TEST sau import không phải scaffold hợp lệ.

## T5 26/11 — cutover, ngày không có slot cadence

1. **Preflight:** UI xác minh Make backup, VENHO OS release/health và BFF production. D1: Harry merge nhánh VENHO OS `codex/gc2-legacy-freeze` (`dd236e5`), chờ timer deploy và kiểm HEAD chứa commit. Legacy route chỉ trả 503 sau switch v2; lượt legacy 25/11 đã duyệt vẫn chạy. Dùng `gc2_cutover status 2026-11-27` để xác nhận `DISABLED`, pause=1, chỉ Hanoi được prepare. `stop-legacy` kiểm backup <1 giờ, mapping ba kênh, không delivery quá hạn nonterminal, Hanoi `IN_REVIEW` hoặc `APPROVED`, không outbox/execution cho slot. Nếu chỉ thiếu backup mới, chạy `gc2_cutover backup-check` → `BACKUP` rồi chạy lại preflight. Vì Harry duyệt sau khi chuyển OS, preflight này dùng phần kiểm readiness không yêu cầu approval; gate cuối vẫn bắt buộc approval đúng revision/hash. Hiển thị trạng thái bảo trì cho đội duyệt và yêu cầu dừng thao tác Growth cũ trên dashboard, Telegram, direct callbacks và workflow trong thời gian freeze.
   Sau khi deploy bản sửa lịch worker, chờ 90 giây để xác minh tick `expire-overdue` tự chạy và slot sắp tới vẫn chưa có command. Worker ghi kết quả từng delivery và số lượt gọi từng tác vụ mỗi 10 phút. MK-1…MK-6 dùng webhook TEST gửi trực tiếp và áp receipt qua lệnh one-shot. Phạm vi đó kiểm Make và receipt, còn scheduler production cần kiểm riêng.

   Nếu còn delivery quá hạn, chạy `gc2_cutover expire-overdue-now` và nhập `EXPIRE` qua terminal. Lệnh yêu cầu production đang `DISABLED` hoặc global pause, đồng thời chưa có grant production. Chạy lại status cho slot cũ và slot đang chuẩn bị. Danh sách `expired` có thể rỗng nếu worker đã chuyển delivery sang `EXPIRED` trước. Kiểm tra không có command hoặc execution mới trước khi tiếp tục.

2. **Dừng legacy:** `gc2_cutover stop-legacy` → `STOP_LEGACY`. Wrapper ghi trạng thái và tạm dừng `venho-os-deploy.timer`, xác minh deploy service đã drain, rồi disable user timers `venho-growth-publish-0900.timer`, `venho-growth-publish-1700.timer`, `venho-growth-weekly-cycle.timer`, `venho-growth-replace-rejected.timer`, `venho-growth-trend-scan.timer`, `venho-growth-fast-lane.timer`, `venho-growth-expire-stale.timer`. Các instances `venho-growth-publish@{primary,second,weekly-cycle,replace-rejected,trend-scan,fast-lane,expire-stale}.service` phải inactive. Không hard-kill job đang chạy. Giữ `venho-growth-reconcile` và `venho-growth-insights` vì chỉ đọc Meta/viết analytics riêng. Tắt manual workflow `growth-publish-scheduler.yml` ở `west-lake-living/venho-ai-studio`; yêu cầu `gh` có quyền Actions write ngay trên máy operator. Kiểm không còn run chưa kết thúc trên cả bốn workflow bằng `gh api --paginate --jq`: mỗi trang phải trả số 0. Kiểm cả quyền đọc các workflow và quyền tắt scheduler trước cửa sổ T5. Nếu thiếu quyền, dừng và xử lý quyền trước khi sang bước tiếp. Nếu unit/state khác inventory, dừng đối chiếu. Đối chiếu registry local theo Git blob với GitHub `main`; không sync hoặc reset tự động. Registry scan chặn `DISPATCHING`, row chưa rõ hoặc bài chờ duyệt/chờ đăng/đã đăng sẵn từ 27/11. Không xóa hay sửa tay registry; Harry phải quyết định disposition trước khi sang bước tiếp. Nếu cần kiểm lại sau khi drain, chạy `gc2_cutover snapshot` theo bước 3.
3. **Drain và snapshot:** Claude kiểm Make History/queue/incomplete buffers, Meta scheduled posts trên cả ba đích và callback legacy vào webhook. Không còn lượt đang chạy, hàng đợi, bài hẹn lịch hoặc grant có thể đăng. `gc2_cutover snapshot` → `MAKE_DRAINED` để lưu private legacy registry/slots, bản sao SQLite của `growth.db` và checksum cho từng file có mặt. Nếu `~/venho/state/growth-reports/insights.db` tồn tại, snapshot và kiểm checksum như trước. Nếu T0-06 chưa chạy và file vắng, `INSIGHTS=ABSENT (D2 deferred)` là kết quả hợp lệ. Các lần kiểm sau phải phát hiện file xuất hiện hoặc biến mất sau snapshot, chạy backup v2 + rehearsal mới, và chạy `legacy-import --dry-run` trên bản sao. Xem báo cáo đếm/mapping đã lọc ở `~/venho/state/growth-engine/cutover-20261126/legacy-dry-run.md`. Importer production chưa an toàn cho Page B/IG và chưa có đường chuyển `insights.db` vào `metric_observations`. Không chuyển approval legacy, không apply delta/import insights vào DB thật từ bước này. D2 đã chốt theo §12.2(4,10): hoãn import thật. Task theo dõi sau cutover: triển khai và chạy backfill T0-06, xác minh mapping Page B/IG, viết đường chuyển insights sang `metric_observations`, đối chiếu report dry-run và xin duyệt trước khi apply.
4. **VENHO OS cố định v2, epoch:** `gc2_cutover switch-and-epoch` → `SWITCH_V2` sau khi snapshot và dry-run bước 3 đạt. Switch giữ v2 sau khi thoát, kiểm health header v2 và login 200, rồi dùng audited `bump_epoch` khi GC2 còn `DISABLED` và chưa có grant production. Worker/API đọc epoch từ runtime controls; không sửa env thủ công. Wrapper kiểm legacy POST trả 503 sau switch v2. Claude đăng nhập, xác nhận Publishing v2, `channels`/controls scope, preview JPEG đúng và đường duyệt legacy đã bị khóa theo thực tế. Nếu URL cũ vẫn có thể ghi, dừng.
5. **Bearer + Make:** `gc2_cutover rotate` → `ROTATE_BEARERS`. Restart ba service sau khi hash đổi; handoff mode 600 dùng đúng principal. Trên Mac chạy khối Make bên dưới, rồi import vào **scenario hiện có 5868920**, vì đây là webhook/connection authority đã được cấu hình cho cả ba route và chỉ có một scenario sản xuất cần quay lui. Không tạo scenario production song song. Import trong lúc không còn legacy sender và GC2 còn pause.
6. **DRY_RUN:** Sau checklist UI, `gc2_cutover dry-run` → `MAKE_MAPPING_CHECKED`. Runtime `DRY_RUN` + pause. So mapping DB và config thật cho cả ba route, đối chiếu UI Page/account đích, cùng một webhook production chứa đúng router, slot 27 chỉ Hanoi, slot 28 dự kiến ba target. Wrapper in inventory cho 27 và 28; slot tương lai chưa tạo hiện mảng delivery rỗng, vẫn đối chiếu được ba mapping cấu hình. Không gửi webhook hoặc cấp grant để kiểm mapping. Khi đã gen slot 28, gate kiểm từng revision/mapping thực tế cho cả ba trước khi resume.
7. **Duyệt:** Harry duyệt slot 27/11 09:00 Page `1124616474074140` trên VENHO OS v2. Tải lại thấy `APPROVED`, xem JPEG và caption. `gc2_cutover live` chạy gate trước khi hỏi `LIVE_HANOI`; kiểm revision/hash/QC, mapping, backup mới, không overdue, và chỉ Hanoi enabled. Kỳ vọng `LIVE_MANUAL`, pause=0, Page B và IG tắt. Legacy phải tiếp tục dừng. Wrapper khôi phục `venho-os-deploy.timer` về trạng thái cũ sau khi arm Hanoi; nếu khôi phục lỗi, kiểm timer và controls trước khi chạy tiếp. Sau giờ slot, không phát lại bất kỳ delivery đã quá deadline.

### Khối Mac — dựng file Make sau khi rotate bearer

Chạy tại checkout cùng SHA bàn giao trên Mac, đã có hai file input ở bước T4. Dùng TTY thật; công cụ đọc Access ID/Secret ẩn. Không dán giá trị vào lệnh. Handoff lấy từ ASUS qua alias đã xác minh.

```bash
job="$(mktemp)"
cat > "$job" <<'SCRIPT'
#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
trap 'rm -f -- "$0"' EXIT
{ exec 3<>/dev/tty; } 2>/dev/null || { echo CONTROLLING_TTY_REQUIRED >&2; exit 2; }
chmod 600 _incoming/make_production_export.json _incoming/make_test_export.json
scp -p asus-server:~/venho/secrets/growth-engine.make-bearers.tmp _incoming/growth-engine.make-bearers.tmp
chmod 600 _incoming/growth-engine.make-bearers.tmp
python3 scripts/growth_engine/prepare_make_test_blueprint.py --environment production \
  --source _incoming/make_test_export.json --production-export _incoming/make_production_export.json
python3 scripts/growth_engine/check_make_blueprint.py _incoming/make_production_import.json
python3 scripts/growth_engine/fill_make_production_secrets.py
SCRIPT
bash "$job"
```

**Make UI:** Sau import đặt **Immediately as data arrives**, bật **Sequential processing**, mở rồi **Save HTTP 25** (I1 GET, body trống) và Save scenario. Đối chiếu method trong mapper viết thường `get`/`post` và mọi key có gạch ngang trong mapping bọc backtick, ví dụ `headers.\`content-type\``. Common filter phải AND `schema_version = growth.command.v2` + `environment = production`; Router đúng ba filter `fb_hanoi`, `fb_venho`, `ig_venho`, fallback off. Xác minh Page Hanoi `1124616474074140`, Page Ven Hồ `803531149684177`, IG `17841457936965829`; production connection `Ven Ho Hotel Hanoi (Ha Pham)`. Instagram nhận signed image URL JPEG 4:5 (variant ≤5 MiB). Kiểm authorize/receipt/Skip đúng nhánh và giữ URL/webhook production không đổi. Xác nhận `/internal` yêu cầu Access, media signed đi đến API và no-store, Cloudflare Host/Access token name đúng. Khóa scenario nếu có sai lệch. Khi import/save/kiểm xong, xóa file import có bí mật và clipboard trên Mac; bản legacy backup vẫn giữ mode 600. Giữ bearer handoff mode 600 tối thiểu trong cửa sổ quay lui nếu cần nhập lại, rồi xóa bản Mac/ASUS.

## T6 27/11 — kiểm bài đầu

09:00 chỉ đọc Make History và Page Hanoi, ghi timestamp/ID, tuyệt đối không Run once. Sau 09:30:

```bash
gc2_cutover status 2026-11-27
```

Kỳ vọng một command, execution `REPORTED/POST_CREATED`, receipt `APPLIED`, verification `EXISTS/MATCH`, delivery `PUBLISHED`, post ID tiền tố `1124616474074140_`. Đối chiếu bài thực tế trên Page. Page B/IG không có bài slot này. Nếu `UNKNOWN`, thiếu receipt hoặc thấy sai Page/ảnh, pause qua VENHO OS ngay nếu đang trong khung khóa script; ngoài khung dùng `gc2_cutover pause` → `PAUSE`. Đối chiếu Make History, Meta, receipts và [UNKNOWN runbook](unknown_reconcile.md). Không retry, resend, cấp grant mới hoặc bật Page B/IG.

## T6 27/11 sau 09:30 — chuẩn bị nhóm 28/11

```bash
gc2_cutover expand
gc2_cutover status 2026-11-28
```

Gõ `EXPAND_TO_THREE` sau khi wrapper chứng minh Hanoi `POST_CREATED`, receipt `APPLIED` và verification cùng execution khớp. Wrapper bật hai target bổ sung dưới global pause để tạo nội dung và queue một package cho ba target. Pause giữ tới khi mở nhóm tối 27/11. Nếu Hanoi không đạt, wrapper dừng trước khi bật hai target. Đối soát Make History, receipt timeout và Page thật theo [UNKNOWN runbook](unknown_reconcile.md).

## T6 27/11 tối — duyệt và mở nhóm cho slot 28/11

Harry duyệt đủ ba delivery trên VENHO OS v2. Đối chiếu Page/account, JPEG, revision và hash trước khi chạy:

```bash
gc2_cutover resume-three
```

Hoàn tất [offsite và diễn tập restore trên Mac](backup_offsite.md) trước bước này. Wrapper kiểm lại Hanoi 27/11 và xác minh trên Drive rằng backup offsite chưa đủ 26 giờ, đúng thư mục và khớp checksum. Khi đạt, gõ `LIVE_THREE` tối 27/11. Cả `expand` và `resume-three` chỉ chạy sau hết phút 09:30 của slot Hanoi và trước 08:30 của slot nhóm. Engine kiểm lại offsite, backup cục bộ mới và approval hiện tại của cả ba target rồi mới bỏ global pause trong `LIVE_MANUAL`. Nếu offsite thiếu, cũ, lệch hash hoặc Drive lỗi, giữ nguyên pause. Kiểm timer và chạy lại `backup offsite-now` sau khi khắc phục.

## T7 28/11 — ba kênh đăng lúc 09:00

Trong khung khóa chỉ đọc Make History và ba đích. Sau 09:30 chạy `gc2_cutover status 2026-11-28` để đối soát receipt/verify từng target. Khi có UNKNOWN, pause và đối soát riêng, không đăng lại.

## Các slot tiếp theo

Jobs lane tạo slot/target tự động mỗi ngày 00:10 ICT, horizon 14 ngày. Tác vụ tạo delivery tự động chạy Chủ nhật 20:00 và 22:00, cộng fast lane mỗi giờ :40 từ 07:40 đến 22:40. Cả hai chỉ chạy khi production không DISABLED và không pause; fast lane hiện cũng có thể lấy target tương lai chưa có delivery. Slot 28/11 được chuẩn bị bằng `expand`. Slot 30/11 nằm trong lượt Chủ nhật 29/11 nếu chưa tạo. Không có SLA cố định T-2. Telegram nhắc T-24h và T-6h theo mốc hạn của bài nếu bot và dashboard URL HTTPS đã cấu hình, poll 15 phút. Mọi delivery vẫn cần Harry duyệt.

Nếu cần SLA T-2 cố định, task riêng là một lượt prepare hằng ngày cho đúng slot cadence sau hai ngày, idempotent theo slot, một package/ba target, reserve qua ledger hiện có và báo thiếu ngân sách. Ước tính 6.200 VND cho một draft + một ảnh, thêm 800–1.200 VND cho 2–3 lượt QC. Tổng 7.000–7.400 VND/slot, khoảng 112.000–140.600 VND cho 16–19 slot/tháng, trước ảnh bổ sung, retry và chi phí khác. Trần GC2 vẫn 500.000 VND/tháng.

## Rollback trước grant đầu tiên (§12.3)

1. `gc2_cutover rollback-pause` → `ROLLBACK_PAUSE`. Pause rồi kiểm **0 production grants**, đặt `DISABLED`. Nếu đã có grant, giữ pause và forward-recover, không cấp lại quyền legacy.
2. Claude deactivate scenario `5868920`, drain, import **bản legacy backup đã kiểm SHA-256**, đặt lại schedule cũ, kiểm hook/filter/connection và bật scenario theo trạng thái cũ. Kiểm không có run đang chờ và không có v2 grant. Không replay.
3. Trong ngày 26/11, sau xác nhận Make và slot legacy còn an toàn, `gc2_cutover rollback-restore` → `LEGACY_MAKE_RESTORED`. Xác minh lại 0 grant, switch OS về legacy và kiểm health, bật từng timer/workflow theo snapshot ban đầu, kiểm enablement/activity/state. Có `Persistent=true`; ngoài `CUTOVER_DATE` wrapper chặn khôi phục timer tự động, cần Harry đối chiếu nguy cơ catch-up trước khi thao tác riêng. Wrapper kiểm POST không session lại trả 401; giữ `venho-os-deploy.timer` dừng khi rollback và in trạng thái. Nếu một phần khôi phục lỗi, giữ GC2 pause và kiểm từng trạng thái trước khi làm tiếp.

## Tham chiếu bootstrap hạ tầng ban đầu

Các bước dưới đây là tham chiếu cài mới; vận hành đợt 25–28/11 theo các khối phía trên.

## 0. Tạo snapshot triển khai và kiểm tra cổng

Trên ASUS server, trong checkout GC2 sạch tại SHA đã review:

```bash
cd "$HOME/venho/gc2-src"
git status --short
git rev-parse HEAD
git fetch origin gc2/build-v1-2
read -r -p 'SHA đã review: ' REVIEWED_GIT_SHA
[[ "$REVIEWED_GIT_SHA" =~ ^[0-9a-f]{40}$ ]]
git cat-file -e "${REVIEWED_GIT_SHA}^{commit}"
git merge-base --is-ancestor "$REVIEWED_GIT_SHA" origin/gc2/build-v1-2
```

**Mong đợi:** working tree sạch; SHA đã review tồn tại và là tổ tiên của `origin/gc2/build-v1-2`. Ghi lại SHA và đường dẫn release hiện hành để rollback:

```bash
readlink -f "$HOME/venho/growth-engine/current"
```

Với bootstrap lần đầu, cổng 8021 phải trống trước khi bật API. Trên production hiện có API active tại 8021; khi cập nhật release, xác nhận listener thuộc Growth API service và không dừng API trước khi deploy script yêu cầu. Không chọn cổng khác nếu owner sai hoặc không xác định được. Cổng 8022/8023 không được tái sử dụng.

```bash
ss -H -ltnp 'sport = :8021'
```

**Mong đợi:** bootstrap đầu tiên không có output; deploy đang chạy phải cho thấy listener 8021 thuộc Growth API. **Dừng:** listener có owner khác/không xác định. Không yêu cầu port trống khi nâng release trên production đang hoạt động.

**Quay lui:** chưa có thay đổi.

## 1. Migrate DB mới, khởi tạo DISABLED, deploy release

Các lệnh dưới đây là quy trình bootstrap ban đầu. Trên server hiện tại, DB/schema 9, controls và channel rows đã tồn tại; **không tạo DB mới, không chạy lại bootstrap/provision**. Để nạp patch sau release `7eedfa3`, dùng checkout sạch tại SHA mới và chạy `deploy-release.sh <SHA>`; script chỉ chạy `migrate --check`, không có migration mới trong patch này. Unit được copy vào user systemd dir, daemon-reload rồi enable đúng cả ba units.

Đường DB production phải nằm trong `~/venho/state/growth-engine/`, tách khỏi legacy. Media dùng `~/venho/state/growth-engine/media/`. Không chạy migrate trên `~/venho/growth-runtime/venho-ai-studio` hoặc legacy DB.

```bash
cd "$HOME/venho/gc2-src"
install -d -m 700 "$HOME/venho/state/growth-engine" "$HOME/venho/state/growth-engine/media"
test "$(stat -c '%a' "$HOME/venho/state/growth-engine")" = 700
test "$(stat -c '%a' "$HOME/venho/state/growth-engine/media")" = 700
```

Đặt `GE_DB_PATH=$HOME/venho/state/growth-engine/growth_engine.db`, `GE_MEDIA_ROOT=$HOME/venho/state/growth-engine/media`, `GE_ENV=production`, `GE_PUBLIC_BASE_URL=https://growth-api.venhohotel.com` trong env file mode 600. Kiểm tra đường dẫn mà không in giá trị:

```bash
systemd-run --user --pipe --wait --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" \
  --setenv=GE_ENV=production \
  /usr/bin/python3 -c 'import os,pathlib,sys; root=(pathlib.Path.home()/"venho/state/growth-engine").resolve(); db=pathlib.Path(os.environ["GE_DB_PATH"]).expanduser().resolve(); media=pathlib.Path(os.environ["GE_MEDIA_ROOT"]).expanduser().resolve(); ok=db.parent==root and media==root/"media" and "legacy" not in str(db).lower(); print("production_state_path="+("PASS" if ok else "FAIL")); sys.exit(0 if ok else 1)'
```

Migrate bằng managed Python 3.11 và khởi tạo control row ở `DISABLED`, global pause bật:

```bash
UV_PYTHON_PREFERENCE=only-managed "$HOME/.local/bin/uv" sync --frozen --python 3.11 --extra api --extra drive --extra gemini
systemd-run --user --pipe --wait --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" \
  --property="WorkingDirectory=$PWD" --setenv=GE_ENV=production \
  "$PWD/.venv/bin/venho-engine" migrate
systemd-run --user --pipe --wait --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" \
  --property="WorkingDirectory=$PWD" --setenv=GE_ENV=production \
  /usr/bin/python3 "$PWD/ops/asus-server/growth-engine/initialize-production-controls.py"
systemd-run --user --pipe --wait --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" \
  --property="WorkingDirectory=$PWD" --setenv=GE_ENV=production \
  "$PWD/.venv/bin/python" ops/asus-server/growth-engine/manage-production-channels.py provision
```

`initialize-production-controls.py` chỉ tạo hàng đầu tiên nếu chưa có; ghi audit; đặt `DISABLED` + `global_pause=1`; nếu thấy mode khác thì dừng, không ghi đè. Chạy lại sau deploy để xác minh vẫn fail-closed.

Deploy đúng SHA trước; deploy script cài unit files và tạo `current`, vì vậy chỉ xác minh unit sau khi release tồn tại:

```bash
git fetch origin gc2/build-v1-2
read -r -p 'SHA đã review: ' REVIEWED_GIT_SHA
[[ "$REVIEWED_GIT_SHA" =~ ^[0-9a-f]{40}$ ]]
git cat-file -e "${REVIEWED_GIT_SHA}^{commit}"
git merge-base --is-ancestor "$REVIEWED_GIT_SHA" origin/gc2/build-v1-2
bash ops/asus-server/growth-engine/deploy-release.sh "$REVIEWED_GIT_SHA"
systemd-analyze --user verify growth-engine-api.service \
  growth-engine-worker@publish.service growth-engine-worker@jobs.service
if [[ "$(loginctl show-user "$USER" -p Linger --value)" != "yes" ]]; then
  sudo loginctl enable-linger "$USER"
fi
test "$(loginctl show-user "$USER" -p Linger --value)" = "yes"
systemctl --user enable growth-engine-api.service growth-engine-worker@publish.service growth-engine-worker@jobs.service
systemctl --user is-enabled growth-engine-api.service growth-engine-worker@publish.service growth-engine-worker@jobs.service
systemctl --user is-active growth-engine-api.service growth-engine-worker@publish.service growth-engine-worker@jobs.service
```

Doctor chạy bằng env production; yêu cầu exit 0, không có `FAIL`, và `Channel config` PASS.

```bash
systemd-run --user --pipe --wait --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" \
  --property="WorkingDirectory=$HOME/venho/growth-engine/current" --setenv=GE_ENV=production \
  "$HOME/venho/growth-engine/current/.venv/bin/venho-engine" doctor
systemd-run --user --pipe --wait --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" --setenv=GE_ENV=production \
  /usr/bin/python3 "$HOME/venho/gc2-src/ops/asus-server/growth-engine/initialize-production-controls.py"
ss -H -ltnp 'sport = :8021'
```

**Mong đợi:** schema current, doctor không có FAIL, API/worker units active và enabled; `Linger=yes`; runtime `DISABLED`, global pause bật; API chỉ bind loopback 8021. Bootstrap ban đầu tạo channel rows disabled.

**Dừng:** ở bootstrap ban đầu, DB nằm ngoài state GC2 mới; doctor có FAIL; controls không `DISABLED` + paused; API không ready hoặc bind sai port; unit chưa enabled/active hoặc `Linger` chưa bật. Doctor WARN cần được giải quyết/ghi nhận trước khi mở kênh. `Publish lane instance` PASS khi lock owner là MainPID duy nhất của unit publish active; lock do PID khác giữ là FAIL.

**Quay lui:** đặt mode `DISABLED` và global pause qua dashboard/API operator trước khi đổi release. `deploy-release.sh` tự rollback `current` nếu switch/healthcheck cùng lượt deploy lỗi. Nếu cần rollback sau deploy thành công, đặt `PREVIOUS_RELEASE` bằng chính đường dẫn đã ghi ở bước 0, kiểm tra nó nằm dưới thư mục releases, rồi atomic-switch và restart:

```bash
read -r -p 'Đường dẫn PREVIOUS_RELEASE đã ghi ở bước 0: ' PREVIOUS_RELEASE
case "$PREVIOUS_RELEASE" in "$HOME/venho/growth-engine/releases/"*) test -d "$PREVIOUS_RELEASE" ;; *) exit 1 ;; esac
ln -s "$PREVIOUS_RELEASE" "$HOME/venho/growth-engine/.current.rollback.$$"
mv -Tf "$HOME/venho/growth-engine/.current.rollback.$$" "$HOME/venho/growth-engine/current"
systemctl --user restart growth-engine-api.service growth-engine-worker@publish.service growth-engine-worker@jobs.service
```

For a first deploy with no previous release, keep the migrated DB/media for diagnosis and stop/disable these three units after the runtime is fail-closed. Do not remove the new state or invoke the legacy publisher.

## 2. Production hostname, Tunnel ingress, DNS và Access

Theo xác nhận 11/11/2026, DNS/Tunnel/Access production đã tồn tại và edge trả đúng 403/404/`private, no-store`. Không tạo route/app/service token trùng. Chỉ tái kiểm tra sau deploy nếu cần; `/internal/*` phải tiếp tục qua Access Service Auth, `/media/publish/*` không qua Access nhưng kiểm signed capability.

Trên server, công cụ sẽ tự backup `/etc/cloudflared/config.yml`, thêm rule trước catch-all, validate file candidate, cài atomic và restart đúng `cloudflared.service`:

```bash
sudo python3 "$HOME/venho/gc2-src/ops/asus-server/growth-engine/configure-production-cloudflared-ingress.py"
```

Rule cố định: `^/(internal|media/publish)/` → `http://127.0.0.1:8021`. Không gọi `cloudflared-update`. Script từ chối route trùng/sai origin, config không có catch-all `http_status:404`, hoặc unit sai. Cloudflared hỗ trợ validate ingress và kiểm tra URL khớp rule qua `tunnel ingress validate`/`tunnel ingress rule` ([Cloudflare config docs](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/configuration-file/)).

```bash
sudo cloudflared --config /etc/cloudflared/config.yml tunnel ingress validate
sudo cloudflared --config /etc/cloudflared/config.yml tunnel ingress rule https://growth-api.venhohotel.com/internal/growth/v2/executions/authorize
sudo cloudflared --config /etc/cloudflared/config.yml tunnel ingress rule https://growth-api.venhohotel.com/media/publish/probe.jpg
systemctl is-active cloudflared.service
```

**Mong đợi:** ingress validation PASS; hai test URL khớp rule mới và origin 8021; service active. Sau khi DNS/Access dashboard được cấp, unauthenticated `/internal` trả 403; request có Access service token qua tới app (GET trên POST-only authorize nên trả 405); malformed `/media/publish` trả API 403 cùng `Cache-Control: private, no-store`.

**Dừng:** Cloudflare Access chặn `/media/publish`; `/internal` mở không xác thực; origin là 8022/8023; route khớp rule sai; Cache-Control thiếu; service không active.

**Quay lui:** script giữ backup có timestamp. Khôi phục đúng file backup đã ghi, chạy `sudo cloudflared --config /etc/cloudflared/config.yml tunnel ingress validate` rồi `sudo systemctl restart cloudflared.service`; xác nhận active. Nếu dashboard đã tạo DNS/Access, Claude xóa/tắt riêng sau khi xác nhận API đang `DISABLED`.

## 3. Production secrets và health notifications

Trên server, tạo ba bearer mới theo principal. `--rotate-existing` là thao tác tường minh vì `GE_SERVICE_TOKENS` đã có hash từ 06/11 và handoff cũ không còn. Script chỉ lưu SHA-256 vào env và ghi bearer plaintext vào handoff mode 600; stdout chỉ in trạng thái, không in bearer.

```bash
cd "$HOME/venho/gc2-src"
python3 ops/asus-server/growth-engine/setup-production-make-bearers.py --rotate-existing
stat -c '%a' "$HOME/venho/secrets/growth-engine.env" "$HOME/venho/secrets/growth-engine.make-bearers.tmp"
```

Trước khi chạy, xác nhận production vẫn `global_pause=1`; lệnh rotation giữ DB và capability key, thay ba service-token hashes. Restart API để nạp hashes mới. Chuyển handoff mode 600 về Mac bằng SCP; không in/cat và không ghi vào shell history. Dùng [fill_make_production_secrets.py](../../../scripts/growth_engine/fill_make_production_secrets.py) để gắn bearer đúng route; giữ handoff server/Mac tới khi các target của slot đầu và slot kế tiếp sau Hanoi đã xác minh xong.

Từ Mac, nạp 5 Meta read token cho ba account production (hai Page aliases + hai biến probe FB + một IG) bằng script đã có. Token nhập ẩn; output chỉ là tên biến/trạng thái:

```bash
python3 ops/asus-server/growth-engine/push-meta-tokens.py --host asus-server
```

Trên server điền `GE_TELEGRAM_BOT_TOKEN`, `GE_TELEGRAM_CHAT_ID`, `GE_HEARTBEAT_URL` từ secret store/Healthchecks; bot token phải thuộc `@venho_growth_alerts_bot`, không dùng `@Venhohotel_bot`. Giữ `growth-engine.env` mode 600. Không gửi tin Telegram thử.

Lấy hạn thật trên ASUS từ IG token đã có trong env production, không in token:

```bash
set -Eeuo pipefail
cd "$HOME/venho/gc2-src"
python3 ops/asus-server/growth-engine/update-meta-token-expiry.py
systemctl --user restart growth-engine-worker@publish.service
```

Script gọi Graph API v27.0 `debug_token` bằng token `GE_META_READ_TOKEN_IG_VENHO` ngay trên server; xác nhận token hợp lệ và thuộc app `1679968647246378`, rồi ghi `expires_at` và `data_access_expires_at` vào `growth-engine.env`. Hạn có ngày được lưu thành ngày ICT; `expires_at` bằng 0 hoặc không có được lưu là `GE_META_TOKEN_EXPIRY_IG_VENHO=never` (token không hết hạn theo thời gian). `data_access_expires_at` vẫn phải có ngày hợp lệ và được giám sát độc lập. Chỉ output mã kết quả và hai giá trị expiry, không output token/URL/lỗi Graph. File env phải là file thường, mode 600, do tài khoản hiện hành sở hữu. Nếu Graph không cho token hiện tại gọi `debug_token`, script dừng mà không sửa env; lúc đó lấy hai ngày trong Access Token Debugger rồi cập nhật thủ công. Restart publish worker để nạp metadata mới.

`doctor` trả WARN khi còn 14 ngày trở xuống hoặc metadata thiếu/sai. Worker publish kiểm tra mỗi 6 giờ và enqueue một Telegram notification bền vững cho mỗi loại expiry/ngày; notification dispatcher gửi qua bot production.

Đối chiếu tên biến mà không in giá trị:

```bash
python3 - "$HOME/venho/secrets/growth-engine.env" <<'PY'
import sys
from pathlib import Path
required = {
    "GE_CAPABILITY_KEYS", "GE_SERVICE_TOKENS", "GE_PUBLIC_BASE_URL", "GE_DASHBOARD_BASE_URL",
    "GE_HEARTBEAT_URL", "GE_TELEGRAM_BOT_TOKEN", "GE_TELEGRAM_CHAT_ID",
    "GE_META_TOKEN_EXPIRY_IG_VENHO", "GE_META_DATA_ACCESS_EXPIRY_IG_VENHO",
    "GE_META_READ_TOKEN_PAGE_A", "GE_META_READ_TOKEN_FB_HANOI", "GE_META_READ_TOKEN_PAGE_B",
    "GE_META_READ_TOKEN_FB_VENHO", "GE_META_READ_TOKEN_IG_VENHO",
    "GE_MAKE_WEBHOOK_URL_PAGE_A", "GE_MAKE_WEBHOOK_URL_PAGE_B", "GE_MAKE_WEBHOOK_URL_IG_VENHO",
}
values = {}
for line in Path(sys.argv[1]).read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        key, value = line.split("=", 1)
        values[key] = value.strip()
missing = [name for name in sorted(required) if not values.get(name) or "REQUIRED_FROM_P0" in values[name]]
for name in missing:
    print(f"MISSING {name}")
if missing:
    sys.exit(1)
print("PASS " + " ".join(sorted(required)))
PY
```

Restart API/workers after env changes; run `doctor` again. Verify heartbeat after one healthy interval (60 s) and inspect only redacted status. Do not test by sending Telegram production message.

**Mong đợi:** all required variable names pass; Meta token helper reports the five names configured; doctor reports expiry dates and warns inside the 14-day window; heartbeat seen; no secret value displayed. Access Client ID/Secret are entered into Make, not this env file.

**Dừng:** thiếu bất kỳ biến nào, file mode khác 600, token/script error, doctor không PASS, heartbeat vắng hoặc notification worker lỗi.

**Quay lui:** giữ API `DISABLED` + global pause; khôi phục env từ secret store đã duyệt, không xóa handoff khi Make cần nạp lại bearer. Không đưa secret vào chat/Git.

## 4. Snapshot, tạo và duyệt Make blueprint production

Trên Make, dùng **Copy blueprint to clipboard** của scenario hiện tại `5868920` làm backup rollback. Lưu clipboard vào `_incoming/make_production_export.json` mode 600, tính checksum ngoài Git, rồi xóa clipboard. Không in/đính kèm file vì có thể chứa webhook/signature. Scenario phải Inactive trong lúc import/chỉnh.

Copy export vào `_incoming/make_production_export.json` với mode 600. Generator hỗ trợ `--environment production`; nó thay filter legacy bằng common filter production, tạo đúng Router 3 nhánh, set đúng Page/IG IDs, giữ connections hiện có từ export, tải hai ảnh Facebook riêng theo nhánh, dùng signed URL cho IG và xóa Webhook response khi sequential:

```bash
umask 077
chmod 600 _incoming/make_production_export.json
python3 scripts/growth_engine/prepare_make_test_blueprint.py \
  --environment production \
  --source _incoming/make_production_export.json \
  --output _incoming/make_production_import.json
python3 scripts/growth_engine/check_make_blueprint.py _incoming/make_production_import.json
```

Checker phải PASS: 26 module, 3 route, không URL/secret literal; module destinations phải là `1124616474074140`, `17841457936965829`, `803531149684177`. Nếu export khác format, destination key không nhận diện được, checker fail hoặc giữ literal cũ, dừng; không sửa Make thủ công theo phỏng đoán.

Checker chạy trên blueprint draft **chưa có secret**. Sau khi draft pass và được Harry duyệt, chuyển handoff bearer mode 600 từ server về `_incoming/growth-engine.make-bearers.tmp`, rồi chạy filler production trên Mac:

```bash
chmod 600 _incoming/make_production_import.json _incoming/growth-engine.make-bearers.tmp
python3 scripts/growth_engine/fill_make_production_secrets.py
stat -f '%Lp' _incoming/make_production_import.secret.json
```

Filler hỏi Access Client ID/Secret ẩn, dùng base URL `https://growth-api.venhohotel.com`, đối chiếu bearer theo route và ghi `_incoming/make_production_import.secret.json` mode 600. Không chạy `check_make_blueprint.py` trên file đã điền bearer; filler tự kiểm 3 route, 9 internal modules, header/host và placeholder, chỉ in số lượng thay. Không commit file secret.

**Chỉ sau khi Harry duyệt bản draft reviewable:** import file secret vào scenario `5868920`, giữ scenario Inactive khi nhập. Kiểm tra connection hiện có trên từng module, Router/filter/channel IDs và thứ tự route; `Venho signature` bị gỡ, common filter là `schema_version = growth.command.v2` AND `environment = production`. Ghi bước xoay/retire literal hex theo [retire_legacy.md](retire_legacy.md), không ghi giá trị.

Sau import tách riêng hai thao tác UI bắt buộc: (1) đặt scheduling về **Immediately as data arrives** rồi Save; (2) mở HTTP module `25` (I1), xác nhận Method `GET` và body rỗng, rồi Save module. Giữ sequential ON, error handler terminal Skip, Store incomplete executions = No, không có Retry/Break/Resume và không thêm Webhook response.

Caption của post module lấy từ authorize response (`data.caption`), là nội dung approved của command. Facebook mỗi route tải `media_url` riêng rồi map binary của route đó; Instagram map signed `media_url`. Receipt map verbatim module output `id`. Hai Page Facebook là hai command riêng, không một payload fan-out.

**Mong đợi:** scenario Inactive trong lúc review; đúng 26 module/3 route, connections không đổi; immediate trigger, sequential ON, HTTP 25 saved; secret fields được Make bảo vệ; không đăng bài.

**Dừng:** thiếu Harry approval, ID/connection không khớp, literal URL còn, filter sai, schedule/Module 25 chưa Save, hoặc scenario bị Active ngoài giờ cutover.

**Quay lui:** khi runtime vẫn `DISABLED` và scenario Inactive, import export rollback đã lưu, kiểm tra connection/filter, khôi phục setting cũ và giữ scenario Inactive cho đến khi đối chiếu xong. Không bật legacy nếu không có quyết định retire/rollback mới.

## 5. Lịch, command và duyệt nhóm

Không sửa `config/projects/venho_hotel/growth/cadence_policy.yaml`: 4 slot/tuần (Mon/Wed/Fri/Sat 09:00 ICT). Sau khi đủ production channels, `EnsureSlots` phải tạo 4 slot và 12 targets mỗi tuần: 4 Hanoi, 4 Ven Hồ, 4 Instagram. Mỗi FB slot dùng một approved Facebook caption/ảnh bytes nhưng có 2 delivery, 2 command, 2 receipt và 2 verify. Cả hai delivery FB thuộc cùng nhóm duyệt; batch approval hỗ trợ hai Page cùng Instagram và không tự dispatch.

Trước mở channel, VENHO OS phải hiển thị đúng 4 slot cùng 12 targets và group approval. Kiểm tra không có due/overdue approved command nào sẽ được phát ngoài ý muốn khi pause được mở. Không bấm duyệt hoặc chuyển runtime nếu inventory slot/targets chưa khớp.

**Quay lui:** giữ `DISABLED` + pause; sửa lịch/targets trên database production qua luồng được audit. Không sửa trực tiếp SQL.

## 6. Mở theo thứ tự — LIVE_MANUAL

Ba channel/config records đã được provision disabled ở bước 1. `manage-production-channels.py set-enabled` chỉ cho phép mở nếu runtime `LIVE_MANUAL`, global pause đang bật, ID đúng, config có và thứ tự mở hợp lệ. Thực hiện trên dashboard operator:

1. Trong P4 dry run giữ `DISABLED` + pause. Chỉ tại T−0 đã tính sau P4 PASS, bài được Harry duyệt và đủ 48 giờ đệm mới chuyển sang `LIVE_MANUAL`, vẫn giữ pause ON, rồi bật riêng `fb_hanoi` cho slot được chọn. Legacy publisher được tạm dừng sau khi export backup và drain runs/grants; không xóa code/registry/literal.
2. Mở `fb_hanoi`:

   ```bash
   systemd-run --user --pipe --wait --collect \
     --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" --setenv=GE_ENV=production \
     "$HOME/venho/growth-engine/current/.venv/bin/python" \
     "$HOME/venho/gc2-src/ops/asus-server/growth-engine/manage-production-channels.py" set-enabled --channel fb_hanoi --enable
   ```

   Khi còn pause, rà route, filter, Page ID `1124616474074140`, approved slot và ảnh. Tại 09:00 của slot Hanoi đầu tiên đã chọn theo điều kiện 48 giờ, chỉ bỏ global pause theo lịch đã duyệt; đối chiếu Make History → receipt APPLIED → verify. Page `fb_venho` và IG chưa publish slot đầu theo staging decision.
3. Sau khi Hanoi ổn, giữ/đặt pause ON. Trước generation cho slot lịch kế tiếp, bật `fb_venho` bằng lệnh tương tự, rà ID `803531149684177`; bật `ig_venho`, rà ID `17841457936965829`. Đảm bảo ba targets cùng tồn tại trước khi jobs lane tạo package, rồi group-approve slot đó. Resume đúng 09:00 và đối soát từng receipt.
4. Lỗi ở Ven Hồ/IG được xử lý riêng theo route/receipt; không resend Hanoi. IG dùng signed URL; xác minh media ID và MK-11/container-publish evidence.

Mỗi lần xác minh phải dựa trên bài đã tới lịch; không gửi thử ngoài lịch. MK-11 và route `fb_venho` được kiểm đúng ở các bước mở tương ứng.

**Dừng / quay về DISABLED:** bất kỳ ID, filter, ảnh, outcome hoặc receipt nào không rõ; lỗi/timeout sau khi post module bắt đầu; duplicate/UNKNOWN; thiếu group approval. Qua operator API, bật global pause và đặt mode `DISABLED`, giữ scenario Inactive nếu cần, rồi tắt target bằng script sau khi pause:

```bash
systemd-run --user --pipe --wait --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" --setenv=GE_ENV=production \
  "$HOME/venho/growth-engine/current/.venv/bin/python" \
  "$HOME/venho/gc2-src/ops/asus-server/growth-engine/manage-production-channels.py" set-enabled --channel fb_hanoi --disable
systemd-run --user --pipe --wait --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" --setenv=GE_ENV=production \
  "$HOME/venho/growth-engine/current/.venv/bin/python" \
  "$HOME/venho/gc2-src/ops/asus-server/growth-engine/manage-production-channels.py" set-enabled --channel fb_venho --disable
systemd-run --user --pipe --wait --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" --setenv=GE_ENV=production \
  "$HOME/venho/growth-engine/current/.venv/bin/python" \
  "$HOME/venho/gc2-src/ops/asus-server/growth-engine/manage-production-channels.py" set-enabled --channel ig_venho --disable
```

Đối soát command/execution/receipt trước mọi lần gửi tiếp. Không chạy lại module đăng và không gửi lại Hanoi để sửa riêng Ven Hồ.

## 7. Dọn TEST sau khi cutover được đối soát

Sau khi mọi ca TEST/MK còn mở đã được đóng, evidence đã lưu an toàn và không còn cần re-import:

```bash
systemctl --user stop growth-engine-api-test-src
systemctl --user is-active growth-engine-api-test-src || true
rm -f "$HOME/venho/secrets/growth-engine-test.make-bearers.tmp"
find "$HOME/venho/state/growth-engine-test" -path '*/secrets/growth-engine-test.make-bearers.tmp' -type f -delete
rm -f "$HOME/venho/secrets/growth-engine.make-bearers.tmp"
test ! -e "$HOME/venho/secrets/growth-engine-test.make-bearers.tmp"
test ! -e "$HOME/venho/secrets/growth-engine.make-bearers.tmp"
```

Không xóa TEST DB/media/archive hoặc bài test cho tới khi evidence được review; việc xóa bài là quyết định riêng của Harry.

## Các biến secret phải có mặt (chỉ tên)

| Nhóm | Tên biến / nguồn |
|---|---|
| Meta read | `GE_META_READ_TOKEN_PAGE_A`, `GE_META_READ_TOKEN_FB_HANOI`, `GE_META_READ_TOKEN_PAGE_B`, `GE_META_READ_TOKEN_FB_VENHO`, `GE_META_READ_TOKEN_IG_VENHO` |
| Make webhook refs | `GE_MAKE_WEBHOOK_URL_PAGE_A`, `GE_MAKE_WEBHOOK_URL_PAGE_B`, `GE_MAKE_WEBHOOK_URL_IG_VENHO` |
| Make bearer | `GE_MAKE_BEARER_FB_HANOI`, `GE_MAKE_BEARER_FB_VENHO`, `GE_MAKE_BEARER_IG_VENHO` trong handoff mode 600; hash theo principal trong `GE_SERVICE_TOKENS` |
| Runtime + alerts | `GE_CAPABILITY_KEYS`, `GE_TELEGRAM_BOT_TOKEN` (bot `@venho_growth_alerts_bot`), `GE_TELEGRAM_CHAT_ID`, `GE_HEARTBEAT_URL` |
| Meta expiry metadata | `GE_META_TOKEN_EXPIRY_IG_VENHO`, `GE_META_DATA_ACCESS_EXPIRY_IG_VENHO` (dates only; no token value) |
| Make Access | `CF-Access-Client-Id`, `CF-Access-Client-Secret` nhập vào từng module `/internal`; không lưu trong repo |

Không ghi URL webhook, token, signed URL, Access secret hoặc thông tin đăng nhập vào runbook/log/chat.
