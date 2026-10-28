#!/usr/bin/env python3
"""Bounded, offline verification of the first failed identity network artifact.

Reads only the retained ZIP and immutable Git blobs. Never invokes Docker,
compiler/runtime tools, sockets, CI actions, or the product/collector code.
"""
import ast
import datetime
import hashlib
import io
import json
import pathlib
import platform
import re
import stat
import subprocess
import sys
import tarfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[2]
SHA = "756695fb9b0f6ec85d978202e2b3c586aa3db16f"
ZIP_SHA = "fad8b54f1030b71556437ec5e72c854c8d3e73335228aae9d221f24759fa83da"
CAP = 8 * 1024 * 1024
CONTROL_PATHS = [
    "hosted/scripts/test-identity-network.py",
    "hosted/scripts/test_identity_network_collector.py",
    "docs/hosted-identity-production-network-ci-contract.md",
    ".github/workflows/identity-network.yml",
]
PACKET_BASE = "verification/identity-production-network-contract/"
PACKET_PATHS = [PACKET_BASE + "contract.json", PACKET_BASE + "packet-manifest.json"]
for image in ("elixir", "postgres"):
    PACKET_PATHS.extend(PACKET_BASE + "inputs/registry/" + image + suffix for suffix in
                        ("-index.json", "-amd64-manifest.json", "-amd64-config.json"))
META_NAMES = [
    "artifact-manifest.json", "collector-source-bindings.json", "collector-source.tar",
    "finalizer.json", "host.json", "literal-helper-bindings.json", "literal-helpers.tar",
    "pg-image.json", "prepare-terminal.json", "product-source-manifest.json",
    "selected-contract-metadata.tar", "state.json", "test-image.json",
]
EXPLICIT_ZIP_NAMES = set(META_NAMES)
EXPLICIT_ZIP_NAMES.update(f"logs/{n:04d}.{ext}" for n in range(1, 22)
                          for ext in ("json", "stdout", "stderr"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def binding(data):
    return {"bytes": len(data), "sha256": digest(data)}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def safe_name(name):
    assert isinstance(name, str) and name and not name.startswith("/")
    assert "\\" not in name and ":" not in name and "\x00" not in name
    assert all(part not in ("", ".", "..") for part in name.split("/"))
    assert str(pathlib.PurePosixPath(name)) == name


def git_blobs(revision, paths):
    request = "".join(revision + ":" + path + "\n" for path in paths).encode()
    run = subprocess.run(["git", "--no-replace-objects", "cat-file", "--batch"],
                         input=request, cwd=REPO, capture_output=True, timeout=20, check=True)
    assert not run.stderr and len(run.stdout) <= CAP
    cursor, result = 0, {}
    for path in paths:
        end = run.stdout.index(b"\n", cursor)
        oid, kind, size = run.stdout[cursor:end].split()
        assert kind == b"blob" and re.fullmatch(b"[0-9a-f]{40}", oid)
        cursor = end + 1
        body = run.stdout[cursor:cursor + int(size)]
        assert len(body) == int(size)
        assert hashlib.sha1(b"blob " + size + b"\x00" + body).hexdigest().encode() == oid
        result[path] = body
        cursor += int(size)
        assert run.stdout[cursor:cursor + 1] == b"\n"
        cursor += 1
    assert cursor == len(run.stdout)
    return result, request, run.stdout


def safe_tar(raw, expected_names):
    result, folded, total = {}, set(), 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
        for member in archive.getmembers():
            safe_name(member.name)
            assert member.name not in result and member.name.casefold() not in folded
            assert member.isfile() and not member.linkname and not member.pax_headers
            assert 0 <= member.size <= CAP
            total += member.size
            assert total <= CAP
            folded.add(member.name.casefold())
            body = archive.extractfile(member).read(CAP + 1)
            assert len(body) == member.size
            result[member.name] = body
    assert set(result) == set(expected_names)
    return result


def write_regular(relative, body):
    safe_name(relative)
    target = ROOT / "selected" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.is_symlink()
    if target.exists():
        assert target.is_file() and target.read_bytes() == body
    else:
        with target.open("xb") as stream:
            stream.write(body)


def main():
    zip_bytes = (ROOT / "artifact.zip").read_bytes()
    assert len(zip_bytes) == 729361 and digest(zip_bytes) == ZIP_SHA
    members, folded, expanded = {}, set(), 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for member in archive.infolist():
            safe_name(member.filename)
            assert member.filename not in members and member.filename.casefold() not in folded
            assert not member.is_dir() and not member.flag_bits & 1
            assert stat.S_IFMT(member.external_attr >> 16) in (0, stat.S_IFREG)
            assert 0 <= member.file_size <= CAP
            expanded += member.file_size
            assert expanded <= CAP
            folded.add(member.filename.casefold())
            body = archive.read(member)  # Verifies each CRC, including non-extracted members.
            assert len(body) == member.file_size
            members[member.filename] = body
    assert set(members) == EXPLICIT_ZIP_NAMES and len(members) == 76
    artifact_manifest = json.loads(members["artifact-manifest.json"])
    actual = {name: binding(body) for name, body in members.items()
              if name != "artifact-manifest.json"}
    assert artifact_manifest["files"] == actual
    assert digest(canonical(actual)) == artifact_manifest["tree_digest_sha256"]
    assert artifact_manifest["schema"] == 1

    controls, request3, output3 = git_blobs(SHA, CONTROL_PATHS)
    collector = controls[CONTROL_PATHS[0]]
    constants = {}
    for node in ast.parse(collector).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                constants[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass  # Parse literals only; never import or execute the collector.
    source_archive = safe_tar(members["collector-source.tar"], CONTROL_PATHS)
    assert source_archive == controls
    assert json.loads(members["collector-source-bindings.json"]) == {
        name: binding(body) for name, body in controls.items()}

    product_manifest = json.loads(members["product-source-manifest.json"])
    assert product_manifest == constants["FROZEN_MANIFEST"] and len(product_manifest) == 177
    assert digest(canonical(product_manifest)) == constants["FROZEN_PRODUCT_DIGEST"]
    assert product_manifest["hosted/mix.lock"]["sha256"] == constants["FROZEN_LOCK_SHA256"]
    product, request2, output2 = git_blobs(SHA, sorted(product_manifest))
    assert {name: binding(body) for name, body in product.items()} == product_manifest
    frozen_product, _, _ = git_blobs(constants["PRODUCT_COMMIT"], sorted(product_manifest))
    assert product == frozen_product

    metadata, request4, output4 = git_blobs(SHA, PACKET_PATHS)
    assert safe_tar(members["selected-contract-metadata.tar"], PACKET_PATHS) == metadata
    assert digest(metadata[PACKET_BASE + "contract.json"]) == constants["CONTRACT_SHA256"]
    packet = json.loads(metadata[PACKET_BASE + "packet-manifest.json"])
    assert packet["tree_digest_sha256"] == constants["CONTRACT_PACKET"]
    assert digest(canonical(packet["files"])) == constants["CONTRACT_PACKET"]
    for name, body in metadata.items():
        if name != PACKET_BASE + "packet-manifest.json":
            assert packet["files"][name.removeprefix(PACKET_BASE)] == binding(body)
    for label, role in (("elixir", "test"), ("postgres", "pg")):
        image = constants["IMAGES"][role]
        assert digest(metadata[PACKET_BASE + "inputs/registry/" + label + "-amd64-manifest.json"]) == image["ref"].split("@sha256:")[1]
        assert digest(metadata[PACKET_BASE + "inputs/registry/" + label + "-amd64-config.json"]) == image["config"].removeprefix("sha256:")

    helpers = {"collector-" + name + ".exs": constants[key].encode() for name, key in (
        ("prerequisites", "PREREQUISITES_EXS"), ("bootstrap", "BOOTSTRAP_EXS"),
        ("manifest", "MANIFEST_EXS"), ("netns", "NETNS_EXS"), ("observer", "OBSERVER_EXS"))}
    # Reproduce only the four explicit literal substitutions at committed lines
    # 539-540. Do not execute the collector's top-level source.
    bootstrap = constants["BOOTSTRAP_EXS"]
    for placeholder, value in {
            "HEX_URL": constants["BOOTSTRAP"]["hex"]["url"],
            "HEX_SHA": constants["BOOTSTRAP"]["hex"]["sha512"],
            "REBAR_URL": constants["BOOTSTRAP"]["rebar"]["url"],
            "REBAR_SHA": constants["BOOTSTRAP"]["rebar"]["sha512"]}.items():
        bootstrap = bootstrap.replace(placeholder, value)
    helpers["collector-bootstrap.exs"] = bootstrap.encode()
    helpers["frozen-manifest.json"] = canonical(constants["FROZEN_MANIFEST"])
    assert safe_tar(members["literal-helpers.tar"], helpers) == helpers
    assert json.loads(members["literal-helper-bindings.json"]) == {
        name: binding(body) for name, body in helpers.items()}

    state = json.loads(members["state.json"])
    finalizer = json.loads(members["finalizer.json"])
    host = json.loads(members["host.json"])
    assert state["sha"] == SHA and state["run_id"] == "40723227447" and state["attempt"] == "1"
    assert host["github_run_id"] == state["run_id"] and host["attempt"] == state["attempt"]
    assert host["runner"] == "ubuntu-24.04" and host["uname"][0] == "Linux" and host["uname"][-1] == "x86_64"
    assert state["source"] == {
        "delivery_revision": SHA, "frozen_product_commit": constants["PRODUCT_COMMIT"],
        "product_files": 177, "product_tree_digest_sha256": constants["FROZEN_PRODUCT_DIGEST"],
        "lock_sha256": constants["FROZEN_LOCK_SHA256"]}
    logs = [json.loads(members[f"logs/{n:04d}.json"]) for n in range(1, 22)]
    log_bytes = 0
    for n, log in enumerate(logs, 1):
        assert log["stdout_complete"] is True and log["stderr_complete"] is True
        assert log["overflow"] is False and log["timed_out"] is False
        assert 0 <= log["elapsed_seconds"] < log["timeout_seconds"]
        assert log["cwd"] == "/home/runner/work/mixer/mixer"
        assert log["host_environment"] == {
            "DOCKER_CONFIG": "/home/runner/work/mixer/mixer/identity-network-evidence/.scratch/docker",
            "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1",
            "HOME": "/home/runner/work/mixer/mixer/identity-network-evidence/.scratch",
            "LANG": "C.UTF-8", "PATH": "/usr/local/bin:/usr/bin:/bin"}
        for ext in ("stdout", "stderr"):
            assert log[ext + "_bytes"] == len(members[f"logs/{n:04d}.{ext}"])
            log_bytes += log[ext + "_bytes"]
        assert log["exit_code"] == (1 if n == 21 else 0)
    assert log_bytes == state["log_bytes"] and state["command_number"] == 21
    assert logs[0]["argv"] == ["git", "--no-replace-objects", "rev-parse", "HEAD"]
    assert members["logs/0001.stdout"].decode().strip() == SHA
    for n, request, output in ((2, request2, output2), (3, request3, output3), (4, request4, output4)):
        log = logs[n - 1]
        assert log["argv"] == ["git", "--no-replace-objects", "cat-file", "--batch"]
        assert log["stdin_sha256"] == digest(request) and log["stdin_bytes"] == len(request)
        assert members[f"logs/{n:04d}.stdout"] == output
    docker_version = json.loads(members["logs/0006.stdout"])
    for pull_n, inspect_n, role in ((7, 8, "test"), (9, 10, "pg")):
        image = constants["IMAGES"][role]
        assert logs[pull_n - 1]["argv"] == ["docker", "pull", "--platform", "linux/amd64", image["ref"]]
        assert logs[inspect_n - 1]["argv"] == ["docker", "image", "inspect", image["ref"]]
        inspected = json.loads(members[f"logs/{inspect_n:04d}.stdout"])
        retained = json.loads(members[role + "-image.json"])
        assert inspected == [retained]
        assert retained["Id"] == image["config"] and retained["Architecture"] == "amd64" and retained["Os"] == "linux"
        expected_repo_digest = image["ref"].removeprefix("library/") if role == "pg" else image["ref"]
        assert retained["RepoDigests"] == [expected_repo_digest]

    assert len(state["containers"]) == 1 and not state["unresolved_creates"]
    owned = state["containers"][0]
    cid = owned["cid"]
    assert re.fullmatch("[0-9a-f]{64}", cid) and owned["role"] == "prepare" and owned["state"] == "removed"
    assert owned["label"] == state["label"] and owned["name"] == state["label"] + "-prepare"
    assert owned["image_id"] == constants["IMAGES"]["test"]["config"]
    assert members["logs/0011.stdout"] == (cid + "\n").encode()
    argv = logs[10]["argv"]
    assert argv[:2] == ["docker", "create"] and argv[argv.index("--network") + 1] == "default"
    assert argv[argv.index("--name") + 1] == owned["name"]
    assert argv[-3:] == [owned["image_id"], "-e", "Process.sleep(:infinity)"]
    terminal = json.loads(members["prepare-terminal.json"])
    assert terminal == json.loads(members["logs/0016.stdout"])[0]
    inspections = []
    for n in (12, 13, 14, 16, 17, 19):
        assert logs[n - 1]["argv"] == ["docker", "container", "inspect", cid]
        rows = json.loads(members[f"logs/{n:04d}.stdout"])
        assert len(rows) == 1
        row = rows[0]
        assert row["Id"] == cid and row["Image"] == owned["image_id"] and row["Name"] == "/" + owned["name"]
        assert row["Config"]["Labels"]["mixer.identity.run"] == owned["label"]
        assert row["Config"]["Labels"]["mixer.identity.role"] == "prepare"
        assert row["HostConfig"]["NetworkMode"] == "bridge"
        assert row["State"]["Status"] == "created" and row["State"]["Running"] is False and row["State"]["Pid"] == 0
        assert row["State"]["StartedAt"] == "0001-01-01T00:00:00Z" and row["State"]["OOMKilled"] is False
        inspections.append(n)
    assert logs[14]["argv"] == ["docker", "stop", "--time", "2", cid]
    assert logs[17]["argv"] == ["docker", "logs", cid] and members["logs/0018.stdout"] == b""
    assert logs[19]["argv"] == ["docker", "rm", "--volumes", cid]
    assert members["logs/0020.stdout"] == (cid + "\n").encode()
    assert logs[20]["argv"] == ["docker", "container", "inspect", cid]
    assert members["logs/0021.stdout"] == b"[]\n"
    assert members["logs/0021.stderr"] == ("Error response from daemon: No such container: " + cid + "\n").encode()
    assert state["primary_failure"] == {"type": "CollectorError", "message": "container network mismatch"}
    assert state["primary_outcome_frozen"] is True and state["status"] == "FAILED-or-partial" and state["cancelled"] is False
    assert state["cleanup"] == {"container_teardown_is_product_lifecycle_proof": False, "errors": [],
        "status": "verified-exact-created-IDs-absent", "unresolved_creates": []}
    assert finalizer == {"cleanup_verified": True, "no_retry_of_identity_lost_or_unknown_create": True,
        "primary_status": "FAILED-or-partial", "same_original_aggregate_deadline": True, "schema": 1}
    assert not any(log["argv"][:2] in (["docker", "start"], ["docker", "exec"], ["docker", "cp"]) for log in logs)
    assert not any("mix" in log["argv"] or "openssl" in log["argv"] for log in logs)
    assert b'network = {"prepare": "default", "test": "none", "pg": "container:" + (test_cid or "")}[role]' in collector
    assert b'require(config.get("NetworkMode") == network' in collector

    # Explicit file selection only; the three bulk Git outputs remain immutable in ZIP.
    selected = EXPLICIT_ZIP_NAMES - {"logs/0002.stdout", "logs/0003.stdout", "logs/0004.stdout"}
    for name in sorted(selected):
        write_regular("artifact/" + name, members[name])
    for label, archive in (("collector-source", source_archive), ("literal-helpers", helpers),
                           ("selected-contract-metadata", metadata)):
        for name, body in archive.items():
            write_regular(label + "/" + name, body)
    summary = {
        "schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "command": "python3 -B verification/github-delivery-identity-network/network-review/verify_failed_artifact.py",
        "scope": "offline retained failed-artifact and immutable committed-blob verification only",
        "reviewer_python": platform.python_version(),
        "reviewer_git": subprocess.check_output(["git", "--version"], text=True, timeout=5).strip(),
        "reviewer_script_sha256": digest(pathlib.Path(__file__).read_bytes()),
        "delivery_revision": SHA, "zip": {"bytes": len(zip_bytes), "sha256": ZIP_SHA},
        "zip_members": len(members), "expanded_bytes": expanded,
        "artifact_manifest_bound_files": len(actual), "artifact_tree_digest_sha256": artifact_manifest["tree_digest_sha256"],
        "all_member_crc_size_and_sha256_verified": True,
        "source": {"collector_files_bound_to_delivery_revision": len(controls),
            "metadata_files_bound_to_delivery_revision": len(metadata),
            "literal_helpers_bound_to_committed_AST_literals": len(helpers),
            "product_files_bound_to_delivery_and_frozen_revisions": len(product),
            "frozen_product_commit": constants["PRODUCT_COMMIT"],
            "product_digest_sha256": constants["FROZEN_PRODUCT_DIGEST"],
            "lock_sha256": constants["FROZEN_LOCK_SHA256"]},
        "command_receipts_verified": len(logs), "raw_log_bytes_bound": log_bytes,
        "remote_host_python": host["python"], "remote_git": members["logs/0005.stdout"].decode().strip(),
        "remote_docker_version": docker_version,
        "remote_scope": {"images_pulled_and_platform_config_pins_verified": 2,
            "containers_created": 1, "containers_started": 0, "docker_exec_or_copy_commands": 0,
            "bootstrap_downloads_or_tool_probes": 0, "product_methods_run": 0,
            "postgres_processes_or_migrations_run": 0, "TLS_or_OpenSSL_processes_run": 0,
            "synthetic_signing_keys_created_by_fixture": 0},
        "primary_failure": {"type": "CollectorError", "message": "container network mismatch",
            "requested_prepare_network": "default", "observed_prepare_NetworkMode": "bridge",
            "first_rejected_inspection_command": 12, "source_validator_lines": [189, 190],
            "source_create_line": 772},
        "cleanup": {"exact_created_cid": cid, "removed_command": 20, "absence_command": 21,
            "all_created_owned_container_ids_absent": True, "unresolved_creates": [],
            "host_scratch_removal": "reported by state and bound seal source; no separate filesystem listing receipt",
            "images": "pulled; no image-removal receipt or claim", "product_lifecycle_proof": False},
        "safe_selection": {"zip_members_selected": len(selected), "tar_members_selected": 18,
            "regular_files_only": True, "traversal_links_devices_fifo_duplicate_aliases_encryption_refused": True},
        "review_activity": {"network_requests": 0, "runtime_commands": 0, "product_tests": 0,
            "CI_mutations": 0, "canonical_writes": 0, "commits_or_pushes": 0},
        "result": "failed attempt verified and retained; no product-runtime qualification"
    }
    (ROOT / "verification-result.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
