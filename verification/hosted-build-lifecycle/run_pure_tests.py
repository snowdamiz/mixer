#!/usr/bin/env python3
"""Record one bounded standalone ExUnit run; never invoke Mix or an application harness."""

import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = "hosted/lib/mixer_hosted/builds/lifecycle.ex"
TEST = "hosted/test/mixer_hosted/builds/lifecycle_test.exs"
COMMAND = [
    "elixir",
    "-r",
    SOURCE,
    "-e",
    f'ExUnit.start(); Code.require_file("{TEST}")',
]
ENVIRONMENT = dict(os.environ, ERL_FLAGS="+S 2:2")


def run(command, timeout):
    started = time.monotonic()
    try:
        result = subprocess.run(
            command, cwd=ROOT, env=ENVIRONMENT, capture_output=True, text=True, timeout=timeout
        )
        return {
            "command": command,
            "timeout_seconds": timeout,
            "exit_code": result.returncode,
            "elapsed_seconds": time.monotonic() - started,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "command": command,
            "timeout_seconds": timeout,
            "exit_code": None,
            "timed_out": True,
            "elapsed_seconds": time.monotonic() - started,
            "stdout": (error.stdout or b"").decode(errors="replace") if isinstance(error.stdout, bytes) else (error.stdout or ""),
            "stderr": (error.stderr or b"").decode(errors="replace") if isinstance(error.stderr, bytes) else (error.stderr or ""),
        }


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


attempts = HERE / "attempts"
attempts.mkdir(exist_ok=True)
name = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
destination = attempts / name
destination.mkdir()
hashes = {path: digest(path) for path in (SOURCE, TEST)}
tree_bytes = b"".join(path.encode() + b"\0" + value.encode() + b"\n" for path, value in sorted(hashes.items()))
metadata = {
    "scope": "Host-only pure deterministic ExUnit; no Mix/test_helper/application/DB/provider/native harness",
    "source_revision": run(["git", "rev-parse", "HEAD"], 10),
    "source_sha256": hashes,
    "source_tree_sha256": hashlib.sha256(tree_bytes).hexdigest(),
    "environment_override": {"ERL_FLAGS": "+S 2:2"},
    "toolchain": run(["elixir", "--version"], 10),
    "otp_exact": run(
        [
            "elixir",
            "-e",
            'otp = List.to_string(:erlang.system_info(:otp_release)); IO.write(File.read!(Path.join([List.to_string(:code.root_dir()), "releases", otp, "OTP_VERSION"])))',
        ],
        10,
    ),
    "host": platform.uname()._asdict(),
    "elixir_path": shutil.which("elixir"),
    "python": sys.version,
}
result = run(COMMAND, 120)
metadata["test"] = result
metadata["source_unchanged_during_run"] = hashes == {path: digest(path) for path in (SOURCE, TEST)}
metadata["accepted_scope_result"] = result["exit_code"] == 0 and metadata["source_unchanged_during_run"]
(destination / "command.json").write_text(json.dumps(metadata, indent=2) + "\n")
(destination / "stdout.txt").write_text(result["stdout"])
(destination / "stderr.txt").write_text(result["stderr"])
print(json.dumps({"attempt": str(destination.relative_to(ROOT)), **metadata}, indent=2))
sys.exit(0 if metadata["accepted_scope_result"] else 1)
