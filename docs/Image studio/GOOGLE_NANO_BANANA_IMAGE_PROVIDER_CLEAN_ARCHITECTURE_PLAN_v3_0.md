# GOOGLE NANO BANANA IMAGE PROVIDER — VENHO OS CLEAN ARCHITECTURE PLAN v3.0

| Field | Value |
|---|---|
| **Project** | VENHO OS / Creative Studio — Image Generation Provider Layer |
| **Business scope** | Linh An AI KOL identity assets + Ven Hồ Hotel visual production |
| **Document type** | Technical Specification, Implementation Plan & Machine-Executable Roadmap |
| **Version** | 3.0 |
| **Date** | 2026-08-10 |
| **Supersedes** | `GOOGLE_NANO_BANANA_IMAGE_PROVIDER_CLEAN_ARCHITECTURE_PLAN_v2_1.md`, `venho-os/docs/GOOGLE_GEMINI_IMAGE_PROVIDER_IMPLEMENTATION.md` |
| **Status** | READY FOR IMPLEMENTATION — NO CODE CHANGE EXECUTED, NO PAID API CALL AUTHORIZED |
| **Primary repo** | `venho-os` (Next.js 16 App Router, `/os`) |
| **Secondary repo (read-only for this task)** | `venho-ai-studio` (Python, M01–M09) |
| **Primary goal** | Add Google Nano Banana image generation as a **selectable, server-controlled provider** behind a Clean Architecture seam, without changing the generation protocol, Validator Studio, immutable artifact contract, or the human official-promotion gate. |
| **Secondary goal** | Reduce **cost per accepted asset** and give Linh An identity generation a second chance at crossing the Face QC ≥ 90 gate that the current OpenAI path has not yet crossed. |

---

# PART 0 — ORIENTATION

## 0.1 Tóm tắt cho Harry (tiếng Việt — phần duy nhất dành cho người, không dành cho AI agent)

### 0.1.1 Vấn đề thật đang giải

Có **hai** vấn đề, và v2.1 mới chỉ nói rõ một:

1. **Chi phí.** `gpt-image-2` ở tier chất lượng cao tốn khoảng **$0.211/ảnh** (1024×1024, quality `high`). Nano Banana 2 ở 1K tốn **$0.067/ảnh** → rẻ hơn khoảng **3,1 lần**. Nhưng nếu hiện tại Venho OS đang gọi `gpt-image-2` ở tier `medium` (~$0.053/ảnh) thì Nano Banana 2 **đắt hơn**, không rẻ hơn. → **Việc đầu tiên phải làm không phải là viết code, mà là xác định chính xác quality tier hiện tại trong `generate_image.py`.** Xem §3.
2. **Chất lượng chưa qua cổng.** Theo `task_status.md`, Face QC live hiện tại là **84,03–88,8**, chưa chạm ngưỡng official **≥ 90**. Nghĩa là số ảnh đạt full-gate của OpenAI hiện tại đang là **0**. Điều này làm hỏng tiêu chí so sánh của v2.1 ("chi phí trên mỗi ảnh đạt cổng phải thấp hơn OpenAI") — chia cho 0. v3.0 sửa lại luật quyết định này ở §35.6.

### 0.1.2 Ba con số cần nhớ

| Model | 1K | 2K | 4K |
|---|---:|---:|---:|
| Nano Banana 2 Lite (`gemini-3.1-flash-lite-image`) | $0,0336 | — | — |
| Nano Banana 2 (`gemini-3.1-flash-image`) | $0,067 | $0,101 | $0,151 |
| Nano Banana Pro (`gemini-3-pro-image`) | $0,134 | **$0,134** | $0,240 |

> **Luật tiết kiệm số 1:** Pro tính giá 1K và 2K **bằng nhau**. Nếu đã chọn Pro thì không bao giờ được yêu cầu 1K — luôn yêu cầu 2K. Đây là nâng cấp miễn phí. Đã đưa thành rule cứng trong registry ở §14.4.

### 0.1.3 Những gì v3.0 sửa so với v2.1 (5 điểm nặng nhất)

| # | v2.1 nói | Thực tế trong repo | v3.0 sửa |
|---|---|---|---|
| 1 | Use case chạy **đồng bộ** trong route handler | `venho-os` đã có **durable file-backed job store** (`queued→generating→validating→succeeded/failed/cancelled`, `/api/v1/studio/jobs`, có cancel + history) | Provider chạy **bên trong job worker**, không phải trong HTTP handler. §13, §18 |
| 2 | "Manifest v2 extension" | Manifest hiện tại đã là **`schemaVersion: 1.1`** | Bump lên **1.2**, thêm block `generation` cộng dồn. §19 |
| 3 | Không có trần chi tiêu | `venho-ai-studio` đã có `shared/budget/BudgetLedger` + cảnh báo 70/85/100% | Thêm **Budget Guard** phía `venho-os`, cùng contract. §28.2 |
| 4 | Chỉ kiểm tra "ảnh trả về có > 0 byte" | Gemini có lỗi đã ghi nhận: **bỏ qua `aspect_ratio`/`image_size`** và trả về tỉ lệ mặc định | Bắt buộc **verify kích thước thật** sau khi sinh; lệch → fail closed. §23.5 |
| 5 | So sánh pass-rate với ngưỡng 10 điểm % | n=18 không phân giải nổi 10 điểm %, và baseline OpenAI đang có 0 ảnh đạt cổng | Luật quyết định mới, có khoảng tin cậy Wilson và nhánh xử lý baseline = 0. §35.6 |

### 0.1.4 Việc Harry phải quyết trước khi agent code (không được để agent tự đoán)

Xem đầy đủ ở **§7 Open Decisions**. Tóm tắt: OD-1 quality tier hiện tại của `gpt-image-2`; OD-2 trần chi tiêu ngày (đề xuất $5); OD-3 vị trí thư mục module trong `venho-os`; OD-4 có bật `nano-banana-2-lite` trong lần này hay để Phase sau; OD-5 ngân sách cho phép của Stage A + Stage B (ước tính $1,31 + $7,72 ở §3.4).

### 0.1.5 Cách dùng file này

Nạp nguyên file vào Claude Extension trong VS Code, rồi ra lệnh:

```text
Read this plan completely. Execute PHASE 0 only (§39, task NB-P0-*).
Do not write any application code in Phase 0. Report the Discovery Inventory
in the exact format of §39.2 and STOP.
```

Sau mỗi phase, agent phải dừng và báo cáo theo §32.5. Không phase nào được tự nhảy sang phase sau.

---

## 0.2 Document contract — how an implementation agent must use this file

This document is the **single source of truth** for this change. It is written to be executed, not admired.

```text
RULE 0.2.1  This document supersedes v2.1 and the older handoff doc.
            If a statement here conflicts with an older VENHO document,
            this document wins for the image-provider scope ONLY.
            It does NOT override L4/L5/L6 OS governance or CLAUDE.md.

RULE 0.2.2  Sections marked [LOCKED] are decisions. Do not renegotiate them
            in code. If a LOCKED decision appears wrong during implementation,
            STOP and raise a Change Request (§6.4). Do not silently deviate.

RULE 0.2.3  Sections marked [VERIFY] contain external facts with a snapshot
            date. Re-verify against the live vendor docs before writing the
            code that depends on them. If reality differs, report the delta
            BEFORE coding, do not "adapt quietly".

RULE 0.2.4  Sections marked [DISCOVER] describe what the repository is
            assumed to contain. The agent must confirm the assumption against
            the real repository in Phase 0 and report any mismatch.

RULE 0.2.5  Any code block in this document is a CONTRACT SKETCH, not
            copy-paste-ready code. Names, imports and signatures must be
            adapted to the real repository and the real installed SDK types.
            Fidelity to the *contract* is mandatory; fidelity to the
            *characters* is not.

RULE 0.2.6  No paid provider API call may be made until Phase 7, and only
            after explicit human authorization recorded in the conversation.
```

### 0.2.1 Reading order for an implementation agent

```text
1. §0.2  this contract
2. §4    locked invariants          <- what you may never break
3. §5    scope + module ownership   <- what you may never touch
4. §8    defect register            <- what v2.1 got wrong; do not reintroduce
5. §9–15 architecture               <- the shape you must build
6. §16–22 contracts                 <- the interfaces you must honour
7. §39   roadmap                    <- what to do first
8. Everything else on demand, by section reference.
```

---

## 0.3 Glossary

| Term | Meaning in this document |
|---|---|
| **Provider** | A source of generated image bytes. `openai`, `nano-banana-2`, `nano-banana-pro`, `nano-banana-2-lite`, `mock`. |
| **Generator ID / Provider ID** | The stable, user-facing, server-validated identifier. Never a vendor model string. |
| **Model ID** | The vendor's technical string (e.g. `gemini-3.1-flash-image`). **Server-side only.** Never accepted from a client. |
| **Attempt** | One paid (or mock) generation call. Immutable. Identified by `runId + variantId + attemptId`. |
| **Artifact** | The verified, hashed, atomically written image plus its sidecar files inside the attempt directory. |
| **Manifest** | The JSON audit record of an attempt. Currently `schemaVersion 1.1`, becomes `1.2` in this change. |
| **Lane** | `identity` (static pose, standing face reference permitted) vs `action` (dynamic pose, text-to-image forced). Existing VENHO concept — unchanged here. |
| **Full-gate pass** | An attempt that satisfies every existing pre-human official-candidate condition, including Face QC ≥ 90. Not a human approval. |
| **Official** | A human-promoted asset. Only a human action creates this. No code path in this change may produce it. |
| **Aspect preset** | `portrait` / `square` / `story` — a VENHO UI concept. |
| **Aspect ratio** | `2:3` / `1:1` / `9:16` — the vendor wire value. |
| **Image size tier** | `512` / `1K` / `2K` / `4K` — the vendor wire value for output resolution. |
| **Breakpoint #1** | The VENHO "external breakpoint" for image generation (Flow / GPT Image). This change narrows it, it does not close it — Google Flow remains manual and out of pipeline. |

---

## 0.4 Related documents and supersession

```text
SUPERSEDED BY THIS FILE (mark them as historical, do not delete)
  GOOGLE_NANO_BANANA_IMAGE_PROVIDER_CLEAN_ARCHITECTURE_PLAN_v2_1.md
  venho-os/docs/GOOGLE_GEMINI_IMAGE_PROVIDER_IMPLEMENTATION.md

STILL AUTHORITATIVE, THIS FILE DEFERS TO THEM
  venho-ai-studio/CLAUDE.md                       (test discipline, ownership)
  VENHO L4 Execution OS v1.1                      (task lifecycle, TASKS.md)
  VENHO L5 Production OS v1.2                     (output registry, promotion)
  VENHO_GROWTH_AGENT_MASTER_PLAN_v3_1_CONSOLIDATED (GR-D2 provider decision)
  Linh An Character Bible 07A–07F                 (identity + QC rubric)
  Visual DNA v2.7                                 (scenario/subject profiles)

TO BE CREATED BY THIS CHANGE
  venho-os/docs/studio/image-generation/ADR-IMG-001..007.md
  venho-os/docs/studio/image-generation/BENCHMARK_PROTOCOL.md
  venho-os/docs/studio/image-generation/RUNBOOK.md
```

> **L5 Production OS note.** This document is an L0–L6 governance artifact and is therefore exempt from the Output Registry promotion gates, per L5 v1.2 §governance exemption. The **benchmark reports** it produces are NOT exempt and must be registered in `PRODUCTION_REGISTRY.md` as Tier-1 internal outputs.

---

# PART I — DECISIONS

# 1. EXECUTIVE DECISION

## 1.1 Decision [LOCKED]

Add Google Gemini native image generation as an **additional image-generation provider** behind a server-side provider abstraction inside `venho-os`.

```text
Public provider IDs accepted at the HTTP boundary:
  openai
  nano-banana-2
  nano-banana-pro
  nano-banana-2-lite        (behind its own flag; see OD-4)

Internal-only provider IDs (never accepted from a browser):
  mock
```

Server-controlled mapping (the only place this mapping may exist — §14.3):

```text
openai              -> the OpenAI image model currently configured in generate_image.py
nano-banana-2       -> gemini-3.1-flash-image
nano-banana-pro     -> gemini-3-pro-image
nano-banana-2-lite  -> gemini-3.1-flash-lite-image
mock                -> mock-image-v1 (deterministic fixture, zero cost)
```

Google Flow remains a **manual creative tool** and is **not** a production backend. It must never bypass the
`generation → artifact → manifest → validator → human review` pipeline. This preserves VENHO External Breakpoint #1 semantics.

## 1.2 Default rollout rule [LOCKED]

```bash
IMAGE_GENERATION_DEFAULT_PROVIDER=openai
```

The default provider does **not** change until the Stage B decision benchmark passes §35.6. After that, changing the default is a **configuration change on the server**, never a browser-side model-ID change and never a code edit in more than one place.

## 1.3 Model roles [LOCKED]

| Use case | Provider ID | Model ID | Role |
|---|---|---|---|
| Linh An identity / lifestyle default | `nano-banana-2` | `gemini-3.1-flash-image` | Primary Google candidate: best quality-per-dollar with multi-reference character handling |
| Linh An difficult identity, complex reference, near-official candidate | `nano-banana-pro` | `gemini-3-pro-image` | Premium escalation only |
| Ven Hồ Hotel simple, high-volume, **non-character** creatives | `nano-banana-2-lite` | `gemini-3.1-flash-lite-image` | Efficiency lane, 1K only |
| Baseline / control / rollback | `openai` | current mapping | Compatibility + benchmark control |
| Automated tests | `mock` | `mock-image-v1` | Zero-cost determinism |

### 1.3.1 Model selection rules [LOCKED]

```text
RULE 1.3.1a  Linh An identity lane starts at nano-banana-2. Never at Lite.
             Lite is not positioned by the vendor for multi-reference
             character consistency and caps at 1K output.

RULE 1.3.1b  nano-banana-pro is an ESCALATION, not a default. It may be used
             when the same frozen prompt/reference conditions demonstrate
             materially better QC on the same scenario.

RULE 1.3.1c  If nano-banana-pro is selected, imageSize MUST be 2K, never 1K.
             1K and 2K cost the same on Pro. Requesting 1K is pure waste.
             Enforce in the registry preflight, not in the UI only.

RULE 1.3.1d  Do NOT introduce gemini-2.5-flash-image. It is the legacy
             Nano Banana model and is scheduled for retirement.

RULE 1.3.1e  Never route every image to Pro "to be safe". That inverts the
             entire cost objective of this change.
```

## 1.4 What this change is NOT

```text
It is NOT a validator change.
It is NOT a prompt-engineering change.
It is NOT a DNA change.
It is NOT a publishing change.
It is NOT an official-asset promotion.
It is NOT a migration of the Python image_studio_runtime.
It is NOT a rewrite of Creative Studio.
```

---

# 2. VERIFIED EXTERNAL FACTS — SNAPSHOT 2026-08-10 [VERIFY]

> Every fact in this section was verified on 2026-08-10 against public vendor documentation. Vendor behaviour changes. **Re-verify §2.2, §2.3 and §2.5 before writing the Gemini adapter (Phase 3) and before the Stage A benchmark (Phase 7).** Record the re-verification result in the phase report.

## 2.1 Naming — Nano Banana IS the Gemini image model family [LOCKED]

```text
Nano Banana 2 Lite  -> Gemini 3.1 Flash Lite Image -> gemini-3.1-flash-lite-image
Nano Banana 2       -> Gemini 3.1 Flash Image      -> gemini-3.1-flash-image
Nano Banana Pro     -> Gemini 3 Pro Image          -> gemini-3-pro-image
Nano Banana         -> Gemini 2.5 Flash Image      -> gemini-2.5-flash-image  (legacy, retiring)
```

There is no separate "Nano Banana 2 API" sitting above Gemini Flash. Product name and technical model ID are two labels for one model. Therefore:

```text
UI + HTTP boundary  = Nano Banana product name (semantic, stable)
server registry     = Google technical model ID (may change, single source)
transport           = Gemini API via @google/genai
```

> **Preview-suffix trap.** Earlier releases of these models carried a `-preview` suffix (e.g. `gemini-3.1-flash-image-preview`, `gemini-3-pro-image-preview`). Current documentation uses the un-suffixed IDs. **The agent must confirm which ID the installed SDK + the project's API key actually accept, and put the confirmed string in exactly one place (§14.3).** A wrong model string produces a 404-class failure, not a silent fallback — fail loudly and report.

## 2.2 API surface — Interactions API [VERIFY]

The Interactions API is Google's current primary interface for Gemini models and is the documented path for image generation. `generateContent` still exists but is the legacy surface.

**Confirmed JavaScript request shape:**

```ts
// VERIFIED SHAPE, 2026-08-10. Field names are snake_case even in JavaScript.
const interaction = await ai.interactions.create({
  model: "gemini-3.1-flash-image",
  input: [ /* text and image parts */ ],
  response_format: {
    type: "image",
    mime_type: "image/png",
    aspect_ratio: "2:3",
    image_size: "2K",
  },
  store: false,
});

const base64 = interaction.output_image.data;
```

```text
CRITICAL DX NOTE — DO NOT GET THIS WRONG
  Interactions API (ai.interactions.create)  -> snake_case:  response_format, mime_type,
                                                aspect_ratio, image_size, previous_interaction_id
  Legacy generateContent / chat.sendMessage  -> camelCase:  responseFormat, mimeType,
                                                aspectRatio, imageSize, inlineData

  Mixing the two conventions is the single most likely cause of "the model
  ignored my aspect ratio" bugs. Always follow the INSTALLED SDK's TypeScript
  types. If tsc accepts a camelCase key on interactions.create, stop and
  re-read the SDK typings before assuming it works.
```

## 2.3 Supported wire values [VERIFY]

```text
aspect_ratio (documented set):
  "1:1" "1:4" "1:8" "2:3" "3:2" "3:4" "4:1" "4:3" "4:5" "5:4" "8:1" "9:16" "16:9" "21:9"

image_size (documented set):
  "512"  "1K"  "2K"  "4K"

  NOTE: the smallest tier's wire value is the string "512", NOT "0.5K".
        v2.1 called it 0.5K in the price table. Corrected here (defect D-14).
        VENHO does not use 512 in v3.0 — it is documented only so that nobody
        invents "0.5K" and gets a 400.
```

All three VENHO presets are supported: `portrait → 2:3`, `square → 1:1`, `story → 9:16`.

## 2.4 Known vendor defect — output geometry may not honour the request [VERIFY]

There are reproducible public developer reports of Gemini image models ignoring `aspect_ratio` / `image_size` and returning the model's default geometry instead. This is a **cost-bearing correctness risk**: you pay for an image that does not match the requested contract, and the benchmark becomes invalid because the independent variable silently changed.

```text
MANDATORY MITIGATION (new in v3.0, defect D-04)
  After decoding the returned bytes, the application layer MUST measure the
  real pixel dimensions and compare them against the requested aspect ratio
  and size tier.
    - mismatch  -> IMAGE_GENERATION_GEOMETRY_MISMATCH, artifact still written
                   (it was paid for), manifest records requested vs actual,
                   attempt is marked NOT eligible for benchmark aggregation.
    - never silently accept, never silently resize, never silently retry.
  See §23.5 for the tolerance table.
```

## 2.5 Storage, provenance, grounding [VERIFY]

```text
store=false        Opts out of provider-side interaction retention.
                   Consequence: previous_interaction_id and background=true
                   become unavailable. This is intentional for VENHO — we
                   keep our own immutable manifest trail. [LOCKED]

retention          With store=true, paid tier retains interactions ~55 days,
                   free tier ~1 day. VENHO does not rely on this.

SynthID            Gemini image output carries an invisible SynthID watermark.
                   Record it as an EXPECTATION, never as a verified fact
                   (§19.4). Never attempt to remove or alter it. [LOCKED]

Google Search      Grounding tools are NOT used by VENHO for image generation
grounding          (§23.4). Additionally, grounding is documented as NOT
                   SUPPORTED on gemini-3.1-flash-lite-image at all.

Batch API          Not available on the Interactions API surface. A 50% batch
                   discount exists but only via the legacy generateContent
                   batch path. Deferred: see ADR-IMG-006.

Flex / Priority    The Interactions API exposes service tiers (Flex advertised
service tiers      at ~50% cost reduction). Applicability to image models is
                   NOT confirmed. Deferred: see ADR-IMG-007. Do NOT implement
                   speculatively in this change.
```

## 2.6 SDK and runtime [VERIFY / DISCOVER]

```text
SDK              @google/genai  (JavaScript / TypeScript)
Minimum version  >= 2.3.0 for Interactions API support
Do NOT add       @google/generative-ai  (the older, separate package)

The agent must:
  1. read the repository's package manager and lockfile;
  2. install a current stable @google/genai with Interactions support;
  3. pin per repository dependency policy;
  4. commit the lockfile;
  5. confirm only ONE Google generative-AI SDK exists in the tree.
```

---

# 3. COST MODEL AND BUSINESS CASE

> v2.1 asserted a cost benefit but never established the baseline it was being compared against. That is the largest analytical gap in v2.1 (defect D-01). This section fixes it.

## 3.1 How Google actually bills these models

Per-image prices are a rounding of token math:

```text
cost_output_usd = image_output_tokens * image_output_token_rate / 1e6

image output token rate:
  gemini-3.1-flash-lite-image   $30  per 1M image output tokens
  gemini-3.1-flash-image        $60  per 1M image output tokens
  gemini-3-pro-image            $120 per 1M image output tokens

image output tokens per image:
  Flash:  747 @512 · 1120 @1K · 1680 @2K · 2520 @4K
  Pro:    1120 @1K · 1120 @2K · 2000 @4K
  Lite:   1120 @1K
```

Input is billed separately and is small but not zero:

```text
Each reference image consumes ~1120 input image tokens.
Text prompt input is billed at the model family's text input rate.
Pro image additionally incurs variable "thinking" tokens at the text output rate.
```

## 3.2 Price snapshot 2026-08-10 [VERIFY]

| Provider ID | 512 | 1K | 2K | 4K |
|---|---:|---:|---:|---:|
| `nano-banana-2-lite` | — | **$0.0336** | — | — |
| `nano-banana-2` | $0.045 | **$0.067** | $0.101 | $0.151 |
| `nano-banana-pro` | — | $0.134 | **$0.134** | $0.240 |

## 3.3 The OpenAI baseline — MUST BE ESTABLISHED BEFORE ANY CLAIM [DISCOVER]

`gpt-image-2` is token-billed (approx. $8/M image input, $30/M image output, $5/M text input). The commonly quoted per-image figures at 1024×1024 are:

| gpt-image-2 quality tier | ≈ cost / image | vs `nano-banana-2` @1K ($0.067) |
|---|---:|---|
| `low` | ≈ $0.006 | Gemini is **~11× more expensive** |
| `medium` | ≈ $0.053 | Gemini is **~1.26× more expensive** |
| `high` | ≈ $0.211 | Gemini is **~3.1× cheaper** ✅ |

```text
CONSEQUENCE — THIS IS THE MOST IMPORTANT SENTENCE IN THIS DOCUMENT'S
BUSINESS CASE:

  The cost argument for Nano Banana is TRUE only if the current Linh An
  generation path calls gpt-image-2 at `high` quality.
  At `medium` it is FALSE and the change must be justified on QUALITY
  (crossing Face QC >= 90) rather than on cost.

  Phase 0 task NB-P0-T4 must read the actual quality/size parameters out of
  ops/VenHoSocialManager/generate_image.py and record them in the Discovery
  Inventory. Do not proceed to Phase 8 decision-making without this number.
  See OD-1.
```

## 3.4 Benchmark spend forecast (informational, not authorization)

Using Nano Banana list prices at 2K for identity work and 1K for the hotel lane:

| Stage | Composition | Images | Est. output spend |
|---|---|---:|---:|
| A — smoke | 6 scenarios × 1 × {NB2 @2K, NB Pro @2K} | 12 | ≈ $1.41 |
| B — decision | 6 scenarios × 3 × {NB2 @2K, OpenAI control} | 36 | ≈ $1.82 + OpenAI control |
| B — Pro escalation (targeted) | up to 6 × 1 @2K | 6 | ≈ $0.80 |
| C — hotel Lite lane | 6 × 2 × {Lite @1K, NB2 @1K} | 24 | ≈ $1.20 |

```text
These are OUTPUT-ONLY estimates. Add input/reference/thinking tokens and any
failed-but-billed attempts. Budget with a 1.5x safety factor.
Nothing in this table authorizes spending. Authorization is §34.2.
```

## 3.5 The real business metric [LOCKED]

```text
costPerFullGatePass = totalGenerationSpend / fullGatePassCount

if fullGatePassCount == 0:
    report "N/A — no full-gate pass in this window"
    NEVER divide by zero
    NEVER report Infinity as if it were a measured number
```

Choose the **cheapest model that passes the same VENHO gate**, not the cheapest model per generated image. For Linh An, identity consistency outranks per-image price. For non-character Ven Hồ assets, identity risk is absent so cost may be optimised more aggressively.

---

# 4. LOCKED VENHO INVARIANTS

These predate this change and are not negotiable within it.

## 4.1 Official quality gate [LOCKED]

```text
An asset becomes official only when ALL of these hold:
  Face QC >= 90
  every applicable validator approves
  no QC kill switch is raised
  human review is complete
  the explicit official-promotion action has been executed by a human

A generation provider cannot override, soften, or shortcut any of these.
```

## 4.2 Pipeline status is not human approval [LOCKED]

Statuses such as `generated`, `validated`, `approved`, `usable`, `needs_review`, `revise` are **pipeline** states. None of them means "official". Preserve the existing status vocabulary exactly; this change renames nothing.

> Context: `task_status.md` records live Face QC of 84.03–88.8 and explicitly forbids classifying existing `revise`/`usable` artifacts as official. That prohibition stands unchanged.

## 4.3 Identity lane vs action lane [LOCKED]

```text
identity lane (static poses)
  -> may use the approved standing face reference per current protocol

action lane (running, cycling, sitting, jumping, dancing, swimming, climbing…)
  -> standing face reference stays disabled; text-to-image is forced so the
     standing reference cannot corrupt body geometry
```

Do not modify lane logic to improve a Gemini benchmark score. That would invalidate the benchmark and corrupt the asset contract simultaneously.

## 4.4 Prompt lock [LOCKED]

Gemini receives the existing server-resolved `generationPrompt`, including the server-appended `linh_an_generation_protocol_v1`. It never receives the raw `userPrompt`.

```text
FORBIDDEN: any Gemini-specific prompt shortcut that bypasses
  DNA resolution · lane policy · outfit resolution ·
  environment resolution · generation protocol append
```

## 4.5 Validator independence [LOCKED]

Do not modify validator thresholds, prompts, reference sets, provider, or QC logic. Known validator entry points include `validate_generated.py` and `validate_intent.py`; any additional Face/Image-DNA validation path found in Phase 0 is equally frozen. The Face Validator contract (3 gates, 5 score keys, 0–100 scale) is untouched.

## 4.6 Immutable generation artifacts [LOCKED]

```text
NEVER overwrite attempt-NNN/image.png
NEVER reuse a run directory for a new paid request
NEVER replace a failed attempt with a later result
NEVER mutate an old manifest to make a new generation look like an old one

Every retry is a NEW attempt with a NEW attempt ID and a NEW directory.
```

## 4.7 No publishing, no promotion [LOCKED]

```text
This change must not publish to Facebook / Instagram / Threads / Zalo,
must not upload to an official CDN or library as an official asset,
and must not promote any generated asset to official automatically.
```

## 4.8 Test discipline [LOCKED]

```text
0 paid API calls in the automated test suite. Default provider in tests = mock.
This mirrors the existing repo-wide rule in CLAUDE.md and must not be relaxed
"just for one integration test".
```

---

# 5. SCOPE AND MODULE OWNERSHIP

## 5.1 In scope

- Google Gemini image-generation provider adapters (`nano-banana-2`, `nano-banana-pro`, optionally `nano-banana-2-lite`).
- Provider registry, descriptors, and single-source model mapping.
- Gemini credential and configuration handling, server-side only.
- Provider selection in the HTTP API, the durable job record, and the UI.
- Provider capabilities endpoint (server-owned catalog).
- Separation of aspect preset / aspect ratio / image size tier.
- Output geometry verification (new).
- Budget Guard with a daily spend cap and an append-only cost ledger (new).
- Additive manifest extension `1.1 → 1.2`.
- Provider-domain error taxonomy and sanitized HTTP mapping.
- Immutable + atomic artifact write where missing.
- Mock provider, unit/integration tests, zero live calls.
- Opt-in live smoke benchmark and a decision benchmark protocol.
- Rollback documentation and an operations runbook.

## 5.2 Out of scope [LOCKED]

```text
Rewriting Validator Studio                Changing Face QC thresholds
Retuning Linh An DNA                      Gemini-specific prompt engineering
Batch generation architecture             Flex/Priority service tiers
Google Search / Image Search grounding    Multi-turn Gemini editing
Gemini Files API optimisation             Automatic provider failover
Automatic paid retry                      Automatic official promotion
Social publishing                         Replacing the asset storage backend
Migrating the Python image_studio_runtime Renaming historical asset directories
Fixing unrelated pre-existing lint errors Refactoring the design-token WIP
```

## 5.3 Module ownership map — anti-duplication [LOCKED]

VENHO currently has **two** image-generation runtimes. Confusing them will create a duplicate architecture, which the VENHO anti-duplication principle forbids.

| Runtime | Repo | Purpose | Gemini in THIS change? |
|---|---|---|---|
| Creative Studio image generation | `venho-os` (TypeScript/Next.js) | Interactive, human-in-the-loop generation from the OS UI | **YES — this is the only target** |
| `image_studio_runtime` | `venho-ai-studio` (Python) | Automated Growth Agent pipeline generation | **NO — untouched. Follow-on task.** |

```text
RULE 5.3.1  This change modifies venho-os only.
RULE 5.3.2  venho-ai-studio is READ-ONLY for this task. Read it to learn
            contracts (BudgetLedger, manifest, validator). Do not edit it.
RULE 5.3.3  Do not port the Gemini adapter into Python in the same task.
            One module ownership boundary per task (CLAUDE.md rule 5).
RULE 5.3.4  When the venho-os provider is proven, a SEPARATE task may add
            the same provider behind image_studio_runtime's existing
            provider seam, reusing this document's contracts.
```

## 5.4 Known pre-existing failures — do not "fix" them [DISCOVER]

```text
npm run lint  is currently blocked by TWO pre-existing errors in
              venho-os/design_handoff_venho_os_cockpit/support.js

These are NOT caused by this change and are NOT in scope.
Report them as pre-existing in every phase report. Do not edit that file.
If lint output changes shape, report the delta rather than adapting silently.
```

---

# 6. DECISION RECORDS

Each decision is locked. Changing one requires a Change Request through L2 governance (§6.4), not a code edit.

| ID | Decision | Status | Rationale |
|---|---|---|---|
| **ADR-IMG-001** | Provider abstraction via a single `ImageGenerationProviderPort`; application layer never imports a vendor SDK | LOCKED | Interchangeable providers; benchmark validity; testability |
| **ADR-IMG-002** | Interactions API via `@google/genai` is the only production Gemini call path; raw REST is debugging-only | LOCKED | Two production paths double the mapping, error handling and telemetry surface |
| **ADR-IMG-003** | `store: false` on every Gemini request | LOCKED | VENHO's manifest is the canonical audit trail; minimise external retention; single-turn generation needs no server state |
| **ADR-IMG-004** | Zero automatic retries on a paid generation call | LOCKED | An ambiguous timeout can occur *after* the provider billed. A hidden retry creates duplicate cost, duplicate assets and ambiguous provenance |
| **ADR-IMG-005** | The provider returns bytes; the application layer owns persistence | LOCKED | A provider that writes canonical artifacts couples infrastructure to the asset contract and cannot be swapped |
| **ADR-IMG-006** | Batch API (50% discount) deferred | DEFERRED | Not available on the Interactions API surface; would require the legacy generateContent path and a second production integration. Revisit after Stage B, as a standalone ADR |
| **ADR-IMG-007** | Flex / Priority service tiers deferred | DEFERRED | Applicability to image models unconfirmed as of 2026-08-10; would add an uncontrolled variable to the benchmark |
| **ADR-IMG-008** | Provider work happens inside the existing durable job worker, not in the HTTP handler | LOCKED | `venho-os` already owns durable file-backed jobs with cancel/history; a second synchronous path would fork the execution model |
| **ADR-IMG-009** | A daily budget cap blocks paid generation before the provider call | LOCKED | Solo-founder cost exposure; mirrors the existing `BudgetLedger` policy in `venho-ai-studio` |

## 6.4 Change Request procedure

```text
IF an implementation reality contradicts a LOCKED decision:
  1. STOP implementing.
  2. Write CR-IMG-<nnn> stating: the decision, the observed reality,
     the options, the recommended option, and the blast radius.
  3. Report it to Harry and WAIT.
  4. Do not implement the workaround "temporarily".
```

---

# 7. OPEN DECISIONS — REQUIRE HARRY BEFORE OR DURING IMPLEMENTATION

| ID | Question | Blocks | Default if unanswered |
|---|---|---|---|
| **OD-1** | What quality tier / size does the current `gpt-image-2` call use? | Phase 8 decision, and the entire cost claim (§3.3) | Agent must READ it from the code in Phase 0 and report — no guessing |
| **OD-2** | Daily paid-generation budget cap in USD | Phase 1 (Budget Guard) | Implement with `IMAGE_GENERATION_DAILY_BUDGET_USD=5.00` and a hard block at 100% |
| **OD-3** | Module folder location in `venho-os` (`src/modules/…` vs the repo's existing convention) | Phase 1 | Follow the repo's dominant existing convention; never create a second architecture (§38.3) |
| **OD-4** | Ship `nano-banana-2-lite` now, or defer to a later task? | Phase 3 scope | Implement the adapter, ship it **disabled** behind `IMAGE_GENERATION_LITE_ENABLED=false` |
| **OD-5** | Authorized spend for Stage A and Stage B | Phase 7, Phase 8 | Blocked. No live call without an explicit number |
| **OD-6** | Should the Pro escalation be a manual UI choice, or a suggested route after a Flash failure? | Phase 5 UI | Manual choice only. No automatic escalation — automatic escalation is hidden spending |

---

# PART II — DEFECT REGISTER (REVIEW OF v2.1)

# 8. DEFECTS FOUND IN v2.1 AND CORRECTED IN v3.0

> This is the audit trail of the review. An implementation agent should read it to understand **why** certain rules exist, and to avoid reintroducing a corrected defect from an older copy of the plan.

| ID | Severity | Defect in v2.1 | Correction in v3.0 | Where |
|---|---|---|---|---|
| **D-01** | 🔴 Critical | The cost benefit was asserted without ever establishing the OpenAI baseline cost. At `gpt-image-2` medium quality, Nano Banana 2 is *more* expensive, not cheaper. | Full cost model with the baseline made an explicit Phase-0 discovery task and an Open Decision. | §3.3, OD-1 |
| **D-02** | 🔴 Critical | The use case is specified as a synchronous call inside the route handler. The repo already has a **durable file-backed job store** with `queued→generating→validating→succeeded/failed/cancelled`, status API, cancel and history. | Provider execution moved inside the job worker; job record extended with provider fields; cancel semantics defined. | §13, §18, ADR-IMG-008 |
| **D-03** | 🔴 Critical | Decision rule requires "cost per full-gate pass lower than OpenAI", but the current OpenAI baseline has **zero** full-gate passes (live Face QC 84.03–88.8 < 90). The rule divides by zero. | Rewritten decision rule with an explicit zero-baseline branch. | §35.6 |
| **D-04** | 🔴 Critical | Output validation checks only "bytes exist, dimensions > 0". Gemini has documented cases of ignoring `aspect_ratio` / `image_size`. A paid, geometrically wrong image would be accepted and would silently invalidate the benchmark. | Mandatory geometry verification with a tolerance table and a dedicated error code. | §2.4, §23.5 |
| **D-05** | 🟠 High | No spend cap anywhere. Concurrency 2 limits parallelism, not total spend. A loop bug could bill unbounded. | Budget Guard: preflight estimate + append-only cost ledger + daily cap + 70/85/100% alerts, mirroring `BudgetLedger`. | §28.2, §21 |
| **D-06** | 🟠 High | Manifest called a "v2 extension" while the live manifest is `schemaVersion 1.1`. Two numbering schemes would collide. | Additive bump to `schemaVersion 1.2` with a documented compatibility rule. | §19 |
| **D-07** | 🟠 High | `mock` appears in the same provider union as public providers, with only a prose rule that it "must not be accepted". A single missed check exposes it. | Two-tier enum: `PublicImageGenerationProviderId` at the HTTP boundary, `ImageGenerationProviderId` internally. Type system enforces it. | §11.1 |
| **D-08** | 🟠 High | Error code naming is inconsistent: §19.2 says `GENERATION_ATTEMPT_ALREADY_EXISTS`, §20 says `IMAGE_GENERATION_ATTEMPT_ALREADY_EXISTS`. | One canonical taxonomy, one prefix, one table. | §22 |
| **D-09** | 🟠 High | No statement about the Next.js route runtime. A route doing filesystem writes and `execFile` cannot run on the Edge runtime, and the default `maxDuration` will cut off a 4K Pro generation. | Explicit `runtime = "nodejs"` and `maxDuration` requirements, plus a timeout-vs-platform-limit rule. | §16.6 |
| **D-10** | 🟡 Medium | Pro pricing is listed (1K and 2K both $0.134) but the obvious consequence is never turned into a rule, so an agent could ship a Pro path that requests 1K and wastes half the resolution it already paid for. | Hard rule: Pro always requests 2K; enforced in registry preflight. | RULE 1.3.1c |
| **D-11** | 🟡 Medium | No composition root. Clean Architecture is described but nothing says where the object graph is assembled, so wiring would leak into the route. | Explicit composition root module with a single `buildImageGenerationModule()`. | §15 |
| **D-12** | 🟡 Medium | `references` appear in the domain command and in the security section, but the HTTP request contract never defines how a client names a reference. | `referenceAssetIds: string[]` defined in the request schema with resolution rules. | §16.2 |
| **D-13** | 🟡 Medium | `runId` / `variantId` / `attemptId` are required by the command but absent from the request contract; ownership of their generation is undefined. | Server owns all three. Client may supply an `idempotencyKey` only. | §16.3 |
| **D-14** | 🟡 Medium | Price table lists a "0.5K" tier; the API wire value is the string `"512"`. | Corrected, and documented as a trap. | §2.3 |
| **D-15** | 🟡 Medium | Stage B decision benchmark uses n=18 against a 10-percentage-point threshold. The resolution is 5.56 pts and the sampling error is far larger than the threshold. | Wilson score intervals reported; decision rule restated as a non-inferiority test with declared uncertainty. | §35.5 |
| **D-16** | 🟡 Medium | `estimatedTotalCostUsd` is left permanently `null` even though the vendor publishes exact token counts per image and per reference image. | Token-based total estimator with a documented formula; `actualCostUsd` still reserved for billing truth. | §21.2 |
| **D-17** | 🟡 Medium | Capabilities endpoint returns cost but not the supported sizes/ratios, so the UI cannot disable an unsupported combination and must learn by 400. | Capabilities response carries the full capability matrix; UI is capability-driven. | §17 |
| **D-18** | 🟡 Medium | The architecture diagram still says "Gemini Flash / Gemini Pro adapter" after the v2.1 rename, and omits Lite. | Diagrams regenerated with product naming and all adapters. | §10 |
| **D-19** | 🟢 Low | UI spec is English-only although the operator interface is Vietnamese. | Vietnamese copy strings supplied for every control and error. | §31.6 |
| **D-20** | 🟢 Low | Benchmark directory example uses a non-ISO historical folder name with no rule about which convention applies to new folders. | Explicit rule: preserve historical names, ISO-8601 for anything new. | §35.4 |
| **D-21** | 🟢 Low | No Definition of Ready — only a Definition of Done — so an agent could start Phase 1 without the Phase 0 inventory. | Definition of Ready added and made a Phase-1 precondition. | §37.1 |
| **D-22** | 🟢 Low | No risk register and no operations runbook for the period after cutover. | Both added. | §42, §43 |
| **D-23** | 🟢 Low | The plan does not declare the known pre-existing lint failures, so an agent may either "fix" unrelated files or misreport the build as broken by this change. | Declared explicitly as out of scope. | §5.4 |

## 8.1 What v2.1 got right and v3.0 preserves unchanged

Good architecture in v2.1 that must survive: the provider-does-not-persist rule; aspect/resolution separation; no hidden retries; server-owned model mapping; client cannot submit model IDs or paths; `store=false`; no grounding; the immutable attempt contract; the smoke-vs-decision benchmark split; the "provider is replaceable, the gate is not" framing. None of that is re-litigated here.

---

# PART III — ARCHITECTURE

# 9. CLEAN ARCHITECTURE BOUNDARIES

## 9.1 The dependency rule [LOCKED]

```text
        ┌──────────────────────────────────────────┐
        │  INTERFACE  (HTTP routes, React, CLI)    │  knows: application
        └───────────────────┬──────────────────────┘
                            │ depends on
        ┌───────────────────▼──────────────────────┐
        │  APPLICATION  (use cases, ports, services)│  knows: domain
        └───────────────────┬──────────────────────┘
                            │ depends on
        ┌───────────────────▼──────────────────────┐
        │  DOMAIN  (types, rules, errors, policy)   │  knows: nothing
        └───────────────────▲──────────────────────┘
                            │ implements ports
        ┌───────────────────┴──────────────────────┐
        │  INFRASTRUCTURE (Gemini, OpenAI, fs, job) │  knows: application+domain
        └──────────────────────────────────────────┘
```

Dependencies point **inward**. Infrastructure depends on the application's ports; the application never depends on infrastructure.

## 9.2 Forbidden imports [LOCKED]

```text
domain/**       must not import:  @google/genai, openai, next/*, node:fs,
                                  node:child_process, node:crypto,
                                  anything under infrastructure/

application/**  must not import:  @google/genai, openai, next/*,
                                  node:fs, node:child_process,
                                  anything under infrastructure/ or interface/

interface/**    must not import:  @google/genai, openai
                                  (it composes; it does not call vendors)

infrastructure/** MAY import domain + application ports. That is its job.
```

```text
ENFORCEMENT (do not rely on discipline alone)
  Add a lint rule or a dedicated architecture test that fails the build when a
  forbidden import appears. A test is preferable because it runs everywhere:
  tests/image-generation/architecture-boundaries.test.ts
  It reads the source files under the module and asserts the import graph.
  See §33.9.
```

## 9.3 Provider abstraction rule [LOCKED]

Application code knows exactly one abstraction:

```ts
ImageGenerationProviderPort
```

It must never know `GoogleGenAI`, an OpenAI client, a Python script path, or a REST endpoint.

## 9.4 Explicit side effects [LOCKED]

Remote calls, filesystem writes, child processes, job-store mutations and manifest writes are side effects and must sit behind ports. There must be no hidden SDK call inside a mapper, a React component, or a "helper" utility.

## 9.5 Additive migration [LOCKED]

```text
Do NOT rewrite Creative Studio before Gemini is proven.

Preferred sequence:
  existing route
    -> thin controller (schema + auth + map to command)
    -> existing durable job enqueue
    -> job worker calls the new use case
    -> provider registry
    -> existing OpenAI generator wrapped as an adapter
    -> Gemini adapters added alongside
    -> existing validators, untouched
```

---

# 10. SYSTEM CONTEXT AND FLOW

## 10.1 Container view

```text
┌──────────────────────────────────────────────────────────────┐
│ Creative Studio UI  (venho-os /os)                           │
│  scenario · outfit · lane · prompt · aspect preset           │
│  NEW: Image Generator selector · size tier · cost estimate    │
└───────────────────────────┬──────────────────────────────────┘
                            │ POST /api/v1/studio/generate-image
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ Next.js API Controller  (runtime = "nodejs")                 │
│  auth · strict request schema · map HTTP -> command           │
│  enqueue durable job · return jobId immediately               │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ Durable Job Store (existing, file-backed)                    │
│  queued -> generating -> validating -> succeeded/failed/      │
│                                        cancelled              │
│  NEW fields: providerId · modelId · imageSize · estCostUsd    │
└───────────────────────────┬──────────────────────────────────┘
                            │ worker picks up
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ GenerateStudioImageUseCase   (application layer)             │
│  1 resolve provider descriptor      6 verify bytes+geometry   │
│  2 resolve lane/reference policy    7 write immutable artifact│
│  3 preflight capability check       8 write manifest 1.2      │
│  4 budget guard + concurrency lease 9 run existing validators │
│  5 call provider EXACTLY ONCE      10 record cost ledger      │
└───────────────────────────┬──────────────────────────────────┘
                            │ ImageGenerationProviderPort
        ┌───────────┬───────┴────────┬───────────────┬──────────┐
        ▼           ▼                ▼               ▼          ▼
   OpenAI      Nano Banana 2   Nano Banana Pro  NB 2 Lite    Mock
   adapter        adapter          adapter       adapter    adapter
        │           └────────────────┴───────────────┘          │
        │                        │                              │
        │                @google/genai                    fixture bytes
        │                Interactions API                 (zero cost)
        │                store = false
        ▼
  legacy bridge: execFile(generate_image.py) -> temp file -> bytes
        │
        └────────────────────────┬─────────────────────────────┘
                                 ▼
                    ProviderGenerateImageResult (bytes + metadata)
                                 ▼
              Artifact Store (atomic, hashed, immutable)
                                 ▼
                    Manifest schemaVersion 1.2
                                 ▼
                 Existing Validator Studio (UNCHANGED)
                                 ▼
                        Human review gate
                                 ▼
              Official promotion — explicit human action only
```

## 10.2 Success sequence

```text
UI            Controller       JobStore        Worker/UseCase     Provider
 │  submit  →    │                │                  │                │
 │               │ validate       │                  │                │
 │               │ enqueue     →  │ queued           │                │
 │  ← jobId      │                │                  │                │
 │  poll status →│  read       →  │                  │                │
 │                                │ →  claim      →  │                │
 │                                │    generating    │ budget check   │
 │                                │                  │ concurrency    │
 │                                │                  │  → generate  → │
 │                                │                  │  ← bytes       │
 │                                │                  │ verify+geometry│
 │                                │                  │ write artifact │
 │                                │                  │ write manifest │
 │                                │    validating ←  │ run validators │
 │                                │    succeeded  ←  │ record cost    │
 │  ← result     │                │                  │                │
```

## 10.3 Failure sequence (provider error after possible billing)

```text
Worker → Provider : generate
Provider ⇢ timeout / 5xx / safety block / no image
Worker  : DO NOT retry
Worker  : write generation-error.json  (no image.png)
Worker  : write manifest with status = generation_failed
Worker  : record cost ledger entry with costCertainty = "unknown"
Worker  : job -> failed, with a sanitized user-facing message
UI      : offers a MANUAL retry, clearly labelled as a NEW PAID ATTEMPT
```

---

# 11. DOMAIN MODEL

> All snippets are contract sketches (RULE 0.2.5). Adapt naming to the repo.

## 11.1 Provider IDs — two tiers [LOCKED, fixes D-07]

```ts
// domain/image-generation-provider-id.ts
//
// WHY TWO TIERS:
// `mock` must exist internally (tests) but must be structurally impossible to
// select over HTTP. A prose rule is not enough — one missed check leaks a
// zero-cost provider into production and silently produces fake assets.
// The type system does the enforcing here.

/** Providers a browser/API client is allowed to name. */
export const PUBLIC_IMAGE_GENERATION_PROVIDER_IDS = [
  "openai",
  "nano-banana-2",
  "nano-banana-pro",
  "nano-banana-2-lite",
] as const;

/** Providers that exist inside the server process. */
export const INTERNAL_IMAGE_GENERATION_PROVIDER_IDS = [
  ...PUBLIC_IMAGE_GENERATION_PROVIDER_IDS,
  "mock",
] as const;

export type PublicImageGenerationProviderId =
  (typeof PUBLIC_IMAGE_GENERATION_PROVIDER_IDS)[number];

export type ImageGenerationProviderId =
  (typeof INTERNAL_IMAGE_GENERATION_PROVIDER_IDS)[number];
```

```text
RULE 11.1a  The HTTP request schema validates against PUBLIC_* only.
RULE 11.1b  An unknown or non-public value returns
            400 IMAGE_GENERATION_PROVIDER_INVALID.
            It NEVER falls back to openai. Silent fallback destroys the
            benchmark and hides misconfiguration.
RULE 11.1c  `mock` is additionally disabled by the registry when
            NODE_ENV === "production".
```

## 11.2 Aspect preset and ratio

```ts
// domain/image-aspect.ts
export type ImageAspectPreset = "portrait" | "square" | "story";

/** Canonical, server-owned. The UI never sends a raw ratio. */
export const ASPECT_RATIO_MAP = {
  portrait: "2:3",
  square: "1:1",
  story: "9:16",
} as const;

export type ImageAspectRatio =
  (typeof ASPECT_RATIO_MAP)[ImageAspectPreset];
```

## 11.3 Image size tier

```ts
// domain/image-size.ts
//
// WIRE VALUES. The vendor expects an uppercase "K" and the literal string
// "512" for the smallest tier. Lowercase "1k" is rejected upstream.
// VENHO does not currently use "512"; it is typed so nobody invents "0.5K".
export type ImageSizeTier = "512" | "1K" | "2K" | "4K";

export const VENHO_SUPPORTED_IMAGE_SIZES: ImageSizeTier[] = ["1K", "2K", "4K"];
```

## 11.4 Reference role and resolved reference

```ts
// domain/image-reference.ts
export type ImageReferenceRole = "face" | "environment";
// Do NOT add "style" / "product" roles until a real requirement exists.

/**
 * The application layer only ever sees an ALREADY-TRUSTED reference:
 * resolved from a server-side asset library, authorized, size-checked,
 * MIME-checked and hashed. A provider never resolves a path.
 */
export type ResolvedImageReference = {
  assetId: string;                       // stable library ID, not a path
  role: ImageReferenceRole;
  mimeType: "image/png" | "image/jpeg";
  bytes: Uint8Array;
  sha256: string;
  byteLength: number;
};
```

## 11.5 Generation lane

```ts
// domain/generation-lane.ts
// Mirrors the EXISTING venho-os lane concept. Do not redefine it here —
// import or re-export the existing type if one already exists (§ Phase 0).
export type GenerationLane = "identity" | "action";
```

## 11.6 Generate command

```ts
// domain/generate-image-command.ts
export type GenerateImageCommand = {
  // Identity of the attempt — ALL server-generated (see D-13).
  runId: string;
  variantId: string;
  attemptId: string;          // e.g. "attempt-001", zero-padded to 3 digits

  providerId: ImageGenerationProviderId;

  /** Server-resolved prompt INCLUDING linh_an_generation_protocol_v1. */
  generationPrompt: string;
  generationPromptSha256: string;

  aspectPreset: ImageAspectPreset;
  aspectRatio: ImageAspectRatio;
  imageSize: ImageSizeTier;

  lane: GenerationLane;
  references: ResolvedImageReference[];

  /** For log correlation across HTTP -> job -> worker -> provider. */
  correlationId: string;
  jobId: string;
};
```

```text
RULE 11.6a  If the current application supports MORE lanes, presets, or
            fields than this sketch, KEEP THEM. This is a minimum contract,
            not a permission to delete existing behaviour.
```

## 11.7 Provider result

```ts
// domain/provider-result.ts
export type ProviderGenerateImageResult = {
  providerId: ImageGenerationProviderId;
  modelId: string;

  image: {
    bytes: Uint8Array;
    mimeType: "image/png" | "image/jpeg";
  };

  providerRequestId?: string;

  usage?: {
    inputTokens?: number;
    outputTokens?: number;
    totalTokens?: number;
    imageInputTokens?: number;
    imageOutputTokens?: number;
    thinkingTokens?: number;
    [key: string]: number | string | undefined;
  };

  /**
   * SANITIZED metadata only. Never place secrets, auth headers, or an
   * unrestricted raw provider response here — this object reaches the
   * manifest, and the manifest is committed/archived.
   */
  providerMetadata?: Record<string, string | number | boolean | null | undefined>;

  /** Wall-clock duration of the provider call, for the benchmark. */
  durationMs: number;
};
```

## 11.8 Bytes are not an artifact [LOCKED]

```text
Returned bytes become a VENHO artifact only after ALL of:
  bytes present and non-empty
  MIME is in the accepted set
  an image decoder can actually read the data
  width > 0 and height > 0
  geometry matches the requested ratio/size within tolerance   (§23.5)
  byte length is within the configured maximum
  SHA-256 computed over the final bytes
  atomic write succeeded
  canonical immutable path assigned
```

---

# 12. PORTS

```ts
// application/ports/image-generation-provider.port.ts
export interface ImageGenerationProviderPort {
  readonly id: ImageGenerationProviderId;

  /**
   * Call the upstream generator EXACTLY ONCE.
   * MUST NOT retry (ADR-IMG-004). MUST NOT write to disk (ADR-IMG-005).
   * MUST translate vendor errors into ImageGenerationError (§22).
   */
  generate(
    input: ProviderGenerateImageInput,
    context: ProviderRequestContext,
  ): Promise<ProviderGenerateImageResult>;
}

export type ProviderGenerateImageInput = {
  prompt: string;
  aspectRatio: ImageAspectRatio;
  imageSize: ImageSizeTier;
  references: ResolvedImageReference[];
};

export type ProviderRequestContext = {
  correlationId: string;
  abortSignal?: AbortSignal;
};
```

```ts
// application/ports/image-artifact-store.port.ts
export interface ImageArtifactStorePort {
  /** Fails if the canonical path already exists. Never overwrites. */
  writeImmutable(input: {
    runId: string; variantId: string; attemptId: string;
    bytes: Uint8Array; mimeType: string;
  }): Promise<PersistedArtifact>;

  exists(runId: string, variantId: string, attemptId: string): Promise<boolean>;

  writeSidecar(input: {
    runId: string; variantId: string; attemptId: string;
    filename: string; content: string;
  }): Promise<void>;
}
```

```ts
// application/ports/image-reference-loader.port.ts
export interface ImageReferenceLoaderPort {
  /**
   * Resolve trusted asset IDs into bytes.
   * MUST reject: path traversal, absolute paths, file:// URLs, remote URLs,
   * unknown asset IDs, unauthorized assets, disallowed MIME, oversize files.
   */
  resolve(assetIds: string[], lane: GenerationLane): Promise<ResolvedImageReference[]>;
}
```

```ts
// application/ports/generation-concurrency.port.ts
export interface GenerationConcurrencyPort {
  acquire(input: { correlationId: string }): Promise<GenerationLease>;
}
export interface GenerationLease {
  readonly leaseId: string;
  release(): Promise<void>;
}
```

```ts
// application/ports/generation-budget.port.ts   (NEW — fixes D-05)
export interface GenerationBudgetPort {
  /** Called BEFORE the paid provider call. Throws if the cap is reached. */
  assertWithinBudget(input: {
    providerId: ImageGenerationProviderId;
    estimatedCostUsd: number;
  }): Promise<BudgetDecision>;

  /** Append-only. Called after success AND after ambiguous failure. */
  record(entry: CostLedgerEntry): Promise<void>;
}
```

```ts
// application/ports/validator-gateway.port.ts
export interface ValidatorGatewayPort {
  /** Wraps the EXISTING validator invocation. Behaviour must not change. */
  validate(input: { artifact: PersistedArtifact; manifest: GenerationManifest }):
    Promise<ValidatorResult>;
}
```

```ts
// application/ports/generation-job.port.ts      (NEW — fixes D-02)
export interface GenerationJobPort {
  markGenerating(jobId: string, patch: JobProviderPatch): Promise<void>;
  markValidating(jobId: string): Promise<void>;
  markSucceeded(jobId: string, result: JobResultSummary): Promise<void>;
  markFailed(jobId: string, error: SanitizedJobError): Promise<void>;
  isCancelRequested(jobId: string): Promise<boolean>;
}
```

---

# 13. APPLICATION USE CASE

## 13.1 Responsibilities

```text
 1  resolve the trusted provider descriptor
 2  preflight: capability check (size/ratio/reference caps supported?)
 3  preflight: lane + reference policy (existing rules, unchanged)
 4  preflight: attempt uniqueness (canonical path must not exist)
 5  preflight: budget guard (estimated cost vs remaining daily cap)
 6  acquire the concurrency lease
 7  check for a cancel request BEFORE spending
 8  call the provider EXACTLY ONCE
 9  verify bytes: decodable, MIME, size, GEOMETRY
10  write the immutable artifact atomically
11  write manifest 1.2 + prompt/inputs/references sidecars
12  record the cost ledger entry
13  run the EXISTING validator path
14  persist QC results into the manifest
15  return a sanitized result
16  release the lease in `finally`, always
```

## 13.2 Non-responsibilities

```text
It does NOT construct SDK clients, parse vendor-specific response shapes,
render UI, execute SQL, change validator thresholds, or decide official status.
```

## 13.3 Reference algorithm

```ts
// application/use-cases/generate-studio-image.use-case.ts
//
// READ THIS BEFORE EDITING:
//  * Exactly one provider call happens in this function. If you find yourself
//    adding a second call site, you are adding hidden cost (ADR-IMG-004).
//  * Everything before `provider.generate` is free. Everything after it is
//    already paid for. That boundary is why the order below is not arbitrary:
//    all cheap rejections happen first.
export async function execute(
  command: GenerateImageCommand,
  deps: UseCaseDeps,
): Promise<GenerateStudioImageResult> {
  assertCommandInvariants(command);

  // ---- FREE PREFLIGHT (fail here, not after paying) ----------------------
  const descriptor = deps.providerRegistry.getDescriptor(command.providerId);
  assertProviderEnabled(descriptor);
  assertCapabilitySupported(descriptor, command);        // size, ratio, ref caps
  assertReferencePolicy(command.lane, command.references); // existing rules

  if (await deps.artifactStore.exists(command.runId, command.variantId, command.attemptId)) {
    throw new ImageGenerationError("IMAGE_GENERATION_ATTEMPT_ALREADY_EXISTS");
  }

  const estimate = deps.costEstimator.estimate({
    providerId: command.providerId,
    imageSize: command.imageSize,
    referenceCount: command.references.length,
    promptChars: command.generationPrompt.length,
  });

  await deps.budget.assertWithinBudget({
    providerId: command.providerId,
    estimatedCostUsd: estimate.estimatedTotalCostUsd,
  });

  const lease = await deps.concurrency.acquire({ correlationId: command.correlationId });

  try {
    if (await deps.jobs.isCancelRequested(command.jobId)) {
      throw new ImageGenerationError("IMAGE_GENERATION_CANCELLED_BEFORE_SPEND");
    }

    await deps.jobs.markGenerating(command.jobId, {
      providerId: descriptor.id,
      modelId: descriptor.modelId,
      imageSize: command.imageSize,
      aspectRatio: command.aspectRatio,
      estimatedCostUsd: estimate.estimatedTotalCostUsd,
    });

    // ================== THE ONLY PAID CALL IN THIS FILE ==================
    const providerResult = await deps.providerRegistry
      .get(command.providerId)
      .generate(
        {
          prompt: command.generationPrompt,
          aspectRatio: command.aspectRatio,
          imageSize: command.imageSize,
          references: command.references,
        },
        { correlationId: command.correlationId, abortSignal: deps.abortSignal },
      );
    // =====================================================================
    // From here on, money is spent. Never throw away the evidence: even a
    // geometry mismatch gets persisted, because we paid for those bytes.

    const verified = await deps.imageOutputVerifier.verify({
      image: providerResult.image,
      requestedAspectRatio: command.aspectRatio,
      requestedImageSize: command.imageSize,
    });

    const artifact = await deps.artifactStore.writeImmutable({
      runId: command.runId,
      variantId: command.variantId,
      attemptId: command.attemptId,
      bytes: verified.bytes,
      mimeType: verified.mimeType,
    });

    const manifest = await deps.manifestService.recordGenerationSuccess({
      command, providerResult, verified, artifact, estimate,
    });

    await deps.budget.record({
      at: new Date().toISOString(),
      runId: command.runId, variantId: command.variantId, attemptId: command.attemptId,
      providerId: descriptor.id, modelId: descriptor.modelId,
      imageSize: command.imageSize,
      estimatedTotalCostUsd: estimate.estimatedTotalCostUsd,
      costCertainty: "estimated",
      outcome: verified.geometryMatches ? "success" : "geometry_mismatch",
    });

    await deps.jobs.markValidating(command.jobId);

    // Existing Validator Studio. UNCHANGED. If it throws, the artifact and
    // the generation manifest still stand — we do not delete paid evidence.
    const qc = await deps.validatorGateway.validate({ artifact, manifest });
    await deps.manifestService.recordValidationResult({ manifest, qc });

    await deps.jobs.markSucceeded(command.jobId, summarize(artifact, qc));

    return {
      artifact,
      generation: sanitizeGenerationResult(providerResult, verified),
      qc,
    };
  } catch (error) {
    const mapped = mapToImageGenerationError(error);
    await deps.failureRecorder.record({ command, error: mapped, estimate });
    await deps.jobs.markFailed(command.jobId, sanitizeForClient(mapped));
    throw mapped;
  } finally {
    await lease.release();
  }
}
```

## 13.4 Cancellation semantics [NEW — fixes D-02]

```text
cancel requested while job is `queued`
  -> job -> cancelled. No spend. No artifact. No ledger entry.

cancel requested while job is `generating`
  -> the provider call is NOT interruptible without ambiguity.
     Let the in-flight call finish, persist the artifact and manifest, THEN
     mark the job cancelled with `cancelledAfterSpend: true`.
     Record the cost ledger entry.
     RATIONALE: aborting mid-call does not un-bill the request. Throwing away
     an image you already paid for is strictly worse than keeping it.

cancel requested while job is `validating`
  -> let validation finish. Validation is free and its result is useful.

NEVER report a cancelled-after-spend job as "no cost incurred".
```

---

# 14. PROVIDER REGISTRY

## 14.1 Descriptor

```ts
// domain/provider-descriptor.ts
export type ImageGenerationProviderDescriptor = {
  id: ImageGenerationProviderId;
  displayName: string;          // "Nano Banana 2"
  displayNameVi: string;        // Vietnamese UI label
  modelId: string;              // server-side only, never sent to a client
  enabled: boolean;
  disabledReason?: ProviderDisabledReason;

  capabilities: {
    supportsFaceReference: boolean;
    supportsEnvironmentReference: boolean;
    maxCharacterReferences: number;
    maxObjectReferences: number;
    maxStyleReferences: number;
    supportedImageSizes: ImageSizeTier[];
    supportedAspectRatios: ImageAspectRatio[];
    supportsSearchGrounding: boolean;   // informational; VENHO never uses it
  };

  policy: {
    /** Identity-lane use of this provider is forbidden (Lite). */
    forbiddenForIdentityLane: boolean;
    /** Force a minimum size because smaller costs the same (Pro -> 2K). */
    minimumEconomicImageSize?: ImageSizeTier;
  };
};

export type ProviderDisabledReason =
  | "provider_not_configured"
  | "provider_disabled_by_config"
  | "provider_disabled_in_production";
```

## 14.2 Required descriptors [VERIFY reference caps before Phase 3]

```text
openai
  modelId                : <resolved from generate_image.py in Phase 0>
  sizes                  : <resolved in Phase 0 — do NOT assume 1K/2K/4K>
  ratios                 : portrait, square, story (existing behaviour)
  identity lane          : allowed
  role                   : baseline + rollback target

nano-banana-2
  modelId                : gemini-3.1-flash-image
  character references   : up to 4
  object references      : up to 10
  style references       : 0
  sizes                  : 1K, 2K, 4K
  ratios                 : 2:3, 1:1, 9:16
  identity lane          : allowed  (this is the Linh An default)
  provider-side storage  : disabled by VENHO (store=false)

nano-banana-pro
  modelId                : gemini-3-pro-image
  character references   : up to 5
  object references      : up to 6
  style references       : up to 3
  sizes                  : 1K, 2K, 4K
  minimumEconomicImageSize : 2K        <-- RULE 1.3.1c
  identity lane          : allowed (escalation only)

nano-banana-2-lite
  modelId                : gemini-3.1-flash-lite-image
  sizes                  : 1K ONLY
  search grounding       : NOT SUPPORTED by the model at all
  character reference    : not positioned for multi-reference identity work
  identity lane          : forbiddenForIdentityLane = true   <-- HARD POLICY
  intended use           : Ven Hồ non-character, high-volume 1K candidates
  ships                  : disabled by default (OD-4)

mock
  modelId                : mock-image-v1
  enabled                : false when NODE_ENV === "production"
```

## 14.3 Single source of truth for model mapping [LOCKED]

```ts
// infrastructure/config/provider-model-map.ts
//
// THIS IS THE ONLY PLACE A VENDOR MODEL STRING MAY APPEAR IN THE CODEBASE.
// If you need a model ID somewhere else, read the resolved descriptor instead.
export const PROVIDER_MODEL_MAP = {
  openai: process.env.OPENAI_IMAGE_MODEL ?? "<resolved in Phase 0>",
  "nano-banana-2": "gemini-3.1-flash-image",
  "nano-banana-pro": "gemini-3-pro-image",
  "nano-banana-2-lite": "gemini-3.1-flash-lite-image",
  mock: "mock-image-v1",
} as const;
```

```text
FORBIDDEN duplication sites — a model string must NOT appear in:
  route.ts · any React component · the manifest writer · a benchmark script ·
  the Gemini adapter · a test fixture that asserts business behaviour ·
  a comment used as documentation of truth

A test MUST assert that no vendor model string appears outside this module.
(§33.9 — it is a cheap grep-style test and it prevents the exact regression
v2.1 had, where route.ts hard-coded `model: "gpt-image-2"` into the manifest.)
```

## 14.4 Preflight rules owned by the registry [LOCKED]

```ts
// Enforced server-side BEFORE any paid call. The UI mirrors these rules for
// UX, but the UI is never the enforcement point.
assertCapabilitySupported(descriptor, command):
  1. descriptor.enabled === true                       else PROVIDER_DISABLED
  2. imageSize ∈ capabilities.supportedImageSizes      else UNSUPPORTED_SIZE
  3. aspectRatio ∈ capabilities.supportedAspectRatios  else UNSUPPORTED_RATIO
  4. lane === "identity" && policy.forbiddenForIdentityLane
                                                       else PROVIDER_NOT_ALLOWED_FOR_LANE
  5. count(references, role="face") <= maxCharacterReferences
  6. count(references, role="environment") <= maxObjectReferences
  7. policy.minimumEconomicImageSize present && requested size is smaller
       -> reject with UNSUPPORTED_SIZE and an explanatory message.
          DO NOT silently upgrade the request: a silent upgrade changes what
          the benchmark measured and what the user believes they bought.
```

## 14.5 Registry construction

```ts
// infrastructure/registry/image-provider-registry.ts
// Constructed once, server-side, in the composition root (§15).
const providers = new Map<ImageGenerationProviderId, ImageGenerationProviderPort>([
  ["openai", openAiLegacyProvider],
  ["nano-banana-2", nanoBanana2Provider],
  ["nano-banana-pro", nanoBananaProProvider],
  ["nano-banana-2-lite", nanoBanana2LiteProvider],
  ["mock", mockProvider],
]);
```

---

# 15. COMPOSITION ROOT [NEW — fixes D-11]

Clean Architecture needs exactly one place where the object graph is assembled. Without it, wiring leaks into route handlers and the layers rot.

```ts
// infrastructure/composition/image-generation.module.ts
//
// The ONLY place that knows every concrete class.
// Routes, the job worker and scripts all call buildImageGenerationModule().
// Nothing else constructs an adapter.
export function buildImageGenerationModule(
  env: ImageGenerationEnv = readImageGenerationEnv(),
): ImageGenerationModule {
  const geminiClient = env.googleEnabled
    ? createGeminiClient(env.geminiApiKey)   // throws if enabled without a key
    : null;

  const registry = new ImageProviderRegistry({
    descriptors: buildDescriptors(env),      // enabled flags resolved here
    providers: {
      openai: new OpenAiLegacyImageProvider({ scriptPath: env.openAiScriptPath }),
      "nano-banana-2": geminiClient && new GeminiImageProvider({ client: geminiClient, providerId: "nano-banana-2" }),
      "nano-banana-pro": geminiClient && new GeminiImageProvider({ client: geminiClient, providerId: "nano-banana-pro" }),
      "nano-banana-2-lite": geminiClient && new GeminiImageProvider({ client: geminiClient, providerId: "nano-banana-2-lite" }),
      mock: env.isProduction ? null : new MockImageProvider(),
    },
  });

  return {
    registry,
    useCase: new GenerateStudioImageUseCase({
      providerRegistry: registry,
      artifactStore:  new FsImageArtifactStore({ root: env.artifactRoot }),
      referenceLoader: new ExistingReferenceLoader({ root: env.referenceRoot }),
      concurrency:    new FileLockConcurrencyAdapter({ max: env.maxConcurrency }),
      budget:         new FileCostLedgerBudgetGuard({ path: env.costLedgerPath, dailyCapUsd: env.dailyBudgetUsd }),
      validatorGateway: new ExistingValidatorGateway({ /* unchanged invocation */ }),
      jobs:           new FileBackedGenerationJobAdapter({ /* EXISTING store */ }),
      imageOutputVerifier: new SharpImageOutputVerifier(),
      costEstimator:  new TokenBasedCostEstimator(IMAGE_PRICING_SNAPSHOT),
      manifestService: new GenerationManifestService({ schemaVersion: "1.2" }),
      failureRecorder: new FsGenerationFailureRecorder(),
    }),
  };
}
```

```text
RULE 15.1  A single instance per process where the runtime allows it.
           Under Next.js dev hot-reload, guard with a module-level singleton
           so you do not leak clients or duplicate in-memory semaphores.
RULE 15.2  When a Gemini provider cannot be constructed (no key), register it
           as a DISABLED DESCRIPTOR rather than omitting it. The UI must be
           able to show "Nano Banana 2 — chưa cấu hình", not silently hide it.
```

---

# PART IV — CONTRACTS (CONTRACT-FIRST)

> VENHO's Contract-First principle: every inter-module interface is defined before implementation. Write these as JSON Schema files under `contracts/` and validate against them in tests, so a contract change is a visible diff rather than an accident.

# 16. HTTP CONTRACT — POST /api/v1/studio/generate-image

## 16.1 Backward compatibility rule [LOCKED]

```text
A request that omits every new field MUST behave exactly as it does today.
Only additive manifest metadata and internal architecture may differ.
This is the single most important regression guarantee of this change.
```

## 16.2 Request — additive fields

```jsonc
{
  // ---- EXISTING FIELDS: preserve all of them verbatim. -------------------
  // The agent must enumerate the real current fields in Phase 0 and list
  // them in the Discovery Inventory. This block shows ONLY the additions.

  // NEW: which generator to use. Public providers only.
  "generationProvider": "nano-banana-2",

  // NEW: output resolution tier, separate from aspect (D-14 / §11.3).
  // Optional. Server default = 1K unless the existing official flow
  // already mandates another tier, in which case preserve that.
  "imageSize": "2K",

  // NEW: client-generated idempotency key (see §16.3). Optional but
  // strongly recommended from the UI.
  "idempotencyKey": "8f3c1b7e-…",

  // NEW: explicit reference selection by trusted asset ID.
  // NEVER a path. NEVER a URL. NEVER a base64 blob.
  "referenceAssetIds": ["linh-an-face-master-v3"]
}
```

### 16.2.1 Field rules

```text
generationProvider   enum(PUBLIC_IMAGE_GENERATION_PROVIDER_IDS), optional.
                     absent -> IMAGE_GENERATION_DEFAULT_PROVIDER
                     unknown value -> 400, never a silent default
                     "mock" -> 400 (it is not in the public enum)

imageSize            enum("1K","2K","4K"), optional.
                     absent -> server default
                     unsupported for the chosen provider -> 400 with the
                     supported list in the error detail (so the UI can heal)

idempotencyKey       string, optional, max 128 chars, opaque.

referenceAssetIds    string[], optional, max 8 entries.
                     Each ID must resolve inside the trusted asset library.
                     Unknown/unauthorized ID -> 400. Never a filesystem read
                     of an arbitrary string.

REJECTED FIELDS (400, do not silently ignore where the schema allows strict
mode; ignore only where strictness would break the current API):
  model / modelId          — the server owns model resolution
  outputPath / imagePath   — the server owns paths
  referencePath            — no client-supplied paths, ever
  apiKey                   — never
  providerHeaders          — never
```

## 16.3 Attempt identity ownership [LOCKED — fixes D-13]

```text
runId       server-generated
variantId   server-generated
attemptId   server-generated, zero-padded 3 digits: attempt-001, attempt-002…

The client NEVER supplies these. It may supply `idempotencyKey` only.

Idempotency behaviour:
  same idempotencyKey seen again while the original job is still active
    -> return the ORIGINAL jobId, 200, do not enqueue a second job
  same idempotencyKey after the original job reached a terminal state
    -> return the original job's result, 200, do not re-spend
  no idempotencyKey supplied
    -> normal enqueue; double-submit protection then relies on the
       canonical attempt-path uniqueness check (§29.1) and the UI busy state
```

## 16.4 Response — job accepted (asynchronous path)

```jsonc
{
  "ok": true,
  "jobId": "job_2026-08-10_0007",
  "status": "queued",
  "generation": {
    "provider": "nano-banana-2",
    "aspectRatio": "2:3",
    "imageSize": "2K",
    "estimatedCostUsd": 0.101,
    "estimateBasis": "output-tokens-only"
  }
}
```

```text
NOTE: `model` is intentionally ABSENT from the accept response. The client has
no use for the vendor model string and exposing it invites clients to start
sending it back. The model IS recorded in the manifest and IS available on the
capabilities endpoint for display purposes.
```

## 16.5 Response — completed job

```jsonc
{
  "ok": true,
  "jobId": "job_2026-08-10_0007",
  "status": "succeeded",
  "runId": "run_…", "variantId": "variant-001", "attemptId": "attempt-001",
  "generation": {
    "provider": "nano-banana-2",
    "model": "gemini-3.1-flash-image",
    "aspectRatio": "2:3",
    "imageSize": "2K",
    "geometry": { "requested": "2:3 @2K", "actual": "1360x2040", "matches": true },
    "durationMs": 5120,
    "estimatedTotalCostUsd": 0.1021
  },
  "artifact": { "path": "…", "sha256": "…", "bytes": 2482913 },
  "qc": { "…": "existing-validator-result-shape-unchanged" }
}
```

```text
NEVER expose in any response:
  the API key · raw provider headers · a raw provider error object ·
  an absolute filesystem path outside the served whitelist ·
  unredacted environment values · the full provider response body
```

## 16.6 Runtime requirements [NEW — fixes D-09]

```ts
// src/app/api/v1/studio/generate-image/route.ts
export const runtime = "nodejs";   // MANDATORY: fs, crypto, child_process
export const dynamic = "force-dynamic";
export const maxDuration = 60;     // seconds — see rule below
```

```text
RULE 16.6a  The route MUST NOT run on the Edge runtime. Edge has no fs,
            no child_process, and no node:crypto in the form used here.

RULE 16.6b  IMAGE_GENERATION_TIMEOUT_MS must be strictly LESS than the
            platform's hard request/function limit, and the job worker's own
            budget must be less than that again. Setting a 120s SDK timeout
            behind a 60s platform limit produces a truncated request with an
            unknown billing outcome — the worst possible failure mode.

RULE 16.6c  The agent must READ the deployment target in Phase 0 (local Mac
            Mini M4 via launchd? Vercel? node server?) and choose real values.
            Do not copy a number from this document into production.

RULE 16.6d  Because generation is enqueued, the HTTP request itself should be
            short-lived. Long waits belong to the job poll endpoint, not to
            the POST.
```

---

# 17. HTTP CONTRACT — GET /api/v1/studio/image-generation/providers

Purpose: the server owns the provider catalog. The UI must never infer availability from browser environment variables or from a hard-coded list.

```jsonc
{
  "defaultProvider": "openai",
  "pricingSnapshotDate": "2026-08-10",
  "currency": "USD",
  "dailyBudget": { "capUsd": 5.0, "spentUsd": 0.402, "remainingUsd": 4.598, "state": "ok" },
  "providers": [
    {
      "id": "openai",
      "label": "GPT Image",
      "labelVi": "GPT Image (hiện tại)",
      "enabled": true,
      "capabilities": {
        "supportedImageSizes": ["1K"],
        "supportedAspectRatios": ["2:3", "1:1", "9:16"],
        "maxCharacterReferences": 1,
        "allowedInIdentityLane": true
      },
      "estimatedOutputCostUsd": { "1K": null },
      "note": "Baseline. Cost depends on the configured quality tier."
    },
    {
      "id": "nano-banana-2",
      "label": "Nano Banana 2",
      "labelVi": "Nano Banana 2 — cân bằng",
      "model": "gemini-3.1-flash-image",
      "enabled": true,
      "capabilities": {
        "supportedImageSizes": ["1K", "2K", "4K"],
        "supportedAspectRatios": ["2:3", "1:1", "9:16"],
        "maxCharacterReferences": 4,
        "maxObjectReferences": 10,
        "allowedInIdentityLane": true
      },
      "estimatedOutputCostUsd": { "1K": 0.067, "2K": 0.101, "4K": 0.151 }
    },
    {
      "id": "nano-banana-pro",
      "label": "Nano Banana Pro",
      "labelVi": "Nano Banana Pro — cao cấp",
      "model": "gemini-3-pro-image",
      "enabled": true,
      "capabilities": {
        "supportedImageSizes": ["2K", "4K"],
        "supportedAspectRatios": ["2:3", "1:1", "9:16"],
        "maxCharacterReferences": 5,
        "maxObjectReferences": 6,
        "maxStyleReferences": 3,
        "allowedInIdentityLane": true,
        "minimumEconomicImageSize": "2K"
      },
      "estimatedOutputCostUsd": { "2K": 0.134, "4K": 0.24 },
      "note": "1K costs the same as 2K, so 1K is not offered."
    },
    {
      "id": "nano-banana-2-lite",
      "label": "Nano Banana 2 Lite",
      "labelVi": "Nano Banana 2 Lite — ảnh khách sạn, không có nhân vật",
      "enabled": false,
      "disabledReason": "provider_disabled_by_config",
      "capabilities": {
        "supportedImageSizes": ["1K"],
        "supportedAspectRatios": ["2:3", "1:1", "9:16"],
        "allowedInIdentityLane": false
      },
      "estimatedOutputCostUsd": { "1K": 0.0336 }
    }
  ]
}
```

```text
RULE 17.1  `mock` NEVER appears in this response.
RULE 17.2  A provider without credentials appears with enabled=false and a
           COARSE disabledReason. Never leak which environment variable is
           missing, and never leak a secret's name if the current security
           policy avoids revealing them.
RULE 17.3  `estimatedOutputCostUsd` for openai is `null` until OD-1 resolves.
           A null is honest. A guessed number becomes a false benchmark.
RULE 17.4  Cache: short TTL only (<= 60s) or no cache. The budget block
           changes as money is spent.
RULE 17.5  Sizes advertised here are exactly what the registry preflight will
           accept. If the UI can select it, the server must accept it, and
           vice versa. A drift between the two is a bug, not a UX detail.
```

---

# 18. DURABLE JOB RECORD CONTRACT [NEW — fixes D-02]

The job store already exists. This change **extends** it additively.

```jsonc
{
  "jobId": "job_2026-08-10_0007",
  "state": "generating",          // queued|generating|validating|succeeded|failed|cancelled
  "createdAt": "2026-08-10T09:14:02+07:00",
  "updatedAt": "2026-08-10T09:14:09+07:00",
  "correlationId": "…",
  "idempotencyKey": "…",

  "runId": "run_…", "variantId": "variant-001", "attemptId": "attempt-001",

  // ---------------- ADDITIVE BLOCK (new in this change) ----------------
  "provider": {
    "id": "nano-banana-2",
    "modelId": "gemini-3.1-flash-image",
    "aspectPreset": "portrait",
    "aspectRatio": "2:3",
    "imageSize": "2K",
    "estimatedCostUsd": 0.101,
    "spendCommitted": false,      // flips true immediately before the call
    "cancelledAfterSpend": false
  },
  // ---------------------------------------------------------------------

  "error": null                   // sanitized shape only; never a raw vendor object
}
```

```text
RULE 18.1  `spendCommitted` flips to true IMMEDIATELY BEFORE the provider
           call and is persisted before the call is issued. If the process
           crashes mid-call, recovery can see that money may have been spent.
           This is the difference between "we do not know" and "we know we do
           not know" — only the second one is operable.

RULE 18.2  A crashed job whose `spendCommitted === true` and which has no
           artifact must be recovered as `failed` with
           `costCertainty = "unknown"`, and it must NEVER be auto-restarted.

RULE 18.3  Existing job readers must keep working. Unknown fields are ignored
           by old readers; if any old reader crashes on unknown keys, fix the
           reader BEFORE shipping (same rule as the manifest, §19.6).
```

---

# 19. MANIFEST CONTRACT — schemaVersion 1.1 → 1.2 [fixes D-06]

## 19.1 Compatibility rule [LOCKED]

```text
ADDITIVE ONLY.
  keep every existing 1.1 field, with the same meaning
  keep the existing top-level legacy `model` field if present, and populate
    it from providerResult.modelId — NEVER from a hard-coded literal
  add the new `generation` object
  bump schemaVersion "1.1" -> "1.2"

Existing 1.1 fields that MUST survive untouched:
  promptHash · outfit requested/effective · scenarioProfile ·
  face reference set version · validation contract · latency/retry ·
  generationLane · effective reference mode · exact submitted prompt ·
  server-added prompt · action protocol · DNA version · validator result
```

## 19.2 Additive `generation` block

```jsonc
{
  "schemaVersion": "1.2",
  "model": "gemini-3.1-flash-image",

  "generation": {
    "provider": "nano-banana-2",
    "model": "gemini-3.1-flash-image",

    "api": "gemini-interactions",
    "apiMode": "standard",
    "storeProviderInteraction": false,

    "aspectPreset": "portrait",
    "aspectRatio": "2:3",
    "imageSize": "2K",
    "mimeType": "image/png",

    "geometry": {
      "requestedAspectRatio": "2:3",
      "requestedImageSize": "2K",
      "actualWidth": 1360,
      "actualHeight": 2040,
      "actualAspectRatio": "2:3",
      "matches": true,
      "toleranceProfile": "v1"
    },

    "referenceCount": 2,
    "referencesByRole": { "face": 1, "environment": 1 },

    "providerRequestId": "interaction-id-if-available",
    "durationMs": 5120,

    "usage": {
      "imageInputTokens": 2240,
      "imageOutputTokens": 1680,
      "inputTokens": 2461,
      "thinkingTokens": null
    },

    "pricing": {
      "snapshotDate": "2026-08-10",
      "currency": "USD",
      "estimatedOutputCostUsd": 0.1008,
      "estimatedInputCostUsd": 0.0013,
      "estimatedTotalCostUsd": 0.1021,
      "estimateBasis": "vendor-token-table",
      "actualCostUsd": null
    },

    "provenance": { "providerSynthIdExpected": true },

    "budget": { "dailySpentBeforeUsd": 0.301, "dailyCapUsd": 5.0 }
  }
}
```

## 19.3 Prompt and reference trace

```jsonc
{
  "promptTrace": {
    "generationPromptSha256": "…",
    "promptSnapshotPath": "prompt.json",
    "serverProtocolId": "linh_an_generation_protocol_v1"
  },
  "referenceTrace": [
    { "assetId": "linh-an-face-master-v3", "role": "face", "sha256": "…" }
  ]
}
```

```text
RULE 19.3a  Hashes SUPPLEMENT the human-readable snapshot; they do not
            replace it if the current asset contract requires both.
RULE 19.3b  Store stable asset IDs, not host-specific absolute paths.
```

## 19.4 SynthID provenance [LOCKED]

```text
Write only:  "providerSynthIdExpected": true
NEVER write: "synthIdVerified": true   unless the application actually ran a
             verification step. It does not. Claiming a verification you did
             not perform is a provenance lie in a permanent audit record.
NEVER attempt to strip or alter provider watermarking.
```

## 19.5 Cost semantics [LOCKED]

```text
estimatedOutputCostUsd  vendor output-token price × documented tokens for the
                        chosen model + size
estimatedInputCostUsd   text input tokens + (referenceCount × image input
                        tokens) × the model's input rate
estimatedTotalCostUsd   the sum above; an ESTIMATE, clearly labelled
actualCostUsd           billing-backed ONLY. Otherwise null. Forever null is
                        an acceptable outcome.

NEVER promote an estimate to `actual` by renaming the field.
```

## 19.6 Failure manifests

```text
On provider failure:
  DO NOT create image.png
  DO NOT create a manifest that looks successful

  Write:  generation-error.json
          manifest.json with status = generation_failed  (only if the existing
          manifest contract supports a failure status additively; otherwise
          write only the existing failure trace format)

THE RULE THAT MATTERS MOST:
  a failure must never be mistakable for a successful generation, by a human
  or by a script.
```

---

# 20. BENCHMARK RESULT CONTRACT

One row per generated sample, appended to `raw-results.jsonl`:

```jsonc
{
  "benchmarkId": "stage-b-2026-08-12",
  "stage": "B",
  "provider": "nano-banana-2",
  "model": "gemini-3.1-flash-image",
  "scenario": "west-lake",
  "variant": 2,
  "lane": "identity",
  "aspectRatio": "2:3",
  "imageSize": "2K",
  "promptSha256": "…",
  "referenceSha256": ["…"],
  "geometryMatches": true,
  "durationMs": 5120,
  "estimatedTotalCostUsd": 0.1021,
  "faceQcScore": 91.4,
  "facePass": true,
  "imageDnaStatus": "pass",
  "intentStatus": "pass",
  "killSwitch": false,
  "fullGatePass": true,
  "humanRating": null,
  "attemptPath": "…",
  "excludedFromAggregation": false,
  "exclusionReason": null
}
```

```text
RULE 20.1  `excludedFromAggregation = true` for any sample where
           geometryMatches === false, or where a frozen variable drifted.
           Report exclusions in the summary — an unexplained missing sample
           is indistinguishable from cherry-picking.
RULE 20.2  Benchmark samples use the PRODUCTION artifact contract. Never
           invent a benchmark-only format that bypasses the audit path.
```

---

# 21. COST LEDGER CONTRACT [NEW — fixes D-05]

Append-only JSONL. One line per paid or possibly-paid attempt.

```jsonc
{
  "at": "2026-08-10T09:14:09+07:00",
  "runId": "run_…", "variantId": "variant-001", "attemptId": "attempt-001",
  "providerId": "nano-banana-2",
  "modelId": "gemini-3.1-flash-image",
  "imageSize": "2K",
  "estimatedTotalCostUsd": 0.1021,
  "costCertainty": "estimated",       // estimated | unknown | billed
  "outcome": "success",               // success | geometry_mismatch | failed | cancelled_after_spend
  "benchmarkId": null
}
```

## 21.1 Budget guard rules [LOCKED]

```text
BEFORE every paid call:
  spentToday = sum(estimatedTotalCostUsd) for entries with at >= local midnight
  if spentToday + estimate > IMAGE_GENERATION_DAILY_BUDGET_USD
      -> 429 IMAGE_GENERATION_BUDGET_EXCEEDED, no provider call
  alert thresholds at 70% / 85% / 100% of the cap (mirrors BudgetLedger)
  an override requires an explicit reason + approver recorded in the ledger

AFTER an ambiguous failure (timeout, aborted, crash with spendCommitted):
  still write a ledger entry with costCertainty = "unknown"
  RATIONALE: an unbilled-but-recorded entry costs you a little conservatism.
  A billed-but-unrecorded entry costs you the entire cap's integrity.

mock provider: never writes a ledger entry.
```

## 21.2 Cost estimator formula [fixes D-16]

```ts
// application/services/generation-cost-estimator.ts
//
// The vendor publishes exact token counts per output image and per input
// image, so a token-based estimate is far better than "output price only".
// It is still an ESTIMATE: thinking tokens on Pro are not predictable.
estimatedOutputCostUsd = IMAGE_OUTPUT_TOKENS[provider][size]
                       * IMAGE_OUTPUT_TOKEN_RATE[provider] / 1e6;

estimatedInputCostUsd  = ( referenceCount * IMAGE_INPUT_TOKENS_PER_IMAGE
                         + approxPromptTokens )
                       * TEXT_INPUT_TOKEN_RATE[provider] / 1e6;

estimatedTotalCostUsd  = estimatedOutputCostUsd + estimatedInputCostUsd;

// approxPromptTokens: use a conservative chars/4 heuristic and mark
// estimateBasis = "vendor-token-table". Never claim more precision than the
// heuristic supports.
```

---

# 22. ERROR TAXONOMY [LOCKED — fixes D-08]

One prefix. One table. No synonyms anywhere in the codebase.

```ts
// domain/image-generation.errors.ts
export type ImageGenerationErrorCode =
  // ---- request / policy (free failures, before any spend) ----
  | "IMAGE_GENERATION_REQUEST_INVALID"
  | "IMAGE_GENERATION_PROVIDER_INVALID"
  | "IMAGE_GENERATION_PROVIDER_DISABLED"
  | "IMAGE_GENERATION_PROVIDER_NOT_CONFIGURED"
  | "IMAGE_GENERATION_PROVIDER_NOT_ALLOWED_FOR_LANE"
  | "IMAGE_GENERATION_UNSUPPORTED_SIZE"
  | "IMAGE_GENERATION_UNSUPPORTED_ASPECT_RATIO"
  | "IMAGE_GENERATION_REFERENCE_INVALID"
  | "IMAGE_GENERATION_REFERENCE_LIMIT_EXCEEDED"
  | "IMAGE_GENERATION_ATTEMPT_ALREADY_EXISTS"
  | "IMAGE_GENERATION_BUDGET_EXCEEDED"
  | "IMAGE_GENERATION_CANCELLED_BEFORE_SPEND"
  // ---- provider (spend may already have occurred) ----
  | "IMAGE_GENERATION_RATE_LIMITED"
  | "IMAGE_GENERATION_TIMEOUT"
  | "IMAGE_GENERATION_PROVIDER_REJECTED"      // safety / policy block
  | "IMAGE_GENERATION_PROVIDER_NO_IMAGE"
  | "IMAGE_GENERATION_INVALID_IMAGE"
  | "IMAGE_GENERATION_GEOMETRY_MISMATCH"      // NEW (D-04)
  // ---- post-generation ----
  | "IMAGE_GENERATION_ARTIFACT_WRITE_FAILED"
  | "IMAGE_GENERATION_VALIDATOR_FAILED"
  | "IMAGE_GENERATION_UNKNOWN";
```

## 22.1 HTTP mapping

| Domain error | HTTP | Spend implication |
|---|---:|---|
| `REQUEST_INVALID`, `PROVIDER_INVALID`, `UNSUPPORTED_SIZE`, `UNSUPPORTED_ASPECT_RATIO`, `REFERENCE_INVALID`, `REFERENCE_LIMIT_EXCEEDED`, `PROVIDER_NOT_ALLOWED_FOR_LANE` | 400 | none |
| `ATTEMPT_ALREADY_EXISTS` | 409 | none |
| `RATE_LIMITED` | 429 | none (rejected upstream) |
| `BUDGET_EXCEEDED` | 429 | none — this is the point |
| `PROVIDER_DISABLED`, `PROVIDER_NOT_CONFIGURED` | 503 | none |
| `TIMEOUT` | 504 | **unknown — may already be billed** |
| `PROVIDER_REJECTED`, `PROVIDER_NO_IMAGE`, `INVALID_IMAGE` | 502 (or the existing project convention) | possibly billed |
| `GEOMETRY_MISMATCH` | 200 with a warning, or 502 by policy — see below | **billed** |
| `ARTIFACT_WRITE_FAILED` | 500 | **billed** — artifact lost, cost real |
| `VALIDATOR_FAILED` | 200 with `qc.status = "UNVALIDATED"` | billed, artifact intact |
| `UNKNOWN` | 500 | unknown |

```text
GEOMETRY_MISMATCH policy decision:
  The artifact IS written (we paid for it) and the manifest records the
  mismatch. The job succeeds with a warning so the human can look at the
  image. The sample is excluded from benchmark aggregation.
  It is NOT a 502, because the bytes are real and useful; it IS a loud
  warning, because the contract was not honoured.

VALIDATOR_FAILED policy:
  Existing behaviour — partial validation errors are `UNVALIDATED`. Do not
  change it. A validator crash never deletes a paid artifact and never marks
  anything approved.
```

## 22.2 Error payload shape

```jsonc
{
  "ok": false,
  "error": {
    "code": "IMAGE_GENERATION_UNSUPPORTED_SIZE",
    "message": "Nano Banana 2 Lite chỉ hỗ trợ 1K.",
    "detail": { "supportedImageSizes": ["1K"] },
    "correlationId": "…",
    "costMayHaveBeenIncurred": false
  }
}
```

```text
RULE 22.2a  `costMayHaveBeenIncurred` is REQUIRED on every error response.
            The user deciding whether to press Retry needs to know whether the
            failed attempt was free. This single boolean prevents the most
            expensive human error in the whole workflow.
RULE 22.2b  No upstream stack traces reach the browser. Log the sanitized
            internal cause with correlationId, provider, model,
            run/variant/attempt, error class, and upstream status if safe.
```

---

# PART V — INFRASTRUCTURE ADAPTERS

# 23. GEMINI ADAPTER

## 23.1 Structure

```text
infrastructure/providers/gemini/
  gemini.client.ts            create + memoize the SDK client
  gemini-image.provider.ts    implements ImageGenerationProviderPort
  gemini-request.mapper.ts    domain input -> Interactions request  (PURE)
  gemini-response.parser.ts   Interactions response -> domain result (PURE)
  gemini-error.mapper.ts      vendor error -> ImageGenerationError   (PURE)
```

```text
WHY THE MAPPER AND PARSER ARE PURE FUNCTIONS:
  They are the only parts we can test exhaustively without a network or a
  bill. Keep every branch of vendor-shape handling inside them; keep the
  provider class thin (call, await, delegate). If you find yourself writing
  an `if (response.…)` inside gemini-image.provider.ts, it belongs in the
  parser instead.
```

## 23.2 Client

```ts
// infrastructure/providers/gemini/gemini.client.ts
import { GoogleGenAI } from "@google/genai";

/**
 * Server-only. Never import this file from a React component or from any
 * module that also runs in the browser bundle.
 */
export function createGeminiClient(apiKey: string): GoogleGenAI {
  if (!apiKey) {
    throw new ImageGenerationError("IMAGE_GENERATION_PROVIDER_NOT_CONFIGURED");
  }
  return new GoogleGenAI({ apiKey });
}
```

### Credential rules [LOCKED]

```text
GEMINI_API_KEY
  server-side only
  never prefixed NEXT_PUBLIC_
  never sent to the browser
  never logged, never persisted in a manifest, never in request-header dumps
  missing -> the Gemini providers are DISABLED descriptors, not crashes
```

## 23.3 Request mapping [VERIFY the SDK types before writing this]

```ts
// infrastructure/providers/gemini/gemini-request.mapper.ts
//
// SNAKE_CASE WARNING (§2.2): the Interactions API uses snake_case keys even
// from JavaScript. `responseFormat` / `mimeType` / `aspectRatio` silently do
// nothing here — that is exactly the class of bug that makes the model return
// its default geometry. Follow the installed SDK's TypeScript types.
export function buildGeminiInteractionRequest(
  modelId: string,
  input: ProviderGenerateImageInput,
): GeminiInteractionCreateParams {
  return {
    model: modelId,

    input: [
      { type: "text", text: input.prompt },
      ...input.references.map((reference) => ({
        type: "image" as const,
        mime_type: reference.mimeType,
        data: Buffer.from(reference.bytes).toString("base64"),
      })),
    ],

    response_format: {
      type: "image",
      mime_type: "image/png",
      aspect_ratio: input.aspectRatio,   // "2:3" | "1:1" | "9:16"
      image_size: input.imageSize,       // "1K" | "2K" | "4K"  (uppercase K)
    },

    // ADR-IMG-003. Also disables previous_interaction_id and background=true,
    // neither of which VENHO uses.
    store: false,

    // NOT SET, deliberately:
    //   tools                    -> no Google Search grounding (§23.4)
    //   previous_interaction_id  -> single-turn only
    //   background               -> incompatible with store:false
  };
}
```

## 23.4 No grounding, no multi-turn state [LOCKED]

```text
Do NOT send tools: [{ type: "google_search" }]

Reasons:
  it injects uncontrolled external context into a frozen benchmark
  it can add cost
  it creates attribution/display obligations for grounded results
  it is unnecessary for identity/environment reference generation
  it is not supported at all on gemini-3.1-flash-lite-image
```

## 23.5 Response parsing and output verification [NEW — fixes D-04]

```ts
// infrastructure/providers/gemini/gemini-response.parser.ts
//
// FAIL CLOSED. A "successful" HTTP response with no usable image is a
// failure, and it is a failure that already cost money. Never paper over it.
export function parseGeminiImageResponse(
  interaction: unknown,
  providerId: ImageGenerationProviderId,
  modelId: string,
  durationMs: number,
): ProviderGenerateImageResult {
  // 1. output_image present?               else PROVIDER_NO_IMAGE
  // 2. output_image.data present?          else PROVIDER_NO_IMAGE
  // 3. base64 decodes?                     else INVALID_IMAGE
  // 4. decoded byteLength > 0?             else INVALID_IMAGE
  // 5. MIME in { image/png, image/jpeg }?  else INVALID_IMAGE
  // 6. usage / request id: OPTIONAL — tolerate absence, never fabricate
  // 7. NEVER return the raw `interaction` object to the application layer
}
```

### Geometry verification (application layer, provider-agnostic)

```ts
// application/services/image-output-verifier.ts
//
// Runs for EVERY provider, not just Gemini. OpenAI can also return something
// other than what was asked for, and the benchmark's independent variable is
// only valid if geometry is held constant.
const EXPECTED_MIN_LONG_EDGE: Record<ImageSizeTier, number> = {
  "512": 448,
  "1K":  896,
  "2K":  1792,
  "4K":  3584,
};
// Tolerance profile "v1":
//   aspect ratio: |actual - requested| <= 0.02   (ratio as a float)
//   size tier:    longEdge >= EXPECTED_MIN_LONG_EDGE[tier]
// Rationale: vendors round to model-native buckets (e.g. 1360x2040 for 2:3
// at 2K). A strict equality check would produce false failures. A ratio drift
// of 2% is invisible to the eye; a fallback to 16:9 is not, and that is
// exactly what this catches.
```

```text
On mismatch:
  keep the bytes, write the artifact, set generation.geometry.matches = false
  raise a WARNING (not a hard error) — see §22.1
  exclude the sample from benchmark aggregation
  surface it clearly in the UI: "Ảnh trả về sai tỉ lệ yêu cầu"
```

## 23.6 Error mapping

```ts
// infrastructure/providers/gemini/gemini-error.mapper.ts
// vendor 400 invalid model/param   -> IMAGE_GENERATION_REQUEST_INVALID
// vendor 401/403                   -> IMAGE_GENERATION_PROVIDER_NOT_CONFIGURED
// vendor 429                       -> IMAGE_GENERATION_RATE_LIMITED
// vendor 5xx                       -> IMAGE_GENERATION_PROVIDER_REJECTED
// safety / policy block            -> IMAGE_GENERATION_PROVIDER_REJECTED
// AbortError / deadline            -> IMAGE_GENERATION_TIMEOUT
// anything else                    -> IMAGE_GENERATION_UNKNOWN
//
// NEVER attempt to bypass a provider safety response.
// NEVER silently switch providers to route around a policy block — that is
// both a policy violation and a hidden charge on a second vendor.
```

---

# 24. OPENAI LEGACY BRIDGE ADAPTER

Current seam [DISCOVER — confirm in Phase 0]:

```text
src/app/api/v1/studio/generate-image/route.ts
  -> execFile(...)
  -> ops/VenHoSocialManager/generate_image.py
```

## 24.1 Objective

Do **not** rewrite the OpenAI implementation. Wrap it.

```ts
// infrastructure/providers/openai/openai-image-legacy.provider.ts
//
// This adapter exists so the clean application layer never depends on
// execFile. It is deliberately boring: run the existing script into a
// PROVIDER-LOCAL temp path, read the bytes back, hand them over, delete the
// temp file. The canonical artifact is written by the artifact store, not
// here (ADR-IMG-005).
export class OpenAiLegacyImageProvider implements ImageGenerationProviderPort {
  readonly id = "openai";
  async generate(input, context) {
    // 1. create a temp dir under the OS temp root (NOT under the artifact root)
    // 2. execFile(python, [scriptPath, ...args, "--out", tmpPath], { signal })
    // 3. on non-zero exit: map stderr -> ImageGenerationError, never leak raw stderr
    // 4. read tmpPath bytes, sniff MIME
    // 5. return { providerId, modelId, image, durationMs, usage? }
    // 6. finally: remove the temp dir
  }
}
```

```text
RULE 24.1a  The temp path must NEVER be inside the canonical artifact tree.
            A half-written file in the artifact tree is indistinguishable
            from a real attempt to any script that scans it.
RULE 24.1b  Propagate the correlationId into the subprocess environment so
            Python-side logs can be joined to the job.
RULE 24.1c  Pass the AbortSignal through to execFile so a platform timeout
            actually stops the child process.
```

## 24.2 Hard-coded model correction [LOCKED]

```text
REMOVE the route-level literal   model: "gpt-image-2"   from manifest creation.

The manifest model MUST come from providerResult.modelId or the resolved
descriptor. This is the exact bug §14.3's test is designed to prevent from
ever coming back.
```

## 24.3 Regression requirement [LOCKED]

```text
For a request that omits `generationProvider`:
    behaviour BEFORE this change  ==  behaviour AFTER this change
except for additive manifest metadata and internal architecture.

This is verified by a dedicated regression test file, not by inspection.
```

---

# 25. MOCK PROVIDER

```ts
// infrastructure/providers/mock/mock-image.provider.ts
// Deterministic. Zero cost. Mandatory.
// Returns tests/fixtures/images/mock-generated.png and fixed metadata:
//   { providerId: "mock", modelId: "mock-image-v1",
//     providerRequestId: "mock-request-001", durationMs: 1 }
//
// It must also be able to SIMULATE failures on demand, because the failure
// paths are the expensive ones to get wrong:
//   MOCK_IMAGE_FAILURE_MODE = none | no_image | invalid_bytes | timeout
//                           | rate_limited | geometry_mismatch
```

```text
RULE 25.1  Production builds may CONTAIN the mock adapter, but the production
           API must never allow a client to select it.
           NODE_ENV === "production"  ->  mock descriptor enabled = false.
RULE 25.2  The mock provider never writes a cost ledger entry.
RULE 25.3  Every test in this module defaults to mock. A test that needs a
           real provider does not exist in this repository (§34).
```

---

# 26. ARTIFACT STORE

## 26.1 Canonical attempt directory [DISCOVER — preserve the real convention]

```text
run-<id>/
  variant-<id>/
    attempt-001/
      image.png
      manifest.json
      prompt.json
      inputs.json
      references.json
      qc.json
```

```text
RULE 26.1a  Do NOT rename an existing production layout to match this sketch.
            Confirm the real layout in Phase 0 and keep it.
RULE 26.1b  attemptId is zero-padded to 3 digits so lexical sort == numeric
            sort. attempt-10 sorting before attempt-2 breaks every report.
```

## 26.2 Atomic write [LOCKED]

```ts
// infrastructure/storage/fs-image-artifact-store.ts
// 1. write bytes to  <finalDir>/.image.png.tmp-<random>   (SAME directory —
//    rename() is only atomic within one filesystem)
// 2. fsync the file handle, then close
// 3. verify the written size equals the buffer length
// 4. rename(tmp, image.png)  with an exclusive-create guarantee
// 5. fsync the directory if the storage policy requires durability
//
// A reader must never observe a partially written image.png. If the storage
// backend is not a POSIX filesystem, implement its equivalent atomic
// create-if-absent operation.
```

## 26.3 Hash and immutability

```text
SHA-256 over the FINAL bytes, after the write, recorded in the manifest.
Before writing: if the canonical path already exists ->
  IMAGE_GENERATION_ATTEMPT_ALREADY_EXISTS. Never overwrite. Never "upsert".
```

---

# 27. REFERENCE LOADER — PATH SAFETY [LOCKED]

```ts
// infrastructure/references/existing-reference-loader.ts
//
// Mirrors the ensure_safe_slug() hardening already applied in venho-ai-studio
// after the path-traversal review. Same threat, same answer.
function resolveAssetPath(assetId: string, root: string): string {
  assertSafeSlug(assetId);                    // ^[a-zA-Z0-9._-]+$  , no ".."
  const resolved = path.resolve(root, assetId + ".png");
  if (!resolved.startsWith(path.resolve(root) + path.sep)) {
    throw new ImageGenerationError("IMAGE_GENERATION_REFERENCE_INVALID");
  }
  return resolved;
}
```

```text
A client-supplied reference identifier must be checked against:
  the allowed project library      the current user's authorization
  the lane reference policy        the asset type
  the MIME type                    the maximum file size

NEVER permit through a generation request:
  ../../path      file:///...      an arbitrary server path
  an arbitrary remote URL          a base64 blob supplied by the client
```

## 27.1 Prompt injection boundary [LOCKED]

```text
Generation prompts and provider text output are CONTENT, never instructions.

Never let generated or provider-returned text control:
  a filesystem path · a shell command · provider selection ·
  a validator threshold · a publish target · an environment variable
```

---

# 28. CONCURRENCY AND BUDGET

## 28.1 Concurrency [LOCKED]

```text
IMAGE_GENERATION_MAX_CONCURRENCY = 2   (maximum simultaneous PAID generations)

single-process / local deployment  -> an in-memory semaphore is acceptable
multi-process / multi-instance     -> a shared lock via the existing durable
                                      job store, Redis, or Postgres

DO NOT pretend an in-memory lock protects multiple instances. If the
deployment is or may become multi-instance, use the file-backed job store's
lease mechanism, which already exists.

The lease MUST have a TTL and a stale-lease recovery path, or one crashed
worker permanently halves your throughput.
```

## 28.2 Budget guard [NEW — LOCKED, fixes D-05]

```text
Config:
  IMAGE_GENERATION_DAILY_BUDGET_USD=5.00        (OD-2)
  IMAGE_GENERATION_BUDGET_ALERT_PCT=70,85,100

Behaviour: §21.1. Ledger contract: §21.

Placement: the LAST preflight check before acquiring the lease, and the check
must re-read the ledger rather than trusting a cached total — two concurrent
workers must not both pass the check at 99% of the cap.
```

## 28.3 Retry policy [LOCKED]

```text
provider adapter automatic retries = 0
application-level automatic paid retries = 0

MANUAL retry is allowed and is a NEW attempt:
  attempt-001 failed  ->  attempt-002 is a NEW paid generation request

WHY (this is the reasoning to keep in the code comment):
  a network timeout can occur AFTER the provider accepted and billed the
  request. A hidden retry therefore creates duplicate cost, duplicate assets
  and ambiguous provenance — and it does so silently, which is worse than
  failing loudly.

EXCEPTION: none. Not for 429. Not for 5xx. Not "just once".
A 429 backoff-and-retry is still a second billable request if the first one
was actually accepted.
```

## 28.4 Timeout [DISCOVER]

```text
Use an AbortController on the provider call if the installed SDK supports it.
Configure IMAGE_GENERATION_TIMEOUT_MS against the REAL runtime limit (§16.6b).
Expected latency for calibration:
  Lite   ~ 4s          Nano Banana 2  ~ 4-10s        Pro  slower, size-dependent
Set the timeout well above the p99 you measure in Stage A, and well below the
platform limit. If those two constraints cannot both be satisfied, that is a
deployment finding to report, not a number to fudge.
```

---

# 29. RELIABILITY AND IDEMPOTENCY

## 29.1 Attempt uniqueness [LOCKED]

```text
Canonical key: runId + variantId + attemptId
Before the provider call: assert the canonical output does not exist.
If it exists: 409 IMAGE_GENERATION_ATTEMPT_ALREADY_EXISTS. Never overwrite.
```

## 29.2 Double-submit defence

```text
Layer 1  UI disables the Generate button while a job for this variant is active
Layer 2  idempotencyKey de-duplicates at the controller (§16.3)
Layer 3  canonical attempt-path uniqueness at the use case
Layer 4  the concurrency lease

Client-side prevention alone is decoration. Layers 2-4 are the real defence.
```

## 29.3 Crash recovery

```text
On worker start, scan for jobs in `generating` whose lease has expired:
  spendCommitted === false  -> safe to requeue
  spendCommitted === true   -> mark failed, costCertainty "unknown",
                               DO NOT auto-restart, surface to the operator
```

---

# 30. OBSERVABILITY

## 30.1 Structured events

```jsonc
{
  "event": "studio.image_generation.completed",
  "correlationId": "…", "jobId": "…",
  "runId": "…", "variantId": "…", "attemptId": "…",
  "provider": "nano-banana-2", "model": "gemini-3.1-flash-image",
  "imageSize": "2K", "aspectRatio": "2:3", "geometryMatches": true,
  "referenceCount": 2, "durationMs": 5120,
  "estimatedTotalCostUsd": 0.1021, "status": "success"
}
```

```jsonc
{ "event": "studio.image_generation.failed",
  "errorCode": "IMAGE_GENERATION_TIMEOUT", "costMayHaveBeenIncurred": true }
```

```jsonc
{ "event": "studio.image_generation.budget_alert",
  "thresholdPct": 85, "spentTodayUsd": 4.25, "capUsd": 5.0 }
```

## 30.2 Metrics (or a report file if no metrics backend exists)

```text
generation_requests_total{provider,model,status}
generation_duration_ms{provider,model}
generation_estimated_cost_usd{provider,model,size}
generation_geometry_mismatch_total{provider,model}
generation_full_gate_pass_total{provider,model}
generation_face_qc_score{provider,model}
generation_validator_fail_total{provider,validator}
generation_budget_spent_usd_today

Do NOT introduce a new observability platform for this integration. A
JSON/CSV benchmark report is acceptable for this version.
```

## 30.3 Log redaction [LOCKED]

```text
NEVER log:
  base64 image bytes            full reference image bytes
  the API key                   Authorization / x-goog-api-key headers
  the entire raw provider response

Prompt logging follows the EXISTING VENHO prompt audit policy — do not
loosen it and do not tighten it here.
```

---

# PART VI — UX / DX

# 31. UI SPECIFICATION

## 31.1 Provider selector

```text
Control label (EN): Image Generator
Control label (VI): Bộ tạo ảnh

Options are rendered from GET /providers. The list is NEVER hard-coded.

DO NOT label this control:  Validator · AI reviewer · Official model · Model
Generation provider and validation provider are different concepts and the
user must never be able to confuse them (A19 in the acceptance matrix).
```

## 31.2 Capability-driven controls [fixes D-17]

```text
Selecting a provider MUST immediately reshape the dependent controls:

  nano-banana-2-lite -> size selector shows 1K only
                     -> if the current lane is `identity`, the option is
                        disabled with the reason shown, not hidden
  nano-banana-pro    -> size selector shows 2K, 4K (1K removed, RULE 1.3.1c)
  nano-banana-2      -> 1K, 2K, 4K
  openai             -> whatever Phase 0 discovers

The server still enforces all of this (§14.4). The UI shapes are for UX; they
are never the security or correctness boundary.
```

## 31.3 Cost display

```text
Show, for the CURRENT provider + size selection:
  "Ước tính: ~$0,101 / ảnh (2K)"
  "Đã chi hôm nay: $0,40 / $5,00"

Always use "~" and the word "ước tính" (estimate). Input/reference tokens are
additional and thinking tokens on Pro are unpredictable.

Confirmation dialog REQUIRED when estimatedCost > IMAGE_GENERATION_CONFIRM_
ABOVE_USD (default 0.20) — i.e. 4K on Pro. The dialog states the estimate and
that a retry is a new paid attempt.
```

## 31.4 Status wording [LOCKED]

```text
NEVER show before validator + human gate:
  Official · Chính thức · Guaranteed identity · Face-lock guaranteed · Approved

Use wording mapped to the REAL pipeline states:
  Candidate            -> Ứng viên
  Generated            -> Đã tạo
  Passed automated QC  -> Đã qua QC tự động
  Ready for human review -> Chờ duyệt
  Unvalidated          -> Chưa kiểm định
```

## 31.5 Busy state

```text
While a job is active for a variant:
  disable Generate
  show the job status and attempt ID
  offer Cancel, with copy that explains cancel-after-spend (§13.4):
    "Huỷ sau khi đã gửi yêu cầu vẫn có thể bị tính phí. Ảnh (nếu có) vẫn
     được lưu lại."
```

## 31.6 Vietnamese copy strings [fixes D-19]

| Key | Vietnamese |
|---|---|
| `provider.label` | Bộ tạo ảnh |
| `provider.openai` | GPT Image (hiện tại) |
| `provider.nb2` | Nano Banana 2 — cân bằng chi phí/chất lượng |
| `provider.nbPro` | Nano Banana Pro — cao cấp, dùng khi Nano Banana 2 chưa đạt |
| `provider.nbLite` | Nano Banana 2 Lite — ảnh khách sạn, không có nhân vật |
| `provider.disabled.notConfigured` | Chưa cấu hình trên máy chủ |
| `provider.disabled.byConfig` | Đang tắt |
| `provider.forbiddenIdentityLane` | Không dùng được cho ảnh nhân vật Linh An |
| `size.label` | Độ phân giải |
| `cost.estimate` | Ước tính: ~{amount} / ảnh ({size}) |
| `cost.today` | Đã chi hôm nay: {spent} / {cap} |
| `error.notConfigured` | Gemini chưa được cấu hình trên máy chủ này. |
| `error.noImage` | Lần tạo này không trả về ảnh dùng được. |
| `error.rateLimited` | Nhà cung cấp đang giới hạn tốc độ. Thử lại sau. |
| `error.timeout` | Hết thời gian chờ. Hệ thống KHÔNG tự thử lại để tránh bị tính phí hai lần. |
| `error.budget` | Đã chạm trần chi tiêu trong ngày ({cap}). |
| `error.geometry` | Ảnh trả về sai tỉ lệ/kích thước đã yêu cầu. Ảnh vẫn được lưu để bạn xem. |
| `retry.warning` | Thử lại sẽ tạo một lần chạy MỚI và bị tính phí thêm. |

## 31.7 Accessibility

```text
The provider selector is a labelled radio group or a native select with a
visible <label>. Keyboard reachable. The disabled reason is announced via
aria-describedby, not conveyed by colour alone. The cost estimate is in the
accessible name of the Generate button, so a screen reader user knows the
price before activating it.
```

---

# 32. DEVELOPER EXPERIENCE — RULES FOR THE IMPLEMENTATION AGENT

## 32.1 Before writing any code

The agent must print:

```text
current git branch                actual generate-image route path
git status summary (file count)   actual OpenAI generator path + its model/quality args
package manager + lockfile        actual manifest writer path
test / lint / build commands      actual validator invocation path(s)
Node + Next.js version            actual durable job store path + state machine
deployment target                 actual artifact root + attempt directory shape
existing lane/reference types     existing reference asset library location
files planned to ADD              files planned to EDIT
pre-existing failures             blockers
```

Do not assume the example file tree already exists.

## 32.2 Change discipline

```text
Step 1  domain contracts + errors + registry + mock       (no vendor SDK)
Step 2  OpenAI legacy adapter + regression tests
Step 3  Gemini adapter (mapper/parser/error, mocked SDK)
Step 4  artifact store + manifest 1.2 + cost ledger
Step 5  job integration + API + capabilities + UI
Step 6  tests / typecheck / lint / build
Step 7  live benchmark — ONLY with explicit authorization

One concern per commit. A commit that touches both the Gemini mapper and the
React selector is too big to review and too big to revert.
```

## 32.3 Do not refactor unrelated code [LOCKED]

```text
This task is not permission to:
  rename Studio modules            rewrite Validator Studio
  migrate Python to TypeScript     redesign the dashboard
  change Linh An DNA               change official-gate semantics
  fix the pre-existing lint errors in design_handoff_venho_os_cockpit/
  touch the ~60 uncommitted design-token WIP files, if still present
```

```text
IF the working tree contains uncommitted user changes: report them, work
alongside them, and NEVER discard or revert them. Harry commits his own work.
```

## 32.4 No live spending without authorization [LOCKED]

```text
The agent must not call a paid Gemini or OpenAI generation endpoint until:
  Phase 7 is reached AND
  Harry has explicitly authorized a specific spend amount (OD-5) AND
  ALLOW_LIVE_IMAGE_GENERATION_TESTS=true is set in the environment.

"Just one test image to check it works" is a paid call. It counts.
```

## 32.5 Phase report format

```text
PHASE <n> REPORT
  files added      : …
  files changed    : …
  what changed     : 3-6 bullets, behaviour not prose
  contracts touched: …
  tests run        : exact commands
  results          : pass/fail counts
  NEW failures     : caused by this change
  PRE-EXISTING     : failures that were already there (§5.4)
  spend            : $0.00  (or the authorized amount and the ledger delta)
  blockers         : …
  next phase       : … and what it needs from Harry
```

## 32.6 Comment style

```text
Comment the WHY, never the WHAT.

GOOD:  // No retry here: a timeout can arrive after the provider billed us.
       // Retrying would double the charge and fork the provenance.
BAD:   // retry count is zero

Mandatory comments at these five places, because each encodes an invariant
that is invisible from the code alone:
  1. the single provider call site        -> ADR-IMG-004 (no retry)
  2. PROVIDER_MODEL_MAP                   -> single source of truth
  3. the artifact store write             -> ADR-IMG-005 (provider ≠ persistence)
  4. store: false                         -> ADR-IMG-003 (privacy/audit)
  5. the geometry verifier                -> D-04 (vendor may ignore the request)
```

---

# PART VII — QUALITY

# 33. TEST STRATEGY

```text
ABSOLUTE RULE: zero paid API calls in the automated suite. Default = mock.
```

## 33.1 Domain / unit

```text
public provider allow-list accepts the 4 public IDs
public provider allow-list REJECTS "mock"
unknown provider -> IMAGE_GENERATION_PROVIDER_INVALID, never a default
provider -> model mapping resolves for every ID
aspect preset -> ratio mapping (portrait 2:3, square 1:1, story 9:16)
image size tier validation, including rejection of "1k" and "0.5K"
reference role policy
identity-lane reference rule (existing behaviour preserved)
action-lane reference rule (standing reference disabled)
Lite is rejected in the identity lane
Pro rejects a 1K request (minimumEconomicImageSize)
reference count above the descriptor cap -> preflight failure, no provider call
attempt uniqueness
pricing lookup for every provider/size pair
cost estimator: output + input token math
cost-per-pass with zero passes -> "N/A", never Infinity, never a crash
budget guard: under cap passes · at cap blocks · concurrent double-spend blocked
```

## 33.2 Gemini request mapper

```text
text-only prompt maps to a single text input part
prompt + face reference
prompt + environment reference
prompt + face + environment
store:false is present on every request
response_format.type === "image"
aspect_ratio is the mapped ratio, not the preset
image_size uses an uppercase K
NO tools key is present (no grounding)
NO previous_interaction_id, NO background
the model is the server-resolved ID, never anything from the request
snake_case keys are used (a camelCase key in the request object fails the test)
```

## 33.3 Gemini response parser

```text
valid PNG                     -> result with bytes + mime
valid JPEG (if accepted)      -> result
missing output_image          -> PROVIDER_NO_IMAGE
empty base64                  -> INVALID_IMAGE
invalid base64                -> INVALID_IMAGE
non-image bytes               -> INVALID_IMAGE
unsupported MIME              -> INVALID_IMAGE
providerRequestId absent      -> tolerated, field undefined
usage metadata absent         -> tolerated, never fabricated
raw interaction object        -> never leaks into the returned result
```

## 33.4 Geometry verifier

```text
exact requested geometry            -> matches true
vendor-native bucket within 2%      -> matches true   (e.g. 1360x2040 @ 2:3)
16:9 returned when 2:3 requested    -> matches false, artifact still written
long edge below the tier minimum    -> matches false
zero-dimension / undecodable        -> INVALID_IMAGE
```

## 33.5 Configuration

```text
GEMINI_API_KEY missing            -> Gemini descriptors disabled, app boots
GOOGLE_ENABLED=true without a key -> startup warning + provider unavailable,
                                     OpenAI generation NOT broken
default provider = openai
an invalid IMAGE_GENERATION_DEFAULT_PROVIDER value fails fast at startup
mock disabled when NODE_ENV=production
```

## 33.6 OpenAI regression [MANDATORY]

```text
a request without generationProvider resolves to openai
prompt resolution is byte-identical to the pre-change output
lane / reference behaviour is unchanged
manifest top-level model is NOT hard-coded in the route
the existing validation path still executes
the existing response shape still satisfies the current UI
```

## 33.7 Artifact and manifest

```text
a new attempt writes a new path
an existing attempt cannot be overwritten -> ATTEMPT_ALREADY_EXISTS
a temp-write failure leaves NO final image.png
sha256 matches the written bytes
the manifest points at the correct artifact
a failed provider call produces no image.png
manifest schemaVersion is 1.2 and every 1.1 field survives
a 1.1 reader does not crash on a 1.2 manifest   <-- run the REAL reader
generation.geometry is recorded on both match and mismatch
no secret, no API key, no raw header appears anywhere in the manifest
```

## 33.8 API, job and UI

```text
API   valid openai request
      valid nano-banana-2 / -pro / -lite request via the mock adapter
      invalid provider -> 400
      "mock" from a client -> 400
      client model override -> rejected/ignored per the schema policy
      provider unavailable -> sanitized 503, no secret name leaked
      duplicate attempt -> 409
      same idempotencyKey twice -> one job, one spend
      budget exceeded -> 429 with costMayHaveBeenIncurred=false

JOB   job record carries provider/model/size/estimate
      spendCommitted flips before the provider call
      cancel while queued -> no spend
      cancel while generating -> artifact kept, cancelledAfterSpend=true
      expired lease with spendCommitted=true is NOT auto-restarted

UI    provider selector renders from the capabilities endpoint
      a disabled provider renders disabled WITH its reason
      the selected provider is included in the request
      the size options change with the provider (Lite=1K, Pro has no 1K)
      the cost estimate changes with provider and size
      Generate is disabled during an active job
      the generation provider selection does NOT alter the validation provider
      the confirm dialog appears above the cost threshold
```

## 33.9 Static, architecture and anti-duplication checks

```text
ARCHITECTURE TEST  (tests/image-generation/architecture-boundaries.test.ts)
  domain/**      imports nothing from application/ infrastructure/ interface/
                 and no vendor SDK, no node:fs, no next/*
  application/** imports no vendor SDK, no node:fs, no next/*
  only infrastructure/providers/gemini/** imports @google/genai

MODEL-STRING TEST  (tests/image-generation/provider-model-map.test.ts)
  no file outside infrastructure/config/provider-model-map.ts contains the
  literals "gemini-3", "gpt-image", or another vendor model string
  (allow-list the test fixtures and this document).
  THIS TEST IS THE GUARD AGAINST THE ORIGINAL route.ts HARD-CODED MODEL BUG.

BUILD COMMANDS — read package.json first; the expected baseline is:
  npm test -- --run
  npx tsc --noEmit
  npm run lint          (expect 2 PRE-EXISTING errors, §5.4)
  npm run build

Report separately: new failures · pre-existing failures · environment blockers.
Never report a pre-existing failure as if this change caused it, and never
report a new failure as pre-existing.
```

---

# 34. LIVE TEST POLICY [LOCKED]

## 34.1 Default

```text
Automated tests: LIVE API = OFF, always, no exceptions, no CI override.
```

## 34.2 Authorization gate

```text
A live benchmark script must refuse to run unless ALL are true:
  ALLOW_LIVE_IMAGE_GENERATION_TESTS=true
  the provider credential is present
  a --authorized-spend-usd argument is supplied and is > 0
  the projected spend (images × estimate) is <= --authorized-spend-usd
  the daily budget guard has headroom for the projected spend

The script prints the projected spend and the image count, then requires an
explicit confirmation token. It never runs on import.
```

## 34.3 CI

```text
CI uses the mock provider. Paid provider tests in CI require a separate,
explicit future policy decision that does not exist today.
```

---

# 35. BENCHMARK PROTOCOL

The purpose is to decide whether Nano Banana lowers **cost per accepted VENHO asset** and/or **crosses the Face QC ≥ 90 gate** that the current path has not crossed. It is not to decide which image is prettier.

## 35.1 Fixed scenarios

```text
01 hero      02 café      03 West Lake
04 rooftop   05 business  06 street

Use the current target library and the existing scenario definitions from
Visual DNA v2.7 / the scenario registry. Do not invent scenarios.
```

## 35.2 Frozen variables [LOCKED]

```text
scenario · generationPrompt (and its hash) · lane · outfit ·
face reference · environment reference · reference hashes ·
aspect ratio · image size tier · validator provider · validator model/version ·
Face QC version · Image DNA validator version · Intent validator version ·
human rating rubric · retry policy (zero)

The provider/model is the ONLY intended independent variable.
Any sample where a frozen variable drifted is EXCLUDED and the exclusion is
reported (§20 RULE 20.1).
```

## 35.3 Stages

| Stage | Purpose | Matrix | Images |
|---|---|---|---:|
| **A — smoke** | prove integration end to end; catch catastrophic identity/reference/format failures | 6 scenarios × 1 variant × {`nano-banana-2` @2K, `nano-banana-pro` @2K} | 12 |
| **B — decision** | produce enough samples to decide the default | 6 scenarios × 3 variants × {`nano-banana-2` @2K, OpenAI control at the SAME conditions} | 36 |
| **B′ — Pro escalation** | targeted, only for scenarios where Flash failed | ≤ 6 × 1 @2K | ≤ 6 |
| **C — hotel Lite lane** | separate, non-character question | 6 hotel scenarios × 2 variants × {`nano-banana-2-lite` @1K, `nano-banana-2` @1K} | 24 |

```text
Stage A success is NOT sufficient to switch the default provider. Ever.
Stage C can NEVER change the Linh An generator default. Different question,
different lane, different risk.
If no comparable OpenAI control exists at the same prompt/reference/size/
validator version, run a fresh OpenAI control group in Stage B. Comparing
against a historical run with a different validator version is not a control.
```

## 35.4 Artifact layout

```text
benchmark-gemini/
  benchmark-config.json          frozen variables + snapshot of descriptors
  nano-banana-2/<scenario>/variant-00N/     production attempt directories
  nano-banana-pro/…
  nano-banana-2-lite/…
  openai/…
  reports/
    raw-results.jsonl            one line per sample (§20)
    summary.json
    summary.md
    exclusions.md
```

```text
RULE 35.4a  Every variant uses the PRODUCTION run/attempt artifact contract.
            No benchmark-only format that bypasses the audit path.
RULE 35.4b  If photos-ai/2026/10-08-linh-an-official-library/benchmark-gemini/
            already exists, PRESERVE it. Do not rename historical folders.
RULE 35.4c  New directories created by this change use ISO-8601 dates
            (2026-08-10), regardless of what the historical ones look like.
RULE 35.4d  Register the benchmark reports in PRODUCTION_REGISTRY.md as
            Tier-1 internal outputs (L5 Production OS, No Orphan Output Rule).
```

## 35.5 Metrics and statistics [fixes D-15]

Per sample: the §20 contract. Aggregated per provider:

```text
fullGatePassRate  +  Wilson 95% score interval
facePassRate      +  Wilson 95% score interval
meanFaceQc, medianFaceQc, minFaceQc
validatorFailureDistribution
geometryMismatchRate
estimatedCostPerGeneratedImage
estimatedCostPerFullGatePass        ("N/A" when passes = 0)
medianGenerationLatency, p95Latency
```

```text
STATISTICAL HONESTY REQUIREMENT

At n = 18 per arm, the 95% Wilson interval around an observed 50% pass rate is
roughly ±23 percentage points. A "10 percentage point" threshold is therefore
NOT resolvable by this sample. v2.1 implied it was.

The report MUST state the interval next to every rate, and MUST NOT claim a
difference smaller than the interval is real. The decision rule below is
written to be usable despite that, by relying on absolute gate-crossing
(a binary, high-signal event) rather than on small rate differences.

If a genuinely statistically-powered comparison is ever required, that is a
separate, larger, separately-authorized benchmark — not a bigger claim made
from the same 18 images.
```

## 35.6 Default-provider decision rule [REWRITTEN — fixes D-03]

First, determine which branch applies:

```text
BRANCH SELECTION
  Let  P_openai = number of OpenAI control samples achieving a FULL GATE PASS
                  (including Face QC >= 90) under Stage B conditions.

  P_openai == 0   -> BRANCH ZERO   (this is the CURRENT expected state:
                                    live Face QC is 84.03-88.8)
  P_openai >  0   -> BRANCH NORMAL
```

### BRANCH ZERO — the baseline currently passes nothing

```text
Adopt nano-banana-2 as the default candidate generator IF:
  Z1  It produces >= 1 full-gate pass in Stage B while OpenAI produces 0.
  Z2  No QC threshold, validator, prompt, lane or reference policy was
      modified to achieve it.
  Z3  Its mean Face QC is >= the OpenAI control's mean Face QC.
  Z4  geometryMismatchRate <= 5%.
  Z5  Human review finds no systematic identity or brand defect that the
      automated QC missed.

  Cost is NOT a criterion in this branch. A provider that crosses the gate
  beats a cheaper provider that never produces a usable asset, at any price
  within the budget cap.

If BOTH providers produce 0 full-gate passes:
  -> DO NOT change the default.
  -> This is not a provider problem; it is a prompt/reference/DNA calibration
     problem. Open a separate calibration task (§35.8).
```

### BRANCH NORMAL — the baseline does pass sometimes

```text
Adopt nano-banana-2 as the default candidate generator IF ALL hold:
  N1  It passes all six scenario classes with >= 1 full-gate candidate each.
  N2  No QC threshold was reduced.
  N3  No Gemini-only prompt/reference modification was made.
  N4  Its full-gate pass rate is not materially below the OpenAI control,
      judged as: the LOWER bound of Gemini's Wilson interval is not below
      (OpenAI's observed rate − 10 points). State the intervals explicitly.
  N5  Its estimated cost per full-gate pass is lower than OpenAI's.
  N6  No material new operational failure appeared (geometry mismatch,
      timeout rate, safety blocks).
  N7  Human review shows no systematic identity/brand defect.

If N4 cannot be evaluated because no comparable control exists, say so.
Do NOT claim the criterion passed.
```

## 35.7 Pro routing rule

```text
IF nano-banana-2 fails a difficult identity/reference scenario
AND nano-banana-pro passes the SAME scenario under the SAME frozen conditions
THEN Pro may be selected MANUALLY for:
       identity master candidates · complex high-fidelity scenes ·
       near-official candidates

Never route everything to Pro. Never auto-escalate (OD-6).
```

## 35.8 Stop rule [LOCKED]

```text
IF neither nano-banana-2 nor nano-banana-pro reaches Face QC >= 90 under the
frozen current reference protocol:

  STOP the default cutover.
  Open a separate calibration task.

  DO NOT lower the Face threshold.
  DO NOT change the validator to make Gemini pass.
  DO NOT generate uncontrolled large batches hoping for a lucky sample.
  DO NOT promote a weak asset.

Note: this is the LIKELY outcome to prepare for, given the current 84-88.8
range. Plan the calibration task as a real possibility, not as a footnote.
```

## 35.9 Post-benchmark routing policy (target state, only after evidence)

```text
Linh An candidate discovery / lifestyle volume  -> nano-banana-2
Linh An complex reference / near-official       -> nano-banana-pro (manual)
Ven Hồ simple 1K non-character volume           -> nano-banana-2-lite (after Stage C)
control / rollback                              -> openai (explicit selection)

FORBIDDEN: automatic hidden failover
  "Gemini failed -> silently charge OpenAI" is a second paid request and a
  second provenance. Any fallback must be a visible, auditable, user-initiated
  new attempt.
```

---

# 36. ACCEPTANCE TEST MATRIX

| ID | Test | Expected |
|---|---|---|
| A01 | Request omits provider | Existing OpenAI behaviour, byte-identical prompt |
| A02 | Request selects `nano-banana-2` | Flash provider resolved, model from the map |
| A03 | Request selects `nano-banana-pro` | Pro resolved; a 1K request is rejected |
| A04 | Request selects an unknown provider | 400, no silent default |
| A05 | Request selects `mock` from a browser | 400 |
| A06 | Client submits a model override | Rejected/ignored per the schema policy |
| A07 | Gemini disabled by config | Safe unavailable response, provider listed as disabled |
| A08 | Gemini key missing | No secret leak, coarse `disabledReason` only |
| A09 | Identity lane + allowed face reference | Reference mapped into the request |
| A10 | Action lane + disallowed standing reference | Existing policy enforced, no provider call |
| A11 | Lite selected in the identity lane | 400 `PROVIDER_NOT_ALLOWED_FOR_LANE` |
| A12 | Gemini returns an image | Immutable artifact + manifest 1.2 created |
| A13 | Gemini returns no image | No image artifact, failure trace written |
| A14 | Gemini returns corrupt bytes | Fail closed, no artifact |
| A15 | Gemini returns 16:9 when 2:3 was requested | Artifact kept, `geometry.matches=false`, warned, excluded from benchmark |
| A16 | Duplicate attempt | 409, no overwrite |
| A17 | Same idempotencyKey twice | One job, one spend |
| A18 | Artifact write fails | No automatic paid retry, ledger entry `costCertainty=unknown` |
| A19 | Validator crashes | Artifact intact, `UNVALIDATED`, not approved |
| A20 | Daily budget reached | 429, no provider call, `costMayHaveBeenIncurred=false` |
| A21 | Cancel while queued | No spend, no artifact |
| A22 | Cancel while generating | Artifact kept, `cancelledAfterSpend=true` |
| A23 | Manifest | Provider/model from the adapter, never a literal |
| A24 | Manifest | No API key, no raw headers, no absolute host paths |
| A25 | Manifest | 1.1 reader does not crash on a 1.2 manifest |
| A26 | Cost | Dated estimate present, `actualCostUsd` null |
| A27 | UI | Generation provider is visibly separate from the validation provider |
| A28 | UI | Size options follow the selected provider's capabilities |
| A29 | Build | Existing OpenAI path non-regressed; pre-existing lint failures unchanged |
| A30 | Architecture | Boundary test and model-string test both pass |

---

# 37. DEFINITION OF READY AND DEFINITION OF DONE

## 37.1 Definition of Ready (before Phase 1) [NEW — fixes D-21]

```text
[ ] Phase 0 Discovery Inventory is complete and reported (§39.2).
[ ] The real generate-image route, OpenAI generator, manifest writer,
    validator invocation, job store and artifact root are all located.
[ ] OD-1 answered: the current gpt-image-2 quality tier and size are known.
[ ] OD-2 answered or the default cap accepted.
[ ] OD-3 answered: the module folder location follows the repo convention.
[ ] The deployment target and its hard timeout limit are known.
[ ] Pre-existing test/lint/build failures are recorded as a baseline.
[ ] The working tree state is understood and no user WIP will be discarded.
```

## 37.2 Definition of Done

### Architecture
```text
[ ] ImageGenerationProviderPort exists and is the only provider abstraction.
[ ] Domain and application import no vendor SDK (enforced by a test).
[ ] Only the Gemini infrastructure folder imports @google/genai.
[ ] The provider never writes a canonical artifact.
[ ] Model mapping has exactly one source of truth (enforced by a test).
[ ] A composition root exists; routes do not construct adapters.
[ ] OpenAI is wrapped without changing the generation protocol.
[ ] A deterministic mock provider exists, with failure simulation.
```

### Gemini
```text
[ ] nano-banana-2 -> gemini-3.1-flash-image
[ ] nano-banana-pro -> gemini-3-pro-image
[ ] nano-banana-2-lite -> gemini-3.1-flash-lite-image (shipped disabled if OD-4 says so)
[ ] @google/genai Interactions API is the only production path.
[ ] store:false on every request.
[ ] No search grounding, no multi-turn state, no background execution.
[ ] No hidden automatic retry anywhere in the path.
[ ] Missing/invalid image fails closed.
[ ] snake_case request keys verified against the installed SDK types.
```

### Cost and budget
```text
[ ] Daily budget cap enforced before every paid call.
[ ] Append-only cost ledger written on success AND on ambiguous failure.
[ ] Budget alerts at 70/85/100%.
[ ] Cost estimator uses the vendor token table, not a flat guess.
[ ] actualCostUsd remains null without billing truth.
[ ] Pro cannot be requested at 1K.
```

### API / job / UI
```text
[ ] generationProvider is allow-listed against the PUBLIC enum.
[ ] An omitted provider defaults to openai.
[ ] The browser cannot choose a model ID, a path, or the mock provider.
[ ] The capabilities endpoint drives the UI; nothing is hard-coded client-side.
[ ] Job records carry provider/model/size/estimate and spendCommitted.
[ ] Cancel semantics implemented per §13.4.
[ ] The UI separates the generation provider from the validation provider.
[ ] Estimates are shown as estimates, in Vietnamese, with today's spend.
[ ] Double-submit is guarded at all four layers.
```

### Artifacts and manifest
```text
[ ] Attempt writes are immutable; canonical writes are atomic.
[ ] SHA-256 recorded; prompt/input/reference trace preserved.
[ ] Geometry requested vs actual recorded on every attempt.
[ ] A failure can never be mistaken for a successful asset.
[ ] schemaVersion 1.2; every 1.1 field survives; the real 1.1 reader is tested.
[ ] No secrets, no raw headers, no absolute host paths in the manifest.
```

### Validation and gates
```text
[ ] Face QC threshold unchanged.
[ ] Image DNA and Intent validators unchanged.
[ ] Lane/reference policy unchanged.
[ ] Pipeline approval does not bypass human review.
[ ] No automatic official promotion anywhere in the change.
[ ] No publishing path touched.
```

### Quality
```text
[ ] Unit, mapper, parser, artifact, API, job and UI tests pass.
[ ] OpenAI regression tests pass.
[ ] Architecture boundary test and model-string test pass.
[ ] tsc --noEmit passes, or pre-existing failures are documented.
[ ] lint passes except the 2 declared pre-existing errors.
[ ] build passes.
[ ] 0 paid API calls in the full suite (verified, not assumed).
```

### Benchmark
```text
[ ] Live calls only after explicit authorization with a spend number.
[ ] Stage A covers all six scenarios.
[ ] Stage B freezes every variable in §35.2.
[ ] Wilson intervals reported next to every rate.
[ ] Cost per full-gate pass reported, with the zero-pass branch handled.
[ ] Exclusions reported with reasons.
[ ] The default-provider decision follows §35.6 and cites the evidence.
[ ] No benchmark asset became official without the normal human gate.
```

---

# PART VIII — EXECUTION

# 38. FILE TREE — TARGET STANDARDIZED STRUCTURE

## 38.1 The rule that comes before the tree [LOCKED]

```text
Architecture is dependency direction, not folder fashion.

The agent must FIRST inspect venho-os and adopt its dominant existing
convention. If the repo already organizes server code under
  src/lib/studio/…   or   src/features/…   or   src/server/…
then place the module there and keep the SAME four internal layers.

Creating src/modules/image-generation/ next to an existing equivalent
structure is a duplicate architecture, which is exactly what VENHO's
anti-duplication principle forbids. See OD-3.
```

## 38.2 Target tree (canonical layout, adapt the root per §38.1)

```text
venho-os/
│
├── src/
│   ├── app/
│   │   └── api/v1/studio/
│   │       ├── generate-image/
│   │       │   └── route.ts                      # thin controller ONLY:
│   │       │                                     #   auth · zod schema ·
│   │       │                                     #   map HTTP -> command ·
│   │       │                                     #   enqueue job · return jobId
│   │       │                                     # runtime = "nodejs" (§16.6)
│   │       ├── jobs/
│   │       │   └── route.ts                      # EXISTING. extend response only
│   │       └── image-generation/
│   │           └── providers/
│   │               └── route.ts                  # NEW. capabilities catalog (§17)
│   │
│   ├── modules/image-generation/                 # <-- or the repo's convention
│   │   │
│   │   ├── domain/                               # pure. no I/O. no SDK. no next/*
│   │   │   ├── image-generation-provider-id.ts   # PUBLIC vs INTERNAL enums (§11.1)
│   │   │   ├── image-aspect.ts                   # preset -> ratio map
│   │   │   ├── image-size.ts                     # "512"|"1K"|"2K"|"4K"
│   │   │   ├── image-reference.ts                # roles + ResolvedImageReference
│   │   │   ├── generation-lane.ts                # identity | action (re-export if it exists)
│   │   │   ├── generate-image-command.ts
│   │   │   ├── provider-descriptor.ts            # capabilities + policy
│   │   │   ├── provider-result.ts
│   │   │   ├── reference-policy.ts               # lane <-> reference rules
│   │   │   └── image-generation.errors.ts        # the ONE error taxonomy (§22)
│   │   │
│   │   ├── application/                          # orchestration. ports only.
│   │   │   ├── ports/
│   │   │   │   ├── image-generation-provider.port.ts
│   │   │   │   ├── image-artifact-store.port.ts
│   │   │   │   ├── image-reference-loader.port.ts
│   │   │   │   ├── generation-concurrency.port.ts
│   │   │   │   ├── generation-budget.port.ts     # NEW (§21)
│   │   │   │   ├── generation-job.port.ts        # NEW (§18)
│   │   │   │   └── validator-gateway.port.ts
│   │   │   │
│   │   │   ├── services/
│   │   │   │   ├── image-output-verifier.ts      # bytes + GEOMETRY (§23.5)
│   │   │   │   ├── generation-manifest.service.ts# schemaVersion 1.2 (§19)
│   │   │   │   ├── generation-cost-estimator.ts  # token math (§21.2)
│   │   │   │   ├── provider-preflight.ts         # capability + lane + caps (§14.4)
│   │   │   │   └── generation-failure-recorder.ts
│   │   │   │
│   │   │   └── use-cases/
│   │   │       └── generate-studio-image.use-case.ts   # THE single paid call site
│   │   │
│   │   ├── infrastructure/                       # everything that touches the world
│   │   │   ├── config/
│   │   │   │   ├── image-generation-env.ts       # parse + validate env (§ App. A)
│   │   │   │   ├── provider-model-map.ts         # ONLY home of model strings
│   │   │   │   ├── provider-descriptors.ts       # descriptors built from env
│   │   │   │   └── image-pricing.snapshot.ts     # dated price + token table
│   │   │   │
│   │   │   ├── registry/
│   │   │   │   └── image-provider-registry.ts
│   │   │   │
│   │   │   ├── providers/
│   │   │   │   ├── gemini/
│   │   │   │   │   ├── gemini.client.ts
│   │   │   │   │   ├── gemini-image.provider.ts  # ONE class, 3 provider IDs
│   │   │   │   │   ├── gemini-request.mapper.ts  # pure
│   │   │   │   │   ├── gemini-response.parser.ts # pure
│   │   │   │   │   └── gemini-error.mapper.ts    # pure
│   │   │   │   ├── openai/
│   │   │   │   │   └── openai-image-legacy.provider.ts  # execFile bridge (§24)
│   │   │   │   └── mock/
│   │   │   │       └── mock-image.provider.ts    # + failure simulation (§25)
│   │   │   │
│   │   │   ├── storage/
│   │   │   │   └── fs-image-artifact-store.ts    # atomic + immutable (§26)
│   │   │   ├── references/
│   │   │   │   └── existing-reference-loader.ts  # path safety (§27)
│   │   │   ├── concurrency/
│   │   │   │   └── generation-concurrency.adapter.ts
│   │   │   ├── budget/
│   │   │   │   ├── file-cost-ledger.ts           # append-only JSONL (§21)
│   │   │   │   └── budget-guard.ts
│   │   │   ├── jobs/
│   │   │   │   └── file-backed-generation-job.adapter.ts  # wraps EXISTING store
│   │   │   ├── validators/
│   │   │   │   └── existing-validator.gateway.ts # wraps EXISTING invocation
│   │   │   └── composition/
│   │   │       └── image-generation.module.ts    # THE composition root (§15)
│   │   │
│   │   └── interface/
│   │       └── http/
│   │           ├── generate-image.request-schema.ts
│   │           ├── generate-image.response-mapper.ts
│   │           └── provider-capabilities.response.ts
│   │
│   ├── components/os/studio/
│   │   ├── ImageGenerationProviderSelector.tsx   # renders from /providers
│   │   ├── ImageGenerationSizeSelector.tsx       # capability-driven (§31.2)
│   │   ├── ImageGenerationCostEstimate.tsx       # + today's spend
│   │   └── ImageGenerationConfirmDialog.tsx      # above the cost threshold
│   │
│   └── lib/studio/                               # EXISTING utilities — leave them
│
├── contracts/image-generation/                   # Contract-First (§ Part IV)
│   ├── generate-image.request.schema.json
│   ├── generate-image.response.schema.json
│   ├── provider-capabilities.response.schema.json
│   ├── generation-job.schema.json
│   ├── manifest.generation-1.2.schema.json
│   ├── cost-ledger-entry.schema.json
│   └── benchmark-sample.schema.json
│
├── ops/VenHoSocialManager/                       # LEGACY — do not move
│   ├── generate_image.py                         # wrapped, not rewritten
│   ├── validate_generated.py                     # FROZEN
│   └── validate_intent.py                        # FROZEN
│
├── scripts/image-generation/
│   ├── benchmark-providers.ts                    # requires authorization (§34.2)
│   ├── summarize-benchmark.ts                    # Wilson intervals (§35.5)
│   └── verify-pricing-snapshot.ts                # re-check the price table
│
├── tests/
│   ├── fixtures/images/
│   │   ├── mock-generated.png
│   │   ├── invalid-image.bin
│   │   ├── wrong-geometry-16x9.png
│   │   └── reference-sample.png
│   ├── fixtures/gemini/
│   │   ├── interaction-success.json
│   │   ├── interaction-no-image.json
│   │   ├── interaction-empty-data.json
│   │   └── interaction-safety-block.json
│   └── image-generation/
│       ├── architecture-boundaries.test.ts       # §33.9
│       ├── provider-model-map.test.ts            # §33.9
│       ├── provider-id-enum.test.ts
│       ├── aspect-ratio.test.ts
│       ├── image-size.test.ts
│       ├── reference-policy.test.ts
│       ├── provider-preflight.test.ts
│       ├── cost-estimator.test.ts
│       ├── budget-guard.test.ts
│       ├── gemini-request.mapper.test.ts
│       ├── gemini-response.parser.test.ts
│       ├── gemini-error.mapper.test.ts
│       ├── image-output-verifier.test.ts
│       ├── artifact-store.test.ts
│       ├── manifest-1-2-compat.test.ts
│       ├── openai-regression.test.ts
│       ├── generate-studio-image.use-case.test.ts
│       ├── generation-job.test.ts
│       ├── generate-image.route.test.ts
│       └── provider-capabilities.route.test.ts
│
├── docs/studio/image-generation/
│   ├── GOOGLE_NANO_BANANA_IMAGE_PROVIDER_CLEAN_ARCHITECTURE_PLAN_v3.0.md  # this file
│   ├── ADR-IMG-001..009.md
│   ├── BENCHMARK_PROTOCOL.md
│   └── RUNBOOK.md                                # §43
│
├── .env.example                                  # Appendix A
├── package.json
└── <lockfile>
```

## 38.3 Placement decision procedure (OD-3)

```text
1. List the existing top-level folders under src/.
2. Find where comparable server-side domain logic already lives.
3. If a Clean-Architecture-shaped module already exists, mirror its shape and
   naming exactly and place image-generation beside it.
4. Only if no such structure exists, create src/modules/image-generation/.
5. Record the decision and the reason in the Phase 1 report.
```

---

# 39. ROADMAP — MACHINE-EXECUTABLE

## 39.1 How to execute this roadmap

```text
Each phase has: GOAL · INPUTS · TASKS (with IDs) · ACCEPTANCE · STOP CONDITION.

Task IDs map to VENHO L4 Execution OS task records:
  NB-P<phase>-T<n>   e.g. NB-P3-T2
Copy them into TASKS.md with the seven-state lifecycle. Tasks marked [FAST]
qualify for the Fast Lane (<= 30 min).

RULES
  R1  Complete phases in order. Never start phase N+1 before phase N's
      acceptance passes.
  R2  Report in the §32.5 format after EVERY phase, then STOP and wait.
  R3  Never spend money before Phase 7 and never without OD-5.
  R4  If a task reveals a contradiction with a [LOCKED] decision, stop and
      raise a Change Request (§6.4).
  R5  A phase that cannot complete is reported as blocked, with the blocker.
      It is never partially completed and reported as done.
```

---

## PHASE 0 — DISCOVERY (no code)

```text
GOAL     Replace every [DISCOVER] assumption in this document with a fact.
INPUTS   The venho-os repository. This document.
SPEND    $0.00
```

| ID | Task | Output |
|---|---|---|
| NB-P0-T1 | Report git branch, uncommitted file count, and whether user WIP is present | branch + status summary |
| NB-P0-T2 | Locate `generate-image/route.ts`; enumerate EVERY current request field | field list |
| NB-P0-T3 | Locate the OpenAI invocation path (`execFile` target) | path |
| NB-P0-T4 | **Read the actual OpenAI model, quality tier and size arguments** (OD-1) | exact values |
| NB-P0-T5 | Locate the manifest writer; capture the real 1.1 field list | field list |
| NB-P0-T6 | Locate every validator invocation after generation | paths |
| NB-P0-T7 | Locate the durable job store, its state machine and its record shape | path + states |
| NB-P0-T8 | Locate the artifact root and the real attempt directory convention | path + shape |
| NB-P0-T9 | Locate the reference asset library and how references are currently resolved | path |
| NB-P0-T10 | Locate existing lane/reference types and the protocol-append code | paths |
| NB-P0-T11 | Read `package.json`: manager, scripts, Node/Next versions | commands |
| NB-P0-T12 | Determine the deployment target and its hard request/function timeout | number |
| NB-P0-T13 | Run the baseline: test / tsc / lint / build; record pre-existing failures | baseline table |
| NB-P0-T14 | Decide the module folder location per §38.3 (OD-3) | decision + reason |
| NB-P0-T15 | Produce the Discovery Inventory (§39.2) | document |

```text
ACCEPTANCE   §39.2 inventory complete; Definition of Ready (§37.1) satisfiable.
STOP         Report and WAIT. No code in Phase 0. Not one line.
```

## 39.2 Discovery Inventory format (required output of Phase 0)

```markdown
# DISCOVERY INVENTORY — <date>
## Repository state
branch · uncommitted files · user WIP present? · baseline test/lint/build results
## Current generation path
route file · request fields (complete list) · OpenAI script path
OpenAI model + quality tier + size  <-- OD-1 ANSWER
prompt assembly location · protocol-append location
## Persistence
artifact root · attempt directory shape · manifest writer · manifest 1.1 fields
## Job system
store path · state machine · record shape · cancel mechanism · poll endpoint
## Validation
validator entry points · how they are invoked · result shape
## References
asset library location · current resolution mechanism · authorization checks
## Environment
package manager · Node · Next · deployment target · hard timeout
## Decisions
module folder location (OD-3) + reason
## Deltas from the plan
<every place where reality differs from a [DISCOVER] assumption>
## Blockers
```

---

## PHASE 1 — DOMAIN, REGISTRY, MOCK, BUDGET

```text
GOAL     Build the seam. No vendor SDK. No behaviour change yet.
INPUTS   Discovery Inventory. §11 §12 §14 §21 §22.
SPEND    $0.00
```

| ID | Task |
|---|---|
| NB-P1-T1 | Domain types: provider IDs (two-tier), aspect, size, reference, lane, command, result |
| NB-P1-T2 | Error taxonomy `image-generation.errors.ts` + HTTP mapping table [FAST] |
| NB-P1-T3 | Provider descriptors + capabilities + policy fields |
| NB-P1-T4 | `provider-model-map.ts` — single source of truth [FAST] |
| NB-P1-T5 | `image-pricing.snapshot.ts` — prices + token table + snapshot date |
| NB-P1-T6 | `generation-cost-estimator.ts` — token math (§21.2) |
| NB-P1-T7 | Cost ledger + budget guard + daily cap + alerts (§21, §28.2) |
| NB-P1-T8 | Provider registry + `provider-preflight.ts` (§14.4) |
| NB-P1-T9 | Mock provider with failure simulation |
| NB-P1-T10 | Ports (all seven) |
| NB-P1-T11 | Composition root skeleton (§15) |
| NB-P1-T12 | Tests: §33.1 + architecture boundary test + model-string test |

```text
ACCEPTANCE
  [ ] new unit tests pass
  [ ] architecture boundary test passes
  [ ] model-string test passes
  [ ] existing OpenAI requests still work through the UNCHANGED old path
  [ ] tsc + build pass
STOP  Report. Wait.
```

---

## PHASE 2 — OPENAI ADAPTER + REGRESSION

```text
GOAL     Put the existing generator behind the port without changing behaviour.
INPUTS   §24. Phase 1 output.
SPEND    $0.00 (mock only)
```

| ID | Task |
|---|---|
| NB-P2-T1 | `openai-image-legacy.provider.ts`: execFile into a temp path, read bytes back |
| NB-P2-T2 | Propagate correlationId and AbortSignal into the subprocess |
| NB-P2-T3 | Map subprocess failures to the error taxonomy; never leak raw stderr |
| NB-P2-T4 | Remove the hard-coded `model: "gpt-image-2"` from manifest creation |
| NB-P2-T5 | Route the default path through the new use case (still synchronous if the job wiring is not yet done — Phase 5 completes it) |
| NB-P2-T6 | OpenAI regression tests (§33.6) |

```text
ACCEPTANCE
  [ ] a request without generationProvider behaves identically to before
  [ ] the prompt sent to OpenAI is byte-identical to the pre-change prompt
  [ ] the manifest model now comes from the descriptor, not a literal
  [ ] regression tests pass; no validator behaviour changed
STOP  Report. Wait.
```

---

## PHASE 3 — GEMINI ADAPTER (no live call)

```text
GOAL     A complete, tested Gemini adapter that has never been run for real.
INPUTS   §23. Re-verified §2.2/§2.3/§2.6.
SPEND    $0.00
```

| ID | Task |
|---|---|
| NB-P3-T1 | **Re-verify** model IDs, SDK version, request shape and price table against live vendor docs; report the delta before coding |
| NB-P3-T2 | Add `@google/genai`; pin; update the lockfile; confirm only one Google SDK |
| NB-P3-T3 | `gemini.client.ts` + credential rules |
| NB-P3-T4 | `gemini-request.mapper.ts` (pure) — snake_case, store:false, no tools |
| NB-P3-T5 | `gemini-response.parser.ts` (pure) — fail closed |
| NB-P3-T6 | `gemini-error.mapper.ts` (pure) |
| NB-P3-T7 | `gemini-image.provider.ts` — one class, parameterised by provider ID |
| NB-P3-T8 | Register `nano-banana-2`, `-pro`, `-lite` (Lite disabled per OD-4) |
| NB-P3-T9 | Fixtures + tests §33.2, §33.3, §33.5 |

```text
ACCEPTANCE
  [ ] mapper/parser/error tests pass against fixtures
  [ ] the app boots with GEMINI_API_KEY absent; Gemini shows as disabled
  [ ] OpenAI generation is unaffected when Gemini is disabled
  [ ] 0 network calls in the suite (verified)
STOP  Report, including the §2 re-verification delta. Wait.
```

---

## PHASE 4 — VERIFIER, ARTIFACT, MANIFEST 1.2

```text
GOAL     Everything that happens AFTER bytes arrive.
INPUTS   §19 §23.5 §26.
SPEND    $0.00
```

| ID | Task |
|---|---|
| NB-P4-T1 | `image-output-verifier.ts`: decode, MIME, size, **geometry** (§23.5) |
| NB-P4-T2 | Choose and wire the image-decoding library; confirm it works on the deployment target (native binaries) |
| NB-P4-T3 | Atomic + immutable artifact store; SHA-256 |
| NB-P4-T4 | Manifest 1.1 → 1.2 additive; populate `generation`, `geometry`, `pricing` |
| NB-P4-T5 | Failure recorder: `generation-error.json`, failure manifest |
| NB-P4-T6 | Wire the cost ledger write into success and ambiguous-failure paths |
| NB-P4-T7 | Tests §33.4, §33.7 — including running the REAL 1.1 reader against a 1.2 manifest |

```text
ACCEPTANCE
  [ ] geometry mismatch is detected, recorded, and does not delete the artifact
  [ ] an existing attempt cannot be overwritten
  [ ] the 1.1 reader does not crash on 1.2
  [ ] no secret appears in any manifest
STOP  Report. Wait.
```

---

## PHASE 5 — JOB, API, CAPABILITIES, UI

```text
GOAL     Make it selectable by a human, safely.
INPUTS   §16 §17 §18 §31.
SPEND    $0.00 (mock provider in the UI smoke test)
```

| ID | Task |
|---|---|
| NB-P5-T1 | Extend the job record additively (§18); `spendCommitted` before the call |
| NB-P5-T2 | Move provider execution into the job worker (ADR-IMG-008) |
| NB-P5-T3 | Cancel semantics per §13.4; crash recovery per §29.3 |
| NB-P5-T4 | Request schema: `generationProvider`, `imageSize`, `idempotencyKey`, `referenceAssetIds` |
| NB-P5-T5 | Idempotency handling (§16.3) |
| NB-P5-T6 | Route runtime declarations (§16.6) |
| NB-P5-T7 | `GET /providers` capabilities endpoint (§17) |
| NB-P5-T8 | Provider selector + capability-driven size selector |
| NB-P5-T9 | Cost estimate + today's spend + confirm dialog above the threshold |
| NB-P5-T10 | Vietnamese copy strings (§31.6); a11y (§31.7) |
| NB-P5-T11 | Tests §33.8 |

```text
ACCEPTANCE
  [ ] the UI can select a Gemini provider when configured (mock adapter in tests)
  [ ] an unconfigured provider renders disabled with a coarse reason
  [ ] size options follow provider capabilities; Pro offers no 1K
  [ ] the validation provider is untouched by the generation selection
  [ ] double-submit is blocked at all four layers
STOP  Report. Wait.
```

---

## PHASE 6 — STATIC VERIFICATION

```text
GOAL     Prove nothing else broke.
SPEND    $0.00
```

| ID | Task |
|---|---|
| NB-P6-T1 | Run the repo's real test / tsc / lint / build commands |
| NB-P6-T2 | Classify every failure: NEW vs PRE-EXISTING vs environment |
| NB-P6-T3 | Verify 0 network calls in the suite |
| NB-P6-T4 | Verify the architecture and model-string tests still pass |
| NB-P6-T5 | Update `task_status.md` and `task_memory.md` per the VENHO convention |

```text
ACCEPTANCE  New failures = 0. Pre-existing failures unchanged (§5.4).
STOP        Report. WAIT FOR EXPLICIT LIVE AUTHORIZATION (OD-5).
```

---

## PHASE 7 — STAGE A LIVE SMOKE BENCHMARK 💰

```text
GOAL     Prove the integration works against the real API, cheaply.
PRECONDITIONS  ALL of:
  [ ] Harry explicitly authorized a spend amount (OD-5)
  [ ] GEMINI_API_KEY configured
  [ ] ALLOW_LIVE_IMAGE_GENERATION_TESTS=true
  [ ] the daily budget cap has headroom
  [ ] the working tree is clean or its state is understood
SPEND    ≈ $1.41 estimated (12 images). Announce the projection BEFORE running.
```

| ID | Task |
|---|---|
| NB-P7-T1 | Freeze `benchmark-config.json`: prompts, references, hashes, validator versions |
| NB-P7-T2 | Generate 6 scenarios × 1 variant on `nano-banana-2` @2K |
| NB-P7-T3 | Generate 6 scenarios × 1 variant on `nano-banana-pro` @2K |
| NB-P7-T4 | Run the EXISTING validators, unchanged |
| NB-P7-T5 | Produce `raw-results.jsonl`, `summary.json`, `summary.md`, `exclusions.md` |
| NB-P7-T6 | Report actual spend vs projection, and the ledger delta |

```text
ACCEPTANCE
  [ ] every attempt produced an immutable artifact and a 1.2 manifest
  [ ] geometry matched on >= 95% of samples
  [ ] no secret in any output
  [ ] no asset promoted to official
STOP  Report. Wait. Stage A success does NOT authorize Stage B.
```

---

## PHASE 8 — STAGE B DECISION BENCHMARK 💰

```text
GOAL     Gather enough evidence to decide the default.
PRECONDITION  Stage A technically valid + a NEW explicit spend authorization.
SPEND    ≈ $1.82 + the OpenAI control cost. Announce before running.
```

| ID | Task |
|---|---|
| NB-P8-T1 | 6 scenarios × 3 variants on `nano-banana-2` @2K |
| NB-P8-T2 | A comparable OpenAI control group at the SAME frozen conditions |
| NB-P8-T3 | Targeted Pro escalation for scenarios where Flash failed |
| NB-P8-T4 | Aggregate with Wilson intervals (§35.5) |
| NB-P8-T5 | Determine the branch (ZERO vs NORMAL) and apply §35.6 |
| NB-P8-T6 | Write the decision with the evidence cited, and the exclusions listed |
| NB-P8-T7 | Register the reports in `PRODUCTION_REGISTRY.md` |

```text
ACCEPTANCE  A decision document exists that a sceptical reader could audit.
STOP        Report. The DECISION belongs to Harry, not to the agent.
```

---

## PHASE 9 — DEFAULT CUTOVER (configuration only)

```text
PRECONDITION  §35.6 satisfied AND Harry's explicit approval.
TASK          Change IMAGE_GENERATION_DEFAULT_PROVIDER on the server. Nothing else.
FORBIDDEN     Rewriting UI default logic. Changing the default in more than
              one place. Deleting the OpenAI path.
ACCEPTANCE    A single configuration value changed; rollback (§40) still works.
```

## PHASE 10 — STAGE C HOTEL LITE LANE 💰 (optional, separate authorization)

```text
Only if OD-4 enabled Lite. 6 hotel scenarios × 2 variants × 2 models @1K.
Lite may become the default ONLY for a restricted `hotel-simple-volume` lane,
and ONLY if it never touches Linh An identity work.
```

## PHASE 11 — RESUME OFFICIAL LIBRARY PRODUCTION

```text
The provider integration does NOT authorize official asset promotion.
Resume the existing Linh An official library plan under its own gates.
If Face QC is still below 90, the calibration task (§35.8) comes first.
```

---

# 40. ROLLBACK PLAN

## 40.1 Fast rollback (configuration first)

```bash
IMAGE_GENERATION_DEFAULT_PROVIDER=openai
IMAGE_GENERATION_GOOGLE_ENABLED=false
```

The OpenAI path must remain fully functional at all times. If disabling Google breaks OpenAI generation, the seam was built wrong and that is a release blocker.

## 40.2 Code rollback

```text
Gemini is additive, so rollback is: disable the providers, optionally hide the
UI option, retain every manifest and artifact.

NEVER delete historical Gemini attempt artifacts during a rollback.
They were paid for and they are audit evidence.
```

## 40.3 Manifest compatibility

```text
Old readers must ignore unknown additive fields. If any reader crashes on a
1.2 manifest, FIX THE READER BEFORE live rollout — not after.
Rolling back the code does not roll back the manifests already written.
```

---

# 41. EDGE CASES

| # | Situation | Required behaviour |
|---|---|---|
| 41.1 | Gemini returns text but no image | `PROVIDER_NO_IMAGE`, no `image.png`, ledger entry `costCertainty=unknown` |
| 41.2 | Gemini returns empty/invalid image data | `INVALID_IMAGE`, no artifact |
| 41.3 | Returned geometry ≠ requested | Artifact KEPT, `geometry.matches=false`, warned, excluded from the benchmark |
| 41.4 | Provider succeeded but the artifact write failed | Record `providerRequestId` + `stage=artifact_write`; NO automatic retry; the cost was real |
| 41.5 | Network timeout after the provider accepted | Ambiguous. No auto-retry. Failure trace. `costMayHaveBeenIncurred=true` |
| 41.6 | UI requests Gemini but the server has no key | Sanitized `provider_not_configured`. No silent fallback to OpenAI |
| 41.7 | Unsupported provider value | 400. No silent default |
| 41.8 | Client sends an arbitrary model ID | Ignored/rejected by the schema. Server mapping wins |
| 41.9 | Client sends an arbitrary reference path | Rejected. Only server-resolved asset IDs |
| 41.10 | Duplicate request / browser refresh | Idempotency key, then canonical attempt lock |
| 41.11 | Two workers claim the same attempt | Shared lock/unique key arbitrates; one gets 409 |
| 41.12 | Validator crashes after a valid generation | Keep the artifact and manifest; record the validation error; `UNVALIDATED`; never approved |
| 41.13 | Price catalog goes stale | The UI shows a DATED estimate; no accounting uses it; update one module |
| 41.14 | Vendor changes model behaviour | Benchmarks are tied to model ID + date + prompt/reference hashes + validator versions. A material change requires a re-benchmark |
| 41.15 | Reference count grows later | Descriptor caps fail preflight BEFORE any paid request |
| 41.16 | 4K requested where unsupported | Fail preflight. Never silently downgrade — a silent downgrade corrupts both the cost trace and the benchmark |
| 41.17 | Budget cap reached mid-benchmark | Benchmark stops cleanly, reports how many samples were produced, does not partially aggregate as if complete |
| 41.18 | Process crashes with `spendCommitted=true` | Recover as failed, `costCertainty=unknown`, never auto-restart |
| 41.19 | Job cancelled while generating | Artifact kept, `cancelledAfterSpend=true`, ledger written |
| 41.20 | The vendor deprecates a model ID mid-flight | Loud failure from the single mapping module; do not add a fallback chain |

---

# 42. RISK REGISTER [NEW]

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-01 | Nano Banana also fails Face QC ≥ 90 and the whole exercise yields no usable asset | **High** — the current baseline sits at 84–88.8 | High | §35.8 stop rule; treat the calibration task as a planned branch, not a surprise; Stage A is only $1.41 to learn this |
| R-02 | The cost claim is false because the OpenAI baseline is `medium`, not `high` | Medium | High | OD-1 + NB-P0-T4 answer it before any decision; §3.3 |
| R-03 | Vendor model IDs / API shape drift between now and implementation | Medium | Medium | `[VERIFY]` markers; NB-P3-T1 re-verification gate; a single mapping module |
| R-04 | Geometry silently wrong, invalidating the benchmark | Medium | High | §23.5 verifier is mandatory and provider-agnostic |
| R-05 | Runaway spend from a loop or a retry bug | Low | High | Zero retries; concurrency 2; daily cap; ledger; authorization gate on live scripts |
| R-06 | The agent duplicates architecture next to an existing module | Medium | Medium | §38.1/§38.3 procedure; OD-3; reviewed in the Phase 1 report |
| R-07 | The agent modifies validators or thresholds "to make it pass" | Low | Critical | §4.5 LOCKED; §35.8; acceptance A19; explicit prohibition in §32.3 |
| R-08 | The synchronous assumption collides with the durable job store and forks the execution model | Medium | High | ADR-IMG-008; Phase 5 does the wiring explicitly |
| R-09 | Uncommitted design-token WIP is clobbered | Medium | High | §32.3 rule; NB-P0-T1 reports the working tree first |
| R-10 | A secret leaks into a manifest or a log that then gets committed | Low | Critical | §30.3 redaction; A24; sanitized metadata type; a test that greps manifests for key-shaped strings |
| R-11 | The native image-decoding library does not run on the deployment target | Medium | Medium | NB-P4-T2 verifies on the target before the rest of Phase 4 depends on it |
| R-12 | Benchmark conclusions are over-claimed from 18 samples | Medium | Medium | §35.5 statistical honesty requirement; Wilson intervals mandatory in the report |

---

# 43. OPERATIONS RUNBOOK (post-implementation) [NEW]

## 43.1 Daily

```text
Check: generation_budget_spent_usd_today vs the cap.
Check: geometry mismatch count. A spike means the vendor changed something.
Check: jobs stuck in `generating` with an expired lease.
```

## 43.2 "Generation is failing" triage order

```text
1. GET /api/v1/studio/image-generation/providers
   -> is the provider enabled? what is disabledReason?
2. Read the last cost ledger entries — is the daily cap hit?
3. Read the last failed job's error code (NOT the raw provider response).
4. Map the code with §22:
     PROVIDER_NOT_CONFIGURED  -> credential/config issue, not a code issue
     RATE_LIMITED             -> wait; do NOT add a retry
     TIMEOUT                  -> check the platform limit vs IMAGE_GENERATION_TIMEOUT_MS
     GEOMETRY_MISMATCH        -> vendor behaviour change; re-verify §2.3
     PROVIDER_NO_IMAGE        -> often a safety block; read the sanitized reason
5. Only then look at code.
```

## 43.3 Monthly

```text
Run scripts/image-generation/verify-pricing-snapshot.ts and update
image-pricing.snapshot.ts if the vendor changed prices. Bump snapshotDate.
Re-read §2 and record whether any [VERIFY] fact changed.
```

## 43.4 When the vendor changes a model

```text
1. Do NOT add a fallback chain in code.
2. Update provider-model-map.ts (one line).
3. Re-run the architecture + model-string tests.
4. Treat it as a NEW model for benchmark purposes: prior results do not carry
   over. Say so in the report rather than silently reusing old numbers.
```

---

# APPENDIX A — CONFIGURATION

```bash
# ---- provider selection -------------------------------------------------
IMAGE_GENERATION_DEFAULT_PROVIDER=openai      # openai | nano-banana-2 | nano-banana-pro | nano-banana-2-lite

# ---- Google availability ------------------------------------------------
IMAGE_GENERATION_GOOGLE_ENABLED=false
IMAGE_GENERATION_LITE_ENABLED=false           # OD-4
GEMINI_API_KEY=                               # server-only, never NEXT_PUBLIC_

# ---- OpenAI (existing; discovered in Phase 0) ---------------------------
OPENAI_IMAGE_MODEL=                           # populate from NB-P0-T4
OPENAI_IMAGE_QUALITY=                         # populate from NB-P0-T4 (OD-1)

# ---- operational guards -------------------------------------------------
IMAGE_GENERATION_MAX_CONCURRENCY=2
IMAGE_GENERATION_TIMEOUT_MS=                  # < platform limit (§16.6b)
IMAGE_GENERATION_DEFAULT_IMAGE_SIZE=1K

# ---- budget (§21, §28.2) ------------------------------------------------
IMAGE_GENERATION_DAILY_BUDGET_USD=5.00        # OD-2
IMAGE_GENERATION_BUDGET_ALERT_PCT=70,85,100
IMAGE_GENERATION_CONFIRM_ABOVE_USD=0.20
IMAGE_GENERATION_COST_LEDGER_PATH=data/studio/cost-ledger.jsonl

# ---- live test protection (§34) -----------------------------------------
ALLOW_LIVE_IMAGE_GENERATION_TESTS=false
```

## A.1 Environment validation rules

```text
The app MUST start with Gemini disabled and no GEMINI_API_KEY.

IMAGE_GENERATION_GOOGLE_ENABLED=true with no key
  -> startup warning per the existing app policy
  -> the provider is reported unavailable
  -> OpenAI generation is NOT broken

IMAGE_GENERATION_DEFAULT_PROVIDER holding an unknown value
  -> fail fast at startup. A typo here silently changes which vendor you pay.

IMAGE_GENERATION_TIMEOUT_MS >= the platform limit
  -> fail fast at startup with an explanatory message (§16.6b).
```

---

# APPENDIX B — PRICING SNAPSHOT MODULE

```ts
// infrastructure/config/image-pricing.snapshot.ts
//
// UX + benchmark estimates ONLY. NOT accounting truth.
// Verified 2026-08-10. Re-verify monthly (§43.3).
export const IMAGE_PRICING_SNAPSHOT = {
  sourceDate: "2026-08-10",
  currency: "USD",
  mode: "standard",

  /** USD per 1M image OUTPUT tokens. */
  imageOutputTokenRate: {
    "nano-banana-2-lite": 30,
    "nano-banana-2": 60,
    "nano-banana-pro": 120,
  },

  /** Image output tokens consumed per generated image, by size tier. */
  imageOutputTokens: {
    "nano-banana-2-lite": { "1K": 1120 },
    "nano-banana-2": { "512": 747, "1K": 1120, "2K": 1680, "4K": 2520 },
    "nano-banana-pro": { "1K": 1120, "2K": 1120, "4K": 2000 },
  },

  /** Input image tokens consumed per REFERENCE image. */
  imageInputTokensPerReference: {
    "nano-banana-2-lite": 1120,
    "nano-banana-2": 1120,
    "nano-banana-pro": 1120,
  },

  /** Convenience: derived per-image output price. Keep in sync via a test. */
  estimatedOutputCostUsd: {
    "nano-banana-2-lite": { "1K": 0.0336 },
    "nano-banana-2": { "512": 0.0448, "1K": 0.0672, "2K": 0.1008, "4K": 0.1512 },
    "nano-banana-pro": { "1K": 0.1344, "2K": 0.1344, "4K": 0.24 },
  },
} as const;
```

```text
A TEST MUST assert estimatedOutputCostUsd == tokens × rate / 1e6 for every
entry. If someone edits one table and forgets the other, the test catches it
instead of the invoice catching it.
```

---

# APPENDIX C — COPY-PASTE PROMPTS FOR THE CODING AGENT

```text
PHASE 0
  Read this plan completely. Execute PHASE 0 (§39, NB-P0-*) only.
  Write NO application code. Produce the Discovery Inventory in the exact
  format of §39.2, including the OD-1 answer, and STOP.

PHASE 1
  Execute PHASE 1 (NB-P1-*). Domain, registry, mock, budget, ports,
  composition root, tests. No vendor SDK. No behaviour change to the existing
  OpenAI path. Report in the §32.5 format and STOP.

PHASE 2
  Execute PHASE 2 (NB-P2-*). Wrap the existing OpenAI generator behind the
  port. Remove the hard-coded manifest model. Prove byte-identical prompt
  behaviour with regression tests. Report and STOP.

PHASE 3
  Execute PHASE 3 (NB-P3-*). FIRST re-verify §2.2/§2.3/§2.6 against live
  vendor documentation and report the delta BEFORE coding. Then implement the
  Gemini adapter with mocked SDK tests only. Make zero network calls.
  Report and STOP.

PHASE 4
  Execute PHASE 4 (NB-P4-*). Output verifier including geometry, atomic
  artifact store, manifest 1.1 -> 1.2, failure recorder, cost ledger wiring.
  Run the REAL 1.1 reader against a 1.2 manifest. Report and STOP.

PHASE 5
  Execute PHASE 5 (NB-P5-*). Job integration, request schema, capabilities
  endpoint, UI with Vietnamese copy. Default provider stays openai.
  Report and STOP.

PHASE 6
  Execute PHASE 6 (NB-P6-*). Run the repo's real verification commands.
  Classify NEW vs PRE-EXISTING failures. Update task_status.md and
  task_memory.md. Report and STOP. Do not proceed to live generation.

PHASE 7  (only after Harry authorizes a specific spend)
  Execute PHASE 7 (NB-P7-*). Print the projected spend and image count and
  wait for confirmation before the first paid call. Stage A only: 12 images.
  Run the existing validators unchanged. Produce the reports. Report actual
  spend vs projection and STOP.
```

---

# APPENDIX D — EXTERNAL REFERENCES AND RE-VERIFICATION CHECKLIST

```text
https://ai.google.dev/gemini-api/docs/interactions-overview
https://ai.google.dev/gemini-api/docs/get-started
https://ai.google.dev/gemini-api/docs/image-generation
https://ai.google.dev/gemini-api/docs/migrate-to-interactions
https://ai.google.dev/gemini-api/docs/pricing
https://googleapis.github.io/js-genai/
https://deepmind.google/models/gemini-image/flash/
https://platform.openai.com/docs/pricing        (gpt-image-2 baseline)
```

## D.1 Re-verification checklist (run at NB-P3-T1 and monthly)

```text
[ ] Do gemini-3.1-flash-image / gemini-3-pro-image / gemini-3.1-flash-lite-image
    still resolve without a -preview suffix?
[ ] Does interactions.create still take response_format with snake_case keys?
[ ] Is output_image still the convenience accessor?
[ ] Is store:false still supported and still the opt-out?
[ ] Are the aspect_ratio and image_size allowed values unchanged?
[ ] Are the per-image prices and per-image token counts unchanged?
[ ] Is grounding still unsupported on the Lite model?
[ ] Has Batch or Flex become available on the Interactions API? (ADR-IMG-006/007)
[ ] Has the minimum @google/genai version changed?
```

---

# APPENDIX E — FINAL ARCHITECTURE SUMMARY

```text
Creative Studio (venho-os)
  -> existing prompt / lane / reference protocol          [UNCHANGED]
  -> durable job                                          [EXTENDED]
  -> GenerateStudioImageUseCase                           [NEW]
  -> preflight: capability · lane · uniqueness · BUDGET   [NEW]
  -> ImageGenerationProviderPort                          [NEW]
       -> OpenAI legacy adapter        (wraps generate_image.py)
       -> Nano Banana 2 adapter        (gemini-3.1-flash-image)
       -> Nano Banana Pro adapter      (gemini-3-pro-image)
       -> Nano Banana 2 Lite adapter   (gemini-3.1-flash-lite-image)
       -> Mock adapter                 (zero cost, deterministic)
  -> verified bytes + VERIFIED GEOMETRY                   [NEW]
  -> immutable, atomic, hashed artifact                   [HARDENED]
  -> manifest 1.2 + cost trace + cost ledger              [EXTENDED]
  -> existing Validator Studio                            [UNCHANGED]
  -> human review                                         [UNCHANGED]
  -> explicit official promotion                          [UNCHANGED]
```

```text
The business objective is a lower cost per ACCEPTED Linh An / Ven Hồ asset,
and a real chance of crossing the Face QC >= 90 gate.
It is not "use the cheapest provider".

The provider is replaceable.
The DNA, the validators, the immutable trace and the human official gate are
the system of record, and this change does not touch a single one of them.
```

---

**END OF PLAN v3.0**
