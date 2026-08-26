from __future__ import annotations

import dataclasses
import enum
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from identity_restoration.interface.json_bridge import serialize_json
from shared.logging import log


ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / ".venv" / "bin" / "venho-restore"


def _request(tmp_path: Path, *, missing_composite: bool = False) -> Path:
    attempt = "raw-cli-attempt-1"
    artifact = tmp_path / "run" / attempt / "composite.png"
    artifact.parent.mkdir(parents=True)
    if not missing_composite:
        Image.new("RGB", (8, 8), "white").save(artifact)
    a2 = tmp_path / "A2.png"
    Image.new("RGB", (8, 8), "white").save(a2)
    request = tmp_path / "validate.json"
    request.write_text(json.dumps({
        "contractVersion": "1.0",
        "runId": "raw-cli",
        "attemptId": attempt,
        "artifactAttemptId": attempt,
        "compositePath": str(artifact),
        "a2Path": str(a2),
    }), encoding="utf-8")
    return request


def _run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    process_env = os.environ.copy()
    process_env.update({
        "IDR_QC_PROVIDER": "mock",
        "IDR_QC_SAMPLES": "3",
        "IDR_COMFYUI_ENABLED": "false",
        "IDR_COMFYUI_REMOTE_ENABLED": "false",
    })
    if env:
        process_env.update(env)
    return subprocess.run(
        [str(CLI), *args], cwd=ROOT, env=process_env,
        text=True, capture_output=True, check=False,
    )


def test_validate_subprocess_stdout_is_one_json_document(tmp_path: Path) -> None:
    process = _run("validate", "--request", str(_request(tmp_path)))
    assert process.returncode == 1
    payload = json.loads(process.stdout)
    assert payload["status"] == "QC_FAILED"
    assert payload["error"]["code"] == "QC_AUTHORITY_UNAVAILABLE"
    assert process.stdout.count("{") >= 1
    assert process.stdout.strip().endswith("}")
    assert "Gemini vision" not in process.stdout


def test_validate_failure_subprocess_keeps_structured_json_on_nonzero(tmp_path: Path) -> None:
    process = _run("validate", "--request", str(_request(tmp_path, missing_composite=True)))
    assert process.returncode == 1
    payload = json.loads(process.stdout)
    assert payload["status"] == "QC_FAILED"
    assert payload["error"]["code"] == "ERR_GW_QC_ARTIFACT_MISSING"


def test_health_subprocess_stdout_is_json_not_python_repr() -> None:
    process = _run("health")
    assert process.returncode == 0
    payload = json.loads(process.stdout)
    assert payload["status"] == "MOCK_ONLY"
    assert "'" not in process.stdout


class _Kind(enum.Enum):
    OK = "OK"


@dataclasses.dataclass(frozen=True)
class _BoundaryValue:
    kind: _Kind
    path: Path
    at: datetime
    text: str


def test_json_writer_normalizes_boundary_values_without_repr() -> None:
    payload = json.loads(serialize_json(_BoundaryValue(
        kind=_Kind.OK,
        path=Path("/tmp/điagnostic"),
        at=datetime(2026, 8, 26, tzinfo=timezone.utc),
        text='quote " newline\\n unicode ✓',
    )))
    assert payload == {
        "kind": "OK",
        "path": "/tmp/điagnostic",
        "at": "2026-08-26T00:00:00+00:00",
        "text": 'quote " newline\\n unicode ✓',
    }


def test_diagnostics_are_stderr_not_stdout(capsys) -> None:
    log("validator diagnostic: quote=\" unicode=✓")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "validator diagnostic" in captured.err
