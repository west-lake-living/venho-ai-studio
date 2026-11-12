# GC2 Stage B — production cutover

**Trạng thái theo xác nhận của Harry (11/11/2026):** production release `7eedfa3`; DB mới schema 9; runtime `DISABLED`, `global_pause=1`; ba channel tồn tại và `enabled=0`; API và hai worker active. `growth-api.venhohotel.com` đi qua Access app `growth-engine-production-internal` tới API loopback `127.0.0.1:8021`; `/internal` ngoài trả 403, `/media/publish` với token sai trả 403 cùng `Cache-Control: private, no-store`, đường dẫn khác trả 404. Service token Make `make-growth-engine-production` do Harry giữ.

Quyết định Harry ngày 12/11/2026: **hard cutover A**, T−0 là 16/11/2026 lúc 09:00 ICT. Commit `10892c4` sửa `[Install]`, kiểm tra lock publish và cảnh báo hạn Meta token, nhưng server vẫn đang ở `7eedfa3`; deploy bản mới là gate trước cutover. DB schema 9 đã đủ, không tạo DB hoặc migration mới. Nhiệm vụ này chỉ sửa repo; không thao tác server hoặc Make.

## Trạng thái đã chốt

- Make TEST: MK-1…MK-6 PASS; sequential và `Immediately as data arrives` đã có bằng chứng. Điều này mở gate kỹ thuật cho `LIVE_MANUAL`, không tự đổi runtime production.
- Production Make scenario hiện tại: `VenHo Growth Agent-FB/IG`, ID `5868920`; import v2 sẽ thay đường legacy cho cả ba kênh cùng lúc. Blueprint mới có ba route theo thứ tự `fb_hanoi` → `ig_venho` → `fb_venho`.
- Page/account đích: Hanoi `1124616474074140`; Ven Hồ `803531149684177`; Instagram `17841457936965829`.
- Bốn slot mỗi tuần vẫn là thứ Hai, Tư, Sáu, Bảy lúc 09:00 Asia/Ho_Chi_Minh. Mỗi slot Facebook tạo hai delivery/command độc lập (`fb_hanoi`, `fb_venho`), cùng caption/bytes ảnh đã duyệt; mỗi Page có receipt và verify riêng. Instagram có delivery/command riêng. Duyệt nhóm có thể duyệt cả hai Page Facebook và Instagram trong một batch, nhưng không dispatch bài.
- Instagram production bắt buộc dùng signed media URL; ảnh phải là JPEG ≤8 MB, tỉ lệ 4:5–1.91:1. `instagram_photo_v1` hiện là JPEG ≤5 MiB, đúng 4:5.
- API production unit bind `127.0.0.1:8021` theo `growth-engine-api.service` và host inventory. Concierge `8022`, TEST `8023`; không dùng hai cổng đó.
- Telegram production phải dùng token của bot riêng `@venho_growth_alerts_bot`, không dùng `@Venhohotel_bot`.
- Instagram Meta token là long-lived user token, dự kiến hết hạn khoảng `2027-01-10`; Data Access Expires khoảng 3 tháng sau ngày 11/11. Doctor giám sát hai ngày expiry độc lập; xác minh ngày chính xác trên Access Token Debugger.

## Gate trước khi bắt đầu

1. Dùng release SHA đã review và push; checkout nguồn sạch. `deploy-release.sh` đòi checkout sạch và tự chạy `doctor --pre-switch`.
2. Doctor production yêu cầu đủ Make webhook, Meta token, Telegram, DB/media, capability keys và service-token hashes. Vì vậy điền sẵn các secret cần thiết trước lần deploy đầu; bước 3 bên dưới là hoàn tất/đối chiếu rồi restart units.
3. Metadata production trong `channels.yaml` đã được điền theo Make 5868920; ánh xạ Page name↔ID cần xác nhận bằng post ID của lượt production đầu. Ba channel và configs đã provision disabled.
4. Cloudflare production edge đã được xác minh theo kết quả Harry nêu ở trên. Còn phải xác minh VENHO OS production đã deploy BFF/UI Growth v2, dùng `GROWTH_BACKEND=v2`, và group approval gọi đúng API production; chưa có bằng chứng deploy production.
5. `retire_legacy.md` có checklist gỡ filter `Venho signature` và xoay/retire literal hex. Chưa tắt publisher legacy khi chưa đạt các gate retire đã nêu.
6. Production DB hiện rỗng, nên chưa có slot, delivery, revision hoặc approval v2 sẵn sàng. P4 generation/worker và P3 review use cases đã được nối với SQLite trong code và kiểm thử tích hợp, nhưng chưa có production run; credentials/cost policy và VENHO OS v2 production path phải được xác nhận trước khi dùng.
7. `retire_legacy.md` yêu cầu pilot P9-T04 đạt ít nhất 8 slot, 16 target outcomes, 14 ngày ổn định và restore rehearsal. Với production đang `DISABLED` và DB mới rỗng theo trạng thái đã báo, chưa có bằng chứng gate này đạt; khoảng thời gian tới 16/11 không đủ để tạo mới bằng chứng 14 ngày. Vì vậy 16/11 chỉ là ngày mục tiêu: nếu gate chưa có evidence trước cutover, **dừng và dời ngày**, giữ legacy làm publisher duy nhất. Chọn hard cutover A không tự miễn gate.

## Nội dung v2 và legacy import — gate cho slot đầu

Không coi bài `APPROVED_SCHEDULED` trong registry legacy là đã duyệt trong v2. Importer hiện tại giữ raw record/evidence, không tái tạo quyết định approval; các dòng legacy đã duyệt được chuyển sang `IN_REVIEW` với `APPROVAL_NOT_RESTORED`. Các dòng thiếu Page mapping/artifact/post ID được giữ `LEGACY_UNVERIFIED`. Importer mới được áp dụng trên synthetic fixture; phần mapping còn placeholder cho `fb_venho`/`ig_venho` và tạo channel legacy ở environment `test`, nên **không chạy `legacy-import --apply` vào DB production** trước khi có implementation production-safe và report được duyệt.

Pipeline v2 **chưa có bằng chứng đã chạy tạo/duyệt nội dung trên production**. P4 generator/lanes và SQLite wiring cùng P3 review workflows có code và integration tests, nhưng DB production hiện rỗng; điều đó chưa chứng minh provider, media/QC và VENHO OS group approval production hoạt động. Cần xác minh VENHO OS v2 trước khi coi slot nào đã sẵn sàng.

Importer legacy không thể chuyển một bài `APPROVED_SCHEDULED` thành bài đã duyệt v2: approval không được khôi phục, trạng thái thành `IN_REVIEW`; mapping production của importer cũng chưa an toàn. Tạo delivery/revision mới trong v2 và duyệt lại trên VENHO OS v2.

Đường tối thiểu để có delivery đã duyệt cho slot 16/11 là:

1. Deploy/kiểm tra VENHO OS BFF và UI v2, provider/content settings, budget/cost limits, media storage và `jobs` worker. Giữ global pause ON.
2. T−3, sau khi deploy code và xác nhận VENHO OS v2, đặt runtime `LIVE_MANUAL` nhưng giữ `global_pause=1`; bật riêng `fb_hanoi`. Chọn slot 16/11 chỉ khi legacy không còn command/Make run có thể đăng slot này.
3. `EnsureSlots`/jobs lane tạo Hanoi target; sinh package/revision, kiểm tra caption, ảnh, QC, facts, budget và Page ID; duyệt delivery `fb_hanoi` trên VENHO OS v2. Ngày 16/11 chỉ Hanoi được phép phát theo rollout đã chốt.
4. Sau khi Hanoi đã được đối soát, bật `fb_venho` và `ig_venho` trước slot kế tiếp 18/11, trong khi global pause vẫn bật. Tạo slot với đủ ba target trước khi generation chạy, rồi duyệt nhóm. Hai Page Facebook dùng cùng caption/bytes ảnh; Instagram dùng caption cùng nội dung và variant JPEG 4:5.

`EnsureSlots` chỉ tạo target cho channel đang enabled. Nếu VENHO OS v2, provider, media/QC hoặc group approval chưa đạt, giữ pause và dời slot; không thay bằng approval legacy.

Nếu VENHO OS v2 chưa deploy hoặc generation không tạo đủ ba target, dừng ở trạng thái DISABLED/paused; không thay thế bằng cách đánh dấu bài legacy là đã duyệt.

## Lựa chọn cutover

| Phương án | Tác động | Rủi ro đăng trùng / độ phức tạp |
|---|---|---|
| **A — hard cutover (khuyến nghị)** | Tắt/drain publisher legacy, rồi import blueprint v2 vào scenario 5868920. Một authority duy nhất; mở kênh v2 theo từng slot. Có thể bỏ lỡ target chưa mở trong slot chuyển tiếp. | Thấp hơn nếu legacy đã drain và mọi Make run/grant hết hạn. Rollback đơn giản nhất trước grant production đầu tiên. |
| **B — giữ legacy route cho kênh chưa mở** | Chạy tạm hai luồng hoặc giữ route legacy riêng khi v2 đã chạy một phần. | Cao: legacy Facebook hiện có thể đăng một payload lên cả hai Page, nên mở Hanoi ở v2 còn để legacy hoạt động có thể đăng trùng Hanoi. Muốn an toàn phải tách route Page B/IG, lọc theo channel/slot và đối soát hai registry; IG legacy còn dùng Google Drive URL. Phức tạp hơn và chưa có evidence TEST cho cấu hình lai. |

Harry đã chọn A. Theo rollout này, slot 16/11 có `fb_hanoi`; slot kế tiếp theo lịch là thứ Tư 18/11, khi đã bật `fb_venho` và `ig_venho` trước giờ chạy. Do GC2-D02, không được diễn giải slot 16/11 là đã đăng lên cả hai Facebook Page: nếu muốn cả hai Page cùng đăng ngày 16/11 thì phải đổi lịch mở channel trước T−0.

## Lịch cutover theo giờ ICT

### T−3 — thứ Sáu 13/11/2026: chuẩn bị delivery Hanoi

- Deploy release đã review có `[Install]`, doctor lock check và cảnh báo hạn token (tối thiểu commit `10892c4` cùng patch này), không tạo DB mới. Xác nhận schema 9, `DISABLED`/pause, units enabled+active, `Linger=yes`, doctor PASS; kiểm ngày expiry IG và bot production `@venho_growth_alerts_bot`.
- Xác nhận trước khi tiếp tục rằng evidence P9-T04 đã đủ ≥8 slot, ≥16 target outcomes, ≥14 ngày ổn định và restore rehearsal. Nếu không, 16/11 không còn là ngày cutover khả thi: dừng ở đây, giữ legacy làm publisher duy nhất và dời T−0.
- Deploy/kiểm tra VENHO OS BFF/UI v2 và `GROWTH_BACKEND=v2`; xác minh group approval gọi đúng API production trước khi tạo approval thật.
- Chuyển sang `LIVE_MANUAL`, giữ `global_pause=1`, bật riêng `fb_hanoi`. Tạo/đảm bảo slot 16/11 và Hanoi target; sinh nội dung/ảnh trong v2, rà QC/facts/Page ID/caption, rồi duyệt delivery `fb_hanoi` trên VENHO OS v2. Không có lệnh nào được phép dispatch khi pause bật.
- Kiểm tra registry/queue legacy cho slot 16/11. Nếu còn lệnh legacy có thể đăng, hủy/drain theo luồng được audit hoặc chọn slot sau; không tạo hai authority cho cùng một slot.

### T−1 — Chủ Nhật 15/11/2026: blueprint và secret import

- Trong Make scenario `5868920`, dùng **Copy blueprint to clipboard** cho bản backup legacy; lưu riêng tư thành `_incoming/make_production_export.json` mode 600, tính checksum, rồi xóa clipboard. Giữ file backup ngoài Git.
- Tạo draft production từ export, chạy checker **trên draft chưa có secret**, rồi review số module/route/mapping. Kỳ vọng 26 module, 3 route, sequential bật, Immediately trigger, đúng destination IDs. Không chạy secret scanner trên file đã điền bearer vì nó cố ý báo token literal.
- Tạo bearer mới với helper `setup-production-make-bearers.py --rotate-existing` khi production vẫn pause. Server chỉ nhận hash trong env; transfer handoff về Mac vào `_incoming/growth-engine.make-bearers.tmp` mode 600. Restart API để nạp hashes mới; không in handoff.
- Từ Mac, tải handoff bằng alias SSH đã cấu hình và khóa quyền ngay sau khi chuyển:

  ```bash
  scp -p asus-server:~/venho/secrets/growth-engine.make-bearers.tmp _incoming/growth-engine.make-bearers.tmp
  chmod 600 _incoming/growth-engine.make-bearers.tmp
  stat -f '%Lp' _incoming/growth-engine.make-bearers.tmp
  ```

  Kết quả mong đợi là `600`; dừng nếu SSH alias không trỏ tới ASUS production hoặc mode khác `600`. Không mở/in handoff.
- Chạy `fill_make_production_secrets.py` với Access production nhập ẩn. Script thay base URL bằng `https://growth-api.venhohotel.com`, bearer theo route, Access Client ID/Secret; ghi `_incoming/make_production_import.secret.json` mode 600 và chỉ in số lượng thay. Filler kiểm tra filter production, 9 internal modules, route/bearer khớp và không còn placeholder.
- Giữ handoff trên server/Mac và file import secret tới khi slot 18/11 và các route đã đối soát xong.

### T−0 — cửa sổ cutover, không đăng thử

1. Chỉ bắt đầu nếu toàn bộ gate retire trong [retire_legacy.md](retire_legacy.md) đã đạt và evidence được ghi. Nếu thiếu bất kỳ mục nào, **dừng; giữ legacy làm publisher duy nhất và dời T−0**. Khi đạt gate: giữ global pause ON; tắt đúng timer/workflow publish đã định danh, chặn legacy writes, drain Make runs/queues và chờ capability TTL.
2. Ghi snapshot cuối/checksum; kiểm không còn legacy command/run cho slot 16/11 và không có v2 grant nào đã dispatch. Backup scenario clipboard sẵn sàng.
3. Import `_incoming/make_production_import.secret.json` vào scenario 5868920. Kiểm common filter `schema_version` + `environment=production`, Router filters/ID, routes theo thứ tự, connections, caption/image mappings, bearer theo principal, Access headers, error handlers và Page/IG destination.
4. Đặt schedule **Immediately as data arrives** rồi Save scenario; bật **Sequential processing** và xác nhận lưu; mở HTTP 25 (I1), xác nhận GET/body rỗng và Save module. Chưa bật scenario nếu còn sai lệch.
5. Bật scenario, giữ runtime `LIVE_MANUAL`, chỉ `fb_hanoi` enabled, pause ON. Đối chiếu slot/delivery đã duyệt. Trước 09:00 xác nhận không có legacy execution pending; tại slot đã duyệt bỏ pause để dispatch Hanoi. Không gửi thử ngoài lịch.
6. Đọc Make History: F1 image 200, authorize, Facebook Pages module 3, receipt. Chờ receipt `APPLIED` và verify post trên Hanoi Page `1124616474074140`; ghi post ID/permalink và xác nhận tên↔ID. Nếu execution/outcome mơ hồ, bật pause và không chạy lại module.

### T+slot kế — thứ Tư 18/11/2026

- Sau khi Hanoi đã `REPORTED`/verified, giữ global pause ON; bật `fb_venho` và `ig_venho` trước khi generation lane tạo slot 18/11. Đảm bảo slot có đủ ba target trước khi tạo package/deliveries; group-approve Hanoi + Ven Hồ + IG cho cùng package/caption, Facebook cùng bytes ảnh và IG variant 4:5.
- Tại 09:00, dispatch theo lịch với ba route v2; đối chiếu Hanoi, Ven Hồ Page `803531149684177`, IG media/account `17841457936965829` riêng từng receipt/verify. Sau khi tất cả đạt, xóa bearer handoff server/Mac và `_incoming/make_production_import.secret.json`; không commit.

### Quay lui

- **Trước grant/post v2 đầu tiên:** giữ pause, tắt scenario v2, import lại blueprint backup `5868920`; chỉ bật legacy sau khi xác nhận v2 queue/grant bị chặn, legacy filters/queue khôi phục đúng và slot 16/11 chưa thể bị đăng muộn.
- **Sau Hanoi đã đăng hoặc khi có UNKNOWN:** pause v2, đối soát delivery/receipt/post từng target trước. Chỉ import backup rồi bật legacy nếu route legacy được giới hạn để không đăng lại Hanoi và không còn run/queue muộn. Legacy fan-out hiện có thể đăng Hanoi cùng Page Ven Hồ; nếu không chứng minh được cách chặn target đã thành công, không bật lại legacy—giữ pause và forward-recover trên DB v2.
- Không phục hồi registry legacy làm authority sau khi v2 đã có grant production.

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

Trước khi chạy, xác nhận production vẫn `global_pause=1`; lệnh rotation giữ DB và capability key, thay ba service-token hashes. Restart API để nạp hashes mới. Chuyển handoff mode 600 về Mac bằng SCP; không in/cat và không ghi vào shell history. Dùng [fill_make_production_secrets.py](../../../scripts/growth_engine/fill_make_production_secrets.py) để gắn bearer đúng route; giữ handoff server/Mac tới khi slot 18/11 và các route đã xác minh xong.

Từ Mac, nạp 5 Meta read token cho ba account production (hai Page aliases + hai biến probe FB + một IG) bằng script đã có. Token nhập ẩn; output chỉ là tên biến/trạng thái:

```bash
python3 ops/asus-server/growth-engine/push-meta-tokens.py --host asus-server
```

Trên server điền `GE_TELEGRAM_BOT_TOKEN`, `GE_TELEGRAM_CHAT_ID`, `GE_HEARTBEAT_URL` từ secret store/Healthchecks; bot token phải thuộc `@venho_growth_alerts_bot`, không dùng `@Venhohotel_bot`. Giữ `growth-engine.env` mode 600. Không gửi tin Telegram thử.

Thêm metadata expiry, không phải token: `GE_META_TOKEN_EXPIRY_IG_VENHO=2027-01-10` là ngày ước tính theo thông tin hiện có; `GE_META_DATA_ACCESS_EXPIRY_IG_VENHO=2027-02-09` là ước tính 90 ngày từ 11/11. Đối chiếu cả hai ngày với Access Token Debugger và sửa nếu khác. `doctor` trả WARN khi còn 14 ngày trở xuống hoặc metadata thiếu/sai. Worker publish kiểm tra mỗi 6 giờ và enqueue một Telegram notification bền vững cho mỗi loại expiry/ngày; notification dispatcher gửi qua bot production.

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

1. Ở T−3 đặt mode `LIVE_MANUAL`, giữ global pause ON; chỉ bật `fb_hanoi` cho slot 16/11. Legacy phải tiếp tục publisher duy nhất cho tới cửa sổ hard cutover, v2 không được dispatch khi pause.
2. Mở `fb_hanoi`:

   ```bash
   systemd-run --user --pipe --wait --collect \
     --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" --setenv=GE_ENV=production \
     "$HOME/venho/growth-engine/current/.venv/bin/python" \
     "$HOME/venho/gc2-src/ops/asus-server/growth-engine/manage-production-channels.py" set-enabled --channel fb_hanoi --enable
   ```

   Khi còn pause, rà route, filter, Page ID `1124616474074140`, approved slot và ảnh. Tại 09:00 ngày 16/11 chỉ bỏ global pause theo lịch đã duyệt; đối chiếu Make History → receipt APPLIED → verify. Page `fb_venho` và IG chưa publish slot này theo staging decision.
3. Sau khi Hanoi ổn, giữ/đặt pause ON. Trước generation cho slot kế 18/11, bật `fb_venho` bằng lệnh tương tự, rà ID `803531149684177`; bật `ig_venho`, rà ID `17841457936965829`. Đảm bảo ba targets cùng tồn tại trước khi jobs lane tạo package, rồi group-approve slot 18/11. Resume đúng 09:00 và đối soát từng receipt.
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
