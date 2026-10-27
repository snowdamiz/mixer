"""New correction-only freeze/read-only check; no subprocesses or old seals run."""
import datetime
import hashlib
import json
from pathlib import Path
import stat
import sys
from run_group import custody, digest, source_rows, write

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def members():
    return [{"path": str(p.relative_to(HERE)), "bytes": len(p.read_bytes()),
             "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(HERE.rglob("*")) if p.is_file() and p != HERE / "seal.json"]


def tree(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def check():
    raw = (HERE / "seal.json").read_bytes()
    seal = json.loads(raw)
    rows = members()
    assert seal["members"] == rows and seal["tree_sha256"] == tree(rows)
    assert all(stat.S_IMODE(p.stat().st_mode) & 0o222 == 0 for p in HERE.rglob("*") if p.is_file())
    custody()
    print(json.dumps({"seal_sha256": hashlib.sha256(raw).hexdigest(), "members": len(rows),
        "bytes": sum(r["bytes"] for r in rows), "tree_sha256": tree(rows),
        "all_members_match": True, "all_files_read_only": True,
        "scope": "read-only final custody; no test/native/compiler execution"}))


def freeze():
    assert not (HERE / "seal.json").exists()
    before = custody()
    summaries = []
    for label, expected in (("legacy-attempt1", 1), ("all-attempt1", 0), ("all-final", 0)):
        directory = HERE / "commands" / label
        plan = json.loads((directory / "plan.json").read_bytes())
        receipt = json.loads((directory / "receipt.json").read_bytes())
        assert receipt["exit"] == expected and not receipt["timed_out"]
        assert receipt["inputs_unchanged"] and receipt["child_reaped"] and receipt["owned_group_absent"]
        assert receipt["source_before"] == receipt["source_after"]
        assert plan["source"] == receipt["source_before"]
        assert receipt["tool_after"] == {k: plan["tool"][k] for k in ("path", "bytes", "sha256")}
        for row in receipt["outputs"]:
            assert digest(ROOT / row["path"]) == row
        for row in receipt["source_before"]:
            snapshot = directory / Path(row["path"]).name
            got = digest(snapshot)
            assert (got["bytes"], got["sha256"]) == (row["bytes"], row["sha256"])
        if label == "all-final":
            assert source_rows() == receipt["source_before"], "final exact source changed"
            assert b"Ran 76 tests" in (directory / "stderr").read_bytes()
            assert b"\nOK\n" in (directory / "stderr").read_bytes()
            assert b'"exhaustive_read_schedules": 100842' in (directory / "stdout").read_bytes()
        summaries.append({"label": label, "exit": expected, "receipt": digest(directory / "receipt.json")})
    after = custody()
    assert before == after
    write(HERE / "final-custody.json", {"before": before, "after": after, "unchanged": True,
        "input_members": len(before), "input_bytes": sum(r["bytes"] for r in before),
        "original_declared_inputs": 299, "original_declared_bytes": 40253112})
    assert not list(HERE.rglob("__pycache__"))
    rows = members()
    tool = Path(sys.executable).resolve()
    seal = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "immutable-R1-R3-corrected-host-model-candidate-awaiting-independent-review",
        "member_count": len(rows), "member_bytes": sum(r["bytes"] for r in rows),
        "tree_algorithm": "sha256 of UTF-8 json.dumps(members, sort_keys=True, separators=(',', ':'))",
        "tree_sha256": tree(rows), "members": rows, "commands": summaries,
        "argv": [str(tool), "-B", str(Path(__file__).resolve()), "--freeze"],
        "tool": {**digest(tool), "version": sys.version}, "seal_script": digest(Path(__file__).resolve()),
        "root_policy_funding_or_native_implementation_selected": False,
        "actual_Rust_source_compiled_or_native_execution": False, "product_source_changes": False,
        "all_three_selectors": "Pending", "all_six_upstream_needs": "Pending",
        "FieldLog_operational_OTA_GA": False}
    write(HERE / "seal.json", seal)
    for path in HERE.rglob("*"):
        if path.is_file():
            path.chmod(0o444)
    check()


if __name__ == "__main__":
    assert sys.argv[1:] in (["--freeze"], ["--check"])
    freeze() if sys.argv[1:] == ["--freeze"] else check()
