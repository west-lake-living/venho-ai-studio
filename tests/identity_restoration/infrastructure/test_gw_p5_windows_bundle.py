from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BUNDLE = ROOT / "scripts" / "windows-gpu-worker"


def test_gw_p5_windows_bundle_has_all_referenced_scripts() -> None:
    expected = {
        "gw_p5_t1_run_on_windows.ps1",
        "gw_p5_t1_register_autostart.ps1",
        "start_comfyui_worker.ps1",
        "gw_p5_hardening_verify_on_windows.ps1",
    }
    assert expected <= {path.name for path in BUNDLE.glob("*.ps1")}
    wrapper = (BUNDLE / "gw_p5_t1_run_on_windows.ps1").read_text(encoding="utf-8")
    assert "gw_p5_t1_register_autostart.ps1" in wrapper
    assert (BUNDLE / "gw_p5_t1_register_autostart.ps1").exists()


def test_gw_p5_bundle_is_ascii_safe_and_loopback_locked() -> None:
    for path in BUNDLE.glob("gw_p5_*.ps1"):
        text = path.read_text(encoding="utf-8")
        assert "â€" not in text, path
    launcher = (BUNDLE / "start_comfyui_worker.ps1").read_text(encoding="utf-8")
    assert "127.0.0.1" in launcher
    assert "0.0.0.0" in launcher
    assert "Refusing to start" in launcher


def test_gw_p5_scheduler_is_current_user_limited_and_verifier_is_resumable() -> None:
    register = (BUNDLE / "gw_p5_t1_register_autostart.ps1").read_text(encoding="utf-8")
    verifier = (BUNDLE / "gw_p5_hardening_verify_on_windows.ps1").read_text(encoding="utf-8")
    assert "-LogonType Interactive" in register
    assert "-RunLevel Limited" in register
    assert "-AtLogOn" in register
    assert "-Stage PreReboot" in verifier
    assert "-Stage PostReboot" in verifier
    assert "Restart-Computer" not in verifier
    assert "shutdown.exe" not in verifier


def test_gw_p5_soak_harness_is_bounded_and_stops_on_failure() -> None:
    harness = (ROOT / "scripts" / "gw_p5_worker_soak.py").read_text(encoding="utf-8")
    assert "args.count not in {2, 10}" in harness
    assert "stopped_on_failure" in harness
    assert "comfyui-remote" in harness
    assert "validator_studio" not in harness
    assert "gemini" not in harness.lower()
