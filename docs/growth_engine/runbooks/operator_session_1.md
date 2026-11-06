# Phiên vận hành Growth Engine — phiên 1

**Trạng thái:** phiên đã bắt đầu; Page Facebook TEST và healthcheck đã được tạo. URL, tài khoản Instagram TEST, route Make, credentials và các gate còn lại phải được xác minh khi thực hiện. Không thay giá trị `REQUIRED_FROM_P0` bằng phỏng đoán.

**Meta read app:** VENHO Growth Read — App ID `1679968647246378` (Development). Không ghi Meta token vào runbook.

Ngày 2026-11-05, chỉ thêm `pages_read_user_content`; Meta hiển thị **Ready for testing**. Trước khi tạo token mới, Harry thu hồi token cũ khỏi Facebook Business Integrations.

Trước mọi lệnh `systemctl --user enable`, chạy `systemd-analyze --user verify` cho toàn bộ unit file được cài; lệnh kiểm tất cả unit của repo nằm ở mục 8.

Thực hiện đúng thứ tự. Nếu kết quả không đạt mong đợi ở một bước, dừng tại đó; không bật publisher hoặc tiếp tục Make TEST. Không ghi token, webhook URL, Access secret, signed URL hay nội dung file env vào terminal log/evidence.

## 1. Cài age và tạo recipient backup

Trên ASUS server (Ubuntu/Debian):

```bash
if ! command -v age >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y age
fi
age --version
```

Nếu `age` được cài riêng cho user tại `~/.local/bin`, thêm đường dẫn đó vào `PATH` của environment file và xác minh lệnh chạy được trong systemd user. Trên máy operator giữ private identity:

```bash
mkdir -p -m 700 "$HOME/.config/age"
test -e "$HOME/.config/age/venho-backup.key" || age-keygen -o "$HOME/.config/age/venho-backup.key"
chmod 600 "$HOME/.config/age/venho-backup.key"
age-keygen -y "$HOME/.config/age/venho-backup.key" > "$HOME/.config/age/growth-engine-backup.recipient"
cat "$HOME/.config/age/growth-engine-backup.recipient"
```

**Mong đợi:** `age --version` thành công; keygen in một recipient `age1…`. Chỉ recipient công khai được chép vào env server; identity riêng giữ ở máy operator.

**Dừng:** nếu `age` chưa cài được hoặc keygen/recipient không hợp lệ, chưa tạo backup và chưa chạy restore rehearsal.

## 2. Tạo production và TEST environment files

Trên server, tạo file production với quyền `600`; mở editor cục bộ để điền giá trị từ secret store và hồ sơ đã duyệt. Không đưa giá trị secret vào command hoặc Git:

```bash
install -d -m 700 "$HOME/venho/secrets"
umask 077
install -m 600 /dev/null "$HOME/venho/secrets/growth-engine.env"
${EDITOR:-vi} "$HOME/venho/secrets/growth-engine.env"
chmod 600 "$HOME/venho/secrets/growth-engine.env"
test "$(stat -c '%a' "$HOME/venho/secrets/growth-engine.env")" = 600
grep -qx 'GE_ENV=production' "$HOME/venho/secrets/growth-engine.env"
```

Production `Settings` yêu cầu `GE_DB_PATH`, `GE_MEDIA_ROOT`, `GE_PUBLIC_BASE_URL`, `GE_DASHBOARD_BASE_URL`, `GE_CAPABILITY_KEYS`, `GE_SERVICE_TOKENS`, ít nhất một `GE_MAKE_WEBHOOK_URL_*`, ít nhất một `GE_META_READ_TOKEN_*`, `GE_TELEGRAM_BOT_TOKEN` và `GE_TELEGRAM_CHAT_ID`. Mọi biến Make/Meta/Telegram đã khai báo phải có giá trị không rỗng và không chứa `REQUIRED_FROM_P0`. `GE_AGE_RECIPIENT` cần cho backup, nhưng không được `Settings`/`doctor` kiểm tra; `GE_HEARTBEAT_URL` cũng không phải điều kiện settings hiện tại.

Ánh xạ token Meta: `GE_META_READ_TOKEN_PAGE_A` ↔ `GE_META_READ_TOKEN_FB_HANOI` (`fb_hanoi`); `GE_META_READ_TOKEN_PAGE_B` ↔ `GE_META_READ_TOKEN_FB_VENHO` (`fb_venho`); `GE_META_READ_TOKEN_IG_VENHO` dùng cùng tên cho `ig_venho`. Điền hai alias mỗi Page với cùng Page access token để vừa thỏa tham chiếu manifest vừa chạy probe. Không ghi giá trị token vào runbook. Bảng chi tiết nằm trong [environment_manifest.md](../environment_manifest.md).

Tạo riêng file API TEST; DB và media phải nằm trong thư mục TEST riêng, không trỏ vào production:

```bash
umask 077
install -m 600 /dev/null "$HOME/venho/secrets/growth-engine-test.env"
${EDITOR:-vi} "$HOME/venho/secrets/growth-engine-test.env"
chmod 600 "$HOME/venho/secrets/growth-engine-test.env"
test "$(stat -c '%a' "$HOME/venho/secrets/growth-engine-test.env")" = 600
grep -qx 'GE_ENV=test' "$HOME/venho/secrets/growth-engine-test.env"
```

Với `GE_ENV=test`, `Settings` không tự bắt buộc biến production-only như Telegram, dashboard URL hay Meta token; `doctor` cần các giá trị không rỗng cho `GE_DB_PATH`, `GE_MEDIA_ROOT`, `GE_PUBLIC_BASE_URL`, `GE_CAPABILITY_KEYS`, `GE_SERVICE_TOKENS`. Các `GE_MAKE_WEBHOOK_URL_*`, `GE_META_READ_TOKEN_*` hoặc `GE_TELEGRAM_*` nào được khai báo cũng phải không rỗng/placeholder. Riêng `send_test_command.py --create-command` còn cần `GE_TEST_CHANNEL_KEY`, `GE_TEST_CHANNEL_ID`, ID đích đúng (`GE_TEST_REMOTE_PAGE_ID` hoặc `GE_TEST_REMOTE_IG_ID`), URL webhook TEST tương ứng; `channels.yaml` cần Graph API version đã xác minh. Mã API/publish TEST hiện không cần Meta read token. Không sao chép production bearer, webhook hay Page ID vào TEST.

Các tên Meta TEST `GE_META_READ_TOKEN_PAGE_TEST`/`GE_META_READ_TOKEN_IG_TEST` là tham chiếu manifest; chỉ điền nếu có tác vụ đọc Meta TEST đã được xác định. `Settings` không yêu cầu chúng cho API TEST.

Meta token lifecycle: biến Page trên server là Page access token lấy từ long-lived user token; không hết hạn theo thời gian nhưng có thể bị thu hồi. Instagram dùng long-lived user token khoảng 60 ngày; đặt nhắc gia hạn trước hạn. Không ghi giá trị token vào tài liệu/log.

**Mong đợi:** cả hai file tồn tại với mode `600`; kiểm tra chỉ in quyền và `GE_ENV`, không in giá trị còn lại.

**Dừng:** thiếu secret/route TEST, giá trị placeholder còn trong production file, DB path trùng nhau hoặc mode khác `600` thì không deploy.

## 3. Push branch đã review, deploy ở DISABLED và mở API TEST riêng

Trên checkout GC2 sạch, sau khi review các commit:

```bash
git status --short
git rev-parse HEAD
git push origin gc2/build-v1-2
```

Ghi lại SHA được review, rồi trên cùng checkout chạy:

```bash
bash ops/asus-server/growth-engine/deploy-release.sh <reviewed-git-sha>
```

Script yêu cầu production DB đã ở schema mục tiêu và runtime control `production` đã là `DISABLED`; script không migrate DB. Sau khi deploy, mở API TEST dùng đúng release hiện hành nhưng env file/DB TEST riêng:

```bash
systemd-run --user --unit=growth-engine-api-test --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine-test.env" \
  --property="WorkingDirectory=$HOME/venho/growth-engine/current" \
  --setenv=GE_ENV=test \
  "$HOME/venho/growth-engine/current/.venv/bin/venho-engine" \
  api --host 127.0.0.1 --port 8022
```

Kiểm tra TEST API:

```bash
curl --fail --silent --show-error http://127.0.0.1:8022/health/live
curl --fail --silent --show-error http://127.0.0.1:8022/health/ready
```

**Mong đợi:** deploy báo đúng release SHA đang hoạt động, `doctor` PASS, production mode vẫn `DISABLED`; TEST API trả `live` và `ready` trên loopback cổng `8022` với DB TEST.

**Dừng:** source checkout bẩn, SHA chưa có trên origin, migration/doctor không PASS, production chưa `DISABLED`, hoặc TEST API không ready. Deploy script tự rollback khi health/doctor sau switch lỗi. Dừng API TEST bằng:

```bash
systemctl --user stop growth-engine-api-test.service
```

## 4. Cấu hình Cloudflare hostname và Access cho TEST

Harry cấu hình Tunnel/hostname TEST theo ADR-05/ADR-06: `/internal/*` dùng Access Service Token; `/media/publish/*` có Access Bypass nhưng vẫn yêu cầu signed capability. Không thay đổi hostname production ở bước này.

Từ máy ngoài, với `GE_TEST_HOST` là hostname TEST đã được xác minh, thử endpoint authorize bằng body rỗng và không có Access headers:

```bash
curl --silent --show-error --include --max-time 10 \
  "https://${GE_TEST_HOST}/internal/growth/v2/executions/authorize" \
  -H 'Content-Type: application/json' --data '{}'
```

Sau đó dùng hai Access TEST secrets đã nạp an toàn vào shell/credential manager để xác nhận request qua được Access nhưng vẫn bị ứng dụng từ chối vì thiếu bearer:

```bash
curl --config <(printf 'header = "CF-Access-Client-Id: %s"\nheader = "CF-Access-Client-Secret: %s"\n' "$CF_ACCESS_TEST_CLIENT_ID" "$CF_ACCESS_TEST_CLIENT_SECRET") \
  --silent --show-error --include --max-time 10 \
  "https://${GE_TEST_HOST}/internal/growth/v2/executions/authorize" \
  -H 'Content-Type: application/json' --data '{}'
```

**Mong đợi:** không Access headers bị edge chặn trước application; Access hợp lệ nhưng thiếu bearer bị application trả 401 JSON. Ghi chính xác status/content type và evidence đã khử bí mật vào ADR-05/ADR-06.

**Dừng:** login redirect không rõ nguồn, request không bị edge bảo vệ, hoặc không phân biệt được edge denial với application 401. Chưa đạt thì không nối Make TEST.

## 5. Tạo scenario Make TEST và chạy MK-1…MK-11

Trong Make, duplicate `VenHo Growth Agent-FB/IG` thành TEST; schedule off; gắn Page Facebook TEST đã đối chiếu ID cho hai nhánh Facebook và tài khoản Instagram TEST đã đối chiếu ID cho nhánh Instagram. Không dùng ba production ID trong `channels.yaml` làm TEST destination, và không dùng label thay ID. Do SQLite yêu cầu remote account duy nhất trong mỗi môi trường, mỗi nhánh dùng TEST DB riêng và API TEST phải trỏ đúng DB của lệnh trước khi thử. Tạo một webhook TEST, một Router với đúng ba nhánh `fb_hanoi`, `fb_venho`, `ig_venho`, mỗi nhánh lọc theo `channel_key` cố định, fallback off. Làm theo [make_blueprint_v2.md](make_blueprint_v2.md), điền đủ MK-1…MK-11 trong [make_capabilities.md](../make_capabilities.md) bằng History/module output thật đã khử bí mật. Facebook dùng ảnh binary từ HTTP trong từng nhánh; Instagram dùng `media_url` ở trường image URL.

Webhook TEST chưa có data structure. Payload mẫu [make_test_sample_payload.json](make_test_sample_payload.json) theo đúng JSON Schema `growth.command.v2`; envelope này **không có** `content`, `image_url` hoặc `publication_id`. `command_token` và `payload_hash` chỉ là giá trị tổng hợp để Make nhận tên/kiểu trường, không phải chữ ký hợp lệ; authorize sẽ từ chối nó. Không gửi mẫu khi đường đi tới module HTTP/đăng bài còn nối. Dùng đúng năm bước sau:

1. Xác nhận chỉ scenario TEST đang mở, schedule vẫn OFF; tạm ngắt toàn bộ module sau Custom webhook để không gọi HTTP hay đăng bài.
2. Trên Custom webhook của TEST scenario, bấm **Redetermine data structure**.
3. Trong terminal cục bộ chạy Python dưới đây; nhập webhook URL tại prompt ẩn, không dán URL vào lệnh hay chat. Chỉ HTTP status được in:
   ```bash
   python3 - <<'PY'
   import getpass
   from pathlib import Path
   from urllib.request import Request, urlopen
   url = getpass.getpass("TEST webhook URL (hidden): ")
   body = Path("docs/growth_engine/runbooks/make_test_sample_payload.json").read_bytes()
   request = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
   with urlopen(request, timeout=20) as response:
       print(f"HTTP {response.status}")
   PY
   ```
4. Xác nhận Make nhận các trường envelope; không tính lần nhận mẫu là MK pass hoặc bằng chứng đăng.
5. Chỉ nối lại module sau khi đã áp filter `channel_key`, route, authorize và response theo blueprint; chưa bật lịch TEST.

Nếu webhook không thể nhận cấu trúc trước khi chạy module downstream, không gửi mẫu qua luồng đang nối; giữ scenario dừng và ghi gate chờ xử lý. Payload giả không thể dùng để kiểm tra authorize hay đăng bài.

Sau khi mọi gate được duyệt, thứ tự mở target production là `fb_hanoi` → `fb_venho` → `ig_venho`; chỉ mở target kế tiếp sau khi target trước có receipt/verify xác định. Trong phiên TEST này không bật production và không đăng thử công khai.

Chọn `GE_TEST_CHANNEL_KEY` (`fb_hanoi`, `fb_venho`, hoặc `ig_venho`), `GE_TEST_CHANNEL_ID` riêng cho nhánh, TEST DB và đúng API TEST trước khi tạo command. Facebook dùng `GE_TEST_REMOTE_PAGE_ID`, Instagram dùng `GE_TEST_REMOTE_IG_ID`. Tạo command TEST và private envelope (lệnh này không gửi webhook):

```bash
mkdir -p -m 700 "$HOME/.cache/growth-engine"
umask 077
python3 scripts/growth_engine/send_test_command.py \
  --create-command \
  --envelope-file "$HOME/.cache/growth-engine/test-envelope.json"
```

Chỉ sau khi destination ID, TEST scenario, DB, filter và credentials đã được kiểm tra, và Harry đã đồng ý đăng thử công khai, có thể gửi lệnh tới destination TEST:

```bash
python3 scripts/growth_engine/send_test_command.py \
  --envelope-file "$HOME/.cache/growth-engine/test-envelope.json" \
  --send --confirm-test-remote-id "$GE_TEST_REMOTE_PAGE_ID"
```

Ví dụ trên dành cho Facebook. Với Instagram, dùng `GE_TEST_REMOTE_IG_ID` thay cho `GE_TEST_REMOTE_PAGE_ID`.

**Mong đợi:** mỗi lệnh chỉ chạy đúng một route TEST; ghi module output/receipt/post ID hoặc media ID thật và kết quả đủ MK-1…MK-11. Webhook ACK không phải bằng chứng bài đăng.

**Dừng:** Page/scenario ID mơ hồ, filter sai, một lệnh chạm production, module retry/resume đang bật, hoặc kết quả Facebook/Instagram không rõ. Không chạy lại module đăng; xử lý theo History/receipt.

## 6. Xác minh healthchecks và Telegram

Sau khi production deploy vẫn `DISABLED`, kiểm tra health và units:

```bash
systemctl --user is-active growth-engine-api.service
systemctl --user is-active growth-engine-worker@publish.service
systemctl --user is-active growth-engine-worker@jobs.service
curl --fail --silent --show-error http://127.0.0.1:8021/health/ready
journalctl --user -u growth-engine-worker@publish.service -u growth-engine-worker@jobs.service --since '-10 min' --no-pager
```

`GE_HEARTBEAT_URL`, `GE_TELEGRAM_BOT_TOKEN` và `GE_TELEGRAM_CHAT_ID` được nạp qua `growth-engine.env`; không in file env. Worker chỉ ping healthchecks sau khi các task health-gated pass. Telegram được xử lý qua durable `notify` job; không tạo tin nhắn thử và không gửi vào chat production chỉ để kiểm tra.

**Mong đợi:** ba units active, API ready; heartbeat xuất hiện sau một chu kỳ healthy 60 giây; không có lỗi dispatch notification trong journal. Telegram credentials cần khớp chat TEST được Harry chọn trước khi có notification TEST đã được duyệt.

**Dừng:** API/DB not-ready, worker lặp lỗi, heartbeat không tới hoặc Telegram credential/chat chưa được kiểm tra. Dừng workers bằng `systemctl --user stop growth-engine-worker@publish.service growth-engine-worker@jobs.service`; production vẫn `DISABLED`.

## 7. Restore rehearsal vào thư mục mới

Tạo backup mới không ghi đè; env file được source trong shell nhưng không in ra:

```bash
set -a
. "$HOME/venho/secrets/growth-engine.env"
set +a
mkdir -p -m 700 "$HOME/venho/state/growth-engine/backup-staging"
venho-engine backup now --destination "$HOME/venho/state/growth-engine/backup-staging/growth-engine-restore-rehearsal.age"
```

Chép **backup đã mã hóa** về Mac và chạy từ checkout GC2 trên Mac. Identity riêng giữ trên Mac; chọn target chưa tồn tại:

```bash
mkdir -p -m 700 "$HOME/venho/growth-engine-restore"
test ! -e "$HOME/venho/growth-engine-restore/growth-engine-restore-rehearsal.age"
scp asus-server:venho/state/growth-engine/backup-staging/growth-engine-restore-rehearsal.age \
  "$HOME/venho/growth-engine-restore/growth-engine-restore-rehearsal.age"
export PATH="$PWD/.venv/bin:$PATH"
export GE_ENV=test
ops/asus-server/growth-engine/restore-rehearsal.sh \
  "$HOME/venho/growth-engine-restore/growth-engine-restore-rehearsal.age" \
  "$HOME/.config/age/venho-backup.key" \
  "$HOME/venho/growth-engine-restore/rehearsal-<unique-suffix>"
```

**Mong đợi:** `restore rehearsal passed: integrity, foreign keys, DISABLED and global pause`; target mới có DB/media đã kiểm tra, epoch cũ bị vô hiệu.

**Dừng:** backup thiếu, identity không giải mã, target đã tồn tại, integrity/FK/media hash lỗi, hoặc control không DISABLED + global pause. Không chạy worker trên target restore rehearsal.

## 8. Cài timer T0-05/T0-06

Chỉ cài sau khi ba token đọc Meta đã nạp an toàn vào `growth-engine.env`, config candidate đã được probe và kiểm tra, và lệnh báo cáo chạy thành công ở chế độ operator. Hai lệnh legacy đọc `publication_registry.json`/config và ghi vào `~/venho/state/growth-reports/`; chúng không dùng DB Growth Engine v2.

Để backfill bài Page Ven Hồ Hotel cũ chưa có trong registry, tạo snapshot đối soát 90 ngày và chạy Insights ngay sau đó, trước khi snapshot 7 ngày kế tiếp ghi cùng ngày lịch:

```bash
venho-analytics reconcile-channels --days 90
venho-analytics insights-backfill --days 90
venho-analytics insights-report
```

**Mong đợi:** report reconcile có các dòng `fb_venho` riêng; `insights.db` nằm trong `~/venho/state/growth-reports/` và có metric đã xác minh.

**Dừng:** nếu không đủ quyền đọc hoặc report có `UNAVAILABLE`, không đánh dấu bài là thiếu và không enable timer trước khi xử lý token/quyền.

```bash
find ops/asus-server -type f \( -name '*.service' -o -name '*.timer' \) -print0 \
  | xargs -0 -n1 systemd-analyze --user verify
systemctl --user daemon-reload
install -d -m 700 "$HOME/venho/state/growth-reports"
systemctl --user enable --now venho-growth-reconcile.timer venho-growth-insights.timer
systemctl --user list-timers --all 'venho-growth-*'
```

**Mong đợi:** cả hai timer hiện trạng thái enabled/active; lệnh chạy bằng legacy runtime `~/venho/growth-runtime/venho-ai-studio/.venv/bin/venho-analytics`. Reconcile quét 7 ngày; Insights chạy backfill rồi ghi báo cáo. Output chỉ nằm trong `~/venho/state/growth-reports/`.

**Dừng:** nếu thiếu token/quyền Meta, lệnh báo lỗi, output không nằm ngoài git, hoặc timer gọi runtime/DB v2 thì dừng và chạy `systemctl --user disable --now venho-growth-reconcile.timer venho-growth-insights.timer`; lưu lỗi đã khử bí mật. Không sửa lịch legacy publish timers. Production v2 giữ `DISABLED`.
