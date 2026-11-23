#!/usr/bin/env python3
"""Bounded stock Phoenix/PostgreSQL D6 release fixture, with root-only XCTest."""
import argparse
import base64
from contextlib import contextmanager
import http.client
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from urllib.parse import urlencode
import uuid

import hashlib
HERE = Path(__file__).resolve().parent
from prepare import ORIGIN_PORT, require, write


def read(path):
    return json.loads(path.read_bytes())

def digest(value):
    return hashlib.sha256(value).hexdigest()

PORT = ORIGIN_PORT
ORIGIN = f"http://127.0.0.1:{PORT}"

OBSERVER = "FieldLogUITests/D6ReleaseObserver/testBaselineReviewRollbackAndOffline"
TENANT = "/v3/orgs/mixer-local/projects/fieldlog"

def absent(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return True
    return False

def reusable(port):
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        sock.listen()

def request(path, method="GET", token=None):
    conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=4)
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        conn.request(method, path, headers=headers)
        result = conn.getresponse()
        return result.status, result.read(8 * 1024 * 1024)
    finally:
        conn.close()

class Run:
    def __init__(self, args, work):
        self.args, self.work = args, work
        self.receipt = {"scope": "stock Phoenix HTTP on loopback, restored disposable PostgreSQL fixture, "
                                 "loopback SCRAM connections without TLS, API and restricted roles",
                        "mode": args.mode, "authenticatedManagedBuildArtifactDownloadInThisLease": False,
                        "managedBuildHistoricalStateAvailable": False,
                        "nativeExecuted": False, "commands": {}, "offers": []}
        self.children = {}
        self.workspace = uuid.uuid4()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.pgport = sock.getsockname()[1]
        self.env = {k: os.environ[k] for k in ("PATH", "HOME", "SHELL", "DEVELOPER_DIR")
                    if k in os.environ}
        self.env["HOME"] = str(args.work / "home")
        self.env.update(MIX_ENV="test", ERL_FLAGS="+S 4:4", HEX_OFFLINE="1", LANG="C",
                        TMPDIR=str(work), HEX_HOME=str(args.work / "hex"), MIX_HOME=str(args.work / "mix"), D6_RUN=str(work), PGPORT=str(self.pgport),
                        PGDATABASE="postgres", MIXER_RELEASE_FIXTURE_SCRATCH=str(work),
                        MIXER_HOSTED_ROLE="api", MIXER_DATABASE_HOST="127.0.0.1",
                        MIXER_DATABASE_USER="mixer_replay_writer", MIXER_DATABASE_POOL_SIZE="2",
                        MIXER_SECRET_KEY_BASE=secrets.token_hex(48), MIXER_HTTP_PORT=str(PORT),
                        MIXER_HTTP_BIND="127.0.0.1", MIXER_LOCAL_RELEASE_WRITER_ENABLED="true",
                        MIXER_LOCAL_ARTIFACT_UPLOAD_ENABLED="true",
                        MIXER_DATABASE_PASSWORD=secrets.token_hex(24),
                        MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD=secrets.token_hex(24),
                        MIXER_LOCAL_ARTIFACT_UPLOAD_PASSWORD=secrets.token_hex(24))

    def start(self, label, *argv, cwd=None, env=None, stdin=None):
        args = [str(item) for item in argv]
        with (self.work / (label + ".log")).open("xb") as log:
            child = subprocess.Popen(args, cwd=cwd, env=env or self.env, start_new_session=True,
                                     stdin=stdin, stdout=log, stderr=subprocess.STDOUT)
        self.children[label] = child
        self.receipt["commands"][label] = {"argv": args, "pid": child.pid}
        return child

    def close(self, label, signum=None, timeout=20):
        child = self.children[label]
        if signum is not None and child.poll() is None:
            os.killpg(child.pid, signum)
        code = child.wait(timeout=timeout)
        deadline = time.monotonic() + 3
        while not absent(child.pid) and time.monotonic() < deadline:
            time.sleep(.05)
        gone = absent(child.pid)
        path = self.work / (label + ".log")
        self.receipt["commands"][label].update(exit=code, reaped=True, groupAbsent=gone,
                                               logSHA256=digest(path.read_bytes()))
        require(gone, f"UNKNOWN process-group custody for {label} {child.pid}")
        del self.children[label]
        return code

    def command(self, label, *argv, cwd=None, env=None, stdin=None, timeout=65):
        self.start(label, *argv, cwd=cwd, env=env, stdin=stdin)
        code = self.close(label, timeout=timeout)
        require(code == 0, f"{label} exited {code}; see {label}.log")
        return (self.work / (label + ".log")).read_text().strip()

    def mix(self, label, action, **values):
        env = dict(self.env, D6_COMMAND=action, MIXER_DATABASE_NAME=self.env["PGDATABASE"], **values)
        argv = ("mix", "run", "--no-compile", "--no-start", HERE / "release.exs")
        if action == "serve":
            return self.start(label, *argv, cwd=self.args.work / "hosted", env=env)
        return self.command(label, *argv, cwd=self.args.work / "hosted", env=env)

    def setup(self):
        self.receipt["toolVersions"] = {
            "postgres": self.command("postgres-version", "postgres", "--version"),
            "elixir": self.command("elixir-version", "elixir", "--version"),
        }
        reusable(PORT)
        reusable(self.pgport)
        data = self.work / "db"
        self.command("initdb", "initdb", "-D", data, "-U", "mixer_replay_admin",
                     "--auth=reject", "--no-sync", "--locale=C", "--encoding=UTF8")
        (data / "pg_hba.conf").write_text("local all all trust\n"
            "host all mixer_replay_writer,mixer_release_delivery,mixer_artifact_uploader 127.0.0.1/32 scram-sha-256\n")
        child = self.start("postgres", "postgres", "-D", data, "-h", "127.0.0.1",
                           "-k", self.work, "-p", self.pgport, "-c", "jit=off")
        pidfile = data / "postmaster.pid"
        deadline = time.monotonic() + 12
        while True:
            fields = pidfile.read_text().splitlines() if pidfile.is_file() else []
            if len(fields) >= 8 and fields[0] == str(child.pid) and fields[7].strip() == "ready":
                break
            require(time.monotonic() < deadline and child.poll() is None, "PostgreSQL readiness failed")
            time.sleep(.05)
        self.conn = ("-h", self.work, "-p", str(self.pgport), "-U", "mixer_replay_admin", "-w")
        self.psql("create-source-db", "CREATE DATABASE d6_seed")
        self.env["PGDATABASE"] = "d6_seed"
        self.mix("provision", "provision")
        self.command("dump", "pg_dump", *self.conn, "-Fc", "-f", self.work / "fixture.dump", "d6_seed")
        self.psql("create-target-db", "CREATE DATABASE d6_replay")
        self.command("restore", "pg_restore", *self.conn, "--exit-on-error", "-1",
                     "-d", "d6_replay", self.work / "fixture.dump")
        self.env["PGDATABASE"] = "d6_replay"
        self.command("expiry-constraints", "psql", *self.conn, "-v", "ON_ERROR_STOP=1",
                     "-d", "d6_replay", "-f", HERE / "restore-expiry.sql")
        self.command("artifact-key-constraint", "psql", *self.conn, "-v", "ON_ERROR_STOP=1",
                     "-d", "d6_replay", "-f", self.args.work / "tests/integration/phoenix-release-restore/restore-artifact-key.sql")
        # Password SQL is written only inside the private lease and sent on stdin.
        password_sql = "\n".join(f"ALTER ROLE {role} PASSWORD '{self.env[key]}';" for role, key in [
            ("mixer_replay_writer", "MIXER_DATABASE_PASSWORD"),
            ("mixer_release_delivery", "MIXER_LOCAL_RELEASE_DELIVERY_PASSWORD"),
            ("mixer_artifact_uploader", "MIXER_LOCAL_ARTIFACT_UPLOAD_PASSWORD")])
        password_file = self.work / "passwords.sql"
        password_file.write_text(password_sql)
        with password_file.open("rb") as commands:
            self.command("restricted-logins", "psql", *self.conn, "-v", "ON_ERROR_STOP=1",
                         "-d", "d6_replay", stdin=commands)
        password_file.unlink()

    def psql(self, name, sql):
        return self.command(name, "psql", *self.conn, "-At", "-v", "ON_ERROR_STOP=1",
                            "-d", self.env["PGDATABASE"], "-c", sql)

    def offer(self, sequence, folder, config):
        status, body = request(self.offer_path)
        if not sequence:
            require(status == 204 and not body, f"Expected empty offer, got {status}")
            return
        require(status == 200, f"Offer returned {status}")
        offer_sha = digest(body)
        offer = json.loads(body)
        assignment = read(folder / "assignment.json" if sequence != 3 else self.args.input / "fixture/rollback.json")
        require(offer["signed_assignment"] == assignment and assignment["assignment"]["sequence"] == sequence
                and assignment["assignment"]["runtime"] == config["host"]["runtime"], "Offer differs from signed assignment")
        path = offer["artifact_url"]
        require(path.startswith("/v3/artifacts/"), "Wrong updater artifact route")
        status, body = request(path)
        require(status == 200, f"Updater artifact returned {status}")
        envelope = json.loads(body)
        name = "staged" if sequence == 2 else "baseline"
        sha = digest(base64.b64decode(envelope["payload"], validate=True))
        require(sha == self.payloads[name] and envelope["signed_manifest"] == read(folder / "signed-manifest.json"),
                "Updater artifact bytes differ")
        self.receipt["offers"].append({"sequence": sequence, "payloadSHA256": sha,
            "assignmentSHA256": digest(json.dumps(assignment, sort_keys=True).encode()),
            "artifact": assignment["assignment"]["artifact_sha256"], "HTTP": status,
            "runtime": config["host"]["runtime"], "offerHTTP": 200,
            "offerBodySHA256": offer_sha, "artifactBodySHA256": digest(body)})

    def publish(self, sequence, fixture, config):
        name = "staged" if sequence == 2 else "baseline"
        folder = fixture / name
        env = dict(self.env, MIXER_RELEASE_ORIGIN=ORIGIN,
                   MIXER_RELEASE_TOKEN=(self.work/"operator.token").read_text())
        scope = ("--organization", "mixer-local", "--project", "fieldlog", "--channel", "beta")
        if sequence < 3:
            argv = ("publish", folder, *scope, "--rollout", "100", "--assignment", folder/"assignment.json")
        else:
            digest1 = read(folder/"assignment.json")["assignment"]["artifact_sha256"]
            argv = ("rollback", digest1, *scope, "--reason", "Restore the local FieldLog baseline",
                    "--assignment", fixture/"rollback.json")
        self.command(f"stock-cli-{sequence}", self.args.cli, "update", *argv, env=env)
        self.offer(sequence, folder, config)
        return self.receipt["offers"][-1]

    def history(self, expected):
        rows = self.psql("publication-history", "SELECT sequence::text || ':' || action || ':' || "
                         "artifact_sha256 FROM mixer_release_publications ORDER BY sequence").splitlines()
        require(len(rows) == expected, "Wrong SQL publication count")
        for i, row in enumerate(self.receipt["offers"], 1):
            require(rows[i-1] == f"{i}:{'rollback' if i == 3 else 'publish'}:{row['artifact']}",
                    "Wrong SQL publication row")
        self.receipt["sqlPublicationHistory"] = rows

    def execute(self):
        fixture = self.args.input / "fixture"
        config = read(fixture/"config.json")
        require(digest(self.args.cli.read_bytes()) == self.args.cli_sha256, "Wrong stock CLI")
        seal = read(self.args.input / "seal-receipt.json")
        app = self.args.input / "Products/Debug-iphonesimulator/FieldLog.app"
        require(seal["runtime"] == config["host"]["runtime"]
                and seal["unsignedMachO"] == digest((app / "FieldLog").read_bytes())
                and seal["identitySHA256"] == digest((app / "ChecklistRelease/identity.json").read_bytes())
                and seal["rootsSHA256"] == digest((app / "ChecklistRelease/roots.json").read_bytes()),
                "release host differs from installed fixture")
        self.payloads = seal["payloads"]
        self.receipt["joinedFixture"] = seal
        self.receipt["stockCLISHA256"] = self.args.cli_sha256
        self.env["MIXER_LOCAL_RELEASE_CONFIG"] = json.dumps(config)
        self.offer_path = "/v3/updates?" + urlencode(dict(config["host"]["scope"],
            channel="beta", runtime=config["host"]["runtime"], installation=str(self.workspace)))
        self.setup()
        child = self.mix("phoenix", "serve", D6_ROOT_AUTH="yes")
        deadline = time.monotonic() + 15
        while True:
            try:
                if b"D6_ORIGIN_READY" in (self.work/"phoenix.log").read_bytes() and request("/health/live")[0] == 200:
                    break
            except OSError:
                pass
            require(time.monotonic() < deadline and child.poll() is None, "Phoenix readiness failed")
            time.sleep(.1)
        self.offer(0, None, config)
        denied, _ = request(TENANT + "/releases/validate", "POST")
        require(denied == 401, f"Missing bearer returned {denied}")
        self.receipt["missingBearerHTTP"] = denied
        for sequence in (1, 2, 3):
            self.publish(sequence, fixture, config)
        self.history(3)
        self.receipt["historicalRuntimeOfferHTTP"] = {}
        for previous in read(self.args.input / "historical-negative.json")["runtimes"]:
            old_query = "/v3/updates?" + urlencode(dict(config["host"]["scope"],
                channel="beta", runtime=previous, installation=str(self.workspace)))
            code, body = request(old_query)
            require(code == 204 and not body, "old runtime received an offer")
            self.receipt["historicalRuntimeOfferHTTP"][previous] = code
        self.receipt["passed"] = True

    def stop_origin(self):
        require(self.close("phoenix", signal.SIGTERM) in (0, -signal.SIGTERM), "Phoenix stop failed")
        try:
            request("/health/live")
        except ConnectionRefusedError:
            self.receipt["offlineRefused"] = True
        else:
            raise RuntimeError("Origin still accepting connections")
        reusable(PORT)

    def cleanup(self):
        if "phoenix" in self.children:
            self.stop_origin()
        if "postgres" in self.children:
            require(self.close("postgres", signal.SIGINT) == 0, "PostgreSQL did not stop cleanly")
        reusable(self.pgport)
        reusable(PORT)
        require(not self.children, "Child closure incomplete")
        self.receipt["portsReusable"] = [PORT, self.pgport]

if __name__ == "__main__":
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    args = parser.parse_args()
    args.work = args.work.resolve(strict=True)
    args.mode = "root-host"
    args.input = args.work / "renewed"
    args.evidence = args.work / "release-host"
    args.cli = Path((args.work / "cli-path").read_text().strip())
    args.cli_sha256 = read(args.work / "generation.json")["cliSHA256"]
    args.evidence.mkdir(mode=0o700)
    work = Path(tempfile.mkdtemp(prefix="mixer-d6-db-", dir="/private/tmp")).resolve()
    run = Run(args, work)
    try:
        run.execute()
    except Exception as error:
        run.receipt.update(passed=False, failure=str(error))
    finally:
        try:
            run.cleanup()
            run.receipt["terminalClosure"] = True
        except Exception as error:
            run.receipt.update(passed=False, terminalClosure=False, hold=str(work), cleanupFailure=str(error))
        if run.receipt["terminalClosure"]:
            for log in work.glob("*.log"):
                shutil.copyfile(log, args.evidence/log.name)
            shutil.rmtree(work)
            run.receipt["scratchRemoved"] = not work.exists()
        write(args.evidence/"receipt.json", run.receipt)
    print(json.dumps({k:v for k,v in run.receipt.items() if k not in ("commands", "offers")}))
    raise SystemExit(0 if run.receipt["passed"] else 1)
