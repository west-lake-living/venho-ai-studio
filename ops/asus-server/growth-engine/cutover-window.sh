#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ "$-" != *x* ]] || exit 2
PREP_DATE=2026-11-25
CUTOVER_DATE=2026-11-26
FIRST_SLOT=2026-11-27
GROUP_SLOT=2026-11-28
EXPAND_DATE=2026-11-27
RESUME_THREE_DATE=2026-11-27
PREVIOUS_CUTOVER_DATE=2026-11-24
BACKUP_DATE=2026-11-20

root="$HOME/venho/growth-engine/current"
ops="$root/ops/asus-server/growth-engine"
venv="$root/.venv/bin"
engine="$ops/run-with-legacy-provider-env.sh"
env_file="$HOME/venho/secrets/growth-engine.env"
evidence="$HOME/venho/state/growth-engine/cutover-${CUTOVER_DATE//-/}"
legacy="$HOME/venho/growth-runtime/venho-ai-studio"
os_timer=venho-os-deploy.timer
os_timer_state="$evidence/venho-os-deploy.timer.state"
os_freeze_commit=dd236e53fd153278daa7f846cb11ff3a2e7d52ca
insights="$HOME/venho/state/growth-reports/insights.db"
legacy_repo=west-lake-living/venho-ai-studio
legacy_workflows=(growth-publish-scheduler.yml growth-daily-cycle.yml growth-replace-rejected.yml growth-expire-stale-approvals.yml)
names=(0900 1700 weekly-cycle replace-rejected trend-scan fast-lane expire-stale)
instances=(primary second weekly-cycle replace-rejected trend-scan fast-lane expire-stale)
fail() { printf 'CUTOVER=BLOCKED reason=%s\n' "$1" >&2; exit 1; }
read_clock() {
  timestamp="$(TZ=Asia/Ho_Chi_Minh date '+%F %H%M')"
  read -r today clock <<< "$timestamp"
  (( 10#$clock < 830 || 10#$clock > 930 )) || fail 'publish window 08:30–09:30 ICT'
}
read_clock
require_group_window() {
  read_clock
  [[ "$today" == "$1" && "$timestamp" > "$FIRST_SLOT 0930" && "$timestamp" < "$GROUP_SLOT 0830" ]] \
    || fail wrong_group_window
}
validate_schedule() {
  "$venv/python" - "$root/config/projects/venho_hotel/growth/cadence_policy.yaml" \
    "$PREP_DATE" "$CUTOVER_DATE" "$FIRST_SLOT" "$GROUP_SLOT" "$EXPAND_DATE" "$RESUME_THREE_DATE" <<'PY'
import sys
from datetime import date
from pathlib import Path

import yaml

policy = yaml.safe_load(Path(sys.argv[1]).read_text())
prep, cutover, first, group, expand, resume = map(date.fromisoformat, sys.argv[2:])
days = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
cadence = {slot["day"] for slot in policy["slots"]}
if not (
    policy["publish_time"] == "09:00"
    and policy["timezone"] == "Asia/Ho_Chi_Minh"
    and all(days[slot.weekday()] in cadence for slot in (first, group))
    and prep < cutover < first < group
    and first <= expand <= resume <= group
):
    sys.exit(1)
PY
}
confirm() {
  { exec 3<>/dev/tty; } 2>/dev/null || fail controlling_terminal_required
  "$venv/python" -c 'import termios; termios.tcflush(3, termios.TCIFLUSH)' || fail controlling_terminal_required
  printf 'Gõ %s để xác nhận: ' "$1" >&3
  local answer
  IFS= read -r -u 3 answer && [[ "$answer" == "$1" ]] || fail declined
  exec 3>&-
}
control() {
  "$engine" cutover-ops "$1" --date "$2" --operator-confirmed "$1:$2"
}
channel() {
  systemd-run --user --pipe --wait --collect --quiet --property="EnvironmentFile=$env_file" \
    "$venv/python" "$ops/manage-production-channels.py" set-enabled --channel "$@"
}
legacy_write_status() {
  curl --silent --max-time 3 -X POST -o /dev/null -w '%{http_code}' \
    http://127.0.0.1:3000/api/v1/studio/growth/approve-group
}
os_timer_active_state() {
  systemctl --user show "$os_timer" -p ActiveState --value
}
hold_os_timer() {
  local prior
  if [[ ! -f "$os_timer_state" ]]; then
    prior="$(os_timer_active_state)"
    [[ "$prior" == active || "$prior" == inactive ]] || fail unexpected_os_deploy_timer_state
    printf '%s\n' "$prior" > "$os_timer_state"
  fi
  systemctl --user stop "$os_timer"
  require_os_timer_held
  printf 'OS_DEPLOY_TIMER=%s BEFORE=%s AFTER=inactive\n' "$os_timer" "$(< "$os_timer_state")"
}
require_os_timer_held() {
  [[ -f "$os_timer_state" && "$(os_timer_active_state)" == inactive ]] || fail os_deploy_timer_not_held
  [[ "$(systemctl --user show venho-os-deploy.service -p ActiveState --value)" =~ ^(inactive|failed)$ ]] \
    || fail os_deploy_service_not_drained
}
restore_os_timer() {
  local prior current
  prior="$(< "$os_timer_state")"
  if [[ "$prior" == active ]]; then systemctl --user start "$os_timer"; fi
  current="$(os_timer_active_state)"
  [[ "$current" == "$prior" ]] || fail os_deploy_timer_restore_mismatch
  printf 'OS_DEPLOY_TIMER=%s BEFORE=%s AFTER=%s\n' "$os_timer" "$prior" "$current"
}
legacy_clear() {
  local unit active enabled mode
  for mode in "${names[@]}"; do
    unit="venho-growth-publish-$mode.timer"
    [[ "$mode" == 0900 || "$mode" == 1700 ]] || unit="venho-growth-$mode.timer"
    active="$(systemctl --user show "$unit" -p ActiveState --value)"
    enabled="$(systemctl --user show "$unit" -p UnitFileState --value)"
    [[ "$active" == inactive && "$enabled" == disabled ]] || fail "${unit}_not_stopped"
  done
  for mode in "${instances[@]}"; do
    active="$(systemctl --user show "venho-growth-publish@$mode.service" -p ActiveState --value)"
    [[ "$active" == inactive ]] || fail "legacy_service_${mode}_not_drained"
  done
  local runs workflow registry remote_blob
  local drained_pattern=$'^0(\n0)*$'
  [[ "$(legacy_write_status)" == 503 ]] || fail legacy_dashboard_write_not_frozen
  for workflow in "${legacy_workflows[@]}"; do
    [[ "$(gh api "repos/$legacy_repo/actions/workflows/$workflow" --jq .state)" == disabled_manually ]] \
      || fail "${workflow}_not_disabled"
    runs="$(gh api --paginate "repos/$legacy_repo/actions/workflows/$workflow/runs?per_page=100" \
      --jq '[.workflow_runs[] | select(.status != "completed")] | length')" || fail legacy_workflow_query_failed
    [[ "$runs" =~ $drained_pattern ]] || fail "${workflow}_runs_not_drained"
  done
  registry=data/projects/venho_hotel/publishing/publication_registry.json
  git -C "$legacy" fetch --quiet origin main >/dev/null 2>&1 || fail legacy_registry_fetch_failed
  remote_blob="$(git -C "$legacy" rev-parse "FETCH_HEAD:$registry" 2>/dev/null)" || fail legacy_remote_registry_missing
  [[ "$(git -C "$legacy" hash-object -- "$legacy/$registry")" == "$remote_blob" ]] || fail 'legacy local registry differs from GitHub'
  case "$1" in
    check) "$venv/python" "$ops/legacy-cutover-snapshot.py" "$legacy" "$evidence" --check --require-frozen --insights "$insights" --first-slot "$FIRST_SLOT" ;;
    snapshot) "$venv/python" "$ops/legacy-cutover-snapshot.py" "$legacy" "$evidence" --require-frozen --insights "$insights" --first-slot "$FIRST_SLOT" ;;
  esac
}
validate_schedule || fail invalid_cutover_schedule
case "${1:-}" in
  friday-backup)
    if [[ "$today" != "$BACKUP_DATE" ]] || (( 10#$clock <= 930 )); then fail wrong_backup_date_or_time; fi ;;
  t2)
    if [[ "$today" != "$PREP_DATE" ]] || (( 10#$clock <= 930 )); then fail wrong_preparation_date_or_time; fi ;;
  stop-legacy|snapshot|switch-and-epoch|rotate|dry-run|live)
    [[ "$today" == "$CUTOVER_DATE" ]] || fail wrong_cutover_date ;;
  expand) require_group_window "$EXPAND_DATE" ;;
  resume-three) require_group_window "$RESUME_THREE_DATE" ;;
  rollback-restore)
    [[ "$today" == "$CUTOVER_DATE" ]] || fail rollback_requires_separate_catch_up_review ;;
esac
if [[ -d "${evidence%/*}/cutover-${PREVIOUS_CUTOVER_DATE//-/}" ]]; then
  printf 'CUTOVER_WARNING=prior_evidence_ignored DATE=%s\n' "$PREVIOUS_CUTOVER_DATE" >&2
fi
mkdir -p -- "$evidence"
chmod 700 "$evidence"
exec 9>"$evidence/.operator.lock"
flock -n 9 || fail another_cutover_operation


case "${1:-}" in
  friday-backup)
    confirm FIRST_BACKUP
    install -d "$HOME/.config/systemd/user"
    install -m 644 "$ops/growth-engine-backup.service" "$ops/growth-engine-backup.timer" "$HOME/.config/systemd/user/"
    systemctl --user daemon-reload
    systemctl --user start growth-engine-backup.service
    "$engine" restore-rehearsal
    systemctl --user enable --now growth-engine-backup.timer
    systemctl --user is-active --quiet growth-engine-backup.timer
    doctor="$("$engine" doctor)"
    [[ "$doctor" == *'| Backup age | **PASS** |'* ]] || fail doctor_backup_age_not_pass
    printf 'DOCTOR_BACKUP_AGE=PASS TIMER=growth-engine-backup.timer STATE=active\n'
    ;;
  t2)
    "$engine" cutover-ops generation-clear --date "$FIRST_SLOT"
    "$engine" cutover-ops backup-fresh --date "$FIRST_SLOT"
    confirm "PREPARE_${FIRST_SLOT##*-}"
    channel fb_hanoi --enable --prepare-only
    "$engine" prepare-slot --date "$FIRST_SLOT" --channel fb_hanoi
    ;;
  stop-legacy)
    "$engine" cutover-ops disabled-preflight --date "$FIRST_SLOT"
    "$venv/python" "$ops/legacy-cutover-snapshot.py" "$legacy" "$evidence" --check \
      --insights "$insights" --first-slot "$FIRST_SLOT"
    printf '%s\n' 'Chỉ xác nhận sau khi Make 5868920 Inactive, đã drain History/queue và đã tạm dừng mọi callback legacy ngoài repo.'
    confirm STOP_LEGACY
    "$venv/python" "$ops/legacy-cutover-snapshot.py" "$legacy" "$evidence" --record-frozen \
      --first-slot "$FIRST_SLOT"
    [[ ! -e "$evidence/legacy-timers.tsv" ]] || fail 'legacy timer state already saved'
    tmp="$(mktemp "$evidence/.timers.XXXXXX")"
    trap 'rm -f -- "$tmp"' EXIT
    for mode in "${names[@]}"; do
      unit="venho-growth-publish-$mode.timer"
      [[ "$mode" == 0900 || "$mode" == 1700 ]] || unit="venho-growth-$mode.timer"
      enabled="$(systemctl --user show "$unit" -p UnitFileState --value)"
      active="$(systemctl --user show "$unit" -p ActiveState --value)"
      [[ "$enabled" == enabled || "$enabled" == disabled ]] || fail "${unit}_unexpected_enablement"
      [[ "$active" == active || "$active" == inactive ]] || fail "${unit}_unexpected_activity"
      printf '%s\t%s\t%s\n' "$unit" "$enabled" "$active" >> "$tmp"
    done
    workflow_tmp="$(mktemp "$evidence/.workflows.XXXXXX")"
    trap 'rm -f -- "$tmp" "$workflow_tmp"' EXIT
    for workflow in "${legacy_workflows[@]}"; do
      workflow_state="$(gh api "repos/$legacy_repo/actions/workflows/$workflow" --jq .state)"
      [[ "$workflow_state" == active || "$workflow_state" == disabled_manually ]] || fail unexpected_legacy_workflow_state
      printf '%s\t%s\n' "$workflow" "$workflow_state" >> "$workflow_tmp"
    done
    git -C "$HOME/venho/venho-os" merge-base --is-ancestor "$os_freeze_commit" HEAD 2>/dev/null \
      || fail legacy_write_guard_not_deployed
    hold_os_timer
    git -C "$HOME/venho/venho-os" merge-base --is-ancestor "$os_freeze_commit" HEAD 2>/dev/null \
      || fail legacy_write_guard_not_deployed
    [[ "$(legacy_write_status)" == 401 ]] || fail legacy_backend_probe_unexpected
    mv -- "$tmp" "$evidence/legacy-timers.tsv"
    mv -- "$workflow_tmp" "$evidence/legacy-workflows.tsv"
    while IFS=$'\t' read -r workflow workflow_state; do
      if [[ "$workflow_state" == active ]]; then
        gh workflow disable "$workflow" --repo "$legacy_repo" >/dev/null
      fi
    done < "$evidence/legacy-workflows.tsv"
    while IFS=$'\t' read -r unit enabled active; do
      systemctl --user disable --now "$unit"
    done < "$evidence/legacy-timers.tsv"
    bash "$root/ops/asus-server/venho-os/growth-backend-switch.sh" v2
    legacy_clear check
    ;;
  snapshot)
    require_os_timer_held
    confirm MAKE_DRAINED
    legacy_clear snapshot
    systemctl --user start growth-engine-backup.service
    "$engine" restore-rehearsal
    "$engine" legacy-import --dry-run --source "$evidence/legacy-snapshot/source" --report "$evidence/legacy-dry-run.md" >"$evidence/legacy-dry-run.log" 2>&1 || fail legacy_import_dry_run_failed
    printf 'LEGACY_IMPORT_DRY_RUN=PASS\n'
    ;;
  switch-and-epoch)
    require_os_timer_held
    legacy_clear snapshot
    [[ -s "$evidence/legacy-dry-run.md" ]] || fail missing_legacy_delta_review
    confirm SWITCH_V2
    systemctl --user start growth-engine-backup.service
    "$engine" restore-rehearsal
    control epoch "$FIRST_SLOT"
    ;;
  rotate)
    require_os_timer_held
    [[ "$(legacy_write_status)" == 503 ]] || fail legacy_dashboard_write_not_frozen
    legacy_clear check
    "$engine" cutover-ops disabled-preflight --date "$FIRST_SLOT"
    confirm ROTATE_BEARERS
    "$venv/python" "$ops/setup-production-make-bearers.py" --rotate-existing
    systemctl --user restart growth-engine-api.service growth-engine-worker@publish.service growth-engine-worker@jobs.service
    for unit in growth-engine-api.service growth-engine-worker@publish.service growth-engine-worker@jobs.service; do
      systemctl --user is-active --quiet "$unit"
    done
    ;;
  dry-run)
    require_os_timer_held
    [[ "$(legacy_write_status)" == 503 ]] || fail legacy_dashboard_write_not_frozen
    legacy_clear check
    [[ -f "$evidence/legacy-snapshot/manifest.json" ]] || fail missing_legacy_snapshot
    confirm MAKE_MAPPING_CHECKED
    systemctl --user start growth-engine-backup.service
    control dry-run "$FIRST_SLOT"
    "$engine" cutover-ops preflight --date "$FIRST_SLOT"
    "$engine" cutover-ops status --date "$GROUP_SLOT"
    ;;
  live)
    require_os_timer_held
    [[ "$(legacy_write_status)" == 503 ]] || fail legacy_dashboard_write_not_frozen
    legacy_clear check
    "$engine" cutover-ops approved --date "$FIRST_SLOT"
    confirm LIVE_HANOI
    control live-hanoi "$FIRST_SLOT"
    control resume-hanoi "$FIRST_SLOT"
    restore_os_timer
    ;;
  backup-check)
    confirm BACKUP
    systemctl --user start growth-engine-backup.service
    "$engine" restore-rehearsal
    ;;
  expire-overdue-now)
    confirm EXPIRE
    control expire-overdue-now "$FIRST_SLOT"
    ;;
  status)
    "$engine" cutover-ops status --date "${2:-$FIRST_SLOT}"
    ;;
  pause)
    confirm PAUSE
    control pause "$FIRST_SLOT"
    ;;
  expand)
    [[ "$(legacy_write_status)" == 503 ]] || fail legacy_dashboard_write_not_frozen
    legacy_clear check
    "$engine" cutover-ops verified-hanoi --date "$FIRST_SLOT"
    confirm EXPAND_TO_THREE
    require_group_window "$EXPAND_DATE"
    control pause "$GROUP_SLOT"
    channel fb_venho --enable
    channel ig_venho --enable
    "$engine" prepare-slot --date "$GROUP_SLOT" --channel group
    ;;
  resume-three)
    [[ "$(legacy_write_status)" == 503 ]] || fail legacy_dashboard_write_not_frozen
    legacy_clear check
    "$engine" cutover-ops verified-hanoi --date "$FIRST_SLOT"
    "$engine" backup offsite-status
    confirm LIVE_THREE
    systemctl --user start growth-engine-backup.service
    require_group_window "$RESUME_THREE_DATE"
    control resume-all "$GROUP_SLOT"
    ;;
  rollback-pause)
    confirm ROLLBACK_PAUSE
    control pause "$FIRST_SLOT"
    hold_os_timer
    printf 'ROLLBACK_OS_DEPLOY_TIMER=%s STATE=inactive\n' "$os_timer"
    control rollback "$FIRST_SLOT"
    ;;
  rollback-restore)
    confirm LEGACY_MAKE_RESTORED
    read_clock
    [[ "$today" == "$CUTOVER_DATE" ]] || fail rollback_requires_separate_catch_up_review
    hold_os_timer
    control rollback "$FIRST_SLOT"
    bash "$root/ops/asus-server/venho-os/growth-backend-switch.sh" legacy
    [[ -s "$evidence/legacy-timers.tsv" ]] || fail missing_timer_snapshot
    while IFS=$'\t' read -r unit enabled active; do
      if [[ "$enabled" == enabled ]]; then systemctl --user enable "$unit"; fi
      if [[ "$active" == active ]]; then systemctl --user start "$unit"; fi
      [[ "$(systemctl --user show "$unit" -p ActiveState --value)" == "$active" ]] || fail timer_restore_activity_mismatch
      [[ "$(systemctl --user show "$unit" -p UnitFileState --value)" == "$enabled" ]] || fail timer_restore_enablement_mismatch
    done < "$evidence/legacy-timers.tsv"
    [[ -s "$evidence/legacy-workflows.tsv" ]] || fail missing_workflow_snapshot
    while IFS=$'\t' read -r workflow prior; do
      if [[ "$prior" == active ]]; then
        gh workflow enable "$workflow" --repo "$legacy_repo" >/dev/null
      fi
      [[ "$(gh api "repos/$legacy_repo/actions/workflows/$workflow" --jq .state)" == "$prior" ]] \
        || fail workflow_restore_mismatch
    done < "$evidence/legacy-workflows.tsv"
    [[ "$(legacy_write_status)" == 401 ]] || fail legacy_write_freeze_restore_mismatch
    printf 'ROLLBACK=PASS OS_DEPLOY_TIMER=%s STATE=inactive\n' "$os_timer"
    ;;
  *) fail usage ;;
esac
