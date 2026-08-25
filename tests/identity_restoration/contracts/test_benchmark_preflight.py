from __future__ import annotations

import json
import shutil
from pathlib import Path

from identity_restoration.application.benchmark_preflight import run_benchmark_preflight
from identity_restoration.application.benchmark_runner import BenchmarkRunner
from identity_restoration.interface.cli import main


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = REPO_ROOT / "contracts" / "identity_restoration"
MANIFEST = CONTRACTS / "benchmark_set.yaml"
SCHEMA = CONTRACTS / "benchmark_row.schema.json"


def test_preflight_accepts_validated_physical_smoke_evidence(capsys) -> None:
    assert main(["benchmark", "preflight", "--manifest", str(MANIFEST)]) == 0
    first = json.loads(capsys.readouterr().out)
    assert main(["benchmark", "preflight", "--manifest", str(MANIFEST)]) == 0
    second = json.loads(capsys.readouterr().out)
    assert first == second
    assert first["officialBenchmarkReady"] is True
    assert first["executorReady"] is True
    assert first["officialExecutionReady"] is True
    assert {branch["branch"] for branch in first["branches"]} == {
        "control", "comfyui-local", "comfyui-remote", "nano-banana-edit"
    }


def test_control_capability_is_real_and_no_provider_is_required(tmp_path: Path) -> None:
    from identity_restoration.application.benchmark_executor import ControlBenchmarkExecutor

    manifest = json.loads(json.dumps(__import__("yaml").safe_load(MANIFEST.read_text())))
    case = manifest["cases"][0]
    executor = ControlBenchmarkExecutor(REPO_ROOT)
    evidence = executor.execute(case=case, branch="control", run_id="preflight", attempt_id="a1", seed=42)
    assert evidence["executorStatus"] == "COMPLETED"
    assert evidence["outputSha256"] == case["baseFrame"]["sha256"]
    assert evidence["provider"] is None
    assert executor.capabilities()["control"]["ready"] is True


def test_missing_executor_keeps_run_blocked_before_output_directory(tmp_path: Path) -> None:
    output_root = tmp_path / "official-runs"
    runner = BenchmarkRunner(manifest_path=MANIFEST, output_root=output_root)
    try:
        runner.run()
    except Exception as exc:
        assert "official execution is not ready" in str(exc) or "executor is not configured" in str(exc)
    assert not output_root.exists()


def test_remote_workflow_hash_mismatch_blocks_preflight(tmp_path: Path) -> None:
    shutil.copytree(REPO_ROOT / "config", tmp_path / "config")
    workflow = tmp_path / "identity_restoration/workflows/face_restore_win_sd15_ipadapter_v2.api.json"
    workflow.parent.mkdir(parents=True)
    shutil.copy(REPO_ROOT / "identity_restoration/workflows/face_restore_win_sd15_ipadapter_v2.api.json", workflow)
    workflow.write_bytes(workflow.read_bytes() + b"\ncorrupted")
    result = run_benchmark_preflight(
        manifest_path=MANIFEST, schema_path=SCHEMA, repo_root=tmp_path
    )
    assert result.official_execution_ready is False
    assert result.workflow_authority["valid"] is False
    assert any("workflow" in blocker for blocker in result.blockers)


def test_incomplete_injected_evidence_capability_blocks_execution() -> None:
    class Incomplete:
        def capabilities(self):
            return {"control": {"ready": True, "physicalCallable": True, "evidenceWriter": False}}

    result = run_benchmark_preflight(
        manifest_path=MANIFEST, schema_path=SCHEMA, repo_root=REPO_ROOT, executor=Incomplete()
    )
    assert result.official_execution_ready is False
    assert any(branch.branch == "control" and not branch.ready for branch in result.branches)
