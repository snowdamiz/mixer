#!/usr/bin/env python3
"""Stage and run selected ordinary HTTP sources; never import the shared collector."""
import argparse
import ast
import datetime
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
BASE = Path(__file__).resolve().parent
TEST = "hosted/test/mixer_hosted_web/customer_artifact_http_integration_test.exs"
IDENTITY = "access_token_verifier admission bounded_json bounded_tcp configured_verifier dns_resolver encoding fetch_flight global_address http_freshness http_wire_guard jwks_transport key_owner manifest trust_snapshot verified_identity verifier".split()
SOURCES = [
    "hosted/lib/mixer_hosted/customer_artifacts.ex",
    "hosted/lib/mixer_hosted/repo.ex",
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
    "hosted/lib/mixer_hosted_web/health_controller.ex",
    "hosted/lib/mixer_hosted_web/plugs/bearer_identity.ex",
    "hosted/lib/mixer_hosted_web/plugs/customer_artifact_request.ex",
    "hosted/lib/mixer_hosted_web/customer_artifact_controller.ex",
    "hosted/lib/mixer_hosted_web/router.ex",
    "hosted/test/support/identity_tls_fixture.ex",
    "hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs",
    "hosted/priv/repo/migrations/20261025000004_add_authorization_state_revisions.exs",
    "hosted/priv/repo/migrations/20261025000005_add_customer_artifact_storage.exs",
] + [f"hosted/lib/mixer_hosted/identity/{name}.ex" for name in IDENTITY]
DEPS = "telemetry decimal db_connection ecto ecto_sql postgrex jason jose mime plug_crypto plug phoenix_pubsub phoenix_template phoenix websock websock_adapter thousand_island hpax bandit mint".split()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def isolated_helper():
    source = ROOT / "hosted/scripts/test-local.py"
    tree = ast.parse(source.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "provision_customer_artifact_fixtures")
    # Keep the named safe helper's exact commands, restricting its literal tuples
    # to the owned HTTP database. No top-level shared script statement executes.
    loop = next(n for n in node.body if isinstance(n, ast.For))
    original = ast.literal_eval(loop.iter)
    selected = [row for row in original if row == ("http_artifact", "mixer_customer_artifact_http", "MIXER_ARTIFACT_HTTP_TEST_PORT")]
    if len(selected) != 1:
        raise RuntimeError("owned HTTP database tuple missing from safe provisioning helper")
    loop.iter = ast.parse(repr(selected), mode="eval").body
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    return module, ast.unparse(module) + "\n", {"path": str(source.relative_to(ROOT)), "whole_source_sha256": digest(source), "executed": "AST-selected named helper with one owned tuple; no shared main imported"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Fresh directory under this collector, default attempts/current UTC")
    parser.add_argument("--list-sources", action="store_true")
    args = parser.parse_args()
    if args.list_sources:
        print(json.dumps({"sources": SOURCES, "test": TEST, "dependencies": DEPS, "excluded": "mixer_hosted application and all unselected ordinary/frozen/Worker/native sources"}, indent=2))
        return 0
    output = (ROOT / args.output).resolve() if args.output else BASE / "attempts" / datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output.relative_to(BASE)
    output.mkdir(parents=True, exist_ok=False)
    inputs = output / "inputs"
    inputs.mkdir()
    scratch = Path(tempfile.mkdtemp(prefix="mixer-customer-artifact-http-"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("MIXER_")}
    env.update(MIX_ENV="test", ERL_FLAGS="+S 2:2", ERL_CRASH_DUMP=str(scratch / "erl_crash.dump"), ERL_CRASH_DUMP_SECONDS="0")
    receipt = {"schema": 1, "status": "failed", "started_unix": time.time(), "platform": platform.platform(), "commands": [], "cleanup": {}, "scope": "Actual production Phoenix Router, default BearerIdentity and ConfiguredVerifier, synthetic RS256 bearer via named KeyOwner/TLSFixture JWKS, ephemeral Ed25519 artifact, restricted runtime role and real PostgreSQL artifact transactions over loopback Bandit sockets.", "limitations": ["Host-only synthetic TLS/JWKS identity fixture; no public DNS or configured production identity provider qualification.", "Disposable loopback PostgreSQL without TLS; no Neon, R2/CDN, Cloudflare deployment, production listener, quotas, login or publication.", "Protocol-only payload is not executable guest code; no native/UI/device/store/compiler/GA or separate-repository published FieldLog qualification.", "Post-write failure injects backend termination after deferred checks but before final authorization checkpoint/commit; it does not simulate every commit uncertainty.", "No preexisting Go audit history migration or full W11 wire parity claim."]}
    started = False

    def run(label, argv, timeout=120, check=True, cwd=inputs):
        begin = time.time()
        try:
            result = subprocess.run([str(x) for x in argv], cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            data = error.stdout or b""
            if isinstance(data, bytes):
                data = data.decode(errors="replace")
            result = subprocess.CompletedProcess(argv, 124, data + "\nCOLLECTOR: timed out\n")
        log = output / (label + ".log")
        log.write_text(result.stdout)
        receipt["commands"].append({"label": label, "argv": list(map(str, argv)), "cwd": str(cwd), "started_unix": begin, "duration_seconds": time.time() - begin, "exit_code": result.returncode, "output": log.name, "output_sha256": digest(log)})
        if check and result.returncode:
            raise RuntimeError(f"{label} failed ({result.returncode}); preserved {log.name}")
        return result

    try:
        receipt["source_revision"] = run("source-revision", ["git", "rev-parse", "HEAD"], cwd=ROOT).stdout.strip()
        selected = SOURCES + [TEST, "hosted/mix.exs", "hosted/mix.lock", str(Path(__file__).relative_to(ROOT))]
        doc = "docs/hosted-customer-artifact-http-integration.md"
        if (ROOT / doc).exists():
            selected.append(doc)
        manifest = {}
        for name in sorted(selected):
            target = inputs / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
            manifest[name] = digest(target)
        receipt["inputs"] = manifest
        receipt["source_tree_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        (output / "source-list.json").write_text(json.dumps({"compiled": SOURCES, "test": TEST, "dependencies": DEPS}, indent=2) + "\n")
        paths = [ROOT / "hosted/_build/test/lib" / dep / "ebin" for dep in DEPS]
        dependencies = {}
        for path in paths:
            if not path.is_dir():
                raise RuntimeError("pinned dependency BEAM directory missing: " + str(path))
            for file in sorted(path.iterdir()):
                if file.is_file():
                    dependencies[str(file.relative_to(ROOT))] = digest(file)
        (output / "dependency-beams.json").write_text(json.dumps(dependencies, indent=2) + "\n")
        receipt["dependency_manifest_sha256"] = digest(output / "dependency-beams.json")
        codepaths = [v for path in paths for v in ["-pa", str(path)]]
        run("elixir-version", ["elixir", "--version"])
        run("python-version", ["python3", "--version"])
        run("openssl-version", ["openssl", "version"])
        pg = Path(run("postgres-bindir", ["pg_config", "--bindir"]).stdout.strip())
        run("postgres-version", [pg / "postgres", "--version"])
        run("format", ["mix", "format", "--check-formatted", inputs / TEST])
        beams = scratch / "beams"
        beams.mkdir()
        compile_code = "Mix.start(); result = Kernel.ParallelCompiler.compile_to_path(System.argv(), " + json.dumps(str(beams)) + ", warnings_as_errors: true); case result do {:ok, _, []} -> :ok; _ -> IO.inspect(result); System.halt(1) end"
        run("compile", ["elixir", *codepaths, "-e", compile_code, "--", *[inputs / name for name in SOURCES]])
        run("postgres-init", [pg / "initdb", "-D", scratch / "pg", "-U", "mixer_fixture", "-A", "trust", "--no-locale", "-E", "UTF8"])
        with socket.socket() as candidate:
            candidate.bind(("127.0.0.1", 0))
            port = candidate.getsockname()[1]
        run("postgres-start", [pg / "pg_ctl", "-D", scratch / "pg", "-l", scratch / "postgres.log", "-o", f"-h 127.0.0.1 -p {port} -k '' -c timezone=UTC -c max_connections=20", "-w", "start"])
        started = True
        receipt["postgres_endpoint"] = {"host": "127.0.0.1", "port": port, "database": "mixer_customer_artifact_http", "disposable": True}
        module, helper_text, helper_provenance = isolated_helper()
        (output / "executed-provision-helper.py").write_text(helper_text)
        receipt["provision_helper"] = dict(helper_provenance, executed_sha256=digest(output / "executed-provision-helper.py"))
        namespace = {}
        exec(compile(module, "selected-safe-provision-helper", "exec"), namespace)
        env.update(namespace["provision_customer_artifact_fixtures"](pg, port, lambda label, argv: run(label, argv)))
        evidence = output / "http-observations"
        evidence.mkdir()
        env["MIXER_ARTIFACT_HTTP_EVIDENCE"] = str(evidence)
        runner = scratch / "run.exs"
        runner.write_text('Mix.start()\nApplication.put_env(:phoenix, :json_library, Jason)\nApplication.put_env(:jose, :json_module, :jose_json_jason)\nApplication.put_env(:jose, :unsecured_signing, false)\nApplication.put_env(:jose, :crypto_fallback, false)\nLogger.configure(level: :warning)\nExUnit.start(autorun: false, seed: 0, max_cases: 1)\nCode.require_file(' + json.dumps(str(inputs / TEST)) + ')\nresult = ExUnit.run()\nSystem.halt(if result.failures == 0, do: 0, else: 1)\n')
        run("tests", ["elixir", *codepaths, "-pa", beams, runner], timeout=180)
        receipt["status"] = "passed"
    except Exception as error:
        receipt["failure"] = str(error)
    finally:
        cleanup_file = output / "http-observations/http-cleanup.json"
        if cleanup_file.exists():
            http_cleanup = json.loads(cleanup_file.read_text())
            receipt["cleanup"].update(http_cleanup)
            for name in ["bandit", "tls"]:
                try:
                    with socket.create_connection(("127.0.0.1", http_cleanup[name + "_port"]), timeout=0.3):
                        closed = False
                except OSError:
                    closed = True
                receipt["cleanup"][name + "_socket_closed"] = closed
        if started or (scratch / "pg/postmaster.pid").exists():
            try:
                stopped = run("postgres-stop", [pg / "pg_ctl", "-D", scratch / "pg", "-m", "fast", "-w", "stop"], timeout=30, check=False)
                receipt["cleanup"]["postgres_stopped"] = stopped.returncode == 0
            except Exception as error:
                receipt["cleanup"]["postgres_stop_error"] = str(error)
        else:
            receipt["cleanup"]["postgres_not_started"] = True
        if (scratch / "postgres.log").exists():
            shutil.copy2(scratch / "postgres.log", output / "postgres.log")
        if not started or receipt["cleanup"].get("postgres_stopped"):
            shutil.rmtree(scratch)
        receipt["cleanup"]["scratch_removed"] = not scratch.exists()
        receipt["live_source_changes_during_run"] = [name for name, sha in receipt.get("inputs", {}).items() if digest(ROOT / name) != sha]
        if receipt["live_source_changes_during_run"]:
            receipt["status"] = "failed"
            receipt["failure"] = "live selected inputs changed during run; staged snapshot results preserved"
        if receipt["status"] == "passed" and not all(receipt["cleanup"].get(k) for k in ["postgres_stopped", "scratch_removed", "bandit_stopped", "key_owner_stopped", "jwks_workers_stopped", "tls_fixture_stopped", "ephemeral_tls_key_directory_removed", "bandit_socket_closed", "tls_socket_closed"]):
            receipt["status"] = "failed"
            receipt["failure"] = "owned resource cleanup was incomplete"
        receipt["finished_unix"] = time.time()
        receipt["outputs"] = {str(p.relative_to(output)): digest(p) for p in output.rglob("*") if p.is_file() and "inputs" not in p.relative_to(output).parts and p.name != "receipt.json"}
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "receipt": str(output / "receipt.json"), "source_revision": receipt.get("source_revision"), "source_tree_sha256": receipt.get("source_tree_sha256"), "failure": receipt.get("failure"), "cleanup": receipt["cleanup"]}, sort_keys=True))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
