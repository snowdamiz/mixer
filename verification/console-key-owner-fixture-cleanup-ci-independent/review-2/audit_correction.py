#!/usr/bin/env python3
"""Read-only exact correction/pin audit; no producer import or replay."""
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import time

START = time.monotonic()
REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
LANE = REPO / "verification/console-key-owner-fixture-cleanup-ci-correction"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            assert time.monotonic() - START < 55
            block = stream.read(262144)
            if not block:
                return digest.hexdigest()
            digest.update(block)


def pairs(values):
    output = {}
    for key, value in values:
        assert key not in output
        output[key] = value
    return output


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def verify(items, root=None):
    seen = set()
    for item in items:
        relative = item["path"]
        assert relative not in seen
        seen.add(relative)
        if root:
            parsed = PurePosixPath(relative)
            assert str(parsed) == relative and not parsed.is_absolute() and ".." not in parsed.parts
        path = root / relative if root else Path(relative)
        assert path.is_file() and path.stat().st_size == item["bytes"] and sha(path) == item["sha256"]
    return seen


def packet(path, expected, count):
    assert sha(path / "freeze.json") == expected
    seal = read(path / "freeze.json")
    sealed = verify(seal["files"], path)
    actual = set()
    for child in path.rglob("*"):
        assert not child.is_symlink()
        if child.is_file() and child.relative_to(path).as_posix() != "freeze.json":
            actual.add(child.relative_to(path).as_posix())
    assert actual == sealed and len(actual) == count
    digest = hashlib.sha256("".join(v["path"] + "\0" + str(v["bytes"]) + "\0" + v["sha256"] + "\n" for v in seal["files"]).encode()).hexdigest()
    assert digest == seal["tree_sha256"]
    return seal


def main():
    old = LANE / "prepared-1"
    new = LANE / "prepared-2"
    old_seal = packet(old, "34ab3c96238e0e8100331d42109d834d313b39bec9b86582e7ffd78080f97019", 221)
    packet(new, "5ce0557d8cae549b7257a2d0ddfd59f73c4bd59d463fa20377e0038dfd64172e", 225)
    assert sha(new / "execution-plan.json") == "d1d909dee7aa0d93ad78f113689f0aa6db02f760a656f566c627977c35698b22"
    previous = read(old / "execution-plan.json")
    plan = read(new / "execution-plan.json")
    assert len(verify(plan["canonical_inputs"], REPO)) == 25
    assert len(verify(plan["prepared_files"], new)) == 224
    assert len(verify(plan["tools"])) == 980
    for key in ("canonical_inputs", "tools", "dependencies", "source_roster", "test_source", "test_support", "selection", "phases", "limits", "environment", "artifact_schemas", "scope"):
        assert plan[key] == previous[key], key
    changed = []
    for item in old_seal["files"]:
        relative = item["path"]
        if relative != "execution-plan.json" and (old / relative).read_bytes() != (new / relative).read_bytes():
            changed.append(relative)
    assert changed == ["runner.py"]
    expected_diff = "".join(difflib.unified_diff((old / "runner.py").read_text().splitlines(True), (new / "runner.py").read_text().splitlines(True), fromfile="prepared-1/runner.py", tofile="prepared-2/runner.py"))
    assert expected_diff == (new / "runner-directory-boundary.diff").read_text()
    for name in ("runner.py", "prepare-v2.py", "filesystem-boundary-controls.py"):
        ast.parse((new / name).read_text(), filename=name)
    controls = read(new / "filesystem-boundary-controls.json")
    assert controls["status"] == "passed" and controls["ordinary_files_expected"] == 10 and controls["required_artifacts"] == 8
    assert len(controls["controls"]) == 8
    assert [v["rejected"] for v in controls["controls"]] == [False] + [True] * 7
    assert controls["rejected_fixture_evidence_preserved_by_validator"] is True and controls["exact_temporary_control_tree_removed"] is True
    result = {"schema": 1, "status": "passed-independent-directory-boundary-correction-review-runtime-unrun", "created_at": datetime.now(timezone.utc).isoformat(), "command": "python3 -B verification/console-key-owner-fixture-cleanup-ci-independent/review-2/audit_correction.py", "python": sys.version, "script_sha256": sha(Path(__file__)), "producer_plan_sha256": sha(new / "execution-plan.json"), "producer_freeze_sha256": sha(new / "freeze.json"), "source_revision": plan["source_revision"], "selected_source_tree_sha256": plan["source_tree_sha256"], "verified": {"old_packet_members_preserved": 221, "new_packet_members": 225, "prepared_pins": 224, "canonical_pins": 25, "tool_pins": 980, "only_copied_runner_changed": True, "exact_recorded_runner_diff": True, "bootstrap_test_sources_support_schemas_tools_dependencies_unchanged": True}, "producer_filesystem_controls_reviewed_not_replayed": {"valid": 1, "refused": 7, "includes_extra_openssl_symlink_directory_FIFO_phase_symlink": True, "evidence_preserved": True, "temporary_tree_removed": True}, "R01": "closed in source: lstat exact ten ordinary files after confirmed child/group cleanup before reads", "recommend_root_single_exact_bounded_host_release": True, "runtime_or_producer_replay_invocations": 0, "elapsed_seconds": round(time.monotonic() - START, 6), "scope": "Focused runner correction and custody only; targeted seven-method behavior and full Phoenix CI remain unrun here."}
    (OUT / "audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
