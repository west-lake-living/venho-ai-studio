# GC2 v1.2 plan/code deltas

Plan baseline: `GC2_MASTER_PLAN.md` v1.2-CA. Existing committed code and immutable migrations remain authoritative where their names or file layout differ.

| Area | v1.2 plan wording | Committed code shape | Resolution |
|---|---|---|---|
| Target account ID | `remote_account_id` is used for Facebook and Instagram in the domain/schema examples. | SQLite/domain use `remote_account_id` for both platforms; `channels.yaml` keeps the established Facebook key `remote_page_id` and Instagram key `remote_account_id`; Make's Facebook authorize/receipt boundary uses `remote_page_id`. | Keep the existing config/API and database names. Map them at adapters; do not rename fields or edit migrations. |
| Meta read client | Track 0 describes `shared/meta/` and lists a separate `models.py`. | Shared GET-only client and transport/errors are in `shared/meta/graph_client.py`; Growth Engine exposes a thin `GraphClient` adapter; current tests live under `tests/growth_engine/unit/adapters/outbound/meta/`. `get_insights` allows the period to be omitted for the Instagram media candidate. | Keep the committed layout; do not add a duplicate model module. Track 0 probe and legacy analytics import `shared.meta` directly. |
| Track 0 analytics | v1.2 describes legacy registry reconciliation and Insights artifacts under `~/venho/state/growth-reports/`. | Growth Engine also has DB-backed application use cases and SQLite wiring from earlier tasks. | Preserve those v2 use cases. The `venho-analytics` Track 0 commands read the legacy registry/config and write only the external reports path; they do not open the v2 DB. |
| Worker units | P9-T01 names one templated worker unit. | `growth-engine-worker@.service` is instantiated as `publish` and `jobs`; deploy script restarts both instances with the API. | Keep the templated service and document/install both required instances. |
| Python release build | Earlier plan text said `uv sync` without selecting a managed interpreter. | The release must use the project's managed Python 3.11 runtime. | Pin the build command to `UV_PYTHON_PREFERENCE=only-managed ~/.local/bin/uv sync --frozen --python 3.11 --extra api --extra drive --extra gemini`. |
| P0-T04 probe CLI | The old card required account/post/API arguments on every invocation. | Candidate config contains production account IDs, sample post IDs, candidate version/fields/metrics and token environment-variable names; the CLI accepts `--channel`, and `fb_venho` uses `--list-recent`. | Keep commands copy-pasteable with only the three read tokens supplied in the environment; a metric error is reported as `UNSUPPORTED` and does not stop later metrics. |

No existing migration was modified for these deltas.
