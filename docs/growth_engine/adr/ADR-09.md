# ADR-09 — One Make scenario with channel-key Router

**Status:** GC2-D09 confirmed 2026-11-04; TEST evidence and production cutover remain pending.

## Context

The existing Make scenario already has Facebook and Instagram routes. Replacing it with separate scenarios would duplicate connections and require rebuilding the existing workflow.

## Decision

Keep one scenario and one Router for `fb_hanoi`, `fb_venho` and `ig_venho`. The shared filter validates the command schema and environment; each route filters on its fixed `channel_key`; disable the fallback route. Give each route its own application bearer. Only the matching route may create a post. Facebook routes fetch the signed image as binary before posting; the Instagram route passes the signed image URL to Instagram for Business.

The v2 targets are Facebook Page *Ven Hồ Hotel Hanoi* (`1124616474074140`), Facebook Page *Ven Hồ Hotel* (ID still `REQUIRED_FROM_P0`) and Instagram business account `ig_venho` (ID still `REQUIRED_FROM_P0`). Threads remains history-only.

## Consequences

- Existing connections can be reused after each route is tested.
- A disabled scenario affects all three channels; this is accepted at the current scale.
- MK-1…MK-11 must be proven on a TEST copy before live configuration or cutover.
- The production scenario was not opened or modified during this task.

## Alternatives

- One scenario per channel: rejected for the current build because it duplicates scenario/connection configuration and diverges from GC2-D09.
