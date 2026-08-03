#!/usr/bin/env bash
# infra/backup.sh -- daily backup of growth.db + artifacts (v3.1 §10.5).
# Run via infra/launchd/com.venho.dispatch.plist's sibling schedule at 02:00,
# or manually: infra/backup.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${REPO_ROOT}/data/projects/venho_hotel/growth/growth.db"
ARTIFACTS_PATH="${REPO_ROOT}/data/projects/venho_hotel/growth/artifacts"
BACKUP_ROOT="${VENHO_BACKUP_ROOT:-${HOME}/VenhoBackups}"
DATE_STAMP="$(date +%Y-%m-%d)"
DEST="${BACKUP_ROOT}/${DATE_STAMP}"

mkdir -p "${DEST}"

if [ -f "${DB_PATH}" ]; then
  sqlite3 "${DB_PATH}" ".backup '${DEST}/growth.db'"
  echo "backed up growth.db -> ${DEST}/growth.db"
else
  echo "no growth.db found at ${DB_PATH}, skipping DB backup"
fi

if [ -d "${ARTIFACTS_PATH}" ]; then
  cp -R "${ARTIFACTS_PATH}" "${DEST}/artifacts"
  echo "copied artifacts -> ${DEST}/artifacts"
fi

# Off-site copy. Requires `rclone` configured with a remote named "venho-cloud"
# (rclone config) -- left as a manual one-time setup step, not run by default.
if command -v rclone >/dev/null 2>&1 && rclone listremotes | grep -q "^venho-cloud:"; then
  rclone copy "${DEST}" "venho-cloud:backups/${DATE_STAMP}" --progress
  echo "synced ${DEST} -> venho-cloud:backups/${DATE_STAMP}"
else
  echo "rclone remote 'venho-cloud' not configured -- skipping off-site sync"
fi

echo "backup complete: ${DEST}"
