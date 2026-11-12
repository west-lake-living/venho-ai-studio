# GC2 task memory — 2026-11-05

- `GC2_MASTER_PLAN.md` had only its original add commit in `git log -- docs/growth_engine/GC2_MASTER_PLAN.md`; there were no later committed plan patches to reapply.
- Preserve existing ID boundaries and migrations: domain/SQLite `remote_account_id`; existing Facebook config and Make boundary `remote_page_id`.
- Meta candidate configuration is not verified evidence. No token was present, so no Meta, Make, Telegram, SSH or deployment call was made.
- IG media metric period was not supplied in the request; keep it omitted in the candidate probe and confirm through P0-T04 instead of guessing.
- Track 0 reconciliation reads legacy registry/config; Insights writes its own `~/venho/state/growth-reports/insights.db` without opening the Growth Engine v2 DB.
- Legacy suite passed with exactly the baseline's 79 failing node IDs after excluding the five optional `cv2` files; no baseline update was needed.

### 2026-11-11 — DR-GC2-D02: both production Facebook Pages
- Harry confirmed that each Facebook slot should publish to both Ven Hồ Hotel Hanoi (`fb_hanoi`) and Ven Hồ Hotel (`fb_venho`). Use separate deliveries, commands, receipts and verification per Page; do not resend Hanoi to recover Ven Hồ.
- The four-slot weekly cadence is unchanged. `EnsureSlots` creates each enabled channel target per slot; grouped approval can approve the two Facebook deliveries together with Instagram in one atomic batch without publishing.
- Make TEST confirms Instagram cannot fetch public Google Drive files. Signed media URL is mandatory for production; `instagram_photo_v1` is JPEG, ≤5 MiB and exactly 4:5, within Make's stated ≤8 MB and 4:5–1.91:1 limits.

### 2026-11-11 — MK-1 sequential TEST evidence
- Two distinct `fb_hanoi` TEST webhook deliveries were sent 300 ms apart. Make History run 1 started 15:22:30 ICT and lasted 7 s; run 2 started 15:22:39 after run 1 ended and lasted 5 s.
- Both distinct posts (`…_122107590483535879`, `…_122107590693535879`) had applied receipts. MK-1 is PASS. MK-1…MK-6 now satisfy the Make capability gate for `LIVE_MANUAL`; production remains DISABLED until the staged target checks pass.

### 2026-11-12 — DR: reversible cutover and conditional T−0
- Harry decided T−0 temporarily pauses legacy publishing only. Preserve code, registry, scenario export `5868920`, and the old hex literal; do not rotate/delete it during this transition. P9-T04’s 8-slot/16-outcome/14-day/restore gate applies to permanent removal only.
- Compensating controls: MK-1…MK-6 PASS in TEST, `LIVE_MANUAL` with per-post approval, receipt + verify per target, and Telegram alerts.
- Keep 2026-11-16 09:00 ICT only if production P4 passes by the evening of 14/11; otherwise use the 18/11 or 20/11 scheduled slot after P4 passes. Full record: [DR-GC2 reversible cutover](task_memory/decisions/DR-GC2-2026-11-12-reversible-cutover.md).
