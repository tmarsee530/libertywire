#!/usr/bin/env python3
"""Publish foundation-approved events to the private email service.

Absence or failure of this auxiliary service never fails newsroom publication.
Subscriber destinations are never read or written by this adapter.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from build_notification_foundation import notification_significance, parse_dt
except ModuleNotFoundError:
    from scripts.build_notification_foundation import notification_significance, parse_dt

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "history.json"
MANIFEST = ROOT / "data" / "published_timelines.json"
HEALTH = ROOT / "data" / "email_delivery_health.json"
BASE = "https://rallypointnews.com"


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return default


def atomic_json(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def eligible_events(history, manifest, now=None):
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(hours=48)
    active = set(manifest.get("ids") or [])
    events = []
    for record in history.get("storylines") or []:
        timeline_id = record.get("id")
        if timeline_id not in active:
            continue
        for update in record.get("updates") or []:
            eligible, reason = notification_significance(update)
            if not eligible or not update.get("id") or parse_dt(update.get("date")) < cutoff:
                continue
            events.append({
                "eligible": True,
                "timeline_id": timeline_id,
                "material_update_id": update["id"],
                "title": record.get("current_title") or "Developing story",
                "classification": str(update.get("classification") or "UPDATE").upper(),
                "summary": update.get("label") or record.get("current_status", {}).get("summary") or "A material development was published.",
                "canonical_url": f"{BASE}/stories/{timeline_id}/",
                "published_at": update.get("date"),
                "significance_reason": reason,
            })
    events.sort(key=lambda item: (parse_dt(item["published_at"]), item["timeline_id"], item["material_update_id"]))
    return events[-200:]


def request_json(url, method="GET", payload=None, token=None, timeout=15):
    headers = {"accept": "application/json", "user-agent": "RallyPointNews/1.0"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["content-type"] = "application/json"
    if token:
        headers["authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    api = os.getenv("EMAIL_PILOT_API_URL", "").rstrip("/")
    secret = os.getenv("EMAIL_PILOT_INGEST_SECRET", "")
    if not api or not secret:
        print("Email pilot setup is pending; newsroom publication continues.")
        return 0
    events = eligible_events(load(HISTORY, {"storylines": []}), load(MANIFEST, {"ids": []}))
    try:
        result = request_json(api + "/v1/events", "POST", {"events": events}, secret)
        health = request_json(api + "/v1/health")
        health["last_ingest"] = {key: result.get(key, 0) for key in ("events_created", "deliveries_queued", "events_deduped")}
        atomic_json(HEALTH, health)
        print(f"Email pilot: {result.get('events_created', 0)} event(s), {result.get('deliveries_queued', 0)} delivery item(s), {result.get('events_deduped', 0)} deduped.")
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        print(f"::warning::Email pilot auxiliary service unavailable: {type(error).__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
