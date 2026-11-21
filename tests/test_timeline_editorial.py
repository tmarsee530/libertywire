import copy
import json
import tempfile
import unittest
from pathlib import Path
from scripts.timeline_editorial import prepare_records, load_config, in_scope
from scripts.build_timelines import page, index_page, continuity_page

SID = '123456abcdef'


def source(title, index):
    return {'title': title, 'source': f'Source {index}', 'link': f'https://source{index}.test/report',
            'date': f'2026-10-02T12:{index:02d}:00Z'}


class ReviewedTimelineTests(unittest.TestCase):
    def config(self):
        return {'events': {SID: {'title': 'Orion plant explosion', 'scope': 'Orion.*explosion',
                'reviewed_at': '2026-10-02', 'featured': True,
                'why_follow': 'Track the response.', 'watch_next': 'Investigation findings.'}}, 'aliases': {}}

    def record(self, sid=SID):
        return {'id': sid, 'first_seen': '2026-10-02T12:00:00Z', 'current_title': 'Unrelated sports result',
                'status': 'developing', 'coverage': [source('Orion plant explosion reported', 0),
                source('Orion plant explosion prompts evacuation', 1), source('Vikings win football game', 2)]}

    def test_scope_repairs_publication_without_mutating_raw_history(self):
        raw = self.record(); before = copy.deepcopy(raw)
        fixed, decisions = prepare_records([raw], self.config())
        self.assertEqual(raw, before)
        self.assertEqual(fixed[0]['current_title'], 'Orion plant explosion')
        self.assertTrue(all('Orion' in s['title'] for s in fixed[0]['coverage']))
        self.assertEqual(len(decisions), 1)
        again, _ = prepare_records([raw], self.config())
        self.assertEqual(fixed, again)

    def test_unreviewed_game_timelines_drop_other_matchups_without_mutating_history(self):
        raw = {"id": "dfd058af0a3d",
               "current_title": "Georgia vs. South Carolina prediction, odds, time: 2026 college football Week 12 picks",
               "coverage": [
                   source("Georgia vs. South Carolina prediction, odds, time: 2026 college football Week 12 picks", 1),
                   source("South Carolina vs. Georgia picks for 2026 Week 12", 2),
                   source("College football odds, predictions: Alabama vs. Georgia lead Week 6 slate", 3),
                   source("New Mexico State vs. FIU prediction, odds, time: Week 6 college football picks", 4),
               ]}
        original = copy.deepcopy(raw)
        fixed, decisions = prepare_records([raw], {"events": {}, "aliases": {}})
        self.assertEqual(raw, original)
        self.assertEqual(len(fixed[0]["coverage"]), 2)
        self.assertEqual(len(decisions), 2)
        self.assertEqual({x["reason"] for x in decisions}, {"different_named_sports_fixture"})
        self.assertEqual(fixed[0]["id"], raw["id"])
        self.assertTrue(all("Georgia" in x["title"] for x in fixed[0]["coverage"]))
        again, _ = prepare_records(fixed, {"events": {}, "aliases": {}})
        self.assertEqual(fixed, again)

    def test_retail_promotions_cannot_contaminate_october_news_event(self):
        raw = {"id": "fe81d65952a8",
               "current_title": "Three Years After October 7, The Truth Is Out",
               "coverage": [
                   source("Three Years After October 7, The Truth Is Out", 0),
                   source("October 7 anniversary draws renewed scrutiny of the attacks", 1),
                   source("October Prime Day laptop deals include Apple MacBooks and Samsung up to 43% off", 2),
                   source("Last-chance October Prime Day deals including 50% off a Shark vacuum", 3),
                   source("Fore! October Prime Day golf deals on balls and tees", 4),
               ]}
        before = copy.deepcopy(raw)
        fixed, decisions = prepare_records([raw], {"events": {}, "aliases": {}})
        self.assertEqual(raw, before)
        self.assertEqual(len(fixed[0]["coverage"]), 2)
        self.assertEqual([x["reason"] for x in decisions],
                         ["unrelated_commercial_retail_offer"] * 3)
        self.assertEqual(fixed[0]["id"], raw["id"])
        repeated, again = prepare_records(fixed, {"events": {}, "aliases": {}})
        self.assertEqual(fixed, repeated)
        self.assertEqual(again, [])

    def test_genuine_retail_reporting_and_retail_roundup_stay_intact(self):
        anchor = "Amazon reports stronger sales during Prime Day promotion"
        raw = {"id": "cafe0000beef", "current_title": anchor, "coverage": [
            source(anchor, 0),
            source("Amazon Prime Day sales climb as retailers report higher spending", 1),
            source("Amazon Prime Day laptop deals and discounts", 2),
        ]}
        fixed, decisions = prepare_records([raw], {"events": {}, "aliases": {}})
        # The rule is one directional: industry reporting may mention deals.
        self.assertEqual(decisions, [])
        self.assertEqual(len(fixed[0]["coverage"]), 3)

    def test_fort_hood_execution_is_not_other_homicides(self):
        event = load_config()["events"]["27d9cc4ad2ed"]
        valid = [
            "Trump approves firing squad execution of 2009 Fort Hood shooter Nidal Hasan",
            "Fort Hood shooter to be executed by Army firing squad",
            "Pentagon confirms execution decision for Nidal Hasan",
        ]
        unrelated = [
            "Gender-Dysphoric Man Who Killed Female Victim Gets Plea Deal",
            "Man who killed dog walker should be deported, says judge",
            "Man killed girlfriend by forcing her to take abortion pills",
        ]
        for title in valid:
            with self.subTest(title=title):
                self.assertTrue(in_scope(title, "https://news.test/a", event))
        for title in unrelated:
            with self.subTest(title=title):
                self.assertFalse(in_scope(title, "https://news.test/a", event))
        raw = {"id": "27d9cc4ad2ed", "current_title": "We Now Know When Nidal Hasan Will Be Executed",
               "coverage": [source(t, n) for n, t in enumerate(valid + unrelated)]}
        original = copy.deepcopy(raw)
        fixed, decisions = prepare_records([raw], load_config())
        self.assertEqual(raw, original)
        self.assertEqual(fixed[0]["id"], raw["id"])
        self.assertEqual(len(fixed[0]["coverage"]), len(valid))
        self.assertEqual(len(decisions), len(unrelated))
        self.assertEqual({d["reason"] for d in decisions}, {"reviewed_event_scope"})

    def test_farage_suspect_does_not_inherit_other_arrests(self):
        event = load_config()["events"]["d1bb2b487208"]
        valid = ["Widdecombe suspect charged with preparing acts against Farage",
                 "Nigel Farage terror plot suspect appears in court"]
        unrelated = ["Rick Ross arrested on domestic violence charges",
                     "Iran-linked terror suspect charged over UK air base",
                     "Survivor 51 contestant loses part of thumb",
                     "Woman arrested over alleged material support for Palestine Islamic Jihad"]
        for title in valid:
            with self.subTest(title=title):
                self.assertTrue(in_scope(title, "https://news.test/a", event))
        for title in unrelated:
            with self.subTest(title=title):
                self.assertFalse(in_scope(title, "https://news.test/a", event))
        raw = {"id": "d1bb2b487208", "current_title": valid[0],
               "coverage": [source(t, n) for n, t in enumerate(valid + unrelated)]}
        before = copy.deepcopy(raw)
        fixed, decisions = prepare_records([raw], load_config())
        self.assertEqual(raw, before)
        self.assertEqual(fixed[0]["id"], raw["id"])
        self.assertEqual(len(fixed[0]["coverage"]), 2)
        self.assertEqual(len(decisions), len(unrelated))

    def test_reviewed_alias_combines_sources_under_one_owner(self):
        config = self.config(); config['aliases'] = {'abcdef123456': SID}
        second = self.record('abcdef123456')
        second['coverage'] = [source('Officials investigate Orion plant explosion', 3)]
        fixed, _ = prepare_records([self.record(), second], config)
        self.assertEqual([r['id'] for r in fixed], [SID])
        self.assertEqual(len(fixed[0]['coverage']), 3)
        notice = continuity_page('abcdef123456', SID, 'Orion plant explosion')
        self.assertIn(f'rel="canonical" href="https://rallypointnews.com/stories/{SID}/"', notice)
        self.assertIn('noindex,follow', notice)

    def test_repeat_phase_preserves_sources_and_durable_id_without_fake_confirmation(self):
        config = self.config()
        config['events'][SID]['phases'] = [{'key': 'initial', 'match': 'explosion reported',
                                         'label': 'Orion plant explosion reported'}]
        raw = self.record(); raw['coverage'] = [source('Orion plant explosion reported', 0)]
        first, _ = prepare_records([raw], config)
        raw['coverage'].append(source('Orion plant explosion reported today', 4))
        second, _ = prepare_records([raw], config)
        self.assertEqual(first[0]['updates'][0]['id'], second[0]['updates'][0]['id'])
        self.assertEqual(first[0]['updates'][0]['date'], second[0]['updates'][0]['date'])
        self.assertEqual(len(second[0]['updates']), 1)
        self.assertEqual(len(second[0]['updates'][0]['sources']), 2)
        # Existing deterministic corroboration may already recognize a repeat;
        # phase consolidation itself must never invent an independent source.
        self.assertLessEqual(second[0]['updates'][0]['independent_source_count'], 2)

    def test_featured_guide_and_index_escape_text_and_keep_source_links(self):
        config = self.config(); config['events'][SID]['why_follow'] = '<script>bad</script>'
        fixed, _ = prepare_records([self.record()], config)
        body = page(fixed[0], fixed)
        self.assertIn('Understand this story', body)
        self.assertIn('What we’re watching', body)
        self.assertIn('&lt;script&gt;bad&lt;/script&gt;', body)
        self.assertIn('https://source0.test/report', body)
        self.assertIn('data-share-timeline', body)
        self.assertIn('id="featured"', index_page(fixed))

    def test_invalid_alias_config_fails_instead_of_partial_repairs(self):
        config = self.config(); config['aliases'] = {'abcdef123456': 'not-present'}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'rules.json'; p.write_text(json.dumps(config))
            with self.assertRaises(ValueError): load_config(p)

    def test_real_scopes_reject_observed_and_future_unrelated_reports(self):
        events = load_config()['events']
        cases = [('59297c12787c', 'First Glastonbury 2027 tickets sell out'),
                 ('59297c12787c', 'Oil prices rise in Iraq'),
                 ('73d0643d7873', 'Man killed in New York City subway'),
                 ('73d0643d7873', 'Manchester City wins league game'),
                 ('fdb63ce25d40', 'Kai Cenat responds to sexual assault allegations'),
                 ('fdb63ce25d40', 'Letitia James launches antitrust lawsuit'),
                 ('0ba70d45bc7e', 'Houthis launch missile attack on shipping'),
                 ('b04e2dc93058', 'Local police buy more Flock cameras')]
        for sid, title in cases:
            with self.subTest(title=title): self.assertFalse(in_scope(title, 'https://source.test/a', events[sid]))


if __name__ == '__main__': unittest.main()
