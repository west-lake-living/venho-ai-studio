# Mac Mini M4 setup (v3.1 §10.2, §10.6)

Manual runbook for Harry. Nothing in this file is executed by the test
suite or by Claude Code -- it is the physical setup checklist for the
machine that will run Research OS, the generation pipeline, and the
dashboard 24/7.

## 1. Power and sleep

```bash
sudo pmset -a sleep 0 disksleep 0 displaysleep 10
sudo pmset -a womp 1              # wake on network
sudo pmset -a autorestart 1       # auto-restart after power loss
sudo softwareupdate --schedule off
```

## 2. launchd services

Copy every `infra/launchd/com.venho.*.plist` into `~/Library/LaunchAgents/`,
then for each:

```bash
launchctl load ~/Library/LaunchAgents/com.venho.<name>.plist
launchctl start com.venho.<name>
```

Services:
- `com.venho.research.daily` -- 06:00 weather scan, 07:00 stale-knowledge check
- `com.venho.trend.scan` -- Tuesday 09:00 trend scan (T3)
- `com.venho.pipeline.worker` -- `KeepAlive=true`, continuous job worker
- `com.venho.dashboard` -- `KeepAlive=true`, Streamlit on the LAN
- `com.venho.dispatch` -- 08:45 pre-flight, 09:00 dispatch

`launchd` (not cron) because it auto-restarts a crashed process via
`KeepAlive` and survives reboots via `RunAtLoad`.

## 3. Remote access -- Tailscale (IN-D6)

Install Tailscale on the Mac Mini and on Harry's phone, join the same
tailnet. Do **not** port-forward Streamlit to the public internet --
Streamlit has no auth by default (see §15.14).

## 4. Backups

`infra/backup.sh` runs `sqlite3 .backup` + copies artifacts to
`$VENHO_BACKUP_ROOT` (default `~/VenhoBackups`), then syncs off-site via
`rclone` if a `venho-cloud` remote is configured. Schedule it with its own
launchd job at 02:00, or add it as a second `ProgramArguments` entry.

## 5. Verify after setup

- `pmset -g` shows `sleep 0`.
- `launchctl list | grep com.venho` shows all 5 services running.
- A test heartbeat (`infra/heartbeat.py`) reaches the cloud endpoint.
- A test Telegram alert is received on Harry's phone.
- 72h soak: no unexpected reboot, no missed heartbeat.

## 6. Known residual risks (§10.2)

| Risk | Mitigation already in place |
|---|---|
| Power/network outage | UPS + `autorestart 1` + deadman switch (cloud) |
| macOS forced reboot | `softwareupdate --schedule off` |
| Process dies silently | `launchd KeepAlive` + heartbeat |
| Disk full / DB lock | Alert at <10GB free, SQLite WAL mode |
