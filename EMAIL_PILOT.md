# Priority 4B email-delivery pilot

The pilot is implemented but remains off until the owner completes provider, Cloudflare, and DNS authorization. `data/email_pilot_config.json` must stay `enabled: false` and the Worker variable `DELIVERY_ENABLED` must stay `false` until the checklist below passes. Local `rp-follows-v1` follows remain the browser source of truth and are never uploaded in bulk.

## Architecture

- GitHub Pages renders an optional email form only after the reader explicitly follows that one timeline and the pilot config is enabled.
- `alerts.rallypointnews.com` routes to a Cloudflare Worker. D1 stores subscribers, per-story subscriptions, verification tokens, eligible events, delivery leases/receipts, suppressions, rate-limit counters, provider webhook IDs, and privacy-safe metrics.
- Addresses are normalized, keyed by an HMAC hash for uniqueness, and stored as AES-256-GCM ciphertext with a random IV. Raw addresses never enter GitHub, public diagnostics, GA4, or application logs.
- Every story subscription requires a 24-hour double-opt-in token, even when the same address previously confirmed a different story.
- The newsroom adapter submits only events already approved by the Priority 4B significance policy. It reads structured material updates, never HTML or page-change signals. The ingest secret authenticates this one-way event ledger.
- D1 unique constraints cover email hash, subscriber/timeline, timeline/update, subscription/event, delivery dedupe key, provider message ID, and provider webhook ID.
- A two-minute scheduled Worker leases pending rows. Resend receives the queue dedupe key as its idempotency key. Transient failures back off up to five attempts; permanent failures stop immediately. A newer pending development for the same story suppresses an older unsent burst.
- Unsubscribe links are HMAC-signed and purpose-bound. One story or all alerts can be stopped without login. Pending/retry rows are cancelled immediately; browser-local follow/read state is untouched.
- Resend bounce/complaint webhooks are signature checked and deduplicated by `svix-id`; hard bounce or complaint suppresses the destination and cancels pending mail.

## Provider choice

Resend is used only as a transactional delivery provider. It supports API idempotency, verified sending domains, provider message IDs, HTTPS webhooks, and bounce/complaint events without requiring a newsletter platform. Cloudflare Workers and D1 fit the existing static site with a small separately deployable service, transactional SQL constraints, scheduled processing, and no account system.

## Required owner-controlled setup

1. Create or select a Cloudflare account for `rallypointnews.com` and create D1 database `rally-point-email`.
2. Replace `REPLACE_WITH_D1_DATABASE_ID` in `email-service/wrangler.toml`, run `npm run migrate`, and route the Worker to `alerts.rallypointnews.com`.
3. Create independent high-entropy Worker secrets with `wrangler secret put`:
   - `RESEND_API_KEY`
   - `RESEND_WEBHOOK_SECRET`
   - `EMAIL_ENCRYPTION_KEY` (base64 of exactly 32 random bytes)
   - `EMAIL_HASH_SECRET`
   - `TOKEN_SECRET`
   - `RATE_LIMIT_SECRET`
   - `INGEST_SECRET`
4. In Resend, verify the dedicated sending subdomain `notify.rallypointnews.com`. Publish the exact SPF, DKIM, and return-path records Resend supplies. Publish DMARC for that subdomain, beginning with monitoring (`p=none`) and moving to enforcement only after real alignment reports are clean. Do not copy example DNS values.
5. Change `EMAIL_FROM` to `Rally Point News <alerts@notify.rallypointnews.com>`. Use `newsroom@rallypointnews.com` as reply-to only if that mailbox actually exists and is monitored; otherwise remove the reply-to variable and field.
6. Register `https://alerts.rallypointnews.com/v1/webhooks/resend` in Resend for bounce, complaint, delivery, failure, and delay events. Store its signing secret only as `RESEND_WEBHOOK_SECRET`.
7. Add GitHub Actions secrets `EMAIL_PILOT_API_URL=https://alerts.rallypointnews.com` and `EMAIL_PILOT_INGEST_SECRET` with the same value as the Worker ingest secret. Add `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` only if GitHub is authorized to deploy the Worker.
8. Deploy with the `Email Pilot Service` workflow or Wrangler. Keep `DELIVERY_ENABLED=false` while testing double opt-in, one controlled eligible event, dedupe, email rendering, canonical click-through, both unsubscribe scopes, webhook suppression, and public diagnostic redaction with an owner-controlled address.
9. After those checks pass, set the Worker `DELIVERY_ENABLED=true`, change `data/email_pilot_config.json` to `enabled: true`, merge that single configuration change, and confirm the normal maintenance workflow succeeds.

Domain verification, DNS authentication, secret creation, the owner-controlled test address, and the first real send cannot be completed safely without owner authorization. Delivery must not be represented as active before those steps are verified.

## Event definitions

- `email_opt_in_started`: browser submits the explicit per-story form; GA4 receives only `timeline_id`.
- `email_opt_in_confirmed`: a valid unused verification token activates the one story subscription; stored internally with opaque references.
- `email_notification_queued`: a new foundation event creates one or more unique delivery rows.
- `email_notification_sent`: Resend accepts one leased delivery and returns a provider ID.
- `email_notification_failed`: one transient retry or terminal failure is recorded with an opaque delivery reference.
- `email_notification_unsubscribed`: the signed story/all action is applied.
- `email_notification_click`: the signed redirect is used for the first time.

No metric includes an address. Refreshes, rerenders, webhook replays, repeated clicks, and duplicate event ingestion are idempotent.

## Deliberately deferred

Web push, accounts, cross-device UI, digests, recommendations, premium alerts, marketing newsletters, monetization, and broad distribution remain out of scope. Before a large marketing-email program, obtain a focused legal/compliance review and add documented retention/deletion periods; this pilot is limited to requested transactional story alerts.
