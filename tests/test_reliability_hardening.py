import importlib.util
import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run_newsroom = load_module("run_newsroom_hardening", "scripts/run_newsroom.py")
stage_publication = load_module("stage_publication_hardening", "scripts/stage_publication.py")


class ArtifactIsolationTests(unittest.TestCase):
    def test_failed_stage_restores_last_known_good_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "data" / "optional.json"
            artifact.parent.mkdir()
            artifact.write_text("old", encoding="utf-8")
            script = root / "fail.py"
            script.write_text("from pathlib import Path\nPath('data/optional.json').write_text('partial')\nraise SystemExit(1)\n", encoding="utf-8")
            stage = {"key": "optional", "label": "Optional", "script": str(script), "expected": "data/optional.json", "core": False, "outputs": ("data/optional.json",)}
            with mock.patch.object(run_newsroom, "ROOT", root), mock.patch.object(run_newsroom.time, "sleep"):
                result, failure = run_newsroom.run_stage(stage, {})
            self.assertEqual("FAILED", result["status"])
            self.assertIsNotNone(failure)
            self.assertEqual("old", artifact.read_text(encoding="utf-8"))

    def test_successful_stage_keeps_new_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "data" / "optional.json"
            artifact.parent.mkdir()
            artifact.write_text("old", encoding="utf-8")
            script = root / "ok.py"
            script.write_text("from pathlib import Path\nPath('data/optional.json').write_text('new')\n", encoding="utf-8")
            stage = {"key": "optional", "label": "Optional", "script": str(script), "expected": "data/optional.json", "core": False, "outputs": ("data/optional.json",)}
            with mock.patch.object(run_newsroom, "ROOT", root):
                result, failure = run_newsroom.run_stage(stage, {})
            self.assertEqual("HEALTHY", result["status"])
            self.assertIsNone(failure)
            self.assertEqual("new", artifact.read_text(encoding="utf-8"))

    def test_auxiliary_stage_has_one_bounded_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            script = root / "fail.py"
            script.write_text("raise SystemExit(1)\n", encoding="utf-8")
            stage = {"key": "feed", "label": "Feed", "script": str(script), "expected": "data/feed.xml", "core": False, "outputs": ("data/feed.xml",)}
            with mock.patch.object(run_newsroom, "ROOT", root), mock.patch.object(run_newsroom.subprocess, "run", wraps=subprocess.run) as called:
                result, _ = run_newsroom.run_stage(stage, {})
            self.assertEqual("FAILED", result["status"])
            self.assertEqual(1, result["attempts"])
            self.assertEqual(1, called.call_count)
            self.assertEqual(30, called.call_args.kwargs["timeout"])


class HealthPolicyTests(unittest.TestCase):
    def signals(self, stages, manifest_age_minutes=0):
        now = datetime.now(timezone.utc)
        return {
            "ingestion": {"age_minutes": 0, "successful_sources": 80, "source_failure_pct": 0},
            "content": {
                "last_story_age_minutes": 0,
                "manifest_updated_at": (now - timedelta(minutes=manifest_age_minutes)).isoformat(),
            },
            "fast_path": {"true_missed_fast_path_events": 0},
            "email_delivery": {"delivery_enabled": False},
            "stages": stages,
        }

    def test_repeated_auxiliary_failure_never_becomes_core_critical(self):
        state, alerts = run_newsroom.classify(self.signals({
            "archive": {"label": "Archive", "status": "FAILED", "attempts": 3, "consecutive_failures": 99, "fallback": "last-known-good"}
        }))
        self.assertEqual("DEGRADED", state)
        self.assertEqual("WARNING", alerts[0]["severity"])

    def test_core_failure_is_critical(self):
        state, alerts = run_newsroom.classify(self.signals({
            "publication": {"label": "Publication", "status": "FAILED", "attempts": 3, "fallback": "last-known-good"}
        }))
        self.assertEqual("CRITICAL", state)
        self.assertTrue(any(item["code"] == "STAGE_PUBLICATION_FAILED" for item in alerts))

    def test_stale_verified_publication_is_critical(self):
        state, alerts = run_newsroom.classify(self.signals({}, manifest_age_minutes=16))
        self.assertEqual("CRITICAL", state)
        self.assertTrue(any(item["code"] == "PUBLICATION_STALE" for item in alerts))


class CommitIsolationTests(unittest.TestCase):
    def test_missing_optional_artifacts_are_not_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / "data").mkdir()
            (root / "data" / "newsroom_health.json").write_text(json.dumps({
                "stages": {"archive": {"status": "HEALTHY"}, "feed": {"status": "FAILED"}}
            }), encoding="utf-8")
            (root / "index.html").write_text("fresh", encoding="utf-8")
            selected = stage_publication.selected_paths(root)
            self.assertIn("index.html", selected)
            self.assertNotIn("archive", selected)
            self.assertNotIn("feed.xml", selected)

    def test_fast_wire_separates_core_and_auxiliary_checks(self):
        workflow = (ROOT / ".github" / "workflows" / "wire-fast.yml").read_text(encoding="utf-8")
        self.assertIn("Verify core publication surfaces", workflow)
        self.assertIn("Check auxiliary publication surfaces", workflow)
        self.assertIn("continue-on-error: true", workflow)
        self.assertIn("python scripts/stage_publication.py", workflow)
        self.assertNotIn("git add index.html recent/index.html", workflow)

    def test_maintenance_is_not_a_production_writer(self):
        workflow = (ROOT / ".github" / "workflows" / "newsroom.yml").read_text(encoding="utf-8")
        self.assertNotIn("git push origin HEAD:main", workflow)
        self.assertNotIn("git commit -m", workflow)

    def test_watchdog_uses_verified_publication_freshness(self):
        workflow = (ROOT / ".github" / "workflows" / "wire-watchdog.yml").read_text(encoding="utf-8")
        self.assertIn("data/newsroom_health.json", workflow)
        self.assertIn(".cycle.completed_at", workflow)
        self.assertIn("bad_core_stages", workflow)

    def test_core_stage_order_matches_publication_path(self):
        core = [stage["key"] for stage in run_newsroom.STAGES if stage["core"]]
        self.assertEqual(["ingestion", "clustering", "history", "publication", "homepage"], core)


if __name__ == "__main__":
    unittest.main()
