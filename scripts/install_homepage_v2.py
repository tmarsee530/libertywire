#!/usr/bin/env python3
from pathlib import Path
import json,re
from html import escape
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[1];p=root/'index.html';s=p.read_text();changed=False
css='<link rel="stylesheet" href="assets/homepage-v2.css?v=8">';js='<script src="assets/homepage-v2.js?v=8" defer></script>'
ns=re.sub(r'<link rel="stylesheet" href="assets/homepage-v2\.css(?:\?v=\d+)?">',css,s)
if ns!=s:s=ns;changed=True
ns=re.sub(r'<script src="assets/homepage-v2\.js(?:\?v=\d+)?" defer></script>',js,s)
if ns!=s:s=ns;changed=True
if css not in s:s=s.replace('</head>',css+'\n</head>',1);changed=True
if js not in s:s=s.replace('</body>',js+'\n</body>',1);changed=True
if '<a class="skip-link" href="#main-content">Skip to main content</a>' not in s:s=s.replace('<body>','<body>\n<a class="skip-link" href="#main-content">Skip to main content</a>',1);changed=True
if '<main>' in s:s=s.replace('<main>','<main id="main-content">',1);changed=True
repls={
 'Rally Point News — AI-Native Multi-Source Newsroom':'Rally Point News — Top Stories, Rally Briefs & Live Headlines',
 'Original multi-source reporting synthesized by the Rally Point News AI newsroom, with sources and uncertainty kept visible.':'Top stories ranked by importance, original source-based Rally Briefs, and live headlines from across the news landscape.',
 'AI-assisted original multi-source reporting with sources and uncertainty kept visible.':'Top stories, original source-based Rally Briefs, and transparent source links.',
 'Rally Point News — AI Newsroom':'Rally Point News — Rally Briefs'
}
for a,b in repls.items():
 if a in s:s=s.replace(a,b);changed=True
if 'MAX_DATASET_AGE_MIN=45' in s:s=s.replace('MAX_DATASET_AGE_MIN=45','MAX_DATASET_AGE_MIN=180');changed=True
ns=re.sub(r'<div class="tone-index"[^>]*>.*?</div>','',s,count=1,flags=re.S)
if ns!=s:s=ns;changed=True
nav='''<!-- RALLY_POINT_CORE_NAV_START -->
<nav class="newsroom-nav newsroom-nav-core" aria-label="Rally Point sections"><a href="#ai-newsroom-home">Top Stories</a><a href="briefs/" data-rp-event="rally_briefs_nav_click">Rally Briefs</a><a href="#grid">Rally Wire</a><a href="topics/" data-rp-event="topics_nav_click">Topics</a><a href="local/" data-rp-event="local_rally_nav_click">Local Rally</a><a href="games/" data-rp-event="games_nav_click">Games</a><a href="sources/">Sources</a><a href="newsletter/" data-rp-event="newsletter_nav_click">Newsletter</a></nav>
<!-- RALLY_POINT_CORE_NAV_END -->'''
m=re.search(r'<!-- RALLY_POINT_CORE_NAV_START -->.*?<!-- RALLY_POINT_CORE_NAV_END -->',s,re.S)
if m:
 if m.group()!=nav:s=s[:m.start()]+nav+s[m.end():];changed=True
elif '</header>' in s:s=s.replace('</header>','</header>\n'+nav,1);changed=True
method='''<!-- RALLY_POINT_METHOD_NOTE_START -->
<aside class="method-note method-note-core" aria-label="How Rally Point works"><strong>How Rally Point works:</strong> Headlines and Rally Briefs are organized by neutral news-value signals including public consequence, geographic reach, institutional significance, safety and economic impact. Recency is secondary to importance. <a href="sources/">Sources and methodology.</a></aside>
<!-- RALLY_POINT_METHOD_NOTE_END -->'''
m=re.search(r'<!-- RALLY_POINT_METHOD_NOTE_START -->.*?<!-- RALLY_POINT_METHOD_NOTE_END -->',s,re.S)
if m:
 if m.group()!=method:s=s[:m.start()]+method+s[m.end():];changed=True
elif '<!-- RALLY_POINT_CORE_NAV_END -->' in s:s=s.replace('<!-- RALLY_POINT_CORE_NAV_END -->','<!-- RALLY_POINT_CORE_NAV_END -->\n'+method,1);changed=True
def importance(b):
 try:
  if b.get('importance_score') is not None:return float(b['importance_score'])
 except:pass
 t=(' '+str(b.get('title',''))+' '+str(b.get('description',''))+' ').lower();score=50
 for term,w in {'supreme court':18,'congress':15,'federal':12,'president':12,'election':14,'midterm':14,'ballot':13,'court':10,'war':18,'attack':14,'shipping':9,'oil':11,'market':8,'tariff':9,'emergency':10,'crash':12,'killed':12,'hurricane':10,'fema':10,'usps':8,'artificial intelligence':8,'crypto':6,'shutdown':10}.items():
  if term in t:score+=w
 try:
  dt=datetime.fromisoformat(str(b.get('published_at','')).replace('Z','+00:00'));dt=dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc);score+=max(0,12-max(0,(datetime.now(timezone.utc)-dt).total_seconds()/86400)*2)
 except:pass
 try:score+=min(8,max(0,int(b.get('source_count') or 0)-2)*2)
 except:pass
 return score
def image_for(b):
 for k in ('image','image_url','lead_image','hero_image'):
  if b.get(k):return str(b[k])
 return ''
bp=root/'data'/'briefs.json';briefs=[]
if bp.exists():
 try:briefs=json.loads(bp.read_text()).get('briefs') or []
 except:briefs=[]
ranked=sorted(briefs,key=lambda b:(importance(b),str(b.get('published_at') or '')),reverse=True)[:6]
if ranked:
 cards=[]
 for i,b in enumerate(ranked):
  title=escape(str(b.get('title') or 'Rally Point Report'));url=escape(str(b.get('url') or '/briefs/'),quote=True);desc=escape(str(b.get('description') or ''));img=image_for(b);sources=b.get('source_count')
  visual=f'<a class="ai-home-visual" href="{url}"><img src="{escape(img,quote=True)}" alt="{escape(str(b.get("image_alt") or b.get("title") or ""),quote=True)}" width="1200" height="675" loading="{("eager" if i==0 else "lazy")}" decoding="async"></a>' if img else f'<a class="ai-home-visual ai-home-placeholder" href="{url}" aria-label="Read {title}"><span>RALLY POINT</span><b>{"TOP REPORT" if i==0 else "RALLY BRIEF"}</b></a>'
  cards.append(f'<article class="ai-home-card {"lead-report" if i==0 else ""}">{visual}<div class="ai-home-copy"><div class="ai-home-meta">{"Top Report" if i==0 else "Rally Brief"}{(" · "+str(int(sources))+" sources") if sources else ""}</div><h3><a href="{url}" data-rp-event="rally_brief_click">{title}</a></h3>{f"<p>{desc}</p>" if desc else ""}<a class="ai-home-read" href="{url}" data-rp-event="rally_brief_click">Read report →</a></div></article>')
 newsroom='''<!-- RALLY_POINT_AI_NEWSROOM_START -->
<section class="ai-newsroom-home ai-newsroom-home-static" id="ai-newsroom-home" aria-labelledby="ai-newsroom-heading"><div class="ai-newsroom-head"><div><div class="ai-newsroom-eyebrow">Rally Point Reports</div><h2 id="ai-newsroom-heading">The stories that matter most.</h2><p>Original source-based reports ordered by editorial importance, not simply publication time.</p></div><a href="briefs/" data-rp-event="rally_briefs_nav_click">All Rally Briefs →</a></div><div class="ai-newsroom-grid">'''+''.join(cards)+'''</div></section>
<!-- RALLY_POINT_AI_NEWSROOM_END -->'''
 m=re.search(r'<!-- RALLY_POINT_AI_NEWSROOM_START -->.*?<!-- RALLY_POINT_AI_NEWSROOM_END -->',s,re.S)
 if m:
  if m.group()!=newsroom:s=s[:m.start()]+newsroom+s[m.end():];changed=True
 else:
  anchor='<!-- RALLY_POINT_METHOD_NOTE_END -->'
  if anchor in s:s=s.replace(anchor,anchor+'\n'+newsroom,1);changed=True
if '<div class="section-label"><span>The Wire</span>' in s:s=s.replace('<div class="section-label"><span>The Wire</span>','<div class="section-label"><span>Rally Wire</span>',1);changed=True
if '<div class="section-label"><span>Source Monitor</span>' in s:s=s.replace('<div class="section-label"><span>Source Monitor</span>','<div class="section-label"><span>Rally Wire</span>',1);changed=True
ns=re.sub(r'<span>Rally Wire</span><small>.*?</small>','<span>Rally Wire</span><small>Live headlines from across the source network</small>',s,count=1,flags=re.S)
if ns!=s:s=ns;changed=True
ns=re.sub(r'\n?<!-- RALLY_POINT_LATEST_BRIEF_START -->.*?<!-- RALLY_POINT_LATEST_BRIEF_END -->\n?','\n',s,flags=re.S)
if ns!=s:s=ns;changed=True
if changed:p.write_text(s);print(f'Installed Rally Point command-center homepage with {len(ranked)} importance-ranked reports')
else:print('Rally Point command-center homepage already installed')
