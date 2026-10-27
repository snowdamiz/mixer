"""Record and seal bounded independent host evidence; no candidate execution."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

producer = json.loads((ROOT / "replay/test-results.json").read_bytes())
independent = json.loads((ROOT / "independent-results.json").read_bytes())
assert (producer["methods"], producer["failures"], producer["errors"], producer["skips"]) == (26, 0, 0, 0)
assert (independent["methods"], independent["failures"], independent["errors"], independent["skips"]) == (9, 3, 0, 0)
assert not list((ROOT / "replay/owned-scratch").iterdir())
assert not any(independent[key] for key in ("owned_fds_final", "stdio_fds_final", "quarantines_final", "owned_scratch_entries_final"))
python = Path(os.path.realpath(sys.executable))
commands = [
    {"argv": ["python3", "verification/swift-retained-profile-composition-independent/verify_custody.py"], "exit_code": 1, "output": "initial-custody-failure.stderr", "scope": "initial exact filesystem closure before exact sidecar selection"},
    {"argv": ["python3", "verification/swift-retained-profile-composition-independent/verify_custody.py"], "exit_code": 0, "stdout": "custody.stdout", "stderr": "custody.stderr", "scope": "corrected root-selected exact metadata closure"},
    {"argv": ["python3", "-B", "verification/swift-retained-profile-composition-independent/prepare_replay.py"], "exit_code": 0, "stdout": "source-custody.stdout", "stderr": "source-custody.stderr"},
    {"argv": ["python3", "-B", "test_preparation.py"], "cwd": "replay", "exit_code": 0, "stdout": "producer-replay.stdout", "stderr": "producer-replay.stderr", "observed_unittest_seconds": 0.679},
    {"argv": ["python3", "-B", "verification/swift-retained-profile-composition-independent/test_independent.py"], "exit_code": 1, "stdout": "history/first-eight-controls/independent.stdout", "stderr": "history/first-eight-controls/independent.stderr", "observed_unittest_seconds": 0.033, "scope": "original eight independent methods"},
    {"argv": ["python3", "-B", "verification/swift-retained-profile-composition-independent/test_independent.py"], "exit_code": 1, "stdout": "independent.stdout", "stderr": "independent.stderr", "observed_unittest_seconds": 0.023, "scope": "nine methods after root-requested pre-close reporting fault"},
]
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=REPO, text=True).strip()
receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "scope": "independent frozen preparation/source/host review only", "disposition": "two required lifecycle corrections; no product implementation selection", "commands": commands,
    "producer_seal_sha256": "c7a8ead8257b8e13543c4fb3bb3ed385513f83080c960a58333b617d05c44860", "producer_member_count": 41, "producer_source_tree_sha256": "fd3c6972e040cb038a5e59d0836eba0c8315c3c4c2eb230f1c82925e5aeed13b",
    "source_commit": head, "committed_tree": tree, "tool": {"python_executable": str(python), "python_sha256": sha(python), "python_version": sys.version, "platform": platform.platform()},
    "producer_replay": {"methods": 26, "passed": 26, "failures": 0, "errors": 0, "skips": 0, "snapshot_mutations": 307, "sufficient_for_claimed_lifecycle": False},
    "independent": {"methods": 9, "passed": 6, "required_failed_controls": 3, "required_findings": 2, "errors": 0, "skips": 0, "raw_failures_preserved": True, "finding_ids": ["R01", "R02"]},
    "cleanup": {"owned_retained_fds_final": 0, "owned_stdio_fds_final": 0, "owned_scratch_entries_final": 0, "actual_successful_and_timeout_children_terminal_reaped": True, "close_failure_remnants_reviewer_retired_after_recording": True, "quarantine_control": "finite no-process model; explicitly retired only after recording; actual stuck OS branch unrun"},
    "boundaries": {"only_review_directory_written": True, "actual_rust_exporter_compiled_or_tested": False, "protocol_types_compiled": False, "actual_original_typed_result_or_15_word_ledger_join": False, "actual_8192_byte_context": False, "native_runtime_or_ui_or_capture": False, "process_inventory": False, "prohibited_hosted_read_import_execute": False, "canonical_product_changed": False, "commit_or_push": False, "real_binding_or_release_or_GA_accepted": False}}
write("receipt.json", receipt)
members = []
for path in sorted(ROOT.rglob("*")):
    if path.is_file() and path.name not in ("seal.json", "seal.sha256"):
        assert not path.is_symlink()
        members.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)})
write("seal.json", {"schema": 1, "scope": "independent finite host preparation review with three failed controls for two required findings", "member_count": len(members), "members": members, "product_native_real_binding_release_GA_accepted": False})
(ROOT / "seal.sha256").write_text(sha(ROOT / "seal.json") + "  seal.json\n")
print(json.dumps({"member_count": len(members), "seal_sha256": sha(ROOT / "seal.json"), "producer_replay_pass": 26, "independent_pass": 6, "independent_failed_controls": 3, "independent_required_findings": 2, "cleanup_final_zero": True}, sort_keys=True))
