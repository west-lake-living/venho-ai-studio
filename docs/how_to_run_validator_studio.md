# Validator Studio — Module 03

Validator Studio scores AI outputs against Module 01 DNA and Module 02 prompt contracts.
It does not generate DNA, rewrite prompts, or edit outputs.

Core rule: AI observes enum/boolean evidence; Python code computes scores and kill-switches.

## Commands

Image artifact:

```bash
venho validate image \
  --project venho_hotel \
  --subject lake_view_room \
  --image path/to/generated.png \
  --prompt data/projects/venho_hotel/prompts/image/LAKE_VIEW_ROOM__booking-style__IMAGE_PROMPT_v1.0.json
```

Prompt JSON by path:

```bash
venho validate prompt \
  --project venho_hotel \
  --subject lake_view_room \
  --prompt-file data/projects/venho_hotel/prompts/image/LAKE_VIEW_ROOM__booking-style__IMAGE_PROMPT_v1.0.json
```

Latest prompt from Module 02 manifest:

```bash
venho validate prompt \
  --project venho_hotel \
  --subject lake_view_room \
  --latest \
  --type image \
  --brief-slug booking-style
```

Face / fictional character image:

```bash
venho validate face \
  --project venho_hotel \
  --subject linh_an \
  --image path/to/generated-character.png
```

Content draft:

```bash
venho validate content \
  --project venho_hotel \
  --subject westlake \
  --draft-file path/to/draft.md \
  --lang vi \
  --platform facebook
```

## Outputs

Reports are written to:

```text
data/projects/<project>/validation/reports/
data/projects/<project>/validation/validation_manifest.json
```

Each run writes both `.md` and `.json` reports.

## Validation Types

### Image

Input: generated image + DNA JSON + optional Module 02 prompt JSON.

Layer 1 observe returns:

- `match_state`: `match`, `partial`, `mismatch`, `not_visible`
- forbidden `violated`: true/false
- allowed imperfection `present`: true/false

Layer 2 scoring is deterministic:

- match = 100
- partial = 60
- mismatch = 0
- not_visible is excluded from the sample

High-severity forbidden violation triggers kill-switch cap and reject/regenerate.

### Prompt

Input: Module 02 prompt JSON.

This is advisory only. Module 02 remains the structural/faithfulness pass-fail gate.
Module 03 scores quality categories such as DNA coverage, clarity, token efficiency,
specificity, and production readiness.

Module 02 can call Module 03 directly with:

```python
from validator_studio.module02_integration import score_module02_prompt_contract

result = run_image_pipeline(
    dna,
    "Booking-style image.",
    "booking-style",
    optimize_fn=optimize_mock,
    advisory_fn=score_module02_prompt_contract,
)
```

The advisory hook must never become a build gate. If scoring fails, Module 02 continues and
records a note.

### Face

Input: fictional character image + Face DNA + 07F rubric.

Grounding/web search are off by contract. The validator must not identify real people or
celebrities. It only compares the artifact against the fictional character DNA.

Binary gate failure overrides weighted score:

- any failed 07F gate -> kill-switch triggered
- overall score = 0
- verdict = reject

### Content

Input: draft text + DNA JSON + `config/projects/<project>/prompt_rules.yaml`.

Scores:

- brand_fit
- tone
- clarity
- cta
- language_fit
- production_readiness

Vietnamese content is valid when `target_language=vi`; it is not penalized for being
Vietnamese.

## Providers

Default provider is `mock`, which makes no network/API calls and is used in tests.

Image and Face validators also have provider code paths that build schema-guarded prompts
for real vision providers. Tests verify these paths with fake clients, not real API calls.

## Testing

Run:

```bash
python3 -m pytest
```

Do not write tests that call real API providers. Prompt Studio pipeline tests must pass
`optimize_fn=optimize_mock` or a fake optimizer.

