#!/usr/bin/env bash
# Auto-deploy venho-os: pull origin/main, rebuild, restart -- only when HEAD changed.
# A failed build rolls the working tree back and leaves the running service untouched.
# Installed at ~/venho/deploy-venho-os.sh (venho-os-deploy.timer, every 15 min);
# this file is the source of truth.
#
# 2026-10-22: every failure now reaches Telegram once (alert-state.sh), with
# what to do. The checkout sat on a side branch from 02/10 and refused every
# deploy for weeks without anyone knowing.
set -uo pipefail

REPO="${VENHO_OS_REPO:-$HOME/venho/venho-os}"
NODE_BIN="$HOME/.nvm/versions/node/v20.20.2/bin"
export PATH="$NODE_BIN:/usr/local/bin:/usr/bin:/bin"
# NOTE: do NOT export NODE_ENV=production here -- it makes `npm ci` skip
# devDependencies (tailwindcss, etc.) and the build fails. The running
# service gets NODE_ENV=production from its own systemd unit.
unset NODE_ENV
. "$HOME/venho/scripts/alert-state.sh"
cd "$REPO" || exit 1

log() { echo "$(date -Is) $*"; }
build() { npm ci --include=dev --no-audit --no-fund --silent && npm run build; }
fetch_fails="$ALERT_STATE_DIR/venho-os-deploy.fetch-fails"

if ! git fetch --quiet origin main; then
  log "fetch failed"
  n=$(( $(cat "$fetch_fails" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$fetch_fails"
  # Network blips are normal; four in a row (1 hour) are not.
  [ "$n" -ge 4 ] && alert_once venho-os-deploy fetch "🟠 Dashboard (venho-os): không lấy được code mới từ GitHub suốt 1 giờ ($(alert_now)). Kiểm tra mạng/SSH key của server: cd ~/venho/venho-os && git fetch origin"
  exit 1
fi
rm -f "$fetch_fails"
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)
ok() { alert_clear venho-os-deploy "✅ Dashboard (venho-os) deploy bình thường lại ($(git log --oneline -1 | cut -c1-80))."; exit 0; }
[ "$LOCAL" = "$REMOTE" ] && ok
# HEAD already contains origin/main (e.g. deliberately pinned to a branch that is ahead of main):
# nothing new to deploy -- do not rebuild + restart every tick (cause of 502 HTML windows, 2026-10-12).
git merge-base --is-ancestor "$REMOTE" "$LOCAL" && ok

if ! git merge --ff-only --quiet origin/main; then
  log "pull --ff-only refused (local changes / diverged) -- HEAD still $LOCAL"
  branch=$(git branch --show-current); ahead=$(git rev-list --count "$REMOTE..$LOCAL"); dirty=$(git status --porcelain | grep -vc '^?? \.next' || true)
  alert_once venho-os-deploy "blocked:$REMOTE" "🔴 Dashboard (venho-os) KHÔNG deploy được bản mới ($(alert_now)).
Bản mới trên main: $(git log --oneline -1 "$REMOTE" | cut -c1-70)
Server đang ở nhánh '${branch:-detached}', có $ahead commit chưa lên main, $dirty file đang sửa.
Xử lý: gộp nhánh đó vào main (PR), hoặc gộp main vào nhánh server rồi build. Đừng reset: sẽ mất commit chưa push."
  exit 1
fi
log "pulled $LOCAL -> $REMOTE, building"

if build >/tmp/venho-os-build.log 2>&1; then
  systemctl --user restart venho-os
  sleep 4
  if systemctl --user is-active --quiet venho-os; then
    log "deployed $REMOTE, service active"
    ok
  else
    log "service NOT active after restart at $REMOTE -- journalctl --user -u venho-os"
    alert_once venho-os-deploy "down:$REMOTE" "🔴 Dashboard (venho-os) KHÔNG CHẠY sau khi deploy $(git log --oneline -1 | cut -c1-60) ($(alert_now)).
Xem: journalctl --user -u venho-os -n 80"
    exit 1
  fi
else
  log "BUILD FAILED at $REMOTE (see /tmp/venho-os-build.log) -- rolling back to $LOCAL, service untouched"
  git reset --hard "$LOCAL" --quiet
  if build >/dev/null 2>&1; then
    log "rollback build ok"
    alert_once venho-os-deploy "build:$REMOTE" "🟠 Build venho-os LỖI ở $(git log --oneline -1 "$REMOTE" | cut -c1-60) ($(alert_now)). Đã quay về bản cũ, Dashboard vẫn chạy bình thường. Log: /tmp/venho-os-build.log"
  else
    log "ROLLBACK BUILD ALSO FAILED -- manual fix needed"
    alert_once venho-os-deploy "rollback:$REMOTE" "🔴 Build venho-os LỖI và build lại bản cũ CŨNG LỖI ($(alert_now)). Lần restart tới Dashboard có thể không lên. Log: /tmp/venho-os-build.log"
  fi
  exit 1
fi
