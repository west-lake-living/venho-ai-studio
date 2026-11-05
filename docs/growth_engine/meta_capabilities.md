# Meta read capability probe — GC2-P0-T04

**Meta app:** VENHO Growth Read — App ID `1679968647246378` (Development).

**Permission update (2026-11-05):** added only `pages_read_user_content` for reading reactions/comments on Page posts. Meta shows **Ready for testing**. No other permission was changed. Facebook engagement capability is **PENDING_REPROBE**. Missing `shares` field is treated as `ZERO`.

**Status:** read access was verified on 2026-11-05 with Meta Graph API Explorer and the local probe, using read-only requests. Candidate API version is pinned to `v27.0`. Tokens were supplied through environment variables only; they are not stored in the repository.

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
| `fb_hanoi` | `1124616474074140` | `1124616474074140_122150227155351048` | `id`, `created_time`, `permalink_url`, `message`, `from`, and `full_picture` readable. Both lifetime metrics, `post_media_view` and `post_total_media_view_unique`, readable. `reactions` and `comments` previously returned Meta code 10; pending re-probe with the added permission. Missing `shares` is `ZERO`. |
| `fb_venho` | `803531149684177` | Recent `posts` edge; latest observed `803531149684177_1973847183910795` (2026-11-04) | Recent posts edge and base fields (`id`, `created_time`, `permalink_url`, `message`, `from`, `full_picture`) readable. `reactions` and `comments` previously returned Meta code 10; pending re-probe with the added permission. Missing `shares` is `ZERO`. |
| `ig_venho` | `17841457936965829` | `18098373959134505` | Media edge and all configured fields (`id`, `timestamp`, `permalink`, `caption`, `media_type`, `media_url`, `owner`, `username`, `like_count`, `comments_count`) readable. All configured metrics (`reach`, `likes`, `comments`, `shares`, `saved`, `total_interactions`, `views`) readable with period omitted. |

The probe checks account IDs against `channels.yaml`. It tests Facebook post metrics with `period=lifetime`, one metric per request, and Instagram metrics with period omitted, one metric per request. A metric error is recorded as `UNSUPPORTED` and does not stop later metric checks. The `fb_venho` check enumerates its `posts` edge instead of using a fixed post ID.

These results verify read access for the observed accounts and sample objects. They do not change production publishing or reconciliation configuration. Do not paste tokens or full environment-file contents into reports.
