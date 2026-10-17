"""Explicit real-test entry point; never performs live calls on discovery."""
import os
import subprocess
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
KIT=ROOT.parent/"paypilot-l05-eval"


@unittest.skipUnless(os.environ.get("HW4_PROFILE"),"Set HW4_PROFILE explicitly")
class LiveHW4(unittest.TestCase):
    def test_real_course_eval_with_capture_and_restore(self):
        profile=os.environ["HW4_PROFILE"]
        phase=os.environ.get("HW4_PHASE","pilot")
        self.assertIn(profile,["clean","lesson-05"])
        self.assertIn(phase,["pilot","full"])
        command=["docker","compose","run","--rm","-T","eval","python","hw4_capture.py",
                 "--set","l05_dialogs","--gate","release","--profile",profile,"--traces"]
        if phase=="pilot":command+=["--only","CONV-H01","--repeat","1"]
        result=subprocess.run(command,cwd=KIT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                              text=True,encoding="utf-8",errors="replace")
        (ROOT/"evidence"/f"{phase}-{profile}.stdout.txt").write_bytes(result.stdout.encode())
        self.assertIn(result.returncode,[0,1],result.stdout[-2500:])
