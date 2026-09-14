#!/usr/bin/env python3
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
READY = ROOT / "data" / "newsletter_ready.json"
STATE = ROOT / "data" / "newsletter_state.json"
API_URL = "https://api.kit.com/v4/broadcasts"


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def main():
    if not READY.exists():
        print("No approved newsletter package is present; nothing to send.")
        return

    ready = load_json(READY, {})
    state = load_json(STATE, {"updated_at": None, "last_broadcast": None, "sent_editions": []})

    edition_id = str(ready.get("edition_id") or "").strip()
    if ready.get("approved") is not True:
        print("Newsletter package is not approved; nothing to send.")
        return
    if not edition_id:
        raise SystemExit("Approved package is missing edition_id.")
    if edition_id in set(state.get("sent_editions") or []):
        print(f"Edition {edition_id} has already been scheduled or sent; skipping.")
        return

    required = ["subject", "preview_text", "description", "content_html"]
    missing = [key for key in required if not str(ready.get(key) or "").strip()]
    if missing:
        raise SystemExit("Approved package is missing required fields: " + ", ".join(missing))

    api_key = os.environ.get("KIT_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("KIT_API_KEY is not available to this workflow.")

    now = datetime.now(timezone.utc)
    send_at = (now + timedelta(minutes=5)).replace(microsecond=0).isoformat()
    published_at = now.replace(microsecond=0).isoformat()

    # Kit V4 represents account-wide targeting explicitly as all_subscribers.
    # Avoid an empty filter array so the first live edition does not depend on
    # undocumented/ambiguous empty-array behavior.
    payload = {
        "content": ready["content_html"],
        "description": ready["description"],
        "public": True,
        "published_at": published_at,
        "preview_text": ready["preview_text"],
        "subject": ready["subject"],
        "subscriber_filter": [
            {
                "all": [
                    {"type": "all_subscribers"}
                ]
            }
        ],
        "send_at": send_at,
    }
    headers = {
        "Content-Type": "application/json",
        "X-Kit-Api-Key": api_key,
    }

    response = requests.post(API_URL, json=payload, headers=headers, timeout=30)
    if response.status_code != 201:
        safe_body = response.text[:1000]
        raise SystemExit(f"Kit broadcast creation failed ({response.status_code}): {safe_body}")

    data = response.json()
    broadcast = data.get("broadcast") or {}
    broadcast_id = broadcast.get("id")
    if not broadcast_id:
        raise SystemExit("Kit returned success but no broadcast id.")

    sent = list(state.get("sent_editions") or [])
    sent.append(edition_id)
    state = {
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "last_broadcast": {
            "edition_id": edition_id,
            "broadcast_id": broadcast_id,
            "status": broadcast.get("status"),
            "send_at": broadcast.get("send_at") or send_at,
            "public_url": broadcast.get("public_url"),
        },
        "sent_editions": sent[-90:],
    }
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    print(f"Kit broadcast {broadcast_id} scheduled for edition {edition_id}.")


if __name__ == "__main__":
    main()
