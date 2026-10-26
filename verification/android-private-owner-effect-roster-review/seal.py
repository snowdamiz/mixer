#!/usr/bin/env python3
"""Seal this independent narrow source-contract review; no product execution."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DOC = ROOT / "docs/android-private-owner-effect-roster-review.md"

def ident(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def read(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return path.read_bytes()

def source_verify():
    argv = [str(Path(sys.executable).resolve()), "-B", str(BASE / "verify.py"), "check"]
    r = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=30, check=False)
    assert r.returncode == 0 and not r.stderr, (r.stdout, r.stderr)
    return {"argv": argv, "cwd": str(ROOT), "exit_code": r.returncode,
            "stdout": r.stdout.decode(), "stderr": r.stderr.decode()}

def seal():
    assert not (BASE / "manifest.json").exists(), "do not replace this independent seal"
    verify = source_verify()
    assert read(BASE / "capture.stderr") == b"" and read(BASE / "check.stderr") == b""
    assert json.loads(read(BASE / "capture.stdout"))["status"] == "independent-R1-custody-and-classification-pass"
    assert json.loads(read(BASE / "check.stdout"))["status"] == "independent-R1-frozen-custody-pass"
    for name in ("verify.py", "seal.py"):
        ast.parse(read(BASE / name).decode(), filename=name)
    assert all(line == line.rstrip() for line in read(DOC).decode().splitlines())
    proof = json.loads(read(BASE / "independent-classification.json"))
    custody = json.loads(read(BASE / "custody.json"))
    assert proof["V2_full_ordered_records_equal"] and proof["V2_count"] == 184
    assert proof["V1_count"] == 5 and proof["complete_closures_unchanged"]
    result = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "selection-ready-contract", "R1_closed": True,
        "C3.3_C3.6_P7_remaining_conflicts_resolved": True,
        "combined_contract": [
            {"role": "original-proposal", "manifest_sha256": "7547220cc7f1ba6648ca2cbb3fdf96e402b5b3af9abf68906263be57688838a7"},
            {"role": "correction-1", "manifest_sha256": "1479c098f5721cc80e0c82f8699d1482a30f71ad241fa06cfe2c6902255bec08"},
            {"role": "R1-roster-amendment", "manifest_sha256": "5a7c7f64cc4ae716446a9756393c82e7cfebad5e29316e4ae4c3b79b52a0aa5f"}],
        "recommendation": "Combined source contract is ready for root implementation selection; root alone selects implementation/profile and future acceptance.",
        "blocking_findings": [], "optional_expansion": False,
        "independently_verified": {"candidate_members": 23, "candidate_bytes": 630064,
            "ordered_complete_V2_records_unchanged": 184, "exact_V1_reclassifications": 5,
            "all_189_historical_anchors_preserved": True, "noninventory_fields_unchanged": True,
            "complete_host_closures_unchanged": True, "B_actual_subjects": 14, "B_substitutes": 73,
            "prior_packet_closed_memberships": 5, "existing_checksum_metadata_separately_bound": 2},
        "prose_review": "Universal correction-1 V2 matrix now applies only to the amended184 active entries; five legacy entries get positive unchanged V1 baseline/compile requirements and no V2 fence semantics.",
        "retained_reviewer_attempt": {"path": "attempts/closure-1", "product_defect": False,
            "resolution": "Original frozen sealers explicitly declare checksum sidecars. Exact80byte metadata lines independently verified, no other extra members allowed."},
        "verification": verify,
        "context_revision": custody["context_revision"], "context_tree": custody["context_tree"],
        "implementation_selected": False, "implementation_accepted": False,
        "product_tests_run": False, "host_closures_executed": False,
        "cross_compilation_run": False, "producer_helpers_executed": False,
        "OTA_authorized": False, "GA_qualified": False,
        "product_profile_CI_metadata_commit_or_prior_member_changes": False,
        "native_runtime_UI_capture_phones_process_discovery_hosted_harness_network_install_signing_credentials_publication": False,
        "pending": ["root implementation/profile selection", "actual selected implementation and both host closures", "independent implementation verification and cross-compilation", "native runtime under pause and disconnected final phones", "separate-repository immutable published FieldLog", "signing/store/operational/accountable GA"],
        "cleanup": "No runtime/capture/scratch resources created; other project processes unchanged."}
    (BASE / "review-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    paths = [DOC, *[p for p in sorted(BASE.rglob("*")) if p.is_file() and p != BASE / "manifest.json"]]
    files = {str(p.relative_to(ROOT)): ident(read(p)) for p in paths}
    manifest = {"schema": 1, "scope": "Independent R1 source-contract recommendation, not implementation or product-test acceptance.",
        "members": len(files), "bytes": sum(v["bytes"] for v in files.values()), "files": files}
    (BASE / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "R1_closed": True, "members": manifest["members"],
        "bytes": manifest["bytes"], "manifest_sha256": ident(read(BASE / "manifest.json"))["sha256"]}))

def check():
    source_verify()
    m = json.loads(read(BASE / "manifest.json"))
    actual = {str(p.relative_to(ROOT)) for p in BASE.rglob("*") if p.is_file() and p != BASE / "manifest.json"}
    actual.add(str(DOC.relative_to(ROOT)))
    assert actual == set(m["files"])
    for name, expected in m["files"].items(): assert ident(read(ROOT / name)) == expected, name
    assert m["members"] == len(m["files"]) and m["bytes"] == sum(v["bytes"] for v in m["files"].values())
    print(json.dumps({"status": "independent-R1-review-seal-pass", "members": m["members"], "bytes": m["bytes"],
                      "manifest_sha256": ident(read(BASE / "manifest.json"))["sha256"]}))

if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in ("seal", "check")
    {"seal": seal, "check": check}[sys.argv[1]]()
