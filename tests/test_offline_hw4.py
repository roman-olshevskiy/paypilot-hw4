"""Offline contract checks against the unchanged official L05 loader/evaluator."""
import copy
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
KIT=ROOT.parent/"paypilot-l05-eval"
sys.path.insert(0,str(KIT))
import loader
import runner
import assertions
import hw4_capture


class OfflineHW4(unittest.TestCase):
    def setUp(self):
        self.cases=loader.load(ROOT/"l05_dialogs.jsonl")

    def test_schema_and_plan(self):
        self.assertEqual(len(self.cases),5)
        self.assertEqual(sum(len(c["turns"])*5 for c in self.cases),195)
        for c in self.cases:
            m=c["additional_metadata"]
            self.assertEqual(m["layer"],"memory")
            self.assertEqual(m["runs"],5)
            self.assertEqual(m["added_in"],"hw4")
            self.assertEqual(m["gate"],"release")
            self.assertEqual(m["assertion"],"dialog")
            self.assertEqual(m["summarize_after"],2)
            self.assertTrue(m["invariants"])

    def test_synthetic_clean_and_corruption(self):
        for case in self.cases:
            turns=[]
            for _ in case["turns"]:
                turns.append({"answer":"240.00 EUR goods_not_received, 90 days, 2026-10-18; original date 2026-07-20.",
                              "trace":{"name":"root","children":[]}})
            turns[2]["trace"]["children"].append({"name":"agent.summarize"})
            self.assertTrue(runner._dialog_run(case,{"turns":turns}).passed,case["id"])
            for inv in case["additional_metadata"]["invariants"]:
                for t in inv["probe_turns"]:
                    turns[t-1]["answer"]="180 EUR service_not_rendered, 60 days, 2026-12-13"
            self.assertFalse(runner._dialog_run(case,{"turns":turns}).passed,case["id"])

    def test_candidate_numbers_do_not_hide_reconfirmation(self):
        case=self.cases[0]
        turns=[{"answer":"240 EUR goods_not_received 90 days 2026-10-18","trace":{}}
               for _ in case["turns"]]
        turns[2]["trace"]={"name":"agent.summarize"}
        turns[4]["answer"]=("I can't reliably repeat the earlier details. "
                            "TX-0401 and TX-0402 are both EUR240. "
                            "Which one is the charge? It might be goods_not_received.")
        self.assertFalse(runner._dialog_run(case,{"turns":turns}).passed)

    def test_absent_summary_and_short_dialog_are_not_green(self):
        case=self.cases[0]
        run={"turns":[{"answer":"240 EUR goods_not_received 90 days 2026-10-18","trace":{}}
                      for _ in case["turns"]]}
        self.assertEqual(runner._dialog_run(case,run).assertion,"precondition")
        run["turns"]=run["turns"][:2]
        self.assertFalse(runner._dialog_run(case,run).passed)

    def test_initial_wrong_value_is_rejected(self):
        case=self.cases[0]
        turns=[{"answer":"240 EUR goods_not_received 90 days 2026-10-18","trace":{}}
               for _ in case["turns"]]
        turns[2]["trace"]={"name":"agent.summarize"}
        turns[0]["answer"]="180 EUR goods_not_received"
        self.assertFalse(runner._dialog_run(case,{"turns":turns}).passed)

    def test_restore_uses_configured_not_effective_retrieval(self):
        state={"defects":{"profile":"clean","extra_defects":[]},
               "clock":{"runtime_override":None},
               "summarize":{"summarize_after_steps":8},
               "retrieval":{"top_k":4,"index":"kb_clean","requested_top_k":4,"requested_index":""}}
        with patch.object(hw4_capture.stand,"set_profile") as profile, \
             patch.object(hw4_capture.stand,"set_defects") as defects, \
             patch.object(hw4_capture.stand,"set_clock") as clock, \
             patch.object(hw4_capture.stand,"set_summarize_after") as summary, \
             patch.object(hw4_capture.stand,"_call") as call:
            hw4_capture.restore(state)
        defects.assert_called_once_with("")
        summary.assert_called_once_with(8)
        call.assert_called_once_with("PUT","/api/_test/retrieval",{"top_k":4,"index":""})
