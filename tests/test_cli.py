"""Phase 7 — CLI command registration tests.

Verifies:
  - Top-level app has 'vision' and 'vault' subgroups
  - vision subcommands: observe, bootstrap, analyze (legacy)
  - vault subcommands: search, diff, export
  - --help exits with code 0 for all groups
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from knowledge_studio.vision.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# TestTopLevel
# ---------------------------------------------------------------------------

class TestTopLevel:
    def test_top_level_help_exits_0(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_top_level_shows_vision_group(self):
        result = runner.invoke(app, ["--help"])
        assert "vision" in result.output

    def test_top_level_shows_vault_group(self):
        result = runner.invoke(app, ["--help"])
        assert "vault" in result.output


# ---------------------------------------------------------------------------
# TestVisionSubcommands
# ---------------------------------------------------------------------------

class TestVisionSubcommands:
    def test_vision_help_exits_0(self):
        result = runner.invoke(app, ["vision", "--help"])
        assert result.exit_code == 0

    def test_vision_has_observe_command(self):
        result = runner.invoke(app, ["vision", "--help"])
        assert "observe" in result.output

    def test_vision_has_bootstrap_command(self):
        result = runner.invoke(app, ["vision", "--help"])
        assert "bootstrap" in result.output

    def test_vision_has_analyze_legacy_command(self):
        result = runner.invoke(app, ["vision", "--help"])
        assert "analyze" in result.output

    def test_observe_help_exits_0(self):
        result = runner.invoke(app, ["vision", "observe", "--help"])
        assert result.exit_code == 0

    def test_observe_help_mentions_mode(self):
        result = runner.invoke(app, ["vision", "observe", "--help"])
        assert "--mode" in result.output

    def test_observe_help_mentions_one_subject_confirmation(self):
        result = runner.invoke(app, ["vision", "observe", "--help"])
        assert "--confirm-one-subject" in result.output

    def test_mode_b_aborts_when_one_subject_not_confirmed(self, tmp_path):
        image = tmp_path / "sample.jpg"
        image.write_bytes(b"fake image")
        result = runner.invoke(
            app,
            [
                "vision", "observe",
                "--mode", "b",
                "--project", "venho_hotel",
                "--subject", "room",
                "--input", str(tmp_path),
            ],
            input="n\n",
        )
        assert result.exit_code == 1
        assert "Aborted. Split the folder by tier/subject and retry." in result.output

    def test_bootstrap_help_exits_0(self):
        result = runner.invoke(app, ["vision", "bootstrap", "--help"])
        assert result.exit_code == 0

    def test_bootstrap_help_mentions_subject(self):
        result = runner.invoke(app, ["vision", "bootstrap", "--help"])
        assert "--subject" in result.output


# ---------------------------------------------------------------------------
# TestVaultSubcommands
# ---------------------------------------------------------------------------

class TestVaultSubcommands:
    def test_vault_help_exits_0(self):
        result = runner.invoke(app, ["vault", "--help"])
        assert result.exit_code == 0

    def test_vault_has_search_command(self):
        result = runner.invoke(app, ["vault", "--help"])
        assert "search" in result.output

    def test_vault_has_diff_command(self):
        result = runner.invoke(app, ["vault", "--help"])
        assert "diff" in result.output

    def test_vault_has_export_command(self):
        result = runner.invoke(app, ["vault", "--help"])
        assert "export" in result.output

    def test_vault_search_help_exits_0(self):
        result = runner.invoke(app, ["vault", "search", "--help"])
        assert result.exit_code == 0

    def test_vault_diff_help_exits_0(self):
        result = runner.invoke(app, ["vault", "diff", "--help"])
        assert result.exit_code == 0

    def test_vault_export_help_exits_0(self):
        result = runner.invoke(app, ["vault", "export", "--help"])
        assert result.exit_code == 0
