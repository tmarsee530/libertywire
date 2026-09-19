import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from scripts import build_timelines
from scripts import publish_email_events as pilot


NOW = datetime(2026, 9, 19, 12, tzinfo=timezone.utc)
TIMELINE = "abc123def456"


def update(uid, classification, label="Material fact", sources=2):
    return {"id": uid, "classification": classification, "label": label, "date": "2026-09-19T11:00:00Z", "sources": [{"source": f"Source {n}"} for n in range(sources)]}


def events(updates):
    history={"storylines":[{"id":TIMELINE,"current_title":"Developing story","updates":updates}]}
    return pilot.eligible_events(history,{"ids":[TIMELINE]},NOW)


class EmailPilotEventTests(unittest.TestCase):
    def test_breaking_event_published_once(self):
        result=events([update("u1","BREAKING")]); self.assertEqual(len(result),1); self.assertEqual(result[0]["material_update_id"],"u1")

    def test_major_development_published(self):
        self.assertEqual(len(events([update("u1","MAJOR DEVELOPMENT")])),1)

    def test_meaningful_corroborated_update_published(self):
        self.assertEqual(len(events([update("u1","UPDATE","Court orders 20 evacuations",2)])),1)

    def test_ordinary_update_suppressed(self):
        self.assertEqual(events([update("u1","UPDATE","Officials discuss plans",1)]),[])

    def test_context_suppressed(self):
        self.assertEqual(events([update("u1","CONTEXT")]),[])

    def test_inactive_timeline_suppressed(self):
        history={"storylines":[{"id":TIMELINE,"updates":[update("u1","BREAKING")]}]}
        self.assertEqual(pilot.eligible_events(history,{"ids":[]},NOW),[])

    def test_wording_change_keeps_same_durable_event(self):
        first=events([update("u1","BREAKING","First wording")])[0]
        second=events([update("u1","BREAKING","Edited wording")])[0]
        self.assertEqual((first["timeline_id"],first["material_update_id"]),(second["timeline_id"],second["material_update_id"]))

    def test_canonical_timeline_url_unchanged(self):
        self.assertEqual(events([update("u1","BREAKING")])[0]["canonical_url"],f"https://rallypointnews.com/stories/{TIMELINE}/")

    def test_missing_configuration_is_safe(self):
        with mock.patch.dict("os.environ",{},clear=True): self.assertEqual(pilot.main(),0)

    def test_opt_in_markup_is_explicit_and_hidden_until_configured(self):
        record={"id":TIMELINE,"current_title":"Story","status":"developing","last_seen":"2026-09-19T11:00:00Z","first_seen":"2026-09-19T10:00:00Z","updates":[update("u1","BREAKING")],"current_status":{"summary":"Changed","classification":"BREAKING","as_of":"2026-09-19T11:00:00Z"},"coverage":[]}
        body=build_timelines.follow_enabled_page("<html><head><link rel=\"stylesheet\" href=\"/assets/timeline.css?v=4\"></head><body><div class=\"story-meta\"></div><section class=\"current-status\"></section><a href=\"/sources/\">Sources</a></body></html>",record)
        self.assertIn('data-email-pilot hidden',body);self.assertIn('type="email"',body);self.assertNotIn('checked',body)

    def test_public_config_keeps_unconfigured_pilot_disabled(self):
        config=json.loads((Path(__file__).parents[1]/"data/email_pilot_config.json").read_text());self.assertFalse(config["enabled"])

    def test_public_artifacts_contain_no_subscriber_address(self):
        root=Path(__file__).parents[1]
        for relative in ("data/email_delivery_health.json","data/email_pilot_config.json","data/notification_health.json","data/notification_queue.json"):
            self.assertNotIn("reader@example.com",(root/relative).read_text())


class EmailPilotSchemaTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        migration=(Path(__file__).parents[1]/"email-service/migrations/0001_email_pilot.sql").read_text()
        self.db.executescript(migration)
        self.db.execute("INSERT INTO subscribers(id,email_hash,email_ciphertext,email_iv,status,created_at) VALUES('p1','hash','cipher','iv','pending','2026-09-19T00:00:00Z')")

    def tearDown(self): self.db.close()

    def test_address_destination_is_ciphertext_not_plain_email_column(self):
        columns={row[1] for row in self.db.execute("PRAGMA table_info(subscribers)")}
        self.assertIn("email_ciphertext",columns);self.assertNotIn("email",columns)

    def test_duplicate_subscriber_hash_is_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO subscribers(id,email_hash,email_ciphertext,email_iv,status,created_at) VALUES('p2','hash','cipher2','iv2','pending','2026-09-19T00:00:00Z')")

    def test_duplicate_subscriber_timeline_is_rejected(self):
        values=("s1","p1",TIMELINE,"pending","2026-09-19T00:00:00Z")
        self.db.execute("INSERT INTO subscriptions(id,subscriber_id,timeline_id,status,followed_at) VALUES(?,?,?,?,?)",values)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO subscriptions(id,subscriber_id,timeline_id,status,followed_at) VALUES('s2','p1',?,'pending','2026-09-19T00:00:00Z')",(TIMELINE,))

    def test_duplicate_subscription_event_delivery_is_rejected(self):
        self.db.execute("UPDATE subscribers SET status='active' WHERE id='p1'")
        self.db.execute("INSERT INTO subscriptions(id,subscriber_id,timeline_id,status,followed_at) VALUES('s1','p1',?,'active','2026-09-19T00:00:00Z')",(TIMELINE,))
        self.db.execute("INSERT INTO notification_events(id,timeline_id,material_update_id,title,classification,summary,canonical_url,published_at,significance_reason,created_at) VALUES('e1',?,'u1','Story','BREAKING','Changed',?,'2026-09-19T01:00:00Z','breaking','2026-09-19T01:00:00Z')",(TIMELINE,f"https://rallypointnews.com/stories/{TIMELINE}/"))
        self.db.execute("INSERT INTO email_deliveries(id,dedupe_key,subscriber_id,subscription_id,event_id,status,not_before,created_at) VALUES('d1','key1','p1','s1','e1','pending','2026-09-19T01:00:00Z','2026-09-19T01:00:00Z')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO email_deliveries(id,dedupe_key,subscriber_id,subscription_id,event_id,status,not_before,created_at) VALUES('d2','key2','p1','s1','e1','pending','2026-09-19T01:00:00Z','2026-09-19T01:00:00Z')")

    def test_unconfirmed_and_unsubscribed_records_are_not_active(self):
        self.db.execute("INSERT INTO subscriptions(id,subscriber_id,timeline_id,status,followed_at) VALUES('s1','p1',?,'pending','2026-09-19T00:00:00Z')",(TIMELINE,))
        active=self.db.execute("SELECT COUNT(*) FROM subscriptions s JOIN subscribers p ON p.id=s.subscriber_id WHERE s.status='active' AND p.status='active'").fetchone()[0]
        self.assertEqual(active,0)

    def test_unsubscribe_cancels_pending_before_delivery(self):
        self.db.execute("UPDATE subscribers SET status='active' WHERE id='p1'")
        self.db.execute("INSERT INTO subscriptions(id,subscriber_id,timeline_id,status,followed_at) VALUES('s1','p1',?,'active','2026-09-19T00:00:00Z')",(TIMELINE,))
        self.db.execute("INSERT INTO notification_events(id,timeline_id,material_update_id,title,classification,summary,canonical_url,published_at,significance_reason,created_at) VALUES('e1',?,'u1','Story','BREAKING','Changed',?,'2026-09-19T01:00:00Z','breaking','2026-09-19T01:00:00Z')",(TIMELINE,f"https://rallypointnews.com/stories/{TIMELINE}/"))
        self.db.execute("INSERT INTO email_deliveries(id,dedupe_key,subscriber_id,subscription_id,event_id,status,not_before,created_at) VALUES('d1','key1','p1','s1','e1','pending','2026-09-19T01:00:00Z','2026-09-19T01:00:00Z')")
        self.db.execute("UPDATE subscriptions SET status='unsubscribed' WHERE id='s1'")
        self.db.execute("UPDATE email_deliveries SET status='cancelled' WHERE subscription_id='s1' AND status IN ('pending','retry')")
        self.assertEqual(self.db.execute("SELECT status FROM email_deliveries WHERE id='d1'").fetchone()[0],"cancelled")


if __name__ == "__main__": unittest.main()
