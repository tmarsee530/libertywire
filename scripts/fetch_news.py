#!/usr/bin/env python3
"""Build Rally Point's shared news dataset from the configured RSS/Atom feeds."""

from __future__ import annotations

import calendar
import html
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

ROOT = Path(__file__).resolve().parents[1]
FEEDS_PATH = ROOT / "feeds.json"
OUTPUT_PATH = ROOT / "data" / "news.json"
MAX_PER_SOURCE = 5
SUMMARY_LEN = 220
TIMEOUT_SECONDS = 20
USER_AGENT = "RallyPointNews/1.0 (+https://rallypointnews.com/)"

TAG_RE = re.compile(r"<[^>]+>")
IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.I)


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = TAG_RE.sub(" ", value)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def summarize(entry) -> str:
    raw = entry.get("summary") or ""
    if not raw and entry.get("content"):
        raw = entry.content[0].get("value", "")
    text = clean_text(raw)
    if len(text) <= SUMMARY_LEN:
        return text
    shortened = text[:SUMMARY_LEN].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return shortened + "…"


def first_image(entry) -> str | None:
    for key in ("media_content", "media_thumbnail"):
        for item in entry.get(key, []) or []:
            url = item.get("url")
            if url:
                return url

    for enclosure in entry.get("enclosures", []) or []:
        href = enclosure.get("href") or enclosure.get("url")
        content_type = enclosure.get("type", "")
        if href and (content_type.startswith("image/") or re.search(r"\.(jpe?g|png|webp)(\?|$)", href, re.I)):
            return href

    raw = entry.get("summary") or ""
    if not raw and entry.get("content"):
        raw = entry.content[0].get("value", "")
    match = IMG_RE.search(raw)
    return match.group(1) if match else None


def published_epoch(entry) -> int:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return int(calendar.timegm(parsed))
    return int(time.time())


def iso_from_epoch(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_source(source: dict) -> tuple[list[dict], str | None]:
    try:
        response = requests.get(
            source["url"],
            headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        if not parsed.entries:
            return [], "feed returned no entries"

        stories = []
        for entry in parsed.entries[:MAX_PER_SOURCE]:
            title = clean_text(entry.get("title"))
            link = entry.get("link", "").strip()
            if not title or not link:
                continue
            epoch = published_epoch(entry)
            stories.append(
                {
                    "source": source["name"],
                    "title": title,
                    "link": link,
                    "date": iso_from_epoch(epoch),
                    "published_epoch": epoch,
                    "image": first_image(entry),
                    "summary": summarize(entry),
                }
            )
        return stories, None
    except Exception as exc:  # A single publisher should never stop the newsroom.
        return [], str(exc)[:240]


def dedupe(stories: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for story in stories:
        key = re.sub(r"\W+", " ", story["title"].lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        unique.append(story)
    return unique


def main() -> None:
    feeds = json.loads(FEEDS_PATH.read_text(encoding="utf-8"))
    all_stories: list[dict] = []
    healthy_sources: list[str] = []
    failed_sources: list[dict] = []

    for source in feeds:
        stories, error = fetch_source(source)
        if stories:
            all_stories.extend(stories)
            healthy_sources.append(source["name"])
        else:
            failed_sources.append({"source": source["name"], "error": error or "unknown error"})

    stories = dedupe(all_stories)
    stories.sort(key=lambda item: item["published_epoch"], reverse=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_count": len(feeds),
        "healthy_source_count": len(healthy_sources),
        "healthy_sources": healthy_sources,
        "failed_sources": failed_sources,
        "story_count": len(stories),
        "stories": stories,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Generated {len(stories)} stories from {len(healthy_sources)}/{len(feeds)} healthy sources.")
    for failed in failed_sources:
        print(f"FAILED: {failed['source']}: {failed['error']}")

    if not stories:
        raise SystemExit("No stories were fetched; refusing to publish an empty newsroom dataset.")


if __name__ == "__main__":
    main()
