#!/usr/bin/env python3
"""Bind completed producer commands to one immutable logical source snapshot.

This collector does not confer independent acceptance or execute any guest.
"""
import datetime
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = "39199ae5475de5d03926807ce60add5dcb0741c2"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    return json.loads((HERE / name).read_text())


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + "\n")


reg = read("qualification/regressions.json")
named = read("qualification/named/receipt.json")
extra = read("qualification/additional-reference-receipt.json")
legacy = read("legacy-parity-receipt.json")
surface = read("surface-receipt.json")
layout = read("layout-map.json")
assert reg["status"] == extra["status"] == legacy["status"] == surface["status"] == "pass"
assert named["status"] == "named_synthetic_commands_passed_review_pending"
assert len(reg["commands"]) == 21 and len(extra["commands"]) == 2
assert len(named["commands"]) == 36
assert all(c["exit_code"] == 0 for c in reg["commands"] + extra["commands"] + named["commands"])
assert all(c["exactly_one_passed"] for c in named["commands"])
assert all(c["exactly_two_passed"] for c in extra["commands"])
assert len(legacy["comparisons"]) == 4 and all(c["equal"] for c in legacy["comparisons"])
assert legacy["baseline_revision"] == BASE
assert len(surface["current_exports"]) == 28 and len(surface["headers"]) == 3
assert surface["original_exports"] == surface["current_exports"]
assert reg["unchanged_source"] and named["source_manifest"] == named["source_manifest_after"]

source = {}
for manifest in [reg["source_manifest"], named["source_manifest"], legacy["current_source_manifest"]]:
    for name, value in manifest.items():
        assert name not in source or source[name] == value, name
        assert digest((ROOT / name).read_bytes()) == value, name
        source[name] = value
assert extra["source_manifest"] == reg["source_manifest"]
source = dict(sorted(source.items()))
source_digest = digest(json.dumps(source, sort_keys=True).encode())

owned = [
    "vm/src/experimental/cache/mod.rs",
    "vm/src/experimental/cache/decode.rs",
    "vm/src/experimental/cache/borrowed.rs",
    "vm/src/experimental/cache/tests.rs",
    "vm/src/experimental_swift_reactor/cache.rs",
    "vm/src/experimental_swift_reactor/cache_tests.rs",
]
root_expected = {
    "vm/src/experimental/mod.rs": "c33b8da10f8a2b7a47b5fcece6709f10f294cc0b926f4727ab607fbdb7bc0c81",
    "vm/src/experimental/descriptors.rs": "05d35c81eaeb2d86e8bc7c63f2b0122e1286198788730a927d439cd0a2a979ae",
    "vm/src/experimental_swift_reactor/mod.rs": "427fba158aa06825914d887ed9d19649453b1b2671d5c4cd962ca7c9cced6e2c",
    "vm/src/experimental_swift_reactor/control.rs": "55e0e89c5da57347f02fd13dfb97296c19c3ace7d94fc11109dd224c9046b79f",
    "vm/src/experimental_swift_reactor/control_tests.rs": "0618d894583264b194d69f90c7a29a01a6a62f96a6118c337a508c5b910236b7",
    "vm/tests/swift_reactor_validation_allocations.rs": "5fc2aafcd477f3f9845e787116a4ab73ec68319c0aa1996090a57b95571a3cb6",
    "verification/swift-cache-stage-acceptance.json": "7214cb876a18df7ddedc364acc52f57cc04b2b8916968ef360ee4a0eb7f28089",
    "verification/swift-cache-stage-contract/proposal-receipt.json": "94476317a7bf4ea59266e7cad2f75d99bfae8196bd05abd21df4f64ed40628a3",
}
for name, value in root_expected.items():
    assert digest((ROOT / name).read_bytes()) == value, name

overlays = {}
for name, value in source.items():
    p = subprocess.run(["git", "show", BASE + ":" + name], cwd=ROOT, capture_output=True)
    original = digest(p.stdout) if p.returncode == 0 else None
    if original != value:
        overlays[name] = {"baseline_sha256": original, "frozen_sha256": value}
save("source-freeze.json", {"baseline_revision": BASE, "source_manifest": source,
                            "source_manifest_sha256": source_digest,
                            "overlays": overlays})

# Store exact source bytes with fixed archive metadata; subsequent checks use hashes.
tar_bytes = io.BytesIO()
with tarfile.open(fileobj=tar_bytes, mode="w") as archive:
    for name, value in source.items():
        data = (ROOT / name).read_bytes()
        assert digest(data) == value
        item = tarfile.TarInfo(name)
        item.size = len(data)
        item.mode = 0o644
        item.mtime = 0
        archive.addfile(item, io.BytesIO(data))
with (HERE / "frozen-source.tar.gz").open("wb") as output:
    with gzip.GzipFile(fileobj=output, mode="wb", mtime=0, filename="") as zipped:
        zipped.write(tar_bytes.getvalue())

plan = json.loads((ROOT / "verification/swift-cache-stage-contract/acceptance.json").read_text())
test_source = (ROOT / owned[-1]).read_text()
tests = []
for test in plan["tests"]:
    name = test["name"]
    function = re.search(r"^fn " + re.escape(name) + r"\(", test_source, re.M)
    assert function is not None, name
    selections = [i for i, c in enumerate(named["commands"])
                  if any(a.endswith("::" + name) for a in c["argv"])]
    assert len(selections) == 2
    assert ["--release" in named["commands"][i]["argv"] for i in selections] == [False, True]
    tests.append({"name": name, "source": owned[-1], "line": test_source[:function.start()].count("\n") + 1,
                  "named_command_indices": selections, "executed_modes": ["debug", "release"],
                  "contract_assertions": test["assertions"], "independent_assertion_review": "pending"})
save("coverage-map.json", {"scope": "execution mapping; assertion adequacy still requires independent review",
                          "tests": tests})

artifact_names = [
    "qualification/regressions.json", "qualification/named/receipt.json",
    "qualification/additional-reference-receipt.json", "legacy-parity-receipt.json",
    "surface-receipt.json", "layout-map.json", "layout-map.md", "coverage-map.json",
    "source-freeze.json", "frozen-source.tar.gz", "qualify.py",
    "qualify_additional_references.py", "check_legacy_parity.py", "check_surface.py",
    "build_layout_map.py", "finalize.py", "README.md",
    "qualification-attempt-1/regressions.json", "validation-deadline-isolated-retry.log",
    "observation-tail-revision-proposal.md",
]
bindings = {str((HERE / name).relative_to(ROOT)): digest((HERE / name).read_bytes()) for name in artifact_names}
for name in [
    "verification/swift-cache-stage-acceptance.json",
    "verification/swift-cache-stage-contract/proposal-receipt.json",
    "verification/swift-cache-stage-contract/acceptance.json",
    "verification/swift-observation-accounting/acceptance.json",
    "verification/swift-validation-deadline-repair/isolated-2/receipt.json",
    "docs/swift-cache-stage-contract.md", "docs/swift-reactor-execution-stage-design.md",
]:
    bindings[name] = digest((ROOT / name).read_bytes())
matrix = [{"argv": c["argv"], "passed": c["total_passed"]} for c in reg["commands"][:16]]
receipt = {
    "schema": "mixer-private-swift-function-cache-producer-v1",
    "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "status": "producer_commands_passed_independent_acceptance_pending",
    "baseline_revision": BASE,
    "source_manifest_sha256": source_digest,
    "source_manifest": "verification/swift-function-cache/source-freeze.json",
    "owned_source_sha256": {name: source[name] for name in owned},
    "root_owned_frozen_sha256": root_expected,
    "regression_source_manifest_sha256": reg["source_manifest_sha256"],
    "named_source_manifest_sha256": named["source_manifest_sha256"],
    "tools": reg["tools"],
    "feature_matrix": matrix,
    "qualification": {"regression_commands": 21, "supplemental_reference_commands": 2,
                      "named_commands": 36, "named_tests_per_mode": 18,
                      "explicit_ignored_reference_tests_per_mode": 9,
                      "legacy_comparisons": legacy["comparisons"],
                      "native_exports_unchanged": 28, "native_headers_unchanged": 3},
    "layout": {"cleanup": 36760, "header": 37088, "construction": 31880,
               "operation": 21120, "foundation": 16504,
               "accounting": "named logical Rust object and requested payload model; not compiler-stack or RSS"},
    "historical_observations": [
        {"path": "verification/swift-function-cache/qualification-attempt-1/regressions.json",
         "result": "Existing 10 ms validation-allocation deadline probe expired before injected ordinal; preserved original failure. Separate root-owned test-only bounded retry repair is bound above; final matrix passes."},
        {"path": "verification/swift-function-cache/observation-tail-revision-proposal.md",
         "result": "Initial two-Optional last-use proposal rejected. Accepted root v3 foundation uses six Option<WasiUsage>; cache uses its exact source and no assumed slack."},
        {"result": "Initial grouped ignored-reference commands selected 7 tests; supplemental table-memory commands each execute 2, completing 9 per mode."},
    ],
    "bindings": bindings,
    "pending": ["independent cache implementation source/assertion/accounting review and root acceptance",
                "executor implementation and composed final-tail accounting",
                "53,777,114-byte target instantiation/initialization/invocation and target performance",
                "physical iOS/Android runs (phones disconnected)",
                "immutable published package consumer/dogfood, signing, stores, release and GA gates"],
    "limits": {"target_instantiated": False, "target_initialized": False, "target_invoked": False,
               "physical_devices_discovered_or_run": False, "public_execution_route_added": False,
               "dependencies_added": False, "commits_or_pushes_by_cache_agent": False,
               "ga_gate_state_changes": 0},
}
assert layout["exclusive_cache_header"]["total"] == receipt["layout"]["header"]
for name, value in source.items():
    assert digest((ROOT / name).read_bytes()) == value, name
save("producer-receipt.json", receipt)
print(json.dumps({"status": receipt["status"], "source_manifest_sha256": source_digest,
                  "producer_receipt_sha256": digest((HERE / "producer-receipt.json").read_bytes()),
                  "source_files": len(source), "overlay_files": len(overlays)}, indent=2))
