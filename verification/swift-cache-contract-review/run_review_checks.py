#!/usr/bin/env python3
"""Retain bounded contract-review evidence; never instantiate the full reactor."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ENV = dict(os.environ)
ENV["PATH"] = "/opt/homebrew/opt/rustup/bin:" + ENV.get("PATH", "")
FILES = [
    "AGENTS.md", "mixer-product-plan.md", "docs/swift-reactor-execution-stage-design.md",
    "docs/swift-cache-stage-contract.md", "verification/swift-cache-stage-contract/acceptance.json",
    "verification/swift-cache-stage-contract/proposal-receipt.json",
    "verification/swift-cache-stage-contract/check_contract.py",
    "verification/swift-cache-stage-contract/artifact_checks.py",
    "vm/Cargo.toml", "vm/Cargo.lock", "vm/src/experimental/cache/mod.rs",
    "vm/src/experimental/cache/decode.rs", "vm/src/experimental/cache/tests.rs",
    "vm/src/experimental/descriptors.rs", "vm/src/experimental/swift.rs",
    "vm/src/experimental/policy.rs", "vm/src/experimental/metadata.rs",
    "vm/src/experimental_swift_reactor/control.rs", "vm/src/experimental_wasi/accounted.rs",
    "vm/tests/swift_reactor_validation.rs", "vm/tests/swift_reactor_validation_fixture.rs",
]


def inventory():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}


def command(argv):
    completed = subprocess.run(argv, cwd=ROOT, env=ENV, text=True, capture_output=True)
    return {"argv": argv, "resolved_executable": shutil.which(argv[0], path=ENV["PATH"]),
            "exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def main():
    before = inventory()
    receipt = {
        "schema": "mixer-swift-cache-contract-independent-review-v1",
        "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "Independent proposal/current-source review, artifact consistency and existing small synthetic regression tests only",
        "revision_before": command(["git", "rev-parse", "HEAD"]),
        "dirty_before": command(["git", "status", "--short"]),
        "source_before": before,
        "source_before_sha256": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
        "commands": [],
        "review_decision": "cache_contract_refinement_required_descriptor_prerequisite_may_proceed",
        "target_instantiated": False, "device_discovery_or_runs": False,
        "publication_commits_or_pushes": False, "product_or_proposal_modified": False,
        "cache_engine_acceptance": "pending; implementation absent",
        "limitations": ["Concurrent lanes may change HEAD or source; before/after manifests are retained.",
                        "Existing legacy/validator tests do not test a Swift cache implementation.",
                        "No allocator, transient-layout, target-performance, physical-device, published-consumer or GA acceptance follows."],
    }
    commands = [["python3", "--version"], ["rustc", "-Vv"], ["cargo", "-V"],
                ["python3", "-B", "verification/swift-cache-stage-contract/check_contract.py"],
                ["python3", "-B", "verification/swift-cache-stage-contract/artifact_checks.py", "-v"]]
    base = ["cargo", "test", "--locked", "--manifest-path", "vm/Cargo.toml", "--features",
            "experimental-swift-reactor,experimental-span-execution"]
    for release in (False, True):
        mode = ["--release"] if release else []
        commands.append(base + mode + ["--lib", "experimental::cache::tests", "--", "--nocapture"])
        commands.append(base + mode + ["--test", "swift_reactor_validation",
                        "independent_signature_aggregate_local_operand_and_control_ceilings", "--", "--exact", "--nocapture"])
    for argv in commands:
        result = command(argv)
        if argv[0] == "cargo" and "test" in argv:
            output = result["stdout"] + result["stderr"]
            count = 3 if "--lib" in argv else 1
            result["expected_test_count"] = count
            result["expected_tests_passed"] = bool(re.search(
                rf"^test result: ok\. {count} passed; 0 failed; 0 ignored;", output, re.MULTILINE))
        receipt["commands"].append(result)
    receipt["source_after"] = inventory()
    receipt["reviewed_source_unchanged_during_commands"] = receipt["source_after"] == before
    receipt["revision_after"] = command(["git", "rev-parse", "HEAD"])
    receipt["dirty_after"] = command(["git", "status", "--short"])
    receipt["bounded_checks_passed"] = all(result["exit_code"] == 0 and result.get("expected_tests_passed", True)
                                           for result in receipt["commands"])
    (HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: receipt[key] for key in ("bounded_checks_passed", "reviewed_source_unchanged_during_commands",
                                                  "review_decision", "target_instantiated", "cache_engine_acceptance")}, indent=2))
    return 0 if receipt["bounded_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
