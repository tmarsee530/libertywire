#!/usr/bin/env python3
"""Build notification candidates without delivering messages.

This is a durable file adapter for the static production stack.  Its IDs and
state transitions map directly to a future database/worker implementation.
Core publication does not import this module and must remain independent.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    from timeline_intelligence import MAJOR_TERMS, fact_tokens, state_concepts
except ModuleNotFoundError:
    from scripts.timeline_intelligence import MAJOR_TERMS, fact_tokens, state_concepts

ROOT = Path(__file__).resolve().parents[1]
FOLLOWS = ROOT / "data" / "server_follows.json"
HISTORY = ROOT / "data" / "history.json"
MANIFEST = ROOT / "data" / "published_timelines.json"
QUEUE = ROOT / "data" / "notification_queue.json"
HEALTH = ROOT / "data" / "notification_health.json"
DASHBOARD = ROOT / "notification-health" / "index.html"
SCHEMA_VERSION = 1
QUEUE_LIMIT = 10000
DELIVERY_ENABLED = False


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_dt(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def family_name(source):
    value = str(source or "").strip().lower()
    aliases = {
        "fox news politics": "fox news", "fox news world": "fox news",
        "fox business": "fox news", "national review the corner": "national review",
        "realclearpolicy": "realclear", "realclearworld": "realclear",
        "realcleardefense": "realclear", "realclearpolitics": "realclear",
    }
    return aliases.get(value, value)


def notification_significance(update):
    """Return (eligible, reason) using material update metadata, never page changes."""
    classification = str(update.get("classification") or "UPDATE").upper()
    if classification == "BREAKING":
        return True, "breaking_material_development"
    if classification == "MAJOR DEVELOPMENT":
        return True, "major_material_development"
    if classification == "CONTEXT":
        return False, "context_not_notifiable"
    if classification != "UPDATE":
        return False, "unsupported_classification"
    label = str(update.get("label") or "")
    tokens = fact_tokens(label)
    decisive = bool(tokens & MAJOR_TERMS or state_concepts(label) or any(any(c.isdigit() for c in token) for token in tokens))
    families = {family_name(source.get("source")) for source in update.get("sources") or [] if source.get("source")}
    if decisive and len(families) >= 2:
        return True, "meaningful_update_independently_corroborated"
    return False, "ordinary_update_below_notification_threshold"


def delivery_channels(follow):
    channels = follow.get("channels") or {}
    return [name for name in ("email", "web_push") if channels.get(name) is True]


def queue_key(follow_id, timeline_id, update_id):
    raw = f"{follow_id}:{timeline_id}:{update_id}:notification-v1"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def updates_after_cursor(follow, updates):
    valid = [update for update in updates if update.get("id")]
    cursor = follow.get("last_delivered_material_update_id") or follow.get("baseline_material_update_id")
    ids = [update["id"] for update in valid]
    if cursor in ids:
        return valid[ids.index(cursor) + 1:]
    followed_at = parse_dt(follow.get("followed_at"))
    return [update for update in valid if parse_dt(update.get("date")) > followed_at]


def evaluate_follow(follow, record, active_ids, existing_keys, stamp):
    timeline_id = follow.get("timeline_id")
    if follow.get("status") != "active":
        return [], [{"timeline_id": timeline_id, "reason": "follow_not_active"}]
    if timeline_id not in active_ids:
        return [], [{"timeline_id": timeline_id, "reason": "timeline_inactive_or_archived"}]
    if not record:
        return [], [{"timeline_id": timeline_id, "reason": "timeline_record_unavailable"}]
    channels = delivery_channels(follow)
    candidates, observations = [], []
    for update in updates_after_cursor(follow, record.get("updates") or []):
        eligible, reason = notification_significance(update)
        if not channels:
            eligible, reason = False, "no_delivery_channel_eligible"
        key = queue_key(follow.get("id"), timeline_id, update["id"])
        item = {
            "schema_version": SCHEMA_VERSION,
            "id": key[:24], "dedupe_key": key,
            "follow_id": follow.get("id"), "subject_ref": follow.get("subject_ref"),
            "timeline_id": timeline_id, "material_update_id": update["id"],
            "classification": update.get("classification") or "UPDATE",
            "significance_reason": reason, "created_at": stamp,
            "eligible_channels": channels, "status": "pending" if eligible else "suppressed",
            "attempts": 0, "last_error": None, "delivered_at": None,
        }
        observations.append({"timeline_id": timeline_id, "update_id": update["id"], "classification": item["classification"], "eligible": eligible, "reason": reason, "deduped": key in existing_keys})
        if key not in existing_keys:
            candidates.append(item)
            existing_keys.add(key)
    return candidates, observations


def build(follows_payload, history_payload, manifest_payload, prior_queue, stamp=None):
    stamp = stamp or now_iso()
    follows = follows_payload.get("follows") or []
    records = {record.get("id"): record for record in history_payload.get("storylines") or [] if record.get("id")}
    active_ids = set(manifest_payload.get("ids") or [])
    existing = list(prior_queue.get("items") or [])
    existing_keys = {item.get("dedupe_key") for item in existing if item.get("dedupe_key")}
    new_items, observations = [], []
    for follow in follows:
        items, seen = evaluate_follow(follow, records.get(follow.get("timeline_id")), active_ids, existing_keys, stamp)
        new_items.extend(items); observations.extend(seen)
    all_items = (existing + new_items)[-QUEUE_LIMIT:]
    pending = [item for item in all_items if item.get("status") == "pending"]
    created_counts = Counter(item.get("status") for item in new_items)
    class_counts = Counter(item.get("classification") for item in new_items)
    duplicate_count = sum(bool(item.get("deduped")) for item in observations)
    oldest = min((parse_dt(item.get("created_at")) for item in pending), default=None)
    age = round(max(0, (parse_dt(stamp) - oldest).total_seconds() / 60), 1) if oldest else None
    queue_payload = {"schema_version": SCHEMA_VERSION, "generated_at": stamp, "delivery_enabled": DELIVERY_ENABLED, "items": all_items}
    health = {
        "schema_version": SCHEMA_VERSION, "generated_at": stamp, "state": "READY",
        "delivery_enabled": DELIVERY_ENABLED, "configured_follows": len(follows),
        "active_follows": sum(f.get("status") == "active" for f in follows),
        "active_timelines_scanned": len(active_ids), "material_updates_observed": sum(len(r.get("updates") or []) for r in records.values() if r.get("id") in active_ids),
        "candidates_created": created_counts.get("pending", 0),
        "candidates_suppressed": created_counts.get("suppressed", 0),
        "candidates_deduped": duplicate_count,
        "candidate_by_classification": dict(sorted(class_counts.items())),
        "queue_backlog": len(pending), "oldest_pending_age_minutes": age,
        "processing_errors": 0, "duplicate_pending_keys": len(pending) - len({x.get("dedupe_key") for x in pending}),
        "metrics": {
            "notification_candidate_created": created_counts.get("pending", 0),
            "notification_candidate_suppressed": created_counts.get("suppressed", 0),
            "notification_queue_created": len(new_items),
            "notification_deduped": duplicate_count,
            "notification_candidate_by_classification": dict(sorted(class_counts.items())),
        },
        "observations": observations[-100:],
    }
    return queue_payload, health


def render_dashboard(health, queue_payload):
    esc = lambda value: html.escape(str(value if value is not None else "—"))
    rows = "".join(f"<tr><td>{esc(item.get('timeline_id'))}</td><td>{esc(item.get('material_update_id'))}</td><td>{esc(item.get('classification'))}</td><td>{esc(item.get('status'))}</td><td>{esc(item.get('significance_reason'))}</td></tr>" for item in (queue_payload.get("items") or [])[-50:]) or "<tr><td colspan='5'>No server-side follows or notification candidates are configured.</td></tr>"
    cards = [("Server follows", health["configured_follows"]),("Candidates",health["candidates_created"]),("Suppressed",health["candidates_suppressed"]),("Deduped",health["candidates_deduped"]),("Pending",health["queue_backlog"]),("Delivery", "DISABLED")]
    card_html="".join(f"<div><span>{esc(k)}</span><strong>{esc(v)}</strong></div>" for k,v in cards)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Notification Foundation · Rally Point News</title><style>body{{font:14px/1.45 Arial,sans-serif;color:#12213a;background:#f5f7fa;margin:0}}main{{max-width:1100px;margin:auto;padding:28px 16px}}h1{{font:700 38px Georgia,serif;margin:0}}.warning{{background:#fff4d6;border:1px solid #d9ae45;padding:12px;margin:18px 0}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.cards div,section{{background:#fff;border:1px solid #d9e0ea;padding:15px}}.cards span{{display:block;color:#667085;text-transform:uppercase;font-size:11px}}.cards strong{{font-size:22px}}section{{margin-top:16px;overflow:auto}}table{{border-collapse:collapse;width:100%}}th,td{{padding:8px;text-align:left;border-bottom:1px solid #ddd}}@media(max-width:650px){{.cards{{grid-template-columns:1fr 1fr}}}}</style></head><body><main><h1>Notification Foundation</h1><p>Generated {esc(health['generated_at'])} · aggregate diagnostics only</p><div class="warning"><strong>No delivery is enabled.</strong> This foundation creates inspectable candidates; it cannot send email or push notifications.</div><div class="cards">{card_html}</div><section><h2>Recent candidate state</h2><table><thead><tr><th>Timeline</th><th>Update</th><th>Class</th><th>Status</th><th>Reason</th></tr></thead><tbody>{rows}</tbody></table></section></main></body></html>'''


def main():
    follows = load(FOLLOWS, {"schema_version": SCHEMA_VERSION, "follows": []})
    history = load(HISTORY, {"storylines": []})
    manifest = load(MANIFEST, {"ids": []})
    prior = load(QUEUE, {"schema_version": SCHEMA_VERSION, "items": []})
    queue_payload, health = build(follows, history, manifest, prior)
    atomic_json(QUEUE, queue_payload); atomic_json(HEALTH, health)
    DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text(render_dashboard(health, queue_payload), encoding="utf-8")
    print(f"Notification foundation ready: {health['candidates_created']} candidate(s), {health['candidates_suppressed']} suppressed, {health['candidates_deduped']} deduped; delivery disabled")


if __name__ == "__main__":
    main()
