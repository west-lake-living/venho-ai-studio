# DR-GC2 — Reversible publisher cutover

**Decision owner:** Harry  
**Date:** 2026-11-12 (ICT)  
**Status:** DECIDED — schedule superseded 2026-11-12

## Decision

At T−0, temporarily pause the legacy publisher and switch the active Make scenario to v2. Keep legacy source code, registry and data intact. Before importing over production scenario `5868920`, save its blueprint export as the rollback backup. Do not delete or rotate the legacy 64-character hex literal during this temporary transition; preserve it inside the protected backup and revisit it only under a separately approved permanent-retirement change.

P9-T04’s ≥8 slots, ≥16 target outcomes, ≥14 stable days and restore rehearsal gate applies to **permanent removal** of legacy publishing, not the reversible pause at T−0.

## Guardrails during transition

- Keep the production runtime `LIVE_MANUAL`; approve every post individually before dispatch.
- Require a separate receipt and verification for each Facebook Page and Instagram target.
- Keep Telegram operational for alerts. An `UNKNOWN`, missing receipt, wrong target or failed verification pauses that target; never resend a target already verified successful.
- Make TEST evidence MK-1 through MK-6 is PASS. Treat it as a technical control, not as a substitute for per-post approval or production verification.
- Rollback may import the saved scenario export and resume legacy only after confirming v2 has no live run, queued grant or late execution that could publish the same slot/target.

## Superseded schedule

The prior fixed T−0 of 2026-11-16 at 09:00 ICT is cancelled. Legacy remains the sole publisher until P4 passes and Harry approves one real `fb_hanoi` delivery in VENHO OS. Only then choose the nearest cadence slot that starts at least 48 hours after both gates passed. Until that slot, keep legacy publishing and keep v2 non-dispatching. No replacement cutover date is reserved in advance.

## Record updates

This decision supersedes any wording in the Stage B cutover notes that makes the P9-T04 permanent-retirement gate a prerequisite for a reversible pause. It also supersedes the 16/11 conditional schedule. Permanent retirement remains blocked until its evidence is complete.
