#!/usr/bin/env python3
"""Independent selected migration replay and adversity review on owned PostgreSQL16."""
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
PRODUCER = ROOT / "verification/hosted-browser-activation-preparation-migration"
IMAGE = "postgres@sha256:9e2cf6287f25c3151f4c9421ccce2b17f3e60061c111a29165e0d2cdd9ff0a97"
DEPS = ["telemetry", "decimal", "db_connection", "ecto", "ecto_sql", "postgrex", "jason", "oban"]
BROWSER = "hosted/lib/mixer_hosted/browser_auth/"
MODULES = [BROWSER + n for n in ["storage_schema.ex", "activation_preparation_schema.ex", "catalog_manifest.ex", "catalog_manifest_v2.ex", "catalog.ex"]] + ["hosted/lib/mixer_hosted/customer_artifacts/schema.ex"]
MIGRATIONS = ["20261024000000_add_oban.exs", "20261025000000_add_build_journals.exs", "20261025000001_add_build_admission.exs", "20261025000002_add_build_aggregate_limits.exs", "20261025000003_add_customer_authorization.exs", "20261025000004_add_authorization_state_revisions.exs", "20261025000005_add_customer_artifact_storage.exs", "20261025000006_add_customer_workspace_discovery.exs", "20261025000007_add_browser_sessions.exs", "20261025000008_add_browser_activation_preparation.exs"]
SPEC = "hosted/test/mixer_hosted/browser_auth/migration_spec.exs"
REVIEW = "verification/hosted-browser-activation-preparation-migration-review/review.exs"
SOURCES = MODULES + [BROWSER + "activation_preparation.ex", SPEC, REVIEW, "verification/hosted-browser-activation-preparation-migration-review/run.py", "hosted/test/mixer_hosted/browser_auth/storage_fixture.exs", "hosted/test/mixer_hosted/browser_auth/run_migration_fixture.py", "hosted/mix.lock", "hosted/mix.exs", "docs/hosted-browser-activation-preparation-migration.md"]
SOURCES += ["hosted/priv/repo/migrations/" + name for name in MIGRATIONS]
SOURCES += ["hosted/test/foundation_integration_test.exs"] + [f"hosted/test/mixer_hosted/builds/{name}_test.exs" for name in ["admission", "coordinator", "aggregate_admission"]]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_frozen():
    assert digest(PRODUCER / "handoff.json") == "ef7383d9fac9a6675885237eb7bb5b6d3f1a8179c680d758cc3f51769f3ceefb"
    assert digest(PRODUCER / "seal.json") == "8ab16a016fed507234390a1a59a253bc3c379f7e4291bf3cf57eb059e293b63a"
    handoff = json.loads((PRODUCER / "handoff.json").read_text())
    members = json.loads((PRODUCER / "seal.json").read_text())["members_sha256"]
    assert len(members) == 543
    for rel, value in members.items():
        assert digest(PRODUCER / rel) == value, rel
    for rel, value in handoff["owned_source_files_sha256"].items():
        assert digest(ROOT / rel) == value, rel
    preservation = json.loads((PRODUCER / "source-preservation.json").read_text())
    for rel, value in preservation["pinned_sources"].items():
        assert digest(ROOT / rel) == value, rel
    for item in preservation["old_nine_checks"]:
        assert digest(ROOT / item["path"]) == item["head_sha256"], item["path"]
    return {"handoff_sha256": digest(PRODUCER / "handoff.json"), "seal_sha256": digest(PRODUCER / "seal.json"), "verified_members": len(members), "owned_sources_verified": len(handoff["owned_source_files_sha256"]), "accepted_semantic_pins_verified": len(preservation["pinned_sources"]), "old_migrations_verified": len(preservation["old_nine_checks"])}


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ-") + uuid.uuid4().hex[:8]
    out = BASE / "attempts" / stamp
    inputs = out / "inputs"
    inputs.mkdir(parents=True)
    compiled = out / "compiled"
    name = "mixer-preparation-migration-review-" + uuid.uuid4().hex[:12]
    receipt = {"schema": 1, "commands": [], "cleanup": {}, "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "dependencies": DEPS,
               "scope": "Fresh PG16 selected original ten-migration replay (one aggregate method) and separately authored eleven-method operator/migration adversity suite. Fixture utilities/setup only reused. Exact eight dependency directories and explicit source modules only. One owned serial Docker PostgreSQL16 fixture, two isolated databases. No broad hosted harness/application, RelationCatalog/RelationManifest, frozen inspector/authority-driver/rejected WorkerV2, native runtime/UI/capture/phone/process-discovery or production execution.",
               "pending": ["Broad ordinary hosted CI after delivery", "Full relation admission", "Store original deadline/transaction ownership", "Runtime pool/custody/current identity/OIDC/provider/HTTP/console", "Neon actual operator deployment/customer/FieldLog/GA", "Paused native and physical-phone matrix"]}
    env = dict(os.environ, ERL_FLAGS="+S 2:2", MIX_ENV="test", MIXER_MIGRATION_REVIEW_OUTPUT=str(out))
    attempted_start = False
    beams = {}
    manifest = {}

    def run(label, argv, check=True, timeout=30):
        argv = [str(x) for x in argv]
        entry = {"name": label, "argv": argv, "cwd": str(inputs), "timeout_seconds": timeout}
        receipt["commands"].append(entry)
        try:
            process = subprocess.Popen(argv, cwd=inputs, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                entry["timed_out"] = False
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate(timeout=5)
                entry["timed_out"] = True
            entry["exit_code"] = process.returncode
        except OSError as error:
            stdout, stderr = b"", str(error).encode()
            entry.update(exit_code=None, timed_out=False, spawn_error=type(error).__name__)
        (out / (label + ".stdout")).write_bytes(stdout)
        (out / (label + ".stderr")).write_bytes(stderr)
        entry.update(stdout=label + ".stdout", stderr=label + ".stderr", stdout_sha256=hashlib.sha256(stdout).hexdigest(), stderr_sha256=hashlib.sha256(stderr).hexdigest())
        if check and (entry["exit_code"] != 0 or entry["timed_out"]):
            raise RuntimeError(label + " failed")
        return entry["exit_code"], stdout

    try:
        receipt["frozen_before"] = verify_frozen()
        assert set(MIGRATIONS) == {p.name for p in (ROOT / "hosted/priv/repo/migrations").iterdir() if p.is_file()}
        for rel in SOURCES:
            target = inputs / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, target)
            manifest[rel] = digest(target)
        receipt["sources_sha256"] = manifest
        receipt["source_tree_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        paths = [ROOT / "hosted/_build/test/lib" / dep / "ebin" for dep in DEPS]
        assert all(p.is_dir() for p in paths)
        beams = {str(p.relative_to(ROOT)): digest(p) for directory in paths for p in sorted(directory.iterdir()) if p.is_file()}
        (out / "dependency-beams.json").write_text(json.dumps(beams, indent=2) + "\n")
        receipt["dependency_manifest_sha256"] = digest(out / "dependency-beams.json")
        _, head = run("git-head", ["git", "-C", ROOT, "rev-parse", "HEAD"])
        receipt["source_revision"] = head.decode().strip()
        for label, command in [("python-version", ["python3", "--version"]), ("elixir-version", ["elixir", "--version"]), ("mix-version", ["mix", "--version"]), ("docker-version", ["docker", "version", "--format", "{{json .Server}}"]), ("postgres-image", ["docker", "image", "inspect", IMAGE])]:
            run(label, command)
        pa = [value for path in paths for value in ["-pa", path]]
        compiled.mkdir()
        run("selected-compile", ["elixirc", *pa, "--warnings-as-errors", "-o", compiled, *[inputs / rel for rel in MODULES]])
        formatted = [rel for rel in SOURCES if rel.endswith((".ex", ".exs")) and rel != "hosted/mix.exs"]
        run("actual-mix-format", ["mix", "format", "--check-formatted", *[inputs / rel for rel in formatted]])
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        receipt["owned_server"] = {"container": name, "image": IMAGE, "host": "127.0.0.1", "port": port}
        attempted_start = True
        run("postgres-start", ["docker", "run", "--detach", "--rm", "--name", name, "--label", "mixer.fixture=preparation-migration-review", "--publish", f"127.0.0.1:{port}:5432", "--env", "POSTGRES_USER=browser_admin", "--env", "POSTGRES_HOST_AUTH_METHOD=trust", "--env", "POSTGRES_INITDB_ARGS=--no-locale -E UTF8", IMAGE, "-c", "timezone=UTC"])
        for attempt in range(60):
            code, _ = run("ready-" + str(attempt), ["docker", "exec", name, "pg_isready", "-h", "127.0.0.1", "-U", "browser_admin"], check=False)
            if code == 0:
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                        break
                except OSError:
                    pass
            time.sleep(0.1)
        else:
            raise RuntimeError("owned fixture readiness failed")
        run("postgres-version", ["docker", "exec", name, "postgres", "--version"])
        psql = ["docker", "exec", name, "psql", "-X", "-h", "127.0.0.1", "-U", "browser_admin", "-d", "postgres", "-v", "ON_ERROR_STOP=1"]
        roles = [("browser_schema_owner", "NOLOGIN"), ("browser_writer", "NOLOGIN"), ("browser_lifecycle", "LOGIN"), ("browser_ordinary", "LOGIN"), ("review_neighbor", "NOLOGIN"), ("migration_owner", "LOGIN"), ("migration_runtime", "LOGIN")]
        run("roles", psql + ["-c", ";".join("CREATE ROLE " + role + " " + login + " NOSUPERUSER NOBYPASSRLS NOINHERIT NOCREATEROLE NOCREATEDB NOREPLICATION" for role, login in roles)])
        for database, owner in [("browser_migrations", "migration_owner"), ("browser_storage", "browser_schema_owner")]:
            run("database-" + database, ["docker", "exec", name, "createdb", "-h", "127.0.0.1", "-U", "browser_admin", "-O", owner, database])
        env["MIXER_BROWSER_MIGRATION_PORT"] = str(port)
        env["MIXER_BROWSER_STORAGE_PORT"] = str(port)
        receipt["suites"] = {}
        for label, source, count in [("selected-ten-migrations", SPEC, 1), ("independent-adversity", REVIEW, 11)]:
            result = out / (label + "-result.json")
            entry = out / (label + "-runner.exs")
            entry.write_text('ExUnit.start(autorun: false, seed: 0, max_cases: 1, trace: true)\nCode.require_file(' + json.dumps(str(inputs / source)) + ')\nr=ExUnit.run()\nFile.write!(' + json.dumps(str(result)) + ',Jason.encode!(r))\nSystem.halt(if r.total==' + str(count) + ' and r.failures==0 and r.skipped==0 and r.excluded==0 and Map.get(r,:invalid,0)==0, do: 0, else: 1)\n')
            code, _ = run(label, ["elixir", *pa, "-pa", compiled, entry], check=False, timeout=90)
            receipt["suites"][label] = {"exit_code": code, "expected_methods": count, "counts": json.loads(result.read_text()) if result.exists() else None}
        receipt["tests_passed"] = all(suite["exit_code"] == 0 for suite in receipt["suites"].values())
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
        if compiled.exists():
            (out / "compiled-products.json").write_text(json.dumps({p.name: digest(p) for p in sorted(compiled.iterdir()) if p.is_file()}, indent=2) + "\n")
            shutil.rmtree(compiled)
        receipt["cleanup"]["owned_compile_products_removed"] = not compiled.exists()
        receipt["cleanup"]["no_external_scratch_created"] = True
        receipt["source_changes_during_run"] = [rel for rel, value in manifest.items() if digest(ROOT / rel) != value]
        receipt["dependency_changes_during_run"] = [rel for rel, value in beams.items() if digest(ROOT / rel) != value]
        try:
            receipt["frozen_after"] = verify_frozen()
        except Exception as error:
            receipt["freeze_failure"] = str(error)
        receipt["success"] = receipt.get("tests_passed", False) and not receipt.get("failure") and not receipt.get("freeze_failure") and all(receipt["cleanup"].values()) and not receipt["source_changes_during_run"] and not receipt["dependency_changes_during_run"]
        receipt["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        receipt["outputs_sha256"] = {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob("*")) if p.is_file()}
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        (BASE / "latest.json").write_text(json.dumps({"mutable_pointer_only": True, "attempt": str(out.relative_to(BASE))}, indent=2) + "\n")
        print(str(out.relative_to(ROOT)))
        print(json.dumps({key: receipt.get(key) for key in ["success", "suites", "failure", "freeze_failure", "cleanup"]}))
    return 0 if receipt["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
