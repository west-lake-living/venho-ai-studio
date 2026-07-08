# How to Use Curated Overlays (v2.4 §5.2)

Overlays are human-written YAML files that inject curator knowledge into machine-generated DNA
**at render time** — without touching the DNA generation pipeline.

The overlay survives every DNA regeneration unchanged. It is the mechanism for keeping
human editorial authority over AI output.

---

## File location (§6 — only one location)

```
config/projects/<project>/subjects/<subject>.overrides.yaml
```

Example: `config/projects/venho_hotel/subjects/lake_view_room.overrides.yaml`

There is no shared overlay location. Each subject has its own overlay file.

---

## Overlay format

```yaml
# Overlay for: venho_hotel / lake_view_room

forbidden:
  - no carpet flooring
  - no wallpaper
  - no dark curtains blocking lake view
  - no generic hotel art prints

wording_overrides:
  floor: "dark hardwood floor with subtle grain"
  window_type: "floor-to-ceiling glass panels facing west lake"

allowed_imperfections:
  - slight wooden floor scratches near bed legs
  - minor wall scuffs near door frame
  - visible cable management at TV stand

notes:
  - This room tier faces West Lake directly — lake view is a defining feature
  - Natural light is the dominant light source in daylight shots
```

---

## Merge rules

### `forbidden` (curated first)

Curated forbidden rules are prepended to observed forbidden hints.
Each rule is tagged with its source in the DNA output:

```
- no carpet flooring  [curated]
- indeterminate surface material observed  [observed]
```

If a curated rule overlaps an observed rule (case-insensitive), the observed version is removed —
the curated version takes precedence.

**Curated forbidden rules are policy.** Use them to enforce brand standards that AI observation
may miss (e.g., "no synthetic materials") or to prevent hallucination of specific elements
(e.g., "no bathtub" for rooms that only have a shower).

### `wording_overrides` (replace existing invariant value)

Replace the machine-generated wording for a specific invariant key with canonical brand language.
Only applies if the key already exists in the machine DNA as INVARIANT.

The replaced value is tagged `[curated]` in the output.

### `allowed_imperfections` (curated first)

Curated entries are prepended to AI-observed imperfections.
Duplicates (case-insensitive) are removed from observed list.

### `notes` → `CURATOR NOTES` section

List of editorial notes from the human curator.
These appear verbatim in the `## CURATOR NOTES` section of the DNA Markdown.
Notes are replaced fresh every re-render — they do not accumulate.

---

## What overlays must NOT do

- ❌ Create fake evidence (e.g., inventing invariant keys that don't exist in machine DNA)
- ❌ Change `invariant`/`variable` classification of any feature
- ❌ Change `evidence_count`, `coverage`, `consistency`
- ❌ Add a new invariant key that was never observed (unless it's `curated_only` and clearly marked)

The overlay purpose is to refine wording, add policy rules, and annotate imperfections.
It is not a substitute for actual image observation.

---

## Re-rendering with overlay changes

When you edit the overlay, you do **not** need to re-run vision API calls.
Re-render by running Mode B normally — the pipeline detects no image change and re-renders only:

```bash
venho vision observe --mode b \
  --project venho_hotel \
  --subject lake_view_room \
  --input data/projects/venho_hotel/media/lake_view_room
```

Output: `No image changes detected — DNA is up to date. Skipping regeneration.`
Then: `[overlay] applied (render-only, no version bump)`

---

## Checking overlay is applied

Look for `overlay_applied: true` in the manifest:

```bash
cat data/projects/venho_hotel/knowledge/dna_manifest_lake_view_room.json
```
