#!/usr/bin/env python3
"""Offline verification only; no product imports, tests, Docker or CI actions."""
import ast
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import re
import signal
import stat
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SHA = "0b99469dfbeb06ac53ad0223bd070a35f2a6a700"
ZIP_SHA = "07a806adbd2c00db5167f1d0b77f01e18a9587516841aee6fd9be7ab3cf1233c"

# Reuse only the immutable independent review utility's data-reading helpers.
# Import does not invoke its main(), the product, a runtime, or a test suite.
UTILITY = REPO / "verification/github-delivery-identity-network/network-review/verify_failed_artifact.py"
assert hashlib.sha256(UTILITY.read_bytes()).hexdigest() == "371e6c453a57eb90377acf669c0622c5d71925c2497e10782db296573073ccb6"
spec = importlib.util.spec_from_file_location("immutable_failed_review_readers", UTILITY)
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
reader.ROOT, reader.REPO, reader.CAP = ROOT, REPO, 256 * 1024 * 1024
binding, canonical, digest = reader.binding, reader.canonical, reader.digest
safe_name, safe_tar, git_blobs = reader.safe_name, reader.safe_tar, reader.git_blobs


def source_tar(files):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for name, body in sorted(files.items()):
            member = tarfile.TarInfo(name)
            member.size, member.mode, member.mtime = len(body), 0o644, 0
            archive.addfile(member, io.BytesIO(body))
    return output.getvalue()


def main():
    def deadline(signum, frame):
        raise TimeoutError("offline review exceeded its 50-second command bound")
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(50)
    data = (ROOT / "artifact.zip").read_bytes()
    assert len(data) == 754017 and len(data) <= 64 * 1024 * 1024 and digest(data) == ZIP_SHA
    members, folded, expanded = {}, set(), 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for info in archive.infolist():
            safe_name(info.filename)
            assert info.filename not in members and info.filename.casefold() not in folded
            assert not info.is_dir() and not info.flag_bits & 1
            assert stat.S_IFMT(info.external_attr >> 16) in (0, stat.S_IFREG)
            expanded += info.file_size
            assert 0 <= info.file_size <= 256 * 1024 * 1024 and expanded <= 256 * 1024 * 1024
            body = archive.read(info)
            assert len(body) == info.file_size
            members[info.filename] = body
            folded.add(info.filename.casefold())
    expected_names = set(reader.META_NAMES)
    expected_names.update(f"logs/{n:04d}.{ext}" for n in range(1, 29) for ext in ("json", "stdout", "stderr"))
    assert set(members) == expected_names and len(members) == 97
    manifest = json.loads(members["artifact-manifest.json"])
    observed = {name: binding(body) for name, body in members.items() if name != "artifact-manifest.json"}
    assert manifest["files"] == observed and manifest["tree_digest_sha256"] == digest(canonical(observed))

    controls, input3, output3 = git_blobs(SHA, reader.CONTROL_PATHS)
    collector = controls[reader.CONTROL_PATHS[0]]
    constants = {}
    for node in ast.parse(collector).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                constants[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    assert safe_tar(members["collector-source.tar"], controls) == controls
    assert json.loads(members["collector-source-bindings.json"]) == {name: binding(body) for name, body in controls.items()}
    frozen = constants["FROZEN_MANIFEST"]
    assert len(frozen) == 177 and json.loads(members["product-source-manifest.json"]) == frozen
    assert digest(canonical(frozen)) == constants["FROZEN_PRODUCT_DIGEST"]
    assert frozen["hosted/mix.lock"]["sha256"] == constants["FROZEN_LOCK_SHA256"]
    product, input2, output2 = git_blobs(SHA, sorted(frozen))
    assert {name: binding(body) for name, body in product.items()} == frozen
    original, _, _ = git_blobs(constants["PRODUCT_COMMIT"], sorted(frozen))
    assert original == product
    metadata, input4, output4 = git_blobs(SHA, reader.PACKET_PATHS)
    assert safe_tar(members["selected-contract-metadata.tar"], metadata) == metadata
    packet = json.loads(metadata[reader.PACKET_BASE + "packet-manifest.json"])
    assert digest(metadata[reader.PACKET_BASE + "contract.json"]) == constants["CONTRACT_SHA256"]
    assert packet["tree_digest_sha256"] == digest(canonical(packet["files"])) == constants["CONTRACT_PACKET"]
    for path, body in metadata.items():
        if not path.endswith("/packet-manifest.json"):
            assert packet["files"][path.removeprefix(reader.PACKET_BASE)] == binding(body)
    for label, role in (("elixir", "test"), ("postgres", "pg")):
        image = constants["IMAGES"][role]
        assert digest(metadata[reader.PACKET_BASE + "inputs/registry/" + label + "-amd64-manifest.json"]) == image["ref"].split("@sha256:")[1]
        assert digest(metadata[reader.PACKET_BASE + "inputs/registry/" + label + "-amd64-config.json"]) == image["config"].removeprefix("sha256:")
    helpers = {"collector-" + name + ".exs": constants[key].encode() for name, key in (
        ("prerequisites", "PREREQUISITES_EXS"), ("bootstrap", "BOOTSTRAP_EXS"),
        ("manifest", "MANIFEST_EXS"), ("netns", "NETNS_EXS"), ("observer", "OBSERVER_EXS"))}
    bootstrap = constants["BOOTSTRAP_EXS"]
    for placeholder, value in {"HEX_URL": constants["BOOTSTRAP"]["hex"]["url"], "HEX_SHA": constants["BOOTSTRAP"]["hex"]["sha512"],
                               "REBAR_URL": constants["BOOTSTRAP"]["rebar"]["url"], "REBAR_SHA": constants["BOOTSTRAP"]["rebar"]["sha512"]}.items():
        bootstrap = bootstrap.replace(placeholder, value)
    helpers["collector-bootstrap.exs"] = bootstrap.encode()
    helpers["frozen-manifest.json"] = canonical(frozen)
    assert safe_tar(members["literal-helpers.tar"], helpers) == helpers
    assert json.loads(members["literal-helper-bindings.json"]) == {name: binding(body) for name, body in helpers.items()}

    state, finalizer, host = (json.loads(members[name]) for name in ("state.json", "finalizer.json", "host.json"))
    assert state["sha"] == SHA and state["run_id"] == "40730443928" and state["attempt"] == "1"
    assert host["github_run_id"] == state["run_id"] and host["attempt"] == state["attempt"]
    assert host["uname"][0] == "Linux" and host["uname"][-1] == "x86_64" and host["runner"] == "ubuntu-24.04"
    assert state["source"] == {"delivery_revision": SHA, "frozen_product_commit": constants["PRODUCT_COMMIT"],
        "lock_sha256": constants["FROZEN_LOCK_SHA256"], "product_files": 177, "product_tree_digest_sha256": constants["FROZEN_PRODUCT_DIGEST"]}
    logs = [json.loads(members[f"logs/{n:04d}.json"]) for n in range(1, 29)]
    raw_bytes = 0
    for n, row in enumerate(logs, 1):
        assert row["exit_code"] == (1 if n in (19, 28) else 0)
        assert not row["timed_out"] and not row["overflow"] and row["elapsed_seconds"] < row["timeout_seconds"]
        assert row["stdout_complete"] == (n != 19) and row["stderr_complete"] == (n != 19)
        assert row["cwd"] == "/home/runner/work/mixer/mixer"
        assert row["host_environment"] == {"DOCKER_CONFIG": "/home/runner/work/mixer/mixer/identity-network-evidence/.scratch/docker",
            "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1", "HOME": "/home/runner/work/mixer/mixer/identity-network-evidence/.scratch",
            "LANG": "C.UTF-8", "PATH": "/usr/local/bin:/usr/bin:/bin"}
        for ext in ("stdout", "stderr"):
            assert row[ext + "_bytes"] == len(members[f"logs/{n:04d}.{ext}"])
            raw_bytes += row[ext + "_bytes"]
    assert raw_bytes == state["log_bytes"] and state["command_number"] == 28
    assert members["logs/0001.stdout"].decode().strip() == SHA
    for n, request, output in ((2, input2, output2), (3, input3, output3), (4, input4, output4)):
        assert logs[n - 1]["argv"] == ["git", "--no-replace-objects", "cat-file", "--batch"]
        assert logs[n - 1]["stdin_bytes"] == len(request) and logs[n - 1]["stdin_sha256"] == digest(request)
        assert members[f"logs/{n:04d}.stdout"] == output
    for pull_n, inspect_n, role in ((7, 8, "test"), (9, 10, "pg")):
        image = constants["IMAGES"][role]
        assert logs[pull_n - 1]["argv"] == ["docker", "pull", "--platform", "linux/amd64", image["ref"]]
        assert logs[inspect_n - 1]["argv"] == ["docker", "image", "inspect", image["ref"]]
        retained = json.loads(members[role + "-image.json"])
        assert json.loads(members[f"logs/{inspect_n:04d}.stdout"]) == [retained]
        assert retained["Id"] == image["config"] and retained["Architecture"] == "amd64" and retained["Os"] == "linux"
        assert retained["RepoDigests"] == [image["ref"].removeprefix("library/") if role == "pg" else image["ref"]]


    assert len(state["containers"]) == 1 and not state["unresolved_creates"]
    owned = state["containers"][0]
    cid = owned["cid"]
    assert re.fullmatch("[0-9a-f]{64}", cid) and owned["role"] == "prepare" and owned["state"] == "removed"
    assert owned["label"] == state["label"] and owned["name"] == state["label"] + "-prepare"
    assert owned["image_id"] == constants["IMAGES"]["test"]["config"]
    assert members["logs/0011.stdout"] == (cid + "\n").encode()
    create = logs[10]["argv"]
    assert create[:2] == ["docker", "create"] and create[create.index("--network") + 1] == "bridge"
    assert create[create.index("--name") + 1] == owned["name"] and create[-3:] == [owned["image_id"], "-e", "Process.sleep(:infinity)"]
    snapshots = {}
    for n in (12, 13, 14, 16, 18, 20, 21, 23, 24, 26):
        assert logs[n - 1]["argv"] == ["docker", "container", "inspect", cid]
        row, = json.loads(members[f"logs/{n:04d}.stdout"])
        assert row["Id"] == cid and row["Image"] == owned["image_id"] and row["Name"] == "/" + owned["name"]
        assert row["Config"]["Labels"]["mixer.identity.run"] == owned["label"] and row["Config"]["Labels"]["mixer.identity.role"] == "prepare"
        config = row["HostConfig"]
        assert config["NetworkMode"] == "bridge" and config["ReadonlyRootfs"] is True and config["Privileged"] is False
        assert config["Tmpfs"] == constants["TMPFS"]["prepare"] and row["Mounts"] == []
        assert config["SecurityOpt"] == ["no-new-privileges:true"] and config["CapDrop"] == ["ALL"] and not config["CapAdd"]
        memory, cpus, pids = constants["RESOURCES"]["prepare"]
        assert config["Memory"] == config["MemorySwap"] == memory and config["NanoCpus"] == cpus * 10**9 and config["PidsLimit"] == pids
        env = dict(item.split("=", 1) for item in row["Config"]["Env"])
        assert len(env) == len(row["Config"]["Env"]) and env == constants["BASE_ENV"]
        assert not row["State"]["OOMKilled"]
        for field in ("Binds", "Devices", "DeviceRequests", "PortBindings", "VolumesFrom", "ExtraHosts", "Links"):
            assert not config[field]
        if n < 15:
            assert row["State"]["Status"] == "created" and row["State"]["Pid"] == 0 and not row["State"]["Running"]
        elif n < 22:
            assert row["State"]["Status"] == "running" and row["State"]["Running"] and row["State"]["Pid"] > 0
        else:
            assert row["State"]["Status"] == "exited" and not row["State"]["Running"] and row["State"]["Pid"] == 0 and row["State"]["ExitCode"] == 0
        snapshots[n] = row
    assert logs[14]["argv"] == ["docker", "start", cid] and members["logs/0015.stdout"] == (cid + "\n").encode()

    def exec_argv(command, workdir, interactive=False):
        env = constants["BASE_ENV"]
        argv = ["docker", "exec", *(["-i"] if interactive else []), "--workdir", workdir]
        argv += [part for key, value in sorted(env.items()) for part in ("--env", key + "=" + value)]
        argv += [cid, "/usr/bin/env", "-i", *[key + "=" + value for key, value in sorted(env.items())], *command]
        return argv

    transfer = source_tar({**product, **helpers})
    assert safe_tar(transfer, {**product, **helpers}) == {**product, **helpers}
    assert logs[16]["argv"] == exec_argv(["/usr/bin/tar", "--extract", "--file", "-", "--directory", "/workspace", "--no-same-owner", "--no-same-permissions"], "/workspace", True)
    assert logs[16]["stdin_bytes"] == len(transfer) == 3993600 and logs[16]["stdin_sha256"] == digest(transfer)
    assert logs[16]["exit_code"] == 0 and members["logs/0017.stdout"] == members["logs/0017.stderr"] == b""
    assert logs[18]["argv"] == exec_argv(["/usr/local/bin/elixir", "/workspace/collector-prerequisites.exs"], "/workspace/hosted")
    assert logs[18]["stdin_bytes"] == 0 and logs[18]["stdin_sha256"] is None
    assert logs[18]["failure"] == "nonzero/timeout command" and logs[18]["timeout_seconds"] == 15
    missing = b'** (File.Error) could not read file stats "/usr/bin/openssl": no such file or directory'
    assert members["logs/0019.stderr"].startswith(missing + b"\n")
    assert b"(elixir 1.20.4)" in members["logs/0019.stderr"] and b"/workspace/collector-prerequisites.exs:6:" in members["logs/0019.stderr"]
    assert len(members["logs/0019.stderr"]) == 479 and len(members["logs/0019.stdout"]) == 120
    assert len([row for row in logs if row["argv"][:2] == ["docker", "exec"]]) == 2
    assert logs[21]["argv"] == ["docker", "stop", "--time", "2", cid]
    assert json.loads(members["prepare-terminal.json"]) == snapshots[23]
    assert logs[24]["argv"] == ["docker", "logs", cid]
    assert logs[26]["argv"] == ["docker", "rm", "--volumes", cid] and members["logs/0027.stdout"] == (cid + "\n").encode()
    assert logs[27]["argv"] == ["docker", "container", "inspect", cid]
    assert members["logs/0028.stdout"] == b"[]\n" and members["logs/0028.stderr"] == ("Error response from daemon: No such container: " + cid + "\n").encode()
    assert state["primary_failure"] == {"message": "nonzero/timeout command", "type": "CollectorError"}
    assert state["status"] == "FAILED-or-partial" and state["primary_outcome_frozen"] and not state["cancelled"]
    assert state["cleanup"] == {"container_teardown_is_product_lifecycle_proof": False, "errors": [], "status": "verified-exact-created-IDs-absent", "unresolved_creates": []}
    assert finalizer == {"cleanup_verified": True, "no_retry_of_identity_lost_or_unknown_create": True,
        "primary_status": "FAILED-or-partial", "same_original_aggregate_deadline": True, "schema": 1}
    job_log = (ROOT / "job.log").read_text()
    assert re.search(r"Ran 68 tests in [0-9.]+s", job_log) and " OK" in job_log
    docker = json.loads(members["logs/0006.stdout"])
    assert docker["Client"]["Version"] == docker["Server"]["Version"] == "28.0.4"
    contract = json.loads(metadata[reader.PACKET_BASE + "contract.json"])
    assert "Missing tool fails; no apt install or image fallback" in json.dumps(contract)
    image_config = json.loads(metadata[reader.PACKET_BASE + "inputs/registry/elixir-amd64-config.json"])

    selected = expected_names - {"logs/0002.stdout", "logs/0003.stdout", "logs/0004.stdout"}
    for name in selected:
        reader.write_regular("artifact/" + name, members[name])
    for label, archive in (("collector-source", controls), ("literal-helpers", helpers), ("selected-contract-metadata", metadata)):
        for name, body in archive.items():
            reader.write_regular(label + "/" + name, body)
    result = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": "python3 -B verification/github-delivery-identity-network-transfer/network-review/verify_failed_artifact.py",
        "reviewer_python": platform.python_version(), "reviewer_git": subprocess.check_output(["git", "--version"], text=True, timeout=5).strip(),
        "reviewer_script_sha256": digest(Path(__file__).read_bytes()), "reader_utility_sha256": digest(UTILITY.read_bytes()),
        "delivery_revision": SHA, "zip": {"bytes": len(data), "sha256": ZIP_SHA}, "members": len(members), "expanded_bytes": expanded,
        "all_members_crc_size_and_manifest_sha256_verified": True, "artifact_manifest_files": len(observed), "artifact_manifest_tree_digest_sha256": manifest["tree_digest_sha256"],
        "collector_source_files_bound_to_commit": 4, "contract_metadata_files_bound_to_commit": 8, "literal_helpers_bound_to_committed_AST_literals_and_substitutions": 6,
        "product_files_bound_to_delivery_and_frozen_commit": 177, "frozen_product_commit": constants["PRODUCT_COMMIT"],
        "product_digest_sha256": constants["FROZEN_PRODUCT_DIGEST"], "lock_sha256": constants["FROZEN_LOCK_SHA256"],
        "remote_host": host, "remote_docker": docker, "remote_git": members["logs/0005.stdout"].decode().strip(),
        "remote_control_tests": {"run": 68, "failures": 0, "skipped": 0}, "command_receipts_bound": 28, "raw_log_bytes_bound": raw_bytes,
        "successful_initial_transfer": {"command": 17, "stdin_bytes": len(transfer), "stdin_sha256": digest(transfer), "exit_code": 0,
            "all_183_files_independently_reinventoried_after_extraction": False, "prerequisite_helper_subsequently_loaded_and_executed": True},
        "primary_failure": {"command": 19, "argv": logs[18]["argv"], "exit_code": 1, "stderr": members["logs/0019.stderr"].decode(),
            "timed_out": False, "overflow": False, "producer_stream_complete_flags": False,
            "stream_flag_scope": "generic command failure handler marks streams incomplete; exact retained bytes bound, no complete-stream pass claimed",
            "proven_cause": "File.stat! cannot resolve the required /usr/bin/openssl file in the selected immutable image before bootstrap",
            "scope_of_absence": "ENOENT at this exact required path; missing directory entry and dangling symlink are not distinguished; no alternate path or whole-image filesystem probe performed"},
        "image_history": image_config["history"],
        "actual_remote_scope": {"pinned_images_pulled": 2, "prepare_containers_created_and_started": 1,
            "successful_initial_tar_transfers": 1, "docker_exec_commands": 2, "prerequisite_helper_executions": 1,
            "traceback_actual_elixir_version": "1.20.4", "OTP_patch_or_Mix_version_receipt": False,
            "openssl_CLI_invocations": 0, "bootstrap_downloads": 0, "product_methods_run": 0,
            "test_namespace_created": False, "postgres_started_or_migrations_applied": False,
            "fresh_semantics_loaded_modules_or_post_extraction_immutability_evidence": False, "synthetic_fixture_keys_created": False},
        "cleanup": {"cid": cid, "stop_command": 22, "terminal_exit_code": 0, "OOMKilled": False,
            "exact_remove_command": 27, "exact_absence_command": 28, "exact_created_ID_absent": True, "unresolved_creates": [],
            "images": "pulled; no image-removal receipt or claim", "host_scratch": "removal reported by state and bound seal source; no separate filesystem listing receipt", "product_lifecycle_proof": False},
        "selected_regular_zip_members": len(selected), "selected_regular_tar_members": 18,
        "review_activity": {"local_product_or_control_tests": 0, "local_runtime_or_process_probes": 0, "CI_mutations": 0, "canonical_writes": 0, "held_operations": 0},
        "result": "failed transfer-fixed attempt retained and independently verified; product runtime unqualified"}
    (ROOT / "verification-result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    signal.alarm(0)
    print(json.dumps({k: result[k] for k in ("result", "zip", "members", "artifact_manifest_tree_digest_sha256", "command_receipts_bound", "successful_initial_transfer", "primary_failure", "actual_remote_scope", "cleanup")}, indent=2))


if __name__ == "__main__":
    main()
