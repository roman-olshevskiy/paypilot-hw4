"""Offline analysis: actual traces, per-repeat verdicts and cost scope."""
import hashlib
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
KIT=ROOT.parent/"paypilot-l05-eval"
sys.path.insert(0,str(KIT))
import loader
import runner


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,indent=2,ensure_ascii=False)+chr(10)).encode())


def spans(tree):
    yield tree
    for child in tree.get("children",[]):
        yield from spans(child)


def amount_present(text):
    return bool(re.search(r"(?<![0-9])240(?:[.,]00)?(?![0-9])",text or ""))


def main():
    compiled={c["id"]:c for c in loader.load(ROOT/"l05_dialogs.jsonl")}
    runs=[]
    for folder in sorted((ROOT/"evidence/hw4-runs").glob("*")):
        if not (folder/"manifest.json").exists():continue
        manifest=read(folder/"manifest.json")
        rows=read(folder/"captures.json")
        if len(manifest["reports"])!=1:raise ValueError("Unexpected report count")
        raw_path=ROOT/"reports"/manifest["reports"][0]
        report=read(raw_path)
        assert hashlib.sha256(raw_path.read_bytes()).hexdigest()==manifest["report_sha256"][raw_path.name]
        calls=[s for row in rows for s in spans(row["trace"]) if s.get("name")=="llm.call"]
        summaries=[(row,s) for row in rows for s in spans(row["trace"])
                   if s.get("name")=="agent.summarize"]
        records=[]
        for cid,repeat in sorted({(row["case"],row["run"]) for row in rows}):
            part=[row for row in rows if (row["case"],row["run"])==(cid,repeat)]
            turns=[{"answer":row["response"]["answer"],"trace":row["trace"]} for row in part]
            v2_verdict=runner._dialog_run(compiled[cid],{"turns":turns})
            observed_summary=[]
            for row,s in summaries:
                if (row["case"],row["run"])!=(cid,repeat):continue
                text=s.get("attributes",{}).get("summary.text","")
                observed_summary.append({
                    "turn":row["turn"],"request_id":row["response"]["request_id"],
                    "text":text,"amount_240_present":amount_present(text),
                    "amount_180_present":bool(re.search(r"(?<![0-9])180(?:[.,]00)?(?![0-9])",text)),
                    "correct_reason_literal_present":bool(re.search(r"goods[_ -]+not[_ -]+received",text,re.I)),
                    "substituted_reason_literal_present":bool(re.search(r"service[_ -]+not[_ -]+rendered",text,re.I)),
                    "replaced_messages":s.get("attributes",{}).get("summary.replaced_messages")})
            memory_failed=[c for c in v2_verdict.checks
                           if not c["passed"] and not c["precondition"]
                           and not c["label"].startswith(("initial oracle","independent oracle"))]
            oracle_failed=[c for c in v2_verdict.checks
                           if not c["passed"] and not c["precondition"]
                           and c["label"].startswith(("initial oracle","independent oracle"))]
            failed_turns=[c["turn"] if isinstance(c["turn"],int) else min(c["turn"])
                          for c in memory_failed]
            evidence_loss=[s["turn"] for s in observed_summary if not s["amount_240_present"]]
            records.append({
                "case":cid,"repeat":repeat,"session_id":part[0]["response"]["session_id"],
                "v2_replay_passed":v2_verdict.passed,
                "checks":v2_verdict.checks,
                "first_memory_fail_turn":min(failed_turns) if failed_turns else None,
                "oracle_failures":oracle_failed,
                "first_summary_without_amount_turn":min(evidence_loss) if evidence_loss else None,
                "summary_evidence":observed_summary,
                "chat_requests":len(part),
                "request_ids":[row["response"]["request_id"] for row in part]})
        cost=sum(row["response"]["usage"].get("cost_usd") or 0 for row in rows)
        usage={key:sum(row["response"]["usage"].get(key,0) for row in rows)
               for key in ["input_tokens","output_tokens"]}
        before,after=read(folder/"before.json"),read(folder/"restored.json")
        restored=all(before[k]==after[k] for k in ["defects","clock","summarize","retrieval"])
        runs.append({
            "folder":str(folder.relative_to(ROOT)).replace(chr(92),"/"),
            "report":str(raw_path.relative_to(ROOT)).replace(chr(92),"/"),
            "ran_at":report["ran_at"],"set_hash":report["set_hash"],
            "profile":report["profile"],"passed_cases":report["passed"],"total_cases":report["total"],
            "chat_requests":len(rows),"agent_loop_calls":len(calls),"summarizer_calls":len(summaries),
            "provider_calls_including_summaries":len(calls)+len(summaries),
            "models":sorted({s.get("attributes",{}).get("gen_ai.request.model","") for s in calls}),
            "chat_root_usage":usage,"chat_root_cost_usd":round(cost,6),
            "summary_usage_reported":False,"settings_restored":restored,"repeats":records})
    full=[run for run in runs if run["chat_requests"]==195]
    if full:
        forecast=read(ROOT/"evidence/forecast-v2-commit.json")
        committed=datetime.fromisoformat(forecast["committed_at"])
        for run in full:
            assert committed < datetime.fromisoformat(run["ran_at"])
            assert run["set_hash"]==forecast["set_hash"]
            assert run["settings_restored"]
    total_requests=sum(run["chat_requests"] for run in runs)
    data={"analysis_date":"2026-10-18","runs":runs,
          "total_chat_requests":total_requests,
          "total_provider_calls_including_summaries":sum(run["provider_calls_including_summaries"] for run in runs),
          "chat_root_cost_usd":round(sum(run["chat_root_cost_usd"] for run in runs),6),
          "billing_verified":False,
          "cost_limitations":"Summarizer input/output and cache billing categories are absent from chat/root usage; cost is not a provider invoice.",
          "mechanism_limitations":"Summary text is authentic trace data. Full provider message bodies are not logged; claims about history rely on summary evidence plus matched runtime code and per-turn tool/retrieval spans."}
    save(ROOT/"evidence/run-analysis.json",data)
    print(json.dumps({k:v for k,v in data.items() if k!="runs"},indent=2))


if __name__=="__main__":main()
