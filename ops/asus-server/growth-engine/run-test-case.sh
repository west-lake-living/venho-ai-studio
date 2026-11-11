#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$-" == *x* ]]; then
  printf '%s\n' 'run-test-case: disable shell xtrace before running TEST cases' >&2
  exit 2
fi
: "${HOME:?HOME must be set}"

repo_root="$HOME/venho/gc2-src"
cd "$repo_root"
[[ "$(git rev-parse --show-toplevel)" == "$repo_root" ]] || {
  printf '%s\n' 'run-test-case: expected checkout at ~/venho/gc2-src' >&2
  exit 2
}
python="$repo_root/.venv/bin/python"
[[ -x "$python" ]] || {
  printf '%s\n' 'run-test-case: GC2 source virtualenv is unavailable' >&2
  exit 2
}

exec "$python" scripts/growth_engine/run_test_case.py "$@"
