#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

fail() {
  printf 'GROWTH_BACKEND_SWITCH=BLOCKED reason=%s\n' "$1" >&2
  exit 1
}

[[ $# == 1 && ( "$1" == v2 || "$1" == legacy ) ]] || fail 'usage: growth-backend-switch.sh v2|legacy'
[[ "$-" != *x* ]] || fail 'disable xtrace'
target="$1"
clock="$(TZ=Asia/Ho_Chi_Minh date +%H%M)"
if (( 10#$clock >= 830 && 10#$clock <= 930 )); then
  fail 'legacy publishing window 08:30–09:30 ICT'
fi

os_dir="$HOME/venho/venho-os"
env_file="$os_dir/.env.local"
[[ -f "$env_file" && ! -L "$env_file" ]] || fail 'VENHO OS .env.local is missing or is a symlink'
exec 9>"$HOME/venho/.growth-backend-switch.lock"
flock -n 9 || fail 'another Growth backend switch is running'

base='http://127.0.0.1:3000'
probe_mode() {
  curl --fail --silent --max-time 2 -o /dev/null -D - "$base/api/health/growth-backend" |
    awk 'tolower($1)=="x-venho-growth-backend:" {sub(/\r$/, "", $2); print $2}'
}
mode="$(probe_mode)" || fail 'runtime backend probe unavailable'
[[ "$mode" == legacy || "$mode" == v2 ]] || fail 'deploy VENHO OS runtime backend probe first'

# Read the same local registry used by VENHO OS and the server legacy checkout
# when present. Report only counts, never registry contents or credentials.
if ! python3 - "$HOME/venho" "$(TZ=Asia/Ho_Chi_Minh date +%F)" <<'PY'
import json
import sys
from pathlib import Path

root, today = Path(sys.argv[1]), sys.argv[2]
relative = "data/projects/venho_hotel/publishing/publication_registry.json"
paths = [
    root / "03_AI_STUDIO/venho-ai-studio" / relative,
    root / "growth-runtime/venho-ai-studio" / relative,
]
pending = set()
readable = 0
for path in paths:
    try:
        rows = json.loads(path.read_text())["publications"]
        if not isinstance(rows, list):
            continue
    except (OSError, ValueError, KeyError, TypeError):
        continue
    readable += 1
    for row in rows:
        if (isinstance(row, dict) and row.get("status") == "PENDING_APPROVAL"
                and str(row.get("slot_id", "")).startswith(f"slot-{today}-")):
            pending.add(str(row.get("publication_id") or row["slot_id"]))
if pending:
    print(f"WARN LEGACY_PENDING_APPROVAL_TODAY={len(pending)}")
elif readable:
    print("LEGACY_PENDING_APPROVAL_TODAY=0 source=local_registry")
else:
    print("WARN LEGACY_PENDING_APPROVAL_TODAY=UNKNOWN")
PY
then
  printf '%s\n' 'WARN LEGACY_PENDING_APPROVAL_TODAY=UNKNOWN' >&2
fi

backup="$(mktemp "$env_file.bak-$(date -u +%Y%m%dT%H%M%SZ).XXXXXX")" || fail 'create mode-600 backup'
if ! cp -- "$env_file" "$backup"; then
  rm -f -- "$backup"
  fail 'copy backup'
fi
printf 'ENV_BACKUP=%s\n' "${backup##*/}"

write_mode() {
  python3 - "$backup" "$env_file" "$1" <<'PY'
import os
import re
import sys
import tempfile
from pathlib import Path

source, destination = map(Path, sys.argv[1:3])
mode = sys.argv[3].encode()
lines = source.read_bytes().splitlines(keepends=True)
setting = re.compile(rb"^\s*(?:export\s+)?GROWTH_BACKEND\s*=")
quoted = re.compile(rb"""^\s*(?:export\s+)?[\w.-]+\s*=\s*(['"`])""")
ending = b"\r\n" if lines and lines[0].endswith(b"\r\n") else b"\n"
# Preserve even dotenv multiline values that contain a line resembling an assignment.
output = []
quote = None
keep_quoted = True
seen = False
for line in lines:
    if quote:
        if keep_quoted:
            output.append(line)
        if re.search(rb"(?<!\\)" + re.escape(quote), line):
            quote = None
        continue
    change = bool(setting.match(line))
    if change:
        if not seen:
            output.append(b"GROWTH_BACKEND=" + mode + ending)
            seen = True
    else:
        output.append(line)
    match = quoted.match(line)
    if match and not re.search(rb"(?<!\\)" + re.escape(match[1]), line[match.end():]):
        quote = match[1]
        keep_quoted = not change
if quote:
    sys.exit("ENV_UPDATE=BLOCKED reason=unterminated_quoted_value")
if not seen:
    if output and not output[-1].endswith(b"\n"):
        output.append(ending)
    output.append(b"GROWTH_BACKEND=" + mode + ending)
fd, temp = tempfile.mkstemp(dir=destination.parent, prefix=".growth-backend-")
try:
    with os.fdopen(fd, "wb") as stream:
        stream.writelines(output)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, destination)
finally:
    Path(temp).unlink(missing_ok=True)
PY
}

restart_and_check() {
  local requested="$1" current login attempt
  systemctl --user restart venho-os.service || return 1
  for attempt in {1..20}; do
    if systemctl --user is-active --quiet venho-os.service &&
       login="$(curl --fail --silent --max-time 2 -o /dev/null -w '%{http_code}' "$base/login")" &&
       [[ "$login" == 200 ]] &&
       current="$(probe_mode)" && [[ "$current" == "$requested" ]]; then
      printf 'VENHO_OS=healthy GROWTH_BACKEND=%s\n' "$requested"
      return 0
    fi
    sleep 1
  done
  return 1
}

rollback() {
  local status=$?
  trap - EXIT INT TERM HUP
  if (( status != 0 )); then
    if write_mode legacy && restart_and_check legacy; then
      printf '%s\n' 'GROWTH_BACKEND_ROLLBACK=PASS' >&2
    else
      printf '%s\n' 'GROWTH_BACKEND_ROLLBACK=FAILED' >&2
    fi
  fi
  exit "$status"
}
trap rollback EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP

write_mode "$target" || fail 'update .env.local'
restart_and_check "$target" || fail 'restart or runtime probe'
