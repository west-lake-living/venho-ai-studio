VENHO AI STUDIO
Module 10 — Dashboard Development Plan v1.2 (QC Approved)
Workspace: THE WEST LAKE LIVING Repo: venho-ai-studio Module: dashboard/ Position: Module 10 — Final Unified Presentation Layer Cập nhật: 2026-07-09


0. Báo cáo Kiểm tra Chất lượng (QA Changelog v1.1 → v1.2)
Bản v1.1 gốc là một file bị lẫn tạp: nội dung kế hoạch bị lặp lại 2–3 lần, chèn cả đoạn mã Python thừa và text rác của giao diện chat. Các lỗi sau đã được phát hiện và xử lý:

Dọn trùng lặp & rác: Loại bỏ toàn bộ nội dung lặp (plan xuất hiện 2–3 lần), đoạn code md_content/with open(...), và text giao diện chat rác ("Your MD file is ready", "Gemini is AI and can make mistakes", tên file echo, "Displaying...").
Lỗi font ký tự: Sửa ký tự tiếng Trung 顯示 (lọt vào phần nguyên tắc Module-Independent) thành hiển thị.
Chuẩn hóa tên KOL: Lình An → Linh An cho khớp DNA subject linh_an và task_memory.md.
Thống nhất tên Face Gate: Trước đây dùng lẫn "Face Lock v3.1" và "Master Face v3.1". Đã thống nhất dùng Face Lock v3.1 (gắn với QC gate 07F) trên toàn tài liệu.
Bổ sung bước Roadmap còn thiếu (M06): IA và MVP Acceptance Test có tham chiếu M06 Video Studio nhưng roadmap cũ bỏ sót bước xây màn hình này. Đã thêm Step 7 — Video Studio Preview và đánh số lại các bước.
Sửa mô tả Manual Gate cho đúng nguyên tắc Zero Business Logic: ModuleRequest do M09 đóng gói; Dashboard chỉ phê duyệt và chuyển tiếp sang M04 (không tự build ModuleRequest trên UI).
Cập nhật danh sách DNA subjects theo thực tế: thêm lobby, facade, westlake, outside (theo task_status.md).
Chuẩn hóa định dạng: Cấp heading nhất quán (##); mọi sơ đồ cây/thư mục được bọc trong code block.
Đồng bộ kỷ luật test với backend: Ràng buộc 0 API call trong pytest, đồng bộ chuẩn 423/423 tests của M01–M09.

Quyết định cần xác nhận (Open Decision): Stack đề xuất cho M10 là web JS (Next.js / Nuxt / Vite), khác với Studio Shell hiện có của M01 (Streamlit @ localhost:8501). Cần chốt: M10 là một web app độc lập mới, hay mở rộng trên nền Streamlit sẵn có.


1. Mission
Dashboard (M10) là trung tâm điều khiển và hiển thị hợp nhất của VENHO AI Studio.

M10 không thay thế bất kỳ logic nghiệp vụ nào của các module cốt lõi (M01–M09). Nó đóng vai trò là lớp hiển thị (UI Layer): trực quan hóa trạng thái, giám sát công việc, và cung cấp cổng tương tác thủ công (Manual Gate / Approval) cho người dùng.

Core kiến trúc bất biến:

Dashboard      = Pure Presentation UI

Business Logic = Existing Core Modules (M01–M09) APIs Only


2. Objectives
Single Entry Point: Cửa ngõ duy nhất để quản lý toàn bộ vòng đời dữ liệu từ hình ảnh thô đến phân phối marketing.
Project Management: Khởi tạo, cấu hình và quản lý các không gian dự án (mặc định ban đầu là dự án venho_hotel).
Job & Workflow Monitoring: Giám sát thời gian thực các tác vụ điều phối bởi M04 Automation Studio.
Knowledge & Asset Browser: Xem cấu trúc DNA JSON (contract v1.1), DNA_COMPACT, và hình ảnh KOL Linh An (Face Lock v3.1).
Prompt & Content Preview: Hiển thị cấu trúc Prompt JSON (M02) và duyệt các bản thảo văn xuôi (M05 prose).
Validation & Quality Guardrails: Hiển thị điểm số, báo cáo vi phạm, và gợi ý sửa đổi từ M03 Validator.
Gate Keeper & Publishing Center: Kiểm tra trạng thái phê duyệt (HMAC Signature), hàng đợi phân phối và biên lai (receipt) của M07.
Cognitive Agent Interface: Giao diện nhập Goal cho M09 Agent Studio, duyệt Task Plan và phê duyệt Module Request để gửi sang M04.
System Health & Logs: Giám sát Token usage, Cache hit rate, System logs, và lỗi phân phối.


3. Principles
Thin UI / Stateless: Dashboard không lưu trữ trạng thái nghiệp vụ riêng, không có DB độc lập ngoại trừ cấu hình UI/Theme. Toàn bộ dữ liệu được đọc/ghi thông qua Public API / CLI Contract của các Module con.
Module-Independent: Một module con bị lỗi không được phép làm sập toàn bộ giao diện Dashboard. Các thành phần giao diện phải có cơ chế xuống cấp an toàn (Graceful Degradation — hiển thị Advisory thay vì crash).
Local-First / Developer-Centric: Tối ưu hóa cho việc chạy local mượt mà thông qua giao diện web responsive (ưu tiên hiển thị Desktop).
Zero Business Logic Duplication: Nghiêm cấm viết lại logic kiểm tra dữ liệu, tính điểm, hoặc build prompt trên UI. Dashboard chỉ parse JSON/Markdown kết quả từ các module core.


4. Information Architecture
Dashboard (M10)

├── Home                 (Tổng quan hệ thống, Queue, Quick Actions)

├── Projects             (Quản lý cấu hình dự án, Brand Display "Ven Hồ Hotel")

├── Knowledge Studio     (M01 — Browse DNA JSON v1.1, Overrides, Manifests)

├── Prompt Studio        (M02 — Prompt Library, Deterministic Templates Preview)

├── Validator Studio     (M03 — Validation Reports, Face Score Thresholds)

├── Automation Studio    (M04 — Workflow Controller, Manual Approval Gate)

├── Content Studio       (M05 — Prose Drafts Browser, Editorial Calendar, Export)

├── Video Studio         (M06 — Storyboard Preview, Engine Prompt Packages)

├── Publishing Gateway   (M07 — Distribution Queue, HMAC Approvals, Platform Receipts)

├── Analytics & Feedback (M08 — Performance Score, Sentiment Guardrail, Advisory Alerts)

├── Agent Studio         (M09 — Cognitive Goal Input, Task Planner & Risk Viewer)

├── System Monitor       (Logs, Token Usage, Cache Status, Circuit Breakers)

└── Settings             (API Keys Reference, Provider Configs, Theme)


5. Main Screens & UI Specs
Home
Trạng thái tổng thể của các Agent và Workflow đang chạy.
Hàng đợi tác vụ tích hợp (M04 Automation Queue).
Lối tắt (Quick Actions): "Tạo bài viết mới từ ảnh", "Kiểm tra Staleness DNA".
Projects
Quản lý danh sách dự án. Đọc dữ liệu từ config/projects/{project_name}/.
Hiển thị thông tin Brand tĩnh đúng quy ước: Prompt hiển thị "Ven Ho Hotel" (không dấu), giao diện hiển thị tiếng Việt có dấu "Ven Hồ Hotel".
Knowledge (M01 Interface)
Duyệt danh sách DNA Subjects: lake_view_room, deluxe_double, lobby, facade, linh_an, westlake, outside.
Giao diện hiển thị cây thư mục: _DNA.md, _DNA.json, overrides.yaml.
Lưu ý: Cho phép sửa overrides.yaml (Curated Overlay) nhưng không được can thiệp vào file gốc pass 2A tất định.
Prompt & Content (M02 + M05 Interface)
Xem thư viện prompt cấu trúc. Preview prose văn xuôi được tạo sinh từ M05.
Nút "Yêu cầu tái sinh" (Regenerate) → Dashboard gửi lệnh xuống API M05 với tham số temperature > 0.
Validator (M03 Interface)
Hiển thị biểu đồ radar/line về chất lượng nội dung.
Cảnh báo trực quan nếu điểm Face Lock của KOL Linh An dưới ngưỡng quy định. Thao tác duyệt: ≥ 9.0 APPROVED · 8.0–8.9 CONDITIONAL · < 8.0 REJECT.
Kill-switch: forbidden severity=high → cap overall = 40, verdict = regenerate (đọc từ M03, không tính lại trên UI).
Video Studio (M06 Interface)
Duyệt Storyboard Preview và Shot List do M06 sinh ra (pre-render package).
Xem Engine Prompt Packages (đóng gói theo định dạng engine, ví dụ aspect ratio 9:16).
Ràng buộc: M06 chỉ tạo gói tiền dựng — Dashboard không render, không upload, không publish video.
Automation & Agent (M04 + M09 Interface)
M09 Box: Nơi người dùng nhập "Goal" bằng ngôn ngữ tự nhiên. Giao diện hiển thị TaskPlan và Risk Classifier thu được từ M09.
Manual Gate: Nút "Approve Plan & Dispatch" → phê duyệt và chuyển tiếp gói ModuleRequest (do M09 đóng gói) sang M04 Automation Studio để thực thi. Dashboard không tự dựng ModuleRequest.
Ràng buộc: Tuyệt đối không cho phép Dashboard hoặc M09 tự ý kích hoạt phân phối ra môi trường ngoài.
Publishing & Analytics (M07 + M08 Interface)
M07 Tracker: Hiển thị danh sách bài đăng chờ duyệt. Kiểm tra chữ ký HMAC-SHA256 hợp lệ và TTL trước khi cho phép bấm "Publish Live" (hoặc Dry-run).
M08 Dashboard: Hiển thị Unified Platform Metrics, biểu đồ Sentiment Analysis (cảnh báo từ khóa độc hại), và danh sách "Advisory/Report" dưới dạng khuyến nghị — luôn pending_approval, không tự động áp dụng.


6. Repository Layout
dashboard/

├── app/        # Next.js / Nuxt / Vite main application setup

├── pages/      # Các trang chính theo Kiến trúc Thông tin

├── widgets/    # Các UI Components dùng chung (Biểu đồ, Thẻ trạng thái)

├── services/   # Lớp kết nối, parse CLI/API đầu ra từ M01–M09

├── state/      # Quản lý trạng thái UI local (Theme, Active Project)

├── api/        # Mock API server phục vụ phát triển độc lập và Testing

├── assets/     # CSS, Icons, Static Images

└── tests/      # Component Tests & Giao diện Isolation Tests


7. Data Sources & Integration Seams
Dashboard trao đổi dữ liệu bất biến qua các cổng giao tiếp đã được định nghĩa:

Đọc cấu hình: Thư mục config/projects/ làm Single Source of Truth.
Tương tác Core: Gọi qua Python Bridge Public API hoặc CLI Wrapper của từng Module.
Ràng buộc bảo mật: Mọi lệnh ghi đè hoặc phê duyệt (Approval) gửi từ Dashboard qua M04/M07 phải đính kèm Metadata định danh người dùng và kiểm tra tính toàn vẹn chữ ký (HMAC Verification).


8. Core Widgets Specification
Widget Name
Target Module
Visual Type
Output Requirement
Job Coordinator Queue
M04 Automation
List / Progress Bar
Monitor running tasks, cancel, retry orchestration
Linh An Face Quality Gate
M03 Validator
Gauge Meter / Status Badge
Score & Threshold matching (Face Lock v3.1, gate 07F)
Video Storyboard Preview
M06 Video
Storyboard Grid / Shot List
Preview pre-render package, engine prompt readout
Publishing Live Gateway
M07 Gateway
Table Queue / Action Buttons
HMAC Approval Signature & TTL verification
Brand Sentiment Guardrail
M08 Analytics
Alert Banner / Text Highlighter
Critical Alerts for Vi/En keyword violations
Agent Task Planner
M09 Agent
Workflow Tree Diagram
Display goal-to-task plans, risk markers, block destructive acts
Token & Cache Analytics
System Monitor
Area Chart / Ratio Indicator
Token usage tracking, Cache hit rate optimization



9. Step-by-Step Development Roadmap
Step 0: Scaffold & Base Architecture
Thiết lập cấu trúc thư mục dashboard/. Cấu hình bundler, routing framework.
DoD: Ứng dụng khởi chạy thành công, nhận diện đúng cấu trúc thư mục con, routing hoạt động 100%.
Step 1: Shell & Navigation Master
Xây dựng Sidebar Layout, Topbar hiển thị Tên Dự Án Hiện Tại (venho_hotel) và Module Navigation.
DoD: Chuyển đổi qua lại giữa tất cả các tab module mượt mà, layout responsive.
Step 2: Project Manager Hub
Đọc và hiển thị dữ liệu từ config/projects/. Cho phép chuyển đổi cấu hình hiển thị thương hiệu.
DoD: Hiển thị danh sách dự án, cấu hình đồng bộ chuẩn, hiển thị đúng chữ có dấu "Ven Hồ Hotel" trên UI.
Step 3: Automation & Job Center
Tích hợp với API của M04 Automation Studio để hiển thị tiến độ chạy workflow.
DoD: Theo dõi được trạng thái task (Pending, Running, Success, Failed), thực hiện được lệnh Cancel/Retry thông qua M04 Adapter.
Step 4: Knowledge Browser
Xây dựng UI hiển thị cây tri thức M01 (DNA JSON v1.1, Manifests).
DoD: Hiển thị trực quan dữ liệu DNA của các Subject mà không làm thay đổi hay chạy lại pipeline AI sinh DNA gốc.
Step 5: Prompt & Content Suite
Tích hợp hiển thị Prompt Templates (M02) và Prose Drafts (M05).
DoD: Người dùng đọc được bản thảo văn xuôi, xem lịch biên tập (Calendar UI), bấm nút kích hoạt lệnh sinh lại văn bản (với temperature > 0).
Step 6: Validator Dashboard
Kết nối báo cáo chất lượng từ M03.
DoD: Hiển thị bảng điểm, biểu đồ chất lượng, bộ lọc trạng thái Face Lock của ảnh KOL Linh An.
Step 7: Video Studio Preview
Xây dựng màn hình duyệt Storyboard, Shot List và Engine Prompt Packages từ M06.
DoD: Hiển thị đầy đủ gói tiền dựng của M06 (storyboard, shot list, engine prompt) mà không kích hoạt render/upload; degrade advisory khi thiếu Face DNA (include_character=true).
Step 8: Publishing Gateway Monitor
Xây dựng màn hình quản lý hàng đợi phân phối của M07.
DoD: Hiển thị danh sách bài đăng, nút kích hoạt Dry-run/Publish Live, kiểm tra thời hạn TTL và tính hợp lệ của chữ ký phê duyệt (HMAC).
Step 9: Analytics & Feedback Loop View
Hiển thị Unified Snapshot, báo cáo Sentiment và danh sách Advisory từ M08.
DoD: Trực quan hóa dữ liệu hiệu suất bài đăng, hiển thị các đề xuất cải tiến dưới dạng Alert/Advisory (không tự động can thiệp sửa đổi file core).
Step 10: Agent Cognitive Console
Xây dựng giao diện tương tác với M09 Agent Studio.
DoD: Khung nhập Goal → nhận và vẽ sơ đồ Task Plan → nút Manual Gate chuyển trạng thái duyệt, chuyển tiếp ModuleRequest sang M04 điều phối.
Step 11: Logs, System Monitor & Settings
Trực quan hóa hệ thống log, thống kê lượng Token sử dụng, Cache hit rate của toàn hệ thống.
DoD: Dashboard hiển thị đầy đủ log hệ thống theo thời gian thực, có bộ lọc theo mức độ (Error, Critical Alerts).
Step 12: MVP Acceptance Test (End-to-End Workflow)
Kịch bản kiểm thử tích hợp tối cao trên UI:

Chọn dự án venho_hotel.
Nhập mục tiêu tiếp thị vào Agent Console (M09).
Xem Task Plan được sinh ra, kiểm tra Risk Classifier.
Bấm Duyệt chuyển tiếp sang Automation Studio (M04).
Theo dõi tiến độ chạy Job sinh DNA (M01), Prompt (M02), Prose (M05).
Kiểm tra điểm số Face Lock và chất lượng tại Validator Tab (M03).
Xem bản thảo Content & Video Storyboard (M06).
Thực hiện Dry-run và xác thực chữ ký phê duyệt tại Publishing Gateway (M07).
Xem dữ liệu giả lập và Advisory sinh ra tại Analytics Tab (M08).
Kiểm tra Log & Token tiêu tốn tại System Monitor.
DoD: Toàn bộ kịch bản chạy khép kín thành công từ một giao diện duy nhất, không có lỗi xung đột luồng dữ liệu.


10. Test Discipline & Quality Guardrails
Zero Live API Calls: Tuyệt đối không gọi API thật của nhà cung cấp LLM hoặc nền tảng mạng xã hội trong quá trình chạy kiểm thử Dashboard (pytest). Đồng bộ chuẩn backend hiện tại: 0 API call (M01–M09 đạt 423/423 tests pass).
Isolation Mocking: Tất cả service kết nối module con (M01–M09) trong Dashboard phải được giả lập (Mocked) qua file fixture dữ liệu tĩnh hoặc local mock servers.
Component Boundary Test: Viết Unit test riêng biệt cho từng Widget hiển thị (ví dụ: đảm bảo Widget Validator tự động chuyển trạng thái REJECT khi điểm số đầu vào < 8.0).


11. Risks & Mitigations
Risk 1 — Trượt logic nghiệp vụ vào mã nguồn UI.
Mitigation: Thiết lập rào cản kiểm duyệt code chặt chẽ (Code review rule). Mọi thao tác tính toán logic cốt lõi phải nằm ở phía module Python nền tảng; Dashboard chỉ gọi thực thi qua API/CLI.
Risk 2 — Dashboard bị treo/chậm do tải file JSON/Markdown quá lớn.
Mitigation: Sử dụng Pagination, Lazy loading và UI Cache Local cho các tệp dữ liệu tri thức cồng kềnh.
Risk 3 — Vi phạm nguyên tắc bảo mật khi phân phối.
Mitigation: Dashboard không lưu trữ hay tự sinh Token/API Key. Toàn bộ thông tin nhạy cảm được quản lý bằng biến môi trường hoặc cấu hình mã hóa của Publishing Gateway (M07); giao diện chỉ hiển thị dạng tham chiếu (ẩn ký tự).


---

## Addendum — VenHo OS Next.js Dashboard (2026-07-13)

Quyết định kiến trúc cuối cùng: **M10 chuyển sang Next.js VenHo OS; Streamlit được loại bỏ sau khi migration hoàn tất.**

| Nền tảng | URL | Mục đích |
|---------|-----|---------|
| **Next.js `src/app/os/`** | `localhost:3000/os` | VenHo OS Stage A+B+C — Section UI, Creative tools, Knowledge viewer |
| Streamlit `ui/studio_app.py` | removed | Superseded by Next.js VenHo OS |

### Next.js OS — Implementation Complete

**Codebase:** `Ven Ho Hotel/src/app/os/` + `src/components/os/` + `src/app/api/v1/studio/`

**Stage A ✅ — Section Routing**
- `os/page.tsx` — RSC, reads `searchParams` (Next.js 16 Promise), routes to section components
- `SidebarNavigation.tsx` — 9 items, `<Link>` from next/link, active blue dot
- `WorkspaceHeader.tsx` — dynamic section title
- 8 `PlaceholderSection` wrappers

**Stage B ✅ — Workbench + Creative Studio**
- `src/lib/studio/` — `paths.ts`, `constants.ts` (Python port), `prompt-builder.ts` (pure TS)
- `WorkbenchSection.tsx` — Mode A (Observe) + Mode B (Build DNA), SSE live log via `LiveLog.tsx`
- `CreativeStudioSection.tsx` — Tạo Ảnh AI, Tạo Social Post, Tạo Video Script
- API: `observe` (SSE), `generate-image`, `file`, `save-script`

**Stage C ✅ — Knowledge + Reports**
- `KnowledgeSection.tsx` — DNA Library (colored blocks per section type), Vault Search (highlight), Mode C Linh An
- `ReportsSection.tsx` — DNA Status (4 summary cards + subjects table), Social Content Log (entries + pillar filter)
- API: `dna`, `vault-search`, `social-index`

**Cleanup ✅**
- `src/components/os/shared/ui.tsx` — shared primitives (SectionHeader, Field, PrimaryBtn, CopyBtn, TabBar)
- Xóa `src/shared/kernel/result.ts` + test — dead code
- Xóa unused imports (`SCENARIO_SUBJECT`), redundant aliases (`selectCls`)
- Build: ✓ Compiled, 34/34 pages, 0 TypeScript error

---

END OF DOCUMENT
M10 Dashboard Plan v1.2 đã đồng bộ 100% với task_status.md (M01–M09 COMPLETE, 423/423 tests, 0 API call) và task_memory.md, loại bỏ hoàn toàn nội dung trùng lặp và rác, chuẩn hóa tên gọi và bổ sung bước Roadmap còn thiếu.
Addendum 2026-07-13: Next.js OS Stage A+B+C hoàn thành. M10 dùng Next.js (`localhost:3000/os`) làm entrypoint UI duy nhất; Streamlit đã được loại bỏ.
