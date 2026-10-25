#!/usr/bin/env python3
"""Collect bounded pure host evidence; never starts the hosted application."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCES = [
    "AGENTS.md",
    "hosted/lib/mixer_hosted/builds/lifecycle.ex",
    "hosted/lib/mixer_hosted/builds/journal.ex",
    "hosted/test/mixer_hosted/builds/lifecycle_test.exs",
    "hosted/test/mixer_hosted/builds/journal_test.exs",
    "docs/hosted-build-journal.md",
    "hosted/mix.exs",
    "hosted/mix.lock",
    "verification/hosted-build-journal/collect.py",
]
ELIXIR = "/opt/homebrew/bin/elixir"
JASON_BEAM = "hosted/_build/test/lib/jason/ebin/Elixir.Jason.beam"
ENV = dict(os.environ, ERL_FLAGS="+S 2:2")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sources():
    return {path: digest((ROOT / path).read_bytes()) for path in SOURCES}


def run(label, argv):
    start = time.monotonic()
    result = subprocess.run(argv, cwd=ROOT, env=ENV, capture_output=True, timeout=120)
    stdout = f"{label}.stdout"
    stderr = f"{label}.stderr"
    (OUT / stdout).write_bytes(result.stdout)
    (OUT / stderr).write_bytes(result.stderr)
    return {
        "label": label,
        "argv": argv,
        "cwd": str(ROOT),
        "environmentOverride": {"ERL_FLAGS": "+S 2:2"},
        "timeoutSeconds": 120,
        "exitCode": result.returncode,
        "elapsedSeconds": round(time.monotonic() - start, 6),
        "stdout": stdout,
        "stdoutSHA256": digest(result.stdout),
        "stderr": stderr,
        "stderrSHA256": digest(result.stderr),
    }


before = sources()
revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
commands = [
    run("versions", [ELIXIR, "-e", 'IO.puts("elixir=" <> System.version()); IO.puts("otp=" <> String.trim(File.read!(Path.join([:code.root_dir(), "releases", :erlang.system_info(:otp_release), "OTP_VERSION"]))))']),
    run("format", [ELIXIR, "-e", 'Enum.each(["hosted/lib/mixer_hosted/builds/journal.ex", "hosted/test/mixer_hosted/builds/journal_test.exs"], fn path -> source = File.read!(path); formatted = IO.iodata_to_binary([Code.format_string!(source), "\\n"]); if source != formatted, do: raise("not formatted: " <> path) end); IO.puts("2 files formatted")'.replace('"\\n"', '"\n"')]),
    run("pure-tests", [ELIXIR, "-pa", "hosted/_build/test/lib/jason/ebin", "-r", "hosted/lib/mixer_hosted/builds/lifecycle.ex", "-r", "hosted/lib/mixer_hosted/builds/journal.ex", "-e", 'ExUnit.start(seed: 0); Code.require_file("hosted/test/mixer_hosted/builds/lifecycle_test.exs"); Code.require_file("hosted/test/mixer_hosted/builds/journal_test.exs")']),
]
after = sources()
receipt = {
    "schema": 1,
    "observedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "producer": "/root/hosted_build_journal",
    "baseSourceRevision": revision,
    "sourceSHA256": before,
    "sourceTreeSHA256": digest(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()),
    "sourcesUnchanged": before == after,
    "toolLauncherSHA256": digest(Path(ELIXIR).read_bytes()),
    "jasonBeamSHA256": digest((ROOT / JASON_BEAM).read_bytes()),
    "pythonVersion": sys.version,
    "commands": commands,
    "scope": "Pure deterministic Elixir lifecycle+journal tests with existing Jason JSON round trips. No Mix application, database, network, worker, signing or native processes started.",
    "pending": ["Root durable-store integration verification", "Independent codec acceptance review", "All operational/customer/signing/store/physical-device/GA gates"],
    "cleanup": "Only short-lived Elixir test/format/version processes; all terminated on command completion. No disposable simulator/emulator/database created.",
    "passed": all(item["exitCode"] == 0 for item in commands) and before == after,
}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
for item in commands:
    print(f'{item["label"]}: exit {item["exitCode"]}')
    print((OUT / item["stdout"]).read_text(), end="")
    print((OUT / item["stderr"]).read_text(), end="", file=sys.stderr)
if not receipt["passed"]:
    raise SystemExit(1)
