import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.event_identity import compare
from scripts.build_storylines import cluster
from scripts.canonical_ownership import canonical_groups, enforce_unique_updates, violations
from scripts.timeline_intelligence import meaningful_updates, serializable_model


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

    def test_mamdani_meeting_does_not_merge_with_us_china_negotiations(self):
        self.assertFalse(compare(
            "NYC Mayor Zohran Mamdani and Trump to meet again this week",
            "Top US and China trade negotiators meet in New York ahead of Trump-Xi summit",
        ).same_event)

    def test_player_injury_does_not_merge_with_unrelated_nfl_products(self):
        injury = "Bears QB Caleb Williams exits against Vikings after non-contact hamstring injury"
        unrelated = [
            "Vikings vs Bears odds, picks and betting preview for NFL Week 2",
            "How to watch Panthers vs Falcons: start time and livestream",
            "NFL Week 2 picks for every game",
        ]
        for title in unrelated:
            with self.subTest(title=title):
                self.assertFalse(compare(injury, title).same_event)

    def test_paramount_antitrust_reaction_does_not_match_white_house_access_event(self):
        self.assertFalse(compare(
            "White House bars CNN, MS NOW and Politico reporters",
            "Mark Ruffalo tells California attorney general not to settle Paramount antitrust lawsuit",
        ).same_event)


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

    def test_access_phase_merges_different_affected_outlets(self):
        items = [
            report("Trump to ban left-wing news outlets from White House", "Source A", 0),
            report("Trump says CNN, MS NOW and Politico banned from White House", "Source B", 4),
            report("CNN journalists blocked from accessing White House", "Source C", 30),
            report("MS NOW staff denied access, credentials revoked", "Source D", 34),
            report("CNN says Trump press ban is illegal", "Source E", 40),
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

    def test_white_house_reactions_do_not_replace_factual_current_state(self):
        items = [
            report("White House bars CNN, MS NOW and Politico reporters", "Source A", 0),
            report("Reporters denied White House entry as access decision takes effect", "Source B", 20),
            report("Governor says the president uses the Constitution like a suggestion box", "Source C", 40),
            report("TV host tries shaming official for defending White House media decision", "Source D", 50),
            report("Actors freak out over reports of unrelated antitrust settlement", "Source E", 60),
        ]
        updates = meaningful_updates(items)
        self.assertEqual(len(updates), 2)
        self.assertIn("denied white house entry", updates[-1]["label"].lower())

    def test_access_decision_wording_is_phase_based_not_one_off(self):
        items = [
            report("Administration kicks three outlets out of the White House", "Source A", 0),
            report("Administration bans the same outlets from White House access", "Source B", 4),
            report("Their journalists are turned away when access decision takes effect", "Source C", 30),
        ]
        updates = meaningful_updates(items)
        self.assertEqual(len(updates), 2)


class CanonicalOwnershipTests(unittest.TestCase):
    def timeline(self, sid, items, first_seen, families=3):
        model = serializable_model({"coverage": items, "status": "developing"})
        return {
            "id": sid, "current_title": items[-1]["title"], "first_seen": first_seen,
            "last_seen": items[-1]["date"], "max_source_count": families,
            "max_source_family_count": families, "coverage": items, **model,
        }

    def test_identical_update_sets_have_one_authoritative_owner(self):
        items = [
            report("US and Denmark reach Greenland security agreement", "Source A", 0),
            report("Agreement grants permanent US security role in Greenland", "Source B", 20),
        ]
        older = self.timeline("older-owner", items, "2026-09-18T10:00:00Z", 4)
        duplicate = self.timeline("newer-copy", items, "2026-09-18T12:00:00Z", 3)
        groups = canonical_groups([older, duplicate], {"newer-copy"})
        self.assertEqual(groups[0]["owner_id"], "older-owner")
        self.assertEqual(groups[0]["suppressed_ids"], ["newer-copy"])

    def test_near_identical_update_sets_collapse_only_with_event_identity(self):
        shared = [
            report("White House announces media access decision", "Source A", 0),
            report("Reporters denied entry as White House access decision takes effect", "Source B", 20),
        ]
        one = self.timeline("owner-one", shared, "2026-09-18T10:00:00Z", 5)
        two = self.timeline("owner-two", shared + [report("Badges revoked under White House access decision", "Source C", 30)], "2026-09-18T11:00:00Z", 4)
        groups = canonical_groups([one, two], {"owner-one", "owner-two"})
        self.assertEqual(len(groups), 1)

    def test_shared_update_is_removed_from_incoherent_timeline_not_deleted(self):
        shared = report("Bears quarterback exits with hamstring injury", "Source A", 0)
        injury = self.timeline("injury-owner", [shared, report("Team confirms quarterback will undergo testing", "Source B", 20)], "2026-09-18T10:00:00Z", 4)
        betting = self.timeline("betting-page", [shared, report("NFL Week 2 odds and betting picks", "Source C", 30)], "2026-09-18T11:00:00Z", 3)
        fixed, decisions, purity = enforce_unique_updates([injury, betting], {"injury-owner", "betting-page"})
        self.assertEqual(decisions, [])
        self.assertTrue(any(x["timeline_id"] == "betting-page" for x in purity))
        self.assertEqual(violations(fixed)["shared_material_update_ids"], {})
        self.assertIn(shared["link"], {update["link"] for record in fixed for update in record["updates"]})

    def test_publication_purity_removes_betting_from_injury_timeline(self):
        items = [
            report("Bears quarterback exits with hamstring injury", "Source A", 0),
            report("Vikings vs Bears odds, picks and betting preview", "Source B", 10),
            report("How to watch Panthers vs Falcons: start time and livestream", "Source C", 20),
        ]
        record = self.timeline("injury-owner", items, "2026-09-18T10:00:00Z", 4)
        record["current_title"] = items[0]["title"]
        fixed, _ownership, purity = enforce_unique_updates([record], {"injury-owner"})
        self.assertEqual([x["label"] for x in fixed[0]["updates"]], [items[0]["title"]])
        self.assertEqual({x["reason"] for x in purity}, {"incompatible_content_kind"})

    def test_publication_purity_removes_cross_event_bridge_content(self):
        items = [
            report("Top US and China trade negotiators meet in New York ahead of summit", "Source A", 0),
            report("Trump to visit Mamdani in New York City for first meeting", "Source B", 20),
            report("Zelensky and Trump agree to meet in New York for diplomatic talks", "Source C", 40),
        ]
        record = self.timeline("diplomatic-owner", items, "2026-09-18T10:00:00Z", 4)
        record["current_title"] = items[-1]["title"]
        fixed, _ownership, purity = enforce_unique_updates([record], {"diplomatic-owner"})
        self.assertEqual([x["label"] for x in fixed[0]["updates"]], [items[-1]["title"]])
        self.assertEqual(sum(x["reason"] == "event_identity_mismatch" for x in purity), 2)


if __name__ == "__main__":
    unittest.main()
