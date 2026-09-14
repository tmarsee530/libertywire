#!/usr/bin/env python3
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

ROOT = Path(__file__).resolve().parents[1]
MARKETS = ROOT / "local_markets.json"
NEWS = ROOT / "data" / "news.json"
OUT = ROOT / "data" / "local_news.json"
MAX_PER_MARKET = 24
TIMEOUT = 20
UA = "RallyPointNews/1.0 (+https://rallypointnews.com/)"


def clean(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(text or ""))).strip()


def normalize_entry(entry, source, source_type):
    link = str(entry.get("link") or "").strip()
    title = clean(entry.get("title"))
    if not link or not title:
        return None
    date = entry.get("published") or entry.get("updated") or ""
    summary = clean(entry.get("summary") or entry.get("description") or "")
    return {
        "title": title,
        "link": link,
        "source": source,
        "source_type": source_type,
        "date": date,
        "summary": summary[:500],
    }


def fetch_feed(feed):
    try:
        r = requests.get(feed["url"], headers={"User-Agent": UA}, timeout=TIMEOUT)
        r.raise_for_status()
        parsed = feedparser.parse(r.content)
        return [x for x in (normalize_entry(e, feed["name"], feed.get("type", "local")) for e in parsed.entries[:40]) if x]
    except Exception as e:
        print(f"Local feed failed: {feed['name']}: {e}")
        return []


def national_matches(market):
    if not NEWS.exists():
        return []
    try:
        payload = json.loads(NEWS.read_text())
    except Exception:
        return []
    terms = [x.lower() for x in market.get("keywords", [])]
    matched = []
    for story in payload.get("stories", []):
        hay = f"{story.get('title','')} {story.get('description','')}".lower()
        if not any(term in hay for term in terms):
            continue
        matched.append({
            "title": story.get("title"),
            "link": story.get("link"),
            "source": story.get("source"),
            "source_type": "rally_point_source",
            "date": story.get("date"),
            "summary": story.get("description", "")[:500],
        })
    return matched


def dedupe(items):
    seen = set(); out = []
    for item in items:
        key = (item.get("link") or "").split("#")[0]
        if not key or key in seen:
            continue
        seen.add(key); out.append(item)
    return out


def main():
    config = json.loads(MARKETS.read_text())
    markets_out = []
    for market in config.get("markets", []):
        local = []
        for feed in market.get("feeds", []):
            local.extend(fetch_feed(feed))
        items = dedupe(national_matches(market) + local)[:MAX_PER_MARKET]
        markets_out.append({
            "id": market["id"],
            "city": market["city"],
            "region": market["region"],
            "region_code": market["region_code"],
            "label": market["label"],
            "story_count": len(items),
            "stories": items,
        })
    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "markets": markets_out,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    old = None
    if OUT.exists():
        try: old = json.loads(OUT.read_text())
        except Exception: pass
    comparable_old = dict(old or {}); comparable_old.pop("generated_at", None)
    comparable_new = dict(payload); comparable_new.pop("generated_at", None)
    if comparable_old == comparable_new:
        print("Local Rally data unchanged")
        return
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Built Local Rally data for {len(markets_out)} market(s)")


if __name__ == "__main__":
    main()
