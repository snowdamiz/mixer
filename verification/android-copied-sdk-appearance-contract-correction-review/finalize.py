#!/usr/bin/env python3
"""Freeze this correction review only; old review/producer bytes are read-only."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import platform
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOC = ROOT / "docs/android-copied-sdk-appearance-contract-correction-review.md"


def identity(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


pin = json.loads((HERE / "pin-report.json").read_text())
producer = HERE / "inputs/verification/android-copied-sdk-appearance-contract-correction/seal.json"
assert identity(producer)["sha256"] == pin["producer_seal_sha256"]
sealed = json.loads(producer.read_text())
assert len(sealed["files"]) == 140
assert sum(x["bytes"] for x in sealed["files"].values()) == 752291
for relative, expected in sealed["files"].items():
    assert identity(HERE / "inputs" / relative) == expected, relative
    assert identity(ROOT / relative) == expected, relative
offline = json.loads((HERE / "offline-verification.json").read_text())
probe = json.loads((HERE / "filesystem-probe.json").read_text())
assert probe["checks_passed"] and probe["cleanup"]["scratch_absent"]
assert not (HERE / "owned-filesystem-scratch").exists()
for path in [DOC, *HERE.glob("*.py")]:
    text = path.read_text()
    assert text.endswith("\n") and all(line == line.rstrip() for line in text.splitlines()), path
    if path.suffix == ".py":
        ast.parse(text, filename=str(path))
check_argv = ["git", "diff", "--check", "--", str(DOC.relative_to(ROOT)), str(HERE.relative_to(ROOT))]
check = subprocess.run(check_argv, cwd=ROOT, capture_output=True)
(HERE / "diff-check.stdout").write_bytes(check.stdout)
(HERE / "diff-check.stderr").write_bytes(check.stderr)
assert check.returncode == 0
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
amendment = {
    "id": "R1-root-ascii",
    "requirement": "Reject every non-ASCII SDK-root entry as enumerated before name transformation, selector classification, following/opening entries, copying or generic hashing; then apply ASCII case-insensitive Package* namespace with only exact ordinary pinned Package.swift.",
    "entrypoints": ["create input SDK", "actual staged/generated SDK", "common Swift project preflight", "rendered Python build preflight", "linked-SDK consistency checks"],
    "observable_scope": "Rejects unrelated Unicode SDK-root names too; does not recursively impose ASCII on excluded inner trees.",
    "executable_followup": "Kelvin-sign base/selector and unrelated-Unicode fixtures through create, common verifyLock and rendered direct driver with recomputed local locks and preaccess/tool/output sentinels.",
}
commands = []
for script, prefix in [("filesystem_probe.py", "filesystem-probe"), ("offline_verify.py", "offline-verification")]:
    commands.append({"argv": ["python3", "-B", str((HERE / script).relative_to(ROOT))],
                     "cwd": str(ROOT), "exit_code": 0,
                     "stdout": identity(HERE / (prefix + ".stdout")),
                     "stderr": identity(HERE / (prefix + ".stderr"))})
commands.append(offline["command"])
commands.append({"argv": check_argv, "cwd": str(ROOT), "exit_code": check.returncode,
                 "stdout": identity(HERE / "diff-check.stdout"), "stderr": identity(HERE / "diff-check.stderr")})
commands.append({"argv": ["python3", "-B", str((HERE / "finalize.py").relative_to(ROOT))],
                 "cwd": str(ROOT), "scope": "Own frozen input validation, source text/AST checks and correction review seal."})
(HERE / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
receipt = {
    "schema": 1, "at": now,
    "status": "recommend-root-selection-of-correction-plus-explicit-ascii-root-amendment",
    "source_revision": pin["source_revision"], "proposal_sha256": pin["proposal_sha256"],
    "producer_seal_sha256": pin["producer_seal_sha256"],
    "producer_members_verified": 140, "producer_bytes_verified": 752291,
    "all_producer_input_copies_and_live_members_equal": True,
    "previous_seals_verified_unchanged": offline["seals_verified_unchanged"],
    "source_files_independently_equal_to_accepted_git": offline["source_files_equal_to_accepted_git"],
    "all42_source_profile_files_equal_to_previous_review": True,
    "R1": {"status": "selection-supported-only-with-explicit-amendment", "amendment": amendment,
           "filesystem_probe": "filesystem-probe.json", "compiler_reexecuted": False},
    "R2": {"status": "contract-level-addressed-implementation-tests-pending",
           "implementation_precision": "Android required when requested operation is Android OR configuration.targets includes Android OR an Android lock exists; missing-lock host/iOS/export cases must reject under existing required-context semantics."},
    "R3": {"status": "contract-level-addressed-implementation-tests-pending",
           "selected_candidate_design": "Raw import/inspect avoid profile decode; one rendered hex literal decoded only at build admission."},
    "commands": "commands.json", "tools": {"python": platform.python_version(),
        "git": subprocess.check_output(["git", "--version"], text=True).strip(), "platform": platform.platform()},
    "checks": ["140-member immutable correction copy integrity", "all old87/156 and correction140 live seal members unchanged",
               "51 named source blobs independently bound to accepted Git", "42 unchanged source-pair identities and both projection digests",
               "six inert filesystem cases including observed Kelvin aliases", "own Markdown/Python whitespace/newline and Python AST checks", "scoped git diff check"],
    "exploratory_failure": "exploratory-lookup-failure.json; a read-only source-inputs path lookup was corrected to accepted-source.",
    "cleanup": "Owned inert filesystem scratch removed; source fixtures are represented by exact inert payload hashes/names in probe JSON. No owned background/native/capture process started.",
    "implementation_selected": False, "implementation_accepted": False, "GA_qualified": False,
    "product_files_changed": False, "compiler_or_manifest_evaluation_executed": False,
    "producer_harness_or_product_code_imported_or_executed": False, "process_discovery": False,
    "native_runtime_or_capture_started": False, "whole_build_or_APK_created": False,
    "committed_or_pushed": False,
    "pending": ["Explicit root selection including conservative Unicode-root and legacy Android restrictions",
                "Bounded implementation and Debug/Release source/entrypoint/rendered driver/alias/cleanup tests",
                "Fresh copied-consumer Swift session/default and pure Java API/wire tests",
                "Native ABI/runtime/public V2/OS/lifecycle/rendering and physical acceptance",
                "Immutable signed CLI/SDK distribution, separate-repository FieldLog and OTA/store/operations/GA"],
    "scope": "Independent frozen contract review and host filesystem/source-data evidence only; not admission implementation or ABI/public V2/authenticity acceptance.",
}
(HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
handoff = {"schema": 1, "at": now, "status": receipt["status"],
           "review_doc": {"path": str(DOC.relative_to(ROOT)), **identity(DOC)},
           "receipt": {"path": str((HERE / "receipt.json").relative_to(ROOT)), **identity(HERE / "receipt.json")},
           "proposal_sha256": pin["proposal_sha256"], "producer_seal_sha256": pin["producer_seal_sha256"],
           "required_root_amendment": amendment, "R2_R3_contract_level_addressed": True,
           "implementation_selected": False, "implementation_accepted": False, "GA_qualified": False,
           "native_runtime_or_capture_started": False}
(HERE / "handoff.json").write_text(json.dumps(handoff, indent=2) + "\n")
files = {str(DOC.relative_to(ROOT)): identity(DOC)}
for path in sorted(HERE.rglob("*")):
    if path.is_file() and path != HERE / "seal.json":
        assert not path.is_symlink()
        files[str(path.relative_to(ROOT))] = identity(path)
output = {"schema": "mixer.independent-correction-review.seal.v1", "files": files,
          "files_map_sha256": hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
          "scope": "Exact owned review members; only this self-referential seal excluded. Previous review and producers remain unchanged."}
(HERE / "seal.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
print(json.dumps({"status": receipt["status"], "review_doc": identity(DOC),
                  "seal": identity(HERE / "seal.json"), "members": len(files),
                  "bytes": sum(x["bytes"] for x in files.values())}, indent=2))
