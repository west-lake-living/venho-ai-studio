# Make Growth Engine v2 — TEST runbook

**Scope:** one copied TEST scenario and one verified TEST Facebook Page. Do not edit or run the production scenario. Current capability evidence in `make_capabilities.md` is still `NOT_RUN`; identifiers marked `REQUIRED_FROM_P0` must be supplied by Harry before any posting test.

## Gate before opening Make

- Confirm the Page ID belongs to a disposable TEST Page and the copied scenario is disconnected from production Pages, Instagram and scheduling.
- Get the TEST channel UUID, remote Page ID, scenario ID, webhook route and connection reference from the approved test manifest. Never infer a Page from its display name.
- Ensure the Growth Engine has a migrated disposable TEST database with a current approved delivery, active approval, valid image SHA and current dispatch epoch. The token's command must already exist in that database.
- Keep the TEST scenario schedule off. Run only a manually triggered test bundle after the Page ID and route have been checked.
- Keep credentials in Make connections or server environment variables. Do not paste webhook URLs, bearer tokens, Cloudflare headers or signed media URLs into this runbook, screenshots or execution logs.

## Scenario construction

Make a copy of `VenHo Growth Agent-FB/IG` and label it `TEST — Growth Engine v2`. Use one fixed route for the TEST Facebook Page.

1. **Custom webhook:** create a new TEST only webhook. Do not copy or reuse a production webhook URL.
2. **Router filter:** require all of:
   - `schema_version = growth.command.v2`
   - `environment = test`
   - `channel_id = <verified TEST channel UUID>`
   - fallback route disabled
3. **Fetch media:** HTTP GET the mapped `media_url`, return the binary body and set a 30 second timeout. Continue only for HTTP `200` and `content-type = image/jpeg`. Any other response ends the route before authorize; the outbox can retry while the command is within its window.
4. **Authorize:** HTTP POST `/internal/growth/v2/executions/authorize` with the TEST service bearer and the required Cloudflare Access headers stored in protected connections/environment variables. Map `command_token`, `payload_hash`, and the actual media response status/content type. Never log or screenshot the token or headers.
5. **Authorize filter:** continue only when `execute = true` and current time is earlier than `grant_expires_at_ms`. A false result terminates normally. Do not resume an incomplete execution after this step.
6. **Create photo post:** use the Facebook connection for the verified TEST Page only. Map `message` from the authorize response `caption`; map the binary from step 3. Do not map the caption or image from another bundle or URL.
7. **Success receipt:** HTTP POST `/internal/growth/v2/receipts` with the original command/execution/grant/delivery/revision/channel/Page/payload identity, `outcome = POST_CREATED`, the actual post ID output from step 6, its HTTPS permalink when available, and `event_id = <grant_id>:POST_CREATED`. Inspect the module output bundle to record the real post ID field in `make_capabilities.md`.
8. **Post error handler:** use an error handler that does not retry the Facebook module and does not use Break/Resume. Send `REJECTED_NO_SIDE_EFFECT` only when the exact error class appears in `config/projects/venho_hotel/growth_engine/make_error_classes.yaml`; otherwise send `OUTCOME_UNKNOWN`. Redact the message and any URL query/credentials. Use a deterministic event ID `<grant_id>:<outcome>`.
9. **Optional webhook response:** return a small receipt ACK after the receipt endpoint responds. This response is not proof that Facebook created or verified a post.

Enable sequential processing. Disable incomplete-execution storage where possible; otherwise enforce the no-resume rule above. Check each posting module has no automatic retry. Save these settings as redacted evidence only.

## Required TEST cases

Run each case using the test-command tool and the TEST route only. Record the module outputs and outcome in `docs/growth_engine/make_capabilities.md` after observing them.

| Case | Expected result |
|---|---|
| Valid TEST command | Matching filter only; authorize returns `execute=true`; one photo post on the TEST Page; receipt includes the real returned post ID. |
| Invalid or non-JPEG media | Filter stops before authorize and Facebook. |
| Invalid TEST command token | Authorize returns HTTP 403; Facebook module is not reached. |
| Same command sent twice | The second authorize is `ALREADY_AUTHORIZED`; no second Facebook post. |
| Stop after authorize | Do not resume or rerun the Facebook module. Reconcile from Make History and receipt state. |
| Known pre-publication error | Only the observed class may be added to the YAML list; retryability must also be recorded. |
| Ambiguous Facebook error | Receipt is `OUTCOME_UNKNOWN`; no automatic retry or manual module rerun. |

## Safe test-command sender

`scripts/growth_engine/send_test_command.py --create-command --envelope-file <private-path>` creates a synthetic slot → delivery → revision → approval → command in the isolated SQLite database selected by `GE_DB_PATH`. It requires `GE_ENV=test`, a verified TEST channel/Page ID, a TEST-only HTTPS webhook reference and TEST secrets from the environment. The synthetic JPEG and caption are explicitly labeled test data. The command remains in the local outbox and the private envelope is created with mode `0600`; the command is not sent unless `--send` is also supplied. The sender validates `environment`, the `page_test` manifest/Page identity, signed capability claims and private file permissions before sending. A dry run is the default. To make a network request, an operator must pass `--send` and repeat the configured TEST Page ID with `--confirm-test-page-id`. The webhook URL comes only from the `make_route_ref` variable in the TEST channel manifest. A webhook `ACK` only proves the webhook accepted the envelope; use module History, the receipt inbox and the TEST Page to prove the post result.

The factory refuses placeholder Page/scenario/runtime values and refuses a database that already contains `page_test`; use a dedicated isolated TEST database. Do not handcraft a token or bypass authorize. Add no error class until an observed TEST run proves it safe.
