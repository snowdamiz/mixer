#!/usr/bin/env python3
"""Independent pure source/receipt correction review; no runtime acceptance."""
import ast
import contextlib
import copy
import datetime
import difflib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest import mock
import zipfile

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FAILED = HERE.parent
REPO = HERE.parents[3]
AUTHOR = REPO / "verification/identity-network-transfer-correction"
SHA = "c450ed48d14df1f2cf1140dd3f8807890a8fe9d0"
PATHS = ["hosted/scripts/test-identity-network.py", "hosted/scripts/test_identity_network_collector.py"]
EXPECTED = {PATHS[0]: {"bytes": 115499, "sha256": "0dd09afab430ff2478c8dfe800465dec8cd154ca78f5f80f4049433e92bd540d"},
            PATHS[1]: {"bytes": 67242, "sha256": "0b617486a69a693da79bcb8c4364658fac81013004296f6e05e6368f9e70e683"}}


def binding(body):
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}


def verify_packet(root, expected_digest):
    packet = json.loads((root / "packet-manifest.json").read_bytes())
    for path, expected in packet["files"].items():
        file = root / path
        assert file.is_file() and not file.is_symlink() and binding(file.read_bytes()) == expected
    observed = hashlib.sha256(json.dumps(packet["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert observed == packet["tree_digest_sha256"] == expected_digest
    return len(packet["files"])


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    def deadline(signum, frame):
        raise TimeoutError("pure correction review exceeded 50 seconds")
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(50)
    failed_count = verify_packet(FAILED, "984097146b120f77d5a9e77ab1e53d98df6fc906256a8e7be3dee87a85e7f91b")
    author_count = verify_packet(AUTHOR, "eaf3c781e44e338ccb685243b38145c0dd577dc798524ec2b9083f19b7e7548d")
    assert binding((AUTHOR / "packet-manifest.json").read_bytes())["sha256"] == "3adff9fec33774e43459d55b93799fb4263f1b5a30a9115e7340061b7cef438b"
    before = {path: subprocess.check_output(["git", "--no-replace-objects", "show", SHA + ":" + path], cwd=REPO, timeout=15) for path in PATHS}
    candidate = {path: (REPO / path).read_bytes() for path in PATHS}
    assert {path: binding(body) for path, body in candidate.items()} == EXPECTED
    old_tree, new_tree = ast.parse(before[PATHS[0]]), ast.parse(candidate[PATHS[0]])
    old_methods = next(n for n in old_tree.body if isinstance(n, ast.ClassDef) and n.name == "Collector")
    new_methods = next(n for n in new_tree.body if isinstance(n, ast.ClassDef) and n.name == "Collector")
    old_method_map = {n.name: n for n in old_methods.body if isinstance(n, ast.FunctionDef)}
    changed = {n.name for n in new_methods.body if isinstance(n, ast.FunctionDef) and
               ast.dump(n, include_attributes=False) != ast.dump(old_method_map[n.name], include_attributes=False)}
    assert changed == {"execute", "copy_in"}
    reduced = copy.deepcopy(new_tree)
    reduced.body = [n for n in reduced.body if not (isinstance(n, ast.FunctionDef) and n.name == "validate_transfer_archive")]
    for node in reduced.body:
        if isinstance(node, ast.ClassDef) and node.name == "Collector":
            node.body = [old_method_map[n.name] if isinstance(n, ast.FunctionDef) and n.name in changed else n for n in node.body]
    assert ast.dump(reduced, include_attributes=False) == ast.dump(old_tree, include_attributes=False)
    old_tests, new_tests = ast.parse(before[PATHS[1]]), ast.parse(candidate[PATHS[1]])
    baseline_tests = {n.name: n for n in ast.walk(old_tests) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
    final_tests = {n.name: n for n in ast.walk(new_tests) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
    assert len(baseline_tests) == 58 and len(final_tests) == 68
    assert set(baseline_tests) <= set(final_tests)
    assert all(ast.dump(node, include_attributes=False) == ast.dump(final_tests[name], include_attributes=False) for name, node in baseline_tests.items())
    for path, body in candidate.items():
        target = HERE / "candidate" / Path(path).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    diff = "".join("".join(difflib.unified_diff(before[path].decode().splitlines(True), candidate[path].decode().splitlines(True),
                fromfile=SHA + ":" + path, tofile="candidate:" + path)) for path in PATHS)
    (HERE / "candidate.diff").write_text(diff)
    git_version = subprocess.check_output(["git", "--version"], text=True, cwd=REPO, timeout=5).strip()

    # Reconstruct the original requested transfer solely from retained bytes.
    with zipfile.ZipFile(FAILED / "artifact.zip") as archive:
        frozen = json.loads(archive.read("product-source-manifest.json"))
        raw, cursor, product = archive.read("logs/0002.stdout"), 0, {}
        for path in sorted(frozen):
            end = raw.index(b"\n", cursor)
            oid, kind, size = raw[cursor:end].split()
            assert kind == b"blob"
            cursor = end + 1
            body = raw[cursor:cursor + int(size)]
            assert hashlib.sha1(b"blob " + size + b"\x00" + body).hexdigest().encode() == oid
            assert binding(body) == frozen[path]
            product[path] = body
            cursor += int(size)
            assert raw[cursor:cursor + 1] == b"\n"
            cursor += 1
        assert cursor == len(raw)
        helpers = {}
        helper_bindings = json.loads(archive.read("literal-helper-bindings.json"))
        with tarfile.open(fileobj=io.BytesIO(archive.read("literal-helpers.tar")), mode="r:") as helpers_tar:
            for member in helpers_tar.getmembers():
                assert member.isfile() and member.name in helper_bindings and member.name not in helpers
                helpers[member.name] = helpers_tar.extractfile(member).read()
                assert binding(helpers[member.name]) == helper_bindings[member.name]
        assert len(helpers) == 6
        actual_inspect_bytes = archive.read("logs/0016.stdout")
        actual, = json.loads(actual_inspect_bytes)
    memory = io.BytesIO()
    with tarfile.open(fileobj=memory, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        for path, body in sorted({**product, **helpers}.items()):
            member = tarfile.TarInfo(path)
            member.size, member.mode, member.mtime = len(body), 0o644, 0
            archive.addfile(member, io.BytesIO(body))
    requested_transfer = memory.getvalue()
    assert binding(requested_transfer) == {"bytes": 3993600, "sha256": "14c1b38284fb835a16841b8dcb1065b2ef600abd6d59d2e8d869be561204b9fd"}

    # Any external process or socket event from candidate imports/controls fails.
    forbidden = []
    def guard(event, args):
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.fork", "os.exec"}:
            forbidden.append(event)
            raise RuntimeError("external work forbidden in independent pure review: " + event)
    sys.addaudithook(guard)
    scratch = HERE / ".scratch"
    scratch.mkdir(exist_ok=False)
    tempfile.tempdir = str(scratch)
    subject = load("independent_transfer_candidate", HERE / "candidate/test-identity-network.py")
    assert subject.validate_transfer_archive(requested_transfer) is requested_transfer
    actual_before = json.dumps(actual, sort_keys=True)
    owned = subject.OwnedContainer(cid=actual["Id"], name=actual["Name"].removeprefix("/"), role="prepare",
        image_id=actual["Image"], label=actual["Config"]["Labels"]["mixer.identity.run"])
    assert subject.validate_container_inspect("prepare", actual, owned) is actual
    assert subject.validate_container_environment("prepare", actual) == subject.BASE_ENV
    transcript = []
    expected_argv = ["docker", "exec", "-i", "--workdir", "/workspace"]
    expected_argv += [part for key, value in sorted(subject.BASE_ENV.items()) for part in ("--env", key + "=" + value)]
    expected_argv += [owned.cid, "/usr/bin/env", "-i", *[key + "=" + value for key, value in sorted(subject.BASE_ENV.items())],
        "/usr/bin/tar", "--extract", "--file", "-", "--directory", "/workspace", "--no-same-owner", "--no-same-permissions"]
    def fake_runner(argv, timeout, input_bytes):
        transcript.append({"argv": argv, "timeout_seconds": timeout, "stdin": binding(input_bytes) if input_bytes is not None else None})
        if argv == ["docker", "container", "inspect", owned.cid]:
            assert input_bytes is None
            return 0, actual_inspect_bytes, b""
        assert argv == expected_argv and input_bytes == requested_transfer and 0 < timeout <= 30
        return 0, b"", b""
    with mock.patch.dict("os.environ", {"GITHUB_RUN_ID": "40726592726", "GITHUB_RUN_ATTEMPT": "1"}):
        replay = subject.Collector(REPO, scratch / "replayed-transfer", SHA, runner=fake_runner)
    replay.copy_in(owned, requested_transfer)
    assert len(transcript) == 2 and transcript[1]["argv"] == expected_argv
    assert json.dumps(actual, sort_keys=True) == actual_before
    (HERE / "actual-input-pure-transcript.json").write_text(json.dumps({"scope": "fake command runner only; no Docker or extraction executed", "commands": transcript}, indent=2) + "\n")
    shutil.rmtree(scratch / "replayed-transfer")

    controls = load("independent_transfer_controls", REPO / PATHS[1])
    suite = unittest.defaultTestLoader.loadTestsFromModule(controls)
    assert suite.countTestCases() == 68
    output, start = io.StringIO(), time.monotonic()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    elapsed = time.monotonic() - start
    (HERE / "controls.log").write_text(output.getvalue())
    assert result.testsRun == 68 and not result.failures and not result.errors and not result.skipped and not forbidden
    assert not list(scratch.iterdir())
    scratch.rmdir()
    assert {path: binding((REPO / path).read_bytes()) for path in PATHS} == EXPECTED
    verify_packet(FAILED, "984097146b120f77d5a9e77ab1e53d98df6fc906256a8e7be3dee87a85e7f91b")
    verify_packet(AUTHOR, "eaf3c781e44e338ccb685243b38145c0dd577dc798524ec2b9083f19b7e7548d")
    decision = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "transfer-correction-source-and-pure-controls-suitable-for-root-delivery; runtime-unqualified",
        "command": "python3 -B verification/github-delivery-identity-network-bridge/network-review/correction-review/review_correction.py",
        "reviewer_python": platform.python_version(), "reviewer_git": git_version, "reviewer_script_sha256": binding(Path(__file__).read_bytes())["sha256"],
        "baseline_revision": SHA, "candidate": EXPECTED,
        "source_review": {"collector_changed_methods": sorted(changed), "collector_added_function": "validate_transfer_archive",
            "all_other_collector_AST_unchanged": True, "all_58_baseline_test_methods_AST_unchanged": True,
            "new_test_methods": sorted(set(final_tests) - set(baseline_tests)), "blocking_findings": []},
        "actual_retained_inputs": {"requested_tar": binding(requested_transfer), "members": 183, "new_validator_accepts_exact_requested_tar": True,
            "actual_running_prepare_inspect": binding(actual_inspect_bytes), "full_inspect_and_environment_guard_pass": True,
            "runtime_inspect_fields_modified": 0, "closed_workdir_exact_CID_cleared_env_stdin_tar_plan_verified_with_fake_runner": True,
            "real_transfer_or_extraction_executed": False},
        "pure_controls": {"run": result.testsRun, "failures": 0, "errors": 0, "skipped": 0, "elapsed_seconds": elapsed,
            "external_process_or_socket_audit_events": forbidden},
        "immutable_packets": {"failed_files_verified": failed_count, "failed_digest_sha256": "984097146b120f77d5a9e77ab1e53d98df6fc906256a8e7be3dee87a85e7f91b",
            "author_files_verified": author_count, "author_digest_sha256": "eaf3c781e44e338ccb685243b38145c0dd577dc798524ec2b9083f19b7e7548d"},
        "scratch_cleanup": "only owned pure review .scratch removed after complete verification",
        "activity": {"canonical_writes": 0, "Docker_runtime_compiler_native_UI_capture_process_probes_or_held_operations": 0, "CI_mutations": 0, "commits_or_pushes": 0},
        "limitations": ["GNU tar availability, extraction behavior, resulting modes/ownership and full bootstrap remain remote-CI gates",
            "candidate validation and fake transcript do not prove a successful transfer", "exact two product methods, namespace/PG/migration/semantics/modules/key lifecycle remain unrun",
            "all failed attempts remain failed; no held, native, customer, or GA acceptance"]}
    (HERE / "decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n")
    signal.alarm(0)
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
