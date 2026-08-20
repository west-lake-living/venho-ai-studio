"""Read-only CUDA probe for the GW-P1 Windows worker."""
import json
import platform
import socket
import sys
from datetime import datetime, timezone


def main() -> int:
    result = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": sys.version,
        "torch": None,
        "torch_cuda": None,
        "cuda_available": False,
        "device_name": None,
        "device_count": 0,
        "vram_total_mb": None,
        "vram_free_mb": None,
        "error": None,
    }
    try:
        import torch

        result["torch"] = torch.__version__
        result["torch_cuda"] = torch.version.cuda
        result["cuda_available"] = bool(torch.cuda.is_available())
        result["device_count"] = int(torch.cuda.device_count())
        if result["cuda_available"]:
            result["device_name"] = torch.cuda.get_device_name(0)
            free, total = torch.cuda.mem_get_info(0)
            result["vram_free_mb"] = round(free / 1024 / 1024, 2)
            result["vram_total_mb"] = round(total / 1024 / 1024, 2)
    except Exception as exc:  # evidence collection must report, not hide
        result["error"] = f"{type(exc).__name__}: {exc}"
    print(json.dumps(result, indent=2))
    return 0 if result["cuda_available"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
