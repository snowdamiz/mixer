#!/usr/bin/env python3
"""Independent review seal. Source custody only; no product/producer execution."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
ORIGINAL = BASE.parents[1]
PRE = BASE.parent / "preaccess"
UP = ROOT / "verification/android-private-owner-effect-integration-proposal/correction-1"
DOC = ROOT / "docs/android-private-owner-effect-contract-correction-review.md"

def ident(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def read(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return path.read_bytes()

def verify_bound():
    assert ident(read(ORIGINAL / "manifest.json"))["sha256"] == "8f84a627384e42a5695a52b266f420cb4a26e7c670982266432a022ef1071d58"
    for name, expected in json.loads(read(ORIGINAL / "manifest.json"))["files"].items():
        assert ident(read(ROOT / name)) == expected, name
    assert ident(read(PRE / "manifest.json"))["sha256"] == "638028e6531f4846d5d68e8979b24a0742d243207e54d184addc14bd2246923c"
    for name, expected in json.loads(read(PRE / "manifest.json"))["files"].items():
        assert ident(read(PRE / name)) == expected, name
    assert ident(read(UP / "manifest.json"))["sha256"] == "1479c098f5721cc80e0c82f8699d1482a30f71ad241fa06cfe2c6902255bec08"
    for name, expected in json.loads(read(UP / "manifest.json"))["files"].items():
        assert ident(read(ROOT / name)) == expected, name
    custody = json.loads(read(BASE / "custody.json"))
    for name, expected in custody["snapshots"].items():
        assert ident(read(BASE / name)) == expected, name

def seal():
    verify_bound()
    assert read(BASE / "capture.stderr") == b""
    assert json.loads(read(BASE / "capture.stdout"))["status"] == "admitted-correction-independent-source-custody-pass"
    for name in ("capture.py", "seal.py"):
        ast.parse(read(BASE / name).decode(), filename=name)
    assert all(line == line.rstrip() for line in read(DOC).decode().splitlines())
    spans = {
        "C1.1": [(71,88),(126,130)], "C1.2": [(102,104),(117,124)],
        "C1.3": [(143,157)], "C1.4": [(117,124),(132,157)],
        "C1.5": [(91,100),(159,177)], "C1.6": [(170,177),(228,244),(398,402)],
        "C1.7": [(349,359),(378,387)],
        "C2.1": [(34,37),(51,65),(181,202)], "C2.2": [(187,202),(214,226)],
        "C2.3": [(204,212)], "C2.4": [(102,104),(187,202),(214,226)],
        "C2.5": [(246,255)], "C2.6": [(319,347),(381,394)],
        "C3.1": [(313,347)], "C3.2": [(317,347),(389,394)],
        "C3.3": [(288,311),(349,369)], "C3.4": [(279,311),(370,387)],
        "C3.5": [(373,387)], "C3.6": [(349,394)],
        "P1": [(257,277)], "P2": [(102,104),(187,202)],
        "P3": [(102,113)], "P4": [(71,88),(398,402)],
        "P5": [(21,25),(228,244),(398,417)], "P6": [(398,407)],
        "P7": [(21,25),(338,341),(349,359),(409,411)],
        "P8": [(412,417)], "P9": [(419,440)]}
    pre = json.loads(read(PRE / "plan.json"))
    assert set(spans) == {v["id"] for v in pre["obligations"]}
    conflicting = {"C3.3", "C3.6", "P7"}
    judgments = [{**v, "judgment": "contradictory-R1" if v["id"] in conflicting else "explicit-coherent-source-contract",
        "corrected_document_lines": spans[v["id"]], "implementation_test_pass": False,
        "note": "Five unchanged V1 helper sites are subject to mandatory V2 semantic fence cases." if v["id"] in conflicting else "Contract requirement reviewed; future implementation behavior remains unrun."}
        for v in pre["obligations"]]
    inv = json.loads(read(BASE / "independent-inventory.json"))
    report = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "needs-contract-correction", "blocking_findings": [{"id": "R1",
            "summary": "Universal V2 semantic barrier matrix includes five unchanged V1 helper call sites",
            "exact_sites": [v for v in inv["barriers"] if v["legacy_V1_helper"]],
            "affected_obligations": sorted(conflicting),
            "minimum_correction": "New versioned roster/contract classification distinguishing V1 compile/baseline subjects from V2 semantic barrier subjects; no V1 product behavior changes."}],
        "obligations": judgments, "coherent_contract_obligations": 25,
        "conflicting_obligations": 3, "new_blocking_findings": 1,
        "C1_and_C2_signature_and_ownership_contracts": "explicit/coherent as reviewed source contracts",
        "candidate_manifest_sha256": "1479c098f5721cc80e0c82f8699d1482a30f71ad241fa06cfe2c6902255bec08",
        "preaccess_manifest_sha256": "638028e6531f4846d5d68e8979b24a0742d243207e54d184addc14bd2246923c",
        "producer_reported_666_checks": "custody/coverage only; verifier not executed, no implementation test credit",
        "independent_custody": {"candidate_members": 48, "candidate_bytes": 974667,
            "baseline_source_anchors": 189, "V1_anchors": 5, "V2_region_anchors": 184,
            "concrete_subjects": 14, "concrete_substitutes": 73,
            "original_review_members_unchanged": 77, "preaccess_members_unchanged": 5},
        "retained_reviewer_failures": ["attempts/custody-1", "attempts/custody-2"],
        "failed_attempt_disposition": "Review-helper whitespace/column conventions corrected; no producer or product defect.",
        "commands": [[str(Path(sys.executable).resolve()), "-B", str(BASE / "capture.py")],
                     [str(Path(sys.executable).resolve()), "-B", str(Path(__file__).resolve()), "seal"]],
        "product_tests_run": False, "host_closures_executed": False,
        "producer_helpers_executed": False, "implementation_selected": False,
        "implementation_accepted": False, "cross_compilation_run": False,
        "native_runtime_UI_capture_process_discovery_network_install_signing_credentials_publication": False,
        "hosted_harnesses_accessed": False, "product_profile_metadata_CI_or_original_candidate_edits": False,
        "OTA_authorized": False, "GA_qualified": False,
        "cleanup": "No native/capture/scratch resources created; no other project processes changed."}
    (BASE / "obligation-review.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    paths = [DOC, *[p for p in sorted(BASE.rglob("*")) if p.is_file() and p != BASE / "manifest.json"]]
    files = {str(p.relative_to(ROOT)): ident(read(p)) for p in paths}
    manifest = {"schema": 1, "scope": "Independent source-only correction review, not implementation tests or acceptance.",
        "members": len(files), "bytes": sum(v["bytes"] for v in files.values()), "files": files}
    (BASE / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "blocking_findings": 1,
        "members": manifest["members"], "bytes": manifest["bytes"],
        "manifest_sha256": ident(read(BASE / "manifest.json"))["sha256"]}))

def check():
    verify_bound()
    m = json.loads(read(BASE / "manifest.json"))
    actual = {str(p.relative_to(ROOT)) for p in BASE.rglob("*") if p.is_file() and p != BASE / "manifest.json"}
    actual.add(str(DOC.relative_to(ROOT)))
    assert actual == set(m["files"])
    for name, expected in m["files"].items():
        assert ident(read(ROOT / name)) == expected, name
    assert m["members"] == len(m["files"]) and m["bytes"] == sum(v["bytes"] for v in m["files"].values())
    print(json.dumps({"status": "independent-correction-review-seal-pass", "members": m["members"],
        "bytes": m["bytes"], "manifest_sha256": ident(read(BASE / "manifest.json"))["sha256"]}))

if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in ("seal", "check")
    {"seal": seal, "check": check}[sys.argv[1]]()
