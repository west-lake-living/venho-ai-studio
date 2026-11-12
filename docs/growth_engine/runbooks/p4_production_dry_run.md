# P4 production dry run — không đăng bài

**Cửa sổ:** 13–14/11/2026 ICT.  
**Mục tiêu:** kiểm tra P4 trên production DB cho slot `2026-11-16 09:00 Asia/Ho_Chi_Minh`, chỉ target `fb_hanoi`; runtime phải luôn `DISABLED`, `global_pause=1`, không bật Make và không phát command. Không mở/in giá trị bí mật.

## Trạng thái code cần biết trước

Release cần deploy là `2cc911484735eab1753263b7aafe57a339082aa3`. Code hiện có jobs scheduler và `RunLanes`, nhưng inspection tại SHA này cho thấy ba gate P4 chưa được nối thành luồng có thể PASS:

1. Production channels đang `enabled=0`. `EnsureSlots` chỉ tạo target cho channel enabled; helper mở channel hiện yêu cầu `LIVE_MANUAL`, trái yêu cầu giữ `DISABLED`. Không bypass bằng SQL hoặc đổi runtime trong dry run.
2. CLI không có lệnh one-shot `run-lanes`; jobs worker chạy lịch định kỳ. Lịch hiện có `ensure-slots` 00:10 ICT và fast lane mỗi giờ ở phút :40. Không khởi động transient worker thứ hai.
3. Generation ghi `prepare_variant` và `assemble_revision` jobs vào DB, nhưng jobs worker hiện không có handlers xử lý các job này. `PrepareVariant`/QC evaluator cũng chưa được compose vào bootstrap/job lane. Do đó không thể chứng minh chuỗi generation → variant → QC → revision `IN_REVIEW` bằng release hiện tại.

Các điểm trên có nghĩa P4 dry run **đang BLOCKED theo repo**, trước paid provider call. Không coi package/original image upload là PASS end-to-end. Nếu blocker được sửa bằng release mới trước cửa sổ chạy, lặp lại đúng các bước và chỉ dùng SHA đã review.

## 1. Deploy release, giữ controls fail-closed

Trên ASUS server, từ checkout sạch `~/venho/gc2-src`:

```bash
cd "$HOME/venho/gc2-src"
git fetch origin gc2/build-v1-2
git status --short
git merge-base --is-ancestor 2cc911484735eab1753263b7aafe57a339082aa3 origin/gc2/build-v1-2
bash ops/asus-server/growth-engine/deploy-release.sh 2cc911484735eab1753263b7aafe57a339082aa3
systemd-analyze --user verify growth-engine-api.service growth-engine-worker@publish.service growth-engine-worker@jobs.service
```

Kiểm tra linger, units, doctor và controls:

```bash
loginctl show-user "$USER" -p Linger --value
systemctl --user enable growth-engine-api.service growth-engine-worker@publish.service growth-engine-worker@jobs.service
systemctl --user is-active growth-engine-api.service growth-engine-worker@publish.service growth-engine-worker@jobs.service
systemd-run --user --pipe --wait --collect \
  --property="EnvironmentFile=$HOME/venho/secrets/growth-engine.env" \
  --property="WorkingDirectory=$HOME/venho/growth-engine/current" --setenv=GE_ENV=production \
  "$HOME/venho/growth-engine/current/.venv/bin/venho-engine" doctor
```

Nếu `Linger` chưa `yes`, bật bằng `sudo loginctl enable-linger "$USER"`, rồi kiểm tra lại. Đọc controls bằng truy vấn read-only ở Bước 3.

**PASS:** release đúng SHA; cả ba unit `active` và `enabled`; linger `yes`; doctor không có `FAIL` (WARN về expiry phải được xử lý theo runbook); production controls vẫn `DISABLED`, pause `1`.  
**FAIL/dừng:** deploy rollback, doctor có `FAIL`, unit không active, linger sai hoặc controls đổi khỏi giá trị yêu cầu. Không khởi động P4.

## 2. Kiểm provider, ngân sách và tên biến môi trường

Không dùng `env`, `printenv`, `cat` hoặc shell tracing lên file secret. Lệnh sau chỉ in tên hai biến provider cần có và trạng thái `SET/MISSING`, không in giá trị:

```bash
python3 - "$HOME/venho/secrets/growth-engine.env" <<'PY'
import re, sys
from pathlib import Path

path = Path(sys.argv[1])
values = {}
for line in path.read_text(encoding="utf-8").splitlines():
    match = re.match(r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$", line)
    if match and not line.lstrip().startswith("#"):
        values[match.group(1)] = match.group(2).strip().strip("\"'")
for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
    value = values.get(name, "")
    present = bool(value) and "REQUIRED_FROM_P0" not in value and not value.startswith("YOUR_")
    print(f"{name}: {'SET' if present else 'MISSING'}")
PY
```

Biến bắt buộc theo adapter hiện tại: `ANTHROPIC_API_KEY` cho text (`claude_social_generator`) và `OPENAI_API_KEY` cho ảnh (`gpt-image-2`). Không in hoặc gửi token. `CLAUDE_CONTENT_MODEL` là tùy chọn; nếu chưa đặt thì code dùng default. Giữ `GROWTH_IMAGE_ALTERNATIVES` tắt để giới hạn chi phí lần thử.

Đọc policy (không phải secret) và đối chiếu thủ công với chi phí/API spend đã được duyệt:

```bash
"$HOME/venho/growth-engine/current/.venv/bin/python" - <<'PY'
from pathlib import Path
import yaml
root = Path("config/projects/venho_hotel/growth")
model = yaml.safe_load((root / "model_policy.yaml").read_text())
budget = yaml.safe_load((root / "budget_policy.yaml").read_text())
costs = yaml.safe_load((root / "paid_call_costs.yaml").read_text())
print("model_policy.text_provider:", model.get("text_provider"))
print("model_policy.image_provider:", model.get("image_provider"))
print("monthly_cap:", budget.get("monthly_cap_minor"), budget.get("currency"))
for key in ("text_generation_minor", "image_generation_minor", "vision_qc_minor"):
    print(key + ":", costs.get(key))
PY
```

**PASS:** provider policy khớp implementation; cả hai API key hiện diện; monthly cap còn đủ cho lần chạy, gồm generation và QC.  
**FAIL/dừng:** biến thiếu thì ghi đúng tên biến; policy hiện tại ghi `mock` trong khi adapter gọi Anthropic/OpenAI, nên mismatch cần xử lý trước khi gọi provider; cap không đủ cũng dừng. `vision_qc_minor` hiện chỉ có trong file cost policy, chưa được tính/settle bởi P4 generation flow đang compose.

## 3. Slot 16/11, generation, variant và QC

Nếu lịch T−0 được chuyển sang 18/11 hoặc 20/11, chạy lại P4 cho đúng ngày slot mới: cập nhật ngày trong truy vấn SQLite và màn hình lịch VENHO OS; không dùng lại delivery/approval gắn với slot 16/11.

Kiểm trạng thái bằng SQLite read-only; chỉ in controls, channel flag và số lượng theo job kind/state:

```bash
"$HOME/venho/growth-engine/current/.venv/bin/python" - "$HOME/venho/state/growth-engine/growth_engine.db" <<'PY'
import sqlite3, sys
path = sys.argv[1]
db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
control = db.execute("SELECT publish_mode, global_pause FROM runtime_controls WHERE environment='production'").fetchone()
print("controls:", None if control is None else dict(control))
for row in db.execute("SELECT channel_key, enabled FROM channels WHERE environment='production' ORDER BY channel_key"):
    print("channel:", row["channel_key"], "enabled=", row["enabled"])
for row in db.execute(
    """SELECT s.id AS slot_id, s.local_date, s.local_time, c.channel_key,
              p.id AS package_id, d.id AS delivery_id, d.state,
              r.id AS revision_id, v.id AS variant_id, v.mime, v.byte_size,
              v.qc_status AS variant_qc_status, q.decision AS qc_decision
       FROM slots s JOIN slot_targets t ON t.slot_id=s.id
       JOIN channels c ON c.id=t.channel_id
       LEFT JOIN deliveries d ON d.target_id=t.id AND d.channel_id=c.id
       LEFT JOIN content_packages p ON p.id=d.package_id
       LEFT JOIN delivery_revisions r ON r.id=d.current_revision_id
       LEFT JOIN media_variants v ON v.id=r.variant_id
       LEFT JOIN qc_reports q ON q.id=r.qc_report_id
       WHERE s.local_date='2026-11-16' AND c.environment='production'
       ORDER BY c.channel_key"""
):
    print("slot_delivery:", dict(row))
for row in db.execute("SELECT kind, state, count(*) AS n FROM jobs GROUP BY kind, state ORDER BY kind, state"):
    print("jobs:", row["kind"], row["state"], row["n"])
for table in ("outbox_commands", "executions"):
    for row in db.execute(f"SELECT state, count(*) AS n FROM {table} GROUP BY state ORDER BY state"):
        print(table + ":", row["state"], row["n"])
for row in db.execute("SELECT state, count(*) AS n FROM paid_calls GROUP BY state ORDER BY state"):
    print("paid_calls:", row["state"], row["n"])
db.close()
PY
systemctl --user is-active growth-engine-worker@jobs.service
journalctl --user -u growth-engine-worker@jobs.service --since '2026-11-13 00:00:00' --no-pager
```

Lịch jobs worker là `ensure-slots` 00:10 ICT và fast lane mỗi giờ phút :40. Không chạy thêm `venho-engine worker --lane jobs` tạm thời: đó là scheduler chạy vô hạn, không phải one-shot. Nếu có supported runner ở release đã được sửa, chỉ dùng runner đó sau khi kiểm tra controls còn `DISABLED` + pause `1`; mỗi lần tạo chỉ được target `fb_hanoi` cho slot 16/11.

Trạng thái bắt buộc cho chuỗi P4:

| Bước | PASS yêu cầu |
|---|---|
| Slot/target | Slot đúng `2026-11-16 09:00 ICT`; chỉ có target `fb_hanoi`, Page ID `1124616474074140`; không tạo target Ven Hồ/IG trong dry run. |
| Generation | Một package được tạo; job generation `SUCCEEDED`; caption/facts có snapshot; budget reservation đã settle; không có job `UNKNOWN`. |
| Original/variant | Asset gốc lưu được; job `prepare_variant` `SUCCEEDED`; JPEG variant có đúng profile Facebook và hash/metadata khớp. |
| QC/revision | QC report gắn đúng variant, caption và fact snapshot; decision `PASS` hoặc `REVIEW` theo policy; job `assemble_revision` `SUCCEEDED`; delivery ở `IN_REVIEW`. |
| Safety | Runtime vẫn `DISABLED`, `global_pause=1`; không có command `AUTHORIZED`, không có webhook/Make run, không có post công khai. |

**Dừng ngay** nếu target không tồn tại, channel disabled khiến `EnsureSlots` bỏ qua, bất kỳ job nào `PENDING`/`FAILED` quá thời gian xử lý dự kiến, budget `UNKNOWN`/exceeded, variant/QC/revision thiếu hoặc controls không còn fail-closed. Không chạy lại generation nếu paid-call/job state là `UNKNOWN`.

Với source hiện tại, `channels.enabled=0` làm slot target không được tạo; không được dùng `manage-production-channels.py set-enabled` vì script yêu cầu `LIVE_MANUAL`, và không được bypass bằng SQL. Ngoài ra worker chưa xử lý `prepare_variant`/`assemble_revision` và chưa compose QC. Vì thế Bước 3 **BLOCKED** cho đến khi có supported content-only production path và các job handlers này được nối. Không ghi PASS cho phần generation → QC chỉ vì worker đang active.

## 4. Duyệt trên VENHO OS khi P4 đã đủ luồng

Đăng nhập `os.venhohotel.com` bằng tài khoản operator có quyền `dashboard:read` và `dashboard:write` (group approval endpoint yêu cầu `dashboard:write`). Mở **Publishing → Growth Engine**, xem lịch tuần 16–22/11, chọn slot 16/11 và delivery `fb_hanoi` trong danh sách **Chờ tôi duyệt**. Nếu tên menu khác hoặc trang Growth v2 chưa được deploy, đánh dấu `BLOCKED_UI`; không dùng registry legacy để duyệt thay.

Trước khi bấm duyệt, xác nhận preview ảnh, caption/facts, Page Hanoi ID, lịch `09:00 ICT`, revision và QC đúng cùng package. Bấm duyệt delivery Hanoi. Sau đó tải lại trạng thái và controls.

**PASS:** delivery hiện `APPROVED` với revision/variant/QC đang được duyệt; controls vẫn `DISABLED` + global pause `1`; không có execution `AUTHORIZED`, Make run hay bài công khai.  
**FAIL/dừng:** không thấy delivery/revision/preview, quyền thiếu, QC không đạt, hoặc controls/outbox thay đổi. Không tiếp tục đến T−0.

## 5. Kết luận và quyết định lịch

Ghi `PASS`, `FAIL` hoặc `BLOCKED` riêng cho Bước 1–4, SHA deploy, timestamp ICT, package/delivery IDs và các job state; không ghi token, URL secret, nội dung env hoặc signed URL.

- **Giữ T−0 16/11 09:00** chỉ khi cả bốn bước PASS trước tối 14/11 và approval vẫn không dispatch trong trạng thái `DISABLED`.
- Nếu bất kỳ bước nào FAIL/BLOCKED hoặc chưa có bằng chứng trước hạn, không cutover ngày 16; chọn slot 18/11 hoặc 20/11 sau khi code được sửa và dry run PASS.
- Không thay đổi legacy code/registry/literal hex trong lượt dry run. P9-T04 vẫn là gate riêng trước khi gỡ bỏ publisher legacy vĩnh viễn.
