#!/usr/bin/env python3
"""Pure review of the bridge correction against the immutable failed packet."""
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
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
FAILED = HERE.parent
REPO = HERE.parents[3]
SHA = "756695fb9b0f6ec85d978202e2b3c586aa3db16f"
PATHS = ["hosted/scripts/test-identity-network.py", "hosted/scripts/test_identity_network_collector.py"]


def bind(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def verify_failed_packet():
    packet = json.loads((FAILED / "packet-manifest.json").read_bytes())
    for path, expected in packet["files"].items():
        assert bind((FAILED / path).read_bytes()) == expected
    assert hashlib.sha256(json.dumps(packet["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest() == packet["tree_digest_sha256"]
    return packet["tree_digest_sha256"]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    packet_digest = verify_failed_packet()
    before = {path: subprocess.check_output(["git", "--no-replace-objects", "show", SHA + ":" + path], cwd=REPO, timeout=15) for path in PATHS}
    candidate = {path: (REPO / path).read_bytes() for path in PATHS}
    expected = before[PATHS[0]]
    old1, new1 = b'network = {"prepare": "default", "test": "none"', b'network = {"prepare": "bridge", "test": "none"'
    old2, new2 = b'("none" if role == "test" else "default")', b'("none" if role == "test" else "bridge")'
    assert expected.count(old1) == 1 and expected.count(old2) == 1
    expected = expected.replace(old1, new1).replace(old2, new2)
    assert expected == candidate[PATHS[0]], "collector contains changes beyond the exact two network strings"

    old_tree, new_tree = ast.parse(before[PATHS[1]]), ast.parse(candidate[PATHS[1]])
    old_fixture = next(n for n in old_tree.body if isinstance(n, ast.FunctionDef) and n.name == "exact_container")
    new_fixture = next(n for n in new_tree.body if isinstance(n, ast.FunctionDef) and n.name == "exact_container")
    old_fixture_text = ast.get_source_segment(before[PATHS[1]].decode(), old_fixture)
    new_fixture_text = ast.get_source_segment(candidate[PATHS[1]].decode(), new_fixture)
    assert old_fixture_text.count('else "default"') == 1
    assert new_fixture_text == old_fixture_text.replace('else "default"', 'else "bridge"')
    new_method_name = "test_prepare_create_and_inspection_use_explicit_bridge"
    old_methods = {n.name for n in ast.walk(old_tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
    new_methods = {n.name for n in ast.walk(new_tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
    assert new_methods - old_methods == {new_method_name} and not old_methods - new_methods
    stripped = copy.deepcopy(new_tree)
    for node in ast.walk(stripped):
        if isinstance(node, ast.ClassDef):
            node.body = [child for child in node.body if not (isinstance(child, ast.FunctionDef) and child.name == new_method_name)]
        if isinstance(node, ast.FunctionDef) and node.name == "exact_container":
            for child in ast.walk(node):
                if isinstance(child, ast.Constant) and child.value == "bridge":
                    child.value = "default"
    assert ast.dump(stripped, include_attributes=False) == ast.dump(old_tree, include_attributes=False), "unexpected controls semantic delta"
    for path, body in candidate.items():
        target = HERE / "candidate" / Path(path).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    diff = "".join("".join(difflib.unified_diff(before[path].decode().splitlines(True), candidate[path].decode().splitlines(True), fromfile=SHA + ":" + path, tofile="candidate:" + path)) for path in PATHS)
    (HERE / "candidate.diff").write_text(diff)
    git_version = subprocess.check_output(["git", "--version"], cwd=REPO, text=True, timeout=5).strip()

    # From this point the interpreter may only execute pure Python validation.
    forbidden = []
    def no_external_work(event, args):
        if event.startswith("socket.") or event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.fork", "os.exec"}:
            forbidden.append(event)
            raise RuntimeError("external execution/socket forbidden in pure correction review: " + event)
    sys.addaudithook(no_external_work)
    scratch = HERE / ".scratch"
    scratch.mkdir(exist_ok=False)
    tempfile.tempdir = str(scratch)
    subject = load("independent_bridge_candidate", HERE / "candidate" / "test-identity-network.py")
    actual = json.loads((FAILED / "selected/artifact/logs/0012.stdout").read_bytes())[0]
    owned = subject.OwnedContainer(cid=actual["Id"], name=actual["Name"].removeprefix("/"), role="prepare",
        image_id=actual["Image"], label=actual["Config"]["Labels"]["mixer.identity.run"])
    actual_before = bind(json.dumps(actual, sort_keys=True).encode())
    assert subject.validate_container_inspect("prepare", actual, owned) is actual
    assert subject.validate_container_environment("prepare", actual) == subject.BASE_ENV
    assert actual_before == bind(json.dumps(actual, sort_keys=True).encode()), "actual runtime fields mutated"
    guarded = copy.deepcopy(actual)
    guarded["HostConfig"]["NetworkMode"] = "default"
    try:
        subject.validate_container_inspect("prepare", guarded, owned)
    except subject.CollectorError as error:
        assert str(error) == "container network mismatch"
    else:
        raise AssertionError("legacy inspector value was accepted")
    for disallowed in ("host", "none", "container:" + actual["Id"]):
        guarded = copy.deepcopy(actual)
        guarded["HostConfig"]["NetworkMode"] = disallowed
        try:
            subject.validate_container_inspect("prepare", guarded, owned)
        except subject.CollectorError:
            pass
        else:
            raise AssertionError("wrong prepare network accepted")

    output = io.StringIO()
    controls = load("independent_bridge_controls", REPO / PATHS[1])
    suite = unittest.defaultTestLoader.loadTestsFromModule(controls)
    assert suite.countTestCases() == 58
    started = time.monotonic()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    elapsed = time.monotonic() - started
    (HERE / "controls.log").write_text(output.getvalue())
    assert result.testsRun == 58 and not result.failures and not result.errors and not result.skipped
    assert not forbidden
    assert not list(scratch.iterdir())
    scratch.rmdir()
    assert {path: (REPO / path).read_bytes() for path in PATHS} == candidate
    assert verify_failed_packet() == packet_digest
    decision = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": "bridge-correction-independently-reviewed-suitable-for-root-delivery; remote-runtime-pending",
        "command": "python3 -B verification/github-delivery-identity-network/network-review/correction-review/review_correction.py",
        "python": platform.python_version(), "git": git_version, "source_revision_compared": SHA,
        "reviewer_script_sha256": bind(Path(__file__).read_bytes())["sha256"],
        "candidate": {path: bind(body) for path, body in candidate.items()},
        "collector_delta": "exactly two prepare network string replacements default -> bridge; no other bytes changed",
        "controls_delta": "prepare inspector fixture default -> bridge and one added explicit-create/inspection/legacy-refusal test; all existing AST unchanged",
        "actual_retained_inspection": {"source": "../selected/artifact/logs/0012.stdout", "sha256": bind((FAILED / "selected/artifact/logs/0012.stdout").read_bytes())["sha256"],
            "candidate_full_container_inspect_passed": True, "candidate_exact_environment_allowlist_passed": True,
            "runtime_inspect_fields_modified": 0, "only_dynamic_owned_identity_constructed_from_actual_runtime_fields": True,
            "legacy_default_host_none_and_container_networks_refused": True},
        "pure_controls": {"run": result.testsRun, "failures": 0, "errors": 0, "skipped": 0, "elapsed_seconds": elapsed,
            "external_process_or_socket_audit_events": forbidden},
        "failed_packet_unchanged_digest_sha256": packet_digest,
        "scratch_cleanup": "empty owned .scratch removed after controls",
        "activity": {"Docker_runtime_compiler_native_UI_capture_hosted_or_held_operations": 0, "CI_mutations": 0,
            "canonical_writes": 0, "commits_or_pushes": 0},
        "limitations": ["full runtime phase sequence remains unrun", "source-and-pure-control review does not qualify two product methods", "first failed attempt remains failed and immutable"]}
    (HERE / "decision.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n")
    print(json.dumps(decision, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
