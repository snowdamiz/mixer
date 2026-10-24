#!/usr/bin/env python3
"""Record root's candidate-2 preflight acceptance; execute no VM control code."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = "4f16367b0985d924564b80b00b556f799cb42e3426a9b08fd8aca53b2a0015a4"
CANDIDATE = "e1b88be22eb683c40bfe53cd32f5b48d391b475b6097bab233aaf00b5303453d"
PRODUCER = ROOT / "verification/swift-control-accounting-candidate-2"
REVIEW = ROOT / "verification/swift-control-candidate-2-review"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


out = HERE / "candidate-2-acceptance.json"
assert not out.exists(), "Acceptance is append-only; preserve the existing receipt"
commands = []
for script in [PRODUCER / "verify.py", REVIEW / "verify.py"]:
    argv = ["python3", "-B", str(script.relative_to(ROOT))]
    result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True)
    commands.append({"argv": argv, "cwd": str(ROOT), "exitCode": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr})
    assert result.returncode == 0, result.stdout + result.stderr

producer = read(PRODUCER / "receipt.json")
review = read(REVIEW / "receipt.json")
qualifying = read(PRODUCER / "qualifying.json")["resultDirectory"]
base = read(PRODUCER / qualifying / "baseline-manifest.json")
candidate = read(PRODUCER / qualifying / "candidate-manifest.json")
live = {name: sha(ROOT / "vm" / name) for name in base}
assert len(live) == 119 and live == base
assert hashlib.sha256(canonical(live)).hexdigest() == BASE
assert hashlib.sha256(canonical(candidate)).hexdigest() == CANDIDATE
assert producer["candidateTreeSHA256"] == review["candidateVMClosure"] == CANDIDATE
assert review["sourceAccountingPreflightRecommendation"]
assert read(REVIEW / "findings.json")["unresolvedFindings"] == []
assert read(REVIEW / "findings.json")["resolvedPriorFindings"] == ["SCPR-01"]
assert sha(PRODUCER / "seal.json") == "4550cb63df539164c2c58cac12d15215311720ee199d7f1d2bb06b5695d622b1"
assert sha(REVIEW / "seal.json") == "95e1680d0c22f4c1bf7027623eca10172cfa17a51be5db534201e01b8c615139"
bindings = [
    HERE / "contract.json", HERE / "accounting-scope-interpretation.json",
    ROOT / "docs/swift-control-invocation-contract.md",
    ROOT / "docs/swift-control-accounting-candidate-2.md",
    ROOT / "docs/swift-control-candidate-2-review.md",
    PRODUCER / "seal.json", PRODUCER / "receipt.json", PRODUCER / "source.patch",
    REVIEW / "seal.json", REVIEW / "receipt.json", REVIEW / "findings.json",
    ROOT / "vm/src/experimental_swift_reactor/value_operations.rs",
    PRODUCER / "overlay/src/experimental_swift_reactor/control_operations.rs",
    Path(__file__).resolve(),
]
receipt = {
    "schema": 1, "status": "root-accepted-candidate-2-source-accounting-preflight-only",
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "sourceRevision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "toolVersion": subprocess.check_output(["python3", "--version"], text=True).strip(),
    "baselineVMClosure": BASE, "candidateVMClosure": CANDIDATE,
    "commands": commands,
    "bindings": {str(p.relative_to(ROOT)): sha(p) for p in bindings},
    "acceptedEvidence": {
        "positiveFields": 7640, "wrapperFields": 136, "removedObsoleteFields": 16,
        "freshIndependentCanonicalFunctionsPerConfiguration": 38,
        "freshIndependentMetadataConfigurations": 8,
        "frozenExpandedMethodsIdentical": ["pop32", "close_control", "branch", "run"],
        "production": {"header": 1514504, "active": 1162520, "frame": 2211968},
        "unit": {"header": 2392040, "active": 2325032, "frame": 3949904},
        "original128MiBStateAnd256MiBCombinedCeilingsUnchanged": True,
    },
    "rootSourceReview": [
        "Original value pop charges work, validates agreement, pops once, then performs its sole post-effect fallible live removal.",
        "Candidate wrapper calls that primitive once, latches the existing cleanup mismatch only for Err after actual length change, and returns its exact Result without another debit or diagnostic.",
        "Reviewed actual guards, current-frame floors, control predebit/publication, after-effect removal, terminal route and unchanged original-owner structure; behavior remains to be executed.",
        "Independent actual-source/canonical MIR census and concrete layouts establish authored logical accounting only; optimized machine stack, RSS and total allocator bounds are not inferred.",
    ],
    "authorizedNextWork": [
        "Execute SC01-SC12 and required old suites in a new isolated accepted-baseline plus exact candidate overlay, with original proof/cache/frame ownership and real decoded instructions.",
        "Add finite test-only hooks and original fixtures as needed in the new packet; preserve all frozen producer/reviewer files and current live VM.",
        "If a production correction changes source or concrete types, record it and regenerate affected exact accounting, expansion and layout evidence before requesting implementation acceptance.",
        "Independent behavior review and root acceptance precede live product integration; fetch/dispatch, Ready and public invoke remain outside this slice.",
    ],
    "sourceAccountingPreflightAccepted": True,
    "isolatedControlBehaviorTestingAuthorized": True,
    "controlBehaviorExecutedByRoot": False,
    "implementationAccepted": False, "sc01Through12Passed": False,
    "liveVMUnchanged": True, "nativeRuntime": False, "physicalRuntime": False,
    "gaAcceptance": False,
}
out.write_bytes(canonical(receipt))
print("passed: exact candidate-2 source/accounting preflight accepted; isolated SC01-SC12 behavior work authorized; live VM unchanged")
