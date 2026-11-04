#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: restore-rehearsal.sh BACKUP.age AGE_IDENTITY NEW_TARGET_DIR" >&2
  exit 2
fi

backup_path=$1
identity_path=$2
target_dir=$3

venho-engine restore --from "$backup_path" --target "$target_dir" --identity "$identity_path"

python3 - "$target_dir/growth_engine.db" <<'PY'
import sqlite3
import sys

connection = sqlite3.connect(sys.argv[1])
integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
controls = connection.execute(
    "SELECT publish_mode, global_pause FROM runtime_controls"
).fetchall()
connection.close()
if integrity != "ok" or foreign_keys or any(mode != "DISABLED" or pause != 1 for mode, pause in controls):
    raise SystemExit("restore rehearsal failed validation")
print("restore rehearsal passed: integrity, foreign keys, DISABLED and global pause")
PY
