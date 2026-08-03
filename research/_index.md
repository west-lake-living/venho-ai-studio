## Can Promote
```dataview
TABLE domain, confidence, expires_at
FROM "research/insights" WHERE status = "reviewed" AND evidence_level = "R2"
SORT expires_at ASC
```

## Expiring Soon
```dataview
TABLE evidence_level, expires_at, promoted_fact_keys
FROM "research" WHERE expires_at <= date(today) + dur(7 days) AND status != "archived"
SORT expires_at ASC
```

## Unverified Events
```dataview
TABLE event_name, event_start, venue
FROM "research/events" WHERE verified_by_human = false AND event_end >= date(today)
```
