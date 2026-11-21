import unittest

from scripts.audit_timeline_semantics import audit_timeline, build_report


class TimelineSemanticAuditTests(unittest.TestCase):
    def development(self, sid, label, classification="UPDATE"):
        return {"id": sid, "label": label, "classification": classification}

    def test_current_status_must_match_latest_material_development(self):
        timeline = {"title":"Agency orders Pine County evacuation after wildfire","currentStatus":"Officials are monitoring conditions.","developments":[self.development("new","Agency orders Pine County evacuation after wildfire")]}
        self.assertIn("current_status_mismatch", {item["type"] for item in audit_timeline("one", timeline)})

    def test_cross_event_update_is_flagged(self):
        timeline = {"title":"Bears quarterback exits with hamstring injury","currentStatus":"Bears quarterback exits with hamstring injury.","developments":[self.development("one","Bears quarterback exits with hamstring injury"),self.development("two","Federal Reserve cuts interest rates after September meeting")]}
        self.assertIn("possible_cross_event_update", {item["type"] for item in audit_timeline("one", timeline)})

    def test_semantically_repeated_developments_are_flagged(self):
        timeline = {"title":"White House bars CNN reporters from entry","currentStatus":"White House bars CNN reporters from entry.","developments":[self.development("one","White House bars CNN reporters from entry"),self.development("two","White House bars CNN reporters from entry today")]}
        self.assertIn("possible_duplicate_development", {item["type"] for item in audit_timeline("one", timeline)})

    def test_unrelated_named_fixtures_are_high_severity(self):
        title = "Georgia vs. South Carolina prediction, odds, time: Week 12"
        timeline = {"title": title, "currentStatus": title,
                    "developments": [
                        self.development("current", title),
                        self.development("old", "Alabama vs. Georgia prediction, odds, time: Week 6"),
                    ]}
        findings = audit_timeline("sports", timeline)
        mismatch = [item for item in findings if item["type"] == "different_named_sports_fixture"]
        self.assertEqual(len(mismatch), 1)
        self.assertEqual(mismatch[0]["severity"], "high")
        self.assertEqual(mismatch[0]["update_id"], "old")

    def test_october_prime_day_shopping_is_high_severity_in_october_seven_story(self):
        title = "Three Years After October 7, The Truth Is Out"
        timeline = {"title": title, "currentStatus": title, "developments": [
            self.development("real", title),
            self.development("ad", "October Prime Day laptop deals include MacBooks up to 43% off"),
        ]}
        findings = audit_timeline("october-seven", timeline)
        blocked = [item for item in findings if item["type"] == "unrelated_commercial_retail_offer"]
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0]["severity"], "high")
        self.assertEqual(blocked[0]["update_id"], "ad")

    def test_retail_reporting_is_not_a_false_positive(self):
        title = "Prime Day organizers report stronger holiday shopping sales"
        timeline = {"title": title, "currentStatus": title, "developments": [
            self.development("real", title),
            self.development("deal", "October Prime Day laptop deals include discounts"),
        ]}
        findings = audit_timeline("retail", timeline)
        self.assertNotIn("unrelated_commercial_retail_offer", {x["type"] for x in findings})

    def test_clean_timeline_stays_healthy(self):
        payload = {"generated_at":"2026-09-29T00:00:00Z","timelines":{"one":{"title":"Agency orders Pine County evacuation after wildfire","currentStatus":"Agency orders Pine County evacuation after wildfire.","url":"/stories/one/","developments":[self.development("one","Agency orders Pine County evacuation after wildfire")]}}}
        report = build_report(payload)
        self.assertEqual(report["status"], "HEALTHY")
        self.assertEqual(report["high_severity_findings"], 0)


if __name__ == "__main__":
    unittest.main()
