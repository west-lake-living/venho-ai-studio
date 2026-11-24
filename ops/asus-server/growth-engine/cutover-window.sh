#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ "$-" != *x* ]] || exit 2
root="$HOME/venho/growth-engine/current"
ops="$root/ops/asus-server/growth-engine"
venv="$root/.venv/bin"
engine="$ops/run-with-legacy-provider-env.sh"
env_file="$HOME/venho/secrets/growth-engine.env"
evidence="$HOME/venho/state/growth-engine/cutover-20261124"
legacy="$HOME/venho/growth-runtime/venho-ai-studio"
os_timer=venho-os-deploy.timer
os_timer_state="$evidence/venho-os-deploy.timer.state"
os_freeze_commit=dd236e53fd153278daa7f846cb11ff3a2e7d52ca
insights="$HOME/venho/state/growth-reports/insights.db"
legacy_repo=west-lake-living/venho-ai-studio
names=(0900 1700 weekly-cycle replace-rejected trend-scan fast-lane expire-stale)
instances=(primary second weekly-cycle replace-rejected trend-scan fast-lane expire-stale)
first=2026-11-25
next_slot=2026-11-27
fail() { printf 'CUTOVER=BLOCKED reason=%s\n' "$1" >&2; exit 1; }
clock="$(TZ=Asia/Ho_Chi_Minh date +%H%M)"
(( 10#$clock < 830 || 10#$clock > 930 )) || fail 'publish window 08:30–09:30 ICT'
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
  for workflow in growth-publish-scheduler.yml growth-daily-cycle.yml growth-replace-rejected.yml growth-expire-stale-approvals.yml; do
    runs="$(gh api --paginate "repos/$legacy_repo/actions/workflows/$workflow/runs?per_page=100" \
      --jq '[.workflow_runs[] | select(.status != "completed")] | length')" || fail legacy_workflow_query_failed
    [[ "$runs" =~ $drained_pattern ]] || fail "${workflow}_runs_not_drained"
  done
  [[ "$(gh api "repos/$legacy_repo/actions/workflows/growth-publish-scheduler.yml" --jq .state)" == disabled_manually ]] || fail 'legacy GitHub workflow remains enabled'
  registry=data/projects/venho_hotel/publishing/publication_registry.json
  git -C "$legacy" fetch --quiet origin main >/dev/null 2>&1 || fail legacy_registry_fetch_failed
  remote_blob="$(git -C "$legacy" rev-parse "FETCH_HEAD:$registry" 2>/dev/null)" || fail legacy_remote_registry_missing
  [[ "$(git -C "$legacy" hash-object -- "$legacy/$registry")" == "$remote_blob" ]] || fail 'legacy local registry differs from GitHub'
  case "$1" in
    check) "$venv/python" "$ops/legacy-cutover-snapshot.py" "$legacy" "$evidence" --check --insights "$insights" ;;
    snapshot) "$venv/python" "$ops/legacy-cutover-snapshot.py" "$legacy" "$evidence" --insights "$insights" ;;
  esac
}
mkdir -p -- "$evidence"
chmod 700 "$evidence"
exec 9>"$evidence/.operator.lock"
flock -n 9 || fail another_cutover_operation

today="$(TZ=Asia/Ho_Chi_Minh date +%F)"
case "${1:-}" in
  friday-backup) [[ "$today" == 2026-11-20 ]] && (( 10#$clock > 930 )) || fail wrong_backup_date_or_time ;;
  t2) [[ "$today" == 2026-11-23 ]] || fail wrong_preparation_date ;;
  stop-legacy|snapshot|switch-and-epoch|rotate|dry-run|live) [[ "$today" == 2026-11-24 ]] || fail wrong_cutover_date ;;
  expand) [[ "$today" == 2026-11-25 ]] && (( 10#$clock > 930 )) || fail wrong_expansion_date_or_time ;;
  resume-three) [[ "$today" == 2026-11-26 ]] || fail wrong_group_approval_date ;;
esac

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
    "$engine" cutover-ops backup-fresh --date "$first"
    confirm PREPARE_25
    channel fb_hanoi --enable --prepare-only
    "$engine" prepare-slot --date "$first" --channel fb_hanoi
    ;;
  stop-legacy)
    "$engine" cutover-ops disabled-preflight --date "$first"
    confirm STOP_LEGACY
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
    workflow_state="$(gh api "repos/$legacy_repo/actions/workflows/growth-publish-scheduler.yml" --jq .state)"
    [[ "$workflow_state" == active || "$workflow_state" == disabled_manually ]] || fail unexpected_legacy_workflow_state
    printf '%s\n' "$workflow_state" > "$evidence/legacy-workflow-state"
    git -C "$HOME/venho/venho-os" merge-base --is-ancestor "$os_freeze_commit" HEAD 2>/dev/null \
      || fail legacy_write_guard_not_deployed
    hold_os_timer
    git -C "$HOME/venho/venho-os" merge-base --is-ancestor "$os_freeze_commit" HEAD 2>/dev/null \
      || fail legacy_write_guard_not_deployed
    [[ "$(legacy_write_status)" == 401 ]] || fail legacy_backend_probe_unexpected
    mv -- "$tmp" "$evidence/legacy-timers.tsv"
    gh workflow disable growth-publish-scheduler.yml --repo west-lake-living/venho-ai-studio >/dev/null
    while IFS=$'\t' read -r unit enabled active; do
      systemctl --user disable --now "$unit"
    done < "$evidence/legacy-timers.tsv"
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
    bash "$root/ops/asus-server/venho-os/growth-backend-switch.sh" v2
    [[ "$(legacy_write_status)" == 503 ]] || fail legacy_dashboard_write_not_frozen
    control epoch "$first"
    ;;
  rotate)
    require_os_timer_held
    [[ "$(legacy_write_status)" == 503 ]] || fail legacy_dashboard_write_not_frozen
    legacy_clear check
    "$engine" cutover-ops disabled-preflight --date "$first"
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
    control dry-run "$first"
    "$engine" cutover-ops preflight --date "$first"
    "$engine" cutover-ops status --date "$next_slot"
    ;;
  live)
    require_os_timer_held
    [[ "$(legacy_write_status)" == 503 ]] || fail legacy_dashboard_write_not_frozen
    legacy_clear check
    "$engine" cutover-ops approved --date "$first"
    confirm LIVE_HANOI
    control live-hanoi "$first"
    control resume-hanoi "$first"
    restore_os_timer
    ;;
  backup-check)
    confirm BACKUP
    systemctl --user start growth-engine-backup.service
    "$engine" restore-rehearsal
    ;;
  status)
    "$engine" cutover-ops status --date "${2:-$first}"
    ;;
  pause)
    confirm PAUSE
    control pause "$first"
    ;;
  expand)
    [[ "$(legacy_write_status)" == 503 ]] || fail legacy_dashboard_write_not_frozen
    legacy_clear check
    "$engine" cutover-ops verified-hanoi --date "$first"
    confirm EXPAND_TO_THREE
    control pause "$next_slot"
    channel fb_venho --enable
    channel ig_venho --enable
    "$engine" prepare-slot --date "$next_slot" --channel group
    ;;
  resume-three)
    [[ "$(legacy_write_status)" == 503 ]] || fail legacy_dashboard_write_not_frozen
    legacy_clear check
    "$engine" cutover-ops verified-hanoi --date "$first"
    "$engine" backup offsite-status
    confirm LIVE_THREE
    systemctl --user start growth-engine-backup.service
    control resume-all "$next_slot"
    ;;
  rollback-pause)
    confirm ROLLBACK_PAUSE
    control pause "$first"
    hold_os_timer
    printf 'ROLLBACK_OS_DEPLOY_TIMER=%s STATE=inactive\n' "$os_timer"
    control rollback "$first"
    ;;
  rollback-restore)
    [[ "$(TZ=Asia/Ho_Chi_Minh date +%F)" == 2026-11-24 ]] || fail 'rollback timer restart requires separate catch-up review outside 24/11'
    confirm LEGACY_MAKE_RESTORED
    hold_os_timer
    control rollback "$first"
    bash "$root/ops/asus-server/venho-os/growth-backend-switch.sh" legacy
    [[ -s "$evidence/legacy-timers.tsv" ]] || fail missing_timer_snapshot
    while IFS=$'\t' read -r unit enabled active; do
      if [[ "$enabled" == enabled ]]; then systemctl --user enable "$unit"; fi
      if [[ "$active" == active ]]; then systemctl --user start "$unit"; fi
      [[ "$(systemctl --user show "$unit" -p ActiveState --value)" == "$active" ]] || fail timer_restore_activity_mismatch
      [[ "$(systemctl --user show "$unit" -p UnitFileState --value)" == "$enabled" ]] || fail timer_restore_enablement_mismatch
    done < "$evidence/legacy-timers.tsv"
    prior="$(< "$evidence/legacy-workflow-state")"
    if [[ "$prior" == active ]]; then
      gh workflow enable growth-publish-scheduler.yml --repo west-lake-living/venho-ai-studio >/dev/null
    fi
    [[ "$(gh api repos/west-lake-living/venho-ai-studio/actions/workflows/growth-publish-scheduler.yml --jq .state)" == "$prior" ]] || fail workflow_restore_mismatch
    [[ "$(legacy_write_status)" == 401 ]] || fail legacy_write_freeze_restore_mismatch
    printf 'ROLLBACK=PASS OS_DEPLOY_TIMER=%s STATE=inactive\n' "$os_timer"
    ;;
  *) fail usage ;;
esac
