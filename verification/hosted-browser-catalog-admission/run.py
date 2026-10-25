#!/usr/bin/env python3
"""Selected ordinary sources and dependency beams; one owned disposable PG."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import shutil
import signal
import socket
import subprocess
import tempfile
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--pg-bin", type=pathlib.Path, default=pathlib.Path("/opt/homebrew/opt/postgresql@17/bin"))
args = parser.parse_args()
PG = args.pg_bin.resolve()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
OUT = BASE / "attempts" / stamp
OUT.mkdir(parents=True)
sources = [BASE / "run.py", BASE / "function_surface_spec.exs",
    ROOT / "docs/hosted-browser-catalog-admission.md",
    ROOT / "hosted/mix.lock"] + [ROOT / "hosted/lib/mixer_hosted/browser_auth" / name for name in
    ["storage_schema.ex", "activation_preparation_schema.ex", "activation_preparation.ex", "catalog_manifest.ex", "catalog_manifest_v2.ex", "catalog.ex"]] + [
    ROOT / "hosted/test/mixer_hosted/browser_auth/storage_fixture.exs"] + [
    ROOT / "hosted/priv/repo/migrations" / name for name in [
    "20261025000003_add_customer_authorization.exs",
    "20261025000004_add_authorization_state_revisions.exs",
    "20261025000006_add_customer_workspace_discovery.exs",
    "20261025000007_add_browser_sessions.exs"]]
dependency_dirs = sorted(p / "ebin" for p in (ROOT / "hosted/_build/test/lib").iterdir()
    if p.name != "mixer_hosted" and (p / "ebin").is_dir())
beams = sorted(p for directory in dependency_dirs for p in directory.glob("*.beam"))
if not beams:
    raise RuntimeError("Existing locked dependency beams required; no whole-app build is permitted")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def manifest():
    return {"sources": {str(p.relative_to(ROOT)): digest(p) for p in sources},
        "dependency_beams": {str(p.relative_to(ROOT)): digest(p) for p in beams}}

before = manifest()
(OUT / "source-manifest.json").write_text(json.dumps(before, indent=2) + "\n")
commands = []
scratch = None
passed = False
stopped = True
revision = None

def run(name, command, env=None, check=True, timeout=30):
    command = [str(v) for v in command]
    try:
        proc = subprocess.Popen(command, cwd=ROOT, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    except OSError as error:
        (OUT / (name + ".log")).write_text(str(error) + "\n")
        commands.append({"name": name, "command": command, "timeout_seconds": timeout,
            "timed_out": False, "exit_code": None, "spawn_error": str(error), "output": name + ".log"})
        if check:
            raise
        return None, str(error)
    timed_out = False
    try:
        output, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGKILL)
        output, _ = proc.communicate(timeout=5)
    (OUT / (name + ".log")).write_text(output)
    commands.append({"name": name, "command": command, "timeout_seconds": timeout,
        "timed_out": timed_out, "exit_code": proc.returncode, "output": name + ".log"})
    if (proc.returncode or timed_out) and check:
        print(output[-16000:])
        raise RuntimeError(name + " failed")
    return proc.returncode, output

try:
    _, revision_output = run("git-head", ["git", "rev-parse", "HEAD"])
    revision = revision_output.strip()
    run("postgres-version", [PG / "postgres", "--version"])
    run("elixir-version", ["elixir", "--version"])
    run("python-version", ["python3", "--version"])
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="mixer-browser-function-surface-"))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    run("initdb", [PG / "initdb", "-D", scratch / "data", "-U", "browser_admin", "-A", "trust", "--no-locale", "-E", "UTF8"])
    run("postgres-start", [PG / "pg_ctl", "-D", scratch / "data", "-l", OUT / "postgres.log",
        "-o", f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC", "-w", "start"], timeout=15)
    psql = [PG / "psql", "-X", "-h", "127.0.0.1", "-p", str(port), "-U", "browser_admin", "-d", "postgres", "-v", "ON_ERROR_STOP=1"]
    run("roles", psql + ["-c", "CREATE ROLE browser_schema_owner NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_writer NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_lifecycle LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_ordinary LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE surface_neighbor NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;"])
    run("database", [PG / "createdb", "-h", "127.0.0.1", "-p", str(port), "-U", "browser_admin", "-O", "browser_schema_owner", "browser_storage"])
    environment = os.environ.copy()
    environment["MIXER_BROWSER_STORAGE_PORT"] = str(port)
    command = ["elixir"]
    for directory in dependency_dirs:
        command += ["-pa", directory]
    for name in ["storage_schema.ex", "activation_preparation_schema.ex", "catalog_manifest.ex", "catalog_manifest_v2.ex", "catalog.ex"]:
        command += ["-r", ROOT / "hosted/lib/mixer_hosted/browser_auth" / name]
    command += ["-e", 'ExUnit.start(seed: 0); Code.require_file("verification/hosted-browser-catalog-admission/function_surface_spec.exs")']
    run("selected-exunit", command, env=environment, timeout=60)
    passed = True
finally:
    if scratch is not None and (scratch / "data/postmaster.pid").exists():
        code, _ = run("postgres-stop", [PG / "pg_ctl", "-D", scratch / "data", "-m", "immediate", "-w", "stop"], check=False, timeout=15)
        stopped = code == 0 and not (scratch / "data/postmaster.pid").exists()
    if scratch is not None and stopped:
        shutil.rmtree(scratch)
    after = manifest()
    unchanged = before == after
    (OUT / "source-manifest-after.json").write_text(json.dumps(after, indent=2) + "\n")
    receipt = {"schema": 1, "time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "head": revision, "source_manifest": "source-manifest.json",
        "source_manifest_sha256": digest(OUT / "source-manifest.json"),
        "source_unchanged": unchanged, "commands": commands,
        "function_surface_tests_passed": passed and unchanged,
        "cleanup": {"owned_postgres_stopped": stopped, "owned_scratch_removed": scratch is None or not scratch.exists()},
        "scope": "Named function/type capability prerequisite only. One synthetic loopback PostgreSQL; explicit ordinary source and locked dependency beams. No full-app harness or frozen implementation read/import/execution. No native/capture/UI/phone/provider/production action.",
        "pending": ["Complete nine-relation columns/constraints/indexes/triggers/policy and writer grant matrix",
            "Exact baseline PUBLIC scoped/directory policies preserved and compared",
            "Trusted owner transaction binding and Store ownership",
            "Original owner budget integration, lifecycle pool and startup/re-admission",
            "Preparation helper and combined manifest v2", "Runtime readiness/HTTP facade/provider join",
            "Neon/operator/TLS/custody qualification", "Browser/native/physical checks paused", "Customer/GA qualification"]}
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (BASE / "latest.json").write_text(json.dumps({"mutable_pointer_only": True,
        "attempt": str(OUT.relative_to(BASE)), "receipt": str((OUT / "receipt.json").relative_to(BASE))}, indent=2) + "\n")
    print(str(OUT.relative_to(ROOT)))
if not passed or not unchanged or not stopped:
    raise SystemExit(1)
