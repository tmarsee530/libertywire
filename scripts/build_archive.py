#!/usr/bin/env python3
"""Preserve and index every published Rally Point timeline as a permanent archive."""
from __future__ import annotations

import html, json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORIES = ROOT / "stories"
MANIFEST = ROOT / "data" / "published_timelines.json"
OUT = ROOT / "archive" / "index.html"
INDEX = ROOT / "data" / "archive_index.json"
BASE = "https://rallypointnews.com"

def esc(value):
    return html.escape(str(value or ""), quote=True)

def parse_dt(value):
    try:
        dt = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)

def extract(pattern, body, default=""):
    m = re.search(pattern, body, re.I | re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip()) if m else default

def mark_archived(path):
    body = path.read_text(encoding="utf-8")
    if 'class="archive-notice"' in body:
        return
    notice = '<div class="archive-notice"><strong>Archived timeline.</strong> This page is preserved as a historical record and is no longer actively updating. The status below reflects the last material development Rally Point tracked.</div>'
    body = body.replace('<section class="current-status"', notice + '<section class="current-status"', 1)
    # An archived story should not invite new follows or email alerts.
    body = re.sub(r'<div class="follow-row">.*?</div><section class="email-pilot".*?</section>', "", body, count=1, flags=re.S)
    path.write_text(body, encoding="utf-8")

def main():
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        active = {str(x) for x in manifest.get("ids", [])}
    except (OSError, json.JSONDecodeError):
        active = set()

    entries = []
    if STORIES.exists():
        for page in STORIES.glob("*/index.html"):
            sid = page.parent.name
            body = page.read_text(encoding="utf-8")
            title = extract(r"<h1[^>]*>(.*?)</h1>", body, "Rally Point timeline")
            modified = extract(r'<meta property="article:modified_time" content="([^"]+)"', body)
            published = extract(r'<meta property="article:published_time" content="([^"]+)"', body)
            if sid not in active:
                mark_archived(page)
            entries.append({
                "id": sid,
                "title": title,
                "url": f"/stories/{sid}/",
                "first_seen": published,
                "last_seen": modified,
                "active": sid in active,
            })

    entries.sort(key=lambda x: parse_dt(x.get("last_seen")), reverse=True)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    INDEX.write_text(json.dumps({"generated_at": now, "count": len(entries), "timelines": entries}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    cards = []
    for item in entries:
        state = "LIVE" if item["active"] else "ARCHIVED"
        cards.append(f'<article><p>{state}</p><h2><a href="{esc(item["url"])}">{esc(item["title"])}</a></h2><span>Last material update: {esc(item.get("last_seen") or "date unavailable")}</span></article>')

    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>News Timeline Archive | Rally Point News</title><meta name="description" content="Permanent archive of source-backed Rally Point News live timelines."><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{BASE}/archive/"><script async src="https://www.googletagmanager.com/gtag/js?id=G-KKT59K667B"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag("js",new Date());gtag("config","G-KKT59K667B");</script><meta property="og:type" content="website"><meta property="og:site_name" content="Rally Point News"><meta property="og:title" content="News Timeline Archive | Rally Point News"><meta property="og:description" content="Permanent archive of source-backed Rally Point News timelines."><meta property="og:url" content="{BASE}/archive/"><link rel="stylesheet" href="/assets/timeline.css?v=5"></head><body><header><a class="mast" href="/">Rally Point News</a><nav><a href="/">Top Stories</a><a href="/stories/">Live Timelines</a><a href="/archive/">Archive</a><a href="/sources/">Sources</a></nav></header><main><p class="status">PERMANENT ARCHIVE</p><h1>News timeline archive</h1><p class="dek">Published Rally Point timelines remain available after active coverage ends so chronology, citations, search value, and inbound links do not disappear.</p><section class="timeline-index">{"".join(cards)}</section></main><footer>Rally Point News · <a href="/about/">Editorial standards</a></footer></body></html>'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"Archived {len(entries)} permanent timeline URLs; {len(active)} currently active")

if __name__ == "__main__":
    main()
