#!/usr/bin/env python3
"""Render durable Rally Point topic pages from Brief metadata."""
from __future__ import annotations
import json,re
from html import escape
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data'/'briefs.json'
TOPICS={
'government-policy':('Government & Policy','Federal policy, courts, election administration and public agencies.',{'fema','judge','court','usps','ballot','midterms','tariff','policy','federal','government','congress','act','rules','president','dhs'}),
'world-markets':('World Affairs & Markets','Geopolitics, trade, energy markets and international shipping.',{'oil','saudi','shipping','red','sea','islands','hormuz','tariff','trade','market','markets','international','pipeline','houthi','whiskey'}),
'technology-digital-assets':('Technology & Digital Assets','Artificial intelligence, cryptocurrency, digital markets and technology policy.',{'ai','artificial','intelligence','crypto','cryptocurrency','digital','anthropic','openai','clarity','technology','frontier'}),
'weather-aviation-public-safety':('Weather, Aviation & Public Safety','Weather risk, aviation incidents, transportation safety and public-safety explainers.',{'hurricane','forecast','cone','weather','plane','air','aircraft','aviation','flight','runway','crash','landing','ntsb','safety','fema','emergency'}),
}
STOP={'the','and','for','from','with','what','why','how','did','does','after','new','mean','means','about','into','that','this'}
def toks(x):return {w for w in re.findall(r'[a-z0-9]+',str(x or '').lower()) if len(w)>2 and w not in STOP}
def matches(b,keys):return len(toks(f"{b.get('title','')} {b.get('description','')}")&keys)
def page(slug,name,dek,briefs):
 items=''.join(f'<article class="brief"><h2><a href="{escape(str(b.get("url") or "/briefs/"),quote=True)}">{escape(str(b.get("title") or "Rally Brief"))}</a></h2><p>{escape(str(b.get("description") or "Source-based Rally Point News explainer."))}</p></article>' for b in briefs)
 return f'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(name)} Explainers | Rally Point News</title><meta name="description" content="Rally Point News source-based explainers: {escape(dek)}"><link rel="canonical" href="https://rallypointnews.com/topics/{slug}/"><meta property="og:type" content="website"><meta property="og:site_name" content="Rally Point News"><meta property="og:title" content="{escape(name)} Explainers | Rally Point News"><meta property="og:description" content="{escape(dek)}"><meta property="og:url" content="https://rallypointnews.com/topics/{slug}/"><style>:root{{--ink:#11100e;--paper:#faf9f6;--navy:#0f1d38;--gold:#c8952c;--rule:#e4e1d8;--muted:#6f6a5e}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:Georgia,serif;line-height:1.65}}a{{color:var(--navy)}}header{{background:var(--navy);color:white;border-bottom:3px solid var(--gold);padding:32px 20px}}header div,main{{max-width:820px;margin:auto}}header a{{color:var(--gold)}}h1{{font:800 clamp(32px,6vw,52px)/1.05 Arial,sans-serif;margin:10px 0}}.dek{{color:#d8dfeb}}.brief{{padding:24px 0;border-bottom:1px solid var(--rule)}}.brief h2{{font:800 24px Arial,sans-serif;margin:0 0 8px}}.brief p{{color:var(--muted);margin:0}}main{{padding:36px 20px 70px}}footer{{text-align:center;padding:28px;background:var(--ink);color:#aaa}}footer a{{color:var(--gold)}}</style><script type="application/ld+json">{{"@context":"https://schema.org","@graph":[{{"@type":"CollectionPage","name":"{escape(name)} Explainers","url":"https://rallypointnews.com/topics/{slug}/"}},{{"@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Rally Point News","item":"https://rallypointnews.com/"}},{{"@type":"ListItem","position":2,"name":"Topics","item":"https://rallypointnews.com/topics/"}},{{"@type":"ListItem","position":3,"name":"{escape(name)}","item":"https://rallypointnews.com/topics/{slug}/"}}]}}]}}</script></head><body><header><div><a href="/topics/">← All Topics</a><h1>{escape(name)}</h1><p class="dek">{escape(dek)}</p></div></header><main>{items}<p style="margin-top:30px"><a href="/briefs/">Browse all Rally Briefs →</a></p></main><footer><a href="/">Rally Point News</a> · <a href="/topics/">Topics</a> · <a href="/sources/">Sources &amp; Methodology</a></footer></body></html>'''
def main():
 briefs=json.loads(DATA.read_text(encoding='utf-8')).get('briefs',[]);changed=0
 for slug,(name,dek,keys) in TOPICS.items():
  chosen=[b for b in briefs if matches(b,keys)>0];chosen.sort(key=lambda b:(matches(b,keys),b.get('published_at','')),reverse=True)
  if len(chosen)<2:continue
  path=ROOT/'topics'/slug/'index.html';path.parent.mkdir(parents=True,exist_ok=True);out=page(slug,name,dek,chosen)
  if not path.exists() or path.read_text(encoding='utf-8')!=out:path.write_text(out,encoding='utf-8');changed+=1
 print(f'Rendered {changed} changed topic pages')
if __name__=='__main__':main()
