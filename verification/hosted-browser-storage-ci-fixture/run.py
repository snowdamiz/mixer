#!/usr/bin/env python3
"""Bounded selected storage fixture and paired PG16 directory-plan collector."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "verification/hosted-browser-storage-ci-fixture"
IMAGE = "postgres@sha256:9e2cf6287f25c3151f4c9421ccce2b17f3e60061c111a29165e0d2cdd9ff0a97"
SOURCES = ["hosted/lib/mixer_hosted/browser_auth/" + name for name in
           ["storage_schema.ex", "vault.ex", "stored_snapshot.ex"]]
SOURCES += ["hosted/test/mixer_hosted/browser_auth/" + name for name in
            ["storage_fixture.exs", "storage_spec.exs"]]
SOURCES += ["hosted/priv/repo/migrations/" + name for name in
            ["20261025000003_add_customer_authorization.exs",
             "20261025000004_add_authorization_state_revisions.exs",
             "20261025000006_add_customer_workspace_discovery.exs",
             "20261025000007_add_browser_sessions.exs"]]
INPUTS = SOURCES + ["hosted/mix.exs", "hosted/mix.lock",
                   "hosted/lib/mixer_hosted/authorization/postgres/session.ex",
                   "verification/hosted-browser-storage-ci-fixture/run.py",
                   "verification/hosted-browser-storage-ci-fixture/plan_probe.exs"]
DEPS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, choices=["baseline", "fixed"])
    parser.add_argument("--plans", action="store_true")
    args = parser.parse_args()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
    out = BASE / "attempts" / (args.label + "-" + stamp)
    inputs = out / "inputs"
    inputs.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-storage-ci-fixture-"))
    container = "mixer-storage-ci-fixture-" + uuid.uuid4().hex[:12]
    env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test")
    receipt = {"schema": 1, "label": args.label,
               "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "commands": [], "cleanup": {},
               "scope": "Explicit selected storage sources and ordinary migrations3/4/6/7; one disposable PG16 Linux arm64 server. No whole-app compile, frozen lane, provider, production, native, capture or UI."}
    launched = False

    def run(name, argv, check=True, timeout=30):
        argv = [str(arg) for arg in argv]
        process = subprocess.Popen(argv, cwd=inputs, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=5)
        (out / (name + ".stdout")).write_bytes(stdout)
        (out / (name + ".stderr")).write_bytes(stderr)
        receipt["commands"].append({"name": name, "argv": argv, "cwd": str(inputs),
            "exit_code": process.returncode, "timed_out": timed_out, "timeout_seconds": timeout,
            "stdout": name + ".stdout", "stderr": name + ".stderr"})
        if check and (process.returncode or timed_out):
            raise RuntimeError(name + " failed")
        return process.returncode, stdout

    try:
        manifest = {}
        for rel in INPUTS:
            target = inputs / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, target)
            manifest[rel] = digest(target)
        receipt["source_sha256"] = manifest
        receipt["source_tree_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        paths = [ROOT / "hosted/_build/test/lib" / dep / "ebin" for dep in DEPS]
        dep_manifest = {str(p.relative_to(ROOT)): digest(p) for path in paths
                        for p in sorted(path.iterdir()) if p.is_file()}
        (out / "dependency-beams.json").write_text(json.dumps(dep_manifest, indent=2) + "\n")
        receipt["dependency_manifest_sha256"] = digest(out / "dependency-beams.json")
        _, head = run("git-head", ["git", "-C", ROOT, "rev-parse", "HEAD"])
        receipt["head"] = head.decode().strip()
        run("python-version", ["python3", "--version"])
        run("elixir-version", ["elixir", "--version"])
        run("docker-version", ["docker", "version", "--format", "{{json .Server}}"])
        run("postgres-image", ["docker", "image", "inspect", IMAGE])
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        receipt["owned_server"] = {"container": container, "image": IMAGE, "host": "127.0.0.1", "port": port}
        launched = True
        run("postgres-start", ["docker", "run", "--detach", "--rm", "--name", container,
            "--label", "mixer.fixture=storage-ci-fixture", "--publish", f"127.0.0.1:{port}:5432",
            "--env", "POSTGRES_USER=browser_admin", "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
            "--env", "POSTGRES_INITDB_ARGS=--no-locale -E UTF8", IMAGE, "-c", "timezone=UTC"])
        for i in range(60):
            code, _ = run("postgres-ready-" + str(i), ["docker", "exec", container,
                "pg_isready", "-h", "127.0.0.1", "-U", "browser_admin", "-d", "postgres"], check=False)
            if code == 0:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("owned server did not become ready")
        run("postgres-version", ["docker", "exec", container, "postgres", "--version"])
        psql = ["docker", "exec", container, "psql", "-X", "-h", "127.0.0.1", "-U", "browser_admin", "-d", "postgres", "-v", "ON_ERROR_STOP=1"]
        run("roles", psql + ["-c", "CREATE ROLE browser_schema_owner NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_writer NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_lifecycle LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_ordinary LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_operator LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;"])

        def databases(prefix):
            for database, owner in [("browser_storage", "browser_schema_owner"), ("browser_operator_storage", "browser_operator")]:
                run(prefix + database, ["docker", "exec", container, "createdb", "-h", "127.0.0.1", "-U", "browser_admin", "-O", owner, database])

        databases("create-")
        env["MIXER_BROWSER_STORAGE_PORT"] = str(port)
        env["MIXER_STORAGE_PLAN_OUTPUT"] = str(out)
        codepaths = [arg for path in paths for arg in ["-pa", path]]
        require = [arg for rel in SOURCES[:3] for arg in ["-r", inputs / rel]]
        spec = inputs / "hosted/test/mixer_hosted/browser_auth/storage_spec.exs"
        runner = out / "selected_runner.exs"
        expected = 23 if args.label == "baseline" else 24
        runner.write_text('ExUnit.start(autorun: false, seed: 0, max_cases: 1)\nCode.require_file(' + json.dumps(str(spec)) + ')\nr=ExUnit.run()\nFile.write!(' + json.dumps(str(out / "result.json")) + ',Jason.encode!(r))\nSystem.halt(if r.total==' + str(expected) + ' and r.failures==0 and r.skipped==0 and r.excluded==0 and Map.get(r,:invalid,0)==0, do: 0, else: 1)\n')
        code, _ = run("selected-tests", ["elixir", *codepaths, *require, runner], check=False, timeout=60)
        receipt["selected_exit_code"] = code
        if (out / "result.json").exists():
            receipt["tests"] = json.loads((out / "result.json").read_text())
        receipt["selected_passed"] = code == 0
        if args.plans:
            # Only these two owned synthetic databases are retired and recreated.
            for database in ["browser_storage", "browser_operator_storage"]:
                run("drop-" + database, ["docker", "exec", container, "dropdb", "-h", "127.0.0.1", "-U", "browser_admin", "--force", database])
            databases("plan-create-")
            run("paired-plans", ["elixir", *codepaths, *require,
                inputs / "verification/hosted-browser-storage-ci-fixture/plan_probe.exs"], timeout=30)
            receipt["paired_plans"] = json.loads((out / "plan-summary.json").read_text())
    except Exception as error:
        receipt["failure"] = str(error)
    finally:
        if launched:
            run("postgres-logs", ["docker", "logs", container], check=False)
            code, _ = run("postgres-stop", ["docker", "stop", "--timeout", "5", container], check=False)
            receipt["cleanup"]["owned_postgres_stopped"] = code == 0
            code, _ = run("postgres-removed", ["docker", "container", "inspect", container], check=False)
            receipt["cleanup"]["owned_container_removed"] = code != 0
        else:
            receipt["cleanup"]["owned_container_removed"] = True
        if receipt["cleanup"]["owned_container_removed"]:
            shutil.rmtree(scratch)
        receipt["cleanup"]["owned_scratch_removed"] = not scratch.exists()
        receipt["source_changes_during_run"] = [rel for rel, expected in receipt.get("source_sha256", {}).items() if digest(ROOT / rel) != expected]
        receipt["outputs_sha256"] = {str(p.relative_to(out)): digest(p) for p in sorted(out.iterdir()) if p.is_file()}
        receipt["collection_complete"] = not receipt.get("failure") and all(receipt["cleanup"].values()) and not receipt["source_changes_during_run"]
        receipt["success"] = receipt["collection_complete"] and receipt.get("selected_passed", False)
        receipt["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(str(out.relative_to(ROOT)))
        print(json.dumps({k: receipt.get(k) for k in ["collection_complete", "success", "failure", "tests", "cleanup"]}))
    return 0 if receipt["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
