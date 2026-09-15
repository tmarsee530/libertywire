#!/usr/bin/env python3
from pathlib import Path
import json,re
from html import escape
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[1];p=root/'index.html';s=p.read_text();css='<link rel="stylesheet" href="assets/homepage-v2.css?v=6">';js='<script src="assets/homepage-v2.js?v=6" defer></script>';changed=False
for old in tuple(f'<link rel="stylesheet" href="assets/homepage-v2.css?v={i}">' for i in range(1,6))+('<link rel="stylesheet" href="assets/homepage-v2.css">',):
 if old in s:s=s.replace(old,css);changed=True
for old in tuple(f'<script src="assets/homepage-v2.js?v={i}" defer></script>' for i in range(1,6))+('<script src="assets/homepage-v2.js" defer></script>',):
 if old in s:s=s.replace(old,js);changed=True
if css not in s:s=s.replace('</head>',css+'\n</head>',1);changed=True
if js not in s:s=s.replace('</body>',js+'\n</body>',1);changed=True
if '<a class="skip-link" href="#main-content">Skip to main content</a>' not in s:s=s.replace('<body>','<body>\n<a class="skip-link" href="#main-content">Skip to main content</a>',1);changed=True
if '<main>' in s:s=s.replace('<main>','<main id="main-content">',1);changed=True
if 'Breaking News, Every Minute' in s:s=s.replace('RALLY POINT NEWS — Breaking News, Every Minute','RALLY POINT NEWS — Multi-Source News Intelligence');changed=True
if 'MAX_DATASET_AGE_MIN=45' in s:s=s.replace('MAX_DATASET_AGE_MIN=45','MAX_DATASET_AGE_MIN=180');changed=True
ns=re.sub(r'<div class="tone-index"[^>]*>.*?</div>','',s,count=1,flags=re.S)
if ns!=s:s=ns;changed=True
nav='''<!-- RALLY_POINT_CORE_NAV_START -->
<nav class="newsroom-nav newsroom-nav-core" aria-label="Rally Point sections"><a href="#lead-wrap">Top Story</a><a href="#grid">Source Monitor</a><a href="briefs/" data-rp-event="rally_briefs_nav_click">AI Newsroom</a><a href="topics/" data-rp-event="topics_nav_click">Topics</a><a href="local/" data-rp-event="local_rally_nav_click">Local Rally</a><a href="games/" data-rp-event="games_nav_click">Games</a><a href="sources/">Sources</a><a href="newsletter/" data-rp-event="newsletter_nav_click">Newsletter</a></nav>
<!-- RALLY_POINT_CORE_NAV_END -->'''
m=re.search(r'<!-- RALLY_POINT_CORE_NAV_START -->.*?<!-- RALLY_POINT_CORE_NAV_END -->',s,re.S)
if m:
 if m.group()!=nav:s=s[:m.start()]+nav+s[m.end():];changed=True
elif '</header>' in s:s=s.replace('</header>','</header>\n'+nav,1);changed=True
method='''<!-- RALLY_POINT_METHOD_NOTE_START -->
<aside class="method-note method-note-core" aria-label="How Rally Point works"><strong>How Rally Point works:</strong> source monitoring identifies developing stories. Rally Point reporting is organized by editorial importance using neutral news-value signals such as public consequence, geographic reach, institutional significance, safety and economic impact; recency is secondary. <a href="sources/">See the methodology and source roster.</a></aside>
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
bp=root/'data'/'briefs.json'
if bp.exists():
 try:briefs=json.loads(bp.read_text()).get('briefs') or [];top=max(briefs,key=importance) if briefs else None
 except:top=None
 if top:
  title=escape(str(top.get('title') or 'Read the top Rally Point report'));url=escape(str(top.get('url') or '/briefs/'),quote=True);description=escape(str(top.get('description') or 'Original context and synthesis from the Rally Point News Desk.'))
  brief=f'''<!-- RALLY_POINT_LATEST_BRIEF_START -->
<aside class="latest-brief latest-brief-core" aria-label="Top Rally Point report"><div class="brief-eyebrow">Top Story · AI Newsroom</div><div class="brief-copy"><a class="brief-title" data-rp-event="rally_brief_click" href="{url}">{title}</a><div class="brief-dek">{description}</div><a class="brief-cta" data-rp-event="rally_brief_click" href="{url}">Read the Report →</a></div></aside>
<!-- RALLY_POINT_LATEST_BRIEF_END -->'''
  m=re.search(r'<!-- RALLY_POINT_LATEST_BRIEF_START -->.*?<!-- RALLY_POINT_LATEST_BRIEF_END -->',s,re.S)
  if m:
   if m.group()!=brief:s=s[:m.start()]+brief+s[m.end():];changed=True
  else:
   marker='<div class="section-label"><span>The Wire</span>'
   if marker in s:s=s.replace(marker,brief+'\n'+marker,1);changed=True
if changed:p.write_text(s);print('Installed homepage with importance-ranked AI Newsroom lead')
else:print('Homepage v2 already installed')
