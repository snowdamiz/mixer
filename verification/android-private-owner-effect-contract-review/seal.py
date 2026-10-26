#!/usr/bin/env python3
"""Seal/check this bounded source-review packet, without executing product code."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
DOC = ROOT / "docs/android-private-owner-effect-contract-review.md"

def ident(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

def check_stream(name, status):
    assert (BASE / f"{name}.stderr").read_bytes() == b""
    output = json.loads((BASE / f"{name}.stdout").read_text())
    assert output["status"] == status

def seal():
    check_stream("capture", "source-custody-pass")
    check_stream("check", "frozen-custody-pass")
    check_stream("inspect", "source-inventory-pass")
    for name in ("custody.py", "inspect_sources.py", "seal.py"):
        ast.parse((BASE / name).read_text(), filename=name)
    for path in [DOC, BASE / "README.md"]:
        assert all(line == line.rstrip() for line in path.read_text().splitlines())
    custody = json.loads((BASE / "custody.json").read_text())
    report = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "needs-contract-correction-before-implementation-selection",
        "context_revision": custody["context_revision"], "context_tree": custody["context_tree"],
        "proposal_manifest_sha256": custody["proposal_manifest_sha256"],
        "observer_acceptance_sha256": custody["observer_acceptance_sha256"],
        "findings": [
            {"id": "C1", "selection_correction_required": True,
             "summary": "Missing owner-to-coordinator callback-capable input cancellation bridge",
             "minimum": "Explicit active-operation-safe cancellation entry, scalar-first ordering, bounded reentry guard, independent attempt/fatal outcomes; no disposal."},
            {"id": "C2", "selection_correction_required": True,
             "summary": "Missing exact-bound terminal report route for renderer self-retirement",
             "minimum": "One terminal notification route with exact renderer identity/cause, scalar-first sealing, unchanged core close fallback and independent cleanup; outside successful commit/finish."},
            {"id": "C3", "selection_correction_required": True,
             "summary": "Concrete renderer compile alternative cannot prove required behavior",
             "minimum": "Mandatory executable selected renderer/native-view closure and exact callback seam/leaf roster, including construction and override reentry; native platform proof remains pending."}],
        "additional_entry_mapping_clarification": "Actual focus must reach core.focusChanged; WindowFacts has no focus field. Distinguish transaction operation guards from valid ordinary native callback presentation guards.",
        "source_only_checks": [
            {"script": "custody.py", "mode": "capture", "exit_code": 0, "stdout": "capture.stdout", "stderr": "capture.stderr"},
            {"script": "custody.py", "mode": "check", "exit_code": 0, "stdout": "check.stdout", "stderr": "check.stderr"},
            {"script": "inspect_sources.py", "exit_code": 0, "stdout": "inspect.stdout", "stderr": "inspect.stderr"}],
        "commands": [[str(Path(sys.executable).resolve()), "-B", str(BASE / "custody.py"), "capture"],
                     [str(Path(sys.executable).resolve()), "-B", str(BASE / "custody.py"), "check"],
                     [str(Path(sys.executable).resolve()), "-B", str(BASE / "inspect_sources.py")],
                     [str(Path(sys.executable).resolve()), "-B", str(Path(__file__).resolve()), "seal"]],
        "validation": "Three source-only custody/inventory commands passed; review script ASTs and owned Markdown trailing whitespace checked.",
        "producer_checker_executed": False, "product_tests_run": False,
        "implementation_selected": False, "implementation_accepted": False,
        "cross_compilation_run": False, "native_runtime_started": False,
        "computer_use_or_capture": False, "process_discovery": False,
        "network_install_signing_credentials_publication": False,
        "product_profile_metadata_or_original_proposal_edits": False,
        "OTA_authorization": False, "GA_qualified": False,
        "pending": ["versioned contract correction and root selection", "selected actual implementation host/cross-compile/independent verification", "native runtime under active pause", "disconnected physical phones and final device/accessibility/performance matrix", "separate-repository immutable published FieldLog", "signing/store/operational/accountable GA"],
        "cleanup": "No scratch/native/capture resources created; no cleanup or other-project process changes required.",
        "review_document": str(DOC.relative_to(ROOT)), "review_document_identity": ident(DOC.read_bytes())}
    (BASE / "review-result.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    paths = [DOC, *[p for p in sorted(BASE.rglob("*")) if p.is_file() and p != BASE / "manifest.json"]]
    assert all(not p.is_symlink() for p in paths)
    files = {str(p.relative_to(ROOT)): ident(p.read_bytes()) for p in paths}
    manifest = {"schema": 1, "scope": "Independent source-only contract review; no product tests or implementation acceptance.",
        "files": files, "members": len(files), "bytes": sum(v["bytes"] for v in files.values())}
    (BASE / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": report["status"], "members": manifest["members"],
                      "bytes": manifest["bytes"], "manifest_sha256": ident((BASE / "manifest.json").read_bytes())["sha256"]}))

def check():
    manifest = json.loads((BASE / "manifest.json").read_text())
    actual = {str(p.relative_to(ROOT)) for p in BASE.rglob("*") if p.is_file() and p != BASE / "manifest.json"}
    actual.add(str(DOC.relative_to(ROOT)))
    assert actual == set(manifest["files"]), "review packet membership changed"
    for name, expected in manifest["files"].items():
        path = ROOT / name
        assert not path.is_symlink() and ident(path.read_bytes()) == expected, name
    assert manifest["members"] == len(manifest["files"])
    assert manifest["bytes"] == sum(v["bytes"] for v in manifest["files"].values())
    print(json.dumps({"status": "independent-review-seal-pass", "members": manifest["members"],
                      "bytes": manifest["bytes"], "manifest_sha256": ident((BASE / "manifest.json").read_bytes())["sha256"]}))

if __name__ == "__main__":
    assert len(sys.argv) == 2 and sys.argv[1] in ("seal", "check")
    {"seal": seal, "check": check}[sys.argv[1]]()
