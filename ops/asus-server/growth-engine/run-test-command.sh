#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  printf 'run-test-command: %s\n' "$*" >&2
  exit 2
}

[[ "$-" != *x* ]] || fail "disable shell xtrace before entering TEST credentials"
: "${HOME:?HOME must be set}"

repo_root="$HOME/venho/gc2-src"
cd "$repo_root" || fail "expected checkout at ~/venho/gc2-src"
[[ "$(git rev-parse --show-toplevel)" == "$repo_root" ]] || fail "run from the gc2-src repository root"
python="$repo_root/.venv/bin/python"
[[ -x "$python" ]] || fail "GC2 source virtualenv is unavailable"

exec "$python" scripts/growth_engine/run_test_command.py
