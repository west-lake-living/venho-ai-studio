#!/usr/bin/env bash
# make-signature-test.sh -- check the X-Venho-Signature filter in the Growth
# Make.com scenario (2026-10-22) without anyone seeing the secret.
#
# Sends two requests to MAKE_GROWTH_WEBHOOK_URL:
#   test-sigcheck-<ts>-good  signed exactly like make_gateway.py signs a post
#   test-sigcheck-<ts>-bad   signed with a wrong key
# Both ids contain "test", which the scenario's own guard must stop before any
# Facebook/Instagram module. ONLY run this after reading that guard in the
# scenario: on 2026-08-06 test payloads reached the real Page twice.
#
# Expected in the scenario's History: "-good" passes the signature filter and
# stops at the test guard; "-bad" stops at the signature filter.
set -euo pipefail
ENV_FILE="$HOME/venho/secrets/growth.env"
set -a; . "$ENV_FILE"; set +a
: "${MAKE_GROWTH_WEBHOOK_URL:?missing in $ENV_FILE}"
: "${MAKE_GROWTH_WEBHOOK_SECRET:?missing in $ENV_FILE}"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
send() {
  local pid="test-sigcheck-$ts-$1" key="$2"
  local idem="test-idem-$ts-$1"
  local sig
  sig="$(python3 -c 'import hashlib,hmac,sys; print(hmac.new(sys.argv[1].encode(), f"{sys.argv[2]}:{sys.argv[3]}".encode(), hashlib.sha256).hexdigest())' "$key" "$pid" "$idem")"
  local body
  body="$(python3 -c 'import json,sys; print(json.dumps({"publication_id": sys.argv[1], "idempotency_key": sys.argv[2], "platform": "facebook", "content": {"text": "TEST chữ ký -- KHÔNG ĐĂNG"}, "image_url": "https://venhohotel.com/images/Social-fallback/hotel-front-view.jpg"}))' "$pid" "$idem")"
  local reply
  reply="$(curl -sS -m 30 -X POST "$MAKE_GROWTH_WEBHOOK_URL" -H "Content-Type: application/json" -H "X-Venho-Signature: $sig" --data "$body" -w ' HTTP %{http_code}')"
  echo "$pid -> ${reply:0:200}"
}
send good "$MAKE_GROWTH_WEBHOOK_SECRET"
send bad "wrong-key-$ts"
