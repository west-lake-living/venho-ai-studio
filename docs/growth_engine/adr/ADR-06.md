# ADR-06 — Machine authentication at the edge

**Status:** Draft per ADR-06 defaults; credentials and edge validation are pending.

## Context

The Make Router and research ingest need machine access to a small set of internal endpoints. A shared credential would allow one compromised route to act for every channel. Cloudflare Access and application authorization protect different boundaries and both are required.

## Decision

- `/internal/*` requires Cloudflare Access Service Token headers (`CF-Access-Client-Id` and `CF-Access-Client-Secret`) and an application `Authorization: Bearer …` token.
- The application stores only hashes of service bearers under `GE_SERVICE_TOKENS`; it checks the principal's scope and channel binding on every request.
- Keep independent principals: `make-fb-hanoi` for `fb_hanoi`, `make-fb-venho` for `fb_venho`, `make-ig` for `ig_venho`, and `research-ingest` for research ingestion. The BFF has its own `bff` principal and dashboard/operator scopes.
- Give each Make route only its channel-specific bearer. Never reuse the Hanoi bearer on the Ven Hồ or Instagram route.
- `/media/publish/*` does not use either bearer. It uses the short-lived signed capability in `t`; Access Bypass permits Meta's fetch, while the application validates the capability.
- Keep all credential values in secret stores / Make connection secret fields. Do not put them in scenario text, blueprints, manifests, logs, test fixtures or this ADR. Rotate and revoke principals independently.
- Reject requests with missing, invalid or wrong-channel credentials before any publishing side effect. Never use browser-supplied `X-Venho-*` values as authorization.

## Principal and scope matrix

| Principal | Allowed identity/scope | Where credential is supplied | Status |
|---|---|---|---|
| `make-fb-hanoi` | `fb_hanoi`: authorize, receipt, approved media read | TEST Make route plus Cloudflare Access Service Token for `/internal/*` | Not configured/verified |
| `make-fb-venho` | `fb_venho`: authorize, receipt, approved media read | TEST Make route plus Cloudflare Access Service Token for `/internal/*` | Not configured/verified |
| `make-ig` | `ig_venho`: authorize, receipt, approved media read | TEST Make route plus Cloudflare Access Service Token for `/internal/*` | Not configured/verified |
| `research-ingest` | Research ingest only | GitHub Actions secret plus Cloudflare Access Service Token | Not configured/verified |
| `bff` | Dashboard read/write and operator scopes | Server-side BFF secret; browser session is separately authenticated | Not configured/verified |

## Verification matrix

| Check | Expected behavior | Result |
|---|---|---|
| No Cloudflare Access Service Token on `/internal/*` | Edge denies before application; capture actual status and response type | NOT_RUN |
| Valid Access Service Token, missing application bearer | Application returns 401 JSON | NOT_RUN |
| Valid credentials for `make-fb-hanoi` on `fb_venho` route | Application returns 403; no side effect | NOT_RUN |
| Valid TEST credentials on matching route | Request reaches TEST handler; no live Page is targeted | NOT_RUN |
| Invalid/expired signed media capability | Media handler returns 403 JSON | NOT_RUN |
| Valid signed media capability | Only the approved variant is returned; no credential appears in logs | NOT_RUN |

## Consequences

- Service-token presence alone does not authorize a publish action; the per-channel bearer and scope are also checked.
- Make custom-header support is a prerequisite (MK-6). Keep production publishing closed until that test passes.
- Rotation of one channel credential does not require rotating the others.

## Alternatives

- One shared bearer for all Make routes: rejected because compromise of one route would grant every channel's authority.
- Cloudflare Service Token alone: rejected because it identifies access to the edge but does not authorize a specific application principal/channel.
- Put a bearer on the media URL: rejected; the signed, expiring capability is the media route's authorization mechanism.

## Human gate

Harry creates/configures the Access Service Token and channel credentials in their designated secret stores, confirms Make can send the required headers on the TEST copy, and fills the verification results. No token values are recorded here.
