#!/usr/bin/env python3
"""Execute actual shared pure verdict code on macOS. No UIKit/native input."""
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile

BASE = pathlib.Path(__file__).resolve().parent
ENV = {**os.environ, "DEVELOPER_DIR": "/Applications/Xcode_26.6.app/Contents/Developer"}
commands = []


def run(argv):
    result = subprocess.run(list(map(str, argv)), env=ENV, text=True, capture_output=True)
    commands.append({"argv": list(map(str, argv)), "DEVELOPER_DIR": ENV["DEVELOPER_DIR"],
                     "exitCode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    (BASE / "oracle-commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip()


sources = [BASE / "source/Prototype/DiagnosticRequirement.swift", BASE / "oracle-probe.swift"]
run(["/usr/bin/xcrun", "swiftc", "--version"])
sdk = run(["/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path"])
with tempfile.TemporaryDirectory(prefix="mixer-toggle-diagnostic-oracle-", dir=BASE) as scratch:
    scratch = pathlib.Path(scratch)
    (scratch / "main.swift").write_bytes(sources[1].read_bytes())
    binary = scratch / "oracle"
    run(["/usr/bin/xcrun", "swiftc", "-swift-version", "6", "-sdk", sdk, sources[0], scratch / "main.swift", "-o", binary])
    result = json.loads(run([binary]))
receipt = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "scope": result["scope"],
           "passed": all(item["pass"] for item in result["checks"]), "checkCount": len(result["checks"]),
           "checks": result["checks"], "sources": {str(p.relative_to(BASE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
           "temporaryHostExecutableRemoved": True, "nativeUIKitExecuted": False}
(BASE / "oracle-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
