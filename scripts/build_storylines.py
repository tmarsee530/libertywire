#!/usr/bin/env python3
"""Build deterministic, persistent storyline intelligence without paid AI calls."""
from __future__ import annotations
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];NEWS=ROOT/'data'/'news.json';OUT=ROOT/'data'/'storylines.json';HISTORY=ROOT/'data'/'history.json';FAST=ROOT/'data'/'breaking_fast_path.json'
STOP={'this','that','with','from','have','will','into','after','over','about','says','said','amid','their','they','what','when','where','which','while','could','would','should','more','than','news','report','reports','live','update','updates','high','school','football','years','later','remember','watch','media','next','week','weeks','bill','bills','today','latest','breaking','exclusive','video','photos','photo','trump','president','senate','house','court','federal','government','election','elections','primary','judge','official','officials','american','america','state','states'}
SIGNALS={'supreme court':7,'congress':5,'senate':4,'house ':4,'white house':4,'president':4,'governor':3,'election':5,'war':7,'military':4,'attack':5,'ceasefire':5,'invasion':6,'nuclear':7,'emergency':5,'disaster':6,'hurricane':5,'earthquake':6,'wildfire':5,'evacuation':5,'crash':4,'killed':4,'death':3,'public safety':4,'economy':5,'inflation':4,'jobs':3,'unemployment':4,'federal reserve':5,'interest rate':4,'shutdown':5,'tariff':4,'oil':3,'market':3,'recession':6,'bank':3,'shipping':3,'supply chain':3,'federal court':4,'court':2,'judge':2,'law':2,'policy':2,'border':4,'immigration':3,'artificial intelligence':3,'cyber':4,'outage':4,'data breach':4,'technology':2}
BREAKING_SIGNALS={'attack':4,'nuclear':5,'emergency':4,'disaster':5,'earthquake':5,'wildfire':4,'evacuation':4,'crash':3,'killed':3,'shutdown':3,'outage':3,'data breach':3,'ceasefire':3,'invasion':5,'war':4,'interest rate':2,'federal reserve':2,'supreme court':3}
RISK=('accused','alleged','arrested','indicted','charged','dead','dies','killed','murder','rape','sexual assault','abuse','doxx','election called','projected winner','bankruptcy','insider trading','fraud','corruption','married her brother','married his sister','leaked','classified document')
SOURCE_FAMILIES={'Fox News':'fox','Fox News Politics':'fox','Fox News World':'fox','Fox Business':'fox','National Review':'national-review','National Review The Corner':'national-review','The Daily Signal':'daily-signal','Daily Signal':'daily-signal','The Daily Signal Politics':'daily-signal','Daily Signal Politics':'daily-signal','RealClearPolitics':'realclear','RealClearPolicy':'realclear','RealClearWorld':'realclear','RealClearDefense':'realclear','Associated Press':'ap','AP':'ap','NPR News':'npr','NPR':'npr'}
def family(source):return SOURCE_FAMILIES.get(str(source or '').strip(),str(source or '').strip().lower() or 'unknown')
def tokens(title):return {x for x in re.findall(r"[a-z0-9']{4,}",(title or '').lower()) if x not in STOP}
def anchors(title):
 """Conservative lexical proxy for named entities/proper nouns; used only to prevent false merges."""
 words=re.findall(r"\b[A-Z][A-Za-z0-9'’-]{2,}\b",str(title or ''))
 generic={'The','This','That','With','From','After','Over','About','News','Report','Reports','Live','Update','Updates','Latest','Breaking','Exclusive','Video','Photo','Photos','President','Senate','House','Court','Federal','Government','Election','Elections','State','States','American'}
 return {w.lower().replace('’',"'") for w in words if w not in generic and w.lower() not in STOP}
def pair_score(a,b):
 overlap=len(a&b)
 if overlap<2:return 0
 containment=overlap/max(1,min(len(a),len(b)));jaccard=overlap/max(1,len(a|b));return max(containment,jaccard*1.35)
def compatible(t,a,g):
 scores=sorted((pair_score(t,m) for m in g['member_tokens']),reverse=True)
 if not scores or scores[0]<.40:return 0
 shared=t & g['core_tokens']
 if len(g['member_tokens'])>=2 and len(shared)<2:return 0
 # When both sides expose proper-name anchors, require at least one shared anchor.
 # This blocks generic topical overlap from merging different people/teams/places/events.
 group_anchors=set().union(*g['member_anchors']) if g['member_anchors'] else set()
 if a and group_anchors and not (a&group_anchors):return 0
 return scores[0]
def cluster(stories):
 groups=[]
 for s in stories:
  t=tokens(s.get('title'));a=anchors(s.get('title'));best=None;best_score=0
  for g in groups:
   if s.get('source') in g['sources']:continue
   score=compatible(t,a,g)
   if score>best_score:best,best_score=g,score
  if best:best['stories'].append(s);best['sources'].add(s.get('source'));best['tokens']|=t;best['member_tokens'].append(t);best['member_anchors'].append(a);best['core_tokens']=set.intersection(*best['member_tokens']) if best['member_tokens'] else set()
  else:groups.append({'stories':[s],'sources':{s.get('source')},'tokens':set(t),'member_tokens':[t],'member_anchors':[a],'core_tokens':set(t)})
 return groups
def substantive(payload):return {k:v for k,v in payload.items() if k!='generated_at'}
def importance(all_titles,family_count,age_minutes):
 source_component=min(family_count,6)*3;impact_component=min(sum(weight for phrase,weight in SIGNALS.items() if phrase in all_titles),28);freshness=max(0,1-(max(0,age_minutes)/720))*4
 return round(source_component+impact_component+freshness,2)
def breaking_bonus(all_titles,family_count,age_minutes):
 if age_minutes>120:return 0
 signal=min(sum(weight for phrase,weight in BREAKING_SIGNALS.items() if phrase in all_titles),8);breadth=2 if family_count>=2 else 0;freshness=max(0,1-(max(0,age_minutes)/120))*6
 if not signal and family_count<2:return 0
 return round(min(12,signal+breadth+freshness),2)
def headline_quality(story,newest_epoch,core_tokens):
 title=(story.get('title') or '').strip();low=title.lower();words=re.findall(r"[A-Za-z0-9']+",title);age=max(0,newest_epoch-(story.get('published_epoch') or 0))/60
 freshness=max(0,5-min(age,180)/36);specificity=min(4,len(tokens(title)&core_tokens)*1.35);length_score=3 if 6<=len(words)<=18 else (1.5 if 4<=len(words)<=24 else 0);penalty=0
 for phrase in ('watch live','live updates','live update','video:','photos:','photo:','opinion:','exclusive:','weekly quiz','morning greatness'):
  if phrase in low:penalty+=1.25
 if any(x in low for x in ('humiliating','destroys','slams','meltdown','nightmare','bombshell','shocking')):penalty+=1.25
 if title.isupper():penalty+=1
 if len(title)>145:penalty+=1
 return round(freshness+specificity+length_score-penalty,3)
def choose_lead(stories,core_tokens):
 newest=max((s.get('published_epoch') or 0 for s in stories),default=0)
 return max(stories,key=lambda s:(headline_quality(s,newest,core_tokens),s.get('published_epoch') or 0,len(s.get('title') or '')))
def information_coverage(stories,lead,limit=8):
 """Lead first; then choose independent headlines that add the most unseen substantive information."""
 kept=[lead];seen=set(tokens(lead.get('title')));pool=[s for s in stories if s is not lead];newest=max((s.get('published_epoch') or 0 for s in stories),default=0);used_families={family(lead.get('source'))}
 while pool and len(kept)<limit:
  best=None;best_score=-1
  for s in pool:
   t=tokens(s.get('title'));novel=t-seen
   if not novel:continue
   overlap=len(t&seen)/max(1,len(t));independent=family(s.get('source')) not in used_families
   freshness=max(0,1-max(0,newest-(s.get('published_epoch') or 0))/(12*3600)) if newest else 0
   score=len(novel)*3+(1-overlap)*1.5+(1.25 if independent else 0)+freshness*.5
   if len(novel)<2 and overlap>=.65:continue
   if score>best_score:best,best_score=s,score
  if best is None:break
  kept.append(best);seen|=tokens(best.get('title'));used_families.add(family(best.get('source')));pool.remove(best)
 return kept
def prior_records():
 if not HISTORY.exists():return []
 try:return json.loads(HISTORY.read_text()).get('storylines',[])
 except (json.JSONDecodeError,OSError):return []
def history_match(toks,records,title=''):
 """Match durable stories conservatively: lexical similarity plus a shared named anchor when available."""
 best=None;score=0;a=anchors(title)
 for r in records:
  prior_titles=[r.get('current_title','')]+list(r.get('title_history',[]))[-4:]
  rt=tokens(' '.join(prior_titles));s=pair_score(toks,rt)
  ra=set().union(*(anchors(x) for x in prior_titles)) if prior_titles else set()
  if a and ra and not (a&ra):continue
  if s>score:best,score=r,s
 return best if score>=.48 else None
def fast_lookup():
 try:
  payload=json.loads(FAST.read_text());eligible=[x for x in payload.get('candidates',[]) if x.get('eligible')]
  generated=datetime.fromisoformat(str(payload.get('generated_at','')).replace('Z','+00:00'))
  if not generated.tzinfo:generated=generated.replace(tzinfo=timezone.utc)
  if (datetime.now(timezone.utc)-generated).total_seconds()>900:return {}
  return {link:item for item in eligible for link in item.get('corroborating_links',[]) if link}
 except (OSError,json.JSONDecodeError,TypeError,ValueError):return {}
def main():
 news=json.loads(NEWS.read_text());now=datetime.now(timezone.utc);out=[];history=prior_records();claimed_history_ids=set();fast=fast_lookup()
 for g in cluster(news.get('stories',[])):
  ss=sorted(g['stories'],key=lambda s:s.get('published_epoch') or 0,reverse=True);newest=max((s.get('published_epoch') or 0 for s in ss),default=0);fast_hits=[fast[s.get('link')] for s in ss if s.get('link') in fast];best_fast=max(fast_hits,key=lambda x:x.get('urgency_score',0),default=None);lead=choose_lead(ss,g['core_tokens']);lead=next((s for s in ss if best_fast and s.get('link')==best_fast.get('primary_source_link')),lead);title=lead.get('title','');sources=sorted(x for x in g['sources'] if x);families=sorted({family(x) for x in sources});family_count=len(families);age=(now.timestamp()-newest)/60 if newest else 10**9;all_titles=' '.join((s.get('title') or '').lower() for s in ss);risk=sorted({x for x in RISK if x in all_titles});base=importance(all_titles,family_count,age);identity=' '.join(sorted(g['tokens']))[:300] or title.lower();sid=hashlib.sha1(identity.encode()).hexdigest()[:12]
  prior=history_match(g['tokens'],history,title)
  # Keep a developing story at one durable URL even as its headline vocabulary changes.
  # The content-derived hash remains the fallback for genuinely new stories.
  if prior and prior.get('id') and prior['id'] not in claimed_history_ids:sid=prior['id'];claimed_history_ids.add(sid)
  prior_families=int((prior or {}).get('max_source_family_count',0) or 0);current_prior_families=int((prior or {}).get('current_source_family_count',0) or 0);growth=max(0,family_count-current_prior_families);persistent=bool(prior and (prior_families>=3 or int((prior or {}).get('max_source_count',0))>=3));hot_bonus=min(8,max(0,family_count-2)*1.5+min(growth,3)*1.5+(2 if persistent and age<=360 else 0));break_bonus=breaking_bonus(all_titles,family_count,age);fast_urgency=float((best_fast or {}).get('urgency_score',0) or 0);fast_bonus=round(min(12,max(0,fast_urgency-60)*.3),2);score=round(base+hot_bonus+break_bonus+fast_bonus,2)
  status='breaking' if (best_fast and fast_urgency>=60) or (break_bonus>=6 and age<=120) else ('hot' if family_count>=4 and age<=180 else ('developing' if family_count>=3 and age<=360 else 'active'));ordered=information_coverage(ss,lead,8)
  out.append({'id':sid,'title':title,'importance_score':score,'base_importance_score':base,'hot_bonus':round(hot_bonus,2),'breaking_bonus':break_bonus,'fast_path_bonus':fast_bonus,'fast_path':bool(best_fast),'urgency_score':fast_urgency if best_fast else None,'fast_path_reason':(best_fast or {}).get('reason'),'fast_path_detected_at':(best_fast or {}).get('detected_at'),'source_count':len(sources),'source_family_count':family_count,'source_families':families,'sources':sources,'newest_epoch':newest,'newest_date':next((s.get('date') for s in ss if (s.get('published_epoch') or 0)==newest),lead.get('date')),'risk_flags':risk,'status':status,'coverage':[{'source':s.get('source'),'source_family':family(s.get('source')),'title':s.get('title'),'link':s.get('link'),'date':s.get('date')} for s in ordered]})
 out.sort(key=lambda x:(x['importance_score'],x['newest_epoch'],x['source_family_count'],x['source_count']),reverse=True);payload={'generated_at':now.isoformat().replace('+00:00','Z'),'importance_method':'deterministic neutral news-value signals: consequence/institutional significance/safety/economic impact + independent publisher breadth + sustained cross-source development + short-lived breaking-news freshness boost for consequential new topics; novelty alone does not qualify','headline_method':'deterministic recency + cluster specificity + readable headline length; generic live/video/photo/opinion labels are mildly deprioritized; ideology and sentiment are not scored','fast_path_method':'fresh high-confidence developments from trusted primary sources or two independent trusted publishers are promoted ahead of the normal path; uncertain claims remain on the normal path','coverage_method':'primary headline establishes the topic; subsequent publisher headlines are selected by incremental substantive information, with a modest independent-publisher-family tie-break and freshness secondary; repetitive coverage is omitted','clustering_method':'distinctive-token overlap + cluster-core consistency + shared proper-name anchors when both headlines expose them; durable-history matching also requires stronger lexical similarity and shared named anchors when available; generic political/news terms excluded to reduce false merges','storyline_count':len(out),'multi_source_count':sum(1 for x in out if x['source_count']>=2),'multi_family_count':sum(1 for x in out if x['source_family_count']>=2),'breaking_count':sum(1 for x in out if x['status']=='breaking'),'fast_path_count':sum(1 for x in out if x.get('fast_path')),'developing_count':sum(1 for x in out if x['status'] in ('breaking','developing','hot')),'hot_count':sum(1 for x in out if x['status']=='hot'),'storylines':out[:500]}
 if OUT.exists():
  try:
   old=json.loads(OUT.read_text())
   if substantive(old)==substantive(payload):print(f"Storylines unchanged; {len(out)} storylines; {payload['multi_family_count']} multi-family; {payload['developing_count']} developing");return
  except (json.JSONDecodeError,OSError):pass
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n');print(f"Built {len(out)} storylines; {payload['multi_family_count']} multi-family; {payload['breaking_count']} breaking; {payload['developing_count']} developing; {payload['hot_count']} hot")
if __name__=='__main__':main()
