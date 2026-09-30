# Timeline Semantic Audit

Rally Point's canonical-ownership validator guarantees structural uniqueness. This audit adds a separate, non-mutating semantic quality gate for the published timeline product.

It checks four failure modes:

1. **Current-status drift** — `currentStatus` no longer matches the newest authoritative material development.
2. **Commentary as status** — reaction/opinion accidentally becomes the live state of the event.
3. **Cross-event contamination** — a development is structurally owned by a timeline but does not belong to the same real-world event frame.
4. **Duplicate developments** — separate source URLs produce different durable IDs for substantially the same development.

Run:

```bash
python scripts/audit_timeline_semantics.py
```

Output is written to `data/timeline_semantic_audit.json`.

The audit is intentionally conservative and does not mutate timelines. A high-severity finding means the event should be inspected or covered by a production-derived regression before changing publication logic. This prevents an aggressive cleanup rule from creating false splits.

## Initial production inspection

The 2026-09-30 state index contained 38 authoritative timelines. Structural ownership was healthy, but manual semantic inspection exposed examples of the remaining class of problem: an OpenAI IPO/safety timeline also contained an unrelated Australian government-site incident, and a Jack Smith investigation timeline contained a separate Eric Schmitt/Hawks accusation correction. These are exactly the failures this audit is designed to surface.
