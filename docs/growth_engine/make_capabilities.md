# Make router capability check — GC2-P0-T03

**State (2026-11-11):** TEST run 3 is closed and all four follow-up cases were confirmed in Make History. IG publish, duplicate replay, invalid command token and media-fetch error passed for the exercised routes. `outbox_commands.state=AUTHORIZED` remains the correct terminal transport state. MK-1 remains CONFIGURED; `fb_venho` and MK-11 remain unverified.

**Production scenario:** `VenHo Growth Agent-FB/IG` (ID `5868920`, Active; do not edit).
**TEST scenario:** `VenHo Growth Agent TEST` (ID `6924867`, Active after the 2026-11-11 tests; TEST webhook data structure has 15 fields).
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

- [x] TEST copy exists as `VenHo Growth Agent TEST`, ID `6924867`, with a separate webhook.
- [x] Facebook modules 3 and 12 point to TEST Page `1363761820162798`; Instagram module 6 points to TEST account `@hanhpham1504`, ID `17841472240799413`.
- [x] TEST Router has the three fixed `channel_key` filters and fallback Off, per the 2026-11-10 operator observation; inherited `publication_id` conditions were removed.
- [x] Do not add Webhook response modules while sequential processing is enabled; Make reports they are unsupported in this mode.
- [x] Generated F1/I1 modules use one `Ignore` handler. Hanoi F1 error path was confirmed in Make History; I1 error path remains untested.
- [x] TEST-only credentials and webhook were used; no values are stored here.
- [x] Facebook HTTP media fetches are branch-local; Instagram I1 checks the signed URL and Instagram module 6 receives `media_url`.
- [ ] Ensure every test post is visibly labelled as a test and can be removed by the operator.
- [x] Updated 26-module blueprint was imported; successful webhook runs completed and the scenario remained Active after error-path tests.
- [ ] Recheck the scenario's sequential/concurrency setting before production; MK-1 remains CONFIGURED because parallel behavior was not tested.

## C. Capability evidence matrix

Fill **Result** with `PASS`, `PARTIAL`, `FAIL`, or `NOT_RUN`; use `CONFIGURED — chờ bằng chứng run` for a selected setting whose execution evidence is pending. Attach redacted evidence. Do not infer a pass from a module label or from a webhook 2xx response.

| ID | Check on TEST copy | Result | Evidence / exact observed value | Remediation if FAIL |
|---|---|---|---|---|
| MK-1 | Sequential processing is enabled. | CONFIGURED | TEST scenario 6924867 completed a webhook run; it processed five operations in 8 seconds. The run is consistent with sequential mode; setting remains recorded as configured from the Make UI observation on 2026-11-10. | Keep sequential processing enabled; do not add Webhook response modules. |
| MK-2 | Incomplete executions are disabled, or the runbook explicitly forbids resuming after the response step. | PASS — replay stopped before post | 2026-11-11 10:03:46 ICT: replayed command returned `ALREADY_AUTHORIZED`; Facebook Pages 3 was filtered, with no second execution/receipt. Runbook forbids resume after authorize; Make storage setting itself was not rechecked. | Keep the no-resume rule and review storage setting before production. |
| MK-3 | Facebook/Instagram post modules have no automatic retry and no Break directive. | PARTIAL — duplicate replay | 2026-11-11 10:03:46 ICT: three operations ended at the post-module filter; DB retained one execution/receipt and no second post. This proves replay did not repost, but the posting-module retry setting was not directly inspected or fault-injected. | Visually verify post-module retry/Break settings before production. |
| MK-4 | Each post module returns its real post/media ID in its output bundle. | PASS — Facebook and Instagram paths | Duplicate-case Facebook ID `1363761820162798_122107375689535879`; Instagram media ID `18453049759135668` from 12:16:35 ICT. IG receipt/execution reached `APPLIED`/`REPORTED`; earlier Hanoi receipt also matched History. | Keep receipt mapped verbatim from each module's `id`. |
| MK-5 | The executed route passes the correct image to its post module (Facebook uses that route's downloaded JPEG; Instagram uses the signed image URL). | PASS — `fb_hanoi` and `ig_venho` | Hanoi F1 returned `200 image/jpeg`; IG 12:16:35 ICT passed I1, then Instagram module 6 published after about 9.7 seconds. Meta fetched the signed URL. `fb_venho` remains untested. | Run the successful path once on `fb_venho`. |
| MK-6 | HTTP modules can send the required bearer and Cloudflare Access headers without exposing them in logs. | PASS — Hanoi and IG paths | Authorize/receipt completed in both successful runs. History review did not open modules containing bearer or signed URL values. | Keep credentials protected; avoid opening or exporting secret-bearing module fields during review. |
| MK-7 | Errors proven to occur before publication are distinguished from ambiguous outcomes. | PASS — media and authorize rejection | 11:32:45 F1 and 10:14:07 authorize errors were caught and ended at `Ignore`; neither reached a post module. | Keep pre-publication errors separate from ambiguous post outcomes. |
| MK-8 | Operators know not to rerun a posting module manually; recovery starts from the first webhook module. | PASS — terminal error handling observed | Both error cases ended at `Ignore`; Make run status was Success and the scenario remained Active. No posting-module rerun occurred. | Continue recovery from a fresh webhook command only after reconciling execution/receipt. |
| MK-9 | Router has exactly three routes filtered by fixed `channel_key`; fallback is off; one command reaches one route. | PARTIAL — two route keys exercised | Hanoi runs selected `fb_hanoi`; IG run selected `ig_venho`. Duplicate replay stopped at the Facebook module filter. `fb_venho` remains untested. | Run `fb_venho` in isolation before marking all-route behavior verified. |
| MK-10 | Instagram accepts the signed media URL and Meta can fetch it without receiving a Cloudflare Access login page. | PASS — `ig_venho` | Make History 2026-11-11 12:16:35 ICT: I1/HTTP 25 succeeded, authorize 26, Instagram 6 returned media ID `18453049759135668` after about 9.7 seconds, receipt 27 completed; execution `REPORTED`, receipt `APPLIED`. | Preserve public signed-media access without Cloudflare Access on that path. |
| MK-11 | Instagram output includes the media ID and distinguishes container creation failure from publish failure. | NOT_RUN | Exact field/error evidence: `REQUIRED_FROM_P0` | Keep uncertain outcomes unknown; capture module-level evidence. |
| MK-12 | Each media fetch (both Facebook F1 modules and Instagram I1) catches HTTP errors with one `Ignore`; no authorize/post module runs and the error does not disable the scenario. | PARTIAL | `fb_hanoi` F1 error at 11:32:45 ended at `Ignore`, no authorize/post, scenario Active. IG I1 success is proven; I1 error and `fb_venho` F1 error remain untested. | Exercise the remaining fetch handlers if needed before closing all route-level error checks. |

## D. TEST cases

- [ ] One successful test per `channel_key`; `fb_venho` remains outstanding.
- [x] Broken signed-media URL: F1 `Ignore`; post module not reached. Non-JPEG decoding was not exercised.
- [x] Invalid TEST command token: authorize error caught, then `Ignore`; post module not reached.
- [x] Submit the same command twice: replay stopped before posting; no second execution, receipt or post.
- [ ] Stop after authorize but before the post module: verify the route does not continue or auto-resume.
- [ ] Send one test command per `channel_key`; `fb_venho` route is still missing.
- [x] Instagram image fetch and publish succeeded; container/publish failure behavior remains untested.

| Case | Result | Evidence |
|---|---|---|
| Successful FB Hanoi test | PASS | Make History 22:33 ICT and applied TEST DB receipt: post ID `1363761820162798_122106835935535879`, outcome `POST_CREATED`, execution `REPORTED`, receipt `APPLIED`. |
| Successful FB Ven Ho test | NOT_RUN | Route `fb_venho` has not been exercised. |
| Successful Instagram test | PASS | History 12:16:35 ICT: media ID `18453049759135668`; execution `REPORTED`; receipt `APPLIED`. |
| Invalid media / invalid command token | PASS | F1 11:32:45 → Ignore/no authorize/post; authorize 10:14:07 → caught error/Ignore/no Facebook module; scenario stayed Active. |
| Duplicate command / interrupted execution | PASS — duplicate replay | History 10:03:33 posted once (`…_122107375689535879`), receipt APPLIED. Replay 10:03:46 ended with Facebook module filtered; DB had no second execution/receipt. |

**Remaining TEST gaps:** successful `fb_venho`; Instagram container-creation versus publish-failure distinction (MK-11); visual review of incomplete-execution/retry settings and parallel-processing behavior (MK-1 remains CONFIGURED). MK-12 is partial because only the Hanoi F1 error handler was exercised.

**Gate:** production stays below `LIVE_MANUAL` until remaining target-specific and operational checks pass. `fb_venho` and MK-11 are still unverified.
