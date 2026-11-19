from __future__ import annotations

import errno
import os
import pty
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest


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
        'OPENAI_API_KEY="legacy-openai-synthetic"\n'
        'GOOGLE_OAUTH_CLIENT_ID="legacy-client-id-synthetic"\n'
        'GOOGLE_OAUTH_CLIENT_SECRET="legacy-client-secret-synthetic"\n',
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
        '[[ "$OPENAI_API_KEY" == "legacy-openai-synthetic" ]] && echo OPENAI=LEGACY\n'
        '[[ -z "${GOOGLE_DRIVE_TOKEN_JSON:-}" ]] && echo GOOGLE_DRIVE=NOT_INJECTED\n'
        '[[ -z "${GOOGLE_OAUTH_CLIENT_ID:-}" ]] && echo GOOGLE_CLIENT_ID=NOT_INJECTED\n'
        '[[ -z "${GOOGLE_OAUTH_CLIENT_SECRET:-}" ]] && echo GOOGLE_CLIENT_SECRET=NOT_INJECTED\n',
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
    assert "GOOGLE_DRIVE=NOT_INJECTED" in result.stdout
    assert "GOOGLE_CLIENT_ID=NOT_INJECTED" in result.stdout
    assert "GOOGLE_CLIENT_SECRET=NOT_INJECTED" in result.stdout
    assert "legacy-anthropic-synthetic" not in result.stdout + result.stderr
    assert "legacy-openai-synthetic" not in result.stdout + result.stderr
    assert "gc2-must-not-win" not in result.stdout + result.stderr
    assert "legacy-drive-synthetic" not in result.stdout + result.stderr
    assert "legacy-client-id-synthetic" not in result.stdout + result.stderr
    assert "legacy-client-secret-synthetic" not in result.stdout + result.stderr


def _operator_environment(tmp_path: Path) -> tuple[dict[str, str], Path]:
    home = tmp_path / "home"
    secrets = home / "venho/secrets"
    secrets.mkdir(parents=True)
    (secrets / "growth-engine.env").write_text("GE_ENV=production\n")
    bin_dir = tmp_path / "release/.venv/bin"
    bin_dir.mkdir(parents=True)
    runtime = bin_dir / "venho-engine"
    runtime.touch(mode=0o700)
    (bin_dir / "python").symlink_to(sys.executable)
    call_log = tmp_path / "calls"
    stub = bin_dir / "systemd-run"
    stub.write_text(
        '#!/usr/bin/env bash\n'
        'while [[ "$1" == --* ]]; do shift; done\n'
        'shift\n'
        'if { : >&3; } 2>/dev/null; then exit 99; fi\n'
        'printf "%s\u005cn" "$*" >> "$CALL_LOG"\n'
        'if [[ "${!#}" == --preflight-only ]]; then\n'
        '  printf "PREFLIGHT_STARTED\u005cn" >&2\n'
        '  sleep 0.3\n'
        '  echo \'{"preflight": "READY"}\'\n'
        'fi\n'
    )
    stub.chmod(0o700)
    return {
        **os.environ, "HOME": str(home), "VENHO_GC2_RUNTIME_BIN": str(runtime),
        "PATH": f"{bin_dir}:{os.environ['PATH']}", "CALL_LOG": str(call_log),
    }, call_log


def test_operator_wrapper_blocks_without_controlling_tty(tmp_path: Path) -> None:
    env, call_log = _operator_environment(tmp_path)
    result = subprocess.run(
        [str(_WRAPPER), "reprocess-p4-qc-evidence", "--job", "job-a"],
        start_new_session=True, input="REPROCESS\n", capture_output=True, text=True, env=env,
    )
    assert result.returncode == 2
    assert "ERR_GC2_OPERATOR_TTY_REQUIRED" in result.stderr
    assert not call_log.exists()


@pytest.mark.parametrize(("command", "action", "answer", "status"), [
    ("reprocess-p4-qc-evidence", "REPROCESS", "wrong", 2),
    ("reprocess-p4-qc-evidence", "REPROCESS", "REPROCESS", 0),
    ("resolve-p4-qc-unknown", "RESOLVE", "RESOLVE", 0),
])
def test_operator_wrapper_confirms_only_fresh_tty_input(
    tmp_path: Path, command: str, action: str, answer: str, status: int
) -> None:
    env, call_log = _operator_environment(tmp_path)
    pid, terminal = pty.fork()
    if pid == 0:
        with open(os.devnull, "rb") as source:
            os.dup2(source.fileno(), 0)
        os.execve(str(_WRAPPER), [str(_WRAPPER), command, "--job", "job-a"], env)

    def read_until(marker: bytes) -> bytes:
        data = b""
        deadline = time.monotonic() + 8
        while marker not in data:
            remaining = deadline - time.monotonic()
            assert remaining > 0 and select.select([terminal], [], [], remaining)[0], data
            data += os.read(terminal, 4096)
        return data

    finished = False
    try:
        read_until(b"PREFLIGHT_STARTED")
        # Both a complete stale answer and a partial line must be discarded.
        os.write(terminal, f"{action}\nSTALE".encode())
        assert b'"preflight": "READY"' in read_until(f"job job-a: ".encode())
        assert call_log.read_text().splitlines() == [f"{command} --job job-a --preflight-only"]
        os.write(terminal, f"{answer}\n".encode())
        if status:
            read_until(f"{action}=DECLINED".encode())
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            waited, exit_status = os.waitpid(pid, os.WNOHANG)
            if waited:
                finished = True
                break
            if select.select([terminal], [], [], 0.02)[0]:
                try:
                    os.read(terminal, 4096)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
        assert finished and os.waitstatus_to_exitcode(exit_status) == status
    finally:
        os.close(terminal)
        if not finished:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, os.WNOHANG)

    expected = [f"{command} --job job-a --preflight-only"]
    if status == 0:
        expected.append(f"{command} --job job-a --operator-confirmed {action}:job-a")
    assert call_log.read_text().splitlines() == expected
