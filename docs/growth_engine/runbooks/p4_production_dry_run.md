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

Lệnh inventory dùng mapping catalog; ảnh trong `facade` và `linh_an` không được đưa vào allowlist tự động. Mỗi lần chạy sẽ in candidate path tương đối, group đề xuất và SHA-256. Resolver nhận dạng JPEG/PNG/HEIF theo bytes qua Pillow + `pillow-heif`, không dựa vào hậu tố; SHA luôn ghim bytes gốc và `prepare_variant` xuất JPEG. File corrupt/định dạng không hỗ trợ bị bỏ khỏi lựa chọn kèm `WARN` từng group/file; chỉ FAIL nếu nhóm bắt buộc không còn ảnh hợp lệ. Chỉ nhập `WRITE` khi candidate/SHA khác allowlist hiện tại; nếu file mode 600 và nội dung khớp, script báo `UNCHANGED` và không hỏi ghi lại. File đích là `~/venho/config/growth-engine-image-library.yaml`, ngoài Git.

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

## 7. Lịch sử giải quyết paid call UNKNOWN

Lượt QC đầu nhận HTTP 200 nhưng hậu xử lý lỗi; lệnh resolve-p4-qc-unknown đã settle bằng chứng token và requeue đúng một lần. Lượt QC retry tiếp theo nhận HTTP 200 và paid call thứ hai đã SETTLED 400 VND, nhưng assemble_revision lại FAILED với ERR_GC2_QC_POST_RESPONSE_FAILED (ValueError). Không chạy lại lệnh resolve hoặc worker cho job này. Delivery vẫn DRAFT, chưa có QC report/revision, không có outbox/execution; runtime giữ DISABLED + global_pause=1.

## 8. Reprocess QC evidence đã trả phí

Nguyên nhân đã xác nhận từ lần chạy thật: confidence và điểm QC còn ở dạng float sau khi parse/serialize report; `canonical_json` từ chối float trước khi ghi QC report. Đây cũng là nguyên nhân gốc phù hợp với `ValueError` của lượt đầu. Không nới lỏng canonical JSON. Bộ parse đổi confidence provider thành `confidence_bp`; report đổi các trường điểm thành integer có hậu tố `_bp` theo `round(x * 10000)` bằng `Decimal` + `ROUND_HALF_EVEN`. Mọi so sánh ngưỡng QC hiện diễn ra trước serialize trên thang điểm nội bộ hiện hữu; Growth Engine/BFF hiện không đọc hoặc hiển thị `result_json`. Nếu sau này giao diện hiển thị các điểm serialized, giá trị hiển thị bằng integer chia 10000.

Các float có nguồn provider trong đường QC là `dna_matches[*].confidence` và `forbidden[*].confidence`. Report sau scoring còn các float `overall_score`, `dna_match_score`, `category_scores[*]`, `section_scores[*].score` và `forbidden_violations[*].confidence`; adapter serialize thành `overall_score_bp`, `dna_match_score_bp`, `category_scores_bp`, `score_bp`, `confidence_bp`. Evidence provider gốc trong `paid_calls.provider_response_json` được giữ nguyên byte-for-byte.

### Ngưỡng QC ảnh P4

| Ngưỡng hoặc gate | Giá trị và đơn vị | Nơi áp dụng |
| --- | --- | --- |
| Verdict | ≥90 approve, ≥80 hoặc ≥70 revise, ≥60 regenerate, <60 reject. Điểm 0–100 | `validator_studio/scoring.py`, `verdict_for_score` |
| Trạng thái từng mục DNA | ≥90 OK, ≥60 WARNING, <60 FAIL. Điểm 0–100 | `status_for_score` |
| Báo vấn đề DNA | <90, mức HIGH khi điểm = 0, còn lại MEDIUM. Điểm 0–100 | `score_image_observation` |
| Trọng số confidence tối thiểu | 100 confidence bp = 0,01. Confidence hợp lệ 0–10.000 bp, không có ngưỡng duyệt 7.000 bp | `score_image_observation`, `max(confidence_bp, 100) / 10_000` |
| Kill switch vi phạm HIGH | Ép verdict reject, cap 40 điểm trên thang 0–100 | `score_image_observation`, `config/validation.yaml` |
| Gate GC2 | Vi phạm curated khớp policy hoặc kill switch → FAIL. Thiếu độ phủ → REVIEW | `LegacyQcAdapter._result_from_report`, `_effective_decision` |

Score serialized = điểm × 10.000. Ví dụ 89,99 điểm là 899.900 trong report và vẫn dưới ngưỡng 90 điểm. Ngưỡng chạy trên điểm gốc trước khi serialize. Bảng `validation.thresholds` trong YAML trùng giá trị hiện tại nhưng các hàm trên so với hằng số trong code.

Lệnh `reprocess-p4-qc-evidence --job ...` dùng filtered response evidence từ paid call đã SETTLED, dựng lại observation/report offline và tạo revision `IN_REVIEW`. Không gọi provider, không tạo paid call, không dispatch. Chạy wrapper từ shell SSH có controlling TTY. Wrapper chạy một unit `systemd-run --pipe` riêng với `--preflight-only` để in job, delivery, độ dài evidence và các key đọc được. Sau READY, wrapper xả input chờ và hỏi qua fd 3 mở từ `/dev/tty`. Khi nhận đúng `REPROCESS`, wrapper mới mở unit thực thi với `--operator-confirmed REPROCESS:<job_id>`. Engine kiểm đúng action và job, không đọc input. `RESOLVE` dùng cùng trình tự với xác nhận riêng. Lần chạy lại sau thành công trả `ALREADY_PROCESSED`. Ghi QC report, trạng thái variant, revision, delivery và audit trong cùng một transaction SQLite; mọi lỗi giữa chừng rollback toàn bộ.

Parser chấp nhận JSON sạch, JSON trong code fence, JSON có prose bao quanh, field tuỳ chọn bị lược, enum khác hoa/thường và số/boolean ở dạng chuỗi không mơ hồ. Làm tròn dùng Decimal, `ROUND_HALF_EVEN`; NaN/Inf bị chặn với `ERR_GC2_QC_NONFINITE_NUMBER` và đường dẫn field. Field bắt buộc thiếu, enum không nhận dạng, confidence ngoài 0–1 hoặc kiểu không an toàn sẽ chặn với tên field và lý do. Các giá trị response không được in. Nếu thiếu controlling TTY, wrapper trả `ERR_GC2_OPERATOR_TTY_REQUIRED` trước khi mở unit. `systemd-run --pipe` chỉ chuyển stdio nên phần prompt phải nằm ngoài unit. Bản cũ còn mở tty bằng Python text mode `r+`, yêu cầu seek và lỗi ngay cả trên PTY hợp lệ. Các script operator chạy trực tiếp dùng hai handle đọc/ghi riêng.

Rà canonical JSON: Draft package chuẩn hóa float trong facts/provenance thành chuỗi trước khi hash; trend candidate cũng chuyển float thành chuỗi; media metadata hiện chỉ gồm chuỗi và kích thước ảnh/Pillow là số nguyên, không lưu EXIF float. Các payload bên ngoài khác (research candidate, Make receipt) giữ canonical strict và fail-closed nếu phát sinh float chưa chuẩn hóa.

Nếu stored evidence thiếu observation hoặc không có bằng chứng HTTP 200/paid call tương ứng, lệnh dừng với ERR_GC2_P4_QC_EVIDENCE_INSUFFICIENT. Phương án B là một QC mới, tối đa 400 VND, chỉ sau khi operator duyệt riêng; lệnh này không tự chạy phương án B. Code sửa này không thêm migration; script bên dưới vẫn chạy migration idempotent để áp các migration còn thiếu trước deploy.

**Chạy trên ASUS:** thay `<REVIEWED_P4_SHA>` bằng commit SHA đã review trên nhánh `gc2/build-v1-2`. Dán block này trong SSH; `set -Eeuo pipefail` chỉ chạy trong file script, không trực tiếp trong interactive shell. Script tự xóa file handoff khi kết thúc. Không pipe output của lệnh reprocess/status; sau lệnh `bash` cuối không dán thêm lệnh cùng dòng.

~~~bash
cat > "$HOME/venho/reprocess-p4-qc-evidence.sh" <<'SCRIPT'
#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  printf 'P4 QC reprocess stopped: %s\n' "$*" >&2
  exit 1
}

P4_SHA='<REVIEWED_P4_SHA>'
BRANCH='gc2/build-v1-2'
REPO="$HOME/venho/gc2-src"
SCRIPT_PATH="$HOME/venho/reprocess-p4-qc-evidence.sh"
SOURCE_DIR=''
cleanup() {
  [[ -z "$SOURCE_DIR" ]] || rm -rf "$SOURCE_DIR"
  rm -f "$SCRIPT_PATH"
}
trap cleanup EXIT
REMOTE_URL="$(git -C "$REPO" remote get-url origin)"
SOURCE_DIR="$(mktemp -d "$HOME/venho/gc2-qc-source.XXXXXX")"

git clone --quiet --no-checkout "$REMOTE_URL" "$SOURCE_DIR"
git -C "$SOURCE_DIR" fetch --quiet origin "$BRANCH"
git -C "$SOURCE_DIR" cat-file -e "$P4_SHA^{commit}" || fail 'reviewed SHA is not present in fetched branch'
git -C "$SOURCE_DIR" merge-base --is-ancestor "$P4_SHA" "origin/$BRANCH" || fail 'reviewed SHA is not on the deploy branch'
git -C "$SOURCE_DIR" checkout --quiet --detach "$P4_SHA"
[[ -z "$(git -C "$SOURCE_DIR" status --porcelain)" ]] || fail 'source checkout is not clean'

cd "$SOURCE_DIR"
UV_PYTHON_PREFERENCE=only-managed "$HOME/.local/bin/uv" sync --frozen --python 3.11 --extra api --extra drive --extra gemini || fail 'release environment sync failed'
cd - >/dev/null

systemd-run --user --pipe --wait --collect --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" --property="WorkingDirectory=$SOURCE_DIR" --setenv=GE_ENV=production "$SOURCE_DIR/.venv/bin/venho-engine" migrate || fail 'production migrations did not complete'

bash "$SOURCE_DIR/ops/asus-server/growth-engine/deploy-release.sh" "$P4_SHA" || fail 'release deploy failed; deploy-release restores the previous release on failure'

CURRENT_RELEASE="$(readlink -f "$HOME/venho/growth-engine/current")"
EXPECTED_RELEASE="$HOME/venho/growth-engine/releases/$P4_SHA"
[[ "$CURRENT_RELEASE" == "$EXPECTED_RELEASE" ]] || fail 'current release path does not match the requested SHA'
systemctl --user is-active --quiet growth-engine-api.service || fail 'Growth Engine API is not active'
systemctl --user is-active --quiet growth-engine-worker@publish.service || fail 'publish worker is not active'
systemctl --user is-active --quiet growth-engine-worker@jobs.service || fail 'jobs worker is not active'
[[ "$(git -C "$CURRENT_RELEASE" rev-parse HEAD)" == "$P4_SHA" ]] || fail 'deployed checkout SHA mismatch'
printf 'RELEASE_SHA=%s\nAPI=active\nPUBLISH_WORKER=active\nJOBS_WORKER=active\n' "$P4_SHA"

RUNTIME="$HOME/venho/growth-engine/current/ops/asus-server/growth-engine/run-with-legacy-provider-env.sh"
REPROCESS_STATUS=0
if "$RUNTIME" reprocess-p4-qc-evidence --job e0d00517-3661-4390-a532-6f516e0ef176; then
  printf 'REPROCESS_COMMAND=completed\n'
else
  REPROCESS_STATUS=$?
  printf 'REPROCESS_COMMAND=stopped exit_code=%s\n' "$REPROCESS_STATUS"
fi

"$RUNTIME" p4-slot-status --date 2026-11-21
if (( REPROCESS_STATUS != 0 )); then
  fail 'reprocess was blocked; inspect the status above and do not start a new QC call'
fi
SCRIPT
chmod 700 "$HOME/venho/reprocess-p4-qc-evidence.sh"
bash "$HOME/venho/reprocess-p4-qc-evidence.sh"
~~~

**Kết quả mong đợi:** deploy reports requested SHA; API và hai worker active; preflight identifies the target delivery and stored observation keys without values; operator types REPROCESS; result is REPROCESSED, delivery_state=IN_REVIEW, and provider/paid-call counts are both zero. A repeat returns ALREADY_PROCESSED. p4-slot-status --date 2026-11-21 shows one QC report and revision (including a safe `revision.qc_report` summary with verdict and integer `*_bp` scores), delivery IN_REVIEW, both original/retry QC paid calls still SETTLED at 400 VND each, DISABLED + pause 1, and zero outbox/executions. Do not approve the delivery during this recovery.

**Dừng:** evidence missing/invalid, parser lists a field error, target/config/hash mismatch, controls changed, or deployment SHA/service check fails. ERR_GC2_P4_QC_EVIDENCE_INSUFFICIENT prints the missing evidence and says Option B needs separate approval; do not run provider QC from that failure path.

## 9. Duyệt P4 trên VENHO OS

Release 290957f đã reprocess thành công delivery `2509f430-4a4a-47dd-97a9-4b99e8d4ba88`
sang `IN_REVIEW`, revision `bd5eb9fd-a45b-4768-acf1-a8a40019e83a`.
Bản tóm tắt mới ghi `forbidden_checks` với `rule_id`, `violated` và `confidence_bp`.
Confidence 10.000 bp mô tả độ tin cậy của mục kiểm tra, còn cờ `violated` cho biết kết quả.
Điểm forbidden 100 là trường hợp không có cờ vi phạm. Mục DNA 60 điểm góp vào điểm tổng có trọng số.
Đọc `section_scores` cùng trường `section` và `key` để biết mục nào. Verdict của Validator Studio
là approve. GC2 giữ REVIEW khi detector còn thiếu độ phủ, nên cần Harry duyệt.

Job gốc giữ `FAILED` và lỗi cũ. `p4-slot-status` hiện thêm `recovery_status=RECOVERED`
khi audit recovery trỏ đúng delivery và revision hiện tại. `cutover-readiness` kiểm approval
khớp revision/hash, mapping, QC và outbox/execution. Job lịch sử không nằm trong gate.
Lệnh reprocess trả `ALREADY_PROCESSED` cho audit đã có, với chi phí phát sinh bằng 0.

**Điều kiện cho khối 2.** VENHO OS đã deploy commit `5c684b3eb8419109d9c00900d52a8148c2704bd5` hoặc build chứa route của commit đó. Build có `GET /api/health/growth-backend`.
Endpoint trả 204, `Cache-Control: private, no-store` và `X-Venho-Growth-Backend`.
Chạy build một lần khi đưa route vào release. Sau đó đổi `GROWTH_BACKEND` chỉ cần restart,
do Next đọc biến phía server lúc xử lý request. Dùng phiên SSH có TTY, chạy sau 09:30 ICT
và hoàn tất cùng phiên. Hai chế độ đều chặn thao tác chủ động từ 08:30 đến 09:30 ICT.
Script cảnh báo số mục chờ duyệt hôm nay trong registry legacy cục bộ. Nếu registry chưa đọc được,
kiểm tra queue trên dashboard legacy trước. Trong v2, màn Publishing ẩn phần duyệt legacy.
Legacy scheduler và webhook/Make 5868920 vẫn theo lịch riêng. Restart chỉ làm VENHO OS
gián đoạn ngắn, nên tránh giờ đăng.

**Khối 1 — deploy GC2, kiểm recovery và mở preview.** Dùng block deploy ở §8 với SHA
đã duyệt, rồi thay phần từ dòng `RUNTIME=` đến trước `SCRIPT` bằng đoạn sau.
Block dùng wrapper trên TTY, chạy lại an toàn khi job đã recover.

```bash
RUNTIME="$CURRENT_RELEASE/ops/asus-server/growth-engine/run-with-legacy-provider-env.sh"
"$RUNTIME" reprocess-p4-qc-evidence --job e0d00517-3661-4390-a532-6f516e0ef176
"$RUNTIME" p4-slot-status --date 2026-11-21
"$RUNTIME" p4-review-preview --delivery 2509f430-4a4a-47dd-97a9-4b99e8d4ba88
```

**Trước khối 2.** Chạy Khối 0 deploy VENHO OS main có health route. Script
`ops/asus-server/venho-os/deploy-main.sh` dùng `npm ci --include=dev` và
`npm run build`, restart user unit `venho-os.service`, kiểm health 204 với
backend `legacy` và login 200. Nếu checkout đã ở đúng `origin/main`, script
chỉ kiểm health và in `RESULT=already_current`. Script giữ nguyên `.env.local`,
tạm dừng timer `venho-os-deploy.timer` nếu đang active và in trạng thái trước/sau.
Sau khi thành công, timer trở về trạng thái ban đầu. Sau rollback,
timer auto-deploy dừng để tránh tự áp lại bản lỗi. Nếu release cũ chưa có health
route, rollback xác minh SHA cũ, service active, login 200 và health 404 như baseline.
Deploy bản GC2 có cảnh báo quá hạn trước khi mở v2. Readiness sẽ FAIL nếu slot
duyệt đã quá deadline; khi đó cần chọn slot mới và duyệt lại.

**Khối 2 — mở v2, duyệt, rồi về legacy.** Sau khi thấy `VENHO_OS=healthy GROWTH_BACKEND=v2`,
mở Publishing trên VENHO OS bằng tài khoản có `studio:write`. Kiểm Page `1124616474074140`,
21/11/2026 09:00 ICT, caption và preview JPEG. Sau khi duyệt và tải lại thấy `APPROVED`,
gõ `APPROVED` trong terminal trong vòng 15 phút. Nếu có lỗi, gõ nội dung khác để script quay lại legacy. Hết thời gian cũng quay lại legacy.
Gate PASS xác nhận đúng revision, đúng hash, runtime vẫn DISABLED + pause và không có
outbox/execution. Gate FAIL vẫn quay lại legacy. Sau đó tải lại màn Publishing để
xác nhận dashboard legacy hiện lại.

```bash
cat > "$HOME/venho/p4-approve-on-os.sh" <<'SCRIPT'
#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$HOME/venho/growth-engine/current/ops/asus-server"
SWITCH="$ROOT/venho-os/growth-backend-switch.sh"
ENGINE="$ROOT/growth-engine/run-with-legacy-provider-env.sh"
needs_legacy=0
cleanup() {
  status=$?
  trap - EXIT
  rm -f "$HOME/venho/p4-approve-on-os.sh"
  if (( needs_legacy )) && ! bash "$SWITCH" legacy; then
    printf '%s\n' 'RESTORE_LEGACY=FAILED' >&2
    status=1
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP
{ exec 3<>/dev/tty; } 2>/dev/null || { echo 'ERR_GC2_OPERATOR_TTY_REQUIRED' >&2; exit 2; }

bash "$SWITCH" v2
needs_legacy=1
printf 'Duyệt trên VENHO OS, tải lại rồi gõ APPROVED để kiểm tra: ' >&3
IFS= read -r -t 900 answer <&3
[[ "$answer" == APPROVED ]] || exit 2

ready=0
"$ENGINE" cutover-readiness --date 2026-11-21 --time 09:00 || ready=$?
bash "$SWITCH" legacy
needs_legacy=0
"$ENGINE" p4-slot-status --date 2026-11-21
exit "$ready"
SCRIPT
chmod 700 "$HOME/venho/p4-approve-on-os.sh"
bash "$HOME/venho/p4-approve-on-os.sh"
```
