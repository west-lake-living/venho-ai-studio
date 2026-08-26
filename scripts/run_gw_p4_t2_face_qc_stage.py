#!/usr/bin/env python3
"""Execute one complete three-sample C1 Face-QC case using Validator Studio."""
from __future__ import annotations

import hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.run_gw_p4_t2_c1_face_qc_gate import find_candidate, load_credentials, sha
from shared.vision.paid_call_guard import paid_call_context
from validator_studio.face_validator import validate_face

ROOT = Path(__file__).resolve().parents[1]
A2 = Path("/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png")
CASE = os.environ.get("GW_P4_T2_CASE", "B03")
CANDIDATE = os.environ.get("GW_P4_T2_CANDIDATE", "face_restore_win_sd15_ipadapter_v2_candidate_d30")
RUN_ID = os.environ["GW_P4_T2_FACE_RUN_ID"]
RUN = ROOT / "artifacts/identity-restoration" / RUN_ID
LEDGER = ROOT / "artifacts/identity-restoration/benchmarks" / f"{RUN_ID}-paid-call-ledger.jsonl"

def main() -> int:
    load_credentials(); os.environ["VALIDATOR_LIVE_ENABLED"] = "true"; os.environ["GEMINI_VISION_MODEL"] = "gemini-3.5-flash"
    os.environ["VALIDATOR_MAX_NEW_CALLS"] = "3"; os.environ["VALIDATOR_PAID_CALL_LEDGER"] = str(LEDGER)
    if RUN.exists() or LEDGER.exists() or not A2.is_file(): raise RuntimeError("fresh run path or A2 authority check failed")
    row, image = find_candidate(CASE, CANDIDATE)
    if not image.is_file(): raise RuntimeError("candidate authority check failed")
    RUN.mkdir(parents=True); raw = RUN / "raw"; raw.mkdir()
    def sink(event: dict) -> None:
        index = int(event.get("sampleIndex", 0)); response = event.pop("rawResponse", None)
        if isinstance(response, str):
            path = raw / f"sample-{index}.raw.json"; path.write_text(response, encoding="utf-8")
            event.update({"rawResponsePath": str(path), "rawResponseSha256": hashlib.sha256(response.encode()).hexdigest()})
        event.update({"case": CASE, "sampleIndex": index, "capturedAt": datetime.now(timezone.utc).isoformat()})
        with (raw / f"sample-{index}.events.jsonl").open("a", encoding="utf-8") as f: f.write(json.dumps(event, ensure_ascii=False)+"\n")
    evidence = {"task":"GW-P4-T2","stage":"FACE_QC","case":CASE,"candidate":CANDIDATE,"samplesRequired":3,"thinkingConfig":{"thinking_budget":0,"include_thoughts":False}}
    try:
        with paid_call_context({"benchmarkId":"GW-P4-T2","branch":"C1","imageSha256":sha(image),"reason":"complete three-sample C1 Face-QC after transport recovery"}):
            report = validate_face("venho_hotel", "linh_an", image, provider="gemini", reference_image_paths=[A2], samples=3, raw_response_sink=sink)
        evidence.update({"decision":"FACE_QC_COMPLETE","validSamples":3,"faceQc":report.model_dump(mode="json")})
    except Exception as exc:
        evidence.update({"decision":"PROVIDER_BLOCKED","error":str(exc),"validSamples":0})
    (RUN/"face-qc.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(evidence,ensure_ascii=False,indent=2)); return 0
if __name__ == "__main__": raise SystemExit(main())
