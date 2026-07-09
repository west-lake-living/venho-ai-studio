# M07 to M08 Delivery Receipt Contract

Module 07 writes a delivery receipt after every dry-run or publish attempt. Module 08 can consume this receipt without calling M07 back.

Required fields:

- `contract_version`
- `package_id`
- `project`
- `overall_status`
- `published_timestamp`
- `idempotency_key`
- `platform_results`
- `circuit_breaker`
- `analytics_handoff`

Each platform result includes:

- `success`
- `status`
- `post_id`
- `public_url`
- `error_code`
- `error_message`
- `payload`

Automated tests must use dry-run or mock adapters only. Real API testing is a controlled manual step and must never run inside pytest.
