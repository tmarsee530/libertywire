#!/usr/bin/env python3
"""Build a deterministic research queue for Rally Point's timeline newsroom.

This queue is a research/verification aid, never publication approval. It prefers
important independently corroborated current events. If that set is empty, it
still emits high-value single-family research leads so an AI/editor can pursue
independent verification rather than sitting idle or reviving retired Briefs.
"""
from __future__ import annotations
import json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STORYLINES=ROOT/'data'/'storylines.json';HISTORY=ROOT/'data'/'history.json';OUT=ROOT/'data'/'writer_queue.json'
MAX_CANDIDATES=8;MIN_SOURCES=2;MIN_SOURCE_FAMILIES=2;MAX_RESEARCH_LEADS=4
STOP={'a','an','and','are','as','at','be','been','but','by','for','from','has','have','he','her','his','in','into','is','it','its','new','of','on','or','says','she','that','the','their','this','to','us','u','s','was','were','will','with'}
SOURCE_FAMILIES={
 'Fox News':'fox','Fox News Politics':'fox','Fox News World':'fox','Fox Business':'fox',
 'National Review':'national-review','National Review The Corner':'national-review',
 'The Daily Signal':'daily-signal','Daily Signal':'daily-signal','The Daily Signal Politics':'daily-signal','Daily Signal Politics':'daily-signal',
 'RealClearPolitics':'realclear','RealClearPolicy':'realclear','RealClearWorld':'realclear','RealClearDefense':'realclear',
 'Associated Press':'ap','AP':'ap','Reuters':'reuters','NPR News':'npr','NPR Culture':'npr','NPR':'npr',
 'CBS News':'cbs','CBS Sports':'cbs','ABC News':'abc','NBC News':'nbc','CNN':'cnn',
 'BBC News':'bbc','BBC Sport':'bbc','BBC Sports':'bbc','BBC Entertainment':'bbc','BBC Science':'bbc',
 'New York Post':'new-york-post','Page Six':'new-york-post','New York Times':'new-york-times','Washington Post':'washington-post',
 'Stars and Stripes':'stars-and-stripes','Stars and Stripes Storm Tracker':'stars-and-stripes',
 'Axios':'axios','Politico':'politico','Breitbart':'breitbart','Daily Caller':'daily-caller','Daily Wire':'daily-wire','Hot Air':'hot-air','National Pulse':'national-pulse','RedState':'redstate','WND':'wnd',
 'Washington Times':'washington-times','Washington Examiner':'washington-examiner','Newsmax':'newsmax','The Blaze':'blaze','Washington Free Beacon':'free-beacon','The Federalist':'federalist','Townhall':'townhall','PJ Media':'pj-media','American Thinker':'american-thinker','Commentary Magazine':'commentary','American Spectator':'american-spectator','Twitchy':'twitchy','LifeSiteNews':'lifesitenews','The Epoch Times':'epoch-times','Human Events':'human-events','The College Fix':'college-fix','Legal Insurrection':'legal-insurrection','Just the News':'just-the-news',
 'Reason':'reason','The American Conservative':'american-conservative','City Journal':'city-journal','American Greatness':'american-greatness','The Post Millennial':'post-millennial','Western Journal':'western-journal','Power Line':'power-line','The Spectator World':'spectator-world','The Dispatch':'dispatch','The Daily Economy':'daily-economy','Foundation for Economic Education':'fee','Cato Institute':'cato','Heritage Foundation':'heritage','Judicial Watch':'judicial-watch',
 'The Hill':'the-hill','SCOTUSblog':'scotusblog','Defense News':'defense-news','SpaceNews':'spacenews','Ars Technica':'ars-technica'
}
def substantive(payload):return {k:v for k,v in payload.items() if k!='generated_at'}
def tokens(text):return {w for w in re.findall(r"[a-z0-9]+",str(text or '').lower()) if len(w)>2 and w not in STOP}
def family(source):return SOURCE_FAMILIES.get(str(source or '').strip(),str(source or '').strip().lower() or 'unknown')
def source_families(storyline):return sorted({family(x) for x in storyline.get('sources',[]) if x})
def requirements():return {'fresh_verification':True,'prefer_primary_sources':True,'independent_corroboration_required_for_disputed_or_high_risk_claims':True,'attribute_disputed_claims':True,'distinguish_allegations_from_established_facts':True,'preserve_source_links':True,'state_material_uncertainty':True,'automatic_publication_allowed':False}
def main():
 data=json.loads(STORYLINES.read_text());history={}
 if HISTORY.exists():
  try:history={x.get('id'):x for x in json.loads(HISTORY.read_text()).get('storylines',[]) if x.get('id')}
  except (json.JSONDecodeError,OSError):history={}
 verified=[];research=[]
 for s in data.get('storylines',[]):
  source_count=int(s.get('source_count') or 0);flags=set(s.get('risk_flags') or []);score=float(s.get('importance_score') or 0);families=source_families(s);h=history.get(s.get('id'),{})
  if flags:continue
  growth=max(0,source_count-int(h.get('initial_source_count') or source_count));priority=round(score+min(source_count,5)*1.25+min(growth,3)*1.25+min(len(families),4)*1.5,2)
  base={'storyline_id':s.get('id'),'title':s.get('title'),'priority_score':priority,'importance_score':score,'source_count':source_count,'source_family_count':len(families),'source_families':families,'sources':s.get('sources',[]),'status':s.get('status'),'risk_flags':[],'coverage':s.get('coverage',[])[:8],'history':{'first_seen':h.get('first_seen'),'last_seen':h.get('last_seen'),'max_source_count':h.get('max_source_count'),'source_growth':growth},'publication_requirements':requirements()}
  if source_count>=MIN_SOURCES and len(families)>=MIN_SOURCE_FAMILIES:
   base.update({'candidate_type':'verified_current_event','reason':'multi-family current event suitable for deeper timeline research; fresh verification still required'})
   verified.append(base)
  elif score>=12 and source_count>=1:
   base.update({'candidate_type':'independent_research_lead','research_query':s.get('title'),'reason':'important under-corroborated event; independently research primary and unrelated publisher sources before any publication'})
   research.append(base)
 verified.sort(key=lambda x:(x['priority_score'],x['source_family_count'],x['source_count']),reverse=True)
 research.sort(key=lambda x:(x['importance_score'],x['priority_score']),reverse=True)
 selected=verified[:MAX_CANDIDATES]
 fallback_used=False
 if not selected:
  selected=research[:MAX_RESEARCH_LEADS];fallback_used=True
 payload={'generated_at':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'product':'canonical_timeline_research','policy':{'minimum_sources_for_verified_candidate':MIN_SOURCES,'minimum_source_families_for_verified_candidate':MIN_SOURCE_FAMILIES,'risk_flagged_storylines_allowed':False,'fresh_verification_required':True,'prefer_primary_sources':True,'queue_is_research_gate_not_publication_approval':True,'retired_briefs_used':False,'fallback_independent_research_enabled':True},'fallback_used':fallback_used,'verified_candidate_count':len(verified),'research_lead_count':len(research),'candidate_count':len(selected),'candidates':selected}
 if OUT.exists():
  try:
   old=json.loads(OUT.read_text())
   if substantive(old)==substantive(payload):print(f"Timeline research queue unchanged; {payload['candidate_count']} candidates");return
  except (json.JSONDecodeError,OSError):pass
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n');print(f"Built timeline research queue with {payload['candidate_count']} candidates; fallback={fallback_used}")
if __name__=='__main__':main()
