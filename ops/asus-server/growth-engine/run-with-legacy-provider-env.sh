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

needs_provider=0
if [[ "$1" == "doctor" ]]; then
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
