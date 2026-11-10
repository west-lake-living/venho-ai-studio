# Make router capability check — GC2-P0-T03

**State:** TEST scenario runtime evidence includes a successful end-to-end `fb_hanoi` run on 2026-11-10. MK-1 remains CONFIGURED; MK-4/5/6/9 have PASS evidence for the route exercised. Other route-specific and failure-mode checks remain unrun.

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
- [x] Generated F1/I1 modules use one `Ignore` error handler for fetch failures; this is static blueprint evidence, not yet verified in Make History.
- [ ] Use test-only credentials and webhook. Do not paste secrets into this file.
- [ ] Reposition/duplicate HTTP image download into each Facebook branch; map Instagram `image_url` from `media_url`.
- [ ] Ensure every test post is visibly labelled as a test and can be removed by the operator.
- [ ] Re-import the corrected blueprint and confirm the webhook remains immediate rather than displaying an interval schedule; keep the scenario inactive outside an approved test window.

## C. Capability evidence matrix

Fill **Result** with `PASS`, `PARTIAL`, `FAIL`, or `NOT_RUN`; use `CONFIGURED — chờ bằng chứng run` for a selected setting whose execution evidence is pending. Attach redacted evidence. Do not infer a pass from a module label or from a webhook 2xx response.

| ID | Check on TEST copy | Result | Evidence / exact observed value | Remediation if FAIL |
|---|---|---|---|---|
| MK-1 | Sequential processing is enabled. | CONFIGURED | TEST scenario 6924867 completed a webhook run; it processed five operations in 8 seconds. The run is consistent with sequential mode; setting remains recorded as configured from the Make UI observation on 2026-11-10. | Keep sequential processing enabled; do not add Webhook response modules. |
| MK-2 | Incomplete executions are disabled, or the runbook explicitly forbids resuming after the response step. | NOT_RUN | `REQUIRED_FROM_P0` | Disable storage or document and enforce the no-resume rule. |
| MK-3 | Facebook/Instagram post modules have no automatic retry and no Break directive. | NOT_RUN | `REQUIRED_FROM_P0` | Remove automatic retry/Break; ambiguous outcomes must be reconciled. |
| MK-4 | Each post module returns its real post/media ID in its output bundle. | PASS — exercised Facebook module 3 | Make History run 2026-11-10 22:33 ICT, command `cd73c43a-1a28-4922-bd4d-29aeaf6d665d`: Facebook Pages 3 output `id=1363761820162798_122106835935535879`. TEST DB contains the accepted receipt but it is still `RECEIVED`; delivery application and the DB `platform_post_id` comparison are pending the one-shot receipt step in the runbook. | After applying the receipt, verify stored `platform_post_id` equals the module `id`. |
| MK-5 | The executed route passes the correct image to its post module (Facebook uses that route's downloaded JPEG; Instagram uses the signed image URL). | PASS — route `fb_hanoi` | Make History run 2026-11-10 22:33 ICT: HTTP 4/F1 returned `200 image/jpeg` with `private,no-store` and `cf-cache-status=BYPASS`; Facebook Pages 3 then created the TEST post. This proves the exercised Hanoi route. The `fb_venho` and Instagram branches were filtered out and their path-specific media mappings remain untested. | Run the same successful path once on `fb_venho` and `ig_venho` before treating those destinations as independently verified. |
| MK-6 | HTTP modules can send the required bearer and Cloudflare Access headers without exposing them in logs. | PASS — exercised route | Make History run 2026-11-10 22:33 ICT: authorize HTTP 16 and receipt HTTP 17 both completed after F1, and the API accepted the receipt. The supplied evidence is redacted and contains no bearer or Access credential values. | Keep credentials in protected Make connection/headers; review future History for accidental values. |
| MK-7 | Errors proven to occur before publication are distinguished from ambiguous outcomes. | NOT_RUN | Actual redacted error/status: `REQUIRED_FROM_P0` | Add only observed classifications to `make_error_classes.yaml`; otherwise use `OUTCOME_UNKNOWN`. |
| MK-8 | Operators know not to rerun a posting module manually; recovery starts from the first webhook module. | NOT_RUN | Runbook/evidence: `REQUIRED_FROM_P0` | Add and review the no-manual-rerun instruction. |
| MK-9 | Router has exactly three routes filtered by fixed `channel_key`; fallback is off; one command reaches one route. | PASS — exercised `fb_hanoi` command | Make History run 2026-11-10 22:33 ICT: Router entered the `fb_hanoi` branch; the `ig_venho` and `fb_venho` branches were stopped by their filters. Five operations completed in 8 seconds; no second posting route ran. The other route keys and fallback remain to be exercised. | Test each remaining route key in isolation and record its History branch. |
| MK-10 | Instagram accepts the signed media URL and Meta can fetch it without receiving a Cloudflare Access login page. | NOT_RUN | Redacted result: `REQUIRED_FROM_P0` | Adjust only the TEST edge rule, then retest from Instagram. |
| MK-11 | Instagram output includes the media ID and distinguishes container creation failure from publish failure. | NOT_RUN | Exact field/error evidence: `REQUIRED_FROM_P0` | Keep uncertain outcomes unknown; capture module-level evidence. |
| MK-12 | Each media fetch (both Facebook F1 modules and Instagram I1) catches HTTP errors with one `Ignore`; no authorize/post module runs and the error does not disable the scenario. | CONFIGURED — chờ bằng chứng run | Generator/checker require one terminal `Ignore`; Harry observed an unhandled F1 403 disable the TEST scenario. Runtime routing and active state must be rechecked after re-import. | Re-import the updated TEST blueprint; inject/observe a fetch failure on TEST and confirm the branch stops before authorize, does not retry, and Make does not disable the scenario because of that fetch error. |

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
| Successful FB Hanoi test | PASS | Make History 22:33 ICT: Facebook post ID `1363761820162798_122106835935535879`; TEST DB has the accepted `POST_CREATED` receipt in `RECEIVED`, waiting for apply. |
| Successful FB Ven Ho test | NOT_RUN | `REQUIRED_FROM_P0` |
| Successful Instagram test | NOT_RUN | `REQUIRED_FROM_P0` |
| Invalid image / invalid test credential | NOT_RUN | `REQUIRED_FROM_P0` |
| Duplicate command / interrupted execution | NOT_RUN | `REQUIRED_FROM_P0` |

**Next TEST cases:** (a) execute `ig_venho` and confirm media URL, publish output ID and receipt; (b) replay a command and confirm `ALREADY_AUTHORIZED` without another post; (c) use a broken image and confirm F1 `Ignore` stops before authorize; (d) use a wrong command token and record the safe rejection outcome.

**Gate:** current PASS entries apply only to the tested `fb_hanoi` path; the FB Ven Ho and IG routes still need their own successful TEST runs. Keep production below `LIVE_MANUAL` until all destination-specific MK-1…MK-6 checks pass. MK-7…MK-11 and failure-mode outcomes remain unverified until TEST evidence is reviewed.
