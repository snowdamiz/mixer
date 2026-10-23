#!/usr/bin/env python3
"""Link independent probes against an already captured integration candidate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--name", required=True)
parser.add_argument("--mode", choices=["debug", "release", "tsan"], default="debug")
parser.add_argument("--base-receipt", default="verification/guest-ui-activation/candidate-2/receipt.json")
args = parser.parse_args()
assert args.name and all(c.islower() or c.isdigit() or c == "-" for c in args.name)
out = HERE / args.name
out.mkdir(exist_ok=False)
work = HERE / ".build" / args.name
bundle = work / "ActivationReview.xctest"
binary = bundle / "Contents/MacOS/ActivationReview"
binary.parent.mkdir(parents=True)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
base_path = ROOT / args.base_receipt
base = json.loads(base_path.read_text())
artifact = base["artifacts"][args.mode]["dylib"]
assert sha(artifact["path"]) == artifact["sha256"]
source = Path(base["source"])
for name, digest in base["source_files"].items():
    assert sha(source / name) == digest
for name, digest in base["borrowed_files"].items():
    assert sha(name) == digest
(bundle / "Contents/Info.plist").write_bytes(plistlib.dumps({
    "CFBundleExecutable": binary.name,
    "CFBundleIdentifier": "org.mixer.ui.activation.review",
    "CFBundlePackageType": "BNDL",
    "CFBundleVersion": "1",
}))
command = list(next(c["command"] for c in base["commands"] if c["name"] == args.mode + "-test-link"))
command = [p for p in command if not p.endswith(".swift")]
command[command.index("-o") + 1] = str(binary)
inputs = [HERE / "RecoveryDiagnosticsProbe.swift", HERE / "CloseBindingProbe.swift",
          *sorted((HERE / "probe-inputs").glob("*.swift"))]
command += [str(p) for p in inputs]
record = {
    "base_receipt": str(base_path), "base_receipt_sha256": sha(base_path),
    "candidate": artifact, "mode": args.mode, "input_sha256": {str(p.relative_to(ROOT)): sha(p) for p in inputs},
    "runner_sha256": sha(__file__), "commands": [],
    "scope": "Independent private-store pre/post-intent UI failure and delayed MainActor binding/close probes. Real signed ingress and native-only validation; no VM effects enable, native-window health, physical device or GA qualification.",
}
tests = next(c for c in base["commands"] if c["name"] == args.mode + "-tests")
jobs = [("swift-version", ["swift", "--version"], {}),
        ("link", command, {}), ("tests", [tests["command"][0], str(bundle)], tests["environment"])]
for name, cmd, extra in jobs:
    env = os.environ | {"DEVELOPER_DIR": "/Applications/Xcode.app/Contents/Developer"} | extra
    proc = subprocess.run(cmd, env=env, cwd=ROOT, capture_output=True, timeout=90)
    log = out / (name + ".log")
    log.write_bytes(proc.stdout + proc.stderr)
    record["commands"].append({"name": name, "command": cmd, "extra_environment": extra,
                               "exit_code": proc.returncode, "log_sha256": sha(log)})
    (out / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    print(name, proc.returncode, flush=True)
    if proc.returncode:
        raise SystemExit(proc.returncode)
record["binary"] = {"path": str(binary), "sha256": sha(binary)}
(out / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
