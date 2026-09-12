#!/usr/bin/env python3
"""Generate a deterministic executive operations snapshot for Rally Point News."""
from __future__ import annotations
import json,re
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NEWS=ROOT/"data"/"news.json";OUT=ROOT/"data"/"operations.json"
HIGH_RISK=("accused","alleged","arrested","indicted","charged","dead","dies","killed","election called","projected winner","bankruptcy","insider trading","fraud")
IMPACT=("breaking","supreme court","congress","senate","house","president","governor","election","war","economy","inflation","jobs","federal reserve","market","shutdown","border")
def words(s):return set(re.findall(r"[a-z0-9']{4,}",(s or "").lower()))
def age_minutes(ts):
    if not ts:return 10**9
    d=datetime.fromisoformat(ts.replace("Z","+00:00"));return max(0,(datetime.now(timezone.utc)-d).total_seconds()/60)
def age_bucket(age):
    if age<=20:return "fresh"
    if age<=45:return "aging"
    if age<=120:return "stale"
    return "critical"
def cluster(stories):
    groups=[]
    for story in stories:
        w=words(story.get("title"));best=None;score=0
        for g in groups:
            overlap=len(w & g["words"])
            if overlap>score:best,score=g,overlap
        if best is not None and score>=2 and story.get("source") not in best["sources"]:
            best["stories"].append(story);best["sources"].add(story.get("source"));best["words"]|=w
        else:groups.append({"stories":[story],"sources":{story.get("source")},"words":set(w)})
    return groups
def substantive(payload):
    p=json.loads(json.dumps(payload));p.pop("generated_at",None);p.get("newsroom",{}).pop("dataset_age_minutes",None);return p
def main():
    news=json.loads(NEWS.read_text())
    stories=news.get("stories",[]);groups=cluster(stories);risk=[];ranked=[]
    for g in groups:
        lead=g["stories"][0];title=lead.get("title","");lower=title.lower();fresh=max(0,180-age_minutes(lead.get("date")))/180
        impact=sum(1 for x in IMPACT if x in lower);score=round(len(g["sources"])*3+impact*1.5+fresh,2)
        ranked.append({"title":title,"source_count":len(g["sources"]),"importance_score":score,"sources":sorted(g["sources"])})
        flags=[x for x in HIGH_RISK if x in lower]
        if flags:risk.append({"title":title,"flags":flags,"sources":sorted(g["sources"]),"action":"hold for extra scrutiny" if len(g["sources"])<2 else "publish attributed coverage only"})
    ranked.sort(key=lambda x:x["importance_score"],reverse=True)
    healthy=news.get("healthy_source_count",0);total=news.get("source_count",0);fresh_age=round(age_minutes(news.get("generated_at")),1);freshness=age_bucket(fresh_age)
    status="healthy" if healthy>=max(1,int(total*.75)) and fresh_age<=45 else "degraded"
    payload={"generated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"business_status":status,"newsroom":{"dataset_age_minutes":fresh_age,"dataset_freshness":freshness,"stories":len(stories),"healthy_sources":healthy,"configured_sources":total,"source_health_pct":round(healthy/total*100,1) if total else 0,"failed_sources":news.get("failed_sources",[])},"editorial":{"storylines":len(groups),"risk_queue_count":len(risk),"risk_queue":risk[:20],"top_storylines":ranked[:20]},"audience":{"analytics_connected_to_manager":False,"status":"awaiting analytics tool access"},"revenue":{"revenue_data_connected_to_manager":False,"status":"awaiting revenue/analytics data"},"supervisor":{"owner_action_required":False,"notes":["Routine newsroom operations continue automatically.","High-risk items are flagged for extra scrutiny rather than converted into unsupported original reporting.","No separately billed OpenAI API is required by this workflow."]}}
    if OUT.exists():
        try:
            old=json.loads(OUT.read_text())
            if substantive(old)==substantive(payload):
                print(f"Business snapshot unchanged: {status}; {len(groups)} storylines; {len(risk)} risk flags")
                return
        except (json.JSONDecodeError,OSError):pass
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2)+"\n");print(f"Business status: {status}; {len(groups)} storylines; {len(risk)} risk flags")
if __name__=="__main__":main()
