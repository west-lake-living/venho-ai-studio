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

### Đẩy Meta read token từ Mac

Sau khi token người dùng dài hạn đã được cấp đúng quyền và SSH alias `asus-server` hoạt động, chạy script từ checkout GC2 trên Mac. Script đọc token ẩn, chọn hai Page bằng Page ID, gửi token qua stdin của SSH và chỉ in tên biến cùng trạng thái:

```bash
python3 ops/asus-server/growth-engine/push-meta-tokens.py
```

Có thể chỉ định SSH host alias khác bằng `--host <alias>`. Script gọi Graph API v27.0 `/me/accounts?fields=id,name,access_token`; nếu thiếu một trong hai Page ID đã cấu hình thì dừng trước SSH. Sau khi hoàn tất, trên server chạy lệnh kiểm tra ở cuối mục này; kết quả chỉ được là `DA_CO_GIA_TRI` hoặc `PLACEHOLDER` theo tên biến, không hiển thị giá trị. Không chạy script trong môi trường có shell xtrace hoặc terminal recording.

Tạo riêng file API TEST và bộ bearer TEST từ checkout GC2 đã review trên server. Script không đọc/sửa env production; khi chạy lần đầu nó tạo DB/media path tách biệt, khoá capability mới và ba bearer có principal policy hợp lệ:

```bash
bash ops/asus-server/growth-engine/setup-test-env.sh
```

Script tạo `~/venho/secrets/growth-engine-test.env` và file bàn giao bearer `~/venho/secrets/growth-engine-test.make-bearers.tmp`, đều mode `600`; thư mục secret/state mode `700`. Env giữ `GE_SERVICE_TOKENS` dạng SHA-256, không có bearer thô. Chép ba bearer vào HTTP modules Make TEST, nhưng giữ file handoff trên server ở mode `600` đến khi toàn bộ TEST phase kết thúc để có thể nạp lại sau lần import tiếp theo. Không `cat` file, dán bearer vào terminal lệnh, Git hay chat. Chạy lại script không xoay key/token và không tạo lại file bàn giao đã xóa.

Chỉ xóa bản sao trên Mac sau mỗi lần import. Không xóa handoff trên server cho tới bước kết thúc TEST phase bên dưới.

### Tạo lại TEST database khi môi trường đã có channel

Nếu runner báo `TEST channel already exists in this database`, không chạy lại lệnh tạo command trên DB đó. Trước khi tạo lại TEST env hoặc reset channel, dừng API TEST, sao lưu DB SQLite cùng WAL/SHM và media, rồi để script tạo DB/media mới. Ví dụ:

```bash
systemctl --user stop growth-engine-api-test-src
state="$HOME/venho/state/growth-engine-test"
archive="$state/archive-$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 700 "$archive"
for file in "$state"/growth_engine.db*; do [[ ! -e "$file" ]] || mv -- "$file" "$archive/"; done
[[ ! -d "$state/media" ]] || mv -- "$state/media" "$archive/media"
install -d -m 700 "$state/media"
```

DB mới sẽ được migrate khi API TEST khởi động. Nếu chỉ cần DB/channel mới, giữ nguyên env và bearer hiện tại. Nếu cần tạo lại cả env/bearer, dùng quy trình độc lập sau; script sẽ phát bearer mới nên phải cập nhật Make bằng handoff mới:

```bash
systemctl --user stop growth-engine-api-test-src
state="$HOME/venho/state/growth-engine-test"
archive="$state/archive-env-$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 700 "$archive" "$archive/secrets"
for file in "$state"/growth_engine.db*; do [[ ! -e "$file" ]] || mv -- "$file" "$archive/"; done
[[ ! -d "$state/media" ]] || mv -- "$state/media" "$archive/media"
install -d -m 700 "$state/media"
for file in "$HOME/venho/secrets/growth-engine-test.env" \
            "$HOME/venho/secrets/growth-engine-test.make-bearers.tmp"; do
  [[ ! -e "$file" ]] || mv -- "$file" "$archive/secrets/"
done
for file in "$archive/secrets"/*; do [[ ! -e "$file" ]] || chmod 600 "$file"; done
bash ops/asus-server/growth-engine/setup-test-env.sh
```

Giữ các handoff đã archive ở mode `600` tới cuối TEST phase. Không xóa DB/media backup trước khi xác nhận TEST không cần khôi phục.

Kết thúc TEST phase:

```bash
systemctl --user stop growth-engine-api-test-src
systemctl --user is-active growth-engine-api-test-src || true
rm -f "$HOME/venho/secrets/growth-engine-test.make-bearers.tmp"
find "$HOME/venho/state/growth-engine-test" -path '*/secrets/growth-engine-test.make-bearers.tmp' -type f -delete
test ! -e "$HOME/venho/secrets/growth-engine-test.make-bearers.tmp" && echo ABSENT
```

`find` chỉ xóa file handoff bearer plaintext đã archive trong TEST state. Giữ `growth-engine-test.env` nếu còn cần các ca TEST đang mở; file này không chứa bearer thô. Sau khi đã lưu JSON kết quả đã khử bí mật ra khỏi TEST state và quyết định không chạy thêm TEST, xóa env/DB/media từng ca:

```bash
find "$HOME/venho/secrets/growth-engine-test-cases" -maxdepth 1 -type f -name '*.env' -delete
find "$HOME/venho/state/growth-engine-test/cases" -mindepth 1 -maxdepth 1 -type d -exec rm -rf -- {} +
```

Không xóa archive DB/media cũ trước khi xác nhận không cần khôi phục.

Giữ các bài đăng TEST trên Facebook/Instagram trong thời gian đối chiếu History và lưu bằng chứng; không tự xóa. Sau khi review xong, Harry có thể xóa các bài thử trực tiếp trên hai tài khoản TEST nếu không cần làm hồ sơ.

Với `GE_ENV=test`, `Settings` không tự bắt buộc biến production-only như Telegram, dashboard URL hay Meta token; `doctor` cần các giá trị không rỗng cho `GE_DB_PATH`, `GE_MEDIA_ROOT`, `GE_PUBLIC_BASE_URL`, `GE_CAPABILITY_KEYS`, `GE_SERVICE_TOKENS`. Các `GE_MAKE_WEBHOOK_URL_*`, `GE_META_READ_TOKEN_*` hoặc `GE_TELEGRAM_*` nào được khai báo cũng phải không rỗng/placeholder. Riêng `send_test_command.py --create-command` còn cần `GE_TEST_CHANNEL_KEY`, `GE_TEST_CHANNEL_ID`, ID đích đúng (`GE_TEST_REMOTE_PAGE_ID` hoặc `GE_TEST_REMOTE_IG_ID`), URL webhook TEST tương ứng; `channels.yaml` cần Graph API version đã xác minh. Mã API/publish TEST hiện không cần Meta read token. Không sao chép production bearer, webhook hay Page ID vào TEST.

Các tên Meta TEST `GE_META_READ_TOKEN_PAGE_TEST`/`GE_META_READ_TOKEN_IG_TEST` là tham chiếu manifest; chỉ điền nếu có tác vụ đọc Meta TEST đã được xác định. `Settings` không yêu cầu chúng cho API TEST.

`GE_SERVICE_TOKENS` lưu các entry `principal:sha256`, không lưu bearer thô. `auth.py` băm `SHA256(bearer.strip().encode("utf-8"))`, hex thường, rồi so khớp constant-time. Script dùng đúng principal `make-fb-hanoi` → `fb_hanoi`, `make-fb-venho` → `fb_venho`, `make-ig` → `ig_venho`; không tự đặt principal mới.

Meta token lifecycle: biến Page trên server là Page access token lấy từ long-lived user token; không hết hạn theo thời gian nhưng có thể bị thu hồi. Instagram dùng long-lived user token khoảng 60 ngày; ngày đang dự kiến hết hạn là 2027-01-10. Production doctor WARN trong 14 ngày cuối hoặc khi expiry metadata thiếu/sai; publish worker kiểm tra mỗi 6 giờ và enqueue Telegram notice một lần cho mỗi credential/date. Điền `GE_META_TOKEN_EXPIRY_IG_VENHO` và ngày chính xác từ Debugger vào `GE_META_DATA_ACCESS_EXPIRY_IG_VENHO`. Telegram production phải dùng bot `@venho_growth_alerts_bot`, không dùng `@Venhohotel_bot`. Không ghi token vào tài liệu/log.

**Mong đợi:** TEST env và file bàn giao bearer có mode `600`; giữ file handoff trên server tới khi kết thúc TEST phase. Kiểm tra chỉ in quyền và `GE_ENV`, không in giá trị còn lại.

**Dừng:** thiếu secret/route TEST, giá trị placeholder còn trong production file, DB path trùng nhau hoặc mode khác `600` thì không deploy.

## 3. Push branch đã review, deploy ở DISABLED và mở API TEST riêng

### Đường API TEST độc lập trước production deploy — đã chạy 10/11/2026

TEST đã chạy trước production deploy từ checkout `~/venho/gc2-src`, SHA `8ca8661`, bằng transient user unit `growth-engine-api-test-src`. Không dùng `growth-engine-api-test.service` ở giai đoạn này vì unit đó trỏ `~/venho/growth-engine/current`, đường dẫn chỉ có sau production deploy. Cổng TEST là `127.0.0.1:8023`; DB TEST migrate tới schema `9`.

Harry xác nhận đã dùng `systemd-run --user` để tạo transient unit, chạy `venho-engine migrate` trên DB TEST và khởi động API tại cổng `8023`. Shell history với toàn bộ cờ không được cung cấp; block dưới đây là lệnh tái lập tương đương, giữ nguyên source checkout, env TEST, unit name và bind address:

```bash
cd "$HOME/venho/gc2-src"
git rev-parse --short HEAD  # mong đợi 8ca8661
systemd-run --user --pipe --wait --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine-test.env" \
  --property="WorkingDirectory=$HOME/venho/gc2-src" \
  --setenv=GE_ENV=test \
  "$HOME/venho/gc2-src/.venv/bin/venho-engine" migrate
systemd-run --user --unit=growth-engine-api-test-src \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine-test.env" \
  --property="WorkingDirectory=$HOME/venho/gc2-src" \
  --setenv=GE_ENV=test \
  "$HOME/venho/gc2-src/.venv/bin/venho-engine" api --host 127.0.0.1 --port 8023
curl --silent --show-error --output /dev/null --write-out 'live=%{http_code}\n' http://127.0.0.1:8023/health/live
curl --silent --show-error --output /dev/null --write-out 'ready=%{http_code}\n' http://127.0.0.1:8023/health/ready
```

Kết quả đã xác nhận: live `200`, ready `200`; `https://ge-test.venhohotel.com/internal/...` không có Access token trả `403`; `/media/publish` với token sai trả `403` từ API kèm `Cache-Control: private, no-store`. Probe public đã dùng URL media thử sai; không ghi signed URL vào runbook. Để tái kiểm tra an toàn, chỉ in status/header và dùng URL invalid tổng hợp:

```bash
curl --silent --show-error --max-redirs 0 --output /dev/null \
  --write-out 'internal-without-access=%{http_code}\n' \
  https://ge-test.venhohotel.com/internal/growth/v2/executions/authorize
curl --silent --show-error --max-redirs 0 --dump-header - --output /dev/null \
  'https://ge-test.venhohotel.com/media/publish/0000000000000000000000000000000000000000000000000000000000000000.jpg?t=invalid' \
  | awk 'BEGIN{IGNORECASE=1} /^HTTP\// || /^Cache-Control:/ {gsub("\\r", ""); print}'
```

Các lệnh trên ghi lại cách kiểm tra; không chạy chúng từ máy Mac khi chỉ đang sửa repo. Production deploy và `growth-engine-api-test.service` vẫn là bước riêng phía dưới, sau khi release path `~/venho/growth-engine/current` tồn tại.

Trên checkout GC2 sạch, sau khi review các commit:

```bash
git status --short
git rev-parse HEAD
git push origin gc2/build-v1-2
```

Trước deploy, **Harry/operator chạy migration trên production DB mới** từ một clone GC2 riêng ngoài `~/venho/growth-runtime/venho-ai-studio`. `deploy-release.sh` chỉ gọi `migrate --check`; CLI command `venho-engine migrate` mới áp migration. Từ thư mục gốc checkout GC2 đúng SHA, build cùng runtime đã pin rồi áp schema bằng env file production:

```bash
UV_PYTHON_PREFERENCE=only-managed "$HOME/.local/bin/uv" sync --frozen --python 3.11 --extra api --extra drive --extra gemini
systemd-run --user --pipe --wait --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" \
  --property="WorkingDirectory=$PWD" \
  --setenv=GE_ENV=production \
  "$PWD/.venv/bin/venho-engine" migrate
```

Lệnh `migrate` dùng đúng `GE_DB_PATH` của file production và áp migration; `venho-engine migrate --check` chỉ kiểm tra. Chạy sau khi DB path đã đối chiếu vào vùng state GC2 mới, và trước `deploy-release.sh`; không trỏ vào legacy DB. Không có migration operator/script nào khác trong repo.

Ghi lại SHA được review, rồi trên cùng checkout chạy:

```bash
bash ops/asus-server/growth-engine/deploy-release.sh <reviewed-git-sha>
```

Script yêu cầu production DB đã ở schema mục tiêu và runtime control `production` đã là `DISABLED`; script không migrate DB. Sau deploy, cài user unit API TEST, chạy migration vào DB TEST riêng, rồi start service:

```bash
install -d -m 700 "$HOME/.config/systemd/user"
install -m 644 ops/asus-server/growth-engine/growth-engine-api-test.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemd-run --user --pipe --wait --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine-test.env" \
  --property="WorkingDirectory=$HOME/venho/growth-engine/current" \
  --setenv=GE_ENV=test \
  "$HOME/venho/growth-engine/current/.venv/bin/venho-engine" migrate
systemctl --user start growth-engine-api-test.service
```

Kiểm tra TEST API:

```bash
curl --fail --silent --show-error http://127.0.0.1:8023/health/live
curl --fail --silent --show-error http://127.0.0.1:8023/health/ready
```

**Mong đợi:** deploy báo đúng release SHA đang hoạt động, `doctor` PASS, production mode vẫn `DISABLED`; TEST API trả `live` và `ready` trên loopback cổng `8023` với DB TEST.

**Dừng:** source checkout bẩn, SHA chưa có trên origin, migration/doctor không PASS, production chưa `DISABLED`, hoặc TEST API không ready. Deploy script tự rollback khi health/doctor sau switch lỗi. Dừng API TEST bằng:

```bash
systemctl --user stop growth-engine-api-test.service
```

Xác nhận Access/tunnel từ shell có sẵn `CF_ACCESS_CLIENT_ID` và `CF_ACCESS_CLIENT_SECRET`. Không bật xtrace. GET tới route POST-only phải qua Cloudflare/tunnel và tới ứng dụng, nơi kết quả dự kiến là `405`; thiếu/không hợp lệ service token phải dừng ở Cloudflare `403` hoặc login denial. Header được đọc từ env/config manager và không in giá trị:

```bash
[[ "$-" != *x* ]] || { printf 'Tắt xtrace trước khi gửi Access headers.\n' >&2; exit 2; }
: "${CF_ACCESS_CLIENT_ID:?missing CF_ACCESS_CLIENT_ID}"
: "${CF_ACCESS_CLIENT_SECRET:?missing CF_ACCESS_CLIENT_SECRET}"
probe_status="$(curl --config <(printf 'header = "CF-Access-Client-Id: %s"\nheader = "CF-Access-Client-Secret: %s"\n' \
  "$CF_ACCESS_CLIENT_ID" "$CF_ACCESS_CLIENT_SECRET") \
  --silent --show-error --max-redirs 0 --output /dev/null --write-out '%{http_code}' \
  --request GET https://ge-test.venhohotel.com/internal/growth/v2/executions/authorize)"
printf 'Access/tunnel probe: HTTP %s\n' "$probe_status"
test "$probe_status" = 405
```

Xác nhận `/media/publish` bypass Access nhưng không cache phản hồi lỗi. Lệnh sau chỉ in status và Cache-Control, không in body:

```bash
headers_file="$(mktemp)"
trap 'rm -f "$headers_file"' EXIT
media_status="$(curl --silent --show-error --max-redirs 0 --dump-header "$headers_file" \
  --output /dev/null --write-out '%{http_code}' \
  'https://ge-test.venhohotel.com/media/publish/0000000000000000000000000000000000000000000000000000000000000000.jpg?t=invalid')"
printf 'Invalid media probe: HTTP %s\n' "$media_status"
awk 'BEGIN{IGNORECASE=1} /^Cache-Control:/ {gsub("\r", ""); print}' "$headers_file"
rm -f "$headers_file"
trap - EXIT
```

Sau khi có signed TEST media URL hợp lệ được giữ kín trong `GE_TEST_MEDIA_URL`, lặp lại lệnh `curl` với biến này: kết quả cần là HTTP `200` và `Cache-Control: private, no-store`. Không echo hay dán signed URL.

### Nạp bí mật không lộ

Trong shell Bash tương tác, dùng hàm dưới đây để thay đúng một biến trong environment file. Giá trị được đọc ẩn và truyền qua stdin tới Python, không thành đối số tiến trình; hàm từ chối shell xtrace và không in giá trị:

```bash
setenv() {
  local name="$1" file="$2" value status
  [[ "$-" != *x* ]] || { printf 'Tắt xtrace trước khi nạp bí mật.\n' >&2; return 2; }
  [[ "$name" =~ ^GE_[A-Z0-9_]+$ && -f "$file" ]] || return 2
  IFS= read -r -s -p "Giá trị cho ${name}: " value
  printf '\n' >&2
  printf '%s' "$value" | python3 -c '
import os, re, sys, tempfile
p, n = sys.argv[1:]
v = sys.stdin.read()
if not v or any(char in v for char in "\n\r\0"):
    raise SystemExit("giá trị phải là một dòng không rỗng")
with open(p, encoding="utf-8") as source:
    lines = [line.rstrip("\n") for line in source if not re.match(r"^\s*" + re.escape(n) + r"\s*=", line)]
lines.append(n + "=" + v)
fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(p) or ".")
os.fchmod(fd, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as target:
    target.write("\n".join(lines) + "\n")
os.replace(temp_path, p)
os.chmod(p, 0o600)
' "$file" "$name"
  status=$?
  unset value
  chmod 600 "$file"
  return "$status"
}
```

Chỉ dùng hàm này cho biến TEST bổ sung sau khi xác định lệnh nào sẽ đọc biến đó. Không dùng để thay `GE_SERVICE_TOKENS` hoặc `GE_CAPABILITY_KEYS` mà `setup-test-env.sh` đã tạo.

Kiểm tra chỉ in tên biến, trạng thái và quyền file; không `cat`, `grep` giá trị hay `source` env file:

```bash
python3 - "$HOME/venho/secrets/growth-engine-test.env" <<'PY'
import os, re, sys
path = sys.argv[1]
rows = {}
for line in open(path, encoding="utf-8"):
    match = re.match(r"^\s*(GE_[A-Z0-9_]+)\s*=(.*)$", line.rstrip("\n"))
    if match:
        rows[match.group(1)] = match.group(2).strip().strip("\"")
for name in ("GE_ENV", "GE_DB_PATH", "GE_MEDIA_ROOT", "GE_PUBLIC_BASE_URL", "GE_CAPABILITY_KEYS", "GE_SERVICE_TOKENS", "GE_MAKE_WEBHOOK_URL_PAGE_TEST", "GE_MAKE_WEBHOOK_URL_IG_TEST"):
    value = rows.get(name, "")
    state = "TRONG" if not value else "PLACEHOLDER" if "REQUIRED_FROM_P0" in value else "DA_CO_GIA_TRI"
    print(name, state)
print("FILE_PERMISSION", oct(os.stat(path).st_mode & 0o777))
PY
```

Thêm/bỏ tên trong danh sách status theo env file cần rà; giá trị không bao giờ được in.

## 4. Cấu hình Cloudflare hostname và Access cho TEST

Đã xác minh 10/11/2026: hostname `https://ge-test.venhohotel.com` dùng tunnel locally-managed `venho-n8n` (`/etc/cloudflared/config.yml` trên server). Ingress `^/(internal|media/publish)/` proxy tới `http://localhost:8023`; path khác trả 404. Access app `growth-engine-test-internal` bảo vệ `/internal` bằng Service Auth token có tên `make-growth-engine-test`; `/media/publish` bypass Access nhưng vẫn cần signed capability. Không thay đổi hostname production ở bước này. Tất cả response `/media/publish` phải có `Cache-Control: private, no-store`.

Từ máy ngoài, thử endpoint authorize không có Access headers; Cloudflare phải chặn request:

```bash
curl --silent --show-error --include --max-time 10 \
  https://ge-test.venhohotel.com/internal/growth/v2/executions/authorize \
  -H 'Content-Type: application/json' --data '{}'
```

Sau đó dùng probe GET ở bước 3 với `CF_ACCESS_CLIENT_ID` và `CF_ACCESS_CLIENT_SECRET` trong environment. **Mong đợi:** thiếu Access bị edge chặn; Access hợp lệ qua tunnel và tới ứng dụng, nơi route POST-only trả 405. Probe này không gửi bearer/body và không sửa dữ liệu.

**Dừng:** login redirect không rõ nguồn, request không bị edge bảo vệ, hoặc không phân biệt được edge denial với application 401. Chưa đạt thì không nối Make TEST.

## 5. Tạo scenario Make TEST và chạy MK-1…MK-11

Khi cấu hình ban đầu, dùng bản copy TEST `VenHo Growth Agent TEST` (ID `6924867`), giữ Inactive cho đến khi cấu hình xong, đặt trigger Immediately as data arrives và không sửa production `VenHo Growth Agent-FB/IG` (ID `5868920`). Trạng thái được Harry xác nhận 11/11/2026: TEST Active, sequential, Immediately; webhook có 15 trường. Facebook modules 3/12 cùng Page TEST `1363761820162798`; Instagram module 6 dùng `@hanhpham1504`, ID `17841472240799413`. Không dùng production ID làm TEST destination. Runner dùng DB/channel TEST riêng cho từng ca; ca `sequential` giữ cùng DB/channel cho hai delivery khác nhau. Router cố định `fb_hanoi` → Facebook 3, `ig_venho` → Instagram 6, `fb_venho` → Facebook 12; fallback OFF, không filter `publication_id`, không Webhook response khi sequential. Facebook tải ảnh binary bên trong từng nhánh; Instagram nhận signed `media_url`. Sau import, đặt lại lịch về Immediately as data arrives và mở+Save HTTP 25. Xem [make_blueprint_v2.md](make_blueprint_v2.md) và [make_capabilities.md](../make_capabilities.md) để đối chiếu evidence đã khử bí mật.

Bootstrap webhook dưới đây đã hoàn tất ngày 10/11/2026. Chỉ lặp lại nếu Make phải redetermine data structure; ca `sequential` không cần gửi lại payload mẫu. Payload mẫu [make_test_sample_payload.json](make_test_sample_payload.json) theo đúng JSON Schema `growth.command.v2`; envelope này **không có** `content`, `image_url` hoặc `publication_id`. `command_token` và `payload_hash` chỉ là giá trị tổng hợp để Make nhận tên/kiểu trường, không phải chữ ký hợp lệ; authorize sẽ từ chối nó. Không gửi mẫu khi đường đi tới module HTTP/đăng bài còn nối. Nếu cần reset cấu trúc, dùng đúng năm bước sau:

1. Xác nhận chỉ scenario TEST đang mở, scenario đang Inactive và trigger đặt Immediately as data arrives; tạm ngắt toàn bộ module sau Custom webhook để không gọi HTTP hay đăng bài.
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

Sau khi mọi gate được duyệt, thứ tự mở target production là `fb_hanoi` → `fb_venho` → `ig_venho`; chỉ mở target kế tiếp sau khi target trước có receipt/verify xác định. Trong phiên TEST này không bật production; bài thử công khai chỉ được gửi tới Page TEST sau xác nhận `GUI` bên dưới.

### Runner TEST — fb_hanoi

Lượt đầu ngày 10/11/2026 đã dùng import 20 module và scenario Inactive. Trạng thái sau ca TEST 11/11: scenario `6924867` Active với blueprint 26 module, sequential và Immediately. API TEST dùng transient unit `growth-engine-api-test-src` trên `127.0.0.1:8023`, env `~/venho/secrets/growth-engine-test.env`. TEST Graph API `v27.0` được Harry đọc từ Graph API Explorer; Make connection tham chiếu bằng tên `Ven Ho Hotel Hanoi (Ha Pham)` (ID số chưa xác minh). Runner chỉ cần route ref, Page ID, principal, Graph API version và TEST runtime env; không đọc connection ref/owner.

Sau khi cập nhật checkout server có sửa đổi media handler, restart transient unit `growth-engine-api-test-src` để process nạp code mới. Sửa đổi này không cần DB migration.

Sau khi cập nhật checkout server để có commit chứa manifest và wrapper này, chạy từ `~/venho/gc2-src`:

```bash
bash ops/asus-server/growth-engine/run-test-command.sh
```

Wrapper hỏi ẩn TEST webhook URL rồi idempotently đặt `GE_TEST_CHANNEL_KEY=fb_hanoi`, một UUID chuẩn trong `GE_TEST_CHANNEL_ID`, `GE_TEST_REMOTE_PAGE_ID=1363761820162798` và `GE_MAKE_WEBHOOK_URL_PAGE_TEST`. UUID được sinh một lần nếu thiếu và được giữ nguyên khi chạy lại; `page_test` trong manifest là khóa tra cấu hình, không phải giá trị channel UUID. Wrapper từ chối env không phải TEST, target khác, webhook không khớp giá trị đã lưu hoặc DB/media path ngoài TEST. Không đụng file backup `.bak-20261110102217`.

Sau khi tạo command, wrapper tự GET signed media URL qua `http://127.0.0.1:8023` trước khi hỏi `ACTIVE` hoặc `GUI`. Nó yêu cầu HTTP 200, `image/jpeg`, `Cache-Control: private, no-store`, body khớp SHA trong path và không in URL/token. Nếu check thất bại thì dừng trước cả hai xác nhận, không gửi webhook.

Runner không tự bật/tắt scenario. Trước mỗi lượt, xác nhận đúng scenario TEST đang Active rồi gõ `ACTIVE`; tiếp theo xác nhận `GUI` tại prompt tương ứng. Chỉ sau khi media preflight đạt và cả hai xác nhận mới gửi. Nếu không xác nhận, webhook không được gửi; private envelope mode `600` được giữ lại để tránh tạo command khác.

Sau khi gửi, wrapper đọc DB TEST ở chế độ chỉ đọc tối đa 120 giây, tiếp tục chờ khi receipt còn `RECEIVED`, rồi in command/execution/`receipt_inbox.processing_state`, outcome, `platform_post_id` và `failed_step`. Không in webhook URL, capability token hay media URL; không tự gửi lại khi trạng thái không rõ. Nếu hết hạn khi receipt vẫn `RECEIVED`, dùng lệnh one-shot bên dưới.

### Áp receipt TEST một lần sau Make History

Lượt TEST 3 của Harry (10/11/2026 22:33 ICT, `fb_hanoi`) đã đăng thành công trên Page TEST: History chạy webhook → F1 HTTP 4 (`200 image/jpeg`) → authorize HTTP 16 → Facebook Pages 3 → receipt HTTP 17 trong 5 operations/8 giây. Post ID do Make trả về là `1363761820162798_122106835935535879`. Hai nhánh `ig_venho` và `fb_venho` bị filter. DB snapshot ban đầu cho thấy receipt `RECEIVED` trước khi có worker.

Sau khi cập nhật `~/venho/gc2-src` tới commit có lệnh `apply-test-receipts`, xử lý tối đa một batch job receipt bằng transient unit riêng. Lệnh bị giới hạn vào `GE_ENV=test` và DB nằm dưới TEST state; nó không chạy scheduler, dispatch, timeout watcher hay jobs lane:

```bash
cd "$HOME/venho/gc2-src"
systemd-run --user --pipe --wait --collect \
  --unit=growth-engine-test-receipts \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine-test.env" \
  --property="WorkingDirectory=$HOME/venho/gc2-src" \
  --setenv=GE_ENV=test \
  "$HOME/venho/gc2-src/.venv/bin/venho-engine" apply-test-receipts
```

Kết quả Harry xác nhận ngày 11/11/2026: `receipt_jobs claimed=1 completed=1 failed=0`. Lệnh không restart API TEST; nó mở cùng TEST DB, claim job `apply_receipt`, áp receipt và kết thúc.

Kiểm tra execution, receipt, outcome và đối chiếu platform post ID với giá trị từ Make History:

```bash
sqlite3 -header -column "$HOME/venho/state/growth-engine-test/growth_engine.db" <<'SQL'
SELECT c.id AS command_id,
       e.state AS execution_state,
       i.processing_state AS receipt_inbox_state,
       json_extract(i.body_json, '$.outcome') AS outcome,
       d.platform_post_id AS platform_post_id,
       CASE WHEN d.platform_post_id = json_extract(i.body_json, '$.platform_post_id')
            THEN 'MATCH' ELSE 'MISMATCH' END AS post_id_check
FROM outbox_commands c
JOIN executions e ON e.command_id = c.id
JOIN deliveries d ON d.id = e.delivery_id
JOIN receipt_inbox i ON json_extract(i.body_json, '$.command_id') = c.id
WHERE c.id = 'cd73c43a-1a28-4922-bd4d-29aeaf6d665d';
SQL
```

Kết quả Harry xác nhận: `execution_state=REPORTED`, `receipt_inbox_state=APPLIED`, `outcome=POST_CREATED`, `platform_post_id=1363761820162798_122106835935535879`, `post_id_check=MATCH`. `outbox_commands.state=AUTHORIZED` là đúng: authorize kết thúc giao command; receipt cập nhật execution/delivery/inbox. Không có trạng thái `outbox_commands.COMPLETED`. Đây là receipt report, chưa phải bước verify bài trên Meta.

### Bốn ca TEST follow-up (đã hoàn tất 11/11/2026)

Blueprint 26 module đã được import trước các ca này. Bốn lượt đã hoàn tất; không chạy lại để tránh bài công khai trùng:

```bash
bash ops/asus-server/growth-engine/run-test-case.sh ig_venho
bash ops/asus-server/growth-engine/run-test-case.sh duplicate
bash ops/asus-server/growth-engine/run-test-case.sh broken-media
bash ops/asus-server/growth-engine/run-test-case.sh bad-token
```

Runner mỗi lượt tạo DB/channel TEST riêng, kiểm media URL trên loopback, yêu cầu `ACTIVE` rồi `GUI`, poll/apply receipt và khôi phục API TEST gốc. Kết quả Make History đã ghi trong [make_capabilities.md](../make_capabilities.md): IG publish, duplicate, broken-media và bad-token đều PASS. `test_api_restore=PASS` phải xuất hiện sau mỗi lượt runner.

- `ig_venho`: PASS — I1 `200 image/jpeg`, Meta tải signed URL, media ID `18453049759135668`, receipt `APPLIED`.
- `duplicate`: PASS — replay trả `ALREADY_AUTHORIZED`; một execution/receipt/post.
- `broken-media`: PASS — F1 → `Ignore`, không authorize/post, scenario vẫn Active.
- `bad-token`: PASS — authorize bị từ chối, không module đăng, scenario vẫn Active.

Kết quả và giới hạn evidence đã được ghi trong `make_capabilities.md`. Không chạy lại bốn ca này. Xóa DB/media/env case riêng ở bước dọn cuối giai đoạn TEST.

### Ca sequential cho MK-1 — PASS (11/11/2026)

Không cần chạy lại hoặc import blueprint. Hai webhook `fb_hanoi` được gửi cách nhau 300 ms. Make History run 1 bắt đầu 15:22:30 ICT, chạy 7 giây; run 2 bắt đầu 15:22:39 ICT sau khi run 1 kết thúc, chạy 5 giây. Bài đăng khác nhau (`…_122107590483535879`, `…_122107590693535879`); cả hai receipt `APPLIED`. Kết luận MK-1 PASS: Make xử lý tuần tự.

Lượt runner ghi `test_api_restore=PASS` sau khi transient API TEST được khôi phục và readiness trả 200.

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
