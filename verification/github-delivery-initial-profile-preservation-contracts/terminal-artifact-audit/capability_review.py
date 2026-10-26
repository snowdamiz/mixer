#!/usr/bin/env python3
"""Collect/audit capability evidence as data; never execute artifact members."""
import ast
import datetime
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import tarfile

import audit as base

if not __debug__:
    raise RuntimeError("Audit assertions require an unoptimized Python interpreter")

BASE = pathlib.Path(base.__file__).resolve().parent
ROOT = BASE / "capability"
ROOT.mkdir(exist_ok=True)
base.ROOT = ROOT
SHA = base.SHA
RUN = base.RUN


def capture(name, argv):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=base.REPO, capture_output=True, check=False, timeout=60)
    for stream in ("stdout", "stderr"):
        (ROOT / (name + "." + stream)).write_bytes(getattr(result, stream))
    base.write_json(name + ".command.json", {"started_utc": started, "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "argv": argv, "cwd": str(base.REPO), "exit_code": result.returncode,
                    "stdout": base.digest(result.stdout), "stderr": base.digest(result.stderr), "raw_bytes_never_rendered": True})
    if result.returncode:
        raise RuntimeError(name + " failed; inspect retained bytes safely")
    return result.stdout


def collect():
    payload = capture("artifact-metadata", ["gh", "api", f"repos/snowdamiz/mixer/actions/runs/{RUN}/artifacts?per_page=100"])
    artifacts = json.loads(payload)["artifacts"]
    selected = [a for a in artifacts if a["name"] == "android-binding-host-" + SHA]
    if not selected:
        base.write_json("collection-pending.json", {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "status": "pending", "reason": "No exact-commit capability artifact in metadata", "run_id": RUN})
        print("Capability artifact absent; no retry or cancellation performed.")
        return
    artifact, = selected
    blob = capture("android-binding-host", ["gh", "api", f"repos/snowdamiz/mixer/actions/artifacts/{artifact['id']}/zip"])
    (ROOT / "android-binding-host.zip").write_bytes(blob)
    (ROOT / "android-binding-host.stdout").unlink()
    p = ROOT / "android-binding-host.command.json"
    record = json.loads(p.read_text()); record["stdout_file"] = "android-binding-host.zip"
    p.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"artifact_id": artifact["id"], **base.digest(blob)}))


def literal_assignment(tree, name):
    node, = [n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    return ast.literal_eval(node.value)


def tree_paths(paths):
    return base.run_git(["ls-tree", "-r", "--name-only", SHA, "--", *paths]).decode().splitlines()


def expected_binding_inputs(runner_source):
    paths = set()
    for package in ("experimental-capability-runtime", "runtime-identity", "updates", "sdk"):
        for path in tree_paths([package]):
            suffix = path[len(package) + 1:]
            if suffix in ("Package.swift", "Package.resolved") or suffix.startswith(("Sources/", "Tests/")):
                paths.add(path)
    paths.update(tree_paths(["capability-activation/Sources", "native/android/signed-guest-ui/binding/include"]))
    paths.update("native/android/signed-guest-ui/transport/" + p for p in ("transport.c", "internal.h", "include/mixer_ui_transport.h"))
    fixture = "verification/android-binding-stage4/"
    paths.update(fixture + p for p in ("HostEntry.swift", "HostTests.swift", "HoldingExecutor.swift"))
    paths.update(fixture + "host-bridge/" + p for p in ("host_bridge.c", "mixer_android_host_bridge.h", "host_test.h", "module.modulemap", "test.modulemap"))
    paths.add("capability-activation/Package.resolved")
    inputs = {path: base.digest(base.source(path))["sha256"] for path in sorted(paths)}
    snapshot = dict(inputs)
    snapshot["capability-activation/Sources/MixerCapabilityActivation/Stage4HostEntry.swift"] = inputs[fixture + "HostEntry.swift"]
    for name in ("HostTests.swift", "HoldingExecutor.swift"):
        snapshot["Harness/" + name] = inputs[fixture + name]
    snapshot["Package.resolved"] = inputs["capability-activation/Package.resolved"]
    snapshot["Package.swift"] = base.digest(literal_assignment(ast.parse(runner_source), "PACKAGE").encode())["sha256"]
    return inputs, snapshot


def prepare():
    runner = base.source("scripts/ci/check-android-binding.py")
    inputs, snapshot = expected_binding_inputs(runner)
    base.write_json("expected-source-bindings.json", {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "source_revision": SHA, "input_files": inputs, "source_files": snapshot,
                    "source_tree_sha256": base.digest(json.dumps(snapshot, sort_keys=True).encode())["sha256"],
                    "source_blobs": base.SOURCE_RECORDS, "scope": "Source-only preparation; no CI or native execution; no artifact pass claim."})
    print(json.dumps({"input_paths": len(inputs), "snapshot_paths": len(snapshot), "source_tree_sha256": base.digest(json.dumps(snapshot, sort_keys=True).encode())["sha256"]}))


def audit_native(native):
    assert native["source_revision"] == SHA
    assert native["feature"] == "experimental-capability-native" and native["target_selector"] == "host"
    assert native["mutable_SDK_source_consumed"] is False
    assert native["environment"]["DEVELOPER_DIR"] == "/Applications/Xcode_26.3.app/Contents/Developer"
    assert native["environment"]["SDKROOT"] == "/Applications/Xcode_26.3.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX26.2.sdk"
    assert set(native["tools"]) == {"rustc_selector", "rustc", "cargo", "llvm_nm", "linker"}
    assert native["tools"]["linker"]["path"] == "/Applications/Xcode_26.3.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang"
    assert "Apple clang version 17.0.0" in native["linker"]
    builder = base.source("experimental-capability-runtime/build-vm.py")
    assert native["builder_sha256"] == base.digest(builder)["sha256"]
    required_paths = literal_assignment(ast.parse(builder), "PATHS")
    assert set(native["source_blobs"]) == set(tree_paths(required_paths))
    archive_bytes = io.BytesIO()
    with tarfile.open(fileobj=archive_bytes, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for path, expected in sorted(native["source_blobs"].items()):
            payload = base.source(path)
            base.same(payload, expected)
            assert base.SOURCE_RECORDS[path]["git_blob"] == expected["git_blob"]
            entry = base.run_git(["ls-tree", SHA, "--", path]).split(b" ", 1)[0]
            info = tarfile.TarInfo(path); info.size = len(payload); info.mode = 0o755 if entry == b"100755" else 0o644; info.mtime = 0
            tar.addfile(info, io.BytesIO(payload))
    assert native["source_file_count"] == len(native["source_blobs"])
    manifest = "".join(f"{item['sha256']}  {path}\n" for path, item in sorted(native["source_blobs"].items()))
    assert native["source_manifest_sha256"] == base.digest(manifest.encode())["sha256"]
    assert native["source_archive_sha256"] == base.digest(archive_bytes.getvalue())["sha256"]
    assert set(native["headers"]) == {"mixer_vm.h", "mixer_vm_capability.h", "mixer_vm_guest_ui.h"}
    for name, expected in native["headers"].items():
        base.same(base.source("vm/include/" + name), expected)
    assert len(native["commands"]) == 9
    for command in native["commands"]:
        assert command["exit_code"] == 0 and command["problem"] is None
    return {"source_blob_hashes_sizes_and_git_blobs_verified": len(native["source_blobs"]), "reconstructed_source_archive_sha256_verified": True,
            "commands_recorded": len(native["commands"]), "retained_native_command_logs": 0, "command_status_and_log_hashes_receipt_only": True,
            "retained_library_or_tool_binary_bytes": 0, "tools_receipt_only": native["tools"], "rustc": native["rustc"], "cargo": native["cargo"],
            "linker": native["linker"], "qualification": native["qualification"]}


def audit():
    z, summary = base.archive("android-binding-host")
    names = set(z.namelist())
    expected_receipts = {"apple-toolchain.json", "capability-vm/receipt.json", *("android-binding-" + m + "/receipt.json" for m in ("debug", "release", "tsan"))}
    assert expected_receipts <= names
    apple = json.loads(z.read("apple-toolchain.json"))
    native_payload = z.read("capability-vm/receipt.json")
    native = json.loads(native_payload)
    assert apple["sourceRevision"] == SHA and apple["status"] == "verified-installed-toolchain"
    assert apple["xcode"] == "Xcode 26.3\nBuild version 17C529" and apple["swiftVersion"] == [6, 2, 4]
    assert apple["probeSHA256"] == base.digest(base.source("scripts/ci/verify-apple-toolchain.py"))["sha256"]
    runner = base.source("scripts/ci/check-android-binding.py")
    tree = ast.parse(runner)
    scenario_node, = [n.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SCENARIOS" for t in n.targets)]
    assert isinstance(scenario_node, ast.Call) and isinstance(scenario_node.func, ast.Attribute) and scenario_node.func.attr == "split"
    scenarios = ast.literal_eval(scenario_node.func.value).split()
    assert len(scenarios) == 39 and len(set(scenarios)) == 39
    inputs, snapshot = expected_binding_inputs(runner)
    pins = {p["identity"]: p for p in json.loads(base.source("capability-activation/Package.resolved"))["pins"]}
    modes = []
    for mode in ("debug", "release", "tsan"):
        prefix = "android-binding-" + mode + "/"
        receipt = json.loads(z.read(prefix + "receipt.json"))
        assert receipt["revision"] == SHA and receipt["native_source_revision"] == SHA
        assert receipt["mode"] == mode and receipt["status"] == "passed" and "error" not in receipt
        assert receipt["runner_sha256"] == base.digest(runner)["sha256"]
        assert receipt["input_files"] == inputs and receipt["source_files"] == snapshot
        assert receipt["source_tree_sha256"] == base.digest(json.dumps(snapshot, sort_keys=True).encode())["sha256"]
        assert receipt["native_receipt_sha256"] == base.digest(native_payload)["sha256"]
        assert receipt["cases_executed"] == scenarios
        assert len(receipt["commands"]) == 51 and len(set(c["name"] for c in receipt["commands"])) == 51
        expected_commands = {"swift-version", "clang-version", "fresh-build", "bin-path", *scenarios}
        expected_commands.update(f"{prefix}-{identity}-{kind}" for prefix in ("dependency", "final-dependency") for identity in pins for kind in ("revision", "status"))
        assert {c["name"] for c in receipt["commands"]} == expected_commands
        diagnostics = []
        for command in receipt["commands"]:
            assert command["exit"] == 0
            assert command["environment"] == {"DEVELOPER_DIR": "/Applications/Xcode_26.3.app/Contents/Developer", "TOOLCHAINS": "com.apple.dt.toolchain.XcodeDefault"}
            log = prefix + "logs/" + command["name"] + ".log"
            payload = z.read(log)
            assert command["sha256"] == base.digest(payload)["sha256"]
            if command["name"] in scenarios:
                marker = ("HOST_PASS " + command["name"]).encode()
                assert marker in payload.splitlines()
            if command["name"] == "fresh-build":
                assert b"Build of product 'Stage4HostTests' complete! (" in payload
                argv = command["argv"]
                assert "--force-resolved-versions" in argv and "-warnings-as-errors" in argv
                assert argv[argv.index("-c") + 1] == ("release" if mode == "release" else "debug")
                assert ("--sanitize" in argv) == (mode == "tsan")
            if command["name"] == "swift-version":
                assert b"Apple Swift version 6.2.4" in payload
            if command["name"] == "clang-version":
                assert b"Apple clang version 17.0.0" in payload
            for marker in (b"WARNING: ThreadSanitizer", b"FATAL: ThreadSanitizer", b"ThreadSanitizer: data race", b"ERROR: AddressSanitizer", b"error:", b"TIMEOUT"):
                if marker in payload:
                    diagnostics.append({"command": command["name"], "marker": marker.decode(), "count": payload.count(marker)})
            for identity, pin in pins.items():
                for phase in ("dependency", "final-dependency"):
                    if command["name"] == f"{phase}-{identity}-revision": assert payload.decode().strip() == pin["state"]["revision"]
                    if command["name"] == f"{phase}-{identity}-status": assert not payload.strip()
        assert not diagnostics, diagnostics
        assert set(receipt["dependency_checkouts"]) == set(pins)
        for identity, pin in pins.items():
            assert receipt["dependency_checkouts"][identity] == {"location": pin["location"], "revision": pin["state"]["revision"], "version": pin["state"]["version"], "status": ""}
        expected_native = {str(pathlib.PurePosixPath(receipt["native_receipt"]).parent / "lib/libmixer_vm_capability_experimental.a"): native["library"]["sha256"]}
        expected_native.update({str(pathlib.PurePosixPath(receipt["native_receipt"]).parent / "include" / name): item["sha256"] for name, item in native["headers"].items()})
        assert receipt["native_inputs"] == expected_native
        modes.append({"mode": mode, "status": receipt["status"], "cases_verified": len(scenarios), "command_log_digests_verified": len(receipt["commands"]),
                      "input_hashes_verified_against_commit_bytes": len(inputs), "snapshot_hashes_reconstructed": len(snapshot),
                      "source_tree_sha256": receipt["source_tree_sha256"], "dependency_pins_verified": receipt["dependency_checkouts"],
                      "diagnostic_markers": diagnostics, "executable_hash_only_no_bytes": receipt["executable"], "scope": receipt["scope"],
                      "started_utc": receipt["started_utc"], "completed_utc": receipt["completed_utc"]})
    assert names == expected_receipts | {"android-binding-" + mode + "/logs/" + c["name"] + ".log" for mode in ("debug", "release", "tsan") for c in json.loads(z.read("android-binding-" + mode + "/receipt.json"))["commands"]}
    summary.update({"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "argv": sys.argv, "python": sys.version,
                    "source_revision": SHA, "source_tree": (BASE / "source-tree.stdout").read_text().strip(), "apple_toolchain": apple,
                    "native": audit_native(native), "modes": modes, "status": "passed-retained-host-artifact-audit",
                    "cleanup": {"artifact_code_imported_or_executed": False, "artifacts_extracted": False, "native_or_capture_processes_started_or_queried": False, "subprocesses_reaped": True},
                    "limitations": ["Source hashes are bound to committed bytes; artifact contains no copied source tree, library or executable bytes.", "Native VM nine command outcomes/log hashes and binary/tool hashes are receipt claims; their command logs and binary bytes are absent.", "TSAN applies to fresh Swift host harness; Rust static archive was not rebuilt or TSAN-instrumented by the binding runner.", "No JNI, Looper, native runtime, simulator/emulator/device, literal debugger matrix, public V2, signed UI, immutable package, release or GA qualification."]})
    base.write_json("source-blobs.json", base.SOURCE_RECORDS)
    summary["source_blob_manifest"] = {**base.digest((ROOT / "source-blobs.json").read_bytes()), "unique_paths": len(base.SOURCE_RECORDS), "git_show_template": ["git", "show", SHA + ":<path>"], "git_blob_template": ["git", "rev-parse", SHA + ":<path>"]}
    summary["auditor"] = base.digest(pathlib.Path(__file__).read_bytes())
    base.write_json("audit.json", summary)
    print(json.dumps({"status": summary["status"], "members": summary["members"], "source_blobs": len(base.SOURCE_RECORDS), "modes": [{k:m[k] for k in ("mode", "cases_verified", "command_log_digests_verified")} for m in modes]}))


if __name__ == "__main__":
    {"collect": collect, "audit": audit, "prepare": prepare}[sys.argv[1]]()
