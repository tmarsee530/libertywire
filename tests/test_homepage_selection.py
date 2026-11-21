import unittest

from scripts.homepage_selection import homepage_eligible


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

    def test_rejects_blank_titles(self):
        self.assertFalse(homepage_eligible("  "))


if __name__ == "__main__":
    unittest.main()
