#!/usr/bin/env python3
"""Selected nine-migration integration; no application or frozen-lane loading."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--pg-bin", type=Path, default=Path("/opt/homebrew/opt/postgresql@17/bin"))
parser.add_argument("--output", type=Path, default=ROOT / "verification/hosted-browser-migration-review/attempts")
args = parser.parse_args()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
out = args.output.resolve() / stamp
out.mkdir(parents=True, exist_ok=False)
pg = args.pg_bin.resolve()
hosted = ROOT / "hosted"
schema = hosted / "lib/mixer_hosted/browser_auth/storage_schema.ex"
artifact_schema = hosted / "lib/mixer_hosted/customer_artifacts/schema.ex"
spec = Path(__file__).with_name("independent_spec.exs")
sources = [schema, artifact_schema, spec, Path(__file__).resolve(), hosted / "mix.lock", hosted / "mix.exs"]
sources += sorted((hosted / "priv/repo/migrations").glob("*.exs"))
sources += [Path(__file__).with_name("source_contracts.py"), hosted / "test/foundation_integration_test.exs", ROOT / ".github/workflows/hosted.yml", hosted / "test/mixer_hosted/browser_auth/migration_spec.exs", hosted / "test/mixer_hosted/browser_auth/run_migration_fixture.py"]
sources += [hosted / f"test/mixer_hosted/builds/{n}_test.exs" for n in ("storage", "admission", "aggregate_admission", "coordinator")]
deps = sorted(p for p in (hosted / "_build/test/lib").glob("*/ebin") if p.parent.name != "mixer_hosted")
assert deps, "Compile locked dependencies first; full application beams are never loaded"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest():
    return {str(p.relative_to(ROOT)): digest(p) for p in sources}


before = source_manifest()
for source in sources:
    dest = out / "inputs" / source.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
(out / "dependencies.json").write_text(json.dumps({str(p.relative_to(ROOT)): digest(p) for d in deps for p in sorted(d.glob("*.beam"))}, indent=2) + "\n")
receipt = {"schema": 1, "sources": before, "commands": [], "cleanup": {},
           "source_tree_sha256": hashlib.sha256(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
           "dependency_manifest_sha256": digest(out / "dependencies.json"),
           "scope": "Independent migration SQL assertions using a disclosed adaptation of the producer process/cluster harness: nine applies/idempotence, actual restricted-runtime denials, inert RLS/policies, deliberate disposable permission/RLS drift detection, latest-six and full teardown/reapply, build data preservation. No broad hosted harness/application/provider/native/frozen lane execution.",
           "pending": ["Neon/operator qualification", "Runtime lifecycle admission", "Provider/OIDC/session join", "Browser/native tests paused", "Customer and GA acceptance"]}
env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test", MIXER_REVIEW_ROOT=str(ROOT))
scratch = None
success = False


def run(name, argv, timeout=60, check=True):
    argv = [str(x) for x in argv]
    process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate(timeout=5)
    (out / f"{name}.stdout").write_bytes(stdout)
    (out / f"{name}.stderr").write_bytes(stderr)
    receipt["commands"].append({"name": name, "argv": argv, "timeout_seconds": timeout,
                                "exit_code": process.returncode, "timed_out": timed_out,
                                "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                                "stderr_sha256": hashlib.sha256(stderr).hexdigest()})
    if check and (process.returncode or timed_out):
        raise RuntimeError(f"{name} failed: {process.returncode}; see retained output")
    return process.returncode, stdout


try:
    receipt["source_revision"] = run("git-head", ["git", "rev-parse", "HEAD"])[1].decode().strip()
    run("python-version", ["python3", "--version"])
    run("source-contracts", ["python3", Path(__file__).with_name("source_contracts.py")])
    run("elixir-version", ["elixir", "--version"])
    run("postgres-version", [pg / "postgres", "--version"])
    scratch = Path(tempfile.mkdtemp(prefix="mixer-browser-migration-review-"))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env["MIXER_BROWSER_MIGRATION_PORT"] = str(port)
    run("initdb", [pg / "initdb", "-D", scratch / "data", "-U", "migration_admin", "-A", "trust", "--no-locale", "-E", "UTF8"])
    run("postgres-start", [pg / "pg_ctl", "-D", scratch / "data", "-l", out / "postgres.log", "-o", f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC", "-w", "start"])
    run("roles", [pg / "psql", "-X", "-h", "127.0.0.1", "-p", port, "-U", "migration_admin", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c", "CREATE ROLE migration_owner LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEROLE NOCREATEDB NOREPLICATION; CREATE ROLE migration_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEROLE NOCREATEDB NOREPLICATION;"])
    run("database", [pg / "createdb", "-h", "127.0.0.1", "-p", port, "-U", "migration_admin", "-O", "migration_owner", "browser_migrations"])
    pa = [v for p in deps for v in ["-pa", p]]
    run("migration-integration", ["elixir", *pa, "-r", artifact_schema, "-r", schema, "-e", f'ExUnit.start(seed: 0, trace: true); Code.require_file({json.dumps(str(spec))})'], timeout=90)
    success = True
except Exception as error:
    receipt["failure"] = str(error)
finally:
    stopped = scratch is None or not (scratch / "data/postmaster.pid").exists()
    if not stopped:
        code, _ = run("postgres-stop", [pg / "pg_ctl", "-D", scratch / "data", "-m", "immediate", "-w", "stop"], timeout=20, check=False)
        stopped = code == 0 and not (scratch / "data/postmaster.pid").exists()
    if scratch is not None and stopped:
        shutil.rmtree(scratch)
    receipt["cleanup"] = {"owned_postgres_stopped": stopped, "owned_scratch_removed": scratch is None or not scratch.exists()}
    receipt["source_unchanged"] = before == source_manifest()
    receipt["success"] = success and receipt["source_unchanged"] and all(receipt["cleanup"].values())
    receipt["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"receipt": str(out / "receipt.json"), "success": receipt["success"], "failure": receipt.get("failure"), "cleanup": receipt["cleanup"]}))
raise SystemExit(0 if receipt["success"] else 1)
