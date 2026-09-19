import unittest

from scripts import build_distribution_candidates as dist


class DistributionCandidateTests(unittest.TestCase):
    def test_same_event_dedupe_suppresses_near_duplicate_promotion(self):
        left = {"title": "CNN and Politico reporters barred from White House after Trump ban"}
        right = {"title": "Politico, CNN reporters denied White House access after ban"}
        self.assertTrue(dist.same_event(left, right))

    def test_distinct_events_are_not_deduped(self):
        left = {"title": "CNN reporters barred from White House after Trump ban"}
        right = {"title": "Federal Reserve cuts interest rates by quarter point"}
        self.assertFalse(dist.same_event(left, right))

    def test_tracked_urls_are_platform_specific(self):
        x = dist.tracked_url("abc123def456", "x")
        facebook = dist.tracked_url("abc123def456", "facebook")
        self.assertIn("utm_source=x", x)
        self.assertIn("utm_source=facebook", facebook)
        self.assertIn("utm_campaign=live_timeline", x)
        self.assertNotEqual(x, facebook)

    def test_dedupe_keeps_first_ranked_candidate(self):
        items = [
            {"timeline_id": "one", "title": "CNN and Politico reporters barred from White House after Trump ban"},
            {"timeline_id": "two", "title": "Politico, CNN reporters denied White House access after ban"},
        ]
        selected, suppressed = dist.dedupe_events(items)
        self.assertEqual([x["timeline_id"] for x in selected], ["one"])
        self.assertEqual(suppressed[0]["duplicate_of"], "one")


if __name__ == "__main__":
    unittest.main()
