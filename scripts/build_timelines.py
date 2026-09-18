#!/usr/bin/env python3
"""Publish autonomous, source-backed developing-story timelines."""
from __future__ import annotations

import html, json, re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "history.json"
CURRENT = ROOT / "data" / "storylines.json"
STORIES = ROOT / "stories"
BASE = "https://rallypointnews.com"
MAX_PAGES = 500


def esc(value): return html.escape(str(value or ""), quote=True)

def parse_dt(value):
    try: return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError): return datetime.min.replace(tzinfo=timezone.utc)

def display_time(value):
    dt = parse_dt(value)
    if dt.year == 1: return "Time unavailable"
    local = dt.astimezone(ZoneInfo("America/New_York"))
    return local.strftime("%b %-d, %Y · %-I:%M %p %Z")

def clean_title(value): return re.sub(r"\s+", " ", str(value or "")).strip()

def source_domain(link):
    host = urlparse(str(link or "")).netloc.lower()
    return host.removeprefix("www.")

def tokens_for_related(value):
    stop={"this","that","with","from","after","about","into","over","news","live","latest","breaking","update","updates"}
    return {x for x in re.findall(r"[a-z0-9\u0027]{4,}", clean_title(value).lower()) if x not in stop}

def family_name(source):
    s = str(source or "").strip().lower()
    aliases = {"fox news politics":"fox news","fox news world":"fox news","fox business":"fox news","national review the corner":"national review","realclearpolicy":"realclear","realclearworld":"realclear","realcleardefense":"realclear","realclearpolitics":"realclear"}
    return aliases.get(s, s)

def eligible(record):
    families = int(record.get("max_source_family_count", 0) or 0)
    coverage = record.get("coverage") or []
    title = clean_title(record.get("current_title")).lower()
    if any(marker in title for marker in ("weekly quiz", "morning greatness")): return False
    distinct_families = {family_name(x.get("source")) for x in coverage if x.get("source")}
    # A durable page must contain enough distinct developments to justify its own URL,
    # not merely three publishers repeating essentially the same headline.
    development_count = len(snapshot_titles(sorted(coverage, key=lambda x: parse_dt(x.get("date")))))
    return bool(record.get("id") and len(coverage) >= 3 and families >= 3 and len(distinct_families) >= 3 and development_count >= 2)

def snapshot_titles(coverage):
    """Keep only publisher wording that contributes meaningful new information."""
    stop={"this","that","with","from","after","about","into","over","news","live","latest","breaking","update","updates","report","reports","says","said","exclusive","video","photos","photo","amid","have","will","their","they","more","story","developing"}
    def toks(value):
        return {x for x in re.findall(r"[a-z0-9']{3,}", clean_title(value).lower()) if x not in stop}
    def clauses(title):
        parts=[x.strip(" -–—:;,.") for x in re.split(r"\s*(?:[|;]|\s[—–-]\s|:\s+|[.!?]\s+)\s*",title) if x.strip()]
        return parts or [title]

    seen=set(); out=[]
    for i,item in enumerate(coverage):
        title=clean_title(item.get("title"))
        if not title: continue
        title_words=toks(title)
        novel=title_words-seen
        if i==0:
            label=title
        else:
            # If a headline adds too little, it is additional coverage rather than a new development.
            if len(novel)<2:
                continue
            candidates=[]
            for clause in clauses(title):
                words=toks(clause)
                clause_novel=words-seen
                repeated=words&seen
                count=len(re.findall(r"[A-Za-z0-9']+",clause))
                if len(clause_novel)>=2 and 2<=count<=16:
                    candidates.append((len(clause_novel)*5-len(repeated)*2,-count,clause))
            if not candidates:
                # Do not repeat the full headline just because clause extraction failed.
                continue
            label=max(candidates)[2]
        words=toks(label)
        if i and len(words-seen)<2:
            continue
        out.append((item,label))
        # Learn from the full source headline, not just the displayed fragment, so
        # subsequent entries cannot repackage information already encountered.
        seen|=title_words
    return out

def analytics_tag():
    # Kept outside f-strings so JavaScript braces can never be interpreted by Python.
    return '<script async src="https://www.googletagmanager.com/gtag/js?id=G-KKT59K667B"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag("js",new Date());gtag("config","G-KKT59K667B");</script>'

def page(record, published_records):
    sid = esc(record["id"]); title = clean_title(record.get("current_title")) or "Developing story"
    coverage = sorted(record.get("coverage", []), key=lambda x: parse_dt(x.get("date")))
    description = f"{title}: a source-backed timeline of distinct developments, newest first, with repeated coverage suppressed."
    updates=[]
    for item,snapshot_title in snapshot_titles(coverage):
        link=item.get("link")
        if not link or not snapshot_title: continue
        updates.append(f'''<li class="timeline-update" data-published="{esc(item.get('date'))}"><time datetime="{esc(item.get('date'))}">{esc(display_time(item.get('date')))}</time><div><h2>{esc(snapshot_title)}</h2><p><a href="{esc(link)}" rel="noopener" target="_blank" title="{esc(clean_title(item.get('title')))}">{esc(item.get('source') or source_domain(link))} ↗</a><span>{esc(source_domain(link))}</span></p></div></li>''')
    source_names=sorted({str(x.get("source") or "").strip() for x in coverage if x.get("source")})
    related=[]; base_tokens=tokens_for_related(title)
    for candidate in published_records:
        if candidate.get("id")==record.get("id") or not eligible(candidate): continue
        candidate_title=clean_title(candidate.get("current_title")); candidate_tokens=tokens_for_related(candidate_title); overlap=len(base_tokens&candidate_tokens)
        if overlap<2: continue
        # Prefer genuinely connected stories, not pages that merely share two generic words.
        similarity=overlap/max(1,min(len(base_tokens),len(candidate_tokens)))
        if similarity<.34: continue
        related.append((similarity,overlap,parse_dt(candidate.get("last_seen")),candidate))
    related.sort(key=lambda x:(x[0],x[1],x[2]),reverse=True)
    related_html="".join(f'<li><a href="/stories/{esc(x[3].get("id"))}/">{esc(clean_title(x[3].get("current_title")))}</a></li>' for x in related[:4])
    related_section=('<section class="related"><h2>Related developing stories</h2><ul>'+related_html+'</ul></section>') if related_html else ""
    status=str(record.get("status") or "developing").upper()
    updates.reverse()  # newest information first for returning readers
    schema_items=[{"@type":"ListItem","position":i+1,"name":snapshot_title,"url":item.get("link")} for i,(item,snapshot_title) in enumerate(reversed(snapshot_titles(coverage))) if item.get("link") and snapshot_title]
    schema=json.dumps({"@context":"https://schema.org","@graph":[{"@type":"CollectionPage","@id":f"{BASE}/stories/{record['id']}/#page","name":title,"description":description,"url":f"{BASE}/stories/{record['id']}/","dateModified":record.get("last_seen"),"mainEntity":{"@type":"ItemList","numberOfItems":len(schema_items),"itemListOrder":"https://schema.org/ItemListOrderDescending","itemListElement":schema_items},"isPartOf":{"@type":"WebSite","name":"Rally Point News","url":BASE+"/"},"breadcrumb":{"@id":f"{BASE}/stories/{record['id']}/#breadcrumb"}},{"@type":"BreadcrumbList","@id":f"{BASE}/stories/{record['id']}/#breadcrumb","itemListElement":[{"@type":"ListItem","position":1,"name":"Rally Point News","item":BASE+"/"},{"@type":"ListItem","position":2,"name":"Live News Timelines","item":BASE+"/stories/"},{"@type":"ListItem","position":3,"name":title,"item":f"{BASE}/stories/{record['id']}/"}]}]},ensure_ascii=False).replace("</","<\\/")
    ga=analytics_tag()
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} — Live Timeline | Rally Point News</title><meta name="description" content="{esc(description)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{BASE}/stories/{sid}/">{ga}<meta property="og:type" content="website"><meta property="og:site_name" content="Rally Point News"><meta property="og:title" content="{esc(title)} — Live Timeline"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{BASE}/stories/{sid}/"><meta name="twitter:card" content="summary"><meta name="twitter:title" content="{esc(title)} — Live Timeline"><meta name="twitter:description" content="{esc(description)}"><link rel="stylesheet" href="/assets/timeline.css?v=2"><script type="application/ld+json">{schema}</script></head><body><a class="skip-link" href="#timeline">Skip to updates</a><header><a class="mast" href="/">Rally Point News</a><nav><a href="/">Top Stories</a><a href="/#grid">The Wire</a><a href="/stories/">Live Timelines</a><a href="/sources/">Sources</a></nav></header><main><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>›</span><a href="/stories/">Live Timelines</a></nav><p class="status">{esc(status)}</p><h1>{esc(title)}</h1><p class="dek">What changed, in one finite feed. Newest developments first; repeated coverage is suppressed and every update links to the publisher that reported it.</p><div class="story-meta"><span>Updated {esc(display_time(record.get('last_seen')))}</span><span>Tracking since {esc(display_time(record.get('first_seen')))}</span><span>{len(updates)} developments</span><span>{len(source_names)} sources</span></div><aside><strong>What changed:</strong> Each entry adds distinct information reported about this story. Scan the developments, open the original reporting when you want more, and stop when you reach what you already know.</aside><div class="return-state" id="return-state" hidden><strong id="return-count"></strong><span>since your last visit</span></div><div class="caught-up"><strong>NEWEST FIRST</strong><span>Eastern Time · finite feed</span></div><ol class="timeline" id="timeline">{''.join(updates)}</ol><div class="end-card"><strong>You’ve reached the beginning.</strong><span>That’s the earliest tracked development in this story.</span></div><script>(function(){try{var k="rp-story-{sid}",now=Date.now(),last=Number(localStorage.getItem(k)||0),items=[].slice.call(document.querySelectorAll(".timeline-update")),fresh=last?items.filter(function(x){var d=Date.parse(x.dataset.published||"");return Number.isFinite(d)&&d>last}):[];if(fresh.length){fresh.forEach(function(x){x.classList.add("is-new")});var box=document.getElementById("return-state"),n=document.getElementById("return-count");n.textContent=fresh.length+" new development"+(fresh.length===1?"":"s");box.hidden=false}localStorage.setItem(k,String(now));var state={id:"{sid}",title:{JSON.stringify(title)},visitedAt:now,lastSeen:{JSON.stringify(record.get("last_seen"))}};localStorage.setItem("rp-follow-{sid}",JSON.stringify(state))}catch(e){}})();</script><section class="sources"><h2>Sources tracking this story</h2><p>{esc(' · '.join(source_names))}</p></section>{related_section}<p class="back"><a href="/">← Back to Rally Point News</a></p></main><footer>Rally Point News · Headlines and reporting belong to their respective publishers. <a href="/about/">Editorial standards</a></footer></body></html>'''

def index_page(records):
    cards=[]
    for r in records:
        development_count=len(snapshot_titles(sorted(r.get("coverage", []), key=lambda x: parse_dt(x.get("date")))))
        cards.append(f'''<article><p>{esc(str(r.get("status") or "developing").upper())}</p><h2><a href="/stories/{esc(r["id"])}/">{esc(clean_title(r.get("current_title")))}</a></h2><span>Updated {esc(display_time(r.get("last_seen")))} · {development_count} key developments</span></article>''')
    ga=analytics_tag()
    schema=json.dumps({"@context":"https://schema.org","@type":"CollectionPage","name":"Live News Timelines","url":BASE+"/stories/","description":"Finite, source-backed feeds of distinct developments in major ongoing stories.","mainEntity":{"@type":"ItemList","numberOfItems":len(records),"itemListElement":[{"@type":"ListItem","position":i+1,"url":f"{BASE}/stories/{r['id']}/","name":clean_title(r.get("current_title"))} for i,r in enumerate(records)]},"isPartOf":{"@type":"WebSite","name":"Rally Point News","url":BASE+"/"}},ensure_ascii=False).replace("</","<\\/")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Live News Timelines | Rally Point News</title><meta name="description" content="Follow major developing stories in finite, source-backed feeds with the newest distinct developments first."><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{BASE}/stories/">{ga}<meta property="og:type" content="website"><meta property="og:site_name" content="Rally Point News"><meta property="og:title" content="Live News Timelines | Rally Point News"><meta property="og:description" content="Finite, source-backed feeds of distinct developments in major ongoing stories."><meta property="og:url" content="{BASE}/stories/"><meta name="twitter:card" content="summary"><script type="application/ld+json">{schema}</script><link rel="stylesheet" href="/assets/timeline.css?v=2"></head><body><header><a class="mast" href="/">Rally Point News</a><nav><a href="/">Top Stories</a><a href="/#grid">The Wire</a><a href="/stories/">Live Timelines</a><a href="/sources/">Sources</a></nav></header><main><p class="status">LIVE STORY DESK</p><h1>Developing stories, without the endless scroll</h1><p class="dek">Finite feeds of the developments that matter. Open a story, scan what changed, and reach the end.</p><section class="timeline-index">{''.join(cards)}</section></main><footer>Rally Point News · <a href="/about/">Editorial standards</a></footer></body></html>'''

def main():
    payload=json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {"storylines":[]}
    by_id={x.get("id"):x for x in payload.get("storylines",[]) if x.get("id")}
    current=json.loads(CURRENT.read_text(encoding="utf-8")) if CURRENT.exists() else {"storylines":[]}
    for item in current.get("storylines",[]):
        sid=item.get("id")
        if not sid: continue
        prior=by_id.get(sid,{}); coverage={((x.get("source") or ""),(x.get("link") or "")):x for x in prior.get("coverage",[])}
        for update in item.get("coverage",[]): coverage[(update.get("source") or "",update.get("link") or "")]=update
        by_id[sid]={**prior,"id":sid,"current_title":item.get("title") or prior.get("current_title"),"last_seen":item.get("newest_date") or prior.get("last_seen"),"status":item.get("status") or prior.get("status"),"max_source_count":max(int(prior.get("max_source_count",0) or 0),int(item.get("source_count",0) or 0)),"max_source_family_count":max(int(prior.get("max_source_family_count",0) or 0),int(item.get("source_family_count",0) or 0)),"coverage":list(coverage.values())}
    records=[x for x in by_id.values() if eligible(x)]; records.sort(key=lambda x:parse_dt(x.get("last_seen")),reverse=True); records=records[:MAX_PAGES]
    STORIES.mkdir(parents=True,exist_ok=True); keep={str(record["id"]) for record in records}
    for child in STORIES.iterdir():
        if child.is_dir() and child.name not in keep:
            generated=child/"index.html"
            if generated.exists(): generated.unlink()
            try: child.rmdir()
            except OSError: pass
    for record in records:
        target=STORIES/str(record["id"]); target.mkdir(parents=True,exist_ok=True); (target/"index.html").write_text(page(record,records),encoding="utf-8")
    (STORIES/"index.html").write_text(index_page(records),encoding="utf-8")
    print(f"Published {len(records)} autonomous source-backed story timelines")

if __name__ == "__main__": main()
