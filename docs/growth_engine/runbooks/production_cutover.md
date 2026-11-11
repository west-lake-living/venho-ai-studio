# GC2 Stage B — production cutover

**Trạng thái:** chỉ chuẩn bị quy trình; không chạy server, Make, Meta, Telegram, Healthchecks hoặc Cloudflare trong task này. Không đăng thử công khai. Mọi bước phát hành phải được thực hiện theo cửa sổ cutover và dừng tại gate nếu điều kiện không đạt.

## Trạng thái đã chốt

- Make TEST: MK-1…MK-6 PASS; sequential và `Immediately as data arrives` đã có bằng chứng. Điều này mở gate kỹ thuật cho `LIVE_MANUAL`, không tự đổi runtime production.
- Production Make scenario: `VenHo Growth Agent-FB/IG`, ID `5868920`; ba route theo thứ tự `fb_hanoi` → `ig_venho` → `fb_venho`.
- Page/account đích: Hanoi `1124616474074140`; Ven Hồ `803531149684177`; Instagram `17841457936965829`.
- Bốn slot mỗi tuần vẫn là thứ Hai, Tư, Sáu, Bảy lúc 09:00 Asia/Ho_Chi_Minh. Mỗi slot Facebook tạo hai delivery/command độc lập (`fb_hanoi`, `fb_venho`), cùng caption/bytes ảnh đã duyệt; mỗi Page có receipt và verify riêng. Instagram có delivery/command riêng. Duyệt nhóm có thể duyệt cả hai Page Facebook và Instagram trong một batch, nhưng không dispatch bài.
- Instagram production bắt buộc dùng signed media URL; ảnh phải là JPEG ≤8 MB, tỉ lệ 4:5–1.91:1. `instagram_photo_v1` hiện là JPEG ≤5 MiB, đúng 4:5.
- API production unit bind `127.0.0.1:8021` theo `growth-engine-api.service` và host inventory. Concierge `8022`, TEST `8023`; không dùng hai cổng đó.

## Gate trước khi bắt đầu

1. Dùng release SHA đã review và push; checkout nguồn sạch. `deploy-release.sh` đòi checkout sạch và tự chạy `doctor --pre-switch`.
2. Doctor production yêu cầu đủ Make webhook, Meta token, Telegram, DB/media, capability keys và service-token hashes. Vì vậy điền sẵn các secret cần thiết trước lần deploy đầu; bước 3 bên dưới là hoàn tất/đối chiếu rồi restart units.
3. `channels.yaml` hiện còn metadata production chưa điền (`make_scenario_id`, `make_connection_ref`, `graph_api_version`, owner/ngày xác minh). Xác minh trên Make/Meta, điền manifest **trước bước 1**, rồi provision channel DB ở `DISABLED`. Doctor cần thấy đủ 3 channel/config để báo PASS đầy đủ.
4. Dashboard cần Cloudflare DNS hostname `growth-api.venhohotel.com`, Access Service Auth app/token production và quyền operator trên VENHO OS. Những dashboard này không được thay đổi trong bước chuẩn bị này.
5. `retire_legacy.md` có checklist gỡ filter `Venho signature` và xoay/retire literal hex. Chưa tắt publisher legacy khi chưa đạt các gate retire đã nêu.

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

Xác nhận cổng 8021 đang trống trước khi bật API. Không chọn cổng khác nếu đang có listener; điều tra process trước. Cổng 8022/8023 không được tái sử dụng.

```bash
ss -H -ltnp 'sport = :8021'
```

**Mong đợi:** không có output. **Dừng:** có listener hoặc không xác định được owner. Sau deploy, listener 8021 phải thuộc Growth API; không được là concierge hay TEST.

**Quay lui:** chưa có thay đổi.

## 1. Migrate DB mới, khởi tạo DISABLED, deploy release

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

Xác minh unit files rồi deploy đúng SHA:

```bash
systemd-analyze --user verify \
  ops/asus-server/growth-engine/growth-engine-api.service \
  ops/asus-server/growth-engine/growth-engine-worker@.service
git fetch origin gc2/build-v1-2
read -r -p 'SHA đã review: ' REVIEWED_GIT_SHA
[[ "$REVIEWED_GIT_SHA" =~ ^[0-9a-f]{40}$ ]]
git cat-file -e "${REVIEWED_GIT_SHA}^{commit}"
git merge-base --is-ancestor "$REVIEWED_GIT_SHA" origin/gc2/build-v1-2
bash ops/asus-server/growth-engine/deploy-release.sh "$REVIEWED_GIT_SHA"
systemctl --user enable growth-engine-api.service growth-engine-worker@publish.service growth-engine-worker@jobs.service
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

**Mong đợi:** schema current, doctor PASS, API/worker units active; runtime `DISABLED`, global pause bật; API chỉ bind loopback 8021. Channel rows ban đầu đều disabled.

**Dừng:** DB nằm ngoài state GC2 mới; doctor FAIL/WARN; controls không `DISABLED` + paused; API không ready hoặc bind sai port; unit/doctor không PASS.

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

Tạo trên dashboard Cloudflare DNS route `growth-api.venhohotel.com` qua tunnel locally-managed `venho-n8n`. Tạo Access app production bảo vệ `/internal/*` bằng Service Auth; tạo service token tên riêng cho Make production. `/media/publish/*` không qua Access vì Meta phải tải signed URL; endpoint vẫn kiểm capability và mọi response phải có `Cache-Control: private, no-store`.

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

Trên server, setup API bearer production (mỗi principal một bearer) và capability key mới. Script chỉ ghi SHA-256 vào `GE_SERVICE_TOKENS`, handoff bearer mode 600; không in giá trị:

```bash
cd "$HOME/venho/gc2-src"
python3 ops/asus-server/growth-engine/setup-production-make-bearers.py
stat -c '%a' "$HOME/venho/secrets/growth-engine.env" "$HOME/venho/secrets/growth-engine.make-bearers.tmp"
```

Chỉ mở handoff bằng editor cục bộ an toàn để nhập ba bearer vào HTTP headers Make matching `fb_hanoi`, `fb_venho`, `ig_venho`; không `cat`, không terminal recording. Giữ file tới sau khi scenario production được nhập và xác minh xong.

Từ Mac, nạp 5 Meta read token cho ba account production (hai Page aliases + hai biến probe FB + một IG) bằng script đã có. Token nhập ẩn; output chỉ là tên biến/trạng thái:

```bash
python3 ops/asus-server/growth-engine/push-meta-tokens.py --host asus-server
```

Trên server điền `GE_TELEGRAM_BOT_TOKEN`, `GE_TELEGRAM_CHAT_ID`, `GE_HEARTBEAT_URL` từ secret store/Healthchecks; giữ `growth-engine.env` mode 600. Không gửi tin Telegram thử. Đối chiếu tên biến mà không in giá trị:

```bash
python3 - "$HOME/venho/secrets/growth-engine.env" <<'PY'
import sys
from pathlib import Path
required = {
    "GE_CAPABILITY_KEYS", "GE_SERVICE_TOKENS", "GE_PUBLIC_BASE_URL", "GE_DASHBOARD_BASE_URL",
    "GE_HEARTBEAT_URL", "GE_TELEGRAM_BOT_TOKEN", "GE_TELEGRAM_CHAT_ID",
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

**Mong đợi:** all required variable names pass; Meta token helper reports the five names configured; `doctor` PASS; heartbeat seen; no secret value displayed. Access Client ID/Secret are entered into Make, not this env file.

**Dừng:** thiếu bất kỳ biến nào, file mode khác 600, token/script error, doctor không PASS, heartbeat vắng hoặc notification worker lỗi.

**Quay lui:** giữ API `DISABLED` + global pause; khôi phục env từ secret store đã duyệt, không xóa handoff khi Make cần nạp lại bearer. Không đưa secret vào chat/Git.

## 4. Snapshot, tạo và duyệt Make blueprint production

Trên Make, export scenario hiện tại `5868920` trước khi chỉnh. Lưu export rollback ngoài Git ở nơi riêng tư mode 600; không in hoặc đính kèm export (có thể chứa webhook/signature). Scenario phải Inactive trong lúc thay.

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

**Chỉ sau khi Harry duyệt bản draft reviewable:** import vào scenario `5868920`, giữ scenario Inactive. Nạp base URL `https://growth-api.venhohotel.com`, ba bearer theo route, Access Client ID/Secret vào các module `/internal`. Không tạo file JSON đã điền secret. Kiểm tra connection hiện có trên từng module, Router/filter/channel IDs và thứ tự route; `Venho signature` bị gỡ, common filter là `schema_version = growth.command.v2` AND `environment = production`. Ghi bước xoay/retire literal hex theo [retire_legacy.md](retire_legacy.md), không ghi giá trị.

Sau import tách riêng hai thao tác UI bắt buộc: (1) đặt scheduling về **Immediately as data arrives** rồi Save; (2) mở HTTP module `25` (I1), xác nhận Method `GET` và body rỗng, rồi Save module. Giữ sequential ON, error handler terminal Skip, Store incomplete executions = No, không có Retry/Break/Resume và không thêm Webhook response.

Caption của post module lấy từ authorize response (`data.caption`), là nội dung approved của command. Facebook mỗi route tải `media_url` riêng rồi map binary của route đó; Instagram map signed `media_url`. Receipt map verbatim module output `id`. Hai Page Facebook là hai command riêng, không một payload fan-out.

**Mong đợi:** Make scenario vẫn Inactive; Exactly 3 route/filter đích đúng; connections không đổi; immediate trigger; module 25 saved; secret fields được Make bảo vệ; không đăng bài.

**Dừng:** thiếu Harry approval, ID/connection không khớp, literal URL còn, filter sai, schedule/Module 25 chưa Save, hoặc scenario bị Active ngoài giờ cutover.

**Quay lui:** khi runtime vẫn `DISABLED` và scenario Inactive, import export rollback đã lưu, kiểm tra connection/filter, khôi phục setting cũ và giữ scenario Inactive cho đến khi đối chiếu xong. Không bật legacy nếu không có quyết định retire/rollback mới.

## 5. Lịch, command và duyệt nhóm

Không sửa `config/projects/venho_hotel/growth/cadence_policy.yaml`: 4 slot/tuần (Mon/Wed/Fri/Sat 09:00 ICT). Sau khi đủ production channels, `EnsureSlots` phải tạo 4 slot và 12 targets mỗi tuần: 4 Hanoi, 4 Ven Hồ, 4 Instagram. Mỗi FB slot dùng một approved Facebook caption/ảnh bytes nhưng có 2 delivery, 2 command, 2 receipt và 2 verify. Cả hai delivery FB thuộc cùng nhóm duyệt; batch approval hỗ trợ hai Page cùng Instagram và không tự dispatch.

Trước mở channel, VENHO OS phải hiển thị đúng 4 slot cùng 12 targets và group approval. Kiểm tra không có due/overdue approved command nào sẽ được phát ngoài ý muốn khi pause được mở. Không bấm duyệt hoặc chuyển runtime nếu inventory slot/targets chưa khớp.

**Quay lui:** giữ `DISABLED` + pause; sửa lịch/targets trên database production qua luồng được audit. Không sửa trực tiếp SQL.

## 6. Mở theo thứ tự — LIVE_MANUAL

Ba channel/config records đã được provision disabled ở bước 1. `manage-production-channels.py set-enabled` chỉ cho phép mở nếu runtime `LIVE_MANUAL`, global pause đang bật, ID đúng, config có và thứ tự mở hợp lệ. Thực hiện trên dashboard operator:

1. Đặt mode `LIVE_MANUAL`, giữ global pause ON.
2. Mở `fb_hanoi`:

   ```bash
   systemd-run --user --pipe --wait --collect \
     --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" --setenv=GE_ENV=production \
     "$HOME/venho/growth-engine/current/.venv/bin/python" \
     "$HOME/venho/gc2-src/ops/asus-server/growth-engine/manage-production-channels.py" set-enabled --channel fb_hanoi --enable
   ```

   Khi còn pause, rà đúng route, filter, Page ID `1124616474074140`, approved slot và ảnh. Chỉ resume global pause tại slot đã duyệt để phát bài theo lịch; sau đó kiểm tra Make History → receipt APPLIED → verify.
3. Chỉ khi Hanoi ổn mới pause toàn cục, mở `fb_venho` bằng lệnh tương tự với `--channel fb_venho --enable`, rồi rà Page ID `803531149684177`. Resume tại slot kế tiếp đã duyệt; xác minh receipt riêng. Lỗi Ven Hồ không được resend Hanoi.
4. Chỉ khi cả hai Facebook route ổn mới pause toàn cục, bật `--channel ig_venho --enable`, rà signed URL và image variant; resume tại slot Instagram đã duyệt. Xác minh media ID, receipt và MK-11 container/publish stage riêng.

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
| Runtime + alerts | `GE_CAPABILITY_KEYS`, `GE_TELEGRAM_BOT_TOKEN`, `GE_TELEGRAM_CHAT_ID`, `GE_HEARTBEAT_URL` |
| Make Access | `CF-Access-Client-Id`, `CF-Access-Client-Secret` nhập vào từng module `/internal`; không lưu trong repo |

Không ghi URL webhook, token, signed URL, Access secret hoặc thông tin đăng nhập vào runbook/log/chat.
