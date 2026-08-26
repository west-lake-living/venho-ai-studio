#!/usr/bin/env python3
"""One C1/B03 Face-QC transport probe with Gemini thinking disabled.

The prior T2 attempts are immutable.  This creates a new evidence directory
and permits one live request only; it does not infer a quality result from a
transport result and it does not touch B04, C2, C3, GPU, or Nano.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

from scripts.run_gw_p4_t2_c1_face_qc_gate import find_candidate, load_credentials, sha
from shared.vision.paid_call_guard import paid_call_context
from shared.vision.providers.gemini_vision import GeminiVisionProvider, classify_gemini_failure
from shared.vision.structured import extract_json
from validator_studio.face_validator import validate_face
from validator_studio.schemas.face_validation import FaceValidationObservation


ROOT = Path(__file__).resolve().parents[1]
A2 = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png")
RUN_ID = os.environ.get("GW_P4_T2E_RUN_ID", "gw-p4-t2e-c1-thinking-disabled-20260825-r11")
RUN = ROOT / "artifacts/identity-restoration" / RUN_ID
LEDGER = ROOT / "artifacts/identity-restoration/benchmarks" / f"{RUN_ID}-paid-call-ledger.jsonl"
EVIDENCE = ROOT / "artifacts/identity-restoration/benchmarks" / f"{RUN_ID}-probe.json"
MODEL = "gemini-3.5-flash"


def config_preflight() -> dict:
    provider = object.__new__(GeminiVisionProvider)
    provider.temperature = 0.0
    config = provider._generate_config("production Face Validator prompt", FaceValidationObservation.model_json_schema())
    if config.get("thinking_config") != {"thinking_budget": 0, "include_thoughts": False}:
        raise RuntimeError("thinking-disabled transport profile is not active")
    from google.genai import types
    serialized = types.GenerateContentConfig(**config).model_dump(exclude_none=True)
    if serialized.get("thinking_config", {}).get("thinking_budget") != 0:
        raise RuntimeError("SDK did not serialize thinking_budget=0")
    return {"maxOutputTokens": config["max_output_tokens"], "thinkingConfig": config["thinking_config"], "schema": "UNCHANGED"}


def main() -> int:
    load_credentials()
    os.environ["VALIDATOR_LIVE_ENABLED"] = "true"
    os.environ["GEMINI_VISION_MODEL"] = MODEL
    os.environ["VALIDATOR_MAX_NEW_CALLS"] = "1"
    os.environ["VALIDATOR_PAID_CALL_LEDGER"] = str(LEDGER)
    if RUN.exists() or LEDGER.exists() or EVIDENCE.exists():
        raise RuntimeError("T2E evidence path already exists; refusing duplicate live call")
    if not A2.is_file():
        raise RuntimeError("A2 authority is missing")
    row, image = find_candidate("B03")
    if row.get("denoise") != 0.3 or not image.is_file():
        raise RuntimeError("C1/B03 authority preflight failed")

    RUN.mkdir(parents=True)
    raw_dir = RUN / "raw/B03"
    raw_dir.mkdir(parents=True)
    preflight = config_preflight()
    raw_events: list[dict] = []

    def sink(event: dict) -> None:
        raw = event.get("rawResponse")
        if isinstance(raw, str):
            raw_path = raw_dir / "sample-1.raw.json"
            raw_path.write_text(raw, encoding="utf-8")
            event = {**event, "rawResponseBytes": len(raw.encode()), "rawResponseSha256": hashlib.sha256(raw.encode()).hexdigest()}
            event.pop("rawResponse", None)
        raw_events.append(event)
        with (raw_dir / "sample-1.events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    evidence = {"schema_version": "1.0", "task": "GW-P4-T2E", "candidate": "C1", "case": "B03", "preflight": preflight, "decision": "PROBE_IN_PROGRESS"}
    try:
        with paid_call_context({"benchmarkId": "GW-P4-T2E", "branch": "c1-thinking-disabled-probe", "imageSha256": sha(image), "sampleIndex": 1}):
            report = validate_face("venho_hotel", "linh_an", image, provider="gemini", reference_image_paths=[A2], samples=1, raw_response_sink=sink)
        evidence.update({"decision": "TRANSPORT_RECOVERED_PENDING_3_SAMPLE_FACE_QC", "validSamples": 1, "faceQc": report.model_dump(mode="json"), "scopeGuard": {"B04": "NOT_CALLED", "C2": "UNTOUCHED", "C3": "UNTOUCHED", "gpuJobs": 0, "nanoCalls": 0}})
    except Exception as exc:
        raw_path = raw_dir / "sample-1.raw.json"
        raw = raw_path.read_text(encoding="utf-8") if raw_path.is_file() else ""
        try:
            extract_json(raw)
            parser = "PARSED_UNEXPECTEDLY"
        except Exception as parse_exc:
            parser = str(parse_exc)
        evidence.update({"decision": "PROVIDER_BLOCKED", "validSamples": 0, "failureClass": classify_gemini_failure(exc), "error": str(exc), "parser": parser, "rawBytes": len(raw.encode()), "rawSha256": hashlib.sha256(raw.encode()).hexdigest() if raw else None, "scopeGuard": {"B04": "NOT_CALLED", "C2": "UNTOUCHED", "C3": "UNTOUCHED", "gpuJobs": 0, "nanoCalls": 0}})
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
