#!/usr/bin/env python3
"""Freeze/check only this PREIMPLEMENTATION artifact; never an OTA release gate."""
import datetime
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOC = ROOT / "docs/hosted-transaction-context-preflight.md"
BASELINE = "bc45a20298533b70808607b8228473b1d1efa81d"
EXCLUDED = {HERE / "artifact-manifest.json", HERE / "receipt.json", HERE / "check-output.log"}
def sha(data): return hashlib.sha256(data).hexdigest()
def load(path): return json.loads(path.read_text())
def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def artifact_files():
    return sorted([DOC] + [p for p in HERE.rglob("*") if p.is_file() and p not in EXCLUDED and "__pycache__" not in p.parts])

def validate_runs():
    run_history = []
    for name, passed, total, failures in [("run-1", True, 22, 0), ("run-2", False, 24, 1), ("run-3", True, 24, 0)]:
        run = HERE / name
        receipt, tests = load(run / "receipt.json"), load(run / "tests.json")
        assert receipt["baseline_revision"] == BASELINE
        assert receipt["passed"] is passed
        assert tests["summary"] == {"total": total, "failures": failures, "excluded": 0, "skipped": 0}
        cleanup = receipt["cleanup"]
        assert cleanup["owned_postgres_stopped"] and cleanup["owned_scratch_removed"] and cleanup["owned_socket_removed"]
        assert not cleanup["other_clusters_touched"] and not cleanup["native_processes_started"]
        assert not pathlib.Path(cleanup["owned_scratch"]).exists()
        source_manifest = load(run / "source-manifest.json")
        assert sha(canonical(source_manifest)) == receipt["probe_source_tree_digest"]
        for item in source_manifest:
            frozen = run / "inputs" / item["path"]
            assert sha(frozen.read_bytes()) == item["sha256"]
            if name == "run-3":
                assert sha((HERE / item["path"]).read_bytes()) == item["sha256"]
        packages = load(run / "dependency-source-manifest.json")
        assert {p["name"] for p in packages} == {"telemetry", "decimal", "jason", "db_connection", "ecto", "postgrex", "ecto_sql"}
        assert all(p["installed_tree_matches_accepted_archive"] for p in packages)
        if name == "run-3":
            package_files = {(p["name"], f["path"]): f["sha256"] for p in packages for f in p["copied_files"]}
            for excerpt in load(run / "primary-source-evidence.json"):
                assert package_files[(excerpt["package"], excerpt["path"])] == excerpt["source_sha256"]
            opts = [c["environment_overrides"] for c in load(run / "commands.json") if c["argv"] == ["mix", "run", "probe_test.exs"]]
            assert len(opts) == 1 and opts[0]["MIX_ENV"] == "test" and opts[0]["ERL_FLAGS"] == "+S 2:2"
            observations = tests["observations"]
            assert observations["busy_pool_nonqueued_admission"]["callback_started"] is False
            assert observations["fresh_admission_after_slot_available"]["passed"] is True
            assert observations["after_lock_read_committed_membership"]["after_lock_active"] is False
        run_history.append({"run": name, "passed": passed, "summary": tests["summary"], "cleanup_verified_again": True})
    return run_history

def main():
    history = validate_runs()
    if "--freeze" in sys.argv:
        assert not (HERE / "artifact-manifest.json").exists(), "Existing artifact freeze is immutable; do not silently replace it"
        manifest = [{"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())} for p in artifact_files()]
        (HERE / "artifact-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        receipt = {
            "schema": 1, "status": "preimplementation_seam_probe_passed_pending_root_review",
            "scope": "Host-only public transaction-context/deadline preflight; not product authorization, migration, HTTP, Neon, native, physical device, FieldLog or GA acceptance",
            "frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "accepted_baseline_revision": BASELINE,
            "accepted_baseline_tree": load(HERE / "run-3/receipt.json")["baseline_tree"],
            "passing_run": "run-3", "passing_probe_source_tree_digest": load(HERE / "run-3/receipt.json")["probe_source_tree_digest"],
            "artifact_manifest_sha256": sha((HERE / "artifact-manifest.json").read_bytes()),
            "artifact_tree_digest": sha(canonical(manifest)), "artifact_files": len(manifest),
            "runs": history,
            "freeze_command": ["python3", "verification/hosted-transaction-context-preflight/check.py", "--freeze"],
            "python_version": sys.version,
            "selected_seam": ["fixed Repo", "owning process", "captured public dynamic Repo", "fresh invocation reference", "actual backend/full xid8/database/current role", "transaction-local nonce", "queue:false admission", "fixed monotonic absolute deadline and decreasing budgets"],
            "limitations": ["BEAM callback is not killed by DBConnection deadline", "queued checkout is not bounded by transaction deadline in pinned DBConnection; use queue:false", "already-sent COMMIT may be uncertain", "trusted-process API discipline, not malicious-process protection", "synthetic superuser fixture is not runtime authorization/RLS evidence", "no live product source/dependency/tracker/commit changes by this lane", "physical phones disconnected; native checks not performed in host-only lane"],
            "independent_reviewer": "pending root review", "ga_acceptance": False,
        }
        (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    receipt = load(HERE / "receipt.json")
    manifest = load(HERE / "artifact-manifest.json")
    assert sha((HERE / "artifact-manifest.json").read_bytes()) == receipt["artifact_manifest_sha256"]
    assert sha(canonical(manifest)) == receipt["artifact_tree_digest"]
    assert [str(p.relative_to(ROOT)) for p in artifact_files()] == [item["path"] for item in manifest]
    for item in manifest:
        path = ROOT / item["path"]
        assert path.stat().st_size == item["bytes"] and sha(path.read_bytes()) == item["sha256"], item["path"]
    print(json.dumps({"passed": True, "scope": "artifact integrity and retained run assertions only; no new runtime test", "files": len(manifest), "artifact_tree_digest": receipt["artifact_tree_digest"], "passing_run": "run-3", "passing_cases": 24, "failed_attempts_retained": ["run-2"], "all_owned_scratch_absent": True}))

if __name__ == "__main__": main()
