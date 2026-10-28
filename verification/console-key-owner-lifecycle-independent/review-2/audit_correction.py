#!/usr/bin/env python3
"""Read-only correction custody audit; no producer import/replay or runtime."""
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
REVIEW = Path(__file__).resolve().parent
LANE = REPO / "verification/console-key-owner-lifecycle-implementation"


def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            assert time.monotonic() - START < 55
            data = stream.read(262144)
            if not data:
                return value.hexdigest()
            value.update(data)


def pairs(values):
    result = {}
    for key, value in values:
        assert key not in result, "duplicate key"
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))


def verify(items, root=None):
    seen = set()
    for item in items:
        value = item["path"]
        assert value not in seen
        seen.add(value)
        if root:
            parsed = PurePosixPath(value)
            assert not parsed.is_absolute() and ".." not in parsed.parts and str(parsed) == value
        path = root / value if root else Path(value)
        assert path.is_file() and path.stat().st_size == item["bytes"]
        assert sha(path) == item["sha256"], str(path)
    return seen


def tree(items):
    return hashlib.sha256("".join(v["path"] + "\0" + str(v["bytes"]) + "\0" + v["sha256"] + "\n" for v in items).encode()).hexdigest()


def verify_packet(packet, expected_sha, count):
    assert sha(packet / "freeze.json") == expected_sha
    seal = read(packet / "freeze.json")
    sealed = verify(seal["files"], packet)
    actual = set()
    for path in packet.rglob("*"):
        assert not path.is_symlink()
        if path.is_file() and path.relative_to(packet).as_posix() != "freeze.json":
            actual.add(path.relative_to(packet).as_posix())
    assert sealed == actual and len(sealed) == count
    assert tree(seal["files"]) == seal["tree_sha256"]
    return seal


def main():
    old = LANE / "prepared-1"
    new = LANE / "prepared-2"
    old_seal = verify_packet(old, "2169ba480aed74fcdac967908e578275fd7ebf3ca12d5f54448a3d61604b91a9", 224)
    new_seal = verify_packet(new, "d59a6d3987a3dd892b24bc2fbefba079926dcbb8ade28ad9c429ddd4a54f19ef", 234)
    plan = read(new / "execution-plan.json")
    old_plan = read(old / "execution-plan.json")
    assert sha(new / "execution-plan.json") == "1ae8bd1e9e38c2a18abae465b054fdcf562b842972475bc9bc1d3e80c07a52b3"
    assert new_seal["execution_plan_sha256"] == sha(new / "execution-plan.json")
    prepared = verify(plan["prepared_files"], new)
    assert len(prepared) == 233 and prepared | {"execution-plan.json"} == {v["path"] for v in new_seal["files"]}
    assert len(verify(plan["canonical_inputs"], REPO)) == 216
    assert tree(plan["canonical_inputs"]) == plan["source_tree_sha256"]
    assert len(verify(plan["tools"])) == 969
    assert plan["tools"] == old_plan["tools"] and plan["dependencies"] == old_plan["dependencies"]
    assert plan["source_roster"] == old_plan["source_roster"] and len(plan["source_roster"]) == 18
    unchanged = []
    changed = []
    for item in old_seal["files"]:
        relative = item["path"]
        if relative == "execution-plan.json":
            continue
        if (old / relative).read_bytes() == (new / relative).read_bytes():
            unchanged.append(relative)
        else:
            changed.append(relative)
    assert sorted(changed) == ["bootstrap.exs", "runner.py"]
    assert len(unchanged) == 221
    for relative in plan["source_roster"] + [plan["test_source"]]:
        assert (new / "inputs" / relative).read_bytes() == (REPO / relative).read_bytes()
    assert plan["phases"][0] == old_plan["phases"][0]
    assert plan["phases"][1]["required_artifacts"] == old_plan["phases"][1]["required_artifacts"]
    assert plan["limits"] == old_plan["limits"]
    assert (new / "required-artifact-schemas.json").read_bytes() == (REPO / "verification/console-key-owner-lifecycle-independent/review-1/required-artifact-schemas.json").read_bytes()
    schema = read(new / "required-artifact-schemas.json")
    expanded = dict(schema["schemas"])
    for name, paths in schema["shared_schema_bindings"].items():
        for path in paths:
            assert path not in expanded
            expanded[path] = schema["shared_schemas"][name]
    expected_paths = {phase["id"] + "/" + name for phase in plan["phases"] for name in phase["required_artifacts"]}
    assert len(expanded) == 13 and set(expanded) == expected_paths
    controls = read(new / "validator-controls.json")
    assert controls["good_fixture_artifacts"] == 13 and controls["good_fixture_acceptances"] == 2
    assert controls["malformed_fixture_rejections"] == len(controls["controls"]) == 711
    assert len({item["name"] for item in controls["controls"]}) == 711
    assert all(item["result"] == "rejected" and item["error"] for item in controls["controls"])
    assert controls["strict_json_rejections"] == ["duplicate", "NaN", "Infinity", "-Infinity"]
    assert controls["subprocess_invocations"] == controls["elixir_version_formatter_compiler_product_runtime_invocations"] == 0
    diff = []
    for name in ("runner.py", "bootstrap.exs"):
        diff += list(difflib.unified_diff((old / name).read_text().splitlines(True), (new / name).read_text().splitlines(True), fromfile="prepared-1/" + name, tofile="prepared-2/" + name))
    assert "".join(diff) == (new / "selected-correction.diff").read_text()
    for name in ("runner.py", "prepare-v2.py", "controls-v2.py"):
        ast.parse((new / name).read_text(), filename=name)
    formatter = (new / "inputs/hosted/.formatter.exs").read_text()
    assert formatter == '[\n  inputs: ["mix.exs", "{config,lib,test,priv,scripts}/**/*.{ex,exs}"]\n]\n'
    result = {
        "schema": 1,
        "status": "passed-independent-correction-custody-and-source-scope-runtime-unrun",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": "python3 -B verification/console-key-owner-lifecycle-independent/review-2/audit_correction.py",
        "python": sys.version,
        "review_script_sha256": sha(Path(__file__)),
        "producer_freeze_sha256": sha(new / "freeze.json"),
        "producer_execution_plan_sha256": sha(new / "execution-plan.json"),
        "old_packet_freeze_sha256": sha(old / "freeze.json"),
        "source_revision": plan["source_revision"],
        "source_git_tree": plan["source_git_tree"],
        "selected_source_tree_sha256": plan["source_tree_sha256"],
        "verified": {"old_packet_members": 224, "new_packet_members": 234, "new_prepared_pins": 233, "canonical_pins": 216, "tool_pins": 969, "old_packet_fully_preserved": True, "copied_old_members_unchanged": len(unchanged), "changed_old_members": changed, "exact_schemas_identical_to_independent_review": True, "exact_required_artifacts": 13, "same_two_phases": True, "same_product_sources_tests_beforeimages_dependencies": True, "selected_diff_exact": True, "formatter_inputs_only_defaults": True},
        "producer_controls_reviewed_without_replay": {"positive_acceptances": 2, "malformed_rejections": 711, "strict_json_rejections": 4, "report_names_unique": True},
        "formatter_order": "After ExUnit/postconditions/Mix.State stop, before success phase exit; root explicitly accepted exact ordering in review coordination.",
        "producer_python_executed_or_imported": False,
        "runtime_compiler_formatter_version_child_processes": 0,
        "elapsed_seconds": round(time.monotonic() - START, 6),
        "scope": "Independent source/custody review only; no producer replay, product runtime, DB/network/native/UI/process inventory."
    }
    (REVIEW / "custody-audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
