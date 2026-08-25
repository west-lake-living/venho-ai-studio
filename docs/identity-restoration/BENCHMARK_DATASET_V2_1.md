# GW-P4 Benchmark Dataset v2.1

Status: **COMPLETE — 10/10 source frames verified and frozen; official benchmark dataset ready**

Authoritative manifest: `contracts/identity_restoration/benchmark_set.yaml`.
This report records source discovery, verification, and the authorized
GW-P4-T0.4 generation lineage for B05–B08. No benchmark inference, live Face
QC sweep, or Face-QC-based selection was performed.

## Dataset inventory

| ID | Taxonomy | Status | File | SHA-256 | Size | Provenance |
|---|---|---|---|---|---|---|
| B01 | Close-up Front | FROZEN | `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/12-08-linh-an-a2-front-closeup-1k/run-202608121022/variant-001/image.png` | `e7b00d4a65b2cc97e274e3c00f96e091bda0e614778df5a2d43f17cc3793faf9` | 1024×1024 | Existing production identity artifact; manifest records an A2-front close-up portrait facing front. `run-202608121022` |
| B02 | Half-body | FROZEN | `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/10-08-linh-an-official-library/run-20260810-step5-business/variant-001/image.png` | `b3854325403c879693ab0f720aaf57a78da385ac6220acb59bd730b9d608d58f` | 1024×1280 | Existing production library artifact; manifest describes a three-quarter portrait. `run-20260810-step5-business` |
| B03 | Full-body Standing | FROZEN | `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/07-08-hoang-hon-ho-tay-tu-rooftop/run-20260807130340020/variant-001/image.png` | `098e6816fc21631fe4cd3bbd34b718f04569f8684f5347ab78525faf7ce07d87` | 1088×1920 | Existing production action artifact; manifest explicitly requires full body visible while standing on the Ven Ho Hotel rooftop. `run-20260807130340020` |
| B04 | Running Front 3/4 | FROZEN | `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/action-composite-live/action_01_jogging.png` | `bb031e7adfcc0c7d79544c3edb932eebafc1f797a59881415e57addc584d26a0` | 1024×1280 | Existing GW-P0 Golden-Master locked action-composite base; lineage `gw-p0-t2-20260819-local-rerun` |
| B05 | Running Side | FROZEN | `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/gw-p4-t0-4-b05-running-side/run-001/image.png` | `06f4b6b0b6ea47dee71a240065411899cb3fa2b84633dacddba4d232afce5492` | 1024×1280 | One accepted existing-pipeline generation; true lateral running pose and visible face; run `gw-p4-t0-4-b05-running-side/run-001`. |
| B06 | Walking | FROZEN | `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/gw-p4-t0-4-b06-walking/run-001/image.png` | `526190e3632d189d588dcdfda32f1d7930c449c8a6b2188961d7907ef7746d8e` | 1024×1280 | One accepted existing-pipeline generation; unambiguous walking gait and visible face; run `gw-p4-t0-4-b06-walking/run-001`. |
| B07 | Sitting | FROZEN | `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/gw-p4-t0-4-b07-sitting/run-001/image.png` | `6a39787e5edf0d061d246d9af806ac82d7499429a104fd3f910708dc5718754e` | 1024×1280 | One accepted existing-pipeline generation; seated posture, chair, and bent knees are clear; run `gw-p4-t0-4-b07-sitting/run-001`. |
| B08 | Hair Motion | FROZEN | `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/gw-p4-t0-4-b08-hair-motion/run-001/image.png` | `e6303bb45121b6dd01f992d549d76668cf34b6b82828ffed87f3a65928c970c4` | 1024×1280 | One accepted existing-pipeline generation; strong hair motion crosses the head/cheek boundary without obscuring the face; run `gw-p4-t0-4-b08-hair-motion/run-001`. |
| B09 | West Lake | FROZEN | `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/10-08-linh-an-official-library/run-20260810-step5-cafe/variant-001/image.png` | `9351a446dec761fa733f049212f8d1d4b205a774e47f2a1be1bbd1f2067af912` | 1024×1280 | Existing production library artifact; manifest explicitly describes Linh An inside a West Lake Hanoi café by lake-facing windows. `run-20260810-step5-cafe` |
| B10 | Ven Ho Hotel Interior | FROZEN | `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/smoke-20260811-171445/case-5/variant-001/image.png` | `32c701012e40040772c69bff102719c5d48c9c046bad442f68f1bc520c5bc507` | 848×1264 | Existing approved smoke-run artifact; manifest binds it to a Ven Ho Hotel lake-view room interior with Linh An present. `smoke-20260811-171445/case-5` |

## Selection and immutability policy

Candidates were assessed by taxonomy evidence and recoverable production
lineage, in this order: approved/frozen lineage, Golden-Master/reference
artifact, deterministic production/test artifact, then representative artifact
with recoverable provenance. Face QC scores were not used to choose, exclude,
or rank a source frame. Hard cases are not excluded because of expected QC
difficulty.

Every `FROZEN` source has a stable existing path, SHA-256, decoded dimensions,
and recorded provenance in the authoritative YAML manifest. The validator
rechecks file existence, PNG/JPEG decoding, hash, and dimensions locally. The
original source files were not moved, deleted, or rewritten.

Official readiness is now true for the dataset contract: B05–B08 each have one
real source artifact, decoded dimensions, SHA-256, and generation lineage. The
four new rows were accepted by taxonomy and technical review only; no Face QC
score was used to select or promote them. Full prompt/provider details are in
`BENCHMARK_GENERATION_LINEAGE_V2_1.md`.
