"""Freeze all retained successful phase data; never spawn a child or execute artifact code."""
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
assert __debug__ and not (ROOT / "seal.json").exists()


def digest(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


preparation = json.loads((ROOT / "preparation.json").read_bytes())
for item in preparation["execution_scripts"]:
    assert digest((ROOT / item["path"]).read_bytes()) == item["digest"]
acceptance = json.loads((ROOT / "acceptance.json").read_bytes())
assert acceptance["source_revision"] == "43cbfb9c925e2ee7de43afd92bd588edb7ff60b6"
assert acceptance["source_tree"] == "93cc6868f445fa98c170acf771db73e50d90b4e2"
assert acceptance["successful_jobs"] == 6 and acceptance["successful_steps"] == 64
assert acceptance["retries_executed"] == 0 and acceptance["run_attempt"] == 1
commands = []
phase_names = {"terminal-collection", "core-jvm-audit", "capability-collection", "capability-audit", "acceptance"}
for path in sorted(ROOT.rglob("*.command.json")):
    row = json.loads(path.read_bytes())
    assert row["exit_code"] == 0 and not row.get("timed_out", False), str(path)
    name = path.name.removesuffix(".command.json")
    if path.parent == ROOT and name in phase_names:
        assert row["direct_child_reaped"] and row["owned_process_group_absent_after_reaping"]
        assert row["child_timeout_seconds"] == 60
    stdout = path.parent / row.get("stdout_file", name + ".stdout")
    stderr = path.parent / (name + ".stderr")
    assert digest(stdout.read_bytes()) == row["stdout"], str(stdout)
    assert digest(stderr.read_bytes()) == row["stderr"], str(stderr)
    commands.append(str(path.relative_to(ROOT)))
for directory in (ROOT, ROOT / "capability"):
    rows = json.loads((directory / "source-commands.json").read_bytes())
    assert rows and all(row["exit_code"] == 0 for row in rows)
assert {p.name.removesuffix(".command.json") for p in ROOT.glob("*.command.json")} >= phase_names
(ROOT / "freeze-record.json").write_text(json.dumps({
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "argv": [sys.executable, "-B", *sys.argv],
    "python": sys.version, "source_revision": acceptance["source_revision"], "source_tree": acceptance["source_tree"],
    "commands_verified": len(commands), "execution_scripts_checked_against_preexecution_hashes": True,
    "scope": "In-process data-only finalizer; no subprocesses, imports of artifact code, extraction, native activity or mutations outside owned audit directory",
    "descendant_reaping_scope": "Only fresh accepted phases; historical parent failed collection remains diagnostic with descendant reaping unverified",
}, indent=2) + "\n")
members = []
for path in sorted(ROOT.rglob("*")):
    assert not path.is_symlink()
    if path.is_file():
        members.append({"path": str(path.relative_to(ROOT)), **digest(path.read_bytes())})
seal = {
    "schema": 2, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "scope": "Frozen fresh exact-source terminal six-job CI and retained core/JVM/capability data-only artifact audit; separate fixture audit remains separately sealed",
    "source_revision": acceptance["source_revision"], "source_tree": acceptance["source_tree"], "run_id": acceptance["run_id"],
    "acceptance_sha256": digest((ROOT / "acceptance.json").read_bytes())["sha256"],
    "command_records_verified": commands, "members": members, "member_count": len(members), "total_bytes": sum(m["bytes"] for m in members),
}
(ROOT / "seal.json").write_text(json.dumps(seal, indent=2) + "\n")
print(json.dumps({"status":"sealed", "acceptance_sha256":seal["acceptance_sha256"], "seal_sha256":digest((ROOT / "seal.json").read_bytes())["sha256"], "members":len(members), "bytes":seal["total_bytes"]}))
