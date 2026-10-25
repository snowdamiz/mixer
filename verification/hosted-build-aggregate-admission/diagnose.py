#!/usr/bin/env python3
"""Bounded local producer diagnostics; root owns the complete release collector."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tarfile
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
hosted = root / "hosted"
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=False)
pg_bin = Path("/opt/homebrew/opt/postgresql@17/bin")
scratch = Path(tempfile.mkdtemp(prefix="mixer-aggregate-admission-diagnostic-"))
commands = []
started = False
status = "failed"
cleanup = {}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    return {
        str(path.relative_to(root)): digest(path)
        for path in sorted(hosted.rglob("*"))
        if path.is_file() and path.name != "erl_crash.dump"
        and not {"_build", "deps", "__pycache__", "cover"}.intersection(path.relative_to(hosted).parts)
    }


def run(label, argv, env=None, check=True):
    log = output / f"{label}.log"
    with log.open("wb") as stream:
        try:
            code = subprocess.run(argv, cwd=hosted, env=env, stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=120).returncode
        except subprocess.TimeoutExpired:
            stream.write(b"\nDIAGNOSTIC: 120 second timeout\n")
            code = 124
    commands.append({"label": label, "argv": list(map(str, argv)), "cwd": str(hosted),
                     "exit_code": code, "log": log.name, "sha256": digest(log)})
    if check and code:
        raise RuntimeError(f"{label} failed ({code}); see {log}")
    return code


before = inputs()
with tarfile.open(output / "source.tar.gz", "w:gz") as archive:
    for name in before:
        archive.add(root / name, arcname=name, recursive=False)

try:
    run("revision", ["git", "rev-parse", "HEAD"])
    run("elixir-version", ["elixir", "--version"])
    run("postgres-version", [str(pg_bin / "postgres"), "--version"])
    selected = ["lib/mixer_hosted/builds/admission.ex",
                "priv/repo/migrations/20261025000002_add_build_aggregate_limits.exs",
                "test/mixer_hosted/builds/admission_test.exs",
                "test/mixer_hosted/builds/aggregate_admission_test.exs",
                "test/mixer_hosted/builds/coordinator_test.exs",
                "test/mixer_hosted/builds/storage_test.exs"]
    run("format", ["mix", "format", "--check-formatted", *selected])
    env = dict(os.environ, MIX_ENV="test")
    run("compile", ["mix", "compile", "--warnings-as-errors"], env)
    run("initdb", [str(pg_bin / "initdb"), "-D", str(scratch / "data"), "-U", "mixer_fixture",
                   "--auth-local=trust", "--auth-host=trust", "--no-locale", "-E", "UTF8"])
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
    run("postgres-start", [str(pg_bin / "pg_ctl"), "-D", str(scratch / "data"), "-l",
                           str(output / "postgres.log"), "-o",
                           f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC", "-w", "start"])
    started = True
    env["MIXER_TEST_DATABASE_PORT"] = str(port)
    for db in ["mixer_aggregate_admission_test", "mixer_admission_test", "mixer_coordinator_test",
               "mixer_builds_test"]:
        run("createdb-" + db, [str(pg_bin / "createdb"), "-h", "127.0.0.1", "-p", str(port),
                                 "-U", "mixer_fixture", db])
    run("tests", ["mix", "test", "--warnings-as-errors", "--seed", "0", "--trace", *selected[2:]], env)
    if before != inputs():
        raise RuntimeError("Hosted sources changed during diagnostics")
    status = "passed"
finally:
    if started or (scratch / "data/postmaster.pid").exists():
        cleanup["postgres_stopped"] = run(
            "postgres-stop", [str(pg_bin / "pg_ctl"), "-D", str(scratch / "data"),
                              "-m", "fast", "-w", "stop"], check=False) == 0
    else:
        cleanup["postgres_stopped"] = True
    if cleanup["postgres_stopped"]:
        shutil.rmtree(scratch)
        cleanup["scratch_removed"] = not scratch.exists()
    else:
        status = "failed"
    receipt = {
        "status": status, "source_tree_sha256": hashlib.sha256(
            json.dumps(before, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "inputs": before, "source_archive_sha256": digest(output / "source.tar.gz"),
        "commands": commands, "cleanup": cleanup,
        "scope": "Four current producer build test modules on loopback PostgreSQL 17; synthetic workers only. Root's full collector and independent review remain separate requirements.",
        "limitations": ["No production database migration, cloud, provider execution, signing, public authorization, native device or GA qualification."]
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": status, "receipt": str(output / "receipt.json"), "cleanup": cleanup}))
