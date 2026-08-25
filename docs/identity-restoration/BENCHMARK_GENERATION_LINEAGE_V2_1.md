# GW-P4-T0.4 Benchmark Source Generation Lineage

This record covers only the four previously missing source frames B05–B08.
Each frame was generated exactly once through the existing
`venho-social-content-agent/generate_image.py` pipeline and then reviewed for
taxonomy and catastrophic technical defects. No IdentityRestorer, benchmark
branch, Face QC call, or candidate ranking was run.

## Common generation authority

- Provider: OpenAI API through the existing social-content-agent pipeline.
- Model: `gpt-image-2`.
- Operation: image edit with one face reference.
- Quality: `high`.
- Output size: `1024x1280`.
- Input/reference: `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png`.
- A2 SHA-256: `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`.
- Deterministic seed: unavailable from this provider/pipeline; `seedSupported=false`.
- Benchmark seed `42` is recorded as the later comparison seed and was not
  claimed as the source-generation seed.
- Provider request IDs were not exposed by the existing script and are
  recorded as unavailable; no ID is fabricated.
- The generated output path is used directly as the frozen base path. No
  source image was copied, moved, rewritten, or passed through restoration.

## B05 — Running Side

- Artifact/run ID: `gw-p4-t0-4-b05-running-side/run-001`.
- Output: `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/gw-p4-t0-4-b05-running-side/run-001/image.png`.
- SHA-256: `06f4b6b0b6ea47dee71a240065411899cb3fa2b84633dacddba4d232afce5492`.
- Dimensions: `1024x1280`.
- Artifact mtime recorded after generation: `2026-08-24T18:06:07+0700`.
- Attempt: `1` of `2`; no replacement was required.
- Acceptance rationale: true lateral side-running pose, visible face, mint-
  green athletic outfit, and no observed catastrophic anatomy defect.
- Prompt:

  > Use case: photorealistic-natural. Asset type: authoritative GW-P4 benchmark input frame B05 Running Side. Create exactly one photorealistic editorial image of Linh An, a Vietnamese woman, running laterally from left to right along the real Nguyen Dinh Thi lakeside street beside West Lake in Hanoi. Show a true lateral side-running pose, clearly distinguishable from a front-facing pose, with her face and facial features sufficiently visible for later restoration and QC; use a natural side/three-quarter-side head orientation, not a hidden face. Show enough of her body and running stride to establish the taxonomy. She wears a consistent mint-green Nike athletic running outfit, white running shoes, and a practical tied-back hairstyle. Preserve natural anatomy, realistic hands and feet, coherent limbs, natural daylight, real local lakeside context, no text, no watermark, no extra people, no duplicated limbs, no distorted face. Do not make this an identity-restoration edit; this is the untouched benchmark source frame.

## B06 — Walking

- Artifact/run ID: `gw-p4-t0-4-b06-walking/run-001`.
- Output: `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/gw-p4-t0-4-b06-walking/run-001/image.png`.
- SHA-256: `526190e3632d189d588dcdfda32f1d7930c449c8a6b2188961d7907ef7746d8e`.
- Dimensions: `1024x1280`.
- Artifact mtime recorded after generation: `2026-08-24T18:08:25+0700`.
- Attempt: `1` of `2`; no replacement was required.
- Acceptance rationale: unambiguous walking gait with one foot stepping,
  relaxed arms and shoulders, visible face, and no observed catastrophic
  anatomy defect.
- Prompt:

  > Use case: photorealistic-natural. Asset type: authoritative GW-P4 benchmark input frame B06 Walking. Create exactly one photorealistic editorial image of Linh An, a Vietnamese woman, walking naturally at an easy pace along the real Nguyen Dinh Thi lakeside street beside West Lake in Hanoi. The pose must clearly read as walking, not running: one foot naturally stepping, relaxed arms and shoulders, balanced gait, no airborne stride. Keep her face sufficiently visible for later restoration and QC, with a natural front three-quarter orientation. Show enough body and surrounding context to establish walking. She wears a consistent mint-green Nike athletic outfit and white walking/running shoes, with natural tied-back hair. Preserve natural anatomy, realistic hands and feet, coherent limbs, natural daylight, real local lakeside context, no text, no watermark, no extra people, no duplicated limbs, no distorted face. Do not make this an identity-restoration edit; this is the untouched benchmark source frame.

## B07 — Sitting

- Artifact/run ID: `gw-p4-t0-4-b07-sitting/run-001`.
- Output: `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/gw-p4-t0-4-b07-sitting/run-001/image.png`.
- SHA-256: `6a39787e5edf0d061d246d9af806ac82d7499429a104fd3f910708dc5718754e`.
- Dimensions: `1024x1280`.
- Artifact mtime recorded after generation: `2026-08-24T18:10:37+0700`.
- Attempt: `1` of `2`; no replacement was required.
- Acceptance rationale: clearly seated on a wooden chair with bent knees and
  lake-facing cafe context; no observed catastrophic anatomy defect.
- Prompt:

  > Use case: photorealistic-natural. Asset type: authoritative GW-P4 benchmark input frame B07 Sitting. Create exactly one photorealistic editorial image of Linh An, a Vietnamese woman, clearly seated naturally on a wooden chair at a West Lake Hanoi cafe by a lake-facing window. Her seated posture and bent knees must be unmistakable; show enough body and chair/table context to establish sitting, with face sufficiently visible in a natural front three-quarter orientation for later restoration and QC. Natural anatomy, realistic hands and feet, no impossible joints, mint-green Nike athletic outfit, daylight, no text, no watermark, no extra people, no duplicated limbs, no distorted face. Do not make this an identity-restoration edit; this is the untouched benchmark source frame.

## B08 — Hair Motion

- Artifact/run ID: `gw-p4-t0-4-b08-hair-motion/run-001`.
- Output: `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/photos-ai/2026/gw-p4-t0-4-b08-hair-motion/run-001/image.png`.
- SHA-256: `e6303bb45121b6dd01f992d549d76668cf34b6b82828ffed87f3a65928c970c4`.
- Dimensions: `1024x1280`.
- Artifact mtime recorded after generation: `2026-08-24T18:12:50+0700`.
- Attempt: `1` of `2`; no replacement was required.
- Acceptance rationale: strong wind visibly sweeps hair across the head and
  near one cheek while the face remains readable; calm lakeside composition,
  not another running frame.
- Prompt:

  > Use case: photorealistic-natural. Asset type: authoritative GW-P4 benchmark input frame B08 Hair Motion. Create exactly one photorealistic editorial image of Linh An, a Vietnamese woman, standing or moving slowly beside West Lake in a strong natural breeze. The primary taxonomy is meaningful hair motion: long dark hair must visibly sweep and lift across the head and near one cheek, interacting with the face and hairline boundary while leaving enough of the face visible for later restoration and QC. This must not be another running frame; use a calm standing or slow-walking composition with hair movement as the subject of the stress case. Natural anatomy, realistic hands and feet, coherent hair strands, mint-green athletic outfit, daylight, no text, no watermark, no extra people, no duplicated limbs, no distorted face. Do not make this an identity-restoration edit; this is the untouched benchmark source frame.

## Freeze decision

All four rows have one accepted attempt, real local output bytes, decoded
`1024x1280` dimensions, and independently verified SHA-256 values. Acceptance
was based on requested taxonomy and technical validity only. This document is
lineage evidence, not a Face QC result and not an official benchmark result.
