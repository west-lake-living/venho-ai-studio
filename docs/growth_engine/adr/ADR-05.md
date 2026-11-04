# ADR-05 — Media delivery through Cloudflare edge

**Status:** Design accepted by GC2-D08; edge configuration and external checks are pending.

## Context

Facebook modules in Make need the approved JPEG bytes. Instagram for Business gives Meta a URL to fetch, and that fetch cannot depend on an interactive Cloudflare login page. The public origin must not expose the API or media store directly.

## Decision

- Use `growth-api.venhohotel.com` through the Cloudflare Tunnel.
- The tunnel origin listens on `127.0.0.1:<port selected by P0-T01>`; do not expose the origin port publicly.
- Publish only `/internal/*` and `/media/publish/*` through the tunnel.
- Apply Cloudflare Access Service Token policy to `/internal/*`. The application also requires a principal-specific bearer and scope for each operation.
- Apply Access **Bypass** to `/media/publish/*`; this only bypasses Cloudflare Access. The media handler still verifies the signed `t` capability, expiry, approved variant and SHA-256. Invalid/expired capabilities return 403 JSON. Successful responses use `Content-Type: image/jpeg` and `Cache-Control: private, no-store`.
- Do not route Dashboard or other browser paths through the machine endpoint policy. Do not expose the origin directly.

## Route and validation matrix

All live results are `NOT_RUN`; Harry must configure the edge and run the checks from a machine outside the tunnel host. Record status, content type and a redacted response sample, never request headers or signed URLs.

| Route | Cloudflare policy | Application check | Request/evidence to collect | Result |
|---|---|---|---|---|
| `/internal/growth/v2/executions/authorize` | Service Token required | Bearer + channel scope required | No Access headers: record status and whether JSON/HTML/login redirect; confirm it does not reach the handler. Access headers but no bearer: record application denial; both valid test credentials: record backend response | NOT_RUN |
| `/internal/growth/v2/receipts` | Service Token required | Bearer + channel scope required | Repeat the three cases above using the TEST route | NOT_RUN |
| `/internal/growth/v2/research/ingest` | Service Token required | `research-ingest` principal required | Missing/wrong service token denied; valid TEST principal reaches backend | NOT_RUN |
| `/media/publish/<sha>.jpg?t=<signed>` | Access Bypass | Signed capability, expiry, approved hash | No/invalid/expired signature returns 403 JSON; valid TEST signature returns JPEG bytes with the expected SHA-256 | NOT_RUN |
| Any other public API path | No tunnel route | No handler should be reachable | Probe a non-allowlisted path from outside; record the actual response | NOT_RUN |

## Consequences

- Make's internal HTTP modules need both Cloudflare service-token headers and the separate application bearer. MK-6 must prove Make can send both without exposing them in logs.
- Instagram can fetch signed media without an Access login. MK-10 and P7-T06 must verify the behavior from outside.
- A Bypass rule does not make the media public: the application signature and expiry remain mandatory.
- The actual no-header response may be a denial, HTML login page or redirect; do not assume which. Capture the real response and confirm the protected handler was not reached before accepting the edge configuration.

## Human gate

Harry configures the hostname, Tunnel routes and Access rules, then fills the matrix with redacted external `curl` evidence. No Cloudflare setting or live endpoint was changed for this ADR.
