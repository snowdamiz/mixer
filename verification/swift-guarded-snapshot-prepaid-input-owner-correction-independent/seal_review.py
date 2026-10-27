"""New review packet finalizer/checker; never executes original freeze scripts."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
from run_bounded import custody, row, write, HERE


def members():
    return [{**row(p), "path": str(p.relative_to(HERE))} for p in sorted(HERE.rglob("*"))
            if p.is_file() and p.name != "seal.json"]


def main():
    assert sys.argv[1:] in (["--freeze"], ["--check"])
    if sys.argv[1] == "--check":
        seal = json.loads((HERE / "seal.json").read_bytes())
        assert members() == seal["members"]
        assert custody() == json.loads((HERE / "final-custody.json").read_bytes())["inputs"]
        print(json.dumps({"check": "pass", "seal_sha256": row(HERE / "seal.json")["sha256"],
                          "members": seal["member_count"], "bytes": seal["member_bytes"],
                          "tree_sha256": seal["tree_sha256"]}))
        return
    assert not (HERE / "seal.json").exists()
    inputs = custody()
    receipts = [json.loads((HERE / "commands" / name / "receipt.json").read_bytes())
                for name in ("positive-final", "required-properties", "concrete-findings")]
    assert all(r["inputs_unchanged"] and r["child_reaped"] and r["owned_group_absent"] and
               r["own_source_unchanged"] and not r["timed_out"] for r in receipts)
    assert [r["exit"] for r in receipts] == [0, 1, 0]
    write(HERE / "cleanup.json", {"schema": 1, "owned_groups": [r["owned_pid_pgid"] for r in receipts],
          "children_reaped_and_exact_owned_groups_absent": True, "scratch": [],
          "native_compiler_product_capture_instances_started": 0, "global_inventory": False,
          "other_project_processes_touched": False})
    write(HERE / "final-custody.json", {"schema": 1, "inputs": inputs, "count": len(inputs),
          "total_bytes": sum(e["bytes"] for e in inputs), "all_three_commands_same_before_after": True,
          "tool": {**row(Path(sys.executable).resolve()), "version": sys.version},
          "argv": [str(Path(sys.executable).resolve()), "-B", str(Path(__file__).resolve()), "--freeze"],
          "environment_exact": dict(os.environ), "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "scope": "read-only input custody and owned review packet finalization; no test/native/compiler replay"})
    entries = members()
    digest = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    write(HERE / "seal.json", {"schema": 1, "status": "immutable-independent-return-C1-C2",
          "member_count": len(entries), "member_bytes": sum(e["bytes"] for e in entries),
          "tree_sha256": digest, "members": entries, "all_inputs_unchanged": True,
          "acceptance": False, "native_operational_OTA_GA": False})
    for path in HERE.rglob("*"):
        if path.is_file(): path.chmod(0o444)
    print(json.dumps({"seal_sha256": row(HERE / "seal.json")["sha256"], "members": len(entries),
                      "bytes": sum(e["bytes"] for e in entries), "tree_sha256": digest,
                      "input_members": len(inputs), "status": "returned-C1-C2"}))


if __name__ == "__main__":
    main()
