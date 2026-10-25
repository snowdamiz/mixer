#!/usr/bin/env python3
"""One owned PG16 container, exact selected source, isolated independent review."""
from __future__ import annotations

import datetime as dt
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
HANDOFF = ROOT / "verification/hosted-browser-begin-login/handoff.json"
IMAGE = "sha256:9e2cf6287f25c3151f4c9421ccce2b17f3e60061c111a29165e0d2cdd9ff0a97"
DEPS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason", "oban", "jose", "mint", "hpax"]
IDENTITY = ["encoding", "bounded_json", "trust_snapshot", "manifest", "startup_config", "admission", "global_address", "http_freshness", "http_wire_guard", "dns_resolver", "bounded_tcp", "jwks_transport", "fetch_flight", "key_owner"]
BROWSER = ["vault", "stored_snapshot", "config", "configuration_digest", "custody", "runtime_config", "storage_schema", "activation_preparation", "activation_preparation_schema", "catalog_manifest", "catalog_manifest_v2", "catalog", "relation_manifest", "relation_catalog", "preauth_draft", "lifecycle_repo", "store", "runtime_owner", "protocol"]
SOURCES = ([f"hosted/lib/mixer_hosted/identity/{p}.ex" for p in IDENTITY] + [f"hosted/lib/mixer_hosted/{p}.ex" for p in ["runtime_config", "repo"]] + [f"hosted/lib/mixer_hosted/browser_auth/{p}.ex" for p in BROWSER] + ["hosted/lib/mixer_hosted/customer_artifacts/schema.ex"])


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(values: dict) -> str:
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("script", choices=["runtime_review.exs"])
    parser.add_argument("--expected-handoff", required=True)
    options = parser.parse_args()
    script = options.script
    expected_handoff = options.expected_handoff
    assert len(expected_handoff) == 64 and all(c in "0123456789abcdef" for c in expected_handoff)
    attempt = BASE / "attempts" / (dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-pg16-" + uuid.uuid4().hex[:6])
    attempt.mkdir(parents=True)
    scratch = Path(tempfile.mkdtemp(prefix="mixer-begin-independent-"))
    scratch_identity = (scratch.stat().st_dev, scratch.stat().st_ino)
    owned_name = "mixer-begin-review-" + uuid.uuid4().hex[:10]
    receipt = {"schema_version": 1, "scope": "Independent exact-source selected fixed begin-login component; PG16 Linux Docker, manual synthetic loopback random-port non-TLS configuration, no production Application startup provenance", "commands": [], "owned_container_name": owned_name, "owned_scratch": str(scratch), "native_ui_capture_or_process_discovery": False, "cleanup": {}}
    env = {k: v for k, v in os.environ.items() if k in ["PATH", "HOME", "LANG", "LC_ALL", "TMPDIR"]}
    env.update(ERL_FLAGS="+S 2:2 +SDcpu 1 +SDio 1", MIX_ENV="test", ERL_CRASH_DUMP=str(scratch / "erl.dump"), PREAUTH_REVIEW_OUTPUT=str(attempt))
    selected = {}
    dependencies = {}

    def run(label, argv, *, data=None, timeout=55, check=True, cwd=ROOT):
        argv = list(map(str, argv))
        command = {"label": label, "argv": argv, "cwd": str(cwd), "timeout_seconds": timeout}
        receipt["commands"].append(command)
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE if data is not None else None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = proc.communicate(data.encode() if isinstance(data, str) else data, timeout=timeout)
            command["timed_out"] = False
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            stdout, stderr = proc.communicate(timeout=5)
            command["timed_out"] = True
        command["exit_code"] = proc.returncode
        (attempt / (label + ".stdout")).write_bytes(stdout)
        (attempt / (label + ".stderr")).write_bytes(stderr)
        print(f"{label}: exit {proc.returncode}", flush=True)
        if check and (proc.returncode != 0 or command["timed_out"]):
            raise RuntimeError(f"{label} failed")
        return proc.returncode, stdout.decode(errors="replace")

    def verify_selected():
        drift = [p for p, h in selected.items() if sha(ROOT / p) != h]
        if drift:
            raise RuntimeError("selected source drift: " + ",".join(drift))

    container_created = False
    container_identity = None
    try:
        assert sha(HANDOFF) == expected_handoff, "producer handoff mismatch"
        handoff = json.loads(HANDOFF.read_text())
        selected = handoff["sources"]
        verify_selected()
        receipt["producer_handoff_sha256"] = expected_handoff
        receipt["selected_sources"] = selected
        receipt["selected_source_tree_sha256"] = tree(selected)
        own_files = ["docs/hosted-browser-begin-login-review.md"] + [str(p.relative_to(ROOT)) for p in BASE.iterdir() if p.is_file()]
        receipt["review_sources"] = {p: sha(ROOT / p) for p in sorted(own_files)}
        for p in set(selected) | set(own_files):
            dest = attempt / "inputs" / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / p, dest)
        depdirs = [ROOT / "hosted/_build/test/lib" / dep / "ebin" for dep in DEPS]
        assert all(p.is_dir() for p in depdirs)
        dependencies = {str(p.relative_to(ROOT)): sha(p) for d in depdirs for p in sorted(d.glob("*")) if p.is_file()}
        receipt["dependencies"] = dependencies
        receipt["dependency_tree_sha256"] = tree(dependencies)
        _, revision = run("revision", ["git", "rev-parse", "HEAD"])
        receipt["root_revision_context_only"] = revision.strip()
        run("elixir-version", ["elixir", "--version"])
        run("python-version", ["python3", "--version"])
        run("git-version", ["git", "--version"])
        run("docker-version", ["docker", "--version"])
        run("image-identity", ["docker", "image", "inspect", IMAGE, "--format", "{{json .Id}} {{json .RepoDigests}}"])
        ebin = scratch / "ebin"
        ebin.mkdir()
        compile_code = "Mix.start(); Mix.env(:test); case Kernel.ParallelCompiler.compile_to_path(tl(System.argv()),hd(System.argv()),warnings_as_errors: true, return_diagnostics: true) do {:ok,_,%{compile_warnings: [], runtime_warnings: []}} -> :ok; _ -> System.halt(1) end"
        args = ["elixir"] + [a for d in depdirs for a in ["-pa", d]]
        run("selected-compile", args + ["-e", compile_code, ebin] + SOURCES)
        verify_selected()
        run("postgres-create", ["docker", "create", "--name", owned_name, "--publish", "127.0.0.1::5432", "--env", "POSTGRES_USER=review_admin", "--env", "POSTGRES_HOST_AUTH_METHOD=trust", "--env", "POSTGRES_INITDB_ARGS=--no-locale --encoding=UTF8", IMAGE, "-c", "timezone=UTC", "-c", "log_statement=none", "-c", "log_min_error_statement=panic"])
        container_created = True
        _, container_identity = run("postgres-created-identity", ["docker", "inspect", owned_name, "--format", "{{.Id}}"] )
        container_identity = container_identity.strip()
        receipt["owned_container_id"] = container_identity
        assert len(container_identity) == 64
        run("postgres-start", ["docker", "start", owned_name])
        for index in range(40):
            status, _ = run(f"postgres-ready-{index:02d}", ["docker", "exec", owned_name, "pg_isready", "-U", "review_admin"], check=False, timeout=5)
            if status == 0:
                break
            time.sleep(0.2)
        else:
            raise RuntimeError("owned PG16 readiness timeout")
        _, port = run("postgres-port", ["docker", "port", owned_name, "5432/tcp"])
        env["PREAUTH_REVIEW_PORT"] = port.strip().rsplit(":", 1)[1]
        receipt["port"] = int(env["PREAUTH_REVIEW_PORT"])
        psql = ["docker", "exec", "-i", owned_name, "psql", "-X", "-q", "-A", "-t", "-U", "review_admin", "-d", "postgres", "-v", "ON_ERROR_STOP=1"]
        _, version = run("postgres-version", psql, data="SELECT version(),current_setting('server_version_num'),datcollate,datctype FROM pg_database WHERE datname=current_database();")
        assert "|16" in version and "|C|C" in version, "actual PG16 C/libc fixture required"
        roles = "".join(f"CREATE ROLE {name} {login} NOINHERIT NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOREPLICATION;" for name, login in [("mixer_review_owner", "NOLOGIN"), ("mixer_review_writer", "NOLOGIN"), ("mixer_review_lifecycle", "LOGIN"), ("mixer_review_runtime", "LOGIN")])
        run("postgres-roles", psql, data=roles)
        run("postgres-database", psql, data="CREATE DATABASE review_browser OWNER mixer_review_owner;")
        command = args + ["-pa", ebin]
        run("install", command + [BASE / "install_review.exs"])
        verify_selected()
        _, controls_stdout = run("independent-controls", command + [BASE / script], timeout=55)
        output_lines = [line for line in controls_stdout.splitlines() if line]
        assert output_lines and output_lines[-1].startswith("{"), "missing final component count"
        counts = json.loads(output_lines[-1])
        assert counts == {"component_methods": len(output_lines) - 1}, "unexpected component output"
        assert all(line.startswith("PASS ") for line in output_lines[:-1]), "unexpected diagnostic output"
        assert (attempt / "independent-controls.stderr").read_bytes() == b"", "unexpected runtime stderr"
        receipt["clean_runtime_output"] = True
        receipt["checks"] = json.loads((attempt / "checks.json").read_text())
        receipt["beam_cleanup"] = json.loads((attempt / "beam-cleanup.json").read_text())
        assert all(receipt["beam_cleanup"].values()), "owned BEAM cleanup incomplete"
        receipt["all_recorded_invariants_passed"] = bool(receipt["checks"]) and all(x.get("invariant_passed") is True for x in receipt["checks"])
        verify_selected()
        receipt["execution_completed"] = True
    except Exception as error:
        receipt["failure"] = str(error)
    finally:
        if container_created:
            _, current_identity = run("postgres-cleanup-identity", ["docker", "inspect", owned_name, "--format", "{{.Id}}"], check=False, timeout=10)
            if container_identity is not None and current_identity.strip() != container_identity:
                receipt["cleanup"]["owned_container_identity_checked"] = False
            else:
                receipt["cleanup"]["owned_container_identity_checked"] = True
                run("postgres-stop", ["docker", "stop", "--time", "2", owned_name], check=False, timeout=10)
                run("postgres-remove", ["docker", "rm", "--force", "--volumes", owned_name], check=False, timeout=10)
            status, output = run("owned-container-absent", ["docker", "inspect", owned_name], check=False, timeout=10)
            diagnostic = (attempt / "owned-container-absent.stderr").read_text().lower()
            receipt["cleanup"]["owned_container_absent"] = status == 1 and json.loads(output) == [] and owned_name in diagnostic and ("no such object" in diagnostic or "no such container" in diagnostic)
        else:
            receipt["cleanup"]["owned_container_absent"] = True
            receipt["cleanup"]["owned_container_identity_checked"] = True
        if scratch.exists():
            assert (scratch.stat().st_dev, scratch.stat().st_ino) == scratch_identity
            shutil.rmtree(scratch)
        receipt["cleanup"]["owned_scratch_identity_checked"] = True
        receipt["cleanup"]["owned_scratch_absent"] = not scratch.exists()
        receipt["cleanup"]["no_native_ui_capture_or_process_discovery"] = True
        receipt["selected_source_changes"] = [p for p, h in selected.items() if sha(ROOT / p) != h]
        receipt["dependency_changes"] = [p for p, h in dependencies.items() if sha(ROOT / p) != h]
        for filename, key in [("checks.json", "checks"), ("beam-cleanup.json", "beam_cleanup")]:
            artifact = attempt / filename
            if artifact.is_file():
                receipt[key] = json.loads(artifact.read_text())
        receipt["finished_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        receipt["outputs"] = {str(p.relative_to(attempt)): sha(p) for p in attempt.iterdir() if p.is_file()}
        receipt["valid_execution_receipt"] = receipt.get("execution_completed", False) and all(receipt["cleanup"].values()) and not receipt["selected_source_changes"] and not receipt["dependency_changes"]
        (attempt / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        print(attempt.relative_to(ROOT), flush=True)
        print(json.dumps({k: receipt.get(k) for k in ["valid_execution_receipt", "failure", "cleanup"]}), flush=True)
    return 0 if receipt["valid_execution_receipt"] and receipt.get("all_recorded_invariants_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
