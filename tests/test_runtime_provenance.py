"""Read running container source through a real test; no API/model calls."""
import hashlib
import json
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STAND=ROOT.parent/"paypilot-stand-shared"

class RuntimeProvenance(unittest.TestCase):
    def test_runtime_sources_match_checkout(self):
        paths=["app/agent/loop.py","app/agent/summarize.py",
               "app/engines/disputes.py","app/engines/policy.py"]
        code=("import hashlib,json;from pathlib import Path;"
              "paths="+repr(paths)+";"
              "print(json.dumps({p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}))")
        proc=subprocess.run(["docker","compose","exec","-T","stand","python","-c",code],
                            cwd=STAND,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                            text=True,encoding="utf-8",check=True)
        actual=json.loads(proc.stdout)
        expected={p:hashlib.sha256((STAND/p).read_bytes()).hexdigest() for p in paths}
        (ROOT/"evidence/runtime-source-provenance.json").write_bytes(
            (json.dumps({"runtime":actual,"checkout":expected},indent=2)+chr(10)).encode())
        self.assertEqual(actual,expected)
