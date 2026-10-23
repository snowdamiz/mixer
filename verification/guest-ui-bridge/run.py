#!/usr/bin/env python3
"""Record real bridge commands without substituting generated source or mocks."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def sources():
    paths = [ROOT / "experimental-capability-runtime/Package.swift", ROOT / "sdk/Package.swift",
             ROOT / "contracts/guest-ui-event-v1.json"]
    for folder in ["experimental-capability-runtime/Sources", "experimental-capability-runtime/Tests", "sdk/Sources"]:
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file())
    paths.extend(p for p in (ROOT / "vm/include").glob("*.h"))
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(set(paths))}

name, *command = sys.argv[1:]
if not command:
    raise SystemExit("run.py NAME COMMAND [ARG ...]")
before = sources()
begin = time.monotonic()
environment = {"DEVELOPER_DIR": "/Applications/Xcode.app/Contents/Developer"}
log = OUT / "logs" / (name + ".log")
log.parent.mkdir(parents=True, exist_ok=True)
with log.open("w") as stream:
    process = subprocess.run(command, cwd=ROOT, env={**os.environ, **environment}, stdout=stream, stderr=subprocess.STDOUT)
after = sources()
receipt = {
    "command": command, "cwd": str(ROOT), "environment": environment,
    "exitCode": process.returncode, "elapsedSeconds": time.monotonic() - begin,
    "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "sourceSHA256Before": before, "sourceSHA256After": after, "sourcesUnchanged": before == after,
    "log": str(log.relative_to(ROOT)), "logSHA256": sha(log),
    "tools": {tool: subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
              for tool, args in {"swift": ["swift", "--version"], "xcode": ["xcodebuild", "-version"], "clang": ["clang", "--version"]}.items()},
    "nativeArchive": {"path": str(ROOT / "experimental-capability-runtime/.build/guest-ui-native/libmixer_vm_capability_experimental.a"),
                      "sha256": sha(ROOT / "experimental-capability-runtime/.build/guest-ui-native/libmixer_vm_capability_experimental.a")},
    "scope": "Local Mac bridge unit/integration execution against one combined native archive; no physical device, full Swift guest, renderer or GA claim."
}
(OUT / (name + ".json")).write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({k: receipt[k] for k in ["exitCode", "elapsedSeconds", "sourcesUnchanged", "log"]}))
print(log.read_text()[-12000:])
raise SystemExit(process.returncode)
