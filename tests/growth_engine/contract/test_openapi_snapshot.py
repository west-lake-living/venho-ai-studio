from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from growth_engine.adapters.inbound.cli.main import app


def test_openapi_command_matches_committed_snapshot(tmp_path: Path) -> None:
    snapshot = Path(__file__).resolve().parents[3] / "contracts" / "growth_engine" / "openapi.json"
    generated = tmp_path / "openapi.json"
    result = CliRunner().invoke(app, ["openapi", "--out", str(generated)])
    assert result.exit_code == 0, result.output
    assert generated.read_text() == snapshot.read_text()
