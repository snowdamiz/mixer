#!/usr/bin/env python3
"""Review source binding and independently authored Swift semantics probes only."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
BUILD.mkdir(exist_ok=True)
COMMANDS = []

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(name, argv, timeout=30, env=None):
    result = subprocess.run(argv, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout, env=env)
    output = HERE / (name + ".log")
    output.write_text(result.stdout)
    COMMANDS.append({"argv": argv, "cwd": str(ROOT), "exit_code": result.returncode,
                     "output": str(output.relative_to(ROOT)), "output_sha256": sha(output)})
    if result.returncode:
        raise RuntimeError(name + " failed: " + result.stdout)
    return result.stdout

original_manifest = ROOT / "verification/android-signed-ui-binding-design/source-manifest.sha256"
design_receipt_path = ROOT / "verification/android-signed-ui-binding-design/receipt.json"
design_receipt = json.loads(design_receipt_path.read_text())
if sha(original_manifest) != design_receipt["selected_source_manifest_sha256"]:
    raise RuntimeError("design inspection manifest does not match its own receipt")
if sha(ROOT / design_receipt["proposal"]) != design_receipt["proposal_sha256"]:
    raise RuntimeError("design proposal does not match its own receipt")
original = {}
for line in original_manifest.read_text().splitlines():
    digest, name = line.split("  ", 1)
    original[name] = digest
selected = list(original) + [
    "mixer-product-plan.md",
    str(original_manifest.relative_to(ROOT)),
    str(design_receipt_path.relative_to(ROOT)),
    "docs/android-signed-ui-binding-design.md",
    "capability-activation/Sources/MixerCapabilityActivation/CapabilityConcreteRetirement.swift",
    "capability-activation/Tests/MixerCapabilityActivationTests/CapabilityAttemptReservationTests.swift",
    "verification/android-transport-review/review.md",
    "verification/android-transport-review/receipt.json",
    "verification/android-guest-ui-transport/receipt.json",
    str((HERE / "ContinuationLifetimeProbe.swift").relative_to(ROOT)),
    str((HERE / "review.md").relative_to(ROOT)),
    str((HERE / "verify.py").relative_to(ROOT)),
]

def manifest(name):
    content = "".join(sha(ROOT / p) + "  " + p + "\n" for p in selected)
    target = HERE / name
    target.write_text(content)
    return content

before = manifest("source-before.sha256")
revision = run("source-revision-before", ["git", "rev-parse", "HEAD"])
run("source-status-before", ["git", "status", "--short"])
swiftc = shutil.which("swiftc")
run("swift-version", [swiftc, "--version"])
run("python-version", [os.sys.executable, "--version"])
run("git-version", ["git", "--version"])
run("platform", ["uname", "-a"])
cases = ["continuation_tail", "actual_task_join"]
for mode, flags in [("debug", ["-Onone", "-g"]), ("release", ["-O"]),
                    ("tsan", ["-Onone", "-g", "-sanitize=thread"])]:
    exe = BUILD / ("continuation-" + mode)
    run(mode + "-build", [swiftc, "-swift-version", "6", "-strict-concurrency=complete",
                         "-warnings-as-errors", "-parse-as-library", *flags,
                         str(HERE / "ContinuationLifetimeProbe.swift"), "-o", str(exe)])
    for case in cases:
        result = run(mode + "-" + case, [str(exe), case])
        if "PASS " + case + ":" not in result:
            raise RuntimeError("missing pass marker")

after = manifest("source-after.sha256")
run("source-revision-after", ["git", "rev-parse", "HEAD"])
run("source-status-after", ["git", "status", "--short"])
original_match = {p: {"expected": d, "actual": sha(ROOT / p), "matches": d == sha(ROOT / p)}
                  for p, d in original.items()}
(HERE / "design-source-match.json").write_text(json.dumps(original_match, indent=2) + "\n")
receipt = {
    "status": "proposal_review_with_scoped_host_semantics_evidence",
    "collected_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "source_revision": revision.strip(),
    "selected_source_manifest": str((HERE / "source-before.sha256").relative_to(ROOT)),
    "selected_source_manifest_sha256": sha(HERE / "source-before.sha256"),
    "selected_sources_unchanged": before == after,
    "design_receipt_source_count": len(original),
    "design_receipt_all_sources_match": all(v["matches"] for v in original_match.values()),
    "design_proposal_sha256": sha(ROOT / "docs/android-signed-ui-binding-design.md"),
    "commands": COMMANDS,
    "host_probe_modes": ["debug", "release", "tsan"],
    "host_probe_cases": cases,
    "official_sources_read": [
        "https://developer.android.com/ndk/reference/group/looper",
        "https://developer.android.com/reference/android/os/Looper",
        "https://developer.android.com/ndk/guides/jni-tips",
    ],
    "scope": "Source/design review plus six executions of original Swift continuation/Task.value language-semantics probes. No product binding is implemented or executed.",
    "limitations": [
        "No C transport rerun or modification; existing owner/reviewer receipts inspected as prior context.",
        "No Swift Android binding, JNI, Java widget, actual Android Looper, emulator or physical run.",
        "Host semantics observations do not establish final binding ownership or source closure correctness.",
        "No physical discovery/query/reconnect request; no package download, dependency, production edit, commit, push, customer message, publication or GA authorization.",
    ],
}
(HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
if before != after or not receipt["design_receipt_all_sources_match"]:
    raise RuntimeError("source binding changed or original design receipt is stale")
print("PASS review source bindings and six scoped Swift semantics cases")
