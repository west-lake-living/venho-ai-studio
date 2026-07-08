# Troubleshooting — VENHO AI Studio

---

## Installation / Setup

### `venho: command not found`

The `venho` CLI is installed via pip. Make sure the Python user bin is in PATH:

```bash
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
```

Add this to `~/.zshrc` to make it permanent. Then reload:

```bash
source ~/.zshrc
venho --help
```

### `ModuleNotFoundError` when running venho

The package needs to be installed in editable mode:

```bash
cd /path/to/venho-ai-studio
pip install -e .
```

### `.env` not loaded / API key missing

Create `.env` in the repo root (copy from `.env.example`):

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY and ANTHROPIC_API_KEY
```

---

## Mode A / Mode B Errors

### `No images found in: <path>`

- The input folder is empty or contains no supported image formats.
- Supported extensions: `.jpg`, `.jpeg`, `.png`, `.webp`
- Check the path is correct: `ls <input_dir>`

### `No schema found for project='...' subject='...'`

Subject schema YAML does not exist. Check:

```bash
ls config/projects/<project>/subjects/
ls config/projects/_shared_subjects/
```

If the schema is missing, create it — see [`how_to_create_new_subject.md`](how_to_create_new_subject.md).

### `All images failed in Pass 1. Cannot build DNA.`

All images failed the vision API call. Common causes:

1. **API key invalid or expired** — check `.env` and your OpenAI/Anthropic dashboard
2. **Network error** — check internet connection
3. **Rate limit** — increase `retry.backoff_seconds` in `config/settings.yaml`
4. **Image format unsupported** — convert to JPEG or PNG

Test with mock provider to rule out image issues:

```bash
venho vision observe --mode b --project venho_hotel --subject room \
  --input data/media/rooms --provider mock
```

### DNA looks wrong / features missing

1. Check how many images are in the input folder (`ls | wc -l`). DNA needs multiple images.
2. Confirm **all images are the same subject** (§2.1 rule). Mixed content → features drift to VARIABLE.
3. Check the schema `aggregation_keys` — AI only reports keys that are declared.

---

## Cache

### Observations re-running despite no image change

Cache is keyed by `{image_hash}_{schema_id}_{schema_version}_{prompt_version}`.

If you changed `schema_version` or `prompt_version` in `settings.yaml`, the cache is invalidated by design.
To reuse cache, restore the previous version values.

### Cache files piling up

Cache files are in `data/projects/<project>/observations/`. They are safe to delete — the
pipeline will regenerate them (at API cost). To clear for one subject:

```bash
rm data/projects/venho_hotel/observations/*.json
```

---

## DNA Regeneration

### "No image changes detected" but I want to regenerate

The no-change check compares SHA-256 hashes of image files. If images haven't changed, no
regeneration is triggered. To force regeneration:

```bash
# Delete the manifest to force a fresh start
rm data/projects/venho_hotel/knowledge/dna_manifest_<subject>.json
```

Then re-run Mode B. The pipeline will regenerate from cached observations (no API calls if
cache is still valid).

### Old DNA not archived

Archive happens only when image hashes change **and** a manifest exists from a previous run.
If there is no manifest, the pipeline creates a fresh DNA without archiving (nothing to archive).

---

## Vault

### `Knowledge directory not found`

Run Mode B at least once to generate the first DNA file. The knowledge directory is created
automatically by Mode B.

### `No archived versions for subject`

`venho vault diff` needs at least one archived version to compare against. Archive versions are
created automatically when image hashes change. Run Mode B twice with different image sets to
create an archive.

### `vault export` returns an error about missing DNA

The COMPACT file is only created when `output.compact: true` in `config/settings.yaml`.
Check the setting and re-run Mode B:

```yaml
output:
  compact: true
```

---

## Face Subject / Linh An

### Linh An DNA shows unexpected VARIABLE for face shape

One or more source images have facial drift — face shape is not consistent across images.
This means images with scores < 9.0 may have entered the source folder.

**Fix:** Remove low-quality images from `data/projects/venho_hotel/media/linh_an/`, re-run Mode B.

### Face features classified as INVARIANT when they should be VARIABLE

This happens when all source images show the same expression or hair style.
The Pass 2A algorithm is deterministic — if 100% of images show the same value, it becomes INVARIANT.

**Fix:** Add more images with the desired variation (e.g., images with different hairstyles).

---

## Tests

### Running all tests

```bash
python3 -m pytest tests/ -v
```

### Running only mock tests (no API)

```bash
python3 -m pytest tests/test_mock.py tests/test_pass2a.py tests/test_mode_a_contract.py \
  tests/test_mode_b_contract.py tests/test_overlay_merge.py tests/test_cache.py \
  tests/test_regeneration_policy.py tests/test_subject_resolver.py tests/test_cli.py \
  tests/test_vault.py -v
```

All tests above run without any API calls.

### A test is failing after I changed schema

If you changed `aggregation_keys` in a subject YAML, existing tests that reference those keys
may need updating. Check `tests/test_subject_resolver.py` and `tests/test_phase5.py`.
