#!/usr/bin/env bash
# GC2-P0-T01 — kiểm tra host cho Growth Engine. Chỉ ĐỌC máy.
# Chạy từ xa, không cần repo trên server:
#   ssh <host> 'bash -s' < preflight-host.sh
#   ssh <host> 'bash -s -- /đường/dẫn/state' < preflight-host.sh     (đổi STATE_DIR)
# Biến tuỳ chọn: GE_RUNTIME_PY (mặc định ~/venho/growth-runtime/venho-ai-studio/.venv/bin/python)
#
# LƯU Ý khi chạy bằng `bash -s`: bash đọc chính script từ stdin, nên KHÔNG được redirect/đóng fd 0
# toàn cục. Mọi lệnh có thể đọc stdin đều gắn `</dev/null` riêng (hoặc có heredoc riêng).
set -euo pipefail

STATE_DIR="${1:-$HOME/venho/state/growth-engine}"
RUNTIME_PY="${GE_RUNTIME_PY:-$HOME/venho/growth-runtime/venho-ai-studio/.venv/bin/python}"
NA="n/a"

# Thư mục đã tồn tại gần nhất của STATE_DIR (không tạo gì).
probe_dir="$STATE_DIR"
while [ ! -d "$probe_dir" ] && [ "$probe_dir" != "/" ]; do probe_dir="$(dirname "$probe_dir")"; done

# Với mỗi interpreter: "<path>|<version>|<sqlite_version>"; thiếu thì n/a.
describe_py() {
  local py="$1" v s
  if [ -z "$py" ] || [ ! -x "$py" ]; then echo "${py:-$NA}|$NA|$NA"; return; fi
  v="$("$py" --version </dev/null 2>&1 | head -1)" || v="$NA"
  s="$("$py" -c 'import sqlite3;print(sqlite3.sqlite_version)' </dev/null 2>/dev/null)" || s="$NA"
  echo "$py|${v:-$NA}|${s:-$NA}"
}

SYS_PY="$(command -v python3 </dev/null || true)"
UV_PY=""
if command -v uv >/dev/null 2>&1; then UV_PY="$(uv python find </dev/null 2>/dev/null | head -1 || true)"; fi
PY_SYSTEM="$(describe_py "$SYS_PY")"
PY_RUNTIME="$(describe_py "$RUNTIME_PY")"
PY_UV="$(describe_py "$UV_PY")"

# WAL probe: file tạm trong thư mục tạm, luôn xoá. Ưu tiên interpreter runtime.
PROBE_PY=""
for c in "$RUNTIME_PY" "$UV_PY" "$SYS_PY"; do
  if [ -n "$c" ] && [ -x "$c" ]; then PROBE_PY="$c"; break; fi
done
WAL_PROBE="$NA"
CREATED_DIRS=""
if [ -n "$PROBE_PY" ] && [ -w "$probe_dir" ]; then
  tmpd="$(mktemp -d "$probe_dir/.ge_preflight.XXXXXX")"
  trap 'rm -rf "$tmpd"' EXIT
  WAL_PROBE="$("$PROBE_PY" - "$tmpd" <<'PY' 2>&1 || true
import os, sqlite3, sys
path = os.path.join(sys.argv[1], "probe.db")
try:
    c = sqlite3.connect(path, isolation_level=None)
    mode = c.execute("PRAGMA journal_mode=WAL").fetchone()[0]
    c.execute("PRAGMA foreign_keys=ON")
    fk = c.execute("PRAGMA foreign_keys").fetchone()[0]
    c.execute("BEGIN IMMEDIATE")
    c.execute("COMMIT")
    c.close()
    print("ok journal_mode=%s foreign_keys=%s" % (mode, fk))
except Exception as e:
    print("FAIL %s" % e)
PY
)"
  rm -rf "$tmpd"
  trap - EXIT
  [ -e "$tmpd" ] && CREATED_DIRS="$tmpd"
fi

DISK_FREE="$NA"
if [ -d "$probe_dir" ]; then DISK_FREE="$(df -Pk "$probe_dir" </dev/null | awk 'NR==2{print $4*1024}')"; fi

TZ_SYS="$( (timedatectl show -p Timezone --value </dev/null 2>/dev/null) || (readlink /etc/localtime 2>/dev/null | sed 's|.*/zoneinfo/||') || true)"
[ -n "$TZ_SYS" ] || TZ_SYS="$NA"

# Độ lệch đồng hồ (giây) so header Date của google.com — cần mạng, lỗi thì n/a.
SKEW="$NA"
if command -v curl >/dev/null 2>&1 && [ -n "$SYS_PY" ]; then
  remote_date="$(curl -sI --max-time 5 https://www.google.com </dev/null 2>/dev/null | awk -F': ' 'tolower($1)=="date"{sub(/\r$/,"",$2);print $2}' | head -1 || true)"
  if [ -n "$remote_date" ]; then
    SKEW="$("$SYS_PY" -c 'import sys,time;from email.utils import parsedate_to_datetime as p;print(int(time.time()-p(sys.argv[1]).timestamp()))' "$remote_date" 2>/dev/null || echo "$NA")"
  fi
fi

LINGER="$NA"
if command -v loginctl >/dev/null 2>&1; then
  LINGER="$(loginctl show-user "$(id -un)" -p Linger </dev/null 2>/dev/null | sed 's/Linger=//' || true)"
  [ -n "$LINGER" ] || LINGER="$NA"
fi

LISTENING=""
if command -v ss >/dev/null 2>&1; then
  LISTENING="$(ss -ltn </dev/null 2>/dev/null | awk 'NR>1{n=split($4,a,":");print a[n]}' | sort -un | tr '\n' ' ')"
elif command -v lsof >/dev/null 2>&1; then
  LISTENING="$(lsof -nP -iTCP -sTCP:LISTEN </dev/null 2>/dev/null | awk 'NR>1{n=split($9,a,":");print a[n]}' | sort -un | tr '\n' ' ')"
fi
FREE_PORTS=""; count=0
if [ -n "$LISTENING" ]; then
  for p in $(seq 8020 8040); do
    case " $LISTENING " in *" $p "*) continue;; esac
    FREE_PORTS="$FREE_PORTS $p"; count=$((count+1)); [ "$count" -ge 3 ] && break
  done
fi

have() { command -v "$1" >/dev/null 2>&1 && echo 1 || echo 0; }

# Dựng JSON bằng Python qua biến môi trường (không nội suy chuỗi vào mã).
GE_STATE_DIR="$STATE_DIR" GE_STATE_EXISTS="$([ -d "$STATE_DIR" ] && echo 1 || echo 0)" \
GE_PY_SYSTEM="$PY_SYSTEM" GE_PY_RUNTIME="$PY_RUNTIME" GE_PY_UV="$PY_UV" \
GE_WAL="$WAL_PROBE" GE_CREATED="$CREATED_DIRS" GE_DISK="$DISK_FREE" GE_TZ="$TZ_SYS" \
GE_SKEW="$SKEW" GE_LINGER="$LINGER" GE_LISTEN="$LISTENING" GE_FREE="$FREE_PORTS" \
GE_AGE="$(have age)" GE_UV="$(have uv)" GE_CF="$(have cloudflared)" \
"${SYS_PY:-python3}" -c '
import json, os
E = os.environ
def py(k):
    path, ver, sq = (E[k].split("|") + ["n/a"] * 3)[:3]
    return {"path": path, "version": ver, "sqlite_version": sq}
def ports(k):
    v = E[k].split()
    return v if v else "n/a"
print(json.dumps({
    "state_dir": E["GE_STATE_DIR"],
    "state_dir_exists": E["GE_STATE_EXISTS"] == "1",
    "python_system": py("GE_PY_SYSTEM"),
    "python_runtime": py("GE_PY_RUNTIME"),
    "python_uv": py("GE_PY_UV"),
    "wal_probe": E["GE_WAL"],
    "created_dirs": [d for d in E["GE_CREATED"].split("\n") if d],
    "disk_free_bytes": E["GE_DISK"],
    "timezone": E["GE_TZ"],
    "clock_skew_seconds": E["GE_SKEW"],
    "linger": E["GE_LINGER"],
    "listening_ports": ports("GE_LISTEN"),
    "suggested_free_ports": ports("GE_FREE"),
    "tools": {"age": E["GE_AGE"] == "1", "uv": E["GE_UV"] == "1", "cloudflared": E["GE_CF"] == "1"},
    "note": "sqlite_version phải >= 3.51.3 hoặc bản backport được xác nhận (ADR-01); wal_probe phải bắt đầu bằng ok",
}, indent=2, ensure_ascii=False))
'
