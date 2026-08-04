VENHO AI STUDIO
Module 08 — Analytics & Feedback Development Plan v1.2 (QC-Fixed)
Workspace mẹ: THE WEST LAKE LIVING
Repo: venho-ai-studio
Module: analytics_feedback/
Module ID: M08
Vị trí: Sau M07 Publishing Gateway, trước M09 Agent Studio
Trạng thái: QC PASS — Consolidated Plan (đã sửa lỗi nhất quán)
Nguồn review: VENHO_AI_STUDIO_Module_08_Analytics_Feedback_Development_Plan_v1_1_QC.md
Nguyên tắc cập nhật: M08 là lớp đo lường hiệu năng, chuẩn hóa metrics và sinh feedback advisory. M08 không tự chỉnh Knowledge, không tự tối ưu content, không tự publish và không chứa logic Agent.


Changelog v1.1 → v1.2 (QC-Fixed)
Bản v1.2 giữ nguyên định hướng kiến trúc của v1.1 và chỉ sửa các lỗi nhất quán phát hiện khi rà soát chất lượng. Danh sách sửa đổi:

#
Loại lỗi
Vị trí v1.1
Nội dung sửa
F1
Mâu thuẫn thứ tự triển khai
§17 (roadmap) vs §20 (ưu tiên)
v1.1 đặt Sentiment Guardrail sau Feedback Advisory ở §20, nhưng roadmap và kiến trúc §4 lại đặt Sentiment trước Advisory. Vì advisory mang field guardrail_alerts.negative_sentiment_spike nên bắt buộc Sentiment phải chạy trước. Đã sắp lại §20.
F2
Sai nhất quán thuật ngữ
§4, §5, §17-Step6, §20
"Matrix Standardizer" / matrix_standardizer.py không khớp với "Unified Metrics" dùng ở mọi nơi khác. Đổi thành Unified Metrics Standardizer / metrics_standardizer.py. Từ "matrix" ở §0 đổi thành "unified metrics".
F3
Sai nhất quán pillar/theme
§7, §9, §10 vs §11
Advisory §11 đề xuất content_pillars.westlake_sunset nhưng pillar thực tế là westlake_lifestyle. Đã tách rõ: pillar = westlake_lifestyle, sub-theme = sunset, và thêm field theme trong recommendation.
F4
Sai nhất quán định danh module
§6 config vs §11/§12 contract vs prose
Chuẩn hóa: JSON/config dùng M04_AUTOMATION_STUDIO, prose dùng "M04 Automation Studio (Manual Gate)". Sửa alert_target: "m04_automation" → M04_AUTOMATION_STUDIO.
F5
Thiếu store
§5 stores/ vs §16 outputs
Output có scores/ và alerts/ nhưng stores/ thiếu store tương ứng. Thêm score_store.py và alert_store.py. Cập nhật Step 5 và Step 11.
F6
Ngưỡng sample size chưa định nghĩa
§10 warning "below 20" vs §6 config
Config chỉ có minimum_sample_size: 5 nhưng score cảnh báo "below 20". Thêm strong_conclusion_sample_size và bảng confidence_levels vào scoring_rules.yaml.
F7
Nhập nhằng trách nhiệm derived metrics
§17 Step 6 vs Step 7
Làm rõ: Standardizer (Step 6) điền block metrics; Stats Calculator (Step 7) điền block derived.
F8
Guardrail keyword thiếu tiếng Việt
§6 sentiment_guardrails.yaml
Khách sạn phục vụ khách Việt; keyword chỉ có tiếng Anh sẽ bỏ sót. Thêm keyword tiếng Việt + field languages.
F9
Advisory thiếu approval route rõ ràng
§11
Thêm approval_route để nêu rõ advisory phải qua M04/M09, tách khỏi target_modules (module bị tác động).
F10
Ví dụ dễ gây nhầm
§11 vs §12
Thêm chú thích: advisory (Instagram) và alert (Facebook) là hai ví dụ minh họa cho hai platform khác nhau của cùng một package.


Không thay đổi: ranh giới module, danh sách contract, kỷ luật test 0 API call, các contract số học (đã kiểm chứng đúng).


0. Kết luận QC
Bản M08 Analytics & Feedback Loop đi đúng hướng khi xác định M08 là lớp:

Delivery Receipt từ M07

↓

Thu thập metrics

↓

Chuẩn hóa dữ liệu

↓

Chấm điểm

↓

Sinh feedback advisory

↓

Gửi về M01/M05 qua approval gate

Plan gốc đã có các ý quan trọng: async ingestion, idempotent time-series snapshot, unified engagement metrics, sentiment guardrail, feedback override advisory và kỷ luật test offline 0 API call.

Sau khi rà soát chất lượng, các nguyên tắc sau được giữ và làm rõ:

Ranh giới module

M08 không trực tiếp ghi đè M01 Knowledge.
M08 không trực tiếp thay đổi M05 Content Strategy.
M08 chỉ sinh feedback_advisory.
Việc áp dụng advisory phải qua M04 Automation Studio (Manual Gate) hoặc M09 Agent Studio theo workflow được duyệt.

Dependency

M08 phụ thuộc chính vào M07 Delivery Receipt.
M08 có thể đọc context từ M01, M05, M06 để hiểu nguồn nội dung.
M08 không được gọi M02/M05 để tự sinh nội dung mới.
M08 không được gọi M07 để publish lại.

Thuật ngữ Google

Chuẩn hóa Google Business Profile (không dùng "Google My Business").
Google Analytics cho website → adapter google_analytics.py.
Dữ liệu local listing → google_business.py.

Output

feedback_override.json dễ gây hiểu nhầm là tự override → đổi tên thành feedback_advisory.json.
Nếu cần apply, phải tạo approved_override_request ở workflow khác.

Guardrail khủng hoảng

M08 có thể tạo CRITICAL_ALERT.
M08 không gửi trực tiếp cho Founder nếu chưa qua kênh Notification/Automation.
M08 gửi alert event cho M04 Automation Studio hoặc M09 Agent Studio.

Test convention

Không đặt mục tiêu số test tuyệt đối như 425+.
Thay bằng: 100% M08 tests pass, 0 real API call in pytest, coverage đạt ngưỡng dự án, critical paths có unit test.

Dữ liệu chuỗi thời gian

Snapshot cần unique key.
Lưu raw metrics và normalized metrics tách biệt.
Có metric provenance để biết dữ liệu đến từ platform nào, API nào, lúc nào.

Scoring

Score không chỉ dựa vào engagement rate.
Có baseline theo platform, content type và thời gian.
Tránh kết luận quá sớm khi dữ liệu ít (dùng minimum_sample_size và strong_conclusion_sample_size).


1. Vai trò chính thức của M08
Analytics Feedback là lớp Performance Measurement & Feedback Advisory Layer của VENHO AI Studio.

Nó có nhiệm vụ thu thập dữ liệu hiệu năng từ các bài đã xuất bản, chuẩn hóa dữ liệu, tính chỉ số, phát hiện tín hiệu tốt/xấu và tạo đề xuất có cấu trúc cho chu kỳ sản xuất tiếp theo.

M07 Publishing Gateway

        ↓

Delivery Receipt

        ↓

M08 Analytics Feedback

        ↓

Metrics Snapshot

        ↓

Unified Metrics

        ↓

Performance Score

        ↓

Feedback Advisory

        ↓

M04 Approval / M09 Agent Studio / M01-M05 future cycles

M08 biến hệ thống từ pipeline một chiều thành vòng lặp học tập có kiểm soát.


2. Ranh giới module
2.1 M08 được phép làm
Đọc Delivery Receipt từ M07.
Lập lịch thu thập metrics.
Gọi API insights thông qua adapter.
Chuẩn hóa metrics về unified schema.
Lưu snapshot theo thời gian.
Tính chỉ số phái sinh.
So sánh với baseline.
Chấm điểm performance.
Phát hiện negative sentiment spike.
Tạo feedback advisory.
Tạo critical alert event.
Xuất báo cáo .md + .json.
Gửi advisory/alert cho M04 hoặc M09 xử lý tiếp.
2.2 M08 không được làm
Không tự publish nội dung.
Không tự xóa bài.
Không tự sửa content đã đăng.
Không tự sửa Knowledge/DNA.
Không tự ghi đè Content Strategy.
Không tự tạo prompt.
Không tự tạo nội dung mới.
Không tự quyết định chiến dịch tiếp theo.
Không hard-code Ven Hồ vào core (chỉ để trong config project).
Không chứa logic Agent.


3. Dependency chính thức
3.1 Input upstream
Nguồn input chính:

M07 Delivery Receipt

Nguồn context phụ:

M01 Knowledge Studio

M05 Content Studio

M06 Video Studio

M08 dùng context để hiểu:

Nội dung thuộc pillar nào.
Content type là gì.
Platform nào.
Asset nào.
Knowledge source nào.
Campaign/topic nào.
3.2 Output downstream
M08 xuất:

Feedback Advisory

Critical Alert Event

Analytics Report

Metrics Snapshot

Các output này có thể được dùng bởi:

M04 Automation Studio

M09 Agent Studio

M01 Knowledge Studio

M05 Content Studio

Nhưng M08 không tự apply.


4. Core Architecture
Delivery Receipt Store

        ↓

Ingestion Router

        ↓

Metrics Collection Scheduler

        ↓

Platform Metrics Adapter Registry

        ├── Facebook Insights Adapter

        ├── Instagram Insights Adapter

        ├── Threads Insights Adapter

        ├── Google Business Profile Adapter

        └── Google Analytics Adapter

        ↓

Raw Metrics Store

        ↓

Unified Metrics Standardizer      (map raw → block `metrics`)

        ↓

Stats Calculator                  (điền block `derived`)

        ↓

Time-Series Snapshot Store

        ↓

Baseline Calculator

        ↓

Performance Scorer

        ↓

Sentiment / Quality Scorer

        ↓

Feedback Advisory Generator

        ↓

Analytics Report Renderer

        ↓

M04 / M09 handoff

Lưu ý thứ tự: Sentiment / Quality Scorer luôn chạy trước Feedback Advisory Generator, vì advisory mang kết quả guardrail sentiment.


5. Cấu trúc repo đề xuất
analytics_feedback/

├── __init__.py

├── ingestion_router.py

├── collection_scheduler.py

├── metrics_standardizer.py

├── baseline_calculator.py

├── performance_scorer.py

├── sentiment_scorer.py

├── feedback_advisory_generator.py

├── alert_generator.py

├── report_generator.py

├── exceptions.py

├── cli.py

│

├── adapters/

│   ├── base_metrics_adapter.py

│   ├── facebook_insights.py

│   ├── instagram_insights.py

│   ├── threads_insights.py

│   ├── google_business.py

│   ├── google_analytics.py

│   └── mock_metrics.py

│

├── schemas/

│   ├── delivery_receipt_ref.py

│   ├── raw_metrics.py

│   ├── unified_metrics.py

│   ├── metrics_snapshot.py

│   ├── performance_score.py

│   ├── feedback_advisory.py

│   └── alert_event.py

│

├── stores/

│   ├── raw_metrics_store.py

│   ├── snapshot_store.py

│   ├── score_store.py

│   ├── advisory_store.py

│   ├── alert_store.py

│   └── report_store.py

│

├── utils/

│   ├── stats_calculator.py

│   ├── time_windows.py

│   ├── idempotency.py

│   └── platform_mapping.py

│

├── renderers/

│   ├── analytics_report_md.py

│   ├── feedback_advisory_md.py

│   └── json_renderer.py

│

└── tests/

    ├── fixtures/

    ├── test_unified_metrics.py

    ├── test_snapshot_idempotency.py

    ├── test_baseline.py

    ├── test_performance_scorer.py

    ├── test_sentiment_guardrail.py

    └── test_mock_adapters.py

Ghi chú F2/F5: đổi matrix_standardizer.py → metrics_standardizer.py; thêm stores/score_store.py và stores/alert_store.py để khớp với các thư mục output scores/ và alerts/ ở §16.


6. Config đề xuất
config/

└── projects/

    └── venho_hotel/

        └── analytics/

            ├── platforms.yaml

            ├── metric_mapping.yaml

            ├── collection_schedule.yaml

            ├── scoring_rules.yaml

            ├── sentiment_guardrails.yaml

            └── feedback_policy.yaml

Ví dụ collection_schedule.yaml:

snapshots_after_publish:

  - 24h

  - 72h

  - 7d

  - 14d

default_lookback_days: 30

max_posts_per_run: 50

Ví dụ scoring_rules.yaml:

minimum_sample_size: 5            # dưới ngưỡng này → INSUFFICIENT_DATA

strong_conclusion_sample_size: 20 # dưới ngưỡng này → thêm warning, không kết luận mạnh

confidence_levels:                # ánh xạ sample_size → confidence

  low: 5

  medium: 12

  high: 20

baseline_grouping:

  - platform

  - content_type

  - pillar

weights:                          # tổng = 1.00

  engagement_rate: 0.35

  reach: 0.20

  saves_or_shares: 0.20

  click_actions: 0.15

  sentiment_quality: 0.10

outperform_threshold: 1.25

underperform_threshold: 0.75

Ví dụ sentiment_guardrails.yaml:

negative_spike_threshold: 0.15

minimum_comments_for_alert: 10

languages:                        # hỗ trợ song ngữ cho khách Việt + khách quốc tế

  - vi

  - en

critical_keywords:

  vi:

    - "bẩn"

    - "lừa đảo"

    - "hoàn tiền"

    - "thô lỗ"

    - "mất an toàn"

    - "gián"

    - "hôi"

  en:

    - "dirty"

    - "scam"

    - "refund"

    - "rude"

    - "unsafe"

alert_target: "M04_AUTOMATION_STUDIO"

Ghi chú F6/F8: scoring_rules.yaml bổ sung strong_conclusion_sample_size và bảng confidence_levels; sentiment_guardrails.yaml bổ sung keyword tiếng Việt và field languages; alert_target chuẩn hóa thành M04_AUTOMATION_STUDIO.


7. Input Contract — Delivery Receipt Reference
M08 không cần toàn bộ package gốc. M08 bắt đầu từ receipt M07.

{

  "contract_version": "1.0",

  "package_id": "pkg_20260709_westlake_sunset",

  "project": "venho_hotel",

  "published_timestamp": "2026-07-09T04:00:05Z",

  "content_type": "reel",

  "pillar": "westlake_lifestyle",

  "theme": "sunset",

  "platform_results": {

    "facebook": {

      "success": true,

      "status": "PUBLISHED",

      "post_id": "fb_page_post_983274892374",

      "public_url": "https://facebook.com/venhohotel/posts/983274892374"

    },

    "instagram": {

      "success": true,

      "status": "PUBLISHED",

      "post_id": "ig_media_1792837492384",

      "public_url": "https://instagram.com/p/C-923847/"

    }

  }

}

Ghi chú F3: thêm field theme (sunset) tách khỏi pillar (westlake_lifestyle) để chuỗi ví dụ nhất quán từ receipt → unified → score → advisory.


8. Raw Metrics Contract
Raw metrics giữ dữ liệu gần với platform nhất để audit.

{

  "contract_version": "1.0",

  "package_id": "pkg_20260709_westlake_sunset",

  "platform": "instagram",

  "post_id": "ig_media_1792837492384",

  "snapshot_timestamp_utc": "2026-07-12T11:00:00Z",

  "provider": "meta_insights",

  "api_version": "vXX.X",

  "raw": {

    "impressions": 8900,

    "reach": 7400,

    "likes": 1200,

    "comments": 32,

    "shares": 85,

    "saves": 44,

    "reels_video_view_total_time_ms": 35600000

  }

}


9. Unified Metrics Contract
Unified metrics là dữ liệu chuẩn hóa cho core.

{

  "contract_version": "1.0",

  "snapshot_id": "sha256_package_platform_timestamp",

  "package_id": "pkg_20260709_westlake_sunset",

  "project": "venho_hotel",

  "platform": "instagram",

  "post_id": "ig_media_1792837492384",

  "snapshot_timestamp_utc": "2026-07-12T11:00:00Z",

  "days_since_published": 3,

  "content_type": "reel",

  "pillar": "westlake_lifestyle",

  "theme": "sunset",

  "metrics": {

    "reach": 7400,

    "impressions": 8900,

    "views": 8900,

    "likes": 1200,

    "comments": 32,

    "shares": 85,

    "saves": 44,

    "clicks": 0,

    "booking_clicks": 0,

    "watch_time_ms": 35600000

  },

  "derived": {

    "engagement_count": 1361,

    "engagement_rate_by_reach": 0.184,

    "share_rate": 0.011,

    "save_rate": 0.006,

    "click_rate": 0.0

  },

  "provenance": {

    "source_adapter": "instagram_insights",

    "provider": "meta_insights",

    "api_version": "vXX.X"

  }

}

Kiểm chứng số học: engagement_count = 1200 + 32 + 85 + 44 = 1361; engagement_rate_by_reach = 1361 / 7400 = 0.184; share_rate = 85 / 7400 = 0.011; save_rate = 44 / 7400 = 0.006; click_rate = 0 / 7400 = 0.0. Tất cả đúng.

Trách nhiệm điền dữ liệu (F7): block metrics do Unified Metrics Standardizer (Step 6) điền; block derived do Stats Calculator (Step 7) tính. Block views mặc định lấy bằng impressions cho reel khi API không tách riêng lượt xem; nếu adapter cung cấp plays riêng thì ưu tiên giá trị đó.


10. Performance Score Contract
{

  "contract_version": "1.0",

  "snapshot_id": "sha256_package_platform_timestamp",

  "package_id": "pkg_20260709_westlake_sunset",

  "platform": "instagram",

  "score_timestamp_utc": "2026-07-12T11:05:00Z",

  "baseline_group": {

    "platform": "instagram",

    "content_type": "reel",

    "pillar": "westlake_lifestyle"

  },

  "sample_size": 12,

  "performance_label": "OUTPERFORM",

  "relative_score": 1.42,

  "confidence": "medium",

  "reasons": [

    "Engagement rate is 42% above baseline",

    "Share rate is above historical average"

  ],

  "warnings": [

    "Sample size 12 < strong_conclusion_sample_size (20), avoid strong conclusion"

  ]

}

Kiểm chứng nhãn: relative_score = 1.42 > outperform_threshold (1.25) → OUTPERFORM. sample_size = 12 ≥ minimum_sample_size (5) nên không phải INSUFFICIENT_DATA; nhưng 12 < strong_conclusion_sample_size (20) nên có warning và confidence = medium (theo bảng confidence_levels). Warning F6 đã tham chiếu đúng key config.


11. Feedback Advisory Contract
Tên chính thức: feedback_advisory.json.

Không dùng tên feedback_override.json cho output chính vì dễ hiểu nhầm là tự ghi đè.

{

  "contract_version": "1.0",

  "advisory_id": "adv_20260712_westlake_sunset",

  "target_modules": ["M01_KNOWLEDGE_STUDIO", "M05_CONTENT_STUDIO"],

  "approval_route": ["M04_AUTOMATION_STUDIO", "M09_AGENT_STUDIO"],

  "generated_timestamp_utc": "2026-07-12T11:05:00Z",

  "advisory_type": "CONTENT_STRATEGY_ADVISORY",

  "status": "pending_approval",

  "analysis_summary": "Sunset theme content outperformed the baseline for Instagram Reels within the westlake_lifestyle pillar.",

  "recommendations": [

    {

      "target": "content_pillars.westlake_lifestyle",

      "theme": "sunset",

      "action": "INCREASE_WEIGHT",

      "modifier": 1.25,

      "reason": "Instagram reels with West Lake sunset visuals outperformed the westlake_lifestyle baseline by 42%.",

      "evidence": {

        "package_id": "pkg_20260709_westlake_sunset",

        "platform": "instagram",

        "pillar": "westlake_lifestyle",

        "theme": "sunset",

        "relative_score": 1.42

      }

    }

  ],

  "guardrail_alerts": {

    "negative_sentiment_spike": false,

    "critical_keywords_triggered": []

  },

  "approval_required": true

}

Ghi chú F3/F9: recommendations[].target trỏ đúng pillar content_pillars.westlake_lifestyle, insight "sunset" đưa vào field theme. Thêm approval_route để nêu rõ advisory đi qua M04/M09 (tách khỏi target_modules là module bị tác động).

Ghi chú F10: guardrail_alerts.negative_sentiment_spike = false ở ví dụ này ứng với Instagram; ví dụ alert §12 là kịch bản Facebook của cùng package — hai platform khác nhau nên kết quả sentiment khác nhau.


12. Alert Event Contract
{

  "contract_version": "1.0",

  "alert_id": "alert_20260712_pkg_001",

  "project": "venho_hotel",

  "package_id": "pkg_20260709_westlake_sunset",

  "severity": "CRITICAL",

  "alert_type": "NEGATIVE_SENTIMENT_SPIKE",

  "triggered_at": "2026-07-12T11:05:00Z",

  "platform": "facebook",

  "reason": "Negative comments exceeded threshold.",

  "metrics": {

    "negative_comment_ratio": 0.22,

    "total_comments": 27

  },

  "handoff": {

    "target": "M04_AUTOMATION_STUDIO",

    "requires_human_attention": true

  }

}

Kiểm chứng trigger: negative_comment_ratio = 0.22 ≥ negative_spike_threshold (0.15) và total_comments = 27 ≥ minimum_comments_for_alert (10) → sinh CRITICAL_ALERT đúng. handoff.target = M04_AUTOMATION_STUDIO khớp alert_target trong config (F4).


13. Guardrails
13.1 No Auto-Apply
M08 không được tự ghi vào M01/M05.

M08 chỉ sinh advisory.

Việc áp dụng phải qua:

M04 Automation Studio (Manual Gate)

hoặc

M09 Agent Studio workflow có approval
13.2 Negative Sentiment Circuit Breaker
Nếu negative sentiment vượt ngưỡng:

negative_ratio >= negative_spike_threshold

AND

total_comments >= minimum_comments_for_alert

M08 sinh CRITICAL_ALERT.

M08 không tự xử lý khủng hoảng.
13.3 No Hallucinated Optimization
M08 không được đề xuất mạnh nếu thiếu sample size.

Nếu sample_size < minimum_sample_size → performance_label = INSUFFICIENT_DATA, advisory chỉ được ghi là observation, không phải recommendation mạnh.
Nếu minimum_sample_size ≤ sample_size < strong_conclusion_sample_size → vẫn cho label OUTPERFORM/NORMAL/UNDERPERFORM nhưng bắt buộc kèm warning và confidence không được là high.
13.4 Rate Limit Discipline
Adapter phải có backoff.
Không quét quá dày.
Tôn trọng schedule.
Lưu snapshot để tránh gọi lại không cần thiết.
13.5 Idempotency
Snapshot unique key:

package_id + platform + snapshot_timestamp_utc

snapshot_id = sha256(package_id + platform + snapshot_timestamp_utc).

Nếu snapshot đã tồn tại:

Không ghi trùng.
Có thể update nếu marked as corrected.
Mặc định giữ bản cũ.


14. Kỷ luật kiểm thử
14.1 Nguyên tắc
pytest không gọi API thật.
Không dùng secret thật.
Không phụ thuộc internet.
Mock metrics adapter là mặc định.
Fixture dùng local JSON.
Test không phụ thuộc thời gian thật; dùng frozen time hoặc mock clock.
14.2 Không dùng target test count tuyệt đối
Không dùng:

425+ tests

Dùng:

100% M08 tests pass

0 real API call in pytest

Coverage đạt ngưỡng dự án

Critical paths có unit test
14.3 Critical paths cần test
Delivery receipt parsing
Metrics adapter interface
Raw metrics normalization
Snapshot idempotency
Baseline calculation
Performance scoring
Sentiment guardrail
Feedback advisory generation
Alert event generation
Rate limit / backoff behavior
Mock adapter behavior


15. CLI đề xuất
Collect metrics by receipt
venho analytics collect --receipt data/projects/venho_hotel/publishing/receipts/pkg_001.json
Collect all recent published posts
venho analytics collect-all --project venho_hotel --days-back 7
Generate report
venho analytics report --project venho_hotel --period 7d
Generate feedback advisory
venho analytics advisory --project venho_hotel --period 30d
Dry run
venho analytics collect-all --project venho_hotel --days-back 7 --dry-run


16. Output files
data/projects/<project>/analytics/

├── raw_metrics/

├── snapshots/

├── scores/

├── advisories/

├── alerts/

└── reports/

Mỗi thư mục output có store tương ứng ở §5: raw_metrics/↔raw_metrics_store.py, snapshots/↔snapshot_store.py, scores/↔score_store.py, advisories/↔advisory_store.py, alerts/↔alert_store.py, reports/↔report_store.py (F5).

Ví dụ:

data/projects/venho_hotel/analytics/snapshots/pkg_20260709_instagram_72h.json

data/projects/venho_hotel/analytics/scores/pkg_20260709_instagram_72h.json

data/projects/venho_hotel/analytics/advisories/adv_20260712_westlake_sunset.json

data/projects/venho_hotel/analytics/alerts/alert_20260712_pkg_001.json

data/projects/venho_hotel/analytics/reports/weekly_report_2026_07_12.md


17. Roadmap phát triển theo giai đoạn
Phase 1 — Foundation & Contracts
Mục tiêu:

Tạo module, schema, adapter interface và mock environment.
Step 0 — Module Scaffold
Tạo:

analytics_feedback/

analytics_feedback/adapters/

analytics_feedback/schemas/

analytics_feedback/stores/

analytics_feedback/tests/

config/projects/<project>/analytics/

DoD:

Import module không lỗi.
Không ảnh hưởng module cũ.
Test skeleton chạy được.
Có README nội bộ.
Step 1 — Schemas & Contracts
Tạo:

schemas/delivery_receipt_ref.py

schemas/raw_metrics.py

schemas/unified_metrics.py

schemas/metrics_snapshot.py

schemas/performance_score.py

schemas/feedback_advisory.py

schemas/alert_event.py

DoD:

Validate được JSON mẫu.
Có contract_version.
Có snapshot_id.
Có provenance.
Advisory có status = pending_approval và approval_route.
Step 2 — Base Metrics Adapter + Mock Adapter
Tạo:

adapters/base_metrics_adapter.py

adapters/mock_metrics.py

DoD:

Mọi adapter có chung fetch_metrics().
Mock adapter chạy offline.
Không API call thật trong test.
Fixture metrics trả kết quả tất định.


Phase 2 — Ingestion & Storage
Mục tiêu:

Đọc delivery receipt, lập lịch snapshot và lưu dữ liệu.
Step 3 — Ingestion Router
Tạo:

ingestion_router.py

DoD:

Đọc được delivery receipt M07.
Chỉ lấy platform đã publish success.
Bỏ qua platform failed.
Tạo collection tasks.
Step 4 — Collection Scheduler
Tạo:

collection_scheduler.py

DoD:

Tạo lịch 24h / 72h / 7d / 14d.
Không tạo task trùng.
Tôn trọng config schedule.
Step 5 — Raw & Snapshot Store
Tạo:

stores/raw_metrics_store.py

stores/snapshot_store.py

DoD:

Lưu raw metrics.
Lưu unified snapshot.
Chống trùng snapshot_id.
Có audit provenance.


Phase 3 — Standardization & Scoring
Mục tiêu:

Chuẩn hóa metrics và chấm điểm performance.
Step 6 — Unified Metrics Standardizer
Tạo:

metrics_standardizer.py

DoD:

Map Facebook/Instagram/Threads/Google metrics về unified schema (block metrics).
Missing metrics được ghi null/0 theo quy tắc rõ.
Không làm mất raw metrics.
Step 7 — Stats Calculator
Tạo:

utils/stats_calculator.py

DoD:

Điền block derived của unified metrics.
Tính engagement_count.
Tính engagement_rate_by_reach.
Tính share_rate.
Tính save_rate.
Tính click_rate.
Test bằng fixture.
Step 8 — Baseline Calculator
Tạo:

baseline_calculator.py

DoD:

Tạo baseline theo platform + content_type + pillar.
Tôn trọng minimum_sample_size.
Nếu thiếu dữ liệu → INSUFFICIENT_DATA.
Step 9 — Performance Scorer
Tạo:

performance_scorer.py

stores/score_store.py

DoD:

So sánh snapshot với baseline.
Trả OUTPERFORM / NORMAL / UNDERPERFORM / INSUFFICIENT_DATA.
Có confidence (theo bảng confidence_levels).
Có reasons/warnings; thêm warning khi sample_size < strong_conclusion_sample_size.
Lưu score qua score_store.


Phase 4 — Sentiment & Guardrails
Mục tiêu:

Phát hiện rủi ro phản hồi tiêu cực trước khi sinh advisory.
Step 10 — Sentiment Scorer
Tạo:

sentiment_scorer.py

DoD:

Gắn nhãn positive/neutral/negative bằng rule-based hoặc model nhỏ.
Hỗ trợ tiếng Việt + tiếng Anh (theo languages trong config).
Không gọi API thật trong test.
Test với comment fixture.
Step 11 — Critical Alert Generator
Tạo:

alert_generator.py

stores/alert_store.py

DoD:

Negative ratio vượt ngưỡng → sinh alert.
Nếu total comments quá ít → không alert mạnh.
Alert có handoff target M04/M09.
Không tự gửi tin nhắn trực tiếp trong core.
Lưu alert qua alert_store.


Phase 5 — Feedback Advisory
Mục tiêu:

Sinh đề xuất có cấu trúc, không tự apply. Advisory tiêu thụ kết quả sentiment từ Phase 4.
Step 12 — Feedback Advisory Generator
Tạo:

feedback_advisory_generator.py

DoD:

Sinh advisory từ performance score + sentiment guardrail.
Có evidence (kèm pillar/theme).
Có approval_required = true và approval_route.
Điền guardrail_alerts từ kết quả Sentiment Scorer (Step 10).
Không tự ghi M01/M05.
Step 13 — Advisory Store
Tạo:

stores/advisory_store.py

DoD:

Lưu advisory JSON.
Lưu advisory Markdown.
Có status pending_approval / approved / rejected.
Step 14 — Report Generator
Tạo:

report_generator.py

renderers/analytics_report_md.py

renderers/feedback_advisory_md.py

DoD:

Sinh weekly report.
Sinh campaign report.
Report có metrics, insight, warning, advisory.
Markdown section cố định.


Phase 6 — Platform Adapter MVP
Mục tiêu:

Chuẩn bị adapter thật nhưng test offline vẫn bắt buộc.
Step 15 — Facebook Insights Adapter
Tạo:

adapters/facebook_insights.py

DoD:

Map raw response sang raw_metrics.
Mock response pass.
Real API chỉ dùng ngoài pytest.
Step 16 — Instagram Insights Adapter
Tạo:

adapters/instagram_insights.py

DoD:

Hỗ trợ post/reel metrics.
Map watch time nếu có.
Mock response pass.
Step 17 — Threads Insights Adapter
Tạo:

adapters/threads_insights.py

DoD:

Map views/replies/likes nếu API hỗ trợ.
Feature flag nếu chưa đủ access.
Step 18 — Google Business / Analytics Adapter
Tạo:

adapters/google_business.py

adapters/google_analytics.py

DoD:

Tách local listing metrics (Google Business Profile) và website analytics (Google Analytics).
Mock response pass.
Feature flag nếu chưa cấu hình API.


Phase 7 — CLI & E2E Acceptance
Mục tiêu:

Đóng gói luồng chạy thực tế.
Step 19 — CLI
Tạo:

cli.py

DoD:

venho analytics collect chạy được.
venho analytics collect-all chạy được.
venho analytics report chạy được.
venho analytics advisory chạy được.
Có --dry-run.
Step 20 — End-to-End Dry Run
Test:

M07 delivery receipt fixture

↓

M08 collect mock metrics

↓

standardize

↓

score

↓

sentiment guardrail

↓

generate advisory

↓

generate report

DoD:

Không API thật.
Snapshot đúng.
Score đúng.
Sentiment đúng.
Advisory đúng.
Report đúng.
Step 21 — Controlled Real API Test
Chỉ chạy thủ công, không chạy trong pytest.

DoD:

Dùng test/sandbox hoặc account có quyền.
Secret từ environment.
Có checklist trước khi chạy.
Có rate-limit backoff.
Có log rõ ràng.


18. Definition of Done tổng thể
M08 hoàn thành khi:

Đọc được delivery receipt M07.
Tạo được collection tasks.
Có mock metrics adapter.
Thu được raw metrics.
Chuẩn hóa unified metrics.
Lưu snapshot idempotent.
Tính được derived metrics.
Tạo baseline.
Chấm performance score.
Phát hiện negative sentiment spike.
Sinh critical alert event.
Sinh feedback advisory.
Sinh analytics report.
Output .md + .json.
Có CLI.
Có dry-run.
pytest không gọi API thật.
Không hard-code Ven Hồ vào core.
Không tự apply Knowledge/Content changes.
Handoff rõ cho M04/M09 và future M01/M05 cycles.


19. Rủi ro chính và cách xử lý
Rủi ro 1 — M08 tự sửa Knowledge
Cách xử lý:

Chỉ output advisory.
approval_required = true + approval_route.
Apply qua M04/M09.
Rủi ro 2 — Kết luận từ dữ liệu quá ít
Cách xử lý:

minimum_sample_size và strong_conclusion_sample_size.
INSUFFICIENT_DATA.
confidence level.
warnings.
Rủi ro 3 — Metrics mỗi platform khác nhau
Cách xử lý:

Raw metrics giữ nguyên.
Unified metrics chuẩn hóa.
Provenance rõ ràng.
Rủi ro 4 — Snapshot trùng
Cách xử lý:

snapshot_id.
idempotent store.
no duplicate writes.
Rủi ro 5 — API rate limit
Cách xử lý:

schedule.
backoff.
max posts per run.
adapter feature flags.
Rủi ro 6 — Sentiment alert sai
Cách xử lý:

minimum comment count.
critical keyword list (song ngữ vi/en).
threshold rõ.
output alert, không tự xử lý.
Rủi ro 7 — Test gọi API thật
Cách xử lý:

mock adapter default.
no secrets in CI.
pytest offline.
real API test thủ công.


20. Thứ tự ưu tiên triển khai
Ưu tiên thực tế (đã sắp lại để Sentiment đứng trước Advisory — F1):

1.  Schemas

2.  Mock Metrics Adapter

3.  Ingestion Router

4.  Snapshot Store

5.  Unified Metrics Standardizer

6.  Stats Calculator

7.  Baseline Calculator

8.  Performance Scorer

9.  Sentiment Scorer + Guardrail

10. Feedback Advisory Generator

11. Report Generator

12. Real Platform Adapters

13. CLI

14. E2E Dry Run

15. Controlled Real API Test

Không viết adapter API thật trước khi schemas, mock và standardizer ổn định.

Sentiment Scorer bắt buộc hoàn thành trước Feedback Advisory Generator vì advisory mang field guardrail_alerts.


21. Quan hệ với kiến trúc module mới
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

M08 đứng sau M07 để đo hiệu quả bài đã publish.

M08 đứng trước M09 để cung cấp insight/advisory cho agent hoặc human workflow.

M08 không phải Dashboard.

M08 không phải Agent.

M08 là lớp đo lường và phản hồi có kiểm soát.


22. Kết luận
Analytics Feedback là module đóng vòng lặp học tập của VENHO AI Studio.

Nó giúp hệ thống không chỉ sản xuất và xuất bản nội dung, mà còn học từ dữ liệu thật.

Tuy nhiên, đây là module có rủi ro cao về kết luận sai nếu dữ liệu ít hoặc metrics không chuẩn hóa. Vì vậy M08 phải được xây theo thứ tự:

Receipt

↓

Raw Metrics

↓

Unified Metrics

↓

Snapshot

↓

Baseline

↓

Score

↓

Sentiment Guardrail

↓

Advisory

↓

Approval

Không được bỏ qua baseline và sample size.

Nếu làm đúng, M08 sẽ giúp toàn bộ hệ thống chuyển từ:

AI tạo nội dung theo cảm tính

sang:

AI cải thiện nội dung dựa trên dữ liệu thực tế, nhưng vẫn có kiểm soát của con người

END OF DOCUMENT

