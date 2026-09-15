#!/usr/bin/env python3
"""Build a standards-based RSS feed from published Rally Brief metadata."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://rallypointnews.com"
DATA = ROOT / "data" / "briefs.json"
OUT = ROOT / "feed.xml"


def absolute(url: str) -> str:
    return url if url.startswith("http") else BASE + "/" + url.lstrip("/")


def rss_date(value: str) -> str:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, AttributeError):
        dt = datetime.now(timezone.utc)
    return format_datetime(dt)


def main():
    briefs = json.loads(DATA.read_text(encoding="utf-8")).get("briefs", []) if DATA.exists() else []
    briefs = sorted(briefs, key=lambda b: b.get("published_at", ""), reverse=True)[:50]

    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "Rally Point News — Rally Briefs"
    SubElement(channel, "link").text = BASE + "/briefs/"
    SubElement(channel, "description").text = "Source-based explainers and original Rally Briefs from Rally Point News."
    SubElement(channel, "language").text = "en-us"
    SubElement(channel, "ttl").text = "15"
    if briefs:
        SubElement(channel, "lastBuildDate").text = rss_date(briefs[0].get("updated_at") or briefs[0].get("published_at"))

    for brief in briefs:
        if not brief.get("title") or not brief.get("url"):
            continue
        url = absolute(brief["url"])
        item = SubElement(channel, "item")
        SubElement(item, "title").text = str(brief["title"])
        SubElement(item, "link").text = url
        SubElement(item, "guid", isPermaLink="true").text = url
        SubElement(item, "description").text = str(brief.get("description") or "Source-based Rally Point News explainer.")
        if brief.get("published_at"):
            SubElement(item, "pubDate").text = rss_date(brief["published_at"])

    tree = ElementTree(rss)
    try:
        tree.indent(space="  ")
    except AttributeError:
        pass
    tree.write(OUT, encoding="utf-8", xml_declaration=True)
    print(f"Built RSS feed with {len(briefs)} Rally Briefs")


if __name__ == "__main__":
    main()
