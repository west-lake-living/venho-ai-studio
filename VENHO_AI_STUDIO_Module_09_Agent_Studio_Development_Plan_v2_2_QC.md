VENHO AI STUDIO
Module 09 — Agent Studio Development Plan v2.2 QC
Workspace mẹ: THE WEST LAKE LIVING
Repo: venho-ai-studio
Module: agent_studio/
Module ID: M09
Vị trí: Sau M07 Publishing Gateway và M08 Analytics Feedback
Trạng thái: QC Consolidated Plan (v2.2 — đã sửa lỗi nhất quán)
Nguồn review: VENHO_AI_STUDIO_Module_09_Agent_Studio_Development_Plan_v2_1_QC.md
Nguyên tắc cập nhật: M09 là Cognitive Interface / Agent Orchestration Layer. M09 không thay thế M04 Automation, không tự publish, không tự sửa Knowledge, không tự phân tích metrics, không chứa logic business hard-coded.


0. Kết luận QC
Bản M09 Agent Studio v2.1 QC đã đi đúng hướng khi định nghĩa Agent Studio là lớp chuyển mục tiêu mở của người dùng thành pipeline thực thi có cấu trúc, thông qua M04 Automation Studio. Bản gốc đã xác định rõ các nguyên tắc quan trọng: Knowledge First, Project-agnostic Core, Role-based Persona, Pipeline Orchestration over LLM Autonomy, Human-in-the-loop và test offline 0 API Call.

Sau khi kiểm tra chất lượng, cần chỉnh các điểm sau:

Ranh giới với M04 Automation

M09 chỉ lập kế hoạch, điều phối nhận thức và đóng gói yêu cầu.
M04 mới là module thực thi pipeline.
M09 không tự chạy workflow dài, không tự gọi module sản xuất trực tiếp nếu bypass M04.

Ranh giới với M07 Publishing Gateway

M09 không tự publish.
M09 không gọi API Meta/Google/Threads trực tiếp.
Nếu cần xuất bản, M09 chỉ tạo proposal hoặc request gửi qua M04 approval gate, sau đó M04 mới gọi M07.

Ranh giới với M08 Analytics Feedback

M09 có thể đọc analytics advisory.
M09 không tự thu thập metrics.
M09 không tự tính performance score.
M09 có thể giải thích advisory và đề xuất hành động.

Sửa dependency

M09 nên phụ thuộc vào đầy đủ các module trước đó thông qua contract:
M01 Knowledge
M02 Prompt
M03 Validator
M04 Automation
M05 Content
M06 Video
M07 Publishing Gateway qua M04
M08 Analytics Feedback
M09 không gọi M07 trực tiếp để publish.

Sửa output contract

Agent output không nên chứa recommended_hashtags như output tự do nếu việc đó thuộc M05 Content Studio.
Agent có thể đề xuất content_request hoặc automation_plan.
Output chính nên là:
Plan
Task graph
Required knowledge
Module requests
Validation summary
Human approval requirements

Sửa Persona Template

Persona không được chứa tri thức cứng.
Persona tối thiểu phải chứa: role, scope, allowed modules, forbidden actions, required knowledge.
Persona có thể mở rộng thêm: validation level, approval rules.

Sửa test convention

Không đặt target test count tuyệt đối như 387+.
Thay bằng:
100% M09 tests pass
0 real API call in pytest
Critical paths covered
Mock AI client only in tests

Thêm approval policy

M09 phải phân loại action theo risk level.
Action có external impact phải yêu cầu human approval.
Action read-only có thể chạy tự động.
Approval policy được đặt tập trung tại config/projects/<project>/agents/agent_policy.yaml.


0.1 QC Changelog v2.1 → v2.2
Bản v2.2 sửa các lỗi nhất quán nội tại phát hiện khi rà soát chéo giữa các mục:

Bổ sung Request Validator vào roadmap. request_validator.py xuất hiện trong kiến trúc (Mục 5) và repo (Mục 6) nhưng ở v2.1 không có step nào tạo ra nó. Đã thêm Step 3 — Request Validator vào Phase 2.
Gắn execution_log.py vào step cụ thể. File này là orphan trong v2.1. Đã đưa vào DoD của Result Aggregator.
Sửa mâu thuẫn thứ tự Router ↔ Persona. Mục 1 và Mục 5 đặt Agent Router → Persona Resolver, nhưng roadmap và Mục 19 (priority) của v2.1 đảo ngược. Đã thống nhất toàn bộ theo kiến trúc: Agent Router → Persona Resolver.
Đồng bộ cây config. Mục 4.2 (3 file) vs Mục 7 (4 file) không khớp. Đã thống nhất cả hai gồm: marketing_agent.yaml, linh_an_brand_agent.yaml, hotel_ops_agent.yaml, agent_policy.yaml.
Thêm step cho agent_policy.yaml. Approval policy (điểm 0.8) nay có Step 20 — Agent Policy Config riêng.
Xác định phạm vi hotel_ops_agent. Trước đây được nhắc tới nhưng không định nghĩa. Đã đánh dấu rõ là post-MVP (ngoài phạm vi MVP M09), giữ chỗ trong cây config kèm ghi chú.
Sửa lỗi ranh giới ở Mục 4.2. Câu "Gửi request qua M04/M05/M07" vi phạm nguyên tắc M09 không chạm M07 trực tiếp. Đã sửa thành "Gửi request qua M04 (M04 điều phối tới M05/M07)".
Bổ sung template thiếu. templates/ nay có visual_planning_agent.md để khớp với agent tương ứng.
Đồng bộ danh sách test. tests/ được bổ sung để phủ đủ critical paths ở Mục 13.3: request validator, module request builder, automation bridge, result aggregator, brand display rule.
Hoàn thiện Mục 19 (priority order). Bổ sung Request Validator, Renderers, Research Agent, Visual Planning Agent, Agent Policy Config vốn bị thiếu ở v2.1; sắp xếp lại theo đúng thứ tự phụ thuộc.
Làm rõ ràng buộc Task Plan. Task tham chiếu M05/M06 trong TaskPlan là mô tả kế hoạch; việc dispatch thực tế luôn đóng gói và đi qua M04 Automation Bridge (xem ghi chú Mục 9).


1. Vai trò chính thức của M09
Agent Studio là lớp Cognitive Interface & Agent Orchestration Layer.

Nó biến mục tiêu tự nhiên của người dùng thành kế hoạch thực thi có cấu trúc.

User Goal

    ↓

M09 Request Validator

    ↓

M09 Agent Router

    ↓

M09 Persona Resolver

    ↓

M09 Context Loader

    ↓

M09 Missing Knowledge Detector

    ↓

M09 Task Planner

    ↓

M09 Risk Classifier

    ↓

M09 Module Request Package

    ↓

M04 Automation Studio

    ↓

M01-M08 execution via contracts

    ↓

M09 Result Aggregator

    ↓

Markdown + JSON Report

M09 không phải module thực thi trực tiếp.

M09 là lớp giúp người dùng giao tiếp với toàn bộ AI Studio bằng mục tiêu mở.


2. Nguyên tắc thiết kế
2.1 Knowledge First
Agent không được bịa thông tin.

Nếu thiếu tri thức:

ERR_MISSING_KNOWLEDGE

Agent phải trả về danh sách thiếu:

Knowledge file nào thiếu
Field nào thiếu
Module nào cần bổ sung dữ liệu
2.2 Project-agnostic Core
Core agent engine không chứa logic Ven Hồ.

Project-specific behavior nằm trong:

config/projects/<project>/agents/
2.3 Persona is Configuration
Persona là config, không phải code.

Persona chỉ định:

Role
Scope
Allowed modules
Forbidden actions
Required knowledge
Validation level
Approval rules
2.4 Planning over Autonomy
LLM được dùng để lập kế hoạch, không được tự trị vô hạn.

Không có vòng lặp agent tự chạy không kiểm soát.

Mọi plan phải có:

max_steps
max_cost_estimate nếu có
stop conditions
approval gates
2.5 Human-in-the-loop
Mọi action có tác động bên ngoài phải qua approval:

Publishing
Sending email
Updating public content
Deleting files
Updating official Knowledge
Changing campaign strategy
2.6 Offline Test Discipline
Trong pytest:

Không gọi OpenAI/Claude thật
Không gọi API platform thật
Không đọc secret thật
Không phụ thuộc internet
Dùng mock AI client
Dùng fixture JSON


3. Ranh giới module
3.1 M09 được phép làm
Nhận user goal.
Chọn agent/persona phù hợp.
Load context từ Knowledge.
Lập kế hoạch task.
Tạo request gửi M04.
Đọc advisory từ M08.
Tổng hợp kết quả module.
Tạo báo cáo Markdown + JSON.
Xác định missing knowledge.
Đánh dấu yêu cầu approval.
Đề xuất bước tiếp theo.
3.2 M09 không được làm
Không tự publish.
Không tự gọi Meta/Google/Threads API.
Không tự ghi đè Knowledge.
Không tự tạo content nếu bỏ qua M05.
Không tự tạo video nếu bỏ qua M06.
Không tự validate nếu bỏ qua M03.
Không tự thu thập analytics nếu bỏ qua M08.
Không tự chạy automation nếu bỏ qua M04.
Không chứa business logic cứng của Ven Hồ.
Không chạy vòng lặp vô hạn.


4. Agent Types
4.1 Generic Agents
Research Agent
Vai trò:

Phân tích thị trường.
Phân tích đối thủ.
Tổng hợp xu hướng.
Tạo research brief.

Lưu ý:

Nếu cần dữ liệu mới ngoài hệ thống, phải đánh dấu yêu cầu research external.
Không tự khẳng định dữ liệu nếu không có nguồn.
Documentation Agent
Vai trò:

Viết tài liệu kỹ thuật.
Tạo spec.
Tạo report.
Chuẩn hóa Markdown.
Content Planning Agent
Vai trò:

Lập kế hoạch nội dung.
Đề xuất campaign.
Tạo ContentRequest cho M05.
Không tự viết final content nếu chưa gọi M05.
Image / Visual Planning Agent
Vai trò:

Đề xuất visual task.
Tạo request cho M01/M02/M03/M06.
Không tự phân tích ảnh nếu không qua Knowledge Studio / Vision.
Analytics Insight Agent
Vai trò:

Đọc advisory từ M08.
Giải thích performance.
Tạo action plan.
Không tự tính metrics.
4.2 Project-specific Agents
Project agents nằm trong config.

Ví dụ:

config/projects/venho_hotel/agents/

├── marketing_agent.yaml

├── linh_an_brand_agent.yaml

├── hotel_ops_agent.yaml        # post-MVP, giữ chỗ, chưa triển khai trong MVP M09

└── agent_policy.yaml
Ven Hồ Hotel Marketing Agent
Dùng Brand DNA.
Dùng Content Pillars.
Dùng Analytics Advisory.
Tạo campaign proposal.
Gửi request qua M04 khi được duyệt (M04 điều phối tới M05/M07; M09 không gọi M07 trực tiếp).
Linh An Brand Agent
Dùng Character DNA.
Dùng Face Lock.
Dùng Style Rules.
Không tạo output vi phạm identity.
Luôn yêu cầu Validator nếu có visual/video.
Hotel Ops Agent (post-MVP)
Phạm vi: hỗ trợ vận hành nội bộ khách sạn.
Trạng thái: ngoài phạm vi MVP M09, chỉ giữ chỗ trong cây config.
Sẽ được đặc tả và triển khai ở giai đoạn sau khi core routing/planning ổn định.


5. Core Architecture
Agent Request

    ↓

Request Validator

    ↓

Agent Router

    ↓

Persona Resolver

    ↓

Context Loader

    ↓

Missing Knowledge Detector

    ↓

Task Planner

    ↓

Risk Classifier

    ↓

Module Request Builder

    ↓

M04 Automation Bridge

    ↓

Result Aggregator

    ↓

Agent Response Renderer


6. Repository Structure
agent_studio/

├── __init__.py

├── request_validator.py

├── agent_router.py

├── persona_resolver.py

├── context_loader.py

├── missing_knowledge.py

├── task_planner.py

├── risk_classifier.py

├── module_request_builder.py

├── automation_bridge.py

├── result_aggregator.py

├── execution_log.py

├── cli.py

│

├── agents/

│   ├── base_agent.py

│   ├── research_agent.py

│   ├── documentation_agent.py

│   ├── content_planning_agent.py

│   ├── visual_planning_agent.py

│   └── analytics_insight_agent.py

│

├── schemas/

│   ├── agent_request.py

│   ├── agent_response.py

│   ├── persona.py

│   ├── task_plan.py

│   ├── module_request.py

│   ├── risk_assessment.py

│   └── execution_result.py

│

├── templates/

│   ├── base_persona.md

│   ├── research_agent.md

│   ├── documentation_agent.md

│   ├── content_planning_agent.md

│   ├── visual_planning_agent.md

│   └── analytics_insight_agent.md

│

├── renderers/

│   ├── response_markdown.py

│   └── response_json.py

│

└── tests/

    ├── fixtures/

    ├── test_request_validator.py

    ├── test_agent_router.py

    ├── test_persona_resolver.py

    ├── test_context_loader.py

    ├── test_missing_knowledge.py

    ├── test_task_planner.py

    ├── test_risk_classifier.py

    ├── test_module_request_builder.py

    ├── test_automation_bridge.py

    ├── test_result_aggregator.py

    ├── test_brand_display.py

    └── test_mock_agent_execution.py


7. Config Structure
config/

└── projects/

    └── venho_hotel/

        └── agents/

            ├── marketing_agent.yaml

            ├── linh_an_brand_agent.yaml

            ├── hotel_ops_agent.yaml        # post-MVP

            └── agent_policy.yaml

Ví dụ marketing_agent.yaml:

agent_id: venho_marketing_agent

display_name: "Ven Hồ Hotel Marketing Agent"

type: project_specific

base_agent: content_planning_agent

scope:

  - campaign_planning

  - content_strategy

  - analytics_interpretation

required_knowledge:

  - VENHO_BRAND_DNA

  - VENHO_CONTENT_PILLARS

  - VENHO_WESTLAKE_DNA

allowed_modules:

  - M01

  - M02

  - M03

  - M04

  - M05

  - M08

forbidden_actions:

  - direct_publish

  - delete_content

  - modify_knowledge_without_approval

validation_level: strict

approval_required_for:

  - publishing_request

  - content_strategy_change

  - knowledge_update

Ví dụ agent_policy.yaml (approval policy tập trung):

policy_version: "1.0"

project: venho_hotel

risk_approval_map:

  read_only: auto

  draft_creation: auto

  internal_file_write: config_dependent

  knowledge_update: require_approval

  external_impact: require_approval

  destructive_action: blocked

external_impact_actions:

  - publishing_request

  - send_email

  - update_public_content

  - change_campaign_strategy

default_execution_mode: plan_only

Ghi chú: allowed_modules không liệt kê M07. M09 không bao giờ gọi M07 trực tiếp; mọi yêu cầu publish đi qua M04.


8. Agent Request Contract
{

  "contract_version": "1.0",

  "project": "venho_hotel",

  "agent": "venho_marketing_agent",

  "goal": "Create weekly campaign for West Lake local experience",

  "context": {

    "knowledge_refs": [

      "VENHO_BRAND_DNA",

      "WESTLAKE_EXPERIENCE_DNA"

    ],

    "analytics_refs": [

      "latest_30d_advisory"

    ]

  },

  "constraints": {

    "language": "vi",

    "validation_level": "strict",

    "max_steps": 5,

    "allow_external_actions": false

  },

  "execution_mode": "plan_only",

  "use_mock_engine": false

}


9. Task Plan Contract
Ghi chú ranh giới: Các module bên dưới là mô tả kế hoạch nhận thức của M09. M09 không tự gọi trực tiếp M05/M06/M07. Khi thực thi, mọi task được đóng gói qua Module Request Builder và dispatch qua M04 Automation Bridge (xem task cuối cùng M04_AUTOMATION_STUDIO).

{

  "contract_version": "1.0",

  "plan_id": "plan_20260709_weekly_campaign",

  "project": "venho_hotel",

  "agent": "venho_marketing_agent",

  "goal": "Create weekly campaign for West Lake local experience",

  "tasks": [

    {

      "task_id": "task_001",

      "module": "M08_ANALYTICS_FEEDBACK",

      "action": "read_advisory",

      "input_refs": ["latest_30d_advisory"],

      "risk_level": "read_only",

      "approval_required": false

    },

    {

      "task_id": "task_002",

      "module": "M05_CONTENT_STUDIO",

      "action": "create_content_request",

      "input_refs": ["VENHO_BRAND_DNA", "WESTLAKE_EXPERIENCE_DNA"],

      "risk_level": "draft_creation",

      "approval_required": false

    },

    {

      "task_id": "task_003",

      "module": "M04_AUTOMATION_STUDIO",

      "action": "prepare_manual_gate",

      "input_refs": ["content_package"],

      "risk_level": "external_impact",

      "approval_required": true

    }

  ],

  "stop_conditions": [

    "missing_required_knowledge",

    "validator_fail",

    "approval_required"

  ]

}


10. Agent Response Contract
{

  "contract_version": "1.0",

  "agent_name": "venho_marketing_agent",

  "project": "venho_hotel",

  "status": "SUCCESS",

  "execution_mode": "plan_only",

  "confidence_score": 0.88,

  "knowledge_sources_used": [

    "VENHO_BRAND_DNA",

    "WESTLAKE_EXPERIENCE_DNA"

  ],

  "plan": {

    "plan_id": "plan_20260709_weekly_campaign",

    "tasks_count": 3,

    "approval_required": true

  },

  "module_requests": [

    {

      "target_module": "M05_CONTENT_STUDIO",

      "request_type": "content_request",

      "status": "prepared"

    }

  ],

  "validation_summary": {

    "required": true,

    "status": "pending"

  },

  "missing_knowledge": [],

  "risk_assessment": {

    "highest_risk": "external_impact",

    "manual_gate_required": true

  },

  "execution_log": [

    "Request validated",

    "Router dispatched to venho_marketing_agent",

    "Persona resolved",

    "Context loaded",

    "Task plan generated",

    "Manual approval required before publishing"

  ]

}


11. Risk Classification
M09 phải phân loại task theo risk.

read_only

draft_creation

internal_file_write

knowledge_update

external_impact

destructive_action
Quy tắc approval
read_only              → không cần approval

draft_creation         → không cần approval

internal_file_write    → có thể cần approval theo config

knowledge_update       → cần approval

external_impact        → cần approval

destructive_action     → blocked mặc định

Nguồn cấu hình chuẩn: config/projects/<project>/agents/agent_policy.yaml.


12. Guardrails
12.1 Missing Knowledge
Nếu thiếu tri thức bắt buộc:

{

  "status": "FAILED",

  "error_code": "ERR_MISSING_KNOWLEDGE",

  "missing_knowledge": [

    "VENHO_BRAND_DNA",

    "WESTLAKE_EXPERIENCE_DNA"

  ]

}
12.2 Zero Autonomous Publishing
Agent không được publish.

Nếu user yêu cầu:

Đăng bài này lên Facebook

Agent chỉ được:

Tạo publish request draft.
Đánh dấu external impact.
Gửi sang M04 Manual Gate.
Không gọi M07 trực tiếp nếu chưa qua M04.
12.3 No Direct Knowledge Mutation
Agent không tự sửa DNA/Knowledge.

Nếu cần:

Tạo Knowledge Update Proposal.
Gửi approval.
Sau approval mới có workflow riêng.
12.4 Brand Display Rule
Kết quả hiển thị phải dùng:

Ven Hồ Hotel

Không dùng:

Ven Ho Hotel

Trừ trường hợp technical slug, file name, repo name, domain, env key.
12.5 Max Step / Cost Control
Agent plan phải có:

max_steps
stop_conditions
execution_mode
approval gates

Không có vòng lặp mở.


13. Testing Discipline
13.1 Nguyên tắc
pytest không gọi OpenAI/Claude thật.
Không gọi API thật của module khác.
Không đọc secret thật.
Không phụ thuộc internet.
Mock AI client.
Mock module responses.
Fixture JSON cho request/response.
13.2 Không dùng target test count tuyệt đối
Không dùng:

387+ tests

Dùng:

100% M09 tests pass

0 real API call in pytest

Critical paths covered

Coverage đạt ngưỡng dự án
13.3 Critical paths cần test
Request validation
Agent routing
Persona resolving
Context loading
Missing knowledge detection
Task planning
Risk classification
Approval requirements
Module request building
Automation bridge
Result aggregation
Brand display rule
Mock AI behavior


14. CLI đề xuất
Plan only
venho agent --agent venho_marketing_agent --project venho_hotel --goal "Tạo campaign trải nghiệm mùa hè Hồ Tây" --plan-only
Execute via M04
venho agent --agent venho_marketing_agent --project venho_hotel --goal "Tạo campaign tuần này" --execute
Dry run
venho agent --agent venho_marketing_agent --project venho_hotel --goal "Tạo campaign tuần này" --dry-run
Explain plan
venho agent explain --plan-id plan_20260709_weekly_campaign


15. Output files
data/projects/<project>/agents/

├── plans/

├── responses/

├── logs/

└── proposals/

Ví dụ:

data/projects/venho_hotel/agents/plans/plan_20260709_weekly_campaign.json

data/projects/venho_hotel/agents/responses/response_20260709_weekly_campaign.md


16. Roadmap phát triển theo giai đoạn
Tổng: 27 step (Step 0 → Step 26) chia thành 7 phase. Thứ tự các component core tuân thủ đúng kiến trúc Mục 5: Request Validator → Agent Router → Persona Resolver → Context Loader → Missing Knowledge.
Phase 1 — Foundation & Contracts
Mục tiêu:

Tạo nền tảng Agent Core, schema, persona config và mock testing.
Step 0 — Module Scaffold
Tạo:

agent_studio/

agent_studio/agents/

agent_studio/schemas/

agent_studio/templates/

agent_studio/renderers/

agent_studio/tests/

config/projects/<project>/agents/

DoD:

Import module không lỗi.
Không ảnh hưởng module cũ.
Test skeleton chạy được.
Có README nội bộ.
Step 1 — Schemas & Contracts
Tạo:

schemas/agent_request.py

schemas/agent_response.py

schemas/persona.py

schemas/task_plan.py

schemas/module_request.py

schemas/risk_assessment.py

schemas/execution_result.py

DoD:

Validate được AgentRequest mẫu.
Validate được AgentResponse mẫu.
Validate được Persona mẫu.
Có contract_version.
Có execution_mode.
Có approval flags.
Step 2 — Base Agent Interface
Tạo:

agents/base_agent.py

DoD:

BaseAgent có interface chung.
Agent không tự gọi API ngoài.
Output theo AgentResponse contract.
Mock agent chạy offline.


Phase 2 — Request Handling, Routing & Context
Mục tiêu:

Kiểm tra request, định tuyến đúng persona và nạp tri thức an toàn.
Step 3 — Request Validator
Tạo:

request_validator.py

DoD:

Validate schema AgentRequest.
Từ chối request thiếu field bắt buộc (project, agent, goal).
Trả lỗi rõ ràng, có error_code.
Không side-effect, không gọi API.
Test bằng fixture request hợp lệ và không hợp lệ.
Step 4 — Agent Router
Tạo:

agent_router.py

DoD:

Route theo agent id.
Có fallback agent.
Sai agent trả lỗi rõ.
Test routing bằng fixture.
Step 5 — Persona Resolver
Tạo:

persona_resolver.py

DoD:

Đọc được project-specific persona config.
Không hard-code Ven Hồ.
Validate allowed_modules / forbidden_actions.
Fallback nếu persona thiếu.
Step 6 — Context Loader
Tạo:

context_loader.py

DoD:

Load được Knowledge refs.
Load được Analytics advisory refs.
Load được Prompt refs nếu cần.
Không bịa nếu thiếu file.
Step 7 — Missing Knowledge Detector
Tạo:

missing_knowledge.py

DoD:

Phát hiện thiếu required knowledge.
Trả ERR_MISSING_KNOWLEDGE.
Gợi ý cần bổ sung module nào.


Phase 3 — Planning & Risk Control
Mục tiêu:

Biến goal thành task plan có kiểm soát.
Step 8 — Task Planner
Tạo:

task_planner.py

DoD:

Goal → TaskPlan JSON.
Mỗi task có target module.
Có stop conditions.
Có max_steps.
Không loop vô hạn.
Step 9 — Risk Classifier
Tạo:

risk_classifier.py

DoD:

Phân loại risk level.
Đánh dấu approval_required (đọc theo agent_policy.yaml).
Destructive action bị block mặc định.
Test đủ risk cases.
Step 10 — Module Request Builder
Tạo:

module_request_builder.py

DoD:

Chuyển task plan thành request cho M04.
Không gọi trực tiếp M05/M06/M07 nếu phải qua M04.
Request có contract rõ.


Phase 4 — Automation Bridge & Result Aggregation
Mục tiêu:

Kết nối M09 với M04 và tổng hợp kết quả.
Step 11 — Automation Bridge
Tạo:

automation_bridge.py

DoD:

Gửi request sang M04.
Nhận execution result mock.
Respect approval gate.
Dry-run mode hoạt động.
Step 12 — Result Aggregator
Tạo:

result_aggregator.py

execution_log.py

DoD:

Gom kết quả từ M04.
Tạo AgentResponse.
Gắn validation summary.
Ghi execution log qua execution_log.py.
Step 13 — Renderers
Tạo:

renderers/response_markdown.py

renderers/response_json.py

DoD:

Xuất .md + .json.
Section markdown cố định.
JSON round-trip.


Phase 5 — Generic Agents
Mục tiêu:

Triển khai các agent lõi nhưng vẫn giữ ranh giới module.
Step 14 — Documentation Agent
Tạo:

agents/documentation_agent.py

templates/documentation_agent.md

DoD:

Tạo documentation plan.
Sinh doc request nếu cần.
Không hard-code project.
Step 15 — Research Agent
Tạo:

agents/research_agent.py

templates/research_agent.md

DoD:

Tạo research plan.
Nếu cần web/external data, đánh dấu external_research_required.
Không bịa nguồn.
Step 16 — Content Planning Agent
Tạo:

agents/content_planning_agent.py

templates/content_planning_agent.md

DoD:

Tạo ContentRequest cho M05.
Không tự viết final content.
Có validation requirement.
Step 17 — Visual Planning Agent
Tạo:

agents/visual_planning_agent.py

templates/visual_planning_agent.md

DoD:

Tạo request cho M01/M02/M03/M06.
Không tự phân tích ảnh ngoài pipeline.
Có DNA/Validator requirement.
Step 18 — Analytics Insight Agent
Tạo:

agents/analytics_insight_agent.py

templates/analytics_insight_agent.md

DoD:

Đọc M08 advisory.
Giải thích insight.
Tạo action plan.
Không tự tính metrics.


Phase 6 — Project Agents
Mục tiêu:

Tạo agent riêng cho Ven Hồ/Linh An bằng config, không hard-code core.
Step 19 — Base Persona Template
Tạo:

templates/base_persona.md

DoD:

Có đủ field tối thiểu: role, scope, allowed_modules, forbidden_actions, required_knowledge.
Không chứa tri thức cứng.
Là chuẩn kế thừa cho mọi persona.
Step 20 — Agent Policy Config
Tạo:

config/projects/venho_hotel/agents/agent_policy.yaml

DoD:

Định nghĩa risk_approval_map đầy đủ 6 mức risk.
Liệt kê external_impact_actions.
Risk classifier đọc được policy này.
Destructive action mặc định blocked.
Step 21 — Ven Hồ Hotel Marketing Agent Config
Tạo:

config/projects/venho_hotel/agents/marketing_agent.yaml

DoD:

Persona config hợp lệ.
Required knowledge rõ.
Allowed modules rõ (không có M07).
Approval rules rõ.
Step 22 — Linh An Brand Agent Config
Tạo:

config/projects/venho_hotel/agents/linh_an_brand_agent.yaml

DoD:

Dùng Character DNA / Face Lock refs.
External visual/video actions yêu cầu Validator.
Không tạo identity-breaking output.
Step 23 — Project Agent Acceptance
Test:

Goal: Tạo campaign trải nghiệm mùa hè Hồ Tây

Agent: Ven Hồ Hotel Marketing Agent

Mode: plan_only

DoD:

Route đúng agent.
Load đúng Knowledge.
Tạo TaskPlan.
Không publish.
Approval gate được đánh dấu.

Ghi chú: hotel_ops_agent.yaml là post-MVP, không nằm trong phạm vi Phase 6 MVP.


Phase 7 — CLI & E2E Dry Run
Mục tiêu:

Đóng gói thành công cụ dùng được.
Step 24 — CLI
Tạo:

cli.py

DoD:

venho agent chạy được.
Có --plan-only.
Có --execute.
Có --dry-run.
Có explain.
Step 25 — E2E Dry Run
Test:

User goal

↓

Request Validator

↓

Agent Router

↓

Persona Resolver

↓

Context Loader

↓

Task Planner

↓

Risk Classifier

↓

M04 mock bridge

↓

Agent Response

DoD:

Không API thật.
Không publish.
Không sửa Knowledge.
Response đúng .md + .json.
Step 26 — MVP Acceptance
Kịch bản:

Ven Hồ Marketing Agent tạo weekly campaign plan từ Knowledge + Analytics Advisory.

DoD:

Missing knowledge được xử lý đúng.
Plan rõ ràng.
Có module requests.
Có approval requirements.
Output đọc được.
Test pass offline.


17. Definition of Done tổng thể
M09 hoàn thành khi:

Agent Request/Response contracts ổn định.
Request validator hoạt động.
Agent router hoạt động.
Persona resolver hoạt động.
Context loader hoạt động.
Missing knowledge detector hoạt động.
Task planner tạo TaskPlan JSON.
Risk classifier hoạt động (đọc agent_policy.yaml).
Module request builder đóng gói request cho M04.
Automation bridge kết nối M04.
Result aggregator xuất response (kèm execution log).
Renderers xuất .md + .json.
Generic agents hoạt động ở mức plan/request.
Project agents cấu hình được.
CLI chạy được.
Không API thật trong pytest.
Không hard-code Ven Hồ trong core.
Không tự publish.
Không tự sửa Knowledge.
Không bypass M04 Automation.
Không chứa vòng lặp tự trị vô hạn.


18. Rủi ro chính và cách xử lý
Rủi ro 1 — Agent tự trị quá mức
Cách xử lý:

max_steps.
stop_conditions.
no infinite loop.
M04 executes, M09 plans.
Rủi ro 2 — Agent bypass module boundary
Cách xử lý:

M09 không gọi M07 publish trực tiếp.
M09 không tạo content final ngoài M05.
M09 không tự validate ngoài M03.
Rủi ro 3 — Hallucination
Cách xử lý:

Required knowledge.
Missing knowledge detector.
Source references in output.
Rủi ro 4 — Project logic hard-coded
Cách xử lý:

Persona config.
Project-specific YAML.
Core project-agnostic.
Rủi ro 5 — Test gọi API thật
Cách xử lý:

Mock AI client.
Mock M04 bridge.
Offline fixtures.
No secrets in CI.
Rủi ro 6 — Agent tạo action nguy hiểm
Cách xử lý:

Risk classifier.
Approval gates.
Destructive actions blocked by default.


19. Thứ tự ưu tiên triển khai
Ưu tiên thực tế (đồng bộ với roadmap Mục 16, theo đúng thứ tự phụ thuộc):

1.  Schemas & Contracts

2.  Base Agent

3.  Request Validator

4.  Agent Router

5.  Persona Resolver

6.  Context Loader

7.  Missing Knowledge Detector

8.  Task Planner

9.  Risk Classifier

10. Module Request Builder

11. Automation Bridge

12. Result Aggregator (+ execution log)

13. Renderers

14. Documentation Agent

15. Research Agent

16. Content Planning Agent

17. Visual Planning Agent

18. Analytics Insight Agent

19. Base Persona Template

20. Agent Policy Config

21. Ven Hồ Marketing Agent config

22. Linh An Brand Agent config

23. CLI

24. E2E Dry Run

25. MVP Acceptance

Không triển khai project-specific agents trước khi core routing/context/planning ổn định.


20. Quan hệ với kiến trúc module mới
Kiến trúc hiện tại:

M01 — Knowledge Studio

M02 — Prompt Studio

M03 — Validator Studio

M04 — Automation Studio

M05 — Content Studio

M06 — Video Studio

M07 — Publishing Gateway

M08 — Analytics Feedback

M09 — Agent Studio

M09 là lớp điều phối nhận thức phía trên các module, nhưng không thay thế chúng.

M09 không phải Automation.

M09 không phải Publishing.

M09 không phải Analytics.

M09 là lớp giúp người dùng ra lệnh bằng mục tiêu tự nhiên và biến mục tiêu đó thành kế hoạch module-safe.


21. Kết luận
Agent Studio là lớp giao diện tư duy của VENHO AI Studio.

Nó giúp Founder không cần gọi từng module thủ công, nhưng vẫn giữ được ranh giới kiến trúc:

Agent hiểu mục tiêu

↓

Agent lập kế hoạch

↓

Automation thực thi

↓

Validator kiểm tra

↓

Publishing xuất bản nếu được duyệt

↓

Analytics phản hồi

Điểm quan trọng nhất của M09 là không biến Agent thành hệ thống tự trị nguy hiểm.

M09 phải được xây như một lớp lập kế hoạch có kiểm soát, dựa trên Knowledge, có approval gate và tôn trọng mọi module boundary.

END OF DOCUMENT

