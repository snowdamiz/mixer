#!/usr/bin/env python3
"""Freeze only the root-selected charlist correction and candidate-3 paths."""
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
PRIOR = LANE / "prepared-2"
PREPARED = LANE / "prepared-3"
EXECUTION = LANE / "executions/candidate-2"
TEST = "hosted/test/mixer_hosted/identity/key_owner_inflight_lifecycle_test.exs"


def budget():
    if time.monotonic() >= DEADLINE:
        raise TimeoutError("55-second offline preparation bound exceeded")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode()


def pin(path, relative=None):
    budget()
    data = path.read_bytes()
    return {"path": relative or str(path), "bytes": len(data), "sha256": sha(data)}


def write(relative, value):
    path = PREPARED / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if type(value) is bytes else encoded(value))


def main():
    seal = json.loads((PRIOR / "freeze.json").read_bytes())
    assert pin(PRIOR / "freeze.json")["sha256"] == "a0b9711ae54c50f43766e53dbd55b7e26c23e916c5131acce0609f2b81e4a57d"
    paths = {row["path"] for row in seal["files"]}
    assert len(paths) == len(seal["files"])
    actual = set()
    for path in PRIOR.rglob("*"):
        assert not path.is_symlink()
        if path.is_file() and path.relative_to(PRIOR).as_posix() != "freeze.json":
            actual.add(path.relative_to(PRIOR).as_posix())
    assert actual == paths
    for row in seal["files"]:
        assert pin(PRIOR / row["path"], row["path"]) == row
    correction = json.loads((LANE / "charlist-correction.json").read_bytes())
    before = (LANE / "charlist-correction-beforeimage.exs").read_bytes()
    after = (ROOT / TEST).read_bytes()
    assert before == (PRIOR / "inputs" / TEST).read_bytes()
    assert sha(before) == correction["before_sha256"] and sha(after) == correction["after_sha256"]
    assert before.count(b"'jwks.fixture.invalid'") == 1
    assert before.replace(b"'jwks.fixture.invalid'", b'~c"jwks.fixture.invalid"', 1) == after
    observed = json.loads((LANE / "candidate-2-observed-failure.json").read_bytes())
    assert observed["OpenSSL_invocations"] == 1 and observed["OpenSSL_args"] == [["version"]]
    assert observed["ExUnit_methods_executed"] == 0 and observed["TLS_fixtures_started"] == 0
    assert observed["group_observation"]["groups_equal"] is False

    PREPARED.mkdir(exist_ok=False)
    moved = {"execution-plan.json", "preparation-audit.json", "README.md", "runner.py", "verify.py", "prepare-v2.py", "candidate-2-amendment.json"}
    for row in seal["files"]:
        relative = row["path"]
        target = "inputs/prior-prepared-2/" + relative if relative in moved else relative
        write(target, (PRIOR / relative).read_bytes())
    write("inputs/prior-prepared-2/freeze.json", (PRIOR / "freeze.json").read_bytes())
    for path in sorted(EXECUTION.rglob("*")):
        assert not path.is_symlink()
        if path.is_file():
            write("inputs/candidate-2-execution/" + path.relative_to(EXECUTION).as_posix(), path.read_bytes())
    release_path = ROOT / "verification/console-session-and-checkout-root-review/inflight-lifecycle-candidate-2-release.json"
    release = json.loads(release_path.read_bytes())
    assert release["execution_plan_sha256"] == seal["execution_plan_sha256"]
    write("inputs/root-review/inflight-lifecycle-candidate-2-release.json", release_path.read_bytes())
    for name in ["charlist-correction.json", "charlist-correction.diff", "charlist-correction-beforeimage.exs",
                 "candidate-2-observed-failure.json", "prepare-v3.py"]:
        write(name, (LANE / name).read_bytes())
    write("runner.py", (LANE / "runner-v3.py").read_bytes())
    write("verify.py", (LANE / "verify-v3.py").read_bytes())
    write("README.md", (LANE / "README-v3.md").read_bytes())
    write("inputs/" + TEST, after)

    plan = json.loads((PRIOR / "execution-plan.json").read_bytes())
    canonical = []
    for row in plan["canonical_inputs"]:
        assert row["path"] != "hosted/test/mixer_hosted/identity/key_owner_test.exs"
        current = pin(ROOT / row["path"], row["path"])
        if row["path"] == TEST:
            assert current["sha256"] == correction["after_sha256"]
        else:
            assert current == row, "unselected canonical change: " + row["path"]
        canonical.append(current)
    for tool in plan["tools"]:
        assert pin(Path(tool["path"])) == tool, "tool identity changed: " + tool["path"]
    for path in PREPARED.rglob("*.py"):
        ast.parse(path.read_bytes(), filename=str(path.relative_to(PREPARED)))
    write("candidate-3-amendment.json", {
        "schema": 1, "status": "single-charlist-correction-only-known-group-observation-pending-root-review",
        "prior_prepared_freeze_sha256": pin(PRIOR / "freeze.json")["sha256"],
        "prior_execution_receipt_sha256": pin(EXECUTION / "receipt.json")["sha256"],
        "source_correction": correction,
        "runner_changes": "Only prepared-2/candidate-2 to prepared-3/candidate-3 exact paths",
        "schemas_unchanged_sha256": pin(PRIOR / "required-artifact-schemas.json")["sha256"],
        "zero_warning_policy_unchanged": True, "prospective_method_count": 9,
        "observed_prior_OpenSSL_invocations": 1, "observed_prior_TLS_fixtures": 0, "observed_prior_tests": 0,
        "known_pre_release_finding": observed["group_observation"],
        "new_compiler_formatter_runtime_test_TLS_OpenSSL_invocations": 0, "runtime_release_granted": False})
    files = [pin(path, path.relative_to(PREPARED).as_posix()) for path in sorted(PREPARED.rglob("*")) if path.is_file()]
    source_rows = [row for row in files if row["path"].startswith("inputs/hosted/")]
    source_tree = sha(encoded(source_rows))
    plan.update({
        "status": "frozen-charlist-correction-candidate-3-known-OpenSSL-group-finding-awaiting-root-review",
        "canonical_inputs": canonical, "prepared_files": files,
        "source_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_tree_sha256": source_tree,
        "formatting": "Historical exact formatter outputs retained; the only later change is one equivalent ~c charlist spelling. No new formatter run. Existing runtime read-only five-file equality remains mandatory.",
        "openssl_accounting": "Actual prior audit has one completed version call; wrapper process group differs from retained test VM group. Existing validator would reject group inequality later. VM-group-only failure cleanup is not independent proof of wrapper/native group absence. No speculative cleanup change in this literal/path-only candidate.",
        "known_execution_blockers": ["Root review/coordination of the observed distinct System.cmd/OpenSSL wrapper group before any further runtime release"],
        "prior_candidate_2_receipt_sha256": pin(EXECUTION / "receipt.json")["sha256"],
        "runtime_release_granted": False,
        "pending": ["Narrow charlist/path delta review plus observed OpenSSL process-group ownership review and separate exact root release",
            "Fresh test-module zero-warning compilation and actual nine-method lifecycle execution",
            "KOL08 completed-TLS/pending-JWKS drain and KOL09 required adverse or clean witness",
            "Original KOL08 ordinary owner-crash adaptation", "Production destination/provider/application/HTTP/browser/session/custody/operations/GA",
            "Native/UI/capture/emulators/phones remain paused"]})
    write("execution-plan.json", plan)
    write("preparation-audit.json", {"schema": 1, "status": "offline-candidate-3-preparation-only-passed",
        "command": "python3 -B verification/console-key-owner-inflight-lifecycle-implementation/prepare-v3.py",
        "python": sys.version, "source_tree_sha256": source_tree, "prior_members_unchanged": len(paths),
        "new_compiler_formatter_runtime_test_TLS_OpenSSL_invocations": 0,
        "elapsed_seconds": round(time.monotonic() - START, 6)})
    rows = [pin(path, path.relative_to(PREPARED).as_posix()) for path in sorted(PREPARED.rglob("*")) if path.is_file()]
    freeze = {"schema": 1, "status": "frozen-candidate-3-unexecuted-known-group-finding-awaiting-root-review",
        "sole_excluded_relative_path": "freeze.json", "files": rows, "tree_sha256": sha(encoded(rows)),
        "execution_plan_sha256": pin(PREPARED / "execution-plan.json")["sha256"], "source_tree_sha256": source_tree,
        "prior_prepared_freeze_sha256": pin(PRIOR / "freeze.json")["sha256"], "runtime_release_granted": False}
    write("freeze.json", freeze)
    print(json.dumps({"status": "frozen-candidate-3-narrow-delta-ready-for-review-known-group-finding-retained",
        "files": len(rows), "source_tree_sha256": source_tree, "execution_plan_sha256": freeze["execution_plan_sha256"],
        "freeze_sha256": pin(PREPARED / "freeze.json")["sha256"], "runtime_release_granted": False}, indent=2))


if __name__ == "__main__":
    main()
