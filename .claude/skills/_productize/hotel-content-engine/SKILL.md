# hotel-content-engine

Productized hotel content skill.

Runs a hotel brief through the generic content engine using only `config/projects/<project_id>/...` inputs.

Rules:
- Must run for hotel #2 by adding project config only.
- Must not change core modules for a new hotel.
- Output remains draft until the normal approval and publishing gates.

## Trigger

```bash
venho-rollout productize-run --project <hotel_id> --brief-json <path/to/brief.json>
```

`brief.json` shape: `{"hotel_name": "...", "objective": "...", "single_minded_message": "...", "cta": "..."}`.

## Known limitation (2026-08-06)

This engine is a lightweight demonstration that a second hotel's content
draft can be built from `config/projects/<project_id>/content/tone_of_voice.yaml`
+ `growth/taxonomy.yaml` alone — it does not run the full M02 prompt/M05
copy-candidate pipeline `daily_cycle.py` uses in production. Treat this as
"config-only, core-unmodified" proof, not a second hotel's real production
pipeline yet.
