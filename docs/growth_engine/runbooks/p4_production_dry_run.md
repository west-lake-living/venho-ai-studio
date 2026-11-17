# P4 production dry run — chuẩn bị bài, không dispatch

**Mục tiêu:** tạo đúng một delivery `fb_hanoi` cho một slot cadence tương lai; chạy provider legacy thật dưới ngân sách v2 riêng; tạo variant, QC và bản nháp; Harry duyệt trên VENHO OS. Runtime luôn `DISABLED`, `global_pause=1`; không gọi Make, không tạo command đăng bài và không đăng công khai.

**Ngày T−0 16/11/2026 đã hủy.** P4 dùng slot cadence được chọn sau khi kiểm tra lịch. Chỉ tính ngày cutover sau khi P4 PASS và Harry duyệt một delivery `fb_hanoi` thật trên VENHO OS; chọn slot gần nhất còn cách thời điểm cả hai điều kiện đạt ít nhất 48 giờ. Không tự khôi phục lịch cũ.

## Trạng thái triển khai

Code P4 có audited `prepare-only`, worker cho `generate_slot` → ảnh gốc → `prepare_variant` → QC trong bước `assemble_revision`, review snapshot, ngân sách v2 riêng và lệnh chỉ đọc `cutover-readiness`. Doctor xác minh image allowlist theo catalog legacy và SHA-256 dưới thư mục ảnh server.

Provider do Harry chọn là provider và key legacy đang chạy: `ANTHROPIC_API_KEY` và `OPENAI_API_KEY` từ `~/venho/secrets/growth.env`. Wrapper chỉ chuyển hai key này sang worker/doctor/repair; cấu hình Growth Engine còn lại lấy từ `~/venho/secrets/growth-engine.env`. Không in giá trị hoặc chạy dưới `set -x`.

**Nguồn ảnh theo quyết định Harry:** đọc read-only từ `/home/serveradmin/venho/growth-runtime/venho-ai-studio/assets/raw`. Resolver dùng đúng `config/projects/venho_hotel/growth/reference_assets.yaml`: `venho_rooftop_railing_approved` → `outside`; `venho_room_lake_view_approved` → `room` (đệ quy, gồm `ViewHo-room-1`); `venho_lobby_approved` → `lobby`; `venho_street_railing_approved` và `venho_lake_landscape_approved` → `westlake`. Không có reference ID legacy cho `facade` hoặc `linh_an`; `linh_an` không được allowlist nếu catalog không phê duyệt ảnh người dùng công khai. Không suy luận mapping từ tên file.

Production image allowlist nằm ngoài repo tại `~/venho/config/growth-engine-image-library.yaml` (mode 600). Mỗi mục ghim `path` tương đối bên dưới thư mục nguồn cùng SHA-256. `LocalLegacyImageLibrary` mở file read-only, từ chối `..`, absolute path và symlink, rồi kiểm SHA/định dạng trước khi ingest. Không copy hoặc sửa ảnh legacy. Option A dùng bytes tham chiếu cho GPT Image edit; option C dùng ảnh thật theo cùng vòng xoay legacy. Asset được lưu trong GC2 `media_assets` theo SHA-256.

Doctor chỉ bắt buộc các ID xuất hiện trong scenario registry **và** catalog ảnh legacy. Scenario ID không có trong catalog legacy được báo là bỏ qua, không chặn deploy. Với catalog hiện tại, năm nhóm trên đều được dùng; nếu server không còn ảnh trong folder tương ứng, inventory sẽ nêu nhóm đó và dừng ghi config để Harry bổ sung hoặc quyết định sửa catalog. Doctor kiểm tra file allowlist và SHA thật trước khi đổi release.

## 1. Deploy và kiểm tra fail-closed

Trên ASUS server, thay `<P4_SHA>` bằng commit đã push. Tạo checkout tạm đúng SHA để `deploy-release.sh` cũng lấy unit và wrapper từ cùng revision; không dùng file unit cũ trong `gc2-src`:

```bash
set -Eeuo pipefail
P4_SHA='<P4_SHA>'
REMOTE_URL="$(git -C "$HOME/venho/gc2-src" remote get-url origin)"
SOURCE_DIR="$(mktemp -d "$HOME/venho/gc2-deploy-source.XXXXXX")"
trap 'rm -rf "$SOURCE_DIR"' EXIT
git clone --quiet --no-checkout "$REMOTE_URL" "$SOURCE_DIR"
git -C "$SOURCE_DIR" fetch --quiet origin gc2/build-v1-2
git -C "$SOURCE_DIR" merge-base --is-ancestor "$P4_SHA" origin/gc2/build-v1-2
git -C "$SOURCE_DIR" checkout --quiet --detach "$P4_SHA"
[[ -z "$(git -C "$SOURCE_DIR" status --porcelain)" ]]
bash "$SOURCE_DIR/ops/asus-server/growth-engine/deploy-release.sh" "$P4_SHA"
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

Với một P4 mới chưa có package, chọn ngày cadence tương lai đủ thời gian review. Slot 21/11/2026 đã có DRAFT/package nên **không chạy `prepare-slot` lại cho ngày này**; dùng Section 6 để phục hồi media. Lịch hiện tại là Mon/Wed/Fri/Sat lúc 09:00 ICT. Lệnh minh họa dưới đây chỉ dành cho slot mới chưa có package:

```bash
"$HOME/venho/growth-engine/current/ops/asus-server/growth-engine/run-with-legacy-provider-env.sh" \
  prepare-slot --date 2026-11-21 --channel fb_hanoi
```

Lệnh idempotent: chạy lại trả cùng job cho cùng slot, không phát sinh generation thứ hai. Output chỉ có `slot_id`, `job_id`, trạng thái và `replayed`.

Jobs worker `growth-engine-worker@jobs` xử lý job đã queue; không chạy thêm worker thứ hai. Nó thực hiện generation → lưu asset gốc → `prepare_variant` Facebook JPEG → QC có ngân sách → `assemble_revision` thành `IN_REVIEW`. Mọi recurring generation lane khác đang bị gate ở controls hiện tại.

Với policy hiện tại, doctor cần đủ dự phòng tối đa cho một slot: text 5.000 + tối đa một ảnh 1.200 + tối đa hai lần QC 400 = **7.000 VND**. Ngân sách v2 tháng là 500.000 VND, độc lập ledger legacy. Generation và từng QC call reserve trước khi gọi provider, settle khi có kết quả; lỗi không xác định chuyển `UNKNOWN`, không retry tự động. Không tăng cap trong lần dry run.

Kiểm trạng thái chỉ đọc, không in caption, path, token hoặc signed URL:

```bash
python3 - "$HOME/venho/state/growth-engine/growth_engine.db" 2026-11-21 <<'PY'
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
  cutover-readiness --date 2026-11-21 --time 09:00
```

Lệnh mở SQLite `mode=ro`, không build worker, gọi provider, gọi Make hay sửa DB. **PASS** chỉ khi slot có delivery `fb_hanoi` `APPROVED` đang active; approval khớp revision/hash hiện hành; QC/variant gắn đúng; Page ID `1124616474074140` và route ref `GE_MAKE_WEBHOOK_URL_PAGE_A` khớp mapping đã snapshot trong revision; không có outbox/execution cho delivery đó; runtime vẫn `DISABLED` + pause `1`.

Lưu kết quả lệnh, SHA deploy, thời điểm ICT, slot/delivery/revision ID, job state, ledger state và Harry approval vào biên bản không chứa bí mật. Chỉ ghi P4 PASS khi doctor, generation/QC, VENHO OS approval và `cutover-readiness` đều PASS. Đến đây vẫn không chuyển runtime sang `LIVE_MANUAL`, không bật Make và không dừng legacy.

**Dự kiến:** ngày cutover chỉ tính sau P4 PASS và Harry duyệt một delivery thật trên VENHO OS, với ít nhất 48 giờ đệm.

## 6. Khôi phục DRAFT thiếu ảnh của slot 21/11

**Dry run 17/11/2026:** `generate_slot` và `generate_package` đã thành công; có một DRAFT và paid call đã `SETTLED`, nhưng không có media asset, variant, QC hoặc revision. Root cause là release checkout không có các thư mục `assets/raw` mà resolver legacy ánh xạ tới; adapter cũ bỏ qua ảnh thiếu, còn assembly trước đó được queue dù package không có media. Không có outbox command hoặc execution. Không chạy `prepare-slot`/`generate_package` lần nữa cho slot này.

Lệnh inventory dùng mapping catalog; ảnh trong `facade` và `linh_an` không được đưa vào allowlist tự động. Mỗi lần chạy sẽ in candidate path tương đối, group đề xuất và SHA-256. Chỉ nhập `WRITE` sau khi Harry xem danh sách; file đích là `~/venho/config/growth-engine-image-library.yaml`, mode 600, ngoài Git. Nếu một group đang được catalog dùng nhưng không có file, script dừng ghi.

Lệnh dán một lần sau khi commit này đã được push. Nó lấy checkout sạch SHA mới nhất của nhánh, cho Harry xem và xác nhận allowlist, deploy release, hiển thị topic/brief DRAFT để Harry chọn đúng reference group, rồi chờ status hoàn tất. `repair-p4-media` không gọi lại `generate_package`; không chạy khi Harry không xác nhận candidate list hoặc group bài:

```bash
set -Eeuo pipefail
fail() { printf 'P4 recovery stopped: %s\n' "$*" >&2; exit 1; }
REPO="$HOME/venho/gc2-src"
BRANCH="gc2/build-v1-2"
REMOTE_URL="$(git -C "$REPO" remote get-url origin)"
SOURCE_DIR="$(mktemp -d "$HOME/venho/gc2-p4-source.XXXXXX")"
trap 'rm -rf "$SOURCE_DIR"' EXIT
git clone --quiet --no-checkout "$REMOTE_URL" "$SOURCE_DIR"
git -C "$SOURCE_DIR" fetch --quiet origin "$BRANCH"
P4_SHA="$(git -C "$SOURCE_DIR" rev-parse FETCH_HEAD)"
git -C "$SOURCE_DIR" checkout --quiet --detach "$P4_SHA"
[[ -z "$(git -C "$SOURCE_DIR" status --porcelain)" ]] || fail "source checkout is not clean"

# Read-only inventory; the script writes only the external allowlist after Harry types WRITE.
python3 "$SOURCE_DIR/scripts/growth_engine/prepare_legacy_image_library.py" --apply \
  || fail "image inventory was rejected, incomplete, or not confirmed"

# The release doctor validates all catalog-used groups and every pinned SHA before switching.
bash "$SOURCE_DIR/ops/asus-server/growth-engine/deploy-release.sh" "$P4_SHA"
RUNTIME="$HOME/venho/growth-engine/current/ops/asus-server/growth-engine/run-with-legacy-provider-env.sh"
"$RUNTIME" repair-p4-media --date 2026-11-21 --channel fb_hanoi \
  || fail "media repair did not queue; confirm the legacy reference group shown by the prompt"

STATUS=""
for ((attempt=1; attempt<=120; attempt++)); do
  STATUS="$("$RUNTIME" p4-slot-status --date 2026-11-21)"
  if printf '%s' "$STATUS" | python3 -c 'import json,sys; d=json.load(sys.stdin); j=[x for x in d.get("jobs",[]) if x.get("kind") in {"prepare_variant","assemble_revision"}]; sys.exit(0 if len(j)>=2 and all(x.get("state")=="SUCCEEDED" for x in j) else 3 if any(x.get("state") in {"FAILED","UNKNOWN","DEAD"} for x in j) else 1)'; then
    break
  else
    result=$?
    if [[ "$result" -eq 3 ]]; then printf '%s\n' "$STATUS"; fail "media job reached a terminal error"
    elif [[ "$attempt" -eq 120 ]]; then printf '%s\n' "$STATUS"; fail "timed out waiting for media jobs"
    fi
  fi
  sleep 5
done
printf '%s\n' "$STATUS"
```

**PASS:** asset có SHA nguồn; `prepare_variant` và `assemble_revision` đều `SUCCEEDED`; DRAFT chuyển `IN_REVIEW`; JPEG/QC `PASS` hoặc `REVIEW`; `draft_package` vẫn chỉ có một lượt `SETTLED`; controls vẫn DISABLED/pause; outbox và execution đều bằng 0. Lệnh status chỉ in ID, trạng thái, đường dẫn tương đối và lỗi đã lọc; không in caption, absolute path, URL hay token.

Worker giữ `assemble_revision` ở `PENDING` trước khi claim nếu thiếu variant, cập nhật `last_error` bằng mã/message và lùi `run_at`; vì vậy nó không tiêu attempt liên tục. Nếu variant mất sau preflight do race, handler cũng defer về `PENDING`. Chạy lại `repair-p4-media` để queue lại prepare và assembly. Không sửa SQL tay. Nếu job báo lỗi khác, dùng code/message đã lọc và log INFO mỗi job để sửa riêng lỗi media.

### Notification jobs PENDING

`DISABLED`/`global_pause` ngăn publish/dispatch, không ngăn worker gửi thông báo Telegram. Publish worker dispatch notification nếu bot/chat có cấu hình; khi cấu hình thiếu thì không có dispatcher và job có thể nằm `PENDING`. Vì vậy bốn notify PENDING từ 13/11 và 16/11 không được xem là hành vi bị chặn đúng bởi DISABLED. Trước khi retry, kiểm tra unit publish đang active, Telegram env được nạp và `attempts`/`last_error`; không xóa hoặc gửi lại hàng loạt khi chưa biết từng thông báo còn hợp lệ hay đã cũ.
