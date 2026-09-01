from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/run_candidate_v3_r1_recovery_recheck.py"


def load_task():
    spec = importlib.util.spec_from_file_location("candidate_v3_r1_recovery_recheck", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_recovery_recheck_uses_a_separate_immutable_run_directory() -> None:
    task = load_task()
    assert "r1-recovery-recheck-" in str(task.OUT)
    assert task.OUT != task.R5


def test_recovery_recheck_is_locked_to_the_existing_probe_and_provider() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"FACE_LOCAL", "B01", 1' in source
    assert 'provider="gemini"' in source
    assert "runner.run()" not in source
    assert "separate authoritative resume task required" in source


def test_recovery_recheck_has_no_generation_or_provider_switch_path() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "ComfyUI" not in source
    assert "generate_image" not in source
    assert "openai" not in source.lower()
    assert "nano" in source.lower()
