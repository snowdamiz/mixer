"""Finite split collection/audit/acceptance with exact committed source binding."""
import datetime
import json
from pathlib import Path
import subprocess
import sys

import audit

HERE = Path(__file__).resolve().parent
EXPECTED_TREE = "93cc6868f445fa98c170acf771db73e50d90b4e2"
FIXTURE = "verification/github-delivery-selected-adoption-descriptor-review/fixture-artifact-audit"
FIXTURE_ACCEPTANCE = "3d8ed9afce6751cb05e0f2b89927ddbea3738dd5da102926dee6818fb321732c"
FIXTURE_SEAL = "179c574f004a4bf0e48d36bab3cb929e9fde6bb145769fe97031125e9cbc0ed7"
EXPECTED_JOBS = {"swift", "swift-capability-native", "vm", "services", "android-owner-host", "swift-cache-state-fixture"}
assert __debug__ and not (HERE / "acceptance.json").exists()


def capture(name, argv, stdout_file=None):
    assert not (HERE / (name + ".command.json")).exists()
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    child = subprocess.Popen(argv, cwd=audit.REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = child.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        timed_out = True
        child.kill()
        stdout, stderr = child.communicate(timeout=2)
    stdout_file = stdout_file or (name + ".stdout")
    (HERE / stdout_file).write_bytes(stdout)
    (HERE / (name + ".stderr")).write_bytes(stderr)
    (HERE / (name + ".command.json")).write_text(json.dumps({
        "started_utc": start, "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "argv": argv, "cwd": str(audit.REPO), "exit_code": child.returncode,
        "stdout_file": stdout_file, "stdout": audit.digest(stdout), "stderr": audit.digest(stderr),
        "timed_out": timed_out, "child_timeout_seconds": 55, "direct_child_reaped": child.poll() is not None,
        "scope": "Read-only terminal CI, artifact download or exact committed source inspection; child belongs to owned phase process group",
    }, indent=2) + "\n")
    assert child.returncode == 0 and not timed_out, (name, child.returncode)
    return stdout


def validate_terminal():
    run = json.loads((HERE / "ci-run-api.stdout").read_bytes())
    terminal = json.loads((HERE / "ci-terminal.stdout").read_bytes())
    jobs = json.loads((HERE / "ci-jobs-api.stdout").read_bytes())
    assert run["id"] == audit.RUN and run["head_sha"] == audit.SHA
    assert run["status"] == "completed" and run["conclusion"] == "success" and run["run_attempt"] == 1
    assert run["event"] == "push" and run["head_branch"] == "main" and run["head_repository"]["full_name"] == "snowdamiz/mixer"
    assert terminal["status"] == "completed" and terminal["conclusion"] == "success" and terminal["headSha"] == audit.SHA
    assert {j["name"] for j in terminal["jobs"]} == EXPECTED_JOBS and len(terminal["jobs"]) == 6
    assert sum(len(j["steps"]) for j in terminal["jobs"]) == 64
    assert all(j["status"] == "completed" and j["conclusion"] == "success" and all(s["conclusion"] == "success" for s in j["steps"]) for j in terminal["jobs"])
    assert jobs["total_count"] == len(jobs["jobs"]) == 6
    assert {j["name"] for j in jobs["jobs"]} == EXPECTED_JOBS
    assert {j["id"] for j in jobs["jobs"]} == {j["databaseId"] for j in terminal["jobs"]}
    assert sum(len(j["steps"]) for j in jobs["jobs"]) == 64
    assert all(j["status"] == "completed" and j["conclusion"] == "success" and j["head_sha"] == audit.SHA and j["run_attempt"] == 1 and all(s["status"] == "completed" and s["conclusion"] == "success" for s in j["steps"]) for j in jobs["jobs"])
    assert audit.SHA.encode() in (HERE / "ci-full-log.stdout").read_bytes()
    assert (HERE / "source-tree.stdout").read_text().strip() == EXPECTED_TREE
    assert audit.digest((HERE / "workflow-source.stdout").read_bytes())["sha256"] == audit.WORKFLOW_HASH
    return run, terminal, jobs


def fixture():
    path = audit.REPO / FIXTURE
    assert audit.digest((path / "acceptance.json").read_bytes())["sha256"] == FIXTURE_ACCEPTANCE
    assert audit.digest((path / "seal.json").read_bytes())["sha256"] == FIXTURE_SEAL
    seal = json.loads((path / "seal.json").read_bytes())
    row, = [m for m in seal["members"] if m["path"] == "acceptance.json"]
    assert row["sha256"] == FIXTURE_ACCEPTANCE
    return {"path": FIXTURE + "/acceptance.json", "sha256": FIXTURE_ACCEPTANCE, "seal_sha256": FIXTURE_SEAL,
            "scope": "Actual Rust 1.98.1 closed host fixture separately audited and sealed; not rerun here"}


def collect():
    fixture()
    capture("gh-version", ["gh", "--version"])
    capture("git-version", ["git", "--version"])
    capture("ci-run-api", ["gh", "api", f"repos/snowdamiz/mixer/actions/runs/{audit.RUN}"])
    capture("ci-terminal", ["gh", "run", "view", str(audit.RUN), "--repo", "snowdamiz/mixer", "--json", "status,conclusion,headSha,jobs,url"])
    capture("ci-jobs-api", ["gh", "api", f"repos/snowdamiz/mixer/actions/runs/{audit.RUN}/jobs?per_page=100"])
    capture("ci-full-log", ["gh", "run", "view", str(audit.RUN), "--repo", "snowdamiz/mixer", "--log"])
    capture("source-tree", ["git", "rev-parse", audit.SHA + "^{tree}"])
    capture("workflow-source", ["git", "show", audit.SHA + ":.github/workflows/verify.yml"])
    validate_terminal()
    metadata = json.loads(capture("artifact-metadata", ["gh", "api", f"repos/snowdamiz/mixer/actions/runs/{audit.RUN}/artifacts?per_page=100"]))
    assert metadata["total_count"] == len(metadata["artifacts"])
    for name in ("swift-core-toolchain-host", "android-owner-host"):
        artifact, = [a for a in metadata["artifacts"] if a["name"] == name + "-" + audit.SHA]
        capture(name, ["gh", "api", f"repos/snowdamiz/mixer/actions/artifacts/{artifact['id']}/zip"], name + ".zip")
    print(json.dumps({"status": "fresh-terminal-data-collected", "run_id": audit.RUN, "jobs": 6, "steps": 64, "run_attempt": 1}))


def core_jvm():
    validate_terminal()
    core, jvm = audit.audit_core(), audit.audit_jvm()
    audit.write_json("source-blobs.json", audit.SOURCE_RECORDS)
    audit.write_json("core-jvm-audit.json", {
        "core": core, "jvm": jvm, "source_revision": audit.SHA, "source_tree": EXPECTED_TREE, "run": audit.RUN,
        "source_blobs": audit.digest((HERE / "source-blobs.json").read_bytes()),
        "source_commands": audit.digest((HERE / "source-commands.json").read_bytes()),
        "auditor": audit.digest((HERE / "audit.py").read_bytes()), "python": sys.version,
    })
    print(json.dumps({"status": "core-JVM-audit-passed", "source_paths": len(audit.SOURCE_RECORDS), "JVM_closures": len(jvm["closures"])}))


def accept():
    run, terminal, jobs = validate_terminal()
    prior_phases = ("terminal-collection", "core-jvm-audit", "capability-collection", "capability-audit")
    phase_records = []
    for name in prior_phases:
        row = json.loads((HERE / (name + ".command.json")).read_bytes())
        assert row["exit_code"] == 0 and not row["timed_out"] and row["direct_child_reaped"] and row["owned_process_group_absent_after_reaping"]
        phase_records.append({"path": name + ".command.json", **audit.digest((HERE / (name + ".command.json")).read_bytes())})
    core_jvm = json.loads((HERE / "core-jvm-audit.json").read_bytes())
    assert core_jvm["source_revision"] == audit.SHA and core_jvm["source_tree"] == EXPECTED_TREE and core_jvm["run"] == audit.RUN
    core, jvm = core_jvm["core"], core_jvm["jvm"]
    capability = json.loads((HERE / "capability/audit.json").read_bytes())
    assert capability["status"] == "passed-retained-host-artifact-audit"
    assert capability["source_revision"] == audit.SHA and capability["source_tree"] == EXPECTED_TREE and capability["run_id"] == audit.RUN
    assert [{k: m[k] for k in ("mode", "cases_verified", "command_log_digests_verified")} for m in capability["modes"]] == [
        {"mode": m, "cases_verified": 39, "command_log_digests_verified": 51} for m in ("debug", "release", "tsan")]
    receipt = {
        "schema": 2, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "argv": sys.argv, "python": sys.version,
        "source_revision": audit.SHA, "source_tree": EXPECTED_TREE, "workflow_sha256": audit.WORKFLOW_HASH,
        "run_id": audit.RUN, "run_url": terminal["url"], "run_attempt": run["run_attempt"],
        "status": "all-six-jobs-and-retained-host-artifacts-pass", "successful_jobs": 6, "successful_steps": 64, "retries_executed": 0,
        "scope": "Fresh terminal CI status and data-only retained core/JVM/capability host artifact audit against exact committed source bytes",
        "job_statuses": [{"name":j["name"], "id":j["id"], "status":j["status"], "conclusion":j["conclusion"], "steps":len(j["steps"])} for j in jobs["jobs"]],
        "full_ci_log": {**audit.digest((HERE / "ci-full-log.stdout").read_bytes()), "path":"ci-full-log.stdout", "qualification":"Retained terminal CI context; passing steps are GitHub statuses, not independent reexecution"},
        "core": {k: core[k] for k in ("id", "sha256", "members", "member_bytes")},
        "JVM": {k: jvm[k] for k in ("id", "sha256", "members", "member_bytes")},
        "capability": {k: capability[k] for k in ("id", "sha256", "members", "member_bytes")},
        "binding_cases_per_mode": 39, "binding_command_logs_per_mode": 51,
        "JVM_exact_committed_source_counts": [c["sources_bound_to_exact_commit_bytes"] for c in jvm["closures"]],
        "JVM_retained_class_counts": [c["retained_class_bytes_verified"] for c in jvm["closures"]],
        "phase_records": phase_records, "separate_fixture_artifact_acceptance": fixture(),
        "historical_parent_failed_collection": json.loads((HERE / "prior-failure.json").read_bytes()),
        "limits": [
            "Core library/build-log and capability native-library/tool/9 native command logs are receipt-only hashes",
            "JVM environment class hashes only; other two closures retain 581 class members",
            "TSAN covers the Swift host harness, not Rust archive",
            "Other workflow artifact families were not downloaded or audited; this acceptance covers the three selected core/JVM/capability archives",
            "Historical parent failed collection is diagnostic only; its descendant reaping remains unverified and its outputs provide no accepted phase provenance",
            "No new native runtime, UI, screen capture, physical device, simulator/emulator, public V2, signed package, FieldLog or GA qualification",
        ],
        "cleanup": {"artifacts_extracted_or_executed": False, "native_or_capture_processes_started_or_queried": False,
                    "accepted_audit_phase_children_reaped": True, "accepted_audit_phase_process_groups_absent": True,
                    "historical_parent_failed_collection_descendant_reaping_verified": False, "git_mutations": False, "network_mutations": False},
    }
    (HERE / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "source_revision": audit.SHA, "run_id": audit.RUN, "successful_jobs": 6, "successful_steps": 64}))


{"collect": collect, "core-jvm": core_jvm, "accept": accept}[sys.argv[1]]()
