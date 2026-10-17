"""Read-only real API preflight. No chat, compare, series or model calls."""
import json
import os
import sys
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("SERVICE_URL", "http://localhost:8000")


class Preflight(unittest.TestCase):
    def test_live_preflight_without_model(self):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        paths = {"health":"/health", "defects":"/api/_test/defects",
                 "clock":"/api/_test/clock", "summarize":"/api/_test/summarize_after",
                 "retrieval":"/api/_test/retrieval", "seed":"/api/_test/seed",
                 "prompt":"/api/_test/prompt", "customers":"/api/_test/state/customers",
                 "transactions":"/api/_test/state/transactions"}
        data = {}
        for key,path in paths.items():
            with opener.open(BASE+path, timeout=20) as response:
                data[key] = json.load(response)
        (ROOT/"evidence/preflight.json").write_bytes((json.dumps(data, indent=2)+chr(10)).encode())
        self.assertEqual(data["health"]["status"],"ok")
        self.assertNotEqual(data["health"]["provider"],"mock")
        self.assertFalse(data["health"].get("keys_required"))
        tx = next(t for t in data["transactions"]["rows"] if t["id"]=="TX-0401")
        self.assertEqual(tx["amount"],240)
        self.assertEqual(tx["date"],"2026-07-20")
