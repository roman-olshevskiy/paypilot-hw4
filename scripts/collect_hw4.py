"""Copy only completed runs; preserve all raw bytes."""
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
KIT=ROOT.parent/"paypilot-l05-eval"

for folder in sorted((KIT/"evidence/hw4-runs").glob("*")):
    path=folder/"manifest.json"
    if not path.exists() or not (folder/"restored.json").exists():
        continue
    manifest=json.loads(path.read_text(encoding="utf-8"))
    target=ROOT/"evidence/hw4-runs"/folder.name
    shutil.copytree(folder,target,dirs_exist_ok=True)
    for name in manifest["reports"]:
        shutil.copyfile(KIT/"reports"/name,ROOT/"reports"/name)
        report=json.loads((KIT/"reports"/name).read_text(encoding="utf-8"))
        for case in report["cases"]:
            rel=case.get("traces_dir")
            if rel:
                shutil.copytree(KIT/rel,ROOT/rel,dirs_exist_ok=True)
print("Copied completed runs and unchanged raw reports/traces")
