#!/usr/bin/env python3
"""Bounded custody and exact five-ID roster classification, with no product execution."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
PRIOR = ROOT / "verification/android-private-owner-effect-integration-proposal/correction-1"
ROSTER = PRIOR / "required-host-roster.json"
SOURCE = "native/android/app/src/dev/mixer/android/NativeRenderer.java"
DOC = "docs/android-private-owner-effect-roster-amendment.md"
V1_IDS = {
    "NativeRenderer:L60:C234:1", "NativeRenderer:L61:C242:1",
    "NativeRenderer:L62:C149:1", "NativeRenderer:L62:C454:2", "NativeRenderer:L62:C509:3",
}
SEALS = [
    ("original-proposal", "verification/android-private-owner-effect-integration-proposal/manifest.json", "7547220cc7f1ba6648ca2cbb3fdf96e402b5b3af9abf68906263be57688838a7", False),
    ("original-review", "verification/android-private-owner-effect-contract-review/manifest.json", "8f84a627384e42a5695a52b266f420cb4a26e7c670982266432a022ef1071d58", False),
    ("preaccess-plan", "verification/android-private-owner-effect-contract-review/correction-1/preaccess/manifest.json", "638028e6531f4846d5d68e8979b24a0742d243207e54d184addc14bd2246923c", True),
    ("correction-1", "verification/android-private-owner-effect-integration-proposal/correction-1/manifest.json", "1479c098f5721cc80e0c82f8699d1482a30f71ad241fa06cfe2c6902255bec08", False),
    ("final-correction-review", "verification/android-private-owner-effect-contract-review/correction-1/review/manifest.json", "d6016514ce21f48a537395fbf2d142e6e75489b62d23c5be91266212cb0d0616", False),
]


def ident(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def write(name, value):
    (BASE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def copy_input(name, data):
    target = BASE / "inputs" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def main():
    assert not (BASE / "receipt.json").exists(), "do not replace captured boundary"
    seals = []
    for label, name, expected_hash, relative in SEALS:
        path = ROOT / name
        data = path.read_bytes()
        assert ident(data)["sha256"] == expected_hash, name
        manifest = json.loads(data)
        member_base = path.parent if relative else ROOT
        for member, expected in manifest["files"].items():
            p = member_base / member
            assert p.is_file() and not p.is_symlink() and ident(p.read_bytes()) == expected, member
        copy_input("seals/" + label + ".json", data)
        seals.append({"label": label, "path": name, **ident(data),
                      "member_paths_relative_to_manifest": relative,
                      "members_verified": len(manifest["files"]),
                      "bytes_verified": sum(v["bytes"] for v in manifest["files"].values())})
    inputs = {}
    for name in [str(ROSTER.relative_to(ROOT)), SOURCE,
                 "docs/android-private-owner-effect-integration-correction.md",
                 "docs/android-private-owner-effect-contract-correction-review.md"]:
        data = (ROOT / name).read_bytes()
        copy_input(name, data)
        inputs[name] = ident(data)
    source = (ROOT / SOURCE).read_bytes()
    prior_source = (PRIOR / "inputs" / SOURCE).read_bytes()
    assert source == prior_source, "actual renderer differs from frozen correction source"
    before = json.loads(ROSTER.read_text())
    assert len(before["baseline_callback_barriers"]) == 189
    assert len({r["id"] for r in before["baseline_callback_barriers"]}) == 189
    old = {r["id"]: r for r in before["baseline_callback_barriers"]}
    assert V1_IDS <= old.keys()
    after = {k: v for k, v in before.items() if k != "baseline_callback_barriers"}
    after["baseline_callback_barriers"] = [r for r in before["baseline_callback_barriers"] if r["id"] not in V1_IDS]
    after["v1_compile_baseline_only"] = []
    for r in before["baseline_callback_barriers"]:
        if r["id"] in V1_IDS:
            anchor = {k: v for k, v in r.items() if k != "required_cases"}
            after["v1_compile_baseline_only"].append({
                **anchor, "classification": "V1 compile/baseline-only",
                "active_required_cases": ["complete-source compilation", "positive unchanged V1 apply/children baseline"],
                "V2_semantic_requirements": [], "historical_record_sha256": ident(canonical(r))["sha256"]})
    after["amendment"] = {
        "id": "R1-roster-amendment-1", "classification_only_ids": sorted(V1_IDS),
        "prior_roster": inputs[str(ROSTER.relative_to(ROOT))], "historical_inventory_count": 189,
        "active_V2_semantic_count": 184, "V1_compile_baseline_count": 5,
        "universal_V2_wording_applies_only_to": "baseline_callback_barriers",
        "new_calls_in_selected_V2_regions_remain_mandatory": True,
        "C1_C2_focus_cancellation_terminal_authority_unchanged": True,
        "product_checks_executed": False,
    }
    assert len(after["baseline_callback_barriers"]) == 184
    write("required-host-roster.json", after)
    (BASE / "v2-semantic-barrier-ids.txt").write_text("".join(r["id"] + "\n" for r in after["baseline_callback_barriers"]))
    proof = {
        "schema": 1, "scope": "classification-only-no-product-tests", "classified_V1_ids": sorted(V1_IDS),
        "unchanged_V2_records": [{"id": r["id"], "prior_sha256": ident(canonical(old[r["id"]]))["sha256"],
                                  "amended_sha256": ident(canonical(r))["sha256"], "full_record_equal": old[r["id"]] == r}
                                 for r in after["baseline_callback_barriers"]],
        "V1_anchor_records": [{"id": r["id"], "anchor_equal": {k: old[r["id"]][k] for k in old[r["id"]] if k != "required_cases"} ==
                               {k: r[k] for k in old[r["id"]] if k != "required_cases"},
                               "historical_record_sha256": r["historical_record_sha256"]}
                              for r in after["v1_compile_baseline_only"]],
        "prior_noninventory_fields_sha256": ident(canonical({k: v for k, v in before.items() if k != "baseline_callback_barriers"}))["sha256"],
        "amended_noninventory_preexisting_fields_sha256": ident(canonical({k: after[k] for k in before if k != "baseline_callback_barriers"}))["sha256"],
        "closure_B_sha256": ident(canonical(before["closures"]["B-concrete-renderer-views"]))["sha256"],
    }
    write("classification-proof.json", proof)
    commands = []
    for argv in [["git", "rev-parse", "HEAD"], ["git", "rev-parse", "HEAD^{tree}"], ["git", "--version"]]:
        r = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=10)
        commands.append({"argv": argv, "cwd": str(ROOT), "timeout_seconds": 10, "exit_code": r.returncode,
                         "stdout": r.stdout.decode(), "stderr": r.stderr.decode()})
        assert r.returncode == 0, commands[-1]
    tools = {}
    for name, location in [("python", sys.executable), ("git", shutil.which("git"))]:
        path = Path(location).resolve(strict=True)
        tools[name] = {"path": str(path), **ident(path.read_bytes())}
    tools["python"]["version"] = sys.version
    tools["git"]["version"] = commands[2]["stdout"].strip()
    receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "status": "source-only-R1-roster-amendment-awaiting-independent-review",
               "command": [sys.executable, "-B", str(Path(__file__).resolve())],
               "context_revision": commands[0]["stdout"].strip(), "context_tree": commands[1]["stdout"].strip(),
               "commands": commands, "tools": tools, "prior_seals": seals, "inputs": inputs,
               "amendment_document": {"path": DOC, **ident((ROOT / DOC).read_bytes())},
               "amended_roster": ident((BASE / "required-host-roster.json").read_bytes()),
               "scope": "Only five exact V1 IDs removed from active V2 semantic matrix; all other fields/anchors/requirements preserved.",
               "actual_closure_B_subjects": 14, "closure_B_substitutes": 73,
               "V2_semantic_barriers": 184, "V1_compile_baseline_only": 5,
               "product_tests_run": False, "native_or_cross_compile_run": False,
               "product_source_profile_CI_root_metadata_edits": False, "prior_member_or_verifier_edits": False,
               "network_process_UI_capture_hosted_signing_credentials_publication": False,
               "commit_or_push": False, "new_dependencies": [], "implementation_selected": False,
               "implementation_or_native_OTA_GA_acceptance": False}
    write("receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "V2_semantic_barriers": 184, "V1_compile_baseline_only": 5,
                      "prior_seals_verified": len(seals), "closure_B_subjects": 14, "closure_B_substitutes": 73,
                      "product_tests_run": False}, sort_keys=True))


if __name__ == "__main__":
    main()
