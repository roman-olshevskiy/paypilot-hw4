"""Capture/restore adapter around the unchanged L05 runner; invoked by tests."""
import json
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cli
import runner
import stand


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(data, indent=2, ensure_ascii=False) + chr(10)).encode())


def snapshot():
    return {key: stand._call("GET", path) for key, path in {
        "health": "/health", "defects": "/api/_test/defects",
        "clock": "/api/_test/clock", "summarize": "/api/_test/summarize_after",
        "retrieval": "/api/_test/retrieval", "prompt": "/api/_test/prompt"}.items()}


def restore(before):
    stand.set_profile(before["defects"]["profile"])
    stand.set_defects(",".join(before["defects"].get("extra_defects", [])))
    stand.set_clock(before["clock"].get("runtime_override"))
    stand.set_summarize_after(before["summarize"]["summarize_after_steps"])
    ret = before["retrieval"]
    stand._call("PUT", "/api/_test/retrieval",
                {"top_k": ret.get("requested_top_k", ret["top_k"]), "index": ret.get("requested_index", "")})


def run(argv):
    args = cli.parse(argv)
    if not args.profile or args.dry_run:
        raise ValueError("Explicit live profile required")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    folder = HERE / "evidence/hw4-runs" / (stamp + "-" + args.profile)
    before = snapshot()
    save(folder/"before.json", before)
    records = []
    context = {"case": None, "run": 0, "turn": 0}
    original_chat, original_one_run = stand.chat, runner._one_run
    reports_before = set((HERE/"reports").glob("*.json"))
    code = None
    def chat(message, session_id=None, customer_id=None):
        response = original_chat(message, session_id, customer_id=customer_id)
        tree = stand.trace(response["request_id"])
        context["turn"] += 1
        records.append({**context, "question": message, "response": response, "trace": tree})
        save(folder/"captures.json", records)
        return response
    def one_run(case):
        if context["case"] == case["id"]:
            context["run"] += 1
        else:
            context.update(case=case["id"], run=1)
        context["turn"] = 0
        return original_one_run(case)
    stand.chat, runner._one_run = chat, one_run
    try:
        stand.set_defects("")
        code = cli.main(argv)
        return code
    finally:
        stand.chat, runner._one_run = original_chat, original_one_run
        save(folder/"captures.json", records)
        produced = sorted(set((HERE/"reports").glob("*.json"))-reports_before)
        save(folder/"manifest.json",
             {"profile": args.profile, "argv": argv, "runner_exit_code": code,
              "chat_requests": len(records), "reports": [p.name for p in produced],
              "report_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in produced},
              "usage_scope": "Chat/root usage excludes unreported summarizer usage; separate overhead must not be silently treated as zero."})
        restore(before)
        save(folder/"restored.json", snapshot())


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
