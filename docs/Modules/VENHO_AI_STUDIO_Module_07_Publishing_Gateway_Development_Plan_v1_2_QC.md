VENHO AI STUDIO
Module 07 — Publishing Gateway Development Plan v1.2 QC
Workspace mẹ: THE WEST LAKE LIVING Repo: venho-ai-studio Module: publishing_gateway/ Module ID: M07 Vị trí: Sau M06 Video Studio, trước M08 Analytics Feedback Trạng thái: QC Consolidated Plan — Final Nguồn review: VENHO_AI_STUDIO_Module_07_Publishing_Gateway_Development_Plan_v1_1_QC.md Nguyên tắc cập nhật: M07 là lớp phân phối/xuất bản, không phải Agent Studio. Agent Studio được chuyển sang M09.


0. Kết luận QC
Bản M07 Publishing Gateway đã đi đúng hướng: nó xác định rõ M07 là lớp phân phối và xuất bản qua API, có guardrail, idempotency, queue, circuit breaker, delivery receipt và kỷ luật test offline 0 API call.

Ba nhóm lỗi gốc đã được xử lý dứt điểm trong dòng phiên bản QC này:

Lỗi quy ước thử nghiệm — bỏ mục tiêu số test tuyệt đối (410+), thay bằng quy ước chất lượng (100% test pass, 0 real API call, coverage đạt ngưỡng dự án, critical paths có test). Xem mục 11.
Lỗi xâm phạm ranh giới module — M07 không sáng tạo nội dung, không tạo hashtag/metadata, không quyết định publish, không phân tích performance, không chứa logic Agent. Xem mục 2.
Lỗi đánh số thứ tự — chuẩn hóa lại toàn bộ số thứ tự bước (Step 0–21), đồng bộ giữa roadmap (mục 13), thứ tự ưu tiên (mục 16) và thứ tự bắt buộc (mục 18). Xem mục 0.1.


0.1 Changelog v1.2 — Lỗi phát hiện thêm và cách xử lý
Đây là các lỗi còn sót sau v1.1, được phát hiện trong lần QC này và đã sửa:

#
Lỗi phát hiện
Vị trí cũ
Cách xử lý trong v1.2
E1
receipt_store.py bị tạo hai lần (một lần ở Step Idempotency, một lần ở Step Receipt Generator) — mâu thuẫn "ai sở hữu file".
Step 6 và Step 15 (v1.1)
Tách rõ: receipt_store.py được tạo một lần ở Step Idempotency & Receipt Store (persistence + nguồn idempotency). Step Delivery Receipt Generator chỉ tạo renderers và dùng lại store, không tạo lại.
E2
Thứ tự ưu tiên (mục 16) đặt Receipt trước Adapter, mâu thuẫn thứ tự bắt buộc (mục 18) vốn đặt Receipt sau Adapter.
Mục 16 (v1.1)
Viết lại mục 16 khớp mục 18: receipt_store (persistence) sớm; receipt generator/renderers đứng sau adapters. Phân biệt rõ store và generator.
E3
Nhiều file trong repo structure không có step nào tạo chúng: platform_capabilities.py, token_vault.py, exceptions.py, utils/url_checker.py, utils/time_utils.py.
Mục 6 vs 13 (v1.1)
Bổ sung Step riêng cho Platform Capability Registry và Token Vault; gộp exceptions.py vào Step 0, url_checker.py vào Contract Validator, time_utils.py vào Approval Verifier. Nay 100% file có step.
E4
scheduling xuất hiện trong contract (mục 8) và schedule_policy.yaml (mục 7) nhưng không có step nào hiện thực, và mơ hồ ranh giới ("M07 tự quyết định giờ?").
Mục 7, 8 (v1.1)
Làm rõ ranh giới: M07 không quyết định giờ, chỉ thực thi scheduled_time_utc đã được M04 duyệt sẵn. MVP mặc định publish_now; scheduled-execution là tùy chọn hậu-MVP. Xem mục 4.4.
E5
Mục 4.1 liệt kê cả 4 nền tảng là MVP, nhưng platforms.yaml mẫu để threads và google_business = enabled: false, và DoD lại nói "feature-flag off nếu chưa đủ API access" → không nhất quán.
Mục 4.1, 7, 14 (v1.1)
Phân tầng rõ: Core MVP = Facebook + Instagram (bắt buộc ship). Conditional MVP = Threads + Google Business Profile (ship nếu có API access, nếu không thì feature-flag off). Đồng bộ mọi mục.



1. Vai trò chính thức của M07
Publishing Gateway là lớp Distribution & Delivery Layer của VENHO AI Studio.

Nó nhận gói nội dung đã hoàn thiện và đã được duyệt từ các module trước, sau đó thực thi việc phân phối qua API đến các nền tảng xuất bản.

M05 Content Studio / M06 Video Studio

        ↓

M03 Validator Studio

        ↓

M04 Automation Studio + Manual Approval Gate

        ↓

M07 Publishing Gateway

        ↓

Facebook / Instagram / Threads / Google Business Profile / Future APIs

        ↓

Delivery Receipt

        ↓

M08 Analytics Feedback

M07 là cổng xuất bản, không phải bộ não sáng tạo.


2. Ranh giới module
2.1 M07 được phép làm
Nhận package đã được duyệt.
Kiểm tra approval signature từ M04.
Kiểm tra package contract.
Kiểm tra platform capability.
Kiểm tra brand display rule cuối cùng (static check).
Đưa package vào queue.
Thực thi scheduled_time_utc đã được duyệt sẵn (nếu có).
Gọi API xuất bản.
Retry theo chính sách.
Circuit breaker khi nền tảng lỗi.
Tạo delivery receipt.
Ghi log.
Gửi receipt cho M08 Analytics Feedback.
2.2 M07 không được làm
Không viết lại caption.
Không chỉnh tone.
Không tạo hashtag.
Không tạo metadata sáng tạo.
Không tự tạo ảnh/video.
Không tự quyết định thời điểm publish; chỉ thực thi thời điểm đã được M04 duyệt.
Không tự quyết định publish nếu chưa có approval.
Không phân tích hiệu quả bài đăng.
Không tự đổi giá phòng / tồn kho / chính sách OTA.
Không chứa logic Agent.
Không hard-code Ven Hồ vào core.


3. Dependency chính thức
3.1 Input upstream
M07 nhận input trực tiếp từ:

M04 Automation Studio

M04 là module chịu trách nhiệm điều phối và cấp approval.

Package có thể chứa asset từ:

M05 Content Studio

M06 Video Studio

M02 Prompt Studio

M01 Knowledge Studio

Nhưng M07 không gọi trực tiếp các module này để tạo mới content. Metadata/hashtags/caption luôn đã nằm sẵn trong package đã duyệt; M07 không sinh và không lấy từ M09 Agent Studio.
3.2 Output downstream
M07 xuất output cho:

M08 Analytics Feedback

M08 sẽ dùng delivery receipt để theo dõi performance. M07 chỉ trả receipt, status, platform IDs, URL, error log — không tự phân tích performance.


4. Các nền tảng xuất bản
4.1 Core MVP Platforms (bắt buộc ship)
Facebook Page
Instagram Business
4.2 Conditional MVP Platforms (ship nếu có API access, nếu không thì feature-flag off)
Threads
Google Business Profile

Trong platforms.yaml, hai nền tảng Conditional mặc định enabled: false cho tới khi có đủ API access, và được bật qua feature flag. Adapter của chúng vẫn phải có mock test offline dù chưa bật production.
4.3 Extended Platforms (sau MVP)
YouTube Shorts
TikTok
LinkedIn Page
OTA content update APIs
Website CMS
Email campaign provider
4.4 Scheduling scope (làm rõ ranh giới)
M07 không quyết định giờ đăng. Quyết định lịch thuộc M04.
Nếu publish_now = true → M07 publish ngay sau khi qua guardrail.
Nếu có scheduled_time_utc đã được duyệt → M07 giữ job trong queue và thực thi đúng giờ đó (đây là tính năng tùy chọn hậu-MVP; MVP mặc định chỉ hỗ trợ publish_now).
schedule_policy.yaml chỉ định cửa sổ thực thi được phép và giới hạn tần suất, không định nghĩa quyết định nội dung/giờ sáng tạo.
4.5 OTA Guardrail
OTA Bridge nếu triển khai sau này chỉ được phép:

Cập nhật mô tả tĩnh.
Cập nhật ảnh đã duyệt.
Cập nhật thông tin tiện ích nếu có approval.

Không được phép:

Tự đổi giá phòng.
Tự đổi tồn kho.
Tự đổi chính sách hủy phòng.
Tự bật/tắt phòng bán.


5. Kiến trúc tổng thể M07
Publishing Request

        ↓

Contract Validator

        ↓

Approval Verifier

        ↓

Brand Display Static Check

        ↓

Platform Capability Check

        ↓

Gateway Router

        ↓

Publisher Queue

        ↓

Platform Adapter Registry

        ├── Facebook Adapter

        ├── Instagram Adapter

        ├── Threads Adapter

        └── Google Business Profile Adapter

        ↓

API Response Normalizer

        ↓

Delivery Receipt Generator

        ↓

Receipt Store

        ↓

M08 Analytics Feedback


6. Cấu trúc repo đề xuất
Mỗi file dưới đây được ánh xạ tới đúng một Step tạo ra nó (xem mục 13, cột "Tạo").

publishing_gateway/

├── __init__.py                 # Step 0

├── gateway_router.py           # Step 16

├── contract_validator.py       # Step 4

├── approval_verifier.py        # Step 3

├── brand_guard.py              # Step 5

├── platform_capabilities.py    # Step 6

├── publisher_queue.py          # Step 8

├── circuit_breaker.py          # Step 9

├── token_vault.py              # Step 11

├── receipt_store.py            # Step 7  (tạo 1 lần; Step 17 chỉ dùng lại)

├── exceptions.py               # Step 0

├── cli.py                      # Step 19

│

├── adapters/

│   ├── base_adapter.py         # Step 2

│   ├── facebook.py             # Step 12

│   ├── instagram.py            # Step 13

│   ├── threads.py              # Step 14

│   ├── google_business.py      # Step 15

│   └── mock_adapter.py         # Step 2

│

├── schemas/

│   ├── publishing_request.py   # Step 1

│   ├── delivery_receipt.py     # Step 1

│   ├── platform_result.py      # Step 1

│   └── approval.py             # Step 1

│

├── utils/

│   ├── media_uploader.py       # Step 13

│   ├── idempotency.py          # Step 7

│   ├── url_checker.py          # Step 4

│   └── time_utils.py           # Step 3

│

├── renderers/

│   ├── receipt_markdown.py     # Step 17

│   └── receipt_json.py         # Step 17

│

└── tests/

    ├── fixtures/

    ├── test_contract_validator.py

    ├── test_approval_verifier.py

    ├── test_idempotency.py

    ├── test_circuit_breaker.py

    └── test_mock_adapters.py


7. Config đề xuất
config/

└── projects/

    └── venho_hotel/

        └── publishing/

            ├── platforms.yaml

            ├── brand_display_rules.yaml

            ├── approval_policy.yaml

            ├── schedule_policy.yaml

            └── rate_limits.yaml

Ví dụ platforms.yaml:

project: venho_hotel

platforms:

  facebook:            # Core MVP

    enabled: true

    adapter: facebook

    page_id_env: VENHO_FB_PAGE_ID

    token_env: VENHO_META_ACCESS_TOKEN

  instagram:           # Core MVP

    enabled: true

    adapter: instagram

    ig_business_id_env: VENHO_IG_BUSINESS_ID

    token_env: VENHO_META_ACCESS_TOKEN

  threads:             # Conditional MVP — bật khi có API access

    enabled: false

    adapter: threads

  google_business:     # Conditional MVP — bật khi có API access

    enabled: false

    adapter: google_business

Ví dụ approval_policy.yaml:

require_manual_approval: true

require_validator_pass: true

accepted_statuses:

  - approved

approval_signature_algorithm: hmac_sha256

approval_ttl_minutes: 120

Ví dụ brand_display_rules.yaml:

blocked_display_terms:

  - "Ven Ho Hotel"

required_display_name:

  - "Ven Hồ Hotel"

error_code: "ERR_BRAND_DISPLAY_VIOLATION"

Ví dụ schedule_policy.yaml (chỉ quản lý cửa sổ thực thi, không quyết định nội dung):

allow_scheduled_execution: false   # MVP mặc định chỉ publish_now

allowed_execution_windows_utc:

  - start: "00:00"

    end: "23:59"

max_hold_minutes: 1440


8. Publishing Request Contract
{

  "contract_version": "1.0",

  "package_id": "pkg_20260709_westlake_sunset",

  "project": "venho_hotel",

  "package_status": "approved",

  "approval": {

    "approved_by": "manual_gate",

    "approved_at": "2026-07-09T03:55:00Z",

    "approval_signature": "hmac_sha256_signature_from_m04"

  },

  "platforms": ["facebook", "instagram"],

  "content": {

    "text_prose": "Trải nghiệm hoàng hôn bên Hồ Tây tại Ven Hồ Hotel...",

    "hashtags": ["#VenHoHotel", "#HoTay", "#Sunset"],

    "media_urls": [

      "https://storage.venho.ai/media/video_m06_final_304.mp4"

    ],

    "media_type": "video"

  },

  "scheduling": {

    "publish_now": true,

    "scheduled_time_utc": null

  },

  "idempotency_key": "sha256_package_project_platforms_content_schedule"

}

Ghi chú ranh giới: content.hashtags và content.text_prose là dữ liệu nhận vào đã duyệt. M07 không sinh, không sửa. scheduling chỉ được M07 thực thi, không quyết định (xem mục 4.4).


9. Delivery Receipt Contract
{

  "contract_version": "1.0",

  "package_id": "pkg_20260709_westlake_sunset",

  "project": "venho_hotel",

  "overall_status": "PARTIAL_SUCCESS",

  "published_timestamp": "2026-07-09T04:00:05Z",

  "idempotency_key": "sha256_package_project_platforms_content_schedule",

  "platform_results": {

    "facebook": {

      "success": true,

      "status": "PUBLISHED",

      "post_id": "fb_page_post_983274892374",

      "public_url": "https://facebook.com/venhohotel/posts/983274892374",

      "error_code": null,

      "error_message": null

    },

    "instagram": {

      "success": false,

      "status": "FAILED",

      "post_id": null,

      "public_url": null,

      "error_code": "RATE_LIMIT",

      "error_message": "Instagram API rate limit reached"

    }

  },

  "circuit_breaker": {

    "triggered": false,

    "platform": null,

    "state": "CLOSED"

  },

  "analytics_handoff": {

    "ready_for_m08": true,

    "tracking_started_at": "2026-07-09T04:00:05Z"

  }

}


10. Guardrails
10.1 Approval Verification
M07 chỉ publish nếu:

package_status = approved
approval_signature hợp lệ (HMAC-SHA256)
approval chưa hết hạn
package chưa từng publish thành công với cùng idempotency key

Nếu sai:

ERR_APPROVAL_REQUIRED

ERR_APPROVAL_INVALID

ERR_APPROVAL_EXPIRED

ERR_DUPLICATE_PUBLISH
10.2 Brand Display Rule
M07 chạy static check cuối cùng (chỉ kiểm tra, không sửa nội dung).

Ví dụ:

Nếu text hiển thị chứa "Ven Ho Hotel" thay vì "Ven Hồ Hotel" → block.
Nếu thiếu tên thương hiệu bắt buộc trong campaign cần brand mention → warning hoặc fail theo config.
10.3 Idempotency
Mỗi idempotency_key chỉ được publish thành công một lần cho cùng platform.

Nếu retry:

Nếu platform đã success → không đăng lại.
Nếu platform failed → có thể retry riêng platform đó.
Nếu partial success → chỉ retry phần failed.
10.4 Circuit Breaker
Trạng thái:

CLOSED → HALF_OPEN → OPEN

Quy tắc mặc định:

3 lỗi liên tiếp cùng platform → OPEN.
OPEN thì ngừng gửi platform đó.
Sau cooldown → HALF_OPEN.
Một request test pass → CLOSED.
10.5 Dry Run Mode
M07 phải hỗ trợ:

venho publish --dry-run

Dry run kiểm tra:

Contract
Approval
Brand guard
Platform capability
Media URLs
Queue plan

Nhưng không gọi API thật.
10.6 Sandbox/Test Mode
Dùng khi cần test với API thật nhưng không publish public.

Tuỳ khả năng từng platform.

Nếu platform không hỗ trợ sandbox đầy đủ, phải ghi rõ trong config và docs.


11. Kỷ luật kiểm thử
11.1 Nguyên tắc
pytest không được gọi API thật.
Không đọc secret thật trong test.
Không phụ thuộc internet.
Adapter thật phải được bọc qua interface.
Mock adapter trả response tất định.
Fixture dùng local JSON.
11.2 Không dùng target test count tuyệt đối
Không đặt mục tiêu kiểu:

410+ tests

Thay bằng:

100% test M07 pass

0 real API call in pytest

Coverage đạt ngưỡng dự án

Critical paths có unit test
11.3 Critical paths phải test
Contract validation
Approval verification
Idempotency
Brand guard
Platform capability check
Queue retry
Circuit breaker
Rate limit
Partial success
Receipt generation
Mock adapter behavior
Dry run


12. CLI đề xuất
Publish package
venho publish --package-id pkg_20260709_westlake_sunset --platforms facebook,instagram
Dry run
venho publish --package-id pkg_20260709_westlake_sunset --platforms facebook,instagram --dry-run
Retry failed platform
venho publish retry --package-id pkg_20260709_westlake_sunset --platform instagram
Show receipt
venho publish receipt --package-id pkg_20260709_westlake_sunset
Queue status
venho publish queue status


13. Roadmap phát triển theo giai đoạn
Số thứ tự bước (Step 0–21) là liên tục và duy nhất, đồng bộ với thứ tự ưu tiên (mục 16) và thứ tự bắt buộc (mục 18).
Phase 1 — Foundation & Contracts
Mục tiêu: Tạo nền tảng module, schema, adapter interface và test offline.
Step 0 — Module Scaffold
Tạo:

publishing_gateway/

publishing_gateway/__init__.py

publishing_gateway/exceptions.py

publishing_gateway/adapters/

publishing_gateway/schemas/

publishing_gateway/utils/

publishing_gateway/renderers/

publishing_gateway/tests/

config/projects/<project>/publishing/

DoD:

Import module không lỗi.
Không ảnh hưởng module cũ.
Test skeleton chạy được.
exceptions.py định nghĩa các error code cơ bản.
Có README nội bộ.
Step 1 — Schemas & Contracts
Tạo:

schemas/publishing_request.py

schemas/delivery_receipt.py

schemas/platform_result.py

schemas/approval.py

DoD:

Validate được publishing request mẫu.
Validate được delivery receipt mẫu.
Có contract_version.
Có idempotency key.
Có approval object.
Step 2 — Base Adapter Interface + Mock Adapter
Tạo:

adapters/base_adapter.py

adapters/mock_adapter.py

DoD:

Mọi adapter có chung hàm publish().
Mọi adapter trả PlatformResult.
Mock adapter chạy offline.
Không API call thật trong test.


Phase 2 — Safety Layer
Mục tiêu: Xây guardrail trước khi gọi API thật.
Step 3 — Approval Verifier
Tạo:

approval_verifier.py

utils/time_utils.py

DoD:

Verify được approval signature (HMAC-SHA256).
Reject approval thiếu/sai/hết hạn (dùng time_utils cho TTL).
Test đủ case pass/fail.
Không publish nếu approval invalid.
Step 4 — Contract Validator
Tạo:

contract_validator.py

utils/url_checker.py

DoD:

Kiểm tra required fields.
Kiểm tra platform enabled.
Kiểm tra media URLs hợp lệ về format (dùng url_checker).
Không sửa nội dung.
Step 5 — Brand Guard
Tạo:

brand_guard.py

DoD:

Block được "Ven Ho Hotel" nếu config yêu cầu "Ven Hồ Hotel".
Trả ERR_BRAND_DISPLAY_VIOLATION.
Test bằng fixture offline.
Step 6 — Platform Capability Registry
Tạo:

platform_capabilities.py

DoD:

Khai báo capability từng platform (media type, độ dài text, số ảnh, reel/carousel...).
Reject request vượt capability trước khi vào queue.
Test bằng fixture offline, không gọi API.
Step 7 — Idempotency & Receipt Store
Tạo:

utils/idempotency.py

receipt_store.py

DoD:

idempotency.py sinh và so khớp idempotency key tất định.
receipt_store.py là nguồn sự thật persistence: lưu publish record + delivery receipt (Step 17 chỉ dùng lại, không tạo lại file này).
Cùng idempotency key không publish lại platform đã success.
Partial success chỉ retry failed platform.
Có test deterministic.


Phase 3 — Queue & Reliability
Mục tiêu: Đảm bảo publish an toàn, không spam, không lặp vô hạn.
Step 8 — Publisher Queue
Tạo:

publisher_queue.py

DoD:

Queue nhận job.
Retry theo policy.
Failed job không giết queue.
Có status job.
Step 9 — Circuit Breaker
Tạo:

circuit_breaker.py

DoD:

3 lỗi liên tiếp → OPEN.
Cooldown → HALF_OPEN.
Test pass → CLOSED.
Platform khác không bị ảnh hưởng.
Step 10 — Rate Limit Policy
Tạo hoặc cấu hình:

config/projects/<project>/publishing/rate_limits.yaml

DoD:

Adapter/queue đọc được rate limit config.
Queue không gửi vượt giới hạn config.
Test bằng mock clock nếu cần.
Step 11 — Token Vault & Secrets
Tạo:

token_vault.py

DoD:

Đọc token từ environment variables, không commit secret.
Refresh logic khi token hết hạn (nếu platform hỗ trợ).
Trả clear error khi token invalid (ERR_TOKEN_INVALID).
Test dùng token giả offline, không đọc secret thật.


Phase 4 — Platform Adapter MVP
Mục tiêu: Hiện thực adapter nền tảng chính, nhưng vẫn giữ test offline.
Step 12 — Facebook Adapter (Core MVP)
Tạo:

adapters/facebook.py

DoD:

Map request sang payload Facebook.
Mock response thành PlatformResult.
Không chứa logic content generation.
Có dry-run output.
Step 13 — Instagram Adapter (Core MVP)
Tạo:

adapters/instagram.py

utils/media_uploader.py

DoD:

Hỗ trợ image / carousel / reel package.
Chunk upload có integrity check.
Mock upload hoạt động offline.
Step 14 — Threads Adapter (Conditional MVP)
Tạo:

adapters/threads.py

DoD:

Map text thread.
Validate length/platform constraints.
Mock response pass (kể cả khi production feature-flag off).
Step 15 — Google Business Profile Adapter (Conditional MVP)
Tạo:

adapters/google_business.py

DoD:

Map local update payload.
Handle lỗi location verification.
Mock response pass (kể cả khi production feature-flag off).


Phase 5 — Router, Receipt & M08 Handoff
Mục tiêu: Hoàn thiện luồng thực thi và trả receipt cho Analytics Feedback.
Step 16 — Gateway Router
Tạo:

gateway_router.py

DoD:

Nhận publishing request.
Chạy chuỗi guardrail (contract → approval → brand → capability).
Chọn adapter theo platform, chia payload theo platform.
Đẩy job qua queue + circuit breaker.
Trả kết quả tổng hợp.
Step 17 — Delivery Receipt Generator
Tạo:

renderers/receipt_json.py

renderers/receipt_markdown.py

Dùng lại: receipt_store.py (đã tạo ở Step 7).

DoD:

Sinh receipt JSON đúng contract.
Sinh receipt Markdown để người đọc.
Ghi đủ platform results vào receipt_store.
analytics_handoff.ready_for_m08 = true.
Step 18 — M08 Handoff Contract
Tạo docs:

docs/contracts/m07_to_m08_delivery_receipt.md

DoD:

M08 có thể đọc receipt.
Không cần M08 gọi ngược M07 để hiểu bài đã publish.
Receipt có post_id/public_url/status/timestamp.


Phase 6 — CLI & Acceptance
Mục tiêu: Đóng gói thành công cụ chạy được.
Step 19 — CLI
Tạo:

cli.py

DoD:

venho publish chạy được.
Có --dry-run.
Có retry.
Có receipt view.
Có queue status.
Step 20 — End-to-End Dry Run
Test:

Approved package fixture

↓

M07 validate (contract → approval → brand → capability)

↓

dry-run route

↓

mock adapters

↓

receipt

DoD:

Không API thật.
Receipt đúng.
Partial success xử lý đúng.
Duplicate publish bị chặn.
Step 21 — Controlled Real API Test
Chỉ chạy thủ công, không chạy trong pytest.

DoD:

Dùng test page/account nếu có.
Secret lấy từ environment (qua token vault).
Có checklist trước khi chạy.
Có rollback/cancel instruction nếu platform hỗ trợ.


14. Definition of Done tổng thể
M07 hoàn thành khi:

Schema input/output ổn định.
Approval verifier hoạt động.
Contract validator hoạt động.
Brand guard hoạt động.
Platform capability registry hoạt động.
Idempotency hoạt động.
Token vault hoạt động (secret từ environment).
Queue hoạt động.
Circuit breaker hoạt động.
Rate limit hoạt động.
Mock adapters pass.
Facebook adapter (Core MVP) sẵn sàng.
Instagram adapter (Core MVP) sẵn sàng.
Threads adapter (Conditional MVP) sẵn sàng hoặc feature-flag off nếu chưa đủ API access.
Google Business Profile adapter (Conditional MVP) sẵn sàng hoặc feature-flag off nếu chưa đủ API access.
Gateway router hoạt động.
Delivery receipt sinh đúng contract.
M08 handoff rõ ràng.
CLI chạy được.
Dry-run mode chạy được.
pytest không gọi API thật.
Không hard-code Ven Hồ vào core.
Không chứa logic sáng tạo nội dung.
Không tự publish nếu thiếu approval.
Không tự quyết định thời điểm publish.


15. Rủi ro chính và cách xử lý
Rủi ro 1 — Xâm phạm ranh giới module
Biểu hiện:

M07 sửa caption.
M07 tạo hashtags.
M07 quyết định publish hoặc quyết định giờ đăng.

Cách xử lý:

M07 chỉ nhận package approved.
Không builder content trong M07.
Không AI generation trong M07.
Chỉ thực thi scheduled_time_utc đã được M04 duyệt.
Rủi ro 2 — Đăng trùng bài
Cách xử lý:

Idempotency key.
Receipt store.
Retry only failed platform.
Rủi ro 3 — API lỗi làm treo pipeline
Cách xử lý:

Queue isolation.
Circuit breaker.
Retry policy.
Partial success receipt.
Rủi ro 4 — Test vô tình gọi API thật
Cách xử lý:

Mock adapter mặc định trong test.
CI không có secret thật.
Network call guard nếu cần.
pytest offline.
Rủi ro 5 — Sai tên thương hiệu khi publish
Cách xử lý:

Brand guard static scan.
Project config.
Error code rõ ràng.
Rủi ro 6 — Token lộ hoặc hết hạn
Cách xử lý:

Token vault (Step 11).
Environment variables.
Không commit secret.
Refresh logic.
Clear error khi token invalid.
Rủi ro 7 — API platform thay đổi
Cách xử lý:

Adapter boundary.
Contract tests.
Platform capability config.
Feature flags.


16. Thứ tự ưu tiên triển khai
Thứ tự ưu tiên dưới đây khớp với roadmap (mục 13) và thứ tự bắt buộc (mục 18). Lưu ý phân biệt receipt store (persistence, làm sớm) và receipt generator (renderers, làm sau adapters):

1.  Schemas & Contracts            (Step 1)

2.  Base + Mock Adapter            (Step 2)

3.  Approval Verifier              (Step 3)

4.  Contract Validator             (Step 4)

5.  Brand Guard                    (Step 5)

6.  Platform Capability Registry   (Step 6)

7.  Idempotency & Receipt Store    (Step 7)

8.  Publisher Queue                (Step 8)

9.  Circuit Breaker                (Step 9)

10. Rate Limit Policy              (Step 10)

11. Token Vault                    (Step 11)

12. Facebook Adapter               (Step 12)

13. Instagram Adapter              (Step 13)

14. Threads / Google Business      (Step 14–15, conditional)

15. Gateway Router                 (Step 16)

16. Delivery Receipt Generator     (Step 17)

17. M08 Handoff Contract           (Step 18)

18. CLI                            (Step 19)

19. Dry-run E2E                    (Step 20)

20. Controlled real API test       (Step 21)

Không viết adapter API thật trước khi safety layer xong.


17. Quan hệ với kiến trúc module mới
Kiến trúc đã chỉnh:

M01 — Knowledge Studio

M02 — Prompt Studio

M03 — Validator Studio

M04 — Automation Studio

M05 — Content Studio

M06 — Video Studio

M07 — Publishing Gateway

M08 — Analytics Feedback

M09 — Agent Studio

M07 nằm giữa Automation và Analytics.

Nó không phải Dashboard.

Nó không phải Agent.

Nó là cổng xuất bản an toàn.


18. Kết luận
Publishing Gateway là module nguy hiểm nhất về mặt vận hành vì nó là nơi đầu tiên đưa output AI ra Internet công cộng.

Vì vậy, M07 phải được xây theo thứ tự:

Contract

↓

Approval

↓

Guardrail (Brand + Capability)

↓

Idempotency

↓

Queue (+ Circuit Breaker + Rate Limit + Token Vault)

↓

Adapter

↓

Receipt

Không được đảo ngược.

Nếu làm đúng, M07 sẽ thay thế các workflow trung gian kiểu Make.com bằng một cổng xuất bản có kiểm soát, có log, có receipt, có retry, có circuit breaker và có handoff rõ ràng sang M08 Analytics Feedback.

END OF DOCUMENT

