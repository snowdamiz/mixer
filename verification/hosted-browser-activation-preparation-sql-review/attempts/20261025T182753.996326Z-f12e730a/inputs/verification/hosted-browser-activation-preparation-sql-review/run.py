#!/usr/bin/env python3
"""Independent activation-preparation SQL review on one owned PostgreSQL16 container."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
IMAGE = "postgres@sha256:9e2cf6287f25c3151f4c9421ccce2b17f3e60061c111a29165e0d2cdd9ff0a97"
SOURCES = ["hosted/lib/mixer_hosted/browser_auth/" + n for n in
           ["storage_schema.ex", "catalog_manifest.ex", "catalog.ex", "activation_preparation_schema.ex", "vault.ex", "stored_snapshot.ex", "activation_preparation.ex"]]
SOURCES += ["hosted/lib/mixer_hosted/identity/encoding.ex", "hosted/lib/mixer_hosted/identity/access_token_verifier.ex", "hosted/test/mixer_hosted/browser_auth/storage_fixture.exs", "docs/hosted-browser-activation-preparation-sql.md", "docs/hosted-browser-lifecycle-runtime-contract.md"]
SOURCES += ["hosted/priv/repo/migrations/" + n for n in
            ["20261025000003_add_customer_authorization.exs",
             "20261025000004_add_authorization_state_revisions.exs",
             "20261025000006_add_customer_workspace_discovery.exs",
             "20261025000007_add_browser_sessions.exs"]]
SOURCES += ["hosted/mix.lock", "verification/hosted-browser-activation-preparation-sql-review/run.py",
            "verification/hosted-browser-activation-preparation-sql-review/review.exs"]
DEPS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason"]
EXPECTED = 34


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
    out = BASE / "attempts" / stamp
    inputs = out / "inputs"
    inputs.mkdir(parents=True)
    name = "mixer-preparation-sql-review-" + uuid.uuid4().hex[:12]
    receipt = {"schema": 1, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "commands": [], "cleanup": {}, "independent_test_oracle": True,
               "reused_fixture": "Existing storage_fixture.exs installation/provisioning only, not independent fixture reimplementation.",
               "scope": "ActivationPreparationSchema additive SQL only; independently authored raw SQL adversity tests; explicit ordinary sources/dependency beams; one synthetic loopback PostgreSQL16. No full-app compile/discovery, frozen catalog inspector/authority driver/WorkerV2, readiness/Store/provider/production/native/UI/capture/phone execution.",
               "pending": ["Full relation, constraint, index, trigger, policy and exact writer grants admission", "Store transaction owner and original budget provenance", "Lifecycle pool/readiness and activation preparation v2", "Neon/operator/custody/provider/customer and GA qualification", "Native runtime/physical/UI/capture checks paused"]}
    env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test")
    attempted_start = False

    def run(label, argv, check=True, timeout=30):
        argv = [str(x) for x in argv]
        entry = {"name": label, "argv": argv, "cwd": str(inputs), "timeout_seconds": timeout}
        receipt["commands"].append(entry)
        try:
            p = subprocess.Popen(argv, cwd=inputs, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, start_new_session=True)
            try:
                stdout, stderr = p.communicate(timeout=timeout)
                entry["timed_out"] = False
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                stdout, stderr = p.communicate(timeout=5)
                entry["timed_out"] = True
            entry["exit_code"] = p.returncode
        except OSError as error:
            stdout, stderr = b"", str(error).encode()
            entry.update(exit_code=None, timed_out=False, spawn_error=type(error).__name__)
        (out / (label + ".stdout")).write_bytes(stdout)
        (out / (label + ".stderr")).write_bytes(stderr)
        entry.update(stdout=label + ".stdout", stderr=label + ".stderr")
        if check and (entry["exit_code"] != 0 or entry["timed_out"]):
            raise RuntimeError(label + " failed")
        return entry["exit_code"], stdout

    try:
        manifest = {}
        for rel in SOURCES:
            target = inputs / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, target)
            manifest[rel] = digest(target)
        receipt["sources_sha256"] = manifest
        receipt["source_tree_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        paths = [ROOT / "hosted/_build/test/lib" / dep / "ebin" for dep in DEPS]
        beams = {str(p.relative_to(ROOT)): digest(p) for directory in paths for p in sorted(directory.iterdir()) if p.is_file()}
        (out / "dependency-beams.json").write_text(json.dumps(beams, indent=2) + "\n")
        receipt["dependency_manifest_sha256"] = digest(out / "dependency-beams.json")
        _, head = run("git-head", ["git", "-C", ROOT, "rev-parse", "HEAD"])
        receipt["head"] = head.decode().strip()
        for label, command in [("python-version", ["python3", "--version"]),
            ("elixir-version", ["elixir", "--version"]),
            ("docker-version", ["docker", "version", "--format", "{{json .Server}}"]),
            ("postgres-image", ["docker", "image", "inspect", IMAGE])]:
            run(label, command)
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        receipt["owned_server"] = {"container": name, "image": IMAGE, "host": "127.0.0.1", "port": port}
        attempted_start = True
        run("postgres-start", ["docker", "run", "--detach", "--rm", "--name", name,
            "--label", "mixer.fixture=preparation-sql-review", "--publish", f"127.0.0.1:{port}:5432",
            "--env", "POSTGRES_USER=browser_admin", "--env", "POSTGRES_HOST_AUTH_METHOD=trust",
            "--env", "POSTGRES_INITDB_ARGS=--no-locale -E UTF8", IMAGE, "-c", "timezone=UTC"])
        for attempt in range(60):
            code, _ = run("ready-" + str(attempt), ["docker", "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "browser_admin"], check=False)
            if code == 0:
                # pg_isready can see initdb's temporary Unix-only server; require
                # a published TCP round trip before proceeding.
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                        break
                except OSError:
                    pass
            time.sleep(0.1)
        else:
            raise RuntimeError("owned postgres readiness failed")
        run("postgres-version", ["docker", "exec", name, "postgres", "--version"])
        psql = ["docker", "exec", name, "psql", "-X", "-h", "127.0.0.1", "-U", "browser_admin", "-d", "postgres", "-v", "ON_ERROR_STOP=1"]
        sql = ";".join("CREATE ROLE " + role + " " + login + " NOSUPERUSER NOBYPASSRLS NOINHERIT" for role, login in [
            ("browser_schema_owner", "NOLOGIN"), ("browser_writer", "NOLOGIN"),
            ("browser_lifecycle", "LOGIN"), ("browser_ordinary", "LOGIN"),
            ("review_mid", "NOLOGIN"), ("review_leaf", "NOLOGIN")])
        run("roles", psql + ["-c", sql])
        run("database", ["docker", "exec", name, "createdb", "-h", "127.0.0.1", "-U", "browser_admin", "-O", "browser_schema_owner", "browser_storage"])
        env["MIXER_BROWSER_STORAGE_PORT"] = str(port)
        result = out / "result.json"
        entrypoint = out / "selected_runner.exs"
        entrypoint.write_text('ExUnit.start(autorun: false, seed: 0, max_cases: 1)\nCode.require_file("verification/hosted-browser-activation-preparation-sql-review/review.exs")\nr=ExUnit.run()\nFile.write!(' + json.dumps(str(result)) + ',Jason.encode!(r))\nSystem.halt(if r.total==' + str(EXPECTED) + ' and r.failures==0 and r.skipped==0 and r.excluded==0 and Map.get(r,:invalid,0)==0, do: 0, else: 1)\n')
        command = ["elixir"] + [arg for path in paths for arg in ["-pa", path]] + [arg for rel in SOURCES[:8] for arg in ["-r", inputs / rel]] + [entrypoint]
        # Selected compilation and actual Mix formatter run only on the copied
        # projectless input tree; never invoke the hosted project compile.
        compiled = out / "compiled"
        compiled.mkdir()
        compile_command = ["elixirc"] + [arg for path in paths for arg in ["-pa", path]] + ["--warnings-as-errors", "-o", compiled] + [inputs / rel for rel in SOURCES[:8]]
        run("selected-compile", compile_command)
        run("mix-version", ["mix", "--version"])
        run("actual-mix-format", ["mix", "format", "--check-formatted", str(inputs / SOURCES[3])])
        code, _ = run("independent-tests", command, check=False, timeout=90)
        receipt["tests_passed"] = code == 0
        if result.exists():
            receipt["tests"] = json.loads(result.read_text())
    except Exception as error:
        receipt["failure"] = str(error)
    finally:
        if attempted_start:
            run("postgres-logs", ["docker", "logs", name], check=False)
            code, _ = run("postgres-stop", ["docker", "stop", "--timeout", "5", name], check=False)
            receipt["cleanup"]["owned_postgres_stopped"] = code == 0
            code, _ = run("postgres-removed", ["docker", "container", "inspect", name], check=False)
            receipt["cleanup"]["owned_container_removed"] = code != 0
        else:
            receipt["cleanup"].update(owned_postgres_stopped=True, owned_container_removed=True)
        receipt["source_changes_during_run"] = [rel for rel, sha in receipt.get("sources_sha256", {}).items() if digest(ROOT / rel) != sha]
        receipt["dependency_changes_during_run"] = [rel for rel, sha in locals().get("beams", {}).items() if digest(ROOT / rel) != sha]
        receipt["outputs_sha256"] = {str(p.relative_to(out)): digest(p) for p in out.iterdir() if p.is_file()}
        receipt["success"] = receipt.get("tests_passed", False) and not receipt.get("failure") and all(receipt["cleanup"].values()) and not receipt["source_changes_during_run"] and not receipt["dependency_changes_during_run"]
        receipt["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (BASE / "latest.json").write_text(json.dumps({"mutable_pointer_only": True, "attempt": str(out.relative_to(BASE))}, indent=2) + "\n")
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(str(out.relative_to(ROOT)))
        print(json.dumps({key: receipt.get(key) for key in ["success", "tests", "failure", "cleanup"]}))
    return 0 if receipt["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
