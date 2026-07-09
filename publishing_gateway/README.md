# Publishing Gateway

Module 07 is the distribution and delivery layer for VENHO AI Studio.

Boundaries:

- Receives approved packages from Module 04 after validation and manual approval.
- Checks contract, approval, brand display rules, platform capability, idempotency, queue, and reliability guards before publishing.
- Sends approved payloads to platform adapters and writes delivery receipts for Module 08.
- Does not create, rewrite, translate, schedule, score, or optimize content.
- Does not call real platform APIs during automated tests.
- Does not read real secrets during automated tests.

Current status:

- Offline dry-run pipeline is implemented end to end.
- Core MVP adapters map Facebook and Instagram payloads.
- Conditional adapters map Threads and Google Business Profile payloads while production flags remain off.
- Real API publishing remains a controlled manual test step and is not executed by pytest.
