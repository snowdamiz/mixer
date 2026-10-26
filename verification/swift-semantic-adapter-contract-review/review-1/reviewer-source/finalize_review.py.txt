#!/usr/bin/env python3
"""Seal independent source-contract findings without executing candidate code."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OWNED = ROOT / "verification/swift-semantic-adapter-contract-review"
REVIEW = OWNED / "review-1"
CANDIDATE = OWNED / "candidate-1"
EXPECTED = "d145cda8cdde0915493f5c75102ae0dc11adb577891b1b773322b5c4d0f32cba"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main():
    if (REVIEW / "seal.json").exists():
        raise SystemExit("refuse to replace frozen findings")
    source_manifest = []
    for name, folder, seal_name, original_prefix in (
        ("preaccess", OWNED / "preaccess", "seal.json", None),
        ("candidate", CANDIDATE, "seal.json", CANDIDATE / "members"),
    ):
        raw = (folder / seal_name).read_bytes()
        seal = json.loads(raw)
        if name == "candidate" and sha(raw) != EXPECTED:
            raise SystemExit("candidate seal mismatch")
        for item in seal["members"]:
            member = (original_prefix or folder) / item["path"]
            data = member.read_bytes()
            if len(data) != item["bytes"] or sha(data) != item["sha256"]:
                raise SystemExit(f"frozen member changed: {member}")
            if name == "candidate" and data != (ROOT / item["path"]).read_bytes():
                raise SystemExit(f"producer member changed: {item['path']}")
        source_manifest.append({"input": name, "seal_sha256": sha(raw),
                                "members_verified": len(seal["members"]),
                                "seal_path": str((folder / seal_name).relative_to(ROOT))})
        shutil.copyfile(folder / seal_name, REVIEW / f"{name}-seal.json")
    if sha((ROOT / "verification/swift-semantic-adapter-prerequisite/seal.json").read_bytes()) != EXPECTED:
        raise SystemExit("producer seal changed")
    shutil.copyfile(ROOT / "docs/swift-semantic-adapter-contract-review.md", REVIEW / "reviewed-document.md")
    scripts = ("prepare_preaccess.py", "verify_preaccess.py", "snapshot_candidate.py",
               "audit_source_contract.py", "finalize_review.py")
    for script in scripts:
        destination = REVIEW / "reviewer-source" / (script + ".txt")
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(OWNED / script, destination)
    checked = []
    paths = ["docs/swift-semantic-adapter-contract-review.md"]
    paths.extend(str((OWNED / script).relative_to(ROOT)) for script in scripts)
    paths.extend(str(path.relative_to(ROOT)) for path in (REVIEW / "review.md", REVIEW / "findings.json"))
    for index, relative in enumerate(paths):
        argv = ["git", "diff", "--no-index", "--check", "/dev/null", relative]
        completed = subprocess.run(argv, cwd=ROOT, capture_output=True, check=False)
        (REVIEW / f"whitespace-{index:02d}.stdout").write_bytes(completed.stdout)
        (REVIEW / f"whitespace-{index:02d}.stderr").write_bytes(completed.stderr)
        if completed.returncode not in (0, 1) or completed.stdout or completed.stderr:
            raise SystemExit(f"whitespace refusal: {relative}")
        checked.append({"argv": argv, "exit_code": completed.returncode,
                        "stdout": f"whitespace-{index:02d}.stdout", "stderr": f"whitespace-{index:02d}.stderr"})
    audit = json.loads((REVIEW / "audit.json").read_bytes())
    findings = json.loads((REVIEW / "findings.json").read_bytes())
    write_json(REVIEW / "source-inputs.json", source_manifest)
    write_json(REVIEW / "final-receipt.json", {
        "schema": 1, "at_utc": datetime.now(timezone.utc).isoformat(),
        "command": "python3 verification/swift-semantic-adapter-contract-review/finalize_review.py",
        "source_revision": (REVIEW / "revision.stdout").read_text().strip(),
        "candidate_seal_sha256": EXPECTED,
        "preaccess_seal_sha256": "7ae911b982f2bf96f596969c2c282bd5bbdd7302033a6d1404278f1df23d9ae9",
        "reviewed_document_sha256": sha((REVIEW / "reviewed-document.md").read_bytes()),
        "verdict": findings["verdict"], "blocking_contract_findings": ["R1"],
        "implementation_selected": False, "compiler_executed": False,
        "semantic_runtime_tests_executed": 0, "producer_helpers_imported_or_executed": False,
        "source_excerpt_identities_verified": len(audit["source_excerpt_checks"]),
        "design_source_identities_verified": len(audit["copied_design_seal_source_matches"]),
        "accepted_library_source_matches": len(audit["accepted_source_byte_matches"]),
        "exact_work_and_memory_implementation_proof": "pending; arithmetic declarations only",
        "current_live_VM_authority": "unavailable; not read or claimed",
        "root_reported_CI_context": "40273904826 Swift unfinished; actual Rust1.98.1 envelope unqualified; prior Android40272428143 cancelled after30-minute timeout with macOS capacity notice and logs unavailable",
        "CI_context_independently_verified_here": False,
        "whitespace_commands": checked,
        "native_capture_processes_started_or_queried": False,
        "cleanup": "No build scratch, native/capture process or disposable instance created; synchronous read-only children reaped.",
        "pending": ["R1 separately frozen amendment and independent review", "root implementation selection", "future independent full-field/transition/terminal runtime proof", "exact Rust source/move/lifetime/debit/layout proof", "all real authority/live VM/target/native/release/GA gates"],
    })
    members = []
    for path in sorted(REVIEW.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            members.append({"path": str(path.relative_to(REVIEW)), "bytes": len(data), "sha256": sha(data)})
    write_json(REVIEW / "seal.json", {
        "schema": 1, "scope": "first independent source-contract findings; no runtime/implementation acceptance",
        "excluded": ["seal.json", "seal.sha256"], "members": members,
        "member_count": len(members), "member_bytes": sum(item["bytes"] for item in members),
        "candidate_seal_sha256": EXPECTED,
        "preaccess_seal_sha256": "7ae911b982f2bf96f596969c2c282bd5bbdd7302033a6d1404278f1df23d9ae9",
    })
    seal_hash = sha((REVIEW / "seal.json").read_bytes())
    (REVIEW / "seal.sha256").write_text(f"{seal_hash}  seal.json\n")
    # Re-read every final sealed member before reporting its identity.
    for item in members:
        data = (REVIEW / item["path"]).read_bytes()
        if sha(data) != item["sha256"] or len(data) != item["bytes"]:
            raise SystemExit("final review member changed")
    print(json.dumps({"seal_sha256": seal_hash, "members": len(members),
                      "bytes": sum(item["bytes"] for item in members),
                      "blocking_findings": ["R1"], "semantic_tests_executed": 0,
                      "candidate_originals_unchanged": True}, sort_keys=True))


if __name__ == "__main__":
    main()
