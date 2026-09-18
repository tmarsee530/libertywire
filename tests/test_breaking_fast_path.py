import unittest
from datetime import datetime, timedelta, timezone

from scripts.build_breaking_fast_path import build_payload, evaluate_clusters


NOW = datetime(2026, 9, 18, 12, 0, tzinfo=timezone.utc)


def story(title, source, minutes=2, link=None):
    return {
        "title": title, "source": source,
        "date": (NOW - timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z"),
        "link": link or f"https://example.test/{source}/{abs(hash(title))}",
    }


class BreakingFastPathTests(unittest.TestCase):
    def test_official_high_urgency_development_qualifies(self):
        items = [story("FBI declares emergency warning after attack", "FBI National Press Releases")]
        candidate = evaluate_clusters(items, [], NOW)[0]
        self.assertTrue(candidate["eligible"])
        self.assertEqual(candidate["reason"], "trusted_primary_source")
        self.assertEqual(candidate["source_tier"], 1)

    def test_unconfirmed_claim_is_held_even_from_primary_source(self):
        items = [story("FBI: unconfirmed report of emergency attack", "FBI National Press Releases")]
        candidate = evaluate_clusters(items, [], NOW)[0]
        self.assertFalse(candidate["eligible"])
        self.assertEqual(candidate["reason"], "held_unconfirmed")
        self.assertIn("unconfirmed_claim", candidate["risk_flags"])

    def test_two_independent_established_sources_can_qualify(self):
        title = "Supreme Court issues emergency ruling after major attack"
        items = [
            story(title, "BBC News", 3, "https://bbc.test/ruling"),
            story("Supreme Court emergency ruling follows major attack", "NPR", 4, "https://npr.test/ruling"),
        ]
        candidates = evaluate_clusters(items, [], NOW)
        self.assertEqual(len(candidates), 1)
        self.assertTrue(candidates[0]["eligible"])
        self.assertEqual(candidates[0]["reason"], "independently_corroborated")
        self.assertEqual(candidates[0]["trusted_independent_source_count"], 2)

    def test_low_signal_single_source_stays_on_normal_path(self):
        candidate = evaluate_clusters([story("Analysis: what the new season means", "BBC News")], [], NOW)[0]
        self.assertFalse(candidate["eligible"])
        self.assertEqual(candidate["path"], "normal")

    def test_existing_timeline_interest_is_scored_and_matched(self):
        items = [story("Federal Reserve declares emergency rate decision", "Federal Reserve Press Releases")]
        timelines = [{"id": "rates-1", "title": "Federal Reserve emergency rate decision"}]
        candidate = evaluate_clusters(items, timelines, NOW)[0]
        self.assertEqual(candidate["matched_storyline_id"], "rates-1")
        self.assertEqual(candidate["score_components"]["existing_timeline_interest"], 8)

    def test_duplicate_metrics_and_normal_feed_integrity(self):
        title = "NASA declares emergency after major outage"
        stories = [
            story(title, "NASA News", 1, "https://nasa.test/1"),
            story("NASA declares emergency following major outage", "BBC News", 2, "https://bbc.test/1"),
            story("Local sports team announces roster", "Local Desk", 3, "https://local.test/1"),
        ]
        payload = build_payload({"stories": stories}, {"storylines": []}, NOW)
        self.assertEqual(len(stories), 3)
        self.assertEqual(payload["metrics"]["reports_evaluated"], 3)
        self.assertEqual(payload["metrics"]["duplicate_reports_suppressed"], 1)
        self.assertTrue(payload["policy"]["normal_path_preserved"])

    def test_stale_reports_are_not_fast_path_candidates(self):
        stale = story("FBI declares emergency warning", "FBI National Press Releases", 300)
        self.assertEqual(evaluate_clusters([stale], [], NOW), [])


if __name__ == "__main__":
    unittest.main()
