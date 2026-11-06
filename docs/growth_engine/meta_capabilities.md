# Meta read capability probe — GC2-P0-T04 / T04b

**Meta app:** VENHO Growth Read — App ID `1679968647246378` (Development).

**Permission update (2026-11-05):** added only `pages_read_user_content` for reading reactions/comments on Page posts. Meta shows **Ready for testing**. No other permission was changed. The v27.0 results supplied on 2026-11-06 confirm reactions/comments are readable on both Facebook Pages. Missing `shares` remains governed by the configured `ZERO` policy; the supplied Hanoi result covers reactions/comments.

**Status:** read access was verified with read-only v27.0 requests. Sanitized evidence is stored in `tests/fixtures/growth_engine/fb_engagement_probe_20261105.json` and `fb_engagement_probe_20261106.json`; it contains only account/post IDs, timestamps, field states and counts. Tokens were supplied through environment variables only; they are not stored in the repository.

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
| `fb_hanoi` | `1124616474074140` | Five posts, 2026-10-28 through 2026-11-04 | v27.0 returned reactions/comments for all five: `1/0`, `1/0`, `0/0`, `0/0`, `2/0`. `facebook_engagement` is `SUPPORTED`. |
| `fb_venho` | `803531149684177` | Recent `posts` edge; three samples dated 2026-11-02 and 2026-11-04 | The sanitized re-probe returned reaction/comment totals for all three samples: `0/0`, `0/0`, and `1/0`. Capability is `SUPPORTED` for this page. The re-probe summary did not include a shares result. |
| `ig_venho` | `17841457936965829` | `18098373959134505` | Media edge and all configured fields (`id`, `timestamp`, `permalink`, `caption`, `media_type`, `media_url`, `owner`, `username`, `like_count`, `comments_count`) readable. All configured metrics (`reach`, `likes`, `comments`, `shares`, `saved`, `total_interactions`, `views`) readable with period omitted. |

The probe checks account IDs against `channels.yaml`. It tests Facebook post metrics with `period=lifetime`, one metric per request, and Instagram metrics with period omitted, one metric per request. A metric error is recorded as `UNSUPPORTED` and does not stop later metric checks. The `fb_venho` check enumerates its `posts` edge instead of using a fixed post ID.

These results verify read access for the observed accounts and sample objects. They do not change production publishing or reconciliation configuration. Do not paste tokens or full environment-file contents into reports.

`config/projects/venho_hotel/growth_engine/metrics_registry.yaml` enables `facebook_engagement` for `fb_hanoi` and `fb_venho`, while keeping the default `BLOCKED` for unverified channels. P0-T04b is DONE. The current sample set does not include `post_total_media_view_unique` for the same `fb_venho` posts, so that page's internal engagement rate stays `DATA_INCOMPLETE` until matching denominators are collected.
