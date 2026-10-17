"""Generate HW4 dialog cases from independent PayPilot engines. No stand API."""
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAND = Path(os.environ.get("STAND_DIR", str(ROOT.parent / "paypilot-stand-shared")))
sys.path.insert(0, str(STAND))
from app import seed
from app.engines import disputes

TX = next(row for row in seed.TRANSACTIONS if row[0] == "TX-0401")
assert TX[1] == "ACC-1005" and TX[3:5] == (240.0, "EUR")
REASON = "goods_not_received"
AS_OF = date(2026, 9, 15)
ORACLE = disputes.check(REASON, date.fromisoformat(TX[2]), TX[8], AS_OF,
                        compliance_hold=False)
AMOUNT, WINDOW = TX[3], ORACLE.window_days

START = ("Transaction TX-0401, 240.00 EUR: the goods never arrived. "
         "Confirm its amount and currency and name the single applicable reason code. "
         "We are only discussing this charge; do not create or submit a dispute.")
ELIGIBLE = ("Can I dispute that charge? State the applicable reason code and "
            "filing window in days; do not file anything.")
BACK = ("Back to the original charge: repeat its exact amount, currency and reason code, "
        "then explain the next step. Do not file anything.")
REPEAT = "The amount is 240 euro, as I said at the start."
FINAL = ("For that original charge, state its applicable filing window in days and "
         "the exact filing deadline. Do I still have time? Do not file anything.")

SPECS = [
    ("CONV-H01", "основний", [START, ELIGIBLE,
      "What is my daily card limit?", "And the FX spread if I pay in USD?",
      BACK, REPEAT, FINAL], 2, 1, [5], 7),
    ("CONV-H02", "ізоляція осі", [START, ELIGIBLE,
      "What are my daily card limit and FX spread for USD payments?",
      BACK, FINAL], 2, 1, [4], 5),
    ("CONV-H03", "ізоляція осі", [START, ELIGIBLE,
      "What is my daily card limit?", "And the FX spread if I pay in USD?",
      "How do card payments differ from SEPA transfers?",
      "What should I check before making an international transfer?",
      "Explain what a conversion spread means in plain language.",
      BACK, REPEAT, FINAL], 2, 1, [8], 10),
    ("CONV-H04", "контроль", [START, ELIGIBLE,
      "For this same charge, what evidence of non-delivery should I keep?",
      "What information about this same charge would be needed to review a dispute?",
      BACK, REPEAT, FINAL], 2, 0, [5], 7),
    ("CONV-H05", "найгірший",
      [START + " Its transaction date is 2026-07-20; keep that date with the case.",
       ELIGIBLE, "What is my daily card limit?", "And my FX spread for USD payments?",
       BACK, "How much of my monthly transfer limit remains?",
       "What are the public SWIFT transfer fee components?",
       BACK + " Also repeat the original transaction date in YYYY-MM-DD format.",
       REPEAT, FINAL], 3, 2, [5, 8], 10),
]


def cases():
    result = []
    for cid, role, turns, entities, switches, probes, final in SPECS:
        invs = [
            {"entity": "dispute_amount_eur", "from_turn": 1, "level": 2,
             "probe_turns": probes, "expected_number": AMOUNT, "tolerance": 0.01,
             "oracle_turn": 1, "oracle_by": "seed:TX-0401.amount/currency",
             "defect": "D06"},
            {"entity": "reason_code", "from_turn": 1, "level": 3,
             "probe_turns": probes, "pattern": r"(?i)\bgoods[_ -]+not[_ -]+received\b",
             "oracle_turn": 1, "oracle_by": "scenario intent: goods never arrived; engine:disputes.check",
             "defect": "D07"},
            {"entity": "filing_window_days", "from_turn": 2, "level": 2,
             "probe_turns": [final], "expected_number": WINDOW, "tolerance": 0,
             "oracle_turn": 2, "oracle_by": "engine:disputes.check.window_days",
             "defect": "D07"},
        ]
        # A correct candidate in a list is not evidence of case retention.
        invs[1]["forbid"] = (
            r"(?is)\b(?:which\s+(?:one|transaction|charge)|"
            r"(?:please|could you|can you)\s+confirm\s+(?:the\s+)?(?:amount|transaction|charge)|"
            r"(?:can(?:not|'t)|unable to)\s+(?:reliably\s+)?(?:repeat|recall|identify))")
        if entities == 3:
            invs.append({"entity": "transaction_date", "from_turn": 1, "level": 3,
                         "probe_turns": [8], "pattern": r"2026-07-20",
                         "oracle_turn": 1, "oracle_by": "seed:TX-0401.date",
                         "defect": "D06"})
        checks = [
            {"turn": 1, "assertion": "numeric", "expected_number": AMOUNT, "tolerance": 0.01,
             "label": "initial oracle: transaction amount"},
            {"turn": 1, "assertion": "regex", "pattern": invs[1]["pattern"],
             "label": "initial oracle: scenario reason code"},
            {"turn": 2, "assertion": "numeric", "expected_number": WINDOW, "tolerance": 0,
             "label": "initial oracle: filing window"},
            {"turn": final, "assertion": "regex",
             "pattern": r"(?i)(2026-10-18|18(?:th)?\s+(?:of\s+)?Oct(?:ober)?(?:,?\s+2026)?|Oct(?:ober)?\s+18(?:th)?(?:,?\s+2026)?)",
             "label": "independent oracle: filing deadline"},
        ]
        result.append({
            "id": cid, "scenario": f"{role}: dispute context over {len(turns)} turns",
            "context": {"customer_id": "CUS-0004", "clock": "2026-09-15T10:00:00Z"},
            "turns": [{"role": "user", "content": t} for t in turns],
            "expected_output": f"Retain EUR{AMOUNT:.2f}, {REASON}, {WINDOW} days; deadline {ORACLE.deadline}",
            "additional_metadata": {
                "layer": "memory", "oracle": "engine:disputes", "assertion": "invariant",
                "invariants": invs, "checks": checks, "min_turns": len(turns),
                "axes": {"length": len(turns), "entities": entities, "topic_switches": switches},
                "plan_role": role, "source": "complaint" if cid == "CONV-H01" else "plan",
                "failure_mode": "summarization_drop_or_corruption", "severity": "critical",
                "runs": 5, "gate": "release", "added_in": "hw4",
                "summarize_after": 2, "expect_summarize": True, "summarize_turn": 3,
                "engine_call": "disputes.check('goods_not_received', date(2026,7,20), 'settled', date(2026,9,15), compliance_hold=False)",
                "why_this_level": "Numeric amount/window use L2; canonical reason/date patterns use L3. Independent initial checks catch consistently wrong answers."
            }})
    return result


if __name__ == "__main__":
    content = "".join(json.dumps(c, ensure_ascii=False) + chr(10) for c in cases())
    path = ROOT / "l05_dialogs.jsonl"
    path.write_bytes(content.encode("utf-8"))
    manifest = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "cases": len(cases()), "chat_requests_per_profile": sum(len(c["turns"])*5 for c in cases()),
                "oracle": ORACLE.as_dict(), "transaction": list(TX),
                "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (ROOT/"evidence/dataset-manifest.json").write_bytes((json.dumps(manifest, indent=2)+"\n").encode())
    print(json.dumps(manifest, indent=2))
