from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from identity_restoration.application.benchmark_executor import NanoBananaEditRequest
from identity_restoration.interface import cli


ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "contracts" / "identity_restoration" / "benchmark_set.yaml"
A2 = Path(
    "/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/"
    "assets/face-plates/A2_Front_plate.png"
)


class ExistingNanoExecutor:
    def __init__(self, request_factory):
        self.request_factory = request_factory
        self.calls = []

    def capabilities(self):
        return {
            "nano-banana-edit": {
                "ready": True,
                "providerConfigured": True,
                "fallbackEnabled": False,
                "blockers": [],
                "evidenceFields": [
                    "outputPath", "outputSha256", "executorStatus", "error",
                    "provider", "providerRequestId", "providerRunId", "backend", "host",
                ],
            }
        }

    def execute(self, *, case, branch, run_id, attempt_id, seed):
        request = self.request_factory(case, run_id, attempt_id, seed)
        assert isinstance(request, NanoBananaEditRequest)
        self.calls.append((case["id"], branch, seed, request))
        return {"executorStatus": "COMPLETED", "provider": "nano-banana-2"}


def test_nano_smoke_dispatches_existing_executor_without_remote_url(monkeypatch, tmp_path, capsys):
    holder = {}

    def fake_build_module(env, **kwargs):
        executor = ExistingNanoExecutor(kwargs["nano_banana_request_factory"])
        holder["executor"] = executor
        return SimpleNamespace(nano_banana_executor=executor)

    monkeypatch.setattr(cli, "build_identity_restoration_module", fake_build_module)

    result = cli.main([
        "benchmark", "smoke",
        "--manifest", str(MANIFEST),
        "--branch", "nano-banana-edit",
        "--case", "B01",
        "--a2-path", str(A2),
        "--evidence-root", str(tmp_path / "evidence"),
    ])

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["evidenceType"] == "NON_BENCHMARK"
    assert payload["phase"] == "PREFLIGHT"
    assert payload["officialBenchmarkRunCreated"] is False
    assert payload["paidCallCount"] == 1
    assert holder["executor"].calls[0][0:3] == ("B01", "nano-banana-edit", 42)


def test_nano_smoke_rejects_authority_before_existing_executor(monkeypatch, tmp_path, capsys):
    calls = []

    class NoCallExecutor(ExistingNanoExecutor):
        def execute(self, **kwargs):
            calls.append("provider-path")
            return super().execute(**kwargs)

    def fake_build_module(env, **kwargs):
        return SimpleNamespace(nano_banana_executor=NoCallExecutor(kwargs["nano_banana_request_factory"]))

    monkeypatch.setattr(cli, "build_identity_restoration_module", fake_build_module)
    wrong_a2 = tmp_path / "wrong-a2.png"
    wrong_a2.write_bytes(b"not-the-canonical-a2")

    result = cli.main([
        "benchmark", "smoke",
        "--manifest", str(MANIFEST),
        "--branch", "nano-banana-edit",
        "--case", "B01",
        "--a2-path", str(wrong_a2),
        "--evidence-root", str(tmp_path / "evidence"),
    ])

    assert result == 1
    assert calls == []
    assert "frozen B01 preflight failed" in capsys.readouterr().err


def test_nano_smoke_does_not_accept_external_request_override(monkeypatch, tmp_path, capsys):
    result = cli.main([
        "benchmark", "smoke",
        "--manifest", str(MANIFEST),
        "--branch", "nano-banana-edit",
        "--case", "B01",
        "--request", str(tmp_path / "request.json"),
        "--a2-path", str(A2),
    ])

    assert result == 1
    assert "does not accept a request override" in capsys.readouterr().err
