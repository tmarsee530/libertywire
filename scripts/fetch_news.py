#!/usr/bin/env python3
"""Build Rally Point's shared news dataset from configured RSS/Atom feeds."""
from __future__ import annotations
import calendar, html, json, re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
import feedparser, requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT=Path(__file__).resolve().parents[1]
FEEDS_PATH=ROOT/"feeds.json"
BREADTH_FEEDS_PATH=ROOT/"feeds_breadth.json"
OUTPUT_PATH=ROOT/"data"/"news.json"
# Ingestion depth is intentionally much larger than the homepage display depth.
# This gives the ranking/clustering layer a broad radar while the homepage remains selective.
DEFAULT_MAX_PER_SOURCE=20
MAX_SOURCE_DEPTH=40
SUMMARY_LEN=220
TIMEOUT_SECONDS=25
USER_AGENT="RallyPointNews/1.0 (+https://rallypointnews.com/)"
TAG_RE=re.compile(r"<[^>]+>")
IMG_RE=re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']",re.I)

class FeedLinkParser(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()!="link":return
        a={str(k).lower():v for k,v in attrs if k}
        rel=(a.get("rel") or "").lower();typ=(a.get("type") or "").lower();href=a.get("href")
        if href and "alternate" in rel and typ in {"application/rss+xml","application/atom+xml","application/feed+json"}:
            self.links.append(href)

def session_with_retries():
    retry=Retry(total=2,connect=2,read=2,status=2,backoff_factor=1,status_forcelist=(429,500,502,503,504),allowed_methods=frozenset(["GET"]),respect_retry_after_header=True)
    s=requests.Session();s.headers.update({"User-Agent":USER_AGENT,"Accept":"application/rss+xml, application/atom+xml, application/xml, text/xml, */*"});s.mount("https://",HTTPAdapter(max_retries=retry));s.mount("http://",HTTPAdapter(max_retries=retry));return s
SESSION=session_with_retries()

def clean_text(value):
    if not value:return ""
    return re.sub(r"\s+"," ",html.unescape(TAG_RE.sub(" ",value))).strip()

def summarize(entry):
    raw=entry.get("summary") or ""
    if not raw and entry.get("content"):raw=entry.content[0].get("value","")
    text=clean_text(raw)
    if len(text)<=SUMMARY_LEN:return text
    return text[:SUMMARY_LEN].rsplit(" ",1)[0].rstrip(" ,;:-")+"…"

def first_image(entry):
    for key in ("media_content","media_thumbnail"):
        for item in entry.get(key,[]) or []:
            if item.get("url"):return item["url"]
    for enclosure in entry.get("enclosures",[]) or []:
        href=enclosure.get("href") or enclosure.get("url");ctype=enclosure.get("type","")
        if href and (ctype.startswith("image/") or re.search(r"\.(jpe?g|png|webp)(\?|$)",href,re.I)):return href
    raw=entry.get("summary") or ""
    if not raw and entry.get("content"):raw=entry.content[0].get("value","")
    m=IMG_RE.search(raw);return m.group(1) if m else None

def published_epoch(entry):
    parsed=entry.get("published_parsed") or entry.get("updated_parsed")
    return int(calendar.timegm(parsed)) if parsed else 0

def iso_from_epoch(epoch):
    return datetime.fromtimestamp(epoch,tz=timezone.utc).isoformat().replace("+00:00","Z") if epoch else None

def source_depth(source):
    try:depth=int(source.get("max_entries",DEFAULT_MAX_PER_SOURCE))
    except (TypeError,ValueError):depth=DEFAULT_MAX_PER_SOURCE
    return max(1,min(depth,MAX_SOURCE_DEPTH))

def parse_feed(content,source):
    parsed=feedparser.parse(content)
    if not parsed.entries:return []
    stories=[]
    for entry in parsed.entries[:source_depth(source)]:
        title=clean_text(entry.get("title"));link=(entry.get("link") or "").strip()
        if not title or not link:continue
        epoch=published_epoch(entry)
        stories.append({"source":source["name"],"title":title,"link":link,"date":iso_from_epoch(epoch),"published_epoch":epoch,"image":first_image(entry),"summary":summarize(entry)})
    return stories

def discover_feed(homepage,timeout):
    response=SESSION.get(homepage,timeout=timeout,headers={"Accept":"text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"});response.raise_for_status()
    parser=FeedLinkParser();parser.feed(response.text)
    return urljoin(response.url,parser.links[0]) if parser.links else None

def fetch_source(source):
    timeout=int(source.get("timeout",TIMEOUT_SECONDS));direct_error=None
    try:
        response=SESSION.get(source["url"],timeout=timeout);response.raise_for_status();stories=parse_feed(response.content,source)
        if stories:return stories,None
        direct_error="feed returned no entries"
    except Exception as exc:direct_error=str(exc)[:240]
    homepage=source.get("homepage")
    if not homepage:return [],direct_error
    try:
        discovered=discover_feed(homepage,timeout)
        if not discovered:return [],f"{direct_error}; no advertised RSS/Atom feed found"
        if discovered.rstrip("/")==source["url"].rstrip("/"):return [],direct_error
        response=SESSION.get(discovered,timeout=timeout);response.raise_for_status();stories=parse_feed(response.content,source)
        if stories:return stories,None
        return [],f"{direct_error}; advertised feed returned no entries"
    except Exception as exc:return [],f"{direct_error}; feed autodiscovery failed: {str(exc)[:140]}"[:240]

def dedupe(stories):
    seen=set();unique=[]
    for story in stories:
        key=re.sub(r"\W+"," ",story["title"].lower()).strip()
        if key in seen:continue
        seen.add(key);unique.append(story)
    return unique

def substantive(payload):
    return {k:v for k,v in payload.items() if k!="generated_at"}

def load_feeds():
    feeds=json.loads(FEEDS_PATH.read_text(encoding="utf-8"))
    if BREADTH_FEEDS_PATH.exists():
        feeds.extend(json.loads(BREADTH_FEEDS_PATH.read_text(encoding="utf-8")))
    seen=set();unique=[]
    for source in feeds:
        key=(source.get("name"),source.get("url"))
        if key in seen:continue
        seen.add(key);unique.append(source)
    return unique

def main():
    feeds=load_feeds();all_stories=[];healthy=[];failed=[]
    for source in feeds:
        stories,error=fetch_source(source)
        if stories:all_stories.extend(stories);healthy.append(source["name"])
        else:failed.append({"source":source["name"],"error":error or "unknown error"})
    stories=dedupe(all_stories);stories.sort(key=lambda x:x["published_epoch"],reverse=True)
    payload={"generated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"source_count":len(feeds),"healthy_source_count":len(healthy),"healthy_sources":healthy,"failed_sources":failed,"story_count":len(stories),"stories":stories}
    if not stories:raise SystemExit("No stories were fetched; refusing to publish an empty newsroom dataset.")
    if OUTPUT_PATH.exists():
        try:
            old=json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
            if substantive(old)==substantive(payload):print(f"No substantive change: {len(stories)} stories from {len(healthy)}/{len(feeds)} sources.");return
        except Exception:pass
    OUTPUT_PATH.parent.mkdir(parents=True,exist_ok=True);OUTPUT_PATH.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Generated {len(stories)} stories from {len(healthy)}/{len(feeds)} healthy sources; default radar depth {DEFAULT_MAX_PER_SOURCE}/source.")
    for item in failed:print(f"FAILED: {item['source']}: {item['error']}")
if __name__=="__main__":main()
