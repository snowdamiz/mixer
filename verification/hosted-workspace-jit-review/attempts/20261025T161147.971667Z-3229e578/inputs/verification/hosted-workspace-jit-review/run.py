#!/usr/bin/env python3
"""Independent Session-only checks on one owned disposable PostgreSQL16 server."""
from pathlib import Path
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
BASE = ROOT / "verification/hosted-workspace-jit-review"
IMAGE = "postgres@sha256:9e2cf6287f25c3151f4c9421ccce2b17f3e60061c111a29165e0d2cdd9ff0a97"
SOURCES = ["hosted/lib/mixer_hosted/authorization/postgres/session.ex",
           "hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs",
           "hosted/priv/repo/migrations/20261025000004_add_authorization_state_revisions.exs"]
INPUTS = SOURCES + ["hosted/mix.exs", "hosted/mix.lock",
                   "verification/hosted-workspace-jit-review/run.py",
                   "verification/hosted-workspace-jit-review/independent_spec.exs"]
DEPS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason"]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
    out = BASE / "attempts" / stamp
    out.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-jit-independent-"))
    container = "mixer-jit-independent-" + uuid.uuid4().hex[:12]
    env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test")
    receipt = {"schema": 1, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "commands": [], "cleanup": {}, "scope": "Independent Session-only six-group restricted-login PostgreSQL16 review; no broad harness/frozen lane/provider/native/capture/production action."}
    launched = False
    success = False

    def run(name, argv, check=True, timeout=30):
        argv = [str(arg) for arg in argv]
        process = subprocess.Popen(argv, cwd=out / "inputs", env=env, stdout=subprocess.PIPE,
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
        receipt["commands"].append({"name": name, "argv": argv, "cwd": str(out / "inputs"),
            "exit_code": process.returncode, "timed_out": timed_out, "timeout_seconds": timeout,
            "stdout": name + ".stdout", "stderr": name + ".stderr"})
        if check and (process.returncode or timed_out):
            raise RuntimeError(name + " failed")
        return process.returncode, stdout

    try:
        manifest = {}
        for rel in INPUTS:
            target = out / "inputs" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, target)
            manifest[rel] = digest(target)
        receipt["source_sha256"] = manifest
        receipt["source_tree_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        paths = [ROOT / "hosted/_build/test/lib" / dep / "ebin" for dep in DEPS]
        dep_manifest = {str(p.relative_to(ROOT)): digest(p) for path in paths for p in sorted(path.iterdir()) if p.is_file()}
        (out / "dependency-beams.json").write_text(json.dumps(dep_manifest, indent=2) + "\n")
        receipt["dependency_manifest_sha256"] = digest(out / "dependency-beams.json")
        _, head = run("git-head", ["git", "-C", ROOT, "rev-parse", "HEAD"])
        receipt["head"] = head.decode().strip()
        run("python-version", ["python3", "--version"])
        run("elixir-version", ["elixir", "--version"])
        run("docker-version", ["docker", "version", "--format", "{{json .Server}}"])
        run("postgres-image", ["docker", "image", "inspect", IMAGE])
        beams = scratch / "beams"
        beams.mkdir()
        codepaths = [arg for path in paths for arg in ["-pa", path]]
        run("compile", ["elixirc", "--warnings-as-errors", *codepaths, "-o", beams,
                        *[out / "inputs" / rel for rel in SOURCES]])
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        receipt["owned_server"] = {"container": container, "image": IMAGE, "host": "127.0.0.1", "port": port}
        launched = True
        run("postgres-start", ["docker", "run", "--detach", "--rm", "--name", container,
            "--label", "mixer.fixture=jit-independent", "--publish", f"127.0.0.1:{port}:5432",
            "--env", "POSTGRES_USER=jit_review_admin", "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
            "--env", "POSTGRES_INITDB_ARGS=--no-locale -E UTF8", IMAGE, "-c", "max_connections=16"])
        for i in range(60):
            code, _ = run("postgres-ready-" + str(i), ["docker", "exec", container,
                "pg_isready", "-U", "jit_review_admin"], check=False)
            if code == 0:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("owned server did not become ready")
        run("postgres-version", ["docker", "exec", container, "postgres", "--version"])
        psql = ["docker", "exec", container, "psql", "-X", "-U", "jit_review_admin", "-v", "ON_ERROR_STOP=1"]
        run("roles", psql + ["-d", "postgres", "-c", "CREATE ROLE jit_review_owner NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE NOREPLICATION; CREATE ROLE jit_review_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEDB NOCREATEROLE NOREPLICATION;"])
        run("database", ["docker", "exec", container, "createdb", "-U", "jit_review_admin", "mixer_jit_review"])
        run("schema", psql + ["-d", "mixer_jit_review", "-c", "REVOKE CREATE ON SCHEMA public FROM PUBLIC; ALTER SCHEMA public OWNER TO jit_review_owner; GRANT USAGE ON SCHEMA public TO jit_review_runtime;"])
        env["JIT_REVIEW_PORT"] = str(port)
        env["JIT_REVIEW_SETTINGS"] = str(out / "settings.jsonl")
        runner = scratch / "run.exs"
        runner.write_text('Application.ensure_all_started(:ecto_sql)\nApplication.ensure_all_started(:postgrex)\nApplication.ensure_all_started(:jason)\nLogger.configure(level: :warning)\nExUnit.start(autorun: false, seed: 0, max_cases: 1)\nCode.require_file(' + json.dumps(str(out / "inputs/verification/hosted-workspace-jit-review/independent_spec.exs")) + ')\nr=ExUnit.run()\nFile.write!(' + json.dumps(str(out / "result.json")) + ',Jason.encode!(r))\nSystem.halt(if r.total==6 and r.failures==0 and r.skipped==0 and r.excluded==0, do: 0, else: 1)\n')
        shutil.copy2(runner, out / "runner.exs")
        run("independent-tests", ["elixir", *codepaths, "-pa", beams, runner], timeout=60)
        receipt["tests"] = json.loads((out / "result.json").read_text())
        success = True
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
        receipt["success"] = success and all(receipt["cleanup"].values()) and not receipt["source_changes_during_run"]
        receipt["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(str(out.relative_to(ROOT)))
        print(json.dumps({k: receipt.get(k) for k in ["success", "failure", "tests", "cleanup"]}))
    return 0 if receipt["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
