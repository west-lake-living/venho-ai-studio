# VENHO GW PLAN — PATCH v2.0 → v2.1

**Ngày:** 2026-08-18
**Trạng thái:** ÁP DỤNG NGAY — bổ sung cho `VENHO_LINH_AN_GPU_IDENTITY_RESTORATION_CLEAN_ARCHITECTURE_PLAN_v2_0.md`
**Nguyên nhân:** GW-P0-T0 PASS · DR-GW-01 đóng với kết quả **khả năng (A)**
**Phạm vi patch:** PHẦN 0.5 · PHẦN 10.1 · PHẦN 13 (Phase 0–3) · PHẦN 18 · PHẦN 19

> Đọc file này SONG SONG với v2.0. Nơi nào patch mâu thuẫn v2.0, **patch thắng**.
> Phần nào patch không nhắc tới, v2.0 giữ nguyên hiệu lực.

---

# 1. DR-GW-01 — ĐÓNG

```text
KẾT QUẢ    Khả năng (A) — baseline Action Composite v2.1.1 TỒN TẠI THẬT trong repo.
           13/13 thành phần verified Y.
           venho-os KHÔNG có implementation ComfyUI/ActionComposite trực tiếp.

HỆ QUẢ 1   PHẦN 0.5 của v2.0 (cảnh báo baseline) → chuyển sang trạng thái HISTORICAL.
           Giữ lại làm bằng chứng quy trình. Không xoá.

HỆ QUẢ 2   GW-D3 và GW-D4 được XÁC NHẬN BẰNG THỰC TẾ, không còn là đề xuất.
           Ranh giới Python = image plane / TS = control plane đã đúng sẵn trong code.
           → Hai grep-test cưỡng chế (test_no_comfyui_string_leakage,
             no-direct-comfyui-access) đổi vai trò: từ "sửa lỗi" thành
             "khoá một trạng thái tốt đang có, chống trôi về sau".
           Đây là loại test rẻ nhất và có giá trị dài hạn cao nhất. Vẫn viết.

HỆ QUẢ 3   ⚠️ THAY ĐỔI LỚN NHẤT — xem PHẦN 2.
```

---

# 2. ⚠️ TÁI PHẠM VI: ĐÂY LÀ REFACTOR, KHÔNG PHẢI BUILD

## 2.1 Vấn đề với v2.0 sau khi biết baseline = A

v2.0 được viết phòng hờ cho cả hai khả năng, nên PHẦN 10.1 đánh dấu gần như toàn bộ
`identity_restoration/` là **★ file mới**. Với baseline (A), điều đó **sai và nguy hiểm**:

```text
NẾU LÀM THEO v2.0 NGUYÊN VĂN VỚI BASELINE (A):

  ActionCompositePipeline (đang chạy, có test)
  ComfyUIIdentityRestorer (đang chạy)
              +
  identity_restoration/ (mới, cùng chức năng)
              =
  HAI hệ identity restoration song song

Đây chính xác là lỗi GR-E1 "build trùng" của Growth Plan v3.0,
và là rủi ro mức Cao đã ghi ở Roadmap §22.
```

## 2.2 Nguyên tắc thay thế — Extract, đừng Recreate

```text
CÔNG VIỆC THẬT SỰ CỦA PLAN NÀY, SAU KHI BIẾT (A):

  KHÔNG PHẢI:  viết một identity restoration pipeline mới có kiến trúc sạch
  MÀ LÀ:       rút Port ra khỏi pipeline ĐANG CHẠY, rồi cắm thêm adapter thứ hai
               trỏ sang máy Windows

Trình tự đúng (strangler pattern):

  1. Golden-master test cho pipeline hiện tại      ← lưới an toàn, BẮT BUỘC trước
  2. Rút IdentityRestorerPort từ ComfyUIIdentityRestorer hiện có
  3. Bọc code hiện có thành `comfyui-local` adapter (hành vi KHÔNG ĐỔI)
  4. Thêm `mock` adapter → test chạy 0 network
  5. Thêm `comfyui-remote` adapter → máy Windows
  6. Chuyển default sang remote CHỈ SAU KHI benchmark Phase 4 PASS

Ở mỗi bước, toàn bộ test cũ phải xanh. Không có bước nào "tạm đỏ".
```

## 2.3 Bảng chuyển đổi ký hiệu PHẦN 10.1

Áp dụng lại ký hiệu cho file tree v2.0 §10.1:

| Nhóm file v2.0 | Ký hiệu v2.0 | Ký hiệu ĐÚNG với baseline (A) | Việc thật |
|---|---|---|---|
| `domain/entities.py` (A2Authority, CropTransform, MaskSet) | ★ mới | **◐ DI CHUYỂN** | Code đã tồn tại ở đâu đó trong Action Composite. Move + đổi tên, không viết lại |
| `domain/policies/pixel_preservation.py` | ★ mới | **◐ DI CHUYỂN** | Pixel preservation guard đã có (verified Y) |
| `domain/compositing.py` | ★ mới | **◐ DI CHUYỂN** | Composite logic đã có |
| `application/ports/*` | ★ mới | **★ THẬT SỰ MỚI** | Đây là giá trị cốt lõi plan này thêm vào |
| `application/use_cases/restore_face_crop.py` | ★ mới | **◐ TÁI CẤU TRÚC** | Logic đã nằm trong ProductionRunner — rút ra, không viết lại |
| `infrastructure/restorers/comfyui_remote_restorer.py` | ★ mới | **★ THẬT SỰ MỚI** | Adapter remote — công việc mới duy nhất ở tầng này |
| `infrastructure/restorers/comfyui_local_restorer.py` | *(chưa có trong v2.0)* | **★ THÊM MỚI VÀO PLAN** | Bọc `ComfyUIIdentityRestorer` hiện có |
| `infrastructure/restorers/mock_restorer.py` | ★ mới | **★ THẬT SỰ MỚI** | |
| `infrastructure/comfyui/node_registry.py` | ★ mới | **◐ TẬP TRUNG HOÁ** | Node title đã tồn tại rải rác — gom về một chỗ |
| `infrastructure/composition/*` | ★ mới | **★ THẬT SỰ MỚI** | |
| `ProductionRunner` | không nhắc | **○ SỬA** | Đổi để gọi qua Port thay vì gọi thẳng restorer |
| `WorkflowLedger` | "không build lại" | **○ MỞ RỘNG** | Thêm field lineage remote (workerHost, vramPeak) |

**Bổ sung vào file tree §10.1:**

```text
identity_restoration/infrastructure/restorers/
├── comfyui_local_restorer.py        ★ MỚI — bọc ComfyUIIdentityRestorer hiện có
│                                    #  Hành vi PHẢI giống hệt bản gốc.
│                                    #  Golden-master test chứng minh điều đó.
├── comfyui_remote_restorer.py       ★ MỚI — máy Windows
├── nano_banana_edit_restorer.py     ★ MỚI — baseline so sánh
└── mock_restorer.py                 ★ MỚI — mặc định trong test
```

**Cập nhật enum `restorerId`** (PHẦN 5.1 của v2.0):

```jsonc
"restorerId": { "enum": ["comfyui-local","comfyui-remote","nano-banana-edit","mock"] }
//                        ^^^^^^^^^^^^^^ THÊM. Đây là đường lui an toàn nhất:
//                        nếu remote fail, đổi một chuỗi config là quay về hành vi cũ.
```

---

# 3. ⚠️ RỦI RO MỚI: COUPLING ẨN TRONG ADAPTER HIỆN CÓ

Đây là rủi ro kỹ thuật lớn nhất còn lại sau khi DR-GW-01 đóng.

`ComfyUIIdentityRestorer` hiện tại được viết cho ComfyUI **chạy cùng máy**. Adapter viết
cho localhost gần như luôn mang theo giả định "cùng hệ thống file" — và những giả định đó
**không báo lỗi khi đổi sang máy khác, chúng chỉ trả kết quả sai hoặc rỗng**.

## 3.1 Danh sách nghi phạm — phải grep trước khi viết remote adapter

```text
GW-P1-T0 — COUPLING AUDIT (chạy trước GW-P2)

grep trong ComfyUIIdentityRestorer và toàn bộ đường gọi của nó:

[ ] Đường dẫn tuyệt đối truyền thẳng vào node LoadImage
    → local: "/Users/hanhpham/.../crop.png" chạy được
    → remote: máy Windows không có đường dẫn đó
    → BIỂU HIỆN: node báo file not found, HOẶC tệ hơn — nạp nhầm file cũ trùng tên

[ ] Đọc output trực tiếp từ thư mục ComfyUI output/ trên đĩa
    → thay bằng GET /view

[ ] Ghi input trực tiếp vào thư mục ComfyUI input/ trên đĩa
    → thay bằng POST /upload/image có namespace (v2.0 §8.2)

[ ] Hardcode 127.0.0.1 / localhost / :8188
    → chuyển vào config (v2.0 §11)

[ ] Giả định shared folder / symlink / mount chung

[ ] Giả định độ trễ thấp: timeout tính theo ms, retry gấp, poll interval quá ngắn
    → LAN + upload 3 ảnh sẽ đội thời gian đáng kể

[ ] Xử lý đường dẫn kiểu POSIX (os.path.join, "/" cứng)
    → Windows dùng "\". Chỗ này sai âm thầm, không ném exception.

[ ] Giả định file xuất hiện NGAY sau khi workflow báo completed
    → qua mạng có độ trễ; phải poll /history rồi mới /view

XUẤT RA  docs/identity-restoration/COUPLING_AUDIT_2026-08-18.md
         Mỗi nghi phạm: [Tìm thấy Y/N] [File:dòng] [Cách gỡ]
```

## 3.2 Vì sao audit này quan trọng hơn nó có vẻ

```text
Nếu bỏ qua bước này, kịch bản gần như chắc chắn xảy ra:

  Phase 3 chạy → ComfyUI báo completed → tải về được một ảnh
  → nhưng đó là ảnh từ file cũ trùng tên, hoặc ảnh chưa qua restoration
  → Face QC ra một con số THẬT nhưng VÔ NGHĨA
  → benchmark Phase 4 đo nhầm thứ
  → kết luận sai về việc GPU worker có hiệu quả hay không

Lỗi này không ném exception ở bất kỳ đâu. Nó chỉ trả về số.
Đó là lý do nó nguy hiểm hơn một lỗi làm sập hệ thống.

BIỆN PHÁP CƯỠNG CHẾ (thêm vào DoD):
  restored crop trả về PHẢI khác byte-exact so với crop gửi đi.
  Giống hệt = ERR_GW_EMPTY_OUTPUT, không phải thành công.
```

Thêm test bắt buộc vào v2.0 §12.3:

```python
# 10. ⭐ Chống "restoration giả" — hệ quả của coupling ẩn
def test_restored_crop_differs_from_input_crop():
    """Nếu restored crop giống hệt input crop về byte, nghĩa là workflow
    không chạy, hoặc ta đang đọc nhầm file. FAIL, không phải PASS.
    Đây là lưới an toàn duy nhất bắt được lỗi 'thành công giả' qua mạng."""
```

---

# 4. PHASE 0–3 TÁI PHẠM VI

## GW-P0 — Baseline Freeze (còn lại)

```text
[x] TASK 0 — baseline probe                                    ĐÃ XONG, kết quả (A)
[x] TASK 1 — COUPLING AUDIT (PHẦN 3.1 patch này)               ★ evidence reconstructed/read-only
[x] TASK 2 — GOLDEN-MASTER TEST cho pipeline hiện tại          ★ PASS/CLOSED
[x] Ghi commit hash cả 2 repo
[x] Ghi kết quả test hiện tại (Python + OS)
[x] Ghi SHA-256 của A2-FRONT vào workflow_pins.yaml
[x] Ghi baseline Nano Banana Face QC ≈ 88.x
[x] Đánh dấu v1.0 SUPERSEDED
[x] Di chuyển face_restore_v1_api.json → workflows/_archive/  (GIỮ, đã verified Y)
[x] Viết 8 ADR
```

### GW-P0 — Git baseline snapshot (2026-08-19)

| Repo | Current HEAD commit SHA |
|---|---|
| `venho-ai-studio` | `f3cf924920812e6591f9c11b5e009fd36b610416` |
| `venho-os` | `329c8d2ce6cc24af137c9730a7bd8a804b47e9e3` |

Recorded for GW-P0 baseline freeze. Test baseline is a separate remaining GW-P0 item.

### GW-P0 — Current test baseline (2026-08-19)

| Repo | Commit | Native command | Passed | Failed | Skipped | Errors |
|---|---|---|---:|---:|---:|---:|
| `venho-ai-studio` | `f3cf924920812e6591f9c11b5e009fd36b610416` | `PYTHONPATH=. /usr/bin/python3 -m pytest -q` | 951 | 70 | 0 | 0 |
| `venho-os` | `329c8d2ce6cc24af137c9730a7bd8a804b47e9e3` | `npm test -- --run` | 400 | 0 | 0 | 0 |

Python failure categories recorded without remediation: missing
`data/projects/venho_hotel/knowledge/VENHO_HOTEL_LAKE_VIEW_ROOM_DNA.json` affecting
prompt/knowledge/optimizer/pipeline/video tests; subject-resolver/schema/overlay expectations
using `shared.room` instead of `venho_hotel.room`; one Action Composite config expectation;
and missing raw asset fixture(s). OS suite passed 71 files / 400 tests.

### GW-P0 — A2-FRONT SHA-256 pinned (2026-08-19)

`config/projects/venho_hotel/identity_restoration/workflow_pins.yaml` (mới) ghi sha256
`1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d` cho
`venho-social-content-agent/assets/face-plates/A2_Front_plate.png` — xác nhận bằng `shasum -a 256`
và đối chiếu khớp `identity_reference_sha256` trong `tests/identity_restoration/golden/index.json`
(3/3 case). File này, không phải `assets/linh_an/A2_Front.png` nêu trong `IDR_A2_PATH` ở v2.0, là
identity reference thật đã dùng để đóng băng golden-master GW-P0-T2 (bản gốc chưa crop vuông có
cùng sha256 với `assets/raw/linh_an/A2_Front.png` của repo này, nhưng khác file). Cũng pin kèm
`face_restore_v1_api.json` (sha256 `b232b18d498f9a0064707a83aeebb36306fda147ac50d757a27721267c9f3e25`,
status SUPERSEDED, chưa move vào `_archive/`) và placeholder cho workflow SD1.5 Phase GW-P3.
Chỉ tạo file cấu hình + đọc tài liệu, không sửa production code.

### GW-P0 — Nano Banana masked-edit Face QC baseline (2026-08-19)

Đã đóng băng bằng evidence hiện có, không tạo ảnh mới và không rerun paid request.

- Run/case: `run-202608132052/variant-001`
- Provider/mode: `nano-banana-2` / `gemini-3.1-flash-image` / `masked-edit`
- Face QC: `88.1`, verdict `revise` (comparison baseline/fallback reference only; không phải
  production winner và không tạo acceptance threshold mới).
- A2 authority: `/Users/hanhpham/Developer/Claude-Workspace/projects/venho-social-content-agent/assets/face-plates/A2_Front_plate.png`
- A2 SHA-256: `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`
- Input artifacts:
  - `photos-ai/2026/13-08-action-composite-v21-nano-crop/run-202608132052/variant-001/manifest.json`
  - `assets/action-composite-live/action_01_jogging.png`
  - `assets/action-composite-live/face-mask.png`
- Output artifact: `photos-ai/2026/13-08-action-composite-v21-nano-crop/run-202608132052/variant-001/image.png`
  (SHA-256 `1d64fd2b62812d81e8fb26f728cf23b2f284a43eb85f822c727d8bd50b72266c`)
- Face evidence report:
  `data/projects/venho_hotel/validation/reports/face_linh_an_1d64fd2b6281_20260813-204931.json`
- Run timestamp: `2026-08-13T13:47:18.610Z` → `2026-08-13T13:49:43.327Z`
- Existing reproducibility fields: prompt hash
  `6d46082afd171b7bf333a6c3ad81a39629ed6b73de51cc3e58aff60dddbb0baa`,
  generation protocol `linh_an_generation_protocol_v1`, crop `{left:318, top:69, size:454,
  providerSize:1024}`, one generation and one validation attempt. No seed was recorded.
- Evidence source: immutable manifest and validator report from the existing Venho OS
  masked-edit run; cross-reference `venho-os/task_status.md` and `task_memory.md`.
- API cost/new generation for this baseline task: none.

### GW-P0 — v1.0 superseded marker (2026-08-19)

- Existing v1.0 workflow marked `SUPERSEDED` in
  `config/comfyui/face_restore_v1_api.json`.
- Superseding authority: this v2.1 patch and the current v2.x architecture; v2.1 overrides
  v2.0 wherever they conflict.
- The workflow content was preserved and is now archived for audit/lineage; it is not active.
- The v1.0 worker-roadmap markdown referenced by the v2.0 plan
  (`VENHO_LINH_AN_WINDOWS_COMFYUI_GPU_WORKER_ROADMAP_v1_0.md`) is not present in the current
  workspace, so no absent historical file was fabricated or modified.

### GW-P0 — Legacy workflow archived (2026-08-19)

- Original: `config/comfyui/face_restore_v1_api.json`
- Archive: `workflows/_archive/face_restore_v1_api.json`
- SHA-256 preserved: `f7d04802135eb06db94e6b096b0dc269a644c3bebe90ec61f3855567dde32361`
- `workflow_pins.yaml` and all Golden-Master lineage records now point to the archive path.
- Reason: v1.0 workflow is superseded by the current v2.x authority; it remains auditable and
  is not activated as a current workflow.

### GW-P0 — ADR set and phase audit (2026-08-19)

- ADR-GW-001…ADR-GW-008 đã được tạo theo mapping GW-D1…GW-D12 trong v2.0.
- Golden Master offline regression vẫn PASS (`2 passed`), archive và A2 pin còn traceable.
- Coupling Audit đã được reconstructed/read-only vào
  `docs/identity-restoration/COUPLING_AUDIT_2026-08-18.md`; không có production remediation.

### GW-P0 — Phase closure (2026-08-19)

- T0, T1, T2, commit/test baselines, A2 pin, Nano Banana baseline, v1 supersession, workflow
  archive, and exactly 8 ADRs are evidence-closed.
- Golden Master offline regression: `python3 -m pytest -q tests/test_gw_p0_t2_golden.py` → `2 passed`.
- A2 SHA-256 reverified as
  `1e0c9720087d4bab4b1ab5d65d31827aba99cf4c696c1a72570ed4114dca2c5d`.
- No second `ActionCompositePipeline` definition, no direct ComfyUI references in `venho-os`
  TypeScript sources, and no production architecture change were observed.
- **GW-P0: CLOSED/PASS.**

### TASK 2 — Golden-master test (lưới an toàn cho refactor)

```text
Vì sao BẮT BUỘC: từ đây trở đi ta sẽ di chuyển code đang chạy được.
Refactor không có golden-master = refactor mù. Nếu hành vi đổi, ta sẽ chỉ
phát hiện ra ở Phase 4 khi benchmark cho số lạ — lúc đó không còn biết
số lạ đến từ máy Windows hay từ chính cuộc refactor của mình.

NỘI DUNG
  Chạy ActionCompositePipeline hiện tại trên 3 crop cố định, seed cố định,
  restorer local. Đóng băng output:
    - sha256 của restored crop
    - sha256 của composite
    - pixelLock report (mutatedPixelCount)
    - cropTransform đã serialize
    - Face QC score (samples=3, ghi cả 3 mẫu)

  Lưu vào tests/identity_restoration/golden/ dạng JSON + PNG.

  ⚠️ Face QC có non-determinism đã biết (sự cố 2026-07-17). Vì vậy:
     - so sánh sha256 crop/composite: BẰNG TUYỆT ĐỐI
     - so sánh Face QC: cho phép dung sai ±2.0, và ghi rõ dung sai này là
       giới hạn của validator, KHÔNG phải giới hạn của pipeline.

DoD
  [ ] 3 golden case chạy lại cho kết quả trong dung sai
  [ ] Test này chạy được offline, 0 network (dùng restorer local + mock vision nếu cần)
  [ ] Chạy lại được sau MỖI bước refactor ở Phase 2
```

## GW-P1 — Windows GPU Worker

Không đổi so với v2.0. Vẫn độc lập với repo, vẫn chạy song song được với Phase 2.

**Bổ sung một mục vào DoD:**

```text
[ ] Ghi lại đường dẫn model THẬT trên Windows theo cú pháp Windows,
    xác nhận ComfyUI resolve được. Chuẩn bị sẵn cho nghi phạm "POSIX path" ở §3.1.
```

## GW-P2 — Extract Port (thay thế hoàn toàn Phase 2 của v2.0)

```text
TÊN CŨ  "Port & Mock (không cần máy Windows)"
TÊN MỚI "Extract Port từ pipeline hiện có"

Vẫn KHÔNG cần máy Windows. Vẫn chạy song song được với Phase 1.

TASKS — theo đúng thứ tự, golden-master phải xanh sau MỖI bước

[x] T1  Viết 5 JSON Schema + fixtures — `contracts/identity_restoration/*.schema.json`
        (chuyển khỏi `contracts/` phẳng vì `test_growth_phase1_contracts.py` enumerate
        đúng 17 schema Growth Phase 1 bằng whitelist; 5 schema GW nằm riêng thư mục
        `contracts/identity_restoration/` không bị test đó quét).

[x] T2  application/ports/ — 9 Port thuần interface, không import infrastructure
        (test_layering.py::test_application_does_not_import_infrastructure cưỡng chế).

[x] T3  ComfyUILocalRestorer bọc ComfyUIIdentityRestorer hiện có, implements
        IdentityRestorerPort. KHÔNG sửa `image_studio_runtime/action_composite/`
        — 0 dòng trong thư mục đó bị đổi. Gọi inner restorer ở chế độ "không crop_box"
        (base_image = crop, không composite bên trong adapter) để giữ đúng hành vi cũ;
        compositing chuyển sang domain layer mới.
        → golden-master (`tests/test_gw_p0_t2_golden.py`) vẫn PASS nguyên trạng.

[~] T4  KHÔNG sửa `ProductionRunner` gọi qua RestorerRegistry — quyết định lệch có
        chủ đích: `ProductionRunner`/`ActionCompositePipeline` vẫn là con đường
        production thật, không đụng để giữ rủi ro = 0. `RestoreFaceCropUseCase` mới
        là con đường SONG SONG, độc lập, dùng RestorerRegistry đúng như thiết kế —
        nhưng nó không (chưa) thay thế `ProductionRunner` là caller thật. Việc hợp nhất
        hai đường này là quyết định kiến trúc cần Harry chốt trước khi làm, không tự
        quyết trong phiên này.

[x] T5  MockIdentityRestorer (infrastructure/restorers/mock_restorer.py) + Composition
        Root (infrastructure/composition/identity_restoration_module.py) + env.py.
        `venho-restore run --restorer mock` chạy thật, xác nhận bằng smoke test thủ công.

[~] T6  Domain logic — KHÔNG di chuyển vật lý `CropTransform`/pixel preservation/
        compositing ra khỏi `action_composite/` (quyết định lệch có chủ đích, xem dưới).
        `identity_restoration/domain/policies/pixel_preservation.py` IMPORT trực tiếp
        `action_composite.regression_guard.protected_region` (hàm thuần, không I/O) thay
        vì copy lại — tái dùng thật, không viết lại. `compositing.py` và `entities.py` là
        code mới, pixel math giống hệt `ComfyUIIdentityRestorer`/`ActionCompositePipeline`
        hiện có (paste-qua-mask), không phải logic mới. Không có shim vì không có gì bị
        di chuyển khỏi vị trí cũ — `action_composite/` giữ nguyên 100%, đây là lựa chọn AN
        TOÀN HƠN so với "move + shim" mà patch đề xuất, đánh đổi lấy việc domain layer
        chưa thực sự "sở hữu" logic đó.

[x] T7  test_layering.py (3 test) + test_no_comfyui_string_leakage.py (1 test) —
        tất cả pass, 0 network call.

[x] T8  CLI `venho-restore run|health` — entrypoint `pyproject.toml`. `run --restorer mock`
        đã smoke-test thủ công end-to-end. `--restorer comfyui-local` cần ComfyUI local
        thật đang chạy để verify TRÙNG golden-master byte-exact — KHÔNG làm được trong
        sandbox này (không có ComfyUI server), còn lại như một bước xác minh thủ công
        Harry cần tự chạy.

DoD
  [x] Toàn bộ suite Python cũ vẫn pass — 0 regression (`PYTHONPATH=. /usr/bin/python3
      -m pytest -q`: baseline 951/70 → nay 1005 pass / 69 fail, cùng 69 lỗi baseline cũ,
      KHÔNG có lỗi mới; `tests/test_action_composite*.py` + `test_gw_p0_t2_golden.py`
      50/50 pass nguyên trạng).
  [x] `venho-restore run --restorer mock` chạy end-to-end, output hợp `restoration_result.
      schema.json` — verify thủ công bằng smoke test, JSON output đúng shape.
  [ ] `venho-restore run --restorer comfyui-local` cho kết quả TRÙNG golden-master —
      CẦN ComfyUI local server thật đang chạy để verify, chưa làm được trong phiên này.
  [x] test_layering pass · 53/53 test mới trong `tests/identity_restoration/` pass ·
      0 network call trong pytest (xác nhận: mọi test HTTP dùng recorded fixture hoặc
      monkeypatch `urlopen`).

ROLLBACK
  Xoá `identity_restoration/` + `contracts/identity_restoration/` + revert
  `pyproject.toml` entrypoint. Không file nào trong `image_studio_runtime/action_composite/`
  bị sửa nên rollback không ảnh hưởng production path hiện tại — đúng tinh thần "risk = 0"
  của GW-P2, giữ nguyên ngay cả khi không tách commit T3–T6 riêng như patch gốc đề nghị.
```

**GW-P2: giá trị đã giao (2026-08-20)** — domain/application layer đầy đủ (9 Port, 1 use
case trung tâm theo đúng thuật toán 16 bước PHẦN 7.3 rút gọn còn phù hợp phạm vi crop-based
contract, registry, DTO), 3 adapter (`mock`, `comfyui-local` bọc code cũ, `comfyui-remote`
cho GW-P3), composition root + CLI hoạt động, 5 schema + 9 fixture, 53 test mới 100% pass
0 network. **Quyết định lệch có chủ đích khỏi patch gốc**: KHÔNG sửa `ProductionRunner`
(T4) và KHÔNG di chuyển vật lý code cũ (T6) — ưu tiên rủi ro=0 cho production path hơn là
theo đúng chữ "◐ DI CHUYỂN" của §2.3; hệ quả là `identity_restoration/` hiện là một con
đường SONG SONG đã kiểm chứng đầy đủ nhưng CHƯA phải con đường mà `ActionCompositePipeline`
thật đang gọi — hợp nhất hai đường này là việc cần Harry chốt, không tự quyết.

## GW-P3 — Remote Adapter

```text
Bỏ phần "viết adapter từ đầu". Công việc thu hẹp lại còn:

[x] T1  Đọc COUPLING_AUDIT (P0-T1). Adapter mới né sẵn mọi nghi phạm bằng thiết kế
        (namespace upload theo run/attempt, đọc `name` từ response, base_url qua config,
        bind theo `_meta.title`) — không có nghi phạm nào "Y" trong audit hiện có cần gỡ
        khỏi code MỚI vì code mới chưa tồn tại lúc audit được viết.
[ ] T2  Bật Tailscale, probe HEALTHY từ Mac — CẦN máy Windows thật. Không làm được trong
        sandbox này. `scripts/probe_gpu_worker.py` đã sẵn sàng chạy ngay khi có worker.
[x] T3  node_registry.py — NODE_TITLES + WORKFLOWS, cưỡng chế bằng test_no_comfyui_string_leakage.py.
[x] T4  http_client.py — upload namespaced (đọc `name` từ response, GW-E9) / prompt /
        history (backoff 2s ×1.5 trần 10s) / view / interrupt. 0 network trong test.
[x] T5  graph_binder.py — bind theo `_meta.title`, sống sót qua node-id renumbering.
[x] T6  error_mapper.py — phủ bảng v2.0 §8.5 (OOM→VRAM_EXHAUSTED retryable, 400→
        WORKFLOW_INVALID không retry, empty outputs, timeout, connection refused).
[x] T7  cached_worker_health.py + circuit breaker — viết ở GW-P2, tái dùng nguyên vẹn.
[x] T8  ComfyUIRemoteRestorer implements cùng IdentityRestorerPort với ComfyUILocalRestorer
        (`infrastructure/restorers/comfyui_remote_restorer.py`).
[~] T9  7 fixture ở `contracts/identity_restoration/fixtures/comfyui/` — soạn TAY theo
        tài liệu ComfyUI API, KHÔNG PHẢI ghi lại từ lần chạy thật (cần T2/T12 trước).
        Khi có lần chạy thật đầu tiên: THAY chúng bằng bản ghi thật.
[ ] T10 Tác giả workflow SD1.5 + IPAdapter FaceID trong repo, pin SHA-256 — CẦN ComfyUI
        cài trên Windows để thiết kế/test graph trước khi export.
[x] T11 deploy_workflows_to_worker.py — viết xong, verify SHA-256 trước/sau copy; chưa
        chạy thật (không có đích Windows).
[ ] T12 MỘT crop Linh An thật đi hết chuỗi — CẦN T2 + T10 trước.

EXIT GATE — chặt hơn v2.0
  [ ] Một ảnh thật hoàn tất: base → crop/mask → Windows → restored → composite
      → pixel lock → Face QC → lineage
  [ ] ⭐ restored crop KHÁC byte-exact so với input crop (chống thành công giả, §3.2)
  [ ] ⭐ Chạy CÙNG một crop qua comfyui-local và comfyui-remote.
      cropTransform, mask version, composite geometry PHẢI GIỐNG HỆT.
      Chỉ nội dung pixel vùng editable được phép khác.
      → Đây là bằng chứng sống của ADR-GW-001, và giờ nó kiểm chứng được
        vì ta có HAI adapter thật để so, không phải mock so với thật.

  **CHƯA ĐẠT — GW-P3 CHƯA CLOSED (2026-08-20).** T1, T3–T8, T11 xong và có test offline
  (0 network). T2, T10, T12 và phần "ghi fixture từ lần chạy thật" của T9 cần một máy
  Windows + ComfyUI + Tailscale thật — hạ tầng vật lý này nằm ngoài khả năng của phiên làm
  việc hiện tại (không có máy Windows, không có mạng ra ngoài sandbox). Toàn bộ phần mềm
  phía Mac cho GW-P3 đã sẵn sàng; việc còn lại là hạ tầng, không phải thiết kế/code.

ROLLBACK
  IDR_DEFAULT_RESTORER=comfyui-local → quay về hành vi trước plan này, tức thì.
```

---

# 5. CẬP NHẬT DEFINITION OF DONE

Sửa và bổ sung vào v2.0 §19:

```text
SỬA
 6 [ ] Không tạo M-module mới; không tạo job store thứ hai
       → BỔ SUNG: và KHÔNG tạo pipeline identity restoration thứ hai.
         Chỉ tồn tại MỘT ActionCompositePipeline. Adapter thì nhiều, pipeline thì một.

THÊM MỚI
31 [ ] COUPLING_AUDIT hoàn tất, mọi nghi phạm Y đã gỡ và ghi lại cách gỡ
32 [ ] Golden-master test tồn tại và xanh sau mỗi bước refactor P2-T3→T6
33 [ ] comfyui-local và comfyui-remote implement CÙNG Port, verify bằng test song song
34 [ ] restored crop khác byte-exact input crop (chống thành công giả)
35 [ ] Đổi IDR_DEFAULT_RESTORER về comfyui-local khôi phục hành vi cũ trong 1 bước
36 [ ] Import shim ở vị trí domain cũ còn nguyên; xoá shim là Phase 6, không sớm hơn
```

---

# 6. CẬP NHẬT DECISIONS

| ID | Trạng thái mới |
|---|---|
| **DR-GW-01** | ✅ **ĐÓNG** — khả năng (A) |
| **DR-GW-02** | ✅ **ĐÓNG** — ranh giới repo đã đúng sẵn trong code, không cần quyết định nữa |
| DR-GW-03 | Còn treo — Tailscale thay LAN thô. Khuyến nghị: chấp thuận |
| DR-GW-04 | Còn treo — xử lý thế nào nếu median 86–89 |
| DR-GW-05 | Còn treo — ngân sách benchmark. **Nay tăng lên**: 4 nhánh (local/remote/nano/control) × 10 ảnh × samples 3 ≈ 120 lần gọi vision API |
| DR-GW-06 | Còn treo — Windows có chạy 24/7 không |
| DR-GW-07 | Còn treo — giữ nano-banana-edit vĩnh viễn |
| **DR-GW-08** | ★ **MỚI** — Có giữ `comfyui-local` vĩnh viễn làm fallback khi máy Windows offline không? Khuyến nghị: **có**. Nó đã chạy được, chi phí giữ ≈ 0, và nó là đường lui một-dòng-config |

---

# 7. VIỆC TIẾP THEO — HAI TASK CHẠY SONG SONG

## GW-P0-T1 — Coupling Audit (ưu tiên cao nhất)

```text
LAYER         điều tra, không có code sản phẩm
FILES CREATE  docs/identity-restoration/COUPLING_AUDIT_2026-08-18.md
FILES MODIFY  (rỗng)
CONTRACT REF  PATCH §3.1
TESTS         (không có)

NỘI DUNG
  Đọc toàn bộ ComfyUIIdentityRestorer và đường gọi của nó.
  Với mỗi nghi phạm trong §3.1: [Tìm thấy Y/N] [File:dòng] [Trích code] [Cách gỡ đề xuất].
  Nghi phạm nào N thì ghi N — không suy đoán.

DoD
  [ ] Đủ 8 nghi phạm được trả lời
  [ ] Mỗi Y có trích dẫn code thật
  [ ] Kết luận: ước lượng khối lượng gỡ coupling (giờ), có căn cứ

FORBIDDEN
  Không sửa code ở task này. Chỉ đọc và ghi.
  Không "tiện tay refactor". Golden-master chưa có — sửa lúc này là sửa mù.
```

## GW-P1-T1 — Windows GPU Worker

Không đổi so với v2.0 §20.3. Chạy song song được vì không đụng repo.

```text
⚠️ NHẮC LẠI RỦI RO SỐ MỘT CỦA TASK NÀY: hazard fp16 dòng GTX 16xx.
   Nếu ảnh sinh ra đen hoặc NaN — đổi flag TRƯỚC, đừng đổi model, đừng đổi workflow.
```

---

**Hết patch. v2.1 · 2026-08-18 · Áp dụng chồng lên v2.0.**
