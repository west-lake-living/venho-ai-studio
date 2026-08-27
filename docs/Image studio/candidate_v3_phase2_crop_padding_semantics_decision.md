# Candidate v3 Phase 2 — Crop Padding Semantics Decision Pack

Status: **APPROVED**

This pack resolves the meaning of the already approved Candidate v3 crop
padding ratio `0.20`. It records repository evidence and presents bounded
human choices. It does not implement or approve an executable crop policy.

## Evidence boundary

Sources inspected:

- `docs/Image studio/CANDIDATE_V3_Nangcapcho_comfy_v2_1.md` §5.3 and Phase 2.
- `task_status.md` and `task_memory.md`.
- `identity_restoration/domain/entities.py` and
  `identity_restoration/domain/policies/geometry.py`.
- `identity_restoration/domain/compositing.py`.
- `image_studio_runtime/action_composite/masks.py` and existing crop/transform
  tests.

## Repository evidence classification

### Candidate v3 crop-padding convention: `ABSENT`

- The roadmap names `cropPaddingRatio: <calibrated-value>` and requires a
  calibrated crop, but it does not define whether the ratio is per-side or
  total, whether the crop is rectangular or square, or how its center is
  selected.
- The roadmap does define the processing stage order as padded canvas crop,
  then landmark similarity alignment, then the 512×512 canonical crop.
- The roadmap requires the true canvas bounds to be retained and reflected
  padding when expansion crosses image bounds; exact pixel-bound sampling and
  rounding semantics are not defined.
- The approved transform authority fixes the scalar ratio at `0.20`, but does
  not define its geometric interpretation. That scalar approval is
  `AUTHORITATIVE`; its crop convention remains `ABSENT`.
- `CropTransform` is an integer source-box value object with an exact box
  round-trip check. It does not define Candidate v3 floating-point padding.
- `crop_for_identity(..., scale=2.5)` in `image_studio_runtime` is an existing
  v2 crop helper. It is not Candidate v3 authority and must not be adopted as
  a meaning for `0.20`.

No formula, crop shape, out-of-bounds sampling rule, or rasterization rule is
approved by this pack.

## Shared processing boundary

The following are repository-backed constraints, not additional approvals:

- The approved ratio value is `0.20`.
- The canonical model canvas is `512×512`.
- The transform authority specifies image interpolation `LANCZOS4` and border
  mode `REFLECT_101`.
- The roadmap sequence is padded canvas crop → landmark similarity alignment →
  canonical model crop.
- A non-square source crop must not be resized by a simple rectangular stretch.

For all options below, the displayed crop bounds remain floating-point until a
deterministic rasterization rule is separately approved. The examples use a
face bbox `(x, y, w, h)` and `c = (x + w/2, y + h/2)`.

## CP-A — Bbox dimensions, 20% on each side

**Rule**

```text
pad_x = 0.20 * w
pad_y = 0.20 * h
left   = x - pad_x
top    = y - pad_y
right  = x + w + pad_x
bottom = y + h + pad_y
```

- **Center:** original bbox center `c = (x + w/2, y + h/2)`.
- **Shape:** rectangular; dimensions `1.40w × 1.40h`; source aspect ratio is
  retained.
- **Example:** bbox `100×150` becomes `140×210`, with 20% of the original
  width/height added on every corresponding side.
- **Out of bounds:** the roadmap-compatible interpretation is to retain the
  requested true canvas bounds, clamp the available source intersection, and
  fill the missing model-space samples with `REFLECT_101`; it does not shrink
  the requested geometry. Exact sampling/rasterization remains for approval.
- **Transform order:** crop first, then the roadmap's landmark similarity
  alignment to `512×512`; this follows the authoritative pipeline sequence.
- **Consequence:** adds symmetric per-axis context while allowing a non-square
  padded crop; a later similarity alignment must preserve geometry without
  rectangular stretch.

## CP-B — Square crop from the maximum bbox dimension, 20% on each side

**Rule**

```text
side = max(w, h)
padded_side = 1.40 * side
left   = c_x - padded_side / 2
top    = c_y - padded_side / 2
right  = c_x + padded_side / 2
bottom = c_y + padded_side / 2
```

- **Center:** original bbox center `c`.
- **Shape:** square; `1.40 × max(w,h)` on both axes.
- **Example:** bbox `100×150` becomes a `210×210` square centered on the
  original bbox center.
- **Out of bounds:** same unresolved roadmap-compatible choice as CP-A:
  retain true requested bounds, use the source intersection, and reflect
  missing model-space samples with `REFLECT_101`; exact rasterization needs
  human approval.
- **Transform order:** crop first, then landmark similarity alignment to
  `512×512`, matching the roadmap sequence.
- **Consequence:** supplies symmetric square context and simplifies square
  canonical sampling, but adds more context on the shorter bbox axis than
  CP-A and therefore changes the crop geometry materially.

## CP-C — Square crop with 20% total expansion

**Rule**

```text
side = max(w, h)
padded_side = 1.20 * side
left   = c_x - padded_side / 2
top    = c_y - padded_side / 2
right  = c_x + padded_side / 2
bottom = c_y + padded_side / 2
```

This is equivalent to `0.10 * side` on each side, not `0.20` on each side.

- **Center:** original bbox center `c`.
- **Shape:** square; `1.20 × max(w,h)` on both axes.
- **Example:** bbox `100×150` becomes a `180×180` square centered on the
  original bbox center.
- **Out of bounds:** same unresolved roadmap-compatible choice as CP-A:
  retain true requested bounds, use the source intersection, and reflect
  missing model-space samples with `REFLECT_101`; exact rasterization needs
  human approval.
- **Transform order:** crop first, then landmark similarity alignment to
  `512×512`, matching the roadmap sequence.
- **Consequence:** supplies less context than CP-B and is materially different
  from CP-A because it is square and interprets `0.20` as total expansion.

## Unresolved detail choices that apply to the selected CP option

### Out-of-bounds behavior

- `OOB-A — retain true bounds + reflect`: retain the requested crop box in
  canvas coordinates, preserve the in-bounds intersection, and obtain missing
  model-space samples using `REFLECT_101`. This is the interpretation most
  directly aligned with “retain true canvas bounds” and reflected model-space
  preprocessing, but its exact sampling/rasterization still needs approval.
- `OOB-B — clamp and shrink`: clamp the crop box to the source image and use
  the smaller resulting geometry. Consequence: the requested crop dimensions
  and transform geometry change at the border; this is materially different
  from OOB-A and is not established by repository evidence.

### Transform order

- `TO-A — crop-first`: construct the selected padded canvas crop, then estimate
  the five-point similarity alignment and produce the `512×512` model crop.
  Consequence: the crop box is an explicit canvas-space stage and matches the
  roadmap pipeline diagram.
- `TO-B — direct source-to-template`: estimate the source-to-template
  similarity directly and treat padding only as a sampling extent.
  Consequence: there is no separate padded-crop transform stage; this is not
  the order stated in the roadmap and requires explicit human authority if
  considered.

## Human decisions recorded

The human authority selected CP-B and supplied the following exact semantics:

```text
CROP_CONVENTION = CP-B
RATIO_REFERENCE = max(face_bbox_width, face_bbox_height)
PER_SIDE_OR_TOTAL = 20% PER SIDE
CROP_SHAPE = SQUARE
CROP_CENTER = FACE_BBOX_CENTER
OUT_OF_BOUNDS_BEHAVIOR = OOB-A
TRANSFORM_ORDER = TO-A
RASTERIZATION_RULE = floor(min) / ceil(max); preserve raster extent;
                     REFLECT_101 outside source bounds; share crop origin
                     and geometry across image, binary mask, feather mask,
                     and landmarks
```

The approved CP-B bounds are centered on the face bbox center with
`padded_side = 1.40 × max(face_bbox_width, face_bbox_height)`. Continuous
bounds are computed first; integer raster bounds use `floor(min)` and
`ceil(max)`. The requested crop is never clamped or shrunk. Missing pixels are
synthesized with `REFLECT_101`.

## Guardrails

- Do not register this decision pack as executable configuration.
- P2-T3 may proceed only using the recorded CP-B/OOB-A/TO-A semantics.
- Do not change the approved scalar value `0.20` in this pack.
- Do not use the existing v2 `scale=2.5` helper as Candidate v3 authority.
- Do not clamp away the true canvas geometry or use rectangular stretch without
  an explicit approved rule.
- Candidate v3 remains feature-gated `OFF`; v2/v2.1 remains untouched.
- GPU, provider, and network execution are out of scope.

## Human crop semantics approval

```text
CROP_CONVENTION = CP-B
CROP_PADDING_RATIO = 0.20
RATIO_REFERENCE = max(face_bbox_width, face_bbox_height)
PER_SIDE_OR_TOTAL = 20% PER SIDE
CROP_SHAPE = SQUARE
CROP_CENTER = FACE_BBOX_CENTER
OUT_OF_BOUNDS_BEHAVIOR = OOB-A: preserve requested crop bounds; synthesize
  missing pixels using REFLECT_101; do not clamp or shrink crop
TRANSFORM_ORDER = TO-A: crop-first; source image → padded square crop →
  canonical 512×512 alignment
RASTERIZATION_RULE = continuous float bounds; floor(min) / ceil(max); preserve
  raster extent; REFLECT_101 outside source; same crop origin and geometry for
  image, binary mask, feather mask, and landmarks

APPROVED_BY = Harry Pham
APPROVED_AT = 2026-08-27
STATUS = APPROVED
```
