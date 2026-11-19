from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "ops/asus-server/venho-os/deploy-main.sh"
REQUIRED = "5c684b3eb8419109d9c00900d52a8148c2704bd5"


@pytest.mark.parametrize("case", ["success", "build_failure", "missing_pr", "collision", "publish_window"])
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
        "npm": '[[ "$CASE" != build_failure || "$(git rev-parse HEAD)" == "$OLD" || "$1" != run ]]',
        "systemctl": '''case "$2" in
          show) echo inactive ;;
          start|stop) printf '%s\\n' "$2" >> "$HOME/timer_actions" ;;
          restart) git rev-parse HEAD > "$HOME/serving" ;;
          is-active) exit 0 ;;
        esac''',
        "curl": '''for last; do :; done
        if [[ "$last" == */login ]]; then echo 200; exit 0; fi
        while [[ "$1" != -D ]]; do shift; done
        : > "$2"
        if [[ "$(cat "$HOME/serving")" == "$OLD" ]]; then echo 404; else
          printf 'X-Venho-Growth-Backend: legacy\\r\\n' > "$2"
          echo 204
        fi''',
    }
    for name, body in scripts.items():
        path = stubs / name
        path.write_text("#!/usr/bin/env bash\nset -e\n" + body + "\n")
        path.chmod(0o700)
    (tmp_path / "serving").write_text(old)
    result = subprocess.run(
        ["bash", str(SCRIPT)], capture_output=True, text=True, timeout=20,
        env={**os.environ, "HOME": str(tmp_path), "PATH": f"{stubs}:{os.environ['PATH']}",
             "CASE": case, "OLD": old},
    )
    assert dotenv.read_text() == "GROWTH_BACKEND=legacy\n"
    assert (tmp_path / "serving").read_text().strip() == (new if case == "success" else old)
    assert git(app, "rev-parse", "HEAD") == (new if case == "success" else old)
    if case == "success":
        assert result.returncode == 0, result.stderr
        assert "BACKEND=legacy HEALTH_HTTP=204 LOGIN_HTTP=200" in result.stdout
    else:
        assert result.returncode != 0
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
