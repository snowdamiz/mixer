#!/usr/bin/env python3
"""Seal source preparation and guarded pure evidence; grant no execution authority."""
from offline_guard import install
install()

import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def row(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + "\n")


def source(path, first, last):
    text = (ROOT / path).read_text()
    start = text.index(first)
    stop = text.index(last, start) + len(last)
    return {
        "path": path, **row(ROOT / path),
        "startLine": text[:start].count("\n") + 1,
        "endLine": text[:stop].count("\n") + 1,
    }


manifest = json.loads((HERE / "manifest.json").read_text())
pure = json.loads((HERE / "pure-result.json").read_text())
assert (pure["passed"], pure["failed"], pure["errors"], pure["skipped"]) == (12, 0, 0, 0)
base = "verification/swift-dense512-product-integration/candidate/vm/"
save("derivation.json", {
    "schema": 1,
    "classification": "Stale exact lifecycle ledger/oracle and synthetic limit; no production invariant edit selected",
    "basis": "Frozen actual candidate charge sites plus unchanged baseline workload and non-pin accounting",
    "sources": {
        "constructor": source(base + "src/experimental_swift_reactor/cache.rs", "    fn construct_partial(", "partial.free_pins = dense_allowed_pins(budget.active_pins);"),
        "selection": source(base + "src/experimental_swift_reactor/cache.rs", "    fn available_pin(", "    fn resident_lookup("),
        "selection_before_cold_or_hit": source(base + "src/experimental/cache/borrowed.rs", "    let pin_slot = M::available_pin", "fn pin_acquired<M: CacheMode>"),
        "checked_cumulative_meter": source("vm/src/experimental_swift_reactor/control.rs", "    pub(crate) fn work_with_wasi(", "    /// Charge once before dispatch"),
        "lifecycle_module": source("vm/src/experimental_swift_reactor/lifecycle_tests.rs", "fn module(spec:", "    let mut out = b\"\\0asm"),
    },
    "sl13": {
        "constructor": {"unchangedTerms": "29 + 64 + 512 + 192 + 512*8", "old": 4893, "newBitmapPublication": 1, "new": 4894},
        "coldFormula": "108 + pinSelection + 2*encodedBodyBytes + 3*instructions + 13",
        "calls": [
            {"function": 35, "bodyBytes": 14, "instructions": 6, "oldPinSelection": 1, "newPinSelection": 5, "old": 168, "new": 172},
            {"function": 62, "bodyBytes": 7, "instructions": 3, "oldPinSelection": 1, "newPinSelection": 5, "old": 145, "new": 149},
            {"function": 36, "bodyBytes": 19, "instructions": 9, "oldPinSelection": 2, "newPinSelection": 5, "old": 188, "new": 191},
        ],
        "warm": {"old": [8, 9], "new": [12, 12], "formula": "lookup1 + successfulBitmapSelection5 + checkedIndexChain6"},
        "oldCumulative": [4893, 5061, 5394, 5411],
        "newCumulative": [4894, 5066, 5406, 5430],
        "deltas": [1, 5, 12, 19],
        "newRuntimeObserved": False,
    },
    "sl14": {
        "unchangedNoopBodyBytes": 2, "unchangedNoopInstructions": 1,
        "oldConstructor": 4893, "oldCold": 129, "oldExactCap": 5022,
        "newConstructor": 4894, "newCold": 133, "newExactCap": 5027,
        "invariant": "Initialization completes exactly at cap; first later positive cache charge refuses without committing; one guest instruction remains recorded",
        "testOnlyCap": True, "productionCap": 64000000,
        "structuredFailureObservedInOriginalLog": False,
        "correctedRustConfirmation": "pending",
    },
    "crossChecks": {"generic64EntryConstructor": [4928, 4929], "firstWarmHit": [8, 12], "fullChainWarmHit": [260, 264]},
    "counterResets": 0, "replenishment": 0, "productionDefaultEdits": 0,
})
tests = re.findall(r"#\[test\]\s*fn (\w+)", (HERE / "baseline/vm/src/experimental_swift_reactor/lifecycle_tests.rs").read_text())
save("receipt.json", {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "decision": "Source correction candidate with guarded pure controls; independent review and corrected Rust execution pending",
    "ownership": "verification/swift-pin-bitmap-lifecycle-correction/ only",
    "baselineCommitParentSupplied": manifest["baselineCommitParentSupplied"],
    "baselineGitTreeParentSupplied": manifest["baselineGitTreeParentSupplied"],
    "priorCandidateTreeSHA256": manifest["priorCandidateTreeSHA256"],
    "candidateTreeSHA256": manifest["candidateTreeSHA256"],
    "sourceMembers": 136,
    "newOverlayPaths": manifest["newOverlayPaths"],
    "overlayFilesComparedWithPriorCandidate": 1,
    "exactSubstitutions": 13,
    "preservedLifecycleTestMethods": len(tests),
    "preservedLifecycleTestNames": tests,
    "commands": [
        {"command": "python3 -B verification/swift-pin-bitmap-lifecycle-correction/prepare.py", "exit": 0, "toolVersion": sys.version, "purpose": "Bound baseline and composed single test-only overlay"},
        {"command": "python3 -B verification/swift-pin-bitmap-lifecycle-correction/test_controls.py", "exit": 1, "toolVersion": sys.version, "result": "first-pure-result.json", "output": "first-pure-controls.stderr", "purpose": "Preserved11/12 pure-control result; transcription of two intermediate report literals failed"},
        {"command": "python3 -B verification/swift-pin-bitmap-lifecycle-correction/test_controls.py", "exit": 0, "toolVersion": sys.version, "result": "pure-result.json", "output": "pure-controls.stderr", "purpose": "12/12 guarded source and arithmetic controls"},
    ],
    "actualFailedRun": {"runID": 40806119805, "artifactID": 12868935321, "cargoCommand": 5, "passed": 465, "failed": 2, "ignored": 0, "seconds": 331.42, "sixthCargoCommand": "not run", "status": "failed and preserved"},
    "pure": pure,
    "canonicalEdited": False,
    "frozenPacketsEdited": False,
    "runnerWorkflowEdited": False,
    "nativeUICaptureRuns": 0,
    "localCompilerProductRuntimeRuns": 0,
    "GitGhDeliveryDispatchActions": 0,
    "nestedLiveProcessesSessionsGroupsSignalsWaitsSockets": 0,
    "ownedRuntimeOrCaptureInstancesStarted": 0,
    "cleanup": "No owned child process or runtime scratch was created; only this source/evidence packet remains",
    "heldProcessesProbed": False,
    "publicSignedOTAFieldLogGAQualified": False,
    "nextAction": "Root review and explicit harness rebind before any selected host execution; same six commands/case coverage and finite caps required",
    "pending": ["Independent review", "Corrected actual Rust all-feature Debug and Release", "Formatting/lint", "Canonical product integration", "Native and physical acceptance under the existing pause", "All release and GA gates"],
})
files = {
    p.relative_to(HERE).as_posix(): row(p)
    for p in sorted(HERE.rglob("*")) if p.is_file() and p.name != "seal.json"
}
tree = hashlib.sha256("".join(n + "\0" + files[n]["sha256"] + "\n" for n in sorted(files)).encode()).hexdigest()
save("seal.json", {
    "schema": 1,
    "scope": "Source-only lifecycle fixture correction and pure evidence; no run selected",
    "files": files,
    "treeSHA256": tree,
    "candidateSourceTreeSHA256": manifest["candidateTreeSHA256"],
})
print(json.dumps({"members": len(files), "packetTreeSHA256": tree, "sealSHA256": row(HERE / "seal.json")["sha256"], "candidateTreeSHA256": manifest["candidateTreeSHA256"], "lifecycleMethods": len(tests)}))
