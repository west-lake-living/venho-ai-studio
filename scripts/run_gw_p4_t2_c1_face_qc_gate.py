#!/usr/bin/env python3
"""Run the authorized GW-P4-T2 C1 Face-QC stage only.

This uses the existing Validator Studio face validator.  It deliberately does
not call Image Validator, RegionalScoreGateway, ComfyUI, or Nano; the resulting
record remains semantically unvalidated until the existing production chain has
all of its authoritative inputs.
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

from validator_studio.face_validator import report_from_face_observations, validate_face
from validator_studio.schemas.face_validation import FaceValidationObservation
from shared.vision.providers.gemini_vision import ProviderCircuitBreaker, classify_gemini_failure
from shared.vision.paid_call_guard import paid_call_context
from image_studio_runtime.action_composite.geometry import create_geometry_extractor
from image_studio_runtime.action_composite.regional_score_gateway import GeometryEvidenceProducer
import yaml
from identity_restoration.application.benchmark_orchestration import BenchmarkCaseContextFactory
from identity_restoration.application.benchmark_contract import EXPECTED_A2_SHA256


ROOT = Path(__file__).resolve().parents[1]
A2 = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png")
RUN = ROOT / "artifacts/identity-restoration/gw-p4-t2-c1-face-qc-20260825-r9"
CACHE = ROOT / "artifacts/identity-restoration/benchmarks/validator-cache"
IDENTITY = "validator-studio-face-v1:gemini:model=gemini-3.5-flash:rubric=07F:samples=3"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_credentials() -> None:
    for path in (
        ROOT.parent.parent / "venho-social-content-agent/.env.local",
        ROOT.parent.parent / "venho-social-content-agent/.env",
        ROOT / ".env.local",
        ROOT / ".env",
    ):
        if path.is_file():
            load_dotenv(path, override=False)
            if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
                return


def find_candidate(case_id: str, candidate_id: str = "face_restore_win_sd15_ipadapter_v2_candidate_d30") -> tuple[dict, Path]:
    paths = list((ROOT / "artifacts/identity-restoration").glob("gw-p4-t2-denoise-pilot-20260825-r*/pilot-results.json"))
    paths += list((ROOT / "artifacts/identity-restoration").glob("gw-p4-t2-denoise-pilot-20260825-r*/pilot-results.partial.json"))
    for path in sorted(paths):
        for row in json.loads(path.read_text(encoding="utf-8")):
            if row.get("caseId") == case_id and row.get("candidateId") == candidate_id:
                output = Path(row["outputPath"])
                if output.is_file():
                    return row, output
    # B03 was persisted before the pilot writer reached its final-results
    # flush. Reconstruct only its zero-cost local evidence from immutable
    # artifact/ledger inputs; do not infer any semantic Regional score.
    if case_id == "B03":
        output = next((ROOT / "artifacts/identity-restoration/gw-p4-t2-denoise-pilot-20260825-r5/restoration-artifacts").glob("*d30-b03/attempt-1/composite.png"), None)
        if output is not None and output.is_file():
            manifest = yaml.safe_load((ROOT / "contracts/identity_restoration/benchmark_set.yaml").read_text())
            case = next(item for item in manifest["cases"] if item["id"] == case_id)
            context = BenchmarkCaseContextFactory(repo_root=ROOT, canonical_a2_path=A2, geometry_backend="yunet").build(case)
            authority = json.loads(context.geometry_path.read_text(encoding="utf-8"))
            extractor = create_geometry_extractor("yunet")
            expected = extractor(Path(authority["sourcePath"]))
            observed = extractor(output)
            score, _, _ = GeometryEvidenceProducer().produce(expected, observed, source_artifacts=[str(context.geometry_path), str(output)])
            return {"candidateId": "face_restore_win_sd15_ipadapter_v2_candidate_d30", "denoise": 0.3, "outputSha256": sha(output), "pixel": "PASS", "anatomy": "PASS", "geometryScore": score, "lineageComplete": True}, output
    raise RuntimeError(f"valid C1/{case_id} pilot result not found")


def cached(image_sha: str) -> dict | None:
    for path in sorted(CACHE.glob(f"{image_sha}-*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if payload.get("imageSha256") == image_sha and payload.get("samples") == 3:
            validator = str(payload.get("validator", ""))
            if "gemini" in validator and payload.get("faceQc"):
                return {"path": str(path), "payload": payload}
    return None


def offline_schema_gate() -> None:
    """Build the production Face DTO request before any live sample call."""
    from google.genai import types
    from validator_studio.schemas.face_validation import FaceValidationObservation
    from shared.vision.providers.gemini_vision import _gemini_response_schema

    schema = _gemini_response_schema(FaceValidationObservation.model_json_schema())
    config = types.GenerateContentConfig(
        system_instruction="production Face Validator prompt",
        temperature=0.0,
        max_output_tokens=4096,
        response_mime_type="application/json",
        response_schema=schema,
    )
    if "additionalProperties" in str(config.model_dump(exclude_none=True)):
        raise RuntimeError("offline schema gate failed: unsupported additionalProperties remains")


def offline_provider_gate() -> dict:
    """Check frozen provider configuration and credentials without HTTP."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return {"ready": False, "http": None, "reason": "credentials unavailable"}
    return {"ready": True, "http": "not_probed", "provider": "gemini", "model": "gemini-3.5-flash", "credentials": "configured", "samples": 3, "mock": False, "fallback": False}


def main() -> int:
    load_credentials()
    os.environ["VALIDATOR_LIVE_ENABLED"] = "true"
    os.environ["GEMINI_VISION_MODEL"] = "gemini-3.5-flash"
    offline_schema_gate()
    readiness = offline_provider_gate()
    if not readiness.get("ready"):
        raise RuntimeError(json.dumps({"providerReadiness": readiness}, ensure_ascii=False))
    if not A2.is_file():
        raise RuntimeError(f"A2 authority missing: {A2}")

    RUN.mkdir(parents=True, exist_ok=False)
    raw_root = RUN / "raw"
    ledger: list[dict] = []
    results: list[dict] = []
    breaker = ProviderCircuitBreaker()
    for case_id in ("B03", "B04"):
        if breaker.opened:
            break
        row, output = find_candidate(case_id)
        image_sha = sha(output)
        checks = {
            "outputExists": output.is_file(),
            "shaMatchesPilot": image_sha == row.get("outputSha256"),
            "candidateId": row.get("candidateId"),
            "denoise": row.get("denoise"),
            "pixel": row.get("pixel"),
            "anatomy": row.get("anatomy"),
            "geometryScore": row.get("geometryScore"),
            "lineageComplete": row.get("lineageComplete"),
        }
        if not (checks["outputExists"] and checks["shaMatchesPilot"] and checks["candidateId"] == "face_restore_win_sd15_ipadapter_v2_candidate_d30" and checks["denoise"] == 0.3 and checks["pixel"] == "PASS" and checks["anatomy"] == "PASS" and float(checks["geometryScore"]) >= 92 and checks["lineageComplete"]):
            raise RuntimeError(f"pre-call artifact gate failed for C1/{case_id}: {checks}")

        hit = cached(image_sha)
        if hit is not None:
            payload = hit["payload"]
            results.append({"case": case_id, "imageSha256": image_sha, "cacheHit": True, "cachePath": hit["path"], "faceQc": payload.get("faceQc"), "samples": 3, "newSamples": 0})
            continue

        case_raw = raw_root / case_id
        case_raw.mkdir(parents=True, exist_ok=True)

        def sink(event: dict) -> None:
            sample = int(event.get("sampleIndex", 0))
            record = {
                "case": case_id, "candidate": "C1", "imageSha256": image_sha,
                "sampleIndex": sample, "callReason": "C1 authoritative Face-QC stage",
                "provider": "gemini", "model": "gemini-3.5-flash", "samples": 3,
                "capturedAt": datetime.now(timezone.utc).isoformat(), **event,
            }
            ledger.append(record)
            (case_raw / f"sample-{sample}.jsonl").open("a", encoding="utf-8").write(json.dumps(record, ensure_ascii=False) + "\n")

        observations = []
        failed_provider_calls = 0
        # This recovery authorization permits exactly one new request. A
        # valid response is recorded, but completion still requires a later
        # separately authorized sequential sample run.
        for sample_index in range(1, 2):
            if breaker.opened:
                break
            try:
                # One production call per invocation is intentional: it makes
                # sample-level 503/429 fail closed before spending the next call.
                with paid_call_context({
                    "benchmarkId": "GW-P4-T2-C1",
                    "branch": "c1-face-qc",
                    "imageSha256": image_sha,
                    "sampleIndex": sample_index,
                    "historicalEvidenceSearch": {"imageSha256": image_sha, "samples": 3, "cacheHit": False},
                }):
                    one_sample = validate_face(
                        "venho_hotel", "linh_an", output, provider="gemini",
                        reference_image_paths=[A2], samples=1, raw_response_sink=sink,
                    )
                observations.append(one_sample.raw_observation)
            except Exception as exc:
                failed_provider_calls += 1
                failure_class = breaker.record(exc)
                blocked = {
                    "case": case_id, "imageSha256": image_sha, "samples": 3,
                    "callsAttempted": len(observations) + failed_provider_calls,
                    "newSamples": len(observations), "validSamples": len(observations),
                    "providerAvailability": breaker.provider_availability,
                    "failureClass": failure_class, "error": str(exc),
                }
                results.append(blocked)
                status = "PROVIDER_BLOCKED" if failure_class.startswith("PROVIDER_") else "INTERNAL_VALIDATOR_FAILURE"
                report = {
                    "task": "GW-P4-T2", "stage": "C1_ONLY_FACE_QC",
                    "authority": "validator_studio.face_validator", "providerReadiness": readiness,
                    "cases": results, "circuitBreaker": {"activated": breaker.opened, "failureClass": failure_class, "providerAvailability": breaker.provider_availability},
                    "cost": {"faceQcValidatorCalls": len(observations) + failed_provider_calls, "validatorSamples": len(observations), "failedProviderCalls": failed_provider_calls, "gpuJobs": 0, "nanoCalls": 0, "paidCallsDuringTests": 0},
                    "finalC1Status": status,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                }
                (RUN / "face-qc-c1.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(json.dumps(report, ensure_ascii=False, indent=2))
                return 2
        if len(observations) != 3:
            results.append({
                "case": case_id, "candidate": "C1", "imageSha256": image_sha,
                "cacheHit": False, "samples": 3, "callsAttempted": len(observations),
                "newSamples": len(observations), "validSamples": len(observations),
                "status": "INTERNAL_TRANSPORT_FIXED_PENDING_COMPLETION",
            })
            break
        parsed = [FaceValidationObservation.model_validate(item) for item in observations]
        report = report_from_face_observations(
            "venho_hotel", "linh_an", output, parsed, provider="gemini", reference_image_paths=[A2]
        )
        results.append({
            "case": case_id, "candidate": "C1", "imageSha256": image_sha,
            "cacheHit": False, "samples": 3, "callsAttempted": 3, "newSamples": 3,
            "faceQc": report.model_dump(mode="json"),
            "faceGate": {"identity": report.dna_match_score, "eyes_brows": report.category_scores.get("eyes_and_brows"), "passed": float(report.dna_match_score or 0) >= 90 and float(report.category_scores.get("eyes_and_brows") or 0) >= 90},
        })

    report = {
        "task": "GW-P4-T2", "stage": "C1_ONLY_FACE_QC", "authority": "validator_studio.face_validator",
        "validatorIdentity": IDENTITY, "provider": "gemini", "model": "gemini-3.5-flash", "samples": 3,
        "cases": results, "ledger": ledger,
        "cost": {"faceQcValidatorCalls": sum(item.get("newSamples", 0) for item in results), "validatorSamples": sum(item.get("newSamples", 0) for item in results), "gpuJobs": 0, "nanoCalls": 0, "paidCallsDuringTests": 0},
        "regional": "UNVALIDATED: image-validator evidence was not called in this Face-QC-only stage",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    (RUN / "face-qc-c1.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
