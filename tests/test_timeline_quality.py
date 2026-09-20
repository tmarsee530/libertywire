import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.event_identity import compare
from scripts.build_storylines import cluster
from scripts.timeline_intelligence import meaningful_updates


FIXTURE = Path(__file__).parent / "fixtures" / "timeline_quality_corpus.json"
NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def report(title, source, minutes, link=None):
    return {
        "title": title,
        "source": source,
        "date": (NOW + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z"),
        "link": link or f"https://{source.lower().replace(' ', '')}.test/{minutes}",
    }


class EventIdentityCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads(FIXTURE.read_text())

    def test_same_event_cases_match(self):
        for left, right in self.corpus["same_event"]:
            with self.subTest(left=left, right=right):
                result = compare(left, right)
                self.assertTrue(result.same_event, result)
                self.assertGreaterEqual(result.confidence, .74)

    def test_distinct_event_cases_do_not_match(self):
        for left, right in self.corpus["different_event"]:
            with self.subTest(left=left, right=right):
                self.assertFalse(compare(left, right).same_event)

    def test_multi_topic_roundup_cannot_bridge_unrelated_event(self):
        stories = [
            {**report("White House bans CNN reporters; parties prepare for midterms", "Source A", 0), "published_epoch": 1},
            {**report("CNN journalists denied White House access", "Source B", 1), "published_epoch": 2},
            {**report("Trump, economic news and the midterms", "Source C", 2), "published_epoch": 3},
            {**report("Canada's Mark Carney leads resistance to Trump", "Source D", 3), "published_epoch": 4},
        ]
        groups = cluster(stories)
        carney = next(group for group in groups if any("Carney" in item["title"] for item in group["stories"]))
        self.assertEqual(len(carney["stories"]), 1)

    def test_real_production_paraphrases_share_event_identity(self):
        pairs = [
            ("NORAD jet intercepts aircraft over Camp David", "NORAD F-16 intercepts aircraft in restricted Camp David airspace"),
            ("CENTCOM says 1B oil barrels passed through Hormuz", "US forces moved over 1 billion oil barrels through Strait of Hormuz: CENTCOM"),
            ("Trump announces AI Force and AI czar", "Trump will form an artificial intelligence force and appoint an AI tsar"),
        ]
        for left, right in pairs:
            with self.subTest(left=left):
                self.assertTrue(compare(left, right).same_event)


class MaterialDevelopmentQualityTests(unittest.TestCase):
    def test_repeated_and_rephrased_fact_becomes_corroboration(self):
        items = [
            report("White House bars CNN reporters from entry", "Source A", 0),
            report("CNN journalists denied White House access", "Source B", 5),
            report("White House blocks CNN journalists at gate", "Source C", 8),
        ]
        updates = meaningful_updates(items)
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["source_count"], 3)

    def test_commentary_does_not_advance_chronology(self):
        items = [
            report("White House bars CNN reporters from entry", "Source A", 0),
            report("Expert says White House CNN ban is a major mistake", "Source B", 10),
            report("Columnist reacts to White House CNN access ban", "Source C", 15),
        ]
        self.assertEqual(len(meaningful_updates(items)), 1)

    def test_numerical_revision_supersedes_earlier_fact(self):
        items = [
            report("Officials report 12 injuries in Orion plant explosion", "Source A", 0),
            report("Officials revise Orion plant explosion injury count to 17", "Source B", 30),
        ]
        updates = meaningful_updates(items)
        self.assertEqual(len(updates), 2)
        self.assertEqual(updates[1]["classification"], "CORRECTION")
        self.assertEqual(updates[1]["supersedes_update_id"], updates[0]["id"])

    def test_republication_does_not_inflate_independent_confirmation(self):
        title = "Agency orders Pine County evacuation after wildfire"
        items = [report(title, "Associated Press", 0), report(title, "Local Gazette", 2)]
        update = meaningful_updates(items)[0]
        self.assertEqual(update["source_count"], 2)
        self.assertEqual(update["independent_source_count"], 1)
        self.assertEqual(update["sources"][1]["role"], "republication")

    def test_distinct_state_change_remains_material(self):
        items = [
            report("Agency investigates Pine County bridge damage", "Source A", 0),
            report("Agency orders Pine County bridge closed", "Source B", 20),
        ]
        self.assertEqual(len(meaningful_updates(items)), 2)

    def test_access_decision_and_enforcement_are_two_phases_not_many_articles(self):
        items = [
            report("Trump announces ban on CNN access to White House", "Source A", 0),
            report("White House bans CNN reporters", "Source B", 4),
            report("CNN reporters turned away as White House ban takes effect", "Source C", 30),
            report("CNN journalists denied White House access at gate", "Source D", 34),
            report("Anchor calls CNN White House ban illegal", "Source E", 40),
        ]
        updates = meaningful_updates(items)
        self.assertEqual(len(updates), 2)
        self.assertEqual([item["source_count"] for item in updates], [2, 2])

    def test_repeated_creation_announcement_is_one_development(self):
        items = [
            report("Trump says US will form AI Force and appoint AI czar", "Source A", 0),
            report("Trump announces new artificial intelligence force and AI czar", "Source B", 4),
            report("Trump vows to create AI Force", "Source C", 8),
        ]
        updates = meaningful_updates(items)
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["source_count"], 3)

    def test_reactions_to_agreement_do_not_manufacture_developments(self):
        items = [
            report("US and Denmark reach Greenland security agreement", "Source A", 0),
            report("Trump confirms Greenland security deal", "Source B", 4),
            report("NATO welcomes Greenland agreement", "Source C", 8),
            report("Denmark expresses optimism over Greenland deal", "Source D", 12),
        ]
        updates = meaningful_updates(items)
        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0]["source_count"], 2)


if __name__ == "__main__":
    unittest.main()
