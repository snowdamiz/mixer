#!/usr/bin/env python3
"""Finite, data-only audit. No artifact code is imported or executed."""
import datetime
import hashlib
import json
import pathlib
import stat
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SHA = "e1c108f6c237109477daae5dae9c98da4e74b40a"
RUN = 40391006298
WORKFLOW_HASH = "7f3ab7ef5ec94379a969c91e9f2348cecd2e80908c8a7330aef845f133f38e62"
SOURCE_RECORDS = {}
SOURCE_COMMANDS = []


def digest(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def write_json(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run_git(argv):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(["git", *argv], cwd=REPO, capture_output=True, timeout=60)
    SOURCE_COMMANDS.append({"started_utc": started, "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                            "argv": ["git", *argv], "cwd": str(REPO), "exit_code": result.returncode,
                            "stdout": digest(result.stdout), "stderr": digest(result.stderr),
                            "scope": "Read-only exact-commit source bytes or metadata; output recorded by digest"})
    write_json("source-commands.json", SOURCE_COMMANDS)
    result.check_returncode()
    return result.stdout


def source(path):
    if path not in SOURCE_RECORDS:
        # This allowlist excludes unrelated/frozen hosted harnesses and all artifact code.
        assert not any(s in path.lower() for s in ("hostedcatalog", "hosted-catalog", "authority-driver", "rejectedworker", "hosted-harness")), path
        payload = run_git(["show", SHA + ":" + path])
        SOURCE_RECORDS[path] = {**digest(payload), "git_blob": run_git(["rev-parse", SHA + ":" + path]).decode().strip()}
        return payload
    return run_git(["show", SHA + ":" + path])


def same(data, expected):
    found = digest(data)
    for key in ("bytes", "sha256"):
        if key in expected:
            assert found[key] == expected[key], (key, found, expected)


def archive(name):
    metadata = json.loads((ROOT / "artifact-metadata.stdout").read_bytes())["artifacts"]
    item, = [a for a in metadata if a["name"] == name + "-" + SHA]
    data = (ROOT / (name + ".zip")).read_bytes()
    assert item["workflow_run"]["id"] == RUN
    assert item["workflow_run"]["head_sha"] == SHA
    assert item["expired"] is False
    assert "sha256:" + digest(data)["sha256"] == item["digest"]
    z = zipfile.ZipFile(ROOT / (name + ".zip"))
    seen = set()
    members = []
    total = 0
    for info in z.infolist():
        p = pathlib.PurePosixPath(info.filename)
        assert not p.is_absolute() and ".." not in p.parts and "\\" not in info.filename
        assert info.filename not in seen
        assert not stat.S_ISLNK(info.external_attr >> 16)
        assert not info.flag_bits & 1
        assert info.file_size <= 32 * 1024 * 1024
        seen.add(info.filename)
        payload = z.read(info)
        assert len(payload) == info.file_size
        total += len(payload)
        members.append({"path": info.filename, **digest(payload)})
    assert total <= 64 * 1024 * 1024
    write_json(name + ".members.json", members)
    return z, {"id": item["id"], "name": item["name"], "run_id": RUN, **digest(data), "metadata_digest_verified": True,
               "safe_unique_regular_member_paths": True, "members": len(members), "member_bytes": total,
               "archive_code_imported_or_executed": False, "archive_extracted": False}


def audit_core():
    z, summary = archive("swift-core-toolchain-host")
    assert set(z.namelist()) == {"apple-toolchain.json", "native-vm/receipt.json"}
    apple = json.loads(z.read("apple-toolchain.json"))
    vm = json.loads(z.read("native-vm/receipt.json"))
    assert apple["sourceRevision"] == SHA and vm["source_revision"] == SHA
    assert apple["status"] == "verified-installed-toolchain"
    assert apple["xcode"] == "Xcode 26.3\nBuild version 17C529"
    assert apple["swiftVersion"] == [6, 2, 4]
    assert apple["toolchains"] == "com.apple.dt.toolchain.XcodeDefault"
    assert apple["probeSHA256"] == digest(source("scripts/ci/verify-apple-toolchain.py"))["sha256"]
    assert vm["generator_sha256"] == digest(source("runtime/build-vm.py"))["sha256"]
    assert vm["header_sha256"] == digest(source("vm/include/mixer_vm.h"))["sha256"]
    assert source("vm/include/mixer_vm.h") == source("runtime/Sources/CMixerVM/include/mixer_vm.h")
    archived_sources = run_git(["archive", SHA, "vm", "contracts/vm-session-v1.json"])
    assert vm["source_archive_sha256"] == digest(archived_sources)["sha256"]
    write_json("native-vm-source-archive-verification.json", {"argv": ["git", "archive", SHA, "vm", "contracts/vm-session-v1.json"], **digest(archived_sources), "receipt_matches": True, "archive_not_extracted_or_executed": True})
    assert vm["exit_code"] == 0 and vm["target"] == "host"
    summary.update({"apple_toolchain": apple, "native_vm_receipt": vm, "source_bindings_verified": True,
                    "retained_binary_bytes": 0, "retained_build_log_bytes": 0,
                    "limitations": ["Only two receipt JSON members are retained; compiler/frontend, library, and build-log hashes are receipt claims without corresponding bytes.",
                                    "Toolchain scope text mentions unsigned simulator build generically; this audit ran no simulator and does not infer runtime evidence.",
                                    "Immutable published packaging, runtime fingerprint and signing remain pending."]})
    z.close()
    return summary


def audit_jvm():
    z, summary = archive("android-owner-host")
    closures = []
    for closure, expected_sources, expected_commands, expected_classes in (
        ("android-owner-environment", 39, 26, 175),
        ("android-owner-orchestration", 90, 6, 270),
        ("android-owner-renderer", 93, 6, 311),
    ):
        prefix = closure + "/"
        receipt = json.loads(z.read(prefix + "receipt.json"))
        sources = json.loads(z.read(prefix + "source-map.json"))
        commands = json.loads(z.read(prefix + "commands.json"))
        assert len(sources) == expected_sources and len(commands) == expected_commands
        assert receipt["source_stable"] is True and receipt["status"] == "passed-host-only"
        assert receipt["native_or_capture_processes_started_or_queried"] is False
        if closure != "android-owner-environment":
            assert receipt["revision"] == SHA
            assert z.read(prefix + "revision.stdout").decode().strip() == SHA
        else:
            assert receipt["context_revision_is_inherited_not_live_git"] is True
        for path, expected in sources.items():
            payload = z.read(prefix + "inputs/" + path)
            same(payload, expected)
            assert payload == source(path), path
        for command in commands:
            assert command["exit"] == 0 and command["timeout"] is False and command["child_reaped"] is True
            assert command["output_limit_exceeded"] is False
            for stream in ("stdout", "stderr"):
                same(z.read(prefix + command["label"] + "." + stream), command[stream])
        class_map_name = "classes.json" if closure == "android-owner-environment" else "class-map.json"
        classes = json.loads(z.read(prefix + class_map_name))
        assert len(classes) == expected_classes
        retained = 0
        for path, expected in classes.items():
            member = prefix + "classes/" + path
            if member in z.namelist():
                same(z.read(member), expected)
                retained += 1
        assert retained == (0 if closure == "android-owner-environment" else expected_classes)
        outputs = {}
        for command in commands:
            if command["label"] in ("host", "NativeEnvironmentPlatformV2HostTests", "NativeEnvironmentV2ObserverHostTests"):
                payload = z.read(prefix + command["label"] + ".stdout")
                assert b"PASS " in payload and b"\x1b" not in payload
                outputs[command["label"]] = payload.decode().strip()
        versions = {stream: z.read(prefix + stream).decode().strip() for stream in ("java-version.stderr", "javac-version.stdout")}
        closures.append({"closure": closure, "sources_bound_to_exact_commit_bytes": len(sources), "commands_with_retained_output_digest_verified": len(commands),
                         "retained_class_bytes_verified": retained, "class_hashes_only": len(classes) - retained, "receipt_tools_hashes_only": receipt["tools"],
                         "version_outputs": versions, "outputs": outputs, "cleanup": receipt["cleanup"],
                         "inherited_context_revision_only": receipt.get("context_revision"), "scope": receipt["scope"], "native_runtime_qualified": False})
    summary["closures"] = closures
    z.close()
    return summary


def main():
    assert digest((ROOT / "workflow-source.stdout").read_bytes())["sha256"] == WORKFLOW_HASH
    summary = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "argv": sys.argv,
               "python": sys.version, "source_revision": SHA, "source_tree": (ROOT / "source-tree.stdout").read_text().strip(),
               "workflow_sha256": WORKFLOW_HASH, "run_id": RUN, "run_url": f"https://github.com/snowdamiz/mixer/actions/runs/{RUN}",
               "scope": "Read-only data audit of retained host CI artifacts against exact committed source bytes; no artifact code execution.",
               "core": audit_core(), "jvm_owner": audit_jvm(),
               "capability": {"status": "pending", "reason": "No capability artifact in first metadata snapshot; root coordinates targeted retry terminal outcome."},
               "cleanup": {"native_or_capture_processes_started_or_queried": False, "artifacts_extracted": False, "subprocesses_reaped": True, "network_mutations": False},
               "public_V2_or_native_runtime_or_GA_qualified": False}
    write_json("source-blobs.json", SOURCE_RECORDS)
    summary["source_blob_manifest"] = {"path": "source-blobs.json", **digest((ROOT / "source-blobs.json").read_bytes()), "unique_paths": len(SOURCE_RECORDS), "verification_argv_template": ["git", "show", SHA + ":<path>"], "blob_argv_template": ["git", "rev-parse", SHA + ":<path>"]}
    summary["auditor"] = digest(pathlib.Path(__file__).read_bytes())
    write_json("core-jvm-audit.json", summary)
    print(json.dumps({"status": "core-JVM-audit-passed-capability-pending", "source_blobs": len(SOURCE_RECORDS), "JVM_closures": summary["jvm_owner"]["closures"]}, indent=2))


if __name__ == "__main__":
    main()
