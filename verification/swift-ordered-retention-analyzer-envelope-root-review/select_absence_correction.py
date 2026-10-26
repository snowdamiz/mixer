"""Select the independently reviewed absence guard and exact isolated source."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
packets = []
for path, digest, count, size in [
    ("verification/swift-envelope-absent-state-correction/proposal-1/seal.json",
     "3da07ea9c308c9bee798cf7c891a8f9dfd2a170e85b43341c30caa38cdb9b04c", 35, 205372),
    ("verification/swift-envelope-absent-state-accounting-review/seal.json",
     "c9191a26ed0c5081e9c2ad97082fc61cee3f6eeb94ea49c4be5028b0f54536e4", 22, 119706),
]:
    raw = (ROOT / path).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    entries = json.loads(raw)["members"]
    assert len(entries) == count
    total = 0
    for item in entries:
        relative = pathlib.PurePosixPath(item["path"])
        assert not relative.is_absolute() and ".." not in relative.parts
        data = (ROOT / relative).read_bytes()
        assert len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"], str(relative)
        total += len(data)
    assert total == size
    packets.append({"seal": path, "sha256": digest, "members": count, "bytes": total})
review = ROOT / "verification/swift-envelope-absent-state-accounting-review"
findings = json.loads((review / "findings.json").read_text())
receipt = json.loads((review / "final-review-receipt.json").read_text())
assert findings["blocking_accounting_findings"] == []
assert receipt["mechanical_source_checks"] == {"failed": 0, "passed": 352, "runtime_tests": False}
source_sha = "2cd286a387ce336a18ea2872974e371ca4e772e2fd801f2186a3f62ce639bfef"
assert findings["candidate_source_sha256"] == receipt["candidate_source_sha256"] == source_sha
old = (OUT / "correction-numeric-contract-selection.json").read_bytes()
assert hashlib.sha256(old).hexdigest() == "199dfa75b024d04eeef28f2f40165115797a0bbb3d09a2405426172d8339867c"
result = {
    "schema": 1,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(pathlib.Path(__file__).resolve())],
    "python_version": sys.version,
    "checker_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
    "context_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    "status": "exact-absence-correction-selected-for-isolated-host-qualification",
    "packets": packets,
    "root_verified_members": 57,
    "root_verified_bytes": 325078,
    "candidate_source_sha256": source_sha,
    "parent_source_sha256": "1ef11e06678642231f783fea0e5fe376e8b1912730a6fb696a653ab04cb2043b",
    "source_pair": "verification/swift-envelope-absent-state-correction/proposal-1/src/",
    "prior_numeric_selection_sha256": hashlib.sha256(old).hexdigest(),
    "selected": {"leaf": 425, "W": 24, "B": 471, "G": 112, "T": 42, "finish": 47, "F": 42, "setup": 534},
    "explicit_G_ownership_amendment": {
        "reservation": "The existing single112 prepaid reservation before candidate initialization",
        "scope": "At most one terminal unpaid leaf among absent prior-state backing at any remaining, invalid nonzero entry spent, or readable prior-state underfunding",
        "source_path_upper_groups": {"absent": 7, "invalid_entry_spent": 7, "present_underfunded": 112},
        "single_use": "Complete terminal reply installs validity and status2/3 or reason15 prevents any later orchestrated leaf; rejected debit forms become terminal poison under main-paid W09",
        "caller_owner": "Main-paid W24 owns reply installation, validator, fallback and later latch handling independently of private debit. Leaf or G owns the complete leaf return exactly once.",
        "not_selected": "No repeated arbitrary private invocation entitlement, additional reservation, credit transfer, public refund or use of unassigned margin"
    },
    "caller_contract": "Poststate-only debit coherence for canonical private helper replies, with exact425/spent425/remaining0 paid form and coherent unpaid poison/underfunded forms. This predicate has no historical before-budget input and is not a general reply-shape or authority validator.",
    "public_debit": "534*S_paid + 47*F_paid + 425*N_B",
    "main_B471_public425_refund": False,
    "unchanged": ["Global limits", "Parent framing API/ABI/report prefix", "Candidate2048 single retained owner", "108 transfer edges", "Named logical24656/reserved41984/ceiling65536", "Full replay and semantic prefix authority remain false"],
    "independent_accounting": {"rows": 121, "transfer_edges": 108, "offline_checks": 352, "validator_path_groups": [2, 3, 4, 5]},
    "next_execution_scope": "Fresh bounded host source/layout/API/regression/R2 controls in a NEW implementation namespace, then independent behavior qualification; preserve all old and proposal packets",
    "inherited_limitation": findings["inherited_limitation"],
    "runtime_evidence_exists_for_selected_source": False,
    "implementation_accepted": False,
    "native_runtime_or_capture_authorized": False,
    "GA_qualified": False,
    "errors": [],
}
(OUT / "absence-correction-selection.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: result[key] for key in ("status", "root_verified_members", "root_verified_bytes", "candidate_source_sha256", "implementation_accepted")}))
