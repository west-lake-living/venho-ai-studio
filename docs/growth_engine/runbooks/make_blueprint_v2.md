# Make Growth Engine v2 — TEST runbook

**Scope:** one copied TEST scenario with three verified TEST destinations and one Router. Do not edit or run the production scenario. `make_capabilities.md` remains `NOT_RUN` until Harry records evidence from the TEST copy.

No webhook URL, access token, credential, signed media URL or production Page ID belongs in this file. Redact module output and screenshots before saving them.

## Gate before opening Make

- Confirm the TEST Facebook Pages and Instagram account are disposable TEST destinations and are distinct from all production IDs.
- Map `fb_hanoi`, `fb_venho` and `ig_venho` to the three TEST destinations using verified IDs. Do not infer a destination from its display name.
- Confirm the TEST channel UUIDs, remote IDs, scenario ID, webhook, connection references and bearer principals in the approved TEST manifest.
- Ensure the Growth Engine has a migrated disposable TEST database with current approved deliveries, valid image variants and commands. The scenario must be disconnected from production Pages, Instagram and scheduling.
- Keep credentials in Make connections or protected environment variables. Do not paste secrets into this runbook, screenshots or execution logs.

## Scenario construction

Duplicate `VenHo Growth Agent-FB/IG` as `TEST — Growth Engine v2`. Keep its schedule off. Use one TEST webhook and a single Router with three branches. Match the contract in §8.1.4 of `GC2_MASTER_PLAN.md`.

1. **Custom webhook and common filter:** receive all three channels. Require `schema_version = growth.command.v2` and `environment = test` before the Router.
2. **Router:** create exactly three branches, each with one fixed equality filter: `channel_key = fb_hanoi`, `channel_key = fb_venho`, or `channel_key = ig_venho`. Disable the fallback route. Each command must match exactly one branch.
3. **Facebook branches (`fb_hanoi`, `fb_venho`):** use the same module sequence with a different fixed TEST Page and a different application bearer on each branch:
   - **F1 — Fetch image:** HTTP GET the mapped `media_url`, return the binary body, timeout 30 seconds. Continue only for HTTP 200 and `content-type = image/jpeg`; otherwise stop before authorize.
   - **F2 — Authorize:** HTTP POST `/internal/growth/v2/executions/authorize` with that branch's bearer and Cloudflare Access headers. Map the command token, payload hash and actual media status/type.
   - **F3 — Grant filter:** continue only when `execute = true` and current time is earlier than `grant_expires_at_ms`. Do not resume an incomplete execution after authorize.
   - **F4 — Facebook photo post:** use the branch's fixed TEST Page; map `message` from F2 `caption` and image from F1 binary. Do not map a URL or another branch's image.
   - **F5 — Success receipt:** HTTP POST `/internal/growth/v2/receipts` with the original identities, `outcome = POST_CREATED`, the actual post ID output from F4, the permalink when available and `event_id = <grant_id>:POST_CREATED`.
   - **F6 — Error receipt:** do not retry, Break or Resume F4. Use `REJECTED_NO_SIDE_EFFECT` only for a verified error class in `make_error_classes.yaml`; otherwise send `OUTCOME_UNKNOWN`. Redact provider text and URLs.
4. **Instagram branch (`ig_venho`):** use its own TEST Instagram account and application bearer:
   - **I1 — URL check:** HTTP GET `media_url` to confirm the signed URL is reachable and returns HTTP 200 with `image/jpeg`. This binary is not mapped to the Instagram posting module.
   - **I2 — Authorize** and **I3 — grant filter:** use the same authorization and expiry conditions as the Facebook branches.
   - **I4 — Instagram photo post:** map `image_url = media_url` and `caption = I2.caption`; Meta fetches the image from the signed URL. Ensure the URL remains usable through `execute_before_ms + 30 minutes` and does not encounter a Cloudflare Access login page.
   - **I5 — Success receipt:** send `POST_CREATED` with the media ID returned by I4 and `event_id = <grant_id>:POST_CREATED`.
   - **I6 — Error receipt:** distinguish a verified container-creation failure from a publish-stage/ambiguous failure; the latter is `OUTCOME_UNKNOWN`. Never retry or resume I4.
5. **Webhook response:** optional. Send a small acknowledgement only after the matching branch's receipt module returns. A webhook ACK does not prove a post was created or verified.

Enable sequential processing. Disable incomplete-execution storage where possible; otherwise enforce the no-resume rule. Confirm every posting module has no automatic retry. Record only redacted module outputs and settings.

## Required TEST cases

Run tests only against the copied scenario and verified TEST destinations. Record module-level outputs and evidence in `make_capabilities.md`.

| Case | Expected result |
|---|---|
| One valid command for each `channel_key` | Exactly one matching Router branch; one TEST post on its mapped destination; receipt contains the actual post/media ID. |
| Broken or non-JPEG media | Route stops before authorize and before the posting module. |
| Invalid TEST command token | Authorize rejects it; the posting module is not reached. |
| Same command sent twice | Second authorize is `ALREADY_AUTHORIZED`; no second post. |
| Stop after authorize | Do not resume or rerun the post module; reconcile from History and receipt state. |
| Known pre-publication error | Record only the observed error class and retryability. |
| Ambiguous Facebook error | Receipt is `OUTCOME_UNKNOWN`; no automatic retry or manual rerun. |
| Instagram container/publish errors | Record the exact observed stage; only a proven pre-publication error may be classified as no-side-effect. |

## MK-1…MK-11 evidence checklist

Complete every row in `docs/growth_engine/make_capabilities.md` from the TEST copy. The checks are: sequential processing; incomplete-execution behavior; no automatic retry/Break; actual post/media ID output; Facebook binary input; custom auth headers; proven pre-publication error classes; no manual module rerun; fixed `channel_key` filters with fallback off; Instagram signed image URL fetch; Instagram media ID and separate container/publish errors.

Keep production publishing below `LIVE_MANUAL` until MK-1…MK-6 pass. MK-7…MK-11 and every destination outcome remain unverified until the TEST evidence is reviewed.

## Safe TEST command sender

`scripts/growth_engine/send_test_command.py --create-command --envelope-file <private-path>` creates a synthetic slot → delivery → revision → approval → command in the isolated SQLite database selected by `GE_DB_PATH`. It requires `GE_ENV=test`, a verified TEST channel/Page ID, TEST-only webhook references and TEST secrets from the environment. The synthetic JPEG and caption are test data; the command stays local unless `--send` is also supplied. The private envelope is mode `0600`.

Before sending, the operator must verify the channel key, TEST destination ID, copied scenario, filters, route bearer and isolated TEST database. Only then may they run `--send --confirm-test-page-id <verified-test-id>`. The sender obtains the webhook from the TEST channel manifest and rejects placeholder configuration. Do not handcraft a token or bypass authorize. Use Make History, receipt state and the TEST destination to prove the result; webhook ACK alone is insufficient.
