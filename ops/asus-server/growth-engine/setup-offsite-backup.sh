#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ "$-" != *x* ]] || exit 2
step=preflight
trap 'printf "OFFSITE_SETUP=FAIL STEP=%s\n" "$step" >&2' ERR
fail() { printf 'OFFSITE_SETUP=FAIL STEP=%s CODE=%s\n' "$step" "$1" >&2; exit 1; }
clock="$(TZ=Asia/Ho_Chi_Minh date +%H%M)"
(( 10#$clock < 830 || 10#$clock > 930 )) || fail publish_window_locked
{ exec 3<>/dev/tty; } 2>/dev/null || fail controlling_terminal_required
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
ops="$root/ops/asus-server/growth-engine"
current="$HOME/venho/growth-engine/current"
env_file="$HOME/venho/secrets/growth-engine.env"
[[ -f "$env_file" && ! -L "$env_file" && -O "$env_file" ]] || fail production_env_invalid
[[ "$(stat -c '%a' "$env_file")" == 600 ]] || fail production_env_permissions
python="$(command -v python3)"
"$python" -c 'import termios; termios.tcflush(3,termios.TCIFLUSH)' || fail controlling_terminal_required
printf 'Gõ OFFSITE để deploy và cấu hình backup: ' >&3
IFS= read -r -u 3 answer && [[ "$answer" == OFFSITE ]] || fail declined
exec 3>&-

step=install_age
if ! command -v age >/dev/null; then
  sudo apt-get update
  sudo apt-get install -y age
fi
age --version

step=drive_credentials
if ! systemd-run --user --wait --pipe --collect --quiet --property="EnvironmentFile=$env_file" \
  "$python" -c 'import json, os, sys
try:
    d = json.loads(os.environ.get("GOOGLE_DRIVE_TOKEN_JSON", ""))
    assert d.get("type", "authorized_user") == "authorized_user" and d.get("refresh_token")
    for f in ("client_id", "client_secret"):
        assert os.environ.get("GOOGLE_OAUTH_" + f.upper()) or d.get(f)
except (ValueError, AttributeError, AssertionError):
    sys.exit(1)
print("DRIVE_OAUTH_CONFIGURED=PASS")'; then
  # Emit variable names only. A legacy declaration does not prove refresh or scope.
  "$python" - "$HOME/venho/secrets/growth.env" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
if path.is_file():
    for key in sorted(set(re.findall(
        r"(?m)^\s*(?:export\s+)?(GOOGLE_DRIVE_TOKEN_JSON|GOOGLE_OAUTH_CLIENT_ID|GOOGLE_OAUTH_CLIENT_SECRET)\s*=",
        path.read_text(),
    ))):
        print(f"LEGACY_ENV_DECLARATION={key}")
PY
  fail provision_authorized_user_in_gc2_environment
fi

step=deploy
sha="$(git -C "$root" rev-parse HEAD)"
if [[ "$(git -C "$current" rev-parse HEAD)" != "$sha" ]]; then
  bash "$ops/deploy-release.sh" "$sha"
fi
[[ "$(git -C "$current" rev-parse HEAD)" == "$sha" ]] || fail release_mismatch
for unit in growth-engine-api.service growth-engine-worker@publish.service growth-engine-worker@jobs.service; do
  systemctl --user is-active --quiet "$unit"
done
printf 'RELEASE_SHA=%s\n' "$sha"
engine="$current/ops/asus-server/growth-engine/run-with-legacy-provider-env.sh"

step=configure_folder
if "$engine" backup offsite-check-folder >/dev/null; then
  printf 'FOLDER_ENV=ALREADY_SET\n'
else
  { exec 3<>/dev/tty; } 2>/dev/null || fail controlling_terminal_required
  "$python" -c 'import termios; termios.tcflush(3,termios.TCIFLUSH)' || fail controlling_terminal_required
  printf 'Nhập ID folder VENHO GC2 Backups, hoặc gõ CREATE để OAuth tạo folder riêng: ' >&3
  IFS= read -r -u 3 -s folder || fail folder_required
  printf '\n' >&3
  exec 3>&-
  if [[ "$folder" == CREATE ]]; then
    created="$("$engine" backup offsite-create-folder)"
    folder="$(printf '%s' "$created" | "$python" -c 'import sys,json; print(json.load(sys.stdin)["folder_id"])')"
  fi
  [[ "$folder" =~ ^[A-Za-z0-9_-]{1,150}$ && "$folder" != root ]] || fail invalid_folder
  "$engine" backup offsite-check-folder --folder "$folder" || fail folder_check_failed
  GE_OFFSITE_SETUP_FOLDER="$folder" "$python" - "$env_file" <<'PY'
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone

path = Path(sys.argv[1])
data = path.read_bytes()
entry = b"GE_BACKUP_DRIVE_FOLDER_ID=" + os.environ["GE_OFFSITE_SETUP_FOLDER"].encode("ascii")
pattern = re.compile(br"^[ \t]*(?:export[ \t]+)?GE_BACKUP_DRIVE_FOLDER_ID[ \t]*=[^\r\n]*\r?\n?$")
lines = data.splitlines(keepends=True)
revised = b"".join(line for line in lines if not pattern.fullmatch(line))
if revised and not revised.endswith(b"\n"):
    revised += b"\n"
revised += entry + b"\n"
if data != revised:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f"{path.name}.bak-offsite-{stamp}-", delete=False) as backup:
        with path.open("rb") as original:
            shutil.copyfileobj(original, backup)
        backup.flush()
        os.fsync(backup.fileno())
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".gc2-env-", delete=False) as temp:
        tmp_path = Path(temp.name)
        try:
            temp.write(revised)
            temp.flush()
            os.fsync(temp.fileno())
            os.replace(tmp_path, path)
        finally:
            tmp_path.unlink(missing_ok=True)
print("FOLDER_ENV=PASS")
PY
  unset folder created
fi

step=first_offsite_upload
upload="$("$engine" backup offsite-now)" || { printf '%s\n' "$upload"; fail upload_failed; }
printf '%s\n' "$upload"
"$engine" backup offsite-status
step=timer
install -d "$HOME/.config/systemd/user"
install -m 644 "$ops/growth-engine-backup-offsite.service" "$ops/growth-engine-backup-offsite.timer" "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user enable --now growth-engine-backup-offsite.timer
systemctl --user is-active --quiet growth-engine-backup-offsite.timer
step=doctor
doctor="$("$engine" doctor)"
[[ "$doctor" == *'| Offsite recipient | **PASS** |'* ]] || fail recipient_not_pass
[[ "$doctor" == *'| Offsite backup age | **PASS** |'* ]] || fail offsite_age_not_pass
printf 'OFFSITE_SETUP=PASS TIMER=growth-engine-backup-offsite.timer STATE=active DOCTOR_OFFSITE=PASS\n'
