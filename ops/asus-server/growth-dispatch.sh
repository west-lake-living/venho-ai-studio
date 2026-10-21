#!/usr/bin/env bash
# Server-native Growth publish scheduler (replaces GitHub Actions `schedule`,
# which started 09:00 posts at 13:18-16:34 ICT -- 2026-10-21).
#
#   growth-dispatch.sh primary   09:00 pass, --require-dispatch (nothing due = failure)
#   growth-dispatch.sh second    17:00 pass, catches posts approved after 09:00
#   growth-dispatch.sh sync      update the clone + push pending state, no dispatch
#   growth-dispatch.sh trend-scan Trend Radar scan (Google News + Gemini); Telegram
#                                 alert for new West Lake events in the fast-lane window
#   growth-dispatch.sh fast-lane  draft approved fast-lane events into the slot before
#                                 them (replaces curated drafts; still needs Duyệt)
#   growth-dispatch.sh weekly-cycle      Sunday fortnight drafting (was GitHub Actions,
#                                 which had no assets/raw reference photos -> every
#                                 post since 28/08/2026 shipped a fallback photo)
#   growth-dispatch.sh replace-rejected  regenerate rejected/expired drafts
#   growth-dispatch.sh select-image --publication-id X --option B --selected-by E
#   growth-dispatch.sh upload-image --publication-id X --file F --uploaded-by E
#                                 (Dashboard image picker; stdout is the CLI JSON only)
#
# State lives in git (PublicationRegistry JSON + growth.db). Every run starts
# from origin/main and pushes its state commit back; when someone pushed
# first, growth_state_merge.py merges by publication_id / slot_id instead of
# rebasing binary/JSON blobs. Nothing is ever re-sent to Make on retry.
set -euo pipefail

MODE="${1:-primary}"
case "$MODE" in primary|second|sync|trend-scan|fast-lane|weekly-cycle|replace-rejected|expire-stale|select-image|upload-image) ;; *) echo "unknown mode: $MODE" >&2; exit 2 ;; esac
REPO="$HOME/venho/growth-runtime/venho-ai-studio"
MERGE="$HOME/venho/scripts/growth_state_merge.py"
TELEGRAM="$HOME/venho/scripts/growth-telegram.sh"
PROJECT_DATA="data/projects/venho_hotel"
REGISTRY="$PROJECT_DATA/publishing/publication_registry.json"
DB="$PROJECT_DATA/growth/growth.db"
SNAPSHOT="$PROJECT_DATA/growth/slots_snapshot.json"
TRENDS="$PROJECT_DATA/research/trend_candidates.json"
STATE_FILES=("$REGISTRY" "$DB" "$SNAPSHOT" "$TRENDS")

LOCK_WAIT=3000
case "$MODE" in select-image|upload-image) LOCK_WAIT=90 ;; esac  # a person is waiting
# Fixed path: the Dashboard process may not have XDG_RUNTIME_DIR set, and a
# different lock file would not serialize anything.
exec 9>"/run/user/$(id -u)/venho-growth-dispatch.lock"
flock -w "$LOCK_WAIT" 9 || { echo "Growth runner is busy (weekly drafting?); try again in a few minutes" >&2; exit 75; }

cd "$REPO"
set -a; . "$HOME/venho/secrets/growth.env"; set +a
export PATH="$REPO/.venv/bin:$PATH"
git config user.name "venho-growth-bot"
git config user.email "venho-growth-bot@users.noreply.github.com"

snapshot_slots() { venho-growth slots --weeks-ahead 2 > "$SNAPSHOT.tmp" && mv "$SNAPSHOT.tmp" "$SNAPSHOT" || rm -f "$SNAPSHOT.tmp"; }

commit_state() {
  local f
  for f in "${STATE_FILES[@]}"; do [ -e "$f" ] && git add -f "$f"; done
  git add -u data/projects
  for f in "$PROJECT_DATA/growth/rotation_state.json" "$PROJECT_DATA/growth/evergreen_pool.json"; do
    [ -e "$f" ] && git add -f "$f"
  done
  # Generated copy/prompt records, like the old workflows (json/md only).
  find "$PROJECT_DATA/content" "$PROJECT_DATA/prompts" -type f \( -name "*.json" -o -name "*.md" \) -print0 2>/dev/null \
    | xargs -0 -r git add -f
  git diff --cached --quiet || git commit -q -m "chore: growth server $MODE $(date -u +%Y-%m-%dT%H%MZ)"
}

# Push local state commits; on divergence rebuild them on top of origin/main.
push_state() {
  local attempt tmp
  for attempt in 1 2 3; do
    git fetch -q origin main
    if [ "$(git rev-list --count origin/main..HEAD)" = "0" ]; then return 0; fi
    if git merge-base --is-ancestor origin/main HEAD; then
      git push -q origin HEAD:main && return 0
      continue
    fi
    echo "origin/main moved; merging state (attempt $attempt)" >&2
    tmp="$(mktemp -d)"
    cp "$REGISTRY" "$tmp/registry.json"; cp "$DB" "$tmp/growth.db"; cp "$TRENDS" "$tmp/trends.json"
    # Every other file our unpushed commits touched (generated content,
    # rotation state): ours wins after the reset.
    git diff --name-only "$(git merge-base origin/main HEAD)" HEAD -- data/projects \
      | grep -vxF -e "$REGISTRY" -e "$DB" -e "$TRENDS" -e "$SNAPSHOT" > "$tmp/files" || true
    tar -cf "$tmp/ours.tar" -T "$tmp/files" 2>/dev/null || true
    git reset -q --hard origin/main
    [ -s "$tmp/files" ] && tar -xf "$tmp/ours.tar"
    python3 "$MERGE" registry "$tmp/registry.json" "$REGISTRY" >&2
    python3 "$MERGE" db "$tmp/growth.db" "$DB" >&2
    python3 "$MERGE" trends "$tmp/trends.json" "$TRENDS" >&2
    rm -rf "$tmp"
    snapshot_slots
    commit_state
  done
  echo "state push failed after 3 attempts; local commits kept for next run" >&2
  return 1
}

# 1. Start from origin/main, never discarding unpushed state.
git fetch -q origin main
if [ "$(git rev-list --count origin/main..HEAD)" != "0" ]; then
  echo "unpushed state from a previous run; pushing it first" >&2
  push_state
fi
git reset -q --hard origin/main
if ! cmp -s pyproject.toml .venv/.pyproject.installed 2>/dev/null; then
  "$HOME/.local/bin/uv" pip install -q --python .venv/bin/python -e ".[drive,gemini]"
  cp pyproject.toml .venv/.pyproject.installed
fi

[ "$MODE" = "sync" ] && { echo "sync ok at $(git log --oneline -1)"; exit 0; }

if [ "$MODE" = "select-image" ] || [ "$MODE" = "upload-image" ]; then
  shift
  venho-growth "$MODE" "$@"
  commit_state
  push_state >&2
  exit 0
fi

if [ "$MODE" = "weekly-cycle" ] || [ "$MODE" = "replace-rejected" ]; then
  started="$(date -u +%Y-%m-%dT%H:%M:%S)"
  export GROWTH_TOPIC_IDEATION=1 GROWTH_IMAGE_ALTERNATIVES=1 ANTHROPIC_TIMEOUT_SECONDS=120 OPENAI_VISION_TIMEOUT_SECONDS=180
  set +e
  if [ "$MODE" = "weekly-cycle" ]; then
    venho-growth weekly-cycle --platform facebook --platform instagram
  else
    venho-growth replace-rejected
  fi
  gen_rc=$?
  set -e
  snapshot_slots
  commit_state
  push_rc=0; push_state || push_rc=$?
  # Never again silently: every new draft that had to fall back to a stock
  # photo is reported with its reason.
  alert="$(python3 - "$REGISTRY" "$started" <<'PY'
import json, sys
rows = json.load(open(sys.argv[1]))["publications"]
new = [r for r in rows if str(r.get("created_at", ""))[:19] >= sys.argv[2]]
fallback = [r for r in new if (r.get("content") or {}).get("image_is_fallback")]
if fallback:
    print(f"🖼️ {len(fallback)}/{len(new)} bài mới phải dùng ảnh dự phòng:")
    for r in fallback:
        print(f"• {r.get('slot_id')} {r.get('platform')}: {(r.get('content') or {}).get('image_fallback_reason')} — {str(r.get('topic'))[:60]}")
PY
)"
  [ -n "$alert" ] && { "$TELEGRAM" "$alert" || true; }
  # One album per new draft: image options + caption, picked on the Dashboard.
  venho-growth notify-image-options --since "$started" || true
  [ "$push_rc" = "0" ] || exit "$push_rc"
  exit "$gen_rc"
fi

if [ "$MODE" = "fast-lane" ]; then
  out="$(mktemp)"
  set +e
  venho-growth trend-fast-lane > "$out"
  lane_rc=$?
  set -e
  cat "$out"
  snapshot_slots
  commit_state
  push_rc=0; push_state || push_rc=$?
  alert="$(python3 - "$out" <<'PY'
import json, sys
try:
    outcomes = json.load(open(sys.argv[1])).get("outcomes", [])
except Exception:
    outcomes = []
for o in outcomes:
    if not o.get("alert"):
        continue
    name, start = o.get("event_name"), o.get("event_start")
    if o["status"] == "drafted":
        print(f"⚡ Đã soạn bài sự kiện «{name}» ({start}) vào {o.get('slot_id')}, thay {len(o.get('cancelled_publication_ids') or [])} bài curated. Cần anh Duyệt trên Dashboard.")
    elif o["status"] == "no_free_slot":
        print(f"⚠️ «{name}» ({start}): không còn slot trống trước sự kiện (các slot đã duyệt/giữ). Sự kiện sẽ quay về hàng chờ lane Thứ 7.")
    else:
        print(f"🔴 Soạn bài «{name}» lỗi, đã khôi phục bài curated: {o.get('error', '')[:300]}")
PY
)"
  [ -n "$alert" ] && { "$TELEGRAM" "$alert" || true; }
  [ "$push_rc" = "0" ] || exit "$push_rc"
  exit "$lane_rc"
fi

if [ "$MODE" = "expire-stale" ]; then
  # Was growth-expire-stale-approvals.yml (moved 2026-10-21): GitHub ran its
  # 07:15 cron 4-5 h late, and a second writer of publication_registry.json.
  venho-growth expire-stale-approvals
  venho-growth retire-stale-incidents
  commit_state
  push_state
  exit $?
fi

if [ "$MODE" = "trend-scan" ]; then
  out="$(mktemp)"
  venho-growth trend-scan > "$out"
  cat "$out"
  commit_state
  push_rc=0; push_state || push_rc=$?
  alert="$(python3 - "$out" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
events = data.get("new_fast_lane") or []
if events:
    print(f"📣 Trend Radar: {len(events)} sự kiện Hồ Tây sắp diễn ra — cần anh duyệt (Dashboard → Trend Radar).")
    for e in events:
        when = e.get("event_start") or "?"
        if e.get("event_end") and e["event_end"] != e.get("event_start"):
            when += f" → {e['event_end']}"
        print(f"\n• {e.get('event_name') or e.get('title')}\n  {when} · {e.get('venue') or 'Hồ Tây'} · {e.get('source_count') or 1} nguồn\n  {e.get('source_uri')}")
    print("\nDuyệt xong, bài sẽ thay bài curated gần nhất trước ngày diễn ra (vẫn cần Duyệt bài).")
PY
)"
  [ -n "$alert" ] && { "$TELEGRAM" "$alert" || true; }
  exit "$push_rc"
fi
[ -n "${MAKE_GROWTH_WEBHOOK_URL:-}" ] || { echo "MAKE_GROWTH_WEBHOOK_URL missing" >&2; exit 1; }

# 2. Dispatch.
args=(dispatch-due --allow-shadow --catch-up-today)
[ "$MODE" = "primary" ] && args+=(--require-dispatch)
out="$(mktemp)"
set +e
venho-growth "${args[@]}" > "$out"
dispatch_rc=$?
set -e
cat "$out"

# 3. Persist state whatever the outcome (claims/errors must be recorded).
snapshot_slots
commit_state
push_rc=0; push_state || push_rc=$?

# 4. Tell Harry what went out.
summary="$(python3 - "$out" <<'PY'
import json, sys
try:
    rows = json.load(open(sys.argv[1])).get("publications", [])
except Exception:
    rows = []
for r in rows:
    link = r.get("permalink") or ""
    print(f"• {r.get('platform')}: {r.get('status')} — {str(r.get('topic') or r.get('publication_id'))[:70]} {link}".rstrip())
PY
)"
if [ -n "$summary" ]; then
  icon="✅"; [ "$dispatch_rc" != "0" ] && icon="⚠️"
  "$TELEGRAM" "$icon Growth $(TZ=Asia/Ho_Chi_Minh date '+%H:%M %d/%m') [$MODE]
$summary" || true
fi

[ "$push_rc" = "0" ] || exit "$push_rc"
exit "$dispatch_rc"
