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
