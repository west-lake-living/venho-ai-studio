#!/usr/bin/env bash
# venho-os-watch.sh -- is the Dashboard actually answering? (2026-10-22)
# Timer every 5 min. `Restart=on-failure` hides a crash loop and says nothing
# about a process that is up but returning errors, so this probes the page
# itself. Two failed probes in a row (10 min) alert once; recovery alerts once.
set -uo pipefail
. "$HOME/venho/scripts/alert-state.sh"
fails="$ALERT_STATE_DIR/venho-os-watch.fails"

code=$(curl -s -o /dev/null -m 20 -w '%{http_code}' http://127.0.0.1:3000/login || echo 000)
active=$(systemctl --user is-active venho-os 2>/dev/null || true)
if [ "$code" = "200" ]; then
  rm -f "$fails"
  alert_clear venho-os-watch "✅ Dashboard (os.venhohotel.com) chạy lại bình thường ($(alert_now))."
  exit 0
fi
n=$(( $(cat "$fails" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$fails"
# A deploy restart takes a few seconds; one miss is not an outage.
[ "$n" -ge 2 ] || exit 0
alert_once venho-os-watch "down" "🔴 Dashboard (os.venhohotel.com) KHÔNG TRẢ LỜI từ ~$(alert_now) (HTTP $code, service: $active).
Xem: journalctl --user -u venho-os -n 80
Khởi động lại: systemctl --user restart venho-os"
exit 1
