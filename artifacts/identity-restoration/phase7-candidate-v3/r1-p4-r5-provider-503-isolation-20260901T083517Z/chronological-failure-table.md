# Chronological Gemini Attempt Audit

All rows use the same authoritative request path: `FACE_LOCAL` B01,
multi-image input, `google-genai 1.47.0`, API-key auth, and
`POST https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent`.
HTTP status and response headers were not surfaced by the captured SDK
exception; the provider payload supplied machine error `503` and status
`UNAVAILABLE`.

| UTC timestamp | Task | Retry | Outcome | Provider detail |
|---|---|---:|---|---|
| 2026-09-01 05:06:04 | R1-P4 | 1 | started | — |
| 2026-09-01 05:07:44 | R1-P4 | 1 | failed | `503 UNAVAILABLE`; high demand |
| 2026-09-01 05:07:45 | R1-P4 | 2 | started | — |
| 2026-09-01 05:08:28 | R1-P4 | 2 | success | input 5254 / output 340 |
| 2026-09-01 05:09:46 | R1-P4 | 1 | started | — |
| 2026-09-01 05:11:05 | R1-P4 | 1 | failed | `503 UNAVAILABLE`; high demand |
| 2026-09-01 05:11:05 | R1-P4 | 2 | started | — |
| 2026-09-01 05:12:23 | R1-P4 | 2 | failed | `503 UNAVAILABLE`; high demand |
| 2026-09-01 06:59:09 | R1-P4-R1 | 1 | started | — |
| 2026-09-01 06:59:39 | R1-P4-R1 | 1 | failed | `503 UNAVAILABLE`; high demand |
| 2026-09-01 06:59:39 | R1-P4-R1 | 2 | started | — |
| 2026-09-01 07:00:07 | R1-P4-R1 | 2 | failed | `503 UNAVAILABLE`; high demand |
| 2026-09-01 07:25:12 | R1-P4-R2 | 1 | started | — |
| 2026-09-01 07:25:30 | R1-P4-R2 | 1 | failed | `503 UNAVAILABLE`; high demand |
| 2026-09-01 07:25:31 | R1-P4-R2 | 2 | started | — |
| 2026-09-01 07:25:54 | R1-P4-R2 | 2 | failed | `503 UNAVAILABLE`; high demand |
| 2026-09-01 08:27:23 | R1-P4-R4 | 1 | started | — |
| 2026-09-01 08:27:39 | R1-P4-R4 | 1 | failed | `503 UNAVAILABLE`; high demand |
| 2026-09-01 08:27:39 | R1-P4-R4 | 2 | started | — |
| 2026-09-01 08:27:43 | R1-P4-R4 | 2 | failed | `503 UNAVAILABLE`; high demand |

Request hashes, response headers, and a concrete model ID were not captured
by the old failed-attempt evidence. They are recorded as unknown, not
invented. The successful R1-P4 response on the same adapter path is strong
evidence against a deterministic local endpoint, schema, or authentication
defect.
