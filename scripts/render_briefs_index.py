#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
from html import escape
import json,re
ROOT=Path(__file__).resolve().parents[1];INDEX=ROOT/'briefs'/'index.html';DATA=ROOT/'data'/'briefs.json'
START='<!-- RALLY_BRIEFS_STATIC_START -->';END='<!-- RALLY_BRIEFS_STATIC_END -->'
def fmt_date(v):
 try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).strftime('%B %d, %Y').replace(' 0',' ')
 except:return ''
def image_for(b):
 # Image metadata is optional so publication never depends on artwork being available.
 for k in ('image','image_url','lead_image','hero_image'):
  if b.get(k):return str(b[k])
 return ''
def build_html(briefs):
 cards=[]
 for i,b in enumerate(briefs):
  title=escape(str(b.get('title') or 'Rally Brief'));url=escape(str(b.get('url') or '#'),quote=True);desc=escape(str(b.get('description') or ''));date=fmt_date(b.get('published_at'));sources=b.get('source_count');img=image_for(b)
  visual=(f'<a class="visual" href="{url}" aria-label="Read {title}"><img src="{escape(img,quote=True)}" alt="{escape(str(b.get("image_alt") or title),quote=True)}" width="1200" height="675" loading="{("eager" if i==0 else "lazy")}" decoding="async"></a>' if img else f'<a class="visual placeholder" href="{url}" aria-label="Read {title}"><span>RALLY POINT</span><b>{escape(str(b.get("image_label") or "AI NEWSROOM"))}</b></a>')
  meta=' · '.join(x for x in [date,(f'{int(sources)} sources' if sources else '')] if x)
  cards.append(f'<article class="brief{(" lead" if i==0 else "")}">{visual}<div class="copy"><div class="meta"><span>{("Lead Report" if i==0 else "Rally Point Report")}</span>{(" · "+escape(meta) if meta else "")}</div><h2><a href="{url}">{title}</a></h2>{f"<p>{desc}</p>" if desc else ""}<a class="read" href="{url}">Read full report →</a></div></article>')
 return ''.join(cards) if cards else '<p>No reports have been published yet.</p>'
def main():
 data=json.loads(DATA.read_text()) if DATA.exists() else {'briefs':[]};briefs=data.get('briefs',[]) if isinstance(data,dict) else []
 if not isinstance(briefs,list):briefs=[]
 rendered=f'{START}{build_html(briefs)}{END}'
 page=INDEX.read_text() if INDEX.exists() else ''
 # Preserve the existing document shell for compatibility, but replace its generated archive and add newsroom styling once.
 pattern=re.compile(re.escape(START)+r'.*?'+re.escape(END),re.S)
 if pattern.search(page):updated=pattern.sub(rendered,page,count=1)
 else:
  target='<section id="briefList" aria-live="polite"><p class="empty">Loading Rally Briefs…</p></section>'
  if target not in page:raise SystemExit('Could not locate briefList section')
  updated=page.replace(target,f'<section id="briefList" aria-live="polite">{rendered}</section>',1)
 css='''<style id="rp-ai-newsroom-cards">#briefList{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:20px!important}.brief{display:flex!important;flex-direction:column!important;background:#fff!important;border:1px solid #d8d3c7!important;padding:0!important;overflow:hidden!important}.brief.lead{grid-column:1/-1!important;display:grid!important;grid-template-columns:minmax(0,1.25fr) minmax(300px,.75fr)!important;border-top:4px solid #a51f24!important}.visual{display:block;aspect-ratio:16/9;overflow:hidden;background:#0d1b34;text-decoration:none!important}.visual img{width:100%;height:100%;object-fit:cover;display:block}.placeholder{color:#fff;display:flex;flex-direction:column;justify-content:flex-end;padding:24px;background:linear-gradient(145deg,#0d1b34,#1c3153)}.placeholder span{font:700 9px Arial,sans-serif;letter-spacing:.2em;color:#c89a3c}.placeholder b{font:900 clamp(22px,4vw,38px) Arial,sans-serif;letter-spacing:-.04em}.copy{padding:24px;display:flex;flex-direction:column;flex:1}.brief h2{font:900 clamp(22px,3vw,31px)/1.08 Arial,sans-serif!important;letter-spacing:-.025em;margin:9px 0 11px!important}.brief h2 a{text-decoration:none}.brief p{color:#68645b;margin:0 0 18px}.meta{font:800 9px Arial,sans-serif!important;letter-spacing:.09em;text-transform:uppercase;color:#68645b}.meta span{color:#a51f24}.read{margin-top:auto;padding-top:12px;border-top:1px solid #d8d3c7;font:800 10px Arial,sans-serif;text-transform:uppercase;letter-spacing:.1em;text-decoration:none;color:#0d1b34}@media(max-width:720px){#briefList{grid-template-columns:1fr!important}.brief.lead{grid-column:auto!important;display:flex!important}}</style>'''
 if 'id="rp-ai-newsroom-cards"' not in updated:updated=updated.replace('</head>',css+'</head>',1)
 if updated!=page:INDEX.write_text(updated);print(f'Rendered image-ready AI newsroom archive with {len(briefs)} reports')
 else:print('AI newsroom archive already current')
if __name__=='__main__':main()
