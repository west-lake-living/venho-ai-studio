#!/usr/bin/env python3
"""Run the single, cost-gated GW-P4-T2C C1/B03 recovery request."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

from run_gw_p4_t2_c1_face_qc_gate import find_candidate, load_credentials, sha
from shared.vision.paid_call_guard import paid_call_context
from shared.vision.providers.gemini_vision import (
    GeminiVisionProvider,
    classify_gemini_failure,
    _gemini_response_schema,
)
from shared.vision.structured import StructuredResponseError, extract_json
from validator_studio.face_validator import (
    _build_face_observe_prompt,
    _load_face_rubric,
    validate_face,
)
from validator_studio.schemas.face_validation import FaceValidationObservation
from validator_studio.utils import find_dna_path, load_json
from identity_restoration.application.benchmark_contract import EXPECTED_A2_SHA256


ROOT = Path(__file__).resolve().parents[1]
A2 = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png")
IMAGE_SHA = "b395fc209939a0b5054092a4fdd9979afbfebf16d59b040a291c7aa07bd98a62"
EXPECTED_MODEL = "gemini-3.5-flash"
ARTIFACT = ROOT / "artifacts/identity-restoration/benchmarks/gw-p4-t2c-output-cap-8192-recovery.json"
RUN = ROOT / "artifacts/identity-restoration/gw-p4-t2-c1-face-qc-20260825-r10"
LEDGER = ROOT / "artifacts/identity-restoration/benchmarks/gw-p4-t2c-paid-call-ledger.jsonl"


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_prior_4096_config() -> dict[str, Any]:
    ledger = ROOT / "artifacts/identity-restoration/benchmarks/validator-paid-call-ledger.jsonl"
    records = []
    if ledger.is_file():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if (
                item.get("event") == "intent"
                and item.get("imageSha256") == IMAGE_SHA
                and item.get("sampleIndex") == 1
                and item.get("validatorConfig", {}).get("max_output_tokens") == 4096
            ):
                records.append(item["validatorConfig"])
    if not records:
        raise RuntimeError("frozen 4096 C1/B03 request config is unavailable")
    return records[-1]


def preflight() -> dict[str, Any]:
    if not A2.is_file():
        raise RuntimeError(f"A2 authority missing: {A2}")
    if sha(A2) != EXPECTED_A2_SHA256:
        raise RuntimeError("A2 authority hash mismatch")

    row, output = find_candidate("B03")
    output_sha = sha(output)
    if output_sha != IMAGE_SHA or row.get("outputSha256") != IMAGE_SHA:
        raise RuntimeError("C1/B03 artifact hash mismatch")
    if row.get("candidateId") != "face_restore_win_sd15_ipadapter_v2_candidate_d30" or row.get("denoise") != 0.3:
        raise RuntimeError("C1/B03 candidate identity/denoise mismatch")

    rubric = _load_face_rubric("venho_hotel")
    dna = load_json(find_dna_path("venho_hotel", "linh_an"))
    prompt = _build_face_observe_prompt(dna, rubric, reference_image_paths=[A2])
    raw_schema = FaceValidationObservation.model_json_schema()
    schema = _gemini_response_schema(raw_schema)
    provider = object.__new__(GeminiVisionProvider)
    provider.temperature = 0.0
    config = provider._generate_config(prompt, schema)
    prior = load_prior_4096_config()

    if config["max_output_tokens"] != 8192:
        raise RuntimeError("8192 cap is not active")
    if set(config) != set(prior):
        raise RuntimeError("request config keys changed beyond max_output_tokens")
    for key in config:
        if key != "max_output_tokens" and stable_hash(config[key]) != stable_hash(prior[key]):
            raise RuntimeError(f"request semantic drift detected in {key}")

    return {
        "passed": True,
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "provider": "gemini",
        "model": EXPECTED_MODEL,
        "samples": 3,
        "mock": False,
        "fallback": False,
        "temperature": 0.0,
        "thinkingLevel": "UNCHANGED / NOT EXPOSED BY SDK CONFIG",
        "rubricVersion": rubric.get("version"),
        "rubricHash": stable_hash(rubric),
        "schemaHash": stable_hash(schema),
        "artifactHash": output_sha,
        "a2AuthorityHash": sha(A2),
        "requestDiff": {"max_output_tokens": {"before": 4096, "after": 8192}},
        "artifactPath": str(output),
        "artifactCandidate": row,
        "historicalConfigComparison": "IDENTICAL_EXCEPT_MAX_OUTPUT_TOKENS",
    }


def ledger_records() -> list[dict[str, Any]]:
    if not LEDGER.is_file():
        return []
    records = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if isinstance(item, dict):
            records.append(item)
    return records


def main() -> int:
    load_credentials()
    os.environ["VALIDATOR_LIVE_ENABLED"] = "true"
    os.environ["GEMINI_VISION_MODEL"] = EXPECTED_MODEL
    os.environ["VALIDATOR_MAX_NEW_CALLS"] = "1"
    os.environ["VALIDATOR_PAID_CALL_LEDGER"] = str(LEDGER)

    preflight_data = preflight()
    if RUN.exists() or ARTIFACT.exists() or LEDGER.exists():
        raise RuntimeError("T2C evidence path already exists; refusing duplicate live call")
    RUN.mkdir(parents=True)
    raw_dir = RUN / "raw/B03"
    raw_dir.mkdir(parents=True)
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)

    evidence: dict[str, Any] = {
        "schema_version": "1.0",
        "task": "GW-P4-T2C",
        "roadmap_state_before": {
            "GW-P4-T2": "PROVIDER_BLOCKED",
            "GW-P4": "IN PROGRESS / QUALITY GATE FAILED",
            "GW-P5": "NOT STARTED",
        },
        "transport_change": {"before": 4096, "after": 8192},
        "locked_config": preflight_data,
        "offline_preflight": preflight_data,
        "live_call_count": 0,
        "provider_result": {},
        "parser_result": {},
        "valid_sample_count": 0,
        "decision": "RECOVERY_IN_PROGRESS",
        "roadmap_state_after": {},
        "next_allowed_action": "",
    }
    ARTIFACT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def sink(event: dict[str, Any]) -> None:
        raw = event.get("rawResponse")
        if isinstance(raw, str):
            (raw_dir / "sample-1.raw.json").write_text(raw, encoding="utf-8")
            event = {**event, "rawResponseBytes": len(raw.encode("utf-8")), "rawResponseSha256": hashlib.sha256(raw.encode("utf-8")).hexdigest()}
        record = {"case": "B03", "candidate": "C1", "imageSha256": IMAGE_SHA, "capturedAt": datetime.now(timezone.utc).isoformat(), **event}
        with (raw_dir / "sample-1.events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    try:
        with paid_call_context({
            "benchmarkId": "GW-P4-T2C",
            "branch": "c1-face-qc-output-cap-8192",
            "imageSha256": IMAGE_SHA,
            "sampleIndex": 1,
            "historicalEvidenceSearch": {"imageSha256": IMAGE_SHA, "samples": 3, "cacheHit": False},
        }):
            validate_face(
                "venho_hotel", "linh_an", Path(preflight_data["artifactPath"]), provider="gemini",
                reference_image_paths=[A2], samples=1, raw_response_sink=sink,
            )
    except Exception as exc:
        records = ledger_records()
        intents = [item for item in records if item.get("event") == "intent"]
        results = [item for item in records if item.get("event") == "result"]
        latest = results[-1] if results else {}
        raw_path = raw_dir / "sample-1.raw.json"
        raw = raw_path.read_text(encoding="utf-8") if raw_path.is_file() else ""
        parser_error = str(exc)
        parser_class = classify_gemini_failure(exc)
        if raw:
            try:
                extract_json(raw)
            except StructuredResponseError as parse_exc:
                parser_error = str(parse_exc)
                parser_class = classify_gemini_failure(parse_exc)
        raw_bytes = len(raw.encode("utf-8"))
        raw_sha = hashlib.sha256(raw.encode("utf-8")).hexdigest() if raw else None
        finish_reason = latest.get("finishReason")
        is_max_tokens = "MAX_TOKENS" in str(finish_reason).upper()
        if is_max_tokens:
            parser_class = "PROVIDER_TRUNCATED_RESPONSE"
        evidence.update({
            "live_call_count": len(intents),
            "provider_result": {
                "provider": "gemini", "model": EXPECTED_MODEL, "finishReason": finish_reason,
                "finishMessage": None, "promptTokenCount": latest.get("inputTokens"),
                "candidatesTokenCount": latest.get("outputTokens"), "cachedContentTokenCount": latest.get("cachedTokens"),
                "thoughtsTokenCount": None, "totalTokenCount": None,
                "responsePartsMetadata": None, "rawBytes": raw_bytes, "rawSha256": raw_sha,
                "requestCount": len(intents),
            },
            "parser_result": {
                "status": "INVALID", "error": parser_error, "failureClass": parser_class,
                "inputBytes": raw_bytes, "errorPosition": raw_bytes if raw else None,
                "rawTail": raw[-160:] if raw else None,
            },
            "valid_sample_count": 0,
            "decision": "PROVIDER_TRUNCATED_RESPONSE" if is_max_tokens else parser_class,
            "roadmap_state_after": {
                "GW-P4-T2": "PROVIDER_BLOCKED" if is_max_tokens else "PROVIDER_BLOCKED",
                "GW-P4": "IN PROGRESS / QUALITY GATE FAILED",
                "GW-P5": "NOT STARTED",
            },
            "next_allowed_action": "STOP GW roadmap execution at GW-P4 provider blocker." if is_max_tokens else "STOP; preserve exact provider/schema failure.",
            "scope_guard": {"B04": "NOT CALLED", "C2": "UNTOUCHED", "C3": "UNTOUCHED", "gpuJobs": 0, "nanoCalls": 0},
        })
        ARTIFACT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(evidence, ensure_ascii=False, indent=2))
        return 0

    raise RuntimeError("unexpected valid response path; no downstream action is authorized")


if __name__ == "__main__":
    raise SystemExit(main())
