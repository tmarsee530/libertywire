#!/usr/bin/env python3
"""Build a standards-based RSS feed from published Rally Point live timelines."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://rallypointnews.com"
HISTORY = ROOT / "data" / "history.json"
MANIFEST = ROOT / "data" / "published_timelines.json"
OUT = ROOT / "feed.xml"


def rss_date(value: str) -> str:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError):
        dt = datetime.now(timezone.utc)
    return format_datetime(dt)


def main():
    history = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {"storylines": []}
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {"ids": []}
    ids = {str(x) for x in manifest.get("ids", [])}
    records = [x for x in history.get("storylines", []) if str(x.get("id")) in ids]
    records.sort(key=lambda x: str(x.get("last_seen") or ""), reverse=True)
    records = records[:75]

    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "Rally Point News — Live Timelines"
    SubElement(channel, "link").text = BASE + "/stories/"
    SubElement(channel, "description").text = "Material developments from Rally Point News live timelines, newest updates first."
    SubElement(channel, "language").text = "en-us"
    SubElement(channel, "ttl").text = "5"
    if records:
        SubElement(channel, "lastBuildDate").text = rss_date(records[0].get("last_seen"))

    for record in records:
        sid = str(record.get("id") or "")
        title = str(record.get("current_title") or "").strip()
        if not sid or not title:
            continue
        url = f"{BASE}/stories/{sid}/"
        current = record.get("current_status") or {}
        description = str(current.get("summary") or f"Follow material developments in {title}.").strip()
        item = SubElement(channel, "item")
        SubElement(item, "title").text = title
        SubElement(item, "link").text = url
        SubElement(item, "guid", isPermaLink="true").text = url
        SubElement(item, "description").text = description
        if record.get("last_seen"):
            SubElement(item, "pubDate").text = rss_date(record.get("last_seen"))

    tree = ElementTree(rss)
    try:
        tree.indent(space="  ")
    except AttributeError:
        pass
    tree.write(OUT, encoding="utf-8", xml_declaration=True)
    print(f"Built RSS feed with {len(records)} live timelines")


if __name__ == "__main__":
    main()
