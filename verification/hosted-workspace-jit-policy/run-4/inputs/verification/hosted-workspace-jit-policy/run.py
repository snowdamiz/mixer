#!/usr/bin/env python3
"""Compile explicit ordinary sources and run bounded PG16 JIT/regression suites."""
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

ROOT = Path(__file__).resolve().parents[2]
BASE = "verification/hosted-workspace-jit-policy"
SOURCES = [
    "repo.ex", "identity/encoding.ex", "identity/bounded_json.ex", "identity/verified_identity.ex",
    "authorization/scope.ex", "authorization/policy.ex", "authorization/repository.ex",
    "authorization/postgres/session.ex", "authorization/postgres/evidence.ex",
    "authorization/transaction/snapshot.ex", "authorization/transaction/context.ex",
    "authorization.ex", "authorization/artifact_read.ex", "protocol/artifact_cbor.ex",
    "protocol/artifact_json.ex", "protocol/artifact_v3_policy.ex", "protocol/artifact_admission.ex",
    "audit/customer_artifact_event.ex", "customer_artifacts/schema.ex",
    "customer_artifacts/topology.ex", "customer_artifacts/postgres_storage.ex",
    "customer_workspace.ex", "customer_workspace/input.ex", "customer_workspace/storage.ex",
]
SOURCES = ["hosted/lib/mixer_hosted/" + name for name in SOURCES] + [
    "hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs",
    "hosted/priv/repo/migrations/20261025000004_add_authorization_state_revisions.exs",
    "hosted/priv/repo/migrations/20261025000005_add_customer_artifact_storage.exs",
    "hosted/priv/repo/migrations/20261025000006_add_customer_workspace_discovery.exs",
]
SUITES = [
    ("workspace", ["hosted/test/mixer_hosted/customer_workspace_test.exs", BASE + "/workspace-probe.exs"], 24),
    ("transaction-and-jit", ["hosted/test/mixer_hosted/authorization/transaction_test.exs", "hosted/test/mixer_hosted/authorization/jit_policy_spec.exs"], 28),
    ("artifact-read", ["hosted/test/mixer_hosted/authorization/artifact_read_test.exs"], 15),
    ("artifact-storage", ["hosted/test/mixer_hosted/customer_artifacts/postgres_storage_test.exs"], 19),
]
DEPS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason"]
DATABASES = [
    ("mixer_customer_workspace", "workspace_fixture_admin", "workspace_owner", "workspace_runtime"),
    ("mixer_customer_transaction", "txn_fixture_admin", "txn_authz_owner", "txn_authz_runtime"),
    ("mixer_jit_policy", "txn_fixture_admin", "txn_authz_owner", "txn_authz_runtime"),
    ("mixer_artifact_read_scope", "read_scope_fixture_admin", "read_scope_owner", "read_scope_runtime"),
    ("mixer_customer_artifact_storage", "storage_fixture_admin", "storage_owner", "storage_runtime"),
]
IMAGE = "postgres@sha256:9e2cf6287f25c3151f4c9421ccce2b17f3e60061c111a29165e0d2cdd9ff0a97"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    output.relative_to(ROOT / BASE)
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test")
    scratch = Path(tempfile.mkdtemp(prefix="mixer-workspace-jit-policy-"))
    container = "mixer-workspace-jit-policy-" + str(os.getpid()) + "-" + str(int(time.time()))
    receipt = {"source_revision": args.source_revision,
               "revision_provenance": "supplied HEAD with exact selected input hashes; working-tree changes included",
               "scope": "selected ordinary workspace, authorization transaction, artifact read/storage and JIT controls on one disposable PostgreSQL16.15 Linux arm64 container; no broad hosted harness, frozen lanes, capture, native runtime, provider, deployment or GA qualification",
               "platform": platform.platform(), "started_unix": time.time(), "scratch": str(scratch),
               "commands": [], "cleanup": {}, "suites": {}}
    started = False
    success = False

    def run(name, argv, timeout=90, check=True):
        argv = [str(arg) for arg in argv]
        entry = {"name": name, "argv": argv, "cwd": str(output / "inputs"), "started_unix": time.time()}
        receipt["commands"].append(entry)
        try:
            result = subprocess.run(argv, cwd=output / "inputs", env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            stdout, stderr = result.stdout, result.stderr
            entry["exit_code"] = result.returncode
        except subprocess.TimeoutExpired as error:
            stdout, stderr = error.stdout or b"", error.stderr or b""
            entry["timed_out_seconds"] = timeout
            entry["exit_code"] = None
            raise
        finally:
            (output / (name + ".stdout")).write_bytes(stdout)
            (output / (name + ".stderr")).write_bytes(stderr)
            entry["stdout"] = name + ".stdout"
            entry["stderr"] = name + ".stderr"
            entry["finished_unix"] = time.time()
        if check and result.returncode:
            raise RuntimeError(f"{name} failed ({result.returncode})")
        return result

    try:
        inputs = SOURCES + [name for _, files, _ in SUITES for name in files] + [
            "services/protocol/testdata/signed-release-v3.json", "hosted/mix.exs", "hosted/mix.lock",
            BASE + "/run.py", "docs/hosted-workspace-jit-policy.md"]
        manifest = {}
        for name in sorted(set(inputs)):
            source = ROOT / name
            target = output / "inputs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            manifest[name] = digest(target)
        receipt["input_sha256"] = manifest
        receipt["source_tree_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        paths = [ROOT / "hosted/_build/test/lib" / dep / "ebin" for dep in DEPS]
        deps = {str(beam.relative_to(ROOT)): digest(beam) for path in paths for beam in sorted(path.iterdir()) if beam.is_file()}
        (output / "dependency-beams.json").write_text(json.dumps(deps, indent=2, sort_keys=True) + "\n")
        receipt["dependency_manifest_sha256"] = digest(output / "dependency-beams.json")
        run("elixir-version", ["elixir", "--version"])
        run("python-version", ["python3", "--version"])
        pg = Path(run("postgres-bindir", ["pg_config", "--bindir"]).stdout.decode().strip())
        run("postgres-client-version", [pg / "psql", "--version"])
        formatted = ["hosted/lib/mixer_hosted/authorization/postgres/session.ex",
                     "hosted/test/mixer_hosted/authorization/jit_policy_spec.exs", BASE + "/workspace-probe.exs"]
        run("format", ["mix", "format", "--check-formatted", *[output / "inputs" / name for name in formatted]])
        beams = scratch / "beams"
        beams.mkdir()
        codepaths = [arg for path in paths for arg in ["-pa", str(path)]]
        run("compile", ["elixirc", "--warnings-as-errors", *codepaths, "-o", beams,
                        *[output / "inputs" / name for name in SOURCES]])
        run("docker-version", ["docker", "version", "--format", "{{json .Server}}"])
        run("postgres-image", ["docker", "image", "inspect", IMAGE, "--format", "{{json .}}"], timeout=30)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        receipt["postgres_endpoint"] = {"host": "127.0.0.1", "port": port, "disposable": True, "container": container, "image": IMAGE}
        run("postgres-start", ["docker", "run", "--detach", "--rm", "--name", container,
                              "--label", "mixer.fixture=workspace-jit-policy", "--publish", f"127.0.0.1:{port}:5432",
                              "--env", "POSTGRES_USER=jit_fixture_admin", "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
                              "--env", "POSTGRES_INITDB_ARGS=--no-locale -E UTF8", IMAGE, "-c", "max_connections=36"])
        started = True
        for attempt in range(100):
            if run("postgres-ready-" + str(attempt), [pg / "pg_isready", "-h", "127.0.0.1", "-p", port,
                                                    "-U", "jit_fixture_admin"], check=False).returncode == 0:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("owned PostgreSQL16 did not become ready")
        run("postgres-server-version", ["docker", "exec", container, "postgres", "--version"])
        psql = [pg / "psql", "-h", "127.0.0.1", "-p", port, "-U", "jit_fixture_admin", "-v", "ON_ERROR_STOP=1"]
        roles = []
        seen = set()
        for _, admin, owner, runtime in DATABASES:
            if admin in seen:
                continue
            seen.add(admin)
            roles += [f"CREATE ROLE {admin} LOGIN SUPERUSER", f"CREATE ROLE {owner} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS", f"CREATE ROLE {runtime} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"]
        run("roles", psql + ["-d", "postgres", "-c", ";".join(roles)])
        for database, _, owner, runtime in DATABASES:
            run(database + "-create", [pg / "createdb", "-h", "127.0.0.1", "-p", port, "-U", "jit_fixture_admin", database])
            run(database + "-schema", psql + ["-d", database, "-c", f"REVOKE CREATE ON SCHEMA public FROM PUBLIC; ALTER SCHEMA public OWNER TO {owner}; GRANT USAGE ON SCHEMA public TO {runtime}"])
        for key in ["MIXER_WORKSPACE_TEST_PORT", "MIXER_TRANSACTION_TEST_PORT", "MIXER_ARTIFACT_READ_SCOPE_TEST_PORT", "MIXER_ARTIFACT_STORAGE_TEST_PORT"]:
            env[key] = str(port)
        env["MIXER_JIT_POLICY_SETTINGS_RESULT"] = str(output / "settings-results.jsonl")
        env["MIXER_JIT_POLICY_PROBE_DIR"] = str(output)
        env["MIXER_WORKSPACE_LOCK_EXPIRY_RESULT"] = str(output / "workspace-lock-expiry-result.json")
        env["MIXER_WORKSPACE_MIGRATION_RESULT"] = str(output / "workspace-migration-result.json")
        for name, files, total in SUITES:
            result_path = output / (name + "-result.json")
            runner = scratch / (name + ".exs")
            runner.write_text('Application.ensure_all_started(:ecto_sql)\nApplication.ensure_all_started(:postgrex)\nLogger.configure(level: :warning)\nExUnit.start(autorun: false, seed: 0, max_cases: 1)\n' +
                              ''.join('Code.require_file(' + json.dumps(str(output / "inputs" / file)) + ')\n' for file in files) +
                              'result = ExUnit.run()\nFile.write!(' + json.dumps(str(result_path)) + ', Jason.encode!(result))\n' +
                              f'System.halt(if result.failures == 0 and result.total == {total} and result.skipped == 0 and result.excluded == 0, do: 0, else: 1)\n')
            shutil.copy2(runner, output / (name + "-runner.exs"))
            run(name + "-tests", ["elixir", *codepaths, "-pa", beams, runner], timeout=120)
            receipt["suites"][name] = json.loads(result_path.read_text())
            if "has failed and has been detached" in (output / (name + "-tests.stderr")).read_text():
                raise RuntimeError("observer detached in " + name)
        plan = json.loads((output / "workspace-organization-plan.json").read_text())
        if plan["effective_jit"] != "off" or any("JIT" in element for element in plan["plan"]):
            raise RuntimeError("actual workspace owner JIT policy not verified")
        events = [json.loads(line) for line in (output / "workspace-first-transaction.jsonl").read_text().splitlines()]
        if events[-1]["query"].lower() != "commit":
            raise RuntimeError("observed workspace transaction did not commit")
        receipt["workspace_observer"] = {"organization_query_us": plan["query_us"], "effective_jit": plan["effective_jit"],
                                          "plan_has_jit": False, "transaction_events": len(events), "ending": events[-1]["query"]}
        success = True
    except Exception as error:
        receipt["failure"] = str(error)
    finally:
        if started:
            try:
                run("postgres-logs", ["docker", "logs", container], timeout=30, check=False)
                stopped = run("postgres-stop", ["docker", "stop", "--timeout", "5", container], timeout=30, check=False)
                receipt["cleanup"]["postgres_stopped"] = stopped.returncode == 0
                removed = run("postgres-removed", ["docker", "container", "inspect", container], timeout=30, check=False)
                receipt["cleanup"]["owned_container_removed"] = removed.returncode != 0
            except Exception as error:
                receipt["cleanup"]["error"] = str(error)
        else:
            receipt["cleanup"]["postgres_started"] = False
        if not started or receipt["cleanup"].get("owned_container_removed"):
            shutil.rmtree(scratch)
        receipt["cleanup"]["scratch_removed"] = not scratch.exists()
        receipt["live_source_changes_during_run"] = [name for name, expected in receipt.get("input_sha256", {}).items() if digest(ROOT / name) != expected]
        receipt["output_sha256"] = {str(p.relative_to(output)): digest(p) for p in sorted(output.iterdir()) if p.is_file() and p.name != "receipt.json"}
        receipt["finished_unix"] = time.time()
        receipt["success"] = success and receipt["cleanup"].get("owned_container_removed", not started) and receipt["cleanup"]["scratch_removed"] and not receipt["live_source_changes_during_run"]
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: receipt.get(key) for key in ["success", "failure", "source_tree_sha256", "suites", "workspace_observer", "cleanup"]}, sort_keys=True))
    return 0 if receipt["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
