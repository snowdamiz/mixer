#!/usr/bin/env python3
"""Exercise the frozen private I/O foundation, not the future updater."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

root = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
inputs = json.loads((out / "inputs.json").read_text())
source = Path(inputs["source"])
work = source.parent
native = Path(inputs["native_copy"])
digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for name, expected in inputs["files"].items():
    assert digest(source / name) == expected, name
record = {"status": "running", "source_manifest_sha256": inputs["manifest_sha256"], "commands": [],
          "scope": "Private capability I/O foundation on frozen material dependencies; no coordinator, SPI adoption or executable authority"}
def save():
    (out / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
def run(name, args):
    start = time.monotonic()
    result = subprocess.run(args, cwd=source, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = out / (name + ".log"); log.write_bytes(result.stdout)
    record["commands"].append(dict(name=name, argv=args, cwd=str(source), exit_code=result.returncode,
                                   seconds=time.monotonic()-start, log_sha256=digest(log)))
    save(); print(name, result.returncode, flush=True)
    if result.returncode:
        record["status"] = "failed preserved"; save(); raise SystemExit(result.returncode)
run("swift-version", ["swift", "--version"])
for mode, flags in [("debug", []), ("release", ["-c", "release"]), ("tsan", ["--sanitize", "thread"])]:
    run(mode, ["swift", "test", "--package-path", str(source / "capability-activation"),
        "--scratch-path", str(work / ("build" if mode != "tsan" else "tsan")),
        "-Xcc", "-I" + str(native / "include"), "-Xlinker", "-L" + str(native / "lib"),
        "-Xswiftc", "-warnings-as-errors"] + flags)
record["export_unchanged"] = all(digest(source / name) == expected for name, expected in inputs["files"].items())
record["new_source_unchanged"] = all(digest(root / name) == inputs["files"][name] for name in inputs["new_files"])
record["status"] = "passed" if record["export_unchanged"] and record["new_source_unchanged"] else "source changed"
save()
