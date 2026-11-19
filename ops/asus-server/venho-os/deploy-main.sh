#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

repo="$HOME/venho/venho-os"
unit=venho-os.service
timer=venho-os-deploy.timer
deploy_unit=venho-os-deploy.service
health=/api/health/growth-backend
base=http://127.0.0.1:3000
required=5c684b3eb8419109d9c00900d52a8148c2704bd5
export PATH="$HOME/.nvm/versions/node/v20.20.2/bin:$PATH"
unset NODE_ENV

fail() { printf 'DEPLOY_OS=BLOCKED step=%s\n' "$*" >&2; exit 1; }
clock="$(TZ=Asia/Ho_Chi_Minh date +%H%M)"
(( 10#$clock < 830 || 10#$clock > 930 )) || fail '08:30–09:30 ICT'

cd "$repo"
exec 9>"$HOME/venho/.growth-backend-switch.lock"
flock -n 9 || fail 'Growth backend switch or manual deploy already running'
tmp="$(mktemp -d)"
timer_before=unknown
restore_timer=0
mutating=0
step=preflight

probe() {
  local expected_health="$1"
  login_http="$(curl -sS --max-time 3 -o /dev/null -w '%{http_code}' "$base/login" 2>/dev/null)" || return 1
  health_http="$(curl -sS --max-time 3 -o /dev/null -D "$tmp/headers" -w '%{http_code}' "$base$health" 2>/dev/null)" || return 1
  backend="$(awk 'tolower($1)=="x-venho-growth-backend:" {sub(/\r$/, "", $2); print $2}' "$tmp/headers")"
  [[ "$login_http" == 200 && "$health_http" == "$expected_health" ]] || return 1
  if [[ "$expected_health" == 204 ]]; then
    [[ "$backend" == legacy ]] || return 1
  else
    backend=unavailable
  fi
}

restore_checkout() {
  git -c core.hooksPath=/dev/null switch --quiet --no-overwrite-ignore --detach "$old" || return 1
  git update-ref refs/heads/main "$local_main" "$(git rev-parse main)" || return 1
  if [[ -n "$old_branch" ]]; then
    git -c core.hooksPath=/dev/null switch --quiet --no-overwrite-ignore "$old_branch" || return 1
  fi
}

restart_and_verify() {
  systemctl --user restart "$unit" || return 1
  for ((attempt=0; attempt<30; attempt++)); do
    if systemctl --user is-active --quiet "$unit" && probe "$1"; then return 0; fi
    sleep 2
  done
  return 1
}

build() {
  # Keep dependency/build output private. It may include application output.
  npm ci --include=dev >"$tmp/build.log" 2>&1 &&
    npm run build >>"$tmp/build.log" 2>&1
}

cleanup() {
  local status=$?
  trap - EXIT INT TERM HUP
  if (( status != 0 && mutating )); then
    printf 'DEPLOY_OS=FAILED step=%s\n' "$step" >&2
    # Leave the automatic timer stopped after rollback so it cannot immediately deploy the failed release.
    restore_timer=0
    systemctl --user stop "$timer" || true
    if restore_checkout && build && restart_and_verify "$old_health"; then
      printf 'ROLLED_BACK HEAD=%s BACKEND=%s HEALTH_HTTP=%s LOGIN_HTTP=%s AUTO_DEPLOY_TIMER=stopped\n' \
        "$old" "$backend" "$health_http" "$login_http"
    else
      printf 'ROLLBACK_FAILED expected_HEAD=%s AUTO_DEPLOY_TIMER=stopped\n' "$old" >&2
    fi
  elif (( status != 0 )); then
    printf 'DEPLOY_OS=STOPPED step=%s\n' "$step" >&2
  fi
  if (( restore_timer )) && ! systemctl --user start "$timer"; then
    printf 'AUTO_DEPLOY_TIMER=RESTORE_FAILED\n' >&2
    status=1
  fi
  timer_after="$(systemctl --user show "$timer" -p ActiveState --value)" || timer_after=unknown
  printf 'AUTO_DEPLOY_TIMER=%s BEFORE=%s AFTER=%s\n' "$timer" "$timer_before" "$timer_after"
  rm -rf -- "$tmp"
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM HUP

timer_before="$(systemctl --user show "$timer" -p ActiveState --value)"
case "$timer_before" in
  active|inactive|failed) ;;
  *) fail 'automatic deploy timer is transitioning or unavailable' ;;
esac
if [[ "$timer_before" == active ]]; then
  restore_timer=1
  systemctl --user stop "$timer"
fi
deploy_state="$(systemctl --user show "$deploy_unit" -p ActiveState --value)"
[[ "$deploy_state" == inactive || "$deploy_state" == failed ]] || fail 'automatic deploy still running'
[[ -z "$(git status --porcelain --untracked-files=no -- . ':(exclude).env.local')" ]] || fail 'tracked checkout has changes'
[[ -f .env.local && ! -L .env.local ]] || fail '.env.local missing or symlink'
[[ -z "$(git ls-files -- .env.local)" ]] || fail '.env.local is tracked'
# The existing endpoint may be absent on the pre-deploy commit.
old="$(git rev-parse HEAD)"
old_branch="$(git symbolic-ref -q --short HEAD || true)"
old_health=404
if git cat-file -e "$old:src/app/api/health/growth-backend/route.ts" 2>/dev/null; then old_health=204; fi
printf 'OLD_HEAD=%s\n' "$old"

step=fetch
git -c core.hooksPath=/dev/null fetch --quiet origin refs/heads/main:refs/remotes/origin/main
new="$(git rev-parse origin/main)"
git merge-base --is-ancestor "$required" "$new" || fail 'chưa merge PR'

finish() {
  step=restore_timer
  if (( restore_timer )); then
    systemctl --user start "$timer"
    restore_timer=0
  fi
  printf 'DEPLOY_OS=PASS RESULT=%s OLD_HEAD=%s NEW_HEAD=%s BACKEND=%s HEALTH_HTTP=%s LOGIN_HTTP=%s\n' \
    "$1" "$old" "$new" "$backend" "$health_http" "$login_http"
}

if [[ "$old" == "$new" ]]; then
  step=verify_current
  systemctl --user is-active --quiet "$unit" && probe 204 || fail 'current service or legacy backend is unhealthy'
  finish already_current
  exit 0
fi

probe "$old_health" || fail 'current service or legacy backend is unhealthy'
git merge-base --is-ancestor "$old" "$new" || fail 'current HEAD cannot fast-forward'
local_main="$(git rev-parse main)"
git merge-base --is-ancestor "$local_main" "$old" || fail 'local main conflicts with the running checkout'
if git cat-file -e "$new:.env.local" 2>/dev/null ||
   git cat-file -e "$local_main:.env.local" 2>/dev/null; then
  fail '.env.local is tracked by a deploy commit'
fi
# Load the project dotenv with Next's parser. Require the effective mode to remain legacy.
node -e '
  require("@next/env").loadEnvConfig(process.cwd(), false, {info(){}, error(){}});
  const mode = process.env.GROWTH_BACKEND;
  process.exit(!mode || mode === "legacy" ? 0 : 1);
' >"$tmp/env-check.log" 2>&1 || fail 'effective GROWTH_BACKEND must be legacy'

step=path_collision_check
git read-tree --dry-run -m -u "$old" "$new" || fail 'local paths collide with origin/main'
step=checkout
git -c core.hooksPath=/dev/null switch --quiet --no-overwrite-ignore main
mutating=1
step=fast_forward
git -c core.hooksPath=/dev/null merge --quiet --ff-only --no-overwrite-ignore "$new"
step=build
build
step=restart_probe
restart_and_verify 204
finish deployed
