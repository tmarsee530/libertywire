#!/usr/bin/env python3
"""Build standard and Google News sitemaps from active first-party Rally Point pages."""
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree, register_namespace

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://rallypointnews.com"
BRIEFS_DATA = ROOT / "data" / "briefs.json"
NEWS_NS = "http://www.google.com/schemas/sitemap-news/0.9"
register_namespace("news", NEWS_NS)


def iso_mtime(path: Path):
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def parse_dt(value):
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def load_briefs():
    if not BRIEFS_DATA.exists():
        return []
    try:
        rows = json.loads(BRIEFS_DATA.read_text(encoding="utf-8")).get("briefs", [])
    except (OSError, json.JSONDecodeError):
        return []
    return [b for b in rows if b.get("title") and b.get("url")]


def absolute(url):
    return str(url) if str(url).startswith("http") else BASE + "/" + str(url).lstrip("/")


def indent(tree):
    try: tree.indent(space="  ")
    except AttributeError: pass


def add_entry(entries, loc, page=None, lastmod=None):
    if page is not None and not page.exists():
        return
    entries[loc] = lastmod or (iso_mtime(page) if page is not None else None)


def write_standard(briefs):
    # Only active, canonical first-party product pages belong here. This intentionally
    # includes Rally Briefs and their topic/archive paths because they are current
    # original content and the site's main organic-discovery surface.
    entries = {}
    add_entry(entries, BASE + "/", ROOT / "index.html")
    for route in ("briefs", "topics", "local", "games", "newsletter", "sources", "about", "privacy"):
        add_entry(entries, BASE + f"/{route}/", ROOT / route / "index.html")
    add_entry(entries, BASE + "/games/headline/", ROOT / "games" / "headline" / "index.html")
    topics = ROOT / "topics"
    if topics.exists():
        for page in sorted(topics.glob("*/index.html")):
            add_entry(entries, BASE + f"/topics/{page.parent.name}/", page)
    for brief in briefs:
        slug = str(brief.get("slug") or "").strip()
        page = ROOT / "briefs" / slug / "index.html" if slug else None
        if page is None or not page.exists():
            continue
        lastmod = brief.get("updated_at") or brief.get("published_at") or iso_mtime(page)
        add_entry(entries, absolute(brief["url"]), page, lastmod)

    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for loc, lastmod in entries.items():
        u = SubElement(root, "url")
        SubElement(u, "loc").text = loc
        if lastmod: SubElement(u, "lastmod").text = str(lastmod)
    tree = ElementTree(root); indent(tree)
    tree.write(ROOT / "sitemap.xml", encoding="utf-8", xml_declaration=True)
    return len(entries)


def write_news(briefs):
    # Google News sitemaps should contain only articles published in roughly the
    # last two days. Older Briefs remain in the standard sitemap.
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    cutoff = datetime.now(timezone.utc) - timedelta(days=2)
    count = 0
    for brief in sorted(briefs, key=lambda b: b.get("published_at", ""), reverse=True):
        published = parse_dt(brief.get("published_at"))
        slug = str(brief.get("slug") or "").strip()
        page = ROOT / "briefs" / slug / "index.html" if slug else None
        if not published or published < cutoff or page is None or not page.exists():
            continue
        u = SubElement(root, "url")
        SubElement(u, "loc").text = absolute(brief["url"])
        news = SubElement(u, f"{{{NEWS_NS}}}news")
        publication = SubElement(news, f"{{{NEWS_NS}}}publication")
        SubElement(publication, f"{{{NEWS_NS}}}name").text = "Rally Point News"
        SubElement(publication, f"{{{NEWS_NS}}}language").text = "en"
        SubElement(news, f"{{{NEWS_NS}}}publication_date").text = published.isoformat().replace("+00:00", "Z")
        SubElement(news, f"{{{NEWS_NS}}}title").text = str(brief["title"])
        count += 1
    tree = ElementTree(root); indent(tree)
    tree.write(ROOT / "news-sitemap.xml", encoding="utf-8", xml_declaration=True)
    return count


if __name__ == "__main__":
    briefs = load_briefs()
    standard_count = write_standard(briefs)
    news_count = write_news(briefs)
    print(f"Built discovery sitemaps: {standard_count} standard URLs; {news_count} recent News URLs")
