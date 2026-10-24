#!/usr/bin/env python3
"""Run host tests against a disposable loopback-only PostgreSQL instance."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tarfile
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True, type=Path)
parser.add_argument("--pg-bin", default="/opt/homebrew/opt/postgresql@17/bin", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
output = args.output.resolve()
output.mkdir(parents=True, exist_ok=False)
commands = []


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    inputs = {
        str(p.relative_to(root.parent)): digest(p)
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != "erl_crash.dump"
        and not {"_build", "deps", "__pycache__", "cover"}.intersection(p.relative_to(root).parts)
    }
    # Encoding and admission consume both shared signed bytes and rejection
    # cases. Bind each exact input in the digest and replay archive.
    for name in ("signed-release-v3.json", "release-v3-cases.json"):
        fixture = root.parent / "services/protocol/testdata" / name
        inputs[str(fixture.relative_to(root.parent))] = digest(fixture)
    return inputs


def run(label, argv, env=None, check=True):
    log = output / (label + ".log")
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with log.open("wb") as stream:
        try:
            result = subprocess.run(argv, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=300)
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            stream.write(b"\nCOLLECTOR: command exceeded 300 seconds\n")
            exit_code = 124
    commands.append({"label": label, "argv": list(map(str, argv)), "cwd": str(root), "started": started,
                     "exit_code": exit_code, "log": log.name, "sha256": digest(log)})
    if check and exit_code:
        raise RuntimeError(f"{label} failed ({exit_code}); see {log}")
    return exit_code


before = manifest()
source_digest = hashlib.sha256(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
with tarfile.open(output / "source.tar.gz", "w:gz") as archive:
    for name in before:
        archive.add(root.parent / name, arcname=name, recursive=False)
scratch = Path(tempfile.mkdtemp(prefix="mixer-phoenix-foundation-"))
pg_started = False
status = "failed"
cleanup = {}
try:
    run("revision", ["git", "rev-parse", "HEAD"])
    run("elixir-version", ["elixir", "--version"])
    run("postgres-version", [str(args.pg_bin / "postgres"), "--version"])
    run("format", ["mix", "format", "--check-formatted"])
    env = dict(os.environ, MIX_ENV="test")
    run("compile", ["mix", "compile", "--warnings-as-errors"], env)
    prod_env = {key: value for key, value in os.environ.items() if not key.startswith("MIXER_")}
    prod_env["MIX_ENV"] = "prod"
    prod_env["ERL_CRASH_DUMP_SECONDS"] = "0"
    prod_env["ERL_CRASH_DUMP"] = str(scratch / "release-crash.dump")
    run("release-build", ["mix", "release", "--overwrite"], prod_env)
    code = run("release-missing-config", [str(root / "_build/prod/rel/mixer_hosted/bin/mixer_hosted"),
                                          "eval", ":ok"], prod_env, check=False)
    rejection = (output / "release-missing-config.log").read_text()
    commands[-1]["expected_exit_code"] = 1
    if code != 1 or "invalid or missing hosted setting: MIXER_HOSTED_ROLE" not in rejection:
        raise RuntimeError("release did not reject missing runtime settings as specified")
    release_code = "Code.ensure_loaded!(MixerHosted.Identity.KeyOwner); Code.ensure_loaded!(MixerHosted.Identity.JWKSTransport); values = %{fixture_owner: function_exported?(MixerHosted.Identity.KeyOwner, :start_fixture, 1), fixture_transport: function_exported?(MixerHosted.Identity.JWKSTransport, :fetch_fixture, 6), startup_fixture: Code.ensure_loaded?(MixerHosted.Identity.StartupFixture), startup_dns_fixture: Code.ensure_loaded?(MixerHosted.Identity.StartupDNSFixture)}; IO.inspect(values, label: \"production_test_export_exclusion\"); true = Enum.all?(Map.values(values), &(&1 == false))"
    run("release-test-exclusion", ["elixir", "-pa", str(root / "_build/prod/rel/mixer_hosted/lib/mixer_hosted-0.1.0/ebin"), "-e", release_code], prod_env)
    run("initdb", [str(args.pg_bin / "initdb"), "-D", str(scratch / "data"), "-U", "mixer_fixture",
                   "--auth-local=trust", "--auth-host=trust", "--no-locale", "-E", "UTF8"])
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
    # Only synthetic data; this instance has no external listening interface.
    run("postgres-start", [str(args.pg_bin / "pg_ctl"), "-D", str(scratch / "data"), "-l",
                           str(output / "postgres.log"), "-o", f"-h 127.0.0.1 -p {port} -k ''", "-w", "start"])
    pg_started = True
    env["MIXER_TEST_DATABASE_PORT"] = str(port)
    identity_evidence = output / "identity-metrics"
    identity_evidence.mkdir()
    env["MIXER_TEST_IDENTITY_EVIDENCE"] = str(identity_evidence)
    run("createdb", [str(args.pg_bin / "createdb"), "-h", "127.0.0.1", "-p", str(port), "-U",
                     "mixer_fixture", "mixer_foundation_test"])
    run("createdb-startup", [str(args.pg_bin / "createdb"), "-h", "127.0.0.1", "-p", str(port), "-U",
                            "mixer_fixture", "mixer_startup_test"])
    run("tests", ["mix", "test", "--warnings-as-errors", "--seed", "0", "--trace"], env)
    if before != manifest():
        raise RuntimeError("source changed during tests")
    status = "passed"
finally:
    if pg_started or (scratch / "data/postmaster.pid").exists():
        stopped = run("postgres-stop", [str(args.pg_bin / "pg_ctl"), "-D", str(scratch / "data"),
                                        "-m", "fast", "-w", "stop"], check=False) == 0
        cleanup["postgres_stopped"] = stopped
        if not stopped:
            status = "failed"
    else:
        cleanup["postgres_stopped"] = not (scratch / "data/postmaster.pid").exists()
    if cleanup["postgres_stopped"]:
        # Only this collector's newly created scratch; never another service.
        shutil.rmtree(scratch)
        cleanup["scratch_removed"] = not scratch.exists()
    receipt = {
        "schema": 2, "status": status, "source_tree_sha256": source_digest, "inputs": before,
        "input_paths": "repository-relative; source archive uses the same paths",
        "source_archive_sha256": digest(output / "source.tar.gz"), "commands": commands,
        "cleanup": cleanup,
        "scope": "Host application test suite, Phoenix/Bandit, disposable PostgreSQL and packaged release. Exact tested components are recorded in tests.log. No Neon, Cloudflare, configured identity provider, authenticated HTTP routes, production domain outbox, external-effect, native, or GA qualification.",
        "limitations": ["Synthetic domain table and worker are test-only.",
                        "Database integration uses an isolated loopback PostgreSQL fixture without TLS; production TLS options have configuration tests only.",
                        "Local delayed-job completion does not qualify Cloudflare zero-traffic wake/recovery."]
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": status, "receipt": str(output / "receipt.json"), "cleanup": cleanup}))
