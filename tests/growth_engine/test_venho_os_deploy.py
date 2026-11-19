from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "ops/asus-server/venho-os/deploy-main.sh"
REQUIRED = "5c684b3eb8419109d9c00900d52a8148c2704bd5"


@pytest.mark.parametrize("case", ["success", "already_current", "already_current_inactive", "already_current_unhealthy", "build_failure", "missing_pr", "collision", "publish_window"])
def test_deploy_main_with_local_git_and_fake_services(tmp_path: Path, case: str) -> None:
    def git(directory: Path, *args: str) -> str:
        return subprocess.check_output(["git", "-C", str(directory), *args], text=True).strip()

    origin = tmp_path / "origin"
    origin.mkdir()
    git(origin, "init", "-q", "-b", "main")
    git(origin, "config", "user.name", "Fixture")
    git(origin, "config", "user.email", "fixture@example.test")
    (origin / "fixture").write_text("old")
    git(origin, "add", "fixture")
    git(origin, "commit", "-qm", "old")
    old = git(origin, "rev-parse", "HEAD")
    app = tmp_path / "venho/venho-os"
    app.parent.mkdir()
    git(tmp_path, "clone", "-q", str(origin), str(app))
    dotenv = app / ".env.local"
    dotenv.write_text("GROWTH_BACKEND=legacy\n")
    health = origin / "src/app/api/health/growth-backend/route.ts"
    health.parent.mkdir(parents=True)
    health.write_text("new")
    git(origin, "add", ".")
    git(origin, "commit", "-qm", "new")
    new = git(origin, "rev-parse", "HEAD")
    if case.startswith("already_current"):
        git(app, "pull", "--ff-only", "-q")
    if case == "collision":
        local = app / health.relative_to(origin)
        local.parent.mkdir(parents=True)
        local.write_text("untracked data")

    stubs = tmp_path / "bin"
    stubs.mkdir()
    scripts = {
        "git": f'''if [[ "$1 $2 $3" == "merge-base --is-ancestor {REQUIRED}" ]]; then
          [[ "$CASE" != missing_pr ]]
        else
          exec "{shutil.which("git")}" "$@"
        fi''',
        "date": '[[ "$CASE" == publish_window ]] && echo 0930 || echo 1200',
        "flock": "exit 0",
        "node": "exit 0",
        "npm": 'echo called >> "$HOME/npm_actions"; [[ "$CASE" != build_failure || "$(git rev-parse HEAD)" == "$OLD" || "$1" != run ]]',
        "systemctl": '''case "$2" in
          show) if [[ "$3" == *.timer ]]; then cat "$HOME/timer_state"; else echo inactive; fi ;;
          start|stop) printf '%s\\n' "$2" >> "$HOME/timer_actions"; if [[ "$2" == start ]]; then echo active; else echo inactive; fi > "$HOME/timer_state" ;;
          restart) echo called >> "$HOME/restart_actions"; git rev-parse HEAD > "$HOME/serving" ;;
          is-active) exit 0 ;;
        esac''',
        "curl": '''for last; do :; done
        if [[ "$last" == */login ]]; then echo 200; exit 0; fi
        while [[ "$1" != -D ]]; do shift; done
        : > "$2"
        if [[ "$(cat "$HOME/serving")" == "$OLD" ]]; then echo 404; else
          mode=legacy
          if [[ "$CASE" == already_current_unhealthy ]]; then mode=v2; fi
          printf 'X-Venho-Growth-Backend: %s\\r\\n' "$mode" > "$2"
          echo 204
        fi''',
    }
    for name, body in scripts.items():
        path = stubs / name
        path.write_text("#!/usr/bin/env bash\nset -e\n" + body + "\n")
        path.chmod(0o700)
    (tmp_path / "serving").write_text(new if case.startswith("already_current") else old)
    timer_before = "inactive" if case == "already_current_inactive" else "active"
    (tmp_path / "timer_state").write_text(timer_before + "\n")
    result = subprocess.run(
        ["bash", str(SCRIPT)], capture_output=True, text=True, timeout=20,
        env={**os.environ, "HOME": str(tmp_path), "PATH": f"{stubs}:{os.environ['PATH']}",
             "CASE": case, "OLD": old},
    )
    assert dotenv.read_text() == "GROWTH_BACKEND=legacy\n"
    expected_sha = new if case == "success" or case.startswith("already_current") else old
    assert (tmp_path / "serving").read_text().strip() == expected_sha
    assert git(app, "rev-parse", "HEAD") == expected_sha
    if case in {"success", "already_current", "already_current_inactive"}:
        assert result.returncode == 0, result.stderr
        assert "BACKEND=legacy HEALTH_HTTP=204 LOGIN_HTTP=200" in result.stdout
    else:
        assert result.returncode != 0
    if case.startswith("already_current"):
        assert not (tmp_path / "npm_actions").exists()
        assert not (tmp_path / "restart_actions").exists()
        if case != "already_current_unhealthy":
            assert "RESULT=already_current" in result.stdout
    if case != "publish_window":
        expected_timer = "inactive" if case == "build_failure" else timer_before
        assert f"AUTO_DEPLOY_TIMER=venho-os-deploy.timer BEFORE={timer_before} AFTER={expected_timer}" in result.stdout
        assert (tmp_path / "timer_state").read_text().strip() == expected_timer
    if case == "build_failure":
        assert "ROLLED_BACK" in result.stdout
        assert "start" not in (tmp_path / "timer_actions").read_text()
        assert git(app, "branch", "--show-current") == "main"
    if case == "missing_pr":
        assert "chưa merge PR" in result.stderr
    if case == "collision":
        assert local.read_text() == "untracked data"
    if case == "publish_window":
        assert not (tmp_path / "timer_actions").exists()
