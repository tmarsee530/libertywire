import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.build_breaking_fast_path import build_payload, evaluate_clusters
from scripts import build_storylines as storyline_builder
from scripts import run_newsroom


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

    def test_brand_variants_do_not_count_as_independent_confirmations(self):
        title = "Supreme Court issues emergency ruling after major attack"
        items = [
            story(title, "Fox News", 3, "https://fox.test/ruling"),
            story("Supreme Court emergency ruling follows major attack", "Fox News Politics", 4, "https://fox.test/politics/ruling"),
        ]
        candidate = evaluate_clusters(items, [], NOW)[0]
        self.assertFalse(candidate["eligible"])
        self.assertEqual(candidate["trusted_independent_source_count"], 1)

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

    def _run_storyline_builder(self, fast_payload=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            date = (NOW - timedelta(minutes=2)).isoformat().replace("+00:00", "Z")
            link = "https://fbi.test/emergency"
            news = {"stories": [{
                "title": "FBI declares emergency warning after attack",
                "source": "FBI National Press Releases", "link": link,
                "date": date, "published_epoch": (NOW - timedelta(minutes=2)).timestamp(),
            }]}
            (root / "news.json").write_text(json.dumps(news))
            (root / "history.json").write_text(json.dumps({"storylines": []}))
            if fast_payload is not None:
                (root / "fast.json").write_text(json.dumps(fast_payload))
            old = (storyline_builder.NEWS, storyline_builder.OUT, storyline_builder.HISTORY, storyline_builder.FAST)
            try:
                storyline_builder.NEWS = root / "news.json"
                storyline_builder.OUT = root / "storylines.json"
                storyline_builder.HISTORY = root / "history.json"
                storyline_builder.FAST = root / "fast.json"
                storyline_builder.main()
                return json.loads(storyline_builder.OUT.read_text()), link
            finally:
                storyline_builder.NEWS, storyline_builder.OUT, storyline_builder.HISTORY, storyline_builder.FAST = old

    def test_fast_candidate_is_promoted_by_normal_storyline_publisher(self):
        detected = NOW.isoformat().replace("+00:00", "Z")
        payload, link = self._run_storyline_builder({"generated_at": datetime.now(timezone.utc).isoformat(), "candidates": [{
            "eligible": True, "urgency_score": 88, "reason": "trusted_primary_source",
            "detected_at": detected, "primary_source_link": "https://fbi.test/emergency",
            "corroborating_links": ["https://fbi.test/emergency"],
        }]})
        item = payload["storylines"][0]
        self.assertTrue(item["fast_path"])
        self.assertEqual(item["status"], "breaking")
        self.assertEqual(item["urgency_score"], 88)
        self.assertEqual(item["coverage"][0]["link"], link)

    def test_normal_storyline_ingestion_still_works_without_fast_artifact(self):
        payload, _ = self._run_storyline_builder()
        self.assertEqual(payload["storyline_count"], 1)
        self.assertFalse(payload["storylines"][0]["fast_path"])
        self.assertEqual(payload["fast_path_count"], 0)

    def test_stale_fast_artifact_fails_safe_to_normal_path(self):
        stale = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
        payload, _ = self._run_storyline_builder({"generated_at": stale, "candidates": [{
            "eligible": True, "urgency_score": 99, "reason": "trusted_primary_source",
            "primary_source_link": "https://fbi.test/emergency",
            "corroborating_links": ["https://fbi.test/emergency"],
        }]})
        self.assertFalse(payload["storylines"][0]["fast_path"])
        self.assertEqual(payload["fast_path_count"], 0)

    def test_health_does_not_count_valid_editorial_suppression_as_a_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"; data.mkdir()
            link = "https://news.test/one-fact"
            fixtures = {
                "news.json": {"source_count": 80, "healthy_source_count": 80, "failed_sources": [], "story_count": 1},
                "storylines.json": {"storylines": [{"id": "story-1", "source_family_count": 3, "coverage": [{"link": link}]}]},
                "history.json": {"storylines": [{"id": "story-1", "max_source_family_count": 3, "material_update_count": 1, "coverage": [{"link": link}, {"link": "https://b.test/1"}, {"link": "https://c.test/1"}]}]},
                "published_timelines.json": {"ids": [], "count": 0},
                "breaking_fast_path.json": {"metrics": {"fast_path_events": 1}, "candidates": [{"id": "fast-1", "eligible": True, "primary_source_link": link, "corroborating_links": [link]}]},
            }
            for name, payload in fixtures.items(): (data / name).write_text(json.dumps(payload))
            old_data, old_fast = run_newsroom.DATA, run_newsroom.FAST_PATH
            try:
                run_newsroom.DATA, run_newsroom.FAST_PATH = data, data / "breaking_fast_path.json"
                signals = run_newsroom.build_signals({}, NOW, {})
            finally:
                run_newsroom.DATA, run_newsroom.FAST_PATH = old_data, old_fast
            self.assertEqual(signals["fast_path"]["publication_outcomes"]["editorially_suppressed"], 1)
            self.assertEqual(signals["fast_path"]["true_missed_fast_path_events"], 0)
            _, alerts = run_newsroom.classify(signals)
            self.assertNotIn("FAST_PATH_PUBLICATION_GAP", {x["code"] for x in alerts})


if __name__ == "__main__":
    unittest.main()
