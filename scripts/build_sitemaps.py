#!/usr/bin/env python3
"""Build the sitemap for the current Rally Point News product."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://rallypointnews.com"


def iso_mtime(path: Path):
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def indent(tree):
    try: tree.indent(space="  ")
    except AttributeError: pass


def write_standard():
    # Index only durable pages in the current live-news product. Sources is a
    # first-party transparency page and is linked from the primary navigation.
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    entries = [(BASE + "/", iso_mtime(ROOT / "index.html"))]
    # Utility/transparency pages remain crawlable through internal links, but the
    # sitemap concentrates discovery on the product surfaces we want indexed.
    for route in ("stories", "about", "sources"):
        page = ROOT / route / "index.html"
        if page.exists():
            entries.append((BASE + f"/{route}/", iso_mtime(page)))
    stories = ROOT / "stories"
    history_dates = {}
    history = ROOT / "data" / "history.json"
    if history.exists():
        try:
            payload=json.loads(history.read_text(encoding="utf-8"))
            history_dates={str(x.get("id")):x.get("last_seen") for x in payload.get("storylines",[]) if x.get("id") and x.get("last_seen")}
        except (json.JSONDecodeError,OSError):
            history_dates={}
    if stories.exists():
        for page in sorted(stories.glob("*/index.html")):
            # Story lastmod should mean substantive story change, not merely that
            # the five-minute generator rewrote an identical HTML file.
            entries.append((BASE + f"/stories/{page.parent.name}/", history_dates.get(page.parent.name) or iso_mtime(page)))
    for loc, lastmod in entries:
        u = SubElement(root, "url")
        SubElement(u, "loc").text = loc
        if lastmod:
            SubElement(u, "lastmod").text = lastmod
    tree = ElementTree(root); indent(tree)
    tree.write(ROOT / "sitemap.xml", encoding="utf-8", xml_declaration=True)


def write_news():
    # Rally Point currently ranks and links publisher reporting rather than
    # publishing first-party articles. Do not misrepresent aggregator pages as
    # first-party Google News articles.
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    tree = ElementTree(root); indent(tree)
    tree.write(ROOT / "news-sitemap.xml", encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    write_standard()
    write_news()
    print("Built focused sitemap for homepage, Story Desk, and qualified timelines")
