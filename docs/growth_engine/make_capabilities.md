# Make router capability check — GC2-P0-T03

**State:** checklist ready; no Make scenario was opened or changed in this run.

**Scenario named in the request:** `VenHo Growth Agent-FB/IG`
**Test requirement:** use a copied scenario and test accounts only. Do not use live pages for capability tests.

No webhook URL, access token, or credential belongs in this file. Store only redacted screenshots/output, and blur connection details before attaching evidence.

## A. Read-only inventory of the current scenario

Complete this section from the Make scenario and one recent successful History run. Do not edit the production scenario during inventory.

| Item | Value/evidence |
|---|---|
| Scenario ID | `REQUIRED_FROM_P0` |
| Observed at (ICT) | `REQUIRED_FROM_P0` |
| Router branch names and order | `REQUIRED_FROM_P0` |
| Filter expression on each branch | `REQUIRED_FROM_P0` |
| Fallback route enabled | `REQUIRED_FROM_P0` |
| Facebook/Instagram post module names | `REQUIRED_FROM_P0` |
| Error handler path on each post module | `REQUIRED_FROM_P0` |
| Sequential processing | `REQUIRED_FROM_P0` |
| Incomplete-execution setting | `REQUIRED_FROM_P0` |
| Exact post/media ID output field | `REQUIRED_FROM_P0` |
| Evidence from successful History run | redacted screenshot/export, no tokens or URLs |

For the post ID, inspect the output bundle of the posting module itself. Record the actual returned field name and a synthetic-looking redacted example. Do not record a UI label such as `3. Post ID` as if it were the returned ID.

## B. Prepare the TEST copy

- [ ] Duplicate `VenHo Growth Agent-FB/IG`; name the copy with a clear `TEST` suffix.
- [ ] Confirm all three test destinations are test Page/IG accounts, not production accounts.
- [ ] Confirm the TEST Router has one fixed `channel_key` filter per branch and fallback is off.
- [ ] Use test-only credentials and a test-only webhook. Do not paste secrets into this file.
- [ ] Ensure every test post is visibly labelled as a test and can be removed by the operator.
- [ ] Disable scheduling on the TEST copy; use only a manually initiated test bundle after the test account is confirmed.

## C. Capability evidence matrix

Fill **Result** with `PASS`, `FAIL`, or `NOT_RUN`; attach redacted evidence. Do not infer a pass from a module label or from a webhook 2xx response.

| ID | Check on TEST copy | Result | Evidence / exact observed value | Remediation if FAIL |
|---|---|---|---|---|
| MK-1 | Sequential processing is enabled. | NOT_RUN | `REQUIRED_FROM_P0` | Enable it, then capture the setting. |
| MK-2 | Incomplete executions are disabled, or the runbook explicitly forbids resuming after the response step. | NOT_RUN | `REQUIRED_FROM_P0` | Disable storage or document and enforce the no-resume rule. |
| MK-3 | Facebook/Instagram post modules have no automatic retry and no Break directive. | NOT_RUN | `REQUIRED_FROM_P0` | Remove automatic retry/Break; ambiguous outcomes must be reconciled. |
| MK-4 | Each post module returns its real post/media ID in its output bundle. | NOT_RUN | Exact field: `REQUIRED_FROM_P0` | Remap from the module output; never use a mapping label as a value. |
| MK-5 | Facebook post module receives the downloaded JPEG binary from the HTTP module. | NOT_RUN | `REQUIRED_FROM_P0` | Map the binary output; do not ask Facebook module to fetch an arbitrary URL. |
| MK-6 | HTTP modules can send the required bearer and Cloudflare Access headers without exposing them in logs. | NOT_RUN | `REQUIRED_FROM_P0` | Keep production gate closed until proven. |
| MK-7 | Errors proven to occur before publication are distinguished from ambiguous outcomes. | NOT_RUN | Actual redacted error/status: `REQUIRED_FROM_P0` | Add only observed classifications to `make_error_classes.yaml`; otherwise use `OUTCOME_UNKNOWN`. |
| MK-8 | Operators know not to rerun a posting module manually; recovery starts from the first webhook module. | NOT_RUN | Runbook/evidence: `REQUIRED_FROM_P0` | Add and review the no-manual-rerun instruction. |
| MK-9 | Router filters on the fixed `channel_key` for each route; fallback is off; one command reaches one route. | NOT_RUN | `REQUIRED_FROM_P0` | Correct filters and test each channel key independently. |
| MK-10 | Instagram accepts the signed media URL and Meta can fetch it without receiving a Cloudflare Access login page. | NOT_RUN | Redacted result: `REQUIRED_FROM_P0` | Adjust only the TEST edge rule, then retest from Instagram. |
| MK-11 | Instagram output includes the media ID and distinguishes container creation failure from publish failure. | NOT_RUN | Exact field/error evidence: `REQUIRED_FROM_P0` | Keep uncertain outcomes unknown; capture module-level evidence. |

## D. TEST cases to run after destinations and credentials are confirmed

- [ ] One successful test per test channel; save module-level outputs and verify the returned ID on that test destination.
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
