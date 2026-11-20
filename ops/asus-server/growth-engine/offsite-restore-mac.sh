#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ "$-" != *x* ]] || exit 2
step=preflight
trap 'printf "OFFSITE_RESTORE=FAIL STEP=%s\n" "$step" >&2' ERR
fail() { printf 'OFFSITE_RESTORE=FAIL STEP=%s CODE=%s\n' "$step" "$1" >&2; exit 1; }
clock="$(TZ=Asia/Ho_Chi_Minh date +%H%M)"
(( 10#$clock < 830 || 10#$clock > 930 )) || fail publish_window_locked
[[ $# == 2 && -f "$1" && "$2" =~ ^[0-9a-f]{64}$ ]] || fail supply_download_and_verified_sha256
archive="$1"
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
for cmd in age age-keygen pbpaste pbcopy python3; do command -v "$cmd" >/dev/null || fail missing_tool; done
{ exec 3<>/dev/tty; } 2>/dev/null || fail controlling_terminal_required
step=checksum
recipient="$(PYTHONPATH="$root" python3 - "$archive" "$2" "$root" <<'PY'
import sys
from pathlib import Path
from growth_engine.adapters.outbound.backup.offsite import _checksums, load_recipient
if _checksums(Path(sys.argv[1]))[1] != sys.argv[2]:
    sys.exit("OFFSITE_DOWNLOAD_CHECKSUM=FAIL")
print(load_recipient(Path(sys.argv[3]))[0])
PY
)"
work="$(mktemp -d)"
unset identity
trap 'unset identity; rm -rf -- "$work"' EXIT
step=clipboard
python3 -c 'import termios; termios.tcflush(3, termios.TCIFLUSH)' || fail controlling_terminal_required
printf 'Copy password từ mục VENHO GC2 backup (age) trong Passwords rồi nhấn Enter: ' >&3
IFS= read -r -u 3 answer && [[ -z "$answer" ]] || fail declined
clipboard_ok=0
identity="$(pbpaste)" && clipboard_ok=1
pbcopy </dev/null
(( clipboard_ok )) || fail clipboard_read_failed
exec 3>&-
# Process substitutions use pipes. Reading the identity with built-in printf
# avoids putting it in a process argument or an on-disk file.
step=verify_identity
matched="$(age-keygen -y <(printf '%s\n' "$identity") 2>/dev/null)" || fail invalid_age_identity
[[ "$matched" == "$recipient" ]] || fail recipient_mismatch
step=decrypt
age -d -i <(printf '%s\n' "$identity") -o "$work/backup.tar.gz" -- "$archive" 2>/dev/null || fail decryption_failed
unset identity
step=restore_checks
PYTHONPATH="$root" python3 - "$work" <<'PY'
import sys
import time
from pathlib import Path
from growth_engine.adapters.outbound.backup.restore import RestoreBackup

work = Path(sys.argv[1])
try:
    result = RestoreBackup().restore_archive(
        archive=work / "backup.tar.gz", target=work / "restore", now_ms=time.time_ns() // 1_000_000,
    )
    if result.dispatch_epochs_rotated < 1:
        raise ValueError
except Exception:
    sys.exit("OFFSITE_RESTORE=FAIL STEP=restore_checks")
print("OFFSITE_RESTORE=PASS DOWNLOAD_SHA256=PASS INTEGRITY=PASS FOREIGN_KEYS=PASS MEDIA_MANIFEST=PASS")
PY
