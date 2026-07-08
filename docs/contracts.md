# Output Contracts — VENHO AI Studio (v2.4 / v2.5)

All output files carry a `contract_version` field. When the output shape changes in
a breaking way, this version must be bumped. Downstream consumers (prompt engines,
social pipeline) must pin to a known contract version.

---

## Mode A — Observation JSON (`contract_version: "1.0"`)

Each image in Mode A produces one `.json` file.

### Required fields

| Field | Type | Notes |
|---|---|---|
| `contract_version` | `"1.0"` | Fixed — always observation contract |
| `mode` | `"A"` or `"B"` | Set by pipeline |
| `image_hash` | `str` | SHA-256 of image bytes |
| `image_file` | `str` | Basename only |
| `subject` | `str` | Subject name (e.g. `"universal"`, `"lake_view_room"`) |
| `schema_id` | `str` | Schema used (e.g. `"universal"`, `"venho_hotel.room"`) |
| `schema_version` | `str` | From `settings.yaml` |
| `prompt_version` | `str` | From `settings.yaml` |
| `provider` | `str` | AI provider used |
| `model` | `str` | Model ID |
| `observed_at` | `str` | ISO datetime |
| `features` | `list[ObservedFeature]` | Observed key-value pairs |
| `notable_features` | `list[str]` | Free-text notable details |
| `uncertainty` | `list[str]` | Uncertain elements |

### Mode A Markdown sections (fixed)

```
# IMAGE OBSERVATION
## META
## SUBJECT
## SCENE
## COMPOSITION
## LIGHTING
## PALETTE
## MATERIALS
## AI-USABLE NOTES
## UNCERTAINTY
```

Markdown is rendered from the JSON — if JSON is correct, Markdown is correct.

---

## Mode B — DNA JSON (`contract_version: "1.1"`)

Each subject in Mode B produces one `.json` DNA file.

### Required fields

| Field | Type | Notes |
|---|---|---|
| `contract_version` | `"1.1"` | Fixed — always DNA contract |
| `mode` | `"B"` | Always B for DNA |
| `project` | `str` | Project name (e.g. `"venho_hotel"`) |
| `subject` | `str` | Subject name |
| `dna_version` | `str` | Incremented on image set change |
| `schema_id` | `str` | Schema used |
| `schema_version` | `str` | From `settings.yaml` |
| `prompt_version` | `str` | From `settings.yaml` |
| `provider` | `str` | AI provider used |
| `model` | `str` | Model ID |
| `generated_at` | `str` | ISO datetime |
| `source_images` | `list[str]` | SHA-256 hashes of source images |
| `invariant` | `list[InvariantFeature]` | Stable features across all/most images |
| `variable` | `list[VariableFeature]` | Features that change between images |
| `allowed_imperfections` | `list[AllowedImperfection]` | Acceptable real-world imperfections |
| `forbidden` | `list[ForbiddenRule]` | Things AI must NOT generate |
| `evidence` | `EvidenceSummary` | Statistics |
| `future_capture_notes` | `list[str]` | Notes for next photo shoot |
| `curator_notes` | `list[str]` | From overlay — human editorial notes |

### Mode B DNA Markdown sections (fixed)

```
# PROJECT SUBJECT DNA
## META
## INVARIANT
## VARIABLE
## ALLOWED IMPERFECTIONS
## FORBIDDEN
## EVIDENCE
## WEAK FEATURES
## FUTURE CAPTURE NOTES
## CURATOR NOTES
```

---

## InvariantFeature

```json
{
  "key": "floor",
  "value": "dark hardwood floor",
  "value_source": "machine",
  "evidence_count": 8,
  "coverage": 0.9,
  "consistency": 0.88,
  "confidence": 1.0
}
```

- `value_source`: `"machine"` (AI-detected) or `"curated"` (overlay wording override)
- `coverage`: fraction of images where key was visible
- `consistency`: fraction of visible images where value was the most common value

---

## ForbiddenRule

```json
{"rule": "no synthetic materials", "source": "curated"}
```

- `source`: `"curated"` (from overrides.yaml — policy) or `"observed"` (AI hint)
- Curated rules always appear first in the list

---

## AllowedImperfection

```json
{"value": "minor wall scuffs", "source": "curated"}
```

---

## Cache key format

Observation cache file name:

```
{sha256_of_image}_{schema_id}_{schema_version}_{prompt_version}.json
```

Changing `schema_version` or `prompt_version` invalidates all existing cache files.

---

## Version bump rules

| Event | Action |
|---|---|
| New images added | Archive old DNA, bump `dna_version` (e.g. `1.0` → `1.1`) |
| Overlay edited | Re-render only — no `dna_version` bump, no vision API calls |
| `schema_version` changed | Invalidates observation cache — observations regenerated on next run |
| `prompt_version` changed | Invalidates observation cache |
| Breaking schema shape change | Bump `contract_version` (requires updating all consumers) |
