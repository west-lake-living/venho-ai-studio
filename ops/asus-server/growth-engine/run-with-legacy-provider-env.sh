#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  printf 'growth-engine provider environment: %s\n' "$*" >&2
  exit 1
}

[[ $# -ge 1 ]] || fail "a venho-engine command is required"
[[ "$-" != *x* ]] || fail "disable shell xtrace before sourcing provider credentials"
: "${HOME:?HOME must be set}"

LEGACY_ENV="$HOME/venho/secrets/growth.env"
GC2_ENV="$HOME/venho/secrets/growth-engine.env"
RUNTIME_BIN="${VENHO_GC2_RUNTIME_BIN:-$HOME/venho/growth-engine/current/.venv/bin/venho-engine}"

[[ -r "$GC2_ENV" ]] || fail "Growth Engine production environment file is missing or unreadable"
[[ -x "$RUNTIME_BIN" ]] || fail "Growth Engine runtime executable is unavailable"

case "$1" in
  reprocess-p4-qc-evidence) action=REPROCESS ;;
  resolve-p4-qc-unknown) action=RESOLVE ;;
  *) action='' ;;
esac

if [[ -n "$action" ]]; then
  command_name="$1"
  shift
  job_id=''
  engine_args=("$command_name")
  while (( $# )); do
    case "$1" in
      --job)
        [[ $# -ge 2 && -z "$job_id" && "$2" =~ ^[a-zA-Z0-9_-]+$ ]] || fail "supply one valid --job ID"
        job_id="$2"
        engine_args+=("--job" "$job_id")
        shift 2
        ;;
      --actual-minor|--input-tokens|--output-tokens)
        [[ "$action" == RESOLVE && $# -ge 2 && "$2" =~ ^[0-9]+$ ]] || fail "invalid QC resolution option"
        engine_args+=("$1" "$2")
        shift 2
        ;;
      *) fail "unsupported operator wrapper argument" ;;
    esac
  done
  [[ -n "$job_id" ]] || fail "supply --job ID"
  tty_required() {
    printf '%s\n' '{"result":"BLOCKED","code":"ERR_GC2_OPERATOR_TTY_REQUIRED","reason":"an interactive controlling terminal is required"}' >&2
    exit 2
  }
  { exec 3<>/dev/tty; } 2>/dev/null || tty_required

  run_operator() {
    systemd-run --user --pipe --wait --collect --quiet \
      --property="EnvironmentFile=$GC2_ENV" --setenv=GE_ENV=production \
      --property="WorkingDirectory=${RUNTIME_BIN%/*/*/*}" \
      "$RUNTIME_BIN" "${engine_args[@]}" "$@" </dev/null 3>&-
  }
  if preflight="$(run_operator --preflight-only)"; then
    printf '%s\n' "$preflight"
  else
    status=$?
    printf '%s\n' "$preflight"
    exit "$status"
  fi
  if [[ "$preflight" == *'"result": "ALREADY_PROCESSED"'* ||
        "$preflight" == *'"result": "ALREADY_RESOLVED"'* ]]; then
    exit 0
  fi
  [[ "$preflight" == *'"preflight": "READY"'* ]] || fail "operator preflight did not report READY"

  # Bash read -t 0 only checks readiness. Consume ready lines, then flush
  # partial lines too, which canonical terminal mode does not expose to read.
  while IFS= read -r -t 0 -u 3; do
    IFS= read -r -t 0.01 -u 3 _ || break
  done
  "${RUNTIME_BIN%/*}/python" -c 'import termios; termios.tcflush(3, termios.TCIFLUSH)' || tty_required
  printf 'Gõ %s để xác nhận job %s: ' "$action" "$job_id" >&3
  if ! IFS= read -r -u 3 answer || [[ "$answer" != "$action" ]]; then
    printf '%s=DECLINED\n' "$action"
    exit 2
  fi
  run_operator --operator-confirmed "$action:$job_id"
  exit
fi

needs_provider=0
if [[ "$1" == "doctor" ]]; then
  needs_provider=1
fi
if [[ "$1" == "repair-p4-media" ]]; then
  needs_provider=1
fi
for argument in "$@"; do
  if [[ "$argument" == "jobs" ]]; then
    needs_provider=1
  fi
done

if (( needs_provider )); then
  [[ -r "$LEGACY_ENV" ]] || fail "legacy growth environment file is missing or unreadable"
  # Load only the active legacy provider keys into the v2 process. Restore the
  # isolated Growth Engine configuration from its separate production env file.
  set -a
  . "$LEGACY_ENV"
  set +a
  legacy_anthropic_api_key="${ANTHROPIC_API_KEY:-}"
  legacy_openai_api_key="${OPENAI_API_KEY:-}"
  set -a
  . "$GC2_ENV"
  set +a
  ANTHROPIC_API_KEY="$legacy_anthropic_api_key"
  OPENAI_API_KEY="$legacy_openai_api_key"
  unset GOOGLE_DRIVE_TOKEN_JSON GOOGLE_OAUTH_CLIENT_ID GOOGLE_OAUTH_CLIENT_SECRET
  export ANTHROPIC_API_KEY OPENAI_API_KEY
  unset legacy_anthropic_api_key legacy_openai_api_key
else
  set -a
  . "$GC2_ENV"
  set +a
fi

[[ "${GE_ENV:-}" == "production" ]] || fail "Growth Engine environment must be production"
if (( needs_provider )); then
  [[ -n "${ANTHROPIC_API_KEY:-}" && -n "${OPENAI_API_KEY:-}" ]] \
    || fail "legacy provider keys are not available to the jobs worker"
fi

exec "$RUNTIME_BIN" "$@"
