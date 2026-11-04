# Legacy generation seam

**GC2-P4-T01 · 2026-11-04 · Read-only inventory**

## Call graph

```text
run_weekly_cycle
  ├─ claims/completes a fortnight JobStore record; ensures SlotStore horizon
  └─ eight cadence dates (Mon/Wed/Fri/Sat × 2 weeks)
       └─ run_daily_cycle(day, slot_date)
            ├─ choose topic (_pick_regular_topic / _pick_special_topic)
            │    ├─ local-intel, PublicationRegistry, TrendCandidateStore,
            │    │  weather, optional Gemini topic ideation (read/API)
            │    └─ select_from_candidates → rotation_state.json
            ├─ choose scenario (_pick_scenario → rotation_state.json)
            ├─ build and validate LOCKED creative brief
            ├─ generate image A (_generate_topic_image)
            │    └─ GPT Image provider → RunStore artifact + manifest
            │         → Validator Studio image QC → report JSON
            ├─ upload A to Drive; optionally generate/upload B and upload C
            ├─ for each platform:
            │    └─ _run_content_pipeline_budgeted
            │         └─ run_content_pipeline
            │              ├─ M05ContentBridge.generate_candidates
            │              │    └─ generate_content → content_studio MD/JSON/manifest
            │              └─ M03ValidatorBridge.validate_package
            ├─ READY_FOR_REVIEW → PublicationRegistry.reserve/update
            └─ SlotStore transition; best-effort Telegram alerts on some conditions
```

`run_weekly_cycle` batches eight dates and calls the same `run_daily_cycle` used by the standalone daily command. It does not dispatch posts. `replace_rejected_publication` and `run_fast_lane` are separate entry points that may call `run_daily_cycle`; they first mutate PublicationRegistry/TrendCandidateStore state and can restore it after failure.

## Function inventory

| Hàm / bridge | Input → output | Side effect hiện tại | Cách vô hiệu trong adapter |
|---|---|---|---|
| `run_weekly_cycle` | project, platforms, roots, provider/bridge overrides → `WeeklyCycleResult` gồm các `DailyCycleResult` | Claim/heartbeat/complete/fail ở `growth.db`; tạo/cập nhật slot; gọi toàn bộ daily pipeline; Telegram alert tổng hợp fallback ảnh | Không gọi wrapper. Worker mới cấp `DraftRequest` từ slot và chỉ dùng các provider/reader được inject. |
| `_pick_regular_topic`, `_pick_special_topic`, `_pick_topic` | lane config, project/data root → topic dict `{pillar, topic, dna_subject, ...}` | Đọc publication/local-intel/trend/weather; `_pick_special_topic` có thể gọi `TrendCandidateStore.mark_used`; selector ghi `rotation_state.json` | Adapter nhận candidate/history snapshot và chọn theo phép tính thuần; không advance legacy cursor, không `mark_used`. P4-T05 ingest trend vào DB v2. |
| `_idea_entries` / `ideate_topics` | lane, date, calendar, recent topics, events → danh sách topic strings | Gemini API khi `GROWTH_TOPIC_IDEATION=1` và có key; lỗi thì fallback curated pool | Inject fake/local ideator trong test; production gọi provider riêng, không chạy registry, slot hay Telegram code. |
| `select_from_candidates` / `advance_rotation` | danh sách topic + history + rotation key → một topic dict | Đọc `PublicationRegistry`; ghi `growth/rotation_state.json` và tăng cursor | Dùng selection thuần với cursor/history do caller đọc sẵn; không gọi `advance_rotation`. V2 dedupe bằng candidate/topic state của DB. |
| `_pick_scenario` / `_build_creative_brief` | topic + lane/scenario pools + platform + date → brief dict đã schema-validate | `_pick_scenario` advance `scenario:<day>` trong `rotation_state.json`; brief builder chỉ tạo dữ liệu trong bộ nhớ | Tách chọn scenario thuần từ snapshot; giữ `_build_creative_brief` như mapper dữ liệu nếu không cần sửa global state. |
| `_generate_topic_image` | topic/scenario/DNA/reference/provider → `Path` RunStore folder hoặc failure reason | Paid image provider và budget ledger; RunStore ghi ảnh + manifest; Validator Studio QC và ghi report JSON | Gọi provider qua port, chuẩn hoá bytes, QC qua `FakeQc`/QC port; file chỉ được ghi vào `TemporaryDirectory`, trả local path + provenance. Không gọi `generate_image_run`/RunStore. |
| `_alternative_image_options` / `image_options` | primary scenario + pool + reference resolver → A/B/C option dicts | Có thể gọi thêm image/QC API; chuyển ảnh library sang JPEG; upload mỗi lựa chọn lên Drive | Chỉ tạo option metadata/path cục bộ: A generated, B alternate scenario, C reference photo. Không upload; dùng policy/processor v2 thay EXIF/JPEG helper cũ. |
| `_upload_image_to_drive` | RunStore folder + day/package → public URL hoặc `None` | Google Drive upload và công khai URL; gửi Telegram nếu ảnh bị từ chối ratio | Không gọi. Giữ path/bytes cục bộ; P3 media store tạo variant bất biến và P5 signed URL phục vụ publish. |
| `run_content_pipeline` | LOCKED brief + M05/M03 bridges → package, candidates, validation | Sinh caption qua M05; M05 hiện ghi MD/JSON/manifest; M03 đọc nội dung và DNA để kiểm claim/alignment/content/naturalness | Tạo `ContentRequest`, `read_dna` + `build_content_prompt` và gọi `build_social_draft` trực tiếp với generator inject; nhận `ContentOutput` trong bộ nhớ. Nếu cần artifact QC thì ghi temp. Không gọi `load_content_context`, content engine writer hay prompt bridge writer. |
| `M05ContentBridge.generate_candidates` | brief → candidate dicts | Claude provider mặc định; gọi `generate_content`, ghi MD/JSON/manifest dưới `data/<project>/content/<channel>`; `generate_content` còn gọi `build_content_prompt_for_request` → `save_prompt`, ghi prompt JSON/Markdown dưới data root | Không gọi adapter này nguyên vẹn. `build_content_prompt` là pure mapper; tránh `load_content_context`/`build_content_prompt_for_request`, vì đường đó lưu prompt. Inject provider và tests dùng fake. |
| `M03ValidatorBridge.validate_package` | brief + candidate → verdict/reports | Claim/alignment/content/naturalness validation; đọc markdown nếu có; không gọi Telegram/Make/Meta | Dùng QC/application port ở v2; nếu giữ validator cũ, tạo file trong temp và inject mọi provider cần thiết. |
| `M04AutomationBridge.request_approval` | package → `{approval_request_id, status, package}` | Stub thuần hiện tại; không gửi Telegram | Không dùng làm workflow v2; duyệt qua API/DB và `Notifier` job. |
| `M07PublishingBridge.dispatch` | publish command → gateway result | Có thể gửi webhook Make hoặc Zalo OA | Ngoài generation seam; tuyệt đối không gọi khi tạo draft. Chỉ P5 single-gate dispatch được dùng. |
| `M08AnalyticsBridge.observe` | publication id → analytics/report | Có thể đọc analytics adapter; ghi raw metrics, snapshot, score, advisory, report và research question | Ngoài generation seam; chỉ lane metrics gọi sau publish. |
| `replace_rejected_publication` / `replace_due_rejections` | publication id / batch → replacement draft | Đọc/sửa PublicationRegistry; có thể mở rộng SlotStore; gọi daily pipeline; liên kết publication cũ/mới | V2 dùng `reject_revision` + job `revise`/`new_topic`; không gọi registry helper cũ. |
| `run_fast_lane` | approved trend + free slot → outcomes/publication ids | Sửa registry status để nhường slot; tạo draft; ghi trend `used_at` và ids; phục hồi registry nếu lỗi | P4-T05 đưa trend vào CandidateSource; slot reservation/replacement nằm trong DB transaction + job lane. |
| `_send_alert_best_effort` | event + message → không có output | Có thể gửi Telegram trực tiếp khi có cấu hình; lỗi bị nuốt | Không gọi trực tiếp. V2 enqueue `notify` job và dùng `TelegramNotifier` adapter. |

## Pure-data seam cho P4-T02

Một seam phù hợp là `LegacyGeneratorAdapter.draft(DraftRequest) -> DraftPackage`. Nó dùng topic/fact inputs đã đọc, `read_dna` + pure `build_content_prompt` + social builder, image provider, ImageProcessor và QC port qua dependency injection; trả về `topic_key`, `pillar`, `brief`, `fact_keys`, captions theo mọi `caption_profile` đang bật, cùng option ảnh A/B/C có `path` cục bộ và provenance (scenario, DNA/version, prompt hash, reference IDs, source). Provider calls có thể tốn phí trong production; kết quả và đường dẫn đầu ra không gây side effect bền vững trong adapter.

Không gọi `run_weekly_cycle`, `run_daily_cycle`, `run_content_pipeline`, `M05ContentBridge.generate_candidates`, `generate_content`, `load_content_context`, `build_content_prompt_for_request`, `generate_image_run`, `_upload_image_to_drive`, `PublicationRegistry`, `advance_rotation`, `TrendCandidateStore.mark_used`, `_send_alert_best_effort`, `M07PublishingBridge` hoặc `M08AnalyticsBridge`. `FactStore.__init__` cũng tạo thư mục khi khởi tạo; `LegacyFactSource` nên glob/đọc JSON trực tiếp để bảo đảm read-only, rồi chỉ trả facts đã duyệt và còn hiệu lực tại `DraftRequest.at_ms`. Tests inject fake text/image/QC providers và thư mục tạm; so sánh mtime của publishing registry trước/sau.

Không cần sửa legacy code để tạo seam này nếu adapter dùng builder/provider cấp thấp và tránh các entry point có writer nêu trên. Nếu P4-T02 buộc tái sử dụng nguyên `M05ContentBridge` hoặc `generate_image_run`, phải mở Change Request riêng để thêm chế độ persistence-off/temporary output và test rằng hành vi v3.2 hiện tại không đổi.
