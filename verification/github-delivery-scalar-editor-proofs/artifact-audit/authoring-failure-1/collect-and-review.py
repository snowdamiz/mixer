"""Read retained CI bytes and validate them against the exact pushed tree."""
import datetime
import json
import pathlib
import subprocess
import sys

import audit

HERE = pathlib.Path(__file__).resolve().parent
PARENT = HERE.parent
assert not (HERE / "acceptance.json").exists()

def capture(base, name, argv):
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=audit.REPO, capture_output=True, timeout=60)
    for stream in ("stdout", "stderr"):
        (base / (name + "." + stream)).write_bytes(getattr(result, stream))
    (base / (name + ".command.json")).write_text(json.dumps({
        "started": start, "completed": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "argv": argv, "exit": result.returncode,
        "stdout": audit.digest(result.stdout), "stderr": audit.digest(result.stderr),
    }, indent=2) + "\n")
    assert result.returncode == 0
    return result.stdout

terminal_bytes = capture(PARENT, "ci-terminal", ["gh", "run", "view", str(audit.RUN), "--repo", "snowdamiz/mixer", "--json", "status,conclusion,headSha,jobs,url"])
(PARENT / "ci-terminal.json").write_bytes(terminal_bytes)
terminal = json.loads(terminal_bytes)
assert terminal["status"] == "completed" and terminal["conclusion"] == "success" and terminal["headSha"] == audit.SHA
assert {j["name"] for j in terminal["jobs"]} == {"swift", "swift-capability-native", "vm", "services", "android-owner-host"}
assert all(j["status"] == "completed" and j["conclusion"] == "success" and all(s["conclusion"] == "success" for s in j["steps"]) for j in terminal["jobs"])
capture(HERE, "gh-version", ["gh", "--version"])
capture(HERE, "source-tree", ["git", "rev-parse", audit.SHA + "^{tree}"])
workflow = capture(HERE, "workflow-source", ["git", "show", audit.SHA + ":.github/workflows/engine.yml"])
assert audit.digest(workflow)["sha256"] == audit.WORKFLOW_HASH
metadata = json.loads(capture(HERE, "artifact-metadata", ["gh", "api", f"repos/snowdamiz/mixer/actions/runs/{audit.RUN}/artifacts?per_page=100"]))
for name in ("swift-core-toolchain-host", "android-owner-host"):
    artifact, = [a for a in metadata["artifacts"] if a["name"] == name + "-" + audit.SHA]
    blob = capture(HERE, name, ["gh", "api", f"repos/snowdamiz/mixer/actions/artifacts/{artifact['id']}/zip"])
    (HERE / (name + ".zip")).write_bytes(blob)
    (HERE / (name + ".stdout")).unlink()
core = audit.audit_core()
jvm = audit.audit_jvm()
audit.write_json("source-blobs.json", audit.SOURCE_RECORDS)
audit.write_json("core-jvm-audit.json", {"core": core, "jvm": jvm, "source_revision": audit.SHA, "run": audit.RUN, "source_blobs": audit.digest((HERE / "source-blobs.json").read_bytes())})
# Separate process owns the capability audit globals and all logs.
capture(HERE, "capability-collection", [sys.executable, str(HERE / "capability_review.py"), "collect"])
capture(HERE, "capability-audit", [sys.executable, str(HERE / "capability_review.py"), "audit"])
capability = json.loads((HERE / "capability/audit.json").read_text())
assert capability["status"] == "passed-retained-host-artifact-audit"
receipt = {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "argv": sys.argv, "python": sys.version, "source_revision": audit.SHA,
    "run_id": audit.RUN, "run_url": terminal["url"], "status": "all-five-jobs-and-retained-host-artifacts-pass",
    "successful_jobs": len(terminal["jobs"]), "successful_steps": sum(len(j["steps"]) for j in terminal["jobs"]),
    "retries_executed": 0, "core": {k: core[k] for k in ("id", "sha256", "members", "member_bytes")},
    "JVM": {k: jvm[k] for k in ("id", "sha256", "members", "member_bytes")},
    "capability": {k: capability[k] for k in ("id", "sha256", "members", "member_bytes")},
    "binding_cases_per_mode": 39, "binding_command_logs_per_mode": 51,
    "limits": ["Core library/build-log and capability native-library/tool/9 native command logs are receipt-only hashes", "JVM environment class hashes only; other two closures retain 581 class members", "TSAN covers the Swift host harness, not Rust archive", "No new native runtime, public V2, signed package, FieldLog or GA qualification"],
    "cleanup": {"artifacts_extracted_or_executed": False, "native_or_capture_processes_started_or_queried": False, "children_reaped": True},
}
(HERE / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
