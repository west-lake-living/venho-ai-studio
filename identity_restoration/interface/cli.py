from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..infrastructure.composition.identity_restoration_module import build_identity_restoration_module
from ..infrastructure.composition.env import read_restoration_env
from .json_bridge import dump_result, load_restore_command


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="venho-restore")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run one identity restoration request end-to-end")
    run_p.add_argument("--request", required=True, type=Path, help="Path to a restoration_request JSON")
    run_p.add_argument("--restorer", default=None, help="Override restorerId (mock | comfyui-local)")

    sub.add_parser("health", help="Probe worker health and print WorkerHealth as JSON")

    args = parser.parse_args(argv)

    if args.command == "health":
        module = build_identity_restoration_module()
        health_use_case = module.check_health()
        if health_use_case is None:
            print('{"status": "MOCK_ONLY", "message": "IDR_COMFYUI_ENABLED=false, no worker configured"}')
            return 0
        result = health_use_case.execute()
        print(f'{{"status": "{result.status.value}", "gpuName": {result.gpu_name!r}, '
              f'"vramFreeMb": {result.vram_free_mb}}}')
        return 0

    if args.command == "run":
        module = build_identity_restoration_module()
        cmd = load_restore_command(args.request)
        if args.restorer:
            cmd = _with_restorer(cmd, args.restorer)
        result = module.use_case.execute(cmd)
        print(dump_result(result))
        return 0 if result.status in ("FULL_GATE_PASS", "NEEDS_REVIEW") else 1

    return 2


def _with_restorer(cmd, restorer_id: str):
    from dataclasses import replace
    return replace(cmd, restorer_id=restorer_id)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
