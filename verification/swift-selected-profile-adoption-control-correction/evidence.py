#!/usr/bin/env python3
"""Bounded, lane-owned I1 correction and host control-suite evidence.

Never imports or executes either frozen input packet's orchestration.
"""
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

OWN = Path(__file__).resolve().parent
REPO = OWN.parents[1]
ORIGINAL = REPO / "verification/swift-selected-profile-adoption"
INDEPENDENT = REPO / "verification/swift-selected-profile-adoption-independent"
SOURCE = OWN / "source/vm"
WORK = OWN / "owned-work"
RUSTC = Path("/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc")
TARGET = "src/experimental_swift_reactor/control_tests.rs"
PREFIX = "experimental_swift_reactor::control::tests::"
OLD_TREE = "22b6e945a062b3465156bb9995bce610bd712fa9d3e283e176316d75104bb442"
SELECTION = REPO / "verification/swift-semantic-adapter-root-review/selected-adoption-control-correction-selection.json"
SELECTION_HASH = "ddd67f46d96c49a300bc46aabc73568cd73ab8e8d06c68a4a5dd0164ae452e9b"
SEALS = [(ORIGINAL, "83a7c57bc5f208b06a42384f14b4056040604ef01685a9dfbe8bbe32b832a7ad"),
         (INDEPENDENT, "c270107bb0b73309403eb12fe768f609d31d2973a0ea13627fd4f41ed032974f")]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def identity(path, name=None):
    assert path.is_file() and not path.is_symlink(), path
    data = path.read_bytes()
    return {"path": name or str(path), "bytes": len(data), "sha256": digest(data)}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def read(path):
    return json.loads(path.read_text())


def inventory(root):
    paths = sorted(p for p in root.rglob("*") if p.is_file())
    assert not any(p.is_symlink() for p in root.rglob("*"))
    return [identity(p, p.relative_to(root).as_posix()) for p in paths]


def manifest(root):
    members = inventory(root)
    return {"schema": 1, "member_count": len(members), "members": members,
            "tree_sha256": digest(json.dumps(members, sort_keys=True, separators=(",", ":")).encode())}


def verify_frozen():
    verified = []
    for root, expected in SEALS:
        seal = identity(root / "seal.json")
        assert seal["sha256"] == expected
        declared = read(root / "seal.json")
        actual = inventory(root)
        actual = [m for m in actual if m["path"] != "seal.json"]
        assert actual == declared["members"], root
        assert len(actual) == declared["member_count"]
        assert sum(m["bytes"] for m in actual) == declared["member_bytes"]
        verified.append({"seal": seal, "members": len(actual),
                         "member_bytes": declared["member_bytes"], "closed_file_set_verified": True})
    return verified


def prepare():
    assert not SOURCE.exists() and not WORK.exists()
    assert identity(SELECTION)["sha256"] == SELECTION_HASH
    write(OWN / "inputs/frozen-custody-before.json", verify_frozen())
    for root, _ in SEALS:
        shutil.copyfile(root / "seal.json", OWN / "inputs" / (root.name + "-seal.json"))
    shutil.copyfile(SELECTION, OWN / "inputs/selection.json")
    original = read(ORIGINAL / "source-manifest.json")
    assert original["tree_sha256"] == OLD_TREE and original["member_count"] == 144
    assert manifest(ORIGINAL / "source/vm") == original
    shutil.copytree(ORIGINAL / "source/vm", SOURCE)
    shutil.copytree(ORIGINAL / "host", OWN / "host")
    assert len(inventory(OWN / "host")) == 11
    assert manifest(SOURCE) == original
    write(OWN / "source-manifest-before.json", original)
    before = (SOURCE / TARGET).read_text()
    assert digest(before.encode()) == "f7758c9ee9b4bdc3a26ea35cabd8c2c934f9469a37f701f6866b547f26c00fcb"
    (OWN / "inputs/control_tests.before.rs").write_text(before)
    old = "        + super::super::execution::CONSTRUCTION_BOOTSTRAP_BYTES;"
    new = """        + super::super::execution::CONSTRUCTION_BOOTSTRAP_BYTES
        // Keep selected-owner ingress, moves, cleanup and wrapper places in
        // both floors while isolating the optional-observation increment.
        + super::super::retained_profile_loader_v1::ADOPTION_ENTRY_BYTES_V1
        + super::super::retained_profile_loader_v1::ADOPTION_MOVE_BYTES_V1
        + ADOPTION_CLEANUP_BYTES_V1
        + super::super::cache::INITIAL_PROFILE_WRAPPER_SOURCE_PLACES_V1;"""
    assert before.count(old) == 1
    after = before.replace(old, new)
    (SOURCE / TARGET).write_text(after)
    (OWN / "source-change.diff").write_text("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), fromfile="original/" + TARGET,
        tofile="corrected/" + TARGET)))
    corrected = manifest(SOURCE)
    write(OWN / "source-manifest.json", corrected)
    changed = [m["path"] for m, n in zip(corrected["members"], original["members"]) if m != n]
    assert changed == [TARGET]
    unchanged = [m for m in corrected["members"] if m["path"] != TARGET]
    assert unchanged == [m for m in original["members"] if m["path"] != TARGET]
    write(OWN / "unchanged-source-paths.json", {"schema": 1, "members": unchanged,
          "member_count": 143, "projection_sha256": digest(json.dumps(unchanged, sort_keys=True, separators=(",", ":")).encode()),
          "meaning": "Exact unchanged paths, not new executions under the corrected full-tree digest"})
    write(OWN / "host-support-manifest.json", manifest(OWN / "host"))
    names = [PREFIX + n for n in re.findall(r"#\[test\]\s*fn (\w+)\(", before)]
    assert len(names) == 37
    assert names == [PREFIX + n for n in re.findall(r"#\[test\]\s*fn (\w+)\(", after)]
    write(OWN / "control-methods.json", {"schema": 1, "count": 37, "original_names": sorted(names)})
    # Preserve old failure and summaries byte-for-byte; they retain old attribution.
    historical = ["receipt.json", "final-required-command-matrix.json", "accounting.json"]
    for name in historical:
        dest = OWN / "historical/candidate" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ORIGINAL / name, dest)
    for name in ["review-result.json", "replay/commands/0003-debug-suite-experimental_swift_reactor::control::tests::/receipt.json",
                 "replay/commands/0003-debug-suite-experimental_swift_reactor::control::tests::/stdout",
                 "replay/commands/0003-debug-suite-experimental_swift_reactor::control::tests::/stderr"]:
        dest = OWN / "historical/independent" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(INDEPENDENT / name, dest)
    layouts = []
    for mode in ["debug", "optimized"]:
        for configuration in ["unit", "production"]:
            name = f"layouts/{configuration}-{mode}.json"
            dest = OWN / "historical/candidate" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ORIGINAL / name, dest)
            data = read(dest)
            assert len(data["rows"]) == 201
            assert [r["id"] for r in data["rows"]] == list(range(1, 202))
            layouts.append({"original": identity(ORIGINAL / name), "retained": identity(dest),
                            "rows": 201, "source_tree_sha256": OLD_TREE,
                            "new_measurement": False})
    write(OWN / "layout-custody.json", {"schema": 1, "unchanged_layout_source_paths": True,
          "reason": "Only existing cfg(test) test-body expected-sum arithmetic/comment changed; no types, layout literals, owners, fields or envelopes changed.",
          "measurements": layouts, "all_original165_plus_loader23_plus_adoption13_preserved": True})
    write(OWN / "preparation/inspection-failure.json", {"schema": 1, "exit_code": 2,
          "command": "rg -n 'source_tree|266|commands' verification/swift-selected-profile-adoption/final-byte-validation.json verification/swift-selected-profile-adoption/validation-matrix.json",
          "stderr": "rg: verification/swift-selected-profile-adoption/final-byte-validation.json: No such file or directory (os error 2)\nrg: verification/swift-selected-profile-adoption/validation-matrix.json: No such file or directory (os error 2)\n",
          "classification": "Read-only discovery used nonexistent filenames; subsequently located exact final-required-command-matrix.json. No product or test execution failure."})
    WORK.mkdir()
    write(OWN / "entry-context.json", {"schema": 1, "at": datetime.now(timezone.utc).isoformat(),
          "source_tree_sha256": corrected["tree_sha256"], "python": identity(Path(sys.executable).resolve()),
          "python_version": sys.version, "uname": list(os.uname()), "rustc": identity(RUSTC),
          "AGENTS": identity(REPO / "AGENTS.md"), "scope": "I1 test expectation only; no original packet orchestration imported or run"})
    print(json.dumps({"prepared": True, "source_tree_sha256": corrected["tree_sha256"], "unchanged_sources": 143, "unchanged_host_support": 11}))


def run(label, argv, context=None):
    assert manifest(SOURCE) == read(OWN / "source-manifest.json")
    records = sorted((OWN / "commands").glob("*/receipt.json")) if (OWN / "commands").exists() else []
    dest = OWN / "commands" / f"{len(records)+1:04d}-{label}"
    dest.mkdir(parents=True)
    env = {"PATH": "/usr/bin:/bin", "TMPDIR": str(WORK), "CARGO_MANIFEST_DIR": str(SOURCE)}
    started = time.monotonic()
    killed = None
    with (dest / "stdout").open("wb") as out, (dest / "stderr").open("wb") as err:
        child = subprocess.Popen([str(x) for x in argv], cwd=REPO, env=env, stdout=out, stderr=err)
        deadline = started + 55
        while child.poll() is None:
            if time.monotonic() >= deadline:
                killed = "timeout"
                child.kill()
                break
            if sum((dest / f).stat().st_size for f in ["stdout", "stderr"]) > 1048576:
                killed = "output limit"
                child.kill()
                break
            time.sleep(0.02)
        code = child.wait()
    receipt = {"schema": 1, "label": label, "argv": [str(x) for x in argv], "cwd": str(REPO),
               "environment": env, "source_tree_sha256": read(OWN / "source-manifest.json")["tree_sha256"],
               "runner": identity(Path(__file__)), "elapsed_seconds": time.monotonic()-started,
               "exit_code": code, "terminally_waited": True, "timeout_seconds": 55,
               "output_byte_limit": 1048576, "supervisor_killed_for": killed,
               "stdout": identity(dest / "stdout"), "stderr": identity(dest / "stderr"),
               "executed_artifact": identity(Path(argv[0])), "compiled_context": context}
    write(dest / "receipt.json", receipt)
    print(json.dumps({"command": str(dest.relative_to(OWN)), "exit_code": code,
                      "elapsed_seconds": receipt["elapsed_seconds"], "stdout_bytes": receipt["stdout"]["bytes"],
                      "stderr_bytes": receipt["stderr"]["bytes"]}), flush=True)
    assert code == 0 and killed is None, dest
    return dest, receipt


def tools():
    for label, argv in [("rustc-version", [RUSTC, "-vV"]),
                        ("git-revision-context", [Path("/usr/bin/git"), "rev-parse", "HEAD"]),
                        ("macos-version", [Path("/usr/bin/sw_vers")])]:
        run(label, argv)


def compile_mode(mode):
    assert mode in ["debug", "optimized"]
    argv = [RUSTC, "--crate-name", "mixer_vm", "--edition=2021", "--target", "aarch64-apple-darwin",
            "-C", "opt-level=" + ("0" if mode == "debug" else "3"), "-C", "overflow-checks=yes", "-C", "panic=unwind"]
    for feature in ["experimental-swift-reactor", "experimental-swift-wasi", "experimental-stream-validation", "experimental-function-cache"]:
        argv += ["--cfg", f'feature="{feature}"']
    argv += ["--test", SOURCE / "src/lib.rs", "-o", WORK / f"unit-{mode}"]
    dest, receipt = run(f"compile-unit-{mode}", argv)
    write(OWN / f"compiled-{mode}.json", {"schema": 1, "compile_receipt": identity(dest / "receipt.json"),
          "compile_argv": receipt["argv"], "compile_environment": receipt["environment"],
          "source_tree_sha256": receipt["source_tree_sha256"], "binary": identity(WORK / f"unit-{mode}"),
          "tool_context": identity(OWN / "entry-context.json")})


def suite(mode):
    compiled = read(OWN / f"compiled-{mode}.json")
    binary = WORK / f"unit-{mode}"
    assert identity(binary) == compiled["binary"]
    dest, listing = run(f"list-full-control-{mode}", [binary, PREFIX, "--list"], compiled)
    names = sorted(line.removesuffix(": test") for line in (dest / "stdout").read_text().splitlines() if line.endswith(": test"))
    assert names == read(OWN / "control-methods.json")["original_names"] and len(names) == 37
    dest, receipt = run(f"full-control-{mode}", [binary, PREFIX, "--nocapture", "--test-threads=1"], compiled)
    summarize(mode, dest, compiled, names)


def summarize(mode, dest=None, compiled=None, names=None):
    compiled = compiled or read(OWN / f"compiled-{mode}.json")
    names = names or read(OWN / "control-methods.json")["original_names"]
    dest = dest or sorted((OWN / "commands").glob(f"*-full-control-{mode}"))[-1]
    receipt = read(dest / "receipt.json")
    assert receipt["exit_code"] == 0 and receipt["compiled_context"] == compiled
    assert receipt["source_tree_sha256"] == read(OWN / "source-manifest.json")["tree_sha256"]
    assert identity(dest / "stdout") == receipt["stdout"]
    output = (dest / "stdout").read_text()
    assert "test result: ok. 37 passed; 0 failed; 0 ignored; 0 measured;" in output
    body = output.split("\ntest result:", 1)[0]
    blocks = re.findall(r"^test (\S+) \.\.\. (.*?)(?=^test |\Z)", body, re.M | re.S)
    assert len(blocks) == 37 and all(status.strip().endswith("ok") for _, status in blocks)
    actual = sorted(name for name, _ in blocks)
    assert actual == names
    write(OWN / f"control-result-{mode}.json", {"schema": 1, "methods": names, "passed": 37,
          "failed": 0, "ignored": 0, "skip_arguments": [], "full_original_control_module": True,
          "source_tree_sha256": compiled["source_tree_sha256"], "compiled_context": identity(OWN / f"compiled-{mode}.json"),
          "suite_receipt": identity(dest / "receipt.json"), "complete_name_list_matched_before_and_after": True})


if __name__ == "__main__":
    action = sys.argv[1]
    if action == "prepare": prepare()
    elif action == "tools": tools()
    elif action == "compile": compile_mode(sys.argv[2])
    elif action == "suite": suite(sys.argv[2])
    elif action == "summarize": summarize(sys.argv[2])
    else: raise ValueError(action)
