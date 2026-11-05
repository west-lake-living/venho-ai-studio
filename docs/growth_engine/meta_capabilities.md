# Meta read capability probe — GC2-P0-T04

**Status:** candidate configuration is ready; probes have not been run. No Meta token was available or used in this task. Candidate fields and metrics must be confirmed per account, permission set and API version before they are used by reconciliation or Insights.

Run these from the repository root after the matching read token is present in the environment. No account ID, post ID, field, metric, period or API version needs to be supplied on the command line.

```bash
python3 scripts/growth_engine/probe_meta_read.py --channel fb_hanoi
python3 scripts/growth_engine/probe_meta_read.py --channel fb_venho --list-recent
python3 scripts/growth_engine/probe_meta_read.py --channel ig_venho
```

Required token environment variables:

- `GE_META_READ_TOKEN_FB_HANOI`
- `GE_META_READ_TOKEN_FB_VENHO`
- `GE_META_READ_TOKEN_IG_VENHO`

The probe reads candidates from `config/projects/venho_hotel/growth_engine/meta_probe_candidates.yaml` and checks the account IDs against `channels.yaml`. The candidate version is `v26.0`; Facebook post fields, Page metrics (`period=lifetime`, one metric per request), Instagram media fields and Instagram media metrics (period omitted, one metric per request) remain **unverified**. A metric request error is recorded as `UNSUPPORTED`, then the next candidate metric is attempted. The Facebook Ven Hồ Hotel command enumerates the `posts` edge instead of using a supplied post ID.

| Channel | Candidate account ID | Candidate post/source | Probe result |
|---|---:|---|---|
| `fb_hanoi` | `1124616474074140` | `1124616474074140_122149744263351048` (02/11) | `NOT_RUN` |
| `fb_venho` | `803531149684177` | Recent items via `posts` edge | `NOT_RUN` |
| `ig_venho` | `17841457936965829` | `18098055056408999` (02/11) | `NOT_RUN` |

Record the redacted JSON output, exact readable fields, permission errors and metric results here after the operator runs the commands. Do not paste tokens or full environment-file contents. Do not mark a candidate verified solely because the CLI exited successfully.
