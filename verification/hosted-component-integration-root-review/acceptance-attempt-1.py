#!/usr/bin/env python3
"""Verify frozen component evidence and record root's scoped acceptance."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
bindings = {}


def bind(path, expected=None):
    actual = sha(ROOT / path)
    if expected is not None:
        assert actual == expected, path
    bindings[path] = actual
    return read(ROOT / path) if path.endswith(".json") else actual


producer = bind("verification/hosted-key-owner-implementation/receipt.json",
                "a9a6f27494a4b6af7452f0300f7b62f5942af69c0f73e128462a065f28986286")
review = bind("verification/hosted-key-owner-independent-review/receipt.json",
              "10f979d215719685374cc1238bced7849df2cb5431126d62c462c918cc0d942a")
assert len(producer["bindings"]) == 205 and len(review["bindings"]) == 56
for packet in [producer, review]:
    for path, expected in packet["bindings"].items():
        bind(path, expected)
for path, expected in review["sourceFiles"].items():
    bind(path, expected)
config = read(ROOT / "verification/hosted-key-owner-independent-review/configuration-bindings.json")
for path, expected in config["files"].items():
    bind(path, expected)
assert producer["sourceTreeDigest"] == review["sourceTreeDigest"]
assert review["unresolvedImplementationFindings"] == []
assert review["acceptedPureVerifierUnchanged"] and review["cleanup"]["ownedScratchAndBuildsRemoved"]
assert review["executionResults"]["LinuxSingleRunTotal"] == 58
assert not Path("/private/tmp/mixer-key-owner-independent-ji2mbagy").exists()
assert read(ROOT / "verification/hosted-key-owner-independent-review/linux-cleanup.json")["containerRetained"] is False

commands = []
for script in ["verification/hosted-artifact-admission-implementation/verify.py",
               "verification/hosted-artifact-admission-review/verify.py"]:
    argv = ["python3", "-B", script]
    result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True)
    commands.append({"argv": argv, "cwd": str(ROOT), "exitCode": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr})
    assert result.returncode == 0, result.stdout + result.stderr
bind("verification/hosted-artifact-admission-implementation/seal.json",
     "e21fb9d656e99d5c8ce47c3e42ece7470408850c8005fec68e93a69718f02ef9")
bind("verification/hosted-artifact-admission-review/seal.json",
     "b8a467869f2e9f631b9310c9e0226b67c46b4ffa6f90585a5a56c17b7b1adca2")
for path in ["docs/hosted-artifact-admission-contract.md",
             "docs/hosted-artifact-admission-implementation.md",
             "docs/hosted-artifact-admission-review.md",
             "verification/hosted-artifact-admission-contract/freeze.json",
             "verification/hosted-artifact-admission-review/run-2/receipt.json",
             "verification/hosted-component-integration-root-review/run-1/receipt.json",
             "verification/hosted-component-integration-root-review/run-1/hosted/receipt.json",
             "verification/hosted-component-integration-root-review/complete-run-1.py",
             "verification/hosted-component-integration-root-review/completion.json",
             str(Path(__file__).resolve().relative_to(ROOT))]:
    bind(path)
completion = read(HERE / "completion.json")
assert completion["qualification"]["passedTests"] == 73
assert completion["qualification"]["skippedTests"] == 1
assert completion["qualification"]["failedTests"] == 0
overlay = ROOT / "verification/hosted-artifact-admission-implementation/overlay"
overlay_inputs = {}
for source in sorted(overlay.rglob("*")):
    if source.is_file():
        path = str(source.relative_to(overlay))
        overlay_inputs[path] = sha(source)
assert len(overlay_inputs) == 4
for path, expected in completion["sourceInputs"].items():
    if path in overlay_inputs:
        assert overlay_inputs[path] == expected
        bind(str((overlay / path).relative_to(ROOT)), expected)
    else:
        bind(path, expected)

receipt = {
    "schema": 1, "status": "root-accepted-hosted-key-owner-and-artifact-admission-components",
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "toolVersion": subprocess.check_output(["python3", "--version"], text=True).strip(),
    "bindings": bindings, "commands": commands,
    "keyOwner": {"sourceTreeDigest": producer["sourceTreeDigest"],
                 "producerMacTests": 45, "producerLinuxTests": 46,
                 "independentMacCases": 12, "independentLinuxTotal": 58,
                 "accepted": True,
                 "contractClarification": "verification/hosted-key-owner-root-review/unknown-kid-scope-clarification.json"},
    "artifactAdmission": {"exactOverlay": overlay_inputs, "producerHostedTests": 44,
                          "independentCases": 316, "independentGoOracleComparisons": 257,
                          "originalGoComparisons": 208, "rechecks": 15,
                          "accepted": True, "applyExactOverlayAuthorized": True},
    "composedHostQualification": completion["qualification"],
    "sourceReview": [
        "Root reviewed actual fixed profile/endpoint configuration, bounded reservations, final verification fence, retained lifetime history, transport ownership/cleanup and independent adversarial evidence. Earlier root defects are resolved by exact frozen source.",
        "Root reviewed actual lexical walker, ordered duplicate handling, raw signed spans, base64 allocation bounds, complete host/root/grant semantics, standard signature/payload verification and retained-byte recheck. Independent parser/oracle/boundary evidence matches the inspected overlay.",
        "Combined actual hosted suite, packaged production release and fail-closed missing configuration pass against the exact union. Both cross-language fixture files are now explicitly bound and trigger hosted CI.",
    ],
    "limitations": [
        "Key owner is an explicitly started component; Application/RuntimeConfig startup wiring and authenticated HTTP routes remain unimplemented. Health-only API remains.",
        "Unknown-key pressure may allocate bounded configured-profile negative/eligible-refresh work; no token can create profiles or endpoints. No tenant permission follows from identity verification.",
        "Profile history is process-local, graceful shutdown may wait indefinitely for held owned controllers, and large close-delimited JWKS bodies may time out. Provider/fleet/clock, cross-restart authority and universal memory/real-time bounds are not qualified.",
        "Artifact admission validates explicit supplied host/root policy and bytes; it confers no provenance of policy, membership, storage, publication or execution authority.",
        "The composed macOS suite skips one Linux namespace case; actual production DNS/rebinding coverage is in separate Linux producer/reviewer runs. New combined Linux CI is pending commit/push.",
        "The retained first root collector failed only in its old ExUnit summary parser after all product commands and cleanup passed; separate completion verifies original outputs without claiming another runtime run.",
        "No physical/native, provider, repository authorization, blob durability, Oban release jobs, production deployment or GA gate is accepted."
    ],
    "applicationWired": False, "authenticatedHTTP": False,
    "membershipStorageAccepted": False, "gaAcceptance": False,
}
destination = HERE / "acceptance.json"
assert not destination.exists(), "Preserve existing root decision"
destination.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"status": receipt["status"], "bindings": len(bindings),
                  "hostTestsPassed": 73, "hostTestsSkipped": 1, "overlayFilesAuthorized": 4}))
