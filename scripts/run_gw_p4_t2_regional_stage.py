#!/usr/bin/env python3
"""Materialize C1 Regional evidence from complete Face-QC plus Image-QC."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.run_gw_p4_t2_c1_face_qc_gate import find_candidate, load_credentials, sha
from shared.vision.paid_call_guard import paid_call_context
from validator_studio.image_validator import validate_image
from identity_restoration.application.benchmark_orchestration import BenchmarkCaseContextFactory, BenchmarkRegionalEvidenceAdapter
from identity_restoration.application.benchmark_contract import EXPECTED_A2_SHA256

ROOT=Path(__file__).resolve().parents[1]
A2=Path('/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png')
CASE=os.environ['GW_P4_T2_CASE']; FACE_RUN=ROOT/'artifacts/identity-restoration'/os.environ['GW_P4_T2_FACE_RUN_ID']/'face-qc.json'
CANDIDATE=os.environ.get('GW_P4_T2_CANDIDATE','face_restore_win_sd15_ipadapter_v2_candidate_d30')
RUN_ID=os.environ['GW_P4_T2_REGIONAL_RUN_ID']; RUN=ROOT/'artifacts/identity-restoration'/RUN_ID
LEDGER=ROOT/'artifacts/identity-restoration/benchmarks'/f'{RUN_ID}-paid-call-ledger.jsonl'
def main()->int:
 load_credentials(); os.environ['VALIDATOR_LIVE_ENABLED']='true'; os.environ['GEMINI_VISION_MODEL']='gemini-3.5-flash'; os.environ['VALIDATOR_MAX_NEW_CALLS']='3'; os.environ['VALIDATOR_PAID_CALL_LEDGER']=str(LEDGER)
 if RUN.exists() or LEDGER.exists() or not FACE_RUN.is_file() or sha(A2)!=EXPECTED_A2_SHA256: raise RuntimeError('fresh-run/authority preflight failed')
 face=json.loads(FACE_RUN.read_text())
 if face.get('decision')!='FACE_QC_COMPLETE' or face.get('validSamples')!=3: raise RuntimeError('Face-QC is incomplete')
 row,image=find_candidate(CASE,CANDIDATE); RUN.mkdir(parents=True)
 try:
  with paid_call_context({'benchmarkId':'GW-P4-T2','branch':'C1','imageSha256':sha(image),'reason':'complete Image-QC required by C1 Regional gate'}): image_qc=validate_image('venho_hotel','linh_an',image,provider='gemini',samples=3)
  manifest=json.loads((ROOT/'contracts/identity_restoration/benchmark_set.yaml').read_text()) if False else None
  import yaml
  cases={x['id']:x for x in yaml.safe_load((ROOT/'contracts/identity_restoration/benchmark_set.yaml').read_text())['cases']}
  context=BenchmarkCaseContextFactory(repo_root=ROOT,canonical_a2_path=A2,geometry_backend='yunet').build(cases[CASE])
  q={'faceQc':face['faceQc'],'imageQc':image_qc.model_dump(mode='json')}
  regional=BenchmarkRegionalEvidenceAdapter(evidence_root=ROOT/'artifacts/identity-restoration/benchmarks/regional-evidence').materialize(run_id=RUN_ID,attempt_id=f'{CANDIDATE}-{CASE}-regional-1',benchmark_id='GW-P4-T2',branch=CANDIDATE,context=context,output_path=image,output_qc=q,pixel_preservation=row.get('pixel')=='PASS')
  result={'task':'GW-P4-T2','candidate':CANDIDATE,'case':CASE,'decision':'REGIONAL_COMPLETE','faceQc':face['faceQc'],'imageQc':image_qc.model_dump(mode='json'),'regional':regional}
 except Exception as e: result={'task':'GW-P4-T2','candidate':'C1','case':CASE,'decision':'PROVIDER_BLOCKED','error':str(e)}
 (RUN/'regional.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
