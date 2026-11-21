import unittest

from scripts.homepage_selection import homepage_eligible, homepage_quality, published_publisher_count


class HomepageNewsworthinessTests(unittest.TestCase):
    def test_avoids_commercial_sports_prediction_products(self):
        titles = [
            "Georgia vs. South Carolina prediction, odds, time: Week 12 picks",
            "NFL longshot parlay picks and player props for Week 11",
            "Use FanDuel promo code to get bonus bets",
            "MacBooks rarely go this low — October Prime Day laptop deals",
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertFalse(homepage_eligible(title))

    def test_keeps_material_sports_and_public_interest_news(self):
        titles = [
            "Georgia defeats South Carolina to claim division title",
            "NFL investigating referee after interaction with player",
            "Federal Reserve votes to cut interest rates",
            "Court orders evacuation during California wildfire",
            "President announces major trade agreement",
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertTrue(homepage_eligible(title))

    def test_lead_prefers_verified_publishers_and_breaking_news(self):
        minor = {"importance_score": 22.69}
        material = {"importance_score": 21.87}
        two_publishers = {"status": "developing", "developments": [
            {"sources": [{"source_family": "tmz"}]},
            {"sources": [{"source_family": "page six"}]},
        ]}
        four_publishers = {"status": "breaking", "developments": [
            {"sources": [{"source_family": "npr"}, {"source_family": "american greatness"}]},
            {"sources": [{"source_family": "bbc news"}, {"source_family": "tmz"}]},
        ]}
        self.assertEqual(published_publisher_count(four_publishers), 4)
        self.assertGreater(homepage_quality(material, four_publishers),
                           homepage_quality(minor, two_publishers))

    def test_semantic_risks_do_not_win_top_promotion(self):
        record = {"importance_score": 50}
        published = {"status": "breaking", "developments": [
            {"sources": [{"source_family": "one"}, {"source_family": "two"}]},
        ]}
        baseline = homepage_quality(record, published)
        medium = homepage_quality(record, published, [{"severity": "medium", "type": "possible_cross_event_update"}])
        high = homepage_quality(record, published, [{"severity": "high", "type": "current_status_mismatch"}])
        self.assertEqual(baseline - medium, 10)
        self.assertEqual(high, float("-inf"))
        self.assertEqual(homepage_quality(record, {}), float("-inf"))

    def test_rejects_blank_titles(self):
        self.assertFalse(homepage_eligible("  "))


if __name__ == "__main__":
    unittest.main()
