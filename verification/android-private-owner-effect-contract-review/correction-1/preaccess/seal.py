#!/usr/bin/env python3
"""Freeze preaccess obligations. This helper never opens correction candidates."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ORIGINAL = BASE.parents[1]
ROOT = BASE.parents[3]
DOC = ROOT / "docs/android-private-owner-effect-contract-correction-review.md"
ORIGINAL_SEAL = "8f84a627384e42a5695a52b266f420cb4a26e7c670982266432a022ef1071d58"

def identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def read(path):
    assert path.is_file() and not path.is_symlink(), str(path)
    return path.read_bytes()

def original():
    raw = read(ORIGINAL / "manifest.json")
    assert identity(raw)["sha256"] == ORIGINAL_SEAL
    manifest = json.loads(raw)
    assert manifest["members"] == 77 and manifest["bytes"] == 1426839
    for name, expected in manifest["files"].items():
        assert identity(read(ROOT / name)) == expected, name
    return manifest

def command(argv):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=15, check=False)
    assert result.returncode == 0, (argv, result.stderr)
    return {"argv": argv, "cwd": str(ROOT), "exit_code": result.returncode,
            "stdout": result.stdout.decode(), "stderr": result.stderr.decode()}

def capture():
    assert not (BASE / "manifest.json").exists(), "preaccess capture is one-shot"
    upstream = original()
    document = read(DOC)
    (BASE / "review-plan.md").write_bytes(document)
    obligations = []
    for line in document.decode().splitlines():
        if line.startswith("| C") or line.startswith("| P"):
            parts = line.split("|")
            code = parts[1].strip()
            if code[0] in "CP" and code[1].isdigit():
                obligations.append({"id": code, "obligation": parts[2].strip()})
    assert len(obligations) == 28
    assert len({v["id"] for v in obligations}) == 28
    plan = {"schema": 1, "status": "preaccess-plan-frozen-awaiting-root-candidate-seal",
        "candidate_access_authorized": False, "candidate_opened_or_hashed": False,
        "obligations": obligations,
        "phases": ["wait for root exact frozen seal and access authorization",
                   "independent finite manifest custody check and input snapshots",
                   "read exact corrected contract and map every obligation to lines",
                   "check preserved contract and scope boundaries",
                   "selection-ready-contract or needs-contract-correction report"],
        "possible_outcomes": ["selection-ready-contract", "needs-contract-correction"],
        "not_outcomes": ["implementation acceptance", "native acceptance", "OTA authorization", "GA qualification"],
        "product_tests_or_candidate_helpers_allowed": False,
        "hosted_harness_or_hosted_code_read_import_execute_allowed": False,
        "native_runtime_UI_capture_phones_allowed": False,
        "implementation_profile_metadata_CI_commit_changes_allowed": False,
        "review_document_snapshot": identity(document)}
    (BASE / "plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    commands = [command(["git", "rev-parse", "HEAD"]),
                command(["git", "rev-parse", "HEAD^{tree}"]),
                command(["git", "--version"])]
    py = Path(sys.executable).resolve()
    git = Path(shutil.which("git")).resolve()
    prior_custody = json.loads(read(ORIGINAL / "custody.json"))
    receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": [str(py), "-B", str(Path(__file__).resolve()), "capture"],
        "commands": commands, "context_revision": commands[0]["stdout"].strip(),
        "context_tree": commands[1]["stdout"].strip(),
        "tools": {"python": {"path": str(py), "version": sys.version, **identity(read(py))},
                  "git": {"path": str(git), "version": commands[2]["stdout"].strip(), **identity(read(git))}},
        "original_review_manifest_sha256": ORIGINAL_SEAL,
        "original_members_verified": 77, "original_bytes_verified": 1426839,
        "original_member_identities": upstream["files"],
        "original_proposal_manifest_sha256": prior_custody["proposal_manifest_sha256"],
        "observer_acceptance_sha256": prior_custody["observer_acceptance_sha256"],
        "accepted_core_sha256": "4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6",
        "candidate_files_accessed": [], "candidate_access_authorized": False,
        "product_tests_run": False, "product_metadata_CI_or_original_member_edits": False,
        "hosted_harnesses_or_hosted_code_accessed": False,
        "native_runtime_UI_capture_process_discovery_network_install_signing_credentials_publication": False,
        "cleanup": "No runtime, capture or scratch resources created; other projects unchanged.",
        "scope": "Independent preaccess source-contract review plan only."}
    (BASE / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    files = {str(p.relative_to(BASE)): identity(read(p)) for p in sorted(BASE.iterdir())
             if p.is_file() and p.name != "manifest.json"}
    manifest = {"schema": 1, "members": len(files), "bytes": sum(v["bytes"] for v in files.values()), "files": files}
    (BASE / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": plan["status"], "obligations": len(obligations),
                      "members": manifest["members"], "bytes": manifest["bytes"],
                      "manifest_sha256": identity(read(BASE / "manifest.json"))["sha256"]}))

def check():
    original()
    manifest = json.loads(read(BASE / "manifest.json"))
    assert {p.name for p in BASE.iterdir() if p.is_file() and p.name != "manifest.json"} == set(manifest["files"])
    for name, expected in manifest["files"].items():
        assert identity(read(BASE / name)) == expected, name
    assert manifest["members"] == len(manifest["files"])
    assert manifest["bytes"] == sum(v["bytes"] for v in manifest["files"].values())
    print(json.dumps({"status": "preaccess-plan-and-original-members-pass", "members": manifest["members"],
                      "bytes": manifest["bytes"], "original_members": 77,
                      "candidate_accessed": False,
                      "manifest_sha256": identity(read(BASE / "manifest.json"))["sha256"]}))

if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in ("capture", "check")
    {"capture": capture, "check": check}[sys.argv[1]]()
