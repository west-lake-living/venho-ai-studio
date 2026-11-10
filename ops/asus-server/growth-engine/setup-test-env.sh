#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  printf 'setup-test-env: %s\n' "$*" >&2
  exit 1
}

[[ "$-" != *x* ]] || fail "disable shell xtrace before provisioning TEST secrets"
: "${HOME:?HOME must be set}"

SECRETS_DIR="$HOME/venho/secrets"
TEST_STATE_DIR="$HOME/venho/state/growth-engine-test"
ENV_FILE="$SECRETS_DIR/growth-engine-test.env"
MAKE_BEARERS_FILE="$SECRETS_DIR/growth-engine-test.make-bearers.tmp"
LOCK_DIR="$SECRETS_DIR/.growth-engine-test-env.lock"

file_mode() {
  python3 - "$1" <<'PY'
import os
import stat
import sys

print(f"{stat.S_IMODE(os.stat(sys.argv[1]).st_mode):03o}")
PY
}

[[ ! -L "$HOME/venho" && ! -L "$HOME/venho/secrets" && ! -L "$HOME/venho/state" \
  && ! -L "$TEST_STATE_DIR" && ! -L "$TEST_STATE_DIR/media" \
  && ! -L "$ENV_FILE" && ! -L "$MAKE_BEARERS_FILE" && ! -L "$LOCK_DIR" ]] \
  || fail "TEST or shared state paths must not be symlinks"
if [[ -e "$SECRETS_DIR" ]]; then
  [[ -d "$SECRETS_DIR" ]] || fail "secrets path is not a directory"
  [[ "$(file_mode "$SECRETS_DIR")" == "700" ]] || fail "secrets directory must already have mode 700"
else
  install -d -m 700 "$SECRETS_DIR"
fi
install -d -m 700 "$TEST_STATE_DIR" "$TEST_STATE_DIR/media"
chmod 700 "$TEST_STATE_DIR" "$TEST_STATE_DIR/media"

mkdir "$LOCK_DIR" 2>/dev/null || fail "another setup run holds the TEST env lock"
work_dir=""
cleanup() {
  if [[ -n "$work_dir" && -d "$work_dir" ]]; then rm -rf "$work_dir"; fi
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [[ -e "$ENV_FILE" ]]; then
  [[ "$(file_mode "$ENV_FILE")" == "600" ]] || fail "TEST env exists but is not mode 600; fix permissions before retrying"
  if [[ -e "$MAKE_BEARERS_FILE" ]]; then
    [[ "$(file_mode "$MAKE_BEARERS_FILE")" == "600" ]] || fail "Make bearer handoff exists but is not mode 600"
    printf 'TEST env already exists; secrets were not rotated. Copy the private Make bearer handoff, then delete it: %s\n' "$MAKE_BEARERS_FILE"
  else
    printf 'TEST env already exists; secrets were not rotated or recreated. Make bearer handoff is absent: %s\n' "$MAKE_BEARERS_FILE"
  fi
  exit 0
fi

[[ ! -e "$MAKE_BEARERS_FILE" ]] || fail "orphan Make bearer handoff exists without TEST env; inspect and remove it before retrying"

work_dir="$(mktemp -d "$SECRETS_DIR/.growth-engine-test.XXXXXX")"
chmod 700 "$work_dir"
python3 - "$work_dir/growth-engine-test.env" "$work_dir/growth-engine-test.make-bearers.tmp" "$TEST_STATE_DIR" <<'PY'
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
handoff_path = Path(sys.argv[2])
state_root = Path(sys.argv[3])

principals = (
    ("make-fb-hanoi", "GE_TEST_BEARER_FB_HANOI"),
    ("make-fb-venho", "GE_TEST_BEARER_FB_VENHO"),
    ("make-ig", "GE_TEST_BEARER_IG"),
)
bearers = {principal: secrets.token_urlsafe(48) for principal, _ in principals}
service_tokens = ",".join(
    f"{principal}:{hashlib.sha256(bearers[principal].encode('utf-8')).hexdigest()}"
    for principal, _ in principals
)
key_id = "test-" + secrets.token_hex(4)
capability_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")

environment = {
    "GE_ENV": "test",
    "GE_DB_PATH": str(state_root / "growth_engine.db"),
    "GE_MEDIA_ROOT": str(state_root / "media"),
    "GE_PUBLIC_BASE_URL": "https://ge-test.venhohotel.com",
    "GE_CAPABILITY_KEYS": f"{key_id}:{capability_key}",
    "GE_SERVICE_TOKENS": service_tokens,
}

def write_private(path: Path, content: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(content)
    os.chmod(path, 0o600)

write_private(env_path, "".join(f"{key}={value}\n" for key, value in environment.items()))
handoff = "# Copy the bearer values into the matching Make TEST HTTP modules, then delete this file.\n"
handoff += "".join(f"{variable}={bearers[principal]}\n" for principal, variable in principals)
write_private(handoff_path, handoff)
PY

mv "$work_dir/growth-engine-test.make-bearers.tmp" "$MAKE_BEARERS_FILE"
if ! mv "$work_dir/growth-engine-test.env" "$ENV_FILE"; then
  rm -f "$MAKE_BEARERS_FILE"
  fail "could not install TEST env file"
fi
chmod 600 "$ENV_FILE" "$MAKE_BEARERS_FILE"

printf 'Created TEST env (mode 600): %s\n' "$ENV_FILE"
printf 'Created temporary Make bearer handoff (mode 600): %s\n' "$MAKE_BEARERS_FILE"
printf 'Copy bearer values into Make TEST, then delete the handoff file. Reruns do not rotate or recreate secrets.\n'
