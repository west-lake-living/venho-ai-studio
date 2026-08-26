#!/usr/bin/env python3
"""Run a bounded sequential GW-P5 ComfyUI worker soak.

This is an execution harness only: it uses the existing remote restorer,
existing frozen B01 geometry fixture, and no validator/provider. It stops on
the first failure and refuses more than 12 normal GPU jobs in one invocation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from identity_restoration.application.benchmark_contract import EXPECTED_A2_SHA256
from identity_restoration.application.benchmark_orchestration import BenchmarkCaseContextFactory
from identity_restoration.infrastructure.composition.env import RestorationEnv
from identity_restoration.infrastructure.composition.identity_restoration_module import (
    build_identity_restoration_module,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bounded sequential GW-P5 worker soak")
    parser.add_argument("--count", type=int, required=True, help="2 for smoke or 10 for the final soak")
    parser.add_argument("--base-url", default=os.environ.get("IDR_COMFYUI_REMOTE_BASE_URL"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-root", type=Path,
                        default=ROOT / "artifacts/identity-restoration/hardening")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.count not in {2, 10}:
        raise SystemExit("--count must be exactly 2 (smoke) or 10 (soak)")
    if not args.base_url:
        raise SystemExit("--base-url or IDR_COMFYUI_REMOTE_BASE_URL is required")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_root = args.output_root / f"gw-p5-soak-{stamp}-{args.count}jobs"
    artifact_root = run_root / "restoration-artifacts"
    ledger_path = run_root / "restoration-ledger.jsonl"
    run_root.mkdir(parents=True, exist_ok=False)

    manifest = yaml.safe_load((ROOT / "contracts/identity_restoration/benchmark_set.yaml").read_text())
    cases = {str(item["id"]): item for item in manifest["cases"]}
    case = cases["B01"]
    a2_path = ROOT / "assets/linh_an/A2_Front.png"
    if sha256(a2_path) != EXPECTED_A2_SHA256:
        raise SystemExit("A2 authority hash mismatch")

    context = BenchmarkCaseContextFactory(
        repo_root=ROOT, canonical_a2_path=a2_path, geometry_backend="yunet"
    ).build(case)
    env = RestorationEnv(
        default_restorer="comfyui-remote",
        comfyui_enabled=True,
        comfyui_base_url=args.base_url,
        comfyui_remote_enabled=True,
        comfyui_remote_base_url=args.base_url,
        comfyui_timeout_seconds=600,
        comfyui_remote_timeout_seconds=600,
        health_ttl_seconds=0,
        artifact_root=str(artifact_root),
        ledger_path=str(ledger_path),
        a2_path=str(a2_path.relative_to(ROOT)),
        geometry_backend="yunet",
    )
    module = build_identity_restoration_module(env, repo_root=ROOT)
    report: dict = {
        "schema_version": "1.0",
        "task": "GW-P5-T5",
        "mode": "SMOKE" if args.count == 2 else "SOAK",
        "base_url": args.base_url,
        "fixture": "B01",
        "sequential": True,
        "requested_jobs": args.count,
        "jobs": [],
        "stopped_on_failure": False,
        "network_calls": "ComfyUI remote only",
        "provider_calls": 0,
    }

    input_sha = sha256(context.crop_path)
    for sequence in range(1, args.count + 1):
        run_id = f"gw-p5-{stamp}-job-{sequence:02d}"
        attempt_id = f"attempt-{sequence:02d}"
        command = context.remote_command(run_id, attempt_id, args.seed)
        started = time.perf_counter()
        result = module.use_case.execute(command)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        restored_path = Path(result.restored_crop_path) if result.restored_crop_path else None
        output_sha = sha256(restored_path) if restored_path and restored_path.is_file() else None
        health = result.lineage.get("workerHealth", {}) if result.lineage else {}
        row = {
            "sequence_number": sequence,
            "run_id": run_id,
            "attempt_id": attempt_id,
            "runtime_ms_measured": elapsed_ms,
            "runtime_ms_lineage": (result.lineage or {}).get("runtimeMs"),
            "terminal_status": result.status,
            "error_code": result.error.code if result.error else None,
            "worker_health": health,
            "input_sha256": input_sha,
            "output_sha256": output_sha,
            "output_differs_from_input": bool(output_sha and output_sha != input_sha),
            "restored_crop_path": str(restored_path) if restored_path else None,
            "lineage_present": bool(result.lineage),
        }
        report["jobs"].append(row)
        success = bool(
            result.error is None
            and restored_path
            and restored_path.is_file()
            and output_sha != input_sha
            and bool(result.lineage)
        )
        if not success:
            report["stopped_on_failure"] = True
            break

    report["completed_jobs"] = len(report["jobs"])
    report["consecutive_successes"] = sum(
        1 for row in report["jobs"] if row["error_code"] is None and row["output_differs_from_input"]
    )
    report["result"] = "PASS" if report["completed_jobs"] == args.count and report["consecutive_successes"] == args.count else "FAIL"
    report_path = run_root / "gw-p5-soak-report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"], "report": str(report_path)}, indent=2))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
