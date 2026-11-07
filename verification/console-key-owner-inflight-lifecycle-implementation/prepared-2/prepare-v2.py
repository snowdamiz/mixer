#!/usr/bin/env python3
"""Freeze the exact authorized formatting outputs and runtime-only candidate 2."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess
import sys
import time


START = time.monotonic()
DEADLINE = START + 55
LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
PRIOR = LANE / "prepared-1"
PREPARED = LANE / "prepared-2"
FORMATTING = LANE / "executions/formatting-1"


def budget():
    if time.monotonic() >= DEADLINE:
        raise TimeoutError("55-second offline preparation limit exceeded")


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pin(path, relative=None):
    budget()
    data = path.read_bytes()
    return {"path": relative or str(path), "bytes": len(data), "sha256": sha(data)}


def write(relative, value):
    path = PREPARED / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if type(value) is bytes else encoded(value))


def main():
    prior_freeze = json.loads((PRIOR / "freeze.json").read_bytes())
    assert pin(PRIOR / "freeze.json")["sha256"] == "4d46a3a66e9bbc6a0d699af3a020c1b84a4d1316cf8d672d198f1d76c79b8d2f"
    expected = {row["path"] for row in prior_freeze["files"]}
    assert len(expected) == len(prior_freeze["files"])
    actual = set()
    for path in PRIOR.rglob("*"):
        assert not path.is_symlink()
        if path.is_file() and path.relative_to(PRIOR).as_posix() != "freeze.json":
            actual.add(path.relative_to(PRIOR).as_posix())
    assert actual == expected
    for row in prior_freeze["files"]:
        assert pin(PRIOR / row["path"], row["path"]) == row

    application = json.loads((LANE / "formatting-application.json").read_bytes())
    receipt = json.loads((FORMATTING / "receipt.json").read_bytes())
    observed = json.loads((FORMATTING / "observations.json").read_bytes())
    release_path = ROOT / "verification/console-session-and-checkout-root-review/inflight-lifecycle-formatting-1-release.json"
    release = json.loads(release_path.read_bytes())
    assert pin(release_path)["sha256"] == application["release_sha256"] == "dd68817a7c2edae2cbeea819b615cde70cbcf4dd6c793a4b62b06063930b88e4"
    assert release["execution_plan_sha256"] == receipt["execution_plan_sha256"] == prior_freeze["formatting_plan_sha256"]
    assert receipt["status"] == "passed" and not receipt["errors"] and not receipt["cleanup_errors"]
    assert observed["scratch_removed"] is True and not observed["original_changes"]
    assert all(row["direct_child_reaped"] and row["group_absent"] for row in observed["owned_processes"])

    PREPARED.mkdir(exist_ok=False)
    moved = {"prepare.py", "verify.py", "README.md", "runner.py", "format-only.exs", "format-artifact-schemas.json",
             "execution-plan.json", "formatting-plan.json", "preparation-audit.json", "runner-provenance.json"}
    for row in prior_freeze["files"]:
        relative = row["path"]
        if relative in moved:
            relative = "inputs/prior-prepared-1/" + relative
        write(relative, (PRIOR / row["path"]).read_bytes())
    write("inputs/prior-prepared-1/freeze.json", (PRIOR / "freeze.json").read_bytes())
    for path in sorted(FORMATTING.rglob("*")):
        assert not path.is_symlink()
        if path.is_file():
            write("inputs/formatting-1/" + path.relative_to(FORMATTING).as_posix(), path.read_bytes())
    write("inputs/root-review/inflight-lifecycle-formatting-1-release.json", release_path.read_bytes())
    for name in ["formatting-application.json", "formatting-application.md", "formatting-only-application.diff", "prepare-v2.py"]:
        write(name, (LANE / name).read_bytes())
    write("README.md", (LANE / "README-v2.md").read_bytes())
    write("runner.py", (LANE / "runner-v2.py").read_bytes())
    write("verify.py", (LANE / "verify-v2.py").read_bytes())

    plan = json.loads((PRIOR / "execution-plan.json").read_bytes())
    canonical = []
    changed = {entry["path"]: entry for entry in application["changes"]}
    for row in plan["canonical_inputs"]:
        assert row["path"] != "hosted/test/mixer_hosted/identity/key_owner_test.exs"
        current = pin(ROOT / row["path"], row["path"])
        if row["path"] in changed:
            selected = changed[row["path"]]
            assert current["sha256"] == selected["after_sha256"]
            write("inputs/" + row["path"], (ROOT / row["path"]).read_bytes())
        else:
            assert current == row, "unexpected canonical input change: " + row["path"]
        canonical.append(current)
    for tool in plan["tools"]:
        assert pin(Path(tool["path"])) == tool, "tool identity changed: " + tool["path"]
    for path in PREPARED.rglob("*.py"):
        ast.parse(path.read_bytes(), filename=str(path.relative_to(PREPARED)))

    write("candidate-2-amendment.json", {
        "schema": 1, "status": "exact-authorized-formatting-applied-runtime-candidate-unexecuted",
        "prior_prepared_tree_sha256": prior_freeze["tree_sha256"],
        "prior_terminal_freeze_file_sha256": pin(PRIOR / "freeze.json")["sha256"],
        "formatting_release_sha256": application["release_sha256"],
        "formatting_receipt_sha256": application["formatting_receipt_sha256"],
        "source_changes": application["changes"],
        "harness_changes": ["Runtime-only prepared-2/candidate-2 paths; format-only dispatch removed",
            "Exact terminal root phase and per-phase complete output membership",
            "Parse and retain available JSON observations even when another artifact is missing"],
        "product_method_or_assertion_changes": False, "new_methods": 2, "retained_ordinary_methods": 7,
        "runtime_compile_test_TLS_OpenSSL_invocations": 0, "runtime_release_granted": False})

    files = [pin(path, path.relative_to(PREPARED).as_posix()) for path in sorted(PREPARED.rglob("*")) if path.is_file()]
    source_rows = [row for row in files if row["path"].startswith("inputs/hosted/")]
    source_tree = sha(encoded(source_rows))
    plan.update({
        "status": "frozen-runtime-candidate-2-after-exact-authorized-formatting-awaiting-independent-review-and-root-release",
        "canonical_inputs": canonical, "prepared_files": files,
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_tree_sha256": source_tree,
        "formatting": "One exact root-released format-only pass completed; its two output bindings were verified and applied. Runtime still requires read-only equality for all five authored identity source/test files before any OpenSSL/TLS action.",
        "output_membership": "Exactly the prod/test phase directories before durable root observations, then observations/receipt only; exact per-phase required JSON plus command/stdout and test-only two raw OpenSSL audit streams. Missing/extra members fail, while available required JSON observations are retained.",
        "prior_formatting_receipt_sha256": application["formatting_receipt_sha256"],
        "runtime_release_granted": False,
        "pending": ["Independent full runtime/source/nine-method plan review and separate exact root execution release",
            "Actual fresh production exclusion and nine-method lifecycle compilation/execution",
            "Observed KOL09 adverse or clean witness; no speculative product cleanup fix selected",
            "Original KOL08 ordinary owner-crash adaptation", "Production destination/provider/application/HTTP/browser/session/custody/operations/GA",
            "Native/UI/capture/emulators/phones remain paused"]})
    write("execution-plan.json", plan)
    write("preparation-audit.json", {"schema": 1, "status": "offline-candidate-2-preparation-only-passed",
        "command": "python3 -B verification/console-key-owner-inflight-lifecycle-implementation/prepare-v2.py",
        "python": sys.version, "source_tree_sha256": source_tree, "prior_prepared_members_unchanged": len(expected),
        "source_files": len(source_rows), "tools_pinned": len(plan["tools"]),
        "compiler_formatter_runtime_test_TLS_OpenSSL_invocations": 0,
        "elapsed_seconds": round(time.monotonic() - START, 6)})
    all_files = [pin(path, path.relative_to(PREPARED).as_posix()) for path in sorted(PREPARED.rglob("*")) if path.is_file()]
    freeze = {"schema": 1, "status": "frozen-candidate-2-unexecuted-awaiting-independent-review-and-root-release",
        "sole_excluded_relative_path": "freeze.json", "files": all_files, "tree_sha256": sha(encoded(all_files)),
        "execution_plan_sha256": pin(PREPARED / "execution-plan.json")["sha256"],
        "source_tree_sha256": source_tree, "prior_terminal_freeze_file_sha256": pin(PRIOR / "freeze.json")["sha256"],
        "prior_formatting_receipt_sha256": application["formatting_receipt_sha256"], "runtime_release_granted": False}
    write("freeze.json", freeze)
    print(json.dumps({"status": "frozen-candidate-2-ready-for-independent-runtime-review", "files": len(all_files),
        "source_tree_sha256": source_tree, "execution_plan_sha256": freeze["execution_plan_sha256"],
        "freeze_sha256": pin(PREPARED / "freeze.json")["sha256"], "runtime_release_granted": False}, indent=2))


if __name__ == "__main__":
    main()
