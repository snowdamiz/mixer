#!/usr/bin/env python3
"""Back up one settled local iOS Starter build and read it from a fresh cluster."""

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import traceback
from types import ModuleType
from urllib.parse import parse_qsl, urlencode, urlsplit

DELIVERY = Path(__file__).resolve().parent
ROOT = DELIVERY.parents[2]
BASE = "57f3ed4f17b80f15fc6d646b14c6dbfa05bd7eea"
TREE = "fd2db4b611d952bbfafaf34cee0c02ba048b7346"
LAUNCHER = ROOT / "tests/integration/free-project-starter/replay-restart.py"
REPAIR = ROOT / "scripts/restore-local-authz-expiry.sql"
FIXTURE = DELIVERY / "starter-restore-fixture.patch"
CLI_PATCH = DELIVERY / "starter-swift-lock.patch"
CLI_PATCH_SHA256 = "900dd380712ae10365e92b5d494573e0e2659403db77f0838f821fa9f5bdd068"
BASE_PROVENANCE_SHA256 = "8c7b6022210d13a8830500ef5c406db8f8fd6bcf93c883ab5e6718ed1f172b90"
CLI_PROVENANCE_SHA256 = "1338f7f1b16e646b4665ba67cf08a850da1f08b89b00a8bbcb4505ae48b2e161"
CLI_BLOBS = {
    "OwnedCommand.swift": ("5413ff4c56eddffc65aa925c3503b02f2fcae383", "183796e1701105787524204869dc55cf7b086803"),
    "POSIXCommandControl.swift": ("8f5ac69694687ed6357b2bab828f12906cef0a17", "ab919235bc34467ffd3c13292b25de4d7846a328"),
    "ProcessRunner.swift": ("a988b328499f5ba5502ecbb119d47ee19ae5ff34", "fdd57e151080cb4d98c8b8d057201c28cc62fde0"),
    "ProjectGenerator.swift": ("11e269f91b7f7ed4b4b279ccfa14d7c87a76b8f4", "de0013471a4e448243108d35da475b2da8d0a5fd"),
}
TEST = "test/mixer_hosted/browser_auth/starter_restore_spec.exs"
SUPPORT = "test/support/ordinary_browser_startup_fixture.ex"
SUPPORT_SHA256 = "90e8781bd974496ab8eca4464de4a677a9de1aba0f679396bdece8e5fac0fced"
PINS = {
    LAUNCHER: "f960866d2d70591afc7bae77c1255abc324e18826f83e0b9f3512a2a7fa5b69e",
    REPAIR: "1012536ad091cfd43d8e06f627dc05b2d3a7316af56a58f8e6c8dfa29eb552ad",
}
SYSTEM_ID = "SELECT system_identifier::text FROM pg_control_system()"
ROLES = """SELECT coalesce(jsonb_agg(to_jsonb(r) - 'oid' ORDER BY rolname), '[]')
  FROM pg_roles r WHERE left(rolname,3) <> 'pg_'"""
MEMBERSHIPS = """SELECT coalesce(jsonb_agg(to_jsonb(m) ORDER BY to_jsonb(m)), '[]') FROM (
  SELECT pg_get_userbyid(roleid) AS role, pg_get_userbyid(member) AS member,
         pg_get_userbyid(grantor) AS grantor, admin_option, inherit_option, set_option
  FROM pg_auth_members) m"""


def load_launcher():
    revision_path = f"{BASE}:{LAUNCHER.relative_to(ROOT).as_posix()}"
    source = subprocess.check_output(
        ["git", "--no-pager", "show", revision_path],
        cwd=ROOT,
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
        timeout=10,
    )
    if hashlib.sha256(source).hexdigest() != PINS[LAUNCHER]:
        raise RuntimeError(f"Pinned Starter launcher at {BASE} differs")
    if hashlib.sha256(REPAIR.read_bytes()).hexdigest() != PINS[REPAIR]:
        raise RuntimeError("Pinned expiry repair differs")
    module = ModuleType("starter_restart")
    module.__file__ = str(LAUNCHER)
    exec(compile(source, revision_path, "exec"), vars(module))
    return module


starter = load_launcher()
require, digest = starter.require, starter.digest


class RestoreRun(starter.Run):
    def __init__(self, root, mode):
        super().__init__(root, mode)
        self.bundle = root / "backup"
        self.target = root / "restore"
        self.bundle.mkdir(mode=0o700)
        self.target.mkdir(mode=0o700)
        self.target_pg = self.target_api = None
        self.result.update(launcherSHA256=PINS[LAUNCHER], restoreBase=BASE, restoreBaseTree=TREE,
                           restoreLauncherSHA256=digest(Path(__file__)),
                           restoreFixtureSHA256=digest(FIXTURE),
                           restoreRepairSHA256=PINS[REPAIR], restoredCompilerStarts=None)

    def evidence(self):
        super().evidence()
        if self.result["status"] == "all_real_services_prepost_ready":
            require(self.result["buildPOSTAttempts"] == self.result["workerStarts"] ==
                    self.result["compilerStarts"] == 0, "source fixture already attempted a build")
            require(self.result["processorAdmission"]["paused"]
                    and self.result["workerReadyAuthenticated"], "source build precheck failed")
            self.mark("prepost-verified")

    def stage_restore(self):
        _, out = self.command("restore-base-tree", ["git", "rev-parse", BASE + "^{tree}"], cwd=ROOT)
        require(out.read_text().strip() == TREE, "restore base tree differs")
        self.stage(self.result["mode"])
        require(digest(self.hosted / SUPPORT) == SUPPORT_SHA256, "restore fixture preimage differs")
        self.command("restore-fixture-overlay", ["git", "apply", "--whitespace=error", FIXTURE],
                     env={"GIT_CEILING_DIRECTORIES": str(self.root.parent)})
        shutil.copyfile(DELIVERY / "starter-restore.exs", self.hosted / TEST)
        self.result["restoreFixtureAfterimageSHA256"] = digest(self.hosted / SUPPORT)
        self.result["restoreTestSHA256"] = digest(self.hosted / TEST)

    def stage_provenance(self):
        super().stage_provenance()
        require(self.result["provenanceSourceSHA256"] == BASE_PROVENANCE_SHA256,
                "unexpected CLI archive source digest")
        require(digest(CLI_PATCH) == CLI_PATCH_SHA256, "pinned CLI Swift lock patch differs")
        installed = dict(self.source_entries)
        for name, (before, after) in CLI_BLOBS.items():
            path = f"cli/Sources/MixerBuild/{name}"
            require(installed[path] == ("100644", before), f"CLI patch predecessor differs: {path}")
            installed[path] = ("100644", after)
        self.command("starter-swift-lock-overlay", ["git", "apply", "--whitespace=error", CLI_PATCH],
                     cwd=self.provenance, env={"GIT_CEILING_DIRECTORIES": str(self.root.parent)})
        self.source_entries = installed
        self.result.update(provenanceBaseSHA256=BASE_PROVENANCE_SHA256,
                           provenanceOverlaySHA256=CLI_PATCH_SHA256,
                           provenanceSourceSHA256=CLI_PROVENANCE_SHA256)
        self.verify_provenance("after-swift-lock-overlay")

    def close_source_writers(self):
        self.verify_active_services()
        self.mark("processor.done")
        self.finish("processor", self.processor, seconds=35)
        self.processor = None
        if getattr(self, "relay", None) is not None:
            self.relay.finish()
            self.relay = None
        starter.close_worker(self)
        self.result["sourceWritersClosedBeforeBackup"] = True

    def close_services(self):
        require(not self.unknown and not self.native_pending, "live service custody is unknown")
        self.verify_active_services()
        if getattr(self, "processor", None) is not None:
            self.mark("processor.done")
            self.finish("processor", self.processor, seconds=35, check=False)
            self.processor = None
        if getattr(self, "relay", None) is not None:
            self.relay.finish()
            self.relay = None
        starter.close_worker(self)
        if getattr(self, "api", None) is not None:
            self.mark("api.done")
            self.finish("api", self.api, seconds=35, check=False)
            self.api = None
        if getattr(self, "pg", None) is not None:
            try:
                if self.pg.poll() is None and self.result.get("postgresDataDirectoryVerified"):
                    remaining = self.sql(
                        "database-closed",
                        f"SELECT count(*) FROM pg_database WHERE datname='{starter.DB}'",
                        "postgres",
                    )
                    self.result["databaseDropped"] = remaining == "0"
            except Exception as error:
                if self.unknown:
                    raise
                self.result["databaseDropped"] = False
                self.result["databaseCheckError"] = f"{type(error).__name__}: {error}"
            finally:
                if not self.unknown:
                    self.finish("postgres", self.pg, shutdown=signal.SIGINT, check=False)
                    self.pg = None

    def open_target(self, pg):
        data = self.target / "pg"
        self.command("target-initdb", [pg / "initdb", "-D", data, "-U", "fixture_admin",
                     "--locale=C", "--encoding=UTF8", "--auth=trust", "--no-sync"])
        port = self.port("restored-postgres")
        self.target_conn = ["-h", starter.HOST, "-p", str(port), "-U", "fixture_admin", "-w"]
        self.target_psql = [pg / "psql", *self.target_conn, "-XqAt", "-v", "ON_ERROR_STOP=1"]
        self.target_pg = self.start("restored-postgres", [pg / "postgres", "-D", data, "-h", starter.HOST,
                                    "-p", str(port), "-k", "", "-c", "jit=off"])
        starter.wait(lambda: starter.connected(port), 8, self.target_pg)
        require(self.target_sql("target-directory", "SHOW data_directory", "postgres") == str(data),
                "target PostgreSQL is outside this replay")

    def target_sql(self, label, query, database=starter.DB):
        _, out = self.command(label, [*self.target_psql, "-d", database, "-c", query], seconds=10)
        return out.read_text().strip()

    def restore_database(self, pg, source):
        self.open_target(pg)
        sysid = self.target_sql("target-system-id", SYSTEM_ID, "postgres")
        require(source["systemId"] != sysid, "restored PostgreSQL cluster identity matches source")
        self.result["postgresSystemIdentifiers"] = [source["systemId"], sysid]
        role_dump = self.bundle / "roles.sql"
        require(digest(role_dump) == self.result["roleDumpSHA256"], "role dump changed")
        roles = role_dump.read_bytes()
        bootstrap = b"CREATE ROLE fixture_admin;\n"
        require(roles.count(bootstrap) == 1, "backup must define fixture_admin once")
        target_roles = self.target / "roles.sql"
        target_roles.write_bytes(roles.replace(bootstrap, b"", 1))
        self.command("target-roles", [*self.target_psql, "-d", "postgres", "-f", target_roles])
        require(self.target_sql("target-role-flags", ROLES, "postgres") == source["roles"]
                and self.target_sql("target-role-memberships", MEMBERSHIPS, "postgres") == source["memberships"],
                "restored role attributes or memberships differ")
        dump = self.bundle / "postgres.dump"
        require(digest(dump) == self.result["postgresDumpSHA256"], "PostgreSQL dump changed")
        self.command("target-restore", [pg / "pg_restore", *self.target_conn, "--exit-on-error",
                     "--create", "--dbname", "postgres", dump], seconds=40)
        self.command("target-pinned-expiry", [*self.target_psql, "-d", starter.DB, "-f", REPAIR], seconds=40)
        require(self.target_sql("target-before-api", starter.SNAPSHOT) == source["journal"]
                and digest(dump) == self.result["postgresDumpSHA256"], "restored terminal journal differs")
        self.result.update(restoredJournalMatches=True, restoredRolesMatch=True,
                           pinnedExpiryRepairApplied=True)

    def launch_target_api(self):
        catalog = self.target / "catalog"
        catalog.mkdir()
        self.target_api = self.start("restored-api", ["mix", "test", "--seed", "0", "--trace", TEST],
                                     cwd=self.hosted, env={
            "HEX_OFFLINE": "1", "MIXER_L07_REPLAY": "restore", "MIXER_L07_ROOT": str(self.target),
            "MIXER_BROWSER_CATALOG_FIXTURE_ROOT": str(catalog),
            "MIXER_BROWSER_STORAGE_PORT": str(self.ports["restored-postgres"]),
        })
        ready = self.target / "api.ready"
        auth = starter.wait(lambda: starter.read(ready) if ready.is_file() else None, 40, self.target_api)
        for name in ("port", "issuerPort", "jwksPort"):
            port = auth[name]
            require(type(port) is int and 0 < port < 65536 and port not in self.ports.values(),
                    f"restored fixture port collision: {name}")
            self.ports["restored-" + name] = port
        require(auth["storageReady"] and auth["queuesDisabled"] and auth["role"] == "browser_ordinary",
                "restored endpoint failed restricted admission")
        self.result.update(restoredStorageReady=True, restoredQueuesDisabled=True)
        return auth

    def close_target(self):
        if self.target_api is not None:
            (self.target / "api.done").touch(exist_ok=False)
            code = self.finish("restored-api", self.target_api, seconds=35, check=False)
            self.target_api = None
            self.result["restoredAPIExit"] = code
        if self.target_pg is not None:
            code = self.finish("restored-postgres", self.target_pg, shutdown=signal.SIGINT, check=False)
            self.target_pg = None
            self.result["restoredPostgresExit"] = code


def sqlite_backup(original, backup):
    with closing(sqlite3.connect(original.as_uri() + "?mode=ro", uri=True, timeout=1)) as source:
        with closing(sqlite3.connect(backup)) as target:
            source.backup(target)
            require(target.execute("PRAGMA integrity_check").fetchall() == [("ok",)],
                    "worker SQLite backup failed integrity_check")


def capture_worker(run, operation, row):
    require(re.fullmatch(r"[0-9a-f]{64}", operation) and row["starts"] == 1
            and row["status"] == "native_ready" and starter.ledger(run.state, count=True) == 1,
            "source has no single settled worker operation")
    worker = run.bundle / "worker"
    native = Path(operation) / "native"
    (worker / native).mkdir(mode=0o700, parents=True)
    sqlite_backup(run.state / "operations.sqlite", worker / "operations.sqlite")
    require(starter.ledger(worker, operation) == row and starter.ledger(worker, count=True) == 1,
            "SQLite backup differs from the terminal operation")
    files = {native / "native-build.json": row["manifest_sha256"],
             Path("customer-log-v1-" + operation): None}
    require(tuple(a["kind"] for a in row["artifacts"]) == starter.KINDS, "unexpected artifact types")
    for item in row["artifacts"]:
        sha256 = item["sha256"]
        require(re.fullmatch(r"[0-9a-f]{64}", sha256)
                and (run.state / native / sha256).stat().st_size == item["sizeBytes"],
                "source artifact size differs from worker ledger")
        files[native / sha256] = sha256
    pins = {"operations.sqlite": digest(worker / "operations.sqlite")}
    for relative, expected in files.items():
        source = run.state / relative
        info = source.lstat()
        mode = info.st_mode & 0o777
        require(source.is_file() and not source.is_symlink() and info.st_uid == os.getuid()
                and info.st_nlink == 1 and mode in (0o400, 0o444)
                and (expected is not None or mode == 0o400),
                "retained file is not owned and immutable")
        actual = digest(source)
        require(expected is None or actual == expected, "retained file digest differs")
        shutil.copy2(source, worker / relative)
        require(digest(worker / relative) == actual, "retained copy differs")
        pins[str(relative)] = actual
    run.result["workerBackupSHA256"] = pins
    return pins


def build_readback(body, selection, ledger):
    data = json.loads(body)
    build = data["build"]
    require((build["buildId"], build["revision"], build["state"]) ==
            (selection["build_id"], 2, "native_succeeded"), "unexpected authenticated build")
    expected = {item["kind"]: item for item in ledger}
    require(set(expected) == set(starter.KINDS) and len(ledger) == len(expected),
            "unexpected artifact kinds in the ledger")
    require(len(build["artifacts"]) == len(expected), "incomplete artifact descriptors")
    downloads = {}
    for artifact in build["artifacts"]:
        kind = artifact["kind"]
        require(kind in expected and kind not in downloads, "unexpected or duplicate artifact descriptor")
        item = expected[kind]
        require((artifact["sha256"], artifact["sizeBytes"]) == (item["sha256"], item["sizeBytes"]),
                f"{kind} descriptor differs from the worker ledger")
        advertised = artifact["downloadPath"]
        path = urlsplit(advertised)
        route = "/console-api/v1/build-artifacts/" + kind
        pairs = parse_qsl(path.query, keep_blank_values=True, strict_parsing=True)
        require(path.path == route and not (path.scheme or path.netloc or path.fragment)
                and len(pairs) == len(selection) and dict(pairs) == selection,
                "artifact download URL does not bind the build selection")
        downloads[kind] = advertised
        artifact["downloadPath"] = route + "?" + urlencode(sorted(selection.items()))
    return starter.json_sha(data), downloads


def read_as_owner_and_outsider(auth, path, label):
    code, headers, body = starter.http(auth, path)
    outsider = dict(auth, cookie=auth["unrelatedCookie"])
    denied, outsider_headers, outsider_body = starter.http(outsider, path)
    errors = {403: {"error": {"code": "permission_denied"}}, 404: {"error": {"code": "not_found"}}}
    require(code == 200 and denied in errors, f"{label} returned {code} for owner or {denied} for outsider")
    require(headers.get("cache-control") == outsider_headers.get("cache-control") == "no-store",
            f"{label} response can be cached")
    require(json.loads(outsider_body) == errors[denied], f"{label} exposed data to an unrelated tenant")
    return headers, body, {"httpStatus": code, "outsiderHTTP": denied,
                           "sha256": starter.sha(body), "sizeBytes": len(body)}


def get_readback(auth, selection, row):
    scope = "?" + urlencode(selection)
    _, body, build_output = read_as_owner_and_outsider(auth, starter.BUILD + scope, "build")
    build_output["contentSHA256"], downloads = build_readback(body, selection, row["artifacts"])
    _, body, log_output = read_as_owner_and_outsider(auth, "/console-api/v1/build-logs" + scope, "logs")
    data = json.loads(body)
    logs = data["buildLogs"]
    require((logs["revision"], logs["state"], logs["attempt"]) == (2, "native_succeeded", 1)
            and [(event["event"], event["exitCode"]) for event in logs["events"]] ==
            [("compiler_finished", 0), ("build_command_finished", 0)], "unexpected terminal logs")
    log_output["contentSHA256"] = starter.json_sha(data)
    outputs = {"build": build_output, "logs": log_output}
    for item in row["artifacts"]:
        kind = item["kind"]
        headers, _, output = read_as_owner_and_outsider(auth, downloads[kind], kind)
        require(headers["content-type"] == "application/octet-stream"
                and headers["content-disposition"] == f'attachment; filename="{kind}"'
                and (output["sha256"], output["sizeBytes"]) == (item["sha256"], item["sizeBytes"]),
                f"{kind} bytes or headers differ from the committed artifact")
        outputs[kind] = output
    return outputs


def compare_readback(source, restored):
    for key in ("build", "logs"):
        require(source[key]["contentSHA256"] == restored[key]["contentSHA256"],
                f"restored {key} content differs")
    for kind in starter.KINDS:
        require(all(source[kind][key] == restored[kind][key] for key in ("sha256", "sizeBytes")),
                f"restored {kind} bytes differ")


def replay(run, args):
    full = run.result["mode"] == "full"
    pg = args.pg_bin.resolve(strict=True)
    run.stage_restore()
    run.hosted_dependencies()
    settings = starter.prepare_export(run) if full else {}
    run.command("hosted-test-compile", ["mix", "compile"], cwd=run.hosted,
                env={"HEX_OFFLINE": "1"}, seconds=240)
    run.open_database(args)
    run.launch_api(settings)
    if full:
        outcome = starter.restart_replay(run, False)
        if outcome == "FAILED_CLOSED_NATIVE_BUILD":
            return outcome
        require(outcome == "PASS_SCOPED_STARTER_WORKER_RESTART", "source did not settle")
    else:
        run.launch_processor()
    run.close_source_writers()

    operation = run.result.get("operationId")
    if full:
        row = starter.ledger(run.state, operation)
        pins = capture_worker(run, operation, row)
        spec = row["binding"]["spec"]
        selection = {k: spec[k] for k in (*starter.SCOPE, "build_id", "toolchain_lock_sha256",
                                         "build_definition_sha256")}
        selection["source_sha256"] = spec["source"]["sha256"]
        source_auth = run.auth | starter.read(run.root / "api.renewed")
        source_http = get_readback(source_auth, selection, row)
        run.result["sourceHTTP"] = source_http
    else:
        source_auth = run.auth

    source = {
        "journal": run.sql("source-frozen-journal", starter.SNAPSHOT),
        "systemId": run.sql("source-system-id", SYSTEM_ID, "postgres"),
        "roles": run.sql("source-role-flags", ROLES, "postgres"),
        "memberships": run.sql("source-role-memberships", MEMBERSHIPS, "postgres"),
    }
    require(full or all(value is None for value in json.loads(source["journal"]).values()),
            "fixture-only mode has a build or processor job")
    conn = ["-h", starter.HOST, "-p", str(run.ports["postgres"]), "-U", "fixture_admin", "-w"]
    dump, roles = (run.bundle / name for name in ("postgres.dump", "roles.sql"))
    run.command("source-dump", [pg / "pg_dump", *conn, "--format=custom", "--file", dump, starter.DB], seconds=30)
    run.command("source-roles-dump", [pg / "pg_dumpall", *conn, "--roles-only", "--no-role-passwords",
                                     "--file", roles], seconds=30)
    require(run.sql("source-frozen-after-dump", starter.SNAPSHOT) == source["journal"],
            "source journal changed during backup")
    run.result.update(postgresDumpSHA256=digest(dump), roleDumpSHA256=digest(roles),
                      postgresJournalSHA256=starter.sha(source["journal"].encode()))
    run.close_services()
    require(run.closed() and run.result["databaseDropped"]
            and all(run.attempts[name]["exit"] == 0 for name in ("api", "processor", "postgres")),
            "source services did not close before restoring")
    run.restore_database(pg, source)
    target_worker = run.target / "worker"
    if full:
        shutil.copytree(run.bundle / "worker", target_worker)
        require(all(digest(target_worker / path) == pin for path, pin in pins.items())
                and starter.ledger(target_worker, operation) == row
                and starter.ledger(target_worker, count=True) == 1 and starter.ledger(target_worker),
                "independent store or recovered worker SQLite differs")
        run.result.update(restoredSQLiteIntegrity="ok", restoredWorkerStartsBefore=row["starts"])
    else:
        target_worker.mkdir(mode=0o700)

    auth = run.launch_target_api()
    for cookie_key in ("cookie", "unrelatedCookie"):
        code, _, session = starter.http(dict(auth, cookie=auth[cookie_key]), "/auth/session")
        require(code == 200 and json.loads(session)["state"] == "authenticated",
                "restored fixture session is not authenticated")
    require(all(auth[k] != source_auth[k] for k in ("cookie", "unrelatedCookie")), "restore reused source sessions")
    run.result["restoredFreshSessions"] = True
    if full:
        run.result["restoredHTTP"] = get_readback(auth, selection, row)
        require(starter.ledger(target_worker, operation) == row and starter.ledger(target_worker, count=True) == 1
                and all(digest(target_worker / path) == pin for path, pin in pins.items()),
                "readback changed the independent worker store")
        run.result["restoredWorkerStartsAfter"] = row["starts"]
    require(run.target_sql("target-after-api", starter.SNAPSHOT) == source["journal"],
            "authenticated restoration changed the build journal")
    run.result.update(restoredCompilerStarts=0, restoredProcessorLaunched=False, restoredWorkerLaunched=False)
    if full:
        compare_readback(source_http, run.result["restoredHTTP"])
    return "PASS_SCOPED_STARTER_BACKUP_RESTORE" if full else "PASS_EMPTY_STARTER_RESTORE_CONTROL"


def save_closed_failure_logs(run, receipt):
    commands = sorted({"api", "restored-api"} | {
        name for name, attempt in run.attempts.items() if attempt.get("exit") not in (None, 0)
    })
    logs = [run.root / f"{name}.{stream}" for name in commands for stream in ("out", "err")]
    logs = [log for log in logs if log.is_file() and log.stat().st_size]
    if not logs:
        return
    directory = receipt.with_suffix(".diagnostics")
    directory.mkdir(mode=0o700)
    for log in logs:
        with log.open("rb") as source:
            source.seek(max(0, log.stat().st_size - 32 * 1024))
            (directory / log.name).write_bytes(source.read(32 * 1024))
    run.result["closedFailureDiagnostics"] = str(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fixture-only", action="store_true", help="restore the hosted fixture with zero builds")
    mode.add_argument("--stage-only", action="store_true", help="prepare the CLI and Starter export for live custody replay")
    parser.add_argument("--pg-bin", type=Path, default=Path("/opt/homebrew/opt/postgresql@17/bin"))
    args = parser.parse_args()
    os.umask(0o077)
    parent = ROOT / "verification/local"
    parent.mkdir(parents=True, exist_ok=True)
    if args.stage_only:
        prefix, replay_mode = "l07-xcode-inputs-", "prepare-live-custody"
    else:
        prefix, replay_mode = "l07-starter-backup-", "fixture" if args.fixture_only else "full"
    run = RestoreRun(Path(tempfile.mkdtemp(prefix=prefix, dir=parent)).resolve(), replay_mode)
    print(f"L07 scratch directory {run.root}", flush=True)
    status = "FAILED"
    try:
        if args.stage_only:
            run.stage("inert")
            starter.prepare_export(run)
            require(run.closed() and run.result["buildPOSTAttempts"] == 0,
                    "staging did not close every command or attempted a build POST")
            run.result.update(status="PASS_STAGE", allPreparedCommandsClosed=True,
                              zeroFixtureBuildPOSTs=True)
            run.evidence()
            print(f"PASS_STAGE {run.root / 'result.json'}", flush=True)
            return 0
        status = replay(run, args)
    except BaseException as error:
        run.result["error"] = f"{type(error).__name__}: {error}"
        traceback.print_exc()

    receipt = run.root.with_suffix(".json")
    try:
        if run.unknown or run.native_pending:
            raise starter.Hold("command or native operation custody is unknown")
        if args.stage_only and run.attempts.get("cli-build", {}).get("exit", 0) != 0:
            raise starter.Hold("SwiftPM failed before nested compiler closure could be verified")
        run.close_target()
        run.close_services()
        require(run.closed(), "closure receipts do not cover every command")
        run.result["portsRebound"] = starter.rebound(run.ports.values())
        if not args.stage_only:
            run.verify_provenance("after-service-shutdown")
        if status.startswith("PASS"):
            require(run.result["restoredAPIExit"] == run.result["restoredPostgresExit"] == 0,
                    "restored services did not close normally")
        else:
            save_closed_failure_logs(run, receipt)
        run.result.update(status=status, scratchRemoved=True)
        pending = receipt.with_suffix(".closed.json")
        starter.record(pending, run.result)
        run.load_helper("run-proof").remove_closed_tree(run.root)
        pending.replace(receipt)
    except BaseException as error:
        run.result.update(status="HOLD", scratchRemoved=False, holdReason=f"{type(error).__name__}: {error}")
        hold = run.root / "HOLD.json" if run.root.is_dir() else receipt.with_suffix(".HOLD.json")
        starter.record(hold, run.result)
        print(f"Preserve {run.root}: {run.result['holdReason']}", file=sys.stderr)
        return 74
    print(f"{status} {receipt}", flush=True)
    return 0 if status.startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
