# Cloud fallback dispatch (v3.1 §10.4)

## When this runs

Only when the deadman switch (`infra/deadman_config.yaml`) does not see a
`PUBLISHED` publication by `09:30` for a slot that dispatches at `09:00`.

## Flow

1. On approve, the Mac Mini calls `export_approved_package()`
   (`infra/cloud_fallback/export_approved.py`) which HMAC-signs the package
   and writes it to `data/projects/venho_hotel/growth/exports/YYYY/MM/{content_package_id}/export.json`.
2. That export is synced to the cloud fallback store (Make.com data store or
   a private GitHub repo -- either works; both are just a signed-blob mirror).
3. If the deadman switch fires, the cloud side reads the export, verifies
   the signature with `verify_export_signature()`, and replays the
   `publication_command` directly against the Make.com scenario (or M07's
   HTTP API if reachable).
4. When the Mac Mini comes back online, `publishing_gateway/reconciliation.py`
   reconciles the resulting publication so no duplicate post is created.

## Security invariant

The cloud side never has the private key/logic to *create* an
`ApprovalRequest`. It only holds a pre-signed export. If the signature does
not verify, or the package is not `approval_status: approved`, the cloud
side must refuse to dispatch. This keeps "the system never publishes an
unapproved post" true even during a Mac Mini outage.

## Manual setup (Harry)

This README documents the wiring; standing up the actual Make.com data store
/ private GitHub mirror and the cron/webhook that reads it is a manual
operational step outside this repo's test suite.
