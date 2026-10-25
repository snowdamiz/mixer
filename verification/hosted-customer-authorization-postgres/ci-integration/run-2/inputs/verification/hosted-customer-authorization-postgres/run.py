#!/usr/bin/env python3
"""Selected ordinary sources, real disposable PostgreSQL, no application startup."""
import argparse
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HOSTED = ROOT / "hosted"
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--source-revision", required=True, help="Root-supplied context; no Git query")
parser.add_argument("--pg-bin", type=Path, default=Path("/opt/homebrew/opt/postgresql@17/bin"))
parser.add_argument("--additional-test", type=Path, action="append", default=[])
parser.add_argument("--ci-integration", action="store_true", help="Execute only the new shared fixture helper and test-side migration loading; no shared main")
args = parser.parse_args()
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=False)
scratch = Path(tempfile.mkdtemp(prefix="mixer-authz-postgres-"))
commands = []
cleanup = {}
status = "failed"
env = dict(os.environ, ERL_FLAGS="+S 2:2", ERL_CRASH_DUMP=str(scratch / "erl_crash.dump"))
sources = [
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/authorization/scope.ex",
    "hosted/lib/mixer_hosted/authorization/policy.ex",
    "hosted/lib/mixer_hosted/authorization/repository.ex",
    "hosted/lib/mixer_hosted/authorization/postgres_repository.ex",
    "hosted/lib/mixer_hosted/authorization/postgres/session.ex",
    "hosted/lib/mixer_hosted/authorization/postgres/evidence.ex",
    "hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs",
]
tests = ["hosted/test/mixer_hosted/authorization/postgres_repository_test.exs"]
for extra in args.additional_test:
    extra = extra.resolve()
    if not extra.is_relative_to(ROOT) or extra.suffix != ".exs" or not extra.is_file():
        parser.error("additional tests must be existing repository-local .exs files")
    tests.append(str(extra.relative_to(ROOT)))
inputs = sources + tests + [str(Path(__file__).resolve().relative_to(ROOT)), "hosted/mix.exs", "hosted/mix.lock"]
if args.ci_integration:
    inputs += [
        "hosted/scripts/test-local.py",
        "hosted/priv/repo/migrations/20261024000000_add_oban.exs",
        "hosted/priv/repo/migrations/20261025000000_add_build_journals.exs",
        "hosted/priv/repo/migrations/20261025000001_add_build_admission.exs",
        "hosted/priv/repo/migrations/20261025000002_add_build_aggregate_limits.exs",
        "hosted/test/foundation_integration_test.exs",
        "hosted/test/mixer_hosted/builds/storage_test.exs",
        "hosted/test/mixer_hosted/builds/admission_test.exs",
        "hosted/test/mixer_hosted/builds/aggregate_admission_test.exs",
        "hosted/test/mixer_hosted/builds/coordinator_test.exs",
        "verification/hosted-customer-authorization-postgres/ci-integration/migration_smoke.exs",
    ]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


before = {p: digest(ROOT / p) for p in inputs}
for p in inputs:
    target = output / "inputs" / p
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / p, target)
tree_digest = hashlib.sha256(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run(label, argv, check=True, run_env=None, timeout=90):
    log = output / (label + ".log")
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with log.open("wb") as stream:
        try:
            code = subprocess.run(list(map(str, argv)), cwd=scratch, env=run_env or env,
                                  stdout=stream, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            stream.write(b"\ncollector timeout\n")
            code = 124
    commands.append(dict(label=label, argv=list(map(str, argv)), cwd=str(scratch), started=started,
                         exit_code=code, output=log.name, sha256=digest(log)))
    if check and code:
        raise RuntimeError(f"{label}: exit {code}; see {log}")
    return code


try:
    run("elixir-version", ["elixir", "--version"])
    run("postgres-version", [args.pg_bin / "postgres", "--version"])
    run("python-version", ["python3", "--version"])
    dependency_beams = sorted(p for p in (HOSTED / "_build/test/lib").glob("*/ebin") if p.parent.name != "mixer_hosted")
    if not dependency_beams:
        raise RuntimeError("prebuilt pinned dependencies unavailable; this runner does not fetch dependencies")
    beam_dir = scratch / "beams"
    beam_dir.mkdir()
    pa = [arg for p in dependency_beams for arg in ("-pa", p)]
    format_paths = sources[5:] + tests
    if args.ci_integration:
        format_paths += [p for p in inputs if p.endswith(".exs") and p not in format_paths]
    run("format", ["mix", "format", "--check-formatted"] + [ROOT / p for p in format_paths])
    compile_sources = [p for p in sources if not (args.ci_integration and "/migrations/" in p)]
    run("compile", ["elixirc", "--warnings-as-errors", "-o", beam_dir] + pa + [ROOT / p for p in compile_sources])
    bootstrap_admin = "mixer_fixture" if args.ci_integration else "authz_fixture_admin"
    run("initdb", [args.pg_bin / "initdb", "-D", scratch / "data", "-U", bootstrap_admin,
                   "--auth-local=trust", "--auth-host=trust", "--no-locale", "-E", "UTF8"])
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    run("postgres-start", [args.pg_bin / "pg_ctl", "-D", scratch / "data", "-l", output / "postgres.log",
                           "-o", f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC", "-w", "start"])
    if args.ci_integration:
        harness_path = ROOT / "hosted/scripts/test-local.py"
        harness_source = harness_path.read_text()
        named = [node for node in ast.parse(harness_source).body
                 if isinstance(node, ast.FunctionDef) and node.name == "provision_customer_authorization_fixture"]
        if len(named) != 1 or named[0].decorator_list or len(named[0].args.args) != 3:
            raise RuntimeError("expected exactly one undecorated named three-argument fixture helper")
        helper = named[0]
        namespace = {"__builtins__": __builtins__}
        exec(compile(ast.Module(body=[helper], type_ignores=[]), str(harness_path), "exec"), namespace)
        selected_helper = dict(name=helper.name,
                               source_sha256=hashlib.sha256(ast.get_source_segment(harness_source, helper).encode()).hexdigest(),
                               shared_main_executed=False)
        env.update(namespace[helper.name](args.pg_bin, port, run))
        run("migration-smoke-database", [args.pg_bin / "createdb", "-h", "127.0.0.1", "-p", str(port), "-U", bootstrap_admin, "mixer_authz_migrations_test"])
        run("migration-smoke", ["elixir", "-pa", beam_dir] + pa + [ROOT / "verification/hosted-customer-authorization-postgres/ci-integration/migration_smoke.exs", ROOT / "hosted/priv/repo/migrations"], timeout=90)
    else:
        psql = [args.pg_bin / "psql", "-X", "-h", "127.0.0.1", "-p", str(port), "-U", bootstrap_admin, "-d", "postgres", "-v", "ON_ERROR_STOP=1"]
        run("roles", psql + ["-c", "CREATE ROLE mixer_authz_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS; CREATE ROLE mixer_authz_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;"])
        run("database", [args.pg_bin / "createdb", "-h", "127.0.0.1", "-p", str(port), "-U", bootstrap_admin, "-O", "mixer_authz_owner", "mixer_authz_test"])
        run("database-grants", psql[:-4] + ["mixer_authz_test", "-v", "ON_ERROR_STOP=1", "-c", "REVOKE ALL ON DATABASE mixer_authz_test FROM PUBLIC; GRANT CONNECT ON DATABASE mixer_authz_test TO mixer_authz_runtime; REVOKE CREATE ON SCHEMA public FROM PUBLIC;"])
    env["MIXER_AUTHZ_TEST_PORT"] = str(port)
    entrypoint = scratch / "run.exs"
    entrypoint.write_text('Application.ensure_all_started(:ecto_sql)\nApplication.ensure_all_started(:postgrex)\nLogger.configure(level: :warning)\nExUnit.start(seed: 0, trace: true)\n' +
                          "\n".join("Code.require_file(" + json.dumps(str(ROOT / p)) + ")" for p in tests) + "\n")
    shutil.copyfile(entrypoint, output / "entrypoint.exs")
    run("tests", ["elixir", "-pa", beam_dir] + pa + [entrypoint], timeout=120)
    if before != {p: digest(ROOT / p) for p in inputs}:
        raise RuntimeError("selected inputs changed during execution")
    status = "passed"
finally:
    if (scratch / "data/postmaster.pid").exists():
        cleanup["postgres_stopped"] = run("postgres-stop", [args.pg_bin / "pg_ctl", "-D", scratch / "data", "-m", "fast", "-w", "stop"], check=False) == 0
    else:
        cleanup["postgres_stopped"] = True
    if cleanup["postgres_stopped"]:
        shutil.rmtree(scratch)
        cleanup["owned_scratch_removed"] = not scratch.exists()
    if not all(cleanup.values()):
        status = "failed"
    receipt = dict(schema=1, status=status, source_revision=args.source_revision,
                   revision_origin="Root supplied context; no Git command executed",
                   ci_integration=args.ci_integration,
                   selected_shared_harness_helper=locals().get("selected_helper"),
                   source_tree_sha256=tree_digest, inputs=before, commands=commands, cleanup=cleanup,
                   dependency_beams=[str(p) for p in locals().get("dependency_beams", [])],
                   scope="Selected ordinary authorization sources and tests, Ecto/Postgrex with disposable loopback PostgreSQL17, synthetic state, separate owner/runtime roles and real locks/RLS. No Mix application startup.",
                   limitations=["Pure callback result is not transaction-bound domain authority.",
                                "No protected route/domain/audit/idempotency/Oban composition, real issuer/provider, Neon/TLS, deployed service, native/device or GA qualification.",
                                "Runtime trust boundary permits identity GUCs; this does not protect against hostile API or compromised DB credentials.",
                                "Existing caller-supplied evaluation instant is preserved; future domain facade needs trusted-clock recheck before persistence."])
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(dict(status=status, receipt=str(output / "receipt.json"), cleanup=cleanup)))
