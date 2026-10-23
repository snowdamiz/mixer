#!/usr/bin/env python3
"""Record this artifact-only contract review. Never invokes an engine operation."""
from __future__ import annotations

from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE = "39199ae5475de5d03926807ce60add5dcb0741c2"
ORIGINAL_RECEIPT = "62f825ab418b207c057f384b2c0afdbfabb3fee50e0db75e945f0d3448f092de"
CONTROL_OVERLAY = "55e0e89c5da57347f02fd13dfb97296c19c3ace7d94fc11109dd224c9046b79f"
CACHE_FREEZE = "7214cb876a18df7ddedc364acc52f57cc04b2b8916968ef360ee4a0eb7f28089"
DOC = "docs/swift-executor-stage-contract.md"
SOURCE_PATHS = [
    "AGENTS.md", "mixer-product-plan.md", "vm/Cargo.toml", "vm/Cargo.lock",
    "vm/src/lib.rs", "vm/src/execute.rs", "vm/src/float.rs",
    "vm/src/experimental/mod.rs", "vm/src/experimental/account.rs",
    "vm/src/experimental/descriptors.rs", "vm/src/experimental/metadata.rs",
    "vm/src/experimental/policy.rs", "vm/src/experimental/swift.rs",
    "vm/src/experimental/execution/mod.rs", "vm/src/experimental/cache/mod.rs",
    "vm/src/experimental/cache/decode.rs", "vm/src/experimental_swift_reactor/mod.rs",
    "vm/src/experimental_swift_reactor/control.rs",
    "vm/src/experimental_swift_reactor/control_tests.rs",
    "vm/src/experimental_wasi/mod.rs", "vm/src/experimental_wasi/accounted.rs",
    "vm/src/experimental_wasi/descriptor.rs", "vm/src/experimental_wasi/platform.rs",
]
REFERENCES = [
    "docs/swift-reactor-execution-stage-design.md", "docs/swift-cache-stage-contract.md",
    "verification/swift-reactor-execution-design-review/receipt.json",
    "verification/swift-reactor-validation/2026-10-23-final-v2/receipt.json",
    "verification/swift-runtime-control-root-review/receipt.json",
    "verification/swift-accounted-wasi-root-review/receipt.json",
    "verification/swift-execution-descriptors/final-review.json",
    "verification/swift-cache-prerequisites-root-review/receipt.json",
    "verification/swift-cache-stage-acceptance.json",
    "verification/swift-cache-stage-contract/acceptance.json",
    "verification/swift-instruction-observation/acceptance.json",
    "verification/swift-instruction-observation-review/receipt.json",
    "verification/swift-observation-accounting/acceptance.json",
    "verification/swift-observation-accounting-review/receipt.json",
    "verification/swift-executor-contract-review/decision.json",
    "verification/swift-executor-contract-review/review.md",
    "verification/swift-executor-contract-review/foundation-tail-addendum.md",
    "verification/swift-executor-contract-review/observation-chain-map.json",
    "verification/swift-executor-contract-review/layout-receipt.json",
    "verification/github-ci-3a1bb5a/receipt.json",
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def describe(path: str) -> dict:
    data = (ROOT / path).read_bytes()
    return {"path": path, "bytes": len(data), "sha256": digest(data)}


def write_json(name: str, value) -> None:
    (HERE / name).write_text(json.dumps(value, indent=2) + "\n")


def run(name: str, argv: list[str]) -> dict:
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, check=False)
    outputs = {}
    for stream, data in (("stdout", result.stdout), ("stderr", result.stderr)):
        path = HERE / f"{name}.{stream}.txt"
        path.write_bytes(data)
        outputs[stream] = describe(str(path.relative_to(ROOT)))
    return {"argv": argv, "cwd": str(ROOT), "exit_code": result.returncode, **outputs}


def main() -> None:
    # Document content is the frozen proposal; update only its binding, not content.
    manifest_path = HERE / "acceptance.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["document"]["sha256"] = describe(DOC)["sha256"]
    write_json("acceptance.json", manifest)
    changes = []
    for path in [DOC, str((HERE / "acceptance.json").relative_to(ROOT)),
                 str((HERE / "check_contract.py").relative_to(ROOT)),
                 str((HERE / "collect.py").relative_to(ROOT))]:
        original = (HERE / "historical-v1" / path).read_text().splitlines(keepends=True)
        current = (ROOT / path).read_text().splitlines(keepends=True)
        changes.extend(difflib.unified_diff(original, current,
                       fromfile="historical-v1/" + path, tofile=path))
    (HERE / "revision2-changes.diff").write_text("".join(changes))
    validation = json.loads((ROOT / REFERENCES[3]).read_text())
    rustc = validation["rustcExecutable"]["path"]
    cargo = validation["cargoExecutable"]["path"]
    commands = []
    for name, argv in [
        ("git-version", ["git", "--version"]),
        ("rustc-version", [rustc, "--version", "--verbose"]),
        ("cargo-version", [cargo, "--version"]),
        ("python-version", [sys.executable, "--version"]),
        ("revision", ["git", "rev-parse", "HEAD"]),
        ("dirty-tree", ["git", "status", "--porcelain=v1", "--untracked-files=all"]),
        ("contract-check", [sys.executable, "-B", str(HERE / "check_contract.py")]),
        ("contract-mutations", [sys.executable, "-B", str(HERE / "check_contract.py"), "--mutation-checks"]),
        ("owned-diff-check", ["git", "diff", "--check", "--", DOC, str(HERE.relative_to(ROOT))]),
    ]:
        commands.append(run(name, argv))
    sources = []
    for path in SOURCE_PATHS:
        result = subprocess.run(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT,
                                capture_output=True, check=True)
        working = (ROOT / path).read_bytes()
        sources.append({"path": path, "revision": BASELINE, "bytes": len(result.stdout),
                        "sha256": digest(result.stdout), "working_sha256": digest(working),
                        "working_matches_baseline": working == result.stdout})
    encoded = json.dumps(sources, sort_keys=True, separators=(",", ":")).encode()
    write_json("source-manifest.json", {"scope": "explicit baseline source subset, not an engine acceptance tree",
               "revision": BASELINE, "files": sources, "manifest_entries_sha256": digest(encoded)})
    references = [describe(path) for path in REFERENCES]
    observation = json.loads((ROOT / "verification/swift-observation-accounting/acceptance.json").read_text())
    instruction = json.loads((ROOT / "verification/swift-instruction-observation/acceptance.json").read_text())
    freeze = json.loads((ROOT / "verification/swift-cache-stage-acceptance.json").read_text())
    chains = json.loads((ROOT / "verification/swift-executor-contract-review/observation-chain-map.json").read_text())
    ci = json.loads((ROOT / "verification/github-ci-3a1bb5a/receipt.json").read_text())
    assert observation["accepted"] is True and instruction["accepted"] is True
    assert observation["independent_bindings"] == 522 and observation["producer_bindings"] == 859
    assert observation["source_overlays"]["vm/src/experimental_swift_reactor/control.rs"] == CONTROL_OVERLAY
    assert describe("verification/swift-cache-stage-acceptance.json")["sha256"] == CACHE_FREEZE
    assert freeze["schema"] == "mixer-swift-cache-bounded-implementation-freeze-v3"
    assert freeze["foundation_named_counts"] == manifest["cleanup"]["foundation_counts"]
    assert chains["max_control_parameters"] == 5 and chains["retained_caller_shapes"] == 1
    assert chains["proposed_named_optional_count"] == 6
    assert len(ci["jobs"]) == 3 and all(job["conclusion"] == "success" for job in ci["jobs"])
    control = next(entry for entry in sources if entry["path"] == "vm/src/experimental_swift_reactor/control.rs")
    assert control["sha256"] == CONTROL_OVERLAY, "committed source differs from accepted correction"
    original = HERE / "historical-v1/verification/swift-executor-stage-contract/receipt.json"
    assert digest(original.read_bytes()) == ORIGINAL_RECEIPT
    assert validation["valid"] is True and validation["executed"] is False
    assert validation["artifact"]["sha256"] == "24d85729a659ff3e5fc6f0517709afbb68b371a41829e90785dabd48e0620994"
    assert validation["validation"]["defined_functions"] == 79832
    assert validation["validation"]["work_used"] == 188428924
    revision = (HERE / "revision.stdout.txt").read_text().strip()
    dirty = (HERE / "dirty-tree.stdout.txt").read_text()
    receipt = {
        "schema": "mixer.swift-executor-stage-contract-receipt.v2",
        "proposal_revision": 2,
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "collector_command": [sys.executable, "-B", str(HERE / "collect.py")],
        "scope": "Proposal/artifact consistency and static source review only. No engine build/test, full validation, instantiation, initialize, invoke or device operations.",
        "agent": {"model": "gpt-6.1-sol", "reasoning_effort": "xhigh", "fresh_context": True},
        "python_version": platform.python_version(), "platform": platform.platform(),
        "tool_binaries": [{"path": path, "sha256": digest(Path(path).read_bytes())}
                          for path in (rustc, cargo, sys.executable)],
        "baseline_revision": BASELINE, "observed_revision": revision,
        "dirty_tree": dirty.splitlines(),
        "source_binding": describe(str((HERE / "source-manifest.json").relative_to(ROOT))),
        "history_preservation": describe(str((HERE / "historical-v1/preservation.json").relative_to(ROOT))),
        "original_v1_receipt_sha256": ORIGINAL_RECEIPT,
        "reference_bindings": references,
        "artifact_bindings": [describe(path) for path in [DOC,
            str((HERE / "acceptance.json").relative_to(ROOT)),
            str((HERE / "check_contract.py").relative_to(ROOT)),
            str((HERE / "collect.py").relative_to(ROOT)),
            str((HERE / "revision2-changes.diff").relative_to(ROOT))]],
        "commands": commands,
        "historical_full_target_validation": {"rerun": False, "valid": True, "executed": False,
             "artifact": validation["artifact"], "validation": validation["validation"]},
        "source_reviewed": [
            "legacy execution initialization/allocation/reservation/work/fuel and dispatch algorithms",
            "legacy per-frame cache pins, import/call/return/branch/indirect/numeric and growth order",
            "accepted retained-source descriptors and absolute initializer/segment cursors",
            "single control ledger/phase/first-failure and accounted WASI dispatch/cleanup semantics",
            "accepted overarching and v3 cache contracts; cache evolving implementation is unaccepted",
            "independent R1 review and superseding exhaustive five-parameter plus one caller map",
            "accepted six-Option foundation correction and independently accepted instruction/fuel methods",
        ],
        "historical_v1_artifact_check_attempts": [{
            "exit_code": 1,
            "reason": "Two literal helper-name document anchors missing; doc now explicitly lists work_with_wasi and drop_reserved_with_wasi. Artifact checker issue only.",
            "engine_operation": False,
        }, {
            "exit_code": 1,
            "reason": "Collector version probe could not find rustc on PATH; use exact installed tool binaries already identified by canonical validation receipt. No engine operation attempted.",
            "engine_operation": False,
        }],
        "revision2_prior_artifact_check_failures": [],
        "artifact_checks_passed": all(command["exit_code"] == 0 for command in commands),
        "implementation_tests_executed": 0,
        "synthetic_functions_pending": 20, "runtime_layout_measurements": [],
        "cache_implementation_accepted": False, "observed_fuel_control_delta_accepted": True,
        "foundation_observation_correction_accepted": True,
        "accepted_foundation": manifest["accepted_foundation"],
        "accepted_cache_contract": manifest["accepted_cache_contract"],
        "cleanup_observation_assignment": manifest["cleanup"]["observation_assignment"],
        "implementation_sequence": manifest["implementation_sequence"],
        "hosted_ci_scope": {"revision": ci["revision"], "jobs": ci["jobs"],
                            "limit": "3a1bb5a instruction/fuel checkpoint only; predates six-Option correction"},
        "target_execution_authorized": False, "target_executed": False,
        "device_operations": [], "commits_or_pushes": [], "ga_gate_changes": [],
        "limitations": manifest["explicit_pending"],
        "no_dependency_added": True,
        "review_status": "revision 2 addresses R1 and superseding six-Option addendum; ready for root review; no implementation acceptance",
    }
    write_json("receipt.json", receipt)
    write_json("proposal-receipt.json", receipt)
    print(json.dumps({"artifact_checks_passed": receipt["artifact_checks_passed"],
                      "commands": len(commands), "source_files": len(sources),
                      "reference_bindings": len(references), "synthetic_functions_pending": 20,
                      "implementation_tests_executed": 0, "target_executed": False}, indent=2))
    raise SystemExit(0 if receipt["artifact_checks_passed"] else 1)


if __name__ == "__main__":
    main()
