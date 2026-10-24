#!/usr/bin/env python3
"""Record host release-service ownership regressions and full Go checks."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument("--name", required=True)
args = parser.parse_args()
assert args.name and all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.name)
out = HERE / args.name
out.mkdir()
paths = [p for p in (ROOT / "services").rglob("*")
         if p.is_file() and "verification" not in p.relative_to(ROOT).parts
         and (p.suffix in (".go", ".sql") or p.name in ("go.mod", "go.sum")
              or "testdata" in p.parts)]
paths.append(ROOT / "contracts/release-v2.json")
snapshot = lambda: {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}
before = snapshot()
go = shutil.which("go")
assert go
env = dict(os.environ, GOTOOLCHAIN="go1.26.4")
receipt = {
    "schema": 1, "startedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "running", "sourceRevision": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "sourceFiles": before,
    "sourceTreeSHA256": hashlib.sha256(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    "driverSHA256": sha(Path(__file__).resolve()), "goPath": go,
    "goSHA256": sha(Path(go).resolve()), "python": sys.version,
    "environment": {"GOTOOLCHAIN": env["GOTOOLCHAIN"]}, "commands": [],
    "scope": "Headless Go service tests; caller mutation starts after construction returns.",
    "limitations": ["No concurrent mutation during construction is supported.",
                    "PostgreSQL integration tests require their separate build tag/runner and are not run here.",
                    "No hosted identity, external delivery, production deployment, mobile or GA acceptance."]}
def save():
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
save()
commands = [
    ("go-version", [go, "version"]),
    ("modules", [go, "list", "-m", "-json", "all"]),
    ("focused", [go, "test", "./release", "-run", "^TestConfigOwnership", "-count=1", "-json"]),
    ("services-race", [go, "test", "-race", "-count=1", "-json", "./..."]),
    ("vet", [go, "vet", "./..."]),
]
for name, argv in commands:
    log = out / (name + ".log")
    with log.open("w") as stream:
        result = subprocess.run(argv, cwd=ROOT / "services", env=env, stdout=stream, stderr=subprocess.STDOUT)
    receipt["commands"].append({"name": name, "argv": argv, "cwd": "services", "exitCode": result.returncode,
                                "log": str(log.relative_to(ROOT)), "sha256": sha(log)})
    save()
    if result.returncode:
        receipt["status"] = "failed"
        save()
        raise SystemExit(result.returncode)
assert snapshot() == before, "source changed during qualification"
counts = {}
for name in ("focused", "services-race"):
    events = [json.loads(line) for line in (out / (name + ".log")).read_text().splitlines() if line.startswith("{")]
    counts[name] = {action: len([e for e in events if e.get("Action") == action and "Test" in e])
                   for action in ("pass", "fail", "skip")}
    assert counts[name]["pass"] and not counts[name]["fail"]
receipt.update(status="passed", sourceUnchanged=True, testEvents=counts,
               completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
save()
print(json.dumps({"status": receipt["status"], "sourceFiles": len(before), "testEvents": counts}))
