#!/usr/bin/env python3
"""Push a pinned workflow from the repo to the Windows worker's
``venho_workflows\\`` directory and verify the copy's SHA-256 (GW-D6, v2.0 §9.3).

One-way only: this script never reads FROM the worker. The worker is state,
not source; the pin in workflow_pins.yaml plus the file in
identity_restoration/workflows/ is the only truth.

Usage:
    PYTHONPATH=. /usr/bin/python3 scripts/deploy_workflows_to_worker.py \\
        face_restore_win_sd15_ipadapter_v1 \\
        --dest //venho-gpu-win/VenHoGPU/venho_workflows

Requires the destination to already be reachable (SMB share over Tailscale,
or a local path for testing). Makes no assumption about *how* it is reachable
— that is a Windows worker/network concern (GW-P1/P3), out of this script's
scope.

Interpreter note: run with /usr/bin/python3 (system Python 3.9) — see
probe_gpu_worker.py's docstring for why a bare `python3` can fail here.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow_id")
    parser.add_argument("--dest", required=True, help="Destination directory reachable from this Mac")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    pins_path = repo_root / "config/projects/venho_hotel/identity_restoration/workflow_pins.yaml"
    pins = yaml.safe_load(pins_path.read_text(encoding="utf-8")) or {}
    entry = (pins.get("workflows") or {}).get(args.workflow_id)
    if entry is None:
        print(f"error: no pin for workflowId {args.workflow_id!r} in {pins_path}", file=sys.stderr)
        return 1

    pinned_sha256 = entry.get("sha256", "")
    if not pinned_sha256 or pinned_sha256.startswith("<"):
        print(f"error: workflowId {args.workflow_id!r} has no sha256 pinned yet — author + pin it first",
             file=sys.stderr)
        return 1

    source = Path(entry["path"]) if entry.get("path") else (
        repo_root / "identity_restoration/workflows" / entry["filename"])
    if not source.is_file():
        print(f"error: source workflow file not found: {source}", file=sys.stderr)
        return 1

    actual_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual_sha256 != pinned_sha256:
        print(f"error: {source} sha256={actual_sha256} does not match pin={pinned_sha256}. "
             "Pin drift — fix the pin or the file before deploying.", file=sys.stderr)
        return 1

    dest_dir = Path(args.dest)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / source.name
    shutil.copyfile(source, dest_file)
    deployed_sha256 = hashlib.sha256(dest_file.read_bytes()).hexdigest()
    if deployed_sha256 != pinned_sha256:
        print(f"error: post-copy verification failed at {dest_file}: sha256={deployed_sha256}", file=sys.stderr)
        return 1

    print(f"deployed {source.name} -> {dest_file} sha256={deployed_sha256} OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
