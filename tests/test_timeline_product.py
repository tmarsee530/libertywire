import json
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts import build_history, build_timelines
from scripts.timeline_intelligence import canonical_link, meaningful_updates, serializable_model


NOW = datetime(2026, 9, 18, 16, 0, tzinfo=timezone.utc)


def coverage(title, source, minutes, slug=None, query=""):
    return {
        "title": title, "source": source,
        "date": (NOW + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z"),
        "link": f"https://{source.lower().replace(' ','')}.test/{slug or abs(hash(title))}{query}",
    }


def record(items, sid="abc123def456", status="developing"):
    return {
        "id": sid, "current_title": items[-1]["title"],
        "first_seen": items[0]["date"], "last_seen": items[-1]["date"],
        "max_source_count": len({x["source"] for x in items}),
        "max_source_family_count": len({x["source"] for x in items}),
        "status": status, "coverage": items,
    }


class TimelineIntelligenceTests(unittest.TestCase):
    def test_tracking_urls_and_repeat_reports_are_deduplicated(self):
        items = [
            coverage("Court orders city election recount", "Source A", 0, "ruling", "?utm_source=x"),
            coverage("Court orders city election recount", "Source A", 1, "ruling", "?utm_source=y"),
            coverage("Court orders city election recount", "Source B", 2, "same"),
        ]
        updates = meaningful_updates(items)
        self.assertEqual(len(updates), 1)
        self.assertEqual(len(updates[0]["sources"]), 2)
        self.assertEqual(canonical_link(items[0]["link"]), canonical_link(items[1]["link"]))

    def test_update_id_survives_reclassification_and_corroboration(self):
        base = coverage("Court orders city election recount", "Source A", 0)
        first = meaningful_updates([base], "developing")[0]
        corroborated = meaningful_updates([base, {**base, "source": "Source B", "title": "Court orders city election recount — confirmed"}], "breaking")[0]
        self.assertEqual(first["id"], corroborated["id"])
        self.assertEqual(len(corroborated["sources"]), 2)

    def test_material_state_change_becomes_new_classified_update(self):
        items = [
            coverage("Court hears arguments in city election case", "Source A", 0),
            coverage("Court orders city election recount", "Source B", 20),
            coverage("Governor confirms recount begins Monday", "Source C", 40),
        ]
        updates = meaningful_updates(items)
        self.assertEqual(len(updates), 3)
        self.assertEqual(updates[0]["classification"], "CONTEXT")
        self.assertEqual(updates[1]["classification"], "MAJOR DEVELOPMENT")
        self.assertEqual(updates[2]["classification"], "MAJOR DEVELOPMENT")

    def test_breaking_story_marks_newest_material_update_breaking(self):
        items = [
            coverage("Wildfire grows near Pine County", "Source A", 0),
            coverage("Officials order Pine County evacuation", "Source B", 20),
        ]
        updates = meaningful_updates(items, "breaking")
        self.assertEqual(updates[-1]["classification"], "BREAKING")

    def test_current_status_is_latest_material_development(self):
        items = [
            coverage("Agency opens investigation into bridge failure", "Source A", 0),
            coverage("Agency confirms bridge will remain closed", "Source B", 30),
        ]
        model = serializable_model(record(items))
        self.assertIn("bridge will remain closed", model["current_status"]["summary"].lower())
        self.assertEqual(model["current_status"]["source"], "Source B")
        self.assertNotIn("fact_tokens", model["updates"][0])


class TimelineRenderingTests(unittest.TestCase):
    def test_legacy_record_renders_current_status_reverse_order_and_seo(self):
        items = [
            coverage("Court hears arguments in city election case", "Source A", 0),
            coverage("Court orders city election recount", "Source B", 20),
            coverage("Governor confirms recount begins Monday", "Source C", 40),
        ]
        legacy = record(items)
        body = build_timelines.page(legacy, [legacy])
        self.assertIn("<h2 id=\"current-status-heading\">Current status</h2>", body)
        self.assertIn("MAJOR DEVELOPMENT", body)
        self.assertIn('<link rel="canonical" href="https://rallypointnews.com/stories/abc123def456/">', body)
        self.assertIn('"itemListOrder": "https://schema.org/ItemListOrderDescending"', body)
        self.assertIn('article:modified_time', body)
        self.assertLess(body.index("Governor confirms recount begins Monday"), body.index("Court orders city election recount"))
        self.assertIn('<time datetime="2026-09-18T16:40:00Z">', body)
        self.assertIn("Source C ↗", body)

    def test_long_timeline_keeps_recent_updates_open_and_compacts_earlier_items(self):
        verbs = ["opens", "files", "orders", "confirms", "delays", "approves", "rejects", "launches", "suspends", "settles"]
        items = [coverage(f"Agency {verb} phase {index} of bridge response", f"Source {index}", index * 10) for index, verb in enumerate(verbs)]
        item = record(items)
        model = serializable_model(item)
        self.assertGreaterEqual(model["material_update_count"], 9)
        body = build_timelines.page(item, [item])
        self.assertIn("What happened earlier", body)
        self.assertIn("timeline-earlier", body)
        before_earlier = body.split('<details class="earlier">', 1)[0]
        self.assertEqual(before_earlier.count('class="timeline-update"'), build_timelines.VISIBLE_RECENT_UPDATES)

    def test_existing_canonical_page_survives_stronger_deduplication(self):
        duplicate_items = [
            coverage("Court orders city election recount", "Source A", 0),
            coverage("Court orders city election recount", "Source B", 1),
            coverage("Court orders city election recount", "Source C", 2),
        ]
        legacy = record(duplicate_items)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stories = root / "stories"; stories.mkdir()
            history = root / "history.json"; current = root / "current.json"; manifest = root / "manifest.json"
            history.write_text(json.dumps({"storylines": [legacy]}))
            current.write_text(json.dumps({"storylines": []}))
            manifest.write_text(json.dumps({"ids": [legacy["id"]]}))
            state_index = root / "timeline_state_index.json"
            old = (build_timelines.HISTORY, build_timelines.CURRENT, build_timelines.STORIES, build_timelines.MANIFEST, build_timelines.STATE_INDEX)
            try:
                build_timelines.HISTORY, build_timelines.CURRENT = history, current
                build_timelines.STORIES, build_timelines.MANIFEST, build_timelines.STATE_INDEX = stories, manifest, state_index
                build_timelines.main()
                published = json.loads(manifest.read_text())
                self.assertIn(legacy["id"], published["ids"])
                body = (stories / legacy["id"] / "index.html").read_text()
                self.assertIn(f'https://rallypointnews.com/stories/{legacy["id"]}/', body)
                self.assertIn('data-update-id=', body)
                self.assertIn('/assets/timeline-state.js?v=2', body)
                self.assertIn('data-follow-control', body)
                self.assertIn('id="timeline-follow-data"', body)
                index = json.loads(state_index.read_text())
                self.assertEqual(len(index["timelines"][legacy["id"]]["update_ids"]), serializable_model(legacy)["material_update_count"])
                self.assertEqual(index["schema_version"], 2)
                self.assertEqual(index["timelines"][legacy["id"]]["url"], f'/stories/{legacy["id"]}/')
                self.assertIn('id="following-list"', build_timelines.following_page())
                self.assertIn('noindex,follow', build_timelines.following_page())
            finally:
                build_timelines.HISTORY, build_timelines.CURRENT, build_timelines.STORIES, build_timelines.MANIFEST, build_timelines.STATE_INDEX = old

    def test_new_qualified_timeline_is_published(self):
        items = [
            coverage("Court hears arguments in city election case", "Source A", 0),
            coverage("Court orders city election recount", "Source B", 20),
            coverage("Governor confirms recount begins Monday", "Source C", 40),
        ]
        fresh = record(items, "fed456abc123")
        self.assertTrue(build_timelines.eligible(fresh))




class TimelineHistoryTests(unittest.TestCase):
    def test_history_adds_backward_compatible_timeline_model(self):
        items = [
            coverage("Court hears arguments in city election case", "Source A", 0),
            coverage("Court orders city election recount", "Source B", 20),
            coverage("Governor confirms recount begins Monday", "Source C", 40),
        ]
        current_story = {
            "id": "abc123def456", "title": items[-1]["title"], "newest_date": items[-1]["date"],
            "source_count": 3, "source_family_count": 3,
            "sources": [x["source"] for x in items], "status": "developing", "risk_flags": [],
            "coverage": items,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / "storylines.json"; target = root / "history.json"
            source.write_text(json.dumps({"storylines": [current_story]}))
            old = (build_history.STORYLINES, build_history.OUT)
            try:
                build_history.STORYLINES, build_history.OUT = source, target
                build_history.main()
                stored = json.loads(target.read_text())["storylines"][0]
                self.assertEqual(stored["timeline_schema_version"], 1)
                self.assertEqual(stored["material_update_count"], 3)
                self.assertIn("current_status", stored)
                self.assertEqual(len(stored["updates"]), 3)
            finally:
                build_history.STORYLINES, build_history.OUT = old

    def test_duplicate_clusters_with_same_canonical_id_are_merged(self):
        first = record([
            coverage("Studio announces Resident Evil release", "Source A", 0),
            coverage("Resident Evil release opens Friday", "Source B", 10),
        ], "same123id456")
        second = record([
            coverage("Resident Evil earns $8.8 million in previews", "Source C", 20),
            coverage("Resident Evil sets franchise preview record", "Source D", 30),
        ], "same123id456")
        merged = build_history.merge_same_id(first, second)
        self.assertEqual(merged["id"], "same123id456")
        self.assertEqual(len(merged["coverage"]), 4)
        self.assertEqual(len(set(x["link"] for x in merged["coverage"])), 4)
        self.assertEqual(merged["last_seen"], second["last_seen"])
        self.assertIn("current_status", merged)


if __name__ == "__main__":
    unittest.main()
