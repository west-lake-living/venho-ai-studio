#!/usr/bin/env bash
# growth-telegram.sh "<message>"  -- or, as OnFailure handler:
# growth-telegram.sh --unit-failed <unit>
set -uo pipefail
ENV_FILE="$HOME/venho/secrets/growth.env"
env_get() { grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2-; }
TOK="$(env_get TELEGRAM_BOT_TOKEN)"; CID="$(env_get TELEGRAM_CHAT_ID)"
[ -n "$TOK" ] && [ -n "$CID" ] || { echo "growth-telegram: missing TELEGRAM_* in $ENV_FILE" >&2; exit 1; }

if [ "${1:-}" = "--unit-failed" ]; then
  unit="$2"
  tail_log="$(journalctl --user -u "$unit" -n 15 --no-pager -o cat 2>/dev/null | cut -c1-200)"
  msg="🔴 Growth đăng bài LỖI ($unit) lúc $(TZ=Asia/Ho_Chi_Minh date '+%H:%M %d/%m').
${tail_log}

Xem: journalctl --user -u $unit -n 80"
else
  msg="$1"
fi

curl -fsS -m 20 "https://api.telegram.org/bot${TOK}/sendMessage" \
  --data-urlencode "chat_id=${CID}" \
  --data-urlencode "text=${msg:0:3900}" \
  --data-urlencode "disable_web_page_preview=true" >/dev/null
