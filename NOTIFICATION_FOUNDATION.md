# Priority 4B notification foundation

Delivery is intentionally disabled. The newsroom can determine whether a server-side follow has a genuinely new material development, create one idempotent candidate, and expose aggregate operational state without sending email or push.

## Data contracts

`data/server_follows.json` is the current file adapter. A follow contains:

- `id`: opaque durable follow ID;
- `subject_ref`: opaque `{type, id}` reference (`anonymous_device`, `account`, `email_subscriber`, or `push_subscriber`); never an address or push token here;
- `timeline_id` and `followed_at`;
- `baseline_material_update_id`, `last_delivered_material_update_id`, and optional `last_acknowledged_material_update_id`;
- `channels`: explicit eligibility booleans for `email` and `web_push`;
- `status`: `active` or `unfollowed`;
- `schema_version`.

The file is empty in production because Priority 4A follows remain browser-local. No local follows are uploaded and no anonymous identity is created. `exportFollowsForSync()` only prepares a minimal payload when a future, explicit opt-in flow invokes it; it performs no network request and excludes read history.

Anonymous identity creation is deliberately deferred. When a reader explicitly enables a delivery channel, the server may issue a random, resettable opaque UUID and store it locally; it must not use fingerprinting, IP-based identity, cross-site data, or silent identity stitching. Clearing/resetting that identifier must be supported, and the channel subscription—not ordinary reading—must be the reason it exists.

At scale, these records should move to partitioned database tables. Required unique constraints are `(subject_id, timeline_id)` for active follows and `dedupe_key` for queue items. Personal channel destinations belong in separately encrypted identity/channel tables. Queue workers should claim rows with transactional leases and write delivery receipts before retrying.

## Candidate and queue semantics

`scripts/build_notification_foundation.py` reads published timeline update objects, not HTML, homepage order, or timestamps. The idempotency key is SHA-256 of `follow_id + timeline_id + durable_material_update_id + policy_version`. Repeated refreshes, wording edits, source additions, and reclassification cannot create a second item for the same follow/update.

Default significance policy:

- `BREAKING`: eligible;
- `MAJOR DEVELOPMENT`: eligible;
- `UPDATE`: eligible only when it contains a decisive state/number signal and at least two independent source families;
- `CONTEXT`: suppressed.

Every first evaluation is recorded as `pending` or `suppressed`. A suppressed item remains suppressed if only metadata later changes. Inactive/archived timelines create no candidates, and becoming inactive is not an event.

Queue records include event/follow/timeline/update IDs, classification, reason, channel eligibility, status, attempts, error, delivered time, and dedupe key. `delivery_enabled` is hard-disabled. No provider, permission prompt, address collection, or delivery code exists.

## Observability and failure isolation

`data/notification_health.json` reports candidates, suppressions, dedupes, classification counts, duplicate-key checks, backlog, oldest age, and processing errors. `/notification-health/` is unindexed and displays aggregate/candidate state without subject references. The notification stage runs after publication. Failure produces an auxiliary warning and preserves last-known-good artifacts; it cannot make core newsroom health critical or stop later publication stages.

Published canonical pages can outlive the bounded working history. The processor therefore treats timelines absent from the active manifest as inactive and creates no event merely for that transition. Before delivery launches, the permanent-archive milestone should provide a durable lookup table for canonical timeline metadata; notification identity must continue to use the stable timeline ID and update ID, not an active-history row.

## Exact delivery milestone

Priority 4B delivery should add one channel first—verified email is recommended—using an opt-in consent flow, encrypted channel destinations, database-backed follow and queue tables, transactional worker leases, rate limits/digests, unsubscribe controls, and delivery receipts. Only after email quality is measured should Web Push permission and subscription storage be added. Durable material-update IDs and the existing dedupe key must remain the sole event identity.
