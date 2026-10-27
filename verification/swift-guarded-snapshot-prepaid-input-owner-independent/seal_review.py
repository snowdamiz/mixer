"""Freeze/check only this independent review packet. No child processes."""
import datetime
import hashlib
import json
from pathlib import Path
import stat
import sys

from run_review_once import custody, digest

HERE = Path(__file__).resolve().parent


def tree(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def members():
    return [{"path": str(p.relative_to(HERE)), "bytes": len(p.read_bytes()),
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(HERE.rglob("*")) if p.is_file() and p != HERE / "seal.json"]


def main():
    if sys.argv[1:] == ["--check"]:
        raw = (HERE / "seal.json").read_bytes()
        seal = json.loads(raw)
        actual = members()
        assert seal["members"] == actual
        assert seal["tree_sha256"] == tree(actual)
        assert all(stat.S_IMODE(p.stat().st_mode) & 0o222 == 0 for p in HERE.rglob("*") if p.is_file())
        print(json.dumps({"seal_sha256": hashlib.sha256(raw).hexdigest(), "members": len(actual),
            "bytes": sum(r["bytes"] for r in actual), "tree_sha256": seal["tree_sha256"],
            "all_members_match": True, "all_files_read_only": True, "scope": "read-only self custody; no test replay"}))
        return
    assert sys.argv[1:] == ["--freeze"]
    assert not (HERE / "seal.json").exists()
    before, original_count, original_bytes = custody()
    commands = []
    for label, expected_exit in (("candidate-desired-properties", 1), ("independent-controls", 0),
                                 ("source-comparison", 1), ("source-comparison-v2", 0)):
        directory = HERE / "commands" / label
        receipt = json.loads((directory / "receipt.json").read_bytes())
        assert receipt["exit"] == expected_exit
        assert not receipt["timed_out"]
        assert receipt["inputs_unchanged"] and receipt["owned_group_absent"] and receipt["child_reaped"]
        assert receipt["source_before"] == receipt["source_after"]
        for recorded in receipt["outputs"]:
            path = HERE.parents[1] / recorded["path"]
            assert digest(path) == recorded
        for recorded in receipt["source_before"]:
            assert (directory / Path(recorded["path"]).name).read_bytes()
            raw = (directory / Path(recorded["path"]).name).read_bytes()
            assert (len(raw), hashlib.sha256(raw).hexdigest()) == (recorded["bytes"], recorded["sha256"])
        commands.append({"path": str(directory.relative_to(HERE)), "exit": expected_exit,
                         "receipt_sha256": digest(directory / "receipt.json")["sha256"]})
    after, _, _ = custody()
    assert before == after
    final_custody = {"before": before, "after": after, "unchanged": True,
                     "original_declared_input_count": original_count,
                     "original_declared_input_bytes": original_bytes,
                     "scope": "final read-only frozen input comparison; no producer program replay"}
    (HERE / "final-custody.json").write_text(json.dumps(final_custody, indent=2, sort_keys=True) + "\n")
    rows = members()
    seal = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "immutable-independent-review-return-with-four-preserved-model-failures",
        "member_count": len(rows), "member_bytes": sum(row["bytes"] for row in rows),
        "tree_algorithm": "sha256 of UTF-8 json.dumps(members, sort_keys=True, separators=(',', ':'))",
        "tree_sha256": tree(rows), "members": rows,
        "seal_argv": [sys.executable, "-B", str(Path(__file__).resolve()), "--freeze"],
        "tool": {**digest(Path(sys.executable).resolve()), "version": sys.version},
        "seal_script_sha256": digest(Path(__file__).resolve())["sha256"],
        "commands": commands, "candidate_model_accepted": False,
        "contract_direction_implementable_under_existing_local_trust": True,
        "independent_controls_passed": 16, "exhaustive_read_schedules": 100842,
        "candidate_regressions_failed": 4, "root_policy_or_funding_selected": False,
        "all_three_selectors": "Pending", "compiler_or_product_or_native_execution": False,
        "operational_FieldLog_OTA_GA": False}
    (HERE / "seal.json").write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n")
    for path in HERE.rglob("*"):
        if path.is_file():
            path.chmod(0o444)
    raw = (HERE / "seal.json").read_bytes()
    print(json.dumps({"seal_sha256": hashlib.sha256(raw).hexdigest(), "members": len(rows),
        "bytes": seal["member_bytes"], "tree_sha256": seal["tree_sha256"],
        "all_files_read_only": True, "candidate_model_accepted": False}))


if __name__ == "__main__":
    main()
