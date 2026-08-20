# VENHO — LINH AN GPU IDENTITY RESTORATION WORKER
## CLEAN ARCHITECTURE PLAN v2.0

**Trạng thái:** READY FOR IMPLEMENTATION HANDOFF — Claude Code / Claude Extension VS Code
**Ngày:** 2026-08-18
**Namespace:** `GW` (GPU Worker)
**Repo chính:** `venho-ai-studio` (Python) · **Repo phụ:** `venho-os` (Next.js 16)
**Host compute mới:** Windows 11 + NVIDIA GTX 1660 Super (6 GB VRAM)

**Thay thế hoàn toàn:** `VENHO_LINH_AN_WINDOWS_COMFYUI_GPU_WORKER_ROADMAP_v1_0.md`
*(giữ file v1.0 làm tài liệu lịch sử — không xoá, đánh dấu SUPERSEDED)*

---

# MỤC LỤC

| Phần | Nội dung |
|---|---|
| 0 | Meta — cách đọc, glossary, cảnh báo baseline chưa xác minh |
| 1 | Kết quả rà soát v1.0 — 14 lỗi kiến trúc |
| 2 | Quyết định kiến trúc GW-D1…D12 + chỉ mục ADR |
| 3 | Clean Architecture — layer map và dependency rule |
| 4 | Domain model và state machine |
| 5 | Contracts (Contract-First) |
| 6 | Ports — định nghĩa interface |
| 7 | Application Use Case — thuật toán tham chiếu |
| 8 | Infrastructure — ComfyUI adapter |
| 9 | Windows GPU Worker — hạ tầng vật lý |
| 10 | **File tree hoàn chỉnh (3 cây)** |
| 11 | Config và environment |
| 12 | Test và eval — kỷ luật 0 API call |
| 13 | Roadmap Phase 0–7 (tái phạm vi) |
| 14 | Benchmark protocol |
| 15 | Failure handling và runbook |
| 16 | Security và governance |
| 17 | Cost model |
| 18 | Decisions cần Harry chốt |
| 19 | Definition of Done |
| 20 | Protocol giao việc cho AI coding agent |
| 21 | Nguyên tắc khóa |

---
---

# PHẦN 0 — META

## 0.1 Cách AI Agent đọc file này

```text
READING PROTOCOL — đọc theo đúng thứ tự này, không nhảy cóc:

1. Đọc PHẦN 0.5 trước tiên. Nếu một giả định baseline ở đó SAI với repo thật,
   DỪNG LẠI và báo cáo. Không tự sửa kế hoạch cho khớp.
2. Đọc PHẦN 3 (layer map) để biết code mới đặt ở đâu.
3. Đọc PHẦN 10 (file tree) để biết tên file chính xác cần tạo.
4. Đọc PHẦN 13, tìm Phase đang tới lượt. Chỉ làm ĐÚNG một Phase.
5. Với mỗi file: đọc contract ở PHẦN 5/6 TRƯỚC khi viết implementation.
6. Viết test trước hoặc song song. Không có test = không hoàn thành.
7. Kết thúc Phase: cập nhật `task_memory.md` + `task_status.md`.

QUY TẮC CẤM:
- Không sửa file thuộc pipeline hiện có nếu Phase không yêu cầu rõ ràng.
- Không gọi API thật trong test.
- Không tạo M-module mới (M11, M12...). Xem GW-D2.
- Không đổi ngưỡng QC. Ngưỡng thuộc Character Bible 07F, không thuộc file này.
```

## 0.2 Quan hệ tài liệu

```text
FILE NÀY THAY THẾ
  VENHO_LINH_AN_WINDOWS_COMFYUI_GPU_WORKER_ROADMAP_v1_0.md

FILE NÀY PHỤ THUỘC, KHÔNG ĐƯỢC MÂU THUẪN
  venho-ai-studio/CLAUDE.md                            (kỷ luật test, ownership)
  VENHO L4 Execution OS v1.1                           (task lifecycle, TASKS.md)
  VENHO L5 Production OS v1.2                          (Output Registry, promotion gate)
  VENHO L2 Governance OS                               (Change Request process)
  GOOGLE_NANO_BANANA_IMAGE_PROVIDER_CLEAN_ARCH_v3_0.md (provider port pattern — file này
                                                        NHÂN BẢN pattern đó, không thay thế)
  Linh An Character Bible 07A–07F                      (identity + QC rubric — nguồn ngưỡng)
  Visual DNA v2.7                                      (scenario/subject profiles)

FILE NÀY SẼ TẠO RA
  venho-ai-studio/docs/identity-restoration/ADR-GW-001..008.md
  venho-ai-studio/docs/identity-restoration/BENCHMARK_PROTOCOL.md
  venho-ai-studio/docs/identity-restoration/WINDOWS_WORKER_RUNBOOK.md
```

> **Ghi chú L5.** File này là artifact quản trị L0–L6 nên được miễn Output Registry gate.
> **Báo cáo benchmark do nó sinh ra thì KHÔNG được miễn** — phải đăng ký vào
> `PRODUCTION_REGISTRY.md` dạng Tier-1 internal output.

## 0.3 Glossary

| Thuật ngữ | Nghĩa chính xác trong file này |
|---|---|
| **Identity Restoration** | Thao tác tái tạo vùng mặt bên trong một crop đã chuẩn hoá, sao cho khớp A2-FRONT. Không phải "sinh ảnh". |
| **Restorer** | Một adapter thực hiện Identity Restoration. Có nhiều restorer: `comfyui-remote`, `nano-banana-edit`, `mock`. |
| **Worker** | Máy Windows chạy ComfyUI. Là *hạ tầng*, không phải *module*. |
| **A2-FRONT** | Ảnh identity authority duy nhất của Linh An, khoá bằng SHA-256. |
| **Crop** | Ảnh vuông đã normalize, cắt từ base frame theo `CropTransform`. Đơn vị làm việc của GPU. |
| **CropTransform** | Phép biến đổi affine crop↔canvas. Bắt buộc khả nghịch, có test round-trip. |
| **Pixel Lock** | Guard khẳng định mọi pixel NGOÀI vùng editable không đổi sau composite. |
| **Base frame** | Ảnh action đầy đủ do cloud provider sinh. Không thuộc phạm vi GPU worker. |
| **Full-gate pass** | Đạt toàn bộ điều kiện máy trước con người, gồm Face QC ≥ 90. **Không phải phê duyệt.** |
| **Official** | Tài sản đã được CON NGƯỜI promote. Không code path nào trong plan này tạo ra nó. |
| **Breakpoint #1** | External breakpoint sinh ảnh. Plan này **thu hẹp** nó ở nhánh restoration, không đóng nó. |

## 0.4 Namespace

```text
GW-Dxx    Quyết định kiến trúc đã chốt trong file này
GW-Exx    Lỗi phát hiện ở v1.0
DR-GW-xx  Quyết định còn treo, cần Harry chốt
ADR-GW-xx Architecture Decision Record (file riêng)
GW-Pxx    Phase
ERR_GW_*  Mã lỗi runtime

Không đụng độ: M01–M10 · A1–A8 · GR/RS/TR/PB/IN · MT1–MT3 · K1–K6 · L0–L6 · AS0–AS6
```

## 0.5 ⚠️ CẢNH BÁO — GIẢ ĐỊNH BASELINE CHƯA XÁC MINH

**Đọc mục này trước khi viết bất kỳ dòng code nào.**

Bản v1.0 tuyên bố các thành phần sau **đã tồn tại và đang chạy**. Tôi đối chiếu với
`task_memory.md`, `task_status.md` (bản 2026-08-10, 841/841 tests) và
`GOOGLE_NANO_BANANA_..._v3_0` thì **không tìm thấy tham chiếu nào** tới chúng:

| Thành phần v1.0 tuyên bố có | Tìm thấy trong docs Project? | Hành động bắt buộc |
|---|---|---|
| `ActionCompositePipeline` v2.1.1 | ❌ Không | Verify bằng `grep -r` trong repo |
| `ComfyUIIdentityRestorer` adapter | ❌ Không | Verify |
| A2-FRONT SHA-256 authority lock | ⚠️ Chỉ thấy `A2_Front.png` trong VAL-02 face reference set (4 ảnh), **không thấy cơ chế SHA-256 lock** | Verify |
| Hierarchical face masks | ❌ Không | Verify |
| Pixel preservation regression guard | ❌ Không | Verify |
| `SceneCandidate` / `CandidateSelector` | ❌ Không | Verify |
| `RegionalGate` | ❌ Không | Verify |
| `WorkflowLedger` | ❌ Không | Verify |
| `ProductionRunner` | ❌ Không | Verify |
| `face_restore_v1_api.json` | ❌ Không | Verify |
| Durable job/idempotency | ✅ **Có** — nhưng nằm ở `venho-os` (`job-store.ts`), không phải Python | Xem GW-D3 |
| Manifest schemaVersion 1.1/1.2 | ✅ **Có** — nằm ở `venho-os` | Xem GW-D3 |
| Face Validator + VAL-02 4-ảnh-ref | ✅ **Có** — `validator_studio/face_validator.py` | Tái sử dụng |
| Face QC thực tế ~82.5–88.8 | ✅ **Có** — chưa từng đạt 90 | Xem PHẦN 14 |

**Hai khả năng, và chúng dẫn tới hai kế hoạch rất khác nhau:**

- **(A)** Baseline có thật trong repo nhưng `task_memory.md`/`task_status.md` chưa cập nhật
  (docs mới nhất là 2026-08-10, plan v1.0 là 2026-08-18 → khoảng trống 8 ngày là hợp lý).
  → Plan này chạy đúng như viết, khối lượng ≈ 40% so với (B).
- **(B)** Baseline chỉ tồn tại trong cuộc hội thoại thiết kế với ChatGPT, chưa thành code.
  → **Phase 0 phồng lên thành một dự án con**: phải build toàn bộ Action Composite trước.
  Đây là rủi ro lịch trình lớn nhất của toàn bộ kế hoạch.

```text
GW-P0 TASK 0 — BẮT BUỘC CHẠY ĐẦU TIÊN, KHÔNG ĐƯỢC BỎ QUA

cd venho-ai-studio
grep -rn "ActionComposite\|ComfyUI\|pixel_preserv\|A2_FRONT\|RegionalGate" \
  --include=*.py --include=*.json --include=*.md . | tee /tmp/gw_baseline_probe.txt

cd ../venho-os
grep -rn "ActionComposite\|comfyui\|pixelLock\|a2Front" \
  --include=*.ts --include=*.tsx --include=*.json . | tee -a /tmp/gw_baseline_probe.txt

Xuất kết quả vào docs/identity-restoration/BASELINE_PROBE_2026-08-18.md
với 3 cột: [Thành phần] [Tồn tại Y/N] [Đường dẫn thật].

Nếu ≥ 5 dòng ở bảng trên là "N": DỪNG, báo Harry, yêu cầu quyết định
DR-GW-01 trước khi sang Phase 1.
```

> Tôi nói rõ: **tôi chưa chắc chắn** baseline này có thật. Không đoán bừa — hãy đo.

---
---

# PHẦN 1 — KẾT QUẢ RÀ SOÁT v1.0

## 1.1 Đánh giá tổng thể

Bản v1.0 **đúng về chiến lược, thiếu về kiến trúc**.

Cái nó làm tốt và tôi giữ nguyên: quyết định tách compute host khỏi control plane; nguyên tắc
"QC chứ không phải generator quyết định"; tách bạch "kiến trúc" với "model" ở Decision Gate
Phase 4; cảnh báo không phân loại local compute là "free"; thứ tự implementation nghiêm ngặt.

Cái nó thiếu: **nó là một runbook vận hành, không phải một bản thiết kế phần mềm.**
Một AI coding agent đọc v1.0 sẽ không biết tạo file nào, đặt ở đâu, interface ra sao.
Toàn bộ v1.0 có đúng **một** cây thư mục — và đó là cây trên máy Windows, không phải trong repo.

## 1.2 Bảng lỗi — 14 lỗi

| # | Mức | Lỗi ở v1.0 | Sửa trong v2.0 |
|---|---|---|---|
| **GW-E1** | **Critical** | **Không có Port.** v1.0 mô tả bằng văn xuôi rằng ComfyUI là "compute worker", nhưng không khai báo interface nào. Không có Port thì việc đổi compute host **là** sửa business logic — đúng thứ v1.0 tuyên bố sẽ tránh. | PHẦN 6: `IdentityRestorerPort` là hợp đồng duy nhất. Đổi host = đổi adapter, domain không đổi một dòng. |
| **GW-E2** | **Critical** | **Không có Composition Root.** Không nơi nào lắp object graph → wiring rò rỉ vào CLI/route handler, tầng lớp mục ruỗng. Đây đúng là lỗi D-11 mà Nano Banana v3.0 đã sửa. | PHẦN 3.5 + `infrastructure/composition/identity_restoration_module.py`. |
| **GW-E3** | **Critical** | **Không giải quyết ranh giới 2 repo.** v1.0 nói "AI Studio sở hữu job orchestration + manifest + artifact lineage", nhưng docs Project chứng minh job store và manifest **đang nằm ở `venho-os`**. Mâu thuẫn này nếu để nguyên sẽ đẻ ra job store thứ hai — tái phạm đúng lỗi GR-E1/GR-E2 của Growth Plan. | GW-D3 + PHẦN 3.6: chốt ranh giới rõ ràng, Python = image plane, TS = control plane. |
| **GW-E4** | **Critical** | **Không có Mock restorer.** Repo có invariant "0 API call trong tests". v1.0 không hề đề cập cách test hợp đồng HTTP khi không có máy Windows → CI sẽ chết hoặc test sẽ bị bỏ. | PHẦN 12 + `MockIdentityRestorer` + recorded HTTP fixtures. |
| **GW-E5** | **High** | **Không có File Tree cho repo.** Cây duy nhất là `C:\VenHoGPU\`. AI agent không có chỗ nào để bắt đầu gõ. | PHẦN 10 — 3 cây đầy đủ, đánh dấu ★ new / ○ modified. |
| **GW-E6** | **High** | **Workflow JSON được coi là "trạng thái máy Windows".** v1.0 nói "tạo file workflow versioned" nhưng đặt nó ở `C:\VenHoGPU\workflows\` — ngoài Git. Workflow là **source code**: nó quyết định output. Để ngoài Git = không reproducible, đúng thứ Phase 5 tuyên bố cần. | GW-D6: workflow sống trong repo, pin SHA-256, deploy sang Windows bằng script. |
| **GW-E7** | **High** | **Rò rỉ magic string.** v1.0 dặn "bind bằng `_meta.title`" nhưng không chỉ định nơi lưu các title đó. Chúng sẽ bị rải khắp adapter/test/script — tái phạm đúng regression `model: "gpt-image-2"` hardcode trong route.ts của v2.1. | GW-D7: `comfyui/node_registry.py` là nguồn duy nhất + grep-test cấm xuất hiện nơi khác. |
| **GW-E8** | **High** | **Bỏ sót hazard fp16 của dòng GTX 16xx.** GTX 1660 Super (Turing TU116) không có tensor core; dòng 16xx nổi tiếng cho ra ảnh đen / NaN khi chạy half-precision trong Stable Diffusion. v1.0 chỉ nói chung chung "configure for low-VRAM". Nếu không xử lý, Phase 1 sẽ fail và bị chẩn đoán nhầm là lỗi model. | PHẦN 9.2 — flag matrix cụ thể + test chẩn đoán riêng. |
| **GW-E9** | **High** | **Hazard trùng tên file upload không được nêu.** ComfyUI `/upload/image` mặc định ghi đè theo tên file, và khi `overwrite=false` nó **tự đổi tên** — nghĩa là tên bạn gửi đi không chắc là tên tồn tại trên worker. Hai job chạy gần nhau sẽ giẫm lên nhau. Đây là failure mode cụ thể nhất của kiến trúc này và v1.0 hoàn toàn im lặng. | PHẦN 8.2 — namespace bắt buộc `venho/{runId}/{attemptId}/`, luôn đọc `name` từ response. |
| **GW-E10** | **High** | **"LAN-only" không phải một biện pháp bảo mật.** ComfyUI **không có xác thực**. Bind vào LAN nhà nghĩa là bất kỳ ai trên WiFi đều queue được workflow tuỳ ý và đọc/ghi file hệ thống qua node load/save. Stack đã có sẵn Tailscale nhưng v1.0 không dùng. | GW-D9 + PHẦN 16: bind tailnet, không bind `0.0.0.0`. |
| **GW-E11** | **Medium** | **Không có retention policy cho `output/` trên Windows.** v1.0 nói "worker output là tạm" rồi bỏ đó. Đĩa sẽ đầy trong vài tuần và job fail vì lý do không liên quan gì tới model. | PHẦN 9.3 + `cleanup_worker_cache.ps1`. |
| **GW-E12** | **Medium** | **Health gate không có circuit breaker / cache.** Mỗi job gọi health check độc lập; worker sập giữa chừng sẽ tạo N job fail liên tiếp thay vì dừng sớm. | PHẦN 8.4 — `WorkerHealthPort` + trạng thái 3 mức + TTL. |
| **GW-E13** | **Medium** | **Không có contract-first.** Repo theo Contract-First (16 schema ở `contracts/`). v1.0 mô tả input/output bằng danh sách text trần. | PHẦN 5 — 5 JSON Schema mới kèm fixtures pass/fail. |
| **GW-E14** | **Low** | **Không có ID quyết định, không có ADR, không có rollback per-phase.** Không truy vết được vì sao chọn gì; không quay lui được. | PHẦN 2 (GW-D1…D12) + ADR files + rollback ở từng Phase. |

---
---

# PHẦN 2 — QUYẾT ĐỊNH KIẾN TRÚC

## 2.1 Bảng quyết định

| ID | Quyết định | Lý do | ADR |
|---|---|---|---|
| **GW-D1** | Windows ComfyUI là **một adapter đứng sau `IdentityRestorerPort`**, không phải một tầng của hệ thống. | Chỉ khi đó lời hứa "đổi compute host không đổi business logic" mới là sự thật kiểm chứng được bằng test, không phải lời hứa suông. | ADR-GW-001 |
| **GW-D2** | **Không tạo M-module mới.** Identity Restoration là một bounded context bên trong `venho-ai-studio`, tên package `identity_restoration/`. | Đánh số M11 là thay đổi kiến trúc → bắt buộc Change Request qua L2 Governance. Không làm ngầm trong sub-plan. | ADR-GW-002 |
| **GW-D3** | **Ranh giới repo:** Python = *image plane* (crop/mask/composite/pixel-lock/QC/ComfyUI client). TypeScript = *control plane* (job store, manifest, artifact store, cost ledger, UI, SSE). Giao tiếp qua **subprocess + JSON contract**, đúng pattern `execFile(generate_image.py)` và `validate_generated.py` đang chạy. | Không đẻ job store thứ hai. Tránh GR-E1. | ADR-GW-003 |
| **GW-D4** | **`venho-os` không bao giờ nói chuyện trực tiếp với ComfyUI.** Không có `fetch('http://192.168.x.x:8188')` trong bất kỳ file `.ts`/`.tsx` nào. Có grep-test cưỡng chế. | Dashboard dựng workflow thô = ComfyUI thành ứng dụng thứ hai hướng người dùng. v1.0 nói điều này nhưng không cưỡng chế được. | ADR-GW-003 |
| **GW-D5** | **POC model: SD1.5 + IPAdapter FaceID.** Không phải SDXL + PuLID. | 6 GB VRAM. Crop đã normalize về kích thước gần native 512–768 của SD1.5 → đây là fit tự nhiên, không phải thoả hiệp. Giữ nguyên lựa chọn đúng của v1.0. | ADR-GW-004 |
| **GW-D6** | **Workflow JSON là source code.** Sống ở `identity_restoration/workflows/`, pin SHA-256 trong config, deploy sang Windows bằng script một chiều. Không sửa workflow trên máy Windows. | Reproducibility là exit gate Phase 5. Không thể reproduce thứ nằm ngoài Git. | ADR-GW-005 |
| **GW-D7** | **Một nguồn duy nhất cho mọi định danh ComfyUI** (node title, workflow id, model filename): `infrastructure/comfyui/node_registry.py`. Test cấm chuỗi này xuất hiện ngoài module đó. | Chống đúng regression hardcode model string của v2.1. | ADR-GW-005 |
| **GW-D8** | **Polling `/history`, không dùng WebSocket** cho MVP. | Durable job phải sống sót qua restart process. WebSocket cho progress đẹp nhưng phá resumability. Progress chi tiết là tối ưu hoá Phase 5+. | ADR-GW-006 |
| **GW-D9** | **Truy cập qua Tailscale tailnet, không bind LAN thô.** ComfyUI bind `127.0.0.1` + expose qua tailnet interface. | ComfyUI không có auth. Tailscale đã có trong stack (`infra/setup_macmini.md`). Chi phí thêm ≈ 0. | ADR-GW-007 |
| **GW-D10** | **Mock restorer là mặc định trong test.** 0 network call. Recorded fixtures cho HTTP contract test. | Invariant repo. Không thương lượng. | ADR-GW-008 |
| **GW-D11** | **Restorer registry đa adapter ngay từ đầu**: `comfyui-remote` · `nano-banana-edit` · `mock`. Không hardcode ComfyUI là con đường duy nhất. | Nano Banana masked-edit đã đạt ~88.x — nó là **baseline so sánh sống**, không phải thứ bị vứt bỏ. Nếu GPU worker fail Phase 4, ta còn đường lui đã được wire sẵn. | ADR-GW-001 |
| **GW-D12** | **Ngưỡng QC không thuộc file này.** Face QC ≥ 90 đến từ Character Bible 07F. Nếu benchmark chứng minh 90 là bất khả thi, đó là Change Request lên 07F, **không** phải sửa số trong plan này. | `task_memory.md` #30 đã ghi khuyến nghị xem lại ngưỡng 90; nhưng khuyến nghị ≠ quyền tự sửa. | ADR-GW-002 |

## 2.2 Cái KHÔNG được build lại

```text
KHÔNG VIẾT LẠI — TÁI SỬ DỤNG (sau khi PHẦN 0.5 xác minh chúng tồn tại):

  validator_studio/face_validator.py       ← Face QC, VAL-02 4-ảnh reference, sampling=3
  validator_studio/image_validator.py      ← DNA-match, kill switch
  shared/vision/                           ← VisionClient, analyze_many
  venho-os job store + manifest 1.1/1.2    ← durable job, cancel, reconcile
  venho-os artifact store                  ← atomic, hashed, immutable
  venho-os cost ledger                     ← append-only
  automation_studio/                       ← M04 workflow runner (nếu cần orchestration)

Nếu baseline Action Composite tồn tại (PHẦN 0.5 khả năng A), thêm vào danh sách này:
  ActionCompositePipeline · hierarchical masks · CropTransform · pixel preservation guard
  A2 authority lock · SceneCandidate/CandidateSelector · RegionalGate · WorkflowLedger

Migration thật sự của plan này chỉ là:
    [restorer nội bộ / cloud masked-edit]  →  [restorer chạy trên GPU rời]
Không phải viết lại hệ sinh ảnh.
```

---
---

# PHẦN 3 — CLEAN ARCHITECTURE

## 3.1 Dependency Rule

```text
Mũi tên phụ thuộc CHỈ hướng vào trong. Không ngoại lệ.

        ┌──────────────────────────────────────────────────────┐
        │  INTERFACE            CLI · JSON bridge · (TS caller) │
        │  biết Application, KHÔNG biết Infrastructure          │
        └───────────────────────┬──────────────────────────────┘
                                │
        ┌───────────────────────▼──────────────────────────────┐
        │  APPLICATION          use cases · ports · DTO         │
        │  định nghĩa Port. KHÔNG import bất kỳ adapter nào.    │
        └───────────────────────┬──────────────────────────────┘
                                │
        ┌───────────────────────▼──────────────────────────────┐
        │  DOMAIN               entity · value object · policy  │
        │  thuần tuý. Không I/O, không HTTP, không PIL, không   │
        │  đọc file, không đọc giờ hệ thống.                    │
        └──────────────────────────────────────────────────────┘
                                ▲
        ┌───────────────────────┴──────────────────────────────┐
        │  INFRASTRUCTURE       ComfyUI HTTP · filesystem ·     │
        │                       vision client · clock           │
        │  IMPLEMENT Port. Không ai import ngược vào đây trừ    │
        │  Composition Root.                                    │
        └──────────────────────────────────────────────────────┘

TEST CƯỠNG CHẾ (bắt buộc viết, xem PHẦN 12.4):
  test_layering.py::test_domain_has_no_io_imports
  test_layering.py::test_application_does_not_import_infrastructure
```

## 3.2 Luồng runtime đầy đủ

```text
 VenHo OS Dashboard  (Next.js, Mac Mini)
        │  người dùng bấm Generate
        ▼
 venho-os  API route  →  durable JobStore  →  job worker
        │                                       (đã có sẵn — KHÔNG viết lại)
        │  subprocess + JSON contract (GW-D3)
        ▼
 venho-ai-studio  interface/cli.py  `venho-restore run --request req.json`
        │
        ▼
 ┌────────────────────────────────────────────────────────────────┐
 │ APPLICATION — RestoreFaceCropUseCase                            │
 │                                                                 │
 │  1 verify A2 authority (SHA-256)      ← domain policy, MIỄN PHÍ │
 │  2 verify crop/mask contract          ← domain policy, MIỄN PHÍ │
 │  3 attempt uniqueness (path chưa có)  ← MIỄN PHÍ                │
 │  4 worker health gate (cached, TTL)   ← RẺ                      │
 │  5 acquire concurrency lease (=1)     ← RẺ                      │
 │  6 check cancel request               ← RẺ                      │
 │  ────────────── RANH GIỚI TỐN KÉM ──────────────                │
 │  7 restorer.restore()  ĐÚNG MỘT LẦN                             │
 │  8 verify bytes: decode được, MIME, kích thước, HÌNH HỌC        │
 │  9 composite crop → canvas (domain)                             │
 │ 10 pixel-lock guard                   ← FAIL CỨNG nếu vi phạm   │
 │ 11 chạy Face QC + Regional QC hiện có (KHÔNG sửa ngưỡng)        │
 │ 12 ghi artifact atomically + ledger entry                       │
 │ 13 trả RestorationResult đã sanitize                            │
 │ 14 finally: release lease — LUÔN LUÔN                           │
 └────────────────────────────┬───────────────────────────────────┘
                              │ IdentityRestorerPort
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
  comfyui-remote        nano-banana-edit          mock
  (Windows GPU)         (cloud, baseline 88.x)   (fixture bytes, $0)
         │
         │ HTTP qua Tailscale tailnet
         ▼
 ┌────────────────────────────────────────────────────────────────┐
 │ Windows 11 · GTX 1660 Super · ComfyUI                           │
 │   POST /upload/image   ×3  (crop, mask, A2)                     │
 │   POST /prompt         queue graph đã bind theo _meta.title     │
 │   GET  /history/{id}   poll + backoff                           │
 │   GET  /view?...       tải restored crop                        │
 │ Worker KHÔNG BAO GIỜ ghi artifact chính thức. Output là tạm.    │
 └────────────────────────────────────────────────────────────────┘
```

## 3.3 Đường trở về

```text
RestorationResult (JSON, stdout)
        ▼
venho-os đọc, ghi vào Manifest schemaVersion 1.3
        ▼
Validator Studio hiện có (KHÔNG ĐỔI)
        ▼
Human review gate
        ▼
Official promotion — CHỈ bằng hành động con người rõ ràng
```

## 3.4 Manifest 1.2 → 1.3

```text
Bổ sung vào manifest (KHÔNG xoá field cũ, KHÔNG đổi tên field cũ):

  restoration: {
    restorerId,              // "comfyui-remote" | "nano-banana-edit" | "mock"
    workflowId,              // từ node_registry, không phải chuỗi tự do
    workflowSha256,          // pin — chứng minh reproducibility
    modelIdentifiers: [],    // checkpoint / ipadapter / clip_vision / insightface
    seed,
    restorationParams,       // denoise, steps, cfg, sampler, scheduler
    a2AuthoritySha256,
    cropTransform,           // đủ để đảo ngược
    maskVersion,
    workerHost,              // tên tailnet, KHÔNG phải IP thô
    gpuName, vramTotalMb, vramPeakMb,
    runtimeMs, retryCount,
    pixelLock: { passed, mutatedPixelCount, editableRegionHash }
  }

Test bắt buộc: manifest 1.2 cũ vẫn đọc được (backward compat).
```

## 3.5 Composition Root

```python
# identity_restoration/infrastructure/composition/identity_restoration_module.py
#
# NƠI DUY NHẤT biết mọi concrete class.
# CLI, test integration và script đều gọi build_identity_restoration_module().
# Không file nào khác được phép khởi tạo một adapter.
#
# ĐỌC TRƯỚC KHI SỬA:
#   Nếu bạn thấy mình import một adapter ở ngoài file này, bạn đang phá kiến trúc.
#   Hãy inject qua Port thay vì import.

def build_identity_restoration_module(
    env: RestorationEnv | None = None,
) -> IdentityRestorationModule:
    env = env or read_restoration_env()

    clock: ClockPort = SystemClock()
    health: WorkerHealthPort = CachedWorkerHealth(
        inner=ComfyUIHealthProbe(base_url=env.comfyui_base_url,
                                 timeout_s=env.health_timeout_s),
        ttl_seconds=env.health_ttl_s,
        clock=clock,
    )

    restorers: dict[RestorerId, IdentityRestorerPort] = {
        "mock": MockIdentityRestorer(fixture_root=env.fixture_root),
    }
    if env.comfyui_enabled:
        restorers["comfyui-remote"] = ComfyUIRemoteRestorer(
            client=ComfyUIHttpClient(base_url=env.comfyui_base_url,
                                     timeout_s=env.comfyui_timeout_s),
            workflow_repo=FileWorkflowRepository(root=env.workflow_root),
            node_registry=NODE_REGISTRY,          # GW-D7 — nguồn duy nhất
            health=health,
            clock=clock,
        )
    if env.nano_banana_enabled:
        restorers["nano-banana-edit"] = NanoBananaEditRestorer(...)

    return IdentityRestorationModule(
        use_case=RestoreFaceCropUseCase(
            registry=RestorerRegistry(restorers, default_id=env.default_restorer),
            a2_authority=FileA2AuthorityRepository(env.a2_path),
            artifact_sink=AtomicFileArtifactSink(env.artifact_root),
            qc=ValidatorStudioQcGateway(),        # bọc validator HIỆN CÓ, không sửa
            ledger=JsonlRestorationLedger(env.ledger_path),
            lease=FileConcurrencyLease(env.lease_path, max_concurrent=1),
            clock=clock,
        ),
        health=health,
    )
```

## 3.6 Ranh giới 2 repo — bảng sở hữu (GW-D3)

| Năng lực | `venho-ai-studio` (Py) | `venho-os` (TS) | Ghi chú |
|---|:---:|:---:|---|
| Durable job store, cancel, reconcile | — | ✅ | Đã có, không viết lại |
| Manifest 1.3 writer | — | ✅ | Python trả JSON, TS ghi manifest |
| Artifact store (atomic, hashed) | — | ✅ | |
| Cost ledger | — | ✅ | |
| Restoration ledger (chi tiết kỹ thuật) | ✅ | — | JSONL, phục vụ debug/benchmark |
| UI, SSE, approval queue | — | ✅ | |
| Crop / mask / CropTransform | ✅ | — | |
| Composite + pixel lock | ✅ | — | |
| A2 authority verify | ✅ | — | |
| **ComfyUI HTTP client** | ✅ | ❌ **CẤM** | GW-D4, có grep-test |
| Face QC / Regional QC | ✅ | — | validator_studio hiện có |
| Benchmark runner | ✅ | — | CLI |

---
---

# PHẦN 4 — DOMAIN MODEL & STATE MACHINE

## 4.1 Entity chính

```python
# identity_restoration/domain/entities.py
# THUẦN TUÝ. Không import: requests, httpx, PIL, pathlib.open, datetime.now, os.environ.
# Nhận bytes và số. Trả bytes và số. Nếu bạn cần I/O ở đây → nó thuộc infrastructure.

@dataclass(frozen=True)
class A2Authority:
    """Nguồn identity duy nhất của Linh An. Bất biến trong toàn bộ vòng đời job."""
    image_bytes: bytes
    sha256: str
    def verify(self, expected_sha256: str) -> None:
        # FAIL CỨNG trước khi tốn bất kỳ tài nguyên nào. ERR_GW_A2_HASH_MISMATCH.
        ...

@dataclass(frozen=True)
class CropTransform:
    """Affine crop ↔ canvas. BẮT BUỘC khả nghịch — có test round-trip."""
    source_x: int; source_y: int
    source_w: int; source_h: int
    target_size: int            # crop vuông, ví dụ 768
    rotation_deg: float = 0.0

@dataclass(frozen=True)
class MaskSet:
    """Mask phân cấp. `editable` là vùng DUY NHẤT được phép đổi pixel."""
    editable: bytes             # PNG L-mode
    feather: bytes
    version: str                # ví dụ "hierarchical_v2"

@dataclass(frozen=True)
class RestorationRequest:
    run_id: str; attempt_id: str
    crop_png: bytes
    mask: MaskSet
    a2: A2Authority
    workflow_id: str            # từ node_registry, KHÔNG phải chuỗi tự do
    seed: int
    params: RestorationParams   # denoise, steps, cfg, sampler, scheduler

@dataclass(frozen=True)
class RestoredCrop:
    png_bytes: bytes
    width: int; height: int
    def assert_geometry_matches(self, req: RestorationRequest) -> None:
        # Worker trả sai kích thước = ERR_GW_GEOMETRY_MISMATCH. Không tự resize.
        # Tự resize sẽ giấu bug của workflow và làm hỏng pixel lock.
        ...
```

## 4.2 Policy thuần

```python
# identity_restoration/domain/policies/pixel_preservation.py
#
# Ý nghĩa: một khuôn mặt đẹp nhưng làm đổi pixel ở vùng khoá là FAIL CỨNG.
# Lý do: nó có nghĩa là worker đã sinh lại thân/trang phục/bối cảnh —
# tức nó không còn là restoration nữa, nó là một ảnh khác.

def assert_pixels_preserved(
    before_canvas: bytes, after_canvas: bytes, editable_mask: bytes,
    tolerance: int = 0,          # 0 = byte-exact. Chỉ nới nếu ADR ghi rõ lý do.
) -> PixelLockReport: ...
```

```python
# identity_restoration/domain/policies/promotion.py
#
# BẤT BIẾN — bọc lại luật đã khoá của VENHO. Không code path nào tạo ra "official".
# ComfyUI chạy xong KHÔNG có nghĩa là ảnh hợp lệ.

def is_full_gate_pass(qc: QcResult, pixel: PixelLockReport) -> bool:
    return (qc.face_score >= FACE_QC_MIN          # nhập từ 07F, không hardcode ở đây
            and qc.all_validators_approved
            and not qc.kill_switch_triggered
            and pixel.passed)

def is_official(...) -> NoReturn:
    raise NotImplementedError(
        "Official promotion là hành động của con người. "
        "Không có code path nào trong module này được phép tạo ra nó."
    )
```

## 4.3 State machine

```text
RestorationAttempt

  PENDING
    → VERIFYING_AUTHORITY        (A2 hash, crop/mask contract)
    → HEALTH_GATED               (worker health, cached)
    → LEASED                     (concurrency = 1)
    → RESTORING                  ← ĐIỂM TỐN KÉM DUY NHẤT
    → COMPOSITING
    → PIXEL_LOCKING
    → VALIDATING
    → FULL_GATE_PASS | NEEDS_REVIEW | REJECTED
    ↘ FAILED   (bất kỳ bước nào — luôn giữ lại audit)
    ↘ CANCELLED (chỉ trước RESTORING; sau đó tiền đã tiêu / GPU đã chạy)

BẤT BIẾN:
  - FULL_GATE_PASS ≠ official. Không có state OFFICIAL trong máy trạng thái này.
  - Mọi transition sang FAILED phải ghi lý do có cấu trúc, không ghi chuỗi trần.
  - Retry = attempt MỚI (attempt_id mới). Không bao giờ ghi đè attempt cũ.
  - CANCELLED sau RESTORING là không hợp lệ → chuyển thành FAILED có ghi chú.
```

---
---

# PHẦN 5 — CONTRACTS (Contract-First)

> Mọi schema đặt ở `contracts/`, có version, có fixture pass và fail.
> **Code viết SAU khi contract được duyệt.**

| Schema | Mục đích |
|---|---|
| `restoration_request.schema.json` | Input vào `venho-restore`, do `venho-os` sinh |
| `restoration_result.schema.json` | Output stdout, do `venho-os` đọc |
| `restoration_manifest_1_3.schema.json` | Phần `restoration` bổ sung vào manifest |
| `worker_health.schema.json` | Kết quả health probe |
| `benchmark_row.schema.json` | Một dòng kết quả benchmark |

### 5.1 `restoration_request.schema.json` (rút gọn)

```jsonc
{
  "$id": "https://venho.local/contracts/restoration_request/1.0",
  "type": "object",
  "required": ["contractVersion","runId","attemptId","restorerId",
               "cropPath","maskPath","a2Path","a2Sha256",
               "workflowId","seed","params"],
  "additionalProperties": false,
  "properties": {
    "contractVersion": { "const": "1.0" },
    "runId":     { "type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{2,63}$" },
    "attemptId": { "type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{2,63}$" },
    // restorerId là ENUM. Không nhận chuỗi tự do — chuỗi tự do là cách
    // model string của vendor rò rỉ vào hệ thống (bài học v2.1).
    "restorerId": { "enum": ["comfyui-remote","nano-banana-edit","mock"] },
    "cropPath":  { "type": "string" },
    "maskPath":  { "type": "string" },
    "a2Path":    { "type": "string" },
    "a2Sha256":  { "type": "string", "pattern": "^[a-f0-9]{64}$" },
    "workflowId":{ "type": "string" },     // validate lại với node_registry lúc runtime
    "seed":      { "type": "integer", "minimum": 0, "maximum": 4294967295 },
    "params": {
      "type": "object",
      "required": ["denoise","steps","cfg","sampler","scheduler"],
      "additionalProperties": false,
      "properties": {
        // denoise là tham số nhạy nhất của toàn bộ pipeline này.
        // Quá thấp → mặt cũ không đổi, identity không cải thiện.
        // Quá cao  → mất khớp góc đầu và ánh sáng với Stage A.
        // Cận trên 0.75 là guard rail chủ ý, không phải con số tuỳ tiện.
        "denoise":   { "type": "number", "minimum": 0.05, "maximum": 0.75 },
        "steps":     { "type": "integer", "minimum": 8, "maximum": 60 },
        "cfg":       { "type": "number", "minimum": 1.0, "maximum": 12.0 },
        "sampler":   { "type": "string" },
        "scheduler": { "type": "string" }
      }
    },
    "timeoutSeconds": { "type": "integer", "minimum": 30, "maximum": 1800 }
  }
}
```

### 5.2 `restoration_result.schema.json` (rút gọn)

```jsonc
{
  "$id": "https://venho.local/contracts/restoration_result/1.0",
  "type": "object",
  "required": ["contractVersion","runId","attemptId","status"],
  "properties": {
    "contractVersion": { "const": "1.0" },
    "status": { "enum": ["FULL_GATE_PASS","NEEDS_REVIEW","REJECTED","FAILED","CANCELLED"] },
    "restoredCropPath": { "type": ["string","null"] },
    "compositePath":    { "type": ["string","null"] },
    "pixelLock": {
      "type": "object",
      "required": ["passed","mutatedPixelCount"],
      "properties": {
        "passed": { "type": "boolean" },
        "mutatedPixelCount": { "type": "integer", "minimum": 0 }
      }
    },
    "qc": {
      "type": "object",
      "properties": {
        "faceScore": { "type": "number" },
        "regional":  { "type": "object" },
        "samples":   { "type": "integer", "minimum": 1 }   // sampling=3 mặc định
      }
    },
    "lineage": { "$ref": "restoration_manifest_1_3.schema.json#/definitions/restoration" },
    "error": {
      "type": ["object","null"],
      "properties": {
        // Mã lỗi CÓ CẤU TRÚC. Không bao giờ ném raw stack trace hay
        // nội dung env sang phía TS (bài học sự cố lộ OPENAI_API_KEY 2026-07-17).
        "code":    { "enum": [
          "ERR_GW_A2_HASH_MISMATCH","ERR_GW_WORKER_OFFLINE","ERR_GW_WORKER_TIMEOUT",
          "ERR_GW_VRAM_EXHAUSTED","ERR_GW_WORKFLOW_INVALID","ERR_GW_NODE_BINDING_FAILED",
          "ERR_GW_UPLOAD_FAILED","ERR_GW_EMPTY_OUTPUT","ERR_GW_GEOMETRY_MISMATCH",
          "ERR_GW_PIXEL_LOCK_VIOLATED","ERR_GW_LEASE_UNAVAILABLE","ERR_GW_CANCELLED"
        ]},
        "message": { "type": "string", "maxLength": 500 },
        "retryable": { "type": "boolean" }
      }
    }
  }
}
```

---
---

# PHẦN 6 — PORTS

> **Đây là phần quan trọng nhất của toàn bộ tài liệu.**
> Nếu AI agent chỉ đọc được một phần, hãy đọc phần này.

```python
# identity_restoration/application/ports/identity_restorer.py
#
# HỢP ĐỒNG DUY NHẤT giữa business logic và phần cứng tính toán.
#
# ĐỌC TRƯỚC KHI SỬA:
#   Port này KHÔNG biết ComfyUI tồn tại. Không biết HTTP tồn tại. Không biết
#   Windows tồn tại. Nếu bạn thêm một tham số mang tên vendor vào đây, bạn đã
#   biến việc đổi compute host thành việc sửa business logic — đúng thứ
#   ADR-GW-001 tồn tại để ngăn.

class IdentityRestorerPort(Protocol):
    restorer_id: RestorerId

    def restore(self, request: RestorationRequest) -> RestoredCrop:
        """Tái tạo identity trong vùng editable của crop.

        BẢO ĐẢM PHÍA GỌI (caller đã làm, adapter không cần làm lại):
          - A2 authority đã verify SHA-256.
          - crop và mask cùng kích thước, mask là L-mode.
          - concurrency lease đã giữ.
          - cancel request đã kiểm tra.

        NGHĨA VỤ PHÍA ADAPTER:
          - Gọi backend ĐÚNG MỘT LẦN. Retry là việc của use case, không phải adapter.
            (Adapter tự retry = chi phí ẩn và ledger sai.)
          - Trả bytes PNG hợp lệ, đúng kích thước request.
          - Ném RestorationError có mã ERR_GW_* có cấu trúc, không ném lỗi thô của thư viện.
          - KHÔNG ghi artifact chính thức. KHÔNG chạy QC. KHÔNG quyết định pass/fail.
        """
        ...

    def describe(self) -> RestorerDescriptor:
        """Metadata tĩnh phục vụ manifest lineage: model ids, workflow sha, capability.
        Không gọi mạng."""
        ...
```

```python
# identity_restoration/application/ports/worker_health.py
#
# Tồn tại để sửa GW-E12: không có cái này, worker sập sẽ tạo N job fail liên tiếp
# thay vì dừng ở job đầu tiên.

class WorkerHealthPort(Protocol):
    def probe(self) -> WorkerHealth:
        """Trả HEALTHY | DEGRADED | OFFLINE + gpuName + vramFreeMb + latencyMs.

        Kết quả PHẢI được cache theo TTL. Nếu OFFLINE thì use case
        KHÔNG ĐƯỢC submit — job fail hiển thị rõ ràng, không im lặng, không
        báo hoàn thành giả (bất biến của v1.0 §13, giữ nguyên).
        """
        ...
```

```python
# identity_restoration/application/ports/artifact_sink.py
class ArtifactSinkPort(Protocol):
    def write_atomic(self, key: str, data: bytes) -> PersistedArtifact:
        """Ghi tmp → fsync → rename. Không bao giờ để lộ file ghi dở.
        Trả về đường dẫn + sha256."""
        ...

# identity_restoration/application/ports/qc_gateway.py
class QcGatewayPort(Protocol):
    def validate(self, composite_path: str, a2_path: str) -> QcResult:
        """BỌC validator_studio HIỆN CÓ. Hành vi không được đổi.
        Mặc định samples=3 (đã fix non-determinism 2026-07-17).
        Port này KHÔNG được chứa ngưỡng — ngưỡng thuộc 07F."""
        ...

# identity_restoration/application/ports/ledger.py
class RestorationLedgerPort(Protocol):
    def append(self, entry: LedgerEntry) -> None:
        """Append-only JSONL. Ghi cả khi THÀNH CÔNG và khi THẤT BẠI.
        Attempt fail bị mất khỏi ledger = benchmark nói dối (v1.0 §9 quy tắc 3, giữ nguyên)."""
        ...

# identity_restoration/application/ports/concurrency.py
class ConcurrencyLeasePort(Protocol):
    @contextmanager
    def acquire(self, key: str, ttl_seconds: int) -> Iterator[Lease]:
        """max_concurrent=1 ở Phase 3–5. 6 GB VRAM không chịu được 2 workflow song song;
        biểu hiện sẽ là OOM ngẫu nhiên, rất khó chẩn đoán."""
        ...

# identity_restoration/application/ports/clock.py
class ClockPort(Protocol):
    def now(self) -> datetime: ...
    def monotonic(self) -> float: ...
    # Tồn tại để test timeout/TTL không cần sleep thật.
```

---
---

# PHẦN 7 — APPLICATION USE CASE

## 7.1 Trách nhiệm

```text
 1  resolve restorer từ registry (id đã validate)
 2  verify A2 authority SHA-256                    ← FAIL CỨNG, miễn phí
 3  verify crop/mask contract (kích thước, mode)   ← FAIL CỨNG, miễn phí
 4  verify attempt uniqueness (đường dẫn chưa tồn tại)
 5  worker health gate (cached TTL)
 6  acquire concurrency lease
 7  kiểm tra cancel request TRƯỚC KHI tốn tài nguyên
 8  restorer.restore()  ĐÚNG MỘT LẦN
 9  verify bytes: decode được · MIME · HÌNH HỌC khớp
10  composite crop → canvas (domain, thuần)
11  pixel-lock guard                                ← FAIL CỨNG nếu vi phạm
12  chạy QC gateway (validator hiện có, samples=3)
13  ghi artifact atomic + ledger entry
14  build lineage cho manifest 1.3
15  trả RestorationResult đã sanitize
16  finally: release lease — LUÔN LUÔN, kể cả khi exception
```

## 7.2 Không thuộc trách nhiệm

```text
KHÔNG dựng HTTP client. KHÔNG parse response ComfyUI. KHÔNG render UI.
KHÔNG đổi ngưỡng validator. KHÔNG quyết định official. KHÔNG tự retry.
KHÔNG ghi manifest (đó là việc của venho-os — GW-D3).
```

## 7.3 Thuật toán tham chiếu

```python
# identity_restoration/application/use_cases/restore_face_crop.py
#
# ĐỌC TRƯỚC KHI SỬA:
#   * Đúng MỘT lời gọi restorer trong hàm này. Nếu bạn thấy mình thêm call site
#     thứ hai, bạn đang thêm chi phí ẩn và làm ledger sai.
#   * Mọi thứ TRƯỚC bước 8 là miễn phí. Mọi thứ SAU nó đã tốn GPU-time thật.
#     Đó là lý do thứ tự dưới đây không tuỳ tiện: mọi phép loại rẻ tiền chạy trước.
#   * Không nuốt exception. Fail phải NHÌN THẤY ĐƯỢC. "Fake completion" là
#     failure mode tệ nhất của hệ thống này.

class RestoreFaceCropUseCase:
    def execute(self, cmd: RestoreCommand) -> RestorationResult:
        restorer = self._registry.resolve(cmd.restorer_id)

        # 2–4: rẻ, loại sớm
        a2 = self._a2_repo.load()
        a2.verify(cmd.a2_sha256)                    # ERR_GW_A2_HASH_MISMATCH
        crop, mask = self._load_and_validate_inputs(cmd)
        self._assert_attempt_is_new(cmd)

        # 5: health gate
        health = self._health.probe()
        if health.status is WorkerStatus.OFFLINE:
            return self._fail(cmd, "ERR_GW_WORKER_OFFLINE", retryable=True)

        started = self._clock.monotonic()
        with self._lease.acquire(key="gpu_worker", ttl_seconds=cmd.timeout_s + 60):
            if self._is_cancel_requested(cmd.run_id):
                return self._cancelled(cmd)

            # ══════════ RANH GIỚI TỐN KÉM — DƯỚI ĐÂY LÀ GPU-TIME THẬT ══════════
            try:
                restored = restorer.restore(
                    RestorationRequest(
                        run_id=cmd.run_id, attempt_id=cmd.attempt_id,
                        crop_png=crop.png_bytes, mask=mask, a2=a2,
                        workflow_id=cmd.workflow_id, seed=cmd.seed, params=cmd.params,
                    )
                )
            except RestorationError as err:
                self._ledger.append(LedgerEntry.failure(cmd, err, health))
                return self._fail(cmd, err.code, retryable=err.retryable)

            restored.assert_geometry_matches(...)    # ERR_GW_GEOMETRY_MISMATCH

            composite = composite_crop_into_canvas(  # domain, thuần
                base_canvas=cmd.base_canvas_bytes,
                restored_crop=restored, transform=cmd.crop_transform, mask=mask,
            )
            pixel = assert_pixels_preserved(
                before_canvas=cmd.base_canvas_bytes,
                after_canvas=composite.png_bytes,
                editable_mask=mask.editable,
            )
            if not pixel.passed:
                # FAIL CỨNG. Một khuôn mặt đẹp không mua được quyền đổi pixel
                # ngoài vùng khoá.
                self._ledger.append(LedgerEntry.pixel_violation(cmd, pixel))
                return self._fail(cmd, "ERR_GW_PIXEL_LOCK_VIOLATED", retryable=False)

            composite_art = self._sink.write_atomic(
                key=f"{cmd.run_id}/{cmd.attempt_id}/composite.png",
                data=composite.png_bytes,
            )
            qc = self._qc.validate(composite_art.path, a2_path=self._a2_repo.path)

        runtime_ms = int((self._clock.monotonic() - started) * 1000)
        status = self._decide_status(qc, pixel)      # KHÔNG BAO GIỜ trả "OFFICIAL"
        self._ledger.append(LedgerEntry.success(cmd, qc, pixel, runtime_ms, restorer))
        return RestorationResult(status=status, lineage=..., qc=qc, pixel_lock=pixel)
```

---
---

# PHẦN 8 — INFRASTRUCTURE: COMFYUI ADAPTER

## 8.1 Node registry — nguồn duy nhất (GW-D7)

```python
# identity_restoration/infrastructure/comfyui/node_registry.py
#
# NGUỒN DUY NHẤT cho mọi định danh gắn với ComfyUI.
#
# CẤM tuyệt đối — các chuỗi dưới đây KHÔNG được xuất hiện ở:
#   use case · domain · CLI · component React · test khẳng định hành vi nghiệp vụ ·
#   script benchmark · comment dùng như tài liệu chân lý
#
# Có test grep cưỡng chế: test_no_comfyui_string_leakage.
# Đây chính xác là biện pháp chống lại regression đã xảy ra ở v2.1, khi
# `model: "gpt-image-2"` bị hardcode thẳng vào route.ts và lọt vào manifest.

NODE_TITLES: Final[Mapping[str, str]] = MappingProxyType({
    "LOAD_CROP":      "VENHO_INPUT_CROP",
    "LOAD_MASK":      "VENHO_INPUT_MASK",
    "LOAD_A2":        "VENHO_INPUT_A2_FRONT",
    "SAMPLER":        "VENHO_SAMPLER",
    "SAVE_RESTORED":  "VENHO_OUTPUT_RESTORED_CROP",
})

WORKFLOWS: Final[Mapping[str, WorkflowDescriptor]] = MappingProxyType({
    "face_restore_win_sd15_ipadapter_v1": WorkflowDescriptor(
        filename="face_restore_win_sd15_ipadapter_v1.api.json",
        sha256="<điền ở Phase 3 — pin sau khi workflow ổn định>",
        models=("sd15_base", "ipadapter_faceid_sd15", "clip_vision_h", "insightface_buffalo_l"),
        min_vram_mb=4200,   # đo thật ở Phase 3, không đoán
    ),
})
```

> **Vì sao bind bằng `_meta.title` chứ không bằng node ID:** node ID trong ComfyUI
> thay đổi mỗi lần workflow được lưu lại từ UI. Bind theo ID nghĩa là mọi lần chạm
> workflow đều âm thầm phá adapter. `_meta.title` do ta đặt và ta kiểm soát.
> v1.0 nói đúng điều này — v2.0 chỉ bổ sung nơi lưu và cơ chế cưỡng chế.

## 8.2 Upload namespacing — sửa GW-E9

```python
# identity_restoration/infrastructure/comfyui/http_client.py
#
# ⚠️ HAI HAZARD THẬT CỦA /upload/image — cả hai đều im lặng:
#
#   1. Mặc định ComfyUI GHI ĐÈ theo tên file. Hai job dùng chung tên
#      "crop.png" sẽ giẫm lên nhau, và biểu hiện là "mặt của job khác"
#      — cực khó chẩn đoán vì không có lỗi nào được ném ra.
#
#   2. Khi overwrite=false, ComfyUI TỰ ĐỔI TÊN (thêm hậu tố). Tên bạn gửi đi
#      KHÔNG chắc là tên tồn tại trên worker.
#      → LUÔN đọc `name` và `subfolder` từ response. KHÔNG BAO GIỜ giả định.
#
# Quy tắc bắt buộc:
#   subfolder = f"venho/{run_id}/{attempt_id}"
#   overwrite = False
#   dùng giá trị TRẢ VỀ để bind vào workflow graph.

def upload_image(self, data: bytes, filename: str,
                 run_id: str, attempt_id: str) -> UploadedRef:
    resp = self._post_multipart(
        "/upload/image",
        files={"image": (filename, data, "image/png")},
        data={"overwrite": "false", "type": "input",
              "subfolder": f"venho/{run_id}/{attempt_id}"},
    )
    body = resp.json()
    return UploadedRef(
        name=body["name"],                  # ← nguồn chân lý, không phải `filename`
        subfolder=body.get("subfolder", ""),
        type=body.get("type", "input"),
    )
```

## 8.3 Endpoint contract

| Endpoint | Method | Dùng để | Ghi chú |
|---|---|---|---|
| `/system_stats` | GET | health, gpuName, VRAM | Nền của `WorkerHealthPort` |
| `/upload/image` | POST | 3 input | Namespace bắt buộc (8.2) |
| `/prompt` | POST | queue graph | Trả `prompt_id` |
| `/history/{prompt_id}` | GET | poll kết quả | GW-D8, backoff |
| `/view` | GET | tải output | Params từ history, không tự dựng |
| `/interrupt` | POST | huỷ | Chỉ dùng khi cancel |

```python
# Backoff policy — đặt ở đây để không bị gõ lại rải rác:
#   poll đầu tiên sau 2s, sau đó ×1.5, trần 10s.
#   Tổng thời gian không vượt request.timeoutSeconds.
#   Hết giờ → ERR_GW_WORKER_TIMEOUT + gọi /interrupt (dọn dẹp lịch sự,
#   nhưng không phụ thuộc vào việc nó thành công).
```

## 8.4 Health + circuit breaker

```python
# identity_restoration/infrastructure/health/cached_worker_health.py
#
# Ba trạng thái, không phải hai:
#   HEALTHY   — /system_stats OK, VRAM free ≥ workflow.min_vram_mb
#   DEGRADED  — OK nhưng VRAM free < ngưỡng → CẢNH BÁO, vẫn cho chạy, ghi vào ledger
#   OFFLINE   — không kết nối được hoặc lỗi → CHẶN submit
#
# DEGRADED tồn tại vì: chặn thẳng khi VRAM thấp sẽ chặn cả những job vốn chạy được;
# còn cho chạy im lặng thì OOM sẽ bị quy oan cho model. Ghi nhận rồi cho chạy là
# lựa chọn trung thực nhất.
#
# TTL mặc định 30s. Circuit breaker: 3 lần OFFLINE liên tiếp → mở mạch 5 phút,
# trả OFFLINE ngay không probe, tránh treo mỗi job 10s vô ích.
```

## 8.5 Bảng ánh xạ lỗi

| Biểu hiện từ ComfyUI | Mã ERR_GW_* | Retryable | Xử lý |
|---|---|:---:|---|
| Connection refused / timeout `/system_stats` | `ERR_GW_WORKER_OFFLINE` | ✅ | Chặn submit, job fail hiển thị |
| `/prompt` trả 400 + validation error | `ERR_GW_WORKFLOW_INVALID` | ❌ | Workflow sai — người sửa, không retry |
| Node title không tìm thấy trong graph | `ERR_GW_NODE_BINDING_FAILED` | ❌ | Registry lệch workflow file |
| History có `status.status_str == "error"`, message chứa OOM/CUDA out of memory | `ERR_GW_VRAM_EXHAUSTED` | ⚠️ Tối đa 1 lần | Ghi rõ, **không loop vô hạn** |
| History `completed` nhưng `outputs` rỗng | `ERR_GW_EMPTY_OUTPUT` | ❌ | Artifact verification FAIL |
| `/view` trả bytes không decode được | `ERR_GW_EMPTY_OUTPUT` | ❌ | |
| Kích thước output ≠ request | `ERR_GW_GEOMETRY_MISMATCH` | ❌ | **Không tự resize** |
| Quá `timeoutSeconds` | `ERR_GW_WORKER_TIMEOUT` | ✅ | `/interrupt` rồi fail |

---
---

# PHẦN 9 — WINDOWS GPU WORKER

## 9.1 Thực tế phần cứng

```text
GTX 1660 Super
  Kiến trúc  Turing TU116
  VRAM       6 GB GDDR6
  Compute    7.5  (PyTorch cu12x hỗ trợ đầy đủ)
  Tensor core  KHÔNG CÓ  ← điểm mấu chốt, xem 9.2
  Băng thông 336 GB/s

HỆ QUẢ THIẾT KẾ:
  - SDXL + PuLID: không khả thi ở 6 GB. GW-D5 chọn SD1.5 là đúng.
  - SD1.5 UNet fp16 ≈ 1.7 GB · CLIP-Vision (IPAdapter) ≈ 1.2 GB
    → còn dư cho latent ở 512–768 px. Crop đã normalize nên đây là fit tự nhiên.
  - InsightFace chạy CPU qua onnxruntime — chấp nhận được, tăng vài trăm ms.
  - Concurrency = 1. Bắt buộc. Không thương lượng ở Phase 3–5.
```

## 9.2 ⚠️ Hazard fp16 của dòng GTX 16xx — GW-E8

```text
VẤN ĐỀ ĐÃ BIẾT RỘNG RÃI:
Dòng GTX 16xx (TU116/TU117) thiếu tensor core và nổi tiếng cho ra
ẢNH ĐEN hoặc NaN khi chạy half-precision trong Stable Diffusion —
thường ở khâu VAE decode.

Nếu không xử lý trước, Phase 1 sẽ fail và gần như chắc chắn bị chẩn đoán nhầm là
"model kém" hoặc "workflow sai". Đó là ngõ cụt tốn nhiều ngày nhất của kế hoạch này.

MA TRẬN FLAG — thử THEO THỨ TỰ, dừng ở cái đầu tiên chạy được:

  A  --lowvram --fp32-vae          ← giả thuyết mặc định: fp16 UNet + fp32 VAE
  B  --lowvram --force-fp32        ← an toàn, chậm hơn đáng kể
  C  --novram  --force-fp32        ← chỉ khi B vẫn OOM

⚠️ TÔI KHÔNG CHẮC CHẮN tên flag chính xác ở phiên bản ComfyUI hiện tại —
tên flag có thay đổi giữa các bản. AI agent PHẢI chạy `python main.py --help`
và ghi lại danh sách flag THẬT vào WINDOWS_WORKER_RUNBOOK.md trước khi chốt.
Không copy mù ma trận trên.

BÀI TEST CHẨN ĐOÁN BẮT BUỘC (Phase 1, trước khi cài node identity nào):
  Sinh 1 ảnh 512×512 bằng workflow txt2img SD1.5 trần.
  Kiểm tra: ảnh KHÔNG toàn đen, độ lệch chuẩn pixel > 5.
  Fail → thử flag tiếp theo. Ghi lại flag thắng cuộc vào worker.env.
```

## 9.3 Cây thư mục Windows

```text
C:\VenHoGPU\
├── comfyui\                      # bản cài ComfyUI — KHÔNG sửa file trong này bằng tay
├── venv\                         # Python env cô lập
├── models\
│   ├── checkpoints\              # sd15 base
│   ├── ipadapter\                # ip-adapter-faceid sd15
│   ├── clip_vision\
│   └── insightface\              # buffalo_l
├── venho_workflows\              # ⚠️ ĐÍCH DEPLOY — không phải nơi tác giả sửa (GW-D6)
│   └── face_restore_win_sd15_ipadapter_v1.api.json
├── scripts\
│   ├── gpu_probe.py              # Phase 1 DoD: CUDA, tên GPU, VRAM → JSON
│   ├── fp16_sanity_check.py      # 9.2 — bài test ảnh đen
│   ├── start_worker.ps1          # khởi động có flag đúng, bind tailnet
│   ├── deploy_workflows.ps1      # nhận workflow từ repo, verify SHA-256
│   └── cleanup_worker_cache.ps1  # GW-E11 retention
├── input\                        # ComfyUI ghi vào — namespace venho/{runId}/{attemptId}
├── output\                       # TẠM. Xoá sau 7 ngày. KHÔNG BAO GIỜ là artifact chính thức.
├── logs\                         # xoay vòng, giữ 30 ngày
├── cache\
└── worker.env                    # cấu hình cục bộ máy — KHÔNG commit
```

## 9.4 Retention — sửa GW-E11

```powershell
# cleanup_worker_cache.ps1 — chạy hằng ngày qua Task Scheduler
# Lý do tồn tại: không có nó, đĩa đầy sau vài tuần và job sẽ fail vì lý do
# chẳng liên quan gì tới model — dạng lỗi tốn thời gian chẩn đoán nhất.
#   output\  giữ 7 ngày
#   input\   giữ 3 ngày   (crop/mask/A2 đã có bản gốc bên Mac, không mất mát)
#   logs\    giữ 30 ngày
#   cache\   dọn khi > 20 GB
```

## 9.5 Startup

```powershell
# start_worker.ps1
#   1. kích hoạt venv
#   2. nạp worker.env (đọc flag fp16 thắng cuộc từ 9.2)
#   3. bind 127.0.0.1:8188  ← KHÔNG BAO GIỜ 0.0.0.0 (GW-D9)
#   4. expose qua Tailscale tailnet
#   5. ghi log ra logs\comfyui_{yyyyMMdd}.log
# Đăng ký Task Scheduler chạy lúc logon. KHÔNG dùng Windows Service —
# ComfyUI cần user session để truy cập GPU đúng cách.
```

---
---

# PHẦN 10 — FILE TREE HOÀN CHỈNH

**Chú thích:** ★ = file MỚI do plan này tạo · ○ = file HIỆN CÓ cần sửa · không dấu = hiện có, không đụng

## 10.1 `venho-ai-studio` (Python) — repo chính

```text
venho-ai-studio/
│
├── CLAUDE.md                                              ○ thêm mục identity_restoration
├── task_memory.md                                         ○ cập nhật cuối mỗi Phase
├── task_status.md                                         ○ cập nhật cuối mỗi Phase
├── pyproject.toml                                         ○ thêm entrypoint `venho-restore`
│
├── identity_restoration/                                  ★ BOUNDED CONTEXT MỚI (GW-D2)
│   ├── __init__.py                                        ★ MODULE_ID = "IDR" (KHÔNG phải M11)
│   │
│   ├── domain/                                            ★ THUẦN — không I/O, không import bên thứ 3
│   │   ├── __init__.py
│   │   ├── entities.py                                    ★ A2Authority, CropTransform, MaskSet,
│   │   │                                                  #  RestorationRequest, RestoredCrop, Composite
│   │   ├── value_objects.py                               ★ RestorerId, WorkflowId, Seed,
│   │   │                                                  #  RestorationParams, VramClass
│   │   ├── errors.py                                      ★ RestorationError + toàn bộ ERR_GW_*
│   │   ├── compositing.py                                 ★ composite_crop_into_canvas() — thuần
│   │   └── policies/
│   │       ├── __init__.py
│   │       ├── pixel_preservation.py                      ★ assert_pixels_preserved()
│   │       ├── geometry.py                                ★ CropTransform round-trip invariant
│   │       └── promotion.py                               ★ is_full_gate_pass() / cấm is_official()
│   │
│   ├── application/                                       ★ định nghĩa Port, KHÔNG import adapter
│   │   ├── __init__.py
│   │   ├── ports/
│   │   │   ├── __init__.py
│   │   │   ├── identity_restorer.py                       ★ ⭐ PORT TRUNG TÂM
│   │   │   ├── worker_health.py                           ★
│   │   │   ├── artifact_sink.py                           ★
│   │   │   ├── qc_gateway.py                              ★
│   │   │   ├── ledger.py                                  ★
│   │   │   ├── concurrency.py                             ★
│   │   │   ├── a2_authority_repository.py                 ★
│   │   │   ├── workflow_repository.py                     ★
│   │   │   └── clock.py                                   ★
│   │   ├── dto/
│   │   │   ├── __init__.py
│   │   │   ├── restore_command.py                         ★
│   │   │   ├── restoration_result.py                      ★
│   │   │   └── restorer_descriptor.py                     ★
│   │   ├── registry/
│   │   │   ├── __init__.py
│   │   │   └── restorer_registry.py                       ★ resolve + preflight capability
│   │   └── use_cases/
│   │       ├── __init__.py
│   │       ├── restore_face_crop.py                       ★ ⭐ USE CASE TRUNG TÂM (PHẦN 7.3)
│   │       ├── check_worker_health.py                     ★
│   │       └── run_identity_benchmark.py                  ★ Phase 4
│   │
│   ├── infrastructure/                                    ★ implement Port
│   │   ├── __init__.py
│   │   ├── comfyui/
│   │   │   ├── __init__.py
│   │   │   ├── node_registry.py                           ★ ⭐ NGUỒN DUY NHẤT (GW-D7)
│   │   │   ├── http_client.py                             ★ upload/prompt/history/view + backoff
│   │   │   ├── graph_binder.py                            ★ bind theo _meta.title, không theo node id
│   │   │   ├── workflow_repository.py                     ★ đọc + verify SHA-256
│   │   │   └── error_mapper.py                            ★ bảng PHẦN 8.5
│   │   ├── restorers/
│   │   │   ├── __init__.py
│   │   │   ├── comfyui_remote_restorer.py                 ★ adapter chính
│   │   │   ├── nano_banana_edit_restorer.py               ★ baseline so sánh (GW-D11)
│   │   │   └── mock_restorer.py                           ★ ⭐ MẶC ĐỊNH TRONG TEST (GW-D10)
│   │   ├── health/
│   │   │   ├── __init__.py
│   │   │   ├── comfyui_health_probe.py                    ★
│   │   │   └── cached_worker_health.py                    ★ TTL + circuit breaker
│   │   ├── persistence/
│   │   │   ├── __init__.py
│   │   │   ├── atomic_file_artifact_sink.py               ★ tmp → fsync → rename
│   │   │   ├── jsonl_restoration_ledger.py                ★ append-only
│   │   │   ├── file_a2_authority_repository.py            ★
│   │   │   └── file_concurrency_lease.py                  ★ max_concurrent=1
│   │   ├── qc/
│   │   │   ├── __init__.py
│   │   │   └── validator_studio_qc_gateway.py             ★ BỌC validator hiện có, không sửa nó
│   │   ├── system/
│   │   │   ├── __init__.py
│   │   │   └── system_clock.py                            ★
│   │   └── composition/
│   │       ├── __init__.py
│   │       ├── identity_restoration_module.py             ★ ⭐ COMPOSITION ROOT (PHẦN 3.5)
│   │       └── env.py                                     ★ read_restoration_env() — nơi DUY NHẤT
│   │                                                      #  đọc os.environ
│   │
│   ├── interface/
│   │   ├── __init__.py
│   │   ├── cli.py                                         ★ `venho-restore run|health|benchmark`
│   │   └── json_bridge.py                                 ★ hợp đồng stdin/stdout cho venho-os
│   │
│   └── workflows/                                         ★ ⭐ WORKFLOW LÀ SOURCE CODE (GW-D6)
│       ├── README.md                                      ★ quy tắc sửa + quy trình pin hash
│       ├── face_restore_win_sd15_ipadapter_v1.api.json    ★ workflow POC
│       └── _archive/
│           └── face_restore_v1_api.json                   ○ SDXL/PuLID cũ — GIỮ, không ghi đè
│
├── contracts/                                             ○ thư mục hiện có, thêm 5 schema
│   ├── restoration_request.schema.json                    ★
│   ├── restoration_result.schema.json                     ★
│   ├── restoration_manifest_1_3.schema.json               ★
│   ├── worker_health.schema.json                          ★
│   ├── benchmark_row.schema.json                          ★
│   └── fixtures/identity_restoration/                     ★
│       ├── request_valid.json · request_invalid_denoise.json
│       ├── result_full_gate_pass.json · result_pixel_violation.json
│       └── comfyui/                                       ★ recorded HTTP fixtures (GW-D10)
│           ├── system_stats_healthy.json
│           ├── system_stats_low_vram.json
│           ├── upload_image_renamed.json                  #   ca GW-E9: server đổi tên
│           ├── prompt_queued.json
│           ├── history_completed.json
│           ├── history_error_oom.json
│           └── history_completed_empty_outputs.json
│
├── config/
│   └── projects/venho_hotel/
│       └── identity_restoration/                          ★
│           ├── restoration.yaml                           ★ restorer mặc định, timeout, TTL
│           ├── workflow_pins.yaml                         ★ workflowId → sha256 → models
│           └── benchmark_set.yaml                         ★ B01–B10 (PHẦN 14)
│
├── docs/
│   └── identity-restoration/                              ★
│       ├── ADR-GW-001-restorer-port.md                    ★
│       ├── ADR-GW-002-no-new-module-number.md             ★
│       ├── ADR-GW-003-repo-boundary.md                    ★
│       ├── ADR-GW-004-sd15-ipadapter-poc.md               ★
│       ├── ADR-GW-005-workflow-as-source.md               ★
│       ├── ADR-GW-006-polling-over-websocket.md           ★
│       ├── ADR-GW-007-tailscale-not-lan.md                ★
│       ├── ADR-GW-008-mock-first-testing.md               ★
│       ├── BASELINE_PROBE_2026-08-18.md                   ★ output của PHẦN 0.5
│       ├── BENCHMARK_PROTOCOL.md                          ★
│       ├── WINDOWS_WORKER_RUNBOOK.md                      ★ gồm flag fp16 THẬT (9.2)
│       └── SUPERSEDED_v1_0_ROADMAP.md                     ★ con trỏ tới file v1.0
│
├── scripts/
│   ├── deploy_workflows_to_worker.py                      ★ đẩy repo → Windows, verify hash
│   └── probe_gpu_worker.py                                ★ health CLI một phát
│
└── tests/
    └── identity_restoration/                              ★
        ├── conftest.py                                    ★ fixture: mock restorer, fake clock
        ├── test_layering.py                               ★ ⭐ CƯỠNG CHẾ dependency rule
        ├── test_no_comfyui_string_leakage.py              ★ ⭐ CƯỠNG CHẾ GW-D7
        ├── domain/
        │   ├── test_a2_authority.py · test_crop_transform_roundtrip.py
        │   ├── test_compositing.py · test_pixel_preservation.py
        │   └── test_promotion_policy.py                   #   khẳng định is_official() luôn raise
        ├── application/
        │   ├── test_restore_face_crop_use_case.py         #   happy path + mọi nhánh fail
        │   ├── test_single_provider_call.py               #   ⭐ khẳng định gọi ĐÚNG 1 lần
        │   ├── test_lease_released_on_exception.py
        │   └── test_cancel_before_spend.py
        ├── infrastructure/
        │   ├── test_comfyui_http_client.py                #   dùng recorded fixtures, 0 network
        │   ├── test_upload_namespacing.py                 #   ⭐ ca GW-E9 đổi tên
        │   ├── test_graph_binder.py                       #   bind theo title, ID đổi vẫn chạy
        │   ├── test_error_mapper.py                       #   bảng 8.5 phủ hết
        │   ├── test_cached_worker_health.py               #   TTL + circuit breaker, fake clock
        │   └── test_atomic_artifact_sink.py               #   không lộ file ghi dở
        └── contracts/
            └── test_schema_fixtures.py                    #   mọi fixture pass/fail đúng kỳ vọng
```

## 10.2 `venho-os` (Next.js) — thay đổi tối thiểu

```text
venho-os/
├── src/
│   ├── app/api/v1/studio/
│   │   └── identity-restoration/
│   │       ├── route.ts                                   ★ POST tạo job restoration
│   │       └── health/route.ts                             ★ GET health worker (qua Python)
│   ├── server/studio/
│   │   ├── identity-restoration/
│   │   │   ├── restoration-bridge.ts                       ★ execFile venho-restore + parse JSON
│   │   │   │                                               #  ⚠️ ĐÂY là nơi DUY NHẤT chạm Python
│   │   │   ├── restoration-types.ts                        ★ sinh từ contracts/*.schema.json
│   │   │   └── manifest-1-3.ts                             ★ ghi phần restoration vào manifest
│   │   ├── job-store.ts                                    ○ thêm stage GPU_RESTORING/COMPOSITING
│   │   └── manifest.ts                                     ○ 1.2 → 1.3, giữ backward compat
│   └── app/os/studio/image/
│       └── components/
│           ├── RestorerSelector.tsx                        ★ chọn restorer (mặc định cloud)
│           └── RestorationEvidencePanel.tsx                ★ Face QC · Pixel Lock · workflow · runtime
└── src/server/studio/__tests__/
    ├── restoration-bridge.test.ts                          ★ mock subprocess, 0 network
    └── no-direct-comfyui-access.test.ts                    ★ ⭐ CƯỠNG CHẾ GW-D4
```

```typescript
// no-direct-comfyui-access.test.ts — nội dung cốt lõi
//
// Vì sao test này tồn tại: v1.0 nói "Dashboard không được dựng workflow ComfyUI thô"
// nhưng không có cách nào cưỡng chế. Một câu văn không ngăn được ai cả.
// Grep test thì ngăn được.
it("không file .ts/.tsx nào chạm ComfyUI trực tiếp", () => {
  const hits = grepRepo(/comfyui|:8188|\/upload\/image|\/history\//i, {
    include: ["src/**/*.ts", "src/**/*.tsx"],
    exclude: ["**/restoration-bridge.ts", "**/*.test.ts"],
  });
  expect(hits).toEqual([]);   // ComfyUI chỉ tồn tại phía Python (GW-D4)
});
```

## 10.3 `C:\VenHoGPU\` — Windows worker

Xem PHẦN 9.3. Nhắc lại nguyên tắc: **cây này là trạng thái máy, không phải source code.**
Chỉ `venho_workflows\` có bản sao chân lý trong Git; mọi thứ còn lại có thể xoá và dựng lại
từ `WINDOWS_WORKER_RUNBOOK.md`.

---
---

# PHẦN 11 — CONFIG & ENVIRONMENT

```bash
# .env (venho-ai-studio) — KHÔNG commit
# Đọc DUY NHẤT ở infrastructure/composition/env.py

IDR_DEFAULT_RESTORER=mock            # mock | comfyui-remote | nano-banana-edit
                                     # ⚠️ mặc định mock — bật thật là hành động CÓ Ý THỨC

IDR_COMFYUI_ENABLED=false
IDR_COMFYUI_BASE_URL=http://venho-gpu-win:8188   # tên tailnet, KHÔNG phải IP thô (GW-D9)
IDR_COMFYUI_TIMEOUT_SECONDS=600      # đo thật ở Phase 3 rồi chỉnh
IDR_HEALTH_TTL_SECONDS=30
IDR_HEALTH_TIMEOUT_SECONDS=5

IDR_WORKFLOW_ROOT=identity_restoration/workflows
IDR_ARTIFACT_ROOT=data/projects/venho_hotel/identity_restoration
IDR_LEDGER_PATH=data/projects/venho_hotel/identity_restoration/ledger.jsonl
IDR_A2_PATH=assets/linh_an/A2_Front.png
IDR_MAX_CONCURRENT=1                 # KHÔNG tăng trước khi Phase 5 đo xong VRAM
```

```yaml
# config/projects/venho_hotel/identity_restoration/workflow_pins.yaml
version: 1
workflows:
  face_restore_win_sd15_ipadapter_v1:
    sha256: "<điền ở Phase 3>"       # workflow đổi mà hash không đổi = FAIL CỨNG
    models:
      checkpoint:  "v1-5-pruned-emaonly.safetensors"
      ipadapter:   "ip-adapter-faceid_sd15.bin"
      clip_vision: "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
      insightface: "buffalo_l"
    min_vram_mb: 4200                # ĐO ở Phase 3, không đoán
    defaults:
      denoise: 0.45                  # điểm khởi đầu, Phase 4 sẽ sweep
      steps: 28
      cfg: 5.5
      sampler: "dpmpp_2m"
      scheduler: "karras"
```

```text
KHÔNG BAO GIỜ COMMIT:
  worker.env · IP thật của máy · Tailscale auth key · API key
  đường dẫn tuyệt đối cá nhân (/Users/hanhpham/...) · workflow override chưa version

⚠️ Nhắc lại bài học 2026-07-17: một lệnh `source <(grep ... .env.local)` đã làm
lộ OPENAI_API_KEY vào transcript. Không bao giờ dump env ra stdout, kể cả khi debug.
`json_bridge.py` phải sanitize mọi error message trước khi in.
```

---
---

# PHẦN 12 — TEST & EVAL

## 12.1 Kỷ luật bất biến

```text
0 API call · 0 network call · 0 GPU call trong pytest.
Restorer mặc định trong test là `mock`. Không có ngoại lệ, không có "chỉ lần này".
Toàn bộ hành vi HTTP kiểm bằng recorded fixture ở contracts/fixtures/comfyui/.
```

## 12.2 Kim tự tháp test

| Tầng | Kiểm cái gì | Số test mục tiêu |
|---|---|---:|
| Domain | Toán học thuần: crop round-trip, pixel lock, promotion policy | ~25 |
| Application | Điều phối use case, thứ tự, nhánh lỗi, lease | ~20 |
| Infrastructure | HTTP contract qua fixture, error mapping, health TTL | ~25 |
| Contract | Fixture pass/fail đúng schema | ~10 |
| Kiến trúc | Layering + string leakage + no-direct-comfyui | 3 |
| **Tổng thêm mới** | | **~83** |

## 12.3 Test bắt buộc phải có — nếu thiếu là Phase chưa xong

```python
# 1. Gọi provider ĐÚNG MỘT LẦN — chống chi phí ẩn
def test_restorer_called_exactly_once(): ...

# 2. Lease luôn được trả — kể cả khi restorer ném exception
def test_lease_released_on_restorer_exception(): ...

# 3. Cancel trước điểm tốn kém — không tiêu GPU-time cho job đã huỷ
def test_cancel_checked_before_restore_call(): ...

# 4. Pixel lock là FAIL CỨNG — mặt đẹp không mua được quyền đổi pixel
def test_pixel_violation_fails_even_when_face_qc_is_perfect(): ...

# 5. ⭐ Đổi compute host KHÔNG đổi domain — đây là bằng chứng sống của ADR-GW-001
def test_swapping_restorer_does_not_change_domain_behaviour():
    """Chạy cùng một RestoreCommand qua mock và qua fake-comfyui.
    Domain output (transform, mask, composite geometry) phải GIỐNG HỆT.
    Nếu test này fail, kiến trúc đã rò rỉ — sửa kiến trúc, đừng sửa test."""

# 6. ⭐ ComfyUI đổi tên file upload — ca GW-E9
def test_upload_uses_server_returned_name_not_requested_name(): ...

# 7. Bind theo title, không theo node id
def test_graph_binder_survives_node_id_renumbering(): ...

# 8. Manifest 1.2 cũ vẫn đọc được
def test_manifest_1_2_still_parses(): ...

# 9. is_official() luôn raise
def test_no_code_path_creates_official_asset(): ...
```

## 12.4 Test cưỡng chế kiến trúc

```python
# tests/identity_restoration/test_layering.py
FORBIDDEN_IN_DOMAIN = {"requests","httpx","PIL.Image.open","os.environ",
                       "pathlib.Path.read_bytes","datetime.now","random"}

def test_domain_has_no_io_imports():
    """Domain nhận bytes, trả bytes. Nếu nó cần đọc file hay xem giờ,
    thứ đó thuộc infrastructure. Test này không phải hình thức —
    nó là cái duy nhất giữ cho domain test được mà không cần máy Windows."""

def test_application_does_not_import_infrastructure():
    """Application định nghĩa Port. Nếu nó import adapter, mũi tên phụ thuộc
    đã đảo chiều và Clean Architecture chỉ còn là tên gọi."""
```

---
---

# PHẦN 13 — ROADMAP PHASE 0–7

> Giữ nguyên đánh số Phase của v1.0 để không gây churn.
> Mỗi Phase bổ sung: **file deliverable · DoD · exit gate · rollback**.

## GW-P0 — Baseline Freeze & Probe

| | |
|---|---|
| **Mục tiêu** | Xác minh baseline có thật, đóng băng trước khi đổi hạ tầng |
| **Tầng** | Không có code sản phẩm |
| **Deliverable** | `BASELINE_PROBE_2026-08-18.md` · `SUPERSEDED_v1_0_ROADMAP.md` · 8 file ADR (bản nháp) |

```text
TASKS
[ ] TASK 0 — chạy baseline probe (PHẦN 0.5). BẮT BUỘC ĐẦU TIÊN.
[ ] Ghi commit hash hiện tại của venho-ai-studio và venho-os.
[ ] Ghi kết quả test hiện tại (kỳ vọng 841/841 Python; OS test pass).
[x] Ghi SHA-256 của A2-FRONT vào workflow_pins.yaml.
[ ] Ghi baseline Nano Banana masked-edit Face QC ≈ 88.x làm mốc so sánh.
[ ] Đánh dấu v1.0 SUPERSEDED, không xoá.
[ ] Di chuyển face_restore_v1_api.json (SDXL/PuLID) vào workflows/_archive/ — GIỮ NGUYÊN.
[ ] Viết 8 ADR bản nháp.

DoD
  Baseline reproducible · A2 authority không đổi · không production contract nào bị gỡ
  Toàn bộ việc Windows nằm sau feature flag (IDR_COMFYUI_ENABLED=false)

ROLLBACK  Không có gì để rollback — Phase này chỉ đọc và ghi tài liệu.
```

## GW-P1 — Windows GPU Worker

| | |
|---|---|
| **Mục tiêu** | Biến máy Windows thành compute worker chuyên dụng |
| **Tầng** | Infrastructure host (không code repo) |
| **Deliverable** | `gpu_probe.py` · `fp16_sanity_check.py` · `start_worker.ps1` · `WINDOWS_WORKER_RUNBOOK.md` |

```text
TASKS
[ ] Xác nhận Windows nhận GTX 1660 Super, driver NVIDIA khỏe.
[ ] Tạo venv cô lập, cài PyTorch CUDA. Xác nhận torch.cuda.is_available().
[ ] gpu_probe.py xuất JSON: gpuName, vramTotalMb, vramFreeMb, cudaVersion, torchVersion.
[ ] Cài ComfyUI vào C:\VenHoGPU\comfyui.
[ ] ⚠️ CHẠY `python main.py --help`, ghi danh sách flag THẬT vào RUNBOOK.
[ ] ⚠️ CHẠY fp16_sanity_check.py — ma trận flag PHẦN 9.2. Ghi flag thắng cuộc.
[ ] Khởi động ComfyUI bind 127.0.0.1 TRƯỚC. Chưa mở tailnet ở Phase này.
[ ] Chạy 1 workflow txt2img SD1.5 512×512 tại chỗ, xác nhận ảnh không đen.
[ ] Viết cleanup_worker_cache.ps1, đăng ký Task Scheduler.

DoD
  ComfyUI khởi động ổn định · CUDA inference chạy · 1 workflow tối thiểu hoàn tất cục bộ
  Ảnh sinh ra KHÔNG đen (std pixel > 5) · flag fp16 đã ghi vào worker.env
  KHÔNG có dependency nào của VenHo OS trên Windows

ROLLBACK  Gỡ C:\VenHoGPU. Không ảnh hưởng repo.

⚠️ RỦI RO CAO NHẤT CỦA PHASE NÀY là hazard fp16 (GW-E8). Nếu ảnh đen,
   ĐỪNG đổi model, ĐỪNG đổi workflow — đổi flag trước.
```

## GW-P2 — Port & Mock (KHÔNG CẦN MÁY WINDOWS)

| | |
|---|---|
| **Mục tiêu** | Dựng toàn bộ kiến trúc phần mềm mà chưa cần GPU |
| **Tầng** | Domain + Application + Mock adapter |
| **Deliverable** | Toàn bộ `domain/`, `application/`, `mock_restorer.py`, `composition/`, ~50 test |

> **Thay đổi so với v1.0.** v1.0 để Phase 2 là "remote contract" — tức phần mềm bị chặn
> bởi phần cứng. Đảo lại: dựng port + mock trước, phần mềm chạy xanh trước khi chạm GPU.
> Lợi ích cụ thể: nếu Windows gặp sự cố ở P1, P2 vẫn tiến được. Rủi ro lịch trình
> được tách rời thay vì nối tiếp.

```text
TASKS
[ ] Viết 5 JSON Schema + fixtures pass/fail.
[ ] Viết domain/ đầy đủ. Test round-trip CropTransform. Test pixel lock.
[ ] Viết application/ports/ đầy đủ — KHÔNG import infrastructure.
[ ] Viết RestoreFaceCropUseCase theo đúng thuật toán PHẦN 7.3.
[ ] Viết MockIdentityRestorer trả fixture bytes.
[ ] Viết Composition Root + env.py.
[ ] Viết CLI `venho-restore run --request req.json --restorer mock`.
[ ] Viết test_layering.py và test_no_comfyui_string_leakage.py.

DoD
  `venho-restore run --restorer mock` chạy end-to-end, xuất result JSON hợp lệ schema
  Toàn bộ test mới pass · 0 network call · test_layering pass
  Suite cũ 841/841 vẫn pass (không regression)

ROLLBACK  Xoá identity_restoration/. Không file hiện có nào bị sửa ngoài pyproject.toml.
```

**GW-P2: CLOSED/DONE (2026-08-20).** Xem `VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md` PHẦN 4
"GW-P2 — Extract Port" để biết chi tiết đầy đủ + 2 quyết định lệch có chủ đích khỏi patch
(không sửa `ProductionRunner`, không di chuyển vật lý domain logic). Tóm tắt: 53 test mới,
0 network, 0 regression trên suite cũ, `venho-restore run --restorer mock` smoke-tested
end-to-end.

## GW-P3 — Remote Contract & POC thật

| | |
|---|---|
| **Mục tiêu** | Nối Mac → Windows, hoàn tất một crop Linh An thật |
| **Tầng** | Infrastructure adapter |
| **Deliverable** | `comfyui/*`, `restorers/comfyui_remote_restorer.py`, workflow v1 pinned |

```text
TASKS — mạng
[ ] Bật Tailscale trên máy Windows. Xác nhận tên tailnet resolve từ Mac (GW-D9).
[ ] KHÔNG bind 0.0.0.0. KHÔNG mở port ra Internet.
[ ] `probe_gpu_worker.py` từ Mac trả HEALTHY.

TASKS — adapter
[ ] node_registry.py với NODE_TITLES + WorkflowDescriptor.
[ ] http_client.py: upload (namespaced, đọc name từ response) / prompt / history / view.
[ ] graph_binder.py bind theo _meta.title.
[ ] error_mapper.py phủ hết bảng 8.5.
[ ] cached_worker_health.py + circuit breaker.
[ ] Ghi lại recorded fixtures từ lần chạy thật đầu tiên → contracts/fixtures/comfyui/.

TASKS — workflow
[ ] Tác giả workflow SD1.5 + IPAdapter FaceID TRONG REPO (GW-D6).
[ ] Khai báo _meta.title cho 5 node.
[ ] deploy_workflows_to_worker.py đẩy sang Windows + verify SHA-256.
[ ] Pin sha256 vào workflow_pins.yaml.
[ ] Cài custom node và model file cần thiết — CHỈ những cái workflow này cần.

TASKS — chạy thật
[ ] Chạy 1 crop Linh An thật: base frame → crop/mask → Windows → restored → composite
    → pixel lock → Face QC → lineage.
[ ] Đo latency và VRAM peak thật. Cập nhật min_vram_mb và timeout.

EXIT GATE
  ⚠️ Một workflow chỉ queue thành công KHÔNG qua được Phase này.
  Phải có MỘT ẢNH THẬT đi hết chuỗi trên và có Face QC number thật.

ROLLBACK  IDR_COMFYUI_ENABLED=false → hệ thống quay về mock/nano-banana. Không mất gì.
```

**GW-P3: PARTIAL — phần mềm phía Mac xong, hạ tầng vật lý chưa (2026-08-20).** Xem
`VENHO_GW_PLAN_PATCH_v2_0_TO_v2_1.md` PHẦN 4 "GW-P3 — Remote Adapter" cho breakdown T1–T12.
node_registry/http_client/graph_binder/error_mapper/cached_worker_health/
ComfyUIRemoteRestorer/deploy script đều viết xong + test offline qua fixture soạn tay
(chưa phải bản ghi từ lần chạy thật). Tailscale probe, tác giả workflow, và một lần chạy
thật đều cần máy Windows — không thực hiện được trong phiên làm việc này.

## GW-P4 — Controlled A2 Benchmark

| | |
|---|---|
| **Mục tiêu** | Trả lời: GPU worker có cải thiện identity thật hay không |
| **Deliverable** | `BENCHMARK_PROTOCOL.md` · `benchmark_report_YYYYMMDD.md` (đăng ký Tier-1) |

Chi tiết ở PHẦN 14.

```text
DECISION GATE
  PASS  median Face QC ≥ 90, regional/pixel gate khỏe
        → promote comfyui-remote thành production-candidate restorer

  FAIL  identity dưới ngưỡng
        → KHÔNG ĐỔI KIẾN TRÚC. Giữ nguyên GPU worker architecture.
          Chỉ tune/thay workflow, model, tham số.
          Kiến trúc và model là HAI quyết định riêng biệt (giữ nguyên v1.0 — điểm này rất đúng).

  ⚠️ Nếu ngay cả sau khi sweep tham số mà median vẫn < 90: đó là dữ liệu đầu vào cho
     DR-GW-04 (xem lại ngưỡng ở 07F), KHÔNG phải cái cớ để sửa số trong plan này (GW-D12).
```

## GW-P5 — Worker Hardening

```text
TASKS
[ ] Task Scheduler tự khởi động ComfyUI khi logon.
[ ] Health hiển thị được từ Mac.
[ ] Timeout verified bằng số đo thật, không đoán.
[ ] Lỗi ComfyUI fail nhanh, không treo.
[ ] Job gián đoạn retry an toàn (attempt_id mới, không ghi đè).
[ ] Windows reboot không làm hỏng job record bên venho-os.
[ ] Cleanup script chạy thật ít nhất 1 chu kỳ.
[ ] Ghi runtime điển hình và failure mode khi thiếu VRAM.

EXIT GATE  10+ job liên tiếp không lỗi hạ tầng · lỗi quan sát được và phục hồi được
           · không có lineage artifact nào hỏng

ROLLBACK   Tắt Task Scheduler, quay về khởi động thủ công.
```

## GW-P6 — VenHo OS Dashboard Integration

```text
NGUYÊN TẮC  Dashboard → venho-os service → restoration-bridge → Python → ComfyUI
            Dashboard KHÔNG BAO GIỜ dựng hay submit workflow ComfyUI thô (GW-D4, có test).

TASKS
[ ] restoration-bridge.ts (nơi DUY NHẤT chạm Python).
[ ] Mở rộng job stage: QUEUED · BASE_READY · CROP_READY · GPU_RESTORING · COMPOSITING
    · VALIDATING · COMPLETED · FAILED · CANCELLED
    → map vào durable job contract HIỆN CÓ, KHÔNG tạo job store thứ hai.
[ ] Manifest 1.2 → 1.3, giữ backward compat.
[ ] RestorerSelector.tsx — mặc định KHÔNG phải GPU; chọn GPU là hành động có ý thức.
[ ] RestorationEvidencePanel.tsx — Face QC · Eyes/Brows · Geometry · Anatomy · Outfit
    · Environment · Pixel Lock · workflow version · runtime.
[ ] Hành động người dùng: APPROVE · RETRY FACE · REJECT.
[ ] no-direct-comfyui-access.test.ts pass.

EXIT GATE  Chạy và review trọn vẹn một job Action Composite từ VenHo OS
           mà KHÔNG cần mở ComfyUI thủ công.
```

## GW-P7 — Production Gate

```text
[ ] A2 authority verified
[ ] Benchmark hoàn tất và đã đăng ký PRODUCTION_REGISTRY.md
[ ] Median Face QC ≥ 90
[ ] Không regression giải phẫu nghiêm trọng
[ ] Pixel preservation pass
[ ] Regional gate pass
[ ] Workflow versioned và reproducible (hash pin verified)
[ ] Failure/retry path verified
[ ] Dashboard integration KHÔNG bypass QC của AI Studio
[ ] Official promotion vẫn do con người kiểm soát

TRẠNG THÁI SẢN XUẤT
  Windows ComfyUI  = local identity-restoration worker ưu tiên
  Cloud provider   = base generation / fallback
  VenHo AI Studio  = thẩm quyền QC + artifact
  VenHo OS         = human control plane
```

## 13.9 Thứ tự thực thi nghiêm ngặt

```text
 1  Baseline probe (PHẦN 0.5)          ← nếu fail, DỪNG và hỏi Harry
 2  Freeze baseline + ADR
 3  Domain + Application + Mock         ← KHÔNG cần máy Windows
 4  Validate Windows GPU + fp16 sanity
 5  Cài ComfyUI cục bộ Windows
 6  Workflow tối thiểu CUDA hoàn tất
 7  Bật tailnet
 8  Health check từ AI Studio
 9  Contract upload/queue/download
10  Cài workflow identity nhẹ
11  MỘT crop A2 thật hoàn tất
12  Validate composite + QC
13  Benchmark 10 ảnh
14  Tune workflow CHỈ KHI benchmark fail
15  Harden worker
16  Tích hợp Dashboard
17  Production gate

⚠️ KHÔNG bắt đầu redesign Dashboard trước bước 13.
   Lý do: nếu benchmark fail, toàn bộ công UI là công bỏ đi. v1.0 nói đúng, giữ nguyên.
```

---
---

# PHẦN 14 — BENCHMARK PROTOCOL

## 14.1 Bộ chuẩn 10 ảnh

```text
B01 Close-up Front        B06 Walking
B02 Half-body             B07 Sitting
B03 Full-body Standing    B08 Hair Motion
B04 Running Front 3/4     B09 West Lake
B05 Running Side          B10 Ven Ho Hotel Interior
```

## 14.2 Nhóm so sánh — bổ sung so với v1.0

v1.0 chỉ đo GPU worker. Như vậy không trả lời được câu hỏi kinh doanh thật.
Phải chạy **ba nhánh trên cùng một base frame**:

| Nhánh | Restorer | Mục đích |
|---|---|---|
| **Control** | không restoration | Face QC gốc của base frame |
| **Baseline** | `nano-banana-edit` | Mốc ~88.x đã biết |
| **Treatment** | `comfyui-remote` | Cái đang được đánh giá |

> Không có Control, ta không biết restoration cải thiện bao nhiêu điểm.
> Không có Baseline, ta không biết GPU worker có hơn thứ đã có sẵn không.
> Đây là khác biệt giữa "có số" và "có bằng chứng".

## 14.3 Chỉ số mỗi ảnh

```text
faceQcBefore · faceQcAfter · identityScore · eyesBrowsScore · geometryScore
anatomyScore · outfitScore · environmentScore · globalScore
pixelPreservationResult · runtimeMs · retryCount
workflowId · workflowSha256 · seed · gpuName · vramPeakMb · restorerId
```

Ghi mỗi dòng theo `benchmark_row.schema.json`. Face QC dùng `samples=3`
(đã fix non-determinism 2026-07-17 — chạy 1 lần là không đủ tin cậy).

## 14.4 Quy tắc

```text
1. Cùng một A2-FRONT cho mọi test.
2. KHÔNG chọn scene candidate dựa trên face score (sẽ làm hỏng tính khách quan).
3. KHÔNG giấu ảnh fail.
4. Ghi lại MỌI retry.
5. KHÔNG promotion chính thức trong lúc benchmark.
6. Manifest phải giữ nguyên lineage workflow/model/config.
7. Mỗi nhánh cùng seed để so sánh công bằng.
```

## 14.5 Tiêu chí chấp nhận

```text
Mục tiêu Action Composite hiện tại:
  Median Face QC ≥ 90 · Không regression giải phẫu · Không mutation vùng khoá

Mục tiêu hỗ trợ:
  Close-up identity success ≥ 95% · Action identity success ≥ 80%

Mục tiêu sản xuất về sau:
  Action identity success ≥ 90%

⚠️ BỐI CẢNH TRUNG THỰC: theo task_status.md, Face QC thật của toàn hệ thống
   dao động 82.5–88.8 và CHƯA TỪNG đạt 90 qua ~13 lần chạy thật.
   Đặt kỳ vọng đúng: mục tiêu của Phase 4 là ĐO, không phải chứng minh thành công.
   Một kết quả 86 được ghi trung thực có giá trị hơn một kết quả 91 đạt được bằng
   cách chọn ảnh đẹp.
```

---
---

# PHẦN 15 — FAILURE HANDLING & RUNBOOK

| Tình huống | Hành vi bắt buộc |
|---|---|
| **Worker offline** | Health fail → KHÔNG submit → job fail/block hiển thị rõ → **không bao giờ báo hoàn thành giả** |
| **VRAM exhaustion** | Bắt lỗi → tối đa 1 retry → **không loop vô hạn** → giữ audit → tune workflow riêng |
| **Identity < 90** | QC fail → không promotion → retry có trần → giữ attempt fail trong ledger |
| **Pixel mutation ngoài vùng editable** | **FAIL CỨNG.** Không chấp nhận mặt đẹp nếu worker sinh lại thân/trang phục/bối cảnh |
| **A2 hash mismatch** | **FAIL CỨNG trước restoration.** Không tốn một giây GPU nào |
| **ComfyUI xong nhưng output rỗng/hỏng** | Artifact verification FAIL |
| **Output sai kích thước** | FAIL. **Không tự resize** — resize sẽ giấu bug workflow và phá pixel lock |
| **Windows reboot giữa job** | Job → FAILED có lý do. Retry = attempt_id MỚI |
| **Đĩa Windows đầy** | Health → DEGRADED, cảnh báo Telegram, cleanup script chạy |
| **Hai job cùng lúc** | Lease chặn job thứ hai → `ERR_GW_LEASE_UNAVAILABLE`, retryable |

```text
RUNBOOK — worker không phản hồi (theo thứ tự này)
1. probe_gpu_worker.py từ Mac                    → phân biệt lỗi mạng vs lỗi ComfyUI
2. Tailscale status trên cả hai máy
3. RDP vào Windows, xem logs\comfyui_*.log
4. Kiểm tra ComfyUI process còn sống
5. Kiểm tra dung lượng đĩa
6. nvidia-smi — GPU có bị process khác chiếm?
7. Khởi động lại qua start_worker.ps1
8. Nếu ảnh đen quay lại → xem lại flag fp16 (PHẦN 9.2) TRƯỚC KHI nghi ngờ model
```

---
---

# PHẦN 16 — SECURITY & GOVERNANCE

## 16.1 Mô hình mối đe doạ — vì sao "LAN-only" chưa đủ (GW-E10)

```text
ComfyUI KHÔNG CÓ XÁC THỰC. Không password, không token, không gì cả.

Bind 0.0.0.0:8188 trên WiFi nhà nghĩa là bất kỳ thiết bị nào trong mạng —
gồm cả thiết bị khách, IoT camera, TV, điện thoại bị nhiễm — đều có thể:
  · queue workflow tuỳ ý (chiếm GPU)
  · ĐỌC file hệ thống qua node load
  · GHI file hệ thống qua node save

Đây không phải rủi ro lý thuyết; đó là hành vi mặc định.

QUYẾT ĐỊNH (GW-D9):
  ComfyUI bind 127.0.0.1 · truy cập qua Tailscale tailnet · KHÔNG expose Internet
  Tailscale đã có trong stack (infra/setup_macmini.md). Chi phí thêm ≈ 0.
  Mac gọi bằng TÊN tailnet, không bằng IP thô → IP không lọt vào manifest/log.
```

## 16.2 Governance

```text
[ ] Plan này KHÔNG tạo M-module mới (GW-D2). Muốn tạo → Change Request qua L2.
[ ] Plan này KHÔNG đổi ngưỡng QC (GW-D12). Ngưỡng thuộc 07F.
[ ] Plan này KHÔNG tạo publishing path. M07 vẫn là gateway duy nhất.
[ ] Plan này KHÔNG tạo job store thứ hai (GW-D3).
[ ] Báo cáo benchmark PHẢI đăng ký PRODUCTION_REGISTRY.md dạng Tier-1 internal.
[ ] Official promotion vẫn 100% do con người.
[ ] Mọi thay đổi kiến trúc trong file này cần CR qua L2 — không sửa ngầm.
```

---
---

# PHẦN 17 — COST MODEL

```text
PHÂN LOẠI CHI PHÍ — KHÔNG gộp, KHÔNG gọi local là "free":

  baseImageCloudCost      chi phí sinh base action frame (cloud, có thật)
  restorationLocalCost    GPU-time + điện — chi phí THẬT, không bằng 0
  restorationCloudCost    nếu dùng nano-banana-edit
  validatorApiCost        Face QC vision API × samples(3) — CÓ THẬT và không nhỏ
  retryCost               mọi attempt fail vẫn tốn

CHỈ SỐ KINH DOANH THẬT (kế thừa từ Nano Banana v3.0):
  costPerFullGatePass = totalSpend / fullGatePassCount
  Nếu fullGatePassCount == 0 → báo "N/A — chưa có full-gate pass"
  KHÔNG BAO GIỜ chia cho 0. KHÔNG BAO GIỜ báo Infinity như một con số đo được.

⚠️ Lưu ý về validator cost: mỗi lần restoration đều kéo theo Face QC với samples=3.
   Chạy benchmark 10 ảnh × 3 nhánh = 30 restoration = 90 lần gọi vision API.
   Local GPU tiết kiệm chi phí SINH ẢNH, không tiết kiệm chi phí THẨM ĐỊNH.
   Đây là điều v1.0 chưa nêu và nó ảnh hưởng trực tiếp tới ROI của cả dự án.
```

---
---

# PHẦN 18 — DECISIONS CẦN HARRY CHỐT

| ID | Câu hỏi | Vì sao cần chốt trước | Khuyến nghị |
|---|---|---|---|
| **DR-GW-01** | Baseline Action Composite v2.1.1 có thật trong repo không? | Quyết định khối lượng Phase 0. Khả năng (B) làm plan phồng gấp ~2.5 lần | Chạy TASK 0 rồi trả lời bằng dữ liệu, không bằng trí nhớ |
| **DR-GW-02** | Chấp thuận ranh giới repo GW-D3 (Python = image plane, TS = control plane)? | Chọn sai → job store thứ hai → tái phạm GR-E1 | Chấp thuận. Nó khớp pattern `execFile` đang chạy |
| **DR-GW-03** | Chấp thuận Tailscale thay LAN thô? | Ảnh hưởng setup Phase 1 | Chấp thuận. Chi phí ≈ 0, rủi ro giảm rõ rệt |
| **DR-GW-04** | Nếu benchmark cho median 86–89, xử lý thế nào? | Định trước để không phải quyết định lúc đang thất vọng | Ghi nhận, mở CR lên 07F. **Không** sửa ngưỡng trong plan này |
| **DR-GW-05** | Ngân sách benchmark Phase 4 (≈90 lần gọi vision API)? | Đã từng chạm billing hard limit thật ngày 2026-07-17 | Cần Harry duyệt ngân sách TRƯỚC Phase 4 |
| **DR-GW-06** | Máy Windows có chạy 24/7 không? | Quyết định health TTL, circuit breaker, kỳ vọng SLA | Nếu không, mặc định restorer phải là cloud, GPU là opt-in |
| **DR-GW-07** | Có giữ `nano-banana-edit` làm fallback vĩnh viễn không? | Ảnh hưởng chi phí bảo trì 2 adapter | Giữ. Nó là baseline so sánh sống và là đường lui |

---
---

# PHẦN 19 — DEFINITION OF DONE

```text
KIẾN TRÚC
 1 [ ] IdentityRestorerPort tồn tại; đổi restorer không đổi một dòng domain (test #5)
 2 [ ] Composition Root là nơi DUY NHẤT khởi tạo adapter
 3 [ ] test_layering.py pass
 4 [ ] test_no_comfyui_string_leakage.py pass
 5 [ ] no-direct-comfyui-access.test.ts pass (venho-os)
 6 [ ] Không tạo M-module mới; không tạo job store thứ hai

CONTRACT
 7 [ ] 5 JSON Schema có fixture pass và fail
 8 [ ] Manifest 1.3 ghi đủ lineage; 1.2 cũ vẫn parse được
 9 [ ] Mọi error code là ERR_GW_* có cấu trúc; không rò stack trace/env

CORRECTNESS
10 [ ] A2 hash mismatch fail TRƯỚC khi tốn GPU-time
11 [ ] Pixel lock fail cứng, kể cả khi Face QC hoàn hảo
12 [ ] Geometry mismatch fail — không tự resize
13 [ ] Gọi restorer đúng MỘT lần mỗi attempt
14 [ ] Lease luôn được trả trong finally
15 [ ] Cancel được kiểm tra TRƯỚC điểm tốn kém

WINDOWS WORKER
16 [ ] fp16 sanity check pass; flag thắng cuộc ghi trong worker.env và RUNBOOK
17 [ ] Bind 127.0.0.1 + tailnet; KHÔNG có 0.0.0.0
18 [ ] Cleanup script chạy thật ít nhất 1 chu kỳ
19 [ ] Workflow deploy từ repo và verify SHA-256
20 [ ] gpu_probe.py xuất JSON đúng schema

TEST
21 [ ] ~83 test mới pass · 0 API call · 0 network call
22 [ ] Suite Python cũ vẫn pass (không regression)
23 [ ] Suite venho-os vẫn pass; tsc + build clean

BENCHMARK
24 [ ] 10 ảnh × 3 nhánh (Control/Baseline/Treatment) hoàn tất
25 [ ] Mọi retry và mọi ảnh fail đều được ghi, không giấu
26 [ ] Báo cáo đăng ký PRODUCTION_REGISTRY.md Tier-1

GOVERNANCE
27 [ ] 8 ADR đã viết
28 [ ] task_memory.md + task_status.md cập nhật
29 [ ] v1.0 đánh dấu SUPERSEDED, không xoá
30 [ ] Không tài sản nào được promote official bằng code path tự động
```

---
---

# PHẦN 20 — PROTOCOL GIAO VIỆC CHO AI CODING AGENT

## 20.1 Khuôn mẫu mỗi task

```text
TASK ID       GW-P{phase}-T{n}
PHASE         {tên}
LAYER         domain | application | infrastructure | interface | windows-host
FILES CREATE  {đường dẫn tuyệt đối từ gốc repo}
FILES MODIFY  {đường dẫn — nếu rỗng thì KHÔNG được sửa file nào}
CONTRACT REF  {mục PHẦN 5/6 phải đọc trước}
TESTS         {tên file test bắt buộc}
DoD           {checklist kiểm chứng được}
FORBIDDEN     {những gì task này KHÔNG được đụng}
```

## 20.2 Task đầu tiên — chạy ngay

```text
TASK ID       GW-P0-T0
PHASE         Phase 0 — Baseline Probe
LAYER         không có (chỉ điều tra)
FILES CREATE  docs/identity-restoration/BASELINE_PROBE_2026-08-18.md
FILES MODIFY  (rỗng — KHÔNG sửa bất kỳ file nào)
CONTRACT REF  PHẦN 0.5
TESTS         (không có — task điều tra)

NỘI DUNG
  Chạy grep ở PHẦN 0.5 trên cả hai repo.
  Lập bảng 3 cột: [Thành phần] [Tồn tại Y/N] [Đường dẫn thật + số dòng].
  Với mỗi Y: trích 3–5 dòng code chứng minh.
  Với mỗi N: ghi rõ "không tìm thấy", KHÔNG suy đoán nó có thể ở đâu.

DoD
  [ ] File tồn tại, đủ 11 dòng thành phần
  [ ] Mỗi Y có bằng chứng đường dẫn thật
  [ ] Kết luận rõ ràng: khả năng (A) hay khả năng (B)
  [ ] Nếu ≥5 dòng là N → viết CẢNH BÁO ở đầu file và DỪNG

FORBIDDEN
  Không viết code sản phẩm. Không tạo identity_restoration/.
  Không sửa file nào. Không cài gì. Không đụng máy Windows.
  Không "sửa" plan cho khớp thực tế — báo cáo thực tế, để Harry quyết định.
```

## 20.3 Task thứ hai

```text
TASK ID       GW-P1-T1
PHASE         Phase 1 — Windows GPU Worker
LAYER         windows-host
FILES CREATE  C:\VenHoGPU\scripts\gpu_probe.py
              C:\VenHoGPU\scripts\fp16_sanity_check.py
              docs/identity-restoration/WINDOWS_WORKER_RUNBOOK.md
CONTRACT REF  PHẦN 9.1, 9.2
TESTS         (host-level, không phải pytest)

DoD
  [ ] Windows nhận GTX 1660 Super, driver khỏe
  [ ] venv tạo xong, PyTorch báo CUDA available
  [ ] gpu_probe.py xuất JSON: gpuName, vramTotalMb, vramFreeMb, cudaVersion, torchVersion
  [ ] `python main.py --help` đã chạy, danh sách flag THẬT ghi trong RUNBOOK
  [ ] fp16_sanity_check.py: 1 ảnh 512×512 SD1.5, std pixel > 5, KHÔNG đen
  [ ] Flag thắng cuộc ghi trong worker.env VÀ trong RUNBOOK

FORBIDDEN
  Không cài custom node identity ở task này.
  Không bind 0.0.0.0. Không mở firewall. Không cài gì thuộc VenHo OS lên Windows.
  Không sang Phase tiếp theo cho tới khi DoD pass đủ.
```

---
---

# PHẦN 21 — NGUYÊN TẮC KHÓA

```text
VenHo OS         quyết định và hiển thị.
VenHo AI Studio  điều phối và thẩm định.
Windows ComfyUI  tính toán — và không gì khác.
Cloud provider   sinh base frame hoặc làm đường lui.
A2-FRONT         định nghĩa identity của Linh An.
QC — chứ không phải generator — quyết định một ảnh có đạt hay không.

Và một điều v1.0 chưa nói thành lời:

  KIẾN TRÚC là thứ khiến câu trên có thể KIỂM CHỨNG được bằng test,
  thay vì chỉ là một lời hứa trong tài liệu.

  Nếu đổi compute host mà phải sửa domain — kiến trúc đã thất bại,
  bất kể tài liệu viết gì.
```

**Architecture status: LOCKED — pending DR-GW-01 baseline verification.**

---

*Hết tài liệu. v2.0 · 2026-08-18 · Namespace GW · Thay thế v1.0.*
