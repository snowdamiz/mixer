#!/usr/bin/env python3
"""Exercise and restore the pinned Phoenix release with disposable PostgreSQL 17."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = "71e6ffa51e857d5a1eda3f74c26941996ed275de"
ADMIN = "mixer_replay_admin"
DB = "release_fixture"
PASSWORDS = {
    "mixer_replay_writer": "synthetic-replay-writer",
    "mixer_release_delivery": "synthetic-replay-reader",
    "mixer_artifact_uploader": "synthetic-replay-uploader",
}
ROLES = set(PASSWORDS) | {ADMIN, "mixer_replay_owner", "mixer_replay_stage"}
REPAIR = "scripts/restore-local-authz-expiry.sql"
ROLE_QUERY = """
SELECT jsonb_agg(to_jsonb(r) - 'oid' ORDER BY rolname)::text
FROM pg_catalog.pg_roles r WHERE rolname NOT LIKE 'pg\\_%'
"""
MEMBER_QUERY = """
SELECT jsonb_agg(jsonb_build_array(pg_get_userbyid(roleid), pg_get_userbyid(member),
  pg_get_userbyid(grantor), admin_option, inherit_option, set_option)
  ORDER BY pg_get_userbyid(roleid), pg_get_userbyid(member), pg_get_userbyid(grantor))
FROM pg_catalog.pg_auth_members
"""
EXPIRY_QUERY = """
SET search_path TO pg_catalog;
SELECT conname || ':' || pg_get_expr(conbin, conrelid, false)
FROM pg_constraint WHERE conrelid IN ('public.mixer_authz_credentials'::regclass,
  'public.mixer_authz_families'::regclass)
AND conname IN ('mixer_authz_credentials_check', 'mixer_authz_families_check')
ORDER BY conname
"""
ARTIFACT_KEY_QUERY = """
SET search_path TO pg_catalog;
SELECT pg_get_expr(conbin, conrelid, false) FROM pg_constraint
WHERE conrelid = 'public.mixer_customer_idempotency'::regclass
  AND conname = 'mixer_customer_idempotency_key_check' AND convalidated
"""


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def group_absent(pid):
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return True
    return False


class Replay:
    def __init__(self, work, pg, hex_home, mix_home):
        self.work = work
        self.pg = pg
        self.env = {
            "PATH": f"{pg}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(work),
            "TMPDIR": str(work),
            "LC_ALL": "C",
            "MIX_ENV": "test",
            "HEX_OFFLINE": "1",
            "ERL_FLAGS": "+S 4:4",
            "GIT_NO_LAZY_FETCH": "1",
        }
        self.hex_home = hex_home
        self.mix_home = mix_home
        self.projection = work / "source-tree"
        self.hosted = self.projection / "hosted"
        self.clusters = []
        self.listeners = []
        self.commands = []
        self.holds = []

    def run(self, *args, cwd=None, env=None, seconds=45):
        args = list(map(str, args))
        child = subprocess.Popen(
            args, cwd=cwd or self.work, env=self.env | (env or {}),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True,
        )
        command = {"argv": args, "pid": child.pid}
        try:
            out, err = child.communicate(timeout=seconds)
            require(group_absent(child.pid), "Command group did not close")
        except BaseException:
            self.holds.append(command)
            raise
        self.commands.append(command | {"exit": child.returncode})
        if child.returncode:
            sys.stderr.write(out.decode(errors="replace")[-16000:])
            sys.stderr.write(err.decode(errors="replace")[-16000:])
            raise RuntimeError(f"{args[0]} exited {child.returncode}: {args[1:3]}")
        return out.decode().strip()

    def project(self):
        archive = self.work / "source.tar"
        self.run("git", "archive", f"--output={archive}", BASE, "hosted", REPAIR,
                 "docs/operations/provision-local-artifact-uploader.sql",
                 "services/protocol/testdata/signed-release-v3.json", cwd=ROOT)
        with tarfile.open(archive) as source:
            source.extractall(self.projection, filter="data")
        self.run("git", "apply", "--check", HERE / "configured-fixture.patch", cwd=self.projection)
        self.run("git", "apply", HERE / "configured-fixture.patch", cwd=self.projection)
        test = self.hosted / "test/release_restore_test.exs"
        shutil.copyfile(HERE / test.name, test)
        shutil.copyfile(HERE / "snapshot.sql", self.work / "snapshot.sql")
        shutil.copytree(self.hex_home, self.work / ".hex")
        shutil.copytree(self.mix_home / "archives", self.work / ".mix/archives")
        self.run("mix", "deps.get", "--check-locked", cwd=self.hosted, seconds=90)
        self.run("mix", "compile", "--warnings-as-errors", cwd=self.hosted, seconds=180)
        require((self.hosted / "mix.lock").read_bytes() ==
                (ROOT / "hosted/mix.lock").read_bytes(), "Pinned dependency lock changed")

    def certificates(self):
        pki = self.work / "tls"
        pki.mkdir()
        self.run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", 1,
                 "-subj", "/CN=Mixer release restore CA", "-keyout", pki / "ca.key",
                 "-out", pki / "ca.pem")
        self.run("openssl", "req", "-new", "-newkey", "rsa:2048", "-nodes",
                 "-subj", "/CN=127.0.0.1", "-keyout", pki / "server.key", "-out", pki / "server.csr")
        ext = pki / "server.ext"
        ext.write_text("subjectAltName=DNS:127.0.0.1,IP:127.0.0.1\nextendedKeyUsage=serverAuth\n")
        self.run("openssl", "x509", "-req", "-days", 1, "-in", pki / "server.csr",
                 "-out", pki / "server.pem", "-CA", pki / "ca.pem", "-CAkey", pki / "ca.key",
                 "-CAcreateserial", "-extfile", ext)
        return pki

    def start_cluster(self, name, pki):
        directory = self.work / name
        directory.mkdir()
        data = directory / "data"
        # Keep the socket pathname short on both Darwin and Linux.
        local = self.work / name[0]
        local.mkdir()
        self.run(self.pg / "initdb", "-D", data, "-U", ADMIN, "--auth=reject",
                 "--locale=C", "--encoding=UTF8", "--no-sync")
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        hba = data / "pg_hba.conf"
        hba.write_text(f"local all {ADMIN} trust\n"
                       f"hostssl {DB} {','.join(PASSWORDS)} 127.0.0.1/32 scram-sha-256\n")
        args = [self.pg / "postgres", "-D", data, "-h", "127.0.0.1", "-p", str(port),
                "-k", local, "-c", "ssl=on", "-c", f"ssl_cert_file={pki / 'server.pem'}",
                "-c", f"ssl_key_file={pki / 'server.key'}", "-c", "jit=off"]
        with (directory / "postgres.log").open("wb") as log:
            child = subprocess.Popen(args, env=self.env, stdin=subprocess.PIPE,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        cluster = {"child": child, "data": data, "socket": local, "port": port, "hba": hba}
        self.clusters.append(cluster)
        deadline = time.monotonic() + 12
        while child.poll() is None and time.monotonic() < deadline:
            pid_file = data / "postmaster.pid"
            fields = pid_file.read_text().splitlines() if pid_file.exists() else []
            if (len(fields) >= 8 and fields[0] == str(child.pid) and fields[3] == str(port)
                    and fields[4] == str(local) and fields[7].strip() == "ready"):
                self.listeners.append((name, port))
                require(self.sql(cluster, "SHOW data_directory", "postgres") == str(data),
                        "PostgreSQL data directory differs")
                return cluster
            time.sleep(0.05)
        print((directory / "postgres.log").read_text()[-8000:], file=sys.stderr)
        raise RuntimeError(f"{name} did not reach owned PostgreSQL readiness")

    def conn(self, cluster):
        return ("-h", cluster["socket"], "-p", str(cluster["port"]), "-U", ADMIN, "-w")

    def psql(self, cluster, database, *args):
        return self.run(self.pg / "psql", *self.conn(cluster), "-XqAt", "-v",
                        "ON_ERROR_STOP=1", "-d", database, *args)

    def sql(self, cluster, statement, database=DB):
        return self.psql(cluster, database, "-c", statement)

    def stop_cluster(self, cluster):
        child = cluster["child"]
        if cluster.get("closed"):
            return
        try:
            if child.poll() is None:
                child.send_signal(signal.SIGINT)  # PostgreSQL fast shutdown
            child.wait(timeout=15)
            child.stdin.close()
            require(group_absent(child.pid) and not (cluster["data"] / "postmaster.pid").exists(),
                    "PostgreSQL closure unconfirmed")
            cluster["closed"] = True
            require(child.returncode == 0, "PostgreSQL did not exit cleanly")
        except BaseException:
            if not cluster.get("closed"):
                self.holds.append({"postgres": str(cluster["data"]), "pid": child.pid})
            raise

    def api(self, cluster, phase):
        ports = self.work / f"{phase}-ports"
        try:
            out = self.run(
                "mix", "test", "--warnings-as-errors", "--trace", "--no-color",
                "test/release_restore_test.exs", cwd=self.hosted, seconds=95, env={
                    "PGDATABASE": DB, "PGPORT": str(cluster["port"]),
                    "MIXER_RELEASE_FIXTURE_SCRATCH": str(cluster["socket"]),
                    "RELEASE_RESTORE_ROOT": str(self.work),
                    "RELEASE_RESTORE_PHASE": phase,
                    "RELEASE_RESTORE_PORTS": str(ports),
                },
            )
        finally:
            if not self.holds and ports.exists():
                for line in ports.read_text().splitlines():
                    name, port = line.split()
                    self.listeners.append((phase + "-" + name, int(port)))
        lines = [line.split("RESTORE_PHASE ", 1)[1] for line in out.splitlines()
                 if "RESTORE_PHASE " in line]
        summary = "Result: 1 passed, 1 skipped"
        require(len(lines) == 1 and summary in out.splitlines(), f"No completed {phase} test")
        result = json.loads(lines[0])
        for name in ("phoenix", "jwks"):
            require((phase + "-" + name, result[name + "Port"]) in self.listeners,
                    f"Missing {phase} {name} port observation")
        print(f"{phase} ExUnit: {summary}", file=sys.stderr, flush=True)
        return result | {"exUnit": summary}

    def verify_roles(self, cluster):
        roles = json.loads(self.sql(cluster, ROLE_QUERY))
        require({r["rolname"] for r in roles} == ROLES, "Unexpected fixture roles")
        for role in roles:
            if role["rolname"] != ADMIN:
                require(not any(role[attr] for attr in (
                    "rolsuper", "rolinherit", "rolcreaterole", "rolcreatedb",
                    "rolreplication", "rolbypassrls",
                )), "Unexpected restricted login attributes")
                require(role["rolcanlogin"] == (role["rolname"] != "mixer_replay_owner"),
                        "Unexpected fixture LOGIN")
        return [roles, json.loads(self.sql(cluster, MEMBER_QUERY))]

    def exercise(self):
        pg_version = self.run(self.pg / "postgres", "--version")
        require(" 17." in pg_version, "The pinned expiry repair requires PostgreSQL 17")
        versions = {name: self.run(self.pg / name, "--version")
                    for name in ("initdb", "psql", "pg_dump", "pg_dumpall", "pg_restore")}
        require(all(value.split()[2:] == pg_version.split()[2:] for value in versions.values()),
                "Use clients from the same PostgreSQL installation")
        elixir = self.run("elixir", "--version")
        self.project()
        pki = self.certificates()
        source = self.start_cluster("source", pki)
        self.sql(source, f"CREATE DATABASE {DB}", "postgres")
        candidate = self.api(source, "source")
        source_id = self.sql(source, "SELECT system_identifier::text FROM pg_control_system()")

        # The API, JWKS server and all app pools have exited. Close TCP login and
        # observe a cluster-level read-only default before collecting the dump.
        source["hba"].write_text(f"local all {ADMIN} trust\n")
        self.sql(source, "ALTER SYSTEM SET default_transaction_read_only = on")
        self.run(self.pg / "pg_ctl", "-D", source["data"], "reload")
        deadline = time.monotonic() + 5
        while self.sql(source, "SHOW default_transaction_read_only") != "on":
            require(time.monotonic() < deadline, "Source did not become read-only")
            time.sleep(0.05)
        require(self.sql(source, "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                         "AND pid <> pg_backend_pid()") == "0", "Source still has database clients")

        snapshot = (HERE / "snapshot.sql").read_text()
        frozen = self.sql(source, snapshot)
        require(digest(frozen.encode()) == candidate["snapshotSHA256"], "Source rows changed at freeze")
        expiry = self.sql(source, EXPIRY_QUERY)
        artifact_key = self.sql(source, ARTIFACT_KEY_QUERY)
        require(artifact_key, "Source artifact request-key CHECK absent")
        roles = self.verify_roles(source)
        backup = self.work / "release.dump"
        role_backup = self.work / "roles.sql"
        self.run(self.pg / "pg_dump", *self.conn(source), "-Fc", "-f", backup, DB)
        self.run(self.pg / "pg_dumpall", *self.conn(source), "--roles-only", "--no-role-passwords",
                 "--no-comments", "-f", role_backup)
        require(self.sql(source, snapshot) == frozen, "Source rows changed during backup")
        self.stop_cluster(source)

        target = self.start_cluster("target", pki)
        target_id = self.sql(target, "SELECT system_identifier::text FROM pg_control_system()", "postgres")
        require(target_id != source_id, "Restore did not create a distinct PostgreSQL cluster")
        require(self.sql(target, f"SELECT count(*) FROM pg_database WHERE datname = '{DB}'",
                         "postgres") == "0", "Target database already exists before restore")
        role_sql = role_backup.read_text()
        bootstrap = f"CREATE ROLE {ADMIN};\n"
        require(role_sql.count(bootstrap) == 1, "Unexpected administrator in password-free role dump")
        target_roles = self.work / "target-roles.sql"
        target_roles.write_text(role_sql.replace(bootstrap, "", 1))
        self.psql(target, "postgres", "-f", target_roles)
        self.run(self.pg / "pg_restore", *self.conn(target), "--exit-on-error", "--create",
                 "-d", "postgres", backup)
        for login, password in PASSWORDS.items():
            # These literals match the synthetic configured-release fixture.
            self.sql(target, f"ALTER ROLE {login} PASSWORD '{password}'")
        require(self.verify_roles(target) == roles, "Restored role attributes or memberships differ")
        raw_expiry = self.sql(target, EXPIRY_QUERY)
        raw_artifact_key = self.sql(target, ARTIFACT_KEY_QUERY)
        self.psql(target, DB, "-f", self.projection / REPAIR)
        self.psql(target, DB, "-f", HERE / "restore-artifact-key.sql")
        require(self.sql(target, EXPIRY_QUERY) == expiry, "Restored expiry constraints differ")
        require(self.sql(target, ARTIFACT_KEY_QUERY) == artifact_key,
                "Restored artifact request-key CHECK differs")
        require(self.sql(target, snapshot) == frozen, "Restored rows differ before API start")
        restored = self.api(target, "target")
        require(self.sql(target, snapshot) == frozen, "Readback or retry changed restored rows")
        require(restored["http"] == candidate["http"], "Restored HTTP digests differ")
        self.stop_cluster(target)
        return {
            "sourceRevision": BASE,
            "sourceTree": self.run("git", "rev-parse", BASE + "^{tree}", cwd=ROOT),
            "host": f"{os.uname().sysname} {os.uname().machine}",
            "python": sys.version.split()[0],
            "elixir": elixir,
            "postgres": pg_version,
            "postgresTools": versions,
            "lockedDependenciesSHA256": digest((self.hosted / "mix.lock").read_bytes()),
            "postgresSystemIdentifiers": [source_id, target_id],
            "sourceReadOnlyBeforeDump": True,
            "sourceStoppedBeforeRestore": True,
            "targetDatabaseAbsentBeforeRestore": True,
            "restoredRoleFlagsAndMembershipsMatch": True,
            "expiryCatalogRepairChangedDefinitions": raw_expiry != expiry,
            "artifactRequestKeyCheck": {
                "sourceAndRepaired": artifact_key,
                "rawRestore": raw_artifact_key,
            },
            "backupSHA256": digest(backup.read_bytes()),
            "passwordFreeRolesSHA256": digest(role_backup.read_bytes()),
            "snapshotMatchesAtFreezeAfterDumpBeforeAPIAndAfterRetry": True,
            "source": candidate,
            "target": restored,
        }

    def finish(self):
        if self.holds:
            (self.work / "HOLD.json").write_text(json.dumps(self.holds, indent=2) + "\n")
            raise RuntimeError(f"Unresolved command custody. Preserve {self.work}")
        failures = []
        for cluster in reversed(self.clusters):
            try:
                self.stop_cluster(cluster)
            except (RuntimeError, subprocess.TimeoutExpired, OSError) as error:
                failures.append(str(error))
        if self.holds:
            (self.work / "HOLD.json").write_text(json.dumps(self.holds, indent=2) + "\n")
            raise RuntimeError(f"Unresolved PostgreSQL custody. Preserve {self.work}")
        for name, port in self.listeners:
            try:
                with socket.socket() as listener:
                    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    listener.bind(("127.0.0.1", port))
            except OSError as error:
                failures.append(f"{name} port {port}: {error}")
        shutil.rmtree(self.work)
        require(not self.work.exists(), "Owned scratch still exists")
        require(not failures, "Cleanup failed: " + "; ".join(failures))
        return {"clustersReapedWithExitZeroAndGroupAbsent": len(self.clusters),
                "portsRebound": dict(self.listeners),
                "commandGroupsClosed": len(self.commands), "scratchRemoved": str(self.work)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-bin", required=True, type=Path)
    args = parser.parse_args()
    require(os.geteuid() != 0, "Run this fixture as an unprivileged user")
    hex_home = Path(os.environ.get("HEX_HOME", Path.home() / ".hex")).resolve()
    mix_home = Path(os.environ.get("MIX_HOME", Path.home() / ".mix")).resolve()
    previous = os.umask(0o077)
    try:
        work = Path(tempfile.mkdtemp(prefix="mixer-release-restore-", dir="/tmp")).resolve()
        print(f"Owned scratch: {work}", file=sys.stderr, flush=True)
        replay = Replay(work, args.postgres_bin.resolve(), hex_home, mix_home)
        # A SIGTERM uses the same cleanup path as an interactive interruption.
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
        try:
            report = replay.exercise()
        finally:
            cleanup = replay.finish()
            print("Cleanup: " + json.dumps(cleanup), file=sys.stderr, flush=True)
        print(json.dumps(report | {"cleanup": cleanup}, indent=2))
    finally:
        os.umask(previous)


if __name__ == "__main__":
    main()
