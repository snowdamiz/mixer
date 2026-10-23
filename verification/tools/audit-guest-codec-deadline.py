#!/usr/bin/env python3
"""Match the reviewed codec snapshot and subsequent deadline repair evidence."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def require(condition, detail):
    if not condition:
        raise RuntimeError(detail)


def logs(commands):
    for item in commands:
        expected = item.get("outputSHA256", item.get("output_sha256"))
        require(sha((ROOT / item["output"]).read_bytes()) == expected, item["output"])
        require(item.get("exitCode", item.get("exit_code")) == 0, item["name"])
    return len(commands)


def main():
    codec_path = "capabilities/verification/guest-transport-codec/receipt.json"
    review_path = "verification/guest-transport-codec-review/receipt.json"
    deadline_path = "capabilities/verification/host-deadline/receipt.json"
    codec, review, deadline = map(read, [codec_path, review_path, deadline_path])
    revision = review["reviewed_commit"]
    require(codec["source"]["files"] == review["source"]["files"], "codec/review source mismatch")
    require(codec["scoped_checks_passed"] and review["scoped_checks_passed"] and not review["findings"], "codec review failed")
    changed = []
    for item in review["source"]["files"]:
        blob = subprocess.check_output(["git", "show", revision + ":" + item["path"]], cwd=ROOT)
        require(len(blob) == item["bytes"] and sha(blob) == item["sha256"], item["path"])
        if sha((ROOT / item["path"]).read_bytes()) != item["sha256"]:
            changed.append(item["path"])
    expected_changes = sorted([
        "sdk/Sources/MixerCapabilities/Host.swift", "sdk/Sources/MixerCapabilities/GeneratedIdentity.swift",
        "capabilities/java/mixer/capabilities/CapabilityNativeIdentity.java", "capabilities/schema/hashes.json",
    ])
    require(sorted(changed) == expected_changes, "unexpected change after independent codec review")
    for path, expected in review["review_source_sha256"].items():
        require(sha((ROOT / "verification/guest-transport-codec-review" / path).read_bytes()) == expected, path)
    for item in review["fixed_contract"]["preserved_files"]:
        require(sha((ROOT / item["path"]).read_bytes()) == item["sha256"], item["path"])
    for item in codec["fixture_runs"]:
        require(sha((ROOT / item["raw_outputs"]).read_bytes()) == item["raw_outputs_sha256"], item["raw_outputs"])
        require(item["matched"] == item["total"] == 90 and item["pending"] == 0, "fixture mismatch")
    require(deadline["passed"] and deadline["sourceUnchangedDuringRun"], "deadline qualification failed")
    for item in deadline["source"]["files"]:
        data = (ROOT / item["path"]).read_bytes()
        require(len(data) == item["bytes"] and sha(data) == item["sha256"], item["path"])
    require(sha(json.dumps(deadline["source"]["files"], sort_keys=True, separators=(",", ":")).encode()) == deadline["source"]["digest"], "deadline source digest")
    require(sha((ROOT / "verification/tools/qualify-host-deadline.py").read_bytes()) == deadline["runnerSHA256"], "deadline runner changed")
    require(sha((ROOT / "sdk/Sources/MixerCapabilities/Host.swift").read_bytes()) == deadline["hostMatchesIndependentlyTestedCandidateSHA256"], "candidate mismatch")
    layout = read("verification/capability-native-layout-proposal/receipt.json")
    for path, expected in layout["inputs"].items():
        require(sha((ROOT / path).read_bytes()) == expected, path)
    counts = {
        "codecSourceFilesAtReviewedCommit": len(review["source"]["files"]),
        "codecImplementationLogs": logs(codec["commands"] + codec["tools"]),
        "codecReviewLogs": logs(review["commands"] + review["tools"]),
        "deadlineSourceFiles": len(deadline["source"]["files"]),
        "deadlineLogs": logs(deadline["commands"]),
        "proposedCLayoutLogs": logs(layout["commands"]),
    }
    receipt = {
        "schema": 1, "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "reviewedCodecCommit": revision, "reviewedCodecSourceDigest": review["source"]["digest"],
        "deadlineSourceDigest": deadline["source"]["digest"], "matched": counts,
        "postCodecReviewChanges": changed, "newDeadlineRegression": "capabilities/Tests/MixerCapabilitiesTests/HostDeadlineTests.swift",
        "receipts": {p: sha((ROOT / p).read_bytes()) for p in [codec_path, review_path, deadline_path]},
        "nativeSourceHashAfterRepair": read("capabilities/schema/hashes.json")["nativeImplementationSHA256"],
        "result": "Reviewed codec bytes preserved; exact independently probed Host repair matches host/cross-compile qualification",
        "limitations": ["Codec independent review applies to c8bb3bc; deadline repair has its own exact source receipt",
                        "C layout checks are proposal-only, with no Rust parity or native session functions",
                        "No guest bridge, physical device, activation/release, FieldLog plugin or GA qualification"],
    }
    (ROOT / "verification/guest-codec-deadline-integration-2026-10-23.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
