#!/usr/bin/env python3
"""Publish autonomous, source-backed developing-story timelines."""
from __future__ import annotations

import html, json, re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import urlparse
try:
    from timeline_intelligence import SCHEMA_VERSION, canonical_link, serializable_model
except ModuleNotFoundError:  # package import in the unit-test runner
    from scripts.timeline_intelligence import SCHEMA_VERSION, canonical_link, serializable_model

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / "data" / "history.json"
CURRENT = ROOT / "data" / "storylines.json"
STORIES = ROOT / "stories"
BASE = "https://rallypointnews.com"
MAX_PAGES = 500
MANIFEST = ROOT / "data" / "published_timelines.json"
STATE_INDEX = ROOT / "data" / "timeline_state_index.json"
LONG_TIMELINE_THRESHOLD = 9
VISIBLE_RECENT_UPDATES = 6


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

def timeline_model(record):
    if int(record.get("timeline_schema_version", 0) or 0) == SCHEMA_VERSION and isinstance(record.get("updates"), list) and record.get("current_status"):
        return {
            "timeline_schema_version": SCHEMA_VERSION,
            "current_status": record["current_status"],
            "material_update_count": int(record.get("material_update_count", len(record["updates"])) or 0),
            "updates": record["updates"],
        }
    return serializable_model(record)

def eligible(record, legacy_ids=None):
    families = int(record.get("max_source_family_count", 0) or 0)
    coverage = record.get("coverage") or []
    title = clean_title(record.get("current_title")).lower()
    if any(marker in title for marker in ("weekly quiz", "morning greatness")): return False
    distinct_families = {family_name(x.get("source")) for x in coverage if x.get("source")}
    # A durable page must contain enough distinct developments to justify its own URL,
    # not merely three publishers repeating essentially the same headline.
    development_count = timeline_model(record)["material_update_count"]
    qualifies = bool(record.get("id") and len(coverage) >= 3 and families >= 3 and len(distinct_families) >= 3 and development_count >= 2)
    # Once a canonical story URL has been published, keep it stable while the
    # retained history record exists—even if stronger deduplication compresses it.
    return qualifies or bool(record.get("id") in set(legacy_ids or ()) and coverage)

def snapshot_titles(coverage):
    """Keep only publisher wording that contributes meaningful new information."""
    stop={"this","that","with","from","after","about","into","over","news","live","latest","breaking","update","updates","report","reports","says","said","exclusive","video","photos","photo","amid","have","will","their","they","more","story","developing"}
    state={"approves","approved","blocks","blocked","orders","ordered","resigns","resigned","dies","died","killed","arrests","arrested","indicts","indicted","charges","charged","wins","won","loses","lost","launches","launched","strikes","struck","evacuates","evacuated","confirms","confirmed","withdraws","withdrew","suspends","suspended","rejects","rejected","passes","passed","fails","failed","overturns","overturned","delays","delayed","cancels","canceled","cancelled","announces","announced"}
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
            decisive={x for x in novel if x in state or any(ch.isdigit() for ch in x)}
            if len(novel)<2 and not decisive:
                continue
            candidates=[]
            for clause in clauses(title):
                words=toks(clause)
                clause_novel=words-seen
                repeated=words&seen
                count=len(re.findall(r"[A-Za-z0-9']+",clause))
                clause_decisive={x for x in clause_novel if x in state or any(ch.isdigit() for ch in x)}
                if (len(clause_novel)>=2 or clause_decisive) and 2<=count<=16:
                    candidates.append((len(clause_novel)*5+len(clause_decisive)*3-len(repeated)*2,-count,clause))
            if not candidates:
                # Do not repeat the full headline just because clause extraction failed.
                continue
            label=max(candidates)[2]
        words=toks(label)
        if i:
            remaining=words-seen
            if len(remaining)<2 and not {x for x in remaining if x in state or any(ch.isdigit() for ch in x)}:
                continue
        out.append((item,label))
        # Learn from the full source headline, not just the displayed fragment, so
        # subsequent entries cannot repackage information already encountered.
        seen|=title_words
    return out

def analytics_tag():
    # Kept outside f-strings so JavaScript braces can never be interpreted by Python.
    return '<script async src="https://www.googletagmanager.com/gtag/js?id=G-KKT59K667B"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag("js",new Date());gtag("config","G-KKT59K667B");</script><script src="/assets/timeline-state.js?v=2" defer></script>'

def source_links(update, compact=False):
    sources=update.get("sources") or [{"source":update.get("source"),"link":update.get("link"),"title":update.get("source_title")}]
    links=[]
    for source in sources[:3]:
        link=source.get("link")
        if not link: continue
        name=source.get("source") or source_domain(link)
        links.append(f'<a href="{esc(link)}" rel="noopener" target="_blank" title="{esc(source.get("title"))}">{esc(name)} ↗</a>')
    extra=max(0,len(sources)-3)
    more=f'<span>+{extra} more source{"s" if extra!=1 else ""}</span>' if extra else ""
    domain="" if compact else f'<span>{esc(source_domain(update.get("link")))}</span>'
    return " · ".join(links)+more+domain

def update_html(update, compact=False):
    classification=clean_title(update.get("classification")) or "UPDATE"
    return f'''<li class="timeline-update{' compact' if compact else ''}" data-update-id="{esc(update.get('id'))}" data-published="{esc(update.get('date'))}"><time datetime="{esc(update.get('date'))}">{esc(display_time(update.get('date')))}</time><div><p class="update-class update-{esc(classification.lower().replace(' ','-'))}">{esc(classification)}</p><h2>{esc(update.get('label'))}</h2><p class="update-sources">{source_links(update,compact)}</p></div></li>'''

def page(record, published_records):
    sid = esc(record["id"]); title = clean_title(record.get("current_title")) or "Developing story"
    model=timeline_model(record); updates=list(model["updates"]); newest=list(reversed(updates)); current=model["current_status"]
    summary=clean_title(current.get("summary")) or f"Rally Point is tracking material developments in {title}."
    description=(summary+f" Follow {title} in a source-backed, reverse-chronological timeline.")[:300]
    source_names=sorted({str(x.get("source") or "").strip() for update in updates for x in (update.get("sources") or []) if x.get("source")})
    if len(newest)>=LONG_TIMELINE_THRESHOLD:
        recent=newest[:VISIBLE_RECENT_UPDATES]; earlier=newest[VISIBLE_RECENT_UPDATES:]
    else:
        recent=newest; earlier=[]
    recent_html="".join(update_html(update) for update in recent)
    earlier_html=""
    if earlier:
        earlier_html=f'''<details class="earlier"><summary><strong>What happened earlier</strong><span>{len(earlier)} earlier development{"s" if len(earlier)!=1 else ""}</span></summary><ol class="timeline timeline-earlier" aria-label="Earlier developments, newest first">{"".join(update_html(update,True) for update in earlier)}</ol></details>'''
    current_source=(f'<a href="{esc(current.get("link"))}" rel="noopener" target="_blank">{esc(current.get("source") or source_domain(current.get("link")))} ↗</a>' if current.get("link") else "")
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
    schema_items=[{"@type":"ListItem","position":i+1,"name":update.get("label"),"url":update.get("link")} for i,update in enumerate(newest) if update.get("link") and update.get("label")]
    schema=json.dumps({"@context":"https://schema.org","@graph":[{"@type":"CollectionPage","@id":f"{BASE}/stories/{record['id']}/#page","name":title,"headline":title,"description":description,"url":f"{BASE}/stories/{record['id']}/","datePublished":record.get("first_seen"),"dateModified":record.get("last_seen"),"mainEntity":{"@type":"ItemList","numberOfItems":len(schema_items),"itemListOrder":"https://schema.org/ItemListOrderDescending","itemListElement":schema_items},"isPartOf":{"@type":"WebSite","name":"Rally Point News","url":BASE+"/"},"breadcrumb":{"@id":f"{BASE}/stories/{record['id']}/#breadcrumb"}},{"@type":"BreadcrumbList","@id":f"{BASE}/stories/{record['id']}/#breadcrumb","itemListElement":[{"@type":"ListItem","position":1,"name":"Rally Point News","item":BASE+"/"},{"@type":"ListItem","position":2,"name":"Live News Timelines","item":BASE+"/stories/"},{"@type":"ListItem","position":3,"name":title,"item":f"{BASE}/stories/{record['id']}/"}]}]},ensure_ascii=False).replace("</","<\\/")
    ga=analytics_tag()
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} — Live Timeline | Rally Point News</title><meta name="description" content="{esc(description)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{BASE}/stories/{sid}/">{ga}<meta property="og:type" content="website"><meta property="og:site_name" content="Rally Point News"><meta property="og:title" content="{esc(title)} — Live Timeline"><meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{BASE}/stories/{sid}/"><meta property="article:published_time" content="{esc(record.get('first_seen'))}"><meta property="article:modified_time" content="{esc(record.get('last_seen'))}"><meta name="twitter:card" content="summary"><meta name="twitter:title" content="{esc(title)} — Live Timeline"><meta name="twitter:description" content="{esc(description)}"><link rel="stylesheet" href="/assets/timeline.css?v=4"><script type="application/ld+json">{schema}</script></head><body><a class="skip-link" href="#timeline">Skip to updates</a><header><a class="mast" href="/">Rally Point News</a><nav><a href="/">Top Stories</a><a href="/#grid">The Wire</a><a href="/stories/">Live Timelines</a><a href="/sources/">Sources</a></nav></header><main><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>›</span><a href="/stories/">Live Timelines</a></nav><p class="status">{esc(status)}</p><h1>{esc(title)}</h1><p class="dek">A concise, source-backed record of what materially changed.</p><div class="story-meta"><span>Updated {esc(display_time(record.get('last_seen')))}</span><span>Tracking since {esc(display_time(record.get('first_seen')))}</span><span>{len(updates)} material developments</span><span>{len(source_names)} sources</span></div><section class="current-status" aria-labelledby="current-status-heading"><p class="status-kicker">{esc(current.get('classification') or 'CURRENT STATUS')}</p><h2 id="current-status-heading">Current status</h2><p class="status-summary">{esc(summary)}</p><p class="status-source"><time datetime="{esc(current.get('as_of'))}">As of {esc(display_time(current.get('as_of')))}</time>{' · '+current_source if current_source else ''}</p></section><div class="caught-up"><strong>NEWEST FIRST</strong><span>Eastern Time · material updates only</span></div><ol class="timeline" id="timeline" aria-label="Latest developments, newest first">{recent_html}</ol>{earlier_html}<div class="end-card"><strong>You’ve reached the beginning.</strong><span>That’s the earliest material development tracked in this story.</span></div><section class="sources"><h2>Sources tracking this story</h2><p>{esc(' · '.join(source_names))}</p></section>{related_section}<p class="back"><a href="/">← Back to Rally Point News</a></p></main><footer>Rally Point News · Headlines and reporting belong to their respective publishers. <a href="/about/">Editorial standards</a></footer></body></html>'''

def index_page(records):
    cards=[]
    for r in records:
        development_count=timeline_model(r)["material_update_count"]
        cards.append(f'''<article><p>{esc(str(r.get("status") or "developing").upper())}</p><h2><a href="/stories/{esc(r["id"])}/">{esc(clean_title(r.get("current_title")))}</a></h2><span>Updated {esc(display_time(r.get("last_seen")))} · {development_count} key developments</span></article>''')
    ga=analytics_tag()
    schema=json.dumps({"@context":"https://schema.org","@type":"CollectionPage","name":"Live News Timelines","url":BASE+"/stories/","description":"Finite, source-backed feeds of distinct developments in major ongoing stories.","mainEntity":{"@type":"ItemList","numberOfItems":len(records),"itemListElement":[{"@type":"ListItem","position":i+1,"url":f"{BASE}/stories/{r['id']}/","name":clean_title(r.get("current_title"))} for i,r in enumerate(records)]},"isPartOf":{"@type":"WebSite","name":"Rally Point News","url":BASE+"/"}},ensure_ascii=False).replace("</","<\\/")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Live News Timelines | Rally Point News</title><meta name="description" content="Follow major developing stories in finite, source-backed feeds with the newest distinct developments first."><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{BASE}/stories/">{ga}<meta property="og:type" content="website"><meta property="og:site_name" content="Rally Point News"><meta property="og:title" content="Live News Timelines | Rally Point News"><meta property="og:description" content="Finite, source-backed feeds of distinct developments in major ongoing stories."><meta property="og:url" content="{BASE}/stories/"><meta name="twitter:card" content="summary"><script type="application/ld+json">{schema}</script><link rel="stylesheet" href="/assets/timeline.css?v=4"></head><body><header><a class="mast" href="/">Rally Point News</a><nav><a href="/">Top Stories</a><a href="/#grid">The Wire</a><a href="/stories/">Live Timelines</a><a href="/sources/">Sources</a></nav></header><main><p class="status">LIVE STORY DESK</p><h1>Developing stories, without the endless scroll</h1><p class="dek">Finite feeds of the developments that matter. Open a story, scan what changed, and reach the end.</p><section class="timeline-index">{''.join(cards)}</section></main><footer>Rally Point News · <a href="/about/">Editorial standards</a></footer></body></html>'''

def follow_enabled_page(body, record):
    current=timeline_model(record)["current_status"]
    data=json.dumps({"timelineId":record["id"],"title":clean_title(record.get("current_title")),"currentStatus":clean_title(current.get("summary")),"lastUpdated":record.get("last_seen")},ensure_ascii=False).replace("</","<\\/")
    body=body.replace('/assets/timeline.css?v=4','/assets/timeline.css?v=5')
    body=body.replace('</head>',f'<script type="application/json" id="timeline-follow-data">{data}</script></head>',1)
    body=body.replace('<a href="/sources/">Sources</a>','<a href="/following/">Your Stories</a><a href="/sources/">Sources</a>',1)
    control='<div class="follow-row"><button type="button" class="follow-control" data-follow-control aria-pressed="false">Follow this story</button><span>Saved on this device</span></div>'
    return body.replace('</div><section class="current-status"',f'</div>{control}<section class="current-status"',1)

def following_page():
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Your Stories | Rally Point News</title><meta name="description" content="Stories you intentionally follow on this device."><meta name="robots" content="noindex,follow"><link rel="canonical" href="https://rallypointnews.com/following/"><script async src="https://www.googletagmanager.com/gtag/js?id=G-KKT59K667B"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}gtag("js",new Date());gtag("config","G-KKT59K667B");</script><script src="/assets/timeline-state.js?v=2" defer></script><script src="/assets/following.js?v=1" defer></script><link rel="stylesheet" href="/assets/timeline.css?v=5"></head><body><header><a class="mast" href="/">Rally Point News</a><nav><a href="/">Top Stories</a><a href="/stories/">Live Timelines</a><a href="/following/" aria-current="page">Your Stories</a><a href="/sources/">Sources</a></nav></header><main><p class="status">YOUR STORIES</p><h1>Stories you chose to follow</h1><p class="dek">A private, device-local list of developing stories you want to return to.</p><div id="following-status" class="following-status" role="status" aria-live="polite">Loading your stories…</div><section id="following-list" class="following-list" aria-label="Followed stories"></section></main><footer>Follows stay in this browser. No account is required. · <a href="/privacy/">Privacy</a></footer></body></html>'''

def main():
    payload=json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else {"storylines":[]}
    by_id={x.get("id"):x for x in payload.get("storylines",[]) if x.get("id")}
    current=json.loads(CURRENT.read_text(encoding="utf-8")) if CURRENT.exists() else {"storylines":[]}
    try:previous_ids=set(json.loads(MANIFEST.read_text(encoding="utf-8")).get("ids",[])) if MANIFEST.exists() else set()
    except (OSError,json.JSONDecodeError):previous_ids=set()
    for item in current.get("storylines",[]):
        sid=item.get("id")
        if not sid: continue
        prior=by_id.get(sid,{}); coverage={((x.get("source") or ""),canonical_link(x.get("link"))):x for x in prior.get("coverage",[])}
        for update in item.get("coverage",[]): coverage[(update.get("source") or "",canonical_link(update.get("link")))]=update
        merged={**prior,"id":sid,"current_title":item.get("title") or prior.get("current_title"),"last_seen":item.get("newest_date") or prior.get("last_seen"),"status":item.get("status") or prior.get("status"),"max_source_count":max(int(prior.get("max_source_count",0) or 0),int(item.get("source_count",0) or 0)),"max_source_family_count":max(int(prior.get("max_source_family_count",0) or 0),int(item.get("source_family_count",0) or 0)),"coverage":list(coverage.values())}
        by_id[sid]={**merged,**serializable_model(merged)}
    records=[x for x in by_id.values() if eligible(x,previous_ids)]; records.sort(key=lambda x:parse_dt(x.get("last_seen")),reverse=True); records=records[:MAX_PAGES]
    manifest={"generated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"timeline_schema_version":SCHEMA_VERSION,"count":len(records),"ids":[str(x["id"]) for x in records]}
    MANIFEST.parent.mkdir(parents=True,exist_ok=True); MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    state_index={"generated_at":manifest["generated_at"],"schema_version":2,"timelines":{str(x["id"]):{"title":clean_title(x.get("current_title")),"status":str(x.get("status") or "developing"),"currentStatus":clean_title(timeline_model(x)["current_status"].get("summary")),"last_updated":x.get("last_seen"),"url":f'/stories/{x["id"]}/',"update_ids":[u.get("id") for u in timeline_model(x)["updates"] if u.get("id")]} for x in records}}
    STATE_INDEX.write_text(json.dumps(state_index,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    STORIES.mkdir(parents=True,exist_ok=True); keep={str(record["id"]) for record in records}
    for child in STORIES.iterdir():
        if child.is_dir() and child.name not in keep:
            generated=child/"index.html"
            if generated.exists(): generated.unlink()
            try: child.rmdir()
            except OSError: pass
    for record in records:
        target=STORIES/str(record["id"]); target.mkdir(parents=True,exist_ok=True); (target/"index.html").write_text(follow_enabled_page(page(record,records),record),encoding="utf-8")
    (STORIES/"index.html").write_text(index_page(records).replace('<a href="/sources/">Sources</a>','<a href="/following/">Your Stories</a><a href="/sources/">Sources</a>',1),encoding="utf-8")
    following=ROOT/"following"; following.mkdir(parents=True,exist_ok=True); (following/"index.html").write_text(following_page(),encoding="utf-8")
    print(f"Published {len(records)} autonomous source-backed story timelines")

if __name__ == "__main__": main()
