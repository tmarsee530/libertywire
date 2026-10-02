"""Historical ID reuse must preserve independently established current events."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_storylines as builder


def group(*titles):
    stories = [{"title": title, "source": f"Source {i}",
                "link": f"https://source{i}.test/{title.replace(' ', '-')}",
                "date": "2026-10-02T12:00:00Z", "published_epoch": 1790942400}
               for i, title in enumerate(titles)]
    member_tokens = [builder.tokens(title) for title in titles]
    return {"stories": stories, "sources": {s["source"] for s in stories},
            "tokens": set().union(*member_tokens), "member_tokens": member_tokens,
            "member_anchors": [builder.anchors(title) for title in titles],
            "core_tokens": set.intersection(*(set(t) for t in member_tokens))}


class CurrentEventContinuityTests(unittest.TestCase):
    def run_build(self, groups):
        # Deliberately contaminated history: each current cluster independently
        # matches a real headline in the same old record. Exercise actual history
        # matching and main's ID assignment, rather than mocking a positive match.
        historical = {"id": "abc123def456", "max_source_family_count": 4,
                      "coverage": [s for g in groups for s in g["stories"]]}
        for g in groups:
            self.assertIsNotNone(builder.history_match(
                g["tokens"], [historical], titles=[s["title"] for s in g["stories"]]))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); news = root / "news.json"; out = root / "storylines.json"
            news.write_text(json.dumps({"stories": []}))
            with patch.multiple(builder, NEWS=news, OUT=out), \
                 patch.object(builder, "cluster", return_value=groups), \
                 patch.object(builder, "prior_records", return_value=[historical]), \
                 patch.object(builder, "fast_lookup", return_value={}):
                builder.main()
            return json.loads(out.read_text())["storylines"]

    def test_observed_unrelated_event_pairs_do_not_merge_via_history(self):
        pairs = [
            ("White House bars CNN, MS NOW and Politico reporters",
             "Mark Ruffalo tells California attorney general not to settle Paramount antitrust lawsuit"),
            ("NYC Mayor Zohran Mamdani and Trump to meet again this week",
             "Top US and China trade negotiators meet in New York ahead of Trump-Xi summit"),
            ("Bears QB Caleb Williams exits against Vikings after non-contact hamstring injury",
             "Vikings vs Bears odds, picks and betting preview for NFL Week 2"),
            ("Cornell rape case gets special prosecutor. And, Renee Good's family sues the government",
             "The family of Renee Good files lawsuits over her death during Minneapolis ICE raids"),
        ]
        for left, right in pairs:
            with self.subTest(left=left):
                rows = self.run_build([group(left), group(right)])
                self.assertEqual(len(rows), 2)
                self.assertEqual(len({r["id"] for r in rows}), 2)
                self.assertEqual({tuple(x["title"] for x in r["coverage"]) for r in rows},
                                 {(left,), (right,)})

    def test_genuine_same_event_clusters_keep_the_existing_canonical(self):
        rows = self.run_build([
            group("NORAD jet intercepts aircraft over Camp David"),
            group("NORAD F-16 intercepts aircraft in restricted Camp David airspace"),
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "abc123def456")
        self.assertEqual(len(rows[0]["coverage"]), 2)

    def test_separated_identity_is_deterministic_and_does_not_inherit_breadth(self):
        groups = [group("White House bars CNN reporters"),
                  group("Mark Ruffalo opposes Paramount antitrust lawsuit settlement")]
        first = self.run_build(groups); second = self.run_build(groups)
        self.assertEqual({r["title"]: r["id"] for r in first},
                         {r["title"]: r["id"] for r in second})
        separated = next(r for r in first if "Ruffalo" in r["title"])
        self.assertEqual(separated["source_family_count"], 1)
        self.assertNotEqual(separated["id"], "abc123def456")


if __name__ == "__main__":
    unittest.main()
