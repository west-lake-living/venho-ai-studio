from __future__ import annotations

import os
import subprocess
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[2]
_WRAPPER = _ROOT / "ops/asus-server/growth-engine/run-with-legacy-provider-env.sh"


def test_wrapper_keeps_gc2_paths_and_reuses_only_legacy_provider_keys(tmp_path: Path) -> None:
    home = tmp_path / "home"
    secrets = home / "venho/secrets"
    secrets.mkdir(parents=True)
    (secrets / "growth.env").write_text(
        'GE_ENV="legacy"\n'
        'GE_DB_PATH="/tmp/legacy.db"\n'
        'ANTHROPIC_API_KEY="legacy-anthropic-synthetic"\n'
        'OPENAI_API_KEY="legacy-openai-synthetic"\n',
        encoding="utf-8",
    )
    (secrets / "growth-engine.env").write_text(
        'GE_ENV="production"\n'
        'GE_DB_PATH="/tmp/gc2-production.db"\n'
        'ANTHROPIC_API_KEY="gc2-must-not-win"\n'
        'OPENAI_API_KEY="gc2-must-not-win"\n',
        encoding="utf-8",
    )
    runtime = tmp_path / "venho-engine"
    runtime.write_text(
        "#!/usr/bin/env bash\n"
        'printf "GE_ENV=%s\\n" "$GE_ENV"\n'
        'printf "GE_DB_PATH=%s\\n" "$GE_DB_PATH"\n'
        '[[ "$ANTHROPIC_API_KEY" == "legacy-anthropic-synthetic" ]] && echo ANTHROPIC=LEGACY\n'
        '[[ "$OPENAI_API_KEY" == "legacy-openai-synthetic" ]] && echo OPENAI=LEGACY\n',
        encoding="utf-8",
    )
    runtime.chmod(0o700)

    result = subprocess.run(
        [str(_WRAPPER), "doctor"],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "HOME": str(home),
            "VENHO_GC2_RUNTIME_BIN": str(runtime),
        },
    )

    assert result.returncode == 0, result.stderr
    assert "GE_ENV=production" in result.stdout
    assert "GE_DB_PATH=/tmp/gc2-production.db" in result.stdout
    assert "ANTHROPIC=LEGACY" in result.stdout
    assert "OPENAI=LEGACY" in result.stdout
    assert "legacy-anthropic-synthetic" not in result.stdout + result.stderr
    assert "legacy-openai-synthetic" not in result.stdout + result.stderr
    assert "gc2-must-not-win" not in result.stdout + result.stderr
