#!/usr/bin/env python3
"""One disposable PG process; explicit ordinary sources, no Mix or frozen lanes."""
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

ROOT = pathlib.Path(__file__).resolve().parents[3]
REPO = ROOT.parent
BASE = REPO / "verification/hosted-browser-session-storage"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--pg-bin", type=pathlib.Path, default=pathlib.Path("/opt/homebrew/opt/postgresql@17/bin"))
args = parser.parse_args()
PG = args.pg_bin.resolve()
BASE.mkdir(parents=True, exist_ok=True)
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
# Earlier development used overwritten latest logs. Preserve that last snapshot,
# explicitly without claiming it reconstructs the earlier overwritten attempts.
legacy = [p for p in BASE.iterdir() if p.is_file() and (p.suffix == ".log" or p.name == "receipt.json")]
if legacy:
    development = BASE / ("development-snapshot-" + stamp)
    development.mkdir()
    for path in legacy:
        shutil.move(str(path), development / path.name)
    (development / "README.txt").write_text("Last overwritten development output, preserved when immutable attempt recording began. Earlier per-run outputs were not retained and are not reconstructed here.\n")
OUT = BASE / "attempts" / stamp
OUT.mkdir(parents=True)
source_paths = [
    ROOT / "lib/mixer_hosted/browser_auth/storage_schema.ex",
    ROOT / "lib/mixer_hosted/browser_auth/vault.ex",
    ROOT / "lib/mixer_hosted/browser_auth/stored_snapshot.ex",
    ROOT / "test/mixer_hosted/browser_auth/storage_fixture.exs",
    ROOT / "test/mixer_hosted/browser_auth/storage_spec.exs",
    pathlib.Path(__file__).resolve(), REPO / "docs/hosted-browser-session-storage.md",
    ROOT / "mix.exs", ROOT / "mix.lock",
] + [ROOT / "priv/repo/migrations" / name for name in [
    "20261025000003_add_customer_authorization.exs",
    "20261025000004_add_authorization_state_revisions.exs",
    "20261025000006_add_customer_workspace_discovery.exs",
    "20261025000007_add_browser_sessions.exs",
]]
# Explicit dependency paths exclude the complete hosted application's existing
# beams. No frozen application source or beam is read, compiled or imported.
dependency_dirs = sorted(p / "ebin" for p in (ROOT / "_build/test/lib").iterdir()
                         if p.name != "mixer_hosted" and (p / "ebin").is_dir())
beam_paths = sorted(path for directory in dependency_dirs for path in directory.glob("*.beam"))
if not beam_paths:
    raise RuntimeError("Existing locked dependency beams required; this runner never builds the full app")

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def manifest():
    return {"sources": {str(p.relative_to(REPO)): digest(p) for p in source_paths},
            "dependency_beams": {str(p.relative_to(REPO)): digest(p) for p in beam_paths}}

before = manifest()
(OUT / "source-manifest.json").write_text(json.dumps(before, indent=2) + "\n")
records = []
scratch = None
success = False
unchanged = False
stopped = True
revision = None

def run(name, command, env=None, check=True, timeout=30):
    command = [str(value) for value in command]
    process = subprocess.Popen(command, cwd=REPO, env=env, text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               start_new_session=True)
    timed_out = False
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        output, _ = process.communicate(timeout=5)
    (OUT / (name + ".log")).write_text(output)
    records.append({"name": name, "command": command, "timeout_seconds": timeout,
                    "timed_out": timed_out, "exit_code": process.returncode,
                    "output": name + ".log"})
    if (process.returncode or timed_out) and check:
        print(output[-20000:])
        raise RuntimeError(name + " failed")
    return process.returncode, output

try:
    _, revision_output = run("git-head", ["git", "rev-parse", "HEAD"])
    revision = revision_output.strip()
    run("postgres-version", [PG / "postgres", "--version"])
    run("elixir-version", ["elixir", "--version"])
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="mixer-browser-storage-"))
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    run("initdb", [PG / "initdb", "-D", scratch / "data", "-U", "browser_admin",
                   "-A", "trust", "--no-locale", "-E", "UTF8"])
    run("postgres-start", [PG / "pg_ctl", "-D", scratch / "data", "-l", OUT / "postgres.log",
                           "-o", f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC", "-w", "start"], timeout=15)
    psql = [PG / "psql", "-X", "-h", "127.0.0.1", "-p", str(port), "-U", "browser_admin",
            "-d", "postgres", "-v", "ON_ERROR_STOP=1"]
    run("fixture-roles", psql + ["-c", "CREATE ROLE browser_schema_owner NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_writer NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_lifecycle LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_ordinary LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_operator LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;"])
    for database, owner in [("browser_storage", "browser_schema_owner"), ("browser_operator_storage", "browser_operator")]:
        run(database + "-database", [PG / "createdb", "-h", "127.0.0.1", "-p", str(port),
                                     "-U", "browser_admin", "-O", owner, database])
    environment = os.environ.copy()
    environment["MIXER_BROWSER_STORAGE_PORT"] = str(port)
    command = ["elixir"]
    for directory in dependency_dirs:
        command += ["-pa", str(directory)]
    for source in ["storage_schema.ex", "vault.ex", "stored_snapshot.ex"]:
        command += ["-r", str(ROOT / "lib/mixer_hosted/browser_auth" / source)]
    command += ["-e", 'ExUnit.start(seed: 0); Code.require_file("hosted/test/mixer_hosted/browser_auth/storage_spec.exs")']
    run("focused-exunit", command, env=environment, timeout=60)
    success = True
finally:
    # Inspect the owned PID file even if pg_ctl timed out or failed after starting.
    # No unrelated process/container/simulator is enumerated, killed or modified.
    if scratch is not None and (scratch / "data/postmaster.pid").exists():
        code, _ = run("postgres-stop", [PG / "pg_ctl", "-D", scratch / "data", "-m", "immediate", "-w", "stop"], check=False, timeout=15)
        stopped = code == 0 and not (scratch / "data/postmaster.pid").exists()
    elif scratch is not None:
        stopped = not (scratch / "data/postmaster.pid").exists()
    if scratch is not None and stopped:
        shutil.rmtree(scratch)
    after = manifest()
    unchanged = before == after
    (OUT / "source-manifest-after.json").write_text(json.dumps(after, indent=2) + "\n")
    receipt = {
        "schema": 2, "time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "head": revision, "source_manifest": "source-manifest.json",
        "source_manifest_sha256": digest(OUT / "source-manifest.json"),
        "source_unchanged": unchanged, "commands": records,
        "focused_tests_passed": success and unchanged,
        "cleanup": {"owned_postgres_stopped": stopped, "owned_scratch_removed": scratch is None or not scratch.exists()},
        "scope": "Synthetic loopback PostgreSQL; selected StorageSchema/Vault/StoredSnapshot and ordinary 3/4/6/7 migrations against existing dependency beams only. No whole-app compile, frozen lane, browser/native/provider/production action.",
        "pending": ["Current-verifier/OIDC/provider owner join", "Production lifecycle pool and catalog admission",
                    "Neon ownership transfer/roles/TLS/key custody", "Nine-migration controls integrated by root",
                    "Commit/response uncertainty", "Retention scheduling", "Browser/native/physical checks paused", "Customer and GA review"]}
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (BASE / "latest.json").write_text(json.dumps({"mutable_pointer_only": True, "attempt": str(OUT.relative_to(BASE)), "receipt": str((OUT / "receipt.json").relative_to(BASE))}, indent=2) + "\n")
    print(str(OUT.relative_to(REPO)))
if not success or not unchanged or not stopped:
    raise SystemExit(1)
