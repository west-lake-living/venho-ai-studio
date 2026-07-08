# How to Create a New Subject Schema

A subject schema tells the AI exactly which features to observe for a specific type of image
(e.g. a hotel room, a cafe interior, a face).

---

## Schema file location

```
config/projects/<project>/subjects/<subject>.yaml
```

Example: `config/projects/venho_hotel/subjects/lobby.yaml`

---

## Schema YAML structure

```yaml
schema_id: venho_hotel.lobby
display_name: "Ven Hồ Hotel — Lobby"
description: "Hotel lobby, reception desk, entrance area"

aggregation_keys:
  - key: floor_material
    type: enum
    values:
      - marble
      - granite
      - tile
      - hardwood
      - not_visible

  - key: reception_desk
    type: enum
    values:
      - present
      - not_visible

  - key: lighting_condition
    type: enum
    values:
      - natural_light
      - warm_artificial
      - mixed
      - not_visible

  - key: ceiling_height
    type: free

  - key: overall_style
    type: enum
    values:
      - modern
      - classic
      - boutique
      - not_visible

forbidden_defaults:
  - no lobby furniture visible
  - scene does not show reception area
```

---

## Field reference

### `schema_id`

Unique identifier. Format: `<project>.<subject>` or just `<subject>`.
Used in cache keys — changing it invalidates existing observation cache.

### `display_name`

Human-readable name shown in CLI output.

### `aggregation_keys`

The fixed keys the AI **must** report for every image. These become the rows in
INVARIANT / VARIABLE / WEAK FEATURES in the DNA.

Each key has:
- `key` — exact name (snake_case, English)
- `type` — `enum` (restricted values) or `free` (any string)
- `values` — required for `enum` type. **Always include `"not_visible"` as the last value.**

#### Rules

- All values must be in English (for stable string matching across runs)
- Keys must be stable — changing a key name invalidates existing DNA
- 8–15 keys is a good range. Too few → DNA isn't detailed enough. Too many → AI gets confused.
- Use `enum` for structural features (color, material, style). Use `free` for measurements,
  descriptions, or open-ended details.

### `forbidden_defaults`

Rules that should always appear in FORBIDDEN regardless of observations.
These are starting points — the overrides.yaml is the primary source of curated forbidden rules.

---

## Using Schema Bootstrap (v2.5)

If you're not sure what keys to include, use bootstrap to generate a starter schema:

```bash
venho vision bootstrap \
  --subject lobby \
  --input data/projects/venho_hotel/media/lobby \
  --project venho_hotel \
  --max-sample 3
```

This generates a starter YAML at:
```
config/projects/venho_hotel/subjects/lobby.yaml
```

**Always review and edit the bootstrap output before using it for DNA generation.**
Bootstrap schemas are saved as drafts:

```yaml
status: draft
approved_for_pass1: false
```

After human review, set:

```yaml
approved_for_pass1: true
```

Pass 1 will reject raw bootstrap drafts until this approval flag is changed.

---

## Checklist before first run

- [ ] `schema_id` is unique
- [ ] `aggregation_keys` has 8–15 keys with clear English values
- [ ] Every `enum` key includes `not_visible` as a value
- [ ] `forbidden_defaults` covers the most obvious non-starters
- [ ] Schema reviewed by a human (not raw AI output)
