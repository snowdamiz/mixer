"""Own freeze and read-only check; no compiler or old packet runner imports."""
import datetime
import json
import os
from pathlib import Path
import stat
import sys
from custody import HERE, ROOT, custody, row, tree, verify_packet, write


def members():
    return [{"path": str(p.relative_to(HERE)), "bytes": (r := row(p))["bytes"], "sha256": r["sha256"]}
        for p in sorted(HERE.rglob("*")) if p.is_file() and p != HERE / "seal.json"]


def check():
    seal, paths = verify_packet(HERE)
    assert all(stat.S_IMODE(p.stat().st_mode) & 0o222 == 0 for p in paths)
    actual_inputs = custody()
    final = json.loads((HERE / "final-custody.json").read_bytes())
    assert final["before"] == final["after"] == actual_inputs
    print(json.dumps({"seal_sha256": row(HERE / "seal.json")["sha256"],
        "members": seal["member_count"], "bytes": seal["member_bytes"], "tree_sha256": seal["tree_sha256"],
        "input_members": len(actual_inputs), "all_members_match": True, "all_files_read_only": True,
        "all_frozen_inputs_unchanged": True, "root_acceptance_or_native_OTA_GA": False}))


def freeze():
    assert not (HERE / "seal.json").exists()
    before = custody()
    commands = []
    for base in sorted((HERE / "commands").iterdir()):
        plan = json.loads((base / "plan.json").read_bytes())
        receipt = json.loads((base / "receipt.json").read_bytes())
        assert receipt["exit"] == 0 and not receipt["timed_out"]
        assert receipt["child_reaped"] and receipt["owned_group_absent"]
        assert receipt["inputs_unchanged"] and receipt["source_unchanged"]
        assert receipt["source_before"] == receipt["source_after"] == plan["source"]
        assert receipt["tool_after"] == {k: plan["tool"][k] for k in ("path", "bytes", "sha256")}
        assert json.loads((base / "input-before.json").read_bytes()) == before
        assert (base / "input-before.json").read_bytes() == (base / "input-after.json").read_bytes()
        for entry in receipt["outputs"]:
            assert row(ROOT / entry["path"]) == entry
        for entry in plan["source"]:
            snapshot = row(base / Path(entry["path"]).name)
            assert (snapshot["bytes"], snapshot["sha256"]) == (entry["bytes"], entry["sha256"])
        assert b"\nOK\n" in (base / "stderr").read_bytes()
        commands.append({"label": base.name, "exit": receipt["exit"], "pid_pgid": receipt["owned_pid_pgid"],
            "reaped": True, "owned_group_absent": True, "receipt": row(base / "receipt.json")})
    final = json.loads((HERE / "commands/complete-final/plan.json").read_bytes())
    for entry in final["source"]:
        assert row(ROOT / entry["path"]) == entry
    assert b"Ran 35 tests" in (HERE / "commands/complete-final/stderr").read_bytes()
    after = custody()
    assert before == after and len(before) == 548
    write(HERE / "final-custody.json", {"before": before, "after": after, "unchanged": True,
        "member_count": len(before), "member_bytes": sum(r["bytes"] for r in before), "tree_sha256": tree(before)})
    write(HERE / "cleanup.json", {"schema": 1, "commands": commands, "all_children_reaped": True,
        "all_exact_owned_groups_absent": True, "owned_scratch": [], "deadline_seconds_each": 55,
        "native_compiler_product_UI_capture_started": 0, "global_inventory_or_other_process_touches": False})
    assert not list(HERE.rglob("__pycache__"))
    actual, tool = members(), Path(sys.executable).resolve()
    write(HERE / "seal.json", {"schema": 1,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "frozen-independent-C1-C2-host-review-passed-awaiting-root-acceptance",
        "member_count": len(actual), "member_bytes": sum(r["bytes"] for r in actual),
        "tree_sha256": tree(actual), "tree_algorithm": "sha256 of UTF-8 json.dumps(members,sort_keys=True,separators=(',',':'))",
        "members": actual, "candidate_seal_sha256": "2270f59809b80c49df907a7ea9c20faf4dd45735cabad275ae61065efc19c50b",
        "source_revision_from_frozen_release_only": "9398732c23648a82097d5a72b02b1c77af818e41",
        "final_test_source": final["source"], "final_test_source_tree_sha256": final["source_tree_sha256"],
        "fresh_independent_methods": 35, "failures": 0, "blocking_findings": 0,
        "recommendation": "accept bounded synthetic trusted-local host correction only",
        "root_acceptance": False, "policy_funding_native_OTA_GA": False,
        "all_frozen_inputs_unchanged": True, "input_members": 548,
        "argv": [str(tool), "-B", str(Path(__file__).resolve()), "--freeze"],
        "environment_exact": dict(os.environ), "tool": {**row(tool), "version": sys.version},
        "seal_script": row(Path(__file__).resolve()), "commands": commands})
    for p in HERE.rglob("*"):
        if p.is_file(): p.chmod(0o444)
    check()


if __name__ == "__main__":
    assert sys.argv[1:] in (["--freeze"], ["--check"])
    freeze() if sys.argv[1:] == ["--freeze"] else check()
