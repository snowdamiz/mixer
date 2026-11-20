#!/usr/bin/env python3
"""Replay exactly one combined L07 checkout and signed delivery control."""

import argparse
import base64
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
from urllib.parse import urlencode


PIN = "ea4954ff38a52d231f4b9961fc7e03f684499f72"
REMOTE = "https://github.com/snowdamiz/mixer.git"
FIXTURE = Path(__file__).resolve().parent
ROOT = FIXTURE.parents[2]
HTTP_HOST = "127.0.0.1"
RELEASE_SCOPE = "/v3/orgs/org-a/projects/project-a"
OBSERVATION = "L07_COMBINED "
LISTENERS = "L07_LISTENERS "


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def port():
    with socket.socket() as candidate:
        candidate.bind((HTTP_HOST, 0))
        return candidate.getsockname()[1]


def rebind(number):
    with socket.socket() as probe:
        probe.settimeout(1)
        require(probe.connect_ex((HTTP_HOST, number)) != 0, f"listener still open at {number}")
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind((HTTP_HOST, number))
        probe.listen(1)
    return number


def retry_ready(process, check, seconds=7):
    deadline = time.monotonic() + seconds
    while process.poll() is None and time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except (ConnectionError, TimeoutError):
            pass
        time.sleep(0.05)
    raise RuntimeError(f"readiness failed for owned PID {process.pid}")


class Run:
    def __init__(self, scratch, pg_bin, receipt, *, rehearse_alert=False):
        self.scratch = scratch
        self.source = scratch / "source"
        self.hosted = self.source / "hosted"
        self.pg = pg_bin
        self.receipt = receipt
        self.rehearse_alert = rehearse_alert
        self.pending = {}
        self.ports = {}
        self.receipt["commands"] = []
        tmp = scratch / "tmp"
        tmp.mkdir()
        self.env = {
            "PATH": str(pg_bin) + os.pathsep + os.environ["PATH"],
            "HOME": str(Path.home()),
            "TMPDIR": str(tmp),
            "HEX_HOME": str(scratch / "hex"),
            "MIX_ENV": "test",
            "ERL_FLAGS": "+S 4:4",
            "ERL_CRASH_DUMP_SECONDS": "0",
            "GOCACHE": str(scratch / "go-cache"),
            "GOMODCACHE": str(scratch / "go-modules"),
            "GOFLAGS": "-modcacherw",
            "GOWORK": "off",
            "GOTOOLCHAIN": "local",
            "TZ": "UTC",
            "LC_ALL": "C",
            "PGCONNECT_TIMEOUT": "2",
            "PGOPTIONS": "-c statement_timeout=5000 -c lock_timeout=5000",
        }

    @contextmanager
    def start(self, label, argv, *, cwd=None, env=None, stop=signal.SIGTERM, timeout=30):
        log = self.scratch / f"{label}.log"
        argv = list(map(str, argv))
        row = {"label": label, "argv": argv, "cwd": str(cwd or ROOT),
               "started_UTC": datetime.now(timezone.utc).isoformat()}
        self.receipt["commands"].append(row)
        with log.open("xb") as stream:
            process = subprocess.Popen(argv, cwd=cwd or ROOT, env=self.env if env is None else env,
                                       stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            row["pid_pgid"] = process.pid
            self.pending[process.pid] = label
            try:
                yield process
            finally:
                if process.poll() is None:
                    try:
                        process.send_signal(stop)
                    except ProcessLookupError:
                        pass
                try:
                    row["exit"] = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired as exc:
                    raise RuntimeError(f"terminal custody unknown for {label}") from exc
                row["direct_child_reaped"] = True
                deadline = time.monotonic() + 2
                while True:
                    try:
                        os.killpg(process.pid, 0)
                    except ProcessLookupError:
                        break
                    require(time.monotonic() < deadline, f"owned group still present for {label}")
                    time.sleep(0.05)
                row["group_absent"] = True
                del self.pending[process.pid]
        row["output_sha256"] = sha256(log)

    def command(self, label, argv, *, cwd=None, env=None, timeout=30, check=True):
        with self.start(label, argv, cwd=cwd, env=env, timeout=5) as process:
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(f"{label} timed out after {timeout}s") from exc
        log = self.scratch / f"{label}.log"
        output = log.read_bytes()
        if check:
            require(code == 0, f"{label} exited {code}: {output[-4000:].decode(errors='replace')}")
        return code, output

    def prepare(self, *, release_only=False):
        _, remote = self.command("public-main", ["git", "ls-remote", REMOTE, "refs/heads/main"])
        main = remote.decode().split()[0]
        if main != PIN:
            self.command("public-pin-ancestry", ["git", "merge-base", "--is-ancestor", PIN, main])
        _, tree = self.command("pin-tree", ["git", "rev-parse", f"{PIN}^{{tree}}",
                                           f"{PIN}:hosted", f"{PIN}:services"])
        archive = self.scratch / "source.tar"
        self.command("archive", ["git", "archive", "-o", archive, PIN, "hosted", "services",
                                "tests/integration/hosted_mixed_checkout_recovery_test.exs",
                                "tests/integration/public-update"])
        self.source.mkdir()
        with tarfile.open(archive) as source:
            source.extractall(self.source, filter="data")
        self.test = self.source / "tests/integration/checkout_release_test.exs"
        shutil.copyfile(FIXTURE / "checkout_release_test.exs", self.test)
        git_tree, hosted_tree, services_tree = tree.decode().split()
        self.receipt["source"] = {
            "revision": PIN, "public_main_at_run": main, "tree": git_tree,
            "hosted_tree": hosted_tree, "services_tree": services_tree,
            "archive_sha256": sha256(archive),
            "test_sha256": sha256(self.test),
            "runner_sha256": sha256(Path(__file__)),
        }
        self.receipt["tools"] = {
            key: self.command(f"{key}-version", argv)[1].decode().strip()
            for key, argv in (
                ("postgres", [self.pg / "postgres", "--version"]),
                ("elixir", ["elixir", "--version"]),
                ("go", ["go", "version"]),
            )
        }
        if not release_only:
            self.command("locked-hosted-deps", ["mix", "deps.get", "--check-locked"], cwd=self.hosted)
            self.command("hosted-compile", ["mix", "compile", "--warnings-as-errors"],
                         cwd=self.hosted, timeout=100)
            self.command("test-format", ["mix", "format", "--check-formatted", self.test], cwd=self.hosted)

        overlay = self.scratch / "signer-overlay.json"
        overlay.write_text(json.dumps({"Replace": {
            str(self.source / "services/internal/publicupdatefixture/fixture_test.go"):
            str(self.source / "tests/integration/public-update/fixture_test.go")
        }}))
        self.service = self.scratch / "mixer-service"
        self.signer = self.scratch / "fixture-signer"
        services = self.source / "services"
        self.command("build-release-service", ["go", "build", "-mod=readonly", "-o",
                     self.service, "./cmd/mixer-service"], cwd=services, timeout=120)
        self.command("build-tracked-signer", ["go", "test", "-vet=off", "-mod=readonly",
                     "-overlay", overlay, "-c", "-o", self.signer, "./internal/publicupdatefixture"],
                     cwd=services, timeout=90)

    @contextmanager
    def postgres(self, label, *, host, number, owner, sockets=None):
        data = self.scratch / f"{label}-data"
        local_auth, host_auth = ("trust", "reject") if sockets else ("reject", "trust")
        self.command(f"{label}-init", [self.pg / "initdb", "-D", data, "-U", owner,
                     f"--auth-local={local_auth}", f"--auth-host={host_auth}",
                     "--no-locale", "--encoding=UTF8"])
        settings = ["-h", "" if sockets else host, "-k", str(sockets or ""), "-p", str(number),
                    "-c", "timezone=UTC", "-c", "unix_socket_permissions=0700"]
        client = [self.pg / "psql", "-XAtqw", "-v", "ON_ERROR_STOP=1", "-h", host,
                  "-p", str(number), "-U", owner, "-d", "postgres"]
        with self.start(label, [self.pg / "postgres", "-D", data, *settings],
                        stop=signal.SIGINT) as process:
            def identify():
                result = subprocess.run(client + ["-c", "SHOW data_directory"], env=self.env,
                                        capture_output=True, timeout=3)
                return result.stdout.decode().strip() if result.returncode == 0 else None

            require(Path(retry_ready(process, identify)) == data, f"{label} data directory mismatch")
            yield client
        require(process.returncode == 0 and not (data / "postmaster.pid").exists(),
                f"{label} did not shut down cleanly")
        if sockets:
            require(not any(sockets.iterdir()), f"{label} left a Unix socket or lock")

    def prepare_browser(self, client):
        # Same roles and initial database as provision_browser_read_fixture in hosted/scripts/test-local.py.
        self.command("ordinary-browser-roles", client + ["-c", """
            CREATE ROLE browser_admin LOGIN SUPERUSER;
            CREATE ROLE browser_schema_owner NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
            CREATE ROLE browser_writer NOLOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
            CREATE ROLE browser_lifecycle LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
            CREATE ROLE browser_ordinary LOGIN NOSUPERUSER NOBYPASSRLS NOINHERIT;
        """])
        self.command("ordinary-browser-database", client + ["-c",
                     "CREATE DATABASE browser_storage OWNER browser_schema_owner"])

    @contextmanager
    def release(self, sockets, client, number):
        directory = self.scratch / "signed"
        directory.mkdir()
        tokens = {role: secrets.token_urlsafe(32) for role in ("PUBLISHER", "FOREIGN", "READER")}
        self.command("sign-v3", [self.signer, "-test.run", "^TestSignInputs$", "-test.timeout=10s"],
                     cwd=directory, env={**self.env,
                     "FIXTURE_DIRECTORY": str(directory), "FIXTURE_ADDRESS": f"{HTTP_HOST}:{number}",
                     **{f"FIXTURE_{role}": token for role, token in tokens.items()}})
        config_path = directory / "service.json"
        config = json.loads(config_path.read_bytes())
        del config["data_directory"]
        config.update(storage_backend="postgres",
                      postgres={"connection_string_env": "MIXER_FIXTURE_RUNTIME"})
        config_path.write_text(json.dumps(config))
        dsn = f"host={sockets} port=5432 dbname=postgres sslmode=disable user="
        env = {**self.env, "MIXER_SERVICE_CONFIG": str(config_path)}
        self.command("release-real-migration", [self.service, "migrate-postgres",
                     "--connection-env", "MIXER_FIXTURE_OWNER"], cwd=directory,
                     env={**env, "MIXER_FIXTURE_OWNER": dsn + "mixer_migration_owner"})
        self.command("release-enroll-runtime", client + ["-c", """
            CREATE ROLE mixer_test_runtime LOGIN NOSUPERUSER NOCREATEROLE NOCREATEDB NOBYPASSRLS;
            GRANT mixer_release_runtime TO mixer_test_runtime;
        """])

        def request(method, path, status, *, role=None, key=None, body=None):
            headers = {"Content-Type": "application/json"}
            if role:
                headers["Authorization"] = "Bearer " + tokens[role]
            if key:
                headers["Idempotency-Key"] = key
            connection = http.client.HTTPConnection(HTTP_HOST, number, timeout=2)
            try:
                connection.request(method, path, body=body, headers=headers)
                response = connection.getresponse()
                raw = response.read(65537)
                require(response.status == status and len(raw) <= 65536,
                        f"release {method} {path} expected {status}, got {response.status}: {raw[:512]!r}")
                return raw
            finally:
                connection.close()

        with self.start("release-origin", [self.service], cwd=directory,
                        env={**env, "MIXER_FIXTURE_RUNTIME": dsn + "mixer_test_runtime"}) as process:
            ready = retry_ready(process, lambda: request("GET", RELEASE_SCOPE + "/audit", 200, role="READER"))
            require(json.loads(ready)["events"] == [], "release origin history was not empty")

            coordinates = json.loads((directory / "coordinates.json").read_bytes())
            assignment = (directory / "publish-first.json").read_bytes().rstrip(b"\n")
            manifest = (directory / "first/signed-manifest.json").read_bytes().rstrip(b"\n")
            payload = (directory / "first/payload.wasm").read_bytes()
            artifact = b'{"signed_manifest":' + manifest + b',"payload":"' + base64.b64encode(payload) + b'"}'
            digest = coordinates["first"]
            for method, path, status, key, body in [
                ("PUT", f"/artifacts/{digest}", 201, "upload", artifact),
                ("POST", "/releases/validate", 200, "validate", json.dumps({"artifact_sha256": digest})),
                ("POST", "/channels/production/publish", 200, "publish", b'{"signed_assignment":' + assignment + b"}"),
            ]:
                request(method, RELEASE_SCOPE + path, status, role="PUBLISHER",
                        key="combined-" + key, body=body)
            download = f"/v3/artifacts/{digest}?organization=org-a&project=project-a"
            offer = "/v3/updates?" + urlencode({
                **coordinates["scope"], "channel": coordinates["channel"],
                "runtime": coordinates["runtime"], "installation": coordinates["installations"]["early"],
            })
            expected_offer = directory / "expected-offer"
            expected_offer.write_bytes(b'{"artifact_url":' + json.dumps(download).replace("&", r"\u0026").encode() +
                                       b',"signed_assignment":' + assignment + b"}")
            expected_artifact = directory / "expected-artifact"
            expected_artifact.write_bytes(artifact)
            audit = request("GET", RELEASE_SCOPE + "/audit", 200, role="READER")
            require(len(json.loads(audit)["events"]) == 3, "release did not commit all three publish stages")
            request("GET", f"/v3/artifacts/{digest}?organization=org-b&project=project-b", 404)
            self.receipt["release_publication"] = {
                "upload": 201, "validate": 200, "publish": 200, "protocol": 3, "sequence": 1,
                "audit_events": 3, "foreign_public_artifact": 404, "storage": "postgresql",
            }
            base = f"http://{HTTP_HOST}:{number}"
            yield {
                "L07_RELEASE_OFFER_URL": base + offer,
                "L07_RELEASE_ARTIFACT_URL": base + download,
                "L07_EXPECTED_OFFER": str(expected_offer),
                "L07_EXPECTED_ARTIFACT": str(expected_artifact),
            }
            require(request("GET", RELEASE_SCOPE + "/audit", 200, role="READER") == audit,
                    "release audit changed during checkout control")
            self.receipt["release_publication"]["audit_unchanged"] = True
        require(process.returncode == 0, "release origin did not shut down cleanly")

    def pair25(self, sockets, scratch_parent, operator, *, checkout_burst=False):
        self.ports["release_origin"] = port()
        with ExitStack() as stack:
            release_db = stack.enter_context(self.postgres(
                "release-postgres", host=str(sockets), number=5432, owner="mixer_migration_owner",
                sockets=sockets))
            release_env = stack.enter_context(self.release(sockets, release_db, self.ports["release_origin"]))
            observation_path = self.scratch / "release-observation.json"
            observation_path.write_text(json.dumps({
                name: {"url": release_env[f"L07_RELEASE_{name.upper()}_URL"],
                       "sha256": sha256(Path(release_env[f"L07_EXPECTED_{name.upper()}"]))}
                for name in ("offer", "artifact")
            }))
            output = self.scratch / "pair25-result.json"
            child_scratch = Path(tempfile.mkdtemp(prefix="p25-", dir=scratch_parent))
            custody = child_scratch / "custody.jsonl"
            custody.touch(exist_ok=False)
            self.receipt["pair25Scratch"] = str(child_scratch)
            command = [sys.executable, "-B", ROOT / "tests/integration/l05-pair25-http/run.py",
                       "--worker-crash", "--reserved-scratch", child_scratch, "--receipt", output,
                       "--release-observation", observation_path, "--pg-bin", self.pg]
            if checkout_burst:
                command.append("--checkout-burst")
            if operator is None:
                command.extend(("--inert-finish-on-reopen", "--seconds", "100"))
            else:
                command.extend(("--operator", operator, "--seconds", "900"))
            self.receipt["nestedCustodyUnresolved"] = True
            env = {**self.env, "HEX_HOME": os.environ["HEX_HOME"]}
            try:
                code, stdout = self.command("pair25-outage", command, env=env, timeout=1_230, check=False)
                evidence = json.loads(output.read_bytes())
                self.receipt["pair25"] = evidence
                self.receipt["nestedCustodyUnresolved"] = not evidence.get("scratchRemoved", False)
                require(code == 0 and evidence.get("passed") and evidence.get("nativeDispatchResolved")
                        and evidence["combinedOutage"]["sameBuildAndObanJob"]
                        and evidence["workerStarts"] == evidence["runnerStarts"] == 1
                        and evidence["terminalBuild"]["state"] == "native_succeeded"
                        and evidence["capacityReleaseEvent"] == "coordinator:1:1:completed"
                        and evidence["capacityReleased"] is True
                        and evidence["cancelAttempts"] == 0 and evidence["cancellationExercised"] is False,
                        "Pair25 checkout and completion failed: " + stdout[-3_000:].decode(errors="replace"))
                if checkout_burst:
                    require("burst" in evidence["combinedOutage"], "Pair25 checkout burst evidence missing")
            finally:
                if self.receipt["nestedCustodyUnresolved"] and custody.is_file():
                    with custody.open("rb") as stream:
                        lines = stream.read(32_769).splitlines()
                    try:
                        self.receipt["pair25CustodyJournal"] = [json.loads(line) for line in lines]
                    except ValueError:
                        self.receipt["pair25CustodyJournalIncomplete"] = True

    def phoenix(self, env):
        argv = ["mix", "test", "--warnings-as-errors", "--seed", "0", "--trace",
                "--only", "l07_combined_checkout_release", self.test]
        if not self.rehearse_alert:
            return self.command("phoenix-exunit", argv, cwd=self.hosted, env=env, timeout=60, check=False)

        alert_dir = self.scratch / "alert"
        alert_dir.mkdir(mode=0o700)
        event = alert_dir / "alert.json"
        with self.start("phoenix-exunit", argv, cwd=self.hosted,
                        env={**env, "L07_LOCAL_ALERT_DIR": str(alert_dir)}, timeout=5) as process:
            started = time.monotonic()
            alert = retry_ready(process, lambda: json.loads(event.read_bytes()) if event.is_file() else None,
                                seconds=50)
            require(alert == {"code": "build_checkout_unavailable", "http_status": 503},
                    "unexpected local test alert")
            self.receipt["local_alert"] = alert
            print("LOCAL_TEST_ALERT " + json.dumps(alert, separators=(",", ":")), flush=True)
            with (alert_dir / "ack").open("xb"):
                pass
            self.receipt["local_alert"]["acknowledged"] = True
            code = process.wait(timeout=max(0.1, started + 60 - time.monotonic()))
        return code, (self.scratch / "phoenix-exunit.log").read_bytes()

    def exercise(self, sockets):
        self.ports["postgres_browser"] = port()
        self.ports["release_origin"] = port()
        require(len(set(self.ports.values())) == 2, "loopback port collision")
        with ExitStack() as stack:
            release_db = stack.enter_context(self.postgres(
                "release-postgres", host=str(sockets), number=5432, owner="mixer_migration_owner",
                sockets=sockets))
            browser_port = self.ports["postgres_browser"]
            browser_db = stack.enter_context(self.postgres(
                "browser-postgres", host=HTTP_HOST, number=browser_port, owner="mixer_fixture"))
            self.prepare_browser(browser_db)
            release_env = stack.enter_context(self.release(sockets, release_db, self.ports["release_origin"]))
            catalog = self.scratch / "catalog"
            catalog.mkdir()
            code, output = self.phoenix({
                **self.env, **release_env, "MIXER_BROWSER_STORAGE_PORT": str(browser_port),
                "MIXER_BROWSER_CATALOG_FIXTURE_ROOT": str(catalog),
            })
            lines = output.decode(errors="replace").splitlines()
            self.receipt["live_checkpoints"] = [line for line in lines if "L07_CHECKPOINT " in line]
            for line in lines:
                if LISTENERS in line:
                    self.ports.update(json.loads(line.split(LISTENERS, 1)[1]))
                if OBSERVATION in line:
                    self.receipt["observed"] = json.loads(line.split(OBSERVATION, 1)[1])
            require(code == 0 and "observed" in self.receipt,
                    "focused ExUnit failed: " + "\n".join(lines[-75:]))
            self.receipt["exunit"] = {"focused_tests": 1, "failures": 0}
            if self.rehearse_alert:
                observed = self.receipt["observed"]
                require(observed["exact_key_retry_status"] == 201 and observed["retry_replay_status"] == 200
                        and observed["jobs_one_per_build"], "local alert recovery checks failed")
                self.receipt["local_alert"]["resolved"] = True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--pg-bin", type=Path, default=Path("/opt/homebrew/opt/postgresql@17/bin"))
    parser.add_argument("--rehearse-alert", action="store_true",
                        help="deliver and acknowledge the local test alert during checkout refusal")
    parser.add_argument("--pair25-scratch-parent", type=Path,
                        help="run the Pair25 worker outage with signed delivery, using a short private scratch parent")
    parser.add_argument("--operator", type=Path, help="approved Pair25 operator config for the real compiler retry")
    parser.add_argument("--checkout-burst", action="store_true",
                        help="overlap four same-key build retries with signed reads in Pair25 mode")
    args = parser.parse_args()
    if args.pair25_scratch_parent and (args.rehearse_alert or not os.environ.get("HEX_HOME")):
        parser.error("the Pair25 replay requires a private lock-verified HEX_HOME and no alert flag")
    if args.operator and not args.pair25_scratch_parent:
        parser.error("--operator requires --pair25-scratch-parent")
    if args.checkout_burst and not args.pair25_scratch_parent:
        parser.error("--checkout-burst requires --pair25-scratch-parent")
    args.receipt = args.receipt.resolve()
    require(not args.receipt.exists() and args.receipt.parent.is_dir(), "choose a new receipt path")
    os.umask(0o077)
    local = ROOT / "verification/local"
    local.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="l07-combined-replay.", dir=local))
    sockets = None
    receipt = {
        "schema": 1, "gate": "L07", "whole_gate_passed": False, "status": "FAILED",
        "recorded_UTC": datetime.now(timezone.utc).isoformat(),
        "scope": "Ordinary fixture API and PostgreSQL with one deliberate checkout refusal. Signed release v3 through the developer origin over IPv4 loopback HTTP with a separate PostgreSQL cluster and private Unix socket.",
        "dependencies": "Locked public Elixir and Go dependencies, local synthetic issuer and release credentials. No billing provider or payment credentials.",
        "limits": "One refused POST and one signed offering. No TLS delivery qualification, build processor, native worker, Docker, devices, deployment, or production.",
    }
    run = Run(scratch, args.pg_bin, receipt, rehearse_alert=args.rehearse_alert)
    try:
        run.prepare(release_only=bool(args.pair25_scratch_parent))
        # PostgreSQL limits sockaddr_un length. Use only this freshly owned directory.
        sockets = Path(tempfile.mkdtemp(prefix="mixer-l07-sock.", dir="/tmp"))
        if args.pair25_scratch_parent:
            receipt["scope"] = "One ordinary Pair25 worker outage with an original-key checkout refusal and signed PostgreSQL delivery."
            receipt["limits"] = "Real managed compiler in operator mode. Inert runner in the default Pair25 mode."
            run.pair25(sockets, args.pair25_scratch_parent.resolve(strict=True),
                       args.operator.resolve(strict=True) if args.operator else None,
                       checkout_burst=args.checkout_burst)
            receipt["status"] = "PASS_SCOPED_PAIR25_WORKER_OUTAGE_RELEASE"
        else:
            run.exercise(sockets)
            receipt["status"] = "PASS_SCOPED_COMBINED_CHECKOUT_RELEASE"
    except Exception as exc:
        receipt["error"] = str(exc)
    finally:
        cleanup = receipt["cleanup"] = {"unresolved_groups": run.pending, "ports": run.ports}
        try:
            require(not run.pending, f"retaining scratch for unresolved groups: {run.pending}")
            require(not receipt.get("nestedCustodyUnresolved"), "retaining inputs for unresolved Pair25 custody")
            cleanup["ports_rebound"] = {label: rebind(number) for label, number in run.ports.items()}
            if sockets is not None:
                sockets.rmdir()
                cleanup["private_socket_closed_and_removed"] = not sockets.exists()
            shutil.rmtree(scratch)
            cleanup["scratch_removed"] = not scratch.exists()
        except (OSError, RuntimeError) as exc:
            cleanup.update(error=str(exc), retained_scratch=str(scratch),
                           retained_socket_directory=str(sockets) if sockets and sockets.exists() else None)
            receipt["status"] = "FAILED"
        args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: value for key, value in receipt.items() if key != "commands"}, indent=2))
    return 0 if receipt["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
