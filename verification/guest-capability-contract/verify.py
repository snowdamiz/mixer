#!/usr/bin/env python3
"""Observe raw argument/outcome fixtures using the existing public strict codec.

This does not implement or validate the proposed transport wrapper. The existing
probe receives raw fixture bytes inside its existing envelope, never parser-repaired
bytes. Wrapper and new standalone-payload byte boundaries remain explicitly pending.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
RUN = BASE / "run"
CONTRACT = ROOT / "contracts/guest-capability-transport-v1.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def text_command(command: list[str]) -> dict:
    result = run(command)
    return {
        "command": command,
        "exit_code": result.returncode,
        "stdout": result.stdout.decode("utf-8", "replace").strip(),
        "stderr": result.stderr.decode("utf-8", "replace").strip(),
    }


def envelope(binding: dict, payload: bytes, member: str, kind: str) -> bytes:
    # Only trusted metadata is serialized. Raw fixture bytes are inserted verbatim,
    # preserving duplicates, escape spelling and numeric/base64/Unicode failures.
    metadata = {
        "schema": 1,
        "kind": kind,
        "identity": {"session": "00000000-0000-0000-0000-000000000001", "slot": 0, "generation": 1},
        "capability": binding["capability"],
        "schemaHash": binding["schemaHash"],
        "operation": binding["operation"],
    }
    return json.dumps(metadata, separators=(",", ":")).encode()[:-1] + b',"' + member.encode() + b'":' + payload + b"}"


def main() -> int:
    started = time.time()
    RUN.mkdir(exist_ok=True)
    contract = json.loads(CONTRACT.read_text())
    manifest = json.loads((BASE / "cases.json").read_text())
    assert contract["status"] == "development_contract_only"
    assert len(contract["imports"]["functions"]) == 6
    assert contract["operations"] == manifest["operations"]
    for relative, expected in contract["source"]["sha256_file_bytes"].items():
        actual = digest((ROOT / relative).read_bytes())
        if actual != expected:
            raise RuntimeError(f"Pinned source changed: {relative}; review/re-anchor the development contract before rerun")
    ids = set()
    for case in manifest["cases"]:
        assert case["id"] not in ids
        ids.add(case["id"])
        payload = (BASE / case["file"]).read_bytes()
        assert digest(payload) == case["sha256"], case["id"]
        assert len(payload) == case["bytes"], case["id"]
        assert case["expected"] in ("accept", "reject")

    versions = [text_command(command) for command in (
        ["swift", "--version"], ["python3", "--version"], ["git", "--version"], ["uname", "-sm"]
    )]
    if any(value["exit_code"] != 0 for value in versions):
        raise RuntimeError("Required tool version could not be observed")
    revision = text_command(["git", "rev-parse", "HEAD"])["stdout"]
    tree = text_command(["git", "rev-parse", "HEAD^{tree}"])["stdout"]
    paths = {CONTRACT, BASE / "cases.json", Path(__file__).resolve(), ROOT / "capabilities/Package.swift", ROOT / "sdk/Package.swift"}
    paths.update((ROOT / "sdk/Sources").rglob("*.swift"))
    paths.update((ROOT / "sdk/Sources").rglob("*.c"))
    paths.update((ROOT / "sdk/Sources").rglob("*.h"))
    paths.update((ROOT / "capabilities/Probe").rglob("*.swift"))
    paths.update(ROOT / relative for relative in contract["source"]["sha256_file_bytes"])
    paths.update(BASE / case["file"] for case in manifest["cases"])
    source_hashes = {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in sorted(paths)}
    (RUN / "source-sha256.json").write_text(json.dumps(source_hashes, indent=2) + "\n")

    scratch = BASE / ".build"
    build_command = ["swift", "build", "--package-path", "capabilities", "--scratch-path", str(scratch), "--product", "capability-probe"]
    build = run(build_command)
    (RUN / "build.stdout").write_bytes(build.stdout)
    (RUN / "build.stderr").write_bytes(build.stderr)
    if build.returncode != 0:
        raise RuntimeError("Existing public capability-probe build failed; inspect run/build.stderr")
    bin_command = ["swift", "build", "--package-path", "capabilities", "--scratch-path", str(scratch), "--show-bin-path"]
    binary_path = run(bin_command)
    if binary_path.returncode != 0:
        raise RuntimeError("Could not locate existing capability-probe")
    probe = Path(binary_path.stdout.decode().strip()) / "capability-probe"
    bindings = {op["swiftCase"]: op for op in contract["operations"]}
    expected_dir = RUN / "existing-envelope-expected-calls"
    expected_dir.mkdir(exist_ok=True)
    expected_calls = {}
    for operation, binding in bindings.items():
        positive = next(case for case in manifest["cases"] if case["id"] == operation + "-arguments")
        path = expected_dir / (operation + ".json")
        path.write_bytes(envelope(binding, (BASE / positive["file"]).read_bytes(), "arguments", "call"))
        expected_calls[operation] = path

    observations = []
    for case in manifest["cases"]:
        if case["oracle"] == "not_yet_implemented":
            observations.append({"id": case["id"], "status": "pending_not_executed", "expected": case["expected"], "reason": "New wrapper/API standalone byte boundary is not implemented by the existing codec"})
            continue
        payload = (BASE / case["file"]).read_bytes()
        binding = bindings[case["operation"]]
        if case["phase"] == "arguments":
            command = [str(probe), "roundtrip"]
            input_bytes = envelope(binding, payload, "arguments", "call")
        elif case["phase"] == "outcomes":
            command = [str(probe), "decode-completion", str(expected_calls[case["operation"]])]
            input_bytes = envelope(binding, payload, "outcome", "completion")
        else:
            raise RuntimeError(f"No existing oracle mapping for {case['id']}")
        observed = subprocess.run(command, input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=ROOT)
        expected_exit = 0 if case["expected"] == "accept" else 1
        matched = observed.returncode == expected_exit
        observations.append({
            "id": case["id"], "status": "existing_codec_projection_matched" if matched else "mismatch",
            "scope": "Existing full envelope argument/result semantics only; not the proposed standalone codec/import/wrapper",
            "command": command, "stdin_sha256": digest(input_bytes), "stdin_bytes": len(input_bytes),
            "fixture_sha256": case["sha256"], "expected": case["expected"], "exit_code": observed.returncode,
            "stdout_sha256": digest(observed.stdout), "stdout_bytes": len(observed.stdout),
            "stderr": observed.stderr.decode("utf-8", "replace"),
        })
    executed = [row for row in observations if row["status"] != "pending_not_executed"]
    mismatches = [row for row in executed if row["status"] == "mismatch"]
    pending = len(observations) - len(executed)
    receipt = {
        "schema": 1, "status": "existing_codec_projection_passed_with_pending_new_contract_cases" if not mismatches else "failed",
        "source_revision": revision, "source_tree": tree, "source_manifest": "source-sha256.json",
        "source_manifest_sha256": digest((RUN / "source-sha256.json").read_bytes()),
        "contract_sha256": digest(CONTRACT.read_bytes()), "tools": versions,
        "build": {"command": build_command, "exit_code": build.returncode, "stdout": "build.stdout", "stderr": "build.stderr", "binary_path_command": bin_command, "probe_sha256": digest(probe.read_bytes())},
        "summary": {"fixture_total": len(observations), "existing_codec_projections_executed": len(executed), "matched": len(executed) - len(mismatches), "mismatches": len(mismatches), "new_contract_cases_pending_not_executed": pending},
        "scope": "Offline macOS public strict capability codec only. The legacy host envelope adds bytes/depth/metadata; this does not execute the new standalone argument API or transport wrapper. No Wasm import, mailbox, native I/O, grant/activation, release, full Swift async, physical device or GA evidence.",
        "elapsed_seconds": round(time.time() - started, 3), "observations": observations,
    }
    (RUN / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt["summary"], sort_keys=True))
    print("Scope: existing public-codec projections only; new wrapper/standalone boundary fixtures remain pending.")
    return 1 if mismatches else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(f"Qualification stopped: {error}", file=sys.stderr)
        sys.exit(2)
