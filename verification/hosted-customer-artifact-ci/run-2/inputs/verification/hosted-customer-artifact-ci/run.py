#!/usr/bin/env python3
"""Test the named CI fixture and seven ordinary migrations without shared main."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
HEAD = "9662eda186e3beee084f92ac25c4116c92f2cebc"
SOURCES = [
    "hosted/lib/mixer_hosted/authorization/artifact_read.ex",
    "hosted/lib/mixer_hosted/protocol/artifact_cbor.ex",
    "hosted/lib/mixer_hosted/protocol/artifact_json.ex",
    "hosted/lib/mixer_hosted/protocol/artifact_v3_policy.ex",
    "hosted/lib/mixer_hosted/protocol/artifact_admission.ex",
    "hosted/lib/mixer_hosted/audit/customer_artifact_event.ex",
    "hosted/lib/mixer_hosted/customer_artifacts/schema.ex",
    "hosted/lib/mixer_hosted/customer_artifacts/topology.ex",
    "hosted/lib/mixer_hosted/customer_artifacts/postgres_storage.ex",
    "hosted/lib/mixer_hosted/customer_artifacts.ex",

    "hosted/lib/mixer_hosted/repo.ex",
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/authorization/scope.ex",
    "hosted/lib/mixer_hosted/authorization/policy.ex",
    "hosted/lib/mixer_hosted/authorization/postgres/session.ex",
    "hosted/lib/mixer_hosted/authorization/postgres/evidence.ex",
    "hosted/lib/mixer_hosted/authorization/transaction/snapshot.ex",
    "hosted/lib/mixer_hosted/authorization/transaction/context.ex",
    "hosted/lib/mixer_hosted/authorization.ex",
]
MIGRATIONS = ["20261024000000_add_oban.exs", "20261025000000_add_build_journals.exs",
              "20261025000001_add_build_admission.exs", "20261025000002_add_build_aggregate_limits.exs",
              "20261025000003_add_customer_authorization.exs", "20261025000004_add_authorization_state_revisions.exs", "20261025000005_add_customer_artifact_storage.exs"]
TESTS = ["hosted/test/mixer_hosted/authorization/transaction_test.exs",
         "hosted/test/mixer_hosted/authorization/policy_test.exs",
         "hosted/test/mixer_hosted/authorization/artifact_read_test.exs",
         "hosted/test/mixer_hosted/customer_artifacts/postgres_storage_test.exs",
         "hosted/test/mixer_hosted/customer_artifacts_test.exs"]
CI_TESTS = ["hosted/test/foundation_integration_test.exs"] + [
    f"hosted/test/mixer_hosted/builds/{n}_test.exs"
    for n in ["storage", "admission", "aggregate_admission", "coordinator"]]
HARNESS = "hosted/scripts/test-local.py"
INPUTS = SOURCES + TESTS + [HARNESS, "hosted/mix.exs", "hosted/mix.lock", "services/protocol/testdata/signed-release-v3.json"] + CI_TESTS + [
    "hosted/priv/repo/migrations/" + n for n in MIGRATIONS] + [
    str(HERE.relative_to(ROOT) / n) for n in ["run.py", "migration_smoke.exs", "README.md"]]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = HERE / sys.argv[1]
    assert output.parent == HERE and not output.exists()
    output.mkdir()
    env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test")
    scratch = Path(tempfile.mkdtemp(prefix="mixer-artifact-ci-"))
    receipt = {"source_revision": HEAD, "commands": [], "cleanup": {},
               "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "scope": "Named synthetic CI helper, seven ordinary migrations, and selected customer transaction/artifact ExUnit suites. No shared harness main, application startup, frozen lane or native execution."}
    started = False
    success = False

    def run(name, argv, timeout=90, check=True):
        argv = [str(x) for x in argv]
        result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True, timeout=timeout)
        (output / (name + ".stdout")).write_bytes(result.stdout)
        (output / (name + ".stderr")).write_bytes(result.stderr)
        receipt["commands"].append({"name": name, "argv": argv, "exit_code": result.returncode,
                                     "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                                     "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()})
        if check and result.returncode:
            raise RuntimeError(f"{name}: exit {result.returncode}")
        return result

    try:
        before = {n: digest(ROOT / n) for n in sorted(INPUTS)}
        receipt["inputs"] = before
        receipt["source_tree_sha256"] = hashlib.sha256(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        for name in before:
            target = output / "inputs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        deps = sorted(p for p in (ROOT / "hosted/_build/test/lib").glob("*/ebin") if p.parent.name != "mixer_hosted")
        assert deps
        dep_manifest = {str(p.relative_to(ROOT)): digest(p) for d in deps for p in sorted(d.iterdir()) if p.is_file()}
        (output / "dependencies.json").write_text(json.dumps(dep_manifest, indent=2) + "\n")
        receipt["dependency_manifest_sha256"] = digest(output / "dependencies.json")
        pa = [v for p in deps for v in ["-pa", p]]
        run("python-version", ["python3", "--version"])
        run("elixir-version", ["elixir", "--version"])
        pg = Path(run("postgres-bindir", ["pg_config", "--bindir"]).stdout.decode().strip())
        run("postgres-version", [pg / "postgres", "--version"])
        format_paths = [output / "inputs" / n for n in INPUTS if n.endswith((".ex", ".exs")) and not n.endswith("mix.exs")]
        run("format", ["mix", "format", "--check-formatted", *format_paths])
        beams = scratch / "beams"
        beams.mkdir()
        run("compile", ["elixirc", "--warnings-as-errors", *pa, "-o", beams, *[output / "inputs" / n for n in SOURCES]])
        run("initdb", [pg / "initdb", "-D", scratch / "data", "-U", "mixer_fixture", "-A", "trust", "--no-locale", "-E", "UTF8"])
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        run("postgres-start", [pg / "pg_ctl", "-D", scratch / "data", "-l", scratch / "postgres.log", "-o", f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC", "-w", "start"])
        started = True
        source = (output / "inputs" / HARNESS).read_text()
        nodes = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name in {"provision_customer_transaction_fixture", "provision_customer_artifact_fixtures"}]
        assert len(nodes) == 2 and all(not n.decorator_list and len(n.args.args) == 3 for n in nodes)
        namespace = {"__builtins__": __builtins__}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), HARNESS, "exec"), namespace)
        for node in nodes:
            env.update(namespace[node.name](pg, port, run))
        receipt["shared_helpers"] = [{"name": node.name, "sha256": hashlib.sha256(ast.get_source_segment(source, node).encode()).hexdigest(), "shared_main_executed": False} for node in nodes]
        run("migration-database", [pg / "createdb", "-h", "127.0.0.1", "-p", port, "-U", "mixer_fixture", "mixer_transaction_migrations_test"])
        run("migration-smoke", ["elixir", *pa, "-pa", beams, output / "inputs" / HERE.relative_to(ROOT) / "migration_smoke.exs", output / "inputs/hosted/priv/repo/migrations"])
        entry = scratch / "entry.exs"
        entry.write_text('Application.ensure_all_started(:ecto_sql)\nApplication.ensure_all_started(:postgrex)\nLogger.configure(level: :warning)\nExUnit.start(seed: 0, trace: true)\n' + ''.join('Code.require_file(' + json.dumps(str(output / 'inputs' / name)) + ')\n' for name in TESTS))
        shutil.copyfile(entry, output / "entry.exs")
        run("tests", ["elixir", *pa, "-pa", beams, entry], timeout=120)
        assert before == {n: digest(ROOT / n) for n in INPUTS}, "source changed during execution"
        success = True
    except Exception as error:
        receipt["failure"] = str(error)
    finally:
        stop_needed = started or (scratch / "data/postmaster.pid").exists()
        if stop_needed:
            try:
                receipt["cleanup"]["postgres_stopped"] = run("postgres-stop", [pg / "pg_ctl", "-D", scratch / "data", "-m", "fast", "-w", "stop"], timeout=30, check=False).returncode == 0
            except Exception as error:
                receipt["cleanup"]["postgres_stop_error"] = str(error)
        else:
            receipt["cleanup"]["postgres_started"] = False
        if (scratch / "postgres.log").exists():
            shutil.copyfile(scratch / "postgres.log", output / "postgres.log")
        if not stop_needed or receipt["cleanup"].get("postgres_stopped"):
            shutil.rmtree(scratch)
        receipt["cleanup"]["scratch_removed"] = not scratch.exists()
        receipt["success"] = success and receipt["cleanup"]["scratch_removed"]
        receipt["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: receipt.get(k) for k in ["success", "failure", "source_tree_sha256", "cleanup"]}))
    return 0 if receipt["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
