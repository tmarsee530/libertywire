import unittest
from datetime import datetime, timedelta, timezone

from scripts import build_notification_foundation as notifications
from scripts import run_newsroom


NOW = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
STAMP = NOW.isoformat().replace("+00:00", "Z")
TIMELINE = "abc123def456"


def update(uid, classification, minutes, label=None, sources=2):
    return {
        "id": uid, "classification": classification,
        "label": label or f"Officials confirmed material event {uid}",
        "date": (NOW + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z"),
        "sources": [{"source": f"Source {index}"} for index in range(sources)],
    }


def follow(fid="follow-1", timeline=TIMELINE, status="active", baseline="base", channels=None):
    return {
        "schema_version": 1, "id": fid,
        "subject_ref": {"type": "anonymous_device", "id": "opaque-test-subject"},
        "timeline_id": timeline, "followed_at": STAMP,
        "baseline_material_update_id": baseline,
        "last_delivered_material_update_id": None,
        "last_acknowledged_material_update_id": baseline,
        "channels": channels if channels is not None else {"email": True, "web_push": False},
        "status": status,
    }


def payload(updates, follows=None, active=True, prior=None):
    return notifications.build(
        {"schema_version": 1, "follows": follows if follows is not None else [follow()]},
        {"storylines": [{"id": TIMELINE, "updates": updates}]},
        {"ids": [TIMELINE] if active else []},
        prior or {"items": []}, STAMP,
    )


class SignificanceTests(unittest.TestCase):
    def test_breaking_update_is_candidate(self):
        queue, health = payload([update("base", "CONTEXT", -5), update("breaking", "BREAKING", 5)])
        self.assertEqual(queue["items"][0]["status"], "pending")
        self.assertEqual(queue["items"][0]["material_update_id"], "breaking")
        self.assertEqual(health["candidates_created"], 1)

    def test_major_development_is_candidate(self):
        queue, _ = payload([update("base", "CONTEXT", -5), update("major", "MAJOR DEVELOPMENT", 5)])
        self.assertEqual(queue["items"][0]["significance_reason"], "major_material_development")

    def test_low_significance_update_is_suppressed(self):
        queue, health = payload([update("base", "CONTEXT", -5), update("minor", "UPDATE", 5, "Officials discuss plans", 1)])
        self.assertEqual(queue["items"][0]["status"], "suppressed")
        self.assertEqual(health["candidates_suppressed"], 1)

    def test_context_is_suppressed(self):
        queue, _ = payload([update("base", "CONTEXT", -5), update("context", "CONTEXT", 5)])
        self.assertEqual(queue["items"][0]["significance_reason"], "context_not_notifiable")

    def test_meaningful_corroborated_update_can_qualify(self):
        eligible, reason = notifications.notification_significance(update("u", "UPDATE", 1, "Court orders 20 evacuations", 2))
        self.assertTrue(eligible)
        self.assertEqual(reason, "meaningful_update_independently_corroborated")


class IdempotencyTests(unittest.TestCase):
    def test_same_update_processed_repeatedly_is_idempotent(self):
        updates = [update("base", "CONTEXT", -5), update("new", "BREAKING", 5)]
        first, _ = payload(updates)
        second, health = payload(updates, prior=first)
        self.assertEqual(len(second["items"]), 1)
        self.assertEqual(health["candidates_created"], 0)
        self.assertEqual(health["candidates_deduped"], 1)
        self.assertEqual(health["duplicate_pending_keys"], 0)

    def test_wording_corroboration_and_reclassification_do_not_duplicate(self):
        original = [update("base", "CONTEXT", -5), update("stable", "BREAKING", 5, "Agency orders evacuation", 1)]
        first, _ = payload(original)
        changed = [update("base", "CONTEXT", -5), update("stable", "MAJOR DEVELOPMENT", 5, "Agency confirms and orders evacuation", 3)]
        second, health = payload(changed, prior=first)
        self.assertEqual(len(second["items"]), 1)
        self.assertEqual(health["candidates_created"], 0)
        self.assertEqual(health["candidates_deduped"], 1)

    def test_queue_key_is_stable_and_follower_specific(self):
        one = notifications.queue_key("f1", TIMELINE, "u1")
        self.assertEqual(one, notifications.queue_key("f1", TIMELINE, "u1"))
        self.assertNotEqual(one, notifications.queue_key("f2", TIMELINE, "u1"))


class FollowModelTests(unittest.TestCase):
    def test_one_follower_can_follow_multiple_stories(self):
        second = "def456abc123"
        follows = [follow("f1"), follow("f2", second)]
        history = {"storylines": [
            {"id": TIMELINE, "updates": [update("base", "CONTEXT", -5), update("u1", "BREAKING", 5)]},
            {"id": second, "updates": [update("base", "CONTEXT", -5), update("u2", "MAJOR DEVELOPMENT", 5)]},
        ]}
        queue, _ = notifications.build({"follows": follows}, history, {"ids": [TIMELINE, second]}, {"items": []}, STAMP)
        self.assertEqual({x["timeline_id"] for x in queue["items"]}, {TIMELINE, second})

    def test_multiple_followers_one_story_create_distinct_work(self):
        queue, _ = payload([update("base", "CONTEXT", -5), update("u", "BREAKING", 5)], follows=[follow("f1"), follow("f2")])
        self.assertEqual(len(queue["items"]), 2)
        self.assertEqual(len({x["dedupe_key"] for x in queue["items"]}), 2)

    def test_unfollowed_story_creates_no_candidate(self):
        queue, _ = payload([update("base", "CONTEXT", -5), update("u", "BREAKING", 5)], follows=[follow(status="unfollowed")])
        self.assertEqual(queue["items"], [])

    def test_inactive_story_creates_no_false_candidate(self):
        queue, health = payload([update("base", "CONTEXT", -5), update("u", "BREAKING", 5)], active=False)
        self.assertEqual(queue["items"], [])
        self.assertEqual(health["observations"][0]["reason"], "timeline_inactive_or_archived")

    def test_follow_without_channel_is_suppressed(self):
        queue, _ = payload([update("base", "CONTEXT", -5), update("u", "BREAKING", 5)], follows=[follow(channels={"email": False, "web_push": False})])
        self.assertEqual(queue["items"][0]["status"], "suppressed")
        self.assertEqual(queue["items"][0]["significance_reason"], "no_delivery_channel_eligible")


class ReliabilityTests(unittest.TestCase):
    def test_queue_backlog_health_is_observable(self):
        _, health = payload([update("base", "CONTEXT", -5), update("u", "BREAKING", 5)])
        self.assertEqual(health["queue_backlog"], 1)
        self.assertEqual(health["processing_errors"], 0)
        self.assertFalse(health["delivery_enabled"])
        self.assertEqual(health["metrics"]["notification_candidate_created"], 1)
        self.assertEqual(health["metrics"]["notification_queue_created"], 1)

    def test_notification_failure_is_auxiliary_not_core_critical(self):
        signals = {
            "ingestion": {"age_minutes": 1, "successful_sources": 80, "source_failure_pct": 0},
            "content": {"last_story_age_minutes": 1}, "fast_path": {},
            "stages": {"notifications": {"label": "Notification foundation", "status": "FAILED", "attempts": 3, "consecutive_failures": 8, "fallback": "last-known-good"}},
        }
        state, alerts = run_newsroom.classify(signals)
        self.assertEqual(state, "DEGRADED")
        self.assertEqual(alerts[0]["severity"], "WARNING")


if __name__ == "__main__":
    unittest.main()
