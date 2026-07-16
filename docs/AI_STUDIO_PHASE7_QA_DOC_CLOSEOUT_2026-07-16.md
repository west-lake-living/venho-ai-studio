# AI Studio Phase 7 — QA/DOC Closeout

Roadmap v1.5 has no formal Phase 7 section. This closeout maps to backlog items `QA-01` and `DOC-01`.

## Scope

- Controlled live evaluation matrix is now canonical at `config/quality/controlled_live_matrix.json`.
- Offline evaluator lives in `validator_studio/controlled_matrix.py`.
- Unit/integration tests must never call paid generation.
- Production-ready image workflow requires two consecutive approved runs per case.

## Cases

- E1 running front-facing / mint green / Nguyễn Đình Thi / face ref on
- E2 running 3/4 / Nike pink / Nguyễn Đình Thi / face ref on
- E3 cycling / mint green / Nguyễn Đình Thi / face ref off
- E4 cycling / Nike pink / Nguyễn Đình Thi / face ref off
- E5 static portrait / mint green / West Lake / face ref on
- E6 static portrait / Nike pink / West Lake / face ref on

## Gate

Each run must pass actor geometry, face identity, outfit match, scenario/location, technical quality, and validator availability. Missing validator means `UNVALIDATED`, not approved.
