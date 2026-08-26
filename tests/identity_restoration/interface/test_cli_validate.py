from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from identity_restoration.interface.cli import main


def test_cli_validate_returns_structured_qc_without_restoration(tmp_path: Path, monkeypatch, capsys):
    attempt = "run-cli-attempt-1"
    artifact = tmp_path / "run-cli" / attempt / "composite.png"
    artifact.parent.mkdir(parents=True)
    Image.new("RGB", (8, 8), "white").save(artifact)
    a2 = tmp_path / "A2.png"
    Image.new("RGB", (8, 8), "white").save(a2)
    request = tmp_path / "validate.json"
    request.write_text(json.dumps({
        "contractVersion": "1.0",
        "runId": "run-cli",
        "attemptId": attempt,
        "artifactAttemptId": attempt,
        "compositePath": str(artifact),
        "a2Path": str(a2),
    }), encoding="utf-8")
    monkeypatch.delenv("IDR_QC_ENABLED", raising=False)
    monkeypatch.setenv("IDR_QC_PROVIDER", "mock")

    assert main(["validate", "--request", str(request)]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "QC_FAILED"
    assert payload["runId"] == "run-cli"
    assert payload["attemptId"] == attempt
    assert payload["error"]["code"] == "QC_AUTHORITY_UNAVAILABLE"
