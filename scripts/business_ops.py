#!/usr/bin/env python3
"""Generate Rally Point's deterministic business/editorial operating snapshot.

This intentionally uses no LLM/API. It turns the shared news dataset into
operational signals that an editor/manager can inspect or automate against.
"""
from __future__ import annotations
import json, re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NEWS=ROOT/"data"/"news.json"
OUT=ROOT/"data"/"operations.json"

TOPICS={
 "politics":["congress","senate","house","election","governor","president","white house","campaign","democrat","republican"],
 "economy":["economy","inflation","jobs","market","stocks","fed","rates","trade","tariff","debt","budget"],
 "world":["war","ukraine","russia","china","israel","gaza","iran","nato","europe","foreign"],
 "crime":["crime","murder","killed","arrest","police","shooting","suspect","charged","court"],
 "culture":["school","college","media","hollywood","gender","church","religion","sports","entertainment"],
 "technology":["ai","artificial intelligence","tech","google","apple","microsoft","cyber","internet"],
}
HIGH_IMPACT=["breaking","war","attack","killed","dead","election","supreme court","congress","senate","president","economy","inflation","fed","market","shutdown","emergency"]
RISK_TERMS=["alleged","allegedly","accused","suspect","charged","indicted","leak","leaked","unconfirmed","rumor","claims","claim"]
PRIVATE_PERSON_PATTERNS=[r"\bteen\b",r"\bteacher\b",r"\bstudent\b",r"\bmother\b",r"\bfather\b",r"\bneighbor\b"]

def minutes_old(iso):
    if not iso:return 10**9
    try:return max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(iso.replace("Z","+00:00"))).total_seconds()/60)
    except Exception:return 10**9

def classify(text):
    t=text.lower();scores={k:sum(1 for w in words if w in t) for k,words in TOPICS.items()}
    winner=max(scores,key=scores.get)
    return winner if scores[winner] else "general"

def risk_flags(story):
    t=(story.get("title","")+" "+story.get("summary","")).lower();flags=[]
    if any(w in t for w in RISK_TERMS):flags.append("allegation_or_unconfirmed")
    if any(re.search(p,t) for p in PRIVATE_PERSON_PATTERNS) and any(w in t for w in ["arrest","charged","accused","murder","shooting"]):flags.append("private_person_sensitive")
    if any(w in t for w in ["election result","winner","projected winner","calls race"]):flags.append("election_call")
    if any(w in t for w in ["stock plunges","market crash","bank run","bank collapse"]):flags.append("market_moving")
    if any(w in t for w in ["dead","death","dies","killed"]) and any(w in t for w in ["reportedly","unconfirmed","rumor"]):flags.append("unconfirmed_death")
    return flags

def importance(story):
    t=(story.get("title","")+" "+story.get("summary","")).lower();score=0
    score+=sum(2 for w in HIGH_IMPACT if w in t)
    age=minutes_old(story.get("date"));score+=4 if age<30 else 3 if age<90 else 2 if age<240 else 0
    if story.get("image"):score+=1
    return score

def main():
    data=json.loads(NEWS.read_text(encoding="utf-8"));stories=data.get("stories",[])
    topic_counts=Counter();source_counts=Counter();risk_queue=[];ranked=[]
    for s in stories:
        topic=classify(s.get("title","")+" "+s.get("summary",""));topic_counts[topic]+=1;source_counts[s.get("source","Unknown")]+=1
        flags=risk_flags(s);score=importance(s)
        ranked.append({"title":s.get("title"),"source":s.get("source"),"link":s.get("link"),"topic":topic,"importance_score":score,"age_minutes":round(minutes_old(s.get("date")),1)})
        if flags:risk_queue.append({"title":s.get("title"),"source":s.get("source"),"link":s.get("link"),"flags":flags})
    ranked.sort(key=lambda x:(x["importance_score"],-x["age_minutes"]),reverse=True)
    failed=data.get("failed_sources",[]);healthy=data.get("healthy_source_count",0);total=data.get("source_count",0)
    freshness=sum(1 for s in stories if minutes_old(s.get("date"))<=180)
    payload={
      "generated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
      "executive_status":{
        "newsroom_health_pct":round((healthy/total)*100,1) if total else 0,
        "healthy_sources":healthy,"configured_sources":total,"failed_sources":failed,
        "stories_available":len(stories),"stories_last_3h":freshness,
        "risk_queue_count":len(risk_queue),
        "operating_mode":"automatic",
        "paid_openai_api_required":False
      },
      "editorial":{
        "topic_mix":dict(topic_counts.most_common()),
        "top_candidates":ranked[:20],
        "risk_queue":risk_queue[:50],
        "source_volume":dict(source_counts.most_common())
      },
      "business":{
        "analytics_status":"awaiting_connected_analytics_data",
        "revenue_status":"awaiting_connected_revenue_data",
        "newsletter_status":"embedded_substack_signup_present",
        "monetization_guardrails":["never manufacture pageviews","never click or encourage clicks on ads","never disguise sponsorship","do not create paid API usage without owner approval"],
        "next_free_actions":["maintain source health","improve clustering","build persistent storyline history","generate SEO-safe metadata","monitor site reliability"]
      }
    }
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Operations snapshot: {healthy}/{total} sources; {len(stories)} stories; {len(risk_queue)} risk flags.")
if __name__=="__main__":main()
