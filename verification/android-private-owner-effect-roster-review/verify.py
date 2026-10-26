#!/usr/bin/env python3
"""Independent narrow R1 custody and structured comparison; no product execution."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
UP = ROOT / "verification/android-private-owner-effect-roster-amendment"
EXPECTED = "5a7c7f64cc4ae716446a9756393c82e7cfebad5e29316e4ae4c3b79b52a0aa5f"
IDS = ["NativeRenderer:L60:C234:1", "NativeRenderer:L61:C242:1", "NativeRenderer:L62:C149:1",
       "NativeRenderer:L62:C454:2", "NativeRenderer:L62:C509:3"]
SEALS = [
    ("original-proposal", "verification/android-private-owner-effect-integration-proposal/manifest.json",
     "7547220cc7f1ba6648ca2cbb3fdf96e402b5b3af9abf68906263be57688838a7", 36, 606635, False, "correction-1"),
    ("original-review", "verification/android-private-owner-effect-contract-review/manifest.json",
     "8f84a627384e42a5695a52b266f420cb4a26e7c670982266432a022ef1071d58", 77, 1426839, False, "correction-1"),
    ("preaccess-plan", "verification/android-private-owner-effect-contract-review/correction-1/preaccess/manifest.json",
     "638028e6531f4846d5d68e8979b24a0742d243207e54d184addc14bd2246923c", 5, 58432, True, None),
    ("correction-1", "verification/android-private-owner-effect-integration-proposal/correction-1/manifest.json",
     "1479c098f5721cc80e0c82f8699d1482a30f71ad241fa06cfe2c6902255bec08", 48, 974667, False, None),
    ("final-correction-review", "verification/android-private-owner-effect-contract-review/correction-1/review/manifest.json",
     "d6016514ce21f48a537395fbf2d142e6e75489b62d23c5be91266212cb0d0616", 67, 1160101, False, None)]
SIDECARS = {
    "original-proposal": "c12f2d863326a37c06e062b53b44ed9811a609c613901591559b69f710a9ecde",
    "correction-1": "c89cc5a14c44d5ce8b713f0d757aca64073ace52b4d95555817aa0a15e5c89b0"}

def ident(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def read(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return path.read_bytes()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def copy(path, target):
    data = read(path); target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    return ident(data)

def command(argv):
    r = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=15, check=False)
    assert r.returncode == 0, (argv, r.stderr)
    return {"argv": argv, "cwd": str(ROOT), "exit_code": r.returncode,
            "stdout": r.stdout.decode(), "stderr": r.stderr.decode()}

def prior_closures():
    results = []
    for label, name, digest, count, size, relative, extension in SEALS:
        path = ROOT / name; raw = read(path); assert ident(raw)["sha256"] == digest, label
        m = json.loads(raw); assert len(m["files"]) == count
        assert sum(v["bytes"] for v in m["files"].values()) == size
        expected_paths = set()
        for member, expected in m["files"].items():
            p = path.parent / member if relative else ROOT / member
            assert ident(read(p)) == expected, member
            if p.is_relative_to(path.parent): expected_paths.add(p)
        sidecar = path.parent / "handoff.sha256" if label in SIDECARS else None
        if sidecar:
            assert read(sidecar) == (digest + "  manifest.json\n").encode()
            assert ident(read(sidecar))["sha256"] == SIDECARS[label]
        actual = {p for p in path.parent.rglob("*") if p.is_file()
                  and p != path and p != sidecar and not (extension and p.is_relative_to(path.parent / extension))}
        assert actual == expected_paths, (label, sorted(str(p) for p in actual ^ expected_paths))
        results.append({"label": label, "manifest": name, "sha256": digest, "members": count,
            "bytes": size, "all_member_bytes_unchanged": True, "exact_membership": True,
            "only_authorized_extension_excluded": extension,
            "original_sealer_declared_metadata": None if not sidecar else {
                "path": str(sidecar.relative_to(ROOT)), **ident(read(sidecar)),
                "format": "exact bound manifest SHA256, two spaces, manifest.json and newline"}})
    return results

def capture():
    assert not (BASE / "custody.json").exists(), "capture is one-shot"
    priors = prior_closures()
    raw = read(UP / "manifest.json"); assert ident(raw)["sha256"] == EXPECTED
    manifest = json.loads(raw); assert manifest["members"] == len(manifest["files"]) == 23
    assert manifest["bytes"] == sum(v["bytes"] for v in manifest["files"].values()) == 630064
    snapshots = {}
    for name, expected in manifest["files"].items():
        assert not Path(name).is_absolute() and ".." not in Path(name).parts
        assert name == "docs/android-private-owner-effect-roster-amendment.md" or name.startswith(
            "verification/android-private-owner-effect-roster-amendment/")
        assert ident(read(ROOT / name)) == expected, name
        target = BASE / "candidate" / name
        snapshots[str(target.relative_to(BASE))] = copy(ROOT / name, target)
    target = BASE / "candidate/manifest.json"
    snapshots[str(target.relative_to(BASE))] = copy(UP / "manifest.json", target)
    admission = ROOT / "verification/android-private-owner-effect-integration-root-review/roster-amendment-admission.json"
    target = BASE / "root-admission.json"; snapshots[str(target.relative_to(BASE))] = copy(admission, target)
    assert json.loads(read(target))["manifest_sha256"] == EXPECTED
    sidecar_receipt = ROOT / "verification/android-private-owner-effect-integration-root-review/checksum-sidecar-bindings.json"
    target = BASE / "root-sidecar-bindings.json"
    snapshots[str(target.relative_to(BASE))] = copy(sidecar_receipt, target)
    for label, name, digest, count, size, relative, extension in SEALS:
        if label in SIDECARS:
            for child in ("handoff.sha256", "seal.py"):
                source = (ROOT / name).parent / child
                target = BASE / "sidecar-bindings" / label / child
                snapshots[str(target.relative_to(BASE))] = copy(source, target)
    old_path = ROOT / "verification/android-private-owner-effect-integration-proposal/correction-1/required-host-roster.json"
    old_raw = read(old_path); old = json.loads(old_raw); new = json.loads(read(UP / "required-host-roster.json"))
    assert read(UP / "inputs/verification/android-private-owner-effect-integration-proposal/correction-1/required-host-roster.json") == old_raw
    old_barriers = old["baseline_callback_barriers"]
    assert len(old_barriers) == 189 and len({v["id"] for v in old_barriers}) == 189
    v1 = [v for v in old_barriers if v["id"] in IDS]
    v2 = [v for v in old_barriers if v["id"] not in IDS]
    assert [v["id"] for v in v1] == IDS and len(v2) == 184
    assert new["baseline_callback_barriers"] == v2, "full ordered V2 records changed"
    assert set(new) == set(old) | {"amendment", "v1_compile_baseline_only"}
    unchanged_fields = [k for k in old if k != "baseline_callback_barriers"]
    for k in unchanged_fields: assert new[k] == old[k], k
    assert [v["id"] for v in new["v1_compile_baseline_only"]] == IDS
    v1_proof = []
    for historical, effective in zip(v1, new["v1_compile_baseline_only"]):
        anchors = {k: v for k, v in historical.items() if k != "required_cases"}
        assert {k: effective[k] for k in anchors} == anchors
        assert set(effective) == set(anchors) | {"classification", "active_required_cases", "V2_semantic_requirements", "historical_record_sha256"}
        assert effective["classification"] == "V1 compile/baseline-only"
        assert effective["active_required_cases"] == ["complete-source compilation", "positive unchanged V1 apply/children baseline"]
        assert effective["V2_semantic_requirements"] == []
        assert effective["historical_record_sha256"] == ident(canonical(historical))["sha256"]
        v1_proof.append({"id": historical["id"], "full_historical_record_sha256": ident(canonical(historical))["sha256"],
            "all_anchors_unchanged": True, "classification": effective["classification"], "no_active_V2_requirements": True})
    assert read(UP / "v2-semantic-barrier-ids.txt") == ("\n".join(v["id"] for v in v2) + "\n").encode()
    for entry in old_barriers:
        source = ROOT / "verification/android-private-owner-effect-integration-proposal/correction-1/inputs" / entry["source"]
        line = read(source).decode().splitlines()[entry["line"] - 1]
        assert line.strip() == entry["source_line"]
        assert line[entry["column"] - 1:].startswith(entry["expression"])
    closure = new["closures"]["B-concrete-renderer-views"]
    assert len(closure["actual_production_sources"]) == 14 and len(closure["substitutes"]) == 73
    assert len({v["fqcn"] for v in closure["substitutes"]}) == 73
    amendment = new["amendment"]
    assert amendment["classification_only_ids"] == IDS
    assert amendment["active_V2_semantic_count"] == 184 and amendment["V1_compile_baseline_count"] == 5
    assert amendment["universal_V2_wording_applies_only_to"] == "baseline_callback_barriers"
    assert amendment["prior_roster"] == ident(old_raw)
    proof = {"scope": "Independent exact byte and structured R1 comparison; not product tests.",
        "prior_roster_identity": ident(old_raw), "amended_roster_identity": ident(read(UP / "required-host-roster.json")),
        "V2_full_ordered_records_equal": True, "V2_count": 184,
        "V2_records": [{"id": x["id"], "full_record_sha256": ident(canonical(x))["sha256"], "all_seven_future_cases_unchanged": True} for x in v2],
        "V1_count": 5, "V1_records": v1_proof, "all_189_original_anchors_verified": True,
        "noninventory_fields_unchanged": unchanged_fields,
        "closure_B_actual_subjects": 14, "closure_B_substitutes": 73,
        "complete_closures_unchanged": old["closures"] == new["closures"],
        "product_tests_run": False, "producer_helpers_executed": False}
    (BASE / "independent-classification.json").write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    cmds = [command(["git", "rev-parse", "HEAD"]), command(["git", "rev-parse", "HEAD^{tree}"]), command(["git", "--version"])]
    py = Path(sys.executable).resolve(); git = Path(shutil.which("git")).resolve()
    receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [str(py), "-B", str(Path(__file__).resolve()), "capture"], "commands": cmds,
        "context_revision": cmds[0]["stdout"].strip(), "context_tree": cmds[1]["stdout"].strip(),
        "tools": {"python": {"path": str(py), "version": sys.version, **ident(read(py))},
                  "git": {"path": str(git), "version": cmds[2]["stdout"].strip(), **ident(read(git))}},
        "candidate_manifest_sha256": EXPECTED, "candidate_members": 23, "candidate_bytes": 630064,
        "snapshots": snapshots, "prior_seals": priors,
        "scope": "Independent narrow R1 source-contract review authorized by root; no optional expansion.",
        "product_tests_run": False, "producer_helpers_executed": False,
        "prior_members_product_profile_CI_metadata_or_commit_changes": False,
        "native_runtime_UI_capture_process_discovery_hosted_harness_network_install_signing_credentials_publication": False,
        "cleanup": "No runtime/capture/scratch resources created; other project processes unchanged."}
    (BASE / "custody.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": "independent-R1-custody-and-classification-pass", "candidate_members": 23,
        "candidate_bytes": 630064, "unchanged_V2_records": 184, "classified_V1_records": 5,
        "prior_closed_packets": 5, "actual_B_subjects": 14, "B_substitutes": 73, "product_tests_run": False}))

def check():
    prior_closures()
    receipt = json.loads(read(BASE / "custody.json"))
    assert ident(read(UP / "manifest.json"))["sha256"] == EXPECTED
    for name, expected in receipt["snapshots"].items(): assert ident(read(BASE / name)) == expected, name
    for name, expected in json.loads(read(UP / "manifest.json"))["files"].items():
        assert ident(read(ROOT / name)) == expected, name
    print(json.dumps({"status": "independent-R1-frozen-custody-pass", "prior_closed_packets": 5,
                      "candidate_members": 23, "product_tests_run": False}))

if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in ("capture", "check")
    {"capture": capture, "check": check}[sys.argv[1]]()
