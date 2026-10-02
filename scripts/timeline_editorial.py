"""Reviewed event scopes applied to publication copies, never to raw history."""
from __future__ import annotations
import json
import re
import hashlib
from pathlib import Path
try:
    from timeline_intelligence import canonical_link, serializable_model, current_status, source_family
except ModuleNotFoundError:
    from scripts.timeline_intelligence import canonical_link, serializable_model, current_status, source_family

CONFIG = Path(__file__).resolve().parents[1] / "data" / "timeline_editorial.json"


def load_config(path=None):
    path = Path(path or CONFIG)
    if not path.exists():
        return {"events": {}, "aliases": {}}
    config = json.loads(path.read_text())
    events = config.get("events", {})
    aliases = config.get("aliases", {})
    for sid, event in events.items():
        if not re.fullmatch(r"[a-f0-9]{12}", sid) or not event.get("title") or not event.get("reviewed_at"):
            raise ValueError("Editorial event needs a durable ID, title and review date")
        re.compile(event["scope"], re.I)
        if event.get("exclude_pattern"):
            re.compile(event["exclude_pattern"], re.I)
    for alias, owner in aliases.items():
        if not re.fullmatch(r"[a-f0-9]{12}", alias) or owner not in events or owner == alias or owner in aliases:
            raise ValueError("Editorial alias must point directly to a reviewed event")
    return config


def in_scope(title, link, event):
    if canonical_link(link) in {canonical_link(x) for x in event.get("exclude_links", [])}:
        return False
    if event.get("exclude_pattern") and re.search(event["exclude_pattern"], str(title), re.I):
        return False
    return bool(re.search(event["scope"], str(title), re.I))


def prepare_records(records, config=None):
    config = config if config is not None else load_config()
    events, aliases = config.get("events", {}), config.get("aliases", {})
    grouped = {}
    decisions = []
    for original in records:
        sid = str(original.get("id"))
        owner = aliases.get(sid, sid)
        event = events.get(owner)
        if not event:
            grouped[sid] = dict(original)
            continue
        coverage = []
        for source in original.get("coverage", []):
            if not event.get("hold") and in_scope(source.get("title", ""), source.get("link"), event):
                coverage.append(dict(source))
            else:
                decisions.append({"timeline_id": sid, "owner_id": owner,
                                  "source_title": source.get("title"), "link": source.get("link"),
                                  "reason": "reviewed_event_scope", "reviewed_at": event["reviewed_at"]})
        record = dict(original)
        if owner in grouped:
            prior = grouped[owner]
            coverage = prior.get("coverage", []) + coverage
            record = {**record, **prior}
            record["first_seen"] = min(filter(None, (original.get("first_seen"), prior.get("first_seen"))), default=None)
        # Source links remain durable; additional headlines from the same report
        # cannot manufacture corroboration or inflate the material chronology.
        unique = {(s.get("source"), canonical_link(s.get("link"))): s for s in coverage}
        record.update(id=owner, coverage=list(unique.values()), current_title=event["title"],
                      title_history=[event["title"]], editorial=event)
        source_names = {s.get("source") for s in record["coverage"] if s.get("source")}
        families = {source_family(s.get("source")) for s in record["coverage"] if s.get("source")}
        record.update(max_source_count=len(source_names), max_source_family_count=len(families),
                      current_source_family_count=len(families))
        record.update(serializable_model(record))
        if event.get("phases"):
            record["updates"] = compress_phases(owner, record["updates"], event["phases"])
            record["material_update_count"] = len(record["updates"])
            record["current_status"] = current_status(record["updates"])
        if record["updates"]:
            record["last_seen"] = record["updates"][-1].get("date") or record.get("last_seen")
        grouped[owner] = record
    return list(grouped.values()), decisions


def compress_phases(sid, updates, phases):
    """Only explicitly reviewed repeat facts share a phase, not general topics."""
    kept = []
    groups = {}
    for update in updates:
        phase = next((p for p in phases if re.search(p["match"], update.get("source_title") or update.get("label", ""), re.I)), None)
        if not phase:
            kept.append(update)
            continue
        key = phase["key"]
        if key not in groups:
            item = {**update, "id": hashlib.sha1(f"reviewed:{sid}:{key}".encode()).hexdigest()[:16],
                    "label": phase["label"], "sources": [dict(s) for s in update.get("sources", [])]}
            groups[key] = item
            kept.append(item)
        else:
            item = groups[key]
            links = {canonical_link(s.get("link")) for s in item["sources"]}
            for source in update.get("sources", []):
                if canonical_link(source.get("link")) not in links:
                    # Repeated reporting is not new independent verification.
                    item["sources"].append({**source, "role": "additional_report", "independent": False})
                    links.add(canonical_link(source.get("link")))
            item["source_count"] = len(item["sources"])
    return sorted(kept, key=lambda u: u.get("date") or "")
