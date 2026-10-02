import unittest
from scripts.build_history import bounded_history

class HistoryRetentionTests(unittest.TestCase):
    def test_published_history_survives_newer_transient_clusters(self):
        old={"id":"durable","last_seen":"2026-09-30T12:00:00Z"}
        news=[{"id":str(i),"last_seen":"2026-10-02T12:00:00Z"} for i in range(10)]
        kept=bounded_history(news+[old],{"durable"},3)
        self.assertEqual(len(kept),3)
        self.assertIn(old,kept)
        self.assertEqual(kept[-1],old)

    def test_unpublished_clusters_remain_bounded_by_recency(self):
        records=[{"id":str(i),"last_seen":f"2026-10-0{i}T12:00:00Z"} for i in range(1,4)]
        self.assertEqual([x["id"] for x in bounded_history(records,set(),2)],["3","2"])
