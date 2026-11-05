# Meta read capability probe — GC2-P0-T04 / T04b

**Meta app:** VENHO Growth Read — App ID `1679968647246378` (Development).

**Permission update (2026-11-05):** added only `pages_read_user_content` for reading reactions/comments on Page posts. Meta shows **Ready for testing**. No other permission was changed. The 2026-11-05 sanitized probe supports reactions/comments on `fb_venho`; `fb_hanoi` remains blocked because those fields were not returned for its sample. Missing `shares` is treated as `ZERO` by the configured collection policy; the sanitized output did not include a separate shares observation.

**Status:** read access was verified on 2026-11-05 with Meta Graph API Explorer and the local probe, using read-only requests. The sanitized local report is stored as `tests/fixtures/growth_engine/fb_engagement_probe_20261105.json`; it contains only account/post IDs, timestamps, field states and counts. Candidate API version is pinned to `v27.0`. Tokens were supplied through environment variables only; they are not stored in the repository.

Run these from the repository root when repeating the checks:

```bash
uv run --no-sync python scripts/growth_engine/probe_meta_read.py --channel fb_hanoi
uv run --no-sync python scripts/growth_engine/probe_meta_read.py --channel fb_venho --list-recent
uv run --no-sync python scripts/growth_engine/probe_meta_read.py --channel ig_venho
```

Required token environment variables:

- `GE_META_READ_TOKEN_FB_HANOI`
- `GE_META_READ_TOKEN_FB_VENHO`
- `GE_META_READ_TOKEN_IG_VENHO`

| Channel | Account ID | Sample/source | Verified result |
|---|---:|---|---|
| `fb_hanoi` | `1124616474074140` | `1124616474074140_122150227155351048` | Base fields and both lifetime view metrics remain readable. The sanitized re-probe reported `reactions` and `comments` as `NOT_RETURNED` and supplied no error code. A previous probe returned Meta code 10. Capability remains `BLOCKED`. |
| `fb_venho` | `803531149684177` | Recent `posts` edge; three samples dated 2026-11-02 and 2026-11-04 | The sanitized re-probe returned reaction/comment totals for all three samples: `0/0`, `0/0`, and `1/0`. Capability is `SUPPORTED` for this page. The re-probe summary did not include a shares result. |
| `ig_venho` | `17841457936965829` | `18098373959134505` | Media edge and all configured fields (`id`, `timestamp`, `permalink`, `caption`, `media_type`, `media_url`, `owner`, `username`, `like_count`, `comments_count`) readable. All configured metrics (`reach`, `likes`, `comments`, `shares`, `saved`, `total_interactions`, `views`) readable with period omitted. |

The probe checks account IDs against `channels.yaml`. It tests Facebook post metrics with `period=lifetime`, one metric per request, and Instagram metrics with period omitted, one metric per request. A metric error is recorded as `UNSUPPORTED` and does not stop later metric checks. The `fb_venho` check enumerates its `posts` edge instead of using a fixed post ID.

These results verify read access for the observed accounts and sample objects. They do not change production publishing or reconciliation configuration. Do not paste tokens or full environment-file contents into reports.

`config/projects/venho_hotel/growth_engine/metrics_registry.yaml` enables `facebook_engagement` only for `fb_venho`. `fb_hanoi` stays `BLOCKED` until a probe returns reactions/comments. The current sample set does not include `post_total_media_view_unique` for the same `fb_venho` posts, so the internal engagement rate stays `DATA_INCOMPLETE` until matching denominators are collected.
