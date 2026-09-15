#!/usr/bin/env python3
"""Build deterministic, persistent storyline intelligence without paid AI calls."""
from __future__ import annotations
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];NEWS=ROOT/'data'/'news.json';OUT=ROOT/'data'/'storylines.json'
STOP={'this','that','with','from','have','will','into','after','over','about','says','said','amid','their','they','what','when','where','which','while','could','would','should','more','than','news','report','reports','live','update','updates','high','school','football','years','later','remember','watch','media','next','week','weeks','bill','bills','today','latest','breaking','exclusive','video','photos','photo'}
# Importance uses topic-neutral news-value signals. These weights affect prominence,
# not factual truth or political desirability.
SIGNALS={
 'supreme court':7,'congress':5,'senate':4,'house ':4,'white house':4,'president':4,'governor':3,'election':5,
 'war':7,'military':4,'attack':5,'ceasefire':5,'invasion':6,'nuclear':7,'emergency':5,'disaster':6,'hurricane':5,
 'earthquake':6,'wildfire':5,'evacuation':5,'crash':4,'killed':4,'death':3,'public safety':4,
 'economy':5,'inflation':4,'jobs':3,'unemployment':4,'federal reserve':5,'interest rate':4,'shutdown':5,'tariff':4,
 'oil':3,'market':3,'recession':6,'bank':3,'shipping':3,'supply chain':3,
 'federal court':4,'court':2,'judge':2,'law':2,'policy':2,'border':4,'immigration':3,
 'artificial intelligence':3,'cyber':4,'outage':4,'data breach':4,'technology':2,
}
RISK=('accused','alleged','arrested','indicted','charged','dead','dies','killed','murder','rape','sexual assault','abuse','doxx','election called','projected winner','bankruptcy','insider trading','fraud','corruption','married her brother','married his sister','leaked','classified document')
def tokens(title):return {x for x in re.findall(r"[a-z0-9']{4,}",(title or '').lower()) if x not in STOP}
def pair_score(a,b):
 overlap=len(a&b)
 if overlap<2:return 0
 containment=overlap/max(1,min(len(a),len(b)));jaccard=overlap/max(1,len(a|b));return max(containment,jaccard*1.35)
def cluster(stories):
 groups=[]
 for s in stories:
  t=tokens(s.get('title'));best=None;best_score=0
  for g in groups:
   if s.get('source') in g['sources']:continue
   score=max((pair_score(t,m) for m in g['member_tokens']),default=0)
   if score>best_score:best,best_score=g,score
  if best and best_score>=.34:best['stories'].append(s);best['sources'].add(s.get('source'));best['tokens']|=t;best['member_tokens'].append(t)
  else:groups.append({'stories':[s],'sources':{s.get('source')},'tokens':set(t),'member_tokens':[t]})
 return groups
def substantive(payload):return {k:v for k,v in payload.items() if k!='generated_at'}
def importance(all_titles,source_count,age_minutes):
 # Start with corroboration breadth. Cap it so outlet volume cannot overwhelm impact.
 source_component=min(source_count,6)*3
 impact_component=sum(weight for phrase,weight in SIGNALS.items() if phrase in all_titles)
 impact_component=min(impact_component,28)
 # Freshness matters, but only enough to distinguish similarly consequential stories.
 freshness=max(0,1-(max(0,age_minutes)/720))*4
 return round(source_component+impact_component+freshness,2)
def main():
 news=json.loads(NEWS.read_text());now=datetime.now(timezone.utc);out=[]
 for g in cluster(news.get('stories',[])):
  ss=sorted(g['stories'],key=lambda s:s.get('published_epoch') or 0,reverse=True);lead=ss[0];title=lead.get('title','');sources=sorted(x for x in g['sources'] if x)
  newest=max((s.get('published_epoch') or 0 for s in ss),default=0);age=(now.timestamp()-newest)/60 if newest else 10**9;all_titles=' '.join((s.get('title') or '').lower() for s in ss);risk=sorted({x for x in RISK if x in all_titles});score=importance(all_titles,len(sources),age)
  identity=' '.join(sorted(g['tokens']))[:300] or title.lower();sid=hashlib.sha1(identity.encode()).hexdigest()[:12]
  out.append({'id':sid,'title':title,'importance_score':score,'source_count':len(sources),'sources':sources,'newest_epoch':newest,'newest_date':lead.get('date'),'risk_flags':risk,'status':'developing' if len(sources)>=3 and age<=90 else 'active','coverage':[{'source':s.get('source'),'title':s.get('title'),'link':s.get('link'),'date':s.get('date')} for s in ss[:8]]})
 out.sort(key=lambda x:(x['importance_score'],x['source_count'],x['newest_epoch']),reverse=True)
 payload={'generated_at':now.isoformat().replace('+00:00','Z'),'importance_method':'deterministic neutral news-value signals: consequence/institutional significance/safety/economic impact + source breadth; freshness secondary','storyline_count':len(out),'multi_source_count':sum(1 for x in out if x['source_count']>=2),'developing_count':sum(1 for x in out if x['status']=='developing'),'storylines':out[:500]}
 if OUT.exists():
  try:
   old=json.loads(OUT.read_text())
   if substantive(old)==substantive(payload):print(f"Storylines unchanged; {len(out)} storylines; {payload['multi_source_count']} multi-source; {payload['developing_count']} developing");return
  except (json.JSONDecodeError,OSError):pass
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n');print(f"Built {len(out)} storylines; {payload['multi_source_count']} multi-source; {payload['developing_count']} developing")
if __name__=='__main__':main()
