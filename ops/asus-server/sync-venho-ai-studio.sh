#!/usr/bin/env bash
# Fast-forward-only sync of the venho-ai-studio checkout that VENHO OS
# Dashboard shells out to (STUDIO_DIR / VENHO_PATH_OVERRIDE in
# venho-os/.env.local) against origin/main. Cron, every 5 minutes.
#
# Installed at ~/venho/scripts/sync-venho-ai-studio.sh; this file is the
# source of truth.
#
# Safe by construction:
# - --ff-only: never merges/rebases, so it can never invent a merge commit or
#   silently resolve a real conflict. A true divergence fails loudly.
# - The 4 JSON files venho-os's *-sync.ts modules write directly to disk
#   carry the git skip-worktree bit (set 2026-09-21), so git never touches
#   or flags them and this script cannot clobber a Duyệt/reject write.
#
# 2026-10-21: the checkout sat on a side branch from 17/10, every run failed
# into a log nobody read, and new research notes never arrived (Knowledge
# Facts could not be approved). So now:
# - a checkout off `main` is reported, not just "ff failed";
# - every new failure, and the recovery, goes to Telegram (once per state,
#   not every 5 minutes);
# - untracked files that origin/main now carries identically (a research
#   note the Dashboard fetched on its own, research-note-sync.ts) are
#   dropped before the merge instead of blocking it;
# - Python deps follow pyproject.toml/uv.lock, so new code does not run
#   against a venv that lacks its imports.
set -uo pipefail

REPO_DIR=/home/serveradmin/venho/03_AI_STUDIO/venho-ai-studio
LOG_FILE=/home/serveradmin/venho/scripts/sync-venho-ai-studio.log
FLAG_FILE=/home/serveradmin/venho/scripts/sync-venho-ai-studio.NEEDS_ATTENTION
TELEGRAM=/home/serveradmin/venho/scripts/growth-telegram.sh
UV=/home/serveradmin/.local/bin/uv

log() { echo "$(date -u +%FT%TZ) $*" >> "$LOG_FILE"; }

fail() {
  log "$1"
  if [ ! -e "$FLAG_FILE" ]; then
    "$TELEGRAM" "🔴 venho-ai-studio (thư mục Dashboard dùng) KHÔNG tự cập nhật được: $1
Xem: tail -30 $LOG_FILE" 2>>"$LOG_FILE" || true
  fi
  touch "$FLAG_FILE"
  exit 1
}

recovered() {
  if [ -e "$FLAG_FILE" ]; then
    rm -f "$FLAG_FILE"
    "$TELEGRAM" "✅ venho-ai-studio đã tự cập nhật lại bình thường ($(git log --oneline -1))." 2>>"$LOG_FILE" || true
  fi
}

cd "$REPO_DIR" || fail "repo dir missing: $REPO_DIR"

branch="$(git branch --show-current)"
[ "$branch" = "main" ] || fail "checkout đang ở nhánh '${branch:-detached}', không phải main"

git fetch -q origin main 2>>"$LOG_FILE" || { log "fetch failed"; exit 1; }  # network blips: no alert

BEFORE=$(git rev-parse HEAD)
AFTER=$(git rev-parse origin/main)

if [ "$BEFORE" != "$AFTER" ]; then
  # Untracked files the incoming commits add with the same bytes are copies
  # we already have; anything that differs is left for the merge to refuse.
  while IFS= read -r -d '' path; do
    if git cat-file -e "origin/main:$path" 2>/dev/null \
      && cmp -s "$path" <(git show "origin/main:$path"); then
      rm -f -- "$path" && log "dropped untracked copy of $path (now on main)"
    fi
  done < <(git ls-files --others --exclude-standard -z -- research)

  # A skip-worktree file the incoming commits also change makes git refuse
  # the ff ("local changes would be overwritten"). Since the server runner
  # commits the registry/trends several times a day (2026-10-21), that is
  # routine. The Dashboard's on-disk copy wins here -- its *-sync.ts modules
  # merge GitHub's rows in themselves on every read -- so set it aside, let
  # the ff move the index, then put it back.
  held=()
  while IFS= read -r path; do
    git diff --quiet "$BEFORE" "$AFTER" -- "$path" && continue
    cp -p -- "$path" "$path.sync-hold" || fail "không sao lưu được $path"
    git update-index --no-skip-worktree -- "$path"
    git checkout -q -- "$path"
    held+=("$path")
  done < <(git ls-files -v | sed -n 's/^S //p')

  merge_ok=1
  git merge --ff-only origin/main >>"$LOG_FILE" 2>&1 || merge_ok=0
  for path in "${held[@]}"; do
    mv -f -- "$path.sync-hold" "$path"
    git update-index --skip-worktree -- "$path"
    log "kept Dashboard copy of $path across the ff"
  done
  [ "$merge_ok" = 1 ] || fail "fast-forward ${BEFORE:0:8} -> ${AFTER:0:8} thất bại (git status trong $REPO_DIR)"
  log "synced ${BEFORE:0:8} -> ${AFTER:0:8}"
fi

stamp=.venv/.deps.installed
if ! cat pyproject.toml uv.lock 2>/dev/null | cmp -s - "$stamp"; then
  # --frozen: never rewrite the committed lock (that would block the next ff);
  # --inexact: keep packages other tools on this server installed.
  if "$UV" sync -q --frozen --inexact --extra drive --extra gemini >>"$LOG_FILE" 2>&1; then
    cat pyproject.toml uv.lock > "$stamp"
    log "deps synced"
  else
    fail "uv sync lỗi sau khi cập nhật code (thiếu thư viện Python)"
  fi
fi

recovered
exit 0
