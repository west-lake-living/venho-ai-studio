# Growth Agent Controlled Rollout Runbook

## Runbook

Rollout stages are `shadow`, `pilot_25`, `pilot_50`, and `pilot_100`. Every stage remains human-approved during the pilot. Trend lane never receives auto-approval.

## Rollback

Disable dispatch before rolling back approval or validation flags. Migrations are forward-only with compatible reads. Approved artifacts are immutable. Git export remains available for recovery.

## Budget

Budget cap enforcement remains active during rollout. Paid calls stop at 100% cap unless an override records reason and approver.

## Ownership

M03 owns validation, M04 owns approvals, M07 owns publishing, M08 owns analytics, and M09 owns advisory orchestration. M10 is presentation-only.
