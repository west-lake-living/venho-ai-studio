# alert-state.sh -- sourced helper: Telegram alerts that fire once per
# problem, not once per timer tick (2026-10-22).
#
#   alert_once <key> <fingerprint> <message>
#       sends <message> unless the last alert for <key> had the same
#       fingerprint (same problem still going on).
#   alert_clear <key> <recovery message>
#       if <key> was alerting, sends the recovery message and forgets it.
ALERT_STATE_DIR="${ALERT_STATE_DIR:-$HOME/venho/state/alerts}"
ALERT_TELEGRAM="${ALERT_TELEGRAM:-$HOME/venho/scripts/growth-telegram.sh}"
mkdir -p "$ALERT_STATE_DIR"

alert_once() {
  local key="$1" fingerprint="$2" message="$3" file="$ALERT_STATE_DIR/$1"
  [ -f "$file" ] && [ "$(cat "$file")" = "$fingerprint" ] && return 0
  if "$ALERT_TELEGRAM" "$message"; then printf '%s' "$fingerprint" > "$file"; fi
}

alert_clear() {
  local key="$1" message="$2" file="$ALERT_STATE_DIR/$1"
  [ -f "$file" ] || return 0
  "$ALERT_TELEGRAM" "$message" && rm -f "$file"
}

alert_now() { TZ=Asia/Ho_Chi_Minh date '+%H:%M %d/%m'; }
