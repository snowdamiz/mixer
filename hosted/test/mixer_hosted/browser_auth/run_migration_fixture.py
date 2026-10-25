#!/usr/bin/env python3
"""Selected ten-migration integration; no application or frozen-lane loading."""
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

ROOT = Path(__file__).resolve().parents[4]
BROWSER = "hosted/lib/mixer_hosted/browser_auth/"
MODULES = ["hosted/lib/mixer_hosted/customer_artifacts/schema.ex",
           BROWSER + "storage_schema.ex", BROWSER + "activation_preparation_schema.ex"]
MIGRATIONS = ["20261024000000_add_oban.exs", "20261025000000_add_build_journals.exs",
              "20261025000001_add_build_admission.exs", "20261025000002_add_build_aggregate_limits.exs",
              "20261025000003_add_customer_authorization.exs", "20261025000004_add_authorization_state_revisions.exs",
              "20261025000005_add_customer_artifact_storage.exs", "20261025000006_add_customer_workspace_discovery.exs",
              "20261025000007_add_browser_sessions.exs", "20261025000008_add_browser_activation_preparation.exs"]
DEPS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason", "oban"]
SPEC = "hosted/test/mixer_hosted/browser_auth/migration_spec.exs"
ASSERTIONS = ["hosted/test/foundation_integration_test.exs"] + [
    f"hosted/test/mixer_hosted/builds/{n}_test.exs" for n in ("storage", "admission", "aggregate_admission", "coordinator")]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--pg-bin", type=Path, default=Path("/opt/homebrew/opt/postgresql@17/bin"))
parser.add_argument("--output", type=Path, default=ROOT / "verification/hosted-browser-migration-integration/attempts")
args = parser.parse_args()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
out = args.output.resolve() / stamp
inputs = out / "inputs"
inputs.mkdir(parents=True, exist_ok=False)
pg = args.pg_bin.resolve()
sources = MODULES + [BROWSER + "activation_preparation.ex", SPEC, str(Path(__file__).resolve().relative_to(ROOT)),
                     "hosted/mix.lock", "hosted/mix.exs"] + ASSERTIONS
sources += ["hosted/priv/repo/migrations/" + n for n in MIGRATIONS]
deps = [ROOT / "hosted/_build/test/lib" / name / "ebin" for name in DEPS]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_manifest():
    return {rel: digest(ROOT / rel) for rel in sources}


receipt = {"schema": 2, "commands": [], "cleanup": {}, "dependencies": DEPS,
           "migration_filenames": MIGRATIONS,
           "scope": "Selected ten ordinary migrations under synthetic non-superuser schema owner; inert runtime privileges, additive-only down/up preserving baseline object OIDs/source/ACLs/tables/policies/constraints/data, seven-migration rollback/reapply preserving build data, complete rollback/reapply. Eight named locked dependency ebin directories only. No broad hosted harness/application/provider/native/frozen lane execution.",
           "pending": ["Independent migration review", "Neon/operator qualification", "Runtime lifecycle admission",
                       "Provider/OIDC/session join", "Browser/native tests paused", "Customer and GA acceptance"]}
env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test")
scratch = None
compiled = out / "compiled"
success = False
before = {}
beams = {}


def run(name, argv, timeout=60, check=True, cwd=inputs):
    argv = [str(x) for x in argv]
    entry = {"name": name, "argv": argv, "cwd": str(cwd), "timeout_seconds": timeout}
    receipt["commands"].append(entry)
    try:
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            entry["timed_out"] = False
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=5)
            entry["timed_out"] = True
        entry["exit_code"] = process.returncode
    except OSError as error:
        stdout, stderr = b"", str(error).encode()
        entry.update(exit_code=None, timed_out=False, spawn_error=type(error).__name__)
    (out / f"{name}.stdout").write_bytes(stdout)
    (out / f"{name}.stderr").write_bytes(stderr)
    entry.update(stdout_sha256=hashlib.sha256(stdout).hexdigest(), stderr_sha256=hashlib.sha256(stderr).hexdigest())
    if check and (entry["exit_code"] != 0 or entry["timed_out"]):
        raise RuntimeError(f"{name} failed: {entry['exit_code']}; see retained output")
    return entry["exit_code"], stdout


try:
    assert all(directory.is_dir() for directory in deps), "Compile the eight named locked dependencies first"
    assert set(MIGRATIONS) == {p.name for p in (ROOT / "hosted/priv/repo/migrations").iterdir() if p.is_file()}, "Unexpected migration directory entry"
    before = source_manifest()
    for rel in sources:
        dest = inputs / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, dest)
    beams = {str(p.relative_to(ROOT)): digest(p) for d in deps for p in sorted(d.iterdir()) if p.is_file()}
    (out / "dependencies.json").write_text(json.dumps(beams, indent=2) + "\n")
    receipt.update(sources=before,
                   source_tree_sha256=hashlib.sha256(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                   dependency_manifest_sha256=digest(out / "dependencies.json"))
    receipt["source_revision"] = run("git-head", ["git", "-C", ROOT, "rev-parse", "HEAD"])[1].decode().strip()
    run("python-version", ["python3", "--version"])
    run("elixir-version", ["elixir", "--version"])
    run("mix-version", ["mix", "--version"])
    run("postgres-version", [pg / "postgres", "--version"])
    pa = [v for p in deps for v in ["-pa", p]]
    compiled.mkdir()
    run("selected-compile", ["elixirc", *pa, "--warnings-as-errors", "-o", compiled, *[inputs / rel for rel in MODULES]])
    format_sources = MODULES + [BROWSER + "activation_preparation.ex", SPEC] + ASSERTIONS + ["hosted/priv/repo/migrations/" + n for n in MIGRATIONS]
    run("actual-mix-format", ["mix", "format", "--check-formatted", *[inputs / rel for rel in format_sources]])
    scratch = Path(tempfile.mkdtemp(prefix="mixer-browser-migrations-"))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    receipt["owned_postgres"] = {"scratch": str(scratch), "port": port, "host": "127.0.0.1", "pg_bin": str(pg)}
    env["MIXER_BROWSER_MIGRATION_PORT"] = str(port)
    run("initdb", [pg / "initdb", "-D", scratch / "data", "-U", "migration_admin", "-A", "trust", "--no-locale", "-E", "UTF8"])
    run("postgres-start", [pg / "pg_ctl", "-D", scratch / "data", "-l", out / "postgres.log", "-o", f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC", "-w", "start"])
    run("roles", [pg / "psql", "-X", "-h", "127.0.0.1", "-p", port, "-U", "migration_admin", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-c", "CREATE ROLE migration_owner LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEROLE NOCREATEDB NOREPLICATION; CREATE ROLE migration_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEROLE NOCREATEDB NOREPLICATION;"])
    run("database", [pg / "createdb", "-h", "127.0.0.1", "-p", port, "-U", "migration_admin", "-O", "migration_owner", "browser_migrations"])
    result = out / "result.json"
    entrypoint = out / "selected_runner.exs"
    entrypoint.write_text('ExUnit.start(autorun: false, seed: 0, trace: true)\nCode.require_file(' + json.dumps(str(inputs / SPEC)) + ')\nr=ExUnit.run()\nFile.write!(' + json.dumps(str(result)) + ',Jason.encode!(r))\nSystem.halt(if r.total==1 and r.failures==0 and r.skipped==0 and r.excluded==0 and Map.get(r,:invalid,0)==0, do: 0, else: 1)\n')
    run("migration-integration", ["elixir", *pa, "-pa", compiled, entrypoint], timeout=90)
    receipt["tests"] = json.loads(result.read_text())
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
    if compiled.exists():
        (out / "compiled-products.json").write_text(json.dumps({p.name: digest(p) for p in sorted(compiled.iterdir()) if p.is_file()}, indent=2) + "\n")
        shutil.rmtree(compiled)
    receipt["cleanup"] = {"owned_postgres_stopped": stopped, "owned_scratch_removed": scratch is None or not scratch.exists(), "owned_compile_products_removed": not compiled.exists()}
    receipt["source_unchanged"] = bool(before) and before == source_manifest()
    receipt["dependency_changes"] = [rel for rel, value in beams.items() if digest(ROOT / rel) != value]
    receipt["success"] = success and receipt["source_unchanged"] and not receipt["dependency_changes"] and all(receipt["cleanup"].values())
    receipt["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    receipt["outputs_sha256"] = {p.name: digest(p) for p in sorted(out.iterdir()) if p.is_file()}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"receipt": str(out / "receipt.json"), "success": receipt["success"], "failure": receipt.get("failure"), "cleanup": receipt["cleanup"]}))
raise SystemExit(0 if receipt["success"] else 1)
