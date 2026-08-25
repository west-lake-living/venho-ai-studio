"""GW-P3 Windows-side author/probe entrypoint.

This file intentionally contains no project-specific image generation logic.
It discovers the installed ComfyUI schemas and plugin examples at runtime,
then submits only a graph that passed those live checks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(r"C:\VenHoGPU")
COMFY_ROOT = ROOT / "comfyui"
PYTHON = ROOT / "venv" / "Scripts" / "python.exe"
BASE_URL = "http://127.0.0.1:8188"
CHECKPOINT = "v1-5-pruned-emaonly.safetensors"
CLIP_VISION = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
IPADAPTER = "ip-adapter-faceid-plusv2_sd15.bin"
LORA = "ip-adapter-faceid-plusv2_sd15_lora.safetensors"
PLUGIN = COMFY_ROOT / "custom_nodes" / "ComfyUI_IPAdapter_plus"
CANONICAL_A2_SHA256 = "1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d"
CANONICAL_A2_AUTHORITY = (
    "venho-social-content-agent/assets/face-plates/A2_Front_plate.png"
)
REQUIRED_CLASSES = (
    "CheckpointLoaderSimple", "LoadImage", "LoadImageMask", "VAEEncode",
    "VAEDecode", "SetLatentNoiseMask", "CLIPTextEncode", "KSampler",
    "SaveImage", "IPAdapterUnifiedLoaderFaceID", "IPAdapterInsightFaceLoader",
    "IPAdapterFaceID",
)
# These are resolved from the live /object_info response. They are not assumed
# to exist on a worker: the graph builder fails closed if any schema is absent.
GEOMETRY_CLASSES = ("ImagePadForOutpaint", "ImageCrop", "MaskToImage", "ImageToMask")


class ProbeError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_dump(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def request(method: str, path: str, data: bytes | None = None,
            headers: dict[str, str] | None = None, timeout: int = 30) -> tuple[int, bytes]:
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ProbeError(f"HTTP {exc.code} {method} {path}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise ProbeError(f"ComfyUI unavailable at {BASE_URL}: {exc.reason}") from exc


def get_json(path: str) -> Any:
    status, raw = request("GET", path)
    if status != 200:
        raise ProbeError(f"GET {path} returned HTTP {status}")
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ProbeError(f"GET {path} did not return JSON: {exc}") from exc


def multipart(fields: dict[str, str], file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = "----GW-P3-" + uuid.uuid4().hex
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks += [f"--{boundary}\r\n".encode(),
                   f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                   value.encode(), b"\r\n"]
    chunks += [f"--{boundary}\r\n".encode(),
               f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'.encode(),
               b"Content-Type: application/octet-stream\r\n\r\n",
               file_path.read_bytes(), b"\r\n",
               f"--{boundary}--\r\n".encode()]
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def upload(path: Path, upload_type: str = "input") -> str:
    body, content_type = multipart({"type": upload_type, "overwrite": "false"}, "image", path)
    status, raw = request("POST", "/upload/image", body,
                          {"Content-Type": content_type}, timeout=60)
    if status != 200:
        raise ProbeError(f"upload returned HTTP {status}")
    result = json.loads(raw.decode("utf-8"))
    name = result.get("name")
    if not name:
        raise ProbeError(f"upload response did not contain a filename: {result}")
    return str(name)


def image_check(path: Path) -> dict[str, Any]:
    try:
        from PIL import Image  # type: ignore
    except ImportError as exc:
        raise ProbeError("Pillow is required in C:\\VenHoGPU\\venv to validate image outputs") from exc
    try:
        with Image.open(path) as image:
            image.load()
            return {"format": image.format, "width": image.width,
                    "height": image.height, "mode": image.mode}
    except Exception as exc:  # Pillow exposes several decoder-specific exceptions.
        raise ProbeError(f"image is not decodable: {path}: {exc}") from exc


def geometry_plan(width: int, height: int, multiple: int = 8) -> dict[str, int]:
    """Return deterministic right/bottom padding and original output geometry."""
    if width <= 0 or height <= 0:
        raise ProbeError(f"input crop dimensions must be positive: {width}x{height}")
    if multiple <= 0:
        raise ProbeError("geometry multiple must be positive")
    padded_width = ((width + multiple - 1) // multiple) * multiple
    padded_height = ((height + multiple - 1) // multiple) * multiple
    return {
        "original_width": width,
        "original_height": height,
        "pad_left": 0,
        "pad_top": 0,
        "pad_right": padded_width - width,
        "pad_bottom": padded_height - height,
        "padded_width": padded_width,
        "padded_height": padded_height,
        "multiple": multiple,
    }


def required_paths() -> dict[str, Path]:
    return {
        "python": PYTHON,
        "comfyui_main": COMFY_ROOT / "main.py",
        "checkpoint": COMFY_ROOT / "models" / "checkpoints" / CHECKPOINT,
        "clip_vision": COMFY_ROOT / "models" / "clip_vision" / CLIP_VISION,
        "ipadapter": COMFY_ROOT / "models" / "ipadapter" / IPADAPTER,
        "lora": COMFY_ROOT / "models" / "loras" / LORA,
        "plugin": PLUGIN,
    }


def verify_files() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for label, path in required_paths().items():
        if not path.exists():
            raise ProbeError(f"required {label} missing: {path}")
        result[label] = {"path": str(path), "bytes": path.stat().st_size if path.is_file() else None}
    return result


def verify_python_packages() -> dict[str, str]:
    code = (
        "import insightface, onnxruntime; "
        "print('insightface='+getattr(insightface, '__version__', 'unknown')); "
        "print('onnxruntime='+getattr(onnxruntime, '__version__', 'unknown')); "
        "print('providers='+','.join(onnxruntime.get_available_providers()))"
    )
    completed = subprocess.run([str(PYTHON), "-c", code], capture_output=True, text=True)
    if completed.returncode:
        raise ProbeError("Python dependency check failed:\n" + completed.stderr.strip())
    values: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    if "CUDAExecutionProvider" not in values.get("providers", ""):
        raise ProbeError("onnxruntime-gpu is not exposing CUDAExecutionProvider")
    return values


def discover_examples() -> list[Path]:
    if not PLUGIN.is_dir():
        raise ProbeError(f"plugin directory missing: {PLUGIN}")
    examples = PLUGIN / "examples"
    if not examples.is_dir():
        raise ProbeError(f"plugin examples directory missing: {examples}")
    candidates = []
    for path in examples.rglob("*"):
        if path.suffix.lower() in {".json", ".workflow", ".txt"}:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError:
                continue
            if "faceid" in text and ("sd15" in text or "sd1.5" in text or "plusv2" in text):
                candidates.append(path)
    return sorted(candidates)


def plugin_commit() -> str:
    completed = subprocess.run(["git", "-C", str(PLUGIN), "rev-parse", "HEAD"],
                               capture_output=True, text=True)
    if completed.returncode:
        raise ProbeError(f"could not read plugin commit from {PLUGIN}: {completed.stderr.strip()}")
    return completed.stdout.strip()


def schema_inputs(info: dict[str, Any], class_type: str) -> set[str]:
    definition = info.get(class_type)
    if not isinstance(definition, dict):
        return set()
    input_data = definition.get("input", {})
    names: set[str] = set()
    for section in ("required", "optional"):
        values = input_data.get(section, {}) if isinstance(input_data, dict) else {}
        if isinstance(values, dict):
            names.update(values.keys())
    return names


def choose_name(names: set[str], aliases: tuple[str, ...], label: str) -> str:
    for alias in aliases:
        if alias in names:
            return alias
    raise ProbeError(f"live schema has no supported {label} input; available={sorted(names)}")


def link(node_id: str, output_index: int = 0) -> list[Any]:
    return [node_id, output_index]


def require_inputs(info: dict[str, Any], class_type: str, required: set[str]) -> set[str]:
    if class_type not in info:
        raise ProbeError(f"live /object_info is missing required geometry node: {class_type}")
    names = schema_inputs(info, class_type)
    if not required.issubset(names):
        raise ProbeError(
            f"live schema for {class_type} is incompatible; required={sorted(required)}, "
            f"available={sorted(names)}"
        )
    return names


def build_graph(info: dict[str, Any], crop_name: str, mask_name: str, a2_name: str,
                seed: int, denoise: float,
                crop_size: tuple[int, int] | None = None) -> tuple[dict[str, Any], str]:
    missing = [name for name in REQUIRED_CLASSES if name not in info]
    if missing:
        raise ProbeError("live /object_info is missing required classes: " + ", ".join(missing))
    if crop_size is None:
        raise ProbeError("original crop dimensions are required before building the graph")
    original_width, original_height = crop_size
    plan = geometry_plan(original_width, original_height)
    require_inputs(info, "ImagePadForOutpaint", {"image", "left", "top", "right", "bottom", "feathering"})
    require_inputs(info, "ImageCrop", {"image", "width", "height", "x", "y"})
    require_inputs(info, "MaskToImage", {"mask"})
    require_inputs(info, "ImageToMask", {"image", "channel"})

    # The graph is deliberately assembled from live socket names. Values are only
    # written when the installed node declares that socket.
    graph: dict[str, Any] = {}
    graph["1"] = {"class_type": "CheckpointLoaderSimple", "inputs": {
        choose_name(schema_inputs(info, "CheckpointLoaderSimple"), ("ckpt_name",), "checkpoint"): CHECKPOINT}}
    graph["2"] = {"class_type": "LoadImage", "inputs": {"image": crop_name}}
    graph["3"] = {"class_type": "LoadImage", "inputs": {"image": a2_name}}
    graph["4"] = {"class_type": "LoadImageMask", "inputs": {
        "image": mask_name, "channel": "red"}}
    # ComfyUI's SD1.5 VAE path requires dimensions divisible by eight. Pad only
    # on the right/bottom, then crop the decoded result to the exact source size.
    # The same deterministic pad is applied to the mask through IMAGE -> MASK.
    graph["15"] = {"class_type": "MaskToImage", "inputs": {"mask": link("4", 0)}}
    graph["16"] = {"class_type": "ImagePadForOutpaint", "inputs": {
        "image": link("2", 0), "left": plan["pad_left"], "top": plan["pad_top"],
        "right": plan["pad_right"], "bottom": plan["pad_bottom"], "feathering": 0}}
    graph["17"] = {"class_type": "ImagePadForOutpaint", "inputs": {
        "image": link("15", 0), "left": plan["pad_left"], "top": plan["pad_top"],
        "right": plan["pad_right"], "bottom": plan["pad_bottom"], "feathering": 0}}
    graph["18"] = {"class_type": "ImageToMask", "inputs": {
        "image": link("17", 0), "channel": "red"}}
    graph["5"] = {"class_type": "VAEEncode", "inputs": {
        choose_name(schema_inputs(info, "VAEEncode"), ("pixels",), "VAE pixels"): link("16", 0),
        choose_name(schema_inputs(info, "VAEEncode"), ("vae",), "VAE"): link("1", 2)}}
    graph["6"] = {"class_type": "SetLatentNoiseMask", "inputs": {
        choose_name(schema_inputs(info, "SetLatentNoiseMask"), ("samples",), "latent samples"): link("5", 0),
        choose_name(schema_inputs(info, "SetLatentNoiseMask"), ("mask",), "latent mask"): link("18", 0)}}

    positive_names = schema_inputs(info, "CLIPTextEncode")
    clip_socket = choose_name(positive_names, ("clip",), "CLIP")
    text_socket = choose_name(positive_names, ("text",), "positive prompt")
    graph["7"] = {"class_type": "CLIPTextEncode", "inputs": {clip_socket: link("1", 1), text_socket: "identity restoration"}}
    graph["8"] = {"class_type": "CLIPTextEncode", "inputs": {clip_socket: link("1", 1), text_socket: "low quality, deformed face"}}

    insight_names = schema_inputs(info, "IPAdapterInsightFaceLoader")
    required_insight = {"provider", "model_name"}
    if not required_insight.issubset(insight_names):
        raise ProbeError(
            "IPAdapterInsightFaceLoader live schema changed; required inputs="
            f"{sorted(required_insight)}, available={sorted(insight_names)}"
        )
    insight_inputs = {"provider": "CUDA", "model_name": "buffalo_l"}
    graph["9"] = {"class_type": "IPAdapterInsightFaceLoader", "inputs": insight_inputs}

    unified_names = schema_inputs(info, "IPAdapterUnifiedLoaderFaceID")
    required_unified = {"model", "preset", "lora_strength", "provider"}
    if not required_unified.issubset(unified_names):
        raise ProbeError(
            "IPAdapterUnifiedLoaderFaceID live schema changed; required inputs="
            f"{sorted(required_unified)}, available={sorted(unified_names)}"
        )
    # The installed Unified Loader selects the matching FaceID model/LoRA from
    # its preset. It does not accept a LoRA filename/path input.
    unified_inputs = {
        "model": link("1", 0),
        "preset": "FACEID PLUS V2",
        "lora_strength": 0.6,
        "provider": "CUDA",
    }
    graph["10"] = {"class_type": "IPAdapterUnifiedLoaderFaceID", "inputs": unified_inputs}

    adapter_names = schema_inputs(info, "IPAdapterFaceID")
    required_adapter = {
        "model", "ipadapter", "image", "weight", "weight_faceidv2",
        "weight_type", "combine_embeds", "start_at", "end_at", "embeds_scaling",
    }
    if not required_adapter.issubset(adapter_names):
        raise ProbeError(
            "IPAdapterFaceID live schema changed; required inputs="
            f"{sorted(required_adapter)}, available={sorted(adapter_names)}"
        )
    adapter: dict[str, Any] = {
        "model": link("10", 0),
        "ipadapter": link("10", 1),
        "image": link("3", 0),
        "weight": 1.0,
        "weight_faceidv2": 1.0,
        "weight_type": "linear",
        "combine_embeds": "concat",
        "start_at": 0.0,
        "end_at": 1.0,
        "embeds_scaling": "V only",
    }
    # InsightFace is optional in the live schema but is required for this
    # functional FaceID run. Never silently omit it or switch providers.
    if "insightface" not in adapter_names:
        raise ProbeError("IPAdapterFaceID live schema has no optional insightface socket")
    adapter["insightface"] = link("9", 0)
    graph["11"] = {"class_type": "IPAdapterFaceID", "inputs": adapter}

    sampler_names = schema_inputs(info, "KSampler")
    sampler: dict[str, Any] = {}
    values = {
        "model": link("11", 0), "positive": link("7", 0), "negative": link("8", 0),
        "latent_image": link("6", 0), "seed": seed, "steps": 20, "cfg": 6.0,
        "sampler_name": "euler", "scheduler": "normal", "denoise": denoise,
    }
    for name, value in values.items():
        if name in sampler_names:
            sampler[name] = value
    required_sampler = ("model", "positive", "negative", "latent_image", "seed", "steps", "cfg", "denoise")
    for required in required_sampler:
        if required in sampler_names and required not in sampler:
            raise ProbeError(f"could not bind live KSampler socket: {required}")
    graph["12"] = {"class_type": "KSampler", "inputs": sampler}
    graph["13"] = {"class_type": "VAEDecode", "inputs": {"samples": link("12", 0), "vae": link("1", 2)}}
    graph["19"] = {"class_type": "ImageCrop", "inputs": {
        "image": link("13", 0), "width": original_width, "height": original_height,
        "x": 0, "y": 0}}
    graph["14"] = {"class_type": "SaveImage", "inputs": {"images": link("19", 0), "filename_prefix": "gw-p3"}}

    return graph, "runtime_schema_derived_sd15_faceid_v2_exact_geometry"


def validate_graph(graph: dict[str, Any], info: dict[str, Any]) -> None:
    """Reject unknown classes/sockets before the real /prompt request."""
    for node_id, node in graph.items():
        class_type = node.get("class_type")
        if class_type not in info:
            raise ProbeError(f"graph node {node_id} uses unknown live class_type: {class_type}")
        declared = schema_inputs(info, class_type)
        for input_name in node.get("inputs", {}):
            if input_name not in declared:
                raise ProbeError(
                    f"graph node {node_id} ({class_type}) uses unsupported input "
                    f"{input_name}; live inputs={sorted(declared)}"
                )
    encoded = json.dumps(graph, separators=(",", ":"))
    json.loads(encoded)


def persist_preflight(evidence: Path, stats: Any, object_info: dict[str, Any],
                      package_info: dict[str, str], files: dict[str, Any], examples: list[Path]) -> None:
    json_dump(evidence / "system_stats.json", stats)
    snapshot_classes = REQUIRED_CLASSES + GEOMETRY_CLASSES
    json_dump(evidence / "object_info_required_nodes.json",
              {name: object_info.get(name) for name in snapshot_classes if name in object_info})
    (evidence / "plugin_commit.txt").write_text(plugin_commit() + "\n", encoding="utf-8")
    (evidence / "workflow_lineage.txt").write_text(
        "Installed plugin examples searched:\n" + "\n".join(map(str, examples)) +
        "\nGeometry lineage: runtime_schema_derived_sd15_faceid_v2_exact_geometry\n", encoding="utf-8")
    (evidence / "environment.txt").write_text(
        json.dumps({"python": str(PYTHON), "packages": package_info, "files": files}, indent=2) + "\n",
        encoding="utf-8")


def start_comfyui() -> subprocess.Popen[Any]:
    command = [str(PYTHON), str(COMFY_ROOT / "main.py"), "--listen", "127.0.0.1",
               "--port", "8188", "--lowvram", "--fp32-vae"]
    log_path = ROOT / "logs" / "gw-p3-comfyui.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("a", encoding="utf-8")
    return subprocess.Popen(command, cwd=str(COMFY_ROOT), stdout=log_handle,
                            stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))


def wait_for_health(timeout: int = 90) -> Any:
    deadline = time.time() + timeout
    last: Exception | None = None
    while time.time() < deadline:
        try:
            return get_json("/system_stats")
        except Exception as exc:  # report the final actionable error after the bounded wait.
            last = exc
            time.sleep(2)
    raise ProbeError(f"ComfyUI did not become healthy within {timeout}s: {last}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crop", required=True)
    parser.add_argument("--mask", required=True)
    parser.add_argument("--a2", required=True)
    parser.add_argument("--seed", type=int, default=123456)
    parser.add_argument("--denoise", type=float, default=0.35)
    parser.add_argument("--output-root", default=str(ROOT / "evidence"))
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--start-comfyui", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    evidence = Path(args.output_root) / ("gw-p3-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    evidence.mkdir(parents=True, exist_ok=False)
    log_path = evidence / "execution.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    logging.getLogger().addHandler(file_handler)
    try:
        crop, mask, a2 = map(lambda value: Path(value).resolve(), (args.crop, args.mask, args.a2))
        for label, path in (("crop", crop), ("mask", mask), ("A2", a2)):
            if not path.is_file():
                raise ProbeError(f"{label} image does not exist: {path}")
        if not 0 <= args.denoise <= 1 or args.seed < 0:
            raise ProbeError("seed must be >= 0 and denoise must be between 0 and 1")
        input_meta = {name: image_check(path) for name, path in (("crop", crop), ("mask", mask), ("a2", a2))}
        if (input_meta["mask"]["width"], input_meta["mask"]["height"]) != (
            input_meta["crop"]["width"], input_meta["crop"]["height"]
        ):
            raise ProbeError(
                "mask geometry must equal input crop geometry: "
                f"crop={input_meta['crop']['width']}x{input_meta['crop']['height']}, "
                f"mask={input_meta['mask']['width']}x{input_meta['mask']['height']}"
            )
        actual_a2_sha256 = sha256(a2)
        if actual_a2_sha256 != CANONICAL_A2_SHA256:
            raise ProbeError(
                "A2 authority mismatch: expected "
                f"{CANONICAL_A2_SHA256} for {CANONICAL_A2_AUTHORITY}, got {actual_a2_sha256}. "
                "Do not use assets/raw/linh_an/A2_Front.png."
            )
        files = verify_files()
        packages = verify_python_packages()
        try:
            stats = get_json("/system_stats")
            object_info = get_json("/object_info")
        except ProbeError:
            if not args.start_comfyui:
                raise ProbeError("ComfyUI is offline. Re-run with -StartComfyUI for the frozen startup flags.")
            start_comfyui()
            stats = wait_for_health()
            object_info = get_json("/object_info")
        if not isinstance(object_info, dict):
            raise ProbeError("/object_info did not return a JSON object")
        examples = discover_examples()
        persist_preflight(evidence, stats, object_info, packages, files, examples)
        for label, path in (("input_crop", crop), ("input_mask", mask), ("input_a2", a2)):
            shutil.copyfile(path, evidence / (label + ".png"))
            (evidence / (label + ".sha256")).write_text(sha256(path) + "  " + path.name + "\n", encoding="utf-8")
        if args.preflight_only:
            report = {"status": "PASS", "mode": "preflight", "evidence": str(evidence),
                      "inputs": input_meta, "a2_authority": {
                          "sha256": actual_a2_sha256, "expected_sha256": CANONICAL_A2_SHA256,
                          "source": CANONICAL_A2_AUTHORITY}}
            json_dump(evidence / "verification_report.json", report)
            (evidence / "verification_report.txt").write_text("PASS\nPreflight only; no inference performed.\n", encoding="utf-8")
            print(json.dumps(report, indent=2))
            return 0

        crop_name, mask_name, a2_name = upload(crop), upload(mask), upload(a2)
        graph, lineage = build_graph(
            object_info, crop_name, mask_name, a2_name, args.seed, args.denoise,
            crop_size=(input_meta["crop"]["width"], input_meta["crop"]["height"]),
        )
        validate_graph(graph, object_info)
        json_dump(evidence / "workflow_api.json", graph)
        (evidence / "workflow_api.sha256").write_text(sha256(evidence / "workflow_api.json") + "\n", encoding="utf-8")
        (evidence / "workflow_lineage.txt").write_text(
            (evidence / "workflow_lineage.txt").read_text(encoding="utf-8") + f"Selected lineage: {lineage}\n", encoding="utf-8")
        request_payload = {"prompt": graph, "client_id": "gw-p3-" + uuid.uuid4().hex}
        json_dump(evidence / "request_payload.json", request_payload)
        status, raw = request("POST", "/prompt", json.dumps(request_payload).encode(), {"Content-Type": "application/json"})
        prompt_response = json.loads(raw.decode("utf-8"))
        json_dump(evidence / "prompt_response.json", prompt_response)
        prompt_id = prompt_response.get("prompt_id")
        if status != 200 or not prompt_id:
            raise ProbeError(f"ComfyUI rejected prompt: {prompt_response}")
        (evidence / "prompt_id.txt").write_text(str(prompt_id) + "\n", encoding="utf-8")
        deadline = time.time() + 900
        history = None
        while time.time() < deadline:
            history = get_json("/history/" + urllib.parse.quote(str(prompt_id), safe=""))
            entry = history.get(str(prompt_id), {}) if isinstance(history, dict) else {}
            if entry.get("status", {}).get("completed") or entry.get("outputs"):
                break
            if entry.get("status", {}).get("status_str") == "error":
                raise ProbeError(f"ComfyUI execution error: {entry}")
            time.sleep(2)
        if history is None:
            raise ProbeError("ComfyUI history polling timed out")
        json_dump(evidence / "history_response.json", history)
        entry = history.get(str(prompt_id), {})
        outputs = entry.get("outputs", {})
        image_info = next((item for node in outputs.values() for item in node.get("images", [])
                           if item.get("filename")), None)
        if not image_info:
            raise ProbeError("ComfyUI completed without a downloadable image output")
        query = urllib.parse.urlencode({k: image_info[k] for k in ("filename", "subfolder", "type") if k in image_info})
        _, output_bytes = request("GET", "/view?" + query, timeout=120)
        output_path = evidence / "output.png"
        output_path.write_bytes(output_bytes)
        output_meta = image_check(output_path)
        output_hash = sha256(output_path)
        input_hash = sha256(crop)
        (evidence / "output.sha256").write_text(output_hash + "  output.png\n", encoding="utf-8")
        passed = bool(output_bytes) and output_hash != input_hash
        report = {"status": "PASS" if passed else "FAIL", "prompt_id": prompt_id,
                  "input_crop_sha256": input_hash, "output_sha256": output_hash,
                  "byte_difference": output_hash != input_hash, "output": output_meta,
                  "input": input_meta["crop"],
                  "geometry": geometry_plan(input_meta["crop"]["width"], input_meta["crop"]["height"]),
                  "a2_authority": {"sha256": actual_a2_sha256, "expected_sha256": CANONICAL_A2_SHA256,
                                   "source": CANONICAL_A2_AUTHORITY},
                  "evidence": str(evidence), "mock_used": False, "fallback_used": False}
        if (output_meta["width"], output_meta["height"]) != (
            input_meta["crop"]["width"], input_meta["crop"]["height"]
        ):
            passed = False
            report["status"] = "FAIL"
            report["geometry_error"] = (
                f"output geometry {output_meta['width']}x{output_meta['height']} != "
                f"input geometry {input_meta['crop']['width']}x{input_meta['crop']['height']}"
            )
        json_dump(evidence / "verification_report.json", report)
        (evidence / "verification_report.txt").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0 if passed else 1
    except Exception as exc:
        logging.exception("GW-P3 failed")
        report = {"status": "FAIL", "error": str(exc), "evidence": str(evidence)}
        json_dump(evidence / "verification_report.json", report)
        (evidence / "verification_report.txt").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
