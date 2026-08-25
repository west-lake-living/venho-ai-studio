from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from ..infrastructure.composition.identity_restoration_module import (
    build_identity_restoration_module,
    build_worker_health,
)
from ..application.use_cases.check_worker_health import CheckWorkerHealthUseCase
from ..application.benchmark_runner import (
    BenchmarkExecutionError,
    BenchmarkManifestError,
    BenchmarkRunner,
)
from ..application.benchmark_executor import ComfyUIRemoteBenchmarkExecutor
from ..infrastructure.composition.benchmark_module import build_official_benchmark_executor
from ..application.benchmark_geometry import build_frozen_b01_nano_request
from ..application.benchmark_request_builder import (
    build_benchmark_restore_command,
    validate_benchmark_restore_command,
)
from ..infrastructure.composition.env import read_restoration_env
from .json_bridge import dump_result, load_restore_command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="venho-restore")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run one identity restoration request end-to-end")
    run_p.add_argument("--request", required=True, type=Path, help="Path to a restoration_request JSON")
    run_p.add_argument("--restorer", default=None,
                       help="Override restorerId (mock | comfyui-local | comfyui-remote)")

    sub.add_parser("health", help="Probe worker health and print WorkerHealth as JSON")

    benchmark = sub.add_parser("benchmark", help="Validate and orchestrate the GW-P4 benchmark")
    benchmark_sub = benchmark.add_subparsers(dest="benchmark_command", required=True)
    for name, help_text in (
        ("validate", "Validate the benchmark contract without running it"),
        ("plan", "Print the deterministic 10x3 official decision plan"),
        ("preflight", "Inspect branch executors and evidence readiness without running it"),
        ("smoke", "Run exactly one NON_BENCHMARK/PREFLIGHT branch smoke"),
        ("run", "Run the official benchmark when every case is FROZEN"),
    ):
        command = benchmark_sub.add_parser(name, help=help_text)
        command.add_argument(
            "--manifest", type=Path, default=None,
            help="Override benchmark_set.yaml (for contract tests or controlled use)",
        )
        if name == "smoke":
            command.add_argument(
                "--branch", choices=("comfyui-remote", "nano-banana-edit"), required=True
            )
            command.add_argument("--case", choices=("B01",), required=True)
            command.add_argument(
                "--request", type=Path, required=False,
                help="Optional controlled B01 request override; canonical production geometry is used by default",
            )
            command.add_argument("--remote-base-url", default=None)
            command.add_argument("--a2-path", type=Path, default=None)
            command.add_argument("--evidence-root", type=Path, default=Path("evidence"))
        if name == "run":
            command.add_argument(
                "--reuse-run", default=None,
                help="Explicit prior benchmark run whose verified provider artifacts may be reused",
            )

    args = parser.parse_args(argv)

    if args.command == "health":
        # FACT 2 fix: health must never depend on the inference workflow
        # loading successfully — build it straight from env, no workflow I/O.
        health = build_worker_health()
        if health is None:
            print('{"status": "MOCK_ONLY", "message": "IDR_COMFYUI_ENABLED=false, no worker configured"}')
            return 0
        result = CheckWorkerHealthUseCase(health=health).execute()
        print(f'{{"status": "{result.status.value}", "gpuName": {result.gpu_name!r}, '
              f'"vramFreeMb": {result.vram_free_mb}}}')
        return 0

    if args.command == "run":
        module = build_identity_restoration_module()
        cmd = load_restore_command(args.request)
        if args.restorer:
            cmd = _with_restorer(cmd, args.restorer)
        result = module.use_case.execute(cmd)
        print(dump_result(result))
        return 0 if result.status in ("FULL_GATE_PASS", "NEEDS_REVIEW") else 1

    if args.command == "benchmark":
        runner = BenchmarkRunner(
            manifest_path=args.manifest,
            reuse_run_id=getattr(args, "reuse_run", None),
        )
        if args.benchmark_command == "validate":
            try:
                print(json.dumps(runner.validate(), indent=2, sort_keys=True))
                return 0
            except (BenchmarkManifestError, OSError, ValueError) as exc:
                print(f"benchmark contract invalid: {exc}", file=sys.stderr)
                return 2

        if args.benchmark_command == "plan":
            try:
                print(json.dumps(runner.plan().to_dict(), indent=2, sort_keys=True))
                return 0
            except (BenchmarkManifestError, OSError, ValueError) as exc:
                print(f"benchmark plan unavailable: {exc}", file=sys.stderr)
                return 2

        if args.benchmark_command == "preflight":
            try:
                print(json.dumps(runner.preflight(), indent=2, sort_keys=True))
                return 0
            except (BenchmarkManifestError, OSError, ValueError) as exc:
                print(f"benchmark preflight unavailable: {exc}", file=sys.stderr)
                return 2

        if args.benchmark_command == "smoke":
            try:
                if args.branch == "nano-banana-edit":
                    result = _run_nano_banana_smoke(args, runner)
                else:
                    result = _run_remote_bootstrap_smoke(args, runner)
            except (BenchmarkManifestError, BenchmarkExecutionError, OSError, ValueError) as exc:
                print(f"benchmark smoke blocked: {exc}", file=sys.stderr)
                return 1
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.benchmark_command == "run":
            try:
                runner.executor = build_official_benchmark_executor(runner=runner)
                result = runner.run()
            except (BenchmarkManifestError, BenchmarkExecutionError, OSError, ValueError) as exc:
                print(f"benchmark execution refused: {exc}", file=sys.stderr)
                return 1
            print(json.dumps({
                "runId": result.run_id,
                "runManifest": str(result.run_manifest_path),
                "rows": str(result.rows_path),
                "summary": str(result.summary_path) if result.summary_path else None,
                "decision": result.decision,
                "completedCount": result.completed_count,
                "failedCount": result.failed_count,
            }, indent=2, sort_keys=True))
            return 0 if result.failed_count == 0 else 1

    return 2


def _with_restorer(cmd, restorer_id: str):
    from dataclasses import replace
    return replace(cmd, restorer_id=restorer_id)


def _run_remote_bootstrap_smoke(args, runner: BenchmarkRunner) -> dict:
    """Composition-only entry point for the one non-benchmark bootstrap run."""
    manifest = runner.load()
    if not runner.validate()["officialBenchmarkReady"]:
        raise BenchmarkExecutionError("bootstrap smoke requires an authoritative frozen dataset")
    case = next(case for case in manifest["cases"] if case["id"] == args.case)
    if case.get("status") != "FROZEN":
        raise BenchmarkExecutionError(f"bootstrap smoke case {args.case} is not FROZEN")

    env = read_restoration_env()
    remote_url = args.remote_base_url or env.comfyui_remote_base_url
    a2_path = str(args.a2_path) if args.a2_path is not None else env.a2_path
    smoke_env = replace(
        env,
        default_restorer="comfyui-remote",
        comfyui_enabled=True,
        comfyui_remote_enabled=True,
        comfyui_base_url=remote_url,
        comfyui_remote_base_url=remote_url,
        a2_path=a2_path,
    )
    module = build_identity_restoration_module(smoke_env, repo_root=runner.repo_root)
    try:
        module.registry.resolve("comfyui-remote")
    except KeyError as exc:
        raise BenchmarkExecutionError("comfyui-remote is not registered in the composition root") from exc
    canonical_command = build_benchmark_restore_command(
        case,
        canonical_a2_path=a2_path,
        branch=args.branch,
        run_id="preflight-b01-remote-smoke",
        attempt_id="b01-remote-smoke-1",
        seed=manifest["seed"],
        geometry_backend=env.geometry_backend,
    )
    template = canonical_command
    if args.request is not None:
        override = load_restore_command(args.request)
        validate_benchmark_restore_command(override, case=case, canonical_a2_path=a2_path)
        if override.crop_transform != canonical_command.crop_transform:
            raise BenchmarkExecutionError(
                "request override cropTransform does not match production-derived B01 geometry"
            )
        template = override

    def request_factory(case, run_id, attempt_id, seed):
        return replace(
            template,
            run_id=run_id,
            attempt_id=attempt_id,
            restorer_id="comfyui-remote",
            seed=seed,
        )

    executor = ComfyUIRemoteBenchmarkExecutor(
        use_case=module.use_case,
        request_factory=request_factory,
        repo_root=runner.repo_root,
        health=module.health,
        evidence_root=(args.evidence_root if args.evidence_root.is_absolute()
                       else runner.repo_root / args.evidence_root),
    )
    run_id = "preflight-b01-remote-smoke"
    attempt_id = "b01-remote-smoke-1"
    evidence = executor.execute_bootstrap_smoke(
        case=case,
        branch=args.branch,
        run_id=run_id,
        attempt_id=attempt_id,
        seed=manifest["seed"],
    )
    return {
        "evidenceType": "NON_BENCHMARK",
        "phase": "PREFLIGHT",
        "branch": args.branch,
        "case": args.case,
        "officialExecutionReady": False,
        "evidence": evidence,
    }


def _run_nano_banana_smoke(args, runner: BenchmarkRunner) -> dict:
    """Run the one canonical Nano Banana readiness smoke.

    This is deliberately a composition boundary.  The CLI constructs only
    the frozen B01 request and resolves the already-composed executor; it
    never imports a vendor SDK, calls Gemini directly, or creates a second
    image-generation pipeline.
    """
    if args.request is not None:
        raise BenchmarkExecutionError(
            "nano-banana-edit smoke does not accept a request override; use frozen B01 geometry"
        )

    manifest = runner.load()
    case = next(case for case in manifest["cases"] if case["id"] == args.case)
    if case.get("status") != "FROZEN":
        raise BenchmarkExecutionError(f"bootstrap smoke case {args.case} is not FROZEN")

    geometry_record = case.get("geometryAuthority")
    if not isinstance(geometry_record, dict) or not geometry_record.get("path"):
        raise BenchmarkExecutionError("B01 frozen geometry authority is missing")
    geometry_path = Path(str(geometry_record["path"]))
    if not geometry_path.is_absolute():
        geometry_path = runner.repo_root / geometry_path
    if not geometry_path.is_file():
        raise BenchmarkExecutionError(f"B01 frozen geometry authority is missing: {geometry_path}")

    env = read_restoration_env()
    a2_path = Path(args.a2_path) if args.a2_path is not None else Path(env.a2_path)
    if not a2_path.is_absolute():
        a2_path = runner.repo_root / a2_path
    evidence_root = args.evidence_root
    if not evidence_root.is_absolute():
        evidence_root = runner.repo_root / evidence_root

    run_id = _smoke_run_id("nano")
    attempt_id = "b01-nano-smoke-1"

    def request_factory(case, request_run_id, request_attempt_id, seed):
        return build_frozen_b01_nano_request(
            case,
            geometry_authority_path=geometry_path,
            canonical_a2_path=a2_path,
            run_id=request_run_id,
            attempt_id=request_attempt_id,
            seed=seed,
        )

    # Resolve and validate the frozen request before resolving/calling the
    # provider. This keeps B01/A2/geometry/mask failures strictly preflight
    # failures, independent of the injected executor implementation.
    try:
        request_factory(case, run_id, attempt_id, manifest["seed"])
    except Exception as exc:
        raise BenchmarkExecutionError(f"Nano Banana frozen B01 preflight failed: {exc}") from exc

    # The composition root is the only place allowed to connect the existing
    # GenerateStudioImageUseCase -> GeminiImageProvider path.  If it is not
    # injected/configured, stop before any provider call.
    smoke_env = replace(
        env,
        nano_banana_enabled=True,
        nano_banana_bridge_enabled=True,
        a2_path=str(a2_path),
    )
    module = build_identity_restoration_module(
        smoke_env,
        repo_root=runner.repo_root,
        nano_banana_request_factory=request_factory,
        benchmark_evidence_root=evidence_root,
        canonical_a2_path=a2_path,
    )
    executor = module.nano_banana_executor
    if executor is None:
        raise BenchmarkExecutionError(
            "Nano Banana production port is not registered in the composition root; "
            "inject the existing GenerateStudioImageUseCase/GeminiImageProvider path"
        )
    capability = executor.capabilities().get("nano-banana-edit", {})
    if not capability.get("ready", False):
        blockers = "; ".join(str(item) for item in capability.get("blockers", ()))
        raise BenchmarkExecutionError(
            "Nano Banana smoke is not ready" + (f": {blockers}" if blockers else "")
        )

    evidence = executor.execute(
        case=case,
        branch="nano-banana-edit",
        run_id=run_id,
        attempt_id=attempt_id,
        seed=manifest["seed"],
    )
    return {
        "evidenceType": "NON_BENCHMARK",
        "phase": "PREFLIGHT",
        "branch": "nano-banana-edit",
        "case": "B01",
        "paidCallCount": 1,
        "officialBenchmarkRunCreated": False,
        "evidence": evidence,
    }


def _smoke_run_id(branch: str) -> str:
    from datetime import datetime, timezone

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"preflight-b01-{branch}-smoke-{stamp}"


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
