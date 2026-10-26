#!/usr/bin/env python3
"""One-shot final custody audit for already completed candidate5 CLI checks."""
import datetime
import importlib.util
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
assert not (BASE / "manifest.json").exists(), "Packet already sealed"
spec = importlib.util.spec_from_file_location("candidate5_completed_runner", BASE / "qualify.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
receipt = runner.load(BASE / "receipt.json")
assert receipt["status"] == "passed-exact-candidate5-profile3-host-qualification-awaiting-independent-root-review"
runner.require(BASE / "qualify.py", receipt["runner"])
q = runner.Qualification()
q.commands = runner.load(BASE / "commands.json")
q.versions = receipt["tool_versions"]
assert len(q.commands) == 96
compiler = {}
for name in ("swift", "swiftc"):
    output, _ = q.run("resolve-host-" + name, ["/usr/bin/xcrun", "--find", name])
    path = Path(output.decode().strip()).resolve()
    compiler[name] = {"path": str(path), **runner.identity(path.read_bytes())}
out, err = q.run("resolved-host-swiftc-version", [compiler["swiftc"]["path"], "--version"])
version = (out + err).decode().strip()
assert version.splitlines()[0] == receipt["tool_versions"]["host-swift"].splitlines()[0]
out, _ = q.run("host-sdk-path", ["/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path"])
sdk_path = out.decode().strip()
q.run("final-owned-diff-check", ["/usr/bin/git", "diff", "--check", "--", *runner.OWNED])
assert len(q.commands) == 101
for command in q.commands:
    folder = BASE / "commands" / command["label"]
    assert command["exit"] == command["expected_exit"] and not command["timed_out"] and command["child_reaped"]
    runner.require(folder / "stdout", command["stdout"])
    runner.require(folder / "stderr", command["stderr"])
    assert runner.load(folder / "result.json") == command
    assert command["pid"] == command["pgid"] and command["timeout_seconds"] > 0
source = runner.load(BASE / "source-binding.json")
assert runner.projection(source["files"]) == source["projection_sha256"]
for name, row in source["files"].items():
    runner.require(ROOT / name, row)
    runner.require(BASE / "source" / name, row)
runner.pin(runner.CANDIDATE / "manifest.json", runner.PINS["candidate_manifest"])
candidate = runner.load(runner.CANDIDATE / "manifest.json")
for name, row in candidate["files"].items():
    runner.require(runner.CANDIDATE / name, row)
canonical = runner.load(runner.CANDIDATE / "source-map.json")
for name, row in canonical.items():
    runner.require(ROOT / name, row)
history = {p.relative_to(BASE.parent).as_posix(): runner.identity(p.read_bytes())
           for p in sorted(BASE.parent.rglob("*")) if p.is_file() and BASE not in p.parents}
assert history == runner.load(BASE / "historical-inputs-before.json") == runner.load(BASE / "historical-inputs-after.json")
bindings = runner.load(BASE / "consumer-source-binding.json")
for folder, key in [("Profile3Consumer", "created"), ("CopiedConsumer", "copied_and_customized")]:
    assert runner.regular_files(BASE / folder) == bindings[key]
for removed in receipt["cleanup"]["owned_scratch_removed"]:
    assert not (BASE / removed).exists()
products = runner.load(BASE / "compiled-products-before-cleanup.json")
assert len(products) == 39
dispositions = {}
for mode in ("debug", "release"):
    initial = receipt["compiled_products"]["cli-" + mode + "-before-tests"]
    final = receipt["compiled_products"]["cli-" + mode]
    initial_id = {key: initial[key] for key in ("bytes", "sha256")}
    final_id = {key: final[key] for key in ("bytes", "sha256")}
    assert products[str(Path(final["path"]).relative_to(BASE))] == final_id
    commands = [c for c in q.commands if c["executable"]["path"] == final["path"]]
    assert commands[0]["label"] == mode + "-cli-version"
    assert {key: commands[0]["executable"][key] for key in final_id} == initial_id
    assert all({key: c["executable"][key] for key in final_id} == final_id for c in commands[1:])
    dispositions[mode] = {"initial_version_binary": initial_id, "actual_consumer_and_refusal_binary": final_id,
                          "identity_changed_during_swift_test": initial_id != final_id,
                          "consumer_and_refusal_command_count": len(commands) - 1}
runner.save(BASE / "binary-identity-disposition.json", dispositions)
for mode in ("debug", "release"):
    assert "Test run with 13 tests" in (BASE / "commands" / (mode + "-swift-tests") / "stdout").read_text()
for mode in ("normal", "optimized"):
    for name, count in [("test_android_sdk_compatibility", 10), ("test_android_staging", 9), ("test_android_appearance", 11)]:
        assert "Ran " + str(count) + " tests" in (BASE / "commands" / ("python-" + mode + "-" + name) / "stderr").read_text()
runner.save(BASE / "seal-receipt.json", {
    "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())], "python": sys.version,
    "script": runner.identity(Path(__file__).read_bytes()),
    "status": "Candidate5 profile3 host qualification frozen; independent review and owner acceptance pending",
    "candidate_manifest": runner.PINS["candidate_manifest"], "selection": runner.PINS["selection"],
    "profile_proposal": runner.PINS["profile"], "canonical_inputs_reverified": len(canonical),
    "source_members": len(source["files"]), "source_projection_sha256": source["projection_sha256"],
    "commands": len(q.commands), "successful_commands": sum(c["exit"] == 0 for c in q.commands),
    "expected_refusals": sum(c["expected_exit"] == 1 for c in q.commands),
    "Swift_methods_per_Debug_Release": 13, "Python_methods_per_normal_optimized": [10, 9, 11],
    "copied_host_shared_methods": 4, "copied_host_session_methods": 3, "copied_custom_reducer_methods": 1,
    "compiler": compiler, "compiler_version": version, "host_SDK_path": sdk_path,
    "compiled_products_hashed_removed": 39, "owned_scratch_removed": receipt["cleanup"]["owned_scratch_removed"],
    "historical_profile_packets_unchanged": True,
    "native_runtime_capture_UI_or_inventory": False, "implementation_accepted": False, "GA_qualified": False,
})
(BASE / "README.md").write_text("""# Candidate5 profile3 CLI qualification

Only the compiled NativeOwnerV2 identity and adapter projection changed from
candidate4. The profile ID remains mixer.android-source-pair.3. The runner's
opening 'profile5' wording refers to candidate5, not a new profile ID.

Fresh isolated Debug and Release CLI builds pass thirteen focused Swift methods
per mode. Three Python suites pass 10, 9 and 11 methods in both normal and
optimized modes. Actual CLI creation, Release export and copied app consumers
pass four shared methods, three native-session host methods and one customized
app factory/reducer/revision method. These are host checks, not JNI execution.

Seventy-two actual CLI/driver commands correctly refuse profile2, missing lock,
and owner/core edit, removal and rename inputs. Generic adapter locks are
recomputed for tamper fixtures. Eight in-process preaccess trap controls and the
old-policy pre-lock refusal also pass. No test or product expectation changed.

The 101 command receipts bind literal arguments, tool identities and versions,
source projection, output, deadline, PID/PGID and observed child exit. Release
swift test relinks mixer; both the initial version binary and later consumer and
refusal binary are recorded separately. Thirty-nine products were hashed before
five owned scratch trees were removed. Earlier profile packets remain unchanged.

Java/SDK/D8 evidence is explicitly reused from the immutable candidate5 producer;
this CLI packet runs no new native compiler or runtime. Independent CLI/owner
review, coherent delivery, remote CI, public V2, signed/published FieldLog and GA
remain pending. Never rerun these one-shot writers in the frozen packet.
""")
files = {p.relative_to(BASE).as_posix(): runner.identity(p.read_bytes())
         for p in sorted(BASE.rglob("*")) if p.is_file()}
assert not any(p.is_symlink() for p in BASE.rglob("*"))
runner.save(BASE / "manifest.json", {"schema": 1, "members": len(files), "bytes": sum(x["bytes"] for x in files.values()), "files": files})
print(json.dumps({"members": len(files), "bytes": sum(x["bytes"] for x in files.values()),
                  "manifest": runner.identity((BASE / "manifest.json").read_bytes()),
                  "seal_receipt": runner.identity((BASE / "seal-receipt.json").read_bytes())}))
