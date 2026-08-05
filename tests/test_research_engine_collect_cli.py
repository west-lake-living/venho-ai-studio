from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from research_engine.cli import app
from research_engine.domain.research_note import ResearchDomain

runner = CliRunner()

_CONFIG_ROOT = Path("config/projects/venho_hotel/research")


def test_all_9_domains_are_registered_in_both_domains_yaml_and_the_pydantic_literal() -> None:
    """Regression guard against exactly the drift this feature closed:
    weather_signal existed as a collector but was missing from both
    domains.yaml and ResearchNote's ResearchDomain Literal."""
    import yaml

    domains_yaml = set(yaml.safe_load((_CONFIG_ROOT / "domains.yaml").read_text(encoding="utf-8"))["domains"])
    literal_domains = set(ResearchDomain.__args__)
    assert domains_yaml == literal_domains
    assert len(domains_yaml) == 9
    assert "weather_signal" in domains_yaml


def test_collect_source_cmd_writes_a_real_note(tmp_path: Path) -> None:
    body_file = tmp_path / "body.md"
    body_file.write_text("Khách sạn có 12 phòng, view Hồ Tây.", encoding="utf-8")
    vault_root = tmp_path / "research"

    result = runner.invoke(
        app,
        [
            "collect-source", "--rs-id", "RS-TEST-0001", "--domain", "guest_voice",
            "--source-uri", "https://example.com/review", "--title", "test-review",
            "--body-file", str(body_file), "--vault-root", str(vault_root), "--config-root", str(_CONFIG_ROOT),
        ],
    )

    assert result.exit_code == 0, result.output
    written = Path(result.output.strip())
    assert written.exists()
    assert "domain: guest_voice" in written.read_text(encoding="utf-8")


def test_collect_source_cmd_rejects_unregistered_domain(tmp_path: Path) -> None:
    body_file = tmp_path / "body.md"
    body_file.write_text("x", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "collect-source", "--rs-id", "RS-TEST-0002", "--domain", "not_a_real_domain",
            "--source-uri", "https://example.com", "--title", "Test",
            "--body-file", str(body_file), "--vault-root", str(tmp_path / "research"), "--config-root", str(_CONFIG_ROOT),
        ],
    )

    assert result.exit_code != 0
    assert "not_a_real_domain" in result.output


def test_collect_note_cmd_writes_a_structured_note_with_observations(tmp_path: Path) -> None:
    vault_root = tmp_path / "research"

    result = runner.invoke(
        app,
        [
            "collect-note", "--rs-id", "RS-TEST-0003", "--domain", "weather_signal",
            "--source-uri", "https://example.com/weather", "--title", "test-weather",
            "--observation", "Nắng nhẹ", "--observation", "28 độ C",
            "--vault-root", str(vault_root), "--config-root", str(_CONFIG_ROOT),
        ],
    )

    assert result.exit_code == 0, result.output
    written = Path(result.output.strip())
    content = written.read_text(encoding="utf-8")
    assert "domain: weather_signal" in content
    assert "Nắng nhẹ" in content
    assert "28 độ C" in content
