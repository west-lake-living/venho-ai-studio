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

## Dashboard checkout (`~/venho/03_AI_STUDIO/venho-ai-studio`)

A second, long-lived checkout: VENHO OS shells out to its `venho-*` CLIs.
Kept on `main` by `sync-venho-ai-studio.sh` (cron `*/5`), fast-forward only.

- **Never commit or switch branches in it.** On 17/10/2026 a side branch
  with one deploy commit stopped every sync for 4 days, silently; new
  research notes never arrived and Knowledge Facts could not be approved.
  Do experimental work in a separate worktree/clone. The script now alerts
  on Telegram once when it cannot sync (off `main`, ff refused, `uv sync`
  failed) and once when it recovers.
- It runs `uv sync --frozen --inexact --extra drive --extra gemini` when
  `pyproject.toml`/`uv.lock` change. Adding a dependency means running
  `uv lock` and committing `uv.lock` in the same commit, or `--frozen`
  installs without it.
- Four Dashboard-written JSON files carry `skip-worktree`; keep it if you
  ever have to re-checkout (back them up, re-copy, `git update-index --skip-worktree`).
- `venho-studio-pull.timer` (an older `git pull` every hour) is disabled as
  redundant (2026-10-21); the unit files are kept.
