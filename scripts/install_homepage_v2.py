#!/usr/bin/env python3
from pathlib import Path
import html,json,re
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[1];p=root/'index.html';s=p.read_text();changed=False
css='<link rel="stylesheet" href="assets/homepage-v2.css?v=21">';js='<script src="assets/homepage-v2.js?v=21" defer></script>'
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
nav='''<!-- RALLY_POINT_CORE_NAV_START -->\n<nav class="newsroom-nav newsroom-nav-core" aria-label="Rally Point sections"><a href="#lead">Top Stories</a><a href="#grid">The Wire</a></nav>\n<!-- RALLY_POINT_CORE_NAV_END -->'''
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
 def new_labels(cov):
  if not cov:return []
  seen=set();out=[]
  def norm(part):return re.sub(r"^[^a-z0-9']+|[^a-z0-9']+$",'',part.lower())
  def content(n):return len(n)>3 and n not in stop
  for i,item in enumerate(cov):
   title=str(item.get('title') or '');parts=title.split();ns=[norm(x) for x in parts]
   if i==0:
    seen.update(n for n in ns if content(n));out.append((item,title));continue
   fresh={n for n in ns if content(n) and n not in seen}
   if not fresh:continue
   first=next((j for j,n in enumerate(ns) if n in fresh),0);last=max(j for j,n in enumerate(ns) if n in fresh)
   while first>0 and ns[first-1] and len(ns[first-1])<=3:first-=1
   while last+1<len(ns) and ns[last+1] and len(ns[last+1])<=3:last+=1
   label=[]
   for j in range(first,last+1):
    n=ns[j]
    if not n:continue
    if content(n) and n in seen:continue
    label.append(parts[j])
   seen.update(fresh)
   text=' '.join(label).strip(' ,;:.!?–—-')
   if text:out.append((item,text))
  return out
 rows=[]
 for story in stories:
  labeled=new_labels(distinct([x for x in story.get('coverage',[]) if x.get('link')],8))
  if not labeled:continue
  first=labeled[0][0];related=labeled[1:]
  primary='<a href="'+e(first['link'])+'" rel="noopener" title="'+e(first.get('title'))+'">'+e(first.get('title') or story.get('title'))+'</a>'
  related_html=' · '.join('<a href="'+e(x['link'])+'" rel="noopener" title="'+e(x.get('title'))+'">'+e(label)+'</a> <span>'+e(x.get('source'))+'</span>' for x,label in related)
  rows.append('<section class="server-story"><h2>'+primary+'</h2>'+(('<p>'+related_html+'</p>') if related_html else '')+'</section>')
 block='<!-- RALLY_POINT_SERVER_WIRE_START --><div id="server-wire" aria-label="Current headlines">'+''.join(rows)+'</div><!-- RALLY_POINT_SERVER_WIRE_END -->'
 old=re.search(r'<!-- RALLY_POINT_SERVER_WIRE_START -->.*?<!-- RALLY_POINT_SERVER_WIRE_END -->',s,re.S)
 if old:
  if old.group()!=block:s=s[:old.start()]+block+s[old.end():];changed=True
 else:
  marker='<main id="main-content">'
  if marker in s:s=s.replace(marker,marker+'\n'+block,1);changed=True
except (OSError,json.JSONDecodeError):pass
if changed:p.write_text(s);print('Installed Rally Point homepage with non-repetitive crawlable topic stacks')
else:print('Rally Point composed homepage already installed')
