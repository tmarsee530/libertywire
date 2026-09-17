#!/usr/bin/env python3
from pathlib import Path
import html,json,re
from datetime import datetime
root=Path(__file__).resolve().parents[1];p=root/'index.html';s=p.read_text();changed=False
# The v2 stylesheet is self-contained. Remove the obsolete original theme and hidden chrome
# Remove the obsolete pre-v2 live-wire runtime too. It independently refreshed #lead/#grid every 60 seconds and could overwrite the current homepage after initial render.
ns=re.sub(r'\n?<script>\s*const FEEDS=\[.*?setInterval\(refresh,REFRESH_MS\);\s*</script>','',s,count=1,flags=re.S)
if ns!=s:s=ns;changed=True
# so visitors and crawlers do not download/parse an interface that no longer exists.
for pattern in [r'\n?<link rel="preconnect" href="https://fonts\.googleapis\.com">',r'\n?<link rel="preconnect" href="https://fonts\.gstatic\.com" crossorigin>',r'\n?<link href="https://fonts\.googleapis\.com/css2\?[^\"]+" rel="stylesheet">',r'\n?<style>.*?</style>',r'\n?<div class="utility-bar">.*?</div>',r'\n?<div class="ticker-bar".*?</div></div></div>']:
 ns=re.sub(pattern,'',s,count=1,flags=re.S)
 if ns!=s:s=ns;changed=True
css='<link rel="stylesheet" href="assets/homepage-v2.css?v=28">';js='<script src="assets/homepage-v2.js?v=28" defer></script>'
ns=re.sub(r'<link rel="stylesheet" href="assets/homepage-v2\.css(?:\?v=\d+)?">',css,s)
if ns!=s:s=ns;changed=True
ns=re.sub(r'<script src="assets/homepage-v2\.js(?:\?v=\d+)?" defer></script>',js,s)
if ns!=s:s=ns;changed=True
if css not in s:s=s.replace('</head>',css+'\n</head>',1);changed=True
if js not in s:s=s.replace('</body>',js+'\n</body>',1);changed=True
if '<a class="skip-link" href="#main-content">Skip to main content</a>' not in s:s=s.replace('<body>','<body>\n<a class="skip-link" href="#main-content">Skip to main content</a>',1);changed=True
if '<main>' in s:s=s.replace('<main>','<main id="main-content">',1);changed=True
for a,b in {'Rally Point News — AI-Native Multi-Source Newsroom':'Rally Point News — Top Stories & The Wire','Rally Point News — Top Stories, Rally Briefs & Live Headlines':'Rally Point News — Top Stories & The Wire','Original multi-source reporting synthesized by the Rally Point News AI newsroom, with sources and uncertainty kept visible.':'Top stories and a fast, continuously updated wire of headlines from across the news landscape.','Top stories ranked by importance, original source-based Rally Briefs, and live headlines from across the news landscape.':'Top stories and a fast, continuously updated wire of headlines from across the news landscape.'}.items():
 if a in s:s=s.replace(a,b);changed=True
nav='''<!-- RALLY_POINT_CORE_NAV_START -->\n<nav class="newsroom-nav newsroom-nav-core" aria-label="Rally Point sections"><a href="#lead">Top Stories</a><a href="#grid">The Wire</a><a href="/sources/">Sources</a><a href="/about/">About</a></nav>\n<!-- RALLY_POINT_CORE_NAV_END -->'''
m=re.search(r'<!-- RALLY_POINT_CORE_NAV_START -->.*?<!-- RALLY_POINT_CORE_NAV_END -->',s,re.S)
if m:
 if m.group()!=nav:s=s[:m.start()]+nav+s[m.end():];changed=True
elif '</header>' in s:s=s.replace('</header>','</header>\n'+nav,1);changed=True
preferred='''<!-- RALLY_POINT_PREFERRED_SOURCE_START -->\n<a class="preferred-source" href="https://www.google.com/preferences/source?q=rallypointnews.com" rel="noopener" target="_blank" aria-label="Add Rally Point News as a preferred source in Google">Add Rally Point to Google Preferred Sources</a>\n<!-- RALLY_POINT_PREFERRED_SOURCE_END -->'''
pm=re.search(r'<!-- RALLY_POINT_PREFERRED_SOURCE_START -->.*?<!-- RALLY_POINT_PREFERRED_SOURCE_END -->',s,re.S)
if pm:
 if pm.group()!=preferred:s=s[:pm.start()]+preferred+s[pm.end():];changed=True
elif '<!-- RALLY_POINT_CORE_NAV_END -->' in s:s=s.replace('<!-- RALLY_POINT_CORE_NAV_END -->','<!-- RALLY_POINT_CORE_NAV_END -->\n'+preferred,1);changed=True
for pattern in [r'\n?<!-- RALLY_POINT_METHOD_NOTE_START -->.*?<!-- RALLY_POINT_METHOD_NOTE_END -->\n?',r'\n?<!-- RALLY_POINT_AI_NEWSROOM_START -->.*?<!-- RALLY_POINT_AI_NEWSROOM_END -->\n?',r'\n?<!-- RALLY_POINT_LATEST_BRIEF_START -->.*?<!-- RALLY_POINT_LATEST_BRIEF_END -->\n?']:
 ns=re.sub(pattern,'\n',s,flags=re.S)
 if ns!=s:s=ns;changed=True
for old in ('Rally Wire','Source Monitor'):
 if f'<div class="section-label"><span>{old}</span>' in s:s=s.replace(f'<div class="section-label"><span>{old}</span>','<div class="section-label"><span>The Wire</span>',1);changed=True
ns=re.sub(r'<span>The Wire</span><small>.*?</small>','<span>The Wire</span><small>The essential developing stories</small>',s,count=1,flags=re.S)
if ns!=s:s=ns;changed=True
try:
 d=json.loads((root/'data/storylines.json').read_text());stories=d.get('storylines',[])[:24]
 def e(v):return html.escape(str(v or ''),quote=True)
 stop={'the','and','for','from','with','into','over','after','amid','says','said','report','reports','live','update','updates','latest','breaking','exclusive','video','photo','photos','this','that','these','those','new','news'}
 def toks(title):return {w for w in re.findall(r"[a-z0-9']+",str(title or '').lower()) if len(w)>3 and w not in stop}
 def epoch(item):
  raw=item.get('date')
  if not raw:return 0
  try:return datetime.fromisoformat(str(raw).replace('Z','+00:00')).timestamp()
  except (ValueError,TypeError):return 0
 def distinct(cov,limit=8):
  if not cov:return []
  kept=[cov[0]];seen=set(toks(cov[0].get('title')));pool=list(cov[1:]);newest=max([epoch(x) for x in cov] or [0])
  while pool and len(kept)<limit:
   best_i=-1;best_score=-1;best_novel=set()
   for i,item in enumerate(pool):
    t=toks(item.get('title'))
    if not t:continue
    novel=t-seen;overlap=len(t&seen)/max(1,len(t))
    if len(novel)<2 and overlap>=.62:continue
    freshness=max(0,1-max(0,newest-epoch(item))/(12*3600)) if newest else 0
    score=len(novel)*2+(1-overlap)*2+freshness
    if score>best_score:best_i=i;best_score=score;best_novel=novel
   if best_i<0:break
   picked=pool.pop(best_i);kept.append(picked);seen|=best_novel
  return kept
 def labels(cov):
  if not cov:return []
  seen=set(toks(cov[0].get('title')));out=[(cov[0],str(cov[0].get('title') or ''))]
  for item in cov[1:]:
   title=str(item.get('title') or '');all_words=toks(title);novel=all_words-seen
   if not novel:continue
   clauses=[x.strip() for x in re.split(r'\s*(?:[|;]|\s[—–]\s|:\s+)\s*',title) if x.strip()]
   best='';best_score=-1
   for clause in clauses:
    cw=toks(clause);fresh=len(cw-seen);repeated=len(cw&seen);count=len(re.findall(r"[A-Za-z0-9']+",clause))
    if fresh<2 or count<4:continue
    score=fresh*3-repeated*.8+(1 if count>=5 else 0)
    if score>best_score:best,best_score=clause,score
   display=best or title;out.append((item,display));seen|=toks(display)
  return out
 rows=[]
 for story in stories:
  labeled=labels(distinct([x for x in story.get('coverage',[]) if x.get('link')],8))
  if not labeled:continue
  first=labeled[0][0];related=labeled[1:];hot=story.get('status')=='hot'
  primary='<a href="'+e(first['link'])+'" rel="noopener" title="'+e(first.get('title'))+'">'+e(first.get('title') or story.get('title'))+'</a>'
  related_html=' · '.join('<a href="'+e(x['link'])+'" rel="noopener" title="'+e(x.get('title'))+'" aria-label="'+e(x.get('title'))+'">'+e(label)+'</a> <span>'+e(x.get('source'))+'</span>' for x,label in related)
  rows.append('<section class="server-story'+(' is-hot' if hot else '')+'"><h2>'+primary+'</h2>'+(('<p>'+related_html+'</p>') if related_html else '')+'</section>')
 block='<!-- RALLY_POINT_SERVER_WIRE_START --><div id="server-wire" aria-label="Current headlines">'+''.join(rows)+'</div><!-- RALLY_POINT_SERVER_WIRE_END -->'
 old=re.search(r'<!-- RALLY_POINT_SERVER_WIRE_START -->.*?<!-- RALLY_POINT_SERVER_WIRE_END -->',s,re.S)
 if old:
  if old.group()!=block:s=s[:old.start()]+block+s[old.end():];changed=True
 else:
  marker='<main id="main-content">'
  if marker in s:s=s.replace(marker,marker+'\n'+block,1);changed=True
except (OSError,json.JSONDecodeError):pass
if changed:p.write_text(s);print('Installed lean Rally Point homepage shell with resilient Wire fallback')
else:print('Rally Point lean homepage already installed')
