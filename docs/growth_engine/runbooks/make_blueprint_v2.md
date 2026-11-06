# Make Growth Engine v2 — TEST runbook

**Scope:** one copied TEST scenario with three logical TEST targets and one Router. Do not edit or run the production scenario. `make_capabilities.md` remains `NOT_RUN` until Harry records evidence from the TEST copy.

No webhook URL, access token, credential, signed media URL or production Page ID belongs in this file. Redact module output and screenshots before saving them.

## Quan sát production và TEST — 06/11/2026

Nguồn: cấu hình giao diện Make do Harry cung cấp; **chưa có run MK và chưa có kiểm chứng độc lập từ History**. Production scenario `VenHo Growth Agent-FB/IG` (ID `5868920`) đang Active, không được sửa. Router có thứ tự hiện tại: Facebook Pages module 3, Instagram module 6, Facebook Pages module 12. Nhánh 1 và 3 dùng cùng filter `platform = facebook` AND `publication_id` không chứa `test`; Instagram dùng `platform = instagram` AND `publication_id` không chứa `test`. Cả ba fallback Off. Các filter chưa xét `channel_key`, nên một payload Facebook có thể chạy cả hai nhánh Page. HTTP `Download a file` nằm trước Router; Instagram cũng tải binary dù module đăng Instagram dùng URL. Webhook response module 8 nằm ở nhánh 1, module 7 ở nhánh Instagram; nhánh module 12 chưa có response.

Filter `Venho signature` nằm trên liên kết Custom webhook → HTTP ở production và TEST. Theo quan sát do Harry cung cấp, filter so sánh header `x-venho-signature` với kết quả `sha256(publication_id : idempotency_key : <fixed 64-character hex literal>)`. Không lưu hay sao chép literal đó. Bản chất của literal (muối hay bí mật dùng chung) là **CHƯA XÁC MINH**. Hợp đồng v2 không dùng filter này: API authorize kiểm tra bearer theo route cùng `command_token` có chữ ký; filter chung dùng `schema_version` và `environment`.

TEST scenario `VenHo Growth Agent TEST` (ID `6924867`) đang Inactive, webhook riêng nhưng chưa có data structure. Module Facebook 3 và 12 trỏ Page TEST `1363761820162798`; Instagram 6 trỏ `@hanhpham1504` (ID `17841472240799413`). Scenario TEST hiện vẫn kế thừa filter chữ ký production, các filter Router chưa xét `channel_key`, và chưa có Webhook response ở nhánh module 12. Chưa chạy scenario TEST. Sequential processing, retry/error handlers, output ID fields và mọi MK-1…MK-11 vẫn **CHƯA XÁC MINH**.

## Gate before opening Make

- Confirm the TEST Facebook Page and Instagram account are disposable TEST destinations and are distinct from all production IDs.
- Map `fb_hanoi` and `fb_venho` to the verified Facebook TEST Page, and `ig_venho` to the verified Instagram TEST account. Do not infer a destination from its display name.
- SQLite requires a unique remote account per platform and environment. When both Facebook branches use the same TEST Page, use a separate disposable TEST database and matching TEST API instance for each branch; never bind the other branch's command to the active API database. Instagram also uses an isolated TEST database.
- Confirm the TEST channel UUIDs, remote IDs, scenario ID, webhook, connection references and bearer principals in the approved TEST manifest.
- Ensure the Growth Engine has a migrated disposable TEST database with current approved deliveries, valid image variants and commands. The scenario must be disconnected from production Pages, Instagram and scheduling.
- Keep credentials in Make connections or protected environment variables. Do not paste secrets into this runbook, screenshots or execution logs.

## Scenario construction

Use the existing inactive copy `VenHo Growth Agent TEST` (ID `6924867`); do not duplicate or edit production. Keep TEST schedule off. Use its TEST webhook and one Router with three branches. Match §8.1.4 of `GC2_MASTER_PLAN.md`, with the following TEST-specific branch assignments:

1. **Custom webhook and common filter:** receive all three channels. Require `schema_version = growth.command.v2` and `environment = test` before the Router.
   - Remove the inherited `Venho signature` filter from the TEST webhook → HTTP link; this v2 path does not use that legacy signature check.
2. **Router:** configure three fixed equality filters and no fallback: branch 1 `channel_key = fb_hanoi` → Facebook Pages module 3; branch 2 `channel_key = ig_venho` → Instagram module 6; branch 3 `channel_key = fb_venho` → Facebook Pages module 12. Remove the inherited `publication_id`-does-not-contain-`test` condition from all TEST routes. Each command must match exactly one branch.
3. **Facebook branches (`fb_hanoi` → module 3, `fb_venho` → module 12):** both use verified TEST Page `1363761820162798` and a distinct route bearer. Put a separate HTTP GET `media_url` download inside each branch (duplicate the existing HTTP module or move it into each route); each Facebook module must receive the binary from its own branch's HTTP output:
   - **F1 — Fetch image:** HTTP GET the mapped `media_url`, return the binary body, timeout 30 seconds. Continue only for HTTP 200 and `content-type = image/jpeg`; otherwise stop before authorize.
   - **F2 — Authorize:** HTTP POST `/internal/growth/v2/executions/authorize` with that branch's bearer and Cloudflare Access headers. Map the command token, payload hash and actual media status/type.
   - **F3 — Grant filter:** continue only when `execute = true` and current time is earlier than `grant_expires_at_ms`. Do not resume an incomplete execution after authorize.
   - **F4 — Facebook photo post:** use the branch's fixed TEST Page; map `message` from F2 `caption` and image from F1 binary. Do not map a URL or another branch's image.
   - **F5 — Success receipt:** HTTP POST `/internal/growth/v2/receipts` with the original identities, `outcome = POST_CREATED`, the actual post ID output from F4, the permalink when available and `event_id = <grant_id>:POST_CREATED`.
   - **F6 — Error receipt:** do not retry, Break or Resume F4. Use `REJECTED_NO_SIDE_EFFECT` only for a verified error class in `make_error_classes.yaml`; otherwise send `OUTCOME_UNKNOWN`. Redact provider text and URLs.
4. **Instagram branch (`ig_venho` → module 6):** use the linked TEST Instagram account and its route bearer. Map the image URL directly from `media_url`; do not map the binary from HTTP:
   - **I1 — URL check:** HTTP GET `media_url` to confirm the signed URL is reachable and returns HTTP 200 with `image/jpeg`. This binary is not mapped to the Instagram posting module.
   - **I2 — Authorize** and **I3 — grant filter:** use the same authorization and expiry conditions as the Facebook branches.
   - **I4 — Instagram photo post:** map `image_url = media_url` and `caption = I2.caption`; Meta fetches the image from the signed URL. Ensure the URL remains usable through `execute_before_ms + 30 minutes` and does not encounter a Cloudflare Access login page.
   - **I5 — Success receipt:** send `POST_CREATED` with the media ID returned by I4 and `event_id = <grant_id>:POST_CREATED`.
   - **I6 — Error receipt:** distinguish a verified container-creation failure from a publish-stage/ambiguous failure; the latter is `OUTCOME_UNKNOWN`. Never retry or resume I4.
5. **Webhook response:** add one response module to each of the three TEST branches, after that branch's receipt module. Send a small acknowledgement only after the receipt returns. A webhook ACK does not prove a post was created or verified.

For Make Free, the scenario limit reported by Harry is **two active scenarios maximum**. Keep the TEST copy inactive outside its test window; before activating it, confirm the account will not exceed the two-scenario limit. This is an operator-provided plan fact and has not been independently verified in Make.

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

`scripts/growth_engine/send_test_command.py --create-command --envelope-file <private-path>` creates a synthetic slot → delivery → revision → approval → command in the isolated SQLite database selected by `GE_DB_PATH`. Set `GE_TEST_CHANNEL_KEY` explicitly to `fb_hanoi`, `fb_venho` or `ig_venho`, and set a distinct `GE_TEST_CHANNEL_ID` for that branch. Facebook uses `GE_TEST_REMOTE_PAGE_ID`; Instagram uses `GE_TEST_REMOTE_IG_ID`. The matching TEST manifest entry, Graph version and TEST-only webhook reference must be verified. The synthetic JPEG and caption are test data; the command stays local unless `--send` is also supplied. The private envelope is mode `0600`.

Before sending, the operator must verify the channel key, TEST destination ID, copied scenario, filters, route bearer and isolated TEST database, and obtain Harry's approval for any public test post. Only then may they run `--send --confirm-test-remote-id <verified-test-id>`. The sender obtains the webhook from the TEST channel manifest, rejects production IDs and placeholder configuration, and checks the envelope's channel key and platform. Do not handcraft a token or bypass authorize. Use Make History, receipt state and the TEST destination to prove the result; webhook ACK alone is insufficient.
