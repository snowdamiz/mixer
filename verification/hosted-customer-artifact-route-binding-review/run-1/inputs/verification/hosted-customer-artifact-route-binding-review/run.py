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
    "hosted/lib/mixer_hosted/authorization/artifact_read.ex",
    "hosted/lib/mixer_hosted/protocol/artifact_cbor.ex",
    "hosted/lib/mixer_hosted/protocol/artifact_json.ex",
    "hosted/lib/mixer_hosted/protocol/artifact_v3_policy.ex",
    "hosted/lib/mixer_hosted/protocol/artifact_admission.ex",
    "hosted/lib/mixer_hosted/audit/customer_artifact_event.ex",
    "hosted/lib/mixer_hosted/customer_artifacts/schema.ex",
    "hosted/lib/mixer_hosted/customer_artifacts/topology.ex",
    "hosted/lib/mixer_hosted/customer_artifacts/postgres_storage.ex",
    "hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs",
    "hosted/priv/repo/migrations/20261025000004_add_authorization_state_revisions.exs",
    "hosted/priv/repo/migrations/20261025000005_add_customer_artifact_storage.exs",
]
TEST = "hosted/test/mixer_hosted/customer_artifacts_test.exs"
DEPS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    output.relative_to(ROOT / "verification/hosted-customer-artifact-route-binding-review")
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test")
    receipt = {"source_revision": args.source_revision, "revision_provenance": "reviewer-supplied current HEAD; copied exact source and original plus independent tests", "commands": [], "scope": "independent seven-group upload_at route-boundary review plus original facade regression suite on fresh disposable PostgreSQL; no HTTP, provider or deployment", "platform": platform.platform(), "started_unix": time.time(), "cleanup": {}}
    scratch = Path(tempfile.mkdtemp(prefix="mixer-artifact-facade-"))
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
        inputs = SOURCES + ["services/protocol/testdata/signed-release-v3.json", TEST, "hosted/mix.exs", "hosted/mix.lock", "verification/hosted-customer-artifact-route-binding/run.py", "verification/hosted-customer-artifact-route-binding/README.md"]
        inputs += ["verification/hosted-customer-artifact-route-binding-review/run.py", "verification/hosted-customer-artifact-route-binding-review/additional_tests.exs", "verification/hosted-customer-artifact-route-binding-review/probe_repo.exs"]
        doc = "docs/hosted-customer-artifact-facade.md"
        if (ROOT / doc).is_file():
            inputs.append(doc)
        manifest = {}
        for name in sorted(inputs):
            source = ROOT / name
            target = output / "inputs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            manifest[name] = digest(source)
        original_test = (output / "inputs" / TEST).read_text()
        if not original_test.endswith("end\n"):
            raise RuntimeError("unexpected original test module ending")
        combined = output / "inputs/hosted/test/mixer_hosted/customer_artifacts_review_combined.exs"
        probe_source = (output / "inputs/verification/hosted-customer-artifact-route-binding-review/probe_repo.exs").read_text()
        additional_source = (output / "inputs/verification/hosted-customer-artifact-route-binding-review/additional_tests.exs").read_text()
        combined.write_text(probe_source + "\n" + original_test[:-4] + "\n" + additional_source + "\nend\n")
        receipt["combined_test"] = {"path": str(combined.relative_to(output)), "sha256": digest(combined), "provenance": "verbatim probe Repo + original test module with verbatim independent tests inserted before final end"}
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
        formatted = ["hosted/lib/mixer_hosted/customer_artifacts.ex", TEST]
        run("format", ["mix", "format", "--check-formatted", *[output / "inputs" / name for name in formatted]])
        beams = scratch / "beams"
        beams.mkdir()
        codepaths = [arg for path in paths for arg in ["-pa", str(path)]]
        run("compile", ["elixirc", "--warnings-as-errors", *codepaths, "-o", beams, *[output / "inputs" / name for name in SOURCES]])
        run("postgres-init", [pg / "initdb", "-D", scratch / "pg", "-U", "facade_fixture_admin", "-A", "trust", "--no-locale", "-E", "UTF8"])
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        (scratch / "pg/postgresql.auto.conf").write_text(f"listen_addresses='127.0.0.1'\nport={port}\nunix_socket_directories='{scratch}'\nmax_connections=24\n")
        receipt["postgres_endpoint"] = {"host": "127.0.0.1", "port": port, "database": "mixer_customer_artifact_facade", "disposable": True}
        run("postgres-start", [pg / "pg_ctl", "-D", scratch / "pg", "-l", scratch / "postgres.log", "-w", "start"])
        started = True
        psql = [pg / "psql", "-h", "127.0.0.1", "-p", port, "-U", "facade_fixture_admin", "-v", "ON_ERROR_STOP=1"]
        run("roles-apply", psql + ["-d", "postgres", "-c", "CREATE ROLE facade_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; CREATE ROLE facade_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;"])
        run("database", [pg / "createdb", "-h", "127.0.0.1", "-p", port, "-U", "facade_fixture_admin", "mixer_customer_artifact_facade"])
        run("schema", psql + ["-d", "mixer_customer_artifact_facade", "-c", "REVOKE CREATE ON SCHEMA public FROM PUBLIC; ALTER SCHEMA public OWNER TO facade_owner; GRANT USAGE ON SCHEMA public TO facade_runtime;"])
        env["MIXER_ARTIFACT_FACADE_TEST_PORT"] = str(port)
        runner = scratch / "run.exs"
        runner.write_text('Application.ensure_all_started(:ecto_sql)\nApplication.ensure_all_started(:postgrex)\nExUnit.start(autorun: false, seed: 0, max_cases: 1)\nCode.require_file(' + json.dumps(str(combined)) + ')\nresult = ExUnit.run()\nSystem.halt(if result.failures == 0, do: 0, else: 1)\n')
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
        receipt["finished_unix"] = time.time()
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"success": success, "output": str(output), "source_tree_sha256": receipt.get("source_tree_sha256"), "failure": receipt.get("failure"), "cleanup": receipt["cleanup"]}, sort_keys=True))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
