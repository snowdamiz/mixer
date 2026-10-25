#!/usr/bin/env python3
"""Selected ordinary-source collector; no shared harness, Git or frozen lanes."""
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
    "hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs",
    "hosted/priv/repo/migrations/20261025000004_add_authorization_state_revisions.exs",
    "hosted/priv/repo/migrations/20261025000006_add_customer_workspace_discovery.exs",
]
TEST = "hosted/test/mixer_hosted/customer_workspace_test.exs"
DEPS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    output.relative_to(ROOT / "verification/hosted-customer-workspace-storage")
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test")
    receipt = {"source_revision": args.source_revision, "revision_provenance": "root-supplied current HEAD; copied input tree records uncommitted source", "commands": [], "scope": "Customer workspace discovery against restricted runtime PostgreSQL; selected-row locking, strict cursors, names and identity checks. Host-only synthetic database; no production identity/provider, Neon/Cloudflare, lifecycle writer, native/device/store or GA acceptance.", "platform": platform.platform(), "started_unix": time.time(), "cleanup": {}}
    scratch = Path(tempfile.mkdtemp(prefix="mixer-customer-workspace-"))
    receipt["scratch"] = str(scratch)
    started = False
    success = False

    def run(name, command, *, timeout=90, check=True):
        result = subprocess.run([str(x) for x in command], cwd=output / "inputs", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout, text=True)
        (output / (name + ".log")).write_text(result.stdout)
        receipt["commands"].append({"name": name, "argv": [str(x) for x in command], "exit_code": result.returncode, "output": name + ".log"})
        if check and result.returncode:
            raise RuntimeError(f"{name} failed ({result.returncode}); see preserved log")
        return result

    try:
        inputs = SOURCES + [TEST, "hosted/mix.exs", "hosted/mix.lock", "verification/hosted-customer-workspace-storage/run.py", "docs/hosted-customer-workspace-storage.md"]
        doc = "docs/hosted-customer-workspace-storage.md"
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
        formatted = [name for name in SOURCES if "customer_workspace" in name] + [TEST]
        run("format", ["mix", "format", "--check-formatted", *[output / "inputs" / name for name in formatted]])
        beams = scratch / "beams"
        beams.mkdir()
        codepaths = [arg for path in paths for arg in ["-pa", str(path)]]
        run("compile", ["elixirc", "--warnings-as-errors", *codepaths, "-o", beams, *[output / "inputs" / name for name in SOURCES]])
        run("postgres-init", [pg / "initdb", "-D", scratch / "pg", "-U", "workspace_fixture_admin", "-A", "trust", "--no-locale", "-E", "UTF8"])
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        (scratch / "pg/postgresql.auto.conf").write_text(f"listen_addresses='127.0.0.1'\nport={port}\nunix_socket_directories='{scratch}'\nmax_connections=24\n")
        receipt["postgres_endpoint"] = {"host": "127.0.0.1", "port": port, "database": "mixer_customer_workspace", "disposable": True}
        run("postgres-start", [pg / "pg_ctl", "-D", scratch / "pg", "-l", scratch / "postgres.log", "-w", "start"])
        started = True
        psql = [pg / "psql", "-h", "127.0.0.1", "-p", port, "-U", "workspace_fixture_admin", "-v", "ON_ERROR_STOP=1"]
        run("roles-apply", psql + ["-d", "postgres", "-c", "CREATE ROLE workspace_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; CREATE ROLE workspace_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;"])
        run("database", [pg / "createdb", "-h", "127.0.0.1", "-p", port, "-U", "workspace_fixture_admin", "mixer_customer_workspace"])
        run("schema", psql + ["-d", "mixer_customer_workspace", "-c", "REVOKE CREATE ON SCHEMA public FROM PUBLIC; ALTER SCHEMA public OWNER TO workspace_owner; GRANT USAGE ON SCHEMA public TO workspace_runtime;"])
        env["MIXER_WORKSPACE_TEST_PORT"] = str(port)
        env["MIXER_WORKSPACE_EXUNIT_RESULT"] = str(output / "exunit-result.json")
        env["MIXER_WORKSPACE_MIGRATION_RESULT"] = str(output / "migration-result.json")
        runner = scratch / "run.exs"
        runner.write_text('Application.ensure_all_started(:ecto_sql)\nApplication.ensure_all_started(:postgrex)\nExUnit.start(autorun: false, seed: 0, max_cases: 1)\nCode.require_file(' + json.dumps(str(output / "inputs" / TEST)) + ')\nresult = ExUnit.run()\nFile.write!(System.fetch_env!("MIXER_WORKSPACE_EXUNIT_RESULT"), Jason.encode!(result))\nSystem.halt(if result.failures == 0 and result.total == 24 and result.skipped == 0 and result.excluded == 0, do: 0, else: 1)\n')
        run("tests", ["elixir", *codepaths, "-pa", beams, runner], timeout=120)
        success = True
    except Exception as error:
        receipt["failure"] = str(error)
    finally:
        if started:
            try:
                result = run("postgres-stop", [pg / "pg_ctl", "-D", scratch / "pg", "-m", "immediate", "-w", "stop"], timeout=30, check=False)
                receipt["cleanup"]["postgres_stopped"] = result.returncode == 0
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
        receipt["output_sha256"] = {str(p.relative_to(output)): digest(p) for p in output.glob("*.log")}
        receipt["live_source_changes_during_run"] = [name for name, expected in receipt.get("input_sha256", {}).items() if digest(ROOT / name) != expected]
        receipt["success"] = success and receipt["cleanup"].get("scratch_removed") and not receipt["live_source_changes_during_run"]
        success = receipt["success"]
        if (output / "exunit-result.json").exists():
            receipt["exunit_result"] = json.loads((output / "exunit-result.json").read_text())
        receipt["finished_unix"] = time.time()
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"success": success, "output": str(output), "source_tree_sha256": receipt.get("source_tree_sha256"), "failure": receipt.get("failure"), "cleanup": receipt["cleanup"]}, sort_keys=True))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
