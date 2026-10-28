#!/usr/bin/env python3
"""Read-only independent custody audit; never imports or executes producer code."""
from datetime import datetime, timezone
import ast
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import time

START = time.monotonic()
DEADLINE = START + 55
REPO = Path(__file__).resolve().parents[3]
REVIEW = Path(__file__).resolve().parent
PACKET = REPO / "verification/console-key-owner-lifecycle-implementation/prepared-1"
CONTRACT = REPO / "verification/console-key-owner-lifecycle-contract"


def budget():
    if time.monotonic() >= DEADLINE:
        raise TimeoutError("independent source-only audit exceeded 55 seconds")


def sha(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            budget()
            data = stream.read(262144)
            if not data:
                return result.hexdigest()
            result.update(data)


def pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            raise ValueError("duplicate JSON key " + key)
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))


def relative(value):
    assert isinstance(value, str) and value
    parsed = PurePosixPath(value)
    assert not parsed.is_absolute() and ".." not in parsed.parts and str(parsed) == value
    return value


def check(path, item):
    budget()
    assert path.is_file()
    assert path.stat().st_size == item["bytes"]
    assert sha(path) == item["sha256"], str(path)


def unique_items(items, root=None):
    seen = set()
    for item in items:
        value = relative(item["path"]) if root else item["path"]
        assert value not in seen
        seen.add(value)
        path = root / value if root else Path(value)
        check(path, item)
    return seen


def tree(items):
    return hashlib.sha256("".join(v["path"] + "\0" + str(v["bytes"]) + "\0" + v["sha256"] + "\n" for v in items).encode()).hexdigest()


def main():
    assert sha(PACKET / "freeze.json") == "2169ba480aed74fcdac967908e578275fd7ebf3ca12d5f54448a3d61604b91a9"
    assert sha(PACKET / "execution-plan.json") == "3e9f39f19848f0ab36a524907d73c17fd7b68eaf96546e0185aad281c0496d01"
    seal = read(PACKET / "freeze.json")
    plan = read(PACKET / "execution-plan.json")
    files = unique_items(seal["files"], PACKET)
    actual = set()
    for path in PACKET.rglob("*"):
        assert not path.is_symlink()
        if path.is_file() and path.relative_to(PACKET).as_posix() != "freeze.json":
            actual.add(path.relative_to(PACKET).as_posix())
    assert files == actual and len(files) == 224
    assert seal["sole_excluded_relative_path"] == "freeze.json"
    assert tree(seal["files"]) == seal["tree_sha256"]
    prepared = unique_items(plan["prepared_files"], PACKET)
    assert prepared | {"execution-plan.json"} == actual and len(prepared) == 223
    canonical = unique_items(plan["canonical_inputs"], REPO)
    assert len(canonical) == 212
    assert tree(plan["canonical_inputs"]) == plan["source_tree_sha256"]
    tools = unique_items(plan["tools"])
    assert len(tools) == 969
    assert len(plan["source_roster"]) == len(set(plan["source_roster"])) == 18
    assert len(plan["dependencies"]) == 5
    for source in plan["source_roster"] + [plan["test_source"]]:
        assert source in canonical
        assert (PACKET / "inputs" / source).read_bytes() == (REPO / source).read_bytes()
    beforeimages = {}
    changes = []
    for name in ("admission.ex", "key_owner.ex"):
        source = "hosted/lib/mixer_hosted/identity/" + name
        before = PACKET / "beforeimages" / source
        baseline = CONTRACT / "inputs" / source
        assert before.read_bytes() == baseline.read_bytes()
        beforeimages[name] = sha(before)
        changes += list(difflib.unified_diff(before.read_text().splitlines(True),
                                            (PACKET / "inputs" / source).read_text().splitlines(True),
                                            fromfile="accepted-original/" + source,
                                            tofile="released-candidate/" + source))
    expected_owner = (CONTRACT / "inputs/hosted/lib/mixer_hosted/identity/key_owner.ex").read_text().replace(
        "  defp initialize(options, fixture) do\n",
        "  defp initialize(options, fixture) do\n    Process.flag(:trap_exit, true)\n\n", 1).replace(
        "    Admission.close(s.name)\n", "    Admission.close(s.name, s.table)\n", 1)
    assert (REPO / "hosted/lib/mixer_hosted/identity/key_owner.ex").read_text() == expected_owner
    before_admission = (CONTRACT / "inputs/hosted/lib/mixer_hosted/identity/admission.ex").read_text()
    after_admission = (REPO / "hosted/lib/mixer_hosted/identity/admission.ex").read_text()
    marker = "  def close(owner), do: :persistent_term.erase({__MODULE__, owner})\n"
    assert before_admission.count(marker) == 1
    assert before_admission.split(marker)[0] == after_admission.split("  # Publication and close")[0]
    assert before_admission.split(marker)[1] == "end\n"
    for source in plan["source_roster"]:
        baseline = CONTRACT / "inputs" / source
        if baseline.is_file() and Path(source).name not in beforeimages:
            assert baseline.read_bytes() == (PACKET / "inputs" / source).read_bytes()
    for name in ("runner.py", "prepare.py", "audit.py"):
        ast.parse((PACKET / name).read_text(), filename=name)
    independent = REPO / "verification/console-key-owner-lifecycle-independent"
    assert sha(independent / "preaccess-seal.json") == "1a1ec451725c4aa10bbe5b7282fd7e16bb5435e9ee310846889a83fd613df843"
    preaccess = read(independent / "preaccess-seal.json")
    unique_items(preaccess["files"], independent)
    assert len(preaccess["files"]) == 7
    assert seal["execution_plan_sha256"] == sha(PACKET / "execution-plan.json")
    assert seal["contract_amendment_sha256"] == sha(CONTRACT / "membership-amendment.json")
    source_module_declarations = sum((PACKET / "inputs" / source).read_text().count("defmodule ") for source in plan["source_roster"])
    assert source_module_declarations == 19
    for dep in plan["dependencies"]:
        assert dep["lock_entry"] in (PACKET / "inputs/hosted/mix.lock").read_text()
        for item in dep["files"]:
            destination = PACKET / "dependencies" / dep["name"] / "ebin" / Path(item["path"]).name
            check(destination, item)
            assert destination.relative_to(PACKET).as_posix() in prepared
    output = {
        "schema": 1,
        "status": "passed-independent-frozen-byte-and-scope-audit-runtime-unrun",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": "python3 -B verification/console-key-owner-lifecycle-independent/review-1/audit_frozen_packet.py",
        "python": sys.version,
        "review_script_sha256": sha(Path(__file__)),
        "producer_freeze_sha256": sha(PACKET / "freeze.json"),
        "producer_execution_plan_sha256": sha(PACKET / "execution-plan.json"),
        "preaccess_seal_sha256": sha(independent / "preaccess-seal.json"),
        "source_revision": plan["source_revision"],
        "source_git_tree": plan["source_git_tree"],
        "selected_source_tree_sha256": plan["source_tree_sha256"],
        "verified": {"freeze_members": len(files), "prepared_plan_members": len(prepared), "canonical_pins": len(canonical), "tool_pins": len(tools), "source_files": len(plan["source_roster"]), "source_module_declarations_only": source_module_declarations, "dependency_apps": len(plan["dependencies"]), "dependency_files": sum(len(d["files"]) for d in plan["dependencies"]), "original_beforeimages": beforeimages, "seven_preaccess_members_unchanged": True, "strict_json": True, "no_packet_symlinks": True, "canonical_matches_prepared_sources_and_test": True},
        "product_runtime_invocations": 0,
        "producer_python_executed_or_imported": False,
        "elapsed_seconds": round(time.monotonic() - START, 6),
        "scope": "Custody and source scope only. Manual source/test/runner findings recorded separately; no product test, compiler, version command, DB/network/native/UI/process inventory."
    }
    (REVIEW / "selected-product.diff").write_text("".join(changes))
    (REVIEW / "custody-audit.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
