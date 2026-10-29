#!/usr/bin/env python3
"""Seal the owned source/mock review; importing review arms guards first."""
import review
import datetime
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def save(name, value):
    (HERE / name).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def row(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


controls = json.loads((HERE / "controls-result.json").read_text())
assert controls["tests"] == 11
assert controls["failures"] == controls["errors"] == controls["skips"] == 0
assert controls["liveApiAttempts"] == []
assert controls["scratchRemaining"] == []
assert list(HERE.glob("pure-*")) == []
source_paths = [
    "verification/swift-pin-bitmap-lint-independent-admission/seal.json",
    "verification/swift-pin-bitmap-lint-independent-admission/workflow.yml",
    "verification/swift-pin-bitmap-lint-independent-admission/admit.py",
    "verification/swift-pin-bitmap-lint-independent-admission/bounded_commands.py",
    "verification/swift-pin-bitmap-lint-independent-admission/host_controls.py",
    "vm/tests/differential.rs", "vm/tests/experimental_oracle.rs",
    "vm/tests/float_differential.rs", "vm/tests/table_memory_differential.rs",
]
save("source-basis.json", {"schema": 1, "files": {p: row(ROOT / p) for p in source_paths}})
save("receipt.json", {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "decision": "Accept for root selection of one bounded hosted attempt with two explicit nonblocking evidence limits",
    "parentSuppliedRevision": "6d57e05e58e6d614e58a0a4dc0fad661264fb46f", "GitVerified": False,
    "scope": "Independent host proposal/source/mock review only; candidate semantics previously admitted separately",
    "inputSealSHA256": "2012b4f0aabe97ebc2c10a501ea0f1dcc06791b0b4dcc5db5bb80c371fb28238",
    "inputMembers": 18, "inputTreeSHA256": "b3bb8c60d2a14213b48e7a203b97618cce8214fd78b09219f9d779fd3ef7359c",
    "candidateTreeSHA256": "7f188bd7b0fe12244936bcbde3f1e4b2f9d9d3fedd43cacbf750d4ba55684748",
    "newControls": 11, "newControlsPassed": 11, "existingControlsRerun": False,
    "commands": [
        "python3 -B verification/swift-pin-bitmap-lint-host-proposal-review/review.py",
        "python3 -B verification/swift-pin-bitmap-lint-host-proposal-review/finalize.py",
    ],
    "toolVersion": sys.version, "guardBeforeSubjectImports": True,
    "realNestedProcessSessionGroupSignalTimerWaitSocketCalls": 0, "liveApiAttempts": [],
    "RustNodeSwiftElixirCompilerProductRuntimeRuns": 0, "nativeUICaptureRuns": 0,
    "GitGhDispatchActions": 0, "YAMLParserExecuted": False, "workflowValidation": "structural source review only",
    "canonicalEdits": False, "producerPacketWritten": False, "workflowInstalled": False, "selected": False,
    "disposablePureScratchRemaining": 0, "otherProjectsTouched": False,
    "FieldLog": {"run": 40802230894, "pgid": 2424, "pid": 2621, "probedSignalledRetried": False},
    "localHoldsUnchanged": [20745, 20770, 20780, 20817, 20842, 20851, 20866],
    "limitations": [
        "Unexpected formatter roster changes fail before exact before/after retention",
        "Contradictory FAILED summary text is not independently scanned; actual Cargo exit zero is required",
        "No trusted YAML parser available from parent's guarded check; no dependency installed",
        "Provisioner outside managed custody; same-group descendants only; Node internal pipe caps absent",
        "Scratch excluded from upload even if preserved on runner by custody hold",
    ],
    "pending": ["root selection", "host execution", "artifact interpretation", "canonical integration", "native/physical/published-package FieldLog/GA"],
    "GAQualified": False,
})
files = {p.name: row(p) for p in sorted(HERE.iterdir()) if p.is_file() and p.name != "seal.json"}
tree = hashlib.sha256("".join(n + "\0" + files[n]["sha256"] + "\n" for n in sorted(files)).encode()).hexdigest()
save("seal.json", {"schema": 1, "scope": "Independent host proposal review only", "files": files, "treeSHA256": tree})
print(json.dumps({"members": len(files), "treeSHA256": tree, "sealSHA256": row(HERE / "seal.json")["sha256"], "newControls": 11, "liveApiAttempts": review.ATTEMPTS}, sort_keys=True))
