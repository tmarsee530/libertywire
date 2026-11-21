"""Homepage must expose the authoritative lead without running JavaScript."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ServerRenderedLeadTests(unittest.TestCase):
    def test_authoritative_lead_precedes_secondary_fallback_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "data").mkdir()
            for name in ("install_homepage_v2.py", "homepage_selection.py"):
                (root / "scripts" / name).write_text((ROOT / "scripts" / name).read_text(encoding="utf-8"), encoding="utf-8")
            (root / "index.html").write_text(
                '<!doctype html><html><head></head><body><header></header><main id="main-content">'
                '<section class="lead" id="lead-wrap"><div class="lead-inner"><div id="lead" aria-live="polite">'
                '<div class="kicker">Developing</div><div class="lead-body"><h1><a href="#">Standing by for the lead story…</a></h1></div>'
                '</div></div></section><div class="section-label"><span>The Wire</span></div><div class="grid" id="grid"></div>'
                '</main></body></html>', encoding="utf-8")
            stories = [
                {"id": "aaa123abc123", "title": "Unverified cluster prediction, odds, picks", "source_family_count": 3,
                 "coverage": [{"source": "Source One", "title": "Unverified cluster prediction, odds, picks", "link": "https://example.com/bet", "date": "2026-11-21T12:00:00Z"}]},
                {"id": "bbb123abc123", "title": "Raw story title", "source_family_count": 3,
                 "coverage": [{"source": "Source Two", "title": "Raw story title", "link": "https://example.com/story", "date": "2026-11-21T13:00:00Z"}]},
                {"id": "ccc123abc123", "title": "Another raw story", "source_family_count": 3,
                 "coverage": [{"source": "Source Three", "title": "Another raw story", "link": "https://example.com/other", "date": "2026-11-21T13:10:00Z"}]},
            ]
            (root / "data" / "storylines.json").write_text(json.dumps({"storylines": stories}), encoding="utf-8")
            (root / "data" / "published_timelines.json").write_text(json.dumps({"ids": [s["id"] for s in stories]}), encoding="utf-8")
            state = {"timelines": {
                "aaa123abc123": {"title": "NFL longshot parlay picks and odds", "developments": [{"link": "https://example.com/bet", "source_title": "NFL longshot parlay picks and odds", "label": "NFL longshot parlay picks and odds"}]},
                "bbb123abc123": {"title": "Agency orders Pine County bridge closed", "currentStatus": "Bridge remains closed following the order.", "developments": [{"link": "https://example.com/story", "source_title": "Agency orders Pine County bridge closed", "label": "Agency orders Pine County bridge closed"}]},
                "ccc123abc123": {"title": "Court confirms city election recount", "developments": [{"link": "https://example.com/other", "source_title": "Court confirms city election recount", "label": "Court confirms city election recount"}]},
            }}
            (root / "data" / "timeline_state_index.json").write_text(json.dumps(state), encoding="utf-8")
            command = [sys.executable, str(root / "scripts" / "install_homepage_v2.py")]
            subprocess.run(command, cwd=root, check=True, capture_output=True)
            first = (root / "index.html").read_text(encoding="utf-8")
            self.assertNotIn("Standing by for the lead story", first)
            self.assertIn('<h1><a href="/stories/bbb123abc123/">Agency orders Pine County bridge closed</a></h1>', first)
            self.assertIn("Bridge remains closed following the order.", first)
            self.assertLess(first.index('id="lead-wrap"'), first.index('id="server-wire"'))
            self.assertNotIn('/stories/aaa123abc123/', first)
            self.assertIn('/stories/ccc123abc123/', first)
            subprocess.run(command, cwd=root, check=True, capture_output=True)
            self.assertEqual(first, (root / "index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
