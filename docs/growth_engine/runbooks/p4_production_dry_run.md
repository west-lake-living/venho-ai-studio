# P4 production dry run — chuẩn bị bài, không dispatch

**Mục tiêu:** tạo đúng một delivery `fb_hanoi` cho một slot cadence tương lai; chạy provider legacy thật dưới ngân sách v2 riêng; tạo variant, QC và bản nháp; Harry duyệt trên VENHO OS. Runtime luôn `DISABLED`, `global_pause=1`; không gọi Make, không tạo command đăng bài và không đăng công khai.

**Ngày T−0 16/11/2026 đã hủy.** P4 dùng slot cadence được chọn sau khi kiểm tra lịch. Chỉ tính ngày cutover sau khi P4 PASS và Harry duyệt một delivery `fb_hanoi` thật trên VENHO OS; chọn slot gần nhất còn cách thời điểm cả hai điều kiện đạt ít nhất 48 giờ. Không tự khôi phục lịch cũ.

## Trạng thái triển khai

Code P4 có audited `prepare-only`, worker cho `generate_slot` → `prepare_variant` → `assemble_revision`/QC, review snapshot, ngân sách v2 riêng và lệnh chỉ đọc `cutover-readiness`. Test SQLite giả lập toàn luồng đã chứng minh approval không dispatch khi `DISABLED`. Đây chưa phải bằng chứng chạy provider thật, duyệt UI production hay P4 PASS.

Provider do Harry chọn là provider và key legacy đang chạy: `ANTHROPIC_API_KEY` và `OPENAI_API_KEY` từ `~/venho/secrets/growth.env`. Wrapper chỉ chuyển hai key này sang worker/doctor; DB, media root, capability, tokens và controls vẫn lấy từ `~/venho/secrets/growth-engine.env`. Không in giá trị hoặc chạy dưới `set -x`.

## 1. Deploy và kiểm tra fail-closed

Trên ASUS server, thay `<P4_SHA>` bằng commit đã push của lượt này:

```bash
cd "$HOME/venho/gc2-src"
git status --short
git fetch origin gc2/build-v1-2
git merge-base --is-ancestor <P4_SHA> origin/gc2/build-v1-2
bash ops/asus-server/growth-engine/deploy-release.sh <P4_SHA>
systemctl --user is-enabled growth-engine-api.service growth-engine-worker@publish.service growth-engine-worker@jobs.service
systemctl --user is-active growth-engine-api.service growth-engine-worker@publish.service growth-engine-worker@jobs.service
loginctl show-user "$USER" -p Linger --value
"$HOME/venho/growth-engine/current/ops/asus-server/growth-engine/run-with-legacy-provider-env.sh" doctor
```

**PASS:** checkout sạch; release đúng SHA; ba unit enabled/active; linger `yes`; doctor không `FAIL`; production controls đọc được là `DISABLED` + pause `1`; channel records đã map đúng.

**FAIL/dừng:** doctor thiếu key/policy/ngân sách, bất kỳ `FAIL`, unit/linger chưa đúng hoặc controls khác yêu cầu. Chưa bật channel và chưa queue job. Doctor chỉ in tên biến key, provider và số dư ngân sách v2.

## 2. Mở đúng một target ở chế độ chuẩn bị

Đọc controls/channel trước khi đổi. Dùng helper audit, không chạy SQL sửa trạng thái:

```bash
systemd-run --user --pipe --wait --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" \
  --property="WorkingDirectory=$HOME/venho/growth-engine/current" \
  "$HOME/venho/growth-engine/current/.venv/bin/python" \
  "$HOME/venho/growth-engine/current/ops/asus-server/growth-engine/manage-production-channels.py" \
  set-enabled --channel fb_hanoi --enable --prepare-only
```

Helper chỉ cho phép `fb_hanoi` Page `1124616474074140`, khi runtime `DISABLED`, global pause ON và hai channel còn lại tắt; audit ghi action `prepare_only_enable`. Đây là enable cho tạo nội dung, không cho publish.

Trong trạng thái `DISABLED`, publish scheduler và authorize fail-closed; integration test chứng minh outbox không được claim và FakeMake nhận 0 lệnh dù Hanoi enabled. Jobs worker cũng chặn recurring slot/weekly/fast/replacement generation khi production đang DISABLED hoặc global pause. Nó vẫn xử lý `content_jobs` được queue rõ ràng bằng lệnh P4 ở bước kế tiếp.

**PASS:** helper báo chỉ Hanoi enabled; `fb_venho`/`ig_venho` vẫn disabled; controls không đổi; publish worker vẫn active nhưng không dispatch.

## 3. Chọn slot cadence và queue một lần

Chọn ngày cadence tương lai đủ thời gian review, không chọn lại slot đã qua. Lịch hiện tại là Mon/Wed/Fri/Sat lúc 09:00 ICT. Ví dụ 20/11/2026:

```bash
"$HOME/venho/growth-engine/current/ops/asus-server/growth-engine/run-with-legacy-provider-env.sh" \
  prepare-slot --date 2026-11-20 --channel fb_hanoi
```

Lệnh idempotent: chạy lại trả cùng job cho cùng slot, không phát sinh generation thứ hai. Output chỉ có `slot_id`, `job_id`, trạng thái và `replayed`.

Jobs worker `growth-engine-worker@jobs` xử lý job đã queue; không chạy thêm worker thứ hai. Nó thực hiện generation → lưu asset gốc → `prepare_variant` Facebook JPEG → QC có ngân sách → `assemble_revision` thành `IN_REVIEW`. Mọi recurring generation lane khác đang bị gate ở controls hiện tại.

Với policy hiện tại, doctor cần đủ dự phòng tối đa cho một slot: text 5.000 + tối đa một ảnh 1.200 + tối đa hai lần QC 400 = **7.000 VND**. Ngân sách v2 tháng là 500.000 VND, độc lập ledger legacy. Generation và từng QC call reserve trước khi gọi provider, settle khi có kết quả; lỗi không xác định chuyển `UNKNOWN`, không retry tự động. Không tăng cap trong lần dry run.

Kiểm trạng thái chỉ đọc, không in caption, path, token hoặc signed URL:

```bash
python3 - "$HOME/venho/state/growth-engine/growth_engine.db" 2026-11-20 <<'PY'
import sqlite3, sys
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
for row in db.execute("SELECT publish_mode, global_pause FROM runtime_controls WHERE environment='production'"):
    print("controls:", dict(row))
for row in db.execute("SELECT channel_key, enabled, paused, remote_account_id FROM channels WHERE environment='production' ORDER BY channel_key"):
    print("channel:", dict(row))
for row in db.execute("""SELECT s.local_date, s.local_time, c.channel_key, c.remote_account_id,
       d.state AS delivery_state, v.mime, v.width, v.height, v.byte_size, v.qc_status, q.decision AS qc_decision
       FROM slots s JOIN slot_targets t ON t.slot_id=s.id JOIN channels c ON c.id=t.channel_id
       LEFT JOIN deliveries d ON d.target_id=t.id AND d.active=1
       LEFT JOIN delivery_revisions r ON r.id=d.current_revision_id
       LEFT JOIN media_variants v ON v.id=r.variant_id LEFT JOIN qc_reports q ON q.id=r.qc_report_id
       WHERE s.local_date=? AND c.environment='production' ORDER BY c.channel_key""", (sys.argv[2],)):
    print("target:", dict(row))
for row in db.execute("SELECT kind, state, count(*) AS count FROM jobs GROUP BY kind, state ORDER BY kind, state"):
    print("job:", dict(row))
for row in db.execute("SELECT operation, state, reserved_minor, actual_minor FROM paid_calls ORDER BY created_at"):
    print("paid_call:", dict(row))
db.close()
PY
```

**PASS:** một target `fb_hanoi` đúng Page ID, delivery `IN_REVIEW`, Facebook variant là JPEG đúng profile và QC `PASS`/`REVIEW`; jobs generation/variant/assembly hoàn tất; `paid_calls` generation/QC ở `SETTLED`; runtime vẫn `DISABLED` + pause `1`; không có outbox command/execution.

**FAIL/dừng:** job `FAILED`/`UNKNOWN`, QC `FAIL`, mapping/variant sai, ledger `RESERVED` bất thường, controls thay đổi hoặc có dispatch artifact. Không retry job/provider có kết quả `UNKNOWN`; giữ legacy là publisher duy nhất.

## 4. Harry duyệt bài thật trên VENHO OS

Trong `os.venhohotel.com`, mở **Publishing → Growth Engine → Chờ duyệt** và chọn slot đã queue. Tài khoản operator cần quyền duyệt nhóm (`dashboard:write`). Màn review phải hiển thị:

- kênh `fb_hanoi`, Page ID `1124616474074140`, slot/ngày giờ ICT;
- preview đúng variant JPEG, caption và nhãn **Ảnh dự phòng** nếu bản được chọn là fallback;
- revision, QC và trạng thái `IN_REVIEW` khớp DB.

Harry kiểm tra bài rồi duyệt trên UI. Sau khi tải lại, xác nhận delivery `APPROVED`, approval gắn đúng revision/hash và controls vẫn `DISABLED` + pause `1`. Approval không được tạo command, execution, webhook hay Make History run.

**FAIL/BLOCKED_UI:** màn hình, quyền, Page ID, preview, caption hoặc approval không khớp. Không thay bằng approval registry legacy.

## 5. Chạy readiness chỉ đọc và chốt P4

```bash
"$HOME/venho/growth-engine/current/ops/asus-server/growth-engine/run-with-legacy-provider-env.sh" \
  cutover-readiness --date 2026-11-20 --time 09:00
```

Lệnh mở SQLite `mode=ro`, không build worker, gọi provider, gọi Make hay sửa DB. **PASS** chỉ khi slot có delivery `fb_hanoi` `APPROVED` đang active; approval khớp revision/hash hiện hành; QC/variant gắn đúng; Page ID `1124616474074140` và route ref `GE_MAKE_WEBHOOK_URL_PAGE_A` khớp mapping đã snapshot trong revision; không có outbox/execution cho delivery đó; runtime vẫn `DISABLED` + pause `1`.

Lưu kết quả lệnh, SHA deploy, thời điểm ICT, slot/delivery/revision ID, job state, ledger state và Harry approval vào biên bản không chứa bí mật. Chỉ ghi P4 PASS khi doctor, generation/QC, VENHO OS approval và `cutover-readiness` đều PASS. Đến đây vẫn không chuyển runtime sang `LIVE_MANUAL`, không bật Make và không dừng legacy.

**Dự kiến:** nếu deploy/test provider và UI được hoàn tất trong 13–14/11, P4 có thể PASS sớm nhất **14/11/2026**. Sau đó chọn ngày cutover mới theo điều kiện ≥48 giờ và slot cadence; ngày 16/11 cũ đã hủy.
