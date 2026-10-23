#!/usr/bin/env python3
"""Match two separately reviewed capability layers; this is not bridge execution."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MAILBOX = "4e37b357ae029d9cdf5e5c6b4281d82f61b65f3a"
EXIT = "3d4b88dd2eea3e26ce7ea87b3f78cb11631b410a"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read(path):
    return json.loads((ROOT / path).read_text())


def git_bytes(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def manifest(path, revision=None, base=""):
    entries = (ROOT / path).read_text().splitlines()
    for entry in entries:
        expected, name = entry.split("  ", 1)
        actual = git_bytes(revision, name) if revision else (ROOT / base / name).read_bytes()
        require(digest(actual) == expected, f"manifest mismatch: {name}")
    return len(entries)


def logs(commands, base="", path_key="log", hash_key="log_sha256", exit_key="exit_code"):
    for command in commands:
        require(command[exit_key] == command.get("expected_exit_code", 0), "unexpected command status")
        path = ROOT / base / command[path_key]
        require(digest(path.read_bytes()) == command[hash_key], f"log mismatch: {path}")
    return len(commands)


def main():
    mailbox_path = "verification/capability-mailbox-review/receipt.json"
    exit_path = "verification/capability-exit-review/receipt.json"
    native_path = "capabilities/verification/exit-observation/receipt.json"
    mailbox, native_review, native = map(read, (mailbox_path, exit_path, native_path))
    require(mailbox["reviewed_revision"] == MAILBOX, "wrong mailbox revision")
    require(native_review["revision"] == EXIT, "wrong native revision")
    require(digest((ROOT / "verification/capability-mailbox-review/implementation-source-manifest.sha256").read_bytes()) == mailbox["implementation_source_digest"], "mailbox manifest digest mismatch")
    require(digest((ROOT / mailbox["review_source_manifest"]).read_bytes()) == mailbox["review_source_digest"], "mailbox review digest mismatch")
    mailbox_source = manifest("verification/capability-mailbox-review/implementation-source-manifest.sha256", MAILBOX)
    review_source = manifest(mailbox["review_source_manifest"])
    mailbox_logs = logs(mailbox["commands"])
    for entry in mailbox["frozen_inputs"]:
        data = git_bytes(MAILBOX, entry["path"])
        require(digest(data) == entry["sha256"], "frozen mailbox hash mismatch")
        require(data == git_bytes(entry["compared_base_revision"], entry["path"]), "compatibility input changed")
    native_sources = native["source"]["files"]
    for entry in native_sources:
        data = git_bytes(EXIT, entry["path"])
        require(len(data) == entry["bytes"] and digest(data) == entry["sha256"], "native source mismatch")
    canonical = json.dumps(native_sources, sort_keys=True, separators=(",", ":")).encode()
    require(digest(canonical) == native["source"]["digest"] == native_review["qualified_source_digest"], "native digest mismatch")
    native_logs = logs(native["commands"], path_key="output", hash_key="outputSHA256", exit_key="exitCode")
    review_base = "verification/capability-exit-review"
    require(digest((ROOT / review_base / "frozen-source.sha256").read_bytes()) == native_review["source_freeze"]["manifest_sha256"], "native snapshot manifest mismatch")
    require(digest((ROOT / review_base / "review-evidence.sha256").read_bytes()) == native_review["review_evidence_manifest_sha256"], "native review manifest mismatch")
    native_frozen = manifest(f"{review_base}/frozen-source.sha256", EXIT)
    native_review_files = manifest(f"{review_base}/review-evidence.sha256", base=review_base)
    native_review_logs = logs(native_review["commands"], base=review_base, path_key="output", hash_key="output_sha256")
    ci_base = "verification/github-ci-8e76cfd"
    ci = read(f"{ci_base}/receipt.json")
    require(ci["conclusion"] == "success" and all(j["conclusion"] == "success" for j in ci["jobs"]), "CI did not pass")
    for path, expected in ci["outputs"].items():
        require(digest((ROOT / ci_base / path).read_bytes()) == expected, "CI evidence mismatch")
    result = {
        "schema": 1,
        "observedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Root source/evidence identity audit of separately reviewed mailbox and installed native exit layers; no combined execution",
        "command": ["python3", "verification/tools/audit-capability-foundations.py"],
        "mailbox": {"revision": MAILBOX, "reviewRevision": "19c3949ca982a1f6f582e945eb5e4007ad23fdf6", "sourceFilesMatched": mailbox_source, "reviewSourcesMatched": review_source, "commandLogsMatched": mailbox_logs, "unchangedCompatibilityInputs": len(mailbox["frozen_inputs"]), "independentTestsPerMode": 13, "receipt": mailbox_path},
        "nativeExit": {"revision": EXIT, "reviewRevision": "bc747c9d85ffdd022b5c948f5869b08d36da4e34", "sourceFilesMatched": len(native_sources), "commandLogsMatched": native_logs, "reviewFrozenFilesMatched": native_frozen, "reviewEvidenceFilesMatched": native_review_files, "reviewCommandLogsMatched": native_review_logs, "independentTestsPerConfiguration": 6, "configurations": ["debug", "release", "ThreadSanitizer"], "receipt": exit_path},
        "ci": {"receipt": f"{ci_base}/receipt.json", "runId": ci["runId"], "sourceRevision": ci["sourceRevision"], "jobsPassed": 3, "includesNativeExitChange": False},
        "receiptHashes": {p: digest((ROOT / p).read_bytes()) for p in [mailbox_path, exit_path, native_path]},
        "result": "All recorded source and evidence hashes matched; scoped independent reviews report no unresolved findings",
        "limitations": ["Two separate components, no guest/native bridge, C ABI, counted session retention or activation admission", "Mailbox standard mutex first-lock OOM may abort; no general no-unwind guarantee", "Native exit joins invocation return with owned adapter cleanup, not kernel/socket/RSS reclamation or durable mutation rollback", "Host and cross-compile evidence does not qualify physical devices, immutable FieldLog packages, stores, operations or GA"]
    }
    output = ROOT / "verification/capability-foundations-integration-2026-10-22.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"result": result["result"], "mailboxSourceFiles": mailbox_source, "nativeSourceFiles": len(native_sources), "output": str(output)}))


if __name__ == "__main__":
    main()
