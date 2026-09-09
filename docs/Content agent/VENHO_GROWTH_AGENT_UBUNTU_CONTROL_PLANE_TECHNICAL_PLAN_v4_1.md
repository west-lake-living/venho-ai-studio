# VENHO GROWTH AGENT — UBUNTU CONTROL PLANE

## Technical Specification & Implementation Plan **v4.1** (Clean Architecture Revision)

| | |
|---|---|
| **Project** | Nâng cấp runtime Growth Agent v3.1 → Ubuntu Control Plane 24/7 |
| **Repo chính** | `venho-ai-studio` (Python) |
| **Repo phụ** | `venho-os` (Next.js/TS — review UI) |
| **Trạng thái** | Implementation Handoff — sẵn sàng giao AI coding agent |
| **Thay thế** | v4.0 (2026-09) |
| **Ngôn ngữ code** | Python 3.12, FastAPI, SQLAlchemy 2.x, SQLite (WAL) |

---

> **HƯỚNG DẪN CHO AI CODING AGENT — ĐỌC TRƯỚC KHI VIẾT DÒNG CODE ĐẦU TIÊN**
>
> 1. Đọc `CLAUDE.md`, `task_memory.md`, `task_status.md` trong repo trước mọi task.
> 2. Tài liệu này là **source authority** về kiến trúc. Nếu code hiện tại mâu thuẫn với tài liệu, **dừng lại và báo cáo** — không tự ý sửa theo bên nào.
> 3. Mỗi task phải khai báo `Allowed files`. Chạm file ngoài danh sách đó = task fail.
> 4. Không được đổi ownership của M01/M03/M05/M07 (§3).
> 5. Không tạo publish path thứ hai. M07 là đường ra duy nhất.
> 6. `pytest` mặc định **0 real API call**. Không có ngoại lệ.
> 7. Không hạ acceptance gate để làm test xanh. Gate fail = báo cáo, không sửa gate.
> 8. Mọi external write phải phân loại `SUCCESS | FAILED | UNKNOWN`. `UNKNOWN` **không được** retry mù.

---

# 0. Executive Decision

## 0.1. Quyết định

**GO — nâng cấp runtime authority. KHÔNG rebuild domain. KHÔNG migrate sang PostgreSQL ở v4.1.**

Growth Agent v3.1 đã có đầy đủ domain intelligence (M01 facts, M03 validator, M05 generation, M07 gateway, Evergreen, Trend Radar, budget gate, exact-version approval). Vấn đề duy nhất là **runtime**: GitHub Actions cron không chạy 24/7 event-driven, git-sync gây lock/ENOBUFS, state phân mảnh giữa JSON/SQLite/git, và không duyệt được từ điện thoại.

v4.1 thay **runtime authority**, không thay **domain**.

## 0.2. Delta so với v4.0 — và lý do

| # | v4.0 đề xuất | v4.1 quyết định | Lý do |
|---|---|---|---|
| 1 | PostgreSQL làm operational SSOT, migration 3 stage S0/S1/S2 | **Giữ SQLite (WAL, single-writer), hợp nhất registry JSON vào cùng DB.** Postgres → deferred, có trigger condition (§7.4) | Nguyên nhân gốc của git-sync là GitHub runner ephemeral. Lên host 24/7 thì lý do đó biến mất. Volume thật ~16 dòng/tuần, ~800 dòng/năm, 1 người + 1 cron. Postgres chiếm ~40% khối lượng và gần như toàn bộ rủi ro migration mà không mở khoá giá trị nào |
| 2 | `domain/`, `api/`, `persistence/`, `worker/` là sibling | **Phân tầng đúng Clean Architecture 4 lớp + `ports/` tường minh + composition root** (§2, §4) | v4.0 tuyên bố dependency rule nhưng không có cấu trúc cưỡng chế. AI agent sẽ vi phạm trong 3 commit |
| 3 | Không có cơ chế bảo vệ layer | **Architecture fitness test** (`tests/architecture/test_layer_boundaries.py`) chạy trong CI | Đây là điều duy nhất giữ Clean Architecture sống sót khi AI agent viết code |
| 4 | Hermes có role `writer` | **Hermes chỉ `researcher` + `classifier`.** Writer vẫn là M05 | M05 đã có gpt-5.5 + rubric + validator gate đã test. Giao writer cho Hermes = duplicate M05 + rủi ro giảm chất lượng tiếng Việt chưa kiểm chứng |
| 5 | Meta Insights ở U7 (cuối chuỗi 8 phase) | **Tách thành Phase V0, chạy TRƯỚC U0** | `real_meta_insights_enabled=true` hiện raise `RuntimeError` — chưa có Graph API client thật. Không có số liệu thì mọi việc phía sau không đo được. Việc này độc lập với migration |
| 6 | Không nhắc lỗi Make → FB post ID | **Đưa vào V0 làm việc số 1** | Từ 2026-08-12 Make trả `PUBLISHED` không kèm post ID hợp lệ → M07 fail-closed thành `GATEWAY_ERROR`. Kênh chính chưa xác nhận được đăng thành công. Chặn toàn bộ analytics phía sau |
| 7 | n8n là scheduler, không có phương án thay | **n8n là driving adapter thay được.** Mọi workflow phải là 1 HTTP call thuần tới 1 endpoint. Fallback: systemd timer gọi cùng CLI (§9.4) | Giữ đúng nguyên tắc "không thêm công cụ khi chưa là bottleneck" — nếu n8n gây phiền, gỡ trong 1 giờ, không sửa domain |
| 8 | Video/Reels không được nhắc | **Đưa vào Deferred có tên (§14.4)**, và cấm hard-code giả định image-only trong `ContentPackage` | Kênh đang cần chuyển sang video. Nếu domain giả định 1 ảnh/bài thì sau này phải sửa lõi |
| 9 | 20 bảng Postgres | **14 bảng SQLite** — gộp/bỏ 6 bảng chưa có consumer (§7.3) | Bảng không có consumer là nợ kỹ thuật, không phải kiến trúc |

## 0.3. Invariant BẤT BIẾN — kế thừa nguyên vẹn từ v3.1

Vi phạm bất kỳ dòng nào dưới đây = task fail, không thương lượng.

1. **VENHO AI Studio sở hữu Growth domain.** Không tạo repo/hệ Growth mới.
2. **M03 là validator duy nhất.** Mọi content qua M03 trước review. Sửa sau review → validate lại.
3. **M07 là publishing gateway duy nhất.** Make là adapter phía sau M07, không phải authority.
4. **Human approval bắt buộc** cho final package. Không tồn tại code path auto-publish.
5. Approval gắn với **exact copy version + exact asset version + validation snapshot**.
6. Thay đổi content/image/CTA/fact/schedule có ảnh hưởng → approval cũ **mất hiệu lực tự động**.
7. `HTTP 200` từ downstream **không** đồng nghĩa `PUBLISHED`. Chỉ receipt/reconciliation mới xác nhận.
8. **Không retry write mù** khi outcome `UNKNOWN`.
9. Evidence Ladder R0→R4 giữ nguyên. Chỉ fact **R3 active** được dùng làm factual claim.
10. T7 special lane **không auto-approve**.
11. Test mặc định **0 real API call**.
12. Budget gate **fail-closed**.
13. Rollout stage **không** được tự thay đổi approval requirement.

---

# 1. Scope

## 1.1. In scope

- Runtime migration sang Ubuntu 24/7 (Docker Compose).
- `growth_core`: Core API (FastAPI) + Worker + Outbox, viết theo Clean Architecture.
- Hợp nhất operational state: `publication_registry.json` + `growth.db` + rotation state → **một** SQLite DB có schema versioned (Alembic).
- n8n orchestration ở mức trigger/ingress thuần.
- Hermes adapter (researcher + classifier).
- Approval flow qua Telegram (duyệt được từ điện thoại).
- Publishing dispatch + Make callback + reconciliation trên Ubuntu.
- Real Meta Insights collector + attribution ingestion.
- Health/backup/restore/alert.

## 1.2. Out of scope (v4.1)

- Rebuild M01–M10, M03 validator, M07 logic.
- Auto-approval nội dung cuối.
- PostgreSQL migration (deferred, §7.4).
- Video/Reels publishing (deferred, §14.4).
- Ads automation, CRM, browser automation, microservices, Redis, multi-region.
- Multi-tenant thật (giữ `tenant_id` làm cột, không xây tenant isolation).

---

# 2. Architecture

## 2.1. Bốn lớp

```text
┌──────────────────────────────────────────────────────────────┐
│  L4  COMPOSITION ROOT          composition/                  │
│      Nơi DUY NHẤT chọn implementation cụ thể. Không logic.   │
└───────────────────────────┬──────────────────────────────────┘
                            │ wires
┌───────────────────────────▼──────────────────────────────────┐
│  L3  ADAPTERS                  adapters/                     │
│      driving/  ← thế giới gọi vào (HTTP, CLI, Worker, TG)   │
│      driven/   ← hệ thống gọi ra (DB, Studio, Hermes, Make) │
└───────────────────────────┬──────────────────────────────────┘
                            │ implements ports / calls use cases
┌───────────────────────────▼──────────────────────────────────┐
│  L2  APPLICATION               application/                  │
│      use_cases/  điều phối 1 nghiệp vụ, 1 transaction        │
│      ports/      Protocol interface — hợp đồng ra ngoài      │
│      dto/        object biên, không rò rỉ entity ra ngoài    │
└───────────────────────────┬──────────────────────────────────┘
                            │ uses
┌───────────────────────────▼──────────────────────────────────┐
│  L1  DOMAIN                    domain/                       │
│      Entity, Value Object, State Machine, Policy.            │
│      CHỈ import stdlib. Không I/O, không async, không SQL.   │
└──────────────────────────────────────────────────────────────┘
```

## 2.2. Dependency Rule — cưỡng chế bằng test, không bằng niềm tin

```text
composition  →  adapters  →  application  →  domain
                                ↑
                            (ports)  ←  adapters/driven implements
```

**Luật tuyệt đối:**

| Lớp | ĐƯỢC import | CẤM import |
|---|---|---|
| `domain/` | stdlib, `dataclasses`, `enum`, `datetime`, `decimal` | mọi thứ khác trong `growth_core`, mọi thư viện bên thứ ba |
| `application/` | `domain/`, `application/ports/`, stdlib | `adapters/`, `composition/`, `sqlalchemy`, `fastapi`, `httpx` |
| `adapters/` | `domain/`, `application/`, thư viện bên thứ ba | `composition/`, adapter khác cùng cấp (trừ qua port) |
| `composition/` | tất cả | — |

> **AI AGENT:** Trước khi thêm bất kỳ `import` nào vào `domain/` hoặc `application/`, kiểm tra bảng trên. Nếu bạn thấy mình cần `import sqlalchemy` trong use case, nghĩa là bạn đang thiếu một port — hãy tạo port, đừng import.

Test cưỡng chế: `tests/architecture/test_layer_boundaries.py` (§13.1). Chạy trong CI, fail = block merge.

## 2.3. Core rule

> **n8n gọi Growth Agent. n8n KHÔNG chứa Growth Agent.**
>
> Nếu một business rule xuất hiện trong n8n node (if/switch/expression tính điểm, tính hạn, quyết định approve), đó là bug kiến trúc. Chuyển vào `domain/` hoặc `application/`.

---

# 3. Responsibility Matrix

| Thành phần | ĐƯỢC làm | KHÔNG được làm |
|---|---|---|
| **Hermes** | research, classify, summarize, recommend | **write final copy**, approve, publish, set policy, giữ credential |
| **n8n** | trigger theo lịch, nhận webhook, gọi 1 endpoint Core API, gửi alert | giữ state machine, tính score, quyết định idempotency, chứa if/else nghiệp vụ |
| **Core API** | validate command, transition state, cưỡng chế policy/approval/idempotency/concurrency | sinh văn bản sáng tạo, gọi thẳng Meta/Make |
| **Worker** | thực thi command đã approve, retry read an toàn, reconcile write | bypass approval/M03/M07 |
| **SQLite** | durable operational state, constraint, audit, lease | lưu secret dạng plain text |
| **VENHO AI Studio (M01/M03/M05/M07)** | toàn bộ Growth domain logic | sở hữu scheduler/infrastructure |
| **Make** | adapter giao hàng tới platform | quyết định bài đã được duyệt hay chưa |
| **Telegram** | alert + control surface (approve/reject/kill) | là source of truth |
| **venho-os** | rich review UI | gọi thẳng Make/Meta |

---

# 4. File Tree chuẩn hoá

> **AI AGENT:** Đây là cấu trúc đích. Mỗi task chỉ được tạo/sửa file nằm trong `Allowed files` của task đó. File có dấu `★` là file phải tạo mới ở phase tương ứng.

```text
venho-ai-studio/
│
├── CLAUDE.md                              # đã có — đọc trước mọi task
├── task_memory.md                         # đã có — append sau mỗi phase
├── task_status.md                         # đã có — append sau mỗi phase
├── pyproject.toml                         # thêm package growth_core + entrypoint venho-core
│
├── knowledge_studio/                      # M01 — KHÔNG SỬA
├── validator_studio/                      # M03 — KHÔNG SỬA
├── content_studio/                        # M05 — KHÔNG SỬA
├── publishing_gateway/                    # M07 — CHỈ SỬA theo task V0-02 (post ID mapping)
├── analytics_feedback/                    # M08 — CHỈ SỬA theo task V0-03 (real insights adapter)
├── research_engine/                       # Research OS + Trend Radar — KHÔNG SỬA
├── growth_orchestrator/                   # v3.1 orchestrator — deprecate dần, xem §14.3
├── shared/                                # jobs/notify/vision — dùng lại, không fork
│
├── growth_core/                        ★  # ═══ TOÀN BỘ CODE MỚI NẰM Ở ĐÂY ═══
│   ├── __init__.py
│   │
│   ├── domain/                         ★  # L1 — chỉ stdlib
│   │   ├── __init__.py
│   │   ├── ids.py                         # SlotId, PackageId, PublicationId (NewType/dataclass)
│   │   ├── clock.py                       # BusinessCalendar: tuần ISO, timezone Asia/Ho_Chi_Minh
│   │   ├── errors.py                      # DomainError, InvalidTransition, PolicyViolation
│   │   ├── entities/
│   │   │   ├── publishing_slot.py         # PublishingSlot + state machine (§6.2)
│   │   │   ├── content_package.py         # ContentPackage + state machine (§6.1)
│   │   │   ├── publication.py             # Publication + state machine (§6.3)
│   │   │   ├── approval.py                # ApprovalRequest / ApprovalDecision
│   │   │   └── job.py                     # Job, JobLease, OutboxEvent
│   │   ├── values/
│   │   │   ├── approval_hash.py           # canonical hash của (copy, asset, validation) (§8.3)
│   │   │   ├── idempotency_key.py         # (§8.4)
│   │   │   ├── write_outcome.py           # SUCCESS | FAILED | UNKNOWN (§8.6)
│   │   │   ├── platform.py                # facebook | instagram | threads | zalo_oa
│   │   │   └── money.py                   # budget, Decimal, không float
│   │   └── policies/
│   │       ├── approval_policy.py         # điều kiện approval mất hiệu lực (invariant #6)
│   │       ├── dispatch_policy.py         # điều kiện đủ để dispatch (§8.5)
│   │       ├── budget_policy.py           # fail-closed (invariant #12)
│   │       └── runway_policy.py           # tính runway slot (§8.2)
│   │
│   ├── application/                    ★  # L2 — không import thư viện bên thứ ba
│   │   ├── __init__.py
│   │   ├── ports/                         # Protocol — hợp đồng với thế giới bên ngoài
│   │   │   ├── unit_of_work.py            # UnitOfWork: begin/commit/rollback + repositories
│   │   │   ├── repositories.py            # SlotRepo, PackageRepo, PublicationRepo, JobRepo, AuditRepo
│   │   │   ├── studio_gateway.py          # M01/M03/M05/M07 — anti-corruption layer
│   │   │   ├── reasoning_gateway.py       # Hermes: research(), classify()
│   │   │   ├── delivery_gateway.py        # Make adapter (qua M07)
│   │   │   ├── insights_gateway.py        # Meta Insights read
│   │   │   ├── notifier.py                # Telegram
│   │   │   ├── clock.py                   # now() — inject để test deterministic
│   │   │   └── id_generator.py            # UUID — inject để test deterministic
│   │   ├── dto/
│   │   │   ├── commands.py                # CreateSlots, GeneratePackage, ApprovePackage, Dispatch...
│   │   │   └── views.py                   # read model trả ra API, KHÔNG phải entity
│   │   └── use_cases/                     # 1 file = 1 use case = 1 transaction
│   │       ├── plan_weekly_slots.py
│   │       ├── generate_content_package.py
│   │       ├── validate_package.py
│   │       ├── request_approval.py
│   │       ├── decide_approval.py         # cưỡng chế exact-version hash
│   │       ├── revoke_stale_approvals.py
│   │       ├── dispatch_publication.py
│   │       ├── ingest_delivery_callback.py
│   │       ├── reconcile_publications.py
│   │       ├── run_trend_scan.py
│   │       ├── collect_metrics.py
│   │       └── toggle_kill_switch.py
│   │
│   ├── adapters/                       ★  # L3
│   │   ├── __init__.py
│   │   ├── driving/                       # thế giới gọi VÀO hệ thống
│   │   │   ├── http/
│   │   │   │   ├── app.py                 # FastAPI app factory
│   │   │   │   ├── deps.py                # Depends() → lấy use case từ container
│   │   │   │   ├── errors.py              # DomainError → HTTP status mapping
│   │   │   │   └── routers/
│   │   │   │       ├── health.py
│   │   │   │       ├── slots.py
│   │   │   │       ├── packages.py
│   │   │   │       ├── approval.py
│   │   │   │       ├── publications.py
│   │   │   │       ├── webhooks.py        # /webhooks/make, /webhooks/telegram
│   │   │   │       ├── research.py
│   │   │   │       ├── analytics.py
│   │   │   │       └── admin.py           # kill switch, rollout stage
│   │   │   ├── cli/
│   │   │   │   └── main.py                # entrypoint `venho-core` — mirror mọi endpoint
│   │   │   ├── telegram/
│   │   │   │   └── callback_router.py     # inline button → use case
│   │   │   └── worker/
│   │   │       ├── runner.py              # vòng lặp claim job theo lease
│   │   │       ├── outbox_dispatcher.py
│   │   │       └── schedules.py           # fallback nếu bỏ n8n (§9.4)
│   │   └── driven/                        # hệ thống gọi RA ngoài
│   │       ├── persistence/
│   │       │   ├── engine.py              # SQLite WAL, busy_timeout, foreign_keys=ON
│   │       │   ├── models.py              # SQLAlchemy ORM — KHÔNG dùng làm domain entity
│   │       │   ├── mappers.py             # ORM model ⇄ domain entity
│   │       │   ├── unit_of_work.py
│   │       │   ├── repositories/
│   │       │   │   ├── slot_repository.py
│   │       │   │   ├── package_repository.py
│   │       │   │   ├── publication_repository.py
│   │       │   │   ├── job_repository.py
│   │       │   │   └── audit_repository.py
│   │       │   └── migrations/            # Alembic
│   │       │       ├── env.py
│   │       │       └── versions/
│   │       ├── studio/                    # anti-corruption layer sang M01/M03/M05/M07
│   │       │   ├── knowledge_bridge.py    # → knowledge_studio (M01)
│   │       │   ├── validator_bridge.py    # → validator_studio (M03)
│   │       │   ├── content_bridge.py      # → content_studio (M05)
│   │       │   └── publishing_bridge.py   # → publishing_gateway (M07)
│   │       ├── hermes/
│   │       │   ├── client.py
│   │       │   ├── schemas.py             # JSON Schema cho output của Hermes
│   │       │   └── prompt_boundary.py     # §10.2 — untrusted content boundary
│   │       ├── meta/
│   │       │   └── insights_client.py     # Graph API read-only
│   │       ├── notify/
│   │       │   └── telegram_sender.py     # wrap shared/notify/telegram.py
│   │       └── system/
│   │           ├── system_clock.py
│   │           └── uuid_generator.py
│   │
│   └── composition/                    ★  # L4 — nơi DUY NHẤT `new` object cụ thể
│       ├── settings.py                    # pydantic-settings, đọc env, fail-fast nếu thiếu
│       ├── container.py                   # build_container() → mọi use case đã wire
│       └── bootstrap.py                   # tạo FastAPI app / CLI / worker từ container
│
├── deployment/                         ★
│   └── ubuntu/
│       ├── docker-compose.yml
│       ├── Dockerfile.api
│       ├── Dockerfile.worker
│       ├── env.example
│       ├── caddy/Caddyfile                # hoặc nginx — chỉ expose /webhooks/*
│       ├── backup/
│       │   ├── backup.sh                  # sqlite .backup + artifact tar + checksum
│       │   └── restore_verify.sh          # PHẢI chạy được, có evidence
│       └── runbooks/
│           ├── incident_duplicate_post.md
│           ├── incident_unknown_write.md
│           ├── incident_token_revoked.md
│           └── cutover_u5.md
│
├── n8n/                                ★
│   └── workflows/                         # export JSON, commit vào repo
│       ├── NG-01-daily-control.json
│       ├── NG-02-weekly-content-cycle.json
│       ├── NG-03-trend-weather-cycle.json
│       ├── NG-04-approval-notifier.json
│       ├── NG-05-dispatch-scheduler.json
│       ├── NG-06-make-callback.json
│       ├── NG-07-reconciliation.json
│       ├── NG-08-analytics-collector.json
│       └── NG-09-health-backup.json
│
└── tests/
    ├── architecture/                   ★
    │   └── test_layer_boundaries.py       # ⚠️ CHẠY ĐẦU TIÊN TRONG CI
    ├── growth_core/
    │   ├── domain/                        # thuần, không fixture DB
    │   ├── application/                   # dùng fake port in-memory
    │   └── adapters/
    ├── contract/                       ★  # schema Hermes, Make payload, Meta response
    ├── integration/                    ★  # SQLite thật, HTTP thật, provider fake
    ├── migration/                      ★  # import registry JSON cũ → parity
    └── chaos/                          ★  # kill giữa dispatch, callback trùng, clock skew
```

---

# 5. Deployment vật lý

## 5.1. Docker Compose

```yaml
# deployment/ubuntu/docker-compose.yml
# AI AGENT: dùng đúng service name dưới đây, container_name khớp để runbook chạy được.
services:
  venho-growth-api:      # FastAPI, KHÔNG expose ra internet trừ /webhooks/*
  venho-growth-worker:   # 1 replica DUY NHẤT — single writer, xem §12.1
  n8n:                   # đã chạy sẵn, reuse
  hermes:                # đã chạy sẵn, reuse
  reverse-proxy:         # Caddy/Cloudflare Tunnel — chỉ route /webhooks/*
  backup-runner:         # cron trong container
```

**Không có service `postgres` ở v4.1.** SQLite nằm trên named volume `venho-growth-data`.

## 5.2. Network zones

```text
public_ingress → reverse-proxy → /webhooks/make      (HMAC verified)
                                 /webhooks/telegram  (secret token verified)

private_backend → core-api ⇄ worker ⇄ sqlite-volume
                  core-api → hermes
                  n8n      → core-api
```

Core API (trừ `/webhooks/*`), Hermes, và volume dữ liệu **không expose ra Internet**.
Truy cập admin/UI qua Tailscale hoặc Cloudflare Access.

## 5.3. Secret policy

Cấm lưu secret trong: repo, n8n workflow JSON export, prompt, audit payload, DB row, research vault.
DB chỉ lưu `secret_ref` (tên biến môi trường), không lưu giá trị.
`composition/settings.py` fail-fast khi thiếu secret bắt buộc — **không** fallback silent sang mock ở production.

---

# 6. Domain State Machines

> **AI AGENT:** Cài đặt state machine trong `domain/entities/*.py` dưới dạng phương thức, không phải if/else rải rác ở use case. Mọi transition không hợp lệ raise `InvalidTransition`. Mỗi transition có unit test riêng.

## 6.1. ContentPackage

```text
DRAFT
  → VALIDATING        (gọi M03)
  → VALIDATION_FAILED (quay lại DRAFT sau khi sửa)
  → READY_FOR_REVIEW
  → PENDING_APPROVAL
  → APPROVED          (gắn approval_hash)
  → SUPERSEDED        (bị bản mới thay)
  → REJECTED
  → EXPIRED           (fact hết hạn / event đã qua / asset đổi)
```

Quy tắc: từ `APPROVED`, bất kỳ mutation nào vào copy/asset/CTA/fact → **bắt buộc** về `DRAFT` và huỷ approval. Không có đường tắt.

## 6.2. PublishingSlot

```text
OPEN → DRAFT_ASSIGNED → PENDING_APPROVAL → FILLED → DISPATCHED → COMPLETED
                                              ↘ EVERGREEN_FALLBACK → DISPATCHED
                                              ↘ MISSED   (chỉ hợp lệ khi evergreen pool đã cạn)
```

Slot ID **deterministic** từ `(tenant, date, weekday, platform)` → chạy lại trên khoảng thời gian chồng lấn là idempotent.

## 6.3. Publication

```text
QUEUED → DISPATCHING → GATEWAY_ACCEPTED → PUBLISHED
                          ↘ GATEWAY_ERROR → (retry thủ công)
                          ↘ UNKNOWN        → RECONCILING → PUBLISHED | FAILED
```

`GATEWAY_ACCEPTED` **không phải** `PUBLISHED`. Chỉ receipt có `platform_post_id` hợp lệ mới chuyển sang `PUBLISHED`.

---

# 7. Persistence

## 7.1. Quyết định: SQLite

```python
# adapters/driven/persistence/engine.py
# AI AGENT: PRAGMA dưới đây là bắt buộc. Thiếu bất kỳ dòng nào = mất đảm bảo concurrency.
PRAGMA journal_mode = WAL;        # reader không chặn writer
PRAGMA busy_timeout = 5000;       # chờ 5s thay vì fail ngay
PRAGMA foreign_keys = ON;         # SQLite mặc định TẮT — phải bật thủ công
PRAGMA synchronous = FULL;        # durability, chấp nhận chậm hơn ở volume này
```

**Single-writer:** chỉ container `venho-growth-worker` và `venho-growth-api` ghi, cùng một volume, và `worker` chạy đúng **1 replica**. Mọi mutation đi qua `UnitOfWork` với transaction tường minh.

## 7.2. Optimistic concurrency

Mọi aggregate mutable có cột `version_no INTEGER NOT NULL`.
`UPDATE ... WHERE id = ? AND version_no = ?` → `rowcount == 0` nghĩa là có người ghi trước → raise `ConcurrencyConflict`, caller retry đọc-lại-ghi-lại tối đa 3 lần.

## 7.3. Bảng (14)

| Bảng | Vai trò | Ghi chú so với v4.0 |
|---|---|---|
| `tenants` | tương thích productization | giữ |
| `publishing_slots` | lịch 4 slot/tuần | giữ |
| `content_packages` | gói nội dung + trạng thái | gộp `creative_briefs` vào đây (chưa có consumer riêng) |
| `copy_versions` | từng version văn bản, immutable | giữ |
| `image_artifacts` | asset immutable + hash | đổi tên → `media_artifacts`, thêm `media_type` để mở đường cho video (§14.4) |
| `validation_runs` | snapshot kết quả M03 | giữ |
| `approval_requests` | yêu cầu duyệt + hash | giữ |
| `approval_decisions` | quyết định append-only | giữ |
| `publications` | 1 bài × 1 platform | gộp `publication_attempts` thành cột + bảng con `publication_events` |
| `publication_receipts` | post ID, permalink | giữ |
| `jobs` | durable job + lease | giữ |
| `outbox_events` | append-only, at-least-once | giữ |
| `metric_snapshots` | số liệu Meta theo cửa sổ | giữ |
| `audit_events` | append-only | giữ |

**Bỏ ở v4.1** (chưa có consumer thật, thêm vào là nợ): `knowledge_facts` (M01 đã sở hữu — đọc qua bridge, không copy), `budget_ledger` (v3.1 đã có store riêng), `trend_candidates` (Trend Radar đã có store), `attribution_events` (chưa có nguồn sự kiện thật — xem §14.4), `publication_attempts`, `creative_briefs`.

> **AI AGENT:** Không tạo bảng cho dữ liệu mà module khác đã sở hữu. Nếu cần fact, gọi `KnowledgeBridge`. Sao chép dữ liệu giữa hai store là vi phạm single-source-of-truth.

## 7.4. Điều kiện kích hoạt migration sang PostgreSQL

Chỉ mở lại quyết định này khi **một** điều kiện xảy ra:

- \> 2 tiến trình cần ghi đồng thời một cách thường xuyên, hoặc
- `SQLITE_BUSY` xuất hiện > 1 lần/tuần sau khi đã bật WAL + busy_timeout, hoặc
- \> 50.000 dòng ở bảng lớn nhất, hoặc
- Cần multi-tenant thật (khách sạn thứ hai lên production).

Vì mọi truy cập DB đã đi qua `application/ports/repositories.py`, migration khi đó là **viết lại 1 package `adapters/driven/persistence/`**, không đụng domain/application. Đó chính là lý do lớp port tồn tại.

---

# 8. Core Logic — đặc tả thuật toán

> **AI AGENT:** Mỗi hàm dưới đây phải là hàm thuần trong `domain/policies/` hoặc `domain/values/`, có unit test bảng-tham-số, không I/O.

## 8.1. Slot ID deterministic

```
slot_id = sha256(f"{tenant_id}|{iso_date}|{weekday}|{platform}")[:16]
```
Chạy `plan_weekly_slots` hai lần trên cùng khoảng thời gian → 0 slot trùng.

## 8.2. Runway

```
runway_days = số ngày liên tiếp kể từ hôm nay mà mọi slot đều ở trạng thái
              {FILLED, DISPATCHED, COMPLETED, EVERGREEN_FALLBACK}
alert nếu runway_days < 3
```

## 8.3. Exact-version approval hash

```
approval_hash = sha256(canonical_json({
    "package_id":     ...,
    "copy_version_id":     ...,   # version cụ thể, không phải "latest"
    "media_artifact_ids":  [...],  # đã sort
    "validation_run_id":   ...,
    "cta":                 ...,
    "scheduled_at":        ...,    # ISO-8601 UTC
    "fact_ids":            [...],  # đã sort
}))
```

`canonical_json` = `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`.
Đổi **một ký tự** trong copy → hash đổi → approval cũ vô hiệu. Đây là acceptance test bắt buộc của Gate G2.

## 8.4. Idempotency key cho publication

```
idempotency_key = sha256(f"{slot_id}|{platform}|{approval_hash}")
```
UNIQUE constraint trên `(tenant_id, idempotency_key)`. Dispatch lần hai với cùng key → trả receipt cũ, **không** gọi Make.

## 8.5. Dispatch eligibility — tất cả phải TRUE

```
1. package.state == APPROVED
2. approval_hash khớp hash tính lại từ state hiện tại   ← chống sửa lén sau duyệt
3. kill_switch(global) == OFF và kill_switch(platform) == OFF
4. budget_policy.allows(estimated_cost) == True
5. rollout_stage cho phép platform này
6. mọi fact_id còn active (chưa hết hạn)
7. media artifact tồn tại và hash khớp
8. chưa tồn tại publication PUBLISHED cho cùng idempotency_key
```

Fail bất kỳ điều kiện nào → không dispatch, ghi `audit_events` với lý do cụ thể, không raise ra ngoài dưới dạng lỗi mơ hồ.

## 8.6. Phân loại kết quả write

```
SUCCESS  : HTTP 2xx VÀ có platform_post_id hợp lệ trong response/callback
FAILED   : HTTP 4xx (trừ 429) — lỗi xác định, không retry
UNKNOWN  : timeout, 5xx, 429, mất kết nối, HTTP 2xx nhưng KHÔNG có post_id
```

> ⚠️ **UNKNOWN không bao giờ được retry tự động.** Chuyển sang `RECONCILING`, để reconciliation job đọc lại từ platform xác định thực tế. Đây là cơ chế chống đăng trùng — vi phạm điều này là lỗi nghiêm trọng nhất có thể gây ra trong hệ thống này.

Trường hợp `HTTP 2xx nhưng không có post_id` chính là lỗi thật đang xảy ra với Facebook từ 2026-08-12 (§14.1, task V0-01).

## 8.7. Job claim / lease

```sql
UPDATE jobs
   SET state='RUNNING', lease_owner=?, lease_expires_at=?, version_no=version_no+1
 WHERE id = (SELECT id FROM jobs
              WHERE state='PENDING' AND run_after <= :now
              ORDER BY priority DESC, run_after ASC LIMIT 1)
   AND state='PENDING';
```
Lease hết hạn mà job vẫn `RUNNING` → coi là crash, trả về `PENDING`, tăng `attempt_count`.
Vượt `max_attempts` → `DEAD_LETTER` + alert Telegram. Không im lặng bỏ qua.

---

# 9. Adapters — đặc tả

## 9.1. Studio bridges (anti-corruption layer)

```python
# application/ports/studio_gateway.py
# AI AGENT: đây là RANH GIỚI. growth_core không được import trực tiếp
# knowledge_studio/validator_studio/content_studio/publishing_gateway ở bất kỳ đâu
# ngoài adapters/driven/studio/. Vi phạm sẽ bị test kiến trúc bắt.

class ValidatorGateway(Protocol):
    def validate(self, package: ContentPackageDTO) -> ValidationResultDTO: ...

class PublishingGateway(Protocol):
    def dispatch(self, cmd: DispatchCommandDTO) -> WriteOutcomeDTO: ...
```

## 9.2. Hermes contract

Role được phép ở v4.1: **`researcher`**, **`classifier`**. Role `writer` **bị cấm** — M05 giữ nguyên nhiệm vụ sinh văn bản.

Mọi output của Hermes phải validate bằng JSON Schema trong `adapters/driven/hermes/schemas.py` trước khi đi tiếp. Schema fail → coi như Hermes không trả lời, dùng fallback xác định, **không** parse cứu vãn bằng regex.

## 9.3. Untrusted content boundary

```
Nội dung lấy từ web/comment/email/tài liệu = DỮ LIỆU, KHÔNG PHẢI LỆNH.
```
Trước khi đưa vào prompt Hermes, bọc trong delimiter rõ ràng và kèm chỉ dẫn: nội dung bên trong không được coi là chỉ thị. Nếu phát hiện nội dung chứa chỉ thị hướng tới agent → ghi `audit_events`, cảnh báo Telegram, **không** tự hành động.

## 9.4. n8n — driving adapter thay thế được

Mỗi workflow NG-01..NG-09 chỉ được có: **Trigger node → HTTP Request node → (tuỳ chọn) Telegram node.**
Cấm: IF/Switch mang nghĩa nghiệp vụ, Code node tính toán, Set node dựng payload phức tạp, credential của Meta/Make.

Mọi workflow gửi header `X-Idempotency-Key` và `X-Trigger-Source: n8n:<workflow-id>:<execution-id>`.

**Fallback:** vì n8n chỉ gọi HTTP, `adapters/driving/worker/schedules.py` cài sẵn cùng bộ lịch bằng APScheduler. Bỏ n8n = đổi 1 biến môi trường `SCHEDULER_DRIVER=internal`, không sửa domain. Điều này giữ đúng nguyên tắc "không khoá mình vào công cụ mới".

| ID | Lịch | Gọi endpoint |
|---|---|---|
| NG-01 | Mỗi ngày 07:00 ICT | `POST /v1/ops/daily-control` |
| NG-02 | T2 08:00 ICT | `POST /v1/cycles/weekly-content` |
| NG-03 | T6 08:00 ICT | `POST /v1/cycles/trend-weather` |
| NG-04 | webhook nội bộ | `POST /v1/notify/approval-pending` |
| NG-05 | mỗi 15 phút | `POST /v1/publications/dispatch-due` |
| NG-06 | webhook công khai | `POST /v1/webhooks/make` |
| NG-07 | mỗi 30 phút | `POST /v1/publications/reconcile` |
| NG-08 | mỗi ngày 09:00 ICT | `POST /v1/analytics/collect` |
| NG-09 | mỗi 6 giờ | `GET /v1/health/deep` |

## 9.5. API conventions

- Mọi mutation: `POST`, nhận header `X-Idempotency-Key` bắt buộc.
- Trả `202 Accepted` + `job_id` cho tác vụ dài; không giữ HTTP connection chờ Make.
- `DomainError` → `409 Conflict` kèm `error_code` máy đọc được; không trả stack trace.
- Không có endpoint nào cho phép publish mà bỏ qua approval. Không có query param `?force=true`.

---

# 10. Kill Switch

Ba cấp, kiểm tra theo thứ tự, **ngay trước** lời gọi HTTP ra ngoài (không phải ở tầng API):

```
GLOBAL        → chặn mọi write ra ngoài
PLATFORM      → chặn 1 platform (facebook | instagram | ...)
PUBLICATION   → chặn 1 bài cụ thể
```

Bật được từ: Telegram command, CLI `venho-core kill --scope`, API admin.
Trạng thái lưu trong DB, **fail-closed**: đọc lỗi hoặc không xác định → coi như ĐANG BẬT.
Bật kill switch **không** huỷ approval đã có — chỉ chặn dispatch.

---

# 11. Observability

Metric bắt buộc (Prometheus format tại `/metrics`, chỉ mạng nội bộ):

```
growth_slot_runway_days                    gauge
growth_packages_pending_approval           gauge
growth_publications_by_state{state}        gauge
growth_write_outcome_total{outcome}        counter   # SUCCESS/FAILED/UNKNOWN
growth_publications_unknown_open           gauge     # ⚠️ >0 quá 1h → alert P1
growth_job_dead_letter_total               counter
growth_reconcile_lag_seconds               histogram
growth_kill_switch_active{scope}           gauge
growth_budget_remaining_vnd                gauge
```

SLO khởi điểm: duplicate publication = **0** (hard); `UNKNOWN` tồn đọng > 1h = 0; approval→dispatch p95 < 10 phút sau khi duyệt; job dead-letter < 1/tuần.

---

# 12. Concurrency

## 12.1. Single-writer

Worker chạy **đúng 1 replica**. Đây là ràng buộc kiến trúc, không phải cấu hình tuỳ chọn — ghi vào `docker-compose.yml` với comment giải thích, để không ai scale lên 2 mà không hiểu hậu quả.

## 12.2. Chống double-click / replay

- Approval decision: UNIQUE trên `(approval_request_id)` — quyết định đầu tiên thắng, lần sau trả về quyết định cũ, không lỗi.
- Dispatch: UNIQUE trên `(tenant_id, idempotency_key)`.
- Make callback: UNIQUE trên `(provider_event_id)` — callback trùng bị bỏ qua im lặng nhưng vẫn ghi audit.

---

# 13. Testing Strategy

## 13.1. Architecture fitness test ⚠️ QUAN TRỌNG NHẤT

```python
# tests/architecture/test_layer_boundaries.py
# AI AGENT: file này bảo vệ toàn bộ kiến trúc. KHÔNG được sửa để làm test xanh.
# Nếu test này fail, hãy sửa code vi phạm, không sửa test.

FORBIDDEN = {
    "growth_core.domain":      ["growth_core.application", "growth_core.adapters",
                                "growth_core.composition", "sqlalchemy", "fastapi",
                                "httpx", "requests", "pydantic"],
    "growth_core.application": ["growth_core.adapters", "growth_core.composition",
                                "sqlalchemy", "fastapi", "httpx"],
    "growth_core.adapters":    ["growth_core.composition"],
}
# Thêm: growth_core.{domain,application} KHÔNG được import
# knowledge_studio | validator_studio | content_studio | publishing_gateway
# (chỉ adapters/driven/studio/ được phép)
```

Cài bằng `ast.parse` trên toàn bộ file `.py`, hoặc `import-linter`. Chạy **đầu tiên** trong CI.

## 13.2. Các tầng test

| Tầng | Phạm vi | Ràng buộc |
|---|---|---|
| Unit — domain | state machine, policy, hash, key | thuần, không fixture, chạy < 1s |
| Unit — application | use case với fake port in-memory | 0 DB, 0 HTTP |
| Contract | JSON Schema Hermes, payload Make, response Meta | pinned fixture, fail khi schema đổi |
| Integration | SQLite thật + FastAPI TestClient + provider fake | 0 real API |
| Migration | import `publication_registry.json` + `growth.db` thật → parity | so từng dòng, sai lệch = fail |
| Chaos | kill worker giữa dispatch, callback trùng, clock skew, DB lock | phải không sinh duplicate |
| E2E production-like | 1 slot đi hết vòng đời với Make sandbox | chạy tay ở U5, có evidence |

Bất biến: `pytest` không kèm flag → **0 real API call**. Real call chỉ qua marker tường minh `@pytest.mark.live` và biến môi trường riêng.

---

# 14. Phase Plan

## 14.1. ⚡ Phase V0 — Value Unblock (LÀM TRƯỚC TIÊN, độc lập migration)

**Vì sao trước:** hai lỗi dưới đang chặn toàn bộ vòng phản hồi. Không sửa thì mọi phase sau đều không đo được kết quả. Cả hai không phụ thuộc Ubuntu/Core API.

| Task | Nội dung | Allowed files | DoD |
|---|---|---|---|
| **V0-01** | Sửa mapping Webhook Response trong scenario Make để Facebook trả `platform_post_id` thật. Kiểm tra bằng 1 bài thật. | Make scenario (ngoài repo) + `publishing_gateway/callback_receiver.py` | 1 bài FB đạt `PUBLISHED` với post ID + permalink hợp lệ |
| **V0-02** | Viết `MetaInsightsClient` thật (Graph API, **read-only**, chỉ Page/IG sở hữu). Bật `real_meta_insights_enabled` không còn raise `RuntimeError`. | `analytics_feedback/adapters/meta_insights.py` + test | Thu được reach/impression/engagement thật cho ≥ 3 bài đã đăng |
| **V0-03** | Panel so sánh bài trên `venho-os`: reach / engagement / lưu / bình luận, cắt theo pillar, thứ trong tuần, loại media | `venho-os` PublishingSection | Nhìn được bài nào hiệu quả mà không cần mở Business Suite |

**Ước tính:** 4–6 ngày. **Không bắt đầu U0 trước khi V0 xong.**

## 14.2. Phase U0–U8

| Phase | Mục tiêu | DoD then chốt |
|---|---|---|
| **U0** Baseline & Freeze | Biết chính xác hệ thống hiện tại | Tag release; export + hash registry/growth.db/flags/policies; chạy full test; liệt kê **mọi** scheduler có thể publish; định nghĩa rollback tag |
| **U1** Ubuntu Runtime | Chạy **cùng code** trên Ubuntu, chưa đổi authority | `venho-growth`/`venho-trend`/`venho-rollout` chạy được ở chế độ shadow; **0 production dispatch** từ Ubuntu; full test pass trên Ubuntu |
| **U2** State Consolidation | Hợp nhất JSON + SQLite + rotation → 1 SQLite có schema, sau `repository ports` | Import parity 100% dòng; architecture fitness test pass; **chưa** có publish path |
| **U3** Core API + n8n shadow | API + scheduler chạy song song, chỉ quan sát | 7 ngày shadow, 0 job trùng; lệch lịch trong ngưỡng; alert Telegram đã dedupe |
| **U4** Approval Cutover | Approval authority → Core API; duyệt từ điện thoại | Đổi 1 ký tự → approval cũ vô hiệu; double-click → 1 quyết định; restart n8n → approval còn nguyên; **0** lời gọi Make trực tiếp từ UI |
| **U5** Publishing Cutover | Ubuntu thành authority dispatch | Kill switch → freeze GH workflow → import delta → 1 canary → verify post ID + permalink → 3 slot có kiểm soát → 7 ngày canary. **0 duplicate, 0 unapproved write** |
| **U6** Research/Trend | Chuyển lịch research sang Ubuntu | Chống trùng trend pass; category bị chặn không bao giờ vào hàng duyệt; event hết hạn làm package phụ thuộc vô hiệu |
| **U7** Analytics loop | Nối V0-02 vào vòng học | ≥1 publication truy vết được tới metric snapshot; thiếu dữ liệu là `unknown`, **không phải** 0; recommendation chỉ advisory |
| **U8** Ops Hardening | Backup, restore, remote UI, runbook | Restore test có evidence thật; không có route admin public; xem được vòng đời từ approval tới receipt |

**Critical path:** `V0 → U0 → U1 → U2 → U3 → U4 → U5`. `U6` nhánh song song sau U5. `U7 → U8` sau U5.

## 14.3. Xử lý `growth_orchestrator/` cũ

Không xoá trong v4.1. Sau U5, đánh dấu deprecated bằng comment đầu file, chuyển caller sang `growth_core`. Xoá ở một task dọn dẹp riêng sau khi U5 canary ổn định 4 tuần — **không** gộp việc xoá vào task migration.

## 14.4. Deferred — có tên, có điều kiện

| Hạng mục | Điều kiện mở lại |
|---|---|
| **PostgreSQL migration** | §7.4 |
| **Video/Reels publishing** | Sau khi thử 3 tuần đăng Reels thủ công và có số liệu reach chứng minh. Khi đó cần: `media_artifacts.media_type='video'`, upload path, thumbnail, aspect ratio, và **mở rộng capability của M07** (không viết adapter mới bên ngoài M07). **Từ giờ: cấm hard-code giả định "1 package = 1 ảnh" trong `domain/`** |
| **Attribution events** | Khi có nguồn sự kiện thật (GA4 credential hoặc booking-form feed). Hiện chưa có bài nào mang link UTM |
| **Inbound comment/mention listening** | Việc riêng, không thuộc plan này |

---

# 15. Acceptance Gates

| Gate | Sau phase | Điều kiện PASS |
|---|---|---|
| **G0** Runtime | U1 | Full test pass trên Ubuntu; 0 dispatch production; health endpoint xanh 48h |
| **G1** State parity | U2 | Import lại state cũ → khớp 100%; architecture fitness test pass |
| **G2** Approval | U4 | Đổi 1 ký tự → approval vô hiệu (test tự động); replay/double-click → 1 quyết định; approval sống sót qua restart |
| **G3** Shadow scheduler | U3 | 7 ngày, 0 job trùng, 0 alert lặp |
| **G4** Controlled write | U5 | 1 canary có post ID + permalink thật; kill switch chặn được thật; reconciliation xử lý đúng 1 ca `UNKNOWN` mô phỏng |
| **G5** Production soak | U5+7d | 0 duplicate; 0 unapproved write; 0 `UNKNOWN` tồn > 1h; restore test có evidence |

> **AI AGENT:** Không được tuyên bố phase PASS nếu chưa có evidence tương ứng (log, artifact, test output) lưu trong `artifacts/`. Ghi kết quả vào `task_status.md` với ngày + commit hash.

---

# 16. Rollback

**Trước U5:** GitHub Actions vẫn là production authority. Rollback = tắt container Ubuntu. Rủi ro ~0.

**Rollback U5:**
```
1. Bật GLOBAL kill switch.
2. Đặt runtime_authority=github.
3. Bỏ freeze GitHub production workflows.
4. Export delta state từ SQLite → registry JSON theo định dạng cũ.
5. Xác nhận không có publication nào ở trạng thái DISPATCHING treo.
6. Ghi incident vào task_status.md.
```
Điều kiện tiên quyết: script export ngược (bước 4) phải **viết và test ở U2**, không phải viết lúc sự cố.

---

# 17. Risks

| # | Rủi ro | Mức | Giảm thiểu |
|---|---|---|---|
| 1 | Đăng trùng khi cutover | ⛔ Cao | Idempotency key + UNIQUE constraint + kill switch trước cutover + freeze GH workflow là **bước bắt buộc trước** import delta |
| 2 | AI agent phá layer boundary | ⚠️ Cao | Architecture fitness test chạy đầu tiên trong CI; `Allowed files` trong mỗi task |
| 3 | Split-brain giữa GH Actions và Ubuntu | ⛔ Cao | Không chạy song song production. `runtime_authority` là một giá trị duy nhất trong DB, đọc fail-closed |
| 4 | `UNKNOWN` bị retry mù → đăng 2 lần | ⛔ Cao | §8.6 là invariant; có chaos test riêng |
| 5 | n8n thành nơi chứa logic ngầm | ⚠️ TB | §9.4 giới hạn 3 loại node; review workflow JSON trong PR |
| 6 | Hermes bị prompt injection từ nội dung web | ⚠️ TB | §9.3 boundary + Hermes không giữ credential ghi |
| 7 | Scope creep sang Postgres/video giữa chừng | ⚠️ TB | §14.4 đã đặt tên và điều kiện — mọi đề xuất mở lại phải viện dẫn điều kiện |
| 8 | Backup có nhưng restore chưa từng chạy | ⚠️ TB | G5 yêu cầu evidence restore thật, không chấp nhận "script đã viết" |

---

# 18. AI Coding Handoff Protocol

## 18.1. Mẫu task card

Mỗi task giao cho AI agent phải có front-matter dưới đây. Task thiếu `allowed_files` hoặc `verification` **không được bắt đầu**.

```yaml
task_id:      U2-03
phase:        U2
objective:    "Cài SlotRepository trên SQLite, khớp port đã định nghĩa"
authority:    "plan v4.1 §4 file tree, §7 persistence, §8.1 slot id"
allowed_files:
  - growth_core/adapters/driven/persistence/repositories/slot_repository.py
  - growth_core/adapters/driven/persistence/models.py
  - growth_core/adapters/driven/persistence/mappers.py
  - tests/growth_core/adapters/test_slot_repository.py
forbidden_files:
  - growth_core/domain/**          # task này không được sửa domain
  - publishing_gateway/**          # M07 không thuộc phạm vi
input_contract:   "SlotRepo Protocol trong application/ports/repositories.py"
output_contract:  "Trả về domain entity PublishingSlot, không phải ORM model"
idempotency:      "save() theo slot_id deterministic — gọi 2 lần không tạo 2 dòng"
concurrency:      "UPDATE ... WHERE version_no = ? ; rowcount 0 → ConcurrencyConflict"
failure_semantics: "Lỗi DB → raise PersistenceError, KHÔNG nuốt exception"
acceptance_tests:
  - "save() rồi get() trả về entity tương đương"
  - "save() 2 lần cùng slot_id → 1 dòng"
  - "update với version_no cũ → ConcurrencyConflict"
verification:     "pytest tests/architecture tests/growth_core/adapters -q"
rollback:         "git revert; bảng chưa có consumer production ở U2"
docs_update:      "task_status.md: thêm dòng U2-03 + commit hash"
```

## 18.2. Quy tắc bắt buộc cho AI agent

1. Đọc `CLAUDE.md` + `task_memory.md` + `task_status.md` trước khi sửa.
2. Không đổi ownership M03/M07.
3. Không tạo publish path thứ hai.
4. Không viết SQL mutation business state từ n8n.
5. Không gọi real API trong `pytest`.
6. Mọi mutation phải nêu rõ idempotency + concurrency rule.
7. Mọi external write phải phân loại `SUCCESS/FAILED/UNKNOWN`.
8. Không tuyên bố PASS khi chưa có evidence.
9. **Không hạ gate/sửa test kiến trúc để làm CI xanh.**
10. Một task không vượt quá một ownership boundary, trừ khi là integration task được khai báo tường minh.
11. Nếu phát hiện tài liệu này mâu thuẫn với code hiện tại → **dừng, báo cáo**, không tự chọn bên.

---

# 19. Vị trí kỹ thuật cuối cùng

> Growth Agent v3.1 giữ nguyên **domain intelligence** và **guardrails**.
> v4.1 thay **runtime authority** bằng Ubuntu Control Plane 24/7 gồm Core API (Clean Architecture) + SQLite (WAL, single-writer, sau repository ports) + n8n (driving adapter thay thế được) + Hermes (chỉ research/classify), migration theo shadow/canary để không tạo split-brain hay đăng trùng.
> PostgreSQL và video/Reels được **hoãn có tên và có điều kiện kích hoạt**, không bị xoá khỏi tầm nhìn.

```text
Hermes            nghiên cứu + phân loại
n8n               kích hoạt (thay thế được bằng scheduler nội bộ)
Core API          cưỡng chế state / policy / approval / idempotency
SQLite            operational source of truth
VENHO AI Studio   sở hữu Growth domain
M03               kiểm định
Human             phê duyệt
M07               quyết định publishing eligibility
Make              adapter giao hàng
Receipt           xác nhận kết quả thật
```
