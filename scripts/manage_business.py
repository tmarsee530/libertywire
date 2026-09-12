#!/usr/bin/env python3
"""Generate a deterministic executive operations snapshot for Rally Point News."""
from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
NEWS=ROOT/"data"/"news.json";STORYLINES=ROOT/"data"/"storylines.json";OUT=ROOT/"data"/"operations.json"
def age_minutes(ts):
    if not ts:return 10**9
    d=datetime.fromisoformat(ts.replace("Z","+00:00"));return max(0,(datetime.now(timezone.utc)-d).total_seconds()/60)
def age_bucket(age):
    if age<=20:return "fresh"
    if age<=45:return "aging"
    if age<=120:return "stale"
    return "critical"
def substantive(payload):
    p=json.loads(json.dumps(payload));p.pop("generated_at",None);p.get("newsroom",{}).pop("dataset_age_minutes",None);return p
def main():
    news=json.loads(NEWS.read_text());sl=json.loads(STORYLINES.read_text()) if STORYLINES.exists() else {"storylines":[]}
    stories=news.get("stories",[]);storylines=sl.get("storylines",[]);risk=[]
    for item in storylines:
        flags=item.get("risk_flags") or []
        if flags:
            risk.append({"id":item.get("id"),"title":item.get("title"),"flags":flags,"sources":item.get("sources",[]),"source_count":item.get("source_count",0),"action":"hold for extra scrutiny" if item.get("source_count",0)<2 else "publish attributed coverage only"})
    healthy=news.get("healthy_source_count",0);total=news.get("source_count",0);fresh_age=round(age_minutes(news.get("generated_at")),1);freshness=age_bucket(fresh_age)
    status="healthy" if healthy>=max(1,int(total*.75)) and fresh_age<=45 else "degraded"
    top=[{"id":x.get("id"),"title":x.get("title"),"source_count":x.get("source_count",0),"importance_score":x.get("importance_score",0),"sources":x.get("sources",[]),"status":x.get("status","active")} for x in storylines[:20]]
    payload={"generated_at":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"business_status":status,"newsroom":{"dataset_age_minutes":fresh_age,"dataset_freshness":freshness,"stories":len(stories),"healthy_sources":healthy,"configured_sources":total,"source_health_pct":round(healthy/total*100,1) if total else 0,"failed_sources":news.get("failed_sources",[])},"editorial":{"storylines":sl.get("storyline_count",len(storylines)),"multi_source_storylines":sl.get("multi_source_count",sum(1 for x in storylines if x.get("source_count",0)>=2)),"developing_storylines":sl.get("developing_count",sum(1 for x in storylines if x.get("status")=="developing")),"risk_queue_count":len(risk),"risk_queue":risk[:20],"top_storylines":top},"audience":{"analytics_connected_to_manager":False,"status":"awaiting analytics tool access"},"revenue":{"revenue_data_connected_to_manager":False,"status":"awaiting revenue/analytics data"},"supervisor":{"owner_action_required":False,"notes":["Routine newsroom operations continue automatically.","Executive ranking now uses the shared storyline engine as the single source of editorial clustering truth.","High-risk items are flagged for extra scrutiny rather than converted into unsupported original reporting.","No separately billed OpenAI API is required by this workflow."]}}
    if OUT.exists():
        try:
            old=json.loads(OUT.read_text())
            if substantive(old)==substantive(payload):
                print(f"Business snapshot unchanged: {status}; {len(storylines)} storylines; {len(risk)} risk flags")
                return
        except (json.JSONDecodeError,OSError):pass
    OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2)+"\n");print(f"Business status: {status}; {len(storylines)} storylines; {len(risk)} risk flags")
if __name__=="__main__":main()
