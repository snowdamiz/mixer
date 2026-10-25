#!/usr/bin/env python3
"""CI-fixture repair collector: selected ordinary modules and migrations only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
SOURCES = [
    "hosted/lib/mixer_hosted/repo.ex",
    "hosted/lib/mixer_hosted/identity/encoding.ex",
    "hosted/lib/mixer_hosted/identity/verified_identity.ex",
    "hosted/lib/mixer_hosted/identity/bounded_json.ex",
    "hosted/lib/mixer_hosted/authorization/scope.ex",
    "hosted/lib/mixer_hosted/authorization/policy.ex",
    "hosted/lib/mixer_hosted/authorization/postgres/session.ex",
    "hosted/lib/mixer_hosted/authorization/transaction/snapshot.ex",
    "hosted/lib/mixer_hosted/authorization/transaction/context.ex",
    "hosted/lib/mixer_hosted/customer_workspace.ex",
    "hosted/lib/mixer_hosted/customer_workspace/input.ex",
    "hosted/lib/mixer_hosted/customer_workspace/storage.ex",
    "hosted/lib/mixer_hosted/customer_artifacts/schema.ex",
    "hosted/priv/repo/migrations/20261024000000_add_oban.exs",
    "hosted/priv/repo/migrations/20261025000000_add_build_journals.exs",
    "hosted/priv/repo/migrations/20261025000001_add_build_admission.exs",
    "hosted/priv/repo/migrations/20261025000002_add_build_aggregate_limits.exs",
    "hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs",
    "hosted/priv/repo/migrations/20261025000004_add_authorization_state_revisions.exs",
    "hosted/priv/repo/migrations/20261025000005_add_customer_artifact_storage.exs",
    "hosted/priv/repo/migrations/20261025000006_add_customer_workspace_discovery.exs",
]
TEST = "hosted/test/mixer_hosted/customer_workspace_test.exs"
FIXTURE_TESTS = [
    "hosted/test/foundation_integration_test.exs",
    "hosted/test/mixer_hosted/builds/aggregate_admission_test.exs",
    "hosted/test/mixer_hosted/builds/coordinator_test.exs",
    "hosted/test/mixer_hosted/builds/admission_test.exs",
    "hosted/test/mixer_hosted/builds/storage_test.exs",
]
DEPS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason", "oban"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    output.relative_to(ROOT / "verification/hosted-workspace-ci-fixture-repair/684bd524")
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test")
    receipt = {"source_revision": args.source_revision, "revision_provenance": "root-supplied current HEAD; copied input tree records uncommitted source", "commands": [], "scope": "684bd524 cold first organization read: actual query chronology and nonexecuting EXPLAIN of ordinary identity, topology and organization queries on owned PG16.15 Linux arm64 with C locale, restricted runtime role and unchanged 5s/500ms bounds. All24 ordinary workspace methods and8migration boundaries run. Probe adds recorded planning overhead; not exact Ubuntu amd64 CI reproduction. No frozen lanes, browser/native/phone/provider/GA acceptance.", "platform": platform.platform(), "started_unix": time.time(), "cleanup": {}}
    scratch = Path(tempfile.mkdtemp(prefix="mixer-customer-workspace-"))
    receipt["scratch"] = str(scratch)
    receipt["diagnostic_environment"] = {"MIXER_COLD_READ_DISABLE_JIT": env.get("MIXER_COLD_READ_DISABLE_JIT", "false")}
    started = False
    success = False
    container_name = "mixer-workspace-plan-" + str(os.getpid()) + "-" + str(int(time.time()))

    def run(name, command, *, timeout=90, check=True):
        result = subprocess.run([str(x) for x in command], cwd=output / "inputs", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, text=True)
        (output / (name + ".log")).write_text(result.stdout)
        receipt["commands"].append({"name": name, "argv": [str(x) for x in command], "exit_code": result.returncode, "output": name + ".log"})
        if check and result.returncode:
            raise RuntimeError(f"{name} failed ({result.returncode}); see preserved log")
        return result

    try:
        inputs = SOURCES + FIXTURE_TESTS + [TEST, "hosted/mix.exs", "hosted/mix.lock", "verification/hosted-workspace-ci-fixture-repair/684bd524/collect-cold-read.py", "verification/hosted-workspace-ci-fixture-repair/684bd524/cold-read-probe.exs", "verification/hosted-workspace-ci-fixture-repair/migration-fixtures.exs", "docs/hosted-workspace-ci-fixture-repair.md"]
        doc = "docs/hosted-workspace-ci-fixture-repair.md"
        if (ROOT / doc).is_file():
            inputs.append(doc)
        manifest = {}
        for name in sorted(inputs):
            source = ROOT / name
            target = output / "inputs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            manifest[name] = digest(source)
        receipt["input_sha256"] = manifest
        receipt["source_tree_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        paths = [ROOT / "hosted/_build/test/lib" / dep / "ebin" for dep in DEPS]
        dependency_manifest = {}
        for path in paths:
            if not path.is_dir():
                raise RuntimeError("missing pinned dependency BEAM directory: " + str(path))
            for beam in sorted(path.iterdir()):
                if beam.is_file():
                    dependency_manifest[str(beam.relative_to(ROOT))] = digest(beam)
        (output / "dependency-beams.json").write_text(json.dumps(dependency_manifest, indent=2) + "\n")
        receipt["dependency_manifest_sha256"] = digest(output / "dependency-beams.json")
        run("elixir-version", ["elixir", "--version"])
        run("python-version", ["python3", "--version"])
        pg = Path(run("postgres-bindir", ["pg_config", "--bindir"]).stdout.strip())
        run("postgres-version", [pg / "postgres", "--version"])
        formatted = [name for name in SOURCES if "customer_workspace" in name] + FIXTURE_TESTS + [TEST, "verification/hosted-workspace-ci-fixture-repair/migration-fixtures.exs"]
        run("format", ["mix", "format", "--check-formatted", *[output / "inputs" / name for name in formatted]])
        beams = scratch / "beams"
        beams.mkdir()
        codepaths = [arg for path in paths for arg in ["-pa", str(path)]]
        compile_code = "result = Kernel.ParallelCompiler.compile_to_path(System.argv(), " + json.dumps(str(beams)) + ", return_diagnostics: true); case result do {:ok, _, %{compile_warnings: [], runtime_warnings: []}} -> :ok; _ -> IO.inspect(result); System.halt(1) end"
        run("compile", ["elixir", *codepaths, "-e", compile_code, "--", *[output / "inputs" / name for name in SOURCES]])
        run("docker-version", ["docker", "version", "--format", "{{json .Server}}"])
        run("postgres-image-availability", ["docker", "image", "inspect", "postgres:16", "--format", "{{.Id}}"], timeout=30)
        receipt["postgres_image"] = json.loads(run("postgres-image-inspect", ["docker", "image", "inspect", "postgres:16", "--format", "{{json .RepoDigests}}"]).stdout)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        receipt["postgres_endpoint"] = {"host": "127.0.0.1", "port": port, "database": "mixer_customer_workspace", "disposable": True, "container": container_name}
        run("postgres-start", ["docker", "run", "--detach", "--rm", "--name", container_name, "--label", "mixer.fixture=workspace-plan-diagnostic", "--publish", f"127.0.0.1:{port}:5432", "--env", "POSTGRES_USER=workspace_fixture_admin", "--env", "POSTGRES_DB=postgres", "--env", "POSTGRES_HOST_AUTH_METHOD=trust", "--env", "POSTGRES_INITDB_ARGS=--no-locale -E UTF8", "postgres@sha256:9e2cf6287f25c3151f4c9421ccce2b17f3e60061c111a29165e0d2cdd9ff0a97", "-c", "max_connections=24"], timeout=90)
        started = True
        ready = False
        for attempt in range(100):
            result = run("postgres-ready-" + str(attempt), [pg / "pg_isready", "-h", "127.0.0.1", "-p", port, "-U", "workspace_fixture_admin"], check=False)
            if result.returncode == 0:
                ready = True
                break
            time.sleep(0.1)
        if not ready:
            raise RuntimeError("owned PostgreSQL16 container did not become ready")
        run("postgres-server-version", ["docker", "exec", container_name, "postgres", "--version"])
        psql = [pg / "psql", "-h", "127.0.0.1", "-p", port, "-U", "workspace_fixture_admin", "-v", "ON_ERROR_STOP=1"]
        run("roles-apply", psql + ["-d", "postgres", "-c", "CREATE ROLE workspace_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; CREATE ROLE workspace_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;"])
        run("database", [pg / "createdb", "-h", "127.0.0.1", "-p", port, "-U", "workspace_fixture_admin", "mixer_customer_workspace"])
        run("schema", psql + ["-d", "mixer_customer_workspace", "-c", "REVOKE CREATE ON SCHEMA public FROM PUBLIC; ALTER SCHEMA public OWNER TO workspace_owner; GRANT USAGE ON SCHEMA public TO workspace_runtime;"])
        run("migration-database", [pg / "createdb", "-h", "127.0.0.1", "-p", port, "-U", "workspace_fixture_admin", "mixer_ci_migrations"])
        run("migration-schema", psql + ["-d", "mixer_ci_migrations", "-c", "REVOKE CREATE ON SCHEMA public FROM PUBLIC; ALTER SCHEMA public OWNER TO workspace_owner;"])
        env["MIXER_WORKSPACE_TEST_PORT"] = str(port)
        env["MIXER_CI_MIGRATION_RESULT"] = str(output / "full-migration-result.json")
        env["MIXER_CI_MIGRATION_PATH"] = str(output / "inputs/hosted/priv/repo/migrations")
        run("all-migration-fixtures", ["elixir", *codepaths, "-pa", beams, output / "inputs/verification/hosted-workspace-ci-fixture-repair/migration-fixtures.exs"], timeout=120)
        env["MIXER_COLD_READ_TRACE"] = str(output / "cold-read-trace.jsonl")
        env["MIXER_COLD_READ_PLANS"] = str(output / "cold-read-plans")
        env["MIXER_WORKSPACE_LOCK_EXPIRY_RESULT"] = str(output / "lock-expiry-result.json")
        env["MIXER_WORKSPACE_EXUNIT_RESULT"] = str(output / "exunit-result.json")
        env["MIXER_WORKSPACE_MIGRATION_RESULT"] = str(output / "migration-result.json")
        runner = scratch / "run.exs"
        runner.write_text('Application.ensure_all_started(:ecto_sql)\nApplication.ensure_all_started(:postgrex)\nExUnit.start(autorun: false, seed: 0, max_cases: 1)\nCode.require_file(' + json.dumps(str(output / "inputs" / TEST)) + ')\nCode.require_file(' + json.dumps(str(output / "inputs/verification/hosted-workspace-ci-fixture-repair/684bd524/cold-read-probe.exs")) + ')\nresult = ExUnit.run()\nFile.write!(System.fetch_env!("MIXER_WORKSPACE_EXUNIT_RESULT"), Jason.encode!(result))\nSystem.halt(if result.failures == 0 and result.total == 24 and result.skipped == 0 and result.excluded == 0, do: 0, else: 1)\n')
        run("tests", ["elixir", *codepaths, "-pa", beams, runner], timeout=120)
        trace = [json.loads(line) for line in (output / "cold-read-trace.jsonl").read_text().splitlines()]
        if trace[-1]["query"].lower() != "commit" or sum(e["category"] == "identity" for e in trace) < 2:
            raise RuntimeError("cold-read trace did not capture successful first transaction and both identity checkpoints")
        if "has failed and has been detached" in (output / "tests.log").read_text():
            raise RuntimeError("diagnostic telemetry handler detached; not accepted")
        receipt["cold_read_trace"] = {"events": len(trace), "final_elapsed_us": trace[-1]["elapsed_at_end_us"], "identity_checkpoints": sum(e["category"] == "identity" for e in trace), "explain_overhead_us": sum(e.get("explain_overhead_us",0) for e in trace), "ending": trace[-1]["query"]}
        success = True
    except Exception as error:
        receipt["failure"] = str(error)
    finally:
        if started:
            try:
                run("postgres-container-logs", ["docker", "logs", container_name], timeout=30, check=False)
                result = run("postgres-stop", ["docker", "stop", "--timeout", "5", container_name], timeout=30, check=False)
                receipt["cleanup"]["postgres_stopped"] = result.returncode == 0
                inspected = run("postgres-container-cleanup-check", ["docker", "container", "inspect", container_name], check=False)
                receipt["cleanup"]["owned_container_removed"] = inspected.returncode != 0
            except Exception as error:
                receipt["cleanup"]["postgres_stop_error"] = str(error)
        else:
            receipt["cleanup"]["postgres_started"] = False
        if (scratch / "postgres.log").exists():
            shutil.copy2(scratch / "postgres.log", output / "postgres.log")
        can_remove = not started or receipt["cleanup"].get("postgres_stopped")
        if can_remove:
            shutil.rmtree(scratch)
        receipt["cleanup"]["scratch_removed"] = not scratch.exists()
        receipt["output_sha256"] = {str(p.relative_to(output)): digest(p) for p in output.iterdir() if p.is_file() and p.name != "receipt.json"}
        receipt["live_source_changes_during_run"] = [name for name, expected in receipt.get("input_sha256", {}).items() if digest(ROOT / name) != expected]
        receipt["success"] = success and receipt["cleanup"].get("scratch_removed") and not receipt["live_source_changes_during_run"]
        success = receipt["success"]
        if (output / "exunit-result.json").exists():
            receipt["exunit_result"] = json.loads((output / "exunit-result.json").read_text())
        for name in ["full-migration-result", "lock-expiry-result"]:
            path = output / (name + ".json")
            if path.exists():
                receipt[name.replace("-", "_")] = json.loads(path.read_text())
        receipt["finished_unix"] = time.time()
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"success": success, "output": str(output), "source_tree_sha256": receipt.get("source_tree_sha256"), "failure": receipt.get("failure"), "cleanup": receipt["cleanup"]}, sort_keys=True))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
