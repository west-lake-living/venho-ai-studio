# Growth Engine release deployment

These files prepare a user-level deployment under `~/venho`. They do not deploy automatically; Harry runs the script after the P9 gate is cleared.

## Layout

- Code: `~/venho/growth-engine/releases/<git-sha>` and `current` symlink.
- SQLite and media: `~/venho/state/growth-engine/`.
- Service environment: `~/venho/secrets/growth-engine.env`, mode `600`.
- API: loopback `127.0.0.1:8021`; Cloudflare routing is configured separately.

## Preconditions

1. Run from a clean GC2 checkout whose `origin` contains the requested commit.
2. Install `git`, `uv`, and user systemd support. Create the environment file with `GE_ENV=production`, DB/media paths under the state directory, and reviewed production settings; do not put secrets in Git or command arguments.
3. Confirm the target DB is already at the expected schema and runtime publish mode is `DISABLED`. The release script checks migrations without applying them.
4. Confirm the target release supports both worker lanes. In particular, `venho-engine worker --lane jobs` must be implemented before starting `growth-engine-worker@jobs.service`.

## Deploy a release

From the GC2 checkout, after the release commit is available from `origin`:

```bash
bash ops/asus-server/growth-engine/deploy-release.sh <git-sha>
```

The script clones the requested commit into a new release directory, builds its own frozen environment with `api`, `drive`, and `gemini` extras, checks migrations and `doctor --pre-switch`, installs/reloads these user units, then atomically switches `current`. It restarts the API and `publish`/`jobs` workers, checks that all three units stay active, and runs `doctor` again. A failed restart or doctor restores the prior symlink and restarts the prior release; on a first deployment it removes `current` and stops the units.

The script does not apply migrations, change `runtime_controls`, rotate keys, modify the legacy publisher, or run from `~/venho/growth-runtime/venho-ai-studio`. A database/schema or doctor failure happens before switching the active release.

## Units

The API binds only to localhost. The worker template is instantiated as `growth-engine-worker@publish.service` and `growth-engine-worker@jobs.service`; both use the same release, environment file, and persistent state directory. Failures invoke the existing `venho-growth-alert@.service` notification unit.

If a deploy check fails, retain the printed failure and inspect the release/doctor output before retrying. Do not remove a release or state directory as a rollback step.
