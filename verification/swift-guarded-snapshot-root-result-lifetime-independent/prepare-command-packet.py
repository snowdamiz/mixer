#!/usr/bin/env python3
"""Freeze independent finite probes and source-only command proposal."""
from pathlib import Path
import ast
import datetime
import hashlib
import json

P = Path(__file__).resolve().parent
R = P.parents[1]
PRODUCER = R / "verification/swift-guarded-snapshot-root-result-lifetime-implementation"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def row(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(P)), "bytes": len(data), "sha256": sha(data)}


def write(name, value):
    with (P / name).open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


ast.parse((P / "run-once.py").read_text())
toolchain = json.loads((PRODUCER / "toolchain.json").read_text())
producer_roster = json.loads((PRODUCER / "proposed-command-roster-v2.json").read_text())
assert sha((PRODUCER / "proposed-command-roster-v2.json").read_bytes()) == "8bc1c1ef947c0eb05332729967c82890aadf279a52745451f86c4aedde1b01a3"
assert sha((PRODUCER / "source-freeze-v2.json").read_bytes()) == "01b38d2409b403f01ee5705deb552fd1a17a6e86a9962f3d91502ae80d32e7e0"
assert sha((PRODUCER / "seal.json").read_bytes()) == "7efe39286257be85d0e91f4bdd80b6098d24d7d2f446dcdc2e8dd7adb0159fa4"
for member in json.loads((PRODUCER / "seal.json").read_text())["members"]:
    data = (PRODUCER / member["path"]).read_bytes()
    assert len(data) == member["bytes"] and sha(data) == member["sha256"], member["path"]

instrumentation = json.loads((P / "instrumentation.json").read_text())
loader = "src/experimental_swift_reactor/retained_profile_loader_v1.rs"
assert (P / "source/vm" / loader).read_text().replace(instrumentation["insertion"], "") == (PRODUCER / "source/vm" / loader).read_text()
for sub, manifest_name in [("vm", "independent-vm-manifest.json"), ("host", "independent-host-manifest.json")]:
    manifest = json.loads((P / manifest_name).read_text())
    actual = []
    for file in sorted((P / "source" / sub).rglob("*")):
        if file.is_file():
            data = file.read_bytes()
            actual.append({"path": str(file.relative_to(P / "source" / sub)), "bytes": len(data), "sha256": sha(data)})
    assert actual == manifest["members"]
    producer = json.loads((PRODUCER / ("source-manifest.json" if sub == "vm" else "host-manifest.json")).read_text())["members"]
    assert [x["path"] for x in actual] == [x["path"] for x in producer]
    for new, old in zip(actual, producer):
        assert new == old or (sub == "vm" and new["path"] == loader)

history = (P / "probes/IN01-history.inc.rs").read_bytes()
assert history == (R / "verification/swift-guarded-snapshot-root-result-preaccess/negative/ir02_exact_signature_v1.inc.rs").read_bytes()
write("historical-oracle-interpretation.json", {
    "schema": 1, "status": "root-authorized-preexecution-oracle-interpretation-correction",
    "frozen_preaccess_desired_result": "Exact historical signature rejects; syntax-only evidence if so.",
    "corrected_interpretation": "Command is observational compatibility evidence. The new lifetime may be elided from the sole input root while exact historical spelling remains accepted. Success is not a source defect or escape; inspect actual outcome and preserve it. No API churn merely to reject this spelling.",
    "root_authorization": "Parent explicitly approved this interpretation before any independent compiler launch in message delivered 2026-10-27.",
    "historical_bytes_sha256": sha(history),
    "mandatory_semantic_companions": ["IN02-static", "IN04-lexical-core", "P01-facade", "core-host original-root-live controls"],
    "new_execution_or_retry": False,
})

build = P / "build"
build.mkdir()
common = [toolchain["tool"]["path"], "--crate-name", "mixer_vm", "--edition=2021", "--target", "aarch64-apple-darwin", "-C", "overflow-checks=yes", "-C", "panic=unwind"]
for feature in ["experimental-swift-reactor", "experimental-swift-wasi", "experimental-stream-validation", "experimental-function-cache"]:
    common += ["--cfg", f'feature="{feature}"']
common += ["--cfg", "mixer_bootstrap_one_fixture_v1"]
source = str(P / "source/vm/src/lib.rs")
commands = []
probes = [
    ("P01-facade", "facade", "compiler-positive", [], "Actual opaque facade permits acquisition-owner retirement before complete result/final result return while exact original root survives; shared diagnostic views have short carrier borrows."),
    ("P02-cache", "cache", "compiler-positive", [], "Actual admitted child retains separate child/root lifetimes after acquisition-owner retirement; complete destruction may return child-only token without payload."),
    ("IN01-history", "facade", "compiler-observation", [], "Verbatim historical IR02 helper. Preserve accepted lifetime elision or historical shape refusal as observed, without declaring an escape or forcing API churn."),
    ("IN02-static", "facade", "compiler-negative", ["lifetime may not live long enough", "'root", "'static"], "Force actual original-root result to static through genuine opaque facade after acquisition-owner retirement."),
    ("IN03-foreign-substitution", "facade", "compiler-negative", ["lifetime may not live long enough", "'original", "'foreign"], "Try substituting independently live foreign expected-root lifetime for actual supplying attempt-root output. Positive original-root-return control is P01."),
    ("IN04-lexical-core", "lexical", "compiler-negative", ["E0597", "original_root", "does not live long enough"], "Actual generic production core, actual admission/validator proof and original Guards; original inner ledger ends before accessible proof/guards use, with foreign ledger still alive. Never executed."),
    ("IN05-short-borrow", "facade", "compiler-negative", ["lifetime may not live long enough", "'view", "'root"], "Try promoting a short shared diagnostic carrier view to root-length lifetime. P01 returns the legitimate short view."),
    ("IN06-own-leaf-ok", "facade", "compiler-negative", ["E0507", "original", "shared reference"], "Actual fixed leaf API then try returning owning SnapshotScopeFinishV1 through shared primary view. Compile-only; no product leaf arm executed."),
    ("IN07-own-leaf-err", "facade", "compiler-negative", ["E0507", "original", "shared reference"], "Actual fixed leaf API then try returning owning SnapshotPreScopeFailureV1 through shared primary view. Compile-only; no product leaf arm executed."),
]
for ident, scope, kind, phrases, description in probes:
    fragment = P / "probes" / (ident + ".inc.rs")
    mode = "mixer_independent_ir02_lexical_v1" if scope == "lexical" else f"mixer_ir02_probe_{scope}_v1"
    argv = common + ["--cfg", mode, "-C", "opt-level=0"]
    argv += ["--test"] if scope == "lexical" else ["--crate-type", "rlib"]
    output = str(build / (ident + ".rmeta"))
    argv += [source, "--emit=metadata=" + output]
    environment = {("MIXER_INDEPENDENT_IR02_LEXICAL_PATH_V1" if scope == "lexical" else "MIXER_IR02_PROBE_PATH_V1"): str(fragment)}
    commands.append({"id": ident, "kind": kind, "argv": argv, "environment_additions": environment, "probe": row(fragment), "intended_diagnostic_phrases": phrases, "scope": description, "output_files": [output], "semantic_review_required": True})
for mode, level in [("debug", "0"), ("opt2", "2")]:
    binary = str(build / ("tests-" + mode))
    commands.append({"id": "build-" + mode, "kind": "compiler-positive", "argv": common + ["--cfg", "mixer_independent_ir02_host_v1", "--test", "-C", "opt-level=" + level, source, "-o", binary], "environment_additions": {"MIXER_INDEPENDENT_IR02_HOST_PATH_V1": str(P / "independent-host.inc.rs")}, "output_files": [binary], "scope": "Build exact candidate production bytes plus only cfg(test) include sites and independent core host fragment; no runtime invoked."})
    commands.append({"id": "run-" + mode, "kind": "host", "argv": [binary, "prepaid_actual_owner_v1", "trusted_local_host_account_entry_v1::host_account_v1::tests", "--test-threads=1", "--nocapture"], "environment_additions": {}, "output_files": [], "scope": "Four independent actual-core host tests with exactly22 finite subcases plus original38 selected tests; expected42 tests and470 filtered. Native File setup/loader/VM/product leaf are never run."})
assert len([x for x in commands if x["kind"].startswith("compiler")]) == 11
assert len([x for x in commands if x["kind"] == "host"]) == 2
environment = dict(producer_roster["environment"])
environment["CARGO_MANIFEST_DIR"] = str(P / "source/vm")
environment["TMPDIR"] = str(build)
write("proposed-command-roster.json", {
    "schema": 1, "status": "independent-finite-proposal-not-execution-authority", "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "commands": commands, "compiler_commands": 11, "positive_companions": 2, "semantic_negative_commands": 6, "historical_compatibility_observations": 1, "test_builds": 2, "host_runs": 2,
    "new_host_tests": 4, "new_host_subcases": 22, "existing_test_replay": 38, "expected_test_total_per_mode": 42, "native_or_product_leaf_runs": 0,
    "tool": toolchain["tool"], "tool_version": toolchain["version"], "tool_version_source": "Producer's pinned rustc -vV receipt, no new version query requested", "environment": environment,
    "production_candidate_tree_sha256": "91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f",
    "independent_instrumented_tree_sha256": json.loads((P / "independent-vm-manifest.json").read_text())["tree_sha256"],
    "host11_tree_sha256": "027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2",
    "producer_seal_sha256": "7efe39286257be85d0e91f4bdd80b6098d24d7d2f446dcdc2e8dd7adb0159fa4",
    "producer_roster_sha256": "8bc1c1ef947c0eb05332729967c82890aadf279a52745451f86c4aedde1b01a3",
    "preaccess_oracle_adoption": row(P / "oracle-adoption.json"), "runner": row(P / "run-once.py"),
    "each_command_seconds_max": 55, "work_seconds_max": 51, "cleanup_seconds_max": 54.5, "simultaneous_compilers": 1, "simultaneous_host_binaries": 1, "stdout_stderr_each_bytes_max": 4194304,
    "write_once_each_command": True, "exact_owned_PID_PGID_cleanup_only": True, "global_process_inventory": False, "blind_retries_or_extra_commands": False,
    "release_required": {"execution_released": True, "independent_roster_sha256": "exact hash of this file", "independent_freeze_sha256": "exact hash of command-freeze.json"},
    "preaccess_N12_N13": "Reviewed finite private body boundary only; no claim raw private File/Selected intrinsically borrows root. No negative privacy probe is substituted for that body review.",
    "producer_evidence_reuse": "Review producer metadata/full MIR and18 diagnostics explicitly as producer evidence. Do not repeat equivalent visibility/Some-None/whole-family probes as independent evidence.",
    "historical_interpretation": row(P / "historical-oracle-interpretation.json"),
    "claim_limits": ["No native File/VM/leaf/runtime or setup-prefix execution", "No new price/layout/funding qualification", "No forgotten-result/root durable funding or shutdown", "No useful joint retirement or full charge lifetime", "No selector/custody/native healthy close, FieldLog, OTA or GA acceptance"],
})
members = []
for name in ["oracle-adoption.json", "source-review.json", "source-verification.json", "source-checkpoint-validation.json", "validate-source-checkpoint.py", "instrumentation.json", "independent-vm-manifest.json", "independent-host-manifest.json", "independent-host.inc.rs", "historical-oracle-interpretation.json", "run-once.py", "prepare-command-packet.py", "proposed-command-roster.json"]:
    members.append(row(P / name))
members += [row(path) for path in sorted((P / "probes").glob("*.rs"))]
write("command-freeze.json", {"schema": 1, "status": "independent-preexecution-source-probe-roster-freeze-not-execution-authority", "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "members": members, "production_source_pinned_by_manifests": True, "compiler_or_host_execution_before_freeze": False})
print(json.dumps({"roster_sha256": sha((P / "proposed-command-roster.json").read_bytes()), "freeze_sha256": sha((P / "command-freeze.json").read_bytes()), "runner_sha256": sha((P / "run-once.py").read_bytes()), "compiler_commands": 11, "host_runs": 2, "native_runtime": 0}))
