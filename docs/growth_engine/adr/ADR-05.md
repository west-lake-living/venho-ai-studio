# ADR-05 — Media delivery through Cloudflare edge

**Status:** Decision recorded for this build on 2026-11-05; edge configuration and external checks remain pending under P0-T05.

## Context

Facebook modules in Make need the approved JPEG bytes. Instagram for Business gives Meta a URL to fetch, and that fetch cannot depend on an interactive Cloudflare login page. The public origin must not expose the API or media store directly.

## Decision

- Use `growth-api.venhohotel.com` through the Cloudflare Tunnel.
- The tunnel origin listens on `127.0.0.1:<port selected by P0-T01>`; do not expose the origin port publicly.
- Publish only `/internal/*` and `/media/publish/*` through the tunnel.
- Apply Cloudflare Access Service Token policy to `/internal/*`. The application also requires a principal-specific bearer and scope for each operation.
- Apply Access **Bypass** to `/media/publish/*`; this only bypasses Cloudflare Access. The media handler still verifies the signed `t` capability, expiry, approved variant and SHA-256. Invalid/expired capabilities return 403 JSON. Successful responses use `Content-Type: image/jpeg` and `Cache-Control: private, no-store`.
- Make fetches F1/I1 media before calling authorize. Therefore `/media/publish/*` must serve an unexpired `PENDING` command when its current delivery revision remains active, approved, hash-matched and QC-passed; it must not require an authorization execution to exist yet. The existing signed URL, command deadline/grace, current approval/revision and exact-variant SHA checks still apply.
- Do not route Dashboard or other browser paths through the machine endpoint policy. Do not expose the origin directly.

Under GC2-D02, both Facebook Pages use the same approved source image bytes; Instagram uses its own approved 4:5 media variant. Captions follow the channel's `caption_profile` (defaulting to the same caption) and remain covered by the one grouped approval.

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

## Alternatives

- Put the API under `os.venhohotel.com`: listed as the alternative to the GC2-D08 default; not selected for this build.
- Expose the origin directly or bypass application media signatures: rejected because it broadens access and could return bytes other than the approved variant.
- Use unrelated image bytes for each Facebook Page or silently transform an approved image at dispatch: rejected because approval binds the exact media bytes.

## Human gate

Harry configures the hostname, Tunnel routes and Access rules, then fills the matrix with redacted external `curl` evidence. No Cloudflare setting or live endpoint was changed for this ADR.
