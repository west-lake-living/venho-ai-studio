# ADR-GW-005 — Workflow source code and centralized ComfyUI identifiers

- Status: Accepted; architecture locked
- Decision IDs: GW-D6, GW-D7
- v2.1 amendment: the superseded v1 workflow is archived; future active workflows must live in the repository and be hash-pinned.

## Context

Workflow JSON determines output and cannot be treated as mutable Windows machine state. ComfyUI node titles, workflow IDs, and model filenames must not be duplicated as magic strings.

## Decision

Workflow JSON is source code in the repository, deployed one-way to Windows and verified by SHA-256. A centralized `infrastructure/comfyui/node_registry.py` is the single source for ComfyUI identifiers. The archived `workflows/_archive/face_restore_v1_api.json` remains historical only.

## Rationale

Versioned, pinned workflows make output reproducible and prevent identifier drift.

## Consequences

Workflow edits require a new hash and evidence update. Windows-side edits are not authoritative. Registry grep tests remain required when the implementation phase begins.

## Rejected alternatives

- Editing workflow JSON directly on Windows.
- Keeping active workflow source outside Git.
- Repeating node/model strings across adapters and routes.

## Rollback / reversibility

Restore the previously pinned workflow from Git/archive and select `comfyui-local`; do not mutate the archive.

## References

v2.0 §2.1 GW-D6/GW-D7, §8, §10, §13; `workflow_pins.yaml`; v2.1 legacy workflow archive record.
