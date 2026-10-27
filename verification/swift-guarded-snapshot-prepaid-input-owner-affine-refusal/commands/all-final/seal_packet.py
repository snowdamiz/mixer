"""Fresh freeze/read-only check; no old one-shot scripts or subprocesses."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from run_bounded import custody, row, source_rows, tree, write

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def members():
    return [{"path": str(p.relative_to(HERE)), "bytes": len(p.read_bytes()),
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(HERE.rglob("*")) if p.is_file() and p != HERE / "seal.json"]


def check():
    raw = (HERE / "seal.json").read_bytes()
    seal = json.loads(raw)
    actual = members()
    assert actual == seal["members"] and tree(actual) == seal["tree_sha256"]
    assert len(actual) == seal["member_count"] and sum(e["bytes"] for e in actual) == seal["member_bytes"]
    assert all(stat.S_IMODE(p.stat().st_mode) & 0o222 == 0 for p in HERE.rglob("*") if p.is_file())
    custody()
    print(json.dumps({"seal_sha256": hashlib.sha256(raw).hexdigest(), "members": len(actual),
        "bytes": sum(e["bytes"] for e in actual), "tree_sha256": tree(actual),
        "all_members_match": True, "all_files_read_only": True,
        "scope": "read-only complete packet and frozen-input custody; no test or native/compiler execution"}))


def freeze():
    assert not (HERE / "seal.json").exists()
    before = custody()
    commands = []
    for directory in sorted((HERE / "commands").iterdir()):
        plan = json.loads((directory / "plan.json").read_bytes())
        receipt = json.loads((directory / "receipt.json").read_bytes())
        assert not receipt["timed_out"] and receipt["child_reaped"] and receipt["owned_group_absent"]
        assert receipt["inputs_unchanged"] and receipt["source_unchanged"]
        assert plan["source"] == receipt["source_before"] == receipt["source_after"]
        assert receipt["tool_after"] == {k: plan["tool"][k] for k in ("path", "bytes", "sha256")}
        for entry in receipt["outputs"]: assert row(ROOT / entry["path"]) == entry
        for entry in plan["source"]:
            snapshot = row(directory / Path(entry["path"]).name)
            assert (snapshot["bytes"], snapshot["sha256"]) == (entry["bytes"], entry["sha256"])
        commands.append({"label": directory.name, "exit": receipt["exit"], "receipt": row(directory / "receipt.json")})
    final = HERE / "commands/all-final"
    final_receipt = json.loads((final / "receipt.json").read_bytes())
    assert final_receipt["exit"] == 0 and source_rows() == final_receipt["source_before"]
    assert b"\nOK\n" in (final / "stderr").read_bytes()
    assert b'"exhaustive_read_schedules": 100842' in (final / "stdout").read_bytes()
    after = custody()
    assert before == after
    write(HERE / "final-custody.json", {"before": before, "after": after, "unchanged": True,
          "input_members": len(before), "input_bytes": sum(e["bytes"] for e in before)})
    assert not list(HERE.rglob("__pycache__"))
    actual, tool = members(), Path(sys.executable).resolve()
    seal = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "immutable-C1-C2-host-model-candidate-awaiting-independent-review",
        "member_count": len(actual), "member_bytes": sum(e["bytes"] for e in actual),
        "tree_algorithm": "sha256 of UTF-8 json.dumps(members, sort_keys=True, separators=(',', ':'))",
        "tree_sha256": tree(actual), "members": actual, "commands": commands,
        "argv": [str(tool), "-B", str(Path(__file__).resolve()), "--freeze"],
        "environment_exact": dict(os.environ), "tool": {**row(tool), "version": sys.version},
        "seal_script": row(Path(__file__).resolve()), "source_tree_sha256": tree(source_rows()),
        "source_revision_from_frozen_return_only": "a96712bbd79ff4c0709d2811dd2846b4a0ea0096",
        "root_policy_funding_or_native_implementation_selected": False,
        "compiler_product_native_UI_capture_Git_operations": False,
        "all_three_selectors": "Pending", "all_six_upstream_needs": "Pending",
        "fresh_independent_review_claimed": False, "FieldLog_operational_OTA_GA": False}
    write(HERE / "seal.json", seal)
    for p in HERE.rglob("*"):
        if p.is_file(): p.chmod(0o444)
    check()


if __name__ == "__main__":
    assert sys.argv[1:] in (["--freeze"], ["--check"])
    freeze() if sys.argv[1:] == ["--freeze"] else check()
