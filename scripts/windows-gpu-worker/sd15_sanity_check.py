"""Run one local 512x512 SD1.5 ComfyUI API sanity inference.

This is worker infrastructure evidence, not an image-quality workflow. It
records installed API metadata and preserves complete HTTP error bodies so a
prompt-validation failure is never reported as a CUDA failure.
"""
import argparse
import json
import os
import struct
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zlib
from datetime import datetime, timezone


def request(url, data=None):
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def write_json(path, value):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)


def decode_error(exc):
    text = exc.read().decode("utf-8", errors="replace")
    try:
        body = json.loads(text)
    except json.JSONDecodeError:
        body = None
    return {"status": exc.code, "reason": str(exc.reason), "body": body, "body_text": text}


def png_stats(blob):
    if blob[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("output is not PNG")
    pos, width, height, bit_depth, color_type, chunks = 8, 0, 0, 0, 0, []
    while pos < len(blob):
        length = struct.unpack(">I", blob[pos:pos + 4])[0]
        kind, data = blob[pos + 4:pos + 8], blob[pos + 8:pos + 8 + length]
        pos += length + 12
        if kind == b"IHDR":
            width, height, bit_depth, color_type = struct.unpack(">IIBB", data[:10])
        if kind == b"IDAT":
            chunks.append(data)
    if bit_depth != 8 or color_type not in (2, 6):
        raise ValueError("only 8-bit RGB/RGBA PNG output is supported")
    raw, channels = zlib.decompress(b"".join(chunks)), 3 if color_type == 2 else 4
    stride, previous, values, offset = width * channels, bytearray(width * channels), [], 0
    for _ in range(height):
        filter_type, row = raw[offset], bytearray(raw[offset + 1:offset + 1 + stride])
        offset += stride + 1
        for i in range(stride):
            left = row[i - channels] if i >= channels else 0
            up, upper_left = previous[i], previous[i - channels] if i >= channels else 0
            if filter_type == 1:
                row[i] = (row[i] + left) & 255
            elif filter_type == 2:
                row[i] = (row[i] + up) & 255
            elif filter_type == 3:
                row[i] = (row[i] + ((left + up) // 2)) & 255
            elif filter_type == 4:
                p = left + up - upper_left
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - upper_left)
                row[i] = (row[i] + (left if pa <= pb and pa <= pc else up if pb <= pc else upper_left)) & 255
            elif filter_type != 0:
                raise ValueError(f"unsupported PNG filter {filter_type}")
        values.extend(row[i] for i in range(0, stride, channels))
        previous = row
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return {"width": width, "height": height, "mean_luma": mean, "pixel_std": variance ** 0.5,
            "non_black": max(values) > 5, "nan": False, "inf": False}


def workflow_contract(object_info, workflow):
    rows = []
    for node_id, node in workflow.items():
        class_type, submitted = node["class_type"], node["inputs"]
        node_inputs = object_info.get(class_type, {}).get("input", {})
        required = node_inputs.get("required", {})
        allowed = set(required) | set(node_inputs.get("optional", {}))
        rows.append({"node_id": node_id, "class_type": class_type,
                     "class_type_present": class_type in object_info,
                     "required_inputs": sorted(required), "submitted_inputs": sorted(submitted),
                     "missing_required_inputs": sorted(set(required) - set(submitted)),
                     "unexpected_inputs": sorted(set(submitted) - allowed)})
    return rows


def cuda_device_present(system_stats):
    return any("cuda" in json.dumps(device).lower() or "nvidia" in json.dumps(device).lower()
               for device in system_stats.get("devices", []))


def history_cuda_error(entry):
    text = json.dumps(entry).lower()
    return any(token in text for token in ("cuda error", "cuda out of memory", "cudnn", "cublas", "cuda runtime"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    parser.add_argument("--comfyui", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--evidence-dir")
    parser.add_argument("--seed", type=int, default=151515)
    args = parser.parse_args()
    workflow = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": args.checkpoint}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": "a simple studio photograph", "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {"seed": args.seed, "steps": 20, "cfg": 7.0,
              "sampler_name": "euler", "scheduler": "normal", "denoise": 1.0,
              "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0]}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": "gw_p1_sd15_sanity", "images": ["6", 0]}},
    }
    result = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "checkpoint": args.checkpoint,
              "checkpoint_path": os.path.join(args.comfyui, "models", "checkpoints", args.checkpoint),
              "resolution": [512, 512], "seed": args.seed, "prompt_accepted": False, "cuda_used": False,
              "output": None, "http_error": None, "comfy_prompt_validation_error": False,
              "cuda_runtime_exception": False, "error": None}
    try:
        object_info = json.loads(request(args.comfy_url + "/object_info"))
        system_stats = json.loads(request(args.comfy_url + "/system_stats"))
        result["api_contract"] = workflow_contract(object_info, workflow)
        result["system_stats_cuda_device_present"] = cuda_device_present(system_stats)
        if args.evidence_dir:
            write_json(os.path.join(args.evidence_dir, "comfyui_object_info.json"), object_info)
            write_json(os.path.join(args.evidence_dir, "comfyui_system_stats.json"), system_stats)
        payload = json.dumps({"prompt": workflow, "client_id": str(uuid.uuid4())}).encode("utf-8")
        try:
            queued = json.loads(request(args.comfy_url + "/prompt", payload))
        except urllib.error.HTTPError as exc:
            result["http_error"] = decode_error(exc)
            result["comfy_prompt_validation_error"] = exc.code == 400
            result["error"] = f"HTTP {exc.code} {exc.reason} from /prompt"
        else:
            prompt_id, result["prompt_accepted"] = queued["prompt_id"], True
            deadline, history = time.time() + 600, None
            while time.time() < deadline:
                history = json.loads(request(args.comfy_url + "/history/" + urllib.parse.quote(prompt_id)))
                if prompt_id in history and history[prompt_id].get("outputs"):
                    break
                if prompt_id in history and history_cuda_error(history[prompt_id]):
                    result["cuda_runtime_exception"] = True
                    break
                time.sleep(1)
            if not history or prompt_id not in history or not history[prompt_id].get("outputs"):
                raise TimeoutError("ComfyUI history timeout or execution produced no outputs")
            image = next((item for node in history[prompt_id]["outputs"].values() for item in node.get("images", [])), None)
            if not image:
                raise RuntimeError("ComfyUI produced no image output")
            query = urllib.parse.urlencode({"filename": image["filename"], "subfolder": image.get("subfolder", ""), "type": image.get("type", "output")})
            blob = request(args.comfy_url + "/view?" + query)
            with open(args.output, "wb") as handle:
                handle.write(blob)
            result["output"] = {"path": args.output, **png_stats(blob), "prompt_id": prompt_id}
            result["cuda_used"] = result["system_stats_cuda_device_present"]
    except urllib.error.HTTPError as exc:
        result["http_error"] = decode_error(exc)
        result["error"] = f"HTTP {exc.code} {exc.reason}"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    if args.evidence_dir and result["http_error"]:
        write_json(os.path.join(args.evidence_dir, "sd15_http_error.json"), result["http_error"])
    write_json(args.output + ".json", result)
    print(json.dumps(result, indent=2))
    ok = (result["prompt_accepted"] and result["cuda_used"] and result["output"]
          and result["output"]["width"] == 512 and result["output"]["height"] == 512
          and result["output"]["non_black"] and result["output"]["pixel_std"] > 5
          and not result["cuda_runtime_exception"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
