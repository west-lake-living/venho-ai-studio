# Growth runner on asus-server

Since 2026-10-21 every scheduled Growth job runs here, not on GitHub Actions:
GitHub's `schedule` started 09:00 posts hours late, and its runners have no
`assets/raw/` reference photos (gitignored), so every post drafted there since
28/08/2026 shipped a fallback stock photo.

| Timer | Mode | When (ICT) |
|---|---|---|
| `venho-growth-publish-0900.timer` | `primary` (dispatch, `--require-dispatch`) | Mon/Wed/Fri/Sat 09:00 |
| `venho-growth-publish-1700.timer` | `second` (late approvals) | Mon/Wed/Fri/Sat 17:00 |
| `venho-growth-weekly-cycle.timer` | `weekly-cycle` | Sun 20:00 + 22:00 |
| `venho-growth-replace-rejected.timer` | `replace-rejected` | hourly :25 |
| `venho-growth-trend-scan.timer` | `trend-scan` | 07:15 + 19:15 |
| `venho-growth-fast-lane.timer` | `fast-lane` | hourly 07:40–22:40 |

Install: copy `*.sh`, `*.py` to `~/venho/scripts/`, units to
`~/.config/systemd/user/`, `systemctl --user daemon-reload`, enable the timers.
Runtime clone: `~/venho/growth-runtime/venho-ai-studio` (own venv; reference
photos rsynced into `assets/raw/`). Secrets: `~/venho/secrets/growth.env`
(600). Failures -> `venho-growth-alert@` -> Telegram.

These files are the source of truth; edit here, then copy to the server.
The GitHub workflows for these jobs are `workflow_dispatch` only -- never add
a `schedule` back: two runners holding separate registry copies can send the
same post twice.
