#!/usr/bin/env python3
"""Build Rally Point News standard and Google News sitemaps from published Brief metadata."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, register_namespace

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://rallypointnews.com"
NEWS_NS = "http://www.google.com/schemas/sitemap-news/0.9"
register_namespace("news", NEWS_NS)


def load_briefs():
    path = ROOT / "data" / "briefs.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("briefs", [])


def absolute(url: str) -> str:
    return url if url.startswith("http") else BASE + "/" + url.lstrip("/")


def parse_dt(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def indent(tree):
    try:
        tree.indent(space="  ")
    except AttributeError:
        pass


def topic_urls():
    """Discover real topic landing pages so the sitemap scales with the topic renderer."""
    topics = ROOT / "topics"
    if not topics.exists():
        return []
    urls = []
    for index in sorted(topics.glob("*/index.html")):
        slug = index.parent.name
        if slug:
            urls.append((f"{BASE}/topics/{slug}/", None))
    return urls


def write_standard(briefs):
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    fixed = [
        (BASE + "/", None),
        (BASE + "/briefs/", None),
        (BASE + "/topics/", None),
        (BASE + "/local/", None),
        (BASE + "/sources/", None),
        (BASE + "/newsletter/", None),
        (BASE + "/games/", None),
        (BASE + "/games/headline/", None),
        (BASE + "/privacy/", None),
    ]
    entries = fixed + topic_urls() + [(absolute(b.get("url", "")), b.get("updated_at") or b.get("published_at")) for b in briefs if b.get("url")]
    seen = set()
    for loc, lastmod in entries:
        if not loc or loc in seen:
            continue
        seen.add(loc)
        u = SubElement(root, "url")
        SubElement(u, "loc").text = loc
        if lastmod:
            SubElement(u, "lastmod").text = lastmod
    tree = ElementTree(root); indent(tree)
    tree.write(ROOT / "sitemap.xml", encoding="utf-8", xml_declaration=True)


def write_news(briefs):
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    cutoff = datetime.now(timezone.utc) - timedelta(days=2)
    for b in briefs:
        published = parse_dt(b.get("published_at", ""))
        if not published or published < cutoff or not b.get("url") or not b.get("title"):
            continue
        u = SubElement(root, "url")
        SubElement(u, "loc").text = absolute(b["url"])
        news = SubElement(u, f"{{{NEWS_NS}}}news")
        publication = SubElement(news, f"{{{NEWS_NS}}}publication")
        SubElement(publication, f"{{{NEWS_NS}}}name").text = "Rally Point News"
        SubElement(publication, f"{{{NEWS_NS}}}language").text = "en"
        SubElement(news, f"{{{NEWS_NS}}}publication_date").text = b["published_at"]
        SubElement(news, f"{{{NEWS_NS}}}title").text = b["title"]
    tree = ElementTree(root); indent(tree)
    tree.write(ROOT / "news-sitemap.xml", encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    briefs = load_briefs()
    write_standard(briefs)
    write_news(briefs)
    print(f"Built sitemaps from {len(briefs)} published Briefs and {len(topic_urls())} topic pages")
