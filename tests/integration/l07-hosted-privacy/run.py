#!/usr/bin/env python3
"""Replay synthetic hosted privacy checks with pinned, offline, loopback services."""
import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import time

BASE = "36e1d8bbe1bdbf4522e49cf83d740780d1c54900"
SOURCE = "e326ce2041d8b2176b2086b2f59cd6cde6d97e56"
HERE = Path(__file__).resolve().parent
REGISTRATION_RUNNER = "tests/integration/free-project-starter/registration-runner.py"
TEST_DIR = Path("test/mixer_hosted/browser_auth")
TEST = TEST_DIR / "privacy_http_test.exs"
PROFILES = ("ordinary", "retained")
LOGGER_CONTROL = b"privacy fixture stock Logger control"
PG_CONTROL = b"privacy fixture PostgreSQL log control"
MIB = 1024 * 1024
STOP_AT = 1024 * MIB
CEILING = 1280 * MIB
INPUT_LIMIT = 64 * MIB
FILE_LIMIT = 32 * MIB
MAX_LOG = 4 * MIB
GIT_ENV = dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def size(path):
    total = 0
    for root, _, names in os.walk(path):
        for name in names:
            try:
                status = (Path(root) / name).lstat()
            except FileNotFoundError:
                continue
            total += max(status.st_size, status.st_blocks * 512)
    return total


def sample(scratch, receipt):
    used = size(scratch)
    receipt["scratchPeakSampleBytes"] = max(receipt["scratchPeakSampleBytes"], used)
    require(used < STOP_AT, "Replay scratch hit its 1 GiB stop threshold")


def wait(process, seconds, scratch, receipt):
    deadline = time.monotonic() + seconds
    while True:
        sample(scratch, receipt)
        try:
            status = process.wait(timeout=min(0.5, max(0, deadline - time.monotonic())))
        except subprocess.TimeoutExpired:
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Owned command {process.pid} exceeded {seconds}s") from None
        else:
            sample(scratch, receipt)
            return status


def version(command, env):
    return subprocess.check_output(command, env=env, timeout=10, text=True).strip()


def summarize_log(path, control, markers):
    require(path.stat().st_size <= MAX_LOG, f"{path.name} exceeds log scan budget")
    contents = path.read_bytes()
    return {
        "bytes": len(contents),
        "sha256": hashlib.sha256(contents).hexdigest(),
        "controlSeen": control in contents,
        "markerHits": sorted(label for label, value in markers.items() if value in contents),
    }


def record_line(log, prefix):
    matches = [line[len(prefix):] for line in log.splitlines() if line.startswith(prefix)]
    require(len(matches) == 1, f"Expected exactly one {prefix.decode().strip()} record")
    return json.loads(matches[0])


def reuse_ports(ports):
    with contextlib.ExitStack() as stack:
        for port in ports.values():
            listener = stack.enter_context(socket.socket())
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", port))


def prepare(scratch, repo, mix_cache, hex_cache):
    archive = scratch / "source.tar"
    with archive.open("xb") as stream:
        subprocess.run(["git", "-C", repo, "archive", SOURCE, "hosted", REGISTRATION_RUNNER],
                       stdout=stream, timeout=20, check=True, env=GIT_ENV)
    with tarfile.open(archive) as source:
        require(sum(member.size for member in source.getmembers()) < INPUT_LIMIT,
                "Pinned archive exceeds input budget")
        source.extractall(scratch, filter="data")
    archive.unlink()

    (scratch / "tmp").mkdir()
    cache_inputs = [hex_cache / "packages", mix_cache / "archives"]
    for name in ("cache.bin", "cache.ets"):
        if (hex_cache / name).is_file():
            cache_inputs.append(hex_cache / name)
    require(sum(size(path) if path.is_dir() else path.stat().st_size for path in cache_inputs)
            < INPUT_LIMIT, "Locked dependency cache exceeds input budget")
    for path in cache_inputs:
        target = scratch / ("mix" if path.name == "archives" else "hex") / path.name
        target.parent.mkdir(exist_ok=True)
        if path.is_dir():
            shutil.copytree(path, target)
        else:
            shutil.copyfile(path, target)

    # Test-only overlay in the private archive. Apply after checking both anchors.
    host = scratch / "hosted"
    registration = host / TEST_DIR / "application_registration_proof_test.exs"
    original = registration.read_text()
    helper = "  defp install_create_surface do"
    case = "  use ExUnit.Case, async: false"
    require(original.count(helper) == original.count(case) == 1,
            "Pinned registration fixture differs from expected layout")
    registration.write_text(original.replace(helper, "  def install_create_surface do").replace(
        case, case + "\n  @moduletag :privacy_stock_registration"
    ))
    with (host / TEST).open("xb") as stream:
        stream.write((HERE / TEST.name).read_bytes())

    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("registration_runner", scratch / REGISTRATION_RUNNER)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    return host, fixture


def build(host, fixture, env, scratch, receipt):
    for name, command in (
        ("deps", ["mix", "deps.get", "--check-locked"]),
        ("compile", ["mix", "compile"]),
    ):
        log = scratch / (name + ".log")
        with log.open("xb") as stream:
            with fixture.owned(command, host, env, stream) as process:
                status = wait(process, 120, scratch, receipt)
        receipt["preparation"][name] = {"command": command, "exit": status}
        if status:
            print(log.read_bytes()[-4000:].decode(errors="replace"), file=sys.stderr)
        require(status == 0, f"Offline {name} failed")


def run_profile(mode, host, fixture, base_env, scratch, pg, receipt):
    result = {"mode": mode}
    receipt["profiles"].append(result)
    with fixture.scratch(scratch) as run:
        port = fixture.free_port()
        env = dict(base_env, TMPDIR=str(run), PRIVACY_SCRATCH=str(run), PRIVACY_MODE=mode,
                   MIXER_BROWSER_STORAGE_PORT=str(port),
                   MIXER_BROWSER_CATALOG_FIXTURE_ROOT=str(run))
        pg_log = run / "postgres.log"
        app_log = run / "phoenix.log"
        postgres = [pg / "postgres", "-D", run / "pg", "-h", "127.0.0.1", "-p", str(port),
                    "-k", "", "-c", "fsync=off", "-c", "jit=off"]
        psql = [pg / "psql", "-XqAt", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1",
                "-p", str(port), "-U", "fixture_admin", "-d", "postgres"]
        init = [pg / "initdb", "-D", run / "pg", "-U", "fixture_admin", "--locale=C",
                "--encoding=UTF8", "--auth=trust", "--no-sync"]

        with (run / "initdb.log").open("xb") as output:
            with fixture.owned(init, run, env, output) as setup:
                require(wait(setup, 20, scratch, receipt) == 0, "PostgreSQL initdb failed")

        def sql(query):
            return subprocess.run(psql + ["-c", query], env=env, cwd=run,
                                  capture_output=True, timeout=4)

        with pg_log.open("xb") as output:
            with fixture.owned(postgres, run, env, output) as db:
                result["postgresProcessGroup"] = db.pid
                fixture.wait_until(lambda: sql("SELECT 1").returncode == 0, db, 12)
                require(sql(fixture.ROLES).returncode == 0, "Fixture role installation failed")
                settings = sql("""
                    SELECT name || '=' || setting FROM pg_settings WHERE name IN
                    ('log_destination','logging_collector','log_statement',
                     'log_min_error_statement','log_parameter_max_length_on_error')
                    ORDER BY name
                """)
                require(settings.returncode == 0, "PostgreSQL logging settings unavailable")
                result["postgresSettings"] = dict(line.split("=", 1)
                                                  for line in settings.stdout.decode().splitlines())
                require(result["postgresSettings"] == {
                    "log_destination": "stderr", "log_min_error_statement": "error",
                    "log_parameter_max_length_on_error": "0", "log_statement": "none",
                    "logging_collector": "off",
                }, "PostgreSQL logging differs from the stock control")
                control = sql("DO $$ BEGIN RAISE LOG 'privacy fixture PostgreSQL log control'; END $$")
                require(control.returncode == 0, "PostgreSQL log control failed")

                command = ["mix", "test", "--seed", "0", "--max-cases", "1",
                           "--exclude", "privacy_stock_registration", str(TEST)]
                with app_log.open("xb") as app_output:
                    with fixture.owned(command, host, env, app_output) as app:
                        result["mixProcessGroup"] = app.pid
                        result["exit"] = wait(app, 75, scratch, receipt)
                result["mixGroupObservedAbsent"] = True
                remaining = sql("SELECT count(*) FROM pg_database "
                                "WHERE datname='browser_ordinary_installation_r1422'")
                result["databaseDropped"] = remaining.returncode == 0 and remaining.stdout.strip() == b"0"
            result["postgresGroupObservedAbsent"] = True

        marker_file = run / "synthetic-markers.json"
        markers = {}
        if marker_file.exists():
            markers = {key: value.encode() for key, value in json.loads(marker_file.read_text()).items()}
            require(markers and all(markers.values()), "Fixture marker values are absent")
        log_checks = {
            "loggerStdoutStderr": summarize_log(app_log, LOGGER_CONTROL, markers),
            "postgresStderr": summarize_log(pg_log, PG_CONTROL, markers),
        }
        result["persistedLogs"] = log_checks
        log = app_log.read_bytes()
        ports = {"postgres": port}
        if b"PRIVACY_LISTENERS " in log:
            ports.update(record_line(log, b"PRIVACY_LISTENERS "))
        reuse_ports(ports)
        result["reusableLoopbackPorts"] = ports

        if result["exit"]:
            # Diagnostics contain only synthetic fixture data. Remove known marker values.
            tail = log[-4500:]
            for label, value in markers.items():
                tail = tail.replace(value, f"[{label}]".encode())
            print(tail.decode(errors="replace"), file=sys.stderr)
        require(result["exit"] == 0, f"{mode} hosted HTTP fixture failed")
        require(set(ports) == {"phoenix", "authorization", "jwks", "postgres"},
                "Expected four verified local listener ports")
        require(result["databaseDropped"], "Fixture database was not dropped")
        require(markers and all(log["controlSeen"] and not log["markerHits"]
                                for log in log_checks.values()),
                f"{mode} stock log control or private marker check failed")
        result.update(record_line(log, b"PRIVACY_RESULT "))
        require(result["mode"] == mode, "Fixture reported an unexpected profile")
        result["privilegedMetadata"] = "adverse" if result["eventsWithMarkers"] else "clean"
        print(f"{mode}: enrolled HTTP and stock logs passed, "
              f"privileged metadata {result['privilegedMetadata']}", flush=True)
    result["profileScratchRemoved"] = not run.exists()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, default=Path("/opt/homebrew/opt/postgresql@17/bin"))
    parser.add_argument("--hex-cache", type=Path, default=Path.home() / ".hex")
    parser.add_argument("--mix-cache", type=Path, default=Path.home() / ".mix")
    parser.add_argument("--receipt", type=Path, help="Write sanitized evidence to a new file")
    parser.add_argument("--require-clean-telemetry", action="store_true",
                        help="Exit 2 if a privileged subscriber observed a private marker")
    args = parser.parse_args()

    repo = HERE.parents[2]
    require(not args.receipt or not args.receipt.exists(), "Receipt path already exists")
    require(version(["git", "-C", repo, "rev-parse", SOURCE + "^"], GIT_ENV) == BASE,
            "Corrected source is unavailable or does not descend directly from exact v57")
    hosted_tree = version(["git", "-C", repo, "rev-parse", SOURCE + ":hosted"], GIT_ENV)
    tree = version(["git", "-C", repo, "rev-parse", SOURCE + "^{tree}"], GIT_ENV)
    pg = args.pg_bin.resolve(strict=True)
    os.umask(0o077)
    # Child processes inherit focused per-file and crash-dump limits.
    _, maximum = resource.getrlimit(resource.RLIMIT_FSIZE)
    resource.setrlimit(resource.RLIMIT_FSIZE, (FILE_LIMIT, maximum))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    local = repo / "verification" / "local"
    local.mkdir(exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="l07-hosted-privacy-", dir=local))
    preserve = False
    receipt = {
        "startedAtUTC": datetime.now(timezone.utc).isoformat(),
        "baseCommit": BASE, "commit": SOURCE, "tree": tree, "hostedTree": hosted_tree,
        "requireCleanTelemetry": args.require_clean_telemetry,
        "scratchCeilingBytes": CEILING, "scratchStopThresholdBytes": STOP_AT,
        "scratchPeakSampleBytes": 0, "perFileLimitBytes": FILE_LIMIT,
        "fixtureSHA256": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                          for name in ("run.py", TEST.name)},
        "fixtureOverlay": "Expose and exclude the stock application registration test helper in "
                          "the archive. Add the privacy ExUnit test and use the existing second "
                          "provider mode. Its endpoint keeps the corrected runtime HTTP options "
                          "and uses only an ephemeral loopback address.",
        "externalEgress": "No external service used. No packet capture or general egress proof.",
        "preparation": {}, "profiles": [],
    }
    status = 1
    try:
        host, fixture = prepare(scratch, repo, args.mix_cache, args.hex_cache)
        env = {
            "PATH": os.environ["PATH"], "HOME": str(scratch), "TMPDIR": str(scratch / "tmp"),
            "MIX_HOME": str(scratch / "mix"), "HEX_HOME": str(scratch / "hex"), "LC_ALL": "C",
            "HEX_OFFLINE": "1", "MIX_ENV": "test", "ERL_FLAGS": "+S 4:4",
        }
        receipt["tools"] = {
            "os": " ".join(os.uname()[index] for index in (0, 2, 4)),
            "git": version(["git", "--version"], env),
            "python": sys.version.split()[0],
            "mix": version(["mix", "--version"], env),
            "postgres": version([pg / "postgres", "--version"], env),
        }
        try:
            build(host, fixture, env, scratch, receipt)
            for profile in PROFILES:
                run_profile(profile, host, fixture, env, scratch, pg, receipt)
        except fixture.UnknownCustody:
            preserve = True
            raise
        adverse = any(profile["privilegedMetadata"] == "adverse" for profile in receipt["profiles"])
        status = 2 if adverse and args.require_clean_telemetry else 0
    except (OSError, RuntimeError, TimeoutError, subprocess.SubprocessError) as error:
        receipt["error"] = str(error)
        print(error, file=sys.stderr)
    finally:
        if preserve:
            receipt["heldScratch"] = str(scratch)
        else:
            shutil.rmtree(scratch)
        receipt["scratchRemoved"] = not scratch.exists()
        receipt["exit"] = status
        if args.receipt:
            with args.receipt.open("x") as stream:
                json.dump(receipt, stream, indent=2, sort_keys=True)
                stream.write("\n")
    return status


if __name__ == "__main__":
    sys.exit(main())
