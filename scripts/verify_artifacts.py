"""Validate immutable evidence and completeness offline, without stand calls."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(p):return json.loads(p.read_text(encoding="utf-8"))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    data=read(ROOT/"evidence/run-analysis.json")
    full=[x for x in data["runs"] if x["chat_requests"]==195]
    assert {x["profile"] for x in full}=={"clean","lesson-05"}
    assert len(full)==2 and data["total_chat_requests"]==404
    assert {x["set_hash"] for x in full}=={sha(ROOT/"l05_dialogs.jsonl")[:12]}
    ids=[];sessions=[]
    for run in data["runs"]:
        folder=ROOT/run["folder"]
        manifest=read(folder/"manifest.json")
        for name,expected in manifest["report_sha256"].items():
            assert sha(ROOT/"reports"/name)==expected,name
        rows=read(folder/"captures.json")
        ids.extend(x["response"]["request_id"] for x in rows)
        for rep in run["repeats"]:
            sessions.append(rep["session_id"])
            part=[x for x in rows if x["case"]==rep["case"] and x["run"]==rep["repeat"]]
            assert [x["turn"] for x in part]==list(range(1,len(part)+1))
            assert {x["response"]["session_id"] for x in part}=={rep["session_id"]}
        assert run["settings_restored"]
        if run in full:
            assert len(run["repeats"])==25
            assert all(sum(x["case"]==cid for x in run["repeats"])==5
                       for cid in ["CONV-H01","CONV-H02","CONV-H03","CONV-H04","CONV-H05"])
    assert len(ids)==len(set(ids))==404
    assert len(sessions)==len(set(sessions))==52
    protected=read(ROOT/"evidence/preparation-manifest.json")["protected_datasets_sha256"]
    for name,expected in protected.items():assert sha(Path(name))==expected,name
    prohibited=[]
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git" in p.parts:continue
        assert p.name!=".env",str(p)
        if p.suffix in [".md",".json",".jsonl",".py",".txt"]:
            txt=p.read_text(encoding="utf-8")
            for prefix in ["sk-ant-api03-","ghp_","github_pat_"]:
                if prefix in txt:prohibited.append(str(p.relative_to(ROOT)))
    # Prefix constants above occur only in this audit source.
    assert set(prohibited)<= {"scripts/verify_artifacts.py"},prohibited
    result={"status":"passed","chat_requests":len(ids),"independent_sessions":len(sessions),
            "full_dialogs_per_profile":25,"raw_report_hashes_valid":True,
            "settings_restored_all_runs":True,"prior_golden_hashes_unchanged":True,
            "tracked_secret_prefix_scan":"no credentials found; local scan is not a security guarantee"}
    (ROOT/"evidence/artifact-checks.json").write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+"\\n").encode())
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
