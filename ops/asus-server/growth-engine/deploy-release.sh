#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  echo "Usage: $0 <git-sha>" >&2
  exit 2
}
fail() {
  echo "deploy-release: $*" >&2
  exit 1
}

[[ $# -eq 1 ]] || usage
[[ "$1" =~ ^[0-9a-fA-F]{7,40}$ ]] || fail "git-sha must be 7–40 hexadecimal characters"
RELEASE_SHA="${1,,}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$(git -C "$SCRIPT_DIR/../../.." rev-parse --show-toplevel 2>/dev/null)" \
  || fail "run this script from a GC2 git checkout"
REMOTE_URL="$(git -C "$SOURCE_ROOT" remote get-url origin 2>/dev/null)" \
  || fail "origin remote is not configured in the source checkout"
[[ -z "$(git -C "$SOURCE_ROOT" status --porcelain)" ]] \
  || fail "source checkout must be clean"

BASE_DIR="$HOME/venho/growth-engine"
RELEASES_DIR="$BASE_DIR/releases"
RELEASE_DIR="$RELEASES_DIR/$RELEASE_SHA"
CURRENT_LINK="$BASE_DIR/current"
STATE_DIR="$HOME/venho/state/growth-engine"
SECRETS_FILE="$HOME/venho/secrets/growth-engine.env"
USER_UNITS_DIR="$HOME/.config/systemd/user"
UNITS=(growth-engine-api.service growth-engine-worker@publish.service growth-engine-worker@jobs.service)
SWITCHED=0
PREVIOUS_TARGET=""
HAD_PREVIOUS=0

rollback_current() {
  if (( HAD_PREVIOUS )); then
    local rollback_link="$BASE_DIR/.current.rollback.$$"
    ln -s "$PREVIOUS_TARGET" "$rollback_link"
    mv -Tf "$rollback_link" "$CURRENT_LINK"
    systemctl --user restart "${UNITS[@]}" || true
  else
    rm -f "$CURRENT_LINK"
    systemctl --user stop "${UNITS[@]}" || true
  fi
  SWITCHED=0
}

on_exit() {
  local status=$?
  trap - EXIT
  if (( SWITCHED )); then
    echo "deploy-release: restoring previous current release" >&2
    rollback_current
  fi
  exit "$status"
}
trap on_exit EXIT

[[ -f "$SECRETS_FILE" ]] || fail "missing $SECRETS_FILE"
mode="$(stat -c '%a' "$SECRETS_FILE")"
[[ "$mode" == "600" ]] || fail "growth-engine.env must have mode 600 (currently $mode)"
grep -Eq '^[[:space:]]*GE_ENV=production[[:space:]]*$' "$SECRETS_FILE" \
  || fail "growth-engine.env must set GE_ENV=production"
command -v git >/dev/null 2>&1 || fail "git is required"
command -v uv >/dev/null 2>&1 || fail "uv is required"
command -v systemd-run >/dev/null 2>&1 || fail "systemd-run is required"
command -v systemctl >/dev/null 2>&1 || fail "systemctl is required"

mkdir -p "$RELEASES_DIR" "$STATE_DIR/media/originals" "$STATE_DIR/media/variants" \
  "$STATE_DIR/backup-staging" "$USER_UNITS_DIR"
if [[ -e "$RELEASE_DIR" ]]; then
  fail "release path already exists: $RELEASE_DIR"
fi

git clone --quiet --no-checkout "$REMOTE_URL" "$RELEASE_DIR"
git -C "$RELEASE_DIR" checkout --detach "$RELEASE_SHA"
actual_sha="$(git -C "$RELEASE_DIR" rev-parse HEAD)"
[[ "${actual_sha,,}" == "${RELEASE_SHA,,}" || "${actual_sha,,}" == "${RELEASE_SHA,,}"* ]] \
  || fail "checked out commit does not match requested git-sha"

(cd "$RELEASE_DIR" && uv sync --frozen --extra api --extra drive --extra gemini)

install -m 0644 "$SOURCE_ROOT/ops/asus-server/growth-engine/growth-engine-api.service" "$USER_UNITS_DIR/"
install -m 0644 "$SOURCE_ROOT/ops/asus-server/growth-engine/growth-engine-worker@.service" "$USER_UNITS_DIR/"
systemctl --user daemon-reload

run_release_cli() {
  local release="$1"
  shift
  systemd-run --user --pipe --wait --collect \
    --property="EnvironmentFile=$SECRETS_FILE" \
    --property="WorkingDirectory=$release" \
    --setenv=GE_ENV=production \
    "$release/.venv/bin/venho-engine" "$@"
}

run_release_cli "$RELEASE_DIR" migrate --check
run_release_cli "$RELEASE_DIR" doctor --pre-switch

if [[ -L "$CURRENT_LINK" ]]; then
  PREVIOUS_TARGET="$(readlink -f "$CURRENT_LINK")"
  HAD_PREVIOUS=1
elif [[ -e "$CURRENT_LINK" ]]; then
  fail "current exists but is not a symlink"
fi

next_link="$BASE_DIR/.current.next.$$"
ln -s "$RELEASE_DIR" "$next_link"
mv -Tf "$next_link" "$CURRENT_LINK"
SWITCHED=1

systemctl --user restart "${UNITS[@]}"
for unit in "${UNITS[@]}"; do
  systemctl --user is-active --quiet "$unit" || fail "$unit did not become active"
done
run_release_cli "$RELEASE_DIR" doctor

SWITCHED=0
echo "Growth Engine release ${actual_sha} is active."
