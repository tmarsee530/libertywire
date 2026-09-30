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

    def test_clean_timeline_stays_healthy(self):
        payload = {"generated_at":"2026-09-29T00:00:00Z","timelines":{"one":{"title":"Agency orders Pine County evacuation after wildfire","currentStatus":"Agency orders Pine County evacuation after wildfire.","url":"/stories/one/","developments":[self.development("one","Agency orders Pine County evacuation after wildfire")]}}}
        report = build_report(payload)
        self.assertEqual(report["status"], "HEALTHY")
        self.assertEqual(report["high_severity_findings"], 0)


if __name__ == "__main__":
    unittest.main()
