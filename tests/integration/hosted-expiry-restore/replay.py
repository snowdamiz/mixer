"""Round-trip the pinned authorization expiry checks on disposable PostgreSQL 17."""

import argparse
import json
from pathlib import Path
import os
import signal
import shutil
import socket
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
MIGRATION = ROOT / "hosted/priv/repo/migrations/20261025000003_add_customer_authorization.exs"
MANIFEST = ROOT / "hosted/priv/browser_auth/relation_surface_v1_pg17.json"
REPAIR = ROOT / "scripts/restore-local-authz-expiry.sql"
TABLES = ("mixer_authz_credentials", "mixer_authz_families")
NAMES = tuple(table + "_check" for table in TABLES)


def group_absent(pgid):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return True
    return False


def replay(binaries):
    parent = ROOT / "verification/local"
    parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="authz-expiry-restore-", dir=parent))
    print(work, flush=True)
    env = {"PATH": os.environ["PATH"], "TMPDIR": str(work), "LC_ALL": "C"}
    owners = []
    ports = []
    closed = []
    holds = []

    def run(tool, *args, expected=0):
        command = [str(binaries / tool), *map(str, args)]
        child = subprocess.Popen(command, env=env, start_new_session=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, stderr = child.communicate(timeout=40)
            if not group_absent(child.pid):
                raise RuntimeError("Command group did not close")
        except BaseException:
            holds.append(dict(pid=child.pid, command=command))
            raise
        closed.append(dict(pid=child.pid, command=command, exit=child.returncode))
        if child.returncode != expected:
            raise RuntimeError(stderr.decode(errors="replace"))
        return stdout.decode().strip() if not stderr else (stdout + stderr).decode().strip()

    def argv(port):
        return ("-h", "127.0.0.1", "-p", port, "-U", "restore_fixture", "-w", "-d", "postgres")

    def sql(port, statement, expected=0):
        return run("psql", *argv(port), "-XqAt", "-v", "ON_ERROR_STOP=1", "-c", statement, expected=expected)

    def start(name):
        data = work / name
        run("initdb", "-D", data, "-U", "restore_fixture", "-A", "trust", "--locale=C",
            "--encoding=UTF8", "--no-sync")
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        with (work / (name + ".log")).open("wb") as log:
            child = subprocess.Popen([binaries/"postgres", "-D", data, "-h", "127.0.0.1",
                                      "-p", str(port), "-k", "", "-c", "jit=off"],
                                     env=env, start_new_session=True, stdout=log, stderr=subprocess.STDOUT)
        owners.append(child)
        ports.append(port)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if child.poll() is not None:
                raise RuntimeError(f"{name} PostgreSQL exited before readiness")
            pid_file = data / "postmaster.pid"
            fields = pid_file.read_text().splitlines() if pid_file.is_file() else []
            if len(fields) >= 8 and fields[0] == str(child.pid) and fields[3] == str(port) and fields[7].strip() == "ready":
                return port
            time.sleep(0.1)
        raise RuntimeError(f"{name} PostgreSQL did not become ready")

    table_names = ",".join(f"'public.{table}'::regclass" for table in TABLES)
    constraint_names = ",".join(f"'{name}'" for name in NAMES)
    query = f"""
      SET search_path TO pg_catalog;
      SELECT conname, oid, pg_get_expr(conbin, conrelid, false)
        FROM pg_constraint
       WHERE conrelid IN ({table_names}) AND conname IN ({constraint_names}) ORDER BY conname;
    """
    read_rows = """
      SELECT 'family', to_jsonb(f) FROM public.mixer_authz_families f ORDER BY f.id;
      SELECT 'credential', to_jsonb(c) FROM public.mixer_authz_credentials c ORDER BY c.reference;
    """

    def expressions(rows):
        return {name: expression for name, _, expression in (row.split("|", 2) for row in rows.splitlines())}

    reports = {}
    try:
        version = run("postgres", "--version")
        assert " 17." in version, version
        source, restored = start("source"), start("restored")
        cluster_query = "SELECT system_identifier FROM pg_control_system()"
        assert sql(source, cluster_query) != sql(restored, cluster_query)
        # Use the checked-in migration's table declarations, before the separate policy installation.
        ddl = MIGRATION.read_text().split('statements("""', 1)[1].split('""")', 1)[0]
        sql(source, ddl + """
          INSERT INTO public.mixer_authz_profiles VALUES ('fixture',1,'http://localhost','test','human',true);
          INSERT INTO public.mixer_authz_principals VALUES ('owner','human',true,0,1);
          INSERT INTO public.mixer_authz_families VALUES
            ('bounded','fixture',1,'owner',true,10,11,1), ('open','fixture',1,'owner',true,10,NULL,1);
          INSERT INTO public.mixer_authz_credentials VALUES
            ('fixture',1,'bounded','owner','bounded',true,10,11,1),
            ('fixture',1,'open','owner','open',true,10,NULL,1);
        """)
        manifest = json.loads(MANIFEST.read_text())
        pinned = {name: next(row["expression"] for row in manifest["check_keys"]
                             if row["relation"] == f"public.{table}" and row["columns"] == ["expires_at","not_before"])
                  for name, table in zip(NAMES, TABLES)}
        assert expressions(sql(source, query)) == pinned
        dump = work / "source.dump"
        run("pg_dump", *argv(source), "--format=custom", "--file", dump)
        run("pg_restore", *argv(restored), "--exit-on-error", dump)
        raw = expressions(sql(restored, query))
        assert all(raw[name] != pinned[name] for name in NAMES)
        assert sql(restored, read_rows) == sql(source, read_rows)

        for expiry in (10, -1, 9007199254740992):
            for table in TABLES:
                error = sql(restored, f"UPDATE public.{table} SET expires_at={expiry}", expected=1)
                assert f'{table}_check' in error

        run("psql", *argv(restored), "-Xq", "-f", REPAIR)
        fixed = sql(restored, query)
        assert expressions(fixed) == pinned and sql(restored, read_rows) == sql(source, read_rows)
        run("psql", *argv(restored), "-Xq", "-f", REPAIR)
        assert sql(restored, query) == fixed

        sql(restored, """
          ALTER TABLE public.mixer_authz_credentials DROP CONSTRAINT mixer_authz_credentials_check,
            ADD CONSTRAINT mixer_authz_credentials_check
            CHECK (expires_at >= 0 AND expires_at <= 9007199254740991 AND expires_at > not_before);
          ALTER TABLE public.mixer_authz_families DROP CONSTRAINT mixer_authz_families_check,
            ADD CONSTRAINT mixer_authz_families_check CHECK (expires_at > not_before);
        """)
        unexpected = sql(restored, query)
        error = run("psql", *argv(restored), "-Xq", "-f", REPAIR, expected=3)
        assert "Unexpected restored CHECK on public.mixer_authz_families" in error
        assert sql(restored, query) == unexpected and sql(restored, read_rows) == sql(source, read_rows)
        reports = dict(postgres=version, exactChecks=2, unchangedSeedRows=4, refusedInvalidUpdates=6,
                       idempotent=True, rolledBackUnknownConstraint=True)
    finally:
        for server in reversed(owners):
            try:
                if server.poll() is None:
                    server.send_signal(signal.SIGINT)
                server.wait(timeout=12)
                if not group_absent(server.pid):
                    raise RuntimeError("PostgreSQL group did not close")
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                holds.append(dict(pid=server.pid, type="postgres"))
        if holds:
            (work/"HOLD.json").write_text(json.dumps(holds, indent=2))
            raise RuntimeError(f"Unresolved test custody at {work}")
        shutil.rmtree(work)
        for port in ports:
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", port))
    print(json.dumps({**reports, "closedCommands": len(closed), "closedClusters": len(owners),
                      "portsRebound": len(ports), "scratchRemoved": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-bin", required=True, type=Path)
    replay(parser.parse_args().postgres_bin.resolve())
