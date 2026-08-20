"""Run read-only CUDA precision smoke checks for the GTX 1660 Super.

The orchestrator supplies the ComfyUI startup flags. This script does not
alter checkpoints, workflows, thresholds, or model files.
"""
import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone


def check_config(name, flags):
    row = {"name": name, "flags": flags, "stable": False,
           "checks": {"nan": None, "inf": None, "black_output": None,
                      "cuda_runtime_exception": False}, "error": None}
    try:
        import torch

        row["checks"]["cuda_available"] = bool(torch.cuda.is_available())
        if not row["checks"]["cuda_available"]:
            raise RuntimeError("torch.cuda.is_available() is false")
        device = torch.device("cuda:0")
        dtype = torch.float16 if "force-fp32" not in flags else torch.float32
        torch.cuda.empty_cache()
        a = torch.randn((512, 512), device=device, dtype=dtype)
        b = torch.randn((512, 512), device=device, dtype=dtype)
        value = torch.mm(a, b)
        finite = bool(torch.isfinite(value).all().item())
        maximum = float(value.abs().max().item())
        has_nan = bool(torch.isnan(value).any().item())
        has_inf = bool(torch.isinf(value).any().item())
        row["checks"].update({"finite_tensor": finite, "nan": has_nan, "inf": has_inf,
                               "black_output": maximum <= 1e-8, "non_black_numeric_output": maximum > 1e-8,
                               "max_abs": maximum, "device": torch.cuda.get_device_name(0)})
        row["stable"] = finite and maximum > 1e-8
        torch.cuda.synchronize()
    except Exception as exc:
        row["checks"]["cuda_runtime_exception"] = True
        row["error"] = f"{type(exc).__name__}: {exc}"
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--configs", default="A:--lowvram,--fp32-vae;B:--lowvram,--force-fp32;C:--novram,--force-fp32")
    args = parser.parse_args()
    configs = []
    for item in args.configs.split(";"):
        name, raw_flags = item.split(":", 1)
        configs.append((name, [flag for flag in raw_flags.split(",") if flag]))
    rows = [check_config(name, flags) for name, flags in configs]
    selected = next((row for row in rows if row["stable"]), None)
    report = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "configs": rows,
              "first_stable_config": selected, "result": "PASS" if selected else "FAIL"}
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2))
    return 0 if selected else 1


if __name__ == "__main__":
    raise SystemExit(main())
