#!/usr/bin/env python3
from pathlib import Path
import html,json,re
root=Path(__file__).resolve().parents[1];p=root/'index.html';s=p.read_text();changed=False
css='<link rel="stylesheet" href="assets/homepage-v2.css?v=17">';js='<script src="assets/homepage-v2.js?v=17" defer></script>'
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
 rows=[]
 for story in stories:
  cov=[x for x in story.get('coverage',[]) if x.get('link')][:4]
  if not cov:continue
  rows.append('<section class="server-story"><h2>'+e(cov[0].get('title') or story.get('title'))+'</h2><p>'+' · '.join('<a href="'+e(x['link'])+'" rel="noopener">'+e(x.get('title'))+'</a> <span>'+e(x.get('source'))+'</span>' for x in cov)+'</p></section>')
 block='<!-- RALLY_POINT_SERVER_WIRE_START --><div id="server-wire" aria-label="Current headlines">'+''.join(rows)+'</div><!-- RALLY_POINT_SERVER_WIRE_END -->'
 old=re.search(r'<!-- RALLY_POINT_SERVER_WIRE_START -->.*?<!-- RALLY_POINT_SERVER_WIRE_END -->',s,re.S)
 if old:
  if old.group()!=block:s=s[:old.start()]+block+s[old.end():];changed=True
 else:
  marker='<main id="main-content">'
  if marker in s:s=s.replace(marker,marker+'\n'+block,1);changed=True
except (OSError,json.JSONDecodeError):pass
if changed:p.write_text(s);print('Installed stripped Rally Point homepage with server-rendered headlines')
else:print('Rally Point composed homepage already installed')
