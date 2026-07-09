VENHO AI STUDIO
MODULE 04 — AUTOMATION STUDIO — Development Plan v1.1 (QC Consolidated)
Workspace mẹ: THE WEST LAKE LIVING Repo: venho-ai-studio Module: automation_studio/ Phụ thuộc: Module 01 (DNA) · Module 02 (Prompt) · Module 03 (Validator) · shared/ AI Engine: OpenAI + Claude (gián tiếp, qua module con) Mục tiêu: Điều phối Module 01–03 thành workflow chạy lặp lại — một lệnh, có log/state/report, an toàn, config-first — KHÔNG chứa business logic của module khác.


0. Kết quả QC v1.0 → v1.1
LỖI KHÁI NIỆM (nghiêm trọng)

1. Chuỗi end-to-end bị đứt ở khâu tạo ảnh → SỬA: điểm dừng thủ công (manual_gate);

   pipeline chia HAI NỬA tự động, không liền mạch một lệnh (§6, §16 Phase 9)

2. Chữ ký interface sai module   → SỬA: brief bắt buộc, đa subject, target_language;

   bỏ render_compact rời; validate theo type (§14)

LỖI RANH GIỚI & AN TOÀN

3. Thiếu adapter/registry        → SỬA: thêm adapters/ + action_registry (§5, §14, Phase 1)

4. on_error continue nguy hiểm   → SỬA: dependency-aware (needs + skip_dependents) (§10)

5. Archive chồng chéo            → SỬA: archive thuộc MODULE; automation chỉ kiểm (§3.5, §15)

LỖ HỔNG VẬN HÀNH

6. Thiếu lock/resume/mock, retry chồng → SỬA: run lock, resume-from-step,

   mock mode, retry phân tầng (§10, §12, §16)


1. Vai trò của Module 04
Module 01 tạo DNA · Module 02 tạo Prompt · Module 03 kiểm output. Module 04 nối các bước đó thành quy trình chạy được bằng một lệnh — nhưng chỉ điều phối, không làm thay.

Input / Command / (sau này) Schedule → Automation → Run Pipeline → Save + Report

Automation KHÔNG phân tích ảnh, KHÔNG tạo prompt, KHÔNG validate, KHÔNG tạo/sửa Knowledge. Nó gọi interface công khai của module con và quản lý thứ tự, trạng thái, lỗi, báo cáo.


2. Mục tiêu chính
Biến quy trình thủ công (copy ảnh → chạy từng module tay → lưu → báo cáo) thành workflow: một lệnh, có log, có retry có kiểm soát, có report, có config, có thể resume.


3. Nguyên tắc thiết kế
3.1 Không chứa business logic. Chỉ gọi module con qua adapter (§14). Không import sâu logic nội bộ.

3.2 Config-first. Mọi workflow khai báo bằng YAML; không hard-code chuỗi bước trong code.

3.3 Local-first. Giai đoạn đầu chạy local; không cloud, không DB, không dashboard.

3.4 Manual first, schedule later. Chạy ổn bằng CLI trước; scheduler sau.

3.5 Safe execution — archive thuộc MODULE. Automation KHÔNG tự archive/overwrite file của module con. Module 01/02/03 đã có chính sách archive/version riêng (DNA _archive, prompt _archive, validation manifest). Automation chỉ: (a) truyền cờ đúng để module tự archive, (b) kiểm tra output tồn tại sau run, (c) không bao giờ ghi đè file production trực tiếp.

3.6 Determinism & mock. Test tích hợp chạy module ở mock mode (kế thừa mock của M01–03) để không tốn token; workflow điều phối phải tái lập.


4. Phạm vi MVP v0.1
CÓ:    chạy workflow bằng CLI · đọc YAML · gọi tuần tự module qua adapter ·

       log từng bước · run report · trạng thái success/failed/skipped ·

       dry-run · run lock · Mode A và Mode B của Knowledge Studio

CHƯA:  dashboard · cloud scheduler · Google Drive · Gmail · Make/n8n ·

       multi-user · database · auto-publish · nối liền khâu tạo ảnh (thủ công)


5. Cấu trúc repo
venho-ai-studio/

├── automation_studio/

│   ├── __init__.py

│   ├── cli.py

│   ├── workflow_loader.py

│   ├── workflow_runner.py

│   ├── step_executor.py

│   ├── adapters/                 # MỚI v1.1 — lớp cô lập interface module con

│   │   ├── knowledge_adapter.py

│   │   ├── prompt_adapter.py

│   │   └── validator_adapter.py

│   ├── action_registry.py        # MỚI v1.1 — map module.action → adapter + param schema

│   ├── run_lock.py               # MỚI v1.1 — chặn chạy song song cùng workflow

│   ├── run_state.py

│   ├── report_builder.py

│   ├── scheduler.py              # chuẩn bị, chưa bật ở MVP

│   └── errors.py                 # workflow-level; dùng lại backoff của shared/

│

├── config/

│   └── workflows/

│       ├── mode_a_image_to_md.yaml          # generic, project truyền lúc chạy

│       ├── venho_room_dna_update.yaml

│       ├── venho_prompt_generation.yaml

│       └── venho_half2_validation.yaml       # nửa sau: validate ảnh đã tạo tay

│

├── data/automation_runs/{logs, reports, state, locks}/

│

└── shared/{logging.py, io/}


6. Core Workflow Types — và ĐIỂM DỪNG THỦ CÔNG
Nhận thức quan trọng (sửa lỗi lớn): VENHO chưa có module tạo ảnh. Ảnh sinh ở Flow/GPT Image (ngoài). Vì vậy pipeline sản xuất ảnh chia làm HAI NỬA tự động, ngăn bởi một điểm dừng thủ công:

NỬA 1 (tự động):  media → DNA (M01) → Prompt (M02)

                  → xuất prompt + "generation instructions" cho người

──────── MANUAL GATE ─────────

   Người dùng sang Flow/GPT Image tạo ảnh, tải về,

   đặt vào data/projects/<project>/production/images/

──────────────────────────────

NỬA 2 (tự động):  generated image → Validation (M03) → report

MVP hiện thực hai nửa bằng hai workflow riêng, hoặc một workflow có step type: manual_gate sẽ dừng và in hướng dẫn rồi thoát (chạy lại nửa sau sau khi có ảnh).

Workflow A — General Image to Markdown (Mode A, không gate): input folder → M01 Mode A → observation .md+.json → report. Workflow B — Project DNA Update (Mode B, không gate): media subject → M01 Mode B (compact sinh trong Mode B theo settings) → manifest update → report. Workflow C — Prompt Generation (nửa 1, kết thúc bằng manual_gate): DNA → M02 prompt → generation instructions. Workflow D — Validation (nửa 2): ảnh đã tạo tay → M03 validate → report.


7. Workflow Config Format
workflow_id: venho_room_dna_update      # run target = workflow_id (KHÔNG phải tên file)

name: Ven Ho Lake View Room DNA Update

version: 1.0

project: venho_hotel                    # có thể override bằng --project lúc chạy

trigger: { type: manual }

steps:

  - id: knowledge_mode_b

    module: knowledge_studio

    action: vision_mode_b               # phải tồn tại trong action_registry

    params:

      project: "${project}"

      subject: lake_view_room

      input: data/projects/${project}/media/lake_view_room

    on_error: stop

  - id: update_manifest

    module: knowledge_studio

    action: update_manifest

    needs: [knowledge_mode_b]           # MỚI: khai báo phụ thuộc

    on_error: skip_dependents

output: { report: true, log: true }     # BỎ archive: archive thuộc module (§3.5)

Ghi chú: compact DNA KHÔNG còn là step riêng — Mode B tự sinh compact theo settings.output.compact của Module 01.


8. Run State
{

  "run_id": "run_2026_07_08_153000_venho_room_dna_update",

  "workflow_id": "venho_room_dna_update",

  "project": "venho_hotel",

  "status": "success",

  "resumable_from": null,

  "started_at": "ISO", "finished_at": "ISO",

  "steps": [

    { "id": "knowledge_mode_b", "status": "success",

      "started_at": "ISO", "finished_at": "ISO",

      "outputs": ["VENHO_LAKE_VIEW_ROOM_DNA.md"], "attempts": 1 }

  ]

}

status ∈ {success, failed, skipped, partial} · nếu partial/failed, resumable_from = id bước cần chạy lại.


9. Run Report
# AUTOMATION RUN REPORT

## META

## WORKFLOW

## INPUTS

## STEPS EXECUTED (status từng bước, gồm skipped + lý do)

## MANUAL GATE (nếu có: hướng dẫn người dùng làm gì tiếp)

## OUTPUTS (đối chiếu output kỳ vọng vs thực tế)

## WARNINGS

## FAILED ITEMS

## NEXT ACTIONS (vd: "tạo ảnh ở Flow rồi chạy venho auto run venho_half2_validation")


10. Error Handling (đã nâng cấp)
Loại lỗi: YAML sai, thiếu input, không có ảnh, step failed, output path lỗi, permission, API lỗi từ module con, validation failed, action không có trong registry, workflow đang bị khóa.

Chính sách lỗi phân tầng:

- Module con TỰ retry lỗi API tạm thời (đã có ở M01/M03). Automation KHÔNG retry chồng.

- on_error cấp step:

    stop            → dừng workflow

    continue        → chỉ dùng cho bước ĐỘC LẬP (không ai `needs` nó)

    skip_dependents → bước fail: các bước có `needs` nó → status=skipped, KHÔNG chạy với input thiếu

- retry (cấp workflow) chỉ thêm sau MVP, có max_attempts, chỉ cho lỗi tạm thời.

Điểm mấu chốt: một bước fail không bao giờ được để bước phụ thuộc chạy với input rỗng (vd DNA fail → Prompt tự skip, không sinh prompt rác).


11. Scheduler (chuẩn bị, chưa bật)
MVP chỉ trigger: { type: manual }. Kiến trúc chừa chỗ cho type: schedule (cron) và type: folder_watch. Scheduler được parse nhưng chưa tự chạy ở MVP.


12. Run Lock & Resume (mới v1.1)
Run lock: trước khi chạy, tạo data/automation_runs/locks/<workflow_id>.lock. Nếu đã tồn tại → từ chối, báo "workflow đang chạy". Giải phóng lock khi kết thúc (kể cả khi lỗi). Chặn hai run cùng workflow làm hỏng state/output.

Resume: venho auto resume <run_id> đọc state, chạy lại từ resumable_from. Việc đã xong được bỏ qua nhờ cache của module con (M01 cache observation; M02/M03 manifest) → resume rẻ, không làm lại phần đã hoàn thành.


13. Dry-run
--dry-run kiểm tra KHÔNG gọi AI, KHÔNG ghi output chính:

- YAML hợp lệ, đủ field bắt buộc

- mỗi step.action CÓ trong action_registry, params khớp param-schema của action

- input folder tồn tại

- output path tạo được

- thứ tự + quan hệ needs hợp lý (không phụ thuộc vòng)

Registry là nguồn để dry-run biết action nào hợp lệ — đây là lý do adapter/registry bắt buộc.


14. Integration — qua ADAPTER + REGISTRY (đã sửa chữ ký)
Automation KHÔNG gọi thẳng hàm nội bộ module. Mỗi module có một adapter phơi interface ổn định; action_registry map module.action → hàm adapter + schema tham số. Interface module đổi → chỉ sửa adapter, KHÔNG sửa hàng loạt YAML.

Chữ ký đúng theo module thật:

# knowledge_adapter

vision_mode_a(input, output, project=None, settings=None)

vision_mode_b(project, subject, input, settings=None)   # compact sinh bên trong theo settings

update_manifest(project, subject)

# prompt_adapter  (SỬA: brief bắt buộc, đa subject, target_language)

generate_prompt(project, subject_or_subjects, prompt_type, brief,

                target_language=None, settings=None)

# validator_adapter  (SỬA: theo validation_type)

validate_image(project, subject, image_path, dna_path, prompt_path=None, settings=None)

validate_prompt(project, subject, prompt_json_path, dna_path, settings=None)

action_registry khai báo tham số bắt buộc từng action để dry-run kiểm trước. Thiếu brief cho generate_prompt → dry-run báo lỗi ngay, không đợi chạy thật.


15. Output Organization
Automation chỉ lưu điều phối; output nghiệp vụ do module con lưu ở chỗ của chúng.

data/automation_runs/{logs, reports, state, locks}/

Automation đối chiếu output kỳ vọng vs thực tế trong report, nhưng KHÔNG archive/ghi đè file của module (§3.5).


16. Kế hoạch phát triển theo GIAI ĐOẠN
GIAI ĐOẠN 0 — Khung & nạp cấu hình
Phase 0 — Module setup. Cây automation_studio/, config/workflows/, data/automation_runs/, README. DoD: import không lỗi; venho auto --help chạy; nối shared/logging.

Phase 1 — Workflow Loader + Action Registry. workflow_loader.py, action_registry.py. DoD: load YAML, index theo workflow_id; validate field bắt buộc; action lạ → báo lỗi; venho auto list chạy; registry liệt kê action hợp lệ + param schema.
GIAI ĐOẠN 1 — Chạy chuỗi an toàn (dummy, mock)
Phase 2 — Workflow Runner + Step Executor + dependency errors. workflow_runner.py, step_executor.py. DoD: chạy workflow dummy (adapter mock); success/failed ghi nhận; on_error: stop và continue hoạt động; skip_dependents: bước fail → bước needs nó bị skip (không chạy input rỗng).

Phase 3 — Run State + Run Lock. run_state.py, run_lock.py. DoD: mỗi run có run_id + state JSON (started/finished, status từng step, attempts); lock chặn chạy song song cùng workflow; lock giải phóng cả khi lỗi.

Phase 4 — Report Builder. report_builder.py. DoD: report .md đủ section §9; ghi outputs/warnings/failed/skipped; có mục MANUAL GATE và NEXT ACTIONS.

Phase 5 — Dry-run. trong cli.py/runner. DoD: --dry-run không gọi AI/không ghi; kiểm action qua registry + param; kiểm input/output path; phát hiện phụ thuộc vòng.
GIAI ĐOẠN 2 — Tích hợp module (mock trước, thật sau)
Phase 6 — Adapter Knowledge Studio. adapters/knowledge_adapter.py. DoD: Mode A và Mode B chạy qua adapter; report ghi đúng output M01; cache M01 vẫn hoạt động (resume rẻ); test chạy được ở mock.

Phase 7 — Adapter Prompt Studio. adapters/prompt_adapter.py. DoD: generate_prompt chạy từ DNA với brief bắt buộc + đa subject + target_language; thiếu DNA → báo lỗi rõ; thiếu brief → dry-run chặn; output ghi vào report.

Phase 8 — Adapter Validator Studio. adapters/validator_adapter.py. DoD: validate_prompt và validate_image chạy qua adapter; score/verdict ghi vào report; verdict reject → WARNING + NEXT ACTIONS.
GIAI ĐOẠN 3 — Pipeline thật (có điểm dừng thủ công)
Phase 9 — Two-half pipeline + manual_gate. DoD: Nửa 1 (DNA → Prompt) chạy một lệnh, kết thúc bằng manual_gate in hướng dẫn tạo ảnh; Nửa 2 (image → validation) chạy một lệnh sau khi người dùng đặt ảnh; state đầy đủ; lỗi một step xử lý đúng (stop/skip_dependents); KHÔNG giả vờ nối liền khâu tạo ảnh.

Phase 10 — Resume + Scheduler preparation. DoD: venho auto resume <run_id> chạy lại từ resumable_from, tận dụng cache; trigger field parse được (manual chạy, schedule/folder_watch chỉ parse chưa bật).


17. MVP Acceptance Test
venho auto run mode_a_image_to_md --project _inbox     # → observations + state + report + log

venho auto run venho_room_dna_update                   # → DNA .md+.json+compact + manifest + report

venho auto run venho_prompt_generation                 # → prompt + manual_gate (hướng dẫn tạo ảnh)

# (người dùng tạo ảnh ở Flow, đặt vào production/images/)

venho auto run venho_half2_validation                  # → validation report

Đạt MVP khi: chạy được Mode A và Mode B qua một lệnh, ra output + state + report + log đầy đủ; run lock hoạt động; dry-run bắt lỗi config trước khi chạy thật.


18. Rủi ro chính
1. Chứa logic module khác     → chỉ gọi qua adapter; registry giới hạn action

2. Workflow hard-code         → khai báo YAML; project override lúc chạy

3. Scheduler quá sớm          → manual first; schedule chỉ parse ở MVP

4. Không có report            → mỗi run có state + report + log

5. Ghi đè output              → archive thuộc MODULE; automation không overwrite file production

6. Giả vờ nối liền tạo ảnh    → manual_gate; hai nửa tách bạch (§6)

7. continue làm rác downstream → skip_dependents theo `needs`

8. Retry chồng retry          → module retry API; automation không retry chồng

9. Chạy song song hỏng state  → run lock theo workflow_id

10. Test tốn token            → adapter mock; tích hợp test ở mock trước


19. Nguyên tắc không thay đổi
CLI trước, UI sau. Manual trước, scheduler sau. Config-first.

Không hard-code Ven Hồ. Automation KHÔNG chứa business logic module khác.

Mỗi run có state + log + report. Archive thuộc module con.

Không giả vờ tự động hóa khâu tạo ảnh (điểm dừng thủ công là có thật).

Không DB/cloud trước khi local ổn.


20. Kết luận
Automation Studio nối Module 01–03 thành hệ vận hành thực tế — nhưng trung thực về giới hạn: chuỗi sản xuất ảnh có một điểm dừng thủ công (tạo ảnh ở công cụ ngoài), nên automation điều phối hai nửa chứ không một mạch liền.

Điểm cần giữ tuyệt đối:

Automation chỉ ĐIỀU PHỐI: không tạo, không validate, không sửa.

Gọi module con QUA adapter + registry, không import sâu.

Bước phụ thuộc một bước fail phải SKIP, không chạy input rỗng.

Archive thuộc module con; automation chỉ kiểm và báo cáo.

Khâu tạo ảnh là điểm dừng thủ công — thừa nhận, không giả vờ tự động.

Mỗi run có lock, state, log, report; hỗ trợ resume.

END OF DOCUMENT v1.1 (QC Consolidated)

