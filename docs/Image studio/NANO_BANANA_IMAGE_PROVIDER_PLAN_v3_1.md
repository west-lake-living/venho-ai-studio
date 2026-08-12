# NANO BANANA IMAGE PROVIDER — VENHO OS CREATIVE STUDIO — PLAN v3.1

| Field | Value |
|---|---|
| **Version** | 3.1 (scope-reduced successor to v3.0) |
| **Date** | 2026-08-10 |
| **Repo** | `venho-os` (Next.js 16 App Router, `/os`) — **only repo touched** |
| **Scope** | Add **one** alternative image generator to Creative Studio manual generation |
| **Providers after this change** | `openai` (gpt-image-2, default) · `nano-banana-2` (Gemini) · `mock` (tests only) |
| **Status** | READY FOR IMPLEMENTATION — no code executed, no paid call authorized |
| **Supersedes** | v3.0 and v2.1 of this plan, and `venho-os/docs/GOOGLE_GEMINI_IMAGE_PROVIDER_IMPLEMENTATION.md` |

---

## 0. TÓM TẮT CHO HARRY

### 0.1 Việc này làm gì

Thêm **một nút chọn** trong Creative Studio → Tạo Ảnh AI:

```
Bộ tạo ảnh:   (•) GPT Image 2  — hiện tại, mặc định
              ( ) Nano Banana 2 — Google Gemini
```

Không đổi prompt, không đổi DNA, không đổi validator, không đổi Growth Agent, không đổi mặc định. Người dùng chọn tay mỗi lần tạo ảnh.

### 0.2 Việc này KHÔNG làm

```
KHÔNG đổi provider mặc định        KHÔNG đụng Growth Agent / image_studio_runtime
KHÔNG thêm Nano Banana Pro/Lite    KHÔNG chạy benchmark quyết định
KHÔNG đổi ngưỡng Face QC           KHÔNG tự động promote ảnh official
KHÔNG đăng bài                     KHÔNG sửa 2 lỗi lint cũ trong design_handoff
```

### 0.3 Chi phí

| Provider | Giá/ảnh | Ghi chú |
|---|---:|---|
| Nano Banana 2 @1K | $0,067 | Đủ cho Facebook Page |
| Nano Banana 2 @2K | $0,101 | Dùng khi cần in hoặc zoom |
| gpt-image-2 | phụ thuộc quality tier hiện tại | **Chưa xác định — task NB-P0-T4** |

Chênh lệch ở nhịp 17 bài/tháng là dưới $2/tháng. **Đây không phải quyết định về tiền, mà về chất lượng ảnh.** Mục đích của anh là so sánh trực tiếp bằng mắt.

### 0.4 Ba thứ bắt buộc phải giữ dù scope nhỏ

1. **Kiểm tra tỉ lệ ảnh trả về.** Gemini có lỗi đã ghi nhận: bỏ qua `aspect_ratio`/`image_size` và trả về hình học mặc định. Không kiểm là trả tiền cho ảnh sai khổ mà hệ thống báo thành công.
2. **Không tự động thử lại.** Timeout có thể xảy ra *sau khi* Google đã tính tiền. Thử lại ngầm = trả tiền hai lần.
3. **Trần chi tiêu ngày.** Một vòng lặp sai có thể đốt tiền không giới hạn. Đề xuất $3/ngày.

### 0.5 Đường đi tiếp theo (sau khi anh test)

Nếu Nano Banana cho ảnh tốt hơn, bước sau là đưa nó thành generator mặc định cho **content tự động** — nhưng đó là repo khác (`venho-ai-studio/image_studio_runtime`) và là task riêng. Kiến trúc trong plan này được thiết kế để task đó chỉ phải copy contract, không phải thiết kế lại. Xem §24.

### 0.6 Cách dùng file này

Nạp nguyên file vào Claude Extension trong VS Code:

```text
Read this plan completely. Execute PHASE 0 only (§21).
Write no application code. Report the Discovery Inventory and STOP.
```

Sau mỗi phase agent phải dừng và báo cáo. Tổng cộng 6 phase, chỉ phase cuối tốn tiền (~$0,40).

---

## 1. DECISION AND SCOPE

### 1.1 Decision [LOCKED]

Add Google Gemini image generation as **one additional selectable provider** behind a server-side provider abstraction in `venho-os` Creative Studio.

```text
Public provider IDs (accepted at the HTTP boundary):
  openai            -> the OpenAI image model currently configured
  nano-banana-2     -> gemini-3.1-flash-image

Internal only (never accepted from a browser):
  mock              -> mock-image-v1, deterministic fixture, zero cost
```

```text
IMAGE_GENERATION_DEFAULT_PROVIDER=openai      [LOCKED for this change]
```

The default does not change in this task. Changing it later is a server configuration change, never a code edit and never a browser-side model ID.

### 1.2 In scope

- Gemini provider adapter (`nano-banana-2`) behind `ImageGenerationProviderPort`.
- Provider registry + single-source model mapping.
- Wrapping the existing OpenAI generator behind the same port.
- Deterministic mock provider.
- Provider selection in the HTTP request, the durable job record, and the UI.
- Provider capabilities endpoint (server-owned catalog).
- Aspect preset vs image size tier separation.
- Output byte + **geometry** verification.
- Daily budget cap + append-only cost ledger.
- Additive manifest extension `1.1 → 1.2`.
- Error taxonomy, sanitized HTTP mapping.
- Tests with zero paid calls.
- One opt-in live smoke test (6 images).

### 1.3 Out of scope [LOCKED]

```text
Nano Banana Pro / Lite            Default provider cutover
Decision benchmark (Stage B/C)    Growth Agent / image_studio_runtime
Validator Studio changes          Face QC threshold changes
Linh An DNA changes               Gemini-specific prompt engineering
Batch / Flex service tiers        Google Search grounding
Multi-turn editing                Automatic provider failover
Automatic paid retry              Automatic official promotion
Publishing                        Storage backend replacement
The 2 pre-existing lint errors in design_handoff_venho_os_cockpit/support.js
```

### 1.4 Module ownership [LOCKED]

| Runtime | Repo | Touched here? |
|---|---|---|
| Creative Studio image generation | `venho-os` (TypeScript) | **YES — the only target** |
| `image_studio_runtime` (Growth Agent) | `venho-ai-studio` (Python) | **NO — read-only. See §24** |

```text
RULE 1.4a  venho-ai-studio is READ-ONLY. Read it to learn contracts
           (BudgetLedger, manifest shape, validator invocation). Do not edit.
RULE 1.4b  One module ownership boundary per task (CLAUDE.md rule 5).
```

### 1.5 Extensibility promise

The registry is built so that adding `nano-banana-pro` or `nano-banana-2-lite` later is **one descriptor entry plus one line in the model map** — no architectural change. Do not add them now, and do not design them away either.

---

## 2. VERIFIED EXTERNAL FACTS — SNAPSHOT 2026-08-10 [VERIFY]

> Re-verify §2.1–§2.4 at the start of Phase 3 and report any delta **before** writing the adapter.

### 2.1 Naming and model ID

```text
Nano Banana 2  ->  Gemini 3.1 Flash Image  ->  gemini-3.1-flash-image
```

Product name and technical model ID are two labels for one model. There is no separate "Nano Banana API".

```text
PREVIEW-SUFFIX TRAP
  Earlier releases used gemini-3.1-flash-image-preview. Current docs use the
  un-suffixed ID. The agent MUST confirm which string the installed SDK and
  the project's API key actually accept, and put it in exactly one place
  (§7.2). A wrong model string produces a loud 404-class failure — let it
  fail loudly, never add a fallback chain.
```

Legacy `gemini-2.5-flash-image` must **not** be used. It is retiring.

### 2.2 API surface — Interactions API

```ts
// VERIFIED SHAPE 2026-08-10. Keys are snake_case even in JavaScript.
const interaction = await ai.interactions.create({
  model: "gemini-3.1-flash-image",
  input: [ /* text part + image parts */ ],
  response_format: {
    type: "image",
    mime_type: "image/png",
    aspect_ratio: "2:3",
    image_size: "1K",
  },
  store: false,
});
const base64 = interaction.output_image.data;
```

```text
CRITICAL DX NOTE
  Interactions API (ai.interactions.create) -> snake_case:
      response_format · mime_type · aspect_ratio · image_size
  Legacy generateContent / chat.sendMessage -> camelCase:
      responseFormat · mimeType · aspectRatio · imageSize · inlineData

  Writing `aspectRatio` on an Interactions request does NOT error — it is
  silently ignored, and the model returns its default geometry. This is
  almost certainly the root cause of the public "Gemini ignores my aspect
  ratio" reports. Follow the INSTALLED SDK's TypeScript types, not memory.
```

### 2.3 Supported wire values

```text
aspect_ratio: "1:1" "1:4" "1:8" "2:3" "3:2" "3:4" "4:1" "4:3" "4:5" "5:4"
              "8:1" "9:16" "16:9" "21:9"
image_size:   "512"  "1K"  "2K"  "4K"        (uppercase K; "512" not "0.5K")

VENHO uses: portrait 2:3 · square 1:1 · story 9:16 · sizes 1K / 2K
```

### 2.4 Behaviour, storage, provenance

```text
store: false      Opts out of provider-side retention. Consequence:
                  previous_interaction_id and background=true unavailable.
                  Intentional — VENHO's manifest is the audit trail. [LOCKED]

SynthID           Gemini output carries an invisible SynthID watermark.
                  Record as an EXPECTATION only. Never claim verification the
                  application did not perform. Never attempt to remove it.

Grounding         Not used. tools: [{type:"google_search"}] is FORBIDDEN here
                  — it injects uncontrolled context and can add cost.

Known defect      There are reproducible reports of the model ignoring
                  aspect_ratio / image_size. Mitigation is mandatory: §14.2.
```

### 2.5 SDK

```text
Package            @google/genai   (JavaScript/TypeScript)
Minimum version    >= 2.3.0 for Interactions API support
Do NOT install     @google/generative-ai  (the older, separate package)

The agent must: read the package manager, install a current stable version,
pin it, commit the lockfile, and confirm only ONE Google SDK is in the tree.
```

### 2.6 Pricing snapshot

| Size | Nano Banana 2 |
|---|---:|
| 1K | $0.067 |
| 2K | $0.101 |
| 4K | $0.151 |

Token math behind it: image output tokens × $60/1M. 1120 tokens @1K, 1680 @2K, 2520 @4K. Each reference image consumes ~1120 input image tokens, billed at the Flash text-input rate.

```text
gpt-image-2 baseline: token-billed, price depends on the quality tier.
UNKNOWN until NB-P0-T4 reads it from the code. Do not claim a cost
comparison before that number exists.
```

---

## 3. LOCKED VENHO INVARIANTS

### 3.1 Official quality gate

```text
An asset becomes official only when ALL hold:
  Face QC >= 90 (where applicable) · every applicable validator approves ·
  no QC kill switch · human review complete ·
  the explicit official-promotion action executed by a human

A generation provider cannot override, soften, or shortcut any of these.
```

### 3.2 Pipeline status is not human approval

`generated` · `validated` · `approved` · `usable` · `needs_review` · `revise` are pipeline states. None means "official". Preserve the existing vocabulary exactly — this change renames nothing.

### 3.3 Identity lane vs action lane

```text
identity lane (static poses)  -> may use the approved standing face reference
action lane (running, cycling, sitting, jumping, dancing, swimming, climbing…)
                              -> standing reference disabled, text-to-image forced
```

Do not modify lane logic to make Gemini look better.

### 3.4 Prompt lock

Gemini receives the existing server-resolved `generationPrompt`, including the server-appended `linh_an_generation_protocol_v1`. It never receives the raw `userPrompt`. No Gemini-specific shortcut may bypass DNA resolution, lane policy, outfit resolution, environment resolution, or the generation protocol.

### 3.5 Validator independence

Do not modify validator thresholds, prompts, reference sets, provider, or QC logic. `validate_generated.py`, `validate_intent.py`, and any other validation path found in Phase 0 are frozen. The Face Validator contract (3 gates, 5 score keys, 0–100 scale) is untouched.

### 3.6 Immutable artifacts

```text
NEVER overwrite attempt-NNN/image.png
NEVER reuse a run directory for a new paid request
NEVER replace a failed attempt with a later result
NEVER mutate an old manifest

Every retry is a NEW attempt, NEW ID, NEW directory.
```

### 3.7 No publishing, no promotion, no live calls in tests

```text
No Facebook/Instagram/Threads/Zalo publishing in this change.
No automatic official promotion.
0 paid API calls in the automated test suite. Default provider in tests = mock.
```

---

## 4. ARCHITECTURE

### 4.1 Dependency rule [LOCKED]

```text
   INTERFACE (route, React)  ──depends on──▶  APPLICATION (use case, ports)
                                                     │ depends on
                                                     ▼
                                              DOMAIN (types, rules, errors)
                                                     ▲
                                       implements ports │
                              INFRASTRUCTURE (Gemini, OpenAI, fs, job, budget)
```

```text
domain/**        must not import: @google/genai · openai · next/* · node:fs ·
                                  node:child_process · anything outward
application/**   must not import: any vendor SDK · next/* · node:fs ·
                                  anything under infrastructure/ or interface/
only infrastructure/providers/gemini/** may import @google/genai

ENFORCED BY A TEST, not by discipline: §18.6
```

### 4.2 Flow

```text
Creative Studio UI  (provider selector · size · cost estimate)
        │  POST /api/v1/studio/generate-image
        ▼
Next.js controller   runtime = "nodejs"
   auth · strict schema · map HTTP -> command · enqueue job · return jobId
        ▼
Durable job store (EXISTING, file-backed)
   queued -> generating -> validating -> succeeded/failed/cancelled
   + NEW fields: providerId · modelId · imageSize · estimatedCostUsd · spendCommitted
        ▼
GenerateStudioImageUseCase   (worker)
   preflight (free)  ─ capability · lane/reference · uniqueness · BUDGET
   ▼ ONE paid call ▼
   ImageGenerationProviderPort
        ├─ OpenAiLegacyImageProvider  (execFile generate_image.py -> bytes)
        ├─ GeminiImageProvider        (@google/genai, store:false)
        └─ MockImageProvider          (fixture, zero cost)
   ▼
   verify bytes + GEOMETRY  →  atomic immutable artifact  →  manifest 1.2
   →  cost ledger  →  EXISTING Validator Studio (unchanged)  →  human review
```

### 4.3 Composition root [LOCKED]

Exactly one place assembles the object graph. Routes and workers call it; nothing else constructs an adapter.

```ts
// infrastructure/composition/image-generation.module.ts
export function buildImageGenerationModule(
  env: ImageGenerationEnv = readImageGenerationEnv(),
): ImageGenerationModule {
  const geminiClient = env.googleEnabled ? createGeminiClient(env.geminiApiKey) : null;

  const registry = new ImageProviderRegistry({
    descriptors: buildDescriptors(env),
    providers: {
      openai: new OpenAiLegacyImageProvider({ scriptPath: env.openAiScriptPath }),
      "nano-banana-2": geminiClient
        ? new GeminiImageProvider({ client: geminiClient, providerId: "nano-banana-2" })
        : null,
      mock: env.isProduction ? null : new MockImageProvider(),
    },
  });

  return { registry, useCase: new GenerateStudioImageUseCase({ /* ports */ }) };
}
```

```text
RULE 4.3a  One instance per process. Under Next.js dev hot-reload, guard with
           a module-level singleton so clients and in-memory semaphores are
           not duplicated on every reload.
RULE 4.3b  A provider that cannot be constructed (no API key) is registered as
           a DISABLED DESCRIPTOR, not omitted. The UI must be able to show
           "Nano Banana 2 — chưa cấu hình" rather than silently hiding it.
```

---

## 5. DOMAIN MODEL

> All code here is a **contract sketch**. Adapt names and imports to the real repository and the real installed SDK types. Fidelity to the contract is mandatory; fidelity to the characters is not.

### 5.1 Provider IDs — two tiers [LOCKED]

```ts
// domain/image-generation-provider-id.ts
//
// WHY TWO TIERS: `mock` must exist internally but must be structurally
// impossible to select over HTTP. A prose rule is not enough — one missed
// check leaks a zero-cost provider into production and produces fake assets.
export const PUBLIC_IMAGE_GENERATION_PROVIDER_IDS = ["openai", "nano-banana-2"] as const;
export const INTERNAL_IMAGE_GENERATION_PROVIDER_IDS = [
  ...PUBLIC_IMAGE_GENERATION_PROVIDER_IDS, "mock",
] as const;

export type PublicImageGenerationProviderId =
  (typeof PUBLIC_IMAGE_GENERATION_PROVIDER_IDS)[number];
export type ImageGenerationProviderId =
  (typeof INTERNAL_IMAGE_GENERATION_PROVIDER_IDS)[number];
```

```text
RULE 5.1a  The HTTP schema validates against PUBLIC_* only.
RULE 5.1b  Unknown or non-public value -> 400 IMAGE_GENERATION_PROVIDER_INVALID.
           NEVER a silent fallback to openai. A silent fallback hides
           misconfiguration and bills the wrong vendor.
RULE 5.1c  mock is additionally disabled when NODE_ENV === "production".
```

### 5.2 Aspect and size

```ts
// domain/image-aspect.ts
export type ImageAspectPreset = "portrait" | "square" | "story";
export const ASPECT_RATIO_MAP = {
  portrait: "2:3", square: "1:1", story: "9:16",
} as const;
export type ImageAspectRatio = (typeof ASPECT_RATIO_MAP)[ImageAspectPreset];

// domain/image-size.ts
// Wire values. Uppercase K. "512" is typed so nobody invents "0.5K".
export type ImageSizeTier = "512" | "1K" | "2K" | "4K";
export const VENHO_SUPPORTED_IMAGE_SIZES: ImageSizeTier[] = ["1K", "2K"];
```

### 5.3 References

```ts
// domain/image-reference.ts
export type ImageReferenceRole = "face" | "environment";

/**
 * The application layer only ever sees an ALREADY-TRUSTED reference:
 * resolved from a server-side library, authorized, MIME-checked, size-checked,
 * hashed. A provider never resolves a path.
 */
export type ResolvedImageReference = {
  assetId: string;          // stable library ID, never a path
  role: ImageReferenceRole;
  mimeType: "image/png" | "image/jpeg";
  bytes: Uint8Array;
  sha256: string;
  byteLength: number;
};
```

### 5.4 Command

```ts
// domain/generate-image-command.ts
export type GenerateImageCommand = {
  runId: string;            // \
  variantId: string;        //  > ALL server-generated. Client never supplies.
  attemptId: string;        // /  zero-padded: attempt-001

  providerId: ImageGenerationProviderId;

  generationPrompt: string;           // server-resolved, protocol already appended
  generationPromptSha256: string;

  aspectPreset: ImageAspectPreset;
  aspectRatio: ImageAspectRatio;
  imageSize: ImageSizeTier;

  lane: "identity" | "action";
  references: ResolvedImageReference[];

  correlationId: string;
  jobId: string;
};
```

```text
RULE 5.4a  If the current application supports MORE fields, lanes or presets
           than this sketch, KEEP THEM. This is a minimum contract, not
           permission to delete existing behaviour.
```

### 5.5 Provider result

```ts
// domain/provider-result.ts
export type ProviderGenerateImageResult = {
  providerId: ImageGenerationProviderId;
  modelId: string;
  image: { bytes: Uint8Array; mimeType: "image/png" | "image/jpeg" };
  providerRequestId?: string;
  usage?: {
    inputTokens?: number; outputTokens?: number;
    imageInputTokens?: number; imageOutputTokens?: number;
    [key: string]: number | string | undefined;
  };
  /** SANITIZED only. This reaches the manifest, which is archived.
   *  Never place secrets, auth headers, or a raw provider response here. */
  providerMetadata?: Record<string, string | number | boolean | null | undefined>;
  durationMs: number;
};
```

### 5.6 Bytes are not an artifact [LOCKED]

```text
Returned bytes become a VENHO artifact only after ALL of:
  bytes present and non-empty · MIME accepted · a decoder can read them ·
  width > 0 and height > 0 · GEOMETRY matches the request within tolerance ·
  byte length within the configured maximum · SHA-256 computed ·
  atomic write succeeded · canonical immutable path assigned
```

---

## 6. PORTS

```ts
// application/ports/image-generation-provider.port.ts
export interface ImageGenerationProviderPort {
  readonly id: ImageGenerationProviderId;
  /** Calls upstream EXACTLY ONCE. Must not retry. Must not write to disk.
   *  Must translate vendor errors into ImageGenerationError (§16). */
  generate(
    input: { prompt: string; aspectRatio: ImageAspectRatio;
             imageSize: ImageSizeTier; references: ResolvedImageReference[] },
    context: { correlationId: string; abortSignal?: AbortSignal },
  ): Promise<ProviderGenerateImageResult>;
}
```

```ts
// application/ports/*.port.ts  — the rest, in brief
export interface ImageArtifactStorePort {
  /** Fails if the canonical path exists. Never overwrites. */
  writeImmutable(input: { runId: string; variantId: string; attemptId: string;
                          bytes: Uint8Array; mimeType: string }): Promise<PersistedArtifact>;
  exists(runId: string, variantId: string, attemptId: string): Promise<boolean>;
  writeSidecar(input: { runId: string; variantId: string; attemptId: string;
                        filename: string; content: string }): Promise<void>;
}

export interface ImageReferenceLoaderPort {
  /** Rejects path traversal, absolute paths, file:// and remote URLs,
   *  unknown IDs, unauthorized assets, bad MIME, oversize files. */
  resolve(assetIds: string[], lane: "identity" | "action"): Promise<ResolvedImageReference[]>;
}

export interface GenerationConcurrencyPort {
  acquire(input: { correlationId: string }): Promise<{ leaseId: string; release(): Promise<void> }>;
}

export interface GenerationBudgetPort {
  /** Called BEFORE the paid call. Throws when the daily cap is reached. */
  assertWithinBudget(input: { providerId: ImageGenerationProviderId;
                              estimatedCostUsd: number }): Promise<void>;
  /** Append-only. Called after success AND after ambiguous failure. */
  record(entry: CostLedgerEntry): Promise<void>;
}

export interface GenerationJobPort {
  markGenerating(jobId: string, patch: JobProviderPatch): Promise<void>;
  markValidating(jobId: string): Promise<void>;
  markSucceeded(jobId: string, result: JobResultSummary): Promise<void>;
  markFailed(jobId: string, error: SanitizedJobError): Promise<void>;
  isCancelRequested(jobId: string): Promise<boolean>;
}

export interface ValidatorGatewayPort {
  /** Wraps the EXISTING validator invocation. Behaviour must not change. */
  validate(input: { artifact: PersistedArtifact; manifest: GenerationManifest }):
    Promise<ValidatorResult>;
}
```

---

## 7. USE CASE AND REGISTRY

### 7.1 Reference algorithm

```ts
// application/use-cases/generate-studio-image.use-case.ts
//
// READ BEFORE EDITING:
//  * Exactly ONE provider call happens in this function. If you find yourself
//    adding a second call site, you are adding hidden cost.
//  * Everything before provider.generate() is free. Everything after is
//    already paid for. That boundary is why the ordering below matters:
//    all cheap rejections happen first.
export async function execute(command: GenerateImageCommand, deps: UseCaseDeps) {
  assertCommandInvariants(command);

  // ---------- FREE PREFLIGHT ----------
  const descriptor = deps.registry.getDescriptor(command.providerId);
  assertProviderEnabled(descriptor);
  assertCapabilitySupported(descriptor, command);          // size, ratio, ref caps
  assertReferencePolicy(command.lane, command.references);  // EXISTING rules

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

    // Persisted BEFORE the call: if the process dies mid-call, recovery can
    // see that money may already be gone. "We know we don't know" is operable;
    // "we don't know" is not.
    await deps.jobs.markGenerating(command.jobId, {
      providerId: descriptor.id, modelId: descriptor.modelId,
      imageSize: command.imageSize, aspectRatio: command.aspectRatio,
      estimatedCostUsd: estimate.estimatedTotalCostUsd, spendCommitted: true,
    });

    // ============ THE ONLY PAID CALL IN THIS FILE ============
    const providerResult = await deps.registry.get(command.providerId).generate(
      { prompt: command.generationPrompt, aspectRatio: command.aspectRatio,
        imageSize: command.imageSize, references: command.references },
      { correlationId: command.correlationId, abortSignal: deps.abortSignal },
    );
    // =========================================================
    // From here money is spent. Never discard the evidence: even a geometry
    // mismatch gets persisted, because we paid for those bytes.

    const verified = await deps.imageOutputVerifier.verify({
      image: providerResult.image,
      requestedAspectRatio: command.aspectRatio,
      requestedImageSize: command.imageSize,
    });

    const artifact = await deps.artifactStore.writeImmutable({
      runId: command.runId, variantId: command.variantId, attemptId: command.attemptId,
      bytes: verified.bytes, mimeType: verified.mimeType,
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

    // EXISTING Validator Studio. UNCHANGED. If it throws, the artifact and the
    // generation manifest still stand — we do not delete paid evidence.
    const qc = await deps.validatorGateway.validate({ artifact, manifest });
    await deps.manifestService.recordValidationResult({ manifest, qc });

    await deps.jobs.markSucceeded(command.jobId, summarize(artifact, qc));
    return { artifact, generation: sanitize(providerResult, verified), qc };
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

### 7.2 Model map — single source of truth [LOCKED]

```ts
// infrastructure/config/provider-model-map.ts
//
// THE ONLY PLACE A VENDOR MODEL STRING MAY APPEAR IN THE CODEBASE.
// Everywhere else reads the resolved descriptor.
export const PROVIDER_MODEL_MAP = {
  openai: process.env.OPENAI_IMAGE_MODEL ?? "<resolved in Phase 0>",
  "nano-banana-2": "gemini-3.1-flash-image",
  mock: "mock-image-v1",
} as const;
```

```text
FORBIDDEN duplication sites: route.ts · any React component · the manifest
writer · a benchmark script · the Gemini adapter · a comment used as truth.

A TEST MUST assert no vendor model string appears outside this module (§18.6).
This is the guard against the original bug where route.ts hard-coded
`model: "gpt-image-2"` straight into the manifest.
```

### 7.3 Descriptors

```ts
export type ImageGenerationProviderDescriptor = {
  id: ImageGenerationProviderId;
  displayName: string;        // "Nano Banana 2"
  displayNameVi: string;      // Vietnamese UI label
  modelId: string;            // server-side only, never sent to a client
  enabled: boolean;
  disabledReason?: "provider_not_configured" | "provider_disabled_by_config"
                 | "provider_disabled_in_production";
  capabilities: {
    supportsFaceReference: boolean;
    supportsEnvironmentReference: boolean;
    maxCharacterReferences: number;
    maxObjectReferences: number;
    supportedImageSizes: ImageSizeTier[];
    supportedAspectRatios: ImageAspectRatio[];
  };
};
```

```text
openai
  modelId       <resolved in Phase 0 from generate_image.py>
  sizes         <resolved in Phase 0 — do NOT assume>
  ratios        portrait · square · story  (existing behaviour)

nano-banana-2
  modelId               gemini-3.1-flash-image
  character references  up to 4
  object references     up to 10
  sizes                 1K · 2K
  ratios                2:3 · 1:1 · 9:16
  provider storage      disabled by VENHO (store: false)

mock
  enabled = false when NODE_ENV === "production"
```

### 7.4 Preflight rules owned by the registry [LOCKED]

```text
assertCapabilitySupported(descriptor, command):
  1. descriptor.enabled                      else PROVIDER_DISABLED
  2. imageSize ∈ supportedImageSizes         else UNSUPPORTED_SIZE
  3. aspectRatio ∈ supportedAspectRatios     else UNSUPPORTED_ASPECT_RATIO
  4. face refs  <= maxCharacterReferences    else REFERENCE_LIMIT_EXCEEDED
  5. env refs   <= maxObjectReferences       else REFERENCE_LIMIT_EXCEEDED

Enforced SERVER-SIDE before any paid call. The UI mirrors these rules for UX
but is never the enforcement point.
Never silently upgrade or downgrade a request to make it fit — a silent change
means the user did not buy what they believe they bought.
```

---

## 8. GEMINI ADAPTER

### 8.1 Structure

```text
infrastructure/providers/gemini/
  gemini.client.ts            create the SDK client (server-only)
  gemini-image.provider.ts    thin: call, await, delegate
  gemini-request.mapper.ts    domain input -> Interactions request   (PURE)
  gemini-response.parser.ts   Interactions response -> domain result (PURE)
  gemini-error.mapper.ts      vendor error -> ImageGenerationError   (PURE)
```

```text
WHY MAPPER/PARSER ARE PURE FUNCTIONS
  They are the only parts testable exhaustively without a network or a bill.
  Keep every branch of vendor-shape handling inside them. If you write an
  `if (response.…)` inside gemini-image.provider.ts, it belongs in the parser.
```

### 8.2 Client and credentials

```ts
// infrastructure/providers/gemini/gemini.client.ts
import { GoogleGenAI } from "@google/genai";
/** Server-only. Never import from a React component or browser-bundled module. */
export function createGeminiClient(apiKey: string): GoogleGenAI {
  if (!apiKey) throw new ImageGenerationError("IMAGE_GENERATION_PROVIDER_NOT_CONFIGURED");
  return new GoogleGenAI({ apiKey });
}
```

```text
GEMINI_API_KEY  server-side only · never NEXT_PUBLIC_ · never sent to the
                browser · never logged · never in a manifest · never in a
                header dump. Missing key -> DISABLED descriptor, not a crash.
```

### 8.3 Request mapper

```ts
// infrastructure/providers/gemini/gemini-request.mapper.ts
//
// SNAKE_CASE WARNING (§2.2): the Interactions API uses snake_case keys even
// from JavaScript. `responseFormat` / `aspectRatio` silently do NOTHING here,
// and the model returns its default geometry. Follow the installed SDK types.
export function buildGeminiInteractionRequest(
  modelId: string, input: ProviderGenerateImageInput,
) {
  return {
    model: modelId,
    input: [
      { type: "text", text: input.prompt },
      ...input.references.map((r) => ({
        type: "image" as const,
        mime_type: r.mimeType,
        data: Buffer.from(r.bytes).toString("base64"),
      })),
    ],
    response_format: {
      type: "image",
      mime_type: "image/png",
      aspect_ratio: input.aspectRatio,   // "2:3" | "1:1" | "9:16"
      image_size: input.imageSize,       // "1K" | "2K"  (uppercase K)
    },
    // Privacy/audit decision: VENHO's manifest is the canonical trail.
    // Also disables previous_interaction_id and background=true — neither used.
    store: false,
    // DELIBERATELY NOT SET: tools (no grounding) · previous_interaction_id ·
    // background. Grounding would inject uncontrolled context and add cost.
  };
}
```

### 8.4 Response parser — fail closed

```ts
// infrastructure/providers/gemini/gemini-response.parser.ts
// A "successful" HTTP response with no usable image is a FAILURE — and one
// that already cost money. Never paper over it.
//   1. output_image present?              else PROVIDER_NO_IMAGE
//   2. output_image.data present?         else PROVIDER_NO_IMAGE
//   3. base64 decodes?                    else INVALID_IMAGE
//   4. decoded byteLength > 0?            else INVALID_IMAGE
//   5. MIME ∈ {image/png, image/jpeg}?    else INVALID_IMAGE
//   6. usage / request id OPTIONAL — tolerate absence, never fabricate
//   7. NEVER return the raw `interaction` object to the application layer
```

### 8.5 Error mapper

```text
vendor 400 invalid model/param  -> IMAGE_GENERATION_REQUEST_INVALID
vendor 401 / 403                -> IMAGE_GENERATION_PROVIDER_NOT_CONFIGURED
vendor 429                      -> IMAGE_GENERATION_RATE_LIMITED
vendor 5xx                      -> IMAGE_GENERATION_PROVIDER_REJECTED
safety / policy block           -> IMAGE_GENERATION_PROVIDER_REJECTED
AbortError / deadline           -> IMAGE_GENERATION_TIMEOUT
anything else                   -> IMAGE_GENERATION_UNKNOWN

NEVER attempt to bypass a provider safety response.
NEVER silently switch providers to route around a policy block — that is both
a policy violation and a hidden charge on a second vendor.
```

---

## 9. OPENAI LEGACY BRIDGE

Current seam [DISCOVER — confirm in Phase 0]:

```text
src/app/api/v1/studio/generate-image/route.ts -> execFile(...) -> generate_image.py
```

```ts
// infrastructure/providers/openai/openai-image-legacy.provider.ts
//
// Deliberately boring: run the EXISTING script into a PROVIDER-LOCAL temp
// path, read the bytes, hand them over, delete the temp file. The canonical
// artifact is written by the artifact store, not here.
export class OpenAiLegacyImageProvider implements ImageGenerationProviderPort {
  readonly id = "openai";
  async generate(input, context) {
    // 1. temp dir under the OS temp root — NEVER inside the artifact tree.
    //    A half-written file in the artifact tree is indistinguishable from a
    //    real attempt to any script that scans it.
    // 2. execFile(python, [script, ...args, "--out", tmp], { signal })
    // 3. non-zero exit -> map stderr to a domain error; never leak raw stderr
    // 4. read bytes, sniff MIME
    // 5. return { providerId, modelId, image, durationMs }
    // 6. finally: remove the temp dir
  }
}
```

```text
RULE 9a  Propagate correlationId into the subprocess environment so
         Python-side logs can be joined to the job.
RULE 9b  Pass the AbortSignal into execFile so a timeout actually kills the
         child process.
RULE 9c  REMOVE the route-level literal `model: "gpt-image-2"` from manifest
         creation. The manifest model comes from providerResult.modelId.
RULE 9d  REGRESSION REQUIREMENT: a request omitting `generationProvider` must
         behave EXACTLY as before, except for additive manifest metadata.
         Verified by a dedicated test file, not by inspection.
```

---

## 10. MOCK PROVIDER

```ts
// infrastructure/providers/mock/mock-image.provider.ts
// Deterministic. Zero cost. Mandatory.
// Returns tests/fixtures/images/mock-generated.png and fixed metadata:
//   { providerId: "mock", modelId: "mock-image-v1",
//     providerRequestId: "mock-request-001", durationMs: 1 }
//
// It must SIMULATE failures on demand — failure paths are the expensive ones
// to get wrong:
//   MOCK_IMAGE_FAILURE_MODE = none | no_image | invalid_bytes | timeout
//                           | rate_limited | geometry_mismatch
```

```text
RULE 10a  Production builds may CONTAIN the mock adapter, but the production
          API must never let a client select it.
RULE 10b  The mock provider never writes a cost ledger entry.
RULE 10c  Every test in this module defaults to mock.
```

---

## 11. HTTP CONTRACT — POST /api/v1/studio/generate-image

### 11.1 Backward compatibility [LOCKED]

```text
A request omitting every new field MUST behave exactly as it does today.
This is the single most important regression guarantee of this change.
```

### 11.2 Request — additive fields only

```jsonc
{
  // EXISTING FIELDS: preserve all verbatim. The agent enumerates the real
  // current field list in Phase 0. This block shows ONLY the additions.

  "generationProvider": "nano-banana-2",   // enum PUBLIC only; absent -> default
  "imageSize": "1K",                       // "1K" | "2K"; absent -> server default
  "idempotencyKey": "8f3c1b7e-…",          // optional, opaque, <= 128 chars
  "referenceAssetIds": ["lake-view-room-env-01"]  // trusted IDs; NEVER paths
}
```

```text
generationProvider   unknown value -> 400, never a silent default
                     "mock" -> 400 (not in the public enum)
imageSize            unsupported for the provider -> 400 WITH the supported
                     list in the error detail, so the UI can self-heal
referenceAssetIds    max 8; each must resolve inside the trusted library;
                     unknown/unauthorized -> 400

REJECTED (400 where strictness does not break the current API):
  model · modelId · outputPath · imagePath · referencePath · apiKey ·
  providerHeaders
```

### 11.3 Attempt identity [LOCKED]

```text
runId · variantId · attemptId   ALL server-generated.
attemptId is zero-padded to 3 digits so lexical sort == numeric sort.
(attempt-10 sorting before attempt-2 breaks every report.)

The client may supply `idempotencyKey` only:
  same key while the original job is active  -> return the ORIGINAL jobId
  same key after a terminal state            -> return the original result
  no key                                     -> canonical attempt-path
                                                uniqueness + UI busy state
```

### 11.4 Responses

```jsonc
// accepted
{ "ok": true, "jobId": "job_2026-08-10_0007", "status": "queued",
  "generation": { "provider": "nano-banana-2", "aspectRatio": "2:3",
                  "imageSize": "1K", "estimatedCostUsd": 0.0672 } }
```

```jsonc
// completed
{ "ok": true, "jobId": "…", "status": "succeeded",
  "runId": "…", "variantId": "variant-001", "attemptId": "attempt-001",
  "generation": {
    "provider": "nano-banana-2", "model": "gemini-3.1-flash-image",
    "aspectRatio": "2:3", "imageSize": "1K",
    "geometry": { "requested": "2:3 @1K", "actual": "832x1248", "matches": true },
    "durationMs": 5120, "estimatedTotalCostUsd": 0.0683 },
  "artifact": { "path": "…", "sha256": "…", "bytes": 1482913 },
  "qc": { "…": "existing-validator-result-shape-unchanged" } }
```

```text
NEVER expose: the API key · raw provider headers · a raw provider error
object · absolute host paths outside the served whitelist · unredacted env.
```

### 11.5 Runtime requirements

```ts
// src/app/api/v1/studio/generate-image/route.ts
export const runtime = "nodejs";        // MANDATORY: fs, crypto, child_process
export const dynamic = "force-dynamic";
export const maxDuration = 60;          // seconds — see the rule below
```

```text
RULE 11.5a  MUST NOT run on the Edge runtime.
RULE 11.5b  IMAGE_GENERATION_TIMEOUT_MS must be strictly LESS than the
            platform's hard request limit. A 120s SDK timeout behind a 60s
            platform limit gives a truncated request with an unknown billing
            outcome — the worst possible failure mode.
RULE 11.5c  The agent READS the real deployment target in Phase 0 (Mac Mini
            M4 via launchd? node server? Vercel?) and chooses real numbers.
            Do not copy a number from this document into production.
```

---

## 12. HTTP CONTRACT — GET /api/v1/studio/image-generation/providers

The server owns the catalog. The UI never infers availability from browser env or a hard-coded list.

```jsonc
{
  "defaultProvider": "openai",
  "pricingSnapshotDate": "2026-08-10",
  "currency": "USD",
  "dailyBudget": { "capUsd": 3.0, "spentUsd": 0.201, "remainingUsd": 2.799, "state": "ok" },
  "providers": [
    { "id": "openai", "label": "GPT Image 2", "labelVi": "GPT Image 2 — hiện tại",
      "enabled": true,
      "capabilities": { "supportedImageSizes": ["1K"],
                        "supportedAspectRatios": ["2:3","1:1","9:16"],
                        "maxCharacterReferences": 1 },
      "estimatedOutputCostUsd": { "1K": null },
      "note": "Chi phí phụ thuộc quality tier đang cấu hình." },

    { "id": "nano-banana-2", "label": "Nano Banana 2", "labelVi": "Nano Banana 2 — Google",
      "model": "gemini-3.1-flash-image", "enabled": true,
      "capabilities": { "supportedImageSizes": ["1K","2K"],
                        "supportedAspectRatios": ["2:3","1:1","9:16"],
                        "maxCharacterReferences": 4, "maxObjectReferences": 10 },
      "estimatedOutputCostUsd": { "1K": 0.067, "2K": 0.101 } }
  ]
}
```

```text
RULE 12a  `mock` NEVER appears here.
RULE 12b  A provider without credentials appears with enabled=false and a
          COARSE disabledReason. Never leak which env var is missing.
RULE 12c  openai cost stays `null` until Phase 0 answers it. A null is honest;
          a guessed number becomes a false comparison.
RULE 12d  Cache TTL <= 60s or none — the budget block changes as money is spent.
RULE 12e  What the UI can select, the server must accept, and vice versa.
          Drift between the two is a bug, not a UX detail.
```

---

## 13. DURABLE JOB RECORD — ADDITIVE

```jsonc
{
  "jobId": "job_2026-08-10_0007",
  "state": "generating",   // queued|generating|validating|succeeded|failed|cancelled
  "runId": "…", "variantId": "…", "attemptId": "attempt-001",
  "correlationId": "…", "idempotencyKey": "…",

  // ---------- ADDITIVE BLOCK ----------
  "provider": {
    "id": "nano-banana-2", "modelId": "gemini-3.1-flash-image",
    "aspectPreset": "portrait", "aspectRatio": "2:3", "imageSize": "1K",
    "estimatedCostUsd": 0.0672,
    "spendCommitted": false,
    "cancelledAfterSpend": false
  },
  "error": null            // sanitized shape only; never a raw vendor object
}
```

### 13.1 Cancel semantics [LOCKED]

```text
cancel while `queued`      -> cancelled. No spend, no artifact, no ledger entry.

cancel while `generating`  -> let the in-flight call FINISH, persist the
                              artifact and manifest, THEN mark cancelled with
                              cancelledAfterSpend = true, and write the ledger.
                              Aborting mid-call does not un-bill the request.
                              Discarding an image you already paid for is
                              strictly worse than keeping it.

cancel while `validating`  -> let validation finish. It is free and useful.

NEVER report a cancelled-after-spend job as "no cost incurred".
```

### 13.2 Crash recovery

```text
On worker start, scan jobs in `generating` with an expired lease:
  spendCommitted === false -> safe to requeue
  spendCommitted === true  -> mark failed, costCertainty "unknown",
                              DO NOT auto-restart, surface to the operator
```

---

## 14. ARTIFACT, GEOMETRY, MANIFEST

### 14.1 Artifact store [LOCKED]

```text
Canonical layout [DISCOVER — preserve the real one found in Phase 0]:
  run-<id>/variant-<id>/attempt-001/
      image.png · manifest.json · prompt.json · inputs.json ·
      references.json · qc.json

ATOMIC WRITE:
  1. write bytes to <finalDir>/.image.png.tmp-<random>   (SAME directory —
     rename() is only atomic within one filesystem)
  2. fsync the handle, then close
  3. verify written size == buffer length
  4. rename(tmp, image.png) with exclusive-create semantics
  5. fsync the directory if durability policy requires

A reader must never observe a partially written image.png.
Before writing: if the canonical path exists -> ATTEMPT_ALREADY_EXISTS.
Never overwrite. Never "upsert".
SHA-256 over the FINAL bytes, recorded in the manifest.
```

### 14.2 Geometry verification [MANDATORY]

```ts
// application/services/image-output-verifier.ts
// Runs for EVERY provider, not just Gemini.
const EXPECTED_MIN_LONG_EDGE: Record<ImageSizeTier, number> = {
  "512": 448, "1K": 896, "2K": 1792, "4K": 3584,
};
// Tolerance profile "v1":
//   aspect ratio: |actual - requested| <= 0.02 (as a float)
//   size tier:    longEdge >= EXPECTED_MIN_LONG_EDGE[tier]
//
// Vendors round to model-native buckets (e.g. 832x1248 for 2:3 @1K), so a
// strict equality check produces false failures. A 2% ratio drift is
// invisible; a silent fallback to 16:9 is not — and that is what this catches.
```

```text
On mismatch:
  KEEP the bytes and write the artifact (we paid for them)
  set generation.geometry.matches = false
  raise a WARNING, not a hard failure
  surface it in the UI: "Ảnh trả về sai tỉ lệ yêu cầu"
  NEVER silently resize. NEVER silently retry.
```

### 14.3 Manifest `schemaVersion` 1.1 → 1.2 [LOCKED, ADDITIVE ONLY]

```text
Keep EVERY existing 1.1 field with the same meaning:
  promptHash · outfit requested/effective · scenarioProfile ·
  face reference set version · validation contract · latency/retry ·
  generationLane · effective reference mode · exact submitted prompt ·
  server-added prompt · action protocol · DNA version · validator result

Keep the top-level legacy `model` field and populate it from
providerResult.modelId — NEVER from a hard-coded literal.
```

```jsonc
{
  "schemaVersion": "1.2",
  "model": "gemini-3.1-flash-image",
  "generation": {
    "provider": "nano-banana-2", "model": "gemini-3.1-flash-image",
    "api": "gemini-interactions", "storeProviderInteraction": false,
    "aspectPreset": "portrait", "aspectRatio": "2:3", "imageSize": "1K",
    "mimeType": "image/png",
    "geometry": { "requestedAspectRatio": "2:3", "requestedImageSize": "1K",
                  "actualWidth": 832, "actualHeight": 1248,
                  "matches": true, "toleranceProfile": "v1" },
    "referenceCount": 1, "referencesByRole": { "environment": 1 },
    "providerRequestId": "…", "durationMs": 5120,
    "usage": { "imageInputTokens": 1120, "imageOutputTokens": 1120 },
    "pricing": { "snapshotDate": "2026-08-10", "currency": "USD",
                 "estimatedOutputCostUsd": 0.0672,
                 "estimatedInputCostUsd": 0.0011,
                 "estimatedTotalCostUsd": 0.0683,
                 "estimateBasis": "vendor-token-table",
                 "actualCostUsd": null },
    "provenance": { "providerSynthIdExpected": true },
    "budget": { "dailySpentBeforeUsd": 0.201, "dailyCapUsd": 3.0 }
  }
}
```

```text
RULE 14.3a  Write only providerSynthIdExpected. NEVER synthIdVerified — the
            application performs no verification, and claiming one is a
            provenance lie in a permanent audit record.
RULE 14.3b  actualCostUsd is billing-backed ONLY. Otherwise null, forever if
            need be. Never promote an estimate by renaming the field.
RULE 14.3c  A 1.1 reader must not crash on a 1.2 manifest. Test with the REAL
            reader. If it crashes, fix the reader BEFORE shipping.
```

### 14.4 Failure output

```text
On provider failure:
  DO NOT create image.png
  DO NOT create a manifest that looks successful
  Write generation-error.json, and a failure-status manifest only if the
  existing contract supports it additively.

THE RULE THAT MATTERS MOST: a failure must never be mistakable for a
successful generation — by a human or by a script.
```

---

## 15. SAFETY, BUDGET, RELIABILITY

### 15.1 Reference path safety [LOCKED]

```ts
// infrastructure/references/existing-reference-loader.ts
// Mirrors the ensure_safe_slug() hardening already applied in venho-ai-studio
// after the path-traversal review. Same threat, same answer.
function resolveAssetPath(assetId: string, root: string): string {
  assertSafeSlug(assetId);                       // ^[A-Za-z0-9._-]+$ , no ".."
  const resolved = path.resolve(root, `${assetId}.png`);
  if (!resolved.startsWith(path.resolve(root) + path.sep)) {
    throw new ImageGenerationError("IMAGE_GENERATION_REFERENCE_INVALID");
  }
  return resolved;
}
```

```text
Check every reference against: the allowed project library · the user's
authorization · the lane reference policy · asset type · MIME · max size.

NEVER permit through a generation request:
  ../../path · file:///… · an arbitrary server path · an arbitrary remote URL ·
  a client-supplied base64 blob

PROMPT INJECTION BOUNDARY: prompts and provider text output are CONTENT,
never instructions. They must never control a path, a shell command, provider
selection, a validator threshold, or an environment variable.
```

### 15.2 Budget guard [LOCKED]

```bash
IMAGE_GENERATION_DAILY_BUDGET_USD=3.00
IMAGE_GENERATION_BUDGET_ALERT_PCT=70,85,100
```

```text
BEFORE every paid call:
  spentToday = sum(estimatedTotalCostUsd) since local midnight
  if spentToday + estimate > cap -> 429 IMAGE_GENERATION_BUDGET_EXCEEDED,
     no provider call
  alerts at 70/85/100% (mirrors the existing BudgetLedger policy)
  an override requires a reason + approver recorded in the ledger

Re-read the ledger at check time; do not trust a cached total. Two concurrent
workers must not both pass at 99% of the cap.

AFTER an ambiguous failure (timeout, crash with spendCommitted):
  STILL write a ledger entry with costCertainty = "unknown".
  An unbilled-but-recorded entry costs a little conservatism.
  A billed-but-unrecorded entry costs the cap's entire integrity.
```

Ledger line (append-only JSONL):

```jsonc
{ "at": "2026-08-10T09:14:09+07:00", "runId": "…", "variantId": "…",
  "attemptId": "attempt-001", "providerId": "nano-banana-2",
  "modelId": "gemini-3.1-flash-image", "imageSize": "1K",
  "estimatedTotalCostUsd": 0.0683,
  "costCertainty": "estimated",          // estimated | unknown | billed
  "outcome": "success" }                 // success | geometry_mismatch | failed | cancelled_after_spend
```

Estimator:

```text
estimatedOutputCostUsd = IMAGE_OUTPUT_TOKENS[provider][size] * RATE[provider] / 1e6
estimatedInputCostUsd  = (referenceCount * 1120 + approxPromptTokens)
                       * TEXT_INPUT_RATE[provider] / 1e6
approxPromptTokens: conservative chars/4 heuristic. Mark estimateBasis
"vendor-token-table". Never claim more precision than the heuristic supports.
```

### 15.3 Concurrency and retry [LOCKED]

```text
IMAGE_GENERATION_MAX_CONCURRENCY = 2  (simultaneous PAID generations)
  single-process  -> an in-memory semaphore is acceptable
  multi-instance  -> a shared lease via the existing durable job store
  Do NOT pretend an in-memory lock protects multiple instances.
  The lease needs a TTL and stale-lease recovery, or one crashed worker
  permanently halves throughput.

RETRIES = 0. Provider adapter: 0. Application: 0. No exceptions.
  Not for 429. Not for 5xx. Not "just once".

WHY (keep this as a code comment at the call site):
  a network timeout can occur AFTER the provider accepted and billed the
  request. A hidden retry creates duplicate cost, duplicate assets and
  ambiguous provenance — silently, which is worse than failing loudly.

MANUAL retry is allowed and is a NEW attempt:
  attempt-001 failed -> attempt-002 is a NEW paid generation.
```

### 15.4 Double-submit defence

```text
Layer 1  UI disables Generate while a job for this variant is active
Layer 2  idempotencyKey de-duplicates at the controller
Layer 3  canonical attempt-path uniqueness at the use case
Layer 4  the concurrency lease

Client-side prevention alone is decoration. Layers 2-4 are the real defence.
```

### 15.5 Log redaction [LOCKED]

```text
NEVER log: base64 image bytes · reference image bytes · the API key ·
Authorization / x-goog-api-key headers · the entire raw provider response.
Prompt logging follows the EXISTING VENHO prompt audit policy — neither
loosen nor tighten it here.
```

---

## 16. ERROR TAXONOMY [LOCKED]

One prefix. One table. No synonyms anywhere.

```ts
export type ImageGenerationErrorCode =
  // request / policy — free failures, before any spend
  | "IMAGE_GENERATION_REQUEST_INVALID"
  | "IMAGE_GENERATION_PROVIDER_INVALID"
  | "IMAGE_GENERATION_PROVIDER_DISABLED"
  | "IMAGE_GENERATION_PROVIDER_NOT_CONFIGURED"
  | "IMAGE_GENERATION_UNSUPPORTED_SIZE"
  | "IMAGE_GENERATION_UNSUPPORTED_ASPECT_RATIO"
  | "IMAGE_GENERATION_REFERENCE_INVALID"
  | "IMAGE_GENERATION_REFERENCE_LIMIT_EXCEEDED"
  | "IMAGE_GENERATION_ATTEMPT_ALREADY_EXISTS"
  | "IMAGE_GENERATION_BUDGET_EXCEEDED"
  | "IMAGE_GENERATION_CANCELLED_BEFORE_SPEND"
  // provider — spend may already have occurred
  | "IMAGE_GENERATION_RATE_LIMITED"
  | "IMAGE_GENERATION_TIMEOUT"
  | "IMAGE_GENERATION_PROVIDER_REJECTED"
  | "IMAGE_GENERATION_PROVIDER_NO_IMAGE"
  | "IMAGE_GENERATION_INVALID_IMAGE"
  | "IMAGE_GENERATION_GEOMETRY_MISMATCH"
  // post-generation
  | "IMAGE_GENERATION_ARTIFACT_WRITE_FAILED"
  | "IMAGE_GENERATION_VALIDATOR_FAILED"
  | "IMAGE_GENERATION_UNKNOWN";
```

| Domain error | HTTP | Spend |
|---|---:|---|
| `REQUEST_INVALID`, `PROVIDER_INVALID`, `UNSUPPORTED_*`, `REFERENCE_*` | 400 | none |
| `ATTEMPT_ALREADY_EXISTS` | 409 | none |
| `RATE_LIMITED`, `BUDGET_EXCEEDED` | 429 | none |
| `PROVIDER_DISABLED`, `PROVIDER_NOT_CONFIGURED` | 503 | none |
| `TIMEOUT` | 504 | **unknown — may be billed** |
| `PROVIDER_REJECTED`, `PROVIDER_NO_IMAGE`, `INVALID_IMAGE` | 502 | possibly billed |
| `GEOMETRY_MISMATCH` | 200 + warning | **billed**, artifact kept |
| `ARTIFACT_WRITE_FAILED` | 500 | **billed**, artifact lost |
| `VALIDATOR_FAILED` | 200, `qc.status = "UNVALIDATED"` | billed, artifact intact |
| `UNKNOWN` | 500 | unknown |

```jsonc
{ "ok": false,
  "error": { "code": "IMAGE_GENERATION_TIMEOUT",
             "message": "Hết thời gian chờ. Hệ thống KHÔNG tự thử lại.",
             "detail": {}, "correlationId": "…",
             "costMayHaveBeenIncurred": true } }
```

```text
RULE 16a  `costMayHaveBeenIncurred` is REQUIRED on every error response.
          Someone deciding whether to press Retry needs to know whether the
          failed attempt was free. This one boolean prevents the most
          expensive human error in the whole workflow.
RULE 16b  No upstream stack traces reach the browser. Log the sanitized cause
          with correlationId, provider, model, run/variant/attempt, error
          class, and upstream status if safe.
```

---

## 17. UI SPECIFICATION

### 17.1 Provider selector

```text
Label (VI): Bộ tạo ảnh          Label (EN): Image Generator

Options render from GET /providers. NEVER hard-coded in the component.

DO NOT label this control: Validator · AI reviewer · Official model · Model.
Generation provider and validation provider are different concepts and the
user must never be able to confuse them.
```

### 17.2 Capability-driven controls

```text
Selecting a provider immediately reshapes the dependent controls:
  nano-banana-2  -> size selector shows 1K, 2K
  openai         -> whatever Phase 0 discovers
  a disabled provider is shown DISABLED with its reason, never hidden

The server still enforces all of this. The UI shapes are for UX; they are
never the correctness boundary.
```

### 17.3 Cost display

```text
Show for the CURRENT provider + size:
  "Ước tính: ~$0,067 / ảnh (1K)"
  "Đã chi hôm nay: $0,20 / $3,00"

Always "~" and "ước tính" — input/reference tokens are additional.
Confirmation dialog when estimate > IMAGE_GENERATION_CONFIRM_ABOVE_USD
(default 0.15), stating the estimate and that a retry is a new paid attempt.
```

### 17.4 Status wording [LOCKED]

```text
NEVER show before validator + human gate:
  Official · Chính thức · Guaranteed identity · Face-lock guaranteed · Approved

Use wording mapped to REAL pipeline states:
  Candidate -> Ứng viên            Generated -> Đã tạo
  Passed automated QC -> Đã qua QC tự động
  Ready for human review -> Chờ duyệt     Unvalidated -> Chưa kiểm định
```

### 17.5 Vietnamese copy strings

| Key | Vietnamese |
|---|---|
| `provider.label` | Bộ tạo ảnh |
| `provider.openai` | GPT Image 2 — hiện tại |
| `provider.nb2` | Nano Banana 2 — Google Gemini |
| `provider.disabled.notConfigured` | Chưa cấu hình trên máy chủ |
| `provider.disabled.byConfig` | Đang tắt |
| `size.label` | Độ phân giải |
| `cost.estimate` | Ước tính: ~{amount} / ảnh ({size}) |
| `cost.today` | Đã chi hôm nay: {spent} / {cap} |
| `busy.generating` | Đang tạo ảnh… ({attemptId}) |
| `cancel.warning` | Huỷ sau khi đã gửi yêu cầu vẫn có thể bị tính phí. Ảnh (nếu có) vẫn được lưu. |
| `retry.warning` | Thử lại sẽ tạo một lần chạy MỚI và bị tính phí thêm. |
| `error.notConfigured` | Nano Banana chưa được cấu hình trên máy chủ này. |
| `error.noImage` | Lần tạo này không trả về ảnh dùng được. |
| `error.rateLimited` | Nhà cung cấp đang giới hạn tốc độ. Thử lại sau. |
| `error.timeout` | Hết thời gian chờ. Hệ thống KHÔNG tự thử lại để tránh bị tính phí hai lần. |
| `error.budget` | Đã chạm trần chi tiêu trong ngày ({cap}). |
| `error.geometry` | Ảnh trả về sai tỉ lệ/kích thước đã yêu cầu. Ảnh vẫn được lưu để bạn xem. |

### 17.6 Busy state and accessibility

```text
While a job is active for a variant: disable Generate, show the job status and
attempt ID, offer Cancel with the §17.5 warning copy.

The selector is a labelled radio group or a native <select> with a visible
<label>. Keyboard reachable. The disabled reason is announced via
aria-describedby, not conveyed by colour alone. The cost estimate belongs in
the accessible name of the Generate button, so a screen-reader user knows the
price before activating it.
```

---

## 18. TEST STRATEGY

```text
ABSOLUTE RULE: zero paid API calls in the automated suite. Default = mock.
```

### 18.1 Domain / unit

```text
public enum accepts openai + nano-banana-2, REJECTS mock
unknown provider -> PROVIDER_INVALID, never a default
provider -> model mapping resolves for every ID
aspect preset -> ratio mapping (portrait 2:3, square 1:1, story 9:16)
image size validation, including rejection of "1k" and "0.5K"
reference role policy · identity-lane rule · action-lane rule
reference count above the descriptor cap -> preflight failure, no provider call
attempt uniqueness
pricing lookup for every provider/size pair
cost estimator: output + input token math
budget guard: under cap passes · at cap blocks · concurrent double-spend blocked
```

### 18.2 Gemini request mapper

```text
text-only prompt · prompt + environment reference · prompt + face reference
store:false present on every request
response_format.type === "image"
aspect_ratio is the mapped ratio, not the preset
image_size uses an uppercase K
NO tools key (no grounding) · NO previous_interaction_id · NO background
model is the server-resolved ID, never anything from the request
snake_case keys used — a camelCase key in the request object FAILS the test
```

### 18.3 Gemini response parser

```text
valid PNG -> result       valid JPEG -> result
missing output_image -> PROVIDER_NO_IMAGE
empty base64 / invalid base64 / non-image bytes / bad MIME -> INVALID_IMAGE
providerRequestId absent -> tolerated       usage absent -> tolerated
the raw interaction object never leaks into the returned result
```

### 18.4 Geometry verifier

```text
exact geometry -> matches true
vendor-native bucket within 2% (832x1248 @ 2:3) -> matches true
16:9 returned when 2:3 requested -> matches false, artifact STILL written
long edge below the tier minimum -> matches false
undecodable / zero dimension -> INVALID_IMAGE
```

### 18.5 OpenAI regression [MANDATORY]

```text
a request without generationProvider resolves to openai
the prompt sent to OpenAI is byte-identical to the pre-change prompt
lane / reference behaviour unchanged
manifest top-level model is NOT hard-coded in the route
the existing validation path still executes
the existing response shape still satisfies the current UI
```

### 18.6 Architecture and anti-duplication

```text
ARCHITECTURE TEST  tests/image-generation/architecture-boundaries.test.ts
  domain/**      imports nothing outward, no vendor SDK, no node:fs, no next/*
  application/** imports no vendor SDK, no node:fs, no next/*
  only infrastructure/providers/gemini/** imports @google/genai

MODEL-STRING TEST  tests/image-generation/provider-model-map.test.ts
  no file outside provider-model-map.ts contains "gemini-3" or "gpt-image"
  (allow-list test fixtures and this document)
  THIS IS THE GUARD AGAINST THE ORIGINAL HARD-CODED-MODEL BUG.

PRICING CONSISTENCY TEST
  estimatedOutputCostUsd == tokens × rate / 1e6 for every entry, so editing
  one table and forgetting the other is caught by a test rather than by the
  invoice.
```

### 18.7 Artifact, job, API, UI

```text
ARTIFACT  new attempt writes a new path · existing attempt cannot be
          overwritten · a temp-write failure leaves no final image.png ·
          sha256 matches bytes · failed call produces no image.png ·
          manifest is 1.2 and every 1.1 field survives ·
          the REAL 1.1 reader does not crash on a 1.2 manifest ·
          no secret appears anywhere in the manifest

JOB       record carries provider/model/size/estimate ·
          spendCommitted flips before the call ·
          cancel while queued -> no spend ·
          cancel while generating -> artifact kept, cancelledAfterSpend=true ·
          expired lease with spendCommitted=true is NOT auto-restarted

API       valid openai request · valid nano-banana-2 request via mock ·
          invalid provider -> 400 · "mock" from a client -> 400 ·
          client model override rejected/ignored ·
          provider unavailable -> sanitized 503, no secret name leaked ·
          duplicate attempt -> 409 · same idempotencyKey twice -> one spend ·
          budget exceeded -> 429 with costMayHaveBeenIncurred=false

UI        selector renders from the capabilities endpoint ·
          disabled provider renders disabled WITH its reason ·
          selected provider included in the request ·
          size options follow the provider ·
          cost estimate changes with provider and size ·
          Generate disabled during an active job ·
          the generation selection does NOT alter the validation provider
```

### 18.8 Build commands

```text
Read package.json FIRST. The expected baseline is:
  npm test -- --run
  npx tsc --noEmit
  npm run lint          # expect 2 PRE-EXISTING errors in
                        # design_handoff_venho_os_cockpit/support.js
  npm run build

Report separately: NEW failures · PRE-EXISTING failures · environment
blockers. Never report a pre-existing failure as caused by this change, and
never report a new failure as pre-existing.
```

---

## 19. LIVE TEST POLICY AND SMOKE TEST

### 19.1 Policy [LOCKED]

```text
Automated tests: LIVE API = OFF. Always. No CI override.
CI uses the mock provider.
```

### 19.2 Authorization gate

```text
The smoke script must refuse to run unless ALL are true:
  ALLOW_LIVE_IMAGE_GENERATION_TESTS=true
  GEMINI_API_KEY present
  --authorized-spend-usd supplied and > 0
  projected spend (images × estimate) <= --authorized-spend-usd
  the daily budget guard has headroom

It prints the projected spend and image count, then requires an explicit
confirmation token. It never runs on import.
```

### 19.3 Smoke test scope (Phase 6)

```text
PURPOSE: prove the adapter works against the real API. NOT a quality decision.

  6 images on nano-banana-2 @1K
  covering: 3 hotel DNA subjects (lake_view_room, lobby, westlake)
          + 3 that exercise the plumbing (a reference-free prompt,
            a 2-reference prompt, a 9:16 story ratio)

  ≈ $0.40 total. Announce the projection BEFORE the first call.

CHECK:
  [x] every attempt produced an immutable artifact and a 1.2 manifest
  [x] geometry matched on all 6 (this is the point of the 9:16 case)
  [x] the cost ledger recorded 6 entries
  [x] the existing validators ran unchanged
  [x] no secret appears in any output
  [x] no asset was promoted to official

AFTER THIS, HARRY COMPARES BY EYE. That comparison is the real deliverable of
this whole plan, and it is a human judgement, not a metric.
```

---

## 20. FILE TREE

```text
venho-os/
├── src/
│   ├── app/api/v1/studio/
│   │   ├── generate-image/route.ts          # thin controller · runtime "nodejs"
│   │   ├── jobs/route.ts                    # EXISTING — extend response only
│   │   └── image-generation/providers/route.ts   # NEW · capabilities (§12)
│   │
│   ├── modules/image-generation/            # ← OR the repo's existing convention
│   │   ├── domain/
│   │   │   ├── image-generation-provider-id.ts   # PUBLIC vs INTERNAL enums
│   │   │   ├── image-aspect.ts
│   │   │   ├── image-size.ts
│   │   │   ├── image-reference.ts
│   │   │   ├── generate-image-command.ts
│   │   │   ├── provider-descriptor.ts
│   │   │   ├── provider-result.ts
│   │   │   ├── reference-policy.ts
│   │   │   └── image-generation.errors.ts        # the ONE taxonomy
│   │   ├── application/
│   │   │   ├── ports/
│   │   │   │   ├── image-generation-provider.port.ts
│   │   │   │   ├── image-artifact-store.port.ts
│   │   │   │   ├── image-reference-loader.port.ts
│   │   │   │   ├── generation-concurrency.port.ts
│   │   │   │   ├── generation-budget.port.ts
│   │   │   │   ├── generation-job.port.ts
│   │   │   │   └── validator-gateway.port.ts
│   │   │   ├── services/
│   │   │   │   ├── image-output-verifier.ts      # bytes + GEOMETRY
│   │   │   │   ├── generation-manifest.service.ts# schemaVersion 1.2
│   │   │   │   ├── generation-cost-estimator.ts
│   │   │   │   ├── provider-preflight.ts
│   │   │   │   └── generation-failure-recorder.ts
│   │   │   └── use-cases/generate-studio-image.use-case.ts
│   │   ├── infrastructure/
│   │   │   ├── config/
│   │   │   │   ├── image-generation-env.ts
│   │   │   │   ├── provider-model-map.ts         # ONLY home of model strings
│   │   │   │   ├── provider-descriptors.ts
│   │   │   │   └── image-pricing.snapshot.ts
│   │   │   ├── registry/image-provider-registry.ts
│   │   │   ├── providers/
│   │   │   │   ├── gemini/{gemini.client,gemini-image.provider,
│   │   │   │   │           gemini-request.mapper,gemini-response.parser,
│   │   │   │   │           gemini-error.mapper}.ts
│   │   │   │   ├── openai/openai-image-legacy.provider.ts
│   │   │   │   └── mock/mock-image.provider.ts
│   │   │   ├── storage/fs-image-artifact-store.ts
│   │   │   ├── references/existing-reference-loader.ts
│   │   │   ├── concurrency/generation-concurrency.adapter.ts
│   │   │   ├── budget/{file-cost-ledger,budget-guard}.ts
│   │   │   ├── jobs/file-backed-generation-job.adapter.ts   # wraps EXISTING
│   │   │   ├── validators/existing-validator.gateway.ts     # wraps EXISTING
│   │   │   └── composition/image-generation.module.ts       # composition root
│   │   └── interface/http/
│   │       ├── generate-image.request-schema.ts
│   │       ├── generate-image.response-mapper.ts
│   │       └── provider-capabilities.response.ts
│   │
│   ├── components/os/studio/
│   │   ├── ImageGenerationProviderSelector.tsx
│   │   ├── ImageGenerationSizeSelector.tsx
│   │   ├── ImageGenerationCostEstimate.tsx
│   │   └── ImageGenerationConfirmDialog.tsx
│   └── lib/studio/                          # EXISTING utilities — leave alone
│
├── contracts/image-generation/
│   ├── generate-image.request.schema.json
│   ├── generate-image.response.schema.json
│   ├── provider-capabilities.response.schema.json
│   ├── generation-job.schema.json
│   ├── manifest.generation-1.2.schema.json
│   └── cost-ledger-entry.schema.json
│
├── ops/VenHoSocialManager/                  # LEGACY — do not move
│   ├── generate_image.py                    # wrapped, not rewritten
│   ├── validate_generated.py                # FROZEN
│   └── validate_intent.py                   # FROZEN
│
├── scripts/image-generation/smoke-nano-banana.ts   # requires authorization
│
├── tests/
│   ├── fixtures/images/{mock-generated.png,invalid-image.bin,
│   │                    wrong-geometry-16x9.png,reference-sample.png}
│   ├── fixtures/gemini/{interaction-success,interaction-no-image,
│   │                    interaction-empty-data,interaction-safety-block}.json
│   └── image-generation/
│       ├── architecture-boundaries.test.ts
│       ├── provider-model-map.test.ts
│       ├── provider-id-enum.test.ts
│       ├── aspect-ratio.test.ts
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
│   ├── NANO_BANANA_IMAGE_PROVIDER_PLAN_v3.1.md   # this file
│   └── RUNBOOK.md
├── .env.example
└── package.json
```

### 20.1 Placement rule [LOCKED]

```text
Architecture is dependency direction, not folder fashion.

The agent must FIRST inspect venho-os and adopt its dominant convention. If
comparable server-side domain logic already lives under src/lib/studio/… or
src/features/… or src/server/…, place the module THERE with the same four
layers. Creating src/modules/image-generation/ beside an existing equivalent
structure is a DUPLICATE ARCHITECTURE, which VENHO's anti-duplication
principle forbids. Record the decision and the reason in the Phase 1 report.
```

---

## 21. ROADMAP — 6 PHASES

```text
Task IDs map to L4 Execution OS records: NB-P<phase>-T<n>. Copy into TASKS.md.
[FAST] = Fast Lane eligible (<= 30 min).

R1  Complete phases in order. Never start N+1 before N's acceptance passes.
R2  Report after EVERY phase in the §22 format, then STOP and wait.
R3  No paid call before Phase 6, and not without an explicit spend number.
R4  A contradiction with a [LOCKED] decision -> STOP and raise it. Do not
    implement a workaround "temporarily".
R5  A phase that cannot complete is reported as BLOCKED with the blocker.
    It is never partially completed and reported as done.
```

### PHASE 0 — DISCOVERY (no code, $0)

| ID | Task |
|---|---|
| NB-P0-T1 | Report git branch, uncommitted file count, whether user WIP is present |
| NB-P0-T2 | Locate `generate-image/route.ts`; enumerate EVERY current request field |
| NB-P0-T3 | Locate the OpenAI invocation path (the `execFile` target) |
| NB-P0-T4 | **Read the actual OpenAI model, quality tier and size arguments** |
| NB-P0-T5 | Locate the manifest writer; capture the real 1.1 field list |
| NB-P0-T6 | Locate every validator invocation after generation |
| NB-P0-T7 | Locate the durable job store, its states and record shape |
| NB-P0-T8 | Locate the artifact root and the real attempt directory convention |
| NB-P0-T9 | Locate the reference asset library and how references resolve today |
| NB-P0-T10 | Locate existing lane/reference types and the protocol-append code |
| NB-P0-T11 | Read `package.json`: manager, scripts, Node/Next versions |
| NB-P0-T12 | Determine the deployment target and its hard request timeout |
| NB-P0-T13 | Run the baseline test/tsc/lint/build; record pre-existing failures |
| NB-P0-T14 | Decide the module folder location per §20.1 |
| NB-P0-T15 | Produce the Discovery Inventory |

```text
DISCOVERY INVENTORY FORMAT
  ## Repository state      branch · uncommitted · user WIP? · baseline results
  ## Current path          route file · full request field list · OpenAI script
                           OpenAI model + quality tier + size   <-- NB-P0-T4
                           prompt assembly · protocol-append location
  ## Persistence           artifact root · attempt shape · manifest writer ·
                           manifest 1.1 field list
  ## Job system            store path · states · record shape · cancel · poll
  ## Validation            entry points · invocation · result shape
  ## References            library location · resolution · authorization
  ## Environment           manager · Node · Next · deploy target · hard timeout
  ## Decisions             module folder location + reason
  ## Deltas from the plan  every place reality differs from a [DISCOVER] assumption
  ## Blockers

ACCEPTANCE  Inventory complete. STOP. No code in Phase 0. Not one line.
```

### PHASE 1 — DOMAIN, REGISTRY, MOCK, BUDGET ($0)

| ID | Task |
|---|---|
| NB-P1-T1 | Domain types: provider IDs (two-tier), aspect, size, reference, command, result |
| NB-P1-T2 | Error taxonomy + HTTP mapping table [FAST] |
| NB-P1-T3 | Provider descriptors + capabilities |
| NB-P1-T4 | `provider-model-map.ts` [FAST] |
| NB-P1-T5 | `image-pricing.snapshot.ts` — prices + token table + snapshot date |
| NB-P1-T6 | Cost estimator (token math) |
| NB-P1-T7 | Cost ledger + budget guard + daily cap + alerts |
| NB-P1-T8 | Registry + `provider-preflight.ts` |
| NB-P1-T9 | Mock provider with failure simulation |
| NB-P1-T10 | The seven ports + composition root skeleton |
| NB-P1-T11 | Tests §18.1 + architecture test + model-string test + pricing test |

```text
ACCEPTANCE  new unit tests pass · architecture test passes · model-string test
            passes · existing OpenAI requests still work through the UNCHANGED
            old path · tsc + build pass.
```

### PHASE 2 — OPENAI ADAPTER + REGRESSION ($0)

| ID | Task |
|---|---|
| NB-P2-T1 | `openai-image-legacy.provider.ts`: execFile into a temp path, read bytes |
| NB-P2-T2 | Propagate correlationId and AbortSignal into the subprocess |
| NB-P2-T3 | Map subprocess failures to the taxonomy; never leak raw stderr |
| NB-P2-T4 | Remove the hard-coded `model: "gpt-image-2"` from manifest creation |
| NB-P2-T5 | Route the default path through the new use case |
| NB-P2-T6 | OpenAI regression tests (§18.5) |

```text
ACCEPTANCE  a request without generationProvider behaves identically · the
            prompt is byte-identical · manifest model comes from the
            descriptor · no validator behaviour changed.
```

### PHASE 3 — GEMINI ADAPTER (no live call, $0)

| ID | Task |
|---|---|
| NB-P3-T1 | **Re-verify** §2.1–§2.5 against live vendor docs; report the delta BEFORE coding |
| NB-P3-T2 | Add `@google/genai`; pin; update the lockfile; confirm only one Google SDK |
| NB-P3-T3 | `gemini.client.ts` + credential rules |
| NB-P3-T4 | `gemini-request.mapper.ts` (pure) — snake_case, store:false, no tools |
| NB-P3-T5 | `gemini-response.parser.ts` (pure) — fail closed |
| NB-P3-T6 | `gemini-error.mapper.ts` (pure) |
| NB-P3-T7 | `gemini-image.provider.ts` + register `nano-banana-2` |
| NB-P3-T8 | Fixtures + tests §18.2, §18.3 |

```text
ACCEPTANCE  mapper/parser/error tests pass · the app boots with no
            GEMINI_API_KEY and Gemini shows as disabled · OpenAI unaffected ·
            0 network calls in the suite (verified, not assumed).
```

### PHASE 4 — VERIFIER, ARTIFACT, MANIFEST 1.2 ($0)

| ID | Task |
|---|---|
| NB-P4-T1 | `image-output-verifier.ts`: decode, MIME, size, **geometry** |
| NB-P4-T2 | Choose and wire the image-decoding library; confirm it runs on the deployment target (native binaries) |
| NB-P4-T3 | Atomic + immutable artifact store; SHA-256 |
| NB-P4-T4 | Manifest 1.1 → 1.2 additive; `generation`, `geometry`, `pricing` |
| NB-P4-T5 | Failure recorder: `generation-error.json`, failure manifest |
| NB-P4-T6 | Wire the cost ledger into success and ambiguous-failure paths |
| NB-P4-T7 | Tests §18.4, §18.7 — including the REAL 1.1 reader against a 1.2 manifest |

```text
ACCEPTANCE  geometry mismatch detected, recorded, artifact NOT deleted ·
            an existing attempt cannot be overwritten · the 1.1 reader does
            not crash on 1.2 · no secret in any manifest.
```

### PHASE 5 — JOB, API, CAPABILITIES, UI ($0)

| ID | Task |
|---|---|
| NB-P5-T1 | Extend the job record additively; `spendCommitted` before the call |
| NB-P5-T2 | Move provider execution into the job worker |
| NB-P5-T3 | Cancel semantics §13.1; crash recovery §13.2 |
| NB-P5-T4 | Request schema: provider, imageSize, idempotencyKey, referenceAssetIds |
| NB-P5-T5 | Idempotency handling §11.3 |
| NB-P5-T6 | Route runtime declarations §11.5 |
| NB-P5-T7 | `GET /providers` capabilities endpoint |
| NB-P5-T8 | Provider selector + capability-driven size selector |
| NB-P5-T9 | Cost estimate + today's spend + confirm dialog |
| NB-P5-T10 | Vietnamese copy + accessibility §17.5, §17.6 |
| NB-P5-T11 | Tests §18.7 |

```text
ACCEPTANCE  the UI can select Nano Banana when configured (mock in tests) ·
            an unconfigured provider renders disabled with a coarse reason ·
            the validation provider is untouched · double-submit blocked at
            all four layers · DEFAULT IS STILL openai.
```

### PHASE 6 — VERIFY, THEN LIVE SMOKE 💰

| ID | Task |
|---|---|
| NB-P6-T1 | Run the repo's real test / tsc / lint / build commands |
| NB-P6-T2 | Classify every failure: NEW vs PRE-EXISTING vs environment |
| NB-P6-T3 | Verify 0 network calls in the suite |
| NB-P6-T4 | Update `task_status.md` and `task_memory.md` |
| NB-P6-T5 | **STOP. Report. Wait for an explicit spend authorization.** |
| NB-P6-T6 | With authorization: run the 6-image smoke test (§19.3, ≈ $0.40) |
| NB-P6-T7 | Report actual spend vs projection and the ledger delta |

```text
ACCEPTANCE  New failures = 0 · pre-existing unchanged · 6 artifacts with 1.2
            manifests · geometry matched on all 6 · ledger has 6 entries ·
            nothing promoted to official.

THEN: Harry compares the images by eye. That is the deliverable.
```

---

## 22. PHASE REPORT FORMAT

```text
PHASE <n> REPORT
  files added       : …
  files changed     : …
  what changed      : 3-6 bullets, behaviour not prose
  contracts touched : …
  tests run         : exact commands
  results           : pass/fail counts
  NEW failures      : caused by this change
  PRE-EXISTING      : already there before (§18.8)
  spend             : $0.00 (or the authorized amount + ledger delta)
  blockers          : …
  next phase        : … and what it needs from Harry
```

---

## 23. DEFINITION OF DONE

```text
ARCHITECTURE
[x] ImageGenerationProviderPort is the only provider abstraction
[x] domain + application import no vendor SDK (enforced by a test)
[x] only infrastructure/providers/gemini/** imports @google/genai
[x] the provider never writes a canonical artifact
[x] model mapping has exactly one source of truth (enforced by a test)
[x] a composition root exists; routes do not construct adapters
[x] OpenAI is wrapped without changing the generation protocol
[x] a deterministic mock provider exists, with failure simulation

GEMINI
[x] nano-banana-2 -> gemini-3.1-flash-image, verified against the live SDK
[x] Interactions API via @google/genai is the only production path
[x] store:false on every request
[x] no grounding, no multi-turn state, no background execution
[x] no hidden automatic retry anywhere
[x] missing or invalid image fails closed
[x] snake_case request keys verified against the installed SDK types

COST
[x] daily budget cap enforced before every paid call
[x] append-only ledger written on success AND ambiguous failure
[x] alerts at 70/85/100%
[x] estimator uses the vendor token table
[x] actualCostUsd remains null without billing truth

API / JOB / UI
[x] generationProvider allow-listed against the PUBLIC enum
[x] an omitted provider defaults to openai
[x] the browser cannot choose a model ID, a path, or mock
[x] the capabilities endpoint drives the UI
[x] job records carry provider/model/size/estimate and spendCommitted
[x] cancel semantics implemented per §13.1
[x] generation provider is visibly separate from the validation provider
[x] estimates shown as estimates, in Vietnamese, with today's spend
[x] double-submit guarded at all four layers

ARTIFACTS
[x] writes are immutable and atomic; SHA-256 recorded
[x] geometry requested vs actual recorded on every attempt
[x] a failure can never be mistaken for a successful asset
[x] schemaVersion 1.2; every 1.1 field survives; the real reader is tested
[x] no secrets, no raw headers, no absolute host paths in any manifest

GATES
[x] Face QC threshold unchanged
[x] Image DNA and Intent validators unchanged
[x] lane/reference policy unchanged
[x] no automatic official promotion
[x] no publishing path touched

QUALITY
[x] all test groups in §18 pass
[x] OpenAI regression tests pass
[x] architecture + model-string + pricing tests pass
[x] tsc passes; lint passes except the 2 declared pre-existing errors; build passes
[x] 0 paid API calls in the full suite, verified
```

---

## 24. FOLLOW-ON (NOT THIS TASK): MAKING IT THE DEFAULT FOR CONTENT

> Recorded so the next task does not have to redesign anything. **Do not implement any of this now.**

If the eye comparison after Phase 6 favours Nano Banana, the next step is a **separate task in `venho-ai-studio`**:

```text
GOAL   Add a GeminiImageProvider beside image_studio_runtime/adapters/
       gpt_image_provider.py, so the Growth Agent daily cycle can generate
       Facebook Page images with Nano Banana.

REUSE FROM THIS PLAN (contracts are language-agnostic)
  the provider port shape             the error taxonomy
  the geometry verification rule      the no-retry rule
  the manifest generation block       the cost ledger entry shape

MUST RESPECT THE EXISTING PYTHON RUNTIME'S OWN RULES
  the paid image policy: one paid generation + one targeted repair, then
    the package stays NEEDS_REVIEW
  429/5xx backoff must not create a variant artifact
  cost goes through the EXISTING shared/budget/BudgetLedger — do not create
    a second ledger
  model and quality read from config (GR-D2), never hard-coded
  0 API calls in pytest, mock provider by default

OPEN QUESTION FOR THAT TASK (answer before designing it)
  Which DNA subjects may be AI-generated at all?
  `lake_view_room` / `deluxe_double` / `lobby` / `facade` represent REAL
  inventory a guest books. An AI image that drifts from the real room is a
  brand and possibly an OTA-compliance risk. `westlake` / `outside` /
  seasonal mood shots carry no such risk.
  This is a business decision for Harry, not an architectural one, and it
  should be settled before any code is written.
```

---

## 25. ROLLBACK AND EDGE CASES

### 25.1 Rollback

```bash
IMAGE_GENERATION_GOOGLE_ENABLED=false     # configuration first
```

```text
The OpenAI path must remain fully functional at all times. If disabling Google
breaks OpenAI generation, the seam was built wrong — that is a release blocker.

Gemini is additive, so rollback is: disable the provider, optionally hide the
UI option, retain every manifest and artifact.
NEVER delete historical Gemini attempt artifacts during a rollback. They were
paid for and they are audit evidence.
Rolling back the code does not roll back manifests already written — the 1.1
reader must tolerate 1.2 regardless.
```

### 25.2 Edge cases

| # | Situation | Required behaviour |
|---|---|---|
| 1 | Gemini returns text but no image | `PROVIDER_NO_IMAGE`, no `image.png`, ledger `costCertainty=unknown` |
| 2 | Empty or invalid image data | `INVALID_IMAGE`, no artifact |
| 3 | Geometry ≠ requested | Artifact KEPT, `matches=false`, warned in the UI |
| 4 | Provider succeeded, artifact write failed | Record `providerRequestId` + `stage=artifact_write`; NO retry; the cost was real |
| 5 | Timeout after the provider accepted | Ambiguous. No auto-retry. `costMayHaveBeenIncurred=true` |
| 6 | UI requests Gemini, server has no key | Sanitized `provider_not_configured`. No silent fallback to OpenAI |
| 7 | Unsupported provider value | 400. No silent default |
| 8 | Client sends an arbitrary model ID | Ignored/rejected. Server mapping wins |
| 9 | Client sends an arbitrary reference path | Rejected. Only server-resolved asset IDs |
| 10 | Duplicate request / browser refresh | Idempotency key, then canonical attempt lock |
| 11 | Two workers claim the same attempt | Shared lock arbitrates; one gets 409 |
| 12 | Validator crashes after a valid generation | Keep artifact + manifest; record the error; `UNVALIDATED`; never approved |
| 13 | Budget cap reached | 429 before the call; nothing spent |
| 14 | Crash with `spendCommitted=true` | Recover as failed, `costCertainty=unknown`, never auto-restart |
| 15 | Cancel while generating | Artifact kept, `cancelledAfterSpend=true`, ledger written |
| 16 | Price catalog goes stale | UI shows a DATED estimate; no accounting uses it; update one module |
| 17 | Vendor deprecates the model ID | Loud failure from the single mapping module. Do not add a fallback chain |

---

## APPENDIX A — CONFIGURATION

```bash
# ---- provider selection -------------------------------------------------
IMAGE_GENERATION_DEFAULT_PROVIDER=openai      # openai | nano-banana-2

# ---- Google -------------------------------------------------------------
IMAGE_GENERATION_GOOGLE_ENABLED=false
GEMINI_API_KEY=                               # server-only, never NEXT_PUBLIC_

# ---- OpenAI (existing; discovered in Phase 0) ---------------------------
OPENAI_IMAGE_MODEL=                           # from NB-P0-T4
OPENAI_IMAGE_QUALITY=                         # from NB-P0-T4

# ---- operational guards -------------------------------------------------
IMAGE_GENERATION_MAX_CONCURRENCY=2
IMAGE_GENERATION_TIMEOUT_MS=                  # < the platform limit (§11.5b)
IMAGE_GENERATION_DEFAULT_IMAGE_SIZE=1K

# ---- budget -------------------------------------------------------------
IMAGE_GENERATION_DAILY_BUDGET_USD=3.00
IMAGE_GENERATION_BUDGET_ALERT_PCT=70,85,100
IMAGE_GENERATION_CONFIRM_ABOVE_USD=0.15
IMAGE_GENERATION_COST_LEDGER_PATH=data/studio/cost-ledger.jsonl

# ---- live test protection -----------------------------------------------
ALLOW_LIVE_IMAGE_GENERATION_TESTS=false
```

```text
The app MUST start with Gemini disabled and no GEMINI_API_KEY.
GOOGLE_ENABLED=true with no key -> startup warning, provider unavailable,
  OpenAI generation NOT broken.
An unknown IMAGE_GENERATION_DEFAULT_PROVIDER -> fail fast at startup. A typo
  here silently changes which vendor you pay.
IMAGE_GENERATION_TIMEOUT_MS >= the platform limit -> fail fast at startup.
```

---

## APPENDIX B — PRICING SNAPSHOT MODULE

```ts
// infrastructure/config/image-pricing.snapshot.ts
// UX + estimate only. NOT accounting truth. Verified 2026-08-10.
export const IMAGE_PRICING_SNAPSHOT = {
  sourceDate: "2026-08-10",
  currency: "USD",
  mode: "standard",

  /** USD per 1M image OUTPUT tokens. */
  imageOutputTokenRate: { "nano-banana-2": 60 },

  /** Image output tokens per generated image, by size tier. */
  imageOutputTokens: {
    "nano-banana-2": { "512": 747, "1K": 1120, "2K": 1680, "4K": 2520 },
  },

  /** Input image tokens per REFERENCE image. */
  imageInputTokensPerReference: { "nano-banana-2": 1120 },

  /** Derived per-image output price. A TEST keeps this in sync with the
   *  token math above — so an edit to one table cannot silently diverge. */
  estimatedOutputCostUsd: {
    "nano-banana-2": { "512": 0.0448, "1K": 0.0672, "2K": 0.1008, "4K": 0.1512 },
  },
} as const;
```

---

## APPENDIX C — COPY-PASTE PROMPTS FOR THE CODING AGENT

```text
PHASE 0
  Read this plan completely. Execute PHASE 0 (§21, NB-P0-*) only.
  Write NO application code. Produce the Discovery Inventory in the exact
  format given in §21, including the NB-P0-T4 answer, and STOP.

PHASE 1
  Execute PHASE 1 (NB-P1-*): domain, registry, mock, budget, ports,
  composition root, tests. No vendor SDK. No behaviour change to the existing
  OpenAI path. Report in the §22 format and STOP.

PHASE 2
  Execute PHASE 2 (NB-P2-*): wrap the existing OpenAI generator behind the
  port, remove the hard-coded manifest model, prove byte-identical prompt
  behaviour with regression tests. Report and STOP.

PHASE 3
  Execute PHASE 3 (NB-P3-*). FIRST re-verify §2.1-§2.5 against live vendor
  documentation and report the delta BEFORE coding. Then implement the Gemini
  adapter with mocked-SDK tests only. Make zero network calls. Report and STOP.

PHASE 4
  Execute PHASE 4 (NB-P4-*): output verifier including geometry, atomic
  artifact store, manifest 1.1 -> 1.2, failure recorder, cost ledger wiring.
  Run the REAL 1.1 reader against a 1.2 manifest. Report and STOP.

PHASE 5
  Execute PHASE 5 (NB-P5-*): job integration, request schema, capabilities
  endpoint, UI with Vietnamese copy. The default provider stays openai.
  Report and STOP.

PHASE 6
  Execute NB-P6-T1..T5 only: run the repo's real verification commands,
  classify NEW vs PRE-EXISTING failures, update task_status.md and
  task_memory.md, then STOP. Do NOT run the smoke test until I give you an
  explicit spend authorization.
```

---

## APPENDIX D — EXTERNAL REFERENCES

```text
https://ai.google.dev/gemini-api/docs/interactions-overview
https://ai.google.dev/gemini-api/docs/get-started
https://ai.google.dev/gemini-api/docs/image-generation
https://ai.google.dev/gemini-api/docs/pricing
https://googleapis.github.io/js-genai/
https://platform.openai.com/docs/pricing        (gpt-image-2 baseline)
```

**Re-verification checklist — run at NB-P3-T1 and monthly:**

```text
[x] Does gemini-3.1-flash-image still resolve without a -preview suffix?
[x] Does interactions.create still take response_format with snake_case keys?
[x] Is output_image still the convenience accessor?
[x] Is store:false still the opt-out?
[x] Are the aspect_ratio and image_size allowed values unchanged?
[x] Are the per-image prices and per-image token counts unchanged?
[x] Has the minimum @google/genai version changed?
```

---

## APPENDIX E — SUMMARY

```text
Creative Studio (venho-os)
  -> existing prompt / lane / reference protocol          [UNCHANGED]
  -> durable job                                          [EXTENDED]
  -> GenerateStudioImageUseCase                           [NEW]
  -> preflight: capability · lane · uniqueness · budget   [NEW]
  -> ImageGenerationProviderPort                          [NEW]
       -> OpenAI legacy adapter   (wraps generate_image.py)
       -> Nano Banana 2 adapter   (gemini-3.1-flash-image)
       -> Mock adapter            (zero cost, deterministic)
  -> verified bytes + VERIFIED GEOMETRY                    [NEW]
  -> immutable, atomic, hashed artifact                    [HARDENED]
  -> manifest 1.2 + cost trace + cost ledger               [EXTENDED]
  -> existing Validator Studio                             [UNCHANGED]
  -> human review                                          [UNCHANGED]
  -> explicit official promotion                           [UNCHANGED]
```

```text
The goal of this change is to let a human compare two generators on the same
prompt, the same DNA, the same references and the same validators — and then
decide with their own eyes.

The provider is replaceable. The DNA, the validators, the immutable trace and
the human official gate are the system of record, and this change does not
touch a single one of them.
```

---

**END OF PLAN v3.1**

---

## PHASE REPORT — 2026-08-11 (convergence pass)

**Status: Phases 1–5 substantially complete. Phase 6 stopped at NB-P6-T5 as required — 0 paid calls.**

### Starting state
A prior pass had written the module (~3,800 lines, all unit-tested) but had **not connected most of it**.
Verified by tracing call sites, not by reading tests: `FsImageArtifactStore`, `verifyImageOutput`,
`buildManifest12`, `recordCost`, `buildCostLedgerEntry`, `writeGenerationError`, `writeFailureManifest`
and `sanitizeImageGenerationError` each had **zero** callers outside their own module and tests. All of
Phase 4 was dead code with green tests.

A second, competing implementation (`src/lib/studio/image-generation-provider.ts`) was the path the route
actually used for Gemini. It bypassed the registry, preflight, budget guard, geometry verifier and cost
ledger — and it exposed `mock` over HTTP in every environment.

### Deltas from the plan
- **D10 (new).** The Interaction resource exposes `id` and `usage`. The parser read `responseId` /
  `usageMetadata` — the `models.generateContent` names — so every provider request id and usage record
  silently came back `undefined`. The test fixture encoded the same wrong names, so the bug was
  self-confirming. Fixed in `gemini-response.parser.ts`; fixture corrected.
- **D9 confirmed.** `ImageResponseFormatMimeType` really is the single literal `image/jpeg`.
- **§15.2 gap.** The rule does not cover an *unknown* cost. `estimatedTotalCostUsd ?? 0` made the daily cap
  unenforceable for any provider without a pricing catalog (i.e. OpenAI). Decision taken: `null` now flows
  to the guard as `null`, and an unknown-cost call is refused once the day's **known** spend reaches the cap.
  `CostEstimator` also returns `null` for the total when the input cost is unknown, instead of reporting
  output-only as if it were complete.
- **§18.6 scope.** The model-string test scanned only the module directory, which is exactly why the
  offending file — one directory above it — stayed invisible. It now scans the whole image pipeline with
  comments stripped.

### Regressions found in the previous pass and fixed
1. `mock` selectable over HTTP in production (fake 1×1 PNG into the real approval pipeline).
2. Three vendor model strings hardcoded outside `provider-model-map.ts`.
3. The Gemini path had no budget cap and wrote no ledger entry at all.
4. The OpenAI provider was built with a boot-time `process.env`, losing a dotenv-only `OPENAI_API_KEY`;
   and lost `PATH`, so the subprocess lost the venho python toolchain. Credentials now resolve per call.
5. `activeGenerations` was claimed before the `try/finally`; two setup failures wedged the route at HTTP 429
   until restart. Setup errors also escaped as HTML rather than JSON.
6. Aborting did not cancel the upstream request — the signal now goes into the SDK.
7. Unsupported output MIME (webp/heic/…) was silently relabelled `image/png`.
8. Strict base64 validation rejected line-wrapped payloads — discarding an image already paid for.
9. Failure manifests in attempt directories would have appeared in `generation-history` as real generations.

### Verification (NB-P6-T1..T3)
- `npm test` — **320 passed / 60 files**, up from 297. 0 network calls (the only SDK use is mocked).
- `npx tsc --noEmit` — clean.
- `npm run lint` — 3 errors + 1 warning, **all pre-existing** (`design_handoff/support.js`,
  `PublishingSection.tsx`). No new lint problems.
- `npm run build` — compiles; `/api/v1/studio/image-generation/providers` registered.

### Deliberately NOT ticked
- **§19.3 live smoke (1697–1702)** — requires explicit spend authorization (R3 / NB-P6-T5). Not run.
- **2061** budget alert thresholds are read from config but never emitted.
- **2070** the job record carries `spendCommitted`/`provider`, not yet model/size/estimate.
- **2071** cancel semantics per §13.1 not fully implemented.
- **2073** estimates are shown in Vietnamese, but today's spend is not surfaced in the UI.
- **2074** double-submit is guarded at the route and UI, not at all four layers (no idempotency key yet).
- **2081** manifests still contain absolute host paths in `artifact.imagePath` (pre-existing 1.1 behaviour).
- **2313/2314** vendor prices and the minimum SDK version were not re-checked against live vendor docs;
  only the snapshot's internal consistency and the installed types were verified.

**Next spend decision is Harry's:** the 6-image smoke test (§19.3, ≈ $0.40).

---

# PHASE REPORT — 2026-08-11 (Phase 5 completion + §19.3 live smoke)

**All 57 boxes now ticked.** This pass closed the 14 that the convergence pass
left open, and ran the live smoke test with Harry's spend authorization.

## The five items Harry asked for

| Box | What was actually missing | What it is now |
|---|---|---|
| 2061 | `budgetAlertPct` was parsed from config and read by nobody | `BudgetGuard` fires on the **crossing**, not on every call above the line, and announces every step a single expensive call skipped past. Surfaced in `todaySummary()` as `pctUsed` / `crossedThresholdPct`. |
| 2070 | job record had only `spendCommitted` + a provider **string** | §13 provider block: id, modelId, aspectPreset, aspectRatio, imageSize, estimatedCostUsd, spendCommitted, cancelledAfterSpend. Written **before** the paid call. |
| 2071 | `cancelJob` aborted the controller immediately — the one thing §13.1 forbids | queued → cancelled, no spend. generating/validating → the call is left to finish and bill; the job settles as `cancelled` with `cancelledAfterSpend: true` and the **image is kept**. `DELETE` now answers `cancelledImmediately: false` instead of claiming a cancel it cannot deliver. |
| 2073 | endpoint returned budget; UI never showed it | Spend line under the provider selector, colour-tracking ok/approaching/exceeded, re-read from the server's ledger after every run. |
| 2074 | guarded at the route semaphore and a `disabled` prop only | Four layers: a submit ref (a fast second click beats a re-render), a client idempotency key per variant, server-side replay in `findJobByIdempotencyKey`, and the existing concurrency semaphore. |

## §19.3 live smoke — 6/6 succeeded

| # | Case | QC | Geometry | Actual |
|---|---|---|---|---|
| 1 | lake_view_room DNA, 1 env ref | approved | ✅ | 848×1264 (2:3) |
| 2 | outside/rooftop DNA, 1 env ref | approved | ✅ | 848×1264 (2:3) |
| 3 | westlake DNA, no ref | usable | ✅ | 848×1264 (2:3) |
| 4 | zero refs, no DNA subject | needs_review | ✅ | 848×1264 (2:3) |
| 5 | two refs (face + environment) | usable | ✅ | 848×1264 (2:3) |
| 6 | 9:16 story ratio | usable | ✅ | 768×1376 (0.558 vs 0.5625) |

- Every attempt produced an immutable artifact whose SHA-256 matches the manifest, and a `schemaVersion: 1.2` manifest. No `generation-error.json` anywhere.
- Ledger: **8 nano-banana-2 entries** — 6 cases + 1 pre-flight probe + **1 legitimate retry** (case 4's intent gate scored 20/revise, so `shouldRetry` fired exactly as designed; attempt 2 scored 35 and was selected).
- **Estimated generation cost $0.40768** across the six, against a $0.40 projection. Day total including the probe and retry: **$0.54208 of a $3.00 cap (18%)**.
- No secret appears in any manifest, ledger line or job record (scanned for both live keys). No asset promoted to official; `assets/` untouched.

## Deltas found by running it for real

1. **`GEMINI_API_KEY` was never findable.** `credentialSearchPaths` covered the social agent's `.env` but not its `.env.local` — which is where the key actually lives. The provider reported "chưa cấu hình" for a key plainly present on disk.
2. **The SDK ignores `signal`.** `@google/genai` 2.16.0 ran **3.5 minutes past a 120s abort** and returned normally. Passing the signal in is necessary but not sufficient; the deadline is now also enforced by a race, with the abort as best-effort on top. The timeout error keeps `costMayHaveBeenIncurred: true` because the upstream call may well continue and be billed. **The first version of this test honoured the signal and passed — it proved our own wiring, not the vendor's behaviour.**
3. **120s was the wrong number.** Real nano-banana-2 calls take 1.5–3.5 min; the default was inherited from the OpenAI subprocess. Set to a measured 420000 per RULE 11.5c.
4. **The daily cap silently reset for 7 hours every night.** `dailySpentUsd` prefix-matched a **local** day key against **UTC** timestamps. Between local midnight and 07:00 ICT the two differ, so the evening's spend vanished from the total. Now compared after converting to local time.
5. **Idempotency could replay a corpse.** A job stranded by a restart stays in-progress for 30 minutes before `reconcileOrphanedJobs` reclaims it; a retry in that window was handed a job no process was running. Now reclaimed on the spot.
6. **Reference images are sent inline at full size** — `Rooftop-railing.png` is 9.7 MB, `View-Ho-room-from-inside.png` is 20 MB, so a two-reference request ships ~40 MB of base64. Not fixed (out of scope); the pricing model's 1120 input tokens per reference implies they were meant to be downscaled. **Worth doing before this runs at volume.**
7. **Vendor prices re-checked** against ai.google.dev 2026-08-11: output rate ($60/1M), per-image token counts (747/1120/1680/2520) and per-image prices all **unchanged**. One delta: the published input rate is $0.50/1M, while `imageInputTokenRate` is 1.0. Left as-is deliberately — it over-states input cost by $0.00056 per reference, which is the safe direction for a cap, and matches the plan's own §14.3 example.
8. **The artifact is JPEG, named `image.png`.** The request mapper asks for `image/jpeg`; the filename is kept for §18.5 compatibility (history and the file route both rely on it). The manifest records the true `mimeType`.

## Verification

- `npm test` — **350 passed / 64 files** (297 → 320 → 350).
- `npx tsc --noEmit` — clean. `npm run build` — compiles.
- `npm run lint` — 3 errors + 1 warning, all pre-existing in `design_handoff/support.js` and `PublishingSection.tsx`. No new problems.

**Remaining human step:** Harry compares the six images by eye. Per §19.3 that
comparison — not any number above — is the real deliverable of this plan.
