# How to Run Mode A — Image Observation

Mode A converts any image into a structured `.md` + `.json` observation file.
AI can read the `.md` to understand the image without seeing the original.

## Quick Start

```bash
venho vision observe --mode a --input data/projects/_inbox/media
```

Output goes to `data/projects/_inbox/output/` by default.

## With Custom Output Directory

```bash
venho vision observe --mode a --input /path/to/images --output /path/to/output
```

## Interactive

```bash
venho vision
# → choose A → enter paths
```

## Output Files

Each image produces two files:
- `<image_stem>_<hash8>.md` — human-readable observation with sections:
  SUBJECT / SCENE / COMPOSITION / LIGHTING / PALETTE / MATERIALS / AI-USABLE NOTES / UNCERTAINTY
- `<image_stem>_<hash8>.json` — machine-readable observation JSON with `contract_version`

## Mock Mode (no API cost)

```bash
venho vision observe --mode a --input data/media/rooms --provider mock
```

## Cache

Observations are cached by `sha256(image) + schema_version + prompt_version`.
Running the same images twice costs zero API tokens.
