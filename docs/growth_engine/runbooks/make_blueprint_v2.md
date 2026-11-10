# Make Growth Engine v2 — TEST runbook

**Scope:** one copied TEST scenario with three logical TEST targets and one Router. Do not edit or run the production scenario. MK-1 is configured; run evidence is pending. Other capability checks remain unrun.

No webhook URL, access token, credential, signed media URL or production Page ID belongs in this file. Redact module output and screenshots before saving them.

## Quan sát production — 06/11/2026

Nguồn: cấu hình giao diện Make do Harry cung cấp; **chưa có run MK và chưa có kiểm chứng độc lập từ History**. Production scenario `VenHo Growth Agent-FB/IG` (ID `5868920`) đang Active, không được sửa. Router có thứ tự hiện tại: Facebook Pages module 3, Instagram module 6, Facebook Pages module 12. Nhánh 1 và 3 dùng cùng filter `platform = facebook` AND `publication_id` không chứa `test`; Instagram dùng `platform = instagram` AND `publication_id` không chứa `test`. Cả ba fallback Off. Các filter chưa xét `channel_key`, nên một payload Facebook có thể chạy cả hai nhánh Page. HTTP `Download a file` nằm trước Router; Instagram cũng tải binary dù module đăng Instagram dùng URL. Webhook response module 8 nằm ở nhánh 1, module 7 ở nhánh Instagram; nhánh module 12 chưa có response.

Filter `Venho signature` nằm trên liên kết Custom webhook → HTTP ở production và TEST. Theo quan sát do Harry cung cấp, filter so sánh header `x-venho-signature` với kết quả `sha256(publication_id : idempotency_key : <fixed 64-character hex literal>)`. Không lưu hay sao chép literal đó. Bản chất của literal (muối hay bí mật dùng chung) là **CHƯA XÁC MINH**. Hợp đồng v2 không dùng filter này: API authorize kiểm tra bearer theo route cùng `command_token` có chữ ký; filter chung dùng `schema_version` và `environment`.

## Quan sát scenario TEST trước lần import K4 — 10/11/2026

Nguồn: trạng thái giao diện do Harry cung cấp sau khi chỉnh tay; chưa có kiểm chứng độc lập từ Make History. Giữ nguyên các thay đổi này, không dựng lại.

- Scenario TEST `VenHo Growth Agent TEST` (ID `6924867`): Webhook module `2` có data structure 15 trường; các mapping lấy dữ liệu lệnh dùng `{{2.<field>}}`.
- Filter Webhook → HTTP `v2 TEST common`: `schema_version = growth.command.v2` AND `environment = test`. Filter `Venho signature` đã được gỡ.
- Router module `5`, fallback Off cả ba nhánh: `fb_hanoi` → Facebook Pages `3` → Webhook response `8`; `ig_venho` → Instagram `6` → Webhook response `7`; `fb_venho` → Facebook Pages `12` → Webhook response `13`.
- HTTP tải ảnh module `4` vẫn nằm trước Router. Việc cần làm cho K4 là đưa một HTTP GET `media_url` vào từng nhánh Facebook và map binary của từng HTTP riêng vào module Facebook cùng nhánh. Nhánh Instagram dùng URL `media_url` trực tiếp.
- Bản export có URL literal trong mapper body của hai Webhook response hiện hữu. Không sao chép URL đó vào import/log/báo cáo. Ý tưởng ACK draft trước đây bị thay thế bởi quyết định sequential processing ghi ở mục kết quả import bên dưới.
- Không thay filter, connection, Page/Instagram ID đích TEST hiện có. Giữ nguyên cấu hình scenario khác; trigger/active state không được xác nhận trong lần rà soát này.
- Export mới có HTTP request module `14` và directive `Skip` module `15` trong error handler của Facebook Pages `3`. HTTP request là `POST`, body JSON string có mapping lệnh và hai header placeholders. Draft dùng cấu trúc module này làm template, xóa 14/15 khỏi vị trí mẫu, rồi cấp ID mới từ 16.
- HTTP 14 trong export có header `Authorization` và `CF-Access-Client-Id`; draft thêm `CF-Access-Client-Secret` placeholder theo ADR-06. `Authentication type = API key` là phương án có thể khảo sát để giữ bearer, nhưng hiện **CHƯA XÁC MINH**; draft chỉ dùng custom `Authorization` header placeholder.
- Hai URL literal di sản production nằm ở `mapper.body` của Webhook response modules `7` và `8`. Không ghi hoặc sao chép giá trị; import draft tuần tự loại bỏ cả ba Webhook response module nên các URL đó không được mang sang.
- Bản import K4 trước quyết định sequential có chuỗi `fb_hanoi` `4 → 16 → 3 → 17 → 8`, `ig_venho` `25 → 26 → 6 → 27 → 7`, `fb_venho` `20 → 21 → 12 → 22 → 13`; lỗi được ghi riêng. Chuỗi này được thay bằng draft mới không có responder trong mục kết quả import bên dưới.
- History production `5868920`, run `09/11/2026` (Harry cung cấp, chỉ đọc) xác nhận Facebook Pages `3/12` trả `id` dạng `<page_id>_<post_id>` và không có `post_id`; draft map nguyên `id` vào `platform_post_id`, không tách trong Make. Instagram module `6` trả `id` media.
- History xác nhận HTTP `Download a file` trả `data`, `headers` với key chữ thường như `content-type`, `statusCode` dạng number, `fileName` và `fileSize`. F1/I1 filter dùng `statusCode = 200` AND `headers.content-type = image/jpeg`.
- Trước lần import này K4 chưa chạy scenario và MK-1…MK-11 chưa được ghi. Sau quan sát import, MK-1 là **CONFIGURED — chờ bằng chứng run**, chưa phải PASS; vẫn **CHƯA XÁC MINH**: output cụ thể của HTTP `Make a request` authorize/receipt, cú pháp `formatDate(now; "x")`, hành vi Skip trong error handler và Authentication type `API key`.

## Kết quả import TEST — 10/11/2026

Nguồn: quan sát trực tiếp của Harry trong Make sau import. Không sửa scenario production.

- Import làm giao diện HTTP hiển thị Method trống ở các request; so với module mẫu 14, blueprint lưu `mapper.method` bằng enum chữ thường (`post`). Generator trước đó ghi `POST`; đã đổi mọi HTTP request sang `post`/`get` theo định dạng export.
- I1 (HTTP 25) là `get` và không gửi body. Generator bỏ `contentType`, `inputMethod` và `jsonStringBodyContent` khỏi mapper của I1 để không tạo body JSON rỗng.
- UI sau import hiển thị lịch `Every 15 minutes`, trong khi export gốc có `metadata.instant = true`. Generator giữ `metadata.instant = true`; checker từ chối blueprint không còn trigger ngay khi webhook nhận dữ liệu. Cần xác nhận lại trên UI sau import mới.
- Harry chọn sequential processing sau cảnh báo `Responder is not supported when scenario is configured for sequential processing`. Draft đặt `metadata.scenario.sequential = true` và bỏ Webhook response `8`, `7`, `13`. Các nhánh kết thúc ở receipt tương ứng. MK-1 được ghi CONFIGURED, chờ bằng chứng run; chưa có History run.
- Các quan sát trước đây về filter, ba route, Page/IG TEST đích, connection, caption `16.data.caption`, cùng module HTTP 4 trước Router vẫn được giữ làm bằng chứng người vận hành; không dựng lại cấu hình thủ công.

## Gate before opening Make

- Confirm the TEST Facebook Page and Instagram account are disposable TEST destinations and are distinct from all production IDs.
- Map `fb_hanoi` and `fb_venho` to the verified Facebook TEST Page, and `ig_venho` to the verified Instagram TEST account. Do not infer a destination from its display name.
- SQLite requires a unique remote account per platform and environment. When both Facebook branches use the same TEST Page, use a separate disposable TEST database and matching TEST API instance for each branch; never bind the other branch's command to the active API database. Instagram also uses an isolated TEST database.
- Confirm the TEST channel UUIDs, remote IDs, scenario ID, webhook, connection references and bearer principals in the approved TEST manifest.
- Ensure the Growth Engine has a migrated disposable TEST database with current approved deliveries, valid image variants and commands. The scenario must be disconnected from production Pages, Instagram and scheduling.
- Keep credentials in Make connections or protected environment variables. Do not paste secrets into this runbook, screenshots or execution logs.

## Scenario construction

Use the existing copy `VenHo Growth Agent TEST` (ID `6924867`); do not duplicate or edit production. Keep the current webhook data structure, common filter, Router filters, branch order, connections and TEST destinations listed above. Keep the scenario inactive outside an approved test window and preserve the immediate webhook trigger (`metadata.instant = true`); do not replace it with an interval schedule. Match §8.1.4 of `GC2_MASTER_PLAN.md`, with the following TEST-specific branch assignments:

1. **Custom webhook and common filter:** retain module `2` and the existing 15-field data structure. The filter before the Router requires `schema_version = growth.command.v2` and `environment = test`; the old `Venho signature` filter is removed. Payload mapping references use module `2`.
2. **Router:** retain module `5`, the fixed equality filters and no fallback: branch 1 `channel_key = fb_hanoi` → Facebook Pages module `3`; branch 2 `channel_key = ig_venho` → Instagram module `6`; branch 3 `channel_key = fb_venho` → Facebook Pages module `12`. Each command must match exactly one branch.
3. **Facebook branches (`fb_hanoi` → module 3, `fb_venho` → module 12):** both use verified TEST Page `1363761820162798` and a distinct route bearer. Put a separate HTTP GET `media_url` download inside each branch (duplicate the existing HTTP module or move it into each route); each Facebook module must receive the binary from its own branch's HTTP output:
   - **F1 — Fetch image:** HTTP GET the mapped `media_url`, return the binary body, timeout 30 seconds. Continue only for HTTP 200 and `content-type = image/jpeg`; otherwise stop before authorize.
   - **F2 — Authorize:** HTTP POST `/internal/growth/v2/executions/authorize` with that branch's bearer and Cloudflare Access headers. Map the command token, payload hash and actual media status/type.
   - **F3 — Grant filter:** continue only when `execute = true` and current time is earlier than `grant_expires_at_ms`. Do not resume an incomplete execution after authorize.
   - **F4 — Facebook photo post:** use the branch's fixed TEST Page; map `message` from F2 `caption` and image from F1 binary. Do not map a URL or another branch's image.
   - **F5 — Success receipt:** HTTP POST `/internal/growth/v2/receipts` with the original identities, `outcome = POST_CREATED`, Facebook Pages `id` mapped verbatim to `platform_post_id`, the permalink when available and `event_id = <grant_id>:POST_CREATED`. Do not extract the suffix in Make; split server-side only if the domain needs the plain post ID.
   - **F6 — Error receipt:** do not retry, Break or Resume F4. Use `REJECTED_NO_SIDE_EFFECT` only for a verified error class in `make_error_classes.yaml`; otherwise send `OUTCOME_UNKNOWN`. Redact provider text and URLs. Follow F6 with the exported `Ignore` directive (shown as **Skip**): it records the error receipt, then drops the failed bundle without retry/resume. Verify in TEST that the success receipt is not reached after this handler.
4. **Instagram branch (`ig_venho` → module 6):** use the linked TEST Instagram account and its route bearer. Map the image URL directly from `media_url`; do not map the binary from HTTP:
   - **I1 — URL check:** HTTP GET `media_url` to confirm the signed URL is reachable and returns HTTP 200 with `image/jpeg`. This binary is not mapped to the Instagram posting module.
   - **I2 — Authorize** and **I3 — grant filter:** use the same authorization and expiry conditions as the Facebook branches.
   - **I4 — Instagram photo post:** map `image_url = media_url` and `caption = I2.caption`; Meta fetches the image from the signed URL. Ensure the URL remains usable through `execute_before_ms + 30 minutes` and does not encounter a Cloudflare Access login page.
   - **I5 — Success receipt:** map Instagram module `id` (media ID) to `platform_post_id` with `outcome = POST_CREATED` and `event_id = <grant_id>:POST_CREATED`.
   - **I6 — Error receipt:** distinguish a verified container-creation failure from a publish-stage/ambiguous failure; the latter is `OUTCOME_UNKNOWN`. Never retry or resume I4. Follow I6 with the `Ignore` (**Skip**) directive for the same no-retry/no-resume reason; verify error-path routing in TEST.
5. **Webhook responses:** do not add explicit `Webhook response` modules while sequential processing is enabled. Make reports responders are unsupported with this setting. Each branch ends at its receipt request; the explicit webhook ACK is omitted.

### Credentials for TEST HTTP modules

Keep placeholders in a blueprint draft; supply values only in the Make TEST scenario after import. Never put a production value in this table or in an import file.

| Placeholder | Make field/use | Storage behavior in Make |
|---|---|---|
| `https://set-in-make.invalid` | Replace HTTP base with `https://ge-test.venhohotel.com` for `/internal/growth/v2/*` calls. | TEST host verified; protected credential storage remains **CHƯA XÁC MINH**. |
| `__SET_IN_MAKE_BEARER_FB_HANOI__` | Replace with `GE_TEST_BEARER_FB_HANOI` from the mode-600 server handoff file. | Copy to `fb_hanoi` authorize/receipt modules; delete the handoff file after copying. |
| `__SET_IN_MAKE_BEARER_FB_VENHO__` | Replace with `GE_TEST_BEARER_FB_VENHO` from the mode-600 server handoff file. | Copy to `fb_venho` authorize/receipt modules; delete the handoff file after copying. |
| `__SET_IN_MAKE_BEARER_IG_VENHO__` | Replace with `GE_TEST_BEARER_IG` from the mode-600 server handoff file. | Copy to `ig_venho` authorize/receipt modules; delete the handoff file after copying. |
| `__SET_IN_MAKE_ACCESS_CLIENT_ID__` | Replace with Access service token Client ID from the operator credential manager. | Do not put it in the API env file or repo. |
| `__SET_IN_MAKE_ACCESS_CLIENT_SECRET__` | Replace with Access service token Client Secret from the operator credential manager. | Do not put it in the API env file or repo. |

After blueprint import, Make may reset the scenario schedule to **Every 15 minutes**. Before running: set it to **Immediately as data arrives**, save the scenario, then open HTTP module `25` (I1), confirm Method `GET` and no body, and click **Save** on that module. Recheck sequential processing remains enabled and no Webhook response modules were added.

Do not assume that Make masks values in blueprint exports, history or error logs. Confirm the storage and redaction behavior before entering credentials.

The HTTP module's **Authentication type = API key** may be an alternative protected bearer configuration. This option and its masking/export behavior are **CHƯA XÁC MINH**; the draft keeps bearer as an explicit placeholder in the custom `Authorization` header.

Before importing a generated draft, run `python3 scripts/growth_engine/check_make_blueprint.py _incoming/make_test_import.json`. The checker reports structural counts and error categories only; a passing result does not prove that Make will import the blueprint or that a TEST run is safe.

To recreate the ignored draft from the protected export, run `umask 077` followed by `python3 scripts/growth_engine/prepare_make_test_blueprint.py`. The helper refuses unsupported export shapes and never prints blueprint values. Replace the TEST API placeholder with `https://ge-test.venhohotel.com` in Make.

For Make Free, the scenario limit reported by Harry is **two active scenarios maximum**. Keep the TEST copy inactive outside its test window; before activating it, confirm the account will not exceed the two-scenario limit. This is an operator-provided plan fact and has not been independently verified in Make.

Keep sequential processing enabled (MK-1 CONFIGURED — run evidence pending). Preserve the immediate webhook trigger. Disable incomplete-execution storage where possible; otherwise enforce the no-resume rule. Do not add explicit Webhook response modules. Confirm every posting module has no automatic retry. Record only redacted module outputs and settings.

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
