#!/usr/bin/env python3
"""Capture exact bounded checker commands and versions, without Git/process scans."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
logs = HERE / "commands" / stamp
logs.mkdir(parents=True)
source = HERE / "check.py"
checker = source.read_bytes()
(logs / "checker-source.py").write_bytes(checker)
receipt = {"schema": 1, "at": stamp, "scope": "Python source-only necessary G5 subtrace checker",
           "python": sys.version, "executable": sys.executable, "cwd": str(ROOT),
           "checker_sha256": hashlib.sha256(checker).hexdigest(),
           "input_tree_digest": json.loads((HERE / "input-bindings.json").read_text())["input_tree_digest"],
           "commands": []}
for label, flags in [("normal", []), ("optimized", ["-O"])]:
    argv = [sys.executable, "-B", *flags, str(source)]
    result = subprocess.run(argv, cwd=ROOT, capture_output=True)
    (logs / f"{label}.stdout").write_bytes(result.stdout)
    (logs / f"{label}.stderr").write_bytes(result.stderr)
    receipt["commands"].append({"label": label, "argv": argv, "returncode": result.returncode,
                                 "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                                 "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()})
(logs / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True)+"\n")
(HERE / "latest-run.json").write_text(json.dumps({"receipt": str((logs / "receipt.json").relative_to(ROOT)),
                                                   "checker_sha256": receipt["checker_sha256"],
                                                   "all_passed": all(c["returncode"] == 0 for c in receipt["commands"])},
                                                  indent=2, sort_keys=True)+"\n")
print(json.dumps(receipt, sort_keys=True))
sys.exit(0 if all(c["returncode"] == 0 for c in receipt["commands"]) else 1)
