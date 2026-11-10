# Make router capability check — GC2-P0-T03

**State:** production/TEST scenario inventory comes from operator UI observations. MK-1 is configured on the TEST copy; run evidence is pending. Other capability tests and History outcomes remain unrun.

**Production scenario:** `VenHo Growth Agent-FB/IG` (ID `5868920`, Active; do not edit).
**TEST scenario:** `VenHo Growth Agent TEST` (ID `6924867`, Inactive; TEST webhook data structure has 15 fields).
**Test requirement:** use a copied scenario and test accounts only. Do not use live pages for capability tests.

No webhook URL, access token, or credential belongs in this file. Store only redacted screenshots/output, and blur connection details before attaching evidence.

## A. Read-only inventory of the current scenario

The values below are from the operator's Make UI observation, not a History run. Keep unspecified execution behavior/output fields `CHƯA XÁC MINH` until actual module History is reviewed. Do not edit production during inventory.

| Item | Value/evidence |
|---|---|
| Scenario ID / observed at (ICT) | `5868920` / 06/11/2026; Active |
| Router branches in current order | 1 Facebook Pages 3; 2 Instagram 6; 3 Facebook Pages 12 |
| Required TEST channel mapping | `fb_hanoi` → Facebook Pages 3; `ig_venho` → Instagram 6; `fb_venho` → Facebook Pages 12 |
| Production filter expression | FB branches: `platform = facebook` AND `publication_id` does not contain `test`; IG: `platform = instagram` AND `publication_id` does not contain `test`; no `channel_key` filter |
| Fallback route enabled | Off on all three routes |
| Facebook/Instagram post modules | Facebook Pages 3 and 12; Instagram 6 |
| HTTP image module position | `Download a file` before Router; Instagram also receives the binary download although its post module uses a URL |
| Webhook response modules | 8 on Facebook Pages 3 route; 7 on Instagram 6 route; none on Facebook Pages 12 route |
| Error handler path on each post module | `REQUIRED_FROM_P0` |
| Sequential processing / incomplete-execution setting | `CHƯA XÁC MINH` / `CHƯA XÁC MINH` |
| Exact post/media ID output field | `CHƯA XÁC MINH` — requires module output bundle |
| Evidence from successful History run | None supplied; MK-1 setting observation is recorded in section C |

For the post ID, inspect the output bundle of the posting module itself. Record the actual returned field name and a synthetic-looking redacted example. Do not record a UI label such as `3. Post ID` as if it were the returned ID.

## B. Prepare the TEST copy

- [x] TEST copy exists as `VenHo Growth Agent TEST`, ID `6924867`, Inactive, with a separate webhook.
- [x] Facebook modules 3 and 12 point to TEST Page `1363761820162798`; Instagram module 6 points to TEST account `@hanhpham1504` (its numeric ID is not present in this handoff).
- [x] TEST Router has the three fixed `channel_key` filters and fallback Off, per the 2026-11-10 operator observation; inherited `publication_id` conditions were removed.
- [x] Do not add Webhook response modules while sequential processing is enabled; Make reports they are unsupported in this mode.
- [ ] Use test-only credentials and webhook. Do not paste secrets into this file.
- [ ] Reposition/duplicate HTTP image download into each Facebook branch; map Instagram `image_url` from `media_url`.
- [ ] Ensure every test post is visibly labelled as a test and can be removed by the operator.
- [ ] Re-import the corrected blueprint and confirm the webhook remains immediate rather than displaying an interval schedule; keep the scenario inactive outside an approved test window.

## C. Capability evidence matrix

Fill **Result** with `PASS`, `FAIL`, or `NOT_RUN`; use `CONFIGURED — chờ bằng chứng run` for a selected setting whose execution evidence is pending. Attach redacted evidence. Do not infer a pass from a module label or from a webhook 2xx response.

| ID | Check on TEST copy | Result | Evidence / exact observed value | Remediation if FAIL |
|---|---|---|---|---|
| MK-1 | Sequential processing is enabled. | CONFIGURED — chờ bằng chứng run | Harry selected sequential processing after Make warned that responders are unsupported in this mode on 2026-11-10. Import/runtime evidence is pending. | Keep sequential processing enabled; do not add Webhook response modules. |
| MK-2 | Incomplete executions are disabled, or the runbook explicitly forbids resuming after the response step. | NOT_RUN | `REQUIRED_FROM_P0` | Disable storage or document and enforce the no-resume rule. |
| MK-3 | Facebook/Instagram post modules have no automatic retry and no Break directive. | NOT_RUN | `REQUIRED_FROM_P0` | Remove automatic retry/Break; ambiguous outcomes must be reconciled. |
| MK-4 | Each post module returns its real post/media ID in its output bundle. | NOT_RUN | Exact field: `REQUIRED_FROM_P0` | Remap from the module output; never use a mapping label as a value. |
| MK-5 | Both Facebook post modules receive their own downloaded JPEG binary; the Instagram module receives the signed image URL. | NOT_RUN | `REQUIRED_FROM_P0` | Map HTTP binary only to Facebook; map `media_url` to Instagram's image URL input. |
| MK-6 | HTTP modules can send the required bearer and Cloudflare Access headers without exposing them in logs. | NOT_RUN | `REQUIRED_FROM_P0` | Keep production gate closed until proven. |
| MK-7 | Errors proven to occur before publication are distinguished from ambiguous outcomes. | NOT_RUN | Actual redacted error/status: `REQUIRED_FROM_P0` | Add only observed classifications to `make_error_classes.yaml`; otherwise use `OUTCOME_UNKNOWN`. |
| MK-8 | Operators know not to rerun a posting module manually; recovery starts from the first webhook module. | NOT_RUN | Runbook/evidence: `REQUIRED_FROM_P0` | Add and review the no-manual-rerun instruction. |
| MK-9 | Router has exactly three routes filtered by fixed `channel_key`; fallback is off; one command reaches one route. | NOT_RUN | `REQUIRED_FROM_P0` | Correct all three filters and test each channel key independently. |
| MK-10 | Instagram accepts the signed media URL and Meta can fetch it without receiving a Cloudflare Access login page. | NOT_RUN | Redacted result: `REQUIRED_FROM_P0` | Adjust only the TEST edge rule, then retest from Instagram. |
| MK-11 | Instagram output includes the media ID and distinguishes container creation failure from publish failure. | NOT_RUN | Exact field/error evidence: `REQUIRED_FROM_P0` | Keep uncertain outcomes unknown; capture module-level evidence. |

## D. TEST cases to run after destinations and credentials are confirmed

- [ ] One successful test per `channel_key`; save module-level outputs and verify each returned ID on its mapped TEST destination.
- [ ] Broken/non-JPEG image: verify the post module is not reached.
- [ ] Invalid test credential: capture the exact observed error without saving the token.
- [ ] Submit the same test command twice: verify the second attempt does not create another post.
- [ ] Stop after authorize but before the post module: verify the route does not continue or auto-resume.
- [ ] Send one test command per `channel_key`: verify only its matching route runs.
- [ ] Instagram: verify image fetch succeeds and record separate container/publish outcomes.

| Case | Result | Evidence |
|---|---|---|
| Successful FB Hanoi test | NOT_RUN | `REQUIRED_FROM_P0` |
| Successful FB Ven Ho test | NOT_RUN | `REQUIRED_FROM_P0` |
| Successful Instagram test | NOT_RUN | `REQUIRED_FROM_P0` |
| Invalid image / invalid test credential | NOT_RUN | `REQUIRED_FROM_P0` |
| Duplicate command / interrupted execution | NOT_RUN | `REQUIRED_FROM_P0` |

**Gate:** if MK-1…MK-6 do not pass, keep the production publishing mode below `LIVE_MANUAL`. MK-7…MK-11 and all test outcomes remain unverified until the TEST copy is operated and evidence is reviewed.
