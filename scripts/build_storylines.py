#!/usr/bin/env python3
"""Build deterministic, persistent storyline intelligence without paid AI calls."""
from __future__ import annotations
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];NEWS=ROOT/'data'/'news.json';OUT=ROOT/'data'/'storylines.json';HISTORY=ROOT/'data'/'history.json'
STOP={'this','that','with','from','have','will','into','after','over','about','says','said','amid','their','they','what','when','where','which','while','could','would','should','more','than','news','report','reports','live','update','updates','high','school','football','years','later','remember','watch','media','next','week','weeks','bill','bills','today','latest','breaking','exclusive','video','photos','photo','trump','president','senate','house','court','federal','government','election','elections','primary','judge','official','officials','american','america','state','states'}
SIGNALS={'supreme court':7,'congress':5,'senate':4,'house ':4,'white house':4,'president':4,'governor':3,'election':5,'war':7,'military':4,'attack':5,'ceasefire':5,'invasion':6,'nuclear':7,'emergency':5,'disaster':6,'hurricane':5,'earthquake':6,'wildfire':5,'evacuation':5,'crash':4,'killed':4,'death':3,'public safety':4,'economy':5,'inflation':4,'jobs':3,'unemployment':4,'federal reserve':5,'interest rate':4,'shutdown':5,'tariff':4,'oil':3,'market':3,'recession':6,'bank':3,'shipping':3,'supply chain':3,'federal court':4,'court':2,'judge':2,'law':2,'policy':2,'border':4,'immigration':3,'artificial intelligence':3,'cyber':4,'outage':4,'data breach':4,'technology':2}
RISK=('accused','alleged','arrested','indicted','charged','dead','dies','killed','murder','rape','sexual assault','abuse','doxx','election called','projected winner','bankruptcy','insider trading','fraud','corruption','married her brother','married his sister','leaked','classified document')
# Publisher families are used for homepage importance as well as publication gates.
# Multiple section feeds from one publisher can add useful headlines, but must not
# make a story appear independently hotter than it is.
SOURCE_FAMILIES={
 'Fox News':'fox','Fox News Politics':'fox','Fox News World':'fox','Fox Business':'fox',
 'National Review':'national-review','National Review The Corner':'national-review',
 'The Daily Signal':'daily-signal','Daily Signal':'daily-signal','The Daily Signal Politics':'daily-signal','Daily Signal Politics':'daily-signal',
 'RealClearPolitics':'realclear','RealClearPolicy':'realclear','RealClearWorld':'realclear','RealClearDefense':'realclear',
 'Associated Press':'ap','AP':'ap','NPR News':'npr','NPR':'npr'
}
def family(source):return SOURCE_FAMILIES.get(str(source or '').strip(),str(source or '').strip().lower() or 'unknown')
def tokens(title):return {x for x in re.findall(r"[a-z0-9']{4,}",(title or '').lower()) if x not in STOP}
def pair_score(a,b):
 overlap=len(a&b)
 if overlap<2:return 0
 containment=overlap/max(1,min(len(a),len(b)));jaccard=overlap/max(1,len(a|b));return max(containment,jaccard*1.35)
def compatible(t,g):
 scores=sorted((pair_score(t,m) for m in g['member_tokens']),reverse=True)
 if not scores or scores[0]<.40:return 0
 shared=t & g['core_tokens']
 if len(g['member_tokens'])>=2 and len(shared)<2:return 0
 return scores[0]
def cluster(stories):
 groups=[]
 for s in stories:
  t=tokens(s.get('title'));best=None;best_score=0
  for g in groups:
   # Permit multiple sections of a publisher in the same topic for headline depth;
   # independent-family counting happens later.
   if s.get('source') in g['sources']:continue
   score=compatible(t,g)
   if score>best_score:best,best_score=g,score
  if best:
   best['stories'].append(s);best['sources'].add(s.get('source'));best['tokens']|=t;best['member_tokens'].append(t);best['core_tokens']=set.intersection(*best['member_tokens']) if best['member_tokens'] else set()
  else:groups.append({'stories':[s],'sources':{s.get('source')},'tokens':set(t),'member_tokens':[t],'core_tokens':set(t)})
 return groups
def substantive(payload):return {k:v for k,v in payload.items() if k!='generated_at'}
def importance(all_titles,family_count,age_minutes):
 source_component=min(family_count,6)*3;impact_component=min(sum(weight for phrase,weight in SIGNALS.items() if phrase in all_titles),28);freshness=max(0,1-(max(0,age_minutes)/720))*4
 return round(source_component+impact_component+freshness,2)
def prior_records():
 if not HISTORY.exists():return []
 try:return json.loads(HISTORY.read_text()).get('storylines',[])
 except (json.JSONDecodeError,OSError):return []
def history_match(toks,records):
 best=None;score=0
 for r in records:
  rt=tokens(' '.join([r.get('current_title','')]+list(r.get('title_history',[]))[-4:]));s=pair_score(toks,rt)
  if s>score:best,score=r,s
 return best if score>=.42 else None
def main():
 news=json.loads(NEWS.read_text());now=datetime.now(timezone.utc);out=[];history=prior_records()
 for g in cluster(news.get('stories',[])):
  ss=sorted(g['stories'],key=lambda s:s.get('published_epoch') or 0,reverse=True);lead=ss[0];title=lead.get('title','');sources=sorted(x for x in g['sources'] if x);families=sorted({family(x) for x in sources});family_count=len(families);newest=max((s.get('published_epoch') or 0 for s in ss),default=0);age=(now.timestamp()-newest)/60 if newest else 10**9;all_titles=' '.join((s.get('title') or '').lower() for s in ss);risk=sorted({x for x in RISK if x in all_titles});base=importance(all_titles,family_count,age);identity=' '.join(sorted(g['tokens']))[:300] or title.lower();sid=hashlib.sha1(identity.encode()).hexdigest()[:12]
  prior=history_match(g['tokens'],history);prior_families=int((prior or {}).get('max_source_family_count',0) or 0);current_prior_families=int((prior or {}).get('current_source_family_count',0) or 0);growth=max(0,family_count-current_prior_families);persistent=bool(prior and (prior_families>=3 or int((prior or {}).get('max_source_count',0))>=3));hot_bonus=min(8,max(0,family_count-2)*1.5+min(growth,3)*1.5+(2 if persistent and age<=360 else 0));score=round(base+hot_bonus,2)
  status='hot' if family_count>=4 and age<=180 else ('developing' if family_count>=3 and age<=360 else 'active')
  out.append({'id':sid,'title':title,'importance_score':score,'base_importance_score':base,'hot_bonus':round(hot_bonus,2),'source_count':len(sources),'source_family_count':family_count,'source_families':families,'sources':sources,'newest_epoch':newest,'newest_date':lead.get('date'),'risk_flags':risk,'status':status,'coverage':[{'source':s.get('source'),'title':s.get('title'),'link':s.get('link'),'date':s.get('date')} for s in ss[:8]]})
 out.sort(key=lambda x:(x['importance_score'],x['source_family_count'],x['source_count'],x['newest_epoch']),reverse=True);payload={'generated_at':now.isoformat().replace('+00:00','Z'),'importance_method':'deterministic neutral news-value signals: consequence/institutional significance/safety/economic impact + independent publisher breadth + sustained cross-source development; freshness secondary','clustering_method':'distinctive-token overlap plus cluster-core consistency; generic political/news terms excluded to reduce false merges','storyline_count':len(out),'multi_source_count':sum(1 for x in out if x['source_count']>=2),'multi_family_count':sum(1 for x in out if x['source_family_count']>=2),'developing_count':sum(1 for x in out if x['status'] in ('developing','hot')),'hot_count':sum(1 for x in out if x['status']=='hot'),'storylines':out[:500]}
 if OUT.exists():
  try:
   old=json.loads(OUT.read_text())
   if substantive(old)==substantive(payload):print(f"Storylines unchanged; {len(out)} storylines; {payload['multi_family_count']} multi-family; {payload['developing_count']} developing");return
  except (json.JSONDecodeError,OSError):pass
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n');print(f"Built {len(out)} storylines; {payload['multi_family_count']} multi-family; {payload['developing_count']} developing; {payload['hot_count']} hot")
if __name__=='__main__':main()
