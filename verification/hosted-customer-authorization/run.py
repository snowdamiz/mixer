#!/usr/bin/env python3
"""Retain bounded ordinary-source host policy tests; no application/DB/provider start."""

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE_REVISION = "b375e55ded9e3e10c327891ab681beff2a471e26"
SOURCES = [
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/authorization/scope.ex",
    "hosted/lib/mixer_hosted/authorization/policy.ex",
    "hosted/lib/mixer_hosted/authorization/repository.ex",
]
TEST = "hosted/test/mixer_hosted/authorization/policy_test.exs"
CONTRACTS = [
    "AGENTS.md",
    "mixer-product-plan.md",
    "docs/hosted-identity-contract.md",
    "docs/hosted-customer-authorization.md",
    "hosted/.tool-versions",
]


def main():
    number = 1
    while (HERE / f"run-{number}").exists():
        number += 1
    output = HERE / f"run-{number}"
    output.mkdir()
    inputs = output / "inputs"
    inputs.mkdir()
    driver = output / "driver.py"
    shutil.copyfile(__file__, driver)
    manifest = []
    digest = hashlib.sha256()
    for relative in SOURCES + [TEST] + CONTRACTS:
        source = ROOT / relative
        data = source.read_bytes()
        target = inputs / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()
        manifest.append({"path": relative, "bytes": len(data), "sha256": sha})
        digest.update(relative.encode() + b"\0" + data + b"\0")

    record = {
        "source_revision": SOURCE_REVISION,
        "source_revision_provenance": "supplied by root coordination; no git command executed",
        "input_tree_sha256": digest.hexdigest(),
        "host": {"system": platform.system(), "machine": platform.machine(), "release": platform.release()},
        "python": sys.version,
        "environment_overrides": {"ERL_FLAGS": "+S 2:2"},
        "scope": "standalone pure policy tests; synthetic repository only",
        "not_executed": ["Mix startup", "database", "network", "provider", "server", "UI", "native", "device", "frozen lanes"],
        "commands": [],
        "inputs": manifest,
        "driver_sha256": hashlib.sha256(driver.read_bytes()).hexdigest(),
    }
    environment = os.environ.copy()
    environment["ERL_FLAGS"] = "+S 2:2"
    scratch = Path(tempfile.mkdtemp(prefix="mixer-customer-auth-"))
    record["scratch"] = str(scratch)
    result = False

    def run(label, command):
        start = time.monotonic()
        entry = {"label": label, "argv": command, "cwd": str(scratch), "timeout_seconds": 120}
        try:
            completed = subprocess.run(command, cwd=scratch, env=environment, capture_output=True, timeout=120)
            stdout, stderr, status = completed.stdout, completed.stderr, completed.returncode
        except subprocess.TimeoutExpired as exc:
            stdout, stderr, status = exc.stdout or b"", exc.stderr or b"", "timeout"
        entry.update({"exit_code": status, "elapsed_seconds": round(time.monotonic() - start, 6)})
        (output / f"{label}.stdout").write_bytes(stdout)
        (output / f"{label}.stderr").write_bytes(stderr)
        record["commands"].append(entry)
        print(f"{label}: {status}")
        if stdout:
            print(stdout.decode(errors="replace"))
        if stderr:
            print(stderr.decode(errors="replace"), file=sys.stderr)
        return status == 0, stdout

    try:
        elixir = shutil.which("elixir")
        elixirc = shutil.which("elixirc")
        if not elixir or not elixirc:
            raise RuntimeError("selected Elixir toolchain unavailable")
        record["tools"] = {"elixir": elixir, "elixirc": elixirc}
        for relative in SOURCES + [TEST]:
            destination = scratch / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(inputs / relative, destination)
        (scratch / "ebin").mkdir()
        version_ok, _ = run("tool-version", [elixir, "--version"])
        otp_ok, _ = run("otp-version", [elixir, "-e", 'IO.puts(File.read!(Path.join([:code.root_dir(), "releases", :erlang.system_info(:otp_release), "OTP_VERSION"])))'])
        compile_ok, _ = run("compile", [elixirc, "--warnings-as-errors", "-o", str(scratch / "ebin")] + [str(scratch / path) for path in SOURCES])
        if compile_ok:
            test_ok, test_stdout = run("tests", [elixir, "-pa", str(scratch / "ebin"), "-e", 'ExUnit.start(seed: 0); Code.require_file(hd(System.argv()))', "--", str(scratch / TEST)])
            record["test_summary"] = test_stdout.decode(errors="replace").splitlines()[-3:]
            result = version_ok and otp_ok and test_ok
    except Exception as exc:
        record["harness_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        shutil.rmtree(scratch)
        record["cleanup"] = {"owned_scratch_removed": not scratch.exists(), "native_instances_created": 0, "other_projects_touched": False}
        record["passed"] = result
        (output / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
        print(f"receipt: {output.relative_to(ROOT) / 'receipt.json'}")
    return 0 if result else 1


if __name__ == "__main__":
    raise SystemExit(main())
