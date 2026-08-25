from __future__ import annotations

from pathlib import Path

from identity_restoration.application.benchmark_preflight import run_benchmark_preflight


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "contracts/identity_restoration/benchmark_set.yaml"
SCHEMA = ROOT / "contracts/identity_restoration/benchmark_row.schema.json"


class ReadyNanoExecutor:
    def capabilities(self):
        fields = [
            "outputPath", "outputSha256", "executorStatus", "error", "provider",
            "providerRequestId", "providerRunId", "backend", "host", "operation",
            "model", "seedSupported", "lineage", "evidencePath",
        ]
        return {
            "nano-banana-edit": {
                "executorPath": "tests.ReadyNanoExecutor",
                "adapterPath": "existing-production-path",
                "registered": True,
                "physicalCallable": True,
                "evidenceWriter": True,
                "evidenceFields": fields,
                "providerConfigured": True,
                "fallbackEnabled": False,
                "ready": True,
                "blockers": [],
            }
        }


def test_injected_nano_path_is_ready_without_paid_call():
    result = run_benchmark_preflight(
        manifest_path=MANIFEST, schema_path=SCHEMA, repo_root=ROOT,
        executor=ReadyNanoExecutor(),
    )
    branch = next(item for item in result.branches if item.branch == "nano-banana-edit")
    assert branch.ready is True
    assert branch.physical_callable is True
    assert branch.bootstrap_smoke_allowed is False


def test_injected_nano_path_without_provider_config_fails_closed():
    class Unconfigured(ReadyNanoExecutor):
        def capabilities(self):
            value = super().capabilities()
            value["nano-banana-edit"]["providerConfigured"] = False
            return value

    result = run_benchmark_preflight(
        manifest_path=MANIFEST, schema_path=SCHEMA, repo_root=ROOT,
        executor=Unconfigured(),
    )
    branch = next(item for item in result.branches if item.branch == "nano-banana-edit")
    assert branch.ready is False
    assert any("provider configuration" in item for item in branch.blockers)
