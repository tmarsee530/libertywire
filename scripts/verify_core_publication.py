#!/usr/bin/env python3
"""Validate only the artifacts required to publish the live-news product."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
try:
    from timeline_intelligence import SCHEMA_VERSION
except ModuleNotFoundError:
    from scripts.timeline_intelligence import SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify(root=ROOT):
    root = Path(root)
    data = root / "data"
    required = [
        root / "index.html",
        data / "news.json",
        data / "storylines.json",
        data / "history.json",
        data / "published_timelines.json",
        data / "timeline_state_index.json",
        data / "newsroom_health.json",
        data / "newsroom_dead_letters.json",
        root / "stories" / "index.html",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.is_file() or path.stat().st_size == 0]
    assert not missing, f"missing core publication artifacts: {missing}"

    news = load_json(data / "news.json")
    assert int(news.get("healthy_source_count", 0)) > 0, "no healthy sources in core publication"
    manifest = load_json(data / "published_timelines.json")
    assert manifest.get("timeline_schema_version") == SCHEMA_VERSION
    ids = set(manifest.get("ids") or [])
    assert int(manifest.get("count", -1)) == len(ids)
    history_payload = load_json(data / "history.json")
    history = {item.get("id"): item for item in history_payload.get("storylines", [])}

    homepage = (root / "index.html").read_text(encoding="utf-8")
    homepage_ids = set(re.findall(r'href="/stories/([a-f0-9]{12})/"', homepage))
    assert homepage_ids <= ids, f"homepage links to unpublished timelines: {sorted(homepage_ids - ids)}"

    future_limit = datetime.now(timezone.utc) + timedelta(minutes=11)
    for sid in ids:
        page_path = root / "stories" / sid / "index.html"
        assert page_path.is_file(), f"published timeline page missing: {sid}"
        page = page_path.read_text(encoding="utf-8")
        canonical = f'<link rel="canonical" href="https://rallypointnews.com/stories/{sid}/">'
        assert canonical in page, f"canonical URL changed or missing: {sid}"
        assert "Current status" in page and "NEWEST FIRST" in page
        dates = re.findall(r'class="timeline-update[^>]*" data-published="([^"]+)"', page)
        assert dates == sorted(dates, reverse=True), f"timeline is not newest first: {sid}"
        record = history.get(sid)
        if record:
            assert record.get("current_status")
            assert record.get("material_update_count") == len(record.get("updates") or [])
        # Publication may conservatively remove an update claimed by another
        # canonical while retaining the raw historical record. Compaction must
        # therefore be validated against what the page actually publishes.
        if len(dates) >= 9:
            assert "What happened earlier" in page, f"long timeline was not compacted: {sid}"

    for story in history_payload.get("storylines", []):
        values = [story.get("last_seen")]
        values.extend(item.get("date") for item in story.get("coverage", []))
        values.extend(item.get("at") for item in story.get("changes", []))
        for value in filter(None, values):
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            assert parsed <= future_limit, f"future timestamp survived normalization: {value}"

    state_index = load_json(data / "timeline_state_index.json")
    assert int(state_index.get("schema_version", 0)) >= 2
    update_owners = {}
    update_sets = {}
    for sid, timeline in state_index.get("timelines", {}).items():
        update_ids = tuple(sorted(str(value) for value in timeline.get("update_ids", []) if value))
        if update_ids:
            assert update_ids not in update_sets, f"identical current canonical update sets: {update_sets.get(update_ids)}, {sid}"
            update_sets[update_ids] = sid
        for update_id in update_ids:
            assert update_id not in update_owners, f"material update has multiple canonical owners: {update_id}, {update_owners.get(update_id)}, {sid}"
            update_owners[update_id] = sid
    return {"healthy_sources": news.get("healthy_source_count"), "published_timelines": len(ids)}


if __name__ == "__main__":
    result = verify()
    print(f"Core publication verified: {result['healthy_sources']} healthy sources; {result['published_timelines']} timelines")
