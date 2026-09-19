PRAGMA foreign_keys = ON;

CREATE TABLE subscribers (
  id TEXT PRIMARY KEY,
  email_hash TEXT NOT NULL UNIQUE,
  email_ciphertext TEXT NOT NULL,
  email_iv TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','active','unsubscribed','suppressed')),
  created_at TEXT NOT NULL,
  confirmation_sent_at TEXT,
  confirmed_at TEXT,
  unsubscribed_at TEXT,
  suppression_reason TEXT,
  schema_version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE subscriptions (
  id TEXT PRIMARY KEY,
  subscriber_id TEXT NOT NULL REFERENCES subscribers(id),
  timeline_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','active','unsubscribed')),
  followed_at TEXT NOT NULL,
  baseline_material_update_id TEXT,
  last_delivered_material_update_id TEXT,
  last_acknowledged_material_update_id TEXT,
  confirmed_at TEXT,
  unsubscribed_at TEXT,
  last_sent_at TEXT,
  schema_version INTEGER NOT NULL DEFAULT 1,
  UNIQUE(subscriber_id, timeline_id)
);

CREATE TABLE consent_tokens (
  token_hash TEXT PRIMARY KEY,
  subscriber_id TEXT NOT NULL REFERENCES subscribers(id),
  subscription_id TEXT NOT NULL REFERENCES subscriptions(id),
  purpose TEXT NOT NULL CHECK (purpose = 'verify_email'),
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  used_at TEXT
);

CREATE TABLE notification_events (
  id TEXT PRIMARY KEY,
  timeline_id TEXT NOT NULL,
  material_update_id TEXT NOT NULL,
  title TEXT NOT NULL,
  classification TEXT NOT NULL,
  summary TEXT NOT NULL,
  canonical_url TEXT NOT NULL,
  published_at TEXT NOT NULL,
  significance_reason TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(timeline_id, material_update_id)
);

CREATE TABLE email_deliveries (
  id TEXT PRIMARY KEY,
  dedupe_key TEXT NOT NULL UNIQUE,
  subscriber_id TEXT NOT NULL REFERENCES subscribers(id),
  subscription_id TEXT NOT NULL REFERENCES subscriptions(id),
  event_id TEXT NOT NULL REFERENCES notification_events(id),
  status TEXT NOT NULL CHECK (status IN ('pending','processing','retry','sent','failed','cancelled','suppressed')),
  attempts INTEGER NOT NULL DEFAULT 0,
  not_before TEXT NOT NULL,
  lease_until TEXT,
  created_at TEXT NOT NULL,
  provider_message_id TEXT UNIQUE,
  last_error_code TEXT,
  last_error TEXT,
  delivered_at TEXT,
  failed_at TEXT,
  click_at TEXT,
  UNIQUE(subscription_id, event_id)
);

CREATE TABLE rate_limits (
  key TEXT NOT NULL,
  window_start TEXT NOT NULL,
  count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY(key, window_start)
);

CREATE TABLE provider_events (
  provider_event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  received_at TEXT NOT NULL,
  processed_at TEXT
);

CREATE TABLE email_metrics (
  id TEXT PRIMARY KEY,
  event_name TEXT NOT NULL,
  subscriber_ref TEXT,
  timeline_id TEXT,
  delivery_id TEXT,
  event_at TEXT NOT NULL,
  metadata_json TEXT
);

CREATE INDEX delivery_work ON email_deliveries(status, not_before, lease_until);
CREATE INDEX subscriptions_by_timeline ON subscriptions(timeline_id, status);
CREATE INDEX deliveries_by_subscriber ON email_deliveries(subscriber_id, status);
