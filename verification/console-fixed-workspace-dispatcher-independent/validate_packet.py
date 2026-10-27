#!/opt/homebrew/opt/python@3.14/bin/python3.14
"""Read-only bounded metadata/hash audit; writes only this lane's validation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PRODUCER = ROOT / "verification/console-fixed-workspace-dispatcher"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verified(path, entry):
    return path.stat().st_size == entry["bytes"] and digest(path) == entry["sha256"]


def main():
    plan_path = OUT / "execution-plan.json"
    plan = json.loads(plan_path.read_text())
    release = json.loads((OUT / "host-execution-release.json").read_text())
    receipt = json.loads((OUT / "host-receipt.json").read_text())
    pre = json.loads((OUT / "preexecution-freeze.json").read_text())
    output = (OUT / "host.stdout.txt").read_bytes()
    producer = json.loads((PRODUCER / "freeze.json").read_text())
    checks = []

    def check(name, passed, **details):
        checks.append({"name": name, "pass": bool(passed), **details})

    check("preexecution_inputs_unchanged", all(verified(ROOT / e["path"], e) for e in pre["files"]), count=len(pre["files"]))
    check("root_release_matches_plan", release.get("released") is True and release.get("execution_plan_sha256") == digest(plan_path))
    check("runner_pinned", digest(OUT / "run_host_tests.py") == plan["runner_sha256"])
    check("test_roster_frozen_eight_only", len(plan["independent_roster"]) == 8 and len(plan["selected_test_sources"]) == 1)
    all_pins = plan["tool_files"] + plan["ordinary_source_closure"] + plan["new_product_sources"] + plan["selected_test_sources"]
    all_pins += [entry for dep in plan["dependencies"] for entry in dep["files"]]
    def resolve(entry):
        path = Path(entry["path"])
        return path if path.is_absolute() else ROOT / path
    check("all983_original_pins_current", len(all_pins) == 983 and all(verified(resolve(e), e) for e in all_pins), count=len(all_pins))
    check("producer90_member_seal_intact", digest(PRODUCER / "freeze.json") == plan["producer_freeze"]["sha256"] and len(producer["members"]) == 90 and all(verified(PRODUCER / e["path"], e) for e in producer["members"]), count=len(producer["members"]))
    check("host_output_exact", len(output) == receipt["output_bytes"] and hashlib.sha256(output).hexdigest() == receipt["output_sha256"])
    results = [line.removeprefix("RESULT ") for line in output.decode().splitlines() if line.startswith("RESULT ")]
    check("eight_passed_no_skips", len(results) == 1 and json.loads(results[0]) == {"total": 8, "failures": 0, "excluded": 0, "skipped": 0})
    check("zero_compile_runtime_warnings", b"COMPILED 35 ordinary/new modules; compile_warnings=0 runtime_warnings=0" in output)
    check("host_success", receipt["status"] == "passed" and receipt["exit_code"] == 0 and receipt["runner_error"] is None)
    check("bounded_execution", receipt["child_elapsed_seconds"] <= 55 and receipt["limits"] == plan["limits"])
    check("owned_cleanup_complete", receipt["scratch_removed"] is True and not Path(receipt["scratch"]).exists() and receipt["direct_child_reaped"] is True and receipt["owned_group_absent"] is True and receipt["cleanup_error"] is None)
    check("postrun983_unchanged", receipt["postrun_original_hashes_verified"] == 983 and receipt["postrun_original_changes"] == [])
    check("no_external_or_paused_resources", receipt["no_native_capture_database_container_network_resources_started"] is True)
    result = {"schema": 1, "at": datetime.now(timezone.utc).isoformat(), "status": "passed" if all(c["pass"] for c in checks) else "failed", "command": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", "verification/console-fixed-workspace-dispatcher-independent/validate_packet.py"], "python": sys.version, "source_revision": plan["source_revision"], "source_tree": plan["source_tree"], "checks": checks, "findings": [], "acceptance_scope": "Independent selected source review and eight isolated adversarial component host controls only", "pending": plan["pending"], "GA_verified": 0}
    (OUT / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "checks": len(checks), "findings": []}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
