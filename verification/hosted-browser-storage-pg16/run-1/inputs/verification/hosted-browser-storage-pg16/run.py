#!/usr/bin/env python3
"""Independent frozen browser-storage compatibility fixture on one owned PG16 container."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = Path("verification/hosted-browser-storage-pg16")
SOURCES = ["hosted/lib/mixer_hosted/browser_auth/" + name for name in ["storage_schema.ex", "vault.ex", "stored_snapshot.ex"]]
TESTS = ["hosted/test/mixer_hosted/browser_auth/" + name for name in ["storage_fixture.exs", "storage_spec.exs"]]
MIGRATIONS = ["hosted/priv/repo/migrations/" + name for name in [
    "20261025000003_add_customer_authorization.exs", "20261025000004_add_authorization_state_revisions.exs",
    "20261025000006_add_customer_workspace_discovery.exs", "20261025000007_add_browser_sessions.exs"]]
DEPS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason"]
FROZEN = {
    SOURCES[0]: "676bb977bbe4c322caf63c1a5f40d86e7861847636029948b55cb01f6dedb6dd",
    TESTS[1]: "2d7202653bff248341c94f33d00dbc67fe5a91c137057695578a1bbc5ba52736",
}
IMAGE = "postgres@sha256:9e2cf6287f25c3151f4c9421ccce2b17f3e60061c111a29165e0d2cdd9ff0a97"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    out = (ROOT / BASE / args.attempt).resolve()
    out.relative_to(ROOT / BASE)
    out.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-browser-storage-pg16-"))
    container = "mixer-browser-storage-pg16-" + str(os.getpid()) + "-" + str(int(time.time()))
    env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test")
    receipt = {"status": "failed", "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "platform": platform.platform(), "commands": [], "cleanup": {}, "scratch": str(scratch),
               "scope": "frozen StorageSchema/Vault/StoredSnapshot, existing storage_fixture/storage_spec and ordinary migrations3/4/6/7 against seven explicit locked dependency BEAM paths excluding mixer_hosted; one disposable PostgreSQL16.15 Linux arm64 container; compatibility fixture only, no new security audit or whole-app harness, frozen lanes, provider, native or capture actions"}
    attempted = False

    def run(name, argv, timeout=60, check=True):
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
                                    "exit_code": process.returncode, "timeout_seconds": timeout,
                                    "timed_out": timed_out, "stdout": name + ".stdout", "stderr": name + ".stderr"})
        if check and (process.returncode or timed_out):
            raise RuntimeError(name + " failed")
        return process.returncode, stdout

    try:
        for name, expected in FROZEN.items():
            if sha(ROOT / name) != expected:
                raise RuntimeError("frozen source mismatch: " + name)
        paths = SOURCES + TESTS + MIGRATIONS + [str(BASE / "run.py"), "hosted/mix.exs", "hosted/mix.lock"]
        manifest = {}
        for name in paths:
            target = out / "inputs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
            manifest[name] = sha(target)
        receipt["input_sha256"] = manifest
        receipt["source_tree_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        deps = [ROOT / "hosted/_build/test/lib" / dep / "ebin" for dep in DEPS]
        dependency_manifest = {str(path.relative_to(ROOT)): sha(path) for dep in deps for path in sorted(dep.iterdir()) if path.is_file()}
        (out / "dependency-beams.json").write_text(json.dumps(dependency_manifest, indent=2, sort_keys=True) + "\n")
        receipt["dependency_manifest_sha256"] = sha(out / "dependency-beams.json")
        receipt["dependency_dirs"] = [str(dep.relative_to(ROOT)) for dep in deps]
        receipt["mixer_hosted_beams_excluded"] = all(dep.parent.name != "mixer_hosted" for dep in deps)
        _, head = run("git-head", ["git", "rev-parse", "HEAD"])
        receipt["source_revision"] = head.decode().strip()
        run("elixir-version", ["elixir", "--version"])
        run("python-version", ["python3", "--version"])
        _, pg_bin = run("postgres-bindir", ["pg_config", "--bindir"])
        pg = Path(pg_bin.decode().strip())
        run("postgres-client-version", [pg / "psql", "--version"])
        run("docker-version", ["docker", "version", "--format", "{{json .Server}}"])
        _, image = run("postgres-image-inspect", ["docker", "image", "inspect", IMAGE, "--format", "{{json .}}"])
        image_data = json.loads(image)
        receipt["postgres_image"] = {key: image_data[key] for key in ["Id", "RepoDigests", "Architecture", "Os"]}
        beams = scratch / "beams"
        beams.mkdir()
        codepaths = [arg for dep in deps for arg in ["-pa", str(dep)]]
        run("compile", ["elixirc", "--warnings-as-errors", *codepaths, "-o", beams, *[out / "inputs" / name for name in SOURCES]])
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        receipt["postgres_endpoint"] = {"host": "127.0.0.1", "port": port, "owned_container": container, "disposable": True}
        attempted = True
        run("postgres-start", ["docker", "run", "--detach", "--rm", "--name", container,
                              "--label", "mixer.fixture=browser-storage-pg16", "--publish", f"127.0.0.1:{port}:5432",
                              "--env", "POSTGRES_USER=browser_admin", "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
                              "--env", "POSTGRES_INITDB_ARGS=--no-locale -E UTF8", IMAGE,
                              "-c", "max_connections=36", "-c", "timezone=UTC"])
        for attempt in range(100):
            code, _ = run("postgres-ready-" + str(attempt), [pg / "pg_isready", "-h", "127.0.0.1", "-p", port, "-U", "browser_admin"], check=False)
            if code == 0:
                break
            time.sleep(0.1)
        else:
            raise RuntimeError("owned PostgreSQL16 did not become ready")
        _, version = run("postgres-server-version", ["docker", "exec", container, "postgres", "--version"])
        receipt["postgres_server_version"] = version.decode().strip()
        if receipt["postgres_server_version"] != "postgres (PostgreSQL) 16.15 (Debian 16.15-1.pgdg13+1)":
            raise RuntimeError("unexpected pinned PostgreSQL version")
        psql = [pg / "psql", "-X", "-h", "127.0.0.1", "-p", port, "-U", "browser_admin", "-d", "postgres", "-v", "ON_ERROR_STOP=1"]
        roles = "CREATE ROLE browser_schema_owner NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_writer NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_lifecycle LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_ordinary LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT; CREATE ROLE browser_operator LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;"
        run("fixture-roles", psql + ["-c", roles])
        for database, owner in [("browser_storage", "browser_schema_owner"), ("browser_operator_storage", "browser_operator")]:
            run(database + "-create", [pg / "createdb", "-h", "127.0.0.1", "-p", port, "-U", "browser_admin", "-O", owner, database])
        env["MIXER_BROWSER_STORAGE_PORT"] = str(port)
        runner = out / "selected-runner.exs"
        runner.write_text('Logger.configure(level: :warning)\nExUnit.start(autorun: false, seed: 0, max_cases: 1)\nCode.require_file(' + json.dumps(str(out / "inputs" / TESTS[1])) + ')\nresult = ExUnit.run()\nFile.write!(' + json.dumps(str(out / "test-result.json")) + ', Jason.encode!(result))\nSystem.halt(if result.total == 23 and result.failures == 0 and result.excluded == 0 and result.skipped == 0, do: 0, else: 1)\n')
        run("selected-tests", ["elixir", *codepaths, "-pa", beams, runner], timeout=120)
        receipt["selected_result"] = json.loads((out / "test-result.json").read_text())
        receipt["status"] = "passed"
    except Exception as error:
        receipt["failure"] = str(error)
    finally:
        if attempted:
            try:
                run("postgres-logs", ["docker", "logs", container], timeout=30, check=False)
                code, _ = run("postgres-container-state", ["docker", "container", "inspect", container], timeout=30, check=False)
                if code == 0:
                    code, _ = run("postgres-stop", ["docker", "stop", "--timeout", "5", container], timeout=30, check=False)
                    receipt["cleanup"]["owned_postgres_stopped"] = code == 0
                else:
                    receipt["cleanup"]["owned_postgres_stopped"] = True
                code, _ = run("postgres-removed", ["docker", "container", "inspect", container], timeout=30, check=False)
                receipt["cleanup"]["owned_container_removed"] = code != 0
            except Exception as error:
                receipt["cleanup"]["error"] = str(error)
        else:
            receipt["cleanup"]["owned_postgres_started"] = False
        if not attempted or receipt["cleanup"].get("owned_container_removed"):
            shutil.rmtree(scratch)
        receipt["cleanup"]["owned_scratch_removed"] = not scratch.exists()
        after = {name: sha(ROOT / name) for name in receipt.get("input_sha256", {})}
        receipt["source_unchanged"] = after == receipt.get("input_sha256", {})
        (out / "source-manifest-after.json").write_text(json.dumps(after, indent=2, sort_keys=True) + "\n")
        receipt["dependency_beams_unchanged"] = all(sha(ROOT / name) == expected for name, expected in locals().get("dependency_manifest", {}).items())
        if not receipt["source_unchanged"] or not receipt["dependency_beams_unchanged"] or not receipt["cleanup"]["owned_scratch_removed"] or (attempted and not receipt["cleanup"].get("owned_container_removed")):
            receipt["status"] = "failed"
        receipt["output_sha256"] = {str(path.relative_to(out)): sha(path) for path in sorted(out.iterdir()) if path.is_file() and path.name != "receipt.json"}
        receipt["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: receipt.get(key) for key in ["status", "failure", "selected_result", "postgres_server_version", "source_tree_sha256", "source_unchanged", "cleanup"]}, sort_keys=True))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
