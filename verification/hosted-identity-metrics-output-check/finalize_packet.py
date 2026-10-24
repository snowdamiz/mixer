#!/usr/bin/env python3
"""Freeze the final Linux output-routing observation with complete evidence hashes."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
RUN = OUT / "linux-final"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads((RUN / path).read_text())


def save(path, data):
    with (OUT / path).open("x") as target:
        target.write(json.dumps(data, indent=2, sort_keys=True) + "\n")


receipt = read("receipt.json")
cleanup = read("cleanup.json")
source = read("source-manifest.json")
assert receipt["status"] == "passed" and receipt["passed"] == 46
assert receipt["skipped"] == 0 and receipt["invalid"] == 0
assert receipt["inputsUnchanged"] and receipt["allNineMetricsInExplicitDirectory"]
assert not receipt["legacyEvidencePathCreated"]
assert len(receipt["identityMetrics"]) == 9
assert cleanup["scratchRemoved"] and not cleanup["ownedContainerRetained"]
assert all(cleanup["frozenPacketsUnchanged"].values()) and cleanup["originalCIFailureUnchanged"]
assert cleanup["preexistingContainerIDs"] == cleanup["preexistingContainerIDsStillPresent"]
assert all(sha(ROOT / path) == expected for path, expected in source["files"].items())
for path, expected in receipt["identityMetrics"].items():
    assert sha(RUN / "identity-metrics" / path) == expected
for command in read("execution.json")["commands"]:
    assert command["exitCode"] == 0
    assert sha(RUN / command["output"]) == command["outputSHA256"]

frozen = read("frozen-evidence-before.json")
for name, snapshot in frozen.items():
    current = {str(p.relative_to(ROOT / "verification" / name)): sha(p)
               for p in sorted((ROOT / "verification" / name).rglob("*")) if p.is_file()}
    assert current == snapshot["files"], name
repair_manifest = json.loads((ROOT / "verification/hosted-tls-fixture-ci-repair/evidence-manifest.json").read_text())
for path, expected in repair_manifest["files"].items():
    assert sha(ROOT / path) == expected, path
failure = ROOT / "verification/github-ci-dd604eca-phoenix/artifact/tests.log"

save("receipt.json", {
    "status": "passed final Linux component matrix; root acceptance/CI are separate",
    "sourceRevision": receipt["sourceRevision"],
    "sourceTreeDigest": receipt["sourceTreeDigest"],
    "dependencyTreeDigest": receipt["dependencyTreeDigest"],
    "fixtureSHA256": receipt["fixtureSHA256"],
    "exactSourceChangesFromAcceptedRepair": read("source-differences-from-repair.json"),
    "execution": {"path": "linux-final/execution.json", "sha256": sha(RUN / "execution.json")},
    "observation": {"passed": 46, "invalid": 0, "skipped": 0,
                    "allNineMetricsInExplicitDirectory": True, "legacyEvidencePathCreated": False,
                    "privateTmpAbsentBeforeAndAfter": True, "tlsFixtureDirectoriesRetained": 0,
                    "metrics": receipt["identityMetrics"]},
    "inputsUnchangedDuringRunAndAtFinalization": True,
    "frozenPriorPacketsUnchanged": cleanup["frozenPacketsUnchanged"],
    "originalCIFailure": {"path": str(failure.relative_to(ROOT)), "sha256": sha(failure)},
    "cleanup": {"path": "linux-final/cleanup.json", "sha256": sha(RUN / "cleanup.json"),
                "scratchRemoved": True, "ownedContainerRetained": False,
                "allPreexistingContainerIDsRetained": True},
    "limits": ["Linux identity component only; no devices, store, GA, provider or customer operation",
               "No full hosted/release/database or GitHub CI acceptance in this packet",
               "Root collector source is hash-bound; its invocation and unset-helper behavior are separately tested by root"],
})
files = {str(p.relative_to(ROOT)): sha(p) for p in sorted(OUT.rglob("*")) if p.is_file()}
tree_digest = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
save("evidence-manifest.json", {"files": files, "treeDigest": tree_digest,
    "algorithm": "SHA-256 per file; tree SHA-256 of sorted-key compact UTF-8 JSON file-hash map"})
print(json.dumps({"sourceTreeDigest": receipt["sourceTreeDigest"], "evidenceTreeDigest": tree_digest,
                  "receiptSHA256": sha(OUT / "receipt.json"), "verifiedEvidenceFiles": len(files),
                  "passed": 46, "metrics": 9}, indent=2))
